from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_service.api import create_app
from ai_service.homelab.repository import SqliteHomelabRepository
from ai_service.secondbrain.repository import SqliteSecondBrainRepository


OWNER_ID = "11111111-1111-1111-1111-111111111111"
S3_TOKEN = "test-s3-token"


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


class S3WebhookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.secondbrain_root = self.root / "second-brain"
        self.homelab_root = self.root / "homelab"
        self.secondbrain_root.mkdir()
        self.homelab_root.mkdir()
        self.secondbrain_repo = SqliteSecondBrainRepository()
        self.homelab_repo = SqliteHomelabRepository()

        with patch.dict("os.environ", {"CORTEX_S3_WEBHOOK_TOKEN": S3_TOKEN}):
            self.app = create_app(
                secondbrain_repository=self.secondbrain_repo,
                homelab_repository=self.homelab_repo,
                embedder=FakeEmbedder(),
                s3_secondbrain_root=str(self.secondbrain_root),
                s3_homelab_root=str(self.homelab_root),
            )

        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)
        self.headers = {"X-Cortex-S3-Token": S3_TOKEN}

    def tearDown(self) -> None:
        self.secondbrain_repo.close()
        self.homelab_repo.close()
        self.temp_dir.cleanup()

    def test_rejects_missing_and_wrong_token(self) -> None:
        payload = self._payload("second_brain", "write")

        missing = self.client.post("/api/webhooks/s3", json=payload)
        wrong = self.client.post(
            "/api/webhooks/s3",
            headers={"X-Cortex-S3-Token": "wrong"},
            json=payload,
        )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)

    def test_rejects_invalid_domain_event_and_path(self) -> None:
        bad_domain = self._payload("finance", "write", "wiki/a.md")
        bad_event = self._payload("second_brain", "chmod", "wiki/a.md")
        traversal = {
            "source": "s3",
            "domain": "second_brain",
            "event_type": "write",
            "absolute_path": str(self.secondbrain_root / "secret.md"),
            "relative_path": "../secret.md",
        }

        self.assertEqual(self.client.post("/api/webhooks/s3", headers=self.headers, json=bad_domain).status_code, 400)
        self.assertEqual(self.client.post("/api/webhooks/s3", headers=self.headers, json=bad_event).status_code, 400)
        self.assertEqual(self.client.post("/api/webhooks/s3", headers=self.headers, json=traversal).status_code, 400)

    def test_second_brain_webhook_resyncs_entire_root(self) -> None:
        self._write(self.secondbrain_root, "wiki/s3-sb.md", "# S3 SB\nunique secondbrain s3 phrase")
        self._write(self.secondbrain_root, "dailylogs/another.md", "# Another\nsecondbrain full resync phrase")

        response = self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("second_brain", "write"),
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["result"]["status"], "success")
        self.assertEqual(response.json()["result"]["processed_files"], 2)
        results = self.secondbrain_repo.list_searchable_chunks(OWNER_ID)
        self.assertEqual({doc.vault_path for doc, _ in results}, {"wiki/s3-sb.md", "dailylogs/another.md"})

    def test_second_brain_remove_triggers_full_resync_and_clears_stale_index(self) -> None:
        path = self._write(self.secondbrain_root, "wiki/remove-sb.md", "# Remove SB\nunique removal phrase")
        self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("second_brain", "write", "wiki/remove-sb.md", path),
        )
        path.unlink()

        response = self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("second_brain", "remove"),
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["result"]["status"], "success")
        self.assertEqual(response.json()["result"]["deleted_files"], 1)
        self.assertEqual(self.secondbrain_repo.list_searchable_chunks(OWNER_ID), [])

    def test_homelab_webhook_resyncs_entire_root_with_redaction(self) -> None:
        self._write(self.homelab_root, "docs/s3-hl.md", "# S3 HL\nhomelab s3 secret TOKEN=abc12345")
        self._write(self.homelab_root, "docs/another.md", "# Another\nhomelab full resync phrase")

        response = self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("homelab", "create"),
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["result"]["status"], "success")
        self.assertEqual(response.json()["result"]["processed_files"], 2)
        rows = self.homelab_repo.list_searchable_homelab_chunks(OWNER_ID)
        self.assertEqual({doc.file_path for doc, _ in rows}, {"docs/s3-hl.md", "docs/another.md"})
        redacted = next(chunk.content for doc, chunk in rows if doc.file_path == "docs/s3-hl.md")
        self.assertNotIn("abc12345", redacted)

    def test_homelab_remove_triggers_full_resync_and_clears_stale_index(self) -> None:
        path = self._write(self.homelab_root, "docs/remove-hl.md", "# Remove HL\nhomelab removal phrase")
        self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("homelab", "write", "docs/remove-hl.md", path),
        )
        path.unlink()

        response = self.client.post(
            "/api/webhooks/s3",
            headers=self.headers,
            json=self._payload("homelab", "delete"),
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["result"]["status"], "success")
        self.assertEqual(response.json()["result"]["deleted_files"], 1)
        self.assertEqual(self.homelab_repo.list_searchable_homelab_chunks(OWNER_ID), [])

    def _payload(
        self,
        domain: str,
        event_type: str,
        relative_path: str | None = None,
        path: Path | None = None,
    ) -> dict[str, str]:
        root = self.secondbrain_root if domain == "second_brain" else self.homelab_root
        payload = {
            "source": "s3",
            "domain": domain,
            "event_type": event_type,
        }
        if relative_path is not None:
            payload["relative_path"] = relative_path
            payload["absolute_path"] = str(path or (root / relative_path))
        return payload

    def _write(self, root: Path, relative_path: str, content: str) -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
