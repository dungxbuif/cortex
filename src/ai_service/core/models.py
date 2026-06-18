from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum


DEFAULT_OWNER_ID = "owner"


class CaptureStatus(StrEnum):
    CAPTURED = "captured"
    COPIED = "copied"
    EXPORTED = "exported"
    DISCARDED = "discarded"


class IndexStatus(StrEnum):
    INDEXED = "indexed"
    SKIPPED = "skipped"
    FAILED = "failed"
    DELETED = "deleted"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)
