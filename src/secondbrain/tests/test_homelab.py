from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from secondbrain.homelab import HomelabService, redact_secrets, gfm_slugify
from secondbrain.models import HomelabDocument, HomelabChunk
from secondbrain.repository import SqliteSecondBrainRepository, PostgresPsqlSecondBrainRepository


class MockGoogleAIClient:
    def embed_text(self, text: str) -> tuple[float, ...]:
        # Return a mock 768-dimensional vector
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))


class HomelabServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = SqliteSecondBrainRepository()
        self.ai_client = MockGoogleAIClient()
        self.service = HomelabService(repository=self.repository, ai_client=self.ai_client)

    def tearDown(self) -> None:
        self.repository.close()

    def test_gfm_slugify(self) -> None:
        self.assertEqual(gfm_slugify("Introduction"), "introduction")
        self.assertEqual(gfm_slugify("## 🚀 Service Export Playbook (End-to-End)"), "service-export-playbook-end-to-end")
        self.assertEqual(gfm_slugify("MikroTik Router Configuration & Network Guide"), "mikrotik-router-configuration-network-guide")
        self.assertEqual(gfm_slugify("Centralized PostgreSQL (06/06/2026)"), "centralized-postgresql-06062026")

    def test_redact_secrets(self) -> None:
        raw_text = (
            "ISP WAN IP: 171.229.241.103, local IP: 192.168.1.10\n"
            "password: 'my-super-secret-password'\n"
            "db_secret = \"some_auth_token_here\"\n"
        )
        redacted = redact_secrets(raw_text)
        self.assertIn("192.168.1.10", redacted)  # Local IPs should be preserved
        self.assertNotIn("171.229.241.103", redacted)  # Public IP redacted
        self.assertIn("<REDACTED_IP>", redacted)
        self.assertNotIn("my-super-secret-password", redacted)
        self.assertNotIn("some_auth_token_here", redacted)
        self.assertIn("password: <REDACTED_SECRET>", redacted)
        self.assertIn("db_secret = <REDACTED_SECRET>", redacted)

    def test_validate_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files
            (temp_path / "docs").mkdir()
            (temp_path / "iac").mkdir()

            # AGENT.md
            with open(temp_path / "AGENT.md", "w") as f:
                f.write(
                    "# Gateway\n"
                    "Valid link: [docs/CONTEXT.md](./docs/CONTEXT.md)\n"
                    "Broken link: [broken-file.md](./broken-file.md)\n"
                    "Anchor link check: [docs/PI.md#installation](./docs/PI.md#installation)\n"
                    "Broken anchor check: [docs/PI.md#non-existent](./docs/PI.md#non-existent)\n"
                )

            # docs/CONTEXT.md
            with open(temp_path / "docs" / "CONTEXT.md", "w") as f:
                f.write("# Context\n")

            # docs/PI.md
            with open(temp_path / "docs" / "PI.md", "w") as f:
                f.write(
                    "## 🚀 Installation\n"
                    "Caddy specifications here.\n"
                )

            # iac/README.md
            with open(temp_path / "iac" / "README.md", "w") as f:
                f.write(
                    "- Gateway reference: [AGENT.md](../AGENT.md)\n"
                    "- Missing file: [deploy.tf](./deploy.tf)\n"
                )

            # credentials/secret.txt (Excluded directory, should not cause validation alert)
            (temp_path / "credentials").mkdir()
            with open(temp_path / "credentials" / "secret.txt", "w") as f:
                f.write("sensitive data")

            # Run link validator
            broken = self.service.validate_markdown_links(temp_dir)
            
            # Assert broken links report contents
            self.assertEqual(len(broken), 3)
            
            broken_map = {(b["source_file"], b["raw_link"]): b for b in broken}
            
            # 1. Broken file check in AGENT.md
            self.assertIn(("AGENT.md", "./broken-file.md"), broken_map)
            self.assertEqual(broken_map[("AGENT.md", "./broken-file.md")]["reason"], "File not found")
            
            # 2. Broken anchor check in AGENT.md
            self.assertIn(("AGENT.md", "./docs/PI.md#non-existent"), broken_map)
            self.assertIn("not found in target file", broken_map[("AGENT.md", "./docs/PI.md#non-existent")]["reason"])

            # 3. Missing IaC file check in iac/README.md
            self.assertIn(("iac/README.md", "./deploy.tf"), broken_map)

    def test_sync_and_search_rag_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with open(temp_path / "README.md", "w") as f:
                f.write(
                    "# Homelab Setup\n"
                    "This is the README for our edge gateway.\n"
                    "## VPS configuration\n"
                    "IP public is 171.229.241.103 and port is 7000.\n"
                )

            sync_res = self.service.sync_repository(temp_dir, owner_id="test-owner")
            self.assertEqual(sync_res["processed_files"], 1)

            # Retrieve sync status
            status = self.repository.sync_homelab_status("test-owner")
            self.assertEqual(status.total_documents, 1)
            self.assertEqual(status.indexed_documents, 1)

            # Query search
            matches = self.service.search_knowledge("vps configuration edge gateway", owner_id="test-owner")
            self.assertGreaterEqual(len(matches), 1)
            self.assertEqual(matches[0].document.file_path, "README.md")
            
            # Public IP should be redacted in all retrieved chunks
            contents = [m.chunk.content for m in matches]
            self.assertTrue(any("<REDACTED_IP>" in c for c in contents))
            self.assertTrue(all("171.229.241.103" not in c for c in contents))

    def test_real_exam_link_validation(self) -> None:
        exam_path = "/Users/dungxbuif/workspace/cortex/exam"
        if os.path.exists(exam_path):
            broken = self.service.validate_markdown_links(exam_path)
            self.assertGreater(len(broken), 0)  # We expect at least the deprecated path links to be broken
            print(f"\n[REAL EXAM BROKEN LINKS REPORT] Found {len(broken)} broken links:")
            for b in broken:
                print(f"  - {b['source_file']}:{b['line_number']} -> {b['raw_link']} ({b['reason']})")


class HomelabPostgresIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.repository = PostgresPsqlSecondBrainRepository.from_env()
            cls.repository.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL pgvector database is not reachable: {exc}") from exc
        cls.ai_client = MockGoogleAIClient()
        cls.service = HomelabService(repository=cls.repository, ai_client=cls.ai_client)

    def setUp(self) -> None:
        self.repository.clear_homelab_owner("integration-owner")

    def tearDown(self) -> None:
        self.repository.clear_homelab_owner("integration-owner")

    def test_postgres_sync_and_search_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with open(temp_path / "README.md", "w") as f:
                f.write(
                    "# Homelab Architecture\n"
                    "We run Rathole for traffic tunnel forwarding.\n"
                )

            res = self.service.sync_repository(temp_dir, owner_id="integration-owner")
            self.assertEqual(res["processed_files"], 1)

            # Verify RAG search with pgvector query in Postgres
            matches = self.service.search_knowledge("traffic tunnel forwarding rathole", owner_id="integration-owner")
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].document.file_path, "README.md")
            self.assertIn("Rathole", matches[0].chunk.content)


if __name__ == "__main__":
    unittest.main()
