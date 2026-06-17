from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


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


@dataclass(frozen=True)
class Capture:
    id: str
    owner_id: str
    status: CaptureStatus
    source: str
    raw_text: str
    normalized_markdown: str
    suggested_tags: tuple[str, ...]
    vault_path: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class VaultDocument:
    id: str
    owner_id: str
    vault_path: str
    checksum: str
    document_type: str
    title: str
    frontmatter: dict[str, Any]
    rag_allowed: bool
    private: bool
    archived: bool
    index_status: IndexStatus
    indexed_at: datetime


@dataclass(frozen=True)
class VaultChunk:
    id: str
    document_id: str
    owner_id: str
    vault_path: str
    chunk_index: int
    content: str
    heading_chain: tuple[str, ...]
    token_count: int
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class SearchResult:
    chunk: VaultChunk
    document: VaultDocument
    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SyncStatus:
    owner_id: str
    total_documents: int
    indexed_documents: int
    skipped_documents: int
    failed_documents: int
    total_chunks: int
    last_indexed_at: datetime | None


@dataclass(frozen=True)
class HomelabDocument:
    id: str
    owner_id: str
    repo_url: str
    branch: str
    commit_sha: str
    file_path: str
    checksum: str
    index_status: str
    indexed_at: datetime


@dataclass(frozen=True)
class HomelabChunk:
    id: str
    document_id: str
    owner_id: str
    file_path: str
    chunk_index: int
    content: str
    heading_chain: tuple[str, ...]
    token_count: int
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class HomelabSearchResult:
    chunk: HomelabChunk
    document: HomelabDocument
    score: float


@dataclass(frozen=True)
class HomelabSyncStatus:
    owner_id: str
    total_documents: int
    indexed_documents: int
    skipped_documents: int
    failed_documents: int
    total_chunks: int
    last_indexed_at: datetime | None


