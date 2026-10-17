"""Modern Gradio Web UI for Video-to-Subtitle Studio with word-level timestamps."""

import html
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd

from video_to_subtitle.engine import (
    SegmentTiming,
    WordTiming,
    is_model_cached,
    transcribe,
)
from video_to_subtitle.formatters import (
    export_srt,
    resolve_output_directory,
    to_srt,
)
from video_to_subtitle.cache_manager import (
    clear_model_cache,
    clear_temp_cache,
    get_model_cache_stats,
    get_temp_cache_stats,
    register_exit_cleanup,
    register_session_temp_dir,
)

LANGUAGE_CHOICES = [
    ("🌐 Auto-detect Language", "auto"),
    ("🇺🇸 English (en)", "en"),
    ("🇻🇳 Vietnamese (vi)", "vi"),
    ("🇪🇸 Spanish (es)", "es"),
    ("🇫🇷 French (fr)", "fr"),
    ("🇩🇪 German (de)", "de"),
    ("🇨🇳 Chinese (zh)", "zh"),
    ("🇯🇵 Japanese (ja)", "ja"),
    ("🇰🇷 Korean (ko)", "ko"),
    ("🇵🇹 Portuguese (pt)", "pt"),
    ("🇮🇹 Italian (it)", "it"),
    ("🇷🇺 Russian (ru)", "ru"),
    ("🇸🇦 Arabic (ar)", "ar"),
    ("🇮🇳 Hindi (hi)", "hi"),
    ("🇮🇩 Indonesian (id)", "id"),
    ("🇹🇭 Thai (th)", "th"),
    ("✏️ Other / Custom code...", "custom"),
]


def get_model_choices() -> List[Tuple[str, str]]:
    """Build model dropdown choices with local cache indicators."""
    models_meta = [
        ("tiny", "tiny (Fastest · ~75MB)"),
        ("base", "base (Fast · ~145MB)"),
        ("small", "small (Balanced · ~480MB)"),
        ("medium", "medium (High Accuracy · ~1.5GB)"),
        ("large-v3", "large-v3 (Maximum Accuracy · ~3GB)"),
    ]
    choices = []
    for model_id, label in models_meta:
        if is_model_cached(model_id):
            display_label = f"{label} · ⚡ Cached"
        else:
            display_label = label
        choices.append((display_label, model_id))
    return choices


def render_storage_info() -> str:
    """Render markdown summary of current cache & storage usage."""
    temp_stats = get_temp_cache_stats()
    model_stats = get_model_cache_stats()

    models_list = []
    if model_stats["models"]:
        for m in model_stats["models"]:
            models_list.append(f"- **`{m['model_size']}`**: {m['formatted_size']}")
        models_str = "\n".join(models_list)
    else:
        models_str = "- *No models downloaded locally.*"

    return f"""### 💾 Local Storage & Cache Usage
- **📁 Temporary Files**: `{temp_stats['formatted_size']}` ({temp_stats['file_count']} files in upload & export cache)
- **🧠 Downloaded Whisper Models**: `{model_stats['formatted_total']}`
{models_str}
"""


def get_downloaded_model_choices() -> List[Tuple[str, str]]:
    """Return dropdown choices for downloaded Whisper models available for deletion."""
    model_stats = get_model_cache_stats()
    if not model_stats["models"]:
        return [("No models downloaded", "none")]
    choices = [("All Downloaded Models", "all")]
    for m in model_stats["models"]:
        choices.append((f"{m['model_size']} ({m['formatted_size']})", m["model_size"]))
    return choices


