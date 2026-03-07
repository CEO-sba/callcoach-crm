"""
CallCoach CRM - Configuration
"""
import os
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Database
_default_db = str(DATA_DIR / "callcoach.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")

# Auth - SECRET_KEY MUST be set as a Railway env var to persist across deploys.
# If not set, a random key is generated (but sessions will break on redeploy).
_secret = os.getenv("SECRET_KEY", "")
if not _secret or _secret == "change-this-in-production-to-a-random-secret":
    _secret = secrets.token_hex(32)
    logging.getLogger(__name__).warning(
        "SECRET_KEY not set in environment. Using a random key. "
        "Set SECRET_KEY in Railway env vars to keep logins persistent across deploys."
    )
SECRET_KEY = _secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Transcription
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large-v3
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Free tier: get key from console.groq.com

# App
APP_NAME = "CallCoach CRM"
APP_VERSION = "1.0.0"
MAX_UPLOAD_SIZE_MB = 500
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".mp4"}
