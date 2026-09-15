import os
import sys
import subprocess
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video_to_subtitle.platform_utils import (
    is_gradio_temp_path,
    pick_local_file,
    pick_local_folder,
    reveal_in_file_manager,
)


def test_is_gradio_temp_path():
    assert is_gradio_temp_path("/private/var/folders/37/2x/T/gradio/abc1234/clip.mp4") is True
    assert is_gradio_temp_path("/tmp/gradio/123/video.mp4") is True
    assert is_gradio_temp_path("/Users/user/Videos/gradio_cached/sample.mp4") is True
    assert is_gradio_temp_path("/Users/user/Videos/my_normal_video.mp4") is False
    assert is_gradio_temp_path(None) is False
    assert is_gradio_temp_path("") is False


def test_pick_local_file_success(tmp_path):
    fake_file = tmp_path / "video.mp4"
    fake_file.write_text("dummy")

    with patch("sys.platform", "darwin"):
        mock_res = MagicMock(returncode=0, stdout=str(fake_file) + "\n")
        with patch("subprocess.run", return_value=mock_res) as mock_run:
            result = pick_local_file()
            assert result == str(fake_file)
            mock_run.assert_called_once()


def test_pick_local_file_cancelled():
    with patch("sys.platform", "darwin"):
        mock_res = MagicMock(returncode=0, stdout="\n")
        with patch("subprocess.run", return_value=mock_res):
            result = pick_local_file()
            assert result is None


def test_pick_local_file_non_darwin():
    with patch("sys.platform", "linux"):
        result = pick_local_file()
        assert result is None


def test_pick_local_folder_success(tmp_path):
    with patch("sys.platform", "darwin"):
        mock_res = MagicMock(returncode=0, stdout=str(tmp_path) + "\n")
        with patch("subprocess.run", return_value=mock_res) as mock_run:
            result = pick_local_folder()
            assert result == str(tmp_path)
            mock_run.assert_called_once()


def test_reveal_in_file_manager(tmp_path):
    fake_file = tmp_path / "video.mp4"
    fake_file.write_text("dummy")

    with patch("sys.platform", "darwin"):
        with patch("subprocess.run") as mock_run:
            ok = reveal_in_file_manager(str(fake_file))
            assert ok is True
            mock_run.assert_called_once_with(["open", "-R", str(fake_file)], check=True)

        with patch("subprocess.run") as mock_run:
            ok = reveal_in_file_manager(str(tmp_path))
            assert ok is True
            mock_run.assert_called_once_with(["open", str(tmp_path)], check=True)


if __name__ == "__main__":
    test_is_gradio_temp_path()
    test_pick_local_file_success(sys.modules["pathlib"].Path("/tmp"))
    print("✓ test_platform_utils passed.")
