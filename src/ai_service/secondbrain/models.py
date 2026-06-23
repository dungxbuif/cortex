from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ai_service.core.models import CaptureStatus, IndexStatus


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
class RawChunk:
    id: str
    document_id: str
    owner_id: str
    vault_path: str
    chunk_index: int
    content: str
    heading_chain: tuple[str, ...]
    token_count: int


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
class IngestionJob:
    id: str
    owner_id: str
    bucket: str
    object_key: str
    event_type: str
    status: str
    attempts: int
    message: str
    created_at: datetime
    updated_at: datetime
