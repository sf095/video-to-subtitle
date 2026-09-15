# Spec: Local Video Handling and Non-Cache Storage

## Objective
The application is primarily used locally on the user's computer (macOS). Currently, when a user uploads a video using the Web UI drag-and-drop widget, two issues occur:
1. Gradio streams the video over HTTP into a hidden macOS temporary cache folder (`/private/var/folders/.../T/gradio/...`).
2. The subtitle resolution logic defaults to saving `.srt`, `.vtt`, `.ass`, `.zip`, and burned `.mp4` files into that same hidden cache folder, making it difficult for the user to locate or manage output files.

This specification defines a first-class local desktop experience:
- Provide a native macOS file selection dialog ("📂 Browse File...") so local files are selected directly by their original path on disk, eliminating redundant file duplication into cache.
- Ensure that if a file is uploaded via the drag-and-drop browser widget, outputs are **never** dumped into hidden OS temporary/cache directories. Instead, they default to `~/Downloads` (or a visible `./output` directory).
- Provide a one-click "📂 Show in Finder" / "📂 Open Output Folder" action on completion so users can instantly view their generated files.
- Add an option to clean up temporary cache files to prevent disk bloating.

---

## Assumptions & Discovered Constraints

1. **Local Environment**: The user runs the application locally on macOS (`localhost:7860`).
2. **Browser Upload Limitation**: Web browsers cannot reveal local file paths via standard `<input type="file">` due to browser sandbox security. Therefore, direct file access requires either:
   - Selecting the file via a native OS file dialog (`osascript` on macOS, with fallback).
   - Or pasting/entering the file path directly into the input.
3. **Temp Directory Detection**: When a path originates from a temporary directory (e.g. `/private/var/folders/`, `/tmp/`, or `tempfile.gettempdir()`), `resolve_output_directory` should NOT consider it the user's desired output folder.
4. **Fallback Folder**: For browser uploads without a custom destination, `~/Downloads` is the standard, most intuitive location for desktop users.
5. **Headless / Remote Compatibility**: If the server is ever launched without a GUI or on Linux, native file picker calls must fail gracefully without crashing the server.

---

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: Gradio 4.x
- **OS Automation**: macOS `osascript` (AppleScript) for native Finder file/folder dialogs
- **Testing**: `pytest`

---

## Commands
```bash
# Setup venv & dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Run Tests
PYTHONPATH=. pytest tests/

# Run Application
PYTHONPATH=. python3 app.py
```

---

## Project Structure
```
video_to_subtitle/
├── app.py                         # Web Studio UI: add Browse button, Open in Finder, sensible default out_dir
├── video_to_subtitle/
│   ├── formatters.py              # Update resolve_output_directory to detect temp dirs & fallback to ~/Downloads
│   ├── platform_utils.py          # Native OS dialogs (osascript) and 'reveal in Finder' utilities
│   ├── engine.py                  # Core transcription
│   └── cli.py                     # CLI interface
├── tests/
│   ├── test_output_paths.py       # Unit tests for temp-directory detection and fallback
│   └── test_platform_utils.py     # Unit tests for platform dialog fallbacks
└── docs/specs/
    └── local-file-handling-and-storage.md
```

---

## Code Style & Architecture

