# Spec: Output SRT Files to Input Video Folder

## Objective
Ensure that whenever a video is processed (via CLI, Web UI, or Python core API), the generated SubRip subtitle (`.srt`) files are saved in the same directory as the inputted video file by default.

For local workflows, creators expect subtitles to appear immediately alongside their source video file (`/path/to/video.mp4` -> `/path/to/video.srt`), avoiding manual download steps or searching through temporary directories.

---

## Assumptions & Discovered Constraints

1. **CLI Current Behavior:**
   - `video_to_subtitle/cli.py` already defaults `--output-dir` to `os.path.dirname(os.path.abspath(args.video))`. Subtitles generated via CLI are saved alongside the video file unless `--output-dir` overrides it.
   - We assume this behavior should be preserved, tested, and strictly enforced.

2. **Web UI (`app.py`) Current Behavior & Browser Limitations:**
   - In `app.py`, `run_transcription` currently writes files to `tempfile.mkdtemp(prefix="subtitles_")`.
   - In web browsers, security sandboxing prevents file upload controls (`<input type="file">` / Gradio's `gr.Video(sources=["upload"])`) from exposing the client's absolute directory path on disk (only the filename and uploaded temporary payload are accessible).
   - Therefore, to support saving directly to the same folder as the input video in the Web UI:
     - The Web UI will support entering or choosing a **Direct Local File Path** (e.g. `/Users/name/Videos/sample.mp4`).
     - When a direct local path is provided, the output `.srt` file will be automatically saved in that exact folder (`os.path.dirname(os.path.abspath(path))`).
     - A toggle or output directory selector ("Save to video folder" / "Custom destination") will be visible so users have clear transparency and feedback on where files are saved on their machine.
     - For uploaded files (where the original host folder cannot be accessed via browser sandbox), the UI allows specifying an output folder or falls back to user download buttons, showing a clear notification.

3. **SRT Formats:**
   - The system generates both Standard SRT (`<basename>.srt`) and Word-level SRT (`<basename>.word.srt`). Both will be output to the video folder when SRT generation is triggered.

---

## Tech Stack
- **Language:** Python 3.10+
- **Transcription Engine:** `faster-whisper` (CTranslate2)
- **Audio & Video Processing:** `ffmpeg` / `ffprobe`
- **Web UI:** Gradio 4.x
- **Testing:** `pytest`

---

## Commands
```bash
# Setup venv & dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run Unit & Integration Tests
PYTHONPATH=. python3 tests/test_formatters.py
PYTHONPATH=. pytest tests/

# Run CLI transcription (outputs SRT to same folder as input video)
python3 -m video_to_subtitle.cli /path/to/video.mp4 --format srt

# Run Web UI
PYTHONPATH=. python3 app.py
```

---

## Project Structure
```
video_to_subtitle/
├── app.py                         # Gradio Web Studio UI (adds direct local video path & folder saving)
├── pyproject.toml                 # Packaging & pytest configuration
├── requirements.txt               # Dependencies
├── video_to_subtitle/
│   ├── __init__.py                # Package root
│   ├── engine.py                  # Audio extraction & faster-whisper core
│   ├── formatters.py              # SRT, VTT, ASS, JSON generators & export_all_formats
│   ├── burn_in.py                 # ffmpeg subtitle video burning
│   └── cli.py                     # Command-line interface
├── tests/
│   ├── test_formatters.py         # Subtitle formatting tests
│   ├── test_output_paths.py       # New tests verifying SRT output folder resolution
└── docs/
    └── specs/
        └── srt-output-location.md # This specification document
```

---

## Code Style & Implementation Details

### Path Resolution Logic
Consistent resolution utility for output directories:

```python
import os
from pathlib import Path
from typing import Optional

def resolve_output_directory(video_path: str, custom_output_dir: Optional[str] = None) -> str:
    """
    Resolve the destination directory for subtitle files.
    Defaults to the same folder containing the input video.
    """
    if custom_output_dir and custom_output_dir.strip():
        out_dir = os.path.abspath(custom_output_dir.strip())
    else:
        out_dir = os.path.dirname(os.path.abspath(video_path))
    os.makedirs(out_dir, exist_ok=True)
    return out_dir
```

### Web UI Enhancements in `app.py`
1. Provide a dual-input mechanism for video source:
   - **Upload File**: Standard browser drag-and-drop.
   - **Local File Path**: Text input for local video path with file existence verification.
2. In `run_transcription`:
   - If a local video path is used or available, determine `target_folder = resolve_output_directory(video_path)`.
   - Write `.srt` (and `.word.srt` if selected) directly into `target_folder`.
   - Display a status message: `📁 Subtitle saved to: /path/to/video_folder/video_name.srt`.
   - Keep download buttons interactive so users can still download through the browser if preferred.

---

## Testing Strategy
- **Framework:** `pytest`
- **Test Locations:** `tests/test_output_paths.py`
- **Coverage Requirements:**
  1. CLI output path defaults to input video directory when `--output-dir` is omitted.
  2. Core export functions save `.srt` and `.word.srt` in the specified or derived video directory.
  3. `resolve_output_directory` properly handles absolute paths, relative paths, and custom output overrides.
  4. Web UI transcription logic writes to video directory when given a local file path.

---

## Boundaries
- **Always do:**
  - Save standard `.srt` directly alongside the input video file when a video path on the local filesystem is processed.
  - Inform the user via CLI stdout and UI status banner of the exact location where `.srt` files were written.
  - Preserve backward compatibility for `--output-dir` in the CLI.
  - Maintain all existing tests green (`PYTHONPATH=. python3 tests/test_formatters.py`).
- **Ask first:**
  - Changing existing default subtitle formats for CLI `--format` (currently `all`).
  - Automatically overwriting existing `.srt` files if a backup policy is desired.
- **Never do:**
  - Break browser upload workflow when running on remote or hosted Gradio instances.
  - Hardcode absolute paths or platform-specific directory separators.

---

## Success Criteria
1. When running `python -m video_to_subtitle.cli /path/to/my_video.mp4`, the resulting file `/path/to/my_video.srt` is created in `/path/to/`.
2. When transcribing a local video in the Web UI (`app.py`), the output `.srt` file is automatically saved into the same folder as the input video.
3. Automated unit/integration tests in `tests/test_output_paths.py` pass cleanly verifying that `.srt` output files match the input video directory.
4. Existing tests in `tests/test_formatters.py` continue to pass.

---

---

## Phase 2: Technical Implementation Plan

1. **Major Components & Dependencies:**
   - **Path Resolution Helper (`video_to_subtitle/formatters.py`):**
     Implement `resolve_output_directory(video_path: str, custom_output_dir: Optional[str] = None) -> str`. It guarantees that if `custom_output_dir` is not provided, the returned directory is `os.path.dirname(os.path.abspath(video_path))`.
   - **CLI Pipeline (`video_to_subtitle/cli.py`):**
     Ensure `cli.py` uses `resolve_output_directory(args.video, args.output_dir)`.
   - **Gradio Web Studio (`app.py`):**
     - Add a `local_video_path` textbox input in the Media Input section, allowing users to enter a local video file path (e.g. `/path/to/video.mp4`).
     - In `run_transcription`: if `local_video_path` is given or if `video_path` is a local file outside the temporary directory, automatically save `.srt` (and `.word.srt`) to the video's folder.
     - Also in `run_burn_in`: output the subtitled video to the video's directory when a local video path is used.
     - Display a visible notification banner indicating the exact saved file paths.
   - **Test Suite (`tests/test_output_paths.py`):**
     - Add test cases verifying that `resolve_output_directory` and `export_all_formats` output files directly to the video's folder.
     - Add integration test for CLI output behavior.

2. **Implementation Order:**
   - Step 1: Write `resolve_output_directory` in `video_to_subtitle/formatters.py` and write unit tests in `tests/test_output_paths.py`.
   - Step 2: Ensure CLI uses this helper and verify test coverage.
   - Step 3: Update `app.py` to support direct local file input and saving `.srt` to that directory.
   - Step 4: Run regression tests across all test suites.

3. **Risks and Mitigations:**
   - *Risk:* Browser drag-and-drop upload cannot know the client's host path due to browser sandboxing.
     *Mitigation:* Dual input support in the Web UI: users can either drag-and-drop (saves to temp + download button) or enter the local file path (saves directly to video folder on disk).

---

## Phase 3: Tasks

- [x] **Task 1: Path Resolution Utility & Unit Tests**
  - Acceptance: `resolve_output_directory` resolves to the input video folder when no override is passed, creates directories if missing, and handles both relative and absolute paths.
  - Verify: `PYTHONPATH=. python3 tests/test_output_paths.py`
  - Files: `video_to_subtitle/formatters.py`, `tests/test_output_paths.py`

- [x] **Task 2: CLI Guarantee of Video Folder Output**
  - Acceptance: CLI transcription saves `.srt` files in the exact same directory as the video file.
  - Verify: Automated CLI test in `tests/test_output_paths.py` verifying files are generated next to the video.
  - Files: `video_to_subtitle/cli.py`, `tests/test_output_paths.py`

- [x] **Task 3: Web UI Local Path Input & Folder Saving**
  - Acceptance: `app.py` provides a local video path input, validates file existence, and saves `.srt` and `.word.srt` in the input video's folder, reporting the saved location in the UI.
  - Verify: Automated test calling `run_transcription` with local file path and checking output `.srt` existence.
  - Files: `app.py`, `tests/test_output_paths.py`

- [x] **Task 4: Full Regression and Verification**
  - Acceptance: All tests in `tests/test_formatters.py` and `tests/test_output_paths.py` pass without errors.
  - Verify: `PYTHONPATH=. python3 tests/test_formatters.py && PYTHONPATH=. python3 tests/test_output_paths.py`
  - Files: `tests/test_formatters.py`, `tests/test_output_paths.py`

