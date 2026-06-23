CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    module TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    tool_name TEXT NOT NULL DEFAULT '',
    capability TEXT NOT NULL DEFAULT '',
    source_ref JSONB NOT NULL DEFAULT '{}',
    target_ref JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_module_created
    ON audit_events (module, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_request_created
    ON audit_events (request_id, created_at DESC)
    WHERE request_id <> '';

CREATE INDEX IF NOT EXISTS idx_audit_events_type_created
    ON audit_events (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_source_ref
    ON audit_events USING GIN (source_ref);

CREATE INDEX IF NOT EXISTS idx_audit_events_target_ref
    ON audit_events USING GIN (target_ref);