### 1. Temp Directory Detection in `resolve_output_directory`
```python
import os
import tempfile
from pathlib import Path
from typing import Optional

def is_temp_directory(path: str) -> bool:
    """Check if a path is located inside system or Gradio temporary directories."""
    abs_path = os.path.abspath(path)
    temp_roots = [
        os.path.abspath(tempfile.gettempdir()),
        "/tmp",
        "/private/tmp",
        "/var/tmp",
        "/private/var/folders",
    ]
    return any(abs_path.startswith(root) for root in temp_roots)

def resolve_output_directory(
    video_path: str,
    custom_output_dir: Optional[str] = None,
    default_fallback_dir: Optional[str] = None,
) -> str:
    """
    Resolve the destination directory for subtitle files.
    - If custom_output_dir is provided: use it.
    - If video_path is a real local file (not in temp/cache): use video's parent folder.
    - If video_path is in a temp/cache directory: fallback to default_fallback_dir (e.g. ~/Downloads).
    """
    if custom_output_dir and custom_output_dir.strip():
        out_dir = os.path.abspath(custom_output_dir.strip())
    elif not is_temp_directory(video_path):
        out_dir = os.path.dirname(os.path.abspath(video_path))
    else:
        fallback = default_fallback_dir or os.path.expanduser("~/Downloads")
        out_dir = os.path.abspath(fallback)

    os.makedirs(out_dir, exist_ok=True)
    return out_dir
```

### 2. Native macOS File Picker Utility (`platform_utils.py`)
```python
import subprocess
import sys
from typing import Optional

def pick_local_file(prompt: str = "Select Video File", file_types: Optional[list] = None) -> Optional[str]:
    """Open a native macOS Finder file picker dialog and return the POSIX path."""
    if sys.platform != "darwin":
        return None
    try:
        cmd = [
            "osascript",
            "-e",
            f'POSIX path of (choose file with prompt "{prompt}")',
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        path = res.stdout.strip()
        return path if path else None
    except Exception:
        return None

def open_folder_in_explorer(folder_path: str) -> bool:
    """Reveal or open the folder in macOS Finder (or system file manager)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", folder_path], check=True)
            return True
    except Exception:
        pass
    return False
```

---

## Testing Strategy
- **Framework**: `pytest`
- **Test Coverage**:
  - `test_resolve_output_directory_with_temp_path`: Passing a path in `/tmp` or `/private/var/folders/...` falls back to `~/Downloads` (or configured fallback) instead of keeping it in temp.
  - `test_resolve_output_directory_with_local_video`: Passing `/Users/foo/video.mp4` returns `/Users/foo`.
  - `test_resolve_output_directory_with_custom`: Passing explicit directory returns explicit directory.
  - `test_platform_utils`: Mock `subprocess.run` to verify `osascript` invocation and error handling.

---

## Boundaries
- **Always do:**
  - Save to the video folder when a direct local path outside of temp is provided.
  - Avoid saving outputs into `/private/var/folders/...` or `/tmp/...` unless explicitly requested.
  - Provide cross-platform fallbacks so non-macOS or headless setups don't crash.
  - Keep all existing tests green.
- **Ask first:**
  - Whether the default fallback folder for uploads should be `~/Downloads` or a project-local `./output` directory.
  - Whether to automatically purge uploaded videos from Gradio cache after transcription finishes.
- **Never do:**
  - Block or hang the server waiting on a dialog if launched headlessly.
  - Overwrite user files silently without standard safe naming or notifications.

---

## Success Criteria
1. When uploading via the browser widget without a custom output folder, subtitles and output files are saved to `~/Downloads` instead of the hidden Gradio cache folder.
2. A "📂 Browse..." button in the UI allows local macOS users to pick a video file directly, filling in the local path without uploading to cache.
3. A "📂 Open in Finder" button is displayed on completion, allowing users to open the output folder in Finder with 1 click.
4. If a local file path is selected/entered, subtitles are saved directly beside the original video file.
5. All automated unit tests in `tests/test_output_paths.py` pass.

---

## Phase 2: Technical Implementation Plan