def render_empty_state() -> str:
    """Render a clean onboarding empty state."""
    return """
    <div class="empty-state-card">
        <div style="font-size: 2rem; margin-bottom: 0.35rem;">🎙️</div>
        <h3 style="margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--body-text-color, #0f172a);">
            Ready to Transcribe
        </h3>
        <p style="margin: 0.35rem 0 1.25rem 0; font-size: 0.88rem; color: var(--body-text-color-subdued, #64748b); max-width: 580px; margin-left: auto; margin-right: auto;">
            Upload any video or audio file to transcribe with word-level precision, inspect timestamps, and download SubRip (.srt) subtitles.
        </p>
        <div class="step-card-grid">
            <div class="step-card">
                <span class="step-number">1</span>
                <div style="font-weight: 600; font-size: 0.85rem; color: var(--body-text-color, #0f172a);">Upload Media</div>
                <div style="font-size: 0.76rem; color: var(--body-text-color-subdued, #64748b); margin-top: 0.2rem;">
                    Drag and drop your video or audio file to begin.
                </div>
            </div>
            <div class="step-card">
                <span class="step-number">2</span>
                <div style="font-weight: 600; font-size: 0.85rem; color: var(--body-text-color, #0f172a);">Configure & Run</div>
                <div style="font-size: 0.76rem; color: var(--body-text-color-subdued, #64748b); margin-top: 0.2rem;">
                    Select model size and target language (or let Whisper auto-detect).
                </div>
            </div>
            <div class="step-card">
                <span class="step-number">3</span>
                <div style="font-weight: 600; font-size: 0.85rem; color: var(--body-text-color, #0f172a);">Export Subtitles</div>
                <div style="font-size: 0.76rem; color: var(--body-text-color-subdued, #64748b); margin-top: 0.2rem;">
                    Download formatted SubRip (.srt) subtitles or inspect code directly.
                </div>
            </div>
        </div>
    </div>
    """


def render_metrics_dashboard(
    info: dict,
    segments_count: int,
    words_count: int,
    out_dir: Optional[str] = None,
) -> str:
    """Render high-contrast metric chips summarizing the transcription and output folder."""
    lang = html.escape(str(info.get("language", "Unknown")).upper())
    lang_prob = info.get("language_probability", 1.0) * 100
    duration = info.get("duration", 0.0)
    wpm = int(round((words_count / (duration / 60)))) if duration > 0 else 0
    model = html.escape(str(info.get("model_size", "whisper")))

    saved_banner = ""
    if out_dir:
        escaped_dir = html.escape(str(out_dir))
        saved_banner = f"""
        <div style="padding: 0.6rem 0.9rem; margin-bottom: 0.85rem; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; font-size: 0.85rem; color: #065f46; display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">📁</span>
            <div><b>Subtitles saved to:</b> <code style="background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px;">{escaped_dir}</code></div>
        </div>
        """

    return f"""
    {saved_banner}
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">Language</div>
            <div class="metric-value">{lang}</div>
            <div class="metric-subtext">{lang_prob:.1f}% confidence</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Duration</div>
            <div class="metric-value">{duration:.1f}s</div>
            <div class="metric-subtext">{duration / 60:.2f} min</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Words</div>
            <div class="metric-value">{words_count}</div>
            <div class="metric-subtext">timestamped</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Speaking Rate</div>
            <div class="metric-value">{wpm} <span style="font-size: 0.75rem; font-weight: normal;">WPM</span></div>
            <div class="metric-subtext">conversational cadence</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Segments</div>
            <div class="metric-value">{segments_count}</div>
            <div class="metric-subtext">Model: {model}</div>
        </div>
    </div>
    """


