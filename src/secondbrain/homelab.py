from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SecondBrainSettings
from .google_ai import GoogleAIClient
from .models import HomelabDocument, HomelabChunk, HomelabSearchResult, HomelabSyncStatus, IndexStatus, utc_now
from .vector import tokenize, cosine_similarity

# Exclude list for Homelab documentation indexing
EXCLUDE_FOLDERS = {".git", "credentials", "deprecated", "diagnostics", ".terraform", ".venv", "node_modules", "__pycache__"}
EXCLUDE_FILES = {"local_vars.json"}

# Heading and Link regex
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

# Redaction regexes
SECRET_KEYWORDS_RE = re.compile(
    r"(?i)(api[-_]?key|secret|token|password|passwd|private[-_]?key)(\s*[:=]\s*)[\"']?([a-zA-Z0-9_\-\.\/]{8,})[\"']?"
)
IP_ADDRESS_RE = re.compile(
    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
)


def verify_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[len("sha256="):]
    computed_sig = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_sig, expected_sig)


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def redact_secrets(text: str) -> str:
    # 1. Redact key-value secrets preserving key and separator
    text = SECRET_KEYWORDS_RE.sub(r"\1\2<REDACTED_SECRET>", text)
    # 2. Mask public IP addresses (ignore local subnets 127.0.0.1, 10.x.x.x, 192.168.x.x for readability of local configuration)
    def ip_replacer(match: re.Match) -> str:
        ip = match.group(0)
        if ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.31.")):
            return ip
        return "<REDACTED_IP>"

    return IP_ADDRESS_RE.sub(ip_replacer, text)


def gfm_slugify(heading: str) -> str:
    # Convert to lowercase
    slug = heading.lower().strip()
    # Strip emojis and punctuation (keep letters, numbers, spaces, hyphens, underscores)
    slug = re.sub(r"[^\w\s\-]", "", slug)
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


