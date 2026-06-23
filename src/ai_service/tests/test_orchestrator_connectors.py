from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_service.homelab.repository import SqliteHomelabRepository
from ai_service.homelab.service import HomelabService
from ai_service.orchestrator.connectors import HomelabConnector, SecondBrainConnector
from ai_service.orchestrator.contracts import ConnectorRegistry, ObservationStatus, ToolExecutionContext
from ai_service.orchestrator.registry import DefaultToolRegistry
from ai_service.secondbrain.repository import SqliteSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


def tool_context(owner_id: str = "connector-owner") -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        actor_id="telegram-user",
        actor_type="user",
        conversation_id="conversation-id",
        request_id="request-id",
        channel="telegram",
    )


class SecondBrainConnectorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = SqliteSecondBrainRepository()
        self.service = SecondBrainService(repository=self.repository, embedder=FakeEmbedder())
        self.connector = SecondBrainConnector(self.service)
        self.context = tool_context()

    def tearDown(self) -> None:
        self.repository.close()

    async def test_capture_note_writes_capture_inbox_without_vault_write(self) -> None:
        observation = await self.connector.execute(
            "secondbrain_capture_note",
            "CreateCapture",
            {"content": "Note lai ve consistent hashing", "tags": ["systems"]},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertFalse(observation.data["vault_write"])
        self.assertIn("no Obsidian Vault file", observation.warnings[0])

        captures = self.service.list_captures(owner_id=self.context.owner_id)
        self.assertEqual(len(captures), 1)
        self.assertIn("#systems", captures[0].raw_text)
        self.assertEqual(self.service.search_knowledge("consistent hashing", owner_id=self.context.owner_id), [])

    async def test_search_knowledge_returns_citations_from_indexed_vault_only(self) -> None:
        self.service.index_vault_document(
            "wiki/system-design/consistent-hashing.md",
            """---
type: wiki
title: "Consistent Hashing"
---

# Consistent Hashing

Consistent hashing reduces key movement when cache nodes change.
""",
            owner_id=self.context.owner_id,
        )

        observation = await self.connector.execute(
            "secondbrain_search_knowledge",
            "SearchKnowledge",
            {"query": "consistent hashing cache", "limit": 3},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(observation.citations[0].source_path, "wiki/system-design/consistent-hashing.md")
        self.assertIn("Consistent Hashing", observation.data["results"][0]["title"])

    async def test_registry_validation_for_secondbrain_targets(self) -> None:
        registry = ConnectorRegistry()
        registry.register(self.connector)
        registry.validate_tools(DefaultToolRegistry(), modules={"second_brain"})


class HomelabConnectorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.repository = SqliteHomelabRepository()
        self.service = HomelabService(repository=self.repository, embedder=FakeEmbedder())
        self.connector = HomelabConnector(self.service)
        self.context = tool_context(owner_id="homelab-owner")

    def tearDown(self) -> None:
        self.repository.close()

    async def test_sync_search_and_citation_redacts_sensitive_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = HomelabConnector(self.service, allowed_repo_paths=(temp_dir,))
            path = Path(temp_dir)
            (path / "README.md").write_text(
                "# Homelab Setup\n"
                "Rathole handles edge gateway tunnel forwarding.\n"
                "Public IP is 171.229.241.103.\n",
                encoding="utf-8",
            )

            sync = await connector.execute(
                "homelab_sync_repository",
                "SyncRepository",
                {"repo_path": temp_dir, "commit_sha": "abc123"},
                self.context,
            )
            self.assertEqual(sync.status, ObservationStatus.SUCCESS)
            self.assertEqual(sync.data["processed_files"], 1)

            search = await connector.execute(
                "homelab_search_knowledge",
                "SearchKnowledge",
                {"query": "rathole gateway tunnel", "limit": 1},
                self.context,
            )

        self.assertEqual(search.status, ObservationStatus.SUCCESS)
        self.assertEqual(search.citations[0].source_path, "README.md")
        self.assertEqual(search.citations[0].source_revision, "abc123")
        snippet = search.data["results"][0]["snippet"]
        self.assertIn("<REDACTED_IP>", snippet)
        self.assertNotIn("171.229.241.103", snippet)

    async def test_validate_links_maps_to_service_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = HomelabConnector(self.service, allowed_repo_paths=(temp_dir,))
            path = Path(temp_dir)
            (path / "README.md").write_text("[missing](./missing.md)\n", encoding="utf-8")
            observation = await connector.execute(
                "homelab_validate_links",
                "ValidateLinks",
                {"repo_path": temp_dir},
                self.context,
            )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(len(observation.data["broken_links"]), 1)

    async def test_rejects_unconfigured_repo_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            observation = await self.connector.execute(
                "homelab_validate_links",
                "ValidateLinks",
                {"repo_path": temp_dir},
                self.context,
            )

        self.assertEqual(observation.status, ObservationStatus.PERMISSION_DENIED)
        self.assertEqual(observation.data["reason"], "repo_path_not_allowed")

    async def test_registry_validation_for_homelab_targets(self) -> None:
        registry = ConnectorRegistry()
        registry.register(self.connector)
        registry.validate_tools(DefaultToolRegistry(), modules={"homelab"})


if __name__ == "__main__":
    unittest.main()