def run_transcription(
    video_path: Optional[str] = None,
    custom_output_dir: Optional[str] = None,
    model_size: str = "medium",
    compute_type: str = "default",
    language_choice: str = "auto",
    custom_language: str = "",
    vad_filter: bool = True,
    initial_prompt: Optional[str] = None,
    progress=gr.Progress(track_tqdm=True),
    local_video_path: Optional[str] = None,
):
    effective_video = None
    if video_path and os.path.exists(video_path):
        effective_video = video_path
    elif local_video_path and str(local_video_path).strip():
        candidate = os.path.abspath(str(local_video_path).strip())
        if not os.path.exists(candidate):
            raise gr.Error(f"Local video file not found: {candidate}")
        effective_video = candidate

    if not effective_video:
        raise gr.Error("Please upload a media file.")

    # Determine language parameter
    if language_choice == "custom":
        lang = custom_language.strip() if custom_language and custom_language.strip() else None
    elif language_choice == "auto":
        lang = None
    else:
        lang = language_choice.strip()

    prompt_text = initial_prompt.strip() if initial_prompt and initial_prompt.strip() else None

    progress(0.08, desc="Extracting audio & loading Whisper...")

    def progress_hook(p: float, msg: str):
        progress(p, desc=msg)

    try:
        segments, info = transcribe(
            effective_video,
            model_size=model_size,
            device="auto",
            compute_type=compute_type,
            language=lang,
            vad_filter=vad_filter,
            initial_prompt=prompt_text,
            progress_callback=progress_hook,
        )
    except Exception as e:
        raise gr.Error(f"Transcription failed: {str(e)}")

    # Prepare export file
    # If custom_output_dir is explicitly specified, write to it; otherwise stage in an isolated
    # temporary directory strictly for in-browser downloads (never auto-writing to user's disk).
    base_name = os.path.splitext(os.path.basename(effective_video))[0]
    if custom_output_dir and str(custom_output_dir).strip():
        out_dir = os.path.abspath(str(custom_output_dir).strip())
        os.makedirs(out_dir, exist_ok=True)
        is_custom_save = True
    else:
        out_dir = tempfile.mkdtemp(prefix="subtitles_export_")
        register_session_temp_dir(out_dir)
        is_custom_save = False

    srt_path = export_srt(segments, out_dir, base_name)

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Build segment dataframe and full reading text
    segment_rows = []
    full_paragraphs = []
    for seg in segments:
        duration = seg.end - seg.start
        segment_rows.append(
            {
                "#": seg.id + 1,
                "Start": f"{seg.start:.2f}s",
                "End": f"{seg.end:.2f}s",
                "Duration": f"{duration:.2f}s",
                "Dialogue": seg.text,
            }
        )
        if seg.text.strip():
            full_paragraphs.append(seg.text.strip())

    segment_df = pd.DataFrame(segment_rows)
    full_transcript_text = " ".join(full_paragraphs)

    # Build word-level transcript dataframe
    word_rows = []
    total_words = 0
    for seg in segments:
        if seg.words:
            for w in seg.words:
                total_words += 1
                word_rows.append(
                    {
                        "Start (s)": f"{w.start:.2f}",
                        "End (s)": f"{w.end:.2f}",
                        "Duration (s)": f"{w.end - w.start:.2f}",
                        "Word": w.word.strip(),
                        "Confidence": f"{w.probability * 100:.1f}%",
                    }
                )
        else:
            total_words += 1
            word_rows.append(
                {
                    "Start (s)": f"{seg.start:.2f}",
                    "End (s)": f"{seg.end:.2f}",
                    "Duration (s)": f"{seg.end - seg.start:.2f}",
                    "Word": seg.text,
                    "Confidence": "N/A",
                }
            )

    word_df = pd.DataFrame(word_rows)
    metrics_html = render_metrics_dashboard(
        info, len(segments), total_words, out_dir=(out_dir if is_custom_save else None)
    )

    state_data = {
        "video_path": effective_video,
        "segments": [seg.to_dict() for seg in segments],
        "info": info,
        "srt_path": srt_path,
        "out_dir": out_dir,
        "is_custom_save": is_custom_save,
        "base_name": base_name,
    }

    return (
        metrics_html,
        full_transcript_text,
        segment_df,
        word_df,
        gr.DownloadButton(value=srt_path, interactive=True),
        gr.Code(value=srt_content, language="markdown"),
        state_data,
    )


def clear_all_inputs():
    """Reset all state and outputs to initial empty state."""
    return (
        None,  # input_video
        "",  # output_dir_input
        render_empty_state(),  # summary_output
        "",  # full_transcript_text
        pd.DataFrame(columns=["#", "Start", "End", "Duration", "Dialogue"]),  # segment_df
        pd.DataFrame(
            columns=["Start (s)", "End (s)", "Duration (s)", "Word", "Confidence"]
        ),  # word_df
        gr.DownloadButton(value=None, interactive=False),  # srt_download
        gr.Code(value="", language="markdown"),  # code_viewer
        {},  # state_data
    )