class HomelabService:
    def __init__(self, repository: Any, ai_client: GoogleAIClient | None = None) -> None:
        self.repository = repository
        self.ai_client = ai_client or GoogleAIClient()

    def sync_repository(
        self,
        repo_path: str,
        repo_url: str = "github.com/dungxbuif/Homelab",
        branch: str = "main",
        commit_sha: str = "latest",
        owner_id: str = "homelab",
    ) -> dict[str, int | str]:
        path = Path(repo_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")

        processed_files = 0
        skipped_files = 0
        failed_files = 0

        # Walk directory
        for root, dirs, files in os.walk(repo_path):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]

            for file in files:
                if not file.endswith(".md") or file in EXCLUDE_FILES:
                    continue

                abs_file_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(abs_file_path, repo_path)

                try:
                    with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_content = f.read()

                    checksum = checksum_text(raw_content)

                    # Check for modification
                    existing = self.repository.get_homelab_document(owner_id, rel_file_path)
                    if existing and existing.checksum == checksum:
                        skipped_files += 1
                        continue

                    # Redact content
                    redacted = redact_secrets(raw_content)

                    # Build document metadata
                    doc_id = checksum_text(f"{owner_id}:{rel_file_path}")
                    title = rel_file_path.rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").replace("_", " ").title()

                    document = HomelabDocument(
                        id=doc_id,
                        owner_id=owner_id,
                        repo_url=repo_url,
                        branch=branch,
                        commit_sha=commit_sha,
                        file_path=rel_file_path,
                        checksum=checksum,
                        index_status="indexed",
                        indexed_at=utc_now(),
                    )

                    # Chunk & Embed redacted markdown
                    chunks = self._chunk_homelab_document(owner_id, document, redacted)
                    self.repository.upsert_homelab_document_with_chunks(document, chunks)
                    processed_files += 1

                except Exception:
                    failed_files += 1

        return {
            "status": "success",
            "processed_files": processed_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
        }

    def search_knowledge(
        self,
        query: str,
        owner_id: str = "homelab",
        top_k: int = 5,
    ) -> list[HomelabSearchResult]:
        if not query.strip():
            return []

        query_vector = self.ai_client.embed_text(query)

        # Retrieve and sort
        if hasattr(self.repository, "conn"):  # SQLite
            searchable = self.repository.list_searchable_homelab_chunks(owner_id)
            scored: list[tuple[float, HomelabDocument, HomelabChunk]] = []
            for doc, chunk in searchable:
                score = cosine_similarity(query_vector, chunk.embedding)
                scored.append((score, doc, chunk))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                HomelabSearchResult(chunk=chunk, document=doc, score=score)
                for score, doc, chunk in scored[:top_k]
            ]
        else:  # Postgres
            # Raw SQL vector cosine distance query via Postgres repository psql wrapper
            from .repository import sql_literal, vector_literal
            rows = self.repository._query_json_lines(
                f"""
                SELECT jsonb_build_object(
                  'score', 1 - (c.embedding <=> {vector_literal(query_vector)}),
                  'document', jsonb_build_object(
                    'id', d.id,
                    'owner_id', d.owner_id,
                    'repo_url', d.repo_url,
                    'branch', d.branch,
                    'commit_sha', d.commit_sha,
                    'file_path', d.file_path,
                    'checksum', d.checksum,
                    'index_status', d.index_status,
                    'indexed_at', d.indexed_at
                  ),
                  'chunk', jsonb_build_object(
                    'id', c.id,
                    'document_id', c.document_id,
                    'owner_id', c.owner_id,
                    'file_path', c.file_path,
                    'chunk_index', c.chunk_index,
                    'content', c.content,
                    'heading_chain', c.heading_chain,
                    'token_count', c.token_count,
                    'embedding', c.embedding::text
                  )
                )
                FROM homelab_documents d
                JOIN homelab_document_chunks c ON c.document_id = d.id
                WHERE d.owner_id = {sql_literal(owner_id)}
                  AND d.index_status = 'indexed'
                ORDER BY c.embedding <=> {vector_literal(query_vector)}
                LIMIT {top_k};
                """
            )
            from .repository import homelab_document_from_json, homelab_chunk_from_json
            return [
                HomelabSearchResult(
                    chunk=homelab_chunk_from_json(row["chunk"]),
                    document=homelab_document_from_json(row["document"]),
                    score=float(row["score"]),
                )
                for row in rows
            ]

    def validate_markdown_links(self, repo_path: str) -> list[dict[str, Any]]:
        path = Path(repo_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        # Step 1: Discover all markdown files and compile heading anchors in each file
        md_files: set[str] = set()
        heading_slugs: dict[str, set[str]] = {}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]

            for file in files:
                if not file.endswith(".md") or file in EXCLUDE_FILES:
                    continue

                abs_file_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(abs_file_path, repo_path)
                md_files.add(rel_file_path)

                # Parse headings
                slugs: set[str] = set()
                try:
                    with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            match = HEADING_RE.match(line)
                            if match:
                                heading_text = match.group(2)
                                slugs.add(gfm_slugify(heading_text))
                except Exception:
                    pass
                heading_slugs[rel_file_path] = slugs

        # Step 2: Traverse files and validate links
        broken_links: list[dict[str, Any]] = []

        for rel_file_path in md_files:
            abs_file_path = os.path.join(repo_path, rel_file_path)
            source_dir = os.path.dirname(rel_file_path)

            try:
                with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        for match in LINK_RE.finditer(line):
                            raw_target = match.group(2).split(' "', 1)[0].split(" '", 1)[0].strip()

                            # Ignore absolute links or mailto
                            if raw_target.startswith(("http://", "https://", "mailto:", "ftp:", "tel:", "irc:", "magnet:", "file://")):
                                continue

                            # Parse target path and anchor
                            parts = raw_target.split("#", 1)
                            link_file_rel = parts[0]
                            anchor = parts[1] if len(parts) > 1 else None

                            # Resolve link file path relative to repo root
                            if not link_file_rel:
                                # Self link
                                resolved_file = rel_file_path
                            else:
                                resolved_file = os.path.normpath(os.path.join(source_dir, link_file_rel))

                            # Normalize windows separators to forward slashes
                            resolved_file = resolved_file.replace("\\", "/")

                            # Check if file exists in the repository
                            if resolved_file not in md_files:
                                # Check if it could be a static asset or IaC file outside md_files but existing on disk
                                full_disk_path = os.path.join(repo_path, resolved_file)
                                if not os.path.exists(full_disk_path):
                                    broken_links.append(
                                        {
                                            "source_file": rel_file_path,
                                            "line_number": line_idx,
                                            "raw_link": raw_target,
                                            "reason": "File not found",
                                        }
                                    )
                                    continue

                            # If it is a markdown file, check anchor existence
                            if anchor and resolved_file in heading_slugs:
                                target_slugs = heading_slugs[resolved_file]
                                slugified_anchor = gfm_slugify(anchor)

                                # Match anchor (strict or lenient collapsed hyphen matching)
                                def anchor_matches() -> bool:
                                    if slugified_anchor in target_slugs:
                                        return True
                                    # Lenient check: collapse consecutive hyphens
                                    collapsed_anchor = re.sub(r"-+", "-", slugified_anchor)
                                    for target_slug in target_slugs:
                                        if re.sub(r"-+", "-", target_slug) == collapsed_anchor:
                                            return True
                                    return False

                                if not anchor_matches():
                                    broken_links.append(
                                        {
                                            "source_file": rel_file_path,
                                            "line_number": line_idx,
                                            "raw_link": raw_target,
                                            "reason": f"Anchor '#{anchor}' not found in target file",
                                        }
                                    )
            except Exception as e:
                broken_links.append(
                    {
                        "source_file": rel_file_path,
                        "line_number": 1,
                        "raw_link": "",
                        "reason": f"Failed to read file: {e}",
                    }
                )

        return broken_links

    def _chunk_homelab_document(self, owner_id: str, document: HomelabDocument, body: str) -> list[HomelabChunk]:
        chunks: list[HomelabChunk] = []
        heading_chain: list[str] = []
        buffer: list[str] = []

        def flush() -> None:
            text = "\n".join(buffer).strip()
            buffer.clear()
            if not text:
                return
            chunk_index = len(chunks)
            chunks.append(
                HomelabChunk(
                    id=checksum_text(f"{document.id}:{chunk_index}:{text}"),
                    document_id=document.id,
                    owner_id=owner_id,
                    file_path=document.file_path,
                    chunk_index=chunk_index,
                    content=text,
                    heading_chain=tuple(heading_chain),
                    token_count=len(tokenize(text)),
                    embedding=self.ai_client.embed_text(text),
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
