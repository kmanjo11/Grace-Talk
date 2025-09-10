#!/usr/bin/env python3
"""
Test script for Ubuntu sandbox functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.ubuntu_sandbox import UbuntuSandboxExecutor
from src.utils.docker_executor import DockerCodeExecutor

def test_ubuntu_sandbox():
    """Test Ubuntu sandbox functionality"""
    print("Testing Ubuntu Sandbox...")
    
    sandbox = UbuntuSandboxExecutor()
    
    # Test availability
    print(f"Ubuntu sandbox available: {sandbox.is_available()}")
    
    # Test status
    status = sandbox.get_status()
    print(f"Sandbox status: {status}")
    
    # Test simple Python code execution
    test_code = """
print("Hello from Ubuntu sandbox!")
import sys
print(f"Python version: {sys.version}")
print("Basic math:", 2 + 2)
"""
    
    print("\nExecuting test code...")
    result = sandbox.execute_code(test_code, "python")
    print(f"Result: {result}")
    
    # Test with error handling
    error_code = """
print("Testing error handling...")
raise ValueError("This is a test error")
"""
    
    print("\nTesting error handling...")
    error_result = sandbox.execute_code(error_code, "python")
    print(f"Error result: {error_result}")
    
    # Cleanup
    sandbox.cleanup()
    print("Ubuntu sandbox test completed.")

def test_docker_sandbox():
    """Test Docker sandbox for comparison"""
    print("\nTesting Docker Sandbox...")
    
    docker = DockerCodeExecutor()
    
    # Test availability
    print(f"Docker sandbox available: {docker.is_available()}")
    
    if docker.is_available():
        test_code = """
print("Hello from Docker sandbox!")
import sys
print(f"Python version: {sys.version}")
print("Basic math:", 3 + 3)
"""
        
        print("Executing test code in Docker...")
        result = docker.execute_code(test_code, "python")
        print(f"Docker result: {result}")
    else:
        print("Docker not available for testing")

def test_fallback_chain():
    """Test the complete fallback chain"""
    print("\n" + "="*50)
    print("Testing Complete Sandbox Fallback Chain")
    print("="*50)
    
    # Import the interpreter setup to test the full chain
    try:
        import streamlit as st
        from st_components.st_interpreter import setup_interpreter
        
        # Initialize minimal session state
        if 'interpreter' not in st.session_state:
            from interpreter import interpreter
            st.session_state['interpreter'] = interpreter
        
        if 'docker_available' not in st.session_state:
            st.session_state['docker_available'] = False
        
        if 'prefer_local_exec' not in st.session_state:
            st.session_state['prefer_local_exec'] = False
        
        print("Setting up interpreter with sandbox chain...")
        setup_interpreter()
        print("Interpreter setup completed successfully!")
        
    except Exception as e:
        print(f"Error testing fallback chain: {e}")
        print("This is expected if Streamlit components are not available in test mode")

if __name__ == "__main__":
    print("OpenInterpreter Sandbox Test Suite")
    print("=" * 40)
    
    test_ubuntu_sandbox()
    test_docker_sandbox()
    test_fallback_chain()
    
    print("\n" + "="*40)
    print("All tests completed!")

