"""Modern Gradio Web UI for Video-to-Subtitle Studio with word-level timestamps."""

import html
import os
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd

from video_to_subtitle.burn_in import burn_subtitles, supports_filter
from video_to_subtitle.engine import (
    SegmentTiming,
    WordTiming,
    is_model_cached,
    transcribe,
)
from video_to_subtitle.formatters import (
    export_all_formats,
    to_ass_karaoke,
    to_json,
    to_srt,
    to_vtt,
)

# Preset color & typography schemes for ASS Karaoke subtitles
STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "Classic Gold": {
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000E6FF",
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "bold": True,
        "description": "Crisp white text with vibrant gold karaoke highlight",
    },
    "Cyber Neon": {
        "primary_color": "&H00FFFF00",
        "secondary_color": "&H00FF00FF",
        "outline_color": "&H00101010",
        "back_color": "&H80000000",
        "bold": True,
        "description": "Electric cyan text with vivid magenta highlight",
    },
    "Modern Emerald": {
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H004ADE80",
        "outline_color": "&H001E293B",
        "back_color": "&H80000000",
        "bold": True,
        "description": "Pure white text with fresh emerald green highlight",
    },
    "Warm Sunset": {
        "primary_color": "&H00F8FAFC",
        "secondary_color": "&H002080FF",
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "bold": True,
        "description": "Soft ivory text with warm orange karaoke highlight",
    },
    "Minimalist Clean": {
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00D4D4D8",
        "outline_color": "&H00000000",
        "back_color": "&H60000000",
        "bold": False,
        "description": "Clean white subtitle with subtle darkening box",
    },
}

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


def create_zip_bundle(file_paths: dict, zip_dest: str) -> str:
    """Create a zip archive containing all generated subtitle formats."""
    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        for _, path in file_paths.items():
            if os.path.exists(path):
                zipf.write(path, arcname=os.path.basename(path))
    return zip_dest


def render_empty_state() -> str:
    """Render a clean onboarding empty state."""
    return """
    <div class="empty-state-card">
        <div style="font-size: 2rem; margin-bottom: 0.35rem;">🎙️</div>
        <h3 style="margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--body-text-color, #0f172a);">
            Ready to Transcribe
        </h3>
        <p style="margin: 0.35rem 0 1.25rem 0; font-size: 0.88rem; color: var(--body-text-color-subdued, #64748b); max-width: 580px; margin-left: auto; margin-right: auto;">
            Upload any video or audio file to transcribe with word-level precision, inspect timestamps, download formatted subtitles, or burn karaoke captions.
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
                <div style="font-weight: 600; font-size: 0.85rem; color: var(--body-text-color, #0f172a);">Export & Burn</div>
                <div style="font-size: 0.76rem; color: var(--body-text-color-subdued, #64748b); margin-top: 0.2rem;">
                    Export SRT, VTT, ASS, or burn animated karaoke captions directly.
                </div>
            </div>
        </div>
    </div>
    """


