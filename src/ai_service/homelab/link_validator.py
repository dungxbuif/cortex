from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


EXCLUDE_FOLDERS = {".git", "credentials", "deprecated", "diagnostics", ".terraform", ".venv", "node_modules", "__pycache__"}
EXCLUDE_FILES = {"local_vars.json"}
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def gfm_slugify(heading: str) -> str:
    slug = heading.lower().strip()
    slug = re.sub(r"[^\w\s\-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug.strip("-")


def validate_markdown_links(repo_path: str) -> list[dict[str, Any]]:
    path = Path(repo_path)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

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

            slugs: set[str] = set()
            try:
                with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        match = HEADING_RE.match(line)
                        if match:
                            slugs.add(gfm_slugify(match.group(2)))
            except Exception:
                pass
            heading_slugs[rel_file_path] = slugs

    broken_links: list[dict[str, Any]] = []
    for rel_file_path in md_files:
        abs_file_path = os.path.join(repo_path, rel_file_path)
        source_dir = os.path.dirname(rel_file_path)
        try:
            with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, start=1):
                    for match in LINK_RE.finditer(line):
                        raw_target = match.group(2).split(' "', 1)[0].split(" '", 1)[0].strip()
                        if raw_target.startswith(("http://", "https://", "mailto:", "ftp:", "tel:", "irc:", "magnet:", "file://")):
                            continue

                        parts = raw_target.split("#", 1)
                        link_file_rel = parts[0]
                        anchor = parts[1] if len(parts) > 1 else None
                        resolved_file = rel_file_path if not link_file_rel else os.path.normpath(os.path.join(source_dir, link_file_rel))
                        resolved_file = resolved_file.replace("\\", "/")

                        if resolved_file not in md_files:
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

                        if anchor and resolved_file in heading_slugs:
                            target_slugs = heading_slugs[resolved_file]
                            slugified_anchor = gfm_slugify(anchor)
                            collapsed_anchor = re.sub(r"-+", "-", slugified_anchor)
                            matched = slugified_anchor in target_slugs or any(
                                re.sub(r"-+", "-", target_slug) == collapsed_anchor for target_slug in target_slugs
                            )
                            if not matched:
                                broken_links.append(
                                    {
                                        "source_file": rel_file_path,
                                        "line_number": line_idx,
                                        "raw_link": raw_target,
                                        "reason": f"Anchor '#{anchor}' not found in target file",
                                    }
                                )
        except Exception as exc:
            broken_links.append(
                {
                    "source_file": rel_file_path,
                    "line_number": 1,
                    "raw_link": "",
                    "reason": f"Failed to read file: {exc}",
                }
            )

    return broken_links
