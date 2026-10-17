"""Formatters for converting word-level Whisper segments into SubRip (.srt) subtitles."""

import os
from typing import List, Optional
from video_to_subtitle.engine import SegmentTiming
from video_to_subtitle.platform_utils import is_gradio_temp_path


def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def to_srt(segments: List[SegmentTiming], word_level: bool = False) -> str:
    """
    Generate SubRip (.srt) subtitle string.
    If word_level=True, emits each word as a distinct subtitle entry.
    """
    lines = []
    counter = 1

    if word_level:
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    clean_word = w.word.strip()
                    if not clean_word:
                        continue
                    start_str = format_timestamp_srt(w.start)
                    end_str = format_timestamp_srt(w.end)
                    lines.append(f"{counter}\n{start_str} --> {end_str}\n{clean_word}\n")
                    counter += 1
            else:
                start_str = format_timestamp_srt(seg.start)
                end_str = format_timestamp_srt(seg.end)
                lines.append(f"{counter}\n{start_str} --> {end_str}\n{seg.text}\n")
                counter += 1
    else:
        for seg in segments:
            clean_text = seg.text.strip()
            if not clean_text:
                continue
            start_str = format_timestamp_srt(seg.start)
            end_str = format_timestamp_srt(seg.end)
            lines.append(f"{counter}\n{start_str} --> {end_str}\n{clean_text}\n")
            counter += 1

    return "\n".join(lines).strip() + "\n"


def export_srt(
    segments: List[SegmentTiming],
    output_dir: str,
    base_name: str,
) -> str:
    """Export standard SubRip (.srt) subtitle file and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(to_srt(segments, word_level=False))
    return srt_path


def resolve_output_directory(
    video_path: str,
    custom_output_dir: Optional[str] = None,
    fallback_dir: Optional[str] = None,
) -> str:
    """
    Resolve the destination directory for subtitle files.
    - If custom_output_dir is provided: use it.
    - If video_path is in Gradio temporary cache: fallback to fallback_dir or ~/Downloads.
    - Otherwise: defaults to the same folder containing the input video.
    """
    if custom_output_dir and str(custom_output_dir).strip():
        out_dir = os.path.abspath(str(custom_output_dir).strip())
    elif is_gradio_temp_path(video_path):
        fallback = fallback_dir or os.path.expanduser("~/Downloads")
        out_dir = os.path.abspath(fallback)
    else:
        out_dir = os.path.dirname(os.path.abspath(video_path))
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
