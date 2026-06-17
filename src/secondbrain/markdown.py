from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from typing import Any

from .google_ai import GoogleAIClient
from .models import DEFAULT_OWNER_ID, VaultChunk, VaultDocument, utc_now
from .vector import tokenize

FRONTMATTER_BOUNDARY = "---"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict[str, Any]
    body: str


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_markdown(markdown: str) -> ParsedMarkdown:
    lines = markdown.splitlines()
    if len(lines) >= 2 and lines[0].strip() == FRONTMATTER_BOUNDARY:
        for index in range(1, len(lines)):
            if lines[index].strip() == FRONTMATTER_BOUNDARY:
                frontmatter_lines = lines[1:index]
                body = "\n".join(lines[index + 1 :]).strip()
                return ParsedMarkdown(_parse_simple_frontmatter(frontmatter_lines), body)
    return ParsedMarkdown({}, markdown.strip())


def _parse_simple_frontmatter(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        data[key.strip()] = _parse_frontmatter_value(raw_value.strip())
    return data


def _parse_frontmatter_value(raw_value: str) -> Any:
    if raw_value.lower() in {"true", "false"}:
        return raw_value.lower() == "true"
    if raw_value.startswith("[") and raw_value.endswith("]"):
        try:
            value = ast.literal_eval(raw_value)
            if isinstance(value, list):
                return value
        except (SyntaxError, ValueError):
            inner = raw_value[1:-1].strip()
            if not inner:
                return []
            return [item.strip().strip("\"'") for item in inner.split(",")]
    if (raw_value.startswith('"') and raw_value.endswith('"')) or (
        raw_value.startswith("'") and raw_value.endswith("'")
    ):
        return raw_value[1:-1]
    return raw_value


def build_document(owner_id: str, vault_path: str, markdown: str) -> VaultDocument:
    parsed = parse_markdown(markdown)
    path_parts = [part for part in vault_path.split("/") if part]
    path_document_type = path_parts[0].lower() if path_parts else "unknown"
    if path_document_type in {"raw", "staging", "wiki", "tracking", "dailylogs", "archive"}:
        document_type = path_document_type
    else:
        document_type = str(parsed.frontmatter.get("type") or path_document_type).lower()
    title = str(parsed.frontmatter.get("title") or _title_from_path(vault_path))
    rag_allowed = parsed.frontmatter.get("rag", True) is not False
    private = parsed.frontmatter.get("private", False) is True
    archived = document_type == "archive" or "archive" in path_parts
    document_id = checksum_text(f"{owner_id}:{vault_path}")
    return VaultDocument(
        id=document_id,
        owner_id=owner_id,
        vault_path=vault_path,
        checksum=checksum_text(markdown),
        document_type=document_type,
        title=title,
        frontmatter=parsed.frontmatter,
        rag_allowed=rag_allowed,
        private=private,
        archived=archived,
        index_status="indexed",
        indexed_at=utc_now(),
    )


def chunk_markdown(owner_id: str, document: VaultDocument, markdown: str, ai_client: GoogleAIClient) -> list[VaultChunk]:
    parsed = parse_markdown(markdown)
    chunks: list[VaultChunk] = []
    heading_chain: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        chunk_index = len(chunks)
        chunks.append(
            VaultChunk(
                id=checksum_text(f"{document.id}:{chunk_index}:{text}"),
                document_id=document.id,
                owner_id=owner_id,
                vault_path=document.vault_path,
                chunk_index=chunk_index,
                content=text,
                heading_chain=tuple(heading_chain),
                token_count=len(tokenize(text)),
                embedding=ai_client.embed_text(text),
            )
        )

    for line in parsed.body.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            heading_chain = heading_chain[: level - 1] + [title]
            continue
        if not line.strip():
            flush()
            continue
        buffer.append(line)

    flush()
    return chunks


def normalize_capture_markdown(raw_text: str, source: str) -> str:
    title = raw_text.strip().splitlines()[0][:80].strip() or "Untitled capture"
    return "\n".join(
        [
            "---",
            "type: Raw",
            f'title: "{title}"',
            f'source: "{source}"',
            "status: raw",
            "rag: false",
            "---",
            "",
            "## Noi dung goc",
            "",
            raw_text.strip(),
            "",
        ]
    )


def suggest_tags(raw_text: str) -> tuple[str, ...]:
    text = raw_text.lower()
    tags: list[str] = []
    for keyword, tag in [
        ("python", "python"),
        ("cache", "caching"),
        ("consistent hashing", "system-design"),
        ("rag", "rag"),
        ("ai", "ai"),
    ]:
        if keyword in text and tag not in tags:
            tags.append(tag)
    return tuple(tags)


def _title_from_path(vault_path: str) -> str:
    name = vault_path.rsplit("/", 1)[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return name.replace("-", " ").replace("_", " ").strip().title()
