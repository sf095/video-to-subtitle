"""Command-line interface for Video-to-Subtitle transcription."""

import argparse
import os
import sys
from video_to_subtitle.engine import transcribe
from video_to_subtitle.formatters import (
    export_srt,
    resolve_output_directory,
)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe video to SubRip (.srt) subtitle files using faster-whisper."
    )
    parser.add_argument(
        "video",
        type=str,
        help="Path to input video or audio file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="medium",
        choices=["tiny", "base", "small", "medium", "large-v3", "large-v2"],
        help="Whisper model size (default: medium)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to run inference on (default: auto)",
    )
    parser.add_argument(
        "--compute-type",
        type=str,
        default="default",
        choices=["default", "int8", "float16"],
        help="Quantization / compute type (default: default)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'en', 'vi') or None for auto-detect",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save subtitle outputs (defaults to input video folder)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(args.video))[0]
    out_dir = resolve_output_directory(args.video, args.output_dir)

    print(f"🎬 Processing video: {args.video}")
    print(f"⚙️  Model: {args.model} | Device: {args.device} | Format: srt")

    def on_progress(p: float, msg: str):
        bar_len = 30
        filled = int(round(bar_len * p))
        bar = "=" * filled + "-" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {p * 100:5.1f}% | {msg}")
        sys.stdout.flush()

    try:
        segments, info = transcribe(
            args.video,
            model_size=args.model,
            device=args.device,
            compute_type=args.compute_type,
            language=args.language,
            progress_callback=on_progress,
        )
        print("\n")
    except Exception as e:
        print(f"\n❌ Transcription failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Transcription complete!")
    print(f"   Detected language: {info.get('language')} ({info.get('language_probability', 1.0) * 100:.1f}%)")
    print(f"   Duration: {info.get('duration')}s | Segments: {len(segments)}")

    srt_path = export_srt(segments, out_dir, base_name)

    print("\n📦 Generated subtitle files:")
    print(f"   - {srt_path}")


if __name__ == "__main__":
    main()
