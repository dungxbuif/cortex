from __future__ import annotations

import unittest

from ai_service.core.models import CaptureStatus, IndexStatus, utc_now
from ai_service.homelab.models import HomelabChunk, HomelabDocument
from ai_service.homelab.repository import PostgresPsqlHomelabRepository, SqliteHomelabRepository
from ai_service.secondbrain.models import Capture, VaultChunk, VaultDocument
from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository, SqliteSecondBrainRepository


SB_OWNER = "contract-secondbrain-owner"
HL_OWNER = "contract-homelab-owner"


class SecondBrainRepositoryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.postgres = PostgresPsqlSecondBrainRepository.from_env()
            cls.postgres.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL pgvector database is not reachable: {exc}") from exc

    def setUp(self) -> None:
        self.sqlite = SqliteSecondBrainRepository()
        self.postgres.clear_owner(SB_OWNER)

    def tearDown(self) -> None:
        self.sqlite.close()
        self.postgres.clear_owner(SB_OWNER)

    def test_capture_document_search_and_status_contract(self) -> None:
        for repo in (self.sqlite, self.postgres):
            now = utc_now()
            capture = Capture(
                id=f"{repo.__class__.__name__}-capture",
                owner_id=SB_OWNER,
                status=CaptureStatus.CAPTURED,
                source="contract",
                raw_text="Contract note",
                normalized_markdown="---\nrag: false\n---\nContract note",
                suggested_tags=("contract",),
                vault_path=None,
                created_at=now,
                updated_at=now,
            )
            repo.save_capture(capture)
            self.assertEqual(repo.get_capture(SB_OWNER, capture.id).status, CaptureStatus.CAPTURED)
            self.assertEqual(len(repo.list_captures(SB_OWNER)), 1)

            document = VaultDocument(
                id=f"{repo.__class__.__name__}-doc",
                owner_id=SB_OWNER,
                vault_path="wiki/contract.md",
                checksum=f"{repo.__class__.__name__}-checksum",
                document_type="wiki",
                title="Contract",
                frontmatter={"type": "wiki"},
                rag_allowed=True,
                private=False,
                archived=False,
                index_status=IndexStatus.INDEXED,
                indexed_at=now,
            )
            chunk = VaultChunk(
                id=f"{repo.__class__.__name__}-chunk",
                document_id=document.id,
                owner_id=SB_OWNER,
                vault_path=document.vault_path,
                chunk_index=0,
                content="Repository contract content",
                heading_chain=("Contract",),
                token_count=3,
                embedding=tuple(0.01 if i == 0 else 0.0 for i in range(768)),
            )
            repo.upsert_document_with_chunks(document, [chunk])

            self.assertEqual(repo.get_document(SB_OWNER, document.vault_path).id, document.id)
            searchable = repo.list_searchable_chunks(SB_OWNER)
            self.assertEqual(len(searchable), 1)
            self.assertEqual(searchable[0][0].vault_path, document.vault_path)
            self.assertEqual(searchable[0][1].content, chunk.content)

            status = repo.sync_status(SB_OWNER)
            self.assertEqual(status.total_documents, 1)
            self.assertEqual(status.indexed_documents, 1)
            self.assertEqual(status.total_chunks, 1)


class HomelabRepositoryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.postgres = PostgresPsqlHomelabRepository.from_env()
            cls.postgres.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL pgvector database is not reachable: {exc}") from exc

    def setUp(self) -> None:
        self.sqlite = SqliteHomelabRepository()
        self.postgres.clear_homelab_owner(HL_OWNER)

    def tearDown(self) -> None:
        self.sqlite.close()
        self.postgres.clear_homelab_owner(HL_OWNER)

    def test_document_chunk_and_status_contract(self) -> None:
        for repo in (self.sqlite, self.postgres):
            now = utc_now()
            document = HomelabDocument(
                id=f"{repo.__class__.__name__}-doc",
                owner_id=HL_OWNER,
                repo_url="github.com/dungxbuif/Homelab",
                branch="main",
                commit_sha="contract",
                file_path="README.md",
                checksum=f"{repo.__class__.__name__}-checksum",
                index_status="indexed",
                indexed_at=now,
            )
            chunk = HomelabChunk(
                id=f"{repo.__class__.__name__}-chunk",
                document_id=document.id,
                owner_id=HL_OWNER,
                file_path=document.file_path,
                chunk_index=0,
                content="Homelab repository contract content",
                heading_chain=("Homelab",),
                token_count=4,
                embedding=tuple(0.01 if i == 0 else 0.0 for i in range(768)),
            )
            repo.upsert_homelab_document_with_chunks(document, [chunk])

            self.assertEqual(repo.get_homelab_document(HL_OWNER, document.file_path).id, document.id)
            searchable = repo.list_searchable_homelab_chunks(HL_OWNER)
            self.assertEqual(len(searchable), 1)
            self.assertEqual(searchable[0][0].file_path, document.file_path)
            self.assertEqual(searchable[0][1].content, chunk.content)

            status = repo.sync_homelab_status(HL_OWNER)
            self.assertEqual(status.total_documents, 1)
            self.assertEqual(status.indexed_documents, 1)
            self.assertEqual(status.total_chunks, 1)


if __name__ == "__main__":
    unittest.main()
