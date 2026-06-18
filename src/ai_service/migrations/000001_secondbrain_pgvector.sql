CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS secondbrain_captures (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  normalized_markdown TEXT NOT NULL,
  suggested_tags JSONB NOT NULL,
  vault_path TEXT,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS secondbrain_documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  vault_path TEXT NOT NULL,
  checksum TEXT NOT NULL,
  document_type TEXT NOT NULL,
  title TEXT NOT NULL,
  frontmatter JSONB NOT NULL,
  rag_allowed BOOLEAN NOT NULL,
  private BOOLEAN NOT NULL,
  archived BOOLEAN NOT NULL,
  index_status TEXT NOT NULL,
  indexed_at TIMESTAMPTZ NOT NULL,
  UNIQUE(owner_id, vault_path)
);

CREATE TABLE IF NOT EXISTS secondbrain_document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES secondbrain_documents(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL,
  vault_path TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  heading_chain JSONB NOT NULL,
  token_count INTEGER NOT NULL,
  embedding VECTOR(768) NOT NULL
);

DROP INDEX IF EXISTS idx_secondbrain_chunks_embedding_hnsw;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_type t ON t.oid = a.atttypid
    WHERE c.relname = 'secondbrain_document_chunks'
      AND a.attname = 'embedding'
      AND (t.typname <> 'vector' OR a.atttypmod <> 772)
  ) THEN
    DELETE FROM secondbrain_document_chunks;
    ALTER TABLE secondbrain_document_chunks
      ALTER COLUMN embedding TYPE VECTOR(768)
      USING ('[' || repeat('0,', 767) || '0]')::VECTOR(768);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_secondbrain_documents_owner_path
  ON secondbrain_documents(owner_id, vault_path);

CREATE INDEX IF NOT EXISTS idx_secondbrain_documents_policy
  ON secondbrain_documents(owner_id, rag_allowed, private, archived);

CREATE INDEX IF NOT EXISTS idx_secondbrain_chunks_owner_document
  ON secondbrain_document_chunks(owner_id, document_id);

CREATE INDEX IF NOT EXISTS idx_secondbrain_chunks_embedding_hnsw
  ON secondbrain_document_chunks
  USING hnsw (embedding vector_cosine_ops);
