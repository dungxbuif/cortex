from __future__ import annotations

import uuid

from .markdown import build_document, chunk_markdown, normalize_capture_markdown, suggest_tags
from .object_store import ObjectStore, normalize_object_key
from ai_service.core.models import CaptureStatus, DEFAULT_OWNER_ID, utc_now
from ai_service.core.ports import Embedder, SecondBrainRepository
from ai_service.core.vector import cosine_similarity, tokenize
from ai_service.secondbrain.models import Capture, RawChunk, SearchResult, SyncStatus, VaultChunk
from ai_service.secondbrain.repository import SqliteSecondBrainRepository

MIN_SEARCH_SCORE = 0.16
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "vs",
    "what",
    "with",
    "ai",
    "anh",
    "bao",
    "bi",
    "cac",
    "cach",
    "can",
    "cho",
    "co",
    "cua",
    "duoc",
    "gi",
    "giua",
    "gia",
    "ha",
    "he",
    "hom",
    "khong",
    "la",
    "lam",
    "nao",
    "nay",
    "nhieu",
    "ngay",
    "ngon",
    "nhat",
    "nhu",
    "nhung",
    "noi",
    "nau",
    "ra",
    "sao",
    "sjc",
    "the",
    "thi",
    "thoi",
    "tiet",
    "trong",
    "va",
    "vang",
    "voi",
    "bo",
    "pho",
}


