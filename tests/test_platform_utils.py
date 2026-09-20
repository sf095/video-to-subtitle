import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video_to_subtitle.platform_utils import is_gradio_temp_path


def test_is_gradio_temp_path():
    assert is_gradio_temp_path("/private/var/folders/37/2x/T/gradio/abc1234/clip.mp4") is True
    assert is_gradio_temp_path("/tmp/gradio/123/video.mp4") is True
    assert is_gradio_temp_path("/Users/user/Videos/gradio_cached/sample.mp4") is True
    assert is_gradio_temp_path("/Users/user/Videos/my_normal_video.mp4") is False
    assert is_gradio_temp_path(None) is False
    assert is_gradio_temp_path("") is False


if __name__ == "__main__":
    test_is_gradio_temp_path()
    print("✓ test_platform_utils passed.")
