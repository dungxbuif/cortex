from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ai_service.secondbrain.repository import SqliteSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService
from ai_service.homelab.service import HomelabService
from ai_service.orchestrator.service import ChatMessage, OrchestratorService


def create_app(
    repository: SqliteSecondBrainRepository | None = None,
    secondbrain_repository: Any | None = None,
    homelab_repository: Any | None = None,
    embedder: Any | None = None,
    ai_client: Any | None = None,
) -> Any:
    """Create the optional FastAPI transport adapter.

    Core behavior is implemented in SecondBrainService and can be tested without
    FastAPI. Install project dependencies before running this app.
    """

    try:
        from fastapi import FastAPI, HTTPException
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

    app = FastAPI(title="Cortex Second Brain API")
    service = SecondBrainService(repository=secondbrain_repository, embedder=embedder, ai_client=ai_client)
    homelab_service = HomelabService(repository=homelab_repository, embedder=embedder, ai_client=ai_client)
    orchestrator_service = OrchestratorService(service, homelab_service)

    @app.get("/api/ai/health")
    def ai_health() -> dict[str, str]:
        return {
            "status": "ok",
            "gateway": "python",
            "second_brain": "ok",
            "homelab": "ok",
            "orchestrator": "ok",
        }

    @app.post("/v1/chat/completions")
    def chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            messages = [
                ChatMessage(
                    role=str(message.get("role", "")),
                    content=str(message.get("content", "")),
                    name=str(message.get("name", "")),
                )
                for message in payload.get("messages", [])
            ]
            completion = orchestrator_service.chat_completions(
                messages=messages,
                owner_id=str(payload.get("owner_id", "owner")),
                conversation_id=str(payload.get("conversation_id", "")),
                request_id=str(payload.get("request_id", "")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize(asdict(completion))

    # --- Legacy api/v1 routes (for compat with existing tests) ---
    @app.post("/api/v1/capture")
    def create_capture(payload: dict[str, Any]) -> dict[str, Any]:
        capture = service.create_capture(
            raw_text=str(payload.get("raw_text", "")),
            source=str(payload.get("source", "chat")),
            owner_id=str(payload.get("owner_id", "owner")),
        )
        return _serialize(asdict(capture))

    @app.get("/api/v1/capture")
    def list_captures(owner_id: str = "owner") -> list[dict[str, Any]]:
        return [_serialize(asdict(capture)) for capture in service.list_captures(owner_id)]

    @app.get("/api/v1/sync/status")
    def sync_status(owner_id: str = "owner") -> dict[str, Any]:
        return _serialize(asdict(service.get_sync_status(owner_id)))

    @app.post("/api/v1/search")
    def search(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=str(payload.get("owner_id", "owner")),
            top_k=int(payload.get("top_k", 5)),
        )
        return [_serialize(asdict(result)) for result in results]

    @app.post("/api/v1/homelab/sync")
    def sync_homelab(payload: dict[str, Any]) -> dict[str, Any]:
        res = homelab_service.sync_repository(
            repo_path=str(payload.get("repo_path", "")),
            repo_url=str(payload.get("repo_url", "github.com/dungxbuif/Homelab")),
            branch=str(payload.get("branch", "main")),
            commit_sha=str(payload.get("commit_sha", "latest")),
            owner_id=str(payload.get("owner_id", "homelab")),
        )
        return _serialize(res)

    @app.post("/api/v1/homelab/search")
    def search_homelab(payload: dict[str, Any]) -> list[dict[str, Any]]:
        results = homelab_service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=str(payload.get("owner_id", "homelab")),
            top_k=int(payload.get("top_k", 5)),
        )
        return [_serialize(asdict(result)) for result in results]

    @app.post("/api/v1/homelab/validate-links")
    def validate_links(payload: dict[str, Any]) -> dict[str, Any]:
        broken = homelab_service.validate_markdown_links(
            repo_path=str(payload.get("repo_path", ""))
        )
        return {
            "status": "completed",
            "broken_links": _serialize(broken),
        }

    # --- Standard public REST routes (replacing Go proxy) ---
    @app.post("/api/secondbrain/captures", status_code=201)
    def api_create_capture(payload: dict[str, Any]) -> dict[str, Any]:
        owner_id = payload.get("owner_id") or "owner"
        source = payload.get("source") or "gateway"
        capture = service.create_capture(
            raw_text=str(payload.get("raw_text", "")),
            source=str(source),
            owner_id=str(owner_id),
        )
        return {"capture": _serialize(asdict(capture))}

    @app.get("/api/secondbrain/captures")
    def api_list_captures(owner_id: str = "owner") -> dict[str, Any]:
        captures = service.list_captures(owner_id)
        return {"captures": [_serialize(asdict(c)) for c in captures]}

    @app.get("/api/secondbrain/status")
    def api_secondbrain_status(owner_id: str = "owner") -> dict[str, Any]:
        status_data = service.get_sync_status(owner_id)
        return {
            "total_documents": status_data.total_documents,
            "indexed_documents": status_data.indexed_documents,
            "total_chunks": status_data.total_chunks,
        }

    @app.post("/api/secondbrain/search")
    def api_search_secondbrain(payload: dict[str, Any]) -> dict[str, Any]:
        owner_id = payload.get("owner_id") or "owner"
        top_k = payload.get("top_k")
        if top_k is None:
            top_k = 5
        results = service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=str(owner_id),
            top_k=int(top_k),
        )
        return {"results": [_serialize(asdict(result)) for result in results]}

    @app.post("/api/homelab/sync")
    def api_sync_homelab(payload: dict[str, Any]) -> dict[str, Any]:
        owner_id = payload.get("owner_id") or "owner"
        res = homelab_service.sync_repository(
            repo_path=str(payload.get("repo_path", "")),
            repo_url=str(payload.get("repo_url", "github.com/dungxbuif/Homelab")),
            branch=str(payload.get("branch", "main")),
            commit_sha=str(payload.get("commit_sha", "latest")),
            owner_id=str(owner_id),
        )
        return _serialize(res)

    @app.post("/api/homelab/search")
    def api_search_homelab(payload: dict[str, Any]) -> dict[str, Any]:
        owner_id = payload.get("owner_id") or "owner"
        top_k = payload.get("top_k")
        if top_k is None:
            top_k = 5
        results = homelab_service.search_knowledge(
            query=str(payload.get("query", "")),
            owner_id=str(owner_id),
            top_k=int(top_k),
        )
        return {"results": [_serialize(asdict(result)) for result in results]}

    @app.post("/api/homelab/validate-links")
    def api_validate_homelab_links(payload: dict[str, Any]) -> dict[str, Any]:
        broken = homelab_service.validate_markdown_links(
            repo_path=str(payload.get("repo_path", ""))
        )
        return {
            "status": "completed",
            "broken_links": _serialize(broken),
        }

    return app


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
