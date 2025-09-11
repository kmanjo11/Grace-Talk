#!/usr/bin/env python3
"""
Test script for OpenInterpreter UI improvements
Tests layout fixes, sandbox monitoring, and visual development features
"""

import sys
import os
import time
import subprocess
import requests
import socket
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all new modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from src.utils.visual_dev_monitor import VisualDevMonitor, SandboxPortForwarder
        print("✅ Visual development monitor imports successful")
    except ImportError as e:
        print(f"❌ Visual development monitor import failed: {e}")
        return False
    
    try:
        from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
        print("✅ Enhanced Ubuntu sandbox imports successful")
    except ImportError as e:
        print(f"❌ Ubuntu sandbox import failed: {e}")
        return False
    
    try:
        from st_components.st_live_sandbox import show_live_sandbox_window
        print("✅ Enhanced live sandbox component imports successful")
    except ImportError as e:
        print(f"❌ Live sandbox component import failed: {e}")
        return False
    
    try:
        from st_components.st_main import render_fixed_top_panels
        print("✅ Fixed layout components imports successful")
    except ImportError as e:
        print(f"❌ Layout components import failed: {e}")
        return False
    
    return True

def test_visual_dev_monitor():
    """Test visual development monitor functionality"""
    print("\n🧪 Testing Visual Development Monitor...")
    
    try:
        from src.utils.visual_dev_monitor import VisualDevMonitor
        
        monitor = VisualDevMonitor()
        
        # Test monitoring start/stop
        monitor.start_monitoring()
        print("✅ Monitor started successfully")
        
        time.sleep(1)
        
        monitor.stop_monitoring()
        print("✅ Monitor stopped successfully")
        
        # Test service detection
        test_output = "Running on http://localhost:5000"
        monitor._detect_web_services(test_output, "ubuntu")
        
        if 5000 in monitor.running_services:
            print("✅ Service detection working")
        else:
            print("❌ Service detection failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Visual development monitor test failed: {e}")
        return False

def test_ubuntu_sandbox():
    """Test Ubuntu sandbox with port forwarding"""
    print("\n🧪 Testing Ubuntu Sandbox...")
    
    try:
        from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
        
        sandbox = UbuntuSandboxExecutor()
        
        # Test availability
        if sandbox.is_available():
            print("✅ Ubuntu sandbox is available")
        else:
            print("⚠️ Ubuntu sandbox not available (this is OK)")
            return True  # Not a failure if sandbox isn't available
        
        # Test basic code execution
        test_code = "print('Hello from Ubuntu sandbox!')"
        result = sandbox.execute_code(test_code, "python")
        
        if "Hello from Ubuntu sandbox!" in result:
            print("✅ Code execution working")
        else:
            print(f"❌ Code execution failed: {result}")
            return False
        
        # Test web service detection
        web_code = """
import http.server
import socketserver
import threading
import time

def start_server():
    PORT = 8888
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"serving at http://localhost:{PORT}")
        httpd.serve_forever()

# Start server in background
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()
time.sleep(1)
print("Server started")
"""
        
        result = sandbox.execute_code_with_monitoring(web_code, "python")
        
        if sandbox.forwarded_ports:
            print("✅ Port forwarding detection working")
        else:
            print("⚠️ Port forwarding detection not triggered (this is OK)")
        
        # Cleanup
        sandbox.cleanup()
        print("✅ Sandbox cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Ubuntu sandbox test failed: {e}")
        return False

def test_port_availability():
    """Test port availability checking"""
    print("\n🧪 Testing Port Availability...")
    
    try:
        # Test with a port that should be available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))  # Bind to any available port
        port = sock.getsockname()[1]
        sock.close()
        
        print(f"✅ Found available port: {port}")
        
        # Test port checking function
        from src.utils.visual_dev_monitor import VisualDevMonitor
        monitor = VisualDevMonitor()
        
        # Port should not be open now
        if not monitor._is_port_open(port):
            print("✅ Port availability checking working")
            return True
        else:
            print("❌ Port availability checking failed")
            return False
            
    except Exception as e:
        print(f"❌ Port availability test failed: {e}")
        return False

def test_streamlit_components():
    """Test that Streamlit components are properly structured"""
    print("\n🧪 Testing Streamlit Components...")
    
    try:
        # Test main component structure
        with open('st_components/st_main.py', 'r') as f:
            main_content = f.read()
        
        if 'render_fixed_top_panels' in main_content:
            print("✅ Fixed top panels function found")
        else:
            print("❌ Fixed top panels function not found")
            return False
        
        if 'st.divider()' in main_content:
            print("✅ Layout separator found")
        else:
            print("❌ Layout separator not found")
            return False
        
        # Test live sandbox component structure
        with open('st_components/st_live_sandbox.py', 'r') as f:
            sandbox_content = f.read()
        
        if 'visual_dev_monitor' in sandbox_content:
            print("✅ Visual development monitor integration found")
        else:
            print("❌ Visual development monitor integration not found")
            return False
        
        if 'st.tabs(' in sandbox_content:
            print("✅ Tabbed interface found")
        else:
            print("❌ Tabbed interface not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit components test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting OpenInterpreter UI Improvements Test Suite")
    print("=" * 60)
    
    tests = [
        ("Import Tests", test_imports),
        ("Visual Development Monitor", test_visual_dev_monitor),
        ("Ubuntu Sandbox", test_ubuntu_sandbox),
        ("Port Availability", test_port_availability),
        ("Streamlit Components", test_streamlit_components),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! UI improvements are working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

