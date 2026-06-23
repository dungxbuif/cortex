from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ai_service.homelab.service import HomelabService
from ai_service.orchestrator.contracts import (
    Citation,
    ModuleHealth,
    ObservationStatus,
    ToolExecutionContext,
    ToolObservation,
)
from ai_service.secondbrain.service import SecondBrainService


class SecondBrainConnector:
    module = "second_brain"

    def __init__(self, service: SecondBrainService) -> None:
        self.service = service
        self._handlers = {
            "CreateCapture": self._create_capture,
            "ListCaptures": self._list_captures,
            "GetSyncStatus": self._get_sync_status,
            "SearchKnowledge": self._search_knowledge,
        }

    async def health(self) -> ModuleHealth:
        return _health_from_status(self.module, lambda: self.service.get_sync_status())

    def supported_targets(self) -> set[str]:
        return {"CreateCapture", "ListCaptures", "GetSyncStatus", "SearchKnowledge"}

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        handler = self._handlers.get(target_api)
        if handler is None:
            return _unsupported(self.module, tool_name, target_api)
        return handler(tool_name, args, context)

    def _create_capture(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        raw_text = _append_tags(str(args.get("content", "")), args.get("tags"))
        capture = self.service.create_capture(
            raw_text=raw_text,
            source=str(args.get("source", "telegram")),
            owner_id=context.owner_id,
        )
        data = _to_plain_dict(capture)
        data["vault_write"] = False
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Captured to Second Brain inbox. capture_id={capture.id}; vault_write=false",
            data=data,
            warnings=("Captured in DB inbox only; no Obsidian Vault file was written.",),
        )

    def _list_captures(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        captures = self.service.list_captures(owner_id=context.owner_id)
        data = {"captures": [_to_plain_dict(capture) for capture in captures]}
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(captures)} Second Brain capture(s).",
            data=data,
        )

    def _get_sync_status(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        status = self.service.get_sync_status(owner_id=context.owner_id)
        data = _to_plain_dict(status)
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=(
                f"Second Brain index has {status.indexed_documents}/{status.total_documents} "
                f"indexed document(s) and {status.total_chunks} chunk(s)."
            ),
            data=data,
        )

    def _search_knowledge(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        limit = _positive_int(args.get("limit"), default=5)
        results = self.service.search_knowledge(
            query=str(args.get("query", "")),
            owner_id=context.owner_id,
            top_k=limit,
        )
        citations = tuple(
            Citation(
                label=result.document.title or result.document.vault_path,
                source_path=result.document.vault_path,
                source_revision=_format_datetime(result.document.indexed_at),
                chunk_id=result.chunk.id,
            )
            for result in results
        )
        data = {
            "results": [
                {
                    "title": result.document.title,
                    "vault_path": result.document.vault_path,
                    "indexed_at": _format_datetime(result.document.indexed_at),
                    "chunk_id": result.chunk.id,
                    "snippet": _snippet(result.chunk.content),
                    "score": result.score,
                    "reasons": list(result.reasons),
                }
                for result in results
            ],
        }
        return ToolObservation(
            status=ObservationStatus.SUCCESS if results else ObservationStatus.NOT_FOUND,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(results)} Second Brain result(s).",
            data=data,
            citations=citations,
        )


