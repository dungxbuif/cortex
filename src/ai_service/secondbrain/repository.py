from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from ai_service.core.config import AIServiceSettings
from ai_service.core.migrations import apply_migrations
from ai_service.core.models import CaptureStatus
from ai_service.core.repository import (
    PsqlRepositoryBase,
    jsonb_literal,
    sql_bool,
    sql_literal,
    sql_nullable,
    vector_literal,
)
from ai_service.secondbrain.models import Capture, IngestionJob, SyncStatus, VaultChunk, VaultDocument


class SqliteSecondBrainRepository:
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
            CREATE TABLE IF NOT EXISTS secondbrain_captures (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              status TEXT NOT NULL,
              source TEXT NOT NULL,
              raw_text TEXT NOT NULL,
              normalized_markdown TEXT NOT NULL,
              suggested_tags TEXT NOT NULL,
              vault_path TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS secondbrain_documents (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              vault_path TEXT NOT NULL,
              checksum TEXT NOT NULL,
              document_type TEXT NOT NULL,
              title TEXT NOT NULL,
              frontmatter TEXT NOT NULL,
              rag_allowed INTEGER NOT NULL,
              private INTEGER NOT NULL,
              archived INTEGER NOT NULL,
              index_status TEXT NOT NULL,
              indexed_at TEXT NOT NULL,
              UNIQUE(owner_id, vault_path)
            );

            CREATE TABLE IF NOT EXISTS secondbrain_document_chunks (
              id TEXT PRIMARY KEY,
              document_id TEXT NOT NULL,
              owner_id TEXT NOT NULL,
              vault_path TEXT NOT NULL,
              chunk_index INTEGER NOT NULL,
              content TEXT NOT NULL,
              heading_chain TEXT NOT NULL,
              token_count INTEGER NOT NULL,
              embedding TEXT NOT NULL,
              FOREIGN KEY(document_id) REFERENCES secondbrain_documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS secondbrain_ingestion_jobs (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              bucket TEXT NOT NULL,
              object_key TEXT NOT NULL,
              event_type TEXT NOT NULL,
              status TEXT NOT NULL,
              attempts INTEGER NOT NULL,
              message TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            """
        )
        self.conn.commit()

    def save_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        self.conn.execute(
            """
            INSERT INTO secondbrain_ingestion_jobs (
              id, owner_id, bucket, object_key, event_type, status,
              attempts, message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.owner_id,
                job.bucket,
                job.object_key,
                job.event_type,
                job.status,
                job.attempts,
                job.message,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
            ),
        )
        self.conn.commit()
        return job

    def get_ingestion_job(self, owner_id: str, job_id: str) -> IngestionJob | None:
        row = self.conn.execute(
            """
            SELECT * FROM secondbrain_ingestion_jobs
            WHERE owner_id = ? AND id = ?
            """,
            (owner_id, job_id),
        ).fetchone()
        return self._ingestion_job_from_row(row) if row else None

    def update_ingestion_job_status(
        self,
        owner_id: str,
        job_id: str,
        status: str,
        message: str,
        attempts: int,
    ) -> IngestionJob:
        self.conn.execute(
            """
            UPDATE secondbrain_ingestion_jobs
            SET status = ?, message = ?, attempts = ?, updated_at = ?
            WHERE owner_id = ? AND id = ?
            """,
            (status, message, attempts, datetime.now(UTC).isoformat(), owner_id, job_id),
        )
        self.conn.commit()
        job = self.get_ingestion_job(owner_id, job_id)
        if job is None:
            raise KeyError(f"ingestion job not found: {job_id}")
        return job

    def save_capture(self, capture: Capture) -> Capture:
        self.conn.execute(
            """
            INSERT INTO secondbrain_captures (
              id, owner_id, status, source, raw_text, normalized_markdown,
              suggested_tags, vault_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capture.id,
                capture.owner_id,
                capture.status,
                capture.source,
                capture.raw_text,
                capture.normalized_markdown,
                json.dumps(list(capture.suggested_tags)),
                capture.vault_path,
                capture.created_at.isoformat(),
                capture.updated_at.isoformat(),
            ),
        )
        self.conn.commit()
        return capture

    def list_captures(self, owner_id: str) -> list[Capture]:
        rows = self.conn.execute(
            "SELECT * FROM secondbrain_captures WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        ).fetchall()
        return [self._capture_from_row(row) for row in rows]

    def get_capture(self, owner_id: str, capture_id: str) -> Capture | None:
        row = self.conn.execute(
            "SELECT * FROM secondbrain_captures WHERE owner_id = ? AND id = ?",
            (owner_id, capture_id),
        ).fetchone()
        return self._capture_from_row(row) if row else None

    def update_capture_status(
        self,
        owner_id: str,
        capture_id: str,
        status: CaptureStatus,
        updated_at: datetime,
        vault_path: str | None = None,
    ) -> Capture:
        self.conn.execute(
            """
            UPDATE secondbrain_captures
            SET status = ?, updated_at = ?, vault_path = COALESCE(?, vault_path)
            WHERE owner_id = ? AND id = ?
            """,
            (status, updated_at.isoformat(), vault_path, owner_id, capture_id),
        )
        self.conn.commit()
        capture = self.get_capture(owner_id, capture_id)
        if capture is None:
            raise KeyError(f"capture not found: {capture_id}")
        return capture

    def get_document(self, owner_id: str, vault_path: str) -> VaultDocument | None:
        row = self.conn.execute(
            """
            SELECT
              id AS d_id, owner_id AS d_owner_id, vault_path AS d_vault_path,
              checksum AS d_checksum, document_type AS d_document_type,
              title AS d_title, frontmatter AS d_frontmatter,
              rag_allowed AS d_rag_allowed, private AS d_private,
              archived AS d_archived, index_status AS d_index_status,
              indexed_at AS d_indexed_at
            FROM secondbrain_documents
            WHERE owner_id = ? AND vault_path = ?
            """,
            (owner_id, vault_path),
        ).fetchone()
        return self._document_from_join_row(row) if row else None

    def list_document_paths(self, owner_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT vault_path FROM secondbrain_documents WHERE owner_id = ?",
            (owner_id,),
        ).fetchall()
        return [str(row["vault_path"]) for row in rows]

    def upsert_document_with_chunks(self, document: VaultDocument, chunks: list[VaultChunk]) -> None:
        self.conn.execute(
            """
            INSERT INTO secondbrain_documents (
              id, owner_id, vault_path, checksum, document_type, title,
              frontmatter, rag_allowed, private, archived, index_status, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              checksum = excluded.checksum,
              document_type = excluded.document_type,
              title = excluded.title,
              frontmatter = excluded.frontmatter,
              rag_allowed = excluded.rag_allowed,
              private = excluded.private,
              archived = excluded.archived,
              index_status = excluded.index_status,
              indexed_at = excluded.indexed_at
            """,
            (
                document.id,
                document.owner_id,
                document.vault_path,
                document.checksum,
                document.document_type,
                document.title,
                json.dumps(document.frontmatter, sort_keys=True),
                int(document.rag_allowed),
                int(document.private),
                int(document.archived),
                document.index_status,
                document.indexed_at.isoformat(),
            ),
        )
        self.conn.execute("DELETE FROM secondbrain_document_chunks WHERE document_id = ?", (document.id,))
        for chunk in chunks:
            self.conn.execute(
                """
                INSERT INTO secondbrain_document_chunks (
                  id, document_id, owner_id, vault_path, chunk_index, content,
                  heading_chain, token_count, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.owner_id,
                    chunk.vault_path,
                    chunk.chunk_index,
                    chunk.content,
                    json.dumps(list(chunk.heading_chain)),
                    chunk.token_count,
                    json.dumps(list(chunk.embedding)),
                ),
            )
        self.conn.commit()

    def delete_document(self, owner_id: str, vault_path: str) -> bool:
        document = self.get_document(owner_id, vault_path)
        if document is None:
            return False
        self.conn.execute("DELETE FROM secondbrain_document_chunks WHERE document_id = ?", (document.id,))
        self.conn.execute("DELETE FROM secondbrain_documents WHERE id = ?", (document.id,))
        self.conn.commit()
        return True

    def list_searchable_chunks(self, owner_id: str, include_archive: bool = False) -> list[tuple[VaultDocument, VaultChunk]]:
        archive_clause = "" if include_archive else "AND d.archived = 0"
        rows = self.conn.execute(
            f"""
            SELECT
              d.id AS d_id, d.owner_id AS d_owner_id, d.vault_path AS d_vault_path,
              d.checksum AS d_checksum, d.document_type AS d_document_type,
              d.title AS d_title, d.frontmatter AS d_frontmatter,
              d.rag_allowed AS d_rag_allowed, d.private AS d_private,
              d.archived AS d_archived, d.index_status AS d_index_status,
              d.indexed_at AS d_indexed_at,
              c.id AS c_id, c.document_id AS c_document_id, c.owner_id AS c_owner_id,
              c.vault_path AS c_vault_path, c.chunk_index AS c_chunk_index,
              c.content AS c_content, c.heading_chain AS c_heading_chain,
              c.token_count AS c_token_count, c.embedding AS c_embedding
            FROM secondbrain_documents d
            JOIN secondbrain_document_chunks c ON c.document_id = d.id
            WHERE d.owner_id = ?
              AND d.rag_allowed = 1
              AND d.private = 0
              {archive_clause}
            """,
            (owner_id,),
        ).fetchall()
        return [(self._document_from_join_row(row), self._chunk_from_join_row(row)) for row in rows]

    def sync_status(self, owner_id: str) -> SyncStatus:
        row = self.conn.execute(
            """
            SELECT
              COUNT(*) AS total_documents,
              SUM(CASE WHEN index_status = 'indexed' THEN 1 ELSE 0 END) AS indexed_documents,
              SUM(CASE WHEN index_status = 'skipped' THEN 1 ELSE 0 END) AS skipped_documents,
              SUM(CASE WHEN index_status = 'failed' THEN 1 ELSE 0 END) AS failed_documents,
              MAX(indexed_at) AS last_indexed_at
            FROM secondbrain_documents
            WHERE owner_id = ?
            """,
            (owner_id,),
        ).fetchone()
        chunk_row = self.conn.execute(
            "SELECT COUNT(*) AS total_chunks FROM secondbrain_document_chunks WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()
        last_indexed_at = row["last_indexed_at"]
        return SyncStatus(
            owner_id=owner_id,
            total_documents=int(row["total_documents"] or 0),
            indexed_documents=int(row["indexed_documents"] or 0),
            skipped_documents=int(row["skipped_documents"] or 0),
            failed_documents=int(row["failed_documents"] or 0),
            total_chunks=int(chunk_row["total_chunks"] or 0),
            last_indexed_at=datetime.fromisoformat(last_indexed_at) if last_indexed_at else None,
        )

    def _capture_from_row(self, row: sqlite3.Row) -> Capture:
        return Capture(
            id=row["id"],
            owner_id=row["owner_id"],
            status=CaptureStatus(row["status"]),
            source=row["source"],
            raw_text=row["raw_text"],
            normalized_markdown=row["normalized_markdown"],
            suggested_tags=tuple(json.loads(row["suggested_tags"])),
            vault_path=row["vault_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _document_from_join_row(self, row: sqlite3.Row) -> VaultDocument:
        return VaultDocument(
            id=row["d_id"],
            owner_id=row["d_owner_id"],
            vault_path=row["d_vault_path"],
            checksum=row["d_checksum"],
            document_type=row["d_document_type"],
            title=row["d_title"],
            frontmatter=json.loads(row["d_frontmatter"]),
            rag_allowed=bool(row["d_rag_allowed"]),
            private=bool(row["d_private"]),
            archived=bool(row["d_archived"]),
            index_status=row["d_index_status"],
            indexed_at=datetime.fromisoformat(row["d_indexed_at"]),
        )

    def _chunk_from_join_row(self, row: sqlite3.Row) -> VaultChunk:
        return VaultChunk(
            id=row["c_id"],
            document_id=row["c_document_id"],
            owner_id=row["c_owner_id"],
            vault_path=row["c_vault_path"],
            chunk_index=int(row["c_chunk_index"]),
            content=row["c_content"],
            heading_chain=tuple(json.loads(row["c_heading_chain"])),
            token_count=int(row["c_token_count"]),
            embedding=tuple(float(value) for value in json.loads(row["c_embedding"])),
        )

    def _ingestion_job_from_row(self, row: sqlite3.Row) -> IngestionJob:
        return IngestionJob(
            id=row["id"],
            owner_id=row["owner_id"],
            bucket=row["bucket"],
            object_key=row["object_key"],
            event_type=row["event_type"],
            status=row["status"],
            attempts=int(row["attempts"]),
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )



class PostgresPsqlSecondBrainRepository(PsqlRepositoryBase):
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
    def from_env(cls) -> "PostgresPsqlSecondBrainRepository":
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
            DELETE FROM secondbrain_ingestion_jobs WHERE owner_id = {sql_literal(owner_id)};
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

    def save_capture(self, capture: Capture) -> Capture:
        self._execute(
            f"""
            INSERT INTO secondbrain_captures (
              id, owner_id, status, source, raw_text, normalized_markdown,
              suggested_tags, vault_path, created_at, updated_at
            ) VALUES (
              {sql_literal(capture.id)},
              {sql_literal(capture.owner_id)},
              {sql_literal(capture.status)},
              {sql_literal(capture.source)},
              {sql_literal(capture.raw_text)},
              {sql_literal(capture.normalized_markdown)},
              {jsonb_literal(list(capture.suggested_tags))},
              {sql_nullable(capture.vault_path)},
              {sql_literal(capture.created_at.isoformat())}::timestamptz,
              {sql_literal(capture.updated_at.isoformat())}::timestamptz
            );
            """
        )
        return capture

    def save_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        self._execute(
            f"""
            INSERT INTO secondbrain_ingestion_jobs (
              id, owner_id, bucket, object_key, event_type, status,
              attempts, message, created_at, updated_at
            ) VALUES (
              {sql_literal(job.id)},
              {sql_literal(job.owner_id)},
              {sql_literal(job.bucket)},
              {sql_literal(job.object_key)},
              {sql_literal(job.event_type)},
              {sql_literal(job.status)},
              {job.attempts},
              {sql_literal(job.message)},
              {sql_literal(job.created_at.isoformat())}::timestamptz,
              {sql_literal(job.updated_at.isoformat())}::timestamptz
            );
            """
        )
        return job

    def get_ingestion_job(self, owner_id: str, job_id: str) -> IngestionJob | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'bucket', bucket,
              'object_key', object_key,
              'event_type', event_type,
              'status', status,
              'attempts', attempts,
              'message', message,
              'created_at', created_at,
              'updated_at', updated_at
            )
            FROM secondbrain_ingestion_jobs
            WHERE owner_id = {sql_literal(owner_id)}
              AND id = {sql_literal(job_id)};
            """
        )
        return ingestion_job_from_json(rows[0]) if rows else None

    def update_ingestion_job_status(
        self,
        owner_id: str,
        job_id: str,
        status: str,
        message: str,
        attempts: int,
    ) -> IngestionJob:
        self._execute(
            f"""
            UPDATE secondbrain_ingestion_jobs
            SET status = {sql_literal(status)},
                message = {sql_literal(message)},
                attempts = {attempts},
                updated_at = now()
            WHERE owner_id = {sql_literal(owner_id)}
              AND id = {sql_literal(job_id)};
            """
        )
        job = self.get_ingestion_job(owner_id, job_id)
        if job is None:
            raise KeyError(f"ingestion job not found: {job_id}")
        return job

    def list_captures(self, owner_id: str) -> list[Capture]:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'status', status,
              'source', source,
              'raw_text', raw_text,
              'normalized_markdown', normalized_markdown,
              'suggested_tags', suggested_tags,
              'vault_path', vault_path,
              'created_at', created_at,
              'updated_at', updated_at
            )
            FROM secondbrain_captures
            WHERE owner_id = {sql_literal(owner_id)}
            ORDER BY created_at DESC;
            """
        )
        return [capture_from_json(row) for row in rows]

    def get_capture(self, owner_id: str, capture_id: str) -> Capture | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'status', status,
              'source', source,
              'raw_text', raw_text,
              'normalized_markdown', normalized_markdown,
              'suggested_tags', suggested_tags,
              'vault_path', vault_path,
              'created_at', created_at,
              'updated_at', updated_at
            )
            FROM secondbrain_captures
            WHERE owner_id = {sql_literal(owner_id)}
              AND id = {sql_literal(capture_id)};
            """
        )
        return capture_from_json(rows[0]) if rows else None

    def update_capture_status(
        self,
        owner_id: str,
        capture_id: str,
        status: CaptureStatus,
        updated_at: datetime,
        vault_path: str | None = None,
    ) -> Capture:
        self._execute(
            f"""
            UPDATE secondbrain_captures
            SET status = {sql_literal(status)},
                updated_at = {sql_literal(updated_at.isoformat())}::timestamptz,
                vault_path = COALESCE({sql_nullable(vault_path)}, vault_path)
            WHERE owner_id = {sql_literal(owner_id)}
              AND id = {sql_literal(capture_id)};
            """
        )
        capture = self.get_capture(owner_id, capture_id)
        if capture is None:
            raise KeyError(f"capture not found: {capture_id}")
        return capture

    def get_document(self, owner_id: str, vault_path: str) -> VaultDocument | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'vault_path', vault_path,
              'checksum', checksum,
              'document_type', document_type,
              'title', title,
              'frontmatter', frontmatter,
              'rag_allowed', rag_allowed,
              'private', private,
              'archived', archived,
              'index_status', index_status,
              'indexed_at', indexed_at
            )
            FROM secondbrain_documents
            WHERE owner_id = {sql_literal(owner_id)}
              AND vault_path = {sql_literal(vault_path)};
            """
        )
        return document_from_json(rows[0]) if rows else None

    def list_document_paths(self, owner_id: str) -> list[str]:
        return self._query(
            f"""
            SELECT vault_path
            FROM secondbrain_documents
            WHERE owner_id = {sql_literal(owner_id)};
            """
        )

    def upsert_document_with_chunks(self, document: VaultDocument, chunks: list[VaultChunk]) -> None:
        values = [
            "("
            + ", ".join(
                [
                    sql_literal(chunk.id),
                    sql_literal(chunk.document_id),
                    sql_literal(chunk.owner_id),
                    sql_literal(chunk.vault_path),
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
            INSERT INTO secondbrain_document_chunks (
              id, document_id, owner_id, vault_path, chunk_index, content,
              heading_chain, token_count, embedding
            ) VALUES {", ".join(values)}
            ON CONFLICT(id) DO NOTHING;
            """
        self._execute(
            f"""
            INSERT INTO secondbrain_documents (
              id, owner_id, vault_path, checksum, document_type, title,
              frontmatter, rag_allowed, private, archived, index_status, indexed_at
            ) VALUES (
              {sql_literal(document.id)},
              {sql_literal(document.owner_id)},
              {sql_literal(document.vault_path)},
              {sql_literal(document.checksum)},
              {sql_literal(document.document_type)},
              {sql_literal(document.title)},
              {jsonb_literal(document.frontmatter)},
              {sql_bool(document.rag_allowed)},
              {sql_bool(document.private)},
              {sql_bool(document.archived)},
              {sql_literal(document.index_status)},
              {sql_literal(document.indexed_at.isoformat())}::timestamptz
            )
            ON CONFLICT(id) DO UPDATE SET
              checksum = excluded.checksum,
              document_type = excluded.document_type,
              title = excluded.title,
              frontmatter = excluded.frontmatter,
              rag_allowed = excluded.rag_allowed,
              private = excluded.private,
              archived = excluded.archived,
              index_status = excluded.index_status,
              indexed_at = excluded.indexed_at;

            DELETE FROM secondbrain_document_chunks
            WHERE document_id = {sql_literal(document.id)};

            {chunk_insert}
            """
        )

    def delete_document(self, owner_id: str, vault_path: str) -> bool:
        document = self.get_document(owner_id, vault_path)
        if document is None:
            return False
        self._execute(
            f"""
            DELETE FROM secondbrain_document_chunks
            WHERE document_id = {sql_literal(document.id)};

            DELETE FROM secondbrain_documents
            WHERE id = {sql_literal(document.id)};
            """
        )
        return True

    def list_searchable_chunks(self, owner_id: str, include_archive: bool = False) -> list[tuple[VaultDocument, VaultChunk]]:
        archive_clause = "" if include_archive else "AND d.archived = false"
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'document', jsonb_build_object(
                'id', d.id,
                'owner_id', d.owner_id,
                'vault_path', d.vault_path,
                'checksum', d.checksum,
                'document_type', d.document_type,
                'title', d.title,
                'frontmatter', d.frontmatter,
                'rag_allowed', d.rag_allowed,
                'private', d.private,
                'archived', d.archived,
                'index_status', d.index_status,
                'indexed_at', d.indexed_at
              ),
              'chunk', jsonb_build_object(
                'id', c.id,
                'document_id', c.document_id,
                'owner_id', c.owner_id,
                'vault_path', c.vault_path,
                'chunk_index', c.chunk_index,
                'content', c.content,
                'heading_chain', c.heading_chain,
                'token_count', c.token_count,
                'embedding', c.embedding::text
              )
            )
            FROM secondbrain_documents d
            JOIN secondbrain_document_chunks c ON c.document_id = d.id
            WHERE d.owner_id = {sql_literal(owner_id)}
              AND d.rag_allowed = true
              AND d.private = false
              {archive_clause};
            """
        )
        return [(document_from_json(row["document"]), chunk_from_json(row["chunk"])) for row in rows]

    def sync_status(self, owner_id: str) -> SyncStatus:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'owner_id', {sql_literal(owner_id)},
              'total_documents', COUNT(*),
              'indexed_documents', COALESCE(SUM(CASE WHEN index_status = 'indexed' THEN 1 ELSE 0 END), 0),
              'skipped_documents', COALESCE(SUM(CASE WHEN index_status = 'skipped' THEN 1 ELSE 0 END), 0),
              'failed_documents', COALESCE(SUM(CASE WHEN index_status = 'failed' THEN 1 ELSE 0 END), 0),
              'total_chunks', (
                SELECT COUNT(*) FROM secondbrain_document_chunks WHERE owner_id = {sql_literal(owner_id)}
              ),
              'last_indexed_at', MAX(indexed_at)
            )
            FROM secondbrain_documents
            WHERE owner_id = {sql_literal(owner_id)};
            """
        )
        row = rows[0]
        last_indexed_at = row.get("last_indexed_at")
        return SyncStatus(
            owner_id=owner_id,
            total_documents=int(row["total_documents"] or 0),
            indexed_documents=int(row["indexed_documents"] or 0),
            skipped_documents=int(row["skipped_documents"] or 0),
            failed_documents=int(row["failed_documents"] or 0),
            total_chunks=int(row["total_chunks"] or 0),
            last_indexed_at=datetime.fromisoformat(last_indexed_at) if last_indexed_at else None,
        )

def capture_from_json(row: dict[str, Any]) -> Capture:
    return Capture(
        id=row["id"],
        owner_id=row["owner_id"],
        status=CaptureStatus(row["status"]),
        source=row["source"],
        raw_text=row["raw_text"],
        normalized_markdown=row["normalized_markdown"],
        suggested_tags=tuple(row["suggested_tags"]),
        vault_path=row.get("vault_path"),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def document_from_json(row: dict[str, Any]) -> VaultDocument:
    return VaultDocument(
        id=row["id"],
        owner_id=row["owner_id"],
        vault_path=row["vault_path"],
        checksum=row["checksum"],
        document_type=row["document_type"],
        title=row["title"],
        frontmatter=row["frontmatter"],
        rag_allowed=bool(row["rag_allowed"]),
        private=bool(row["private"]),
        archived=bool(row["archived"]),
        index_status=row["index_status"],
        indexed_at=datetime.fromisoformat(row["indexed_at"]),
    )


def chunk_from_json(row: dict[str, Any]) -> VaultChunk:
    raw_embedding = row["embedding"]
    if isinstance(raw_embedding, str):
        embedding = tuple(float(value) for value in json.loads(raw_embedding))
    else:
        embedding = tuple(float(value) for value in raw_embedding)
    return VaultChunk(
        id=row["id"],
        document_id=row["document_id"],
        owner_id=row["owner_id"],
        vault_path=row["vault_path"],
        chunk_index=int(row["chunk_index"]),
        content=row["content"],
        heading_chain=tuple(row["heading_chain"]),
        token_count=int(row["token_count"]),
        embedding=embedding,
    )


def ingestion_job_from_json(row: dict[str, Any]) -> IngestionJob:
    return IngestionJob(
        id=row["id"],
        owner_id=row["owner_id"],
        bucket=row["bucket"],
        object_key=row["object_key"],
        event_type=row["event_type"],
        status=row["status"],
        attempts=int(row["attempts"]),
        message=row["message"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
