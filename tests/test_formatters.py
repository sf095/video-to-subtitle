import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video_to_subtitle.engine import SegmentTiming, WordTiming
from video_to_subtitle.formatters import (
    format_timestamp_srt,
    to_srt,
    export_srt,
)


def test_timestamp_formatting():
    secs = 3661.234  # 1 hour, 1 minute, 1 second, 234 ms
    assert format_timestamp_srt(secs) == "01:01:01,234", f"SRT failed: {format_timestamp_srt(secs)}"
    print("✓ Timestamp formatting tests passed.")


def test_formatters(tmp_path):
    words = [
        WordTiming(word=" Hello", start=0.5, end=0.9, probability=0.98),
        WordTiming(word=" world", start=1.0, end=1.5, probability=0.99),
    ]
    seg = SegmentTiming(
        id=0,
        start=0.5,
        end=1.5,
        text="Hello world",
        words=words,
    )
    segments = [seg]

    # Standard SRT
    srt = to_srt(segments)
    assert "Hello world" in srt
    assert "00:00:00,500 --> 00:00:01,500" in srt
    print("✓ Standard SRT test passed.")

    # Export SRT
    out_dir = str(tmp_path / "subtitles")
    srt_file = export_srt(segments, out_dir, "sample")
    assert os.path.exists(srt_file)
    with open(srt_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Hello world" in content
        assert "00:00:00,500 --> 00:00:01,500" in content
    print("✓ Export SRT test passed.")


def test_build_app():
    from app import build_app, get_model_choices
    demo = build_app()
    assert demo is not None
    choices = get_model_choices()
    assert len(choices) >= 5
    print("✓ App initialization and model choices test passed.")


if __name__ == "__main__":
    test_timestamp_formatting()
    test_build_app()
    print("\nAll unit tests passed successfully!")
