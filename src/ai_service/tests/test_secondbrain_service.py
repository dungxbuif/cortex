from __future__ import annotations

import unittest

from ai_service.core.models import CaptureStatus
from ai_service.secondbrain.service import SecondBrainService
from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository


OWNER_ID = "service-pgvector-owner"


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


class SecondBrainServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.repository = PostgresPsqlSecondBrainRepository.from_env()
            cls.repository.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL pgvector database is not reachable: {exc}") from exc

    def setUp(self) -> None:
        self.repository.clear_owner(OWNER_ID)
        self.service = SecondBrainService(repository=self.repository, embedder=FakeEmbedder())

    def tearDown(self) -> None:
        self.repository.clear_owner(OWNER_ID)

    def test_capture_lifecycle_keeps_capture_out_of_rag(self) -> None:
        self.assertEqual(self.repository.embedding_column_type(), "vector")
        capture = self.service.create_capture(
            "Note lai: Consistent hashing giup scale cache tot hon.",
            owner_id=OWNER_ID,
        )

        self.assertEqual(capture.owner_id, OWNER_ID)
        self.assertEqual(capture.status, CaptureStatus.CAPTURED)
        self.assertIn("rag: false", capture.normalized_markdown)
        self.assertIn("system-design", capture.suggested_tags)

        copied = self.service.mark_capture_copied(capture.id, owner_id=OWNER_ID)
        self.assertEqual(copied.status, CaptureStatus.COPIED)

        exported = self.service.mark_capture_exported(
            capture.id,
            "raw/consistent-hashing-note.md",
            owner_id=OWNER_ID,
        )
        self.assertEqual(exported.status, CaptureStatus.EXPORTED)
        self.assertEqual(exported.vault_path, "raw/consistent-hashing-note.md")

        results = self.service.search_knowledge("consistent hashing cache", owner_id=OWNER_ID)
        self.assertEqual(results, [])

    def test_sync_status_counts_indexed_documents_and_chunks(self) -> None:
        chunk_count = self.service.index_vault_document(
            "wiki/system-design/consistent-hashing.md",
            """---
type: wiki
title: "Consistent Hashing"
tags: [system-design, cache]
---

# Consistent Hashing

Consistent hashing reduces key remapping when cache nodes are added or removed.

## Use cases

Distributed cache systems use it for stable sharding.
""",
            owner_id=OWNER_ID,
        )

        status = self.service.get_sync_status(owner_id=OWNER_ID)
        self.assertEqual(status.total_documents, 1)
        self.assertEqual(status.indexed_documents, 1)
        self.assertEqual(status.failed_documents, 0)
        self.assertEqual(status.total_chunks, chunk_count)
        self.assertGreaterEqual(status.total_chunks, 2)

    def test_search_prefers_wiki_over_raw_for_same_topic(self) -> None:
        self.service.index_vault_document(
            "raw/consistent-hashing-raw.md",
            """---
type: raw
title: "Consistent Hashing Raw"
---

# Scratch

Consistent hashing helps cache scaling.
""",
            owner_id=OWNER_ID,
        )
        self.service.index_vault_document(
            "wiki/system-design/consistent-hashing.md",
            """---
type: wiki
title: "Consistent Hashing"
---

# Consistent Hashing

Consistent hashing reduces key remapping when cache nodes change in distributed systems.
""",
            owner_id=OWNER_ID,
        )

        results = self.service.search_knowledge("consistent hashing cache scaling", owner_id=OWNER_ID, top_k=2)

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0].document.vault_path, "wiki/system-design/consistent-hashing.md")

    def test_policy_excludes_private_rag_false_and_archive_by_default(self) -> None:
        self.service.index_vault_document(
            "wiki/public-python.md",
            """---
type: wiki
title: "Python Learning"
---

# Python Learning

Python decorators wrap functions.
""",
            owner_id=OWNER_ID,
        )
        self.service.index_vault_document(
            "wiki/private-python.md",
            """---
type: wiki
title: "Private Python"
private: true
---

# Private Python

Python secret learning plan.
""",
            owner_id=OWNER_ID,
        )
        self.service.index_vault_document(
            "wiki/rag-disabled.md",
            """---
type: wiki
title: "RAG Disabled"
rag: false
---

# RAG Disabled

Python note that should not appear.
""",
            owner_id=OWNER_ID,
        )
        self.service.index_vault_document(
            "archive/old-python.md",
            """---
type: archive
title: "Old Python"
---

# Old Python

Python legacy archive note.
""",
            owner_id=OWNER_ID,
        )

        results = self.service.search_knowledge("python", owner_id=OWNER_ID, top_k=10)
        paths = [result.document.vault_path for result in results]

        self.assertEqual(paths, ["wiki/public-python.md"])

    def test_validation_rejects_empty_capture_and_non_markdown_export(self) -> None:
        with self.assertRaises(ValueError):
            self.service.create_capture(" ", owner_id=OWNER_ID)

        capture = self.service.create_capture("Temporary note", owner_id=OWNER_ID)
        with self.assertRaises(ValueError):
            self.service.mark_capture_exported(capture.id, "raw/note.txt", owner_id=OWNER_ID)

    def test_index_skips_unmodified_document(self) -> None:
        content = "---\ntype: wiki\ntitle: Unmodified\n---\n# Unmodified\nTest content"
        
        chunks1 = self.service.index_vault_document("wiki/unmod.md", content, owner_id=OWNER_ID)
        self.assertGreater(chunks1, 0)

        chunks2 = self.service.index_vault_document("wiki/unmod.md", content, owner_id=OWNER_ID)
        self.assertEqual(chunks2, 0)

        chunks3 = self.service.index_vault_document("wiki/unmod.md", content + "\nMore", owner_id=OWNER_ID)
        self.assertGreater(chunks3, 0)


if __name__ == "__main__":
    unittest.main()