class SecondBrainService:
    def __init__(
        self,
        repository: SecondBrainRepository | None = None,
        embedder: Embedder | None = None,
        ai_client: Embedder | None = None,
        object_store: ObjectStore | None = None,
        allowed_bucket: str | None = None,
        object_prefix: str = "second-brain/",
    ) -> None:
        self.repository = repository or SqliteSecondBrainRepository()
        self.embedder = embedder or ai_client or _default_embedder()
        self.object_store = object_store
        self.allowed_bucket = allowed_bucket
        self.object_prefix = object_prefix

    def create_capture(
        self,
        raw_text: str,
        source: str = "chat",
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> Capture:
        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text is required")
        now = utc_now()
        capture = Capture(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            status=CaptureStatus.CAPTURED,
            source=source,
            raw_text=raw_text.strip(),
            normalized_markdown=normalize_capture_markdown(raw_text, source),
            suggested_tags=suggest_tags(raw_text),
            vault_path=None,
            created_at=now,
            updated_at=now,
        )
        return self.repository.save_capture(capture)

    def list_captures(self, owner_id: str = DEFAULT_OWNER_ID) -> list[Capture]:
        return self.repository.list_captures(owner_id)

    def get_capture(self, capture_id: str, owner_id: str = DEFAULT_OWNER_ID) -> Capture:
        capture = self.repository.get_capture(owner_id, capture_id)
        if capture is None:
            raise KeyError(f"capture not found: {capture_id}")
        return capture

    def mark_capture_copied(self, capture_id: str, owner_id: str = DEFAULT_OWNER_ID) -> Capture:
        return self.repository.update_capture_status(owner_id, capture_id, CaptureStatus.COPIED, utc_now())

    def mark_capture_exported(
        self,
        capture_id: str,
        vault_path: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> Capture:
        if not vault_path or not vault_path.endswith(".md"):
            raise ValueError("vault_path must be a markdown file")
        return self.repository.update_capture_status(
            owner_id,
            capture_id,
            CaptureStatus.EXPORTED,
            utc_now(),
            vault_path=vault_path,
        )

    def discard_capture(self, capture_id: str, owner_id: str = DEFAULT_OWNER_ID) -> Capture:
        return self.repository.update_capture_status(owner_id, capture_id, CaptureStatus.DISCARDED, utc_now())

    def index_vault_document(
        self,
        vault_path: str,
        markdown: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> int:
        if not vault_path.endswith(".md"):
            raise ValueError("vault_path must be a markdown file")
        document = build_document(owner_id, vault_path, markdown)
        existing = self.repository.get_document(owner_id, vault_path)
        if existing is not None and existing.checksum == document.checksum:
            return 0
        chunks = _attach_embeddings(chunk_markdown(owner_id, document, markdown), self.embedder)
        self.repository.upsert_document_with_chunks(document, chunks)
        return len(chunks)

    def sync_minio_object(
        self,
        bucket: str,
        object_key: str,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> dict[str, int | str]:
        key = normalize_object_key(object_key)
        if self.allowed_bucket and bucket != self.allowed_bucket:
            raise ValueError("bucket is not allowed")
        if not key.startswith(self.object_prefix):
            return _sync_result("skipped", key, "object outside second-brain prefix", skipped=1)
        if not key.endswith(".md"):
            return _sync_result("skipped", key, "object is not markdown", skipped=1)
        if self.object_store is None:
            raise RuntimeError("object store is not configured")

        markdown = self.object_store.get_text_object(bucket, key)
        vault_path = key[len(self.object_prefix) :]
        if not vault_path:
            return _sync_result("skipped", key, "object key has no vault path", skipped=1)
        chunks = self.index_vault_document(vault_path, markdown, owner_id=owner_id)
        if chunks == 0:
            return _sync_result("skipped", key, "unchanged content", skipped=1)
        return _sync_result("indexed", key, f"indexed {chunks} chunks", processed=1)

    def get_sync_status(self, owner_id: str = DEFAULT_OWNER_ID) -> SyncStatus:
        return self.repository.sync_status(owner_id)

    def search_knowledge(
        self,
        query: str,
        owner_id: str = DEFAULT_OWNER_ID,
        top_k: int = 5,
        include_archive: bool = False,
    ) -> list[SearchResult]:
        if not query or not query.strip():
            raise ValueError("query is required")
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        query_tokens = _meaningful_tokens(query)
        joined_query = " ".join(query_tokens)
        if not joined_query:
            return []

        query_embedding = self.embedder.embed_text(joined_query)
        candidates = self.repository.list_searchable_chunks(owner_id, include_archive=include_archive)
        best_by_document: dict[str, SearchResult] = {}

        for document, chunk in candidates:
            score, reasons = _score_candidate(query_tokens, query_embedding, document, chunk)
            if score < MIN_SEARCH_SCORE:
                continue
            result = SearchResult(chunk=chunk, document=document, score=score, reasons=reasons)
            current = best_by_document.get(document.id)
            if current is None or result.score > current.score:
                best_by_document[document.id] = result

        results = list(best_by_document.values())
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]


def _score_candidate(
    query_tokens: set[str],
    query_embedding: tuple[float, ...],
    document,
    chunk,
) -> tuple[float, tuple[str, ...]]:
    search_text = " ".join([document.title, document.vault_path, chunk.content, *chunk.heading_chain])
    content_tokens = _meaningful_tokens(search_text)
    if not query_tokens or not content_tokens:
        return 0.0, ("empty_tokens",)

    overlap = query_tokens & content_tokens
    if not overlap:
        return 0.0, ("no_lexical_overlap",)

    recall = len(overlap) / len(query_tokens)
    precision = len(overlap) / max(len(content_tokens), 1)
    path_tokens = _meaningful_tokens(document.vault_path.replace("/", " ").replace("-", " ").replace("_", " "))
    title_tokens = _meaningful_tokens(document.title)
    path_overlap = len(query_tokens & path_tokens) / max(min(len(query_tokens), len(path_tokens)), 1)
    title_overlap = len(query_tokens & title_tokens) / max(min(len(query_tokens), len(title_tokens)), 1)
    vector_score = cosine_similarity(query_embedding, chunk.embedding) if recall > 0 else 0.0
    lifecycle_boost, lifecycle_reason = _lifecycle_boost(document.document_type)
    score = (
        0.48 * recall
        + 0.18 * path_overlap
        + 0.16 * title_overlap
        + 0.08 * min(precision * 8, 1.0)
        + 0.06 * vector_score
        + lifecycle_boost
    )
    reasons = (
        f"recall={recall:.3f}",
        f"path={path_overlap:.3f}",
        f"title={title_overlap:.3f}",
        f"precision={precision:.3f}",
        f"vector={vector_score:.3f}",
        lifecycle_reason,
    )
    return score, reasons


def _meaningful_tokens(text: str) -> set[str]:
    normalized = _expand_query_text(_normalize_vietnamese(text))
    return {token for token in tokenize(normalized) if len(token) >= 2 and token not in STOPWORDS}


def _expand_query_text(text: str) -> str:
    expansions: list[str] = []
    if "message queue" in text or "queue" in text:
        expansions.append("rabbitmq streams super streams classic queues kafka nats")
    if "throughput" in text or "msg" in text:
        expansions.append("streams batching msg throughput")
    if "document ai" in text or "ocr" in text:
        expansions.append("layoutlm vintern banking document understanding")
    if "kubernetes" in text or "homelab" in text:
        expansions.append("proxmox cilium longhorn kube-vip argocd")
    return " ".join([text, *expansions])


def _normalize_vietnamese(text: str) -> str:
    replacements = str.maketrans(
        {
            "à": "a",
            "á": "a",
            "ạ": "a",
            "ả": "a",
            "ã": "a",
            "â": "a",
            "ầ": "a",
            "ấ": "a",
            "ậ": "a",
            "ẩ": "a",
            "ẫ": "a",
            "ă": "a",
            "ằ": "a",
            "ắ": "a",
            "ặ": "a",
            "ẳ": "a",
            "ẵ": "a",
            "è": "e",
            "é": "e",
            "ẹ": "e",
            "ẻ": "e",
            "ẽ": "e",
            "ê": "e",
            "ề": "e",
            "ế": "e",
            "ệ": "e",
            "ể": "e",
            "ễ": "e",
            "ì": "i",
            "í": "i",
            "ị": "i",
            "ỉ": "i",
            "ĩ": "i",
            "ò": "o",
            "ó": "o",
            "ọ": "o",
            "ỏ": "o",
            "õ": "o",
            "ô": "o",
            "ồ": "o",
            "ố": "o",
            "ộ": "o",
            "ổ": "o",
            "ỗ": "o",
            "ơ": "o",
            "ờ": "o",
            "ớ": "o",
            "ợ": "o",
            "ở": "o",
            "ỡ": "o",
            "ù": "u",
            "ú": "u",
            "ụ": "u",
            "ủ": "u",
            "ũ": "u",
            "ư": "u",
            "ừ": "u",
            "ứ": "u",
            "ự": "u",
            "ử": "u",
            "ữ": "u",
            "ỳ": "y",
            "ý": "y",
            "ỵ": "y",
            "ỷ": "y",
            "ỹ": "y",
            "đ": "d",
        }
    )
    return text.lower().translate(replacements)


def _lifecycle_boost(document_type: str) -> tuple[float, str]:
    normalized = document_type.lower()
    if normalized == "wiki":
        return 0.10, "lifecycle=wiki_boost"
    if normalized == "staging":
        return 0.08, "lifecycle=staging_boost"
    if normalized == "raw":
        return 0.00, "lifecycle=raw_boost"
    return 0.0, "lifecycle=no_boost"


def _default_embedder() -> Embedder:
    from ai_service.providers.embedding import default_embedder

    return default_embedder()


def _attach_embeddings(raw_chunks: list[RawChunk], embedder: Embedder) -> list[VaultChunk]:
    vectors = embedder.embed_batch([chunk.content for chunk in raw_chunks]) if raw_chunks else []
    return [
        VaultChunk(
            id=chunk.id,
            document_id=chunk.document_id,
            owner_id=chunk.owner_id,
            vault_path=chunk.vault_path,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            heading_chain=chunk.heading_chain,
            token_count=chunk.token_count,
            embedding=vector,
        )
        for chunk, vector in zip(raw_chunks, vectors, strict=True)
    ]


def _sync_result(
    status: str,
    object_key: str,
    message: str,
    processed: int = 0,
    skipped: int = 0,
    failed: int = 0,
) -> dict[str, int | str]:
    return {
        "status": status,
        "processed_files": processed,
        "skipped_files": skipped,
        "failed_files": failed,
        "object_key": object_key,
        "message": message,
    }
