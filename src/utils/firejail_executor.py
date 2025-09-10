import subprocess
import tempfile
import os
import shlex

class FirejailCodeExecutor:
    def __init__(self):
        self.firejail_path = self._find_firejail()

    def _find_firejail(self):
        """Find firejail executable"""
        try:
            result = subprocess.run(['which', 'firejail'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def is_available(self):
        """Check if firejail is available"""
        return self.firejail_path is not None

    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code in a Firejail sandbox"""
        if not self.is_available():
            raise Exception("Firejail is not installed or not found in PATH")

        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as code_file:
            code_file.write(code)
            code_file_path = code_file.name

        try:
            # Build firejail command with restrictions
            cmd = [
                self.firejail_path,
                '--noprofile',  # Start with minimal profile
                '--private',    # Private filesystem
                '--private-dev', # Private /dev
                '--private-etc', # Private /etc
                '--noexec=/tmp', # No execution in /tmp
                '--noexec=/var', # No execution in /var
                '--noexec=/home', # No execution in /home (except allowed)
                '--read-only=/', # Read-only root filesystem
                '--whitelist=/usr',  # Allow /usr
                '--whitelist=/lib',  # Allow /lib
                '--whitelist=/lib64', # Allow /lib64
                '--whitelist=/bin',  # Allow /bin
                '--whitelist=/sbin', # Allow /sbin
                '--tmpfs=/tmp',    # Temporary filesystem for /tmp
                '--net=none',      # No network access
                '--memory-limit=128m',  # Memory limit
                '--cpu=1',         # CPU limit
            ]

            # Add language-specific execution
            if language == "python":
                cmd.extend(['python3', code_file_path])
            elif language == "bash" or language == "sh":
                cmd.extend(['bash', code_file_path])
            else:
                cmd.extend([language, code_file_path])

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr

            if result.returncode != 0:
                output += f"\nExit code: {result.returncode}"

            return output

        except subprocess.TimeoutExpired:
            return "Execution timed out after 30 seconds"
        except Exception as e:
            return f"Firejail execution failed: {str(e)}"
        finally:
            # Clean up temporary file
            try:
                os.unlink(code_file_path)
            except:
                pass
