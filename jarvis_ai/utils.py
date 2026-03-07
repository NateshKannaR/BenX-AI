"""
Utility functions for BenX
"""
import os
import shlex
import subprocess
from typing import Optional, List, Tuple, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def run_cmd(cmd: str, shell: bool = False, timeout: int = 30) -> Tuple[bool, str]:
    """Execute command safely with timeout"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=timeout)
        
        output = result.stdout.strip() if result.stdout else ""
        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Command failed"
            return False, error
        return True, output
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, f"Error: {str(e)}"

def find_tool(tools: List[str]) -> Optional[str]:
    """Find first available tool from list"""
    for tool in tools:
        success, _ = run_cmd(f"which {tool}")
        if success:
            return tool
    return None

def safe_open_app(app: Union[str, List[str]]) -> bool:
    """Safely open application in background"""
    try:
        env = os.environ.copy()
        if isinstance(app, str):
            args = shlex.split(app)
        else:
            args = app
        process = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, start_new_session=True, env=env
        )
        import time
        time.sleep(0.2)
        return process.poll() is None
    except:
        return False

def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return path"""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_file_size(path: Path) -> int:
    """Get file size in bytes"""
    try:
        return path.stat().st_size
    except:
        return 0








