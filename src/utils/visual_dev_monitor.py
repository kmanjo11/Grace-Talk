"""
Visual Development Monitor
Captures and displays visual output from web development in sandboxes
"""

import subprocess
import time
import threading
import queue
import socket
import requests
from datetime import datetime
import base64
import io
from PIL import Image, ImageGrab
import streamlit as st

class VisualDevMonitor:
    def __init__(self):
        self.running_services = {}
        self.screenshots = {}
        self.port_monitor_thread = None
        self.is_monitoring = False
        
    def start_monitoring(self):
        """Start monitoring for web services and visual changes"""
        self.is_monitoring = True
        if not self.port_monitor_thread or not self.port_monitor_thread.is_alive():
            self.port_monitor_thread = threading.Thread(target=self._monitor_ports)
            self.port_monitor_thread.daemon = True
            self.port_monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        
    def _monitor_ports(self):
        """Monitor common development ports for new services"""
        common_ports = [3000, 3001, 5000, 5001, 8000, 8080, 8501, 4200, 9000]
        
        while self.is_monitoring:
            for port in common_ports:
                if self._is_port_open(port) and port not in self.running_services:
                    self._detect_service_type(port)
                elif not self._is_port_open(port) and port in self.running_services:
                    # Service stopped
                    if port in self.running_services:
                        del self.running_services[port]
                    if port in self.screenshots:
                        del self.screenshots[port]
            
            time.sleep(2)  # Check every 2 seconds
    
    def _is_port_open(self, port):
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _detect_service_type(self, port):
        """Detect what type of service is running on a port"""
        try:
            response = requests.get(f'http://localhost:{port}', timeout=5)
            content = response.text.lower()
            
            # Detect service type based on content
            if 'react' in content or 'webpack' in content:
                service_type = 'react'
            elif 'streamlit' in content:
                service_type = 'streamlit'
            elif 'flask' in content or 'werkzeug' in content:
                service_type = 'flask'
            elif 'angular' in content:
                service_type = 'angular'
            elif 'vue' in content:
                service_type = 'vue'
            else:
                service_type = 'web'
            
            self.running_services[port] = {
                'type': service_type,
                'url': f'http://localhost:{port}',
                'detected_at': datetime.now(),
                'status': 'active'
            }
            
            # Take initial screenshot
            self._capture_screenshot(port)
            
        except Exception as e:
            # Still register as unknown web service
            self.running_services[port] = {
                'type': 'unknown',
                'url': f'http://localhost:{port}',
                'detected_at': datetime.now(),
                'status': 'active',
                'error': str(e)
            }
    
    def _detect_web_services(self, output: str, sandbox_type: str):
        """Detect web services from output text"""
        import re
        
        # Common patterns for web service startup
        patterns = [
            (r'Running on http://[^:]+:(\d+)', 'flask'),
            (r'serving at http://[^:]+:(\d+)', 'http_server'),
            (r'Local:\s+http://[^:]+:(\d+)', 'react'),
            (r'localhost:(\d+)', 'generic'),
            (r'port\s+(\d+)', 'generic')
        ]
        
        for pattern, service_type in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            for match in matches:
                port = int(match)
                if port not in self.running_services:
                    self.running_services[port] = {
                        'type': service_type,
                        'url': f'http://localhost:{port}',
                        'detected_at': datetime.now(),
                        'status': 'active',
                        'sandbox': sandbox_type
                    }
    
    def _capture_screenshot(self, port):
        """Capture screenshot of a web service"""
        try:
            # Use headless browser approach (simplified)
            url = f'http://localhost:{port}'
            
            # For now, we'll use a placeholder approach
            # In a full implementation, you'd use selenium or playwright
            self.screenshots[port] = {
                'timestamp': datetime.now(),
                'url': url,
                'status': 'captured',
                'method': 'placeholder'
            }
            
        except Exception as e:
            self.screenshots[port] = {
                'timestamp': datetime.now(),
                'url': f'http://localhost:{port}',
                'status': 'error',
                'error': str(e)
            }
    
    def get_service_preview_html(self, port):
        """Generate HTML for service preview"""
        if port not in self.running_services:
            return "<p>Service not found</p>"
        
        service = self.running_services[port]
        url = service['url']
        
        # Create iframe with security sandbox
        iframe_html = f"""
        <div style="border: 2px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background: #f5f5f5; padding: 8px; font-size: 12px; border-bottom: 1px solid #ddd;">
                <strong>{service['type'].title()}</strong> - {url}
                <span style="float: right; color: green;">● Live</span>
            </div>
            <iframe 
                src="{url}" 
                width="100%" 
                height="400" 
                frameborder="0"
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-top-navigation"
                style="display: block;"
            ></iframe>
        </div>
        """
        return iframe_html
    
    def get_service_info(self, port):
        """Get detailed service information"""
        if port not in self.running_services:
            return None
        
        service = self.running_services[port]
        
        # Try to get additional info
        try:
            response = requests.get(service['url'], timeout=3)
            service['response_time'] = response.elapsed.total_seconds()
            service['status_code'] = response.status_code
            service['content_length'] = len(response.content)
        except:
            pass
        
        return service
    
    def get_all_services(self):
        """Get all detected services"""
        return self.running_services
    
    def refresh_service(self, port):
        """Refresh information for a specific service"""
        if port in self.running_services:
            self._detect_service_type(port)
            self._capture_screenshot(port)

class SandboxPortForwarder:
    """Handle port forwarding from sandboxes to host"""
    
    def __init__(self):
        self.forwarded_ports = {}
    
    def forward_docker_port(self, container_port, host_port=None):
        """Forward port from Docker container"""
        if host_port is None:
            host_port = container_port
        
        try:
            # This would integrate with Docker API
            # For now, we'll track the mapping
            self.forwarded_ports[container_port] = {
                'host_port': host_port,
                'type': 'docker',
                'status': 'active'
            }
            return host_port
        except Exception as e:
            return None
    
    def forward_ubuntu_port(self, sandbox_port, host_port=None):
        """Forward port from Ubuntu sandbox"""
        if host_port is None:
            host_port = sandbox_port
        
        try:
            # Use socat or similar for port forwarding
            cmd = f"socat TCP-LISTEN:{host_port},fork TCP:localhost:{sandbox_port}"
            # This would run in background
            self.forwarded_ports[sandbox_port] = {
                'host_port': host_port,
                'type': 'ubuntu',
                'status': 'active',
                'command': cmd
            }
            return host_port
        except Exception as e:
            return None
    
    def get_forwarded_ports(self):
        """Get all forwarded ports"""
        return self.forwarded_ports
    
    def stop_forwarding(self, port):
        """Stop forwarding for a specific port"""
        if port in self.forwarded_ports:
            # Stop the forwarding process
            del self.forwarded_ports[port]

def get_visual_dev_monitor():
    """Get or create visual development monitor instance"""
    if 'visual_dev_monitor' not in st.session_state:
        st.session_state['visual_dev_monitor'] = VisualDevMonitor()
    
    return st.session_state['visual_dev_monitor']

def get_port_forwarder():
    """Get or create port forwarder instance"""
    if 'port_forwarder' not in st.session_state:
        st.session_state['port_forwarder'] = SandboxPortForwarder()
    
    return st.session_state['port_forwarder']

