# Spec: Remove Burn-In Features and Restrict Export Strictly to SRT

## Objective
Simplify the Video-to-Subtitle application by completely removing all "burn-in" features (rendering subtitles onto video frames or soft-embedding tracks via ffmpeg) and restricting subtitle export exclusively to SubRip (`.srt`) format. All other export formats (`.vtt`, `.ass`, `.json`, `.word.srt`, and `.zip` archive bundles) and related UI tabs, CLI options, and formatters will be removed.

---

## Tech Stack
- **Language**: Python 3.10+
- **Inference Engine**: `faster-whisper`
- **Web Framework**: Gradio 4.x
- **Audio Extraction**: `ffmpeg` (retained for extracting audio from video for transcription)
- **Data Handling**: `pandas`
- **Testing**: `pytest`

---

## Commands
```bash
# Activate environment
source .venv/bin/activate

# Run test suite
pytest

# Run Web Studio UI
python app.py

# Run CLI transcription (generates <basename>.srt)
python -m video_to_subtitle.cli video.mp4
```

---

## Assumptions
1. **Single Export Format**: Only standard SubRip (`.srt`) is generated and exported. Word-level `.word.srt`, WebVTT (`.vtt`), ASS (`.ass`), JSON (`.json`), and `.zip` archive bundles are completely removed from exports.
2. **Word-Level UI Timestamps**: Word-level timestamps in the UI table ("🎯 Word-Level Timestamps" tab) and metrics (WPM, segment timing) remain intact for on-screen inspection, but do not produce separate export files.
3. **Burn-in Module Removal**: `video_to_subtitle/burn_in.py` is removed entirely. `check_ffmpeg()` and `extract_audio()` in `video_to_subtitle/engine.py` are preserved because ffmpeg is required to extract 16kHz WAV audio for Whisper transcription.
4. **CLI Interface**: In `video_to_subtitle/cli.py`, both `--burn-in` and `--format` flags are removed. Running the CLI creates only `<basename>.srt`.
5. **Web UI Inspector & Downloads**:
   - The "🎬 Subtitle Burn-In Studio" tab, video player, and styling controls are deleted.
   - The "💾 Subtitle Export & Inspector" tab is simplified: a single "📥 Download Subtitle (.SRT)" button replaces the multi-button grid and zip download. The code inspector directly displays the generated `.srt` text without format selection radio buttons.
6. **State & Event Handlers**:
   - `run_transcription` return signature is updated to return only the active components (removing unused download buttons, burn status, etc.).
   - `clear_all_inputs` return signature is updated in lockstep.
7. **Cache & Temp Files**:
   - Session temp patterns in `cache_manager.py` are cleaned to remove burn-in patterns (`subtitles_burn_*`, `video_burn_*`), retaining upload and export directories.

---

## Project Structure
```
video_to_subtitle/
├── app.py                     # Web Studio UI: remove Burn-In tab, simplify Export tab to single SRT download & direct SRT preview
├── README.md                  # Update documentation: remove burn-in & non-SRT formats
├── pyproject.toml             # Project config & pytest settings
├── video_to_subtitle/
│   ├── __init__.py
│   ├── burn_in.py             # REMOVED entirely
│   ├── cache_manager.py       # Clean up temporary directory pattern list
│   ├── cli.py                 # CLI interface: remove --burn-in and --format flags; output only .srt
│   ├── engine.py              # Core transcription and ffmpeg audio extraction (unchanged)
│   ├── formatters.py          # Retain only format_timestamp_srt, to_srt, export_srt, resolve_output_directory
│   └── platform_utils.py      # Retain is_gradio_temp_path
├── tests/
│   ├── test_cache_manager.py  # Cache management tests
│   ├── test_formatters.py     # Subtitle formatting tests (update: test only SRT formatters)
│   ├── test_output_paths.py   # Output resolution & app/CLI tests (update: test only SRT generation & updated UI output count)
│   └── test_platform_utils.py # Platform utility tests
└── docs/specs/
    └── remove-burn-in-and-non-srt-export.md
```

---

## Code Style