class HomelabConnector:
    module = "homelab"

    def __init__(
        self,
        service: HomelabService,
        default_repo_path: str | None = None,
        allowed_repo_paths: tuple[str, ...] = (),
    ) -> None:
        self.service = service
        self.default_repo_path = default_repo_path
        self.allowed_repo_paths = tuple(_resolve_path(path) for path in allowed_repo_paths)
        if default_repo_path:
            default_resolved = _resolve_path(default_repo_path)
            if default_resolved not in self.allowed_repo_paths:
                self.allowed_repo_paths = (*self.allowed_repo_paths, default_resolved)
        self._handlers = {
            "GetSyncStatus": self._get_sync_status,
            "SearchKnowledge": self._search_knowledge,
            "ValidateLinks": self._validate_links,
            "SyncRepository": self._sync_repository,
        }

    async def health(self) -> ModuleHealth:
        return _health_from_status(self.module, lambda: self.service.get_sync_status())

    def supported_targets(self) -> set[str]:
        return {"GetSyncStatus", "SearchKnowledge", "ValidateLinks", "SyncRepository"}

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        handler = self._handlers.get(target_api)
        if handler is None:
            return _unsupported(self.module, tool_name, target_api)
        return handler(tool_name, args, context)

    def _get_sync_status(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        status = self.service.get_sync_status(owner_id=context.owner_id)
        data = _to_plain_dict(status)
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=(
                f"Homelab index has {status.indexed_documents}/{status.total_documents} "
                f"indexed document(s) and {status.total_chunks} chunk(s)."
            ),
            data=data,
        )

    def _search_knowledge(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        limit = _positive_int(args.get("limit"), default=5)
        results = self.service.search_knowledge(
            query=str(args.get("query", "")),
            owner_id=context.owner_id,
            top_k=limit,
        )
        citations = tuple(
            Citation(
                label=result.document.file_path,
                source_path=result.document.file_path,
                source_revision=result.document.commit_sha,
                chunk_id=result.chunk.id,
            )
            for result in results
        )
        data = {
            "results": [
                {
                    "file_path": result.document.file_path,
                    "commit_sha": result.document.commit_sha,
                    "chunk_id": result.chunk.id,
                    "snippet": _snippet(result.chunk.content),
                    "score": result.score,
                }
                for result in results
            ],
        }
        return ToolObservation(
            status=ObservationStatus.SUCCESS if results else ObservationStatus.NOT_FOUND,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(results)} Homelab result(s).",
            data=data,
            citations=citations,
        )

    def _validate_links(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        repo_path = self._allowed_repo_path(args)
        if repo_path is None:
            return _path_not_allowed(self.module, tool_name)
        broken = self.service.validate_markdown_links(repo_path)
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(broken)} broken Homelab markdown link(s).",
            data={"broken_links": broken},
        )

    def _sync_repository(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        repo_path = self._allowed_repo_path(args)
        if repo_path is None:
            return _path_not_allowed(self.module, tool_name)
        result = self.service.sync_repository(
            repo_path=repo_path,
            repo_url=str(args.get("repo_url", "github.com/dungxbuif/Homelab")),
            branch=str(args.get("branch", "main")),
            commit_sha=str(args.get("commit_sha", "latest")),
            owner_id=context.owner_id,
        )
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=(
                "Homelab repository mirror synced. "
                f"processed={result.get('processed_files', 0)} skipped={result.get('skipped_files', 0)} "
                f"failed={result.get('failed_files', 0)}"
            ),
            data=dict(result),
        )

    def _allowed_repo_path(self, args: dict[str, Any]) -> str | None:
        raw = str(args.get("repo_path") or self.default_repo_path or "")
        if not raw:
            return None
        candidate = _resolve_path(raw)
        if not self.allowed_repo_paths:
            return None
        if any(candidate == allowed or _is_relative_to(candidate, allowed) for allowed in self.allowed_repo_paths):
            return str(candidate)
        return None


def _health_from_status(module: str, read_status: Callable[[], Any]) -> ModuleHealth:
    try:
        status = read_status()
    except Exception as exc:
        return ModuleHealth(module=module, status="degraded", message=str(exc))
    return ModuleHealth(module=module, status="ok", message=str(_to_plain_dict(status)))


def _unsupported(module: str, tool_name: str, target_api: str) -> ToolObservation:
    return ToolObservation(
        status=ObservationStatus.VALIDATION_ERROR,
        module=module,
        tool=tool_name,
        safe_user_message=f"Unsupported target API for {module}: {target_api}",
        data={"target_api": target_api},
    )


def _path_not_allowed(module: str, tool_name: str) -> ToolObservation:
    return ToolObservation(
        status=ObservationStatus.PERMISSION_DENIED,
        module=module,
        tool=tool_name,
        safe_user_message="Homelab repository path is not configured or not allowed.",
        data={"reason": "repo_path_not_allowed"},
    )


def _resolve_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _is_relative_to(candidate: Path, allowed: Path) -> bool:
    try:
        candidate.relative_to(allowed)
    except ValueError:
        return False
    return True


def _append_tags(content: str, raw_tags: Any) -> str:
    tags = _normalize_tags(raw_tags)
    if not tags:
        return content
    return f"{content.rstrip()}\n\nTags: {' '.join(tags)}"


def _normalize_tags(raw_tags: Any) -> list[str]:
    if not isinstance(raw_tags, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in raw_tags:
        value = str(tag).strip().lower().replace(" ", "-")
        value = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"})
        if not value:
            continue
        formatted = f"#{value}"
        if formatted not in seen:
            normalized.append(formatted)
            seen.add(formatted)
    return normalized


def _positive_int(value: Any, default: int) -> int:
    if value is None:
        return default
    parsed = int(value)
    return parsed if parsed > 0 else default


def _snippet(text: str, limit: int = 500) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _to_plain_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_plain_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_plain_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain_dict(item) for item in value]
    if isinstance(value, datetime):
        return _format_datetime(value)
    return value


def _format_datetime(value: datetime | None) -> str:
    return value.isoformat() if value else ""


__all__ = ["HomelabConnector", "SecondBrainConnector"]
