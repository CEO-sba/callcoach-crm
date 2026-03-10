"""
CallCoach CRM - Transcription Service

Priority order:
1. Groq Whisper API (cloud, free tier, fast) - recommended for production
2. Local faster-whisper (offline, no API costs) - for local development
3. Placeholder fallback
"""
import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import faster-whisper; fall back gracefully
WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    logger.info("faster-whisper not installed. Will use Groq cloud transcription if GROQ_API_KEY is set.")

_model = None


def get_whisper_model(model_size: str = "base"):
    """Lazy-load the Whisper model."""
    global _model
    if _model is None and WHISPER_AVAILABLE:
        logger.info(f"Loading Whisper model: {model_size}")
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


def _convert_to_wav(file_path: str) -> str:
    """Convert audio to WAV format using ffmpeg for Groq API compatibility."""
    input_path = Path(file_path)
    wav_path = input_path.with_suffix(".wav")

    if input_path.suffix.lower() == ".wav":
        return file_path

    try:
        result = subprocess.run(
            ["ffmpeg", "-i", str(input_path), "-ar", "16000", "-ac", "1",
             "-y", str(wav_path)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and wav_path.exists():
            logger.info(f"Converted {input_path.name} to WAV: {wav_path.stat().st_size} bytes")
            return str(wav_path)
        else:
            logger.error(f"ffmpeg conversion failed: {result.stderr}")
            return file_path
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return file_path


async def _transcribe_with_groq(file_path: str) -> dict:
    """Transcribe using Groq's Whisper API (free tier, very fast)."""
    from app.config import GROQ_API_KEY
    import httpx

    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set. Cannot use cloud transcription.")
        return None

    # Convert to WAV for best compatibility
    wav_path = _convert_to_wav(file_path)
    audio_path = Path(wav_path)

    # Check file size (Groq limit is 25MB)
    file_size = audio_path.stat().st_size
    if file_size > 25 * 1024 * 1024:
        logger.warning(f"File too large for Groq API ({file_size} bytes). Max is 25MB.")
        return None

    logger.info(f"Sending {audio_path.name} ({file_size} bytes) to Groq Whisper API...")

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            with open(str(audio_path), "rb") as f:
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files={"file": (audio_path.name, f, "audio/wav")},
                    data={
                        "model": "whisper-large-v3",
                        "response_format": "verbose_json",
                        "language": "en",
                        "temperature": 0.0,
                    },
                )

        if response.status_code != 200:
            logger.error(f"Groq API error {response.status_code}: {response.text}")
            return None

        data = response.json()
        text = data.get("text", "")
        duration = data.get("duration", 0)

        # Parse segments if available
        segments = []
        for seg in data.get("segments", []):
            segments.append({
                "start": round(seg.get("start", 0), 2),
                "end": round(seg.get("end", 0), 2),
                "text": seg.get("text", "").strip(),
                "speaker": "unknown"
            })

        logger.info(f"Groq transcription complete: {len(text)} chars, {duration:.1f}s duration")

        # Clean up temp WAV if we created one
        if wav_path != file_path and Path(wav_path).exists():
            try:
                os.unlink(wav_path)
            except Exception:
                pass

        return {
            "text": text,
            "segments": segments,
            "duration": round(duration, 2),
            "language": data.get("language", "en")
        }

    except Exception as e:
        logger.error(f"Groq transcription failed: {e}")
        # Clean up temp WAV
        if wav_path != file_path and Path(wav_path).exists():
            try:
                os.unlink(wav_path)
            except Exception:
                pass
        return None


async def transcribe_audio(file_path: str, model_size: str = "base") -> dict:
    """
    Transcribe an audio file to text with timestamps.

    Priority: Groq Cloud > Local Whisper > Placeholder

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

    # Try Groq cloud first (works in production without heavy dependencies)
    from app.config import GROQ_API_KEY
    if GROQ_API_KEY:
        result = await _transcribe_with_groq(file_path)
        if result and result.get("text"):
            return result
        logger.warning("Groq transcription returned empty. Falling back...")

    # Try local Whisper
    if WHISPER_AVAILABLE:
        return await _transcribe_with_whisper(file_path, model_size)

    # Final fallback
    logger.warning("No transcription method available. Set GROQ_API_KEY or install faster-whisper.")
    return {
        "text": "[No transcription available. Set GROQ_API_KEY in .env for cloud transcription.]",
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
                "speaker": "unknown"
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
    from app.config import GROQ_API_KEY
    return {
        "whisper_available": WHISPER_AVAILABLE,
        "groq_available": bool(GROQ_API_KEY),
        "model_loaded": _model is not None,
        "supported_formats": [".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".mp4"]
    }
