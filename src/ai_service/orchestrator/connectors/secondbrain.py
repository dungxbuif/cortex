from __future__ import annotations

import asyncio
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ai_service.orchestrator.contracts import (
    Citation,
    ModuleHealth,
    ObservationStatus,
    ToolExecutionContext,
    ToolObservation,
)
from ai_service.secondbrain.service import SecondBrainService
from .helpers import *

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


