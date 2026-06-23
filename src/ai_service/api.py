from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import hmac
import json
from pathlib import Path
import time
from typing import Any

from ai_service.secondbrain.repository import SqliteSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService
from ai_service.homelab.service import HomelabService
from ai_service.orchestrator.service import ChatMessage, OrchestratorService

SINGLE_USER_ID = "11111111-1111-1111-1111-111111111111"


def create_app(
    repository: SqliteSecondBrainRepository | None = None,
    secondbrain_repository: Any | None = None,
    homelab_repository: Any | None = None,
    embedder: Any | None = None,
    ai_client: Any | None = None,
    object_store: Any | None = None,
    allowed_bucket: str | None = None,
    object_prefix: str | None = None,
) -> Any:
    """Create the optional FastAPI transport adapter.

    Core behavior is implemented in SecondBrainService and can be tested without
    FastAPI. Install project dependencies before running this app.
    """

    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.responses import StreamingResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError("FastAPI is not installed. Install project dependencies first.") from exc

    if secondbrain_repository is None:
        if repository is not None:
            secondbrain_repository = repository
        else:
            from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository
            try:
                secondbrain_repository = PostgresPsqlSecondBrainRepository.from_env()
                secondbrain_repository.ping()
            except Exception:
                secondbrain_repository = SqliteSecondBrainRepository()

    if homelab_repository is None:
        if repository is not None:
            homelab_repository = repository
        else:
            from ai_service.homelab.repository import PostgresPsqlHomelabRepository, SqliteHomelabRepository
            try:
                homelab_repository = PostgresPsqlHomelabRepository.from_env()
                homelab_repository.ping()
            except Exception:
                homelab_repository = SqliteHomelabRepository()

    import os
    from ai_service.secondbrain.object_store import LocalS3ObjectStore

    if object_store is None:
        object_store = LocalS3ObjectStore.from_env()
    if allowed_bucket is None:
        allowed_bucket = os.getenv("SECOND_BRAIN_MINIO_BUCKET") or None
    if object_prefix is None:
        object_prefix = os.getenv("SECOND_BRAIN_MINIO_PREFIX", "second-brain/")

    jwt_secret = os.getenv("CORTEX_INTERNAL_JWT_SECRET", "cortex-local-internal-only-secret")
    app = FastAPI(title="Cortex API")
    client_dist_dir = Path(__file__).resolve().parents[1] / "client" / "dist"
    service = SecondBrainService(
        repository=secondbrain_repository,
        embedder=embedder,
        ai_client=ai_client,
        object_store=object_store,
        allowed_bucket=allowed_bucket,
        object_prefix=object_prefix,
    )
    homelab_service = HomelabService(repository=homelab_repository, embedder=embedder, ai_client=ai_client)
    orchestrator_service = OrchestratorService(service, homelab_service)

    def current_user(
        authorization: str | None = Header(None, alias="Authorization"),
    ) -> dict[str, str]:
        return _verify_internal_jwt(authorization, jwt_secret)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/auth/dev-token")
    def dev_token() -> dict[str, str]:
        token = _make_internal_jwt(jwt_secret)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": SINGLE_USER_ID,
        }

    @app.get("/api/ai/health")
    def ai_health(_: dict[str, str] = Depends(current_user)) -> dict[str, str]:
        return {
            "status": "ok",
            "gateway": "python",
            "second_brain": "ok",
            "homelab": "ok",
            "orchestrator": "ok",
        }

    @app.get("/ui")
    def cortex_console() -> FileResponse:
        index_path = client_dist_dir / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="UI bundle is not available")
        return FileResponse(index_path, media_type="text/html")

    @app.get("/ui/assets/{asset_path:path}")
    def cortex_console_asset(asset_path: str) -> FileResponse:
        if ".." in Path(asset_path).parts:
            raise HTTPException(status_code=404, detail="UI asset is not available")
        asset_path_obj = client_dist_dir / "assets" / asset_path
        if not asset_path_obj.exists() or not asset_path_obj.is_file():
            raise HTTPException(status_code=404, detail="UI asset is not available")
        return FileResponse(asset_path_obj)

    @app.get("/ui/{path:path}")
    def cortex_console_spa(path: str) -> FileResponse:
        if path.startswith("assets/"):
            raise HTTPException(status_code=404, detail="UI asset is not available")
        index_path = client_dist_dir / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="UI bundle is not available")
        return FileResponse(index_path, media_type="text/html")

    @app.post("/v1/chat/completions")
    def chat_completions(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> Any:
        try:
            completion = _run_chat_completion(orchestrator_service, payload, user["id"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if bool(payload.get("stream")):
            return StreamingResponse(
                _openai_sse_chunks(_serialize(asdict(completion))),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return _serialize(asdict(completion))

    # --- Legacy api/v1 routes (for compat with existing tests) ---
    @app.post("/api/v1/capture")
    def create_capture(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        capture = service.create_capture(
            raw_text=str(payload.get("raw_text", "")),
            source=str(payload.get("source", "chat")),
            owner_id=user["id"],
        )
        return _serialize(asdict(capture))

    @app.get("/api/v1/capture")
    def list_captures(user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
        return [_serialize(asdict(capture)) for capture in service.list_captures(user["id"])]

    @app.get("/api/v1/sync/status")
    def sync_status(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        return _serialize(asdict(service.get_sync_status(user["id"])))

    @app.post("/api/v1/search")
    def search(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
        results = service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=user["id"],
            top_k=int(payload.get("top_k", 5)),
        )
        return [_serialize(asdict(result)) for result in results]

    @app.post("/api/v1/homelab/sync")
    def sync_homelab(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        res = homelab_service.sync_repository(
            repo_path=str(payload.get("repo_path", "")),
            repo_url=str(payload.get("repo_url", "github.com/dungxbuif/Homelab")),
            branch=str(payload.get("branch", "main")),
            commit_sha=str(payload.get("commit_sha", "latest")),
            owner_id=user["id"],
        )
        return _serialize(res)

    @app.post("/api/v1/homelab/search")
    def search_homelab(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> list[dict[str, Any]]:
        results = homelab_service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=user["id"],
            top_k=int(payload.get("top_k", 5)),
        )
        return [_serialize(asdict(result)) for result in results]

    @app.post("/api/v1/homelab/validate-links")
    def validate_links(payload: dict[str, Any], _: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        broken = homelab_service.validate_markdown_links(
            repo_path=str(payload.get("repo_path", ""))
        )
        return {
            "status": "completed",
            "broken_links": _serialize(broken),
        }

    # --- Standard public REST routes (replacing Go proxy) ---
    @app.post("/api/secondbrain/captures", status_code=201)
    def api_create_capture(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        source = payload.get("source") or "gateway"
        capture = service.create_capture(
            raw_text=str(payload.get("raw_text", "")),
            source=str(source),
            owner_id=user["id"],
        )
        return {"capture": _serialize(asdict(capture))}

    @app.get("/api/secondbrain/captures")
    def api_list_captures(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        captures = service.list_captures(user["id"])
        return {"captures": [_serialize(asdict(c)) for c in captures]}

    @app.get("/api/secondbrain/status")
    def api_secondbrain_status(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        status_data = service.get_sync_status(user["id"])
        return {
            "total_documents": status_data.total_documents,
            "indexed_documents": status_data.indexed_documents,
            "total_chunks": status_data.total_chunks,
        }

    @app.post("/api/secondbrain/search")
    def api_search_secondbrain(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        top_k = payload.get("top_k")
        if top_k is None:
            top_k = 5
        results = service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=user["id"],
            top_k=int(top_k),
        )
        return {"results": [_serialize(asdict(result)) for result in results]}

    @app.post("/api/homelab/sync")
    def api_sync_homelab(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        res = homelab_service.sync_repository(
            repo_path=str(payload.get("repo_path", "")),
            repo_url=str(payload.get("repo_url", "github.com/dungxbuif/Homelab")),
            branch=str(payload.get("branch", "main")),
            commit_sha=str(payload.get("commit_sha", "latest")),
            owner_id=user["id"],
        )
        return _serialize(res)

    @app.post("/api/homelab/search")
    def api_search_homelab(payload: dict[str, Any], user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        top_k = payload.get("top_k")
        if top_k is None:
            top_k = 5
        results = homelab_service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=user["id"],
            top_k=int(top_k),
        )
        return {"results": [_serialize(asdict(result)) for result in results]}

    @app.post("/api/homelab/validate-links")
    def api_validate_homelab_links(payload: dict[str, Any], _: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
        broken = homelab_service.validate_markdown_links(
            repo_path=str(payload.get("repo_path", ""))
        )
        return {
            "status": "completed",
            "broken_links": _serialize(broken),
        }

    @app.post("/api/internal/secondbrain/ingestion-jobs/{job_id}/process")
    def process_secondbrain_ingestion_job(
        job_id: str,
        payload: dict[str, Any],
        user: dict[str, str] = Depends(current_user),
    ) -> dict[str, Any]:
        owner_id = user["id"]
        try:
            result = service.process_ingestion_job(job_id, owner_id=owner_id)
            job = service.repository.get_ingestion_job(owner_id, job_id)
            return {"job": _serialize(asdict(job)) if job is not None else None, "result": _serialize(result)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    from fastapi import Header

    @app.post("/api/webhooks/n8n/secondbrain/obsidian-sync", status_code=202)
    def webhook_obsidian_sync(
        payload: dict[str, Any],
        x_cortex_n8n_token: str | None = Header(None, alias="X-Cortex-N8n-Token"),
    ) -> dict[str, Any]:
        expected_token = os.getenv("CORTEX_N8N_API_KEY", "local-dev-token")
        if not x_cortex_n8n_token or x_cortex_n8n_token != expected_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

        bucket = payload.get("bucket")
        object_key = payload.get("object_key")
        event_name = payload.get("event_name") or payload.get("event") or "s3:ObjectCreated:Put"

        if not bucket or not object_key:
            raise HTTPException(status_code=400, detail="bucket and object_key are required")

        try:
            job = service.submit_minio_event(
                bucket=str(bucket),
                object_key=str(object_key),
                owner_id=SINGLE_USER_ID,
                event_name=str(event_name),
            )
            return {"status": "accepted", "job": _serialize(asdict(job))}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


def _run_chat_completion(orchestrator_service: OrchestratorService, payload: dict[str, Any], owner_id: str):
    messages = [
        ChatMessage(
            role=str(message.get("role", "")),
            content=str(message.get("content", "")),
            name=str(message.get("name", "")),
        )
        for message in payload.get("messages", [])
    ]
    return orchestrator_service.chat_completions(
        messages=messages,
        owner_id=owner_id,
        conversation_id=str(payload.get("conversation_id", "single-conversation")),
        request_id=str(payload.get("request_id", "")),
    )


def _openai_sse_chunks(completion: dict[str, Any]):
    content = completion["choices"][0]["message"]["content"]
    base = {
        "id": completion["id"],
        "object": "chat.completion.chunk",
        "created": completion["created"],
        "model": completion["model"],
    }
    role_chunk = {
        **base,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"

    for part in _stream_text_parts(content):
        chunk = {
            **base,
            "choices": [{"index": 0, "delta": {"content": part}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    done_chunk = {
        **base,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def _stream_text_parts(content: str) -> list[str]:
    parts: list[str] = []
    current = ""
    for token in content.split(" "):
        next_value = token if not current else f"{current} {token}"
        if len(next_value) >= 36:
            parts.append(next_value + " ")
            current = ""
        else:
            current = next_value
    if current:
        parts.append(current)
    return parts or [""]


def _make_internal_jwt(secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": SINGLE_USER_ID, "iat": int(time.time()), "scope": "cortex.internal"}
    signing_input = f"{_b64url_json(header)}.{_b64url_json(payload)}"
    signature = _b64url_bytes(hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"


def _verify_internal_jwt(authorization: str | None, secret: str) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 3:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    signing_input = ".".join(parts[:2])
    expected = _b64url_bytes(hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest())
    if not hmac.compare_digest(parts[2], expected):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    try:
        header = json.loads(_b64url_decode(parts[0]).decode("utf-8"))
        payload = json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc

    if header.get("alg") != "HS256" or payload.get("sub") != SINGLE_USER_ID:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    return {"id": SINGLE_USER_ID}


def _b64url_json(value: dict[str, Any]) -> str:
    return _b64url_bytes(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64url_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
