from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .repository import SqliteSecondBrainRepository
from .service import SecondBrainService


def create_app(repository: SqliteSecondBrainRepository | None = None) -> Any:
    """Create the optional FastAPI transport adapter.

    Core behavior is implemented in SecondBrainService and can be tested without
    FastAPI. Install project dependencies before running this app.
    """

    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:
        raise RuntimeError("FastAPI is not installed. Install project dependencies first.") from exc

    app = FastAPI(title="Cortex Second Brain API")
    service = SecondBrainService(repository=repository)

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
