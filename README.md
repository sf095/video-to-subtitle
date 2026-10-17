# 🎬 Video-to-Subtitle Studio

A modern, local, privacy-first application that transcribes videos to SubRip (`.srt`) subtitle files with **word-level timestamps** using **Whisper** (`faster-whisper` / CTranslate2).

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Whisper](https://img.shields.io/badge/Whisper-Word--Level%20Timestamps-green.svg)
![Gradio](https://img.shields.io/badge/UI-Gradio-orange.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

---

## 🌟 Key Features

- **🎯 Word-Level Timestamp Alignment:** Cross-attention word timestamps identify the exact start and end times of every spoken word with confidence scores.
- **⚡ High Performance:** Powered by `faster-whisper` (CTranslate2), running up to 4x faster with significantly reduced memory footprint.
- **📝 SubRip (.SRT) Export:** Clean, standard SubRip subtitle generation with exact segment timing, compatible with any video player or video editor.
- **🖥️ Dual Mode:**
  - **Web Studio (Gradio)**: Modern 2-column layout with metrics dashboard (WPM speaking rate, language confidence, duration), copyable full transcripts, word-level timeline tables, and live subtitle code inspector.
  - **Command-Line (CLI)**: Automate video subtitle generation directly from the terminal.

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have `ffmpeg` installed on your system (used for extracting audio from video):
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

Transcribe any video directly from the command line to generate a `.srt` subtitle file:

```bash
# Transcribe with default medium model (creates video.srt)
python -m video_to_subtitle.cli video.mp4

# Choose specific model (e.g. tiny, small, medium, large-v3)
python -m video_to_subtitle.cli video.mp4 --model small

# Specify target language (e.g. en, vi, es)
python -m video_to_subtitle.cli video.mp4 --language en

# Specify custom output directory
python -m video_to_subtitle.cli video.mp4 --output-dir ./subtitles
```

### CLI Arguments

| Argument | Description | Default |
|---|---|---|
| `video` | Path to input video or audio file | *(Required)* |
| `--model` | Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`, `large-v2`) | `medium` |
| `--device` | Inference device (`auto`, `cpu`, `cuda`) | `auto` |
| `--compute-type` | Quantization (`default`, `int8`, `float16`) | `default` |
| `--language` | Language code (e.g. `en`, `vi`) or auto-detect | `None` |
| `--output-dir` | Output folder for generated subtitles | Same as video folder |

---

## 📁 Project Structure

```
video_to_subtitle/
├── app.py                     # Gradio Web Studio UI
├── requirements.txt           # Dependencies
├── video_to_subtitle/
│   ├── __init__.py
│   ├── engine.py              # faster-whisper core & audio extraction
│   ├── formatters.py          # SubRip (.srt) generator & output path resolution
│   ├── cache_manager.py       # Temporary storage & model cache management
│   ├── platform_utils.py      # Platform utilities
│   └── cli.py                 # Command-line interface
├── tests/                     # Unit and integration test suite
└── docs/                      # Specifications and documentation
```

---

## 📝 License
MIT
