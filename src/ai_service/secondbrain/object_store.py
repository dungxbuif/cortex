from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
from typing import Protocol
import urllib.parse
import urllib.request


class ObjectStore(Protocol):
    def get_text_object(self, bucket: str, object_key: str) -> str:
        ...


@dataclass(frozen=True)
class LocalS3ObjectStore:
    """Filesystem-backed S3-compatible simulation for local development and tests."""

    root: Path

    @classmethod
    def from_env(cls) -> ObjectStore | None:
        endpoint = _env("SECOND_BRAIN_S3_ENDPOINT", "SECOND_BRAIN_MINIO_ENDPOINT")
        access_key = _env("SECOND_BRAIN_S3_ACCESS_KEY", "SECOND_BRAIN_MINIO_ACCESS_KEY")
        secret_key = _env("SECOND_BRAIN_S3_SECRET_KEY", "SECOND_BRAIN_MINIO_SECRET_KEY")

        if endpoint and access_key and secret_key:
            region = _env("SECOND_BRAIN_S3_REGION", "SECOND_BRAIN_MINIO_REGION") or "us-east-1"
            return HttpS3ObjectStore(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                region=region,
            )

        local_root = _env("SECOND_BRAIN_S3_LOCAL_ROOT", "SECOND_BRAIN_MINIO_LOCAL_ROOT")
        if not local_root:
            return None
        return cls(Path(local_root))

    def get_text_object(self, bucket: str, object_key: str) -> str:
        if not bucket or not bucket.strip():
            raise ValueError("bucket is required")
        normalized_key = normalize_object_key(object_key)
        bucket_root = (self.root / bucket).resolve()
        object_path = (bucket_root / normalized_key).resolve()
        if not _is_relative_to(object_path, bucket_root):
            raise ValueError("object_key escapes bucket root")
        if not object_path.is_file():
            raise FileNotFoundError(f"object not found: {bucket}/{normalized_key}")
        return object_path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class HttpS3ObjectStore:
    """Network HTTP-based S3-compatible object store wrapper using standard libraries."""

    endpoint: str
    access_key: str
    secret_key: str
    region: str = "us-east-1"

    def get_text_object(self, bucket: str, object_key: str) -> str:
        normalized_key = normalize_object_key(object_key)
        return s3_get_object(
            endpoint=self.endpoint,
            bucket=bucket,
            object_key=normalized_key,
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region,
        )


def sign(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = sign(("AWS4" + key).encode("utf-8"), date_stamp.encode("utf-8"))
    k_region = sign(k_date, region_name.encode("utf-8"))
    k_service = sign(k_region, service_name.encode("utf-8"))
    k_signing = sign(k_service, b"aws4_request")
    return k_signing


def s3_get_object(
    endpoint: str,
    bucket: str,
    object_key: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
) -> str:
    method = "GET"
    service = "s3"

    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    scheme = parsed.scheme or "https"

    # S3 path-style URL construction
    url = f"{scheme}://{host}/{bucket}/{object_key}"
    canonical_uri = f"/{bucket}/{object_key}"

    # Current datetime
    t = datetime.datetime.utcnow()
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

    # Header parameters
    canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(b"").hexdigest()

    # AWS SigV4 Canonical Request
    canonical_request = (
        f"{method}\n"
        f"{canonical_uri}\n"
        f"\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    # AWS SigV4 String to Sign
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical_request}"
    )

    # Calculate Signature
    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # Set headers
    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    req = urllib.request.Request(url)
    req.add_header("x-amz-date", amz_date)
    req.add_header("x-amz-content-sha256", payload_hash)
    req.add_header("Authorization", authorization_header)

    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode("utf-8")


HttpMinIOObjectStore = HttpS3ObjectStore


def normalize_object_key(object_key: str) -> str:
    if not object_key or not object_key.strip():
        raise ValueError("object_key is required")
    key = object_key.strip().replace("\\", "/").lstrip("/")
    parts = PurePosixPath(key).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("object_key must not contain traversal segments")
    return str(PurePosixPath(*parts))


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _env(primary: str, fallback: str) -> str | None:
    return os.getenv(primary) or os.getenv(fallback)
