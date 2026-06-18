from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
class HomelabRawChunk:
    id: str
    document_id: str
    owner_id: str
    file_path: str
    chunk_index: int
    content: str
    heading_chain: tuple[str, ...]
    token_count: int


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
