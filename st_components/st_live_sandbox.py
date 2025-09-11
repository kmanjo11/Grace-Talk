"""
Live Sandbox Display Component
Provides real-time view of sandbox execution with maximize/minimize functionality
Enhanced with tabbed interface for terminal and visual development monitoring
"""

import streamlit as st
import time
import threading
import queue
from datetime import datetime
from src.utils.docker_executor import DockerCodeExecutor
from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
from src.utils.python_sandbox import RestrictedEnvironment
from src.utils.visual_dev_monitor import get_visual_dev_monitor, get_port_forwarder
import subprocess
import requests
import socket

class LiveSandboxDisplay:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.is_recording = False
        self.session_log = []
        self.running_services = {}  # Track running web services
        self.port_mappings = {}     # Track port mappings
        
    def add_output(self, message, sandbox_type="system"):
        """Add output to the live display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            'timestamp': timestamp,
            'type': sandbox_type,
            'message': message
        }
        self.session_log.append(entry)
        self.output_queue.put(entry)
        
        # Check if this is a web service startup
        self.detect_web_service(message, sandbox_type)
        
    def detect_web_service(self, message, sandbox_type):
        """Detect when web services start and track their ports"""
        web_indicators = [
            ("Flask", "running on", "flask"),
            ("streamlit", "running on", "streamlit"), 
            ("npm start", "localhost:", "react"),
            ("serve", "serving at", "static"),
            ("python -m http.server", "Serving HTTP", "python_server")
        ]
        
        for indicator, port_text, service_type in web_indicators:
            if indicator.lower() in message.lower() and port_text.lower() in message.lower():
                # Extract port number
                import re
                port_match = re.search(r':(\d+)', message)
                if port_match:
                    port = int(port_match.group(1))
                    self.running_services[port] = {
                        'type': service_type,
                        'sandbox': sandbox_type,
                        'started_at': datetime.now(),
                        'status': 'running'
                    }
                    self.port_mappings[port] = f"http://localhost:{port}"
        
    def get_sandbox_icon(self, sandbox_type):
        """Get appropriate icon for sandbox type"""
        icons = {
            'docker': '🐳',
            'ubuntu': '🐧', 
            'python': '🐍',
            'firejail': '🔥',
            'system': '⚙️'
        }
        return icons.get(sandbox_type.lower(), '📟')
    
    def check_port_status(self, port):
        """Check if a port is accessible"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False

def show_live_sandbox_window():
    """Display the enhanced live sandbox window with tabbed interface"""
    
    # Initialize display if not exists
    if 'live_sandbox_display' not in st.session_state:
        st.session_state['live_sandbox_display'] = LiveSandboxDisplay()
    
    display = st.session_state['live_sandbox_display']
    
    # Create popup-style container
    with st.container():
        st.markdown("### 🖥️ Live Sandbox Monitor")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["🖥️ Terminal", "🌐 Web Services", "📊 System Info"])
        
        with tab1:
            render_terminal_view(display)
        
        with tab2:
            render_web_services_view(display)
            
        with tab3:
            render_system_info_view(display)

def render_terminal_view(display):
    """Render the terminal output view"""
    st.markdown("**Live Terminal Output:**")
    
    # Create scrollable container for terminal output
    terminal_container = st.container()
    
    with terminal_container:
        if display.session_log:
            # Show last 20 entries to prevent overwhelming
            recent_logs = display.session_log[-20:]
            
            for entry in recent_logs:
                icon = display.get_sandbox_icon(entry['type'])
                timestamp = entry['timestamp']
                message = entry['message']
                
                # Color code by sandbox type
                if entry['type'] == 'docker':
                    st.markdown(f"🐳 `{timestamp}` **Docker:** {message}")
                elif entry['type'] == 'ubuntu':
                    st.markdown(f"🐧 `{timestamp}` **Ubuntu:** {message}")
                elif entry['type'] == 'python':
                    st.markdown(f"🐍 `{timestamp}` **Python:** {message}")
                else:
                    st.markdown(f"{icon} `{timestamp}` {message}")
        else:
            st.info("No terminal output yet. Execute some code to see live output here!")

