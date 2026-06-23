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

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

cleanup() {
  if [[ -n "${PYTHON_GRPC_PID:-}" ]]; then
    kill "${PYTHON_GRPC_PID}" 2>/dev/null || true
  fi
  if [[ -n "${PYTHON_FASTAPI_PID:-}" ]]; then
    kill "${PYTHON_FASTAPI_PID}" 2>/dev/null || true
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

echo "Starting Python FastAPI Gateway on 127.0.0.1:18080"
(
  cd "${ROOT_DIR}"
  PYTHONPATH=src \
    DATABASE_URL="${DATABASE_URL}" \
    src/ai_service/.venv/bin/python -m uvicorn ai_service.api:create_app --factory --host 127.0.0.1 --port 18080
) &
PYTHON_FASTAPI_PID="$!"

for _ in $(seq 1 60); do
  if nc -z 127.0.0.1 18080 >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! nc -z 127.0.0.1 18080 >/dev/null 2>&1; then
  echo "Python FastAPI Gateway did not become ready on 127.0.0.1:18080" >&2
  exit 1
fi

GO_BACKEND_ADDR="${GO_BACKEND_ADDR:-:8080}"
echo "Starting Go Backend on ${GO_BACKEND_ADDR}"
(
  cd "${ROOT_DIR}/src/backend"
  SERVER_ADDRESS="${GO_BACKEND_ADDR}" \
    DATABASE_URL="${DATABASE_URL}" \
    go run ./cmd/server
)
