from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
from typing import Protocol


class ObjectStore(Protocol):
    def get_text_object(self, bucket: str, object_key: str) -> str:
        ...


@dataclass(frozen=True)
class LocalS3ObjectStore:
    """Filesystem-backed S3/MinIO simulation for local development and tests."""

    root: Path

    @classmethod
    def from_env(cls) -> "LocalS3ObjectStore | None":
        root = os.getenv("SECOND_BRAIN_MINIO_LOCAL_ROOT")
        if not root:
            return None
        return cls(Path(root))

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
