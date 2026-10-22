#!/usr/bin/env bash
set -euo pipefail

ROOT="${SECOND_BRAIN_S3_LOCAL_ROOT:-${SECOND_BRAIN_MINIO_LOCAL_ROOT:-/private/tmp/cortex-secondbrain-s3}}"
BUCKET="${SECOND_BRAIN_S3_BUCKET:-${SECOND_BRAIN_MINIO_BUCKET:-obsidian}}"
KEY="${SECOND_BRAIN_S3_OBJECT_KEY:-${SECOND_BRAIN_MINIO_OBJECT_KEY:-second-brain/wiki/local-s3-action.md}}"
TOKEN="${CORTEX_N8N_API_KEY:-local-dev-token}"
GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:18080}"

mkdir -p "${ROOT}/${BUCKET}/$(dirname "${KEY}")"
cat > "${ROOT}/${BUCKET}/${KEY}" <<'MARKDOWN'
---
type: wiki
title: "Local S3 Action"
tags: [second-brain, sync, local-s3]
---

# Local S3 Action

This note simulates an Obsidian sync object written to an S3-compatible bucket.
MARKDOWN

echo "Wrote local S3 object: ${ROOT}/${BUCKET}/${KEY}"
echo "Use these env vars for the Python AI service:"
echo "  SECOND_BRAIN_S3_LOCAL_ROOT=${ROOT}"
echo "  SECOND_BRAIN_S3_BUCKET=${BUCKET}"
echo "  SECOND_BRAIN_S3_PREFIX=second-brain/"

curl -sS -X POST "${GATEWAY_URL}/api/webhooks/n8n/secondbrain/obsidian-sync" \
  -H "Content-Type: application/json" \
  -H "X-Cortex-N8n-Token: ${TOKEN}" \
  -d "{\"bucket\":\"${BUCKET}\",\"object_key\":\"${KEY}\",\"event_id\":\"local-s3-action\",\"owner_id\":\"owner\"}"

echo
