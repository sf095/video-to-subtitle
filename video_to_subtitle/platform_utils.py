"""Platform-specific utilities for temporary directory detection and file operations."""

import os
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
