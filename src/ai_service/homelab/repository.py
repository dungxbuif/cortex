from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from ai_service.core.config import AIServiceSettings
from ai_service.core.migrations import apply_migrations
from ai_service.core.repository import (
    PsqlRepositoryBase,
    jsonb_literal,
    sql_literal,
    vector_literal,
)
from ai_service.homelab.models import HomelabChunk, HomelabDocument, HomelabSyncStatus


class SqliteHomelabRepository:
    """SQLite repository used for local development and deterministic tests.

    Production can replace this with PostgreSQL/pgvector while preserving service
    semantics and test fixtures.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.conn.close()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """

            CREATE TABLE IF NOT EXISTS homelab_documents (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              repo_url TEXT NOT NULL,
              branch TEXT NOT NULL,
              commit_sha TEXT NOT NULL,
              file_path TEXT NOT NULL,
              checksum TEXT NOT NULL,
              index_status TEXT NOT NULL,
              indexed_at TEXT NOT NULL,
              UNIQUE(owner_id, file_path)
            );

            CREATE TABLE IF NOT EXISTS homelab_document_chunks (
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              owner_id TEXT NOT NULL,
              file_path TEXT NOT NULL,
              chunk_index INTEGER NOT NULL,
              content TEXT NOT NULL,
              heading_chain TEXT NOT NULL,
              token_count INTEGER NOT NULL,
              embedding TEXT NOT NULL,
              FOREIGN KEY(document_id) REFERENCES homelab_documents(id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def get_homelab_document(self, owner_id: str, file_path: str) -> HomelabDocument | None:
        row = self.conn.execute(
            """
            SELECT
              id AS d_id, owner_id AS d_owner_id, repo_url AS d_repo_url,
              branch AS d_branch, commit_sha AS d_commit_sha, file_path AS d_file_path,
              checksum AS d_checksum, index_status AS d_index_status, indexed_at AS d_indexed_at
            FROM homelab_documents
            WHERE owner_id = ? AND file_path = ?
            """,
            (owner_id, file_path),
        ).fetchone()
        return self._homelab_document_from_join_row(row) if row else None

    def list_homelab_document_paths(self, owner_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT file_path FROM homelab_documents WHERE owner_id = ?",
            (owner_id,),
        ).fetchall()
        return [str(row["file_path"]) for row in rows]

    def upsert_homelab_document_with_chunks(self, document: HomelabDocument, chunks: list[HomelabChunk]) -> None:
        self.conn.execute(
            """
            INSERT INTO homelab_documents (
              id, owner_id, repo_url, branch, commit_sha, file_path, checksum,
              index_status, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              repo_url = excluded.repo_url,
              branch = excluded.branch,
              commit_sha = excluded.commit_sha,
              checksum = excluded.checksum,
              index_status = excluded.index_status,
              indexed_at = excluded.indexed_at
            """,
            (
                document.id,
                document.owner_id,
                document.repo_url,
                document.branch,
                document.commit_sha,
                document.file_path,
                document.checksum,
                document.index_status,
                document.indexed_at.isoformat(),
            ),
        )
        self.conn.execute("DELETE FROM homelab_document_chunks WHERE document_id = ?", (document.id,))
        for chunk in chunks:
            self.conn.execute(
                """
                INSERT INTO homelab_document_chunks (
                  id, document_id, owner_id, file_path, chunk_index, content,
                  heading_chain, token_count, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.owner_id,
                    chunk.file_path,
                    chunk.chunk_index,
                    chunk.content,
                    json.dumps(list(chunk.heading_chain)),
                    chunk.token_count,
                    json.dumps(list(chunk.embedding)),
                ),
            )
        self.conn.commit()

    def delete_homelab_document(self, owner_id: str, file_path: str) -> bool:
        document = self.get_homelab_document(owner_id, file_path)
        if document is None:
            return False
        self.conn.execute("DELETE FROM homelab_document_chunks WHERE document_id = ?", (document.id,))
        self.conn.execute("DELETE FROM homelab_documents WHERE id = ?", (document.id,))
        self.conn.commit()
        return True

    def list_searchable_homelab_chunks(self, owner_id: str) -> list[tuple[HomelabDocument, HomelabChunk]]:
        rows = self.conn.execute(
            """
            SELECT
              d.id AS d_id, d.owner_id AS d_owner_id, d.repo_url AS d_repo_url,
              d.branch AS d_branch, d.commit_sha AS d_commit_sha, d.file_path AS d_file_path,
              d.checksum AS d_checksum, d.index_status AS d_index_status, d.indexed_at AS d_indexed_at,
              c.id AS c_id, c.document_id AS c_document_id, c.owner_id AS c_owner_id,
              c.file_path AS c_file_path, c.chunk_index AS c_chunk_index,
              c.content AS c_content, c.heading_chain AS c_heading_chain,
              c.token_count AS c_token_count, c.embedding AS c_embedding
            FROM homelab_documents d
            JOIN homelab_document_chunks c ON c.document_id = d.id
            WHERE d.owner_id = ?
              AND d.index_status = 'indexed'
            """,
            (owner_id,),
        ).fetchall()
        return [(self._homelab_document_from_join_row(row), self._homelab_chunk_from_join_row(row)) for row in rows]

    def sync_homelab_status(self, owner_id: str) -> HomelabSyncStatus:
        row = self.conn.execute(
            """
            SELECT
              COUNT(*) AS total_documents,
              SUM(CASE WHEN index_status = 'indexed' THEN 1 ELSE 0 END) AS indexed_documents,
              SUM(CASE WHEN index_status = 'skipped' THEN 1 ELSE 0 END) AS skipped_documents,
              SUM(CASE WHEN index_status = 'failed' THEN 1 ELSE 0 END) AS failed_documents,
              MAX(indexed_at) AS last_indexed_at
            FROM homelab_documents
            WHERE owner_id = ?
            """,
            (owner_id,),
        ).fetchone()
        chunk_row = self.conn.execute(
            "SELECT COUNT(*) AS total_chunks FROM homelab_document_chunks WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()
        last_indexed_at = row["last_indexed_at"]
        return HomelabSyncStatus(
            owner_id=owner_id,
            total_documents=int(row["total_documents"] or 0),
            indexed_documents=int(row["indexed_documents"] or 0),
            skipped_documents=int(row["skipped_documents"] or 0),
            failed_documents=int(row["failed_documents"] or 0),
            total_chunks=int(chunk_row["total_chunks"] or 0),
            last_indexed_at=datetime.fromisoformat(last_indexed_at) if last_indexed_at else None,
        )

    def _homelab_document_from_join_row(self, row: sqlite3.Row) -> HomelabDocument:
        return HomelabDocument(
            id=row["d_id"],
            owner_id=row["d_owner_id"],
            repo_url=row["d_repo_url"],
            branch=row["d_branch"],
            commit_sha=row["d_commit_sha"],
            file_path=row["d_file_path"],
            checksum=row["d_checksum"],
            index_status=row["d_index_status"],
            indexed_at=datetime.fromisoformat(row["d_indexed_at"]),
        )

    def _homelab_chunk_from_join_row(self, row: sqlite3.Row) -> HomelabChunk:
        return HomelabChunk(
            id=row["c_id"],
            document_id=row["c_document_id"],
            owner_id=row["c_owner_id"],
            file_path=row["c_file_path"],
            chunk_index=int(row["c_chunk_index"]),
            content=row["c_content"],
            heading_chain=tuple(json.loads(row["c_heading_chain"])),
            token_count=int(row["c_token_count"]),
            embedding=tuple(float(value) for value in json.loads(row["c_embedding"])),
        )




class PostgresPsqlHomelabRepository(PsqlRepositoryBase):
    """PostgreSQL repository using local `psql`.

    This keeps integration tests runnable in the current dev environment without
    adding a Python driver dependency. Embeddings are stored with pgvector.
    """

    def __init__(
        self,
        settings: AIServiceSettings | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.settings = settings or AIServiceSettings.from_env()
        postgres = self.settings.postgres
        self.host = host or postgres.host
        self.port = port or postgres.port
        self.database = database or postgres.database
        self.user = user or postgres.user
        self.password = password or postgres.password
        self._create_schema()

    def close(self) -> None:
        return None

    @classmethod
    def from_env(cls) -> "PostgresPsqlHomelabRepository":
        return cls(settings=AIServiceSettings.from_env())

    def ping(self) -> bool:
        try:
            self._query("SELECT 1;")
        except RuntimeError:
            return False
        return True

    def clear_owner(self, owner_id: str) -> None:
        self._execute(
            f"""
            DELETE FROM secondbrain_document_chunks WHERE owner_id = {sql_literal(owner_id)};
            DELETE FROM secondbrain_documents WHERE owner_id = {sql_literal(owner_id)};
            DELETE FROM secondbrain_captures WHERE owner_id = {sql_literal(owner_id)};
            """
        )

    def embedding_column_type(self) -> str:
        rows = self._query(
            """
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name = 'secondbrain_document_chunks'
              AND column_name = 'embedding';
            """
        )
        return rows[0] if rows else ""

    def _create_schema(self) -> None:
        apply_migrations(self, self.settings.migrations_path)

    def execute(self, sql: str) -> None:
        self._execute(sql)

    def query(self, sql: str) -> list[str]:
        return self._query(sql)

    def get_homelab_document(self, owner_id: str, file_path: str) -> HomelabDocument | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'repo_url', repo_url,
              'branch', branch,
              'commit_sha', commit_sha,
              'file_path', file_path,
              'checksum', checksum,
              'index_status', index_status,
              'indexed_at', indexed_at
            )
            FROM homelab_documents
            WHERE owner_id = {sql_literal(owner_id)}
              AND file_path = {sql_literal(file_path)};
            """
        )
        return homelab_document_from_json(rows[0]) if rows else None

    def list_homelab_document_paths(self, owner_id: str) -> list[str]:
        return self._query(
            f"""
            SELECT file_path
            FROM homelab_documents
            WHERE owner_id = {sql_literal(owner_id)};
            """
        )

    def upsert_homelab_document_with_chunks(self, document: HomelabDocument, chunks: list[HomelabChunk]) -> None:
        values = [
            "("
            + ", ".join(
                [
                    sql_literal(chunk.id),
                    sql_literal(chunk.document_id),
                    sql_literal(chunk.owner_id),
                    sql_literal(chunk.file_path),
                    str(chunk.chunk_index),
                    sql_literal(chunk.content),
                    jsonb_literal(list(chunk.heading_chain)),
                    str(chunk.token_count),
                    vector_literal(chunk.embedding),
                ]
            )
            + ")"
            for chunk in chunks
        ]
        chunk_insert = ""
        if values:
            chunk_insert = f"""
            INSERT INTO homelab_document_chunks (
              id, document_id, owner_id, file_path, chunk_index, content,
              heading_chain, token_count, embedding
            ) VALUES {", ".join(values)}
            ON CONFLICT(id) DO NOTHING;
            """
        self._execute(
            f"""
            INSERT INTO homelab_documents (
              id, owner_id, repo_url, branch, commit_sha, file_path, checksum,
              index_status, indexed_at
            ) VALUES (
              {sql_literal(document.id)},
              {sql_literal(document.owner_id)},
              {sql_literal(document.repo_url)},
              {sql_literal(document.branch)},
              {sql_literal(document.commit_sha)},
              {sql_literal(document.file_path)},
              {sql_literal(document.checksum)},
              {sql_literal(document.index_status)},
              {sql_literal(document.indexed_at.isoformat())}::timestamptz
            )
            ON CONFLICT(id) DO UPDATE SET
              repo_url = excluded.repo_url,
              branch = excluded.branch,
              commit_sha = excluded.commit_sha,
              checksum = excluded.checksum,
              index_status = excluded.index_status,
              indexed_at = excluded.indexed_at;

            DELETE FROM homelab_document_chunks
            WHERE document_id = {sql_literal(document.id)};

            {chunk_insert}
            """
        )

    def delete_homelab_document(self, owner_id: str, file_path: str) -> bool:
        document = self.get_homelab_document(owner_id, file_path)
        if document is None:
            return False
        self._execute(
            f"""
            DELETE FROM homelab_document_chunks
            WHERE document_id = {sql_literal(document.id)};

            DELETE FROM homelab_documents
            WHERE id = {sql_literal(document.id)};
            """
        )
        return True

    def list_searchable_homelab_chunks(self, owner_id: str) -> list[tuple[HomelabDocument, HomelabChunk]]:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
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
              AND d.index_status = 'indexed';
            """
        )
        return [(homelab_document_from_json(row["document"]), homelab_chunk_from_json(row["chunk"])) for row in rows]

    def sync_homelab_status(self, owner_id: str) -> HomelabSyncStatus:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'owner_id', {sql_literal(owner_id)},
              'total_documents', COUNT(*),
              'indexed_documents', COALESCE(SUM(CASE WHEN index_status = 'indexed' THEN 1 ELSE 0 END), 0),
              'skipped_documents', COALESCE(SUM(CASE WHEN index_status = 'skipped' THEN 1 ELSE 0 END), 0),
              'failed_documents', COALESCE(SUM(CASE WHEN index_status = 'failed' THEN 1 ELSE 0 END), 0),
              'total_chunks', (
                SELECT COUNT(*) FROM homelab_document_chunks WHERE owner_id = {sql_literal(owner_id)}
              ),
              'last_indexed_at', MAX(indexed_at)
            )
            FROM homelab_documents
            WHERE owner_id = {sql_literal(owner_id)};
            """
        )
        row = rows[0]
        last_indexed_at = row.get("last_indexed_at")
        return HomelabSyncStatus(
            owner_id=owner_id,
            total_documents=int(row["total_documents"] or 0),
            indexed_documents=int(row["indexed_documents"] or 0),
            skipped_documents=int(row["skipped_documents"] or 0),
            failed_documents=int(row["failed_documents"] or 0),
            total_chunks=int(row["total_chunks"] or 0),
            last_indexed_at=datetime.fromisoformat(last_indexed_at) if last_indexed_at else None,
        )

    def clear_homelab_owner(self, owner_id: str) -> None:
        self._execute(
            f"""
            DELETE FROM homelab_document_chunks WHERE owner_id = {sql_literal(owner_id)};
            DELETE FROM homelab_documents WHERE owner_id = {sql_literal(owner_id)};
            """
        )

def homelab_document_from_json(row: dict[str, Any]) -> HomelabDocument:
    return HomelabDocument(
        id=row["id"],
        owner_id=row["owner_id"],
        repo_url=row["repo_url"],
        branch=row["branch"],
        commit_sha=row["commit_sha"],
        file_path=row["file_path"],
        checksum=row["checksum"],
        index_status=row["index_status"],
        indexed_at=datetime.fromisoformat(row["indexed_at"]),
    )


def homelab_chunk_from_json(row: dict[str, Any]) -> HomelabChunk:
    raw_embedding = row["embedding"]
    if isinstance(raw_embedding, str):
        embedding = tuple(float(value) for value in json.loads(raw_embedding))
    else:
        embedding = tuple(float(value) for value in raw_embedding)
    return HomelabChunk(
        id=row["id"],
        document_id=row["document_id"],
        owner_id=row["owner_id"],
        file_path=row["file_path"],
        chunk_index=int(row["chunk_index"]),
        content=row["content"],
        heading_chain=tuple(row["heading_chain"]),
        token_count=int(row["token_count"]),
        embedding=embedding,
    )
