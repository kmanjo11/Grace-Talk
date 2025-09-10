import os
import subprocess
import sys


def ensure_package(pip_name: str) -> bool:
    """Install a pip package at runtime if allowed. Returns True if available/installed."""
    if not pip_name:
        return False
    try:
        __import__(pip_name.split("[", 1)[0].replace('-', '_'))
        return True
    except Exception:
        pass

    allow = os.environ.get('AUTO_INSTALL_DEPS', '1') in ('1', 'true', 'True')
    if not allow:
        return False
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pip_name])
        return True
    except Exception:
        return False
