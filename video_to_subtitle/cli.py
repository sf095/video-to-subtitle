"""Command-line interface for Video-to-Subtitle transcription."""

import argparse
import os
import sys
from video_to_subtitle.burn_in import burn_subtitles
from video_to_subtitle.engine import transcribe
from video_to_subtitle.formatters import (
    export_all_formats,
    resolve_output_directory,
    to_ass_karaoke,
    to_json,
    to_srt,
    to_vtt,
)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe video to subtitle files with word-level timestamps using faster-whisper."
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
    parser.add_argument(
        "--format",
        type=str,
        default="all",
        choices=["all", "srt", "word_srt", "vtt", "ass", "json"],
        help="Output subtitle format (default: all)",
    )
    parser.add_argument(
        "--burn-in",
        action="store_true",
        help="Also burn ASS karaoke subtitles into a new video file",
    )

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(args.video))[0]
    out_dir = resolve_output_directory(args.video, args.output_dir)

    print(f"🎬 Processing video: {args.video}")
    print(f"⚙️  Model: {args.model} | Device: {args.device} | Format: {args.format}")

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

    os.makedirs(out_dir, exist_ok=True)
    generated_files = []

    if args.format == "all":
        paths = export_all_formats(segments, info, out_dir, base_name)
        generated_files.extend(paths.values())
    elif args.format == "srt":
        p = os.path.join(out_dir, f"{base_name}.srt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(to_srt(segments, word_level=False))
        generated_files.append(p)
    elif args.format == "word_srt":
        p = os.path.join(out_dir, f"{base_name}.word.srt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(to_srt(segments, word_level=True))
        generated_files.append(p)
    elif args.format == "vtt":
        p = os.path.join(out_dir, f"{base_name}.vtt")
        with open(p, "w", encoding="utf-8") as f:
            f.write(to_vtt(segments, word_level=False))
        generated_files.append(p)
    elif args.format == "ass":
        p = os.path.join(out_dir, f"{base_name}.ass")
        with open(p, "w", encoding="utf-8") as f:
            f.write(to_ass_karaoke(segments, title=base_name))
        generated_files.append(p)
    elif args.format == "json":
        p = os.path.join(out_dir, f"{base_name}.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(to_json(segments, info))
        generated_files.append(p)

    print("\n📦 Generated subtitle files:")
    for gf in generated_files:
        print(f"   - {gf}")

    if args.burn_in:
        print("\n🔥 Burning subtitles into video...")
        ass_path = os.path.join(out_dir, f"{base_name}.ass")
        if not os.path.exists(ass_path):
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(to_ass_karaoke(segments, title=base_name))
        burned_video, mode = burn_subtitles(args.video, ass_path)
        print(f"   - Output video ({mode}): {burned_video}")


if __name__ == "__main__":
    main()
