CREATE TABLE IF NOT EXISTS secondbrain_ingestion_jobs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  bucket TEXT NOT NULL,
  object_key TEXT NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_secondbrain_ingestion_jobs_owner_status
  ON secondbrain_ingestion_jobs(owner_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_secondbrain_ingestion_jobs_object
  ON secondbrain_ingestion_jobs(bucket, object_key, event_type);
