"""Modern Gradio Web UI for Video-to-Subtitle Studio with word-level timestamps."""

import os
import tempfile
import zipfile
from typing import Optional, Tuple
import gradio as gr
import pandas as pd

from video_to_subtitle.burn_in import burn_subtitles
from video_to_subtitle.engine import SegmentTiming, transcribe
from video_to_subtitle.formatters import (
    export_all_formats,
    to_ass_karaoke,
)


def create_zip_bundle(file_paths: dict, zip_dest: str) -> str:
    """Create a zip archive of all generated subtitle files."""
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fmt, path in file_paths.items():
            if os.path.exists(path):
                zipf.write(path, arcname=os.path.basename(path))
    return zip_dest


def run_transcription(
    video_path: Optional[str],
    model_size: str,
    compute_type: str,
    language: Optional[str],
    progress=gr.Progress(track_tqdm=True),
):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("Please upload or provide a valid video file.")

    lang = language.strip() if language and language.strip() else None

    progress(0.1, desc="Extracting audio & loading Whisper...")

    def progress_hook(p: float, msg: str):
        progress(p, desc=msg)

    try:
        segments, info = transcribe(
            video_path,
            model_size=model_size,
            device="auto",
            compute_type=compute_type,
            language=lang,
            progress_callback=progress_hook,
        )
    except Exception as e:
        raise gr.Error(f"Transcription failed: {str(e)}")

    # Prepare export files in a temporary session directory
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = tempfile.mkdtemp(prefix="subtitles_")
    paths = export_all_formats(segments, info, out_dir, base_name)

    # Create zip bundle
    zip_path = os.path.join(out_dir, f"{base_name}_subtitles.zip")
    create_zip_bundle(paths, zip_path)

    # Build word-level transcript dataframe for the UI
    rows = []
    total_words = 0
    for seg in segments:
        if seg.words:
            for w in seg.words:
                total_words += 1
                rows.append(
                    {
                        "Start (s)": f"{w.start:.2f}",
                        "End (s)": f"{w.end:.2f}",
                        "Word": w.word.strip(),
                        "Confidence": f"{w.probability * 100:.1f}%",
                    }
                )
        else:
            rows.append(
                {
                    "Start (s)": f"{seg.start:.2f}",
                    "End (s)": f"{seg.end:.2f}",
                    "Word": seg.text,
                    "Confidence": "N/A",
                }
            )

    df = pd.DataFrame(rows)

    info_md = f"""### 📊 Transcription Summary
- **Detected Language:** `{info.get('language', 'Unknown').upper()}` ({info.get('language_probability', 1.0) * 100:.1f}% confidence)
- **Duration:** `{info.get('duration', 0):.1f}` seconds
- **Total Segments:** `{len(segments)}`
- **Total Words:** `{total_words}`
- **Model Used:** `{model_size}` (Technique: *Word-level Timestamp Alignment*)
"""

    return (
        info_md,
        df,
        zip_path,
        paths.get("srt"),
        paths.get("ass"),
        paths.get("vtt"),
        paths.get("json"),
        paths.get("word_srt"),
        paths,  # Stored in gr.State for burn-in
    )


def run_burn_in(video_path: Optional[str], state_paths: Optional[dict]):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("Please upload a valid video file first.")
    if not state_paths or "ass" not in state_paths or not os.path.exists(state_paths["ass"]):
        raise gr.Error("Please run transcription first to generate subtitles.")

    ass_path = state_paths["ass"]
    out_dir = os.path.dirname(ass_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    burned_output = os.path.join(out_dir, f"{base_name}_with_karaoke_subs.mp4")

    try:
        output_video, _ = burn_subtitles(video_path, ass_path, burned_output)
        return output_video
    except Exception as e:
        raise gr.Error(f"Subtitle burn-in failed: {str(e)}")


def build_app():
    custom_css = """
    .gradio-container { max-width: 1200px !important; margin: auto; }
    .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; background: #e0f2fe; color: #0369a1; font-weight: bold; font-size: 0.85em; }
    """

    with gr.Blocks(title="Video to Subtitle Studio", css=custom_css, theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🎬 Video-to-Subtitle Studio
            ### Transcribe videos to word-accurate subtitle files (**SRT**, **VTT**, **Karaoke ASS**, **JSON**) using **Whisper** with word-level timestamps.
            <span class="badge">⚡ Powered by faster-whisper & CTranslate2</span>
            <span class="badge">🎯 Word-level Timestamp Alignment</span>
            """
        )

        state_paths = gr.State({})

        with gr.Row():
            with gr.Column(scale=1):
                input_video = gr.Video(label="Upload Video", sources=["upload"])

                with gr.Accordion("⚙️ Advanced Whisper Settings", open=True):
                    model_dropdown = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        value="medium",
                        label="Whisper Model Size",
                        info="Default is 'medium'. 'tiny'/'base' are faster; 'large-v3' is highest accuracy.",
                    )
                    compute_dropdown = gr.Dropdown(
                        choices=["default", "int8", "float16"],
                        value="default",
                        label="Compute Type",
                        info="'default' or 'int8' recommended for Mac CPU/MPS.",
                    )
                    language_input = gr.Textbox(
                        label="Language Code (Optional)",
                        placeholder="e.g. en, vi, es, fr (leave blank to auto-detect)",
                    )

                transcribe_btn = gr.Button("🎙️ Transcribe Video", variant="primary", size="lg")
                burn_btn = gr.Button("🔥 Burn Subtitles into Video (Karaoke Style)", variant="secondary")

            with gr.Column(scale=1):
                summary_output = gr.Markdown("### ℹ️ Upload a video and click 'Transcribe Video' to start.")
                
                with gr.Tab("📝 Word-level Transcript"):
                    transcript_table = gr.DataFrame(
                        headers=["Start (s)", "End (s)", "Word", "Confidence"],
                        datatype=["str", "str", "str", "str"],
                        label="Synchronized Word Timestamps",
                        interactive=False,
                    )

                with gr.Tab("📦 Download Subtitles"):
                    zip_download = gr.File(label="Download All Formats (.zip)")
                    with gr.Row():
                        srt_download = gr.File(label="Standard .SRT")
                        ass_download = gr.File(label="Karaoke .ASS")
                    with gr.Row():
                        vtt_download = gr.File(label="WebVTT .VTT")
                        json_download = gr.File(label="Data .JSON")
                        wordsrt_download = gr.File(label="Word-level .SRT")

                with gr.Tab("🎞️ Burnt-in Video Preview"):
                    burned_video_player = gr.Video(label="Video with Burnt-in Karaoke Subtitles")

        # Event Handlers
        transcribe_btn.click(
            fn=run_transcription,
            inputs=[input_video, model_dropdown, compute_dropdown, language_input],
            outputs=[
                summary_output,
                transcript_table,
                zip_download,
                srt_download,
                ass_download,
                vtt_download,
                json_download,
                wordsrt_download,
                state_paths,
            ],
        )

        burn_btn.click(
            fn=run_burn_in,
            inputs=[input_video, state_paths],
            outputs=[burned_video_player],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch()
