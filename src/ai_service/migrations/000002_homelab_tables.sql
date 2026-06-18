CREATE TABLE IF NOT EXISTS homelab_documents (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  repo_url TEXT NOT NULL,
  branch TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  file_path TEXT NOT NULL,
  checksum TEXT NOT NULL,
  index_status TEXT NOT NULL,
  indexed_at TIMESTAMPTZ NOT NULL,
  UNIQUE(owner_id, file_path)
);

CREATE TABLE IF NOT EXISTS homelab_document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES homelab_documents(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  heading_chain JSONB NOT NULL,
  token_count INTEGER NOT NULL,
  embedding VECTOR(768) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_homelab_documents_owner_path
  ON homelab_documents(owner_id, file_path);

CREATE INDEX IF NOT EXISTS idx_homelab_chunks_owner_document
  ON homelab_document_chunks(owner_id, document_id);

CREATE INDEX IF NOT EXISTS idx_homelab_chunks_embedding_hnsw
  ON homelab_document_chunks
  USING hnsw (embedding vector_cosine_ops);
