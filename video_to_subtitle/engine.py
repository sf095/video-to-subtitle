"""Core transcription engine using faster-whisper with word-level timestamps."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Optional, Tuple

from faster_whisper import WhisperModel

_CACHED_MODELS: Dict[str, WhisperModel] = {}


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class SegmentTiming:
    id: int
    start: float
    end: float
    text: str
    words: List[WordTiming]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "words": [asdict(w) for w in self.words],
        }


def check_ffmpeg() -> str:
    """Verify ffmpeg is installed and return its executable path."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError(
            "ffmpeg was not found in your PATH. Please install ffmpeg to extract audio from video."
        )
    return ffmpeg_path


def extract_audio(video_path: str, output_audio_path: Optional[str] = None) -> str:
    """Extract audio from video file to 16kHz mono WAV format."""
    check_ffmpeg()
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    if output_audio_path is None:
        temp_dir = tempfile.mkdtemp(prefix="whisper_audio_")
        output_audio_path = os.path.join(temp_dir, "extracted_audio.wav")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_audio_path,
    ]

    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to extract audio: {process.stderr}")

    return output_audio_path


def is_model_cached(model_size: str) -> bool:
    """Check if the specified Whisper model is already downloaded locally."""
    try:
        from faster_whisper.utils import download_model
        download_model(model_size, local_files_only=True)
        return True
    except Exception:
        return False


def get_whisper_model(
    model_size: str = "medium",
    device: str = "auto",
    compute_type: str = "default",
) -> WhisperModel:
    """Load or retrieve a cached WhisperModel instance."""
    cache_key = f"{model_size}_{device}_{compute_type}"
    if cache_key not in _CACHED_MODELS:
        try:
            _CACHED_MODELS[cache_key] = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
        except Exception as e:
            err_msg = str(e)
            if "LocalEntryNotFoundError" in type(e).__name__ or "Cannot find the requested files" in err_msg or "offline" in err_msg.lower():
                raise RuntimeError(
                    f"Whisper model '{model_size}' is not downloaded locally, and downloading failed (offline or network error). "
                    f"Please connect to the internet to download it on first use."
                ) from e
            raise
    return _CACHED_MODELS[cache_key]


def evict_model_from_cache(model_size: Optional[str] = None) -> int:
    """
    Evict loaded WhisperModel instances from in-memory cache and run garbage collection.
    
    Args:
        model_size: Specific model size to evict (e.g. 'medium'), or None to evict all.
        
    Returns:
        Number of evicted model instances.
    """
    import gc
    global _CACHED_MODELS
    evicted = 0
    if model_size is None:
        evicted = len(_CACHED_MODELS)
        _CACHED_MODELS.clear()
    else:
        prefix = f"{model_size}_"
        keys_to_remove = [k for k in _CACHED_MODELS if k.startswith(prefix)]
        for k in keys_to_remove:
            del _CACHED_MODELS[k]
            evicted += 1
    gc.collect()
    return evicted



def transcribe(
    media_path: str,
    model_size: str = "medium",
    device: str = "auto",
    compute_type: str = "default",
    language: Optional[str] = None,
    vad_filter: bool = True,
    initial_prompt: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[List[SegmentTiming], dict]:
    """
    Transcribe a video or audio file with word-level timestamps.

    Args:
        media_path: Path to the input video or audio file.
        model_size: Whisper model size (tiny, base, small, medium, large-v3). Default is 'medium'.
        device: Device to run on ('auto', 'cpu', 'cuda').
        compute_type: Quantization / compute type ('default', 'int8', 'float16').
        language: Language code (e.g., 'en', 'vi', 'es') or None for auto-detection.
        vad_filter: Whether to apply Silero VAD to suppress silence hallucinations.
        initial_prompt: Optional prompt to provide vocabulary context, acronyms, or proper nouns.
        progress_callback: Optional callback receiving (progress_ratio, status_message).

    Returns:
        Tuple of (segments: List[SegmentTiming], info_dict: dict).
    """
    if progress_callback:
        progress_callback(0.05, "Extracting audio with ffmpeg...")

    audio_path = extract_audio(media_path)

    try:
        is_cached = is_model_cached(model_size)
        if progress_callback:
            if is_cached:
                progress_callback(0.2, f"Loading cached Whisper model '{model_size}'...")
            else:
                progress_callback(0.2, f"Downloading Whisper model '{model_size}' from HuggingFace (first time only)...")

        model = get_whisper_model(model_size, device=device, compute_type=compute_type)

        if progress_callback:
            progress_callback(0.35, "Running transcription with word-level timestamps...")

        segments_gen, info = model.transcribe(
            audio_path,
            word_timestamps=True,
            language=language,
            vad_filter=vad_filter,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=initial_prompt,
        )

        total_duration = info.duration if info.duration and info.duration > 0 else 1.0
        segments: List[SegmentTiming] = []

        for seg in segments_gen:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append(
                        WordTiming(
                            word=w.word,
                            start=round(w.start, 3),
                            end=round(w.end, 3),
                            probability=round(w.probability, 4),
                        )
                    )
            segments.append(
                SegmentTiming(
                    id=seg.id,
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=seg.text.strip(),
                    words=words,
                )
            )

            if progress_callback:
                current_progress = min(0.95, 0.35 + 0.60 * (seg.end / total_duration))
                progress_callback(
                    current_progress,
                    f"Transcribing: {seg.end:.1f}s / {total_duration:.1f}s...",
                )

        info_dict = {
            "language": info.language,
            "language_probability": round(info.language_probability, 4) if info.language_probability else 1.0,
            "duration": round(info.duration, 2) if info.duration else 0.0,
            "model_size": model_size,
        }

        if progress_callback:
            progress_callback(1.0, "Transcription complete!")

        return segments, info_dict

    finally:
        # Clean up temporary extracted audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                parent = os.path.dirname(audio_path)
                if "whisper_audio_" in parent and os.path.exists(parent):
                    os.rmdir(parent)
            except Exception:
                pass
