#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI_GRPC_PORT="${AI_GRPC_PORT:-50051}"
GO_GATEWAY_ADDR="${GO_GATEWAY_ADDR:-:18080}"
DATABASE_URL="${DATABASE_URL:-postgres://dev:password@localhost:5432/cortex?sslmode=disable}"
AI_SERVICE_ADDRESS="${AI_SERVICE_ADDRESS:-127.0.0.1:${AI_GRPC_PORT}}"
GRPC_ENABLE_FORK_SUPPORT="${GRPC_ENABLE_FORK_SUPPORT:-0}"

if [[ -f "${ROOT_DIR}/src/ai_service/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/src/ai_service/.env.local"
  set +a
fi

cleanup() {
  if [[ -n "${PYTHON_GRPC_PID:-}" ]]; then
    kill "${PYTHON_GRPC_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting Python AI gRPC on 127.0.0.1:${AI_GRPC_PORT}"
(
  cd "${ROOT_DIR}"
  PYTHONPATH=src \
    AI_GRPC_PORT="${AI_GRPC_PORT}" \
    GRPC_ENABLE_FORK_SUPPORT="${GRPC_ENABLE_FORK_SUPPORT}" \
    src/ai_service/.venv/bin/python -m ai_service.grpc_server
) &
PYTHON_GRPC_PID="$!"

for _ in $(seq 1 60); do
  if nc -z 127.0.0.1 "${AI_GRPC_PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! nc -z 127.0.0.1 "${AI_GRPC_PORT}" >/dev/null 2>&1; then
  echo "Python AI gRPC did not become ready on 127.0.0.1:${AI_GRPC_PORT}" >&2
  exit 1
fi

echo "Starting Go Gateway on ${GO_GATEWAY_ADDR}, AI_SERVICE_ADDRESS=${AI_SERVICE_ADDRESS}"
(
  cd "${ROOT_DIR}/src/backend"
  SERVER_ADDRESS="${GO_GATEWAY_ADDR}" \
    DATABASE_URL="${DATABASE_URL}" \
    AI_SERVICE_ADDRESS="${AI_SERVICE_ADDRESS}" \
    go run ./cmd/server
)
