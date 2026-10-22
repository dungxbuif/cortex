from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ai_service.core.ports import Embedder, HomelabRepository
from ai_service.core.repository import sql_literal, vector_literal
from ai_service.core.vector import cosine_similarity
from ai_service.core.models import utc_now
from ai_service.homelab.link_validator import EXCLUDE_FILES, EXCLUDE_FOLDERS, gfm_slugify, validate_markdown_links
from ai_service.homelab.markdown import chunk_homelab_markdown
from ai_service.homelab.models import HomelabChunk, HomelabDocument, HomelabRawChunk, HomelabSearchResult
from ai_service.homelab.redaction import checksum_text, redact_secrets, verify_signature


class HomelabService:
    def __init__(self, repository: HomelabRepository, embedder: Embedder | None = None, ai_client: Embedder | None = None) -> None:
        self.repository = repository
        self.embedder = embedder or ai_client or _default_embedder()

    def sync_repository(
        self,
        repo_path: str,
        repo_url: str = "github.com/dungxbuif/Homelab",
        branch: str = "main",
        commit_sha: str = "latest",
        owner_id: str = "homelab",
        delete_missing: bool = False,
    ) -> dict[str, int | str]:
        path = Path(repo_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")

        processed_files = 0
        skipped_files = 0
        failed_files = 0
        deleted_files = 0
        present_files: set[str] = set()

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]
            for file in files:
                if not file.endswith(".md") or file in EXCLUDE_FILES:
                    continue
                abs_file_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(abs_file_path, repo_path)
                present_files.add(rel_file_path)

                try:
                    with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_content = f.read()

                    checksum = checksum_text(raw_content)
                    existing = self.repository.get_homelab_document(owner_id, rel_file_path)
                    if existing and existing.checksum == checksum:
                        skipped_files += 1
                        continue

                    redacted = redact_secrets(raw_content)
                    doc_id = checksum_text(f"{owner_id}:{rel_file_path}")
                    document = HomelabDocument(
                        id=doc_id,
                        owner_id=owner_id,
                        repo_url=repo_url,
                        branch=branch,
                        commit_sha=commit_sha,
                        file_path=rel_file_path,
                        checksum=checksum,
                        index_status="indexed",
                        indexed_at=utc_now(),
                    )

                    raw_chunks = chunk_homelab_markdown(owner_id, document, redacted)
                    self.repository.upsert_homelab_document_with_chunks(document, _attach_embeddings(raw_chunks, self.embedder))
                    processed_files += 1
                except Exception:
                    failed_files += 1

        if delete_missing:
            for stale_path in sorted(set(self.repository.list_homelab_document_paths(owner_id)) - present_files):
                if self.repository.delete_homelab_document(owner_id, stale_path):
                    deleted_files += 1

        return {
            "status": "success",
            "processed_files": processed_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
            "deleted_files": deleted_files,
        }

    def search_knowledge(self, query: str, owner_id: str = "homelab", top_k: int = 5) -> list[HomelabSearchResult]:
        if not query.strip():
            return []

        query_vector = self.embedder.embed_text(query)
        if hasattr(self.repository, "conn"):
            scored: list[tuple[float, HomelabDocument, HomelabChunk]] = []
            for doc, chunk in self.repository.list_searchable_homelab_chunks(owner_id):
                scored.append((cosine_similarity(query_vector, chunk.embedding), doc, chunk))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [HomelabSearchResult(chunk=chunk, document=doc, score=score) for score, doc, chunk in scored[:top_k]]

        rows = self.repository._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'score', 1 - (c.embedding <=> {vector_literal(query_vector)}),
              'document', jsonb_build_object(
                'id', d.id,
                'owner_id', d.owner_id,
                'repo_url', d.repo_url,
                'branch', d.branch,
                'commit_sha', d.commit_sha,
                'file_path', d.file_path,
                'checksum', d.checksum,
                'index_status', d.index_status,
                'indexed_at', d.indexed_at
              ),
              'chunk', jsonb_build_object(
                'id', c.id,
                'document_id', c.document_id,
                'owner_id', c.owner_id,
                'file_path', c.file_path,
                'chunk_index', c.chunk_index,
                'content', c.content,
                'heading_chain', c.heading_chain,
                'token_count', c.token_count,
                'embedding', c.embedding::text
              )
            )
            FROM homelab_documents d
            JOIN homelab_document_chunks c ON c.document_id = d.id
            WHERE d.owner_id = {sql_literal(owner_id)}
              AND d.index_status = 'indexed'
            ORDER BY c.embedding <=> {vector_literal(query_vector)}
            LIMIT {top_k};
            """
        )
        from ai_service.homelab.repository import homelab_chunk_from_json, homelab_document_from_json

        return [
            HomelabSearchResult(
                chunk=homelab_chunk_from_json(row["chunk"]),
                document=homelab_document_from_json(row["document"]),
                score=float(row["score"]),
            )
            for row in rows
        ]

    def get_sync_status(self, owner_id: str = "homelab"):
        return self.repository.sync_homelab_status(owner_id)

    def validate_markdown_links(self, repo_path: str) -> list[dict[str, Any]]:
        return validate_markdown_links(repo_path)


def _attach_embeddings(raw_chunks: list[HomelabRawChunk], embedder: Embedder) -> list[HomelabChunk]:
    vectors = embedder.embed_batch([chunk.content for chunk in raw_chunks]) if raw_chunks else []
    return [
        HomelabChunk(
            id=chunk.id,
            document_id=chunk.document_id,
            owner_id=chunk.owner_id,
            file_path=chunk.file_path,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            heading_chain=chunk.heading_chain,
            token_count=chunk.token_count,
            embedding=vector,
        )
        for chunk, vector in zip(raw_chunks, vectors, strict=True)
    ]


def _default_embedder() -> Embedder:
    from ai_service.providers.embedding import default_embedder

    return default_embedder()


__all__ = [
    "HomelabService",
    "checksum_text",
    "gfm_slugify",
    "redact_secrets",
    "validate_markdown_links",
    "verify_signature",
]
