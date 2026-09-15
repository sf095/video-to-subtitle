# Spec: Remove Auto Output Subtitles in Web UI

## Objective
When a user transcribes a video in the Web UI (`app.py`), the app should **never** automatically write subtitle files (`.srt`, `.vtt`, `.ass`, `.json`, `.word.srt`, `.zip`) to the user's permanent filesystem (e.g., input video folder, `~/Downloads`, or current working directory).

Instead:
- The Web UI relies 100% on **in-app inspection** (Transcript, Timeline Tables, Code Inspector) and **browser Download buttons** (`.ZIP`, `.SRT`, `.VTT`, `.ASS`, `.JSON`, `.word.srt`).
- Subtitle files required by Gradio's `gr.DownloadButton` are staged in an isolated temporary directory (`tempfile.mkdtemp(prefix="subtitles_export_")`), ensuring the user's disk and project directories remain clean.
- Status messages and UI text are updated to remove references to auto-saving on disk.
- CLI (`video_to_subtitle/cli.py`) behavior remains explicit and unaffected.

---

## Assumptions & Discovered Constraints

1. **User Request**: The user explicitly confirmed: *"Never write subtitles to disk automatically; rely 100% on the browser Download buttons and in-app viewers."*
2. **Temporary File Requirement for Gradio**: Gradio's `gr.DownloadButton(value=file_path)` requires a local file path to serve file downloads to the user's browser. Therefore, files must still be generated into a temporary staging folder (`tempfile.mkdtemp`) so that clicking download buttons works seamlessly.
3. **No Clutter on User Disk**: The user's input video directory, `~/Downloads`, and project folder must receive zero automatic subtitle files when running transcription.
4. **Burn-in Studio**: When the user explicitly requests "Generate Subtitled Video" in the Burn-In studio, the output video is generated into a temporary folder for the in-app player (which has built-in download/save capability), or saved to an explicitly provided path.

---

## Tech Stack
- **Language**: Python 3.10+
- **Framework**: Gradio 4.x
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
├── app.py                         # Updated: writes subtitle exports to isolated temp dir for download buttons only
├── video_to_subtitle/
│   ├── formatters.py              # Export formatting functions
│   ├── platform_utils.py          # Platform dialog & temp utilities
│   ├── engine.py                  # Transcription engine
│   └── cli.py                     # CLI unchanged
├── tests/
│   ├── test_output_paths.py       # Updated: verifies Web UI transcription leaves video dir and ~/Downloads untouched
│   └── test_formatters.py         # Subtitle formatters
└── docs/specs/
    └── remove-auto-output-subtitles.md
```

---

## Code Style & Architecture

### Web UI Transcription Staging in `app.py`
```python
import tempfile
import os

# Inside run_transcription:
base_name = os.path.splitext(os.path.basename(effective_video))[0]

# Stage export files in an isolated temporary directory for DownloadButtons only
export_staging_dir = tempfile.mkdtemp(prefix="subtitles_export_")
paths = export_all_formats(segments, info, export_staging_dir, base_name)

# Create zip bundle in staging directory
zip_path = os.path.join(export_staging_dir, f"{base_name}_subtitles.zip")
create_zip_bundle(paths, zip_path)
```

### Clean UI Notifications
Update `burn_ready_status` to remove claims of saving to disk:
```python
burn_ready_status = (
    "💡 **Subtitles ready!** You can download them below, inspect the formatted code, "
    "or customize styling and click **Generate Subtitled Video**."
)
```

---

## Testing Strategy
- **Framework**: `pytest`
- **Tests in `tests/test_output_paths.py`**:
  - `test_app_transcription_does_not_save_to_video_directory`: Verifies that after `run_transcription`, no `.srt`, `.vtt`, or `.zip` files exist in the source video folder.
  - `test_app_transcription_does_not_save_to_downloads`: Verifies that after `run_transcription` with an upload, no files are written to `~/Downloads`.
  - `test_app_transcription_provides_downloadable_paths`: Verifies that the DownloadButtons receive valid temporary file paths that exist and can be read.

---

## Boundaries
- **Always do:**
  - Keep all in-browser Download buttons (`.ZIP`, `.SRT`, `.VTT`, `.ASS`, `.JSON`, `.word.srt`) fully functional.
  - Keep transcript box, segment table, word timestamps, and live code inspector working.
  - Keep all tests green.
- **Ask first:**
  - Any changes to CLI output behavior.
- **Never do:**
  - Auto-write subtitle files to user's video folder, home folder, or `~/Downloads` during Web UI transcription.

---

## Success Criteria
1. Running transcription in `app.py` leaves the source video folder and `~/Downloads` completely free of subtitle files.
2. The user can download any subtitle format (`.srt`, `.vtt`, `.ass`, `.json`, `.word.srt`, `.zip`) via the UI Download buttons.
3. The UI status notification accurately states that subtitles are ready for download/preview without claiming to have saved them to disk.
4. All unit and integration tests pass with 0 errors.

---

## Phase 2: Technical Implementation Plan

1. **Components to Modify:**
   - **`app.py`**:
     - In `run_transcription`: replace `resolve_output_directory` with `tempfile.mkdtemp(prefix="subtitles_export_")`.
     - Update `state_data["out_dir"]` to point to the staging directory.
     - Update `burn_ready_status` message.
     - In `run_burn_in`: output video to a temporary staging directory if no explicit custom output folder is provided.
     - In `clear_all_inputs`: retain reset state.
   - **`tests/test_output_paths.py`**:
     - Update `test_app_transcription_local_path` to assert that files are NOT created in the video directory.
     - Update `test_app_transcription_upload_redirects_to_downloads` to assert that files are NOT created in `~/Downloads`.
     - Add assertion that `state_data["out_dir"]` is inside temp directory and files exist there for download.

2. **Implementation Sequence:**
   - Step 1: Update `app.py` to stage files in `tempfile.mkdtemp` and update status banners.
   - Step 2: Update `tests/test_output_paths.py` to verify no automatic filesystem pollution.
   - Step 3: Run `pytest` to verify all test suites.

---

## Phase 3: Tasks

- [x] **Task 1: Update Web UI Staging in `app.py`**
  - Acceptance: `run_transcription` stages all download files in `tempfile.mkdtemp` and never writes to video dir or `~/Downloads`. Status messages reflect in-app availability.
  - Verify: `python3 -m py_compile app.py`
  - Files: `app.py`

- [x] **Task 2: Update Test Suite in `tests/test_output_paths.py`**
  - Acceptance: Tests verify no auto-saving to video directory or `~/Downloads`, while ensuring download paths are valid and readable.
  - Verify: `pytest tests/test_output_paths.py`
  - Files: `tests/test_output_paths.py`

- [x] **Task 3: Full Regression Verification**
  - Acceptance: All test suites (`test_formatters.py`, `test_output_paths.py`, `test_platform_utils.py`) pass cleanly.
  - Verify: `pytest`
  - Files: `tests/`
