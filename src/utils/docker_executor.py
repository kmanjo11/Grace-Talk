import tempfile
import os
import uuid
try:
    import docker  # type: ignore
except Exception:  # Docker SDK not installed
    docker = None

class DockerCodeExecutor:
    def __init__(self):
        self.client = None
        self.image_name = "oi-code-sandbox"

    def is_available(self) -> bool:
        """Return True if Docker SDK and daemon are reachable."""
        if docker is None:
            return False
        try:
            if self.client is None:
                self.client = docker.from_env()
            # ping server
            self.client.ping()
            return True
        except Exception:
            self.client = None
            return False

    def _build_sandbox_image(self):
        """Build the sandbox Docker image if it doesn't exist"""
        if not self.is_available():
            raise RuntimeError("Docker is not available")
        try:
            self.client.images.get(self.image_name)
        except Exception:
            dockerfile_content = """
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home --shell /bin/bash sandbox

USER sandbox
WORKDIR /home/sandbox

# Set resource limits
ENV PYTHONPATH=/home/sandbox
"""
            with tempfile.TemporaryDirectory() as temp_dir:
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                self.client.images.build(
                    path=temp_dir,
                    tag=self.image_name,
                    rm=True
                )

    def execute_code(self, code: str, language: str = "python") -> str:
        """Execute code in a Docker container"""
        if not self.is_available():
            return "Docker not available"
        self._build_sandbox_image()

        # Create temporary file for code (use .py for python)
        ext = '.py' if language == 'python' else f'.{language}'
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as code_file:
            code_file.write(code)
            code_file_path = code_file.name

        try:
            # Run code in container
            container = self.client.containers.run(
                self.image_name,
                command=f"python {os.path.basename(code_file_path)}" if language == "python" else f"node {os.path.basename(code_file_path)}",
                volumes={code_file_path: {'bind': f'/home/sandbox/{os.path.basename(code_file_path)}', 'mode': 'ro'}},
                working_dir='/home/sandbox',
                detach=False,
                stdout=True,
                stderr=True,
                remove=True,
                mem_limit='128m',  # Memory limit
                cpu_quota=50000,  # CPU limit (50% of one core)
                read_only=True,  # Read-only filesystem
                network_disabled=True  # No network access
            )

            return container.decode('utf-8')
        except Exception as e:
            # Includes docker.errors.ContainerError and others
            try:
                # Some errors provide stderr
                return f"Error: {e.stderr.decode('utf-8')}"
            except Exception:
                return f"Execution failed: {str(e)}"
        finally:
            # Clean up temporary file
            os.unlink(code_file_path)
