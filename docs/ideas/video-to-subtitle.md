# Video-to-Subtitle Studio (Whisper Word-Level Engine)

## Problem Statement
How might we enable video creators and developers to turn any video into word-accurate, production-ready subtitles (SRT, VTT, animated Karaoke ASS, JSON) locally with zero cloud costs and zero manual timeline scrubbing?

## Recommended Direction
Build a clean, modular, high-throughput Python application with a local Web UI (Gradio) and CLI:
1. **Core Engine (`engine.py`):** Uses `ffmpeg` to extract 16kHz mono audio and runs `faster-whisper` (CTranslate2) with `word_timestamps=True`, defaulting to `medium`.
2. **Subtitle Formatter (`formatters.py`):** Converts word-level timestamp objects into:
   - **SRT** (standard segmented and word-level)
   - **VTT** (standard WebVTT with cues)
   - **ASS** (karaoke animated highlights using `{\k...}` tags)
   - **JSON** (full metadata: words, start/end timestamps, confidence scores)
3. **Web UI (`app.py` via Gradio):**
   - Video upload & interactive media player
   - Model selection (`tiny`, `base`, `small`, `medium`, `large-v3`) & language detection
   - Live transcription progress & synchronized word-level transcript preview
   - One-click downloads for individual subtitle files or bundled `.zip`
   - Optional burnt-in video preview using ffmpeg
4. **CLI Support (`cli.py`):** Direct terminal command for batch video processing and pipeline integration.

## Key Assumptions to Validate
- [ ] `ffmpeg` is present on the host system or can be invoked cleanly for audio extraction and video burn-in.
- [ ] `faster-whisper` runs efficiently on Apple Silicon (CPU / MPS) and CUDA.
- [ ] ASS karaoke syntax (`{\k...}`) renders smoothly in video players (VLC, MPV) and video editors (Premiere, DaVinci).
- [ ] Audio extraction handles multi-channel audio, different codecs, and variable frame rates cleanly.

## MVP Scope
- [x] Audio/Video ingestion (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.mp3`, `.wav`)
- [x] `faster-whisper` integration with `word_timestamps=True` (default: `medium`)
- [x] Multi-format export: `.srt`, `.vtt`, `.ass` (karaoke styled), `.json`
- [x] Web interface (Gradio) with video player and interactive word transcript
- [x] Command-line interface (CLI) for automated/scripted usage
- [x] Video subtitle burn-in generation via `ffmpeg`

## Not Doing (and Why)
- **Multi-speaker Diarization:** Avoids heavy extra models (PyAnnote) and HuggingFace token requirements; keeps setup instant and frictionless.
- **Cloud API / User Accounts:** 100% local, private, and zero-subscription.
- **Heavy Electron Wrapper:** Python + Gradio provides an immediate browser UI without bloated packaged runtimes.

## Verification Checklist
- [x] How Might We framing established
- [x] User and success criteria defined
- [x] Multiple directions explored and stress-tested
- [x] Hidden assumptions surfaced
- [x] Trade-offs codified in "Not Doing"
- [x] Confirmed by user
