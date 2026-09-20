# Spec: In-App Cache Management & Automatic Exit Cleanup

## Objective
Provide comprehensive disk and memory cache management for the Video-to-Subtitle Web Studio application. Users will be able to:
1. **Monitor Storage Usage**: Inspect exact disk consumption for both temporary working files (Gradio uploads, exported subtitle bundles, preview burns) and downloaded AI model weights (`faster-whisper` models: tiny, base, small, medium, large-v3).
2. **In-App Cache Control**: Manually purge temporary media files or selectively/fully delete downloaded model weights directly from the Gradio UI without opening a terminal. Dynamic UI updates reflect newly freed space and immediately refresh the `⚡ Cached` badges in the model selector.
3. **Automatic Cleanup on Exit**: Automatically clean up session temporary directories (`subtitles_export_*`, temp video burn renders) and orphaned session temp files when the application process exits, preventing disk bloat over time.

---

## Tech Stack
- **Language**: Python 3.10+
- **Frameworks & Libraries**: Gradio 4+/6+, Faster-Whisper, Hugging Face Hub cache standard
- **Testing**: `pytest`

---

## Commands
```bash
# Activate environment
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Launch the Gradio Web UI
python app.py
```

---

## Project Structure
```
video_to_subtitle/
├── app.py                            # Add Storage & Cache UI Accordion, wire event handlers, register exit cleanup
├── video_to_subtitle/
│   ├── cache_manager.py              # NEW: Core storage calculation, selective model removal, temp file purging, exit hooks
│   ├── engine.py                     # Expose eviction function for in-memory model cache (_CACHED_MODELS)
│   ├── platform_utils.py             # Existing temp path detection
│   └── formatters.py                 # Subtitle formatters
├── tests/
│   ├── test_cache_manager.py         # NEW: Unit tests for temp purge, model purge, size calculation, safety boundaries
│   ├── test_output_paths.py          # Ensure UI handlers and export workflows remain unaffected
│   └── test_platform_utils.py        # Platform path utility tests
└── docs/specs/
    └── cache-management-and-cleanup.md
```

---

## Code Style & Architecture

### 1. Dedicated Cache Management Module (`video_to_subtitle/cache_manager.py`)
Encapsulate all path resolution, disk inspection, and deletion logic safely:
- `get_temp_cache_stats() -> Dict[str, Any]`: Computes total size (bytes/MB) and file count of Gradio upload folders and `subtitles_export_*` / `video_burn_*` folders.
- `clear_temp_cache() -> Tuple[int, int]`: Deletes temporary files safely with exception handling for open/locked files. Returns `(bytes_freed, files_removed)`.
- `get_model_cache_stats() -> List[Dict[str, Any]]`: Inspects `~/.cache/huggingface/hub/models--Systran--faster-whisper-*`, reporting model name, size on disk, and total size.
- `clear_model_cache(model_size: Optional[str] = None) -> Tuple[int, List[str]]`: Deletes a specific model (e.g. `"medium"`) or all downloaded whisper models, evicts from in-memory cache in `engine.py`, and returns `(bytes_freed, removed_models)`.
- `register_exit_cleanup()`: Registers `atexit` hook to clean up session temp directories on exit without touching model weights.

### 2. Gradio UI Accordion in `app.py`
Integrated neatly into the left configuration column beneath the settings:
```python
with gr.Accordion("🧹 Storage & Cache Management", open=False):
    storage_info_md = gr.Markdown(value=get_storage_summary_markdown())
    with gr.Row():
        clear_temp_btn = gr.Button("🗑️ Clear Temp Files", variant="secondary", size="sm")
        refresh_storage_btn = gr.Button("🔄 Refresh Stats", variant="ghost", size="sm")
    with gr.Row():
        model_delete_dropdown = gr.Dropdown(
            label="Select Model to Delete",
            choices=get_downloaded_model_choices(),
            value="All Models",
            scale=2,
        )
        delete_model_btn = gr.Button("⚠️ Delete Model Weights", variant="stop", size="sm", scale=1)
    cache_feedback_md = gr.Markdown(value="")
```

### 3. Dynamic Synchronization
When model weights are deleted:
- The UI triggers `get_model_choices()` to immediately refresh the main `Whisper Model` dropdown, removing `⚡ Cached` from the deleted model(s).
- The `Select Model to Delete` dropdown refreshes its choices.
- Storage markdown updates with the newly freed megabytes/gigabytes.

---

## Testing Strategy
1. **Unit Tests (`tests/test_cache_manager.py`)**:
   - `test_get_temp_cache_stats`: Verifies accurate size and file calculation against temporary test fixtures.
   - `test_clear_temp_cache`: Verifies temp files are deleted while safely handling non-existent paths or permissions.
   - `test_get_model_cache_stats`: Verifies parsing of HF cache directory structures.
   - `test_clear_model_cache_specific`: Verifies selective deletion of a specific model folder and RAM cache eviction.
   - `test_clear_model_cache_all`: Verifies complete purge of faster-whisper model folders.
   - `test_exit_cleanup_does_not_delete_models`: Asserts exit hook strictly deletes session temporary directories, never HF models.
2. **Regression Tests**:
   - Run existing test suite (`pytest tests/`) to ensure no breaking changes to transcription or export pipelines.

---

## Boundaries
- **Always**:
  - Safely swallow errors for locked or open files during temp cleanup (do not crash the application or exit handler).
  - Evict cleared models from `engine._CACHED_MODELS` so memory is freed immediately.
  - Require explicit user confirmation / clear UI button intent before deleting model weights.
  - Keep exit cleanup strictly scoped to temporary session directories.
- **Ask First**:
  - If we want to clean Hugging Face hub files outside the `models--Systran--faster-whisper-*` namespace (default is NEVER touch external HF models).
- **Never**:
  - Automatically delete downloaded model weights on application exit.
  - Delete files outside designated temporary directory structures (`/tmp`, `$TMPDIR`, or `$GRADIO_TEMP_DIR`).
  - Leave broken references in the UI model dropdown.

---

## Success Criteria
- [ ] User can view storage stats for temporary files and downloaded Whisper models in the Gradio UI.
- [ ] Clicking "Clear Temp Files" frees up temporary space and updates storage stats in real time.
- [ ] Selecting a model (e.g. "medium") and clicking "Delete Model Weights" deletes the local HF directory, evicts RAM cache, updates storage stats, and updates the `⚡ Cached` indicator in the model dropdown.
- [ ] Closing the app or exiting triggers the registered cleanup hook and removes session-created temp directories.
- [ ] All unit and regression tests pass (`pytest tests/`).