### Formatting Function (`video_to_subtitle/formatters.py`)
```python
def export_srt(
    segments: List[SegmentTiming],
    output_dir: str,
    base_name: str,
) -> str:
    """Export standard SubRip (.srt) subtitle file and return its absolute path."""
    os.makedirs(output_dir, exist_ok=True)
    srt_path = os.path.join(output_dir, f"{base_name}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(to_srt(segments, word_level=False))
    return srt_path
```

### Clean Gradio Event Flow (`app.py`)
```python
# Simplified download and preview outputs in run_transcription:
return (
    metrics_html,
    full_transcript_text,
    segment_df,
    word_df,
    gr.DownloadButton(value=srt_path, interactive=True),
    gr.Code(value=srt_content, language="markdown"),
    state_data,
)
```

---

## Testing Strategy
1. **Unit Tests (`tests/test_formatters.py`)**:
   - Verify `format_timestamp_srt` correctly handles millisecond boundaries.
   - Verify `to_srt` produces compliant SubRip files from Whisper segment timings.
   - Remove deprecated tests for `to_vtt`, `to_ass_karaoke`, `to_json`.
2. **Integration & Path Tests (`tests/test_output_paths.py`)**:
   - Verify CLI creates only `<basename>.srt` in the output/video directory.
   - Verify `app.py` `run_transcription` generates only `.srt` (no extra files, no `.zip`).
   - Verify `run_transcription` and `clear_all_inputs` output counts match UI component definitions.
3. **Regression Tests**:
   - Ensure `tests/test_cache_manager.py` and `tests/test_platform_utils.py` continue to pass without error.
   - Run `pytest` to guarantee all tests pass.

---

## Boundaries
- **Always do:**
  - Preserve core Whisper transcription and ffmpeg audio extraction (`engine.py`).
  - Keep word-level timeline and transcript tables in the Web UI for visual inspection.
  - Run `pytest` before completing any phase.
  - Keep UI layout clean, responsive, and free of broken layout hooks.
- **Ask first:**
  - Modifying faster-whisper model parameters or model caching logic.
  - Adding new dependencies.
- **Never do:**
  - Remove ffmpeg audio extraction (required by faster-whisper to process video files).
  - Leave dead imports or dangling UI event bindings.
  - Commit untested changes.

---

## Success Criteria
- [ ] `video_to_subtitle/burn_in.py` is deleted.
- [ ] Non-SRT formatting functions (`to_vtt`, `format_timestamp_vtt`, `to_ass_karaoke`, `format_timestamp_ass`, `to_json`) and zip bundle generation are removed.
- [ ] CLI (`video_to_subtitle/cli.py`) has `--burn-in` and `--format` removed; runs by creating only `.srt`.
- [ ] Web UI (`app.py`):
  - "🎬 Subtitle Burn-In Studio" tab is removed.
  - Header feature pills and onboarding empty state no longer mention burn-in or multi-format export.
  - "💾 Subtitle Export & Inspector" tab is streamlined to a single `.srt` download button and direct `.srt` preview without format dropdown/radios.
- [ ] `tests/test_formatters.py` and `tests/test_output_paths.py` are updated and clean.
- [ ] All unit tests pass (`pytest` exits with 0).
- [ ] Documentation (`README.md`) reflects the simplified SRT-only and burn-in-free architecture.

---

## Implementation Plan

### 1. Major Components & Dependencies
- **Core Formatters (`video_to_subtitle/formatters.py`)**:
  - Remove `format_timestamp_vtt`, `format_timestamp_ass`, `to_vtt`, `to_ass_karaoke`, `to_json`.
  - Replace `export_all_formats` with `export_srt(segments, output_dir, base_name) -> str`.
  - Retain `format_timestamp_srt`, `to_srt`, and `resolve_output_directory`.
- **Burn-In Subsystem (`video_to_subtitle/burn_in.py`)**:
  - Delete `video_to_subtitle/burn_in.py` completely.
- **CLI (`video_to_subtitle/cli.py`)**:
  - Remove `--burn-in` and `--format` arguments and logic.
  - Call `export_srt` to generate `<basename>.srt`.
- **Cache Management (`video_to_subtitle/cache_manager.py`)**:
  - Remove `subtitles_burn_*` and `video_burn_*` patterns from `get_temp_directories()`.
