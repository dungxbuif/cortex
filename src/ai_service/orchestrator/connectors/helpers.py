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

__all__ = [
    "_health_from_status",
    "_unsupported",
    "_path_not_allowed",
    "_resolve_path",
    "_is_relative_to",
    "_append_tags",
    "_normalize_tags",
    "_positive_int",
    "_snippet",
    "_to_plain_dict",
    "_format_datetime",
]

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