def build_app():
    custom_css = """
    /* Main container and typography */
    .gradio-container {
        max-width: 1320px !important;
        margin: 0 auto !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }

    /* Header styling */
    .header-wrapper {
        padding: 1.25rem 0 1rem 0;
        border-bottom: 1px solid var(--border-color-primary, #e2e8f0);
        margin-bottom: 1.25rem;
    }

    .header-title-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.75rem;
    }

    .header-title {
        font-size: 1.65rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--body-text-color, #0f172a);
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .header-subtitle {
        font-size: 0.92rem;
        color: var(--body-text-color-subdued, #64748b);
        margin-top: 0.35rem;
        margin-bottom: 0;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
    }

    .feature-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        font-size: 0.78rem;
        font-weight: 500;
        border-radius: 6px;
        background: var(--background-fill-secondary, #f1f5f9);
        border: 1px solid var(--border-color-primary, #cbd5e1);
        color: var(--body-text-color, #334155);
    }

    /* Metric cards dashboard */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 0.75rem;
        margin: 0.5rem 0 1rem 0;
    }

    .metric-card {
        background: var(--background-fill-secondary, #f8fafc);
        border: 1px solid var(--border-color-primary, #e2e8f0);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        text-align: left;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--body-text-color-subdued, #64748b);
        margin-bottom: 0.2rem;
    }

    .metric-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--body-text-color, #0f172a);
        line-height: 1.2;
    }

    .metric-subtext {
        font-size: 0.72rem;
        color: var(--body-text-color-subdued, #94a3b8);
        margin-top: 0.15rem;
    }

    /* Empty onboarding state */
    .empty-state-card {
        border: 1px dashed var(--border-color-primary, #cbd5e1);
        border-radius: 8px;
        padding: 1.75rem 1.25rem;
        text-align: center;
        background: var(--background-fill-secondary, #fafafa);
        margin-bottom: 1rem;
    }

    .step-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 0.85rem;
        margin-top: 1rem;
        text-align: left;
    }

    .step-card {
        background: var(--background-fill-primary, #ffffff);
        border: 1px solid var(--border-color-primary, #e2e8f0);
        border-radius: 6px;
        padding: 0.75rem;
    }

    .step-number {
        display: inline-block;
        width: 20px;
        height: 20px;
        line-height: 20px;
        border-radius: 50%;
        background: #4338ca;
        color: white;
        font-size: 0.72rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.35rem;
    }

    /* Action bar */
    .action-bar {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    """

    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.indigo,
        neutral_hue=gr.themes.colors.slate,
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    )

    with gr.Blocks(title="Video-to-Subtitle Studio") as demo:
        demo.launch_theme = theme
        demo.launch_css = custom_css
        # Header Section
        gr.HTML(
            """
            <div class="header-wrapper">
                <div class="header-title-row">
                    <div>
                        <h1 class="header-title">🎬 Video-to-Subtitle Studio</h1>
                        <p class="header-subtitle">
                            High-precision video transcription with word-level synchronized timestamps powered by Whisper.
                        </p>
                    </div>
                    <div class="pill-row">
                        <span class="feature-pill">🎯 Word-level Alignment</span>
                        <span class="feature-pill">🔒 100% Local & Private</span>
                        <span class="feature-pill">📝 SubRip (.SRT) Export</span>
                    </div>
                </div>
            </div>
            """
        )

        state_data = gr.State({})

        with gr.Row(equal_height=False):
            # Left Column: Input & Configuration
            with gr.Column(scale=5):
                input_video = gr.Video(
                    label="Media Input (Upload Video or Audio)",
                    sources=["upload"],
                )

                clear_btn = gr.Button(
                    "🗑️ Clear All",
                    variant="ghost",
                    size="sm",
                )

                # Transcription Controls Group
                with gr.Group():
                    model_choices = get_model_choices()
                    default_model = (
                        "tiny" if is_model_cached("tiny") else "medium"
                    )
                    model_dropdown = gr.Dropdown(
                        choices=model_choices,
                        value=default_model,
                        label="Whisper Model",
                        info="⚡ 'Cached' models run instantly without downloading.",
                    )

                    with gr.Row():
                        language_dropdown = gr.Dropdown(
                            choices=LANGUAGE_CHOICES,
                            value="auto",
                            label="Spoken Language",
                            info="Auto-detect or pick source language.",
                            scale=2,
                        )
                        custom_language_input = gr.Textbox(
                            label="Custom Code",
                            placeholder="e.g. ja, it",
                            visible=False,
                            scale=1,
                        )

                    with gr.Accordion("⚙️ Advanced Audio & Model Settings", open=False):
                        compute_dropdown = gr.Dropdown(
                            choices=[
                                ("default (Full Precision Float32)", "default"),
                                ("int8 (Fast & 50% Lower RAM)", "int8"),
                                ("float16 (GPU Optimized)", "float16"),
                            ],
                            value="default",
                            label="Compute Type / Quantization",
                            info="'int8' is ideal for reducing memory on laptops and CPUs.",
                        )
                        vad_checkbox = gr.Checkbox(
                            value=True,
                            label="Enable Voice Activity Detection (Silero VAD)",
                            info="Suppresses non-speech background noise & silence hallucinations.",
                        )
                        initial_prompt_input = gr.Textbox(
                            label="Vocabulary & Terminology Hint (Initial Prompt)",
                            placeholder="e.g. AcmeCorp, GraphQL, Dr. Nguyen, TypeScript",
                            info="Guide Whisper on domain-specific proper nouns, jargon, or acronyms.",
                        )
                        output_dir_input = gr.Textbox(
                            label="Save to Folder (Optional)",
                            placeholder="Leave blank to only use in-browser downloads",
                            info="Leave blank to prevent saving files to disk (download via button below).",
                            lines=1,
                        )

                transcribe_btn = gr.Button(
                    "✨ Transcribe Media",
                    variant="primary",
                    size="lg",
                )

                # Storage & Cache Management Accordion
                with gr.Accordion("🧹 Storage & Cache Management", open=False):
                    storage_info_md = gr.Markdown(value=render_storage_info())
                    with gr.Row():
                        clear_temp_btn = gr.Button("🗑️ Clear Temp Files", variant="secondary", size="sm")
                        refresh_storage_btn = gr.Button("🔄 Refresh Stats", variant="ghost", size="sm")
                    with gr.Row():
                        downloaded_choices = get_downloaded_model_choices()
                        model_delete_dropdown = gr.Dropdown(
                            choices=downloaded_choices,
                            value=downloaded_choices[0][1] if downloaded_choices else "none",
                            label="Model Weights to Delete",
                            scale=2,
                        )
                        delete_model_btn = gr.Button("⚠️ Delete Model", variant="stop", size="sm", scale=1)
                    cache_status_md = gr.Markdown(value="")

            # Right Column: Results, Inspector & Export
            with gr.Column(scale=7):
                summary_output = gr.HTML(value=render_empty_state())

                with gr.Tabs() as tabs:
                    with gr.Tab("📄 Full Transcript & Segments", id="tab_transcript"):
                        with gr.Group():
                            full_transcript_box = gr.Textbox(
                                label="Continuous Transcript",
                                placeholder="Transcription dialogue will appear here once processed...",
                                lines=5,
                                max_lines=12,
                                buttons=["copy"],
                                interactive=False,
                            )
                        segment_table = gr.DataFrame(
                            headers=["#", "Start", "End", "Duration", "Dialogue"],
                            datatype=["number", "str", "str", "str", "str"],
                            label="Segment-by-Segment Timeline",
                            interactive=False,
                            wrap=True,
                        )

                    with gr.Tab("🎯 Word-Level Timestamps", id="tab_words"):
                        word_table = gr.DataFrame(
                            headers=[
                                "Start (s)",
                                "End (s)",
                                "Duration (s)",
                                "Word",
                                "Confidence",
                            ],
                            datatype=["str", "str", "str", "str", "str"],
                            label="Synchronized Word Timestamps",
                            interactive=False,
                        )

                    with gr.Tab("💾 Subtitle Export & Inspector", id="tab_export"):
                        with gr.Group():
                            gr.Markdown("### 📦 Subtitle Download")
                            srt_download = gr.DownloadButton(
                                "📥 Download Subtitle (.SRT)",
                                variant="primary",
                                size="lg",
                                interactive=False,
                            )

                        gr.Markdown("---")
                        gr.Markdown("### 🔍 Live Subtitle Code Inspector")
                        code_viewer = gr.Code(
                            value="// Run transcription to inspect generated subtitle code here.",
                            language="markdown",
                            lines=16,
                            show_line_numbers=True,
                            buttons=["copy"],
                            interactive=False,
                        )

        # Event: Toggle custom language textbox
        def on_language_change(lang_val):
            return gr.Textbox(visible=(lang_val == "custom"))

        language_dropdown.change(
            fn=on_language_change,
            inputs=[language_dropdown],
            outputs=[custom_language_input],
        )

        # Event: Clear all inputs & outputs
        clear_btn.click(
            fn=clear_all_inputs,
            inputs=[],
            outputs=[
                input_video,
                output_dir_input,
                summary_output,
                full_transcript_box,
                segment_table,
                word_table,
                srt_download,
                code_viewer,
                state_data,
            ],
        )

        # Event: Run transcription
        transcribe_btn.click(
            fn=run_transcription,
            inputs=[
                input_video,
                output_dir_input,
                model_dropdown,
                compute_dropdown,
                language_dropdown,
                custom_language_input,
                vad_checkbox,
                initial_prompt_input,
            ],
            outputs=[
                summary_output,
                full_transcript_box,
                segment_table,
                word_table,
                srt_download,
                code_viewer,
                state_data,
            ],
        )

        # Event: Storage & Cache Handlers
        def on_clear_temp():
            result = clear_temp_cache()
            new_storage_info = render_storage_info()
            status_msg = f"✅ Cleared {result['formatted_freed']} of temporary files ({result['files_removed']} files removed)."
            return new_storage_info, status_msg

        def on_delete_model(selected_model):
            if not selected_model or selected_model == "none":
                return render_storage_info(), gr.Dropdown(), gr.Dropdown(), "⚠️ No downloaded model selected to delete."
            result = clear_model_cache(selected_model)
            new_storage_info = render_storage_info()
            new_delete_choices = get_downloaded_model_choices()
            new_delete_val = new_delete_choices[0][1] if new_delete_choices else "none"
            new_model_choices = get_model_choices()
            status_msg = f"✅ Deleted Whisper model weights: {', '.join(result['removed_models'])} ({result['formatted_freed']} freed)."
            return (
                new_storage_info,
                gr.Dropdown(choices=new_delete_choices, value=new_delete_val),
                gr.Dropdown(choices=new_model_choices),
                status_msg,
            )

        def on_refresh_storage():
            new_storage_info = render_storage_info()
            new_delete_choices = get_downloaded_model_choices()
            new_delete_val = new_delete_choices[0][1] if new_delete_choices else "none"
            new_model_choices = get_model_choices()
            return (
                new_storage_info,
                gr.Dropdown(choices=new_delete_choices, value=new_delete_val),
                gr.Dropdown(choices=new_model_choices),
                "🔄 Storage statistics refreshed.",
            )

        clear_temp_btn.click(
            fn=on_clear_temp,
            outputs=[storage_info_md, cache_status_md],
        )

        delete_model_btn.click(
            fn=on_delete_model,
            inputs=[model_delete_dropdown],
            outputs=[storage_info_md, model_delete_dropdown, model_dropdown, cache_status_md],
        )

        refresh_storage_btn.click(
            fn=on_refresh_storage,
            outputs=[storage_info_md, model_delete_dropdown, model_dropdown, cache_status_md],
        )

    register_exit_cleanup()
    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(
        theme=getattr(app, "launch_theme", None),
        css=getattr(app, "launch_css", None),
    )
