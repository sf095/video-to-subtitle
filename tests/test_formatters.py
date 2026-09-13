import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from video_to_subtitle.engine import SegmentTiming, WordTiming
from video_to_subtitle.formatters import (
    format_timestamp_srt,
    format_timestamp_vtt,
    format_timestamp_ass,
    to_srt,
    to_vtt,
    to_ass_karaoke,
    to_json,
)


def test_timestamp_formatting():
    secs = 3661.234  # 1 hour, 1 minute, 1 second, 234 ms
    assert format_timestamp_srt(secs) == "01:01:01,234", f"SRT failed: {format_timestamp_srt(secs)}"
    assert format_timestamp_vtt(secs) == "01:01:01.234", f"VTT failed: {format_timestamp_vtt(secs)}"
    assert format_timestamp_ass(secs) == "1:01:01.23", f"ASS failed: {format_timestamp_ass(secs)}"
    print("✓ Timestamp formatting tests passed.")


def test_formatters():
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

    # SRT
    srt = to_srt(segments)
    assert "Hello world" in srt
    assert "00:00:00,500 --> 00:00:01,500" in srt
    print("✓ Standard SRT test passed.")

    # Word SRT
    word_srt = to_srt(segments, word_level=True)
    assert "Hello" in word_srt
    assert "world" in word_srt
    assert "00:00:00,500 --> 00:00:00,900" in word_srt
    assert "00:00:01,000 --> 00:00:01,500" in word_srt
    print("✓ Word-level SRT test passed.")

    # VTT
    vtt = to_vtt(segments)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.500 --> 00:00:01.500" in vtt
    print("✓ WebVTT test passed.")

    # ASS Karaoke
    ass = to_ass_karaoke(segments)
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "KaraokeDefault" in ass
    assert r"{\kf40} Hello" in ass or r"{\kf" in ass
    print("✓ ASS Karaoke test passed.")

    # ASS Karaoke Custom Styling
    custom_ass = to_ass_karaoke(
        segments,
        font_name="Helvetica",
        font_size=32,
        primary_color="&H00FFFF00",
        secondary_color="&H00FF00FF",
        bold=False,
    )
    assert "Helvetica" in custom_ass
    assert "32" in custom_ass
    assert "&H00FFFF00" in custom_ass
    assert "&H00FF00FF" in custom_ass
    print("✓ ASS Karaoke Custom Styling test passed.")

    # JSON
    j_str = to_json(segments, {"language": "en", "duration": 2.0})
    data = json.loads(j_str)
    assert data["metadata"]["language"] == "en"
    assert len(data["segments"][0]["words"]) == 2
    assert data["segments"][0]["words"][0]["word"] == " Hello"
    print("✓ JSON test passed.")


def test_build_app():
    from app import build_app, get_model_choices
    demo = build_app()
    assert demo is not None
    choices = get_model_choices()
    assert len(choices) >= 5
    print("✓ App initialization and model choices test passed.")


if __name__ == "__main__":
    test_timestamp_formatting()
    test_formatters()
    test_build_app()
    print("\nAll unit tests passed successfully!")
