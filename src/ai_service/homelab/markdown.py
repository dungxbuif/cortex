from __future__ import annotations

import re

from ai_service.core.vector import tokenize
from ai_service.homelab.models import HomelabDocument, HomelabRawChunk
from ai_service.homelab.redaction import checksum_text


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def chunk_homelab_markdown(owner_id: str, document: HomelabDocument, body: str) -> list[HomelabRawChunk]:
    chunks: list[HomelabRawChunk] = []
    heading_chain: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        chunk_index = len(chunks)
        chunks.append(
            HomelabRawChunk(
                id=checksum_text(f"{document.id}:{chunk_index}:{text}"),
                document_id=document.id,
                owner_id=owner_id,
                file_path=document.file_path,
                chunk_index=chunk_index,
                content=text,
                heading_chain=tuple(heading_chain),
                token_count=len(tokenize(text)),
            )
        )

    for line in body.splitlines():
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
