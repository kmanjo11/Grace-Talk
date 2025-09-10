"""
Ubuntu Sandbox Executor
Provides secure code execution using Linux namespaces, chroot, and resource limits
Fallback when Docker is not available
"""

import os
import sys
import subprocess
import tempfile
import shutil
import signal
import time
import pwd
import grp
import resource
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import json


class UbuntuSandboxExecutor:
    """
    Secure code execution sandbox using Linux security features
    """
    
    def __init__(self):
        self.sandbox_root = "/tmp/oi_sandbox"
        self.max_execution_time = 30  # seconds
        self.max_memory = 128 * 1024 * 1024  # 128MB
        self.max_cpu_time = 10  # seconds
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.sandbox_user = "nobody"
        self.sandbox_group = "nogroup"
        
    def is_available(self) -> bool:
        """Check if Ubuntu sandbox can be created"""
        try:
            # Check if we have necessary permissions and tools
            if os.geteuid() != 0:
                # Try to check if we can create basic sandbox without root
                return self._check_user_sandbox_capability()
            
            # Check for required tools
            required_tools = ['unshare', 'chroot']
            for tool in required_tools:
                if not shutil.which(tool):
                    return False
            
            # Test basic namespace creation
            result = subprocess.run(
                ['unshare', '--pid', '--fork', '--mount-proc', 'true'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _check_user_sandbox_capability(self) -> bool:
        """Check if user-level sandboxing is possible"""
        try:
            # Test if we can create a basic restricted environment
            test_dir = tempfile.mkdtemp(prefix="oi_test_")
            try:
                # Test basic file operations
                test_file = os.path.join(test_dir, "test.py")
                with open(test_file, 'w') as f:
                    f.write("print('test')")
                
                # Test basic Python execution with restrictions
                result = subprocess.run(
                    [sys.executable, test_file],
                    cwd=test_dir,
                    capture_output=True,
                    timeout=5,
                    env={'PATH': '/usr/bin:/bin', 'PYTHONPATH': ''}
                )
                return result.returncode == 0
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)
        except Exception:
            return False
    
    def _create_sandbox_environment(self) -> str:
        """Create isolated sandbox environment"""
        sandbox_id = str(uuid.uuid4())[:8]
        sandbox_path = os.path.join(self.sandbox_root, sandbox_id)
        
        # Create sandbox directory structure
        os.makedirs(sandbox_path, exist_ok=True)
        
        # Create basic directory structure
        dirs_to_create = [
            'bin', 'usr/bin', 'lib', 'lib64', 'usr/lib', 'usr/lib64',
            'tmp', 'home/sandbox', 'proc', 'dev', 'sys'
        ]
        
        for dir_name in dirs_to_create:
            os.makedirs(os.path.join(sandbox_path, dir_name), exist_ok=True)
        
        # Copy essential binaries
        essential_bins = [
            '/bin/sh', '/bin/bash', '/usr/bin/python3', '/usr/bin/python3.11'
        ]
        
        for bin_path in essential_bins:
            if os.path.exists(bin_path):
                dest_path = os.path.join(sandbox_path, bin_path.lstrip('/'))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                try:
                    shutil.copy2(bin_path, dest_path)
                except Exception:
                    pass  # Skip if copy fails
        
        # Copy essential libraries (simplified approach)
        self._copy_essential_libraries(sandbox_path)
        
        return sandbox_path
    
    def _copy_essential_libraries(self, sandbox_path: str):
        """Copy essential libraries for Python execution"""
        try:
            # Get Python library dependencies
            python_path = shutil.which('python3')
            if python_path:
                result = subprocess.run(
                    ['ldd', python_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if '=>' in line:
                            parts = line.split('=>')
                            if len(parts) > 1:
                                lib_path = parts[1].strip().split()[0]
                                if os.path.exists(lib_path):
                                    dest_path = os.path.join(sandbox_path, lib_path.lstrip('/'))
                                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                    try:
                                        shutil.copy2(lib_path, dest_path)
                                    except Exception:
                                        pass
        except Exception:
            pass  # Continue without library copying if it fails
    
    def _set_resource_limits(self):
        """Set resource limits for the sandbox process"""
        try:
            # Set memory limit
            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, self.max_memory))
            
            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))
            
            # Set file size limit
            resource.setrlimit(resource.RLIMIT_FSIZE, (self.max_file_size, self.max_file_size))
            
            # Limit number of processes
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            
        except Exception:
            pass  # Continue if resource limits can't be set
    
    def _create_restricted_environment(self) -> Dict[str, str]:
        """Create restricted environment variables"""
        return {
            'PATH': '/bin:/usr/bin',
            'HOME': '/home/sandbox',
            'USER': 'sandbox',
            'SHELL': '/bin/sh',
            'PYTHONPATH': '',
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONUNBUFFERED': '1',
        }
    
    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code in the Ubuntu sandbox"""
        if not self.is_available():
            return "Ubuntu sandbox not available"
        
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as code_file:
            code_file.write(code)
            code_file_path = code_file.name
        
        try:
            if os.geteuid() == 0:
                # Root execution with full sandboxing
                return self._execute_with_full_sandbox(code_file_path, language)
            else:
                # User-level execution with basic restrictions
                return self._execute_with_user_sandbox(code_file_path, language)
        finally:
            # Clean up temporary file
            try:
                os.unlink(code_file_path)
            except Exception:
                pass
    
    def _execute_with_full_sandbox(self, code_file_path: str, language: str) -> str:
        """Execute with full root-level sandboxing"""
        try:
            # Create sandbox environment
            sandbox_path = self._create_sandbox_environment()
            
            # Copy code file to sandbox
            sandbox_code_path = os.path.join(sandbox_path, 'home/sandbox/code.py')
            shutil.copy2(code_file_path, sandbox_code_path)
            
            # Prepare execution command
            if language == "python":
                cmd = ['python3', '/home/sandbox/code.py']
            else:
                return f"Language {language} not supported in Ubuntu sandbox"
            
            # Execute with namespace isolation
            full_cmd = [
                'unshare', '--pid', '--fork', '--mount-proc',
                '--net', '--ipc', '--uts',
                'chroot', sandbox_path
            ] + cmd
            
            # Set up environment
            env = self._create_restricted_environment()
            
            # Execute with timeout
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=self.max_execution_time,
                env=env,
                preexec_fn=self._set_resource_limits
            )
            
            # Clean up sandbox
            shutil.rmtree(sandbox_path, ignore_errors=True)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "Error: Execution timeout"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _execute_with_user_sandbox(self, code_file_path: str, language: str) -> str:
        """Execute with user-level restrictions"""
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory(prefix="oi_user_sandbox_") as temp_dir:
                # Copy code file to temp directory
                sandbox_code_path = os.path.join(temp_dir, f'code.{language}')
                shutil.copy2(code_file_path, sandbox_code_path)
                
                # Prepare execution command
                if language == "python":
                    cmd = [sys.executable, sandbox_code_path]
                else:
                    return f"Language {language} not supported in user sandbox"
                
                # Create restricted environment
                env = self._create_restricted_environment()
                env.update(os.environ)  # Keep some system environment
                
                # Execute with restrictions
                result = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.max_execution_time,
                    env=env
                )
                
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error: {result.stderr}"
                    
        except subprocess.TimeoutExpired:
            return "Error: Execution timeout"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def cleanup(self):
        """Clean up sandbox resources"""
        try:
            if os.path.exists(self.sandbox_root):
                shutil.rmtree(self.sandbox_root, ignore_errors=True)
        except Exception:
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get sandbox status information"""
        return {
            "available": self.is_available(),
            "type": "ubuntu_sandbox",
            "root_access": os.geteuid() == 0,
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory // (1024 * 1024),
            "sandbox_root": self.sandbox_root
        }

