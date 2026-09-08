"""Burn or embed subtitles directly into video using ffmpeg."""

import os
import subprocess
from typing import Optional, Tuple
from video_to_subtitle.engine import check_ffmpeg


def escape_ffmpeg_filter_path(path: str) -> str:
    """Escape path for ffmpeg filter arguments."""
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:").replace("'", "\\'")
    return p


def supports_filter(filter_name: str) -> bool:
    """Check if the current ffmpeg build supports a specific filter."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-filters"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == filter_name:
                return True
    except Exception:
        pass
    return False


def embed_soft_subtitles(video_path: str, subtitle_path: str, output_path: str) -> str:
    """Embed subtitles as a selectable track in the MP4/MKV container without re-encoding."""
    check_ffmpeg()
    base, ext = os.path.splitext(output_path)
    is_mp4 = ext.lower() in [".mp4", ".m4v", ".mov"]

    # For MP4/MOV use mov_text; for MKV use copy
    sub_codec = "mov_text" if is_mp4 else "copy"

    # If subtitle is .ass and container is MP4, convert to srt first for mov_text compatibility
    temp_srt = None
    sub_to_use = subtitle_path
    if is_mp4 and subtitle_path.endswith(".ass"):
        srt_path = os.path.splitext(subtitle_path)[0] + ".srt"
        if os.path.exists(srt_path):
            sub_to_use = srt_path

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        sub_to_use,
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        sub_codec,
        output_path,
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg subtitle embedding failed: {proc.stderr}")

    return output_path


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_video_path: Optional[str] = None,
    prefer_mode: str = "auto",
) -> Tuple[str, str]:
    """
    Burn subtitles into video using ffmpeg.
    Modes:
        - 'auto': Use hardcode if ffmpeg filter is supported, else fallback to soft embedded.
        - 'softcode': Directly embed subtitle as a standard selectable track (fast & lossless).
        - 'hardcode': Require hardcoded burn-in (raises RuntimeError if ffmpeg lacks libass).

    Returns:
        Tuple of (output_video_path, mode_used: 'hardcoded' or 'embedded')
    """
    check_ffmpeg()
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not os.path.exists(subtitle_path):
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")

    if output_video_path is None:
        base, _ = os.path.splitext(video_path)
        output_video_path = f"{base}_subtitled.mp4"

    if prefer_mode == "softcode":
        embed_soft_subtitles(video_path, subtitle_path, output_video_path)
        return output_video_path, "embedded"

    has_ass = supports_filter("ass")
    has_sub = supports_filter("subtitles")
    ext = os.path.splitext(subtitle_path)[1].lower()

    if (ext == ".ass" and has_ass) or (ext != ".ass" and has_sub):
        escaped_sub = escape_ffmpeg_filter_path(subtitle_path)
        vf_filter = f"ass='{escaped_sub}'" if ext == ".ass" else f"subtitles='{escaped_sub}'"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            vf_filter,
            "-c:a",
            "copy",
            output_video_path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0:
            return output_video_path, "hardcoded"
        if prefer_mode == "hardcode":
            raise RuntimeError(f"ffmpeg subtitle burning failed: {proc.stderr}")

    if prefer_mode == "hardcode":
        raise RuntimeError(
            "Your ffmpeg build does not support the 'ass' or 'subtitles' filter required for pixel hardcoding. "
            "Please install ffmpeg with libass (e.g. `brew install ffmpeg`) or select 'Lossless Soft Track'."
        )

    # Fallback to lossless container embedding (mov_text)
    embed_soft_subtitles(video_path, subtitle_path, output_video_path)
    return output_video_path, "embedded"
