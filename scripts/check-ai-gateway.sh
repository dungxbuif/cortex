#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:18080}"

curl -fsS "${GATEWAY_URL}/health" >/dev/null
echo "AI Gateway health: ok"

curl -fsS "${GATEWAY_URL}/api/ai/health" >/dev/null
echo "AI Service internal health: ok"
