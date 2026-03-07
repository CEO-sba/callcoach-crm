"""
CallCoach CRM - Transcription Service

Supports two modes:
1. Local transcription using faster-whisper (offline, no API costs)
2. Fallback to simple file-based processing

For production, you can swap in AssemblyAI, Deepgram, or Google Speech-to-Text.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import faster-whisper; fall back gracefully
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    logger.warning("faster-whisper not installed. Install with: pip install faster-whisper")

_model = None


def get_whisper_model(model_size: str = "base"):
    """Lazy-load the Whisper model."""
    global _model
    if _model is None and WHISPER_AVAILABLE:
        logger.info(f"Loading Whisper model: {model_size}")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


async def transcribe_audio(file_path: str, model_size: str = "base") -> dict:
    """
    Transcribe an audio file to text with timestamps.

    Returns:
    {
        "text": "full transcription text",
        "segments": [{"start": 0.0, "end": 2.5, "text": "Hello...", "speaker": "unknown"}],
        "duration": 120.5,
        "language": "en"
    }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    if WHISPER_AVAILABLE:
        return await _transcribe_with_whisper(file_path, model_size)
    else:
        logger.warning("Whisper not available. Returning placeholder.")
        return {
            "text": "[Transcription requires faster-whisper. Install: pip install faster-whisper]",
            "segments": [],
            "duration": 0,
            "language": "en"
        }


async def _transcribe_with_whisper(file_path: str, model_size: str) -> dict:
    """Transcribe using faster-whisper."""
    model = get_whisper_model(model_size)
    if model is None:
        return {"text": "Model failed to load", "segments": [], "duration": 0, "language": "en"}

    try:
        segments_gen, info = model.transcribe(
            file_path,
            beam_size=5,
            language=None,  # Auto-detect
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=300
            )
        )

        segments = []
        full_text_parts = []
        total_duration = 0

        for segment in segments_gen:
            seg_data = {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip(),
                "speaker": "unknown"  # Speaker diarization can be added later
            }
            segments.append(seg_data)
            full_text_parts.append(segment.text.strip())
            total_duration = max(total_duration, segment.end)

        return {
            "text": " ".join(full_text_parts),
            "segments": segments,
            "duration": round(total_duration, 2),
            "language": info.language if info else "en"
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise


async def transcribe_chunk(audio_data: bytes, model_size: str = "base") -> dict:
    """
    Transcribe a small audio chunk for live coaching.
    Used with WebSocket streaming.
    """
    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        result = await _transcribe_with_whisper(tmp_path, model_size)
        return result

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def get_transcription_status() -> dict:
    """Check if transcription service is available."""
    return {
        "whisper_available": WHISPER_AVAILABLE,
        "model_loaded": _model is not None,
        "supported_formats": [".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".mp4"]
    }