1. **Major Components & Architecture**:
   - **`video_to_subtitle/platform_utils.py`**:
     - `pick_local_file(prompt="Select Video File") -> Optional[str]`: Uses `osascript` on macOS to open a native Finder file picker. Gracefully returns None on cancel or non-macOS.
     - `pick_local_folder(prompt="Select Output Folder") -> Optional[str]`: Uses `osascript` to open a native folder picker.
     - `reveal_in_file_manager(path: str) -> bool`: Uses `open -R <path>` or `open <dir>` on macOS to reveal files/folders in Finder.
     - `is_gradio_temp_path(path: str) -> bool`: Identifies if a path resides inside Gradio or system temporary cache directories.
   - **`video_to_subtitle/formatters.py`**:
     - Update `resolve_output_directory(video_path: str, custom_output_dir: Optional[str] = None, fallback_dir: Optional[str] = None) -> str`:
       - If `custom_output_dir` is specified, use it.
       - If `video_path` is detected as a temporary/Gradio cache path, fallback to `fallback_dir` or `~/Downloads`.
       - Otherwise, use `os.path.dirname(os.path.abspath(video_path))`.
   - **`app.py`**:
     - Add `browse_video_btn = gr.Button("📂 Browse...", size="sm")` next to `local_video_input`.
     - Add `browse_out_btn = gr.Button("📂 Browse...", size="sm")` next to `output_dir_input`.
     - Connect `browse_video_btn.click` and `browse_out_btn.click` to the native picker handlers.
     - Add an `open_folder_btn = gr.Button("📂 Reveal Output in Finder", size="sm")` visible after transcription/burn-in completes.
     - Ensure `run_transcription` uses `~/Downloads` as fallback when a browser-uploaded video is used without custom output directory.
   - **`tests/test_output_paths.py`**:
     - Add test cases verifying that paths in Gradio cache directories fall back to `~/Downloads`.
     - Add tests for `is_gradio_temp_path`.
     - Add unit tests for `platform_utils` with mocking.

2. **Implementation Order**:
   - Step 1: Implement `video_to_subtitle/platform_utils.py`.
   - Step 2: Update `video_to_subtitle/formatters.py` with `is_gradio_temp_path` and fallback logic in `resolve_output_directory`.
   - Step 3: Add unit tests in `tests/test_output_paths.py` and run pytest.
   - Step 4: Update `app.py` with the "📂 Browse..." and "📂 Reveal in Finder" buttons and event handlers.
   - Step 5: Verify all automated tests and UI integration.

3. **Risks and Mitigations**:
   - *Risk:* User cancels the native file picker dialog.
     *Mitigation:* Catch error code -128 in AppleScript / subprocess and return empty string or previous value so UI state does not change or error.
   - *Risk:* App is run on non-macOS or headless environment.
     *Mitigation:* Safe try/except wrappers; return None if `osascript` fails; UI textboxes remain manually editable.

---

## Phase 3: Tasks

- [x] **Task 1: Platform Utilities Module (`platform_utils.py`)**
  - Acceptance: `pick_local_file`, `pick_local_folder`, `reveal_in_file_manager`, and `is_gradio_temp_path` are implemented with robust macOS support and safe fallback.
  - Verify: Unit tests with mocked subprocess calls in `tests/test_platform_utils.py`.
  - Files: `video_to_subtitle/platform_utils.py`, `tests/test_platform_utils.py`

- [x] **Task 2: Gradio Temp Cache Redirection in `resolve_output_directory`**
  - Acceptance: When `video_path` is in a Gradio/OS temp directory and no custom output directory is provided, `resolve_output_directory` falls back to `~/Downloads` instead of the temp folder.
  - Verify: Unit test in `tests/test_output_paths.py`.
  - Files: `video_to_subtitle/formatters.py`, `tests/test_output_paths.py`

- [x] **Task 3: Web UI Integration in `app.py`**
  - Acceptance: "📂 Browse..." buttons added for local video and output folder; "📂 Reveal in Finder" button added to results; browser-upload fallback to `~/Downloads` wired up.
  - Verify: Run `PYTHONPATH=. pytest tests/` and smoke-test app event handlers.
  - Files: `app.py`

- [x] **Task 4: Full Test Suite Verification**
  - Acceptance: All tests in `tests/` pass with zero regressions.
  - Verify: `PYTHONPATH=. pytest tests/`
  - Files: `tests/test_output_paths.py`, `tests/test_formatters.py`, `tests/test_platform_utils.py`

