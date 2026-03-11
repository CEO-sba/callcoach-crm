"""
CallCoach CRM - Cloud Storage Service (Cloudflare R2)

S3-compatible object storage for persistent call recordings.
Falls back to local disk when R2 is not configured (dev mode).
"""
import logging
import io
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import (
    R2_ENDPOINT_URL,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    UPLOAD_DIR,
    is_r2_configured,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# R2 / S3 client  (lazy-initialized)
# ---------------------------------------------------------------------------
_s3_client = None


def _get_s3_client():
    """Get or create the S3-compatible client for R2."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
            region_name="auto",
        )
    return _s3_client


def _ensure_bucket():
    """Create the bucket if it does not exist yet."""
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=R2_BUCKET_NAME)
    except ClientError:
        try:
            client.create_bucket(Bucket=R2_BUCKET_NAME)
            logger.info("Created R2 bucket: %s", R2_BUCKET_NAME)
        except ClientError as e:
            logger.error("Failed to create R2 bucket: %s", e)
            raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_recording(
    file_content: bytes,
    clinic_id: str,
    call_id: str,
    extension: str,
    content_type: str = "audio/webm",
) -> str:
    """
    Upload a call recording and return the storage path/URL.

    When R2 is configured  -> uploads to R2, returns the object key.
    When R2 is NOT configured -> saves to local disk, returns file path.
    """
    if is_r2_configured():
        return _upload_to_r2(file_content, clinic_id, call_id, extension, content_type)
    else:
        return _save_to_disk(file_content, clinic_id, call_id, extension)


def get_recording_url(recording_path: str) -> Optional[str]:
    """
    Get a download URL for a recording.

    R2 paths (start with 'r2://') -> generate presigned URL (valid 1 hour).
    Local paths -> return None (caller uses FileResponse).
    """
    if not recording_path:
        return None

    if recording_path.startswith("r2://"):
        object_key = recording_path[5:]  # strip 'r2://'
        return _generate_presigned_url(object_key)

    return None  # local file, use FileResponse


def download_recording(recording_path: str) -> Optional[bytes]:
    """
    Download recording bytes (used by transcription service).

    R2 paths -> download from R2.
    Local paths -> read from disk.
    """
    if not recording_path:
        return None

    if recording_path.startswith("r2://"):
        object_key = recording_path[5:]
        return _download_from_r2(object_key)

    # Local file
    local_path = Path(recording_path)
    if local_path.exists():
        return local_path.read_bytes()
    return None


def get_local_path_for_transcription(recording_path: str) -> str:
    """
    Ensure the recording is available as a local file for transcription.

    R2 files are downloaded to a temp location.
    Local files are returned as-is.
    """
    if not recording_path or not recording_path.startswith("r2://"):
        return recording_path

    # Download from R2 to temp location
    import tempfile
    object_key = recording_path[5:]
    ext = Path(object_key).suffix
    content = _download_from_r2(object_key)
    if content is None:
        raise FileNotFoundError(f"Recording not found in R2: {object_key}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(content)
    tmp.close()
    logger.info("Downloaded R2 recording to temp file: %s", tmp.name)
    return tmp.name


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _upload_to_r2(
    content: bytes,
    clinic_id: str,
    call_id: str,
    extension: str,
    content_type: str,
) -> str:
    """Upload to Cloudflare R2 and return 'r2://<key>' path."""
    _ensure_bucket()
    client = _get_s3_client()

    object_key = f"recordings/{clinic_id}/{call_id}{extension}"

    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=object_key,
        Body=content,
        ContentType=content_type,
    )
    logger.info("Uploaded recording to R2: %s (%d bytes)", object_key, len(content))

    return f"r2://{object_key}"


def _save_to_disk(
    content: bytes,
    clinic_id: str,
    call_id: str,
    extension: str,
) -> str:
    """Save to local disk (dev fallback) and return file path."""
    call_dir = UPLOAD_DIR / clinic_id
    call_dir.mkdir(parents=True, exist_ok=True)
    file_path = call_dir / f"{call_id}{extension}"
    file_path.write_bytes(content)
    logger.info("Saved recording to disk: %s (%d bytes)", file_path, len(content))
    return str(file_path)


def _generate_presigned_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL (default 1 hour)."""
    # If a public R2.dev URL is set, use it directly (no signing needed)
    if R2_PUBLIC_URL:
        base = R2_PUBLIC_URL.rstrip("/")
        return f"{base}/{object_key}"

    client = _get_s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_BUCKET_NAME, "Key": object_key},
        ExpiresIn=expires_in,
    )
    return url


def _download_from_r2(object_key: str) -> Optional[bytes]:
    """Download an object from R2."""
    client = _get_s3_client()
    try:
        resp = client.get_object(Bucket=R2_BUCKET_NAME, Key=object_key)
        return resp["Body"].read()
    except ClientError as e:
        logger.error("Failed to download from R2: %s - %s", object_key, e)
        return None
