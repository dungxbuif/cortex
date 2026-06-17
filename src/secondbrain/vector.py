from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
VECTOR_DIMENSIONS = 768


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in TOKEN_RE.findall(text))


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def lexical_overlap(query: str, content: str) -> float:
    query_tokens = set(tokenize(query))
    content_tokens = set(tokenize(content))
    if not query_tokens or not content_tokens:
        return 0.0
    return len(query_tokens & content_tokens) / len(query_tokens)