- **Web UI (`app.py`)**:
  - Remove burn-in imports, `STYLE_PRESETS`, `create_zip_bundle`, `run_burn_in`, and `update_code_inspector`.
  - Remove "🎬 Subtitle Burn-In Studio" tab and all associated controls/event handlers.
  - Simplify "💾 Subtitle Export & Inspector" tab: single "📥 Download Subtitle (.SRT)" button and direct `.srt` preview in the code inspector.
  - Update `run_transcription` outputs to 7 elements: `(metrics_html, full_transcript_text, segment_df, word_df, srt_download, code_viewer, state_data)`.
  - Update `clear_all_inputs` outputs to 9 elements: `(input_video, output_dir_input, summary_output, full_transcript_box, segment_table, word_table, srt_download, code_viewer, state_data)`.
- **Test Suites (`tests/`)**:
  - `tests/test_formatters.py`: Update unit tests to verify only SRT formatting.
  - `tests/test_output_paths.py`: Update integration tests for `export_srt`, CLI execution, and matching output element counts (7 for `run_transcription`, 9 for `clear_all_inputs`).
- **Documentation (`README.md`)**:
  - Update README: remove burn-in features, CLI flags, and non-SRT formats.

### 2. Implementation Order
1. Formatters refactor (`video_to_subtitle/formatters.py`)
2. Burn-in removal (`video_to_subtitle/burn_in.py` and `cache_manager.py`)
3. CLI simplification (`video_to_subtitle/cli.py`)
4. Web UI refactor (`app.py`)
5. Test suite updates (`tests/test_formatters.py`, `tests/test_output_paths.py`)
6. Documentation update (`README.md`)
7. Full suite verification via `pytest`

### 3. Risks & Mitigations
- **Gradio Output Mismatch**: Gradio raises runtime exceptions if event handler outputs don't match the component list.
  - *Mitigation*: Strictly synchronize the output lists in `transcribe_btn.click` and `clear_btn.click` with the return statements, and verify with automated tests in `test_output_paths.py`.
- **Audio Extraction Preservation**: `ffmpeg` is used for audio extraction in `engine.py`.
  - *Mitigation*: Keep `engine.py` intact and ensure audio extraction tests pass.

---

## Tasks

- [x] Task 1: Refactor `video_to_subtitle/formatters.py`
  - Acceptance: Non-SRT formatting functions (`to_vtt`, `to_ass_karaoke`, `to_json`) removed; `export_srt` introduced and returns path to `.srt`.
  - Verify: Unit test in `tests/test_formatters.py` passes.
  - Files: `video_to_subtitle/formatters.py`

- [x] Task 2: Delete `video_to_subtitle/burn_in.py` and clean `video_to_subtitle/cache_manager.py`
  - Acceptance: `burn_in.py` deleted; `cache_manager.py` temp directory patterns no longer include burn-in prefixes.
  - Verify: `test_cache_manager.py` passes.
  - Files: `video_to_subtitle/burn_in.py`, `video_to_subtitle/cache_manager.py`

- [x] Task 3: Simplify CLI in `video_to_subtitle/cli.py`
  - Acceptance: `--burn-in` and `--format` flags removed; CLI creates only `<basename>.srt`.
  - Verify: Run `python -m video_to_subtitle.cli --help` and verify options.
  - Files: `video_to_subtitle/cli.py`

- [x] Task 4: Refactor Web Studio UI in `app.py`
  - Acceptance: Burn-In tab and handlers removed; Export tab simplified to single SRT download and direct code viewer; `run_transcription` returns 7 outputs; `clear_all_inputs` returns 9 outputs.
  - Verify: Python syntax and import check passes: `python -c "import app; print(app.build_app())"`.
  - Files: `app.py`

- [x] Task 5: Update Test Suites
  - Acceptance: `test_formatters.py` and `test_output_paths.py` updated to reflect SRT-only export and updated output counts.
  - Verify: `pytest` passes with 100% success.
  - Files: `tests/test_formatters.py`, `tests/test_output_paths.py`

- [x] Task 6: Update Documentation
  - Acceptance: `README.md` updated to remove burn-in features and document SRT-only export.
  - Verify: Review `README.md`.
  - Files: `README.md`

---

## Open Questions
- None identified; all requirements are concrete and bounded.
