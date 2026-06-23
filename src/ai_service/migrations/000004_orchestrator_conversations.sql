CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  channel_ref TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (owner_id, channel, channel_ref)
);

CREATE TABLE IF NOT EXISTS conversation_messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  tool_calls JSONB,
  tool_result JSONB,
  message_token_count INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_recent
  ON conversation_messages (conversation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS pending_confirmations (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL,
  channel TEXT NOT NULL,
  channel_ref TEXT NOT NULL,
  channel_user_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  tool_args JSONB NOT NULL,
  tool_args_hash TEXT NOT NULL,
  policy_decision JSONB NOT NULL,
  audit_event_id TEXT,
  prompt_shown TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pending_confirmations_active
  ON pending_confirmations (conversation_id, status, expires_at);

CREATE INDEX IF NOT EXISTS idx_pending_confirmations_actor
  ON pending_confirmations (channel, channel_ref, channel_user_id, status);
