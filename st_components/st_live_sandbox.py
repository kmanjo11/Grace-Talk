"""
Live Sandbox Display Component
Provides real-time view of sandbox execution with maximize/minimize functionality
"""

import streamlit as st
import time
import threading
import queue
from datetime import datetime
from src.utils.docker_executor import DockerCodeExecutor
from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
from src.utils.python_sandbox import RestrictedEnvironment

class LiveSandboxDisplay:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.is_recording = False
        self.session_log = []
        
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

def show_live_sandbox_window():
    """Display the live sandbox window with maximize/minimize functionality"""
    
    # Initialize display if not exists
    if 'live_sandbox_display' not in st.session_state:
        st.session_state['live_sandbox_display'] = LiveSandboxDisplay()
    
    display = st.session_state['live_sandbox_display']
    
    # Window controls
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.subheader("📺 Live Sandbox Monitor")
    
    with col2:
        is_minimized = st.session_state.get('sandbox_minimized', False)
        if st.button("🔽" if not is_minimized else "🔼", help="Minimize/Maximize"):
            st.session_state['sandbox_minimized'] = not is_minimized
    
    with col3:
        if st.button("🔴" if not display.is_recording else "⏹️", help="Start/Stop Recording"):
            display.is_recording = not display.is_recording
            if display.is_recording:
                display.add_output("Recording started", "system")
            else:
                display.add_output("Recording stopped", "system")
    
    with col4:
        if st.button("❌", help="Close Live View"):
            st.session_state['show_live_sandbox'] = False
            st.rerun()
    
    # Don't show content if minimized
    if st.session_state.get('sandbox_minimized', False):
        st.caption("Live Sandbox Monitor (Minimized)")
        return
    
    # Status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Real-time indicator
        current_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"🔴 **LIVE** {current_time}")
    
    with col2:
        # Active sandbox indicator
        active_sandbox = detect_active_sandbox()
        icon = display.get_sandbox_icon(active_sandbox)
        st.markdown(f"{icon} **{active_sandbox.upper()}**")
    
    with col3:
        # Recording indicator
        if display.is_recording:
            st.markdown("🔴 **REC**")
        else:
            st.markdown("⚪ **STANDBY**")
    
    # Live output display
    st.markdown("---")
    
    # Create scrollable container for output
    output_container = st.container()
    
    with output_container:
        # Show recent log entries (last 20)
        recent_logs = display.session_log[-20:] if display.session_log else []
        
        if not recent_logs:
            st.info("Waiting for sandbox activity...")
        else:
            for entry in recent_logs:
                icon = display.get_sandbox_icon(entry['type'])
                st.text(f"[{entry['timestamp']}] {icon} {entry['message']}")
    
    # Auto-refresh every 2 seconds
    time.sleep(0.1)  # Small delay to prevent excessive refreshing

def detect_active_sandbox():
    """Detect which sandbox is currently active"""
    try:
        # Check Docker availability
        docker_executor = DockerCodeExecutor()
        if docker_executor.is_available():
            return "docker"
        
        # Check Ubuntu sandbox
        ubuntu_sandbox = UbuntuSandboxExecutor()
        if ubuntu_sandbox.is_available():
            return "ubuntu"
        
        # Fallback to Python sandbox
        return "python"
        
    except Exception:
        return "local"

def integrate_with_interpreter():
    """Hook into interpreter execution to capture live output"""
    if 'live_sandbox_display' in st.session_state and st.session_state.get('show_live_sandbox', False):
        display = st.session_state['live_sandbox_display']
        
        # Add sample activity (this would be integrated with actual execution)
        sandbox_type = detect_active_sandbox()
        display.add_output(f"Sandbox {sandbox_type} ready for execution", sandbox_type)
        
        return display
    return None

# Auto-refresh component for live updates
def live_sandbox_auto_refresh():
    """Auto-refresh component to update live display"""
    if st.session_state.get('show_live_sandbox', False):
        # Use st.empty() for dynamic updates
        placeholder = st.empty()
        
        with placeholder.container():
            show_live_sandbox_window()
        
        # Auto-refresh every 2 seconds
        if 'last_refresh' not in st.session_state:
            st.session_state['last_refresh'] = time.time()
        
        if time.time() - st.session_state['last_refresh'] > 2:
            st.session_state['last_refresh'] = time.time()
            st.rerun()
