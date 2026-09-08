# 🎬 Video-to-Subtitle Studio

A modern, local, privacy-first application that transcribes videos to subtitle files with **word-level timestamps** using **Whisper** (`faster-whisper` / CTranslate2).

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Whisper](https://img.shields.io/badge/Whisper-Word--Level%20Timestamps-green.svg)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

---

## 🌟 Key Features

- **🎯 Word-Level Timestamp Alignment:** Cross-attention word timestamps identify the exact start and end times of every spoken word with confidence scores.
- **⚡ High Performance:** Powered by `faster-whisper` (CTranslate2), running up to 4x faster with significantly reduced memory footprint.
- **📦 Multi-Format Subtitle Export:**
  - **SRT (`.srt`)**: Standard segmented subtitles for any video player.
  - **Word-level SRT (`.word.srt`)**: Single word or fast-paced subtitles for short-form clips.
  - **WebVTT (`.vtt`)**: Modern web standard subtitles.
  - **Karaoke ASS (`.ass`)**: Advanced SubStation Alpha format with `{\kf...}` tags for real-time animated word highlighting (TikTok, Reels, Shorts style).
  - **JSON (`.json`)**: Machine-readable structured data containing words, timestamps, and probabilities.
  - **ZIP Archive (`.zip`)**: One-click download containing all formats.
- **🖥️ Dual Mode:**
  - **Web Studio (Gradio)**: Modern 2-column layout with metrics dashboard (WPM speaking rate, language confidence, duration), 1-click sample demo, copyable full transcripts, live subtitle code inspector, and dedicated burn-in studio with custom styling presets.
  - **Command-Line (CLI)**: Automate batch video processing directly from the terminal.
- **🎨 Custom Subtitle Styling & Burn-In:** Choose font families, font sizes, and animated karaoke highlight color schemes (Classic Gold, Cyber Neon, Modern Emerald, Warm Sunset, Minimalist Clean) with automatic libass detection and lossless soft track fallback.

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have `ffmpeg` installed on your system:
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### 2. Setup Virtual Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch Web UI
```bash
source .venv/bin/activate
python app.py
```
Open your browser at `http://127.0.0.1:7860`.

---

## 💻 CLI Usage

You can also transcribe any video directly from the command line:

```bash
# Transcribe with default medium model (exports all subtitle formats)
python -m video_to_subtitle.cli video.mp4

# Choose specific model and output format
python -m video_to_subtitle.cli video.mp4 --model medium --format ass

# Specify target language (e.g. en, vi, es)
python -m video_to_subtitle.cli video.mp4 --language en

# Also burn karaoke subtitles directly into an output video
python -m video_to_subtitle.cli video.mp4 --model medium --burn-in
```

### CLI Arguments

| Argument | Description | Default |
|---|---|---|
| `video` | Path to input video or audio file | *(Required)* |
| `--model` | Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`) | `medium` |
| `--device` | Inference device (`auto`, `cpu`, `cuda`) | `auto` |
| `--compute-type` | Quantization (`default`, `int8`, `float16`) | `default` |
| `--language` | Language code (e.g. `en`, `vi`) or auto-detect | `None` |
| `--output-dir` | Output folder for generated subtitles | Same as video |
| `--format` | `all`, `srt`, `word_srt`, `vtt`, `ass`, `json` | `all` |
| `--burn-in` | Hardcode karaoke subtitles onto video via ffmpeg | `False` |

---

## 📁 Project Structure

```
video_to_subtitle/
├── app.py                     # Gradio Web Studio UI
├── requirements.txt           # Dependencies
├── video_to_subtitle/
│   ├── __init__.py
│   ├── engine.py              # faster-whisper core & audio extraction
│   ├── formatters.py          # SRT, VTT, Karaoke ASS, JSON generators
│   ├── burn_in.py             # ffmpeg subtitle video burning
│   └── cli.py                 # Command-line interface
└── docs/
    └── ideas/
        └── video-to-subtitle.md # Refined product spec one-pager
```

---

## 📝 License
MIT
