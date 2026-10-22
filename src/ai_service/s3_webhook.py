from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


UPSERT_EVENTS = {"create", "write", "modify", "modified", "update"}
DELETE_EVENTS = {"remove", "delete", "deleted"}


@dataclass(frozen=True)
class S3WebhookRoots:
    second_brain: Path
    homelab: Path


@dataclass(frozen=True)
class S3WebhookEvent:
    domain: str
    action: str
    root: Path
    relative_path: str | None = None
    absolute_path: Path | None = None
    old_relative_path: str | None = None
    old_absolute_path: Path | None = None


def parse_s3_webhook_event(payload: dict[str, Any], roots: S3WebhookRoots) -> S3WebhookEvent:
    if str(payload.get("source", "s3")) not in {"s3", "rustfs"}:
        raise ValueError("source must be s3")

    domain = str(payload.get("domain", "")).strip()
    if domain not in {"second_brain", "homelab"}:
        raise ValueError("domain must be second_brain or homelab")

    raw_event_type = str(payload.get("event_type", "")).strip().lower()
    if raw_event_type in UPSERT_EVENTS:
        action = "upsert"
    elif raw_event_type in DELETE_EVENTS:
        action = "delete"
    elif raw_event_type == "rename":
        action = "rename"
    else:
        raise ValueError("event_type is not supported")

    root = _root_for_domain(domain, roots)
    relative_path = None
    absolute_path = None
    if payload.get("relative_path") is not None:
        relative_path = _normalize_relative_path(payload.get("relative_path"))
    if payload.get("absolute_path") is not None:
        absolute_path = _resolve_event_path(root, relative_path, payload.get("absolute_path"))

    old_relative_path = None
    old_absolute_path = None
    if action == "rename" and payload.get("old_relative_path") is not None:
        old_relative_path = _normalize_relative_path(payload.get("old_relative_path"))
        old_absolute_path = _resolve_event_path(root, old_relative_path, payload.get("old_absolute_path"))

    return S3WebhookEvent(
        domain=domain,
        action=action,
        root=root,
        relative_path=relative_path,
        absolute_path=absolute_path,
        old_relative_path=old_relative_path,
        old_absolute_path=old_absolute_path,
    )


RustFSRoots = S3WebhookRoots
RustFSEvent = S3WebhookEvent


def parse_rustfs_event(payload: dict[str, Any], roots: S3WebhookRoots) -> S3WebhookEvent:
    return parse_s3_webhook_event(payload, roots)


def _root_for_domain(domain: str, roots: S3WebhookRoots) -> Path:
    root = roots.second_brain if domain == "second_brain" else roots.homelab
    if not str(root).strip() or str(root) == ".":
        raise ValueError(f"{domain} root is not configured")
    return root.expanduser().resolve(strict=False)


def _normalize_relative_path(value: Any) -> str:
    if value is None:
        raise ValueError("relative_path is required")
    relative_path = str(value).strip().replace("\\", "/").lstrip("/")
    if not relative_path:
        raise ValueError("relative_path is required")
    parts = Path(relative_path).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("relative_path must not contain traversal segments")
    if not relative_path.endswith(".md"):
        raise ValueError("relative_path must be a markdown file")
    return relative_path


def _resolve_event_path(root: Path, relative_path: str | None, absolute_path_value: Any) -> Path:
    if absolute_path_value is None or str(absolute_path_value).strip() == "":
        raise ValueError("absolute_path is required when validating a file path")
    candidate = Path(str(absolute_path_value)).expanduser().resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("absolute_path must stay under configured domain root") from exc
    if relative_path is not None and candidate != (root / relative_path).resolve(strict=False):
        raise ValueError("absolute_path must match configured root plus relative_path")
    return candidate
