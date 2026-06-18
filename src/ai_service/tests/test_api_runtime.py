from __future__ import annotations

import unittest

from ai_service.homelab.repository import PostgresPsqlHomelabRepository
from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository

OWNER_ID = "api-pgvector-owner"


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


class FastAPIRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.repository = PostgresPsqlSecondBrainRepository.from_env()
            self.homelab_repository = PostgresPsqlHomelabRepository.from_env()
            self.repository.ping()
            self.homelab_repository.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL pgvector database is not reachable: {exc}") from exc
        self.repository.clear_owner(OWNER_ID)
        self.homelab_repository.clear_homelab_owner(OWNER_ID)

    def tearDown(self) -> None:
        self.repository.clear_owner(OWNER_ID)
        self.homelab_repository.clear_homelab_owner(OWNER_ID)

    def test_create_app_exposes_expected_routes_and_handles_requests(self) -> None:
        try:
            from ai_service.api import create_app
            from fastapi.testclient import TestClient
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc)) from exc

        app = create_app(
            secondbrain_repository=self.repository,
            homelab_repository=self.homelab_repository,
            embedder=FakeEmbedder(),
        )
        paths = {route.path for route in app.routes}

        self.assertIn("/api/v1/capture", paths)
        self.assertIn("/api/v1/sync/status", paths)
        self.assertIn("/api/v1/search", paths)
        self.assertIn("/api/v1/homelab/sync", paths)
        self.assertIn("/api/v1/homelab/search", paths)
        self.assertIn("/api/v1/homelab/validate-links", paths)
        self.assertEqual(self.repository.embedding_column_type(), "vector")

        client = TestClient(app)
        
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with open(temp_path / "README.md", "w") as f:
                f.write("# README\nLink to [other](./other.md)\n")
            
            validate_res = client.post(
                "/api/v1/homelab/validate-links",
                json={"repo_path": temp_dir}
            )
            self.assertEqual(validate_res.status_code, 200)
            self.assertIn("broken_links", validate_res.json())
            self.assertEqual(len(validate_res.json()["broken_links"]), 1)

        create_response = client.post(
            "/api/v1/capture",
            json={
                "owner_id": OWNER_ID,
                "raw_text": "Note lai: API capture khong duoc RAG doc truc tiep.",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertIn("rag: false", create_response.json()["normalized_markdown"])

        list_response = client.get("/api/v1/capture", params={"owner_id": OWNER_ID})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        sync_response = client.get("/api/v1/sync/status", params={"owner_id": OWNER_ID})
        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(sync_response.json()["total_documents"], 0)

        search_response = client.post(
            "/api/v1/search",
            json={"owner_id": OWNER_ID, "query": "API capture RAG", "top_k": 5},
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json(), [])


if __name__ == "__main__":
    unittest.main()