def render_metrics_dashboard(info: dict, segments_count: int, words_count: int) -> str:
    """Render high-contrast metric chips summarizing the transcription."""
    lang = html.escape(str(info.get("language", "Unknown")).upper())
    lang_prob = info.get("language_probability", 1.0) * 100
    duration = info.get("duration", 0.0)
    wpm = int(round((words_count / (duration / 60)))) if duration > 0 else 0
    model = html.escape(str(info.get("model_size", "whisper")))

    return f"""
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
    video_path: Optional[str],
    model_size: str,
    compute_type: str,
    language_choice: str,
    custom_language: str,
    vad_filter: bool,
    initial_prompt: Optional[str],
    progress=gr.Progress(track_tqdm=True),
):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("Please upload or provide a valid video or audio file.")

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
            video_path,
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

    # Prepare export files in a temporary session directory
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_dir = tempfile.mkdtemp(prefix="subtitles_")
    paths = export_all_formats(segments, info, out_dir, base_name)

    # Create zip bundle
    zip_path = os.path.join(out_dir, f"{base_name}_subtitles.zip")
    create_zip_bundle(paths, zip_path)

    # Read formatted content for the live subtitle inspector
    raw_texts = {}
    format_map = {
        "Standard SubRip (.srt)": (paths.get("srt"), "markdown"),
        "WebVTT (.vtt)": (paths.get("vtt"), "markdown"),
        "Karaoke SubStation (.ass)": (paths.get("ass"), "markdown"),
        "Data (.json)": (paths.get("json"), "json"),
        "Word-level SubRip (.word.srt)": (paths.get("word_srt"), "markdown"),
    }
    for fmt_name, (fpath, lang_type) in format_map.items():
        if fpath and os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                raw_texts[fmt_name] = (f.read(), lang_type)
        else:
            raw_texts[fmt_name] = ("", lang_type)

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
    metrics_html = render_metrics_dashboard(info, len(segments), total_words)

    # Default code inspector view: Standard SRT
    default_code, default_lang = raw_texts.get(
        "Standard SubRip (.srt)", ("", "markdown")
    )

    state_data = {
        "video_path": video_path,
        "segments": [seg.to_dict() for seg in segments],
        "info": info,
        "paths": paths,
        "zip_path": zip_path,
        "raw_texts": raw_texts,
        "out_dir": out_dir,
        "base_name": base_name,
    }

    burn_ready_status = (
        "💡 **Subtitles ready!** Select your desired karaoke style and font size below, "
        "then click **Generate Subtitled Video**."
    )

    return (
        metrics_html,
        full_transcript_text,
        segment_df,
        word_df,
        gr.DownloadButton(value=zip_path, interactive=True),
        gr.DownloadButton(value=paths.get("srt"), interactive=True),
        gr.DownloadButton(value=paths.get("vtt"), interactive=True),
        gr.DownloadButton(value=paths.get("ass"), interactive=True),
        gr.DownloadButton(value=paths.get("json"), interactive=True),
        gr.DownloadButton(value=paths.get("word_srt"), interactive=True),
        gr.Code(value=default_code, language=default_lang),
        burn_ready_status,
        state_data,
    )


def update_code_inspector(selected_format: str, state_data: Optional[dict]):
    """Dynamically swap the code inspector view based on format selection."""
    if not state_data or "raw_texts" not in state_data:
        return gr.Code(value="No subtitles generated yet.", language="markdown")
    raw_texts = state_data["raw_texts"]
    if selected_format in raw_texts:
        content, lang_type = raw_texts[selected_format]
        return gr.Code(value=content, language=lang_type)
    return gr.Code(value="", language="markdown")


def run_burn_in(
    video_path: Optional[str],
    state_data: Optional[dict],
    style_preset: str,
    font_size: int,
    font_family: str,
    burn_mode: str,
    progress=gr.Progress(track_tqdm=True),
):
    if not video_path or not os.path.exists(video_path):
        raise gr.Error("Please upload or provide a valid video file first.")
    if not state_data or "segments" not in state_data:
        raise gr.Error("Please run transcription first before burning subtitles.")

    progress(0.2, desc="Preparing custom subtitle style...")

    # Reconstruct SegmentTiming objects
    segments_data = state_data["segments"]
    segments: List[SegmentTiming] = []
    for s in segments_data:
        words = [WordTiming(**w) for w in s.get("words", [])]
        segments.append(
            SegmentTiming(
                id=s["id"],
                start=s["start"],
                end=s["end"],
                text=s["text"],
                words=words,
            )
        )

    # Retrieve style parameters
    preset = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["Classic Gold"])
    out_dir = state_data.get("out_dir") or tempfile.mkdtemp(prefix="subtitles_")
    base_name = state_data.get("base_name", "output")

    # Generate custom ASS file
    custom_ass_content = to_ass_karaoke(
        segments=segments,
        title=base_name,
        font_name=font_family,
        font_size=int(font_size),
        primary_color=preset["primary_color"],
        secondary_color=preset["secondary_color"],
        outline_color=preset["outline_color"],
        back_color=preset["back_color"],
        bold=preset["bold"],
    )

    custom_ass_path = os.path.join(
        out_dir, f"{base_name}_{style_preset.lower().replace(' ', '_')}.ass"
    )
    with open(custom_ass_path, "w", encoding="utf-8") as f:
        f.write(custom_ass_content)

    burned_output = os.path.join(
        out_dir, f"{base_name}_subtitled.mp4"
    )

    # Translate burn mode selection
    if burn_mode.startswith("Hardcode"):
        prefer_mode = "hardcode"
    elif burn_mode.startswith("Lossless"):
        prefer_mode = "softcode"
    else:
        prefer_mode = "auto"

    progress(0.5, desc="Rendering subtitles into video with ffmpeg...")

    try:
        output_video, mode_used = burn_subtitles(
            video_path,
            custom_ass_path,
            burned_output,
            prefer_mode=prefer_mode,
        )
    except Exception as e:
        raise gr.Error(f"Subtitle burn-in failed: {str(e)}")

    progress(1.0, desc="Video rendering complete!")

    if mode_used == "hardcode":
        status_msg = (
            "✅ **Subtitles hardcoded into video frames!** "
            "Captions are permanently rendered onto the video pixels and will display on any player or social media platform."
        )
    else:
        status_msg = (
            "ℹ️ **Subtitles embedded as a lossless soft track (mov_text)!** "
            "Zero video re-encoding loss. To toggle or view subtitles, enable the subtitle track in your media player (e.g. VLC, QuickTime). "
            "*(For pixel hardcoding, install ffmpeg with libass: `brew install ffmpeg`)*."
        )

    return output_video, status_msg



def clear_all_inputs():
    """Reset all state and outputs to initial empty state."""
    return (
        None,  # input_video
        render_empty_state(),  # summary_output
        "",  # full_transcript_text
        pd.DataFrame(columns=["#", "Start", "End", "Duration", "Dialogue"]),  # segment_df
        pd.DataFrame(
            columns=["Start (s)", "End (s)", "Duration (s)", "Word", "Confidence"]
        ),  # word_df
        gr.DownloadButton(value=None, interactive=False),  # zip_download
        gr.DownloadButton(value=None, interactive=False),  # srt_download
        gr.DownloadButton(value=None, interactive=False),  # vtt_download
        gr.DownloadButton(value=None, interactive=False),  # ass_download
        gr.DownloadButton(value=None, interactive=False),  # json_download
        gr.DownloadButton(value=None, interactive=False),  # wordsrt_download
        gr.Code(value="", language="markdown"),  # code_viewer
        None,  # burned_video_player
        "",  # burn_status_msg
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

    /* Download center header */
    .download-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
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
                        <span class="feature-pill">📦 Multi-format (SRT, VTT, ASS, JSON)</span>
                        <span class="feature-pill">🔥 Karaoke Burn-in</span>
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
                    label="Media Input (Video or Audio)",
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

                transcribe_btn = gr.Button(
                    "✨ Transcribe Media",
                    variant="primary",
                    size="lg",
                )

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
                            gr.Markdown("### 📦 Subtitle Download Center")
                            zip_download = gr.DownloadButton(
                                "📦 Download Subtitle Bundle (.ZIP)",
                                variant="primary",
                                size="lg",
                                interactive=False,
                            )
                            with gr.Row():
                                srt_download = gr.DownloadButton(
                                    "📝 SRT", size="sm", interactive=False
                                )
                                vtt_download = gr.DownloadButton(
                                    "🌐 WebVTT", size="sm", interactive=False
                                )
                                ass_download = gr.DownloadButton(
                                    "🎵 Karaoke ASS", size="sm", interactive=False
                                )
                                json_download = gr.DownloadButton(
                                    "📊 JSON Data", size="sm", interactive=False
                                )
                                wordsrt_download = gr.DownloadButton(
                                    "⚡ Word SRT", size="sm", interactive=False
                                )

                        gr.Markdown("---")
                        gr.Markdown("### 🔍 Live Subtitle Code Inspector")
                        format_radio = gr.Radio(
                            choices=[
                                "Standard SubRip (.srt)",
                                "WebVTT (.vtt)",
                                "Karaoke SubStation (.ass)",
                                "Data (.json)",
                                "Word-level SubRip (.word.srt)",
                            ],
                            value="Standard SubRip (.srt)",
                            label="Preview Subtitle Format",
                        )
                        code_viewer = gr.Code(
                            value="// Run transcription to inspect generated subtitle code here.",
                            language="markdown",
                            lines=14,
                            show_line_numbers=True,
                            buttons=["copy"],
                            interactive=False,
                        )

                    with gr.Tab("🎬 Subtitle Burn-In Studio", id="tab_burn"):
                        with gr.Group():
                            gr.Markdown("### 🎨 Customize Subtitle Styling & Burn-in")
                            with gr.Row():
                                style_preset_dropdown = gr.Dropdown(
                                    choices=list(STYLE_PRESETS.keys()),
                                    value="Classic Gold",
                                    label="Karaoke Color Scheme",
                                    info="Highlight animation color when spoken.",
                                )
                                font_family_dropdown = gr.Dropdown(
                                    choices=[
                                        "Arial",
                                        "Helvetica",
                                        "Trebuchet MS",
                                        "Verdana",
                                        "Times New Roman",
                                        "Courier New",
                                    ],
                                    value="Arial",
                                    label="Font Family",
                                )
                                font_size_slider = gr.Slider(
                                    minimum=16,
                                    maximum=48,
                                    value=24,
                                    step=2,
                                    label="Font Size (pt)",
                                )

                            burn_mode_radio = gr.Radio(
                                choices=[
                                    "Auto-Detect (Hardcode if supported, else soft embed)",
                                    "Hardcode (Burn into video pixels)",
                                    "Lossless Soft Track (Fast container embed)",
                                ],
                                value="Auto-Detect (Hardcode if supported, else soft embed)",
                                label="Subtitling Method",
                            )

                            burn_btn = gr.Button(
                                "🔥 Generate Subtitled Video",
                                variant="primary",
                                size="lg",
                            )

                        burn_status_msg = gr.Markdown(
                            value="💡 Upload a video and run transcription to enable subtitle burn-in."
                        )
                        burned_video_player = gr.Video(
                            label="Subtitled Video Player",
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
                summary_output,
                full_transcript_box,
                segment_table,
                word_table,
                zip_download,
                srt_download,
                vtt_download,
                ass_download,
                json_download,
                wordsrt_download,
                code_viewer,
                burned_video_player,
                burn_status_msg,
                state_data,
            ],
        )

        # Event: Run transcription
        transcribe_btn.click(
            fn=run_transcription,
            inputs=[
                input_video,
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
                zip_download,
                srt_download,
                vtt_download,
                ass_download,
                json_download,
                wordsrt_download,
                code_viewer,
                burn_status_msg,
                state_data,
            ],
        )

        # Event: Format radio change in code inspector
        format_radio.change(
            fn=update_code_inspector,
            inputs=[format_radio, state_data],
            outputs=[code_viewer],
        )

        # Event: Run Burn-In
        burn_btn.click(
            fn=run_burn_in,
            inputs=[
                input_video,
                state_data,
                style_preset_dropdown,
                font_size_slider,
                font_family_dropdown,
                burn_mode_radio,
            ],
            outputs=[burned_video_player, burn_status_msg],
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(
        theme=getattr(app, "launch_theme", None),
        css=getattr(app, "launch_css", None),
    )

