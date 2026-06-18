#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:18080}"

curl -fsS "${GATEWAY_URL}/health" >/dev/null
echo "Go gateway health: ok"

curl -fsS "${GATEWAY_URL}/api/ai/health" >/dev/null
echo "Go -> Python AI gRPC health: ok"
