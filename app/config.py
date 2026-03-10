"""
CallCoach CRM - Configuration
"""
import os
import secrets
import logging
from pathlib import Path
from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

# Load .env file
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Database  (PostgreSQL on Hostinger Cloud)
# ---------------------------------------------------------------------------
_raw_db_url = os.getenv("DATABASE_URL", "")
if _raw_db_url:
    # Normalize postgres:// to postgresql:// for SQLAlchemy 2.x
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = _raw_db_url
else:
    # Fallback to local SQLite for development
    _default_db = str(DATA_DIR / "callcoach.db")
    DATABASE_URL = f"sqlite:///{_default_db}"
    _logger.warning(
        "DATABASE_URL not set. Using local SQLite at %s. "
        "Set DATABASE_URL to a PostgreSQL connection string for production.",
        _default_db,
    )

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
_secret = os.getenv("SECRET_KEY", "")
if not _secret or _secret == "change-this-in-production-to-a-random-secret":
    _secret = secrets.token_hex(32)
    _logger.warning(
        "SECRET_KEY not set in environment. Using a random key. "
        "Set SECRET_KEY in .env to keep logins persistent across deploys."
    )
SECRET_KEY = _secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large-v3
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # Free tier: get key from console.groq.com

# ---------------------------------------------------------------------------
# Cloudflare R2 Storage  (S3-compatible, for persistent call recordings)
# ---------------------------------------------------------------------------
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "callcoach-recordings")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # Optional: custom domain or R2.dev URL

# Derived endpoint for boto3
R2_ENDPOINT_URL = (
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""
)

def is_r2_configured() -> bool:
    """Check if R2 credentials are set."""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
APP_NAME = "CallCoach CRM"
APP_VERSION = "1.1.0"
MAX_UPLOAD_SIZE_MB = 500
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".mp4"}
