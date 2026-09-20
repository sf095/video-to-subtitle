# Spec: Remove Video/Folder Browsing, Reveal in Finder, and Local Video Path Input

## Objective
Streamline the Web Studio UI (`app.py`) by completely removing desktop-specific native OS automation features (AppleScript / Finder dialogs and reveal commands) and removing the secondary manual local video/audio path input (`local_video_input`). The Web UI relies on the direct media uploader widget (`input_video`).

Specifically:
- Remove the local video file browse button (`browse_video_btn`) and output folder browse button (`browse_out_btn`).
- Remove the "Or Local Video/Audio File Path" text input (`local_video_input`).
- Remove both Finder reveal buttons (`open_folder_btn` in Subtitle Export tab, `open_burned_btn` in Subtitle Burn-In Studio tab).
- Clean up the corresponding event handlers (`on_browse_video`, `on_browse_output`, `on_reveal_folder`, `on_reveal_burned`).
- Remove unused native OS helper functions (`pick_local_file`, `pick_local_folder`, `reveal_in_file_manager`) from `video_to_subtitle/platform_utils.py`, retaining only `is_gradio_temp_path`.
- Keep core functionality intact: media uploader widget (`input_video`), in-browser subtitle downloads, in-browser video playback, and CLI operations.
- Update test suites (`tests/test_output_paths.py`, `tests/test_platform_utils.py`).

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

# Run Unit Tests
PYTHONPATH=. pytest tests/

# Run Gradio Web UI
PYTHONPATH=. python3 app.py
```

---

## Project Structure
```
video_to_subtitle/
├── app.py                     # Web Studio UI: remove browse buttons, local_video_input, open_folder_btn, open_burned_btn & event handlers
├── video_to_subtitle/
│   ├── platform_utils.py      # Retain only is_gradio_temp_path
│   ├── formatters.py          # Output formatting & path resolution (unchanged)
│   ├── engine.py              # Core transcription (unchanged)
│   └── cli.py                 # CLI interface (unchanged)
├── tests/
│   ├── test_output_paths.py   # Updated: adjust clear_all_inputs test count and run_transcription outputs
│   ├── test_platform_utils.py # Tests is_gradio_temp_path
│   └── test_formatters.py     # Subtitle formatting tests (unchanged)
└── docs/specs/
    └── remove-browse-and-reveal.md
```

---

## Code Style & Architecture

### 1. UI Input Layout in `app.py`
The left column now cleanly features the media uploader widget directly above the Clear All button:
```python
input_video = gr.Video(
    label="Media Input (Upload Video or Audio)",
    sources=["upload"],
)

clear_btn = gr.Button(
    "🗑️ Clear All",
    variant="ghost",
    size="sm",
)
```

And `output_dir_input` remains a clean standalone textbox:
```python
output_dir_input = gr.Textbox(
    label="Save to Folder (Optional)",
    placeholder="Leave blank to only use in-browser downloads",
    info="Leave blank to prevent saving files to disk (download via buttons below).",
    lines=1,
)
```

### 2. Subtitle Download Center in `app.py`
`zip_download` stands cleanly on its own without `open_folder_btn`:
```python
zip_download = gr.DownloadButton(
    "📦 Download Subtitle Bundle (.ZIP)",
    variant="primary",
    size="lg",
    interactive=False,
)
```

### 3. Component Outputs & Event Wiring Signatures
- `run_transcription`: receives `input_video` as primary media source (plus `local_video_path` as optional backward-compatible kwarg); returns 13 outputs.
- `run_burn_in`: returns 2 outputs `(output_video, status_msg)`.
- `clear_all_inputs`: returns 16 items (removed `local_video_input`, `open_folder_btn`, and `open_burned_btn`).

---

## Testing Strategy
- **Framework**: `pytest`
- **Unit Tests**:
  - `tests/test_platform_utils.py`: verify `is_gradio_temp_path` functionality.
  - `tests/test_output_paths.py`: verify `clear_all_inputs()` returns 16 items and `run_transcription()` works with direct video paths.
  - `tests/test_formatters.py`: verify subtitle formatting unaffected.
- **Pass Criteria**: `pytest` passes with 0 failures and 0 errors.

---

## Boundaries
- **Always do**:
  - Verify all tests pass with `pytest`.
  - Maintain drag-and-drop / browser upload (`input_video`).
  - Maintain all 6 subtitle browser download buttons.
- **Never do**:
  - Break CLI commands (`cli.py`).
  - Delete `is_gradio_temp_path` needed by `resolve_output_directory`.
  - Leave mismatched output tuple counts in Gradio callback wiring.

---

## Tasks

- [x] Task 1: Clean up `video_to_subtitle/platform_utils.py` and `tests/test_platform_utils.py`
- [x] Task 2: Remove Browse and Reveal in Finder buttons from `app.py`
- [x] Task 3: Remove `local_video_input` from `app.py` (component, clear_all_inputs, transcribe_btn wiring)
- [x] Task 4: Update test assertions in `tests/test_output_paths.py` and verify all tests pass
