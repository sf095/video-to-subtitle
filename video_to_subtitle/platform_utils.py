"""Platform-specific utilities for macOS / desktop file dialogs and shell integration."""

import os
import sys
import subprocess
import tempfile
from typing import Optional


def is_gradio_temp_path(path: Optional[str]) -> bool:
    """
    Check if a path is located inside Gradio's upload temporary cache or system temp.
    Gradio uploads typically reside in:
      /private/var/folders/.../T/gradio/<hash>/<filename>
      /tmp/gradio/<hash>/<filename>
      <tempdir>/gradio/...
    """
    if not path:
        return False
    abs_path = os.path.abspath(path)
    parts = abs_path.split(os.sep)
    if "gradio" in parts or "gradio_cached" in parts:
        return True

    # Check custom Gradio temp dir env var
    gradio_temp = os.environ.get("GRADIO_TEMP_DIR")
    if gradio_temp and abs_path.startswith(os.path.abspath(gradio_temp)):
        return True

    return False


def pick_local_file(prompt: str = "Select Video or Audio File") -> Optional[str]:
    """
    Open a native macOS Finder file picker dialog and return the chosen POSIX path.
    Gracefully returns None if user cancels or if not running on macOS.
    """
    if sys.platform != "darwin":
        return None
    try:
        script = f'''
        try
            set chosen to choose file with prompt "{prompt}:"
            return POSIX path of chosen
        on error number -128
            return ""
        end try
        '''
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            path = res.stdout.strip()
            if os.path.exists(path):
                return path
        return None
    except Exception:
        return None


def pick_local_folder(prompt: str = "Select Output Folder") -> Optional[str]:
    """
    Open a native macOS Finder folder picker dialog and return the chosen POSIX path.
    Gracefully returns None if user cancels or if not running on macOS.
    """
    if sys.platform != "darwin":
        return None
    try:
        script = f'''
        try
            set chosen to choose folder with prompt "{prompt}:"
            return POSIX path of chosen
        on error number -128
            return ""
        end try
        '''
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            path = res.stdout.strip()
            if os.path.isdir(path):
                return path
        return None
    except Exception:
        return None


def reveal_in_file_manager(path: str) -> bool:
    """
    Reveal a file or folder in macOS Finder (or open it on other systems).
    Returns True if launched successfully.
    """
    if not path or not os.path.exists(path):
        return False
    try:
        if sys.platform == "darwin":
            if os.path.isfile(path):
                subprocess.run(["open", "-R", path], check=True)
            else:
                subprocess.run(["open", path], check=True)
            return True
        elif sys.platform.startswith("linux"):
            target = path if os.path.isdir(path) else os.path.dirname(path)
            subprocess.run(["xdg-open", target], check=True)
            return True
        elif sys.platform == "win32":
            if os.path.isfile(path):
                subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=True)
            else:
                subprocess.run(["explorer", os.path.normpath(path)], check=True)
            return True
    except Exception:
        pass
    return False