def render_web_services_view(display):
    """Render the enhanced web services monitoring view with visual development"""
    st.markdown("**Running Web Services:**")
    
    # Get visual development monitor
    visual_monitor = get_visual_dev_monitor()
    
    # Start monitoring if not already started
    if not visual_monitor.is_monitoring:
        visual_monitor.start_monitoring()
    
    # Combine services from both display and visual monitor
    all_services = {}
    
    # Add services from display (legacy)
    for port, service_info in display.running_services.items():
        all_services[port] = {
            'type': service_info['type'],
            'sandbox': service_info['sandbox'],
            'source': 'display'
        }
    
    # Add services from visual monitor (enhanced)
    for port, service_info in visual_monitor.get_all_services().items():
        all_services[port] = {
            'type': service_info['type'],
            'sandbox': 'auto-detected',
            'source': 'visual_monitor',
            'url': service_info['url'],
            'detected_at': service_info['detected_at']
        }
    
    if all_services:
        for port, service_info in all_services.items():
            # Create expandable service card
            with st.expander(f"{get_service_icon(service_info['type'])} {service_info['type'].title()} - Port {port}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Service Type:** {service_info['type'].title()}")
                    st.markdown(f"**Sandbox:** {display.get_sandbox_icon(service_info['sandbox'])} {service_info['sandbox']}")
                    
                    # Check if port is still active
                    is_active = display.check_port_status(port)
                    status = "🟢 Active" if is_active else "🔴 Inactive"
                    st.markdown(f"**Status:** {status}")
                    
                    if 'url' in service_info:
                        st.markdown(f"**URL:** [{service_info['url']}]({service_info['url']})")
                
                with col2:
                    # Control buttons
                    if st.button(f"🔄 Refresh", key=f"refresh_{port}"):
                        visual_monitor.refresh_service(port)
                        st.rerun()
                    
                    if st.button(f"🌐 Open", key=f"open_{port}"):
                        st.markdown(f"[Open in new tab]({service_info.get('url', f'http://localhost:{port}')})")
                
                # Visual preview section
                if is_active and service_info['source'] == 'visual_monitor':
                    st.markdown("**Live Preview:**")
                    
                    # Create tabs for different preview modes
                    preview_tab1, preview_tab2 = st.tabs(["🖼️ Embedded View", "📊 Service Info"])
                    
                    with preview_tab1:
                        try:
                            # Get preview HTML
                            preview_html = visual_monitor.get_service_preview_html(port)
                            st.components.v1.html(preview_html, height=450)
                        except Exception as e:
                            st.error(f"Could not load preview: {e}")
                            st.info(f"Try opening manually: http://localhost:{port}")
                    
                    with preview_tab2:
                        # Show detailed service information
                        service_details = visual_monitor.get_service_info(port)
                        if service_details:
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if 'response_time' in service_details:
                                    st.metric("Response Time", f"{service_details['response_time']:.3f}s")
                            
                            with col2:
                                if 'status_code' in service_details:
                                    st.metric("Status Code", service_details['status_code'])
                            
                            with col3:
                                if 'content_length' in service_details:
                                    st.metric("Content Size", f"{service_details['content_length']} bytes")
                            
                            # Show detection time
                            if 'detected_at' in service_details:
                                st.caption(f"Detected at: {service_details['detected_at'].strftime('%H:%M:%S')}")
                
                st.divider()
    else:
        st.info("No web services detected yet. Start a web server to see it here!")
        
        # Show monitoring status
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Auto-Detection Status:**")
            if visual_monitor.is_monitoring:
                st.success("🟢 Monitoring active")
            else:
                st.error("🔴 Monitoring inactive")
        
        with col2:
            if st.button("🔄 Start Monitoring"):
                visual_monitor.start_monitoring()
                st.rerun()
        
        st.markdown("**Supported services:**")
        st.markdown("- 🌶️ Flask applications")
        st.markdown("- ⚛️ React development servers")
        st.markdown("- 🎯 Streamlit applications")
        st.markdown("- 🐍 Python HTTP servers")
        st.markdown("- 📁 Static file servers")
        st.markdown("- 🅰️ Angular applications")
        st.markdown("- 🟢 Vue.js applications")

def render_system_info_view(display):
    """Render system information and sandbox status"""
    st.markdown("**Sandbox Environment Status:**")
    
    # Check available sandbox types
    sandbox_status = check_sandbox_availability()
    
    for sandbox_type, status in sandbox_status.items():
        icon = display.get_sandbox_icon(sandbox_type)
        status_icon = "✅" if status['available'] else "❌"
        st.markdown(f"{icon} **{sandbox_type.title()} Sandbox:** {status_icon} {status['status']}")
    
    st.divider()
    
    # Show session statistics
    st.markdown("**Session Statistics:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Commands", len(display.session_log))
    
    with col2:
        active_services = len([s for s in display.running_services.values() 
                             if display.check_port_status(list(display.running_services.keys())[0])])
        st.metric("Active Services", active_services)
    
    with col3:
        sandbox_types = len(set(entry['type'] for entry in display.session_log))
        st.metric("Sandbox Types Used", sandbox_types)

def get_service_icon(service_type):
    """Get icon for different service types"""
    icons = {
        'flask': '🌶️',
        'react': '⚛️',
        'streamlit': '🎯',
        'python_server': '🐍',
        'static': '📁',
        'nodejs': '🟢',
        'nginx': '🔷'
    }
    return icons.get(service_type, '🌐')

def check_sandbox_availability():
    """Check which sandbox environments are available"""
    status = {}
    
    # Check Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
        status['docker'] = {
            'available': result.returncode == 0,
            'status': 'Available' if result.returncode == 0 else 'Not installed'
        }
    except:
        status['docker'] = {'available': False, 'status': 'Not available'}
    
    # Check Firejail
    try:
        result = subprocess.run(['firejail', '--version'], capture_output=True, text=True, timeout=5)
        status['firejail'] = {
            'available': result.returncode == 0,
            'status': 'Available' if result.returncode == 0 else 'Not installed'
        }
    except:
        status['firejail'] = {'available': False, 'status': 'Not available'}
    
    # Ubuntu sandbox (always available as it's our fallback)
    status['ubuntu'] = {'available': True, 'status': 'Available (fallback)'}
    
    # Python sandbox (always available)
    status['python'] = {'available': True, 'status': 'Available (built-in)'}
    
    return status
