from __future__ import annotations

import json
import unittest
from pathlib import Path

from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService


OWNER_ID = "integration-real-vault-owner"
TESTDATA_ROOT = Path(__file__).parent / "testdata"
VAULT_ROOT = TESTDATA_ROOT / "mock_vault"
GROUND_TRUTH = TESTDATA_ROOT / "ground_truth.json"


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


@unittest.skipUnless(VAULT_ROOT.exists() and GROUND_TRUTH.exists(), "real local Vault testdata is not present")
class PostgresRealVaultIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.repository = PostgresPsqlSecondBrainRepository.from_env()
            cls.repository.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL cortex database is not reachable: {exc}") from exc
        cls.service = SecondBrainService(repository=cls.repository, embedder=FakeEmbedder())

    def setUp(self) -> None:
        self.repository.clear_owner(OWNER_ID)

    def tearDown(self) -> None:
        self.repository.clear_owner(OWNER_ID)

    def test_real_vault_indexes_into_postgres_and_passes_ground_truth(self) -> None:
        indexed_files = 0
        for path in VAULT_ROOT.rglob("*.md"):
            vault_path = path.relative_to(VAULT_ROOT).as_posix()
            self.service.index_vault_document(vault_path, path.read_text(errors="ignore"), owner_id=OWNER_ID)
            indexed_files += 1

        status = self.service.get_sync_status(owner_id=OWNER_ID)
        self.assertEqual(status.total_documents, indexed_files)
        self.assertEqual(status.indexed_documents, indexed_files)
        self.assertGreater(status.total_chunks, indexed_files)
        self.assertEqual(self.repository.embedding_column_type(), "vector")

        ground_truth = json.loads(GROUND_TRUTH.read_text())
        failures: list[str] = []
        for row in ground_truth:
            top_k = int(row["expected_top_k"])
            results = self.service.search_knowledge(row["question"], owner_id=OWNER_ID, top_k=max(top_k, 5))
            paths = [result.document.vault_path for result in results]
            expected = row["expected_files"]
            if expected:
                passed = all(path in paths[:top_k] for path in expected)
            else:
                passed = not paths[:top_k]
            if not passed:
                failures.append(f"{row['id']}: expected={expected} got={paths[:5]}")

        self.assertEqual(failures, [])

    def test_capture_records_are_written_to_postgres_but_not_returned_by_rag(self) -> None:
        capture = self.service.create_capture(
            "Note lai: Capture inbox khong duoc RAG doc truc tiep.",
            owner_id=OWNER_ID,
        )

        stored = self.service.get_capture(capture.id, owner_id=OWNER_ID)
        self.assertEqual(stored.id, capture.id)
        self.assertIn("rag: false", stored.normalized_markdown)
        self.assertEqual(self.service.search_knowledge("Capture inbox RAG", owner_id=OWNER_ID), [])


if __name__ == "__main__":
    unittest.main()
