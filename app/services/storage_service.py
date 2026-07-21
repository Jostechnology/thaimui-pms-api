import io
import base64
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

from app.exception import NotFoundError, OuterServicesError

_client: Minio = None
_bucket: str = None

PRESIGNED_URL_TTL = 3600       # 1 hour — presigned URL lifetime
PRESIGNED_CACHE_TTL = 3300     # 55 min  — Redis TTL (slightly less than URL lifetime)


def init_storage(endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
    global _client, _bucket
    _client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
    _bucket = bucket
    if not _client.bucket_exists(_bucket):
        _client.make_bucket(_bucket)


def _require_client():
    if _client is None:
        raise OuterServicesError("Storage service is not initialised")


def decode_data_url(data_url):
    """Parse a base64 data URL into (bytes, content_type). Raises ValidationError on bad format."""
    from app.exception import ValidationError
    if not data_url or not data_url.startswith("data:"):
        raise ValidationError("รูปภาพต้องเป็น base64 data URL (data:<type>;base64,...)")
    try:
        header, encoded = data_url.split(",", 1)
        content_type = header.split(";")[0][5:]  # strip "data:"
        return base64.b64decode(encoded), content_type
    except Exception:
        raise ValidationError("รูปแบบ base64 data URL ไม่ถูกต้อง")


def upload_image(file_bytes: bytes, object_key: str, content_type: str = "image/jpeg") -> str:
    """Upload bytes to MinIO. Returns object_key — store this in the DB."""
    _require_client()
    try:
        _client.put_object(
            _bucket,
            object_key,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        return object_key
    except S3Error as e:
        raise OuterServicesError(f"Failed to upload image: {e}")


def upload_object(file_bytes: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    """Generic byte upload to MinIO (reports, exports). Returns object_key."""
    _require_client()
    try:
        _client.put_object(
            _bucket,
            object_key,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        return object_key
    except S3Error as e:
        raise OuterServicesError(f"Failed to upload object: {e}")


def get_presigned_url(object_key: str, expires_seconds: int = PRESIGNED_URL_TTL) -> str:
    """
    Generate a presigned GET URL valid for `expires_seconds`.

    Callers that cache this URL in Redis should use PRESIGNED_CACHE_TTL as the
    Redis TTL so the cached URL is always still valid when served.

    Example Redis pattern (once Redis is wired up):
        cached = redis.get(object_key)
        if cached:
            return cached
        url = get_presigned_url(object_key)
        redis.setex(object_key, PRESIGNED_CACHE_TTL, url)
        return url
    """
    _require_client()
    try:
        return _client.presigned_get_object(
            _bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )
    except S3Error as e:
        raise OuterServicesError(f"Failed to generate presigned URL: {e}")


def get_as_base64(object_key: str) -> str:
    """
    Stream object from MinIO into memory and return raw base64 string.
    No disk I/O. Use this when sending images to document-generator.

    For an <img> tag in a Jinja template use:
        data:image/jpeg;base64,{{ image_b64 }}
    """
    _require_client()
    response = None
    try:
        response = _client.get_object(_bucket, object_key)
        data = response.read()
        return base64.b64encode(data).decode("utf-8")
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject"):
            raise NotFoundError(f"Image not found: {object_key}")
        raise OuterServicesError(f"Failed to get image: {e}")
    finally:
        if response:
            response.close()
            response.release_conn()


def delete_image(object_key: str) -> None:
    _require_client()
    try:
        _client.remove_object(_bucket, object_key)
    except S3Error as e:
        raise OuterServicesError(f"Failed to delete image: {e}")


def check_exists(object_key: str) -> bool:
    _require_client()
    try:
        _client.stat_object(_bucket, object_key)
        return True
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject"):
            return False
        raise OuterServicesError(f"Failed to check image existence: {e}")
