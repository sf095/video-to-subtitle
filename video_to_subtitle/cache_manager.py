"""
Cache and storage management utilities for Video-to-Subtitle.

Manages:
1. Gradio temporary upload files, subtitle export archives, and audio/video temp directories.
2. Hugging Face faster-whisper downloaded model weights and RAM eviction.
3. Automatic cleanup of session temporary directories on application exit.
"""

import atexit
import glob
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple

from video_to_subtitle.engine import evict_model_from_cache

# Track session-created temporary directories for atexit cleanup
_SESSION_TEMP_DIRS: Set[str] = set()
_EXIT_HANDLER_REGISTERED: bool = False

# Known faster-whisper model sizes
KNOWN_MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large-v3-turbo"]


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable representation."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_dir_size_and_count(path: str) -> Tuple[int, int]:
    """Calculate total size in bytes and file count of a directory recursively."""
    if not os.path.exists(path):
        return 0, 0
    if os.path.isfile(path):
        return os.path.getsize(path), 1

    total_size = 0
    file_count = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
    except OSError:
        pass
    return total_size, file_count


def get_temp_directories() -> List[str]:
    """Retrieve all temporary directories associated with Gradio and app exports."""
    temp_root = tempfile.gettempdir()
    dirs = []

    # Gradio temp upload directory
    gradio_env = os.environ.get("GRADIO_TEMP_DIR")
    if gradio_env and os.path.exists(gradio_env):
        dirs.append(os.path.abspath(gradio_env))
    else:
        std_gradio_dir = os.path.join(temp_root, "gradio")
        if os.path.exists(std_gradio_dir):
            dirs.append(std_gradio_dir)

    # Subtitle exports and whisper audio temp dirs
    for pattern in ["subtitles_export_*", "whisper_audio_*"]:
        for p in glob.glob(os.path.join(temp_root, pattern)):
            if os.path.isdir(p):
                dirs.append(p)

    # Project-local .gradio cached examples if present
    local_gradio = os.path.abspath(".gradio")
    if os.path.exists(local_gradio):
        dirs.append(local_gradio)

    return list(dict.fromkeys(dirs))


def get_temp_cache_stats() -> Dict[str, Any]:
    """Get total storage stats for temporary files (Gradio uploads and app exports)."""
    dirs = get_temp_directories()
    total_bytes = 0
    total_files = 0

    for d in dirs:
        size, count = get_dir_size_and_count(d)
        total_bytes += size
        total_files += count

    return {
        "total_bytes": total_bytes,
        "formatted_size": format_bytes(total_bytes),
        "file_count": total_files,
        "directories": dirs,
    }


def clear_temp_cache() -> Dict[str, Any]:
    """
    Purge all temporary files and export directories.
    Handles file locking or permission errors safely without raising exceptions.
    """
    dirs = get_temp_directories()
    bytes_freed = 0
    files_removed = 0
    errors = []

    for d in dirs:
        if not os.path.exists(d):
            continue
        try:
            size_before, count_before = get_dir_size_and_count(d)

            # For Gradio upload directory, delete contents but keep directory itself
            if os.path.basename(d) == "gradio" or d == os.environ.get("GRADIO_TEMP_DIR"):
                for entry in os.scandir(d):
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            shutil.rmtree(entry.path, ignore_errors=True)
                        else:
                            os.remove(entry.path)
                    except Exception as e:
                        errors.append(f"{entry.path}: {e}")
            else:
                shutil.rmtree(d, ignore_errors=True)

            size_after, count_after = get_dir_size_and_count(d) if os.path.exists(d) else (0, 0)
            bytes_freed += max(0, size_before - size_after)
            files_removed += max(0, count_before - count_after)
        except Exception as e:
            errors.append(f"{d}: {e}")

    return {
        "bytes_freed": bytes_freed,
        "formatted_freed": format_bytes(bytes_freed),
        "files_removed": files_removed,
        "errors": errors,
    }


def get_hf_hub_cache_dir() -> str:
    """Resolve Hugging Face Hub cache directory path."""
    try:
        from huggingface_hub.constants import HUGGINGFACE_HUB_CACHE
        return HUGGINGFACE_HUB_CACHE
    except Exception:
        hf_home = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
        return os.path.join(hf_home, "hub")


def get_model_cache_stats() -> Dict[str, Any]:
    """
    Get storage consumption for all downloaded faster-whisper models.
    """
    hub_cache = get_hf_hub_cache_dir()
    models_info = []
    total_bytes = 0

    if os.path.exists(hub_cache):
        for entry in os.scandir(hub_cache):
            if entry.is_dir() and "faster-whisper" in entry.name:
                model_name = entry.name.replace("models--Systran--faster-whisper-", "").replace("models--", "")
                size, count = get_dir_size_and_count(entry.path)
                total_bytes += size
                models_info.append({
                    "raw_dir_name": entry.name,
                    "model_size": model_name,
                    "bytes": size,
                    "formatted_size": format_bytes(size),
                    "path": entry.path,
                })

    models_info.sort(key=lambda m: m["bytes"], reverse=True)
    return {
        "total_bytes": total_bytes,
        "formatted_total": format_bytes(total_bytes),
        "models": models_info,
    }


def clear_model_cache(model_size: Optional[str] = None) -> Dict[str, Any]:
    """
    Delete downloaded faster-whisper model weights and evict from RAM.

    Args:
        model_size: Specific model size to delete (e.g. 'medium', 'tiny'), or 'All Models' / None for all.

    Returns:
        Dict with bytes_freed, formatted_freed, removed_models, and errors.
    """
    hub_cache = get_hf_hub_cache_dir()
    bytes_freed = 0
    removed_models = []
    errors = []

    target_all = (model_size is None or model_size.lower() in ("all", "all models", "*"))

    if os.path.exists(hub_cache):
        for entry in os.scandir(hub_cache):
            if not (entry.is_dir() and "faster-whisper" in entry.name):
                continue

            current_size_name = entry.name.replace("models--Systran--faster-whisper-", "").replace("models--", "")
            
            # Check match
            match = False
            if target_all:
                match = True
            elif model_size and (model_size.lower() == current_size_name.lower() or model_size.lower() in entry.name.lower()):
                match = True

            if match:
                try:
                    dir_size, _ = get_dir_size_and_count(entry.path)
                    shutil.rmtree(entry.path, ignore_errors=False)
                    bytes_freed += dir_size
                    removed_models.append(current_size_name)
                    # Also evict from RAM
                    evict_model_from_cache(current_size_name)
                except Exception as e:
                    errors.append(f"{entry.name}: {e}")

    if target_all:
        evict_model_from_cache(None)

    return {
        "bytes_freed": bytes_freed,
        "formatted_freed": format_bytes(bytes_freed),
        "removed_models": removed_models,
        "errors": errors,
    }


def register_session_temp_dir(path: str) -> None:
    """Register a temporary directory created by the current session for exit cleanup."""
    if path:
        _SESSION_TEMP_DIRS.add(os.path.abspath(path))


def cleanup_session_temp_files() -> None:
    """
    Invoked upon application exit.
    Cleans up all tracked temporary directories without touching AI model weights.
    """
    for path in list(_SESSION_TEMP_DIRS):
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass
    _SESSION_TEMP_DIRS.clear()


def register_exit_cleanup() -> None:
    """Register the session cleanup handler with atexit."""
    global _EXIT_HANDLER_REGISTERED
    if not _EXIT_HANDLER_REGISTERED:
        atexit.register(cleanup_session_temp_files)
        _EXIT_HANDLER_REGISTERED = True
