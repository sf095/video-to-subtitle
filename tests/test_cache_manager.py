import os
import shutil
import tempfile
from unittest.mock import patch

from video_to_subtitle.cache_manager import (
    clear_model_cache,
    clear_temp_cache,
    cleanup_session_temp_files,
    format_bytes,
    get_dir_size_and_count,
    get_model_cache_stats,
    get_temp_cache_stats,
    register_session_temp_dir,
)
from video_to_subtitle.engine import _CACHED_MODELS, evict_model_from_cache


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
    assert format_bytes(2500 * 1024 * 1024) == "2.44 GB"


def test_get_dir_size_and_count(tmp_path):
    d = tmp_path / "test_dir"
    d.mkdir()
    f1 = d / "file1.txt"
    f1.write_text("hello")
    f2 = d / "file2.txt"
    f2.write_text("world!")

    size, count = get_dir_size_and_count(str(d))
    assert count == 2
    assert size == len("hello") + len("world!")


def test_temp_cache_stats_and_clear(tmp_path):
    temp_dir = tmp_path / "mock_temp"
    temp_dir.mkdir()
    gradio_dir = temp_dir / "gradio"
    gradio_dir.mkdir()
    (gradio_dir / "test.mp4").write_text("sample video content")

    export_dir = temp_dir / "subtitles_export_123"
    export_dir.mkdir()
    (export_dir / "subs.zip").write_text("sample zip")

    with patch("tempfile.gettempdir", return_value=str(temp_dir)):
        stats = get_temp_cache_stats()
        assert stats["total_bytes"] > 0
        assert stats["file_count"] == 2

        result = clear_temp_cache()
        assert result["files_removed"] == 2
        assert result["bytes_freed"] > 0

        # Verify gradio dir still exists but is empty
        assert os.path.exists(str(gradio_dir))
        assert len(os.listdir(str(gradio_dir))) == 0
        # Verify export dir was removed
        assert not os.path.exists(str(export_dir))


def test_model_cache_stats_and_selective_clear(tmp_path):
    hub_cache = tmp_path / "hub"
    hub_cache.mkdir()

    model_tiny = hub_cache / "models--Systran--faster-whisper-tiny"
    model_tiny.mkdir()
    (model_tiny / "model.bin").write_bytes(b"0" * 1000)

    model_med = hub_cache / "models--Systran--faster-whisper-medium"
    model_med.mkdir()
    (model_med / "model.bin").write_bytes(b"0" * 5000)

    with patch("video_to_subtitle.cache_manager.get_hf_hub_cache_dir", return_value=str(hub_cache)):
        stats = get_model_cache_stats()
        assert len(stats["models"]) == 2
        assert stats["total_bytes"] == 6000

        # Clear only tiny
        res = clear_model_cache("tiny")
        assert "tiny" in res["removed_models"]
        assert not os.path.exists(str(model_tiny))
        assert os.path.exists(str(model_med))

        # Clear remaining (medium) via "All Models"
        res_all = clear_model_cache("All Models")
        assert "medium" in res_all["removed_models"]
        assert not os.path.exists(str(model_med))


def test_evict_model_from_cache():
    _CACHED_MODELS.clear()
    _CACHED_MODELS["tiny_cpu_default"] = "mock_tiny"
    _CACHED_MODELS["medium_cpu_default"] = "mock_medium"

    assert len(_CACHED_MODELS) == 2

    # Evict tiny only
    evicted = evict_model_from_cache("tiny")
    assert evicted == 1
    assert "tiny_cpu_default" not in _CACHED_MODELS
    assert "medium_cpu_default" in _CACHED_MODELS

    # Evict all
    evicted_all = evict_model_from_cache(None)
    assert evicted_all == 1
    assert len(_CACHED_MODELS) == 0


def test_exit_cleanup_temp_files(tmp_path):
    session_dir = tmp_path / "subtitles_export_session"
    session_dir.mkdir()
    (session_dir / "out.srt").write_text("1\n00:00:00 --> 00:00:01\nHi")

    register_session_temp_dir(str(session_dir))
    assert os.path.exists(str(session_dir))

    cleanup_session_temp_files()
    assert not os.path.exists(str(session_dir))


def test_render_storage_info_and_choices():
    from app import get_downloaded_model_choices, render_storage_info

    info_md = render_storage_info()
    assert "### 💾 Local Storage & Cache Usage" in info_md
    assert "Temporary Files" in info_md
    assert "Downloaded Whisper Models" in info_md

    choices = get_downloaded_model_choices()
    assert isinstance(choices, list)
    assert len(choices) >= 1

