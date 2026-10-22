from __future__ import annotations

import unittest
import re

from ai_service.homelab.repository import PostgresPsqlHomelabRepository
from ai_service.secondbrain.repository import PostgresPsqlSecondBrainRepository

OWNER_ID = "11111111-1111-1111-1111-111111111111"


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
        self.assertIn("/api/ai/health", paths)
        self.assertIn("/api/auth/dev-token", paths)
        self.assertIn("/health", paths)
        self.assertIn("/ui", paths)
        self.assertIn("/ui/assets/{asset_path:path}", paths)
        self.assertIn("/v1/chat/completions", paths)

        # Public routes
        self.assertIn("/api/secondbrain/captures", paths)
        self.assertIn("/api/secondbrain/status", paths)
        self.assertIn("/api/secondbrain/search", paths)
        self.assertIn("/api/homelab/sync", paths)
        self.assertIn("/api/homelab/search", paths)
        self.assertIn("/api/homelab/validate-links", paths)
        self.assertIn("/api/webhooks/n8n/secondbrain/obsidian-sync", paths)
        self.assertIn("/api/webhooks/s3", paths)
        self.assertIn("/api/webhooks/rustfs", paths)

        self.assertEqual(self.repository.embedding_column_type(), "vector")

        client = TestClient(app)

        health_response = client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json()["status"], "ok")

        unauth_health_response = client.get("/api/ai/health")
        self.assertEqual(unauth_health_response.status_code, 401)

        token_response = client.get("/api/auth/dev-token")
        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response.json()["user_id"], OWNER_ID)
        auth_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

        ai_health_response = client.get("/api/ai/health", headers=auth_headers)
        self.assertEqual(ai_health_response.status_code, 200)
        self.assertEqual(ai_health_response.json()["gateway"], "python")

        ui_response = client.get("/ui")
        self.assertEqual(ui_response.status_code, 200)
        self.assertIn("Cortex", ui_response.text)
        self.assertIn("/ui/assets/", ui_response.text)

        asset_paths = re.findall(r"/ui/assets/[^\"']+", ui_response.text)
        if asset_paths:
            asset_response = client.get(asset_paths[0])
            self.assertEqual(asset_response.status_code, 200)

        missing_asset_response = client.get("/ui/assets/secret.env")
        self.assertEqual(missing_asset_response.status_code, 404)
        
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with open(temp_path / "README.md", "w") as f:
                f.write("# README\nLink to [other](./other.md)\n")
            
            validate_res = client.post(
                "/api/v1/homelab/validate-links",
                headers=auth_headers,
                json={"repo_path": temp_dir}
            )
            self.assertEqual(validate_res.status_code, 200)
            self.assertIn("broken_links", validate_res.json())
            self.assertEqual(len(validate_res.json()["broken_links"]), 1)

            # Test public link validation
            pub_validate_res = client.post(
                "/api/homelab/validate-links",
                headers=auth_headers,
                json={"repo_path": temp_dir}
            )
            self.assertEqual(pub_validate_res.status_code, 200)
            self.assertEqual(pub_validate_res.json()["status"], "completed")
            self.assertEqual(len(pub_validate_res.json()["broken_links"]), 1)

            sync_res = client.post(
                "/api/v1/homelab/sync",
                headers=auth_headers,
                json={
                    "owner_id": OWNER_ID,
                    "repo_path": temp_dir,
                    "repo_url": "repo",
                    "branch": "main",
                    "commit_sha": "sha",
                },
            )
            self.assertEqual(sync_res.status_code, 200)
            self.assertEqual(sync_res.json()["processed_files"], 1)

            # Modify the file content to force reprocessing on the public sync endpoint
            with open(temp_path / "README.md", "w") as f:
                f.write("# README\nLink to [other](./other.md)\nSome change\n")

            # Test public homelab sync
            pub_sync_res = client.post(
                "/api/homelab/sync",
                headers=auth_headers,
                json={
                    "owner_id": OWNER_ID,
                    "repo_path": temp_dir,
                    "repo_url": "repo-pub",
                    "branch": "main",
                    "commit_sha": "sha-pub",
                },
            )
            self.assertEqual(pub_sync_res.status_code, 200)
            self.assertEqual(pub_sync_res.json()["processed_files"], 1)

        create_response = client.post(
            "/api/v1/capture",
            headers=auth_headers,
            json={
                "owner_id": "ignored-client-owner",
                "raw_text": "Note lai: API capture khong duoc RAG doc truc tiep.",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertIn("rag: false", create_response.json()["normalized_markdown"])

        # Test public captures POST
        pub_create_response = client.post(
            "/api/secondbrain/captures",
            headers=auth_headers,
            json={
                "owner_id": "ignored-client-owner",
                "raw_text": "Public route capture text here.",
            },
        )
        self.assertEqual(pub_create_response.status_code, 201)
        self.assertIn("capture", pub_create_response.json())
        self.assertEqual(pub_create_response.json()["capture"]["raw_text"], "Public route capture text here.")

        list_response = client.get("/api/v1/capture", headers=auth_headers, params={"owner_id": "ignored"})
        self.assertEqual(list_response.status_code, 200)
        # Should contain legacy creation + public creation
        self.assertEqual(len(list_response.json()), 2)

        # Test public captures GET
        pub_list_response = client.get("/api/secondbrain/captures", headers=auth_headers, params={"owner_id": "ignored"})
        self.assertEqual(pub_list_response.status_code, 200)
        self.assertEqual(len(pub_list_response.json()["captures"]), 2)

        sync_response = client.get("/api/v1/sync/status", headers=auth_headers, params={"owner_id": "ignored"})
        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(sync_response.json()["total_documents"], 0)

        # Test public status GET
        pub_sync_response = client.get("/api/secondbrain/status", headers=auth_headers, params={"owner_id": "ignored"})
        self.assertEqual(pub_sync_response.status_code, 200)
        self.assertEqual(pub_sync_response.json()["total_documents"], 0)

        search_response = client.post(
            "/api/v1/search",
            headers=auth_headers,
            json={"owner_id": OWNER_ID, "query": "API capture RAG", "top_k": 5},
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json(), [])

        # Test public search POST
        pub_search_response = client.post(
            "/api/secondbrain/search",
            headers=auth_headers,
            json={"owner_id": OWNER_ID, "query": "API capture RAG", "top_k": 5},
        )
        self.assertEqual(pub_search_response.status_code, 200)
        self.assertEqual(pub_search_response.json()["results"], [])

        # Test public homelab search POST
        pub_hl_search_response = client.post(
            "/api/homelab/search",
            headers=auth_headers,
            json={"owner_id": OWNER_ID, "query": "homelab info", "top_k": 5},
        )
        self.assertEqual(pub_hl_search_response.status_code, 200)
        self.assertIn("results", pub_hl_search_response.json())

        chat_capture = client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json={
                "owner_id": OWNER_ID,
                "request_id": "chatcmpl-api-test",
                "messages": [{"role": "user", "content": "Ghi lai y tuong gateway python"}],
            },
        )
        self.assertEqual(chat_capture.status_code, 200)
        self.assertEqual(chat_capture.json()["id"], "chatcmpl-api-test")
        self.assertIn("capture inbox", chat_capture.json()["choices"][0]["message"]["content"])

        chat_search = client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json={
                "owner_id": OWNER_ID,
                "messages": [{"role": "user", "content": "homelab README link"}],
            },
        )
        self.assertEqual(chat_search.status_code, 200)
        self.assertIn("Ket qua tu Homelab", chat_search.json()["choices"][0]["message"]["content"])

        chat_stream = client.post(
            "/v1/chat/completions",
            headers=auth_headers,
            json={
                "stream": True,
                "messages": [{"role": "user", "content": "homelab README link"}],
            },
        )
        self.assertEqual(chat_stream.status_code, 200)
        self.assertIn("text/event-stream", chat_stream.headers["content-type"])
        self.assertIn("data: [DONE]", chat_stream.text)

        # Test webhook auth missing
        wh_auth_missing = client.post(
            "/api/webhooks/n8n/secondbrain/obsidian-sync",
            json={"bucket": "obsidian", "object_key": "second-brain/wiki/ok.md"},
        )
        self.assertEqual(wh_auth_missing.status_code, 401)

        # Test webhook auth wrong
        wh_auth_wrong = client.post(
            "/api/webhooks/n8n/secondbrain/obsidian-sync",
            headers={"X-Cortex-N8n-Token": "bad-token"},
            json={"bucket": "obsidian", "object_key": "second-brain/wiki/ok.md"},
        )
        self.assertEqual(wh_auth_wrong.status_code, 401)

        # Test webhook success
        import tempfile
        from pathlib import Path
        from ai_service.secondbrain.object_store import LocalS3ObjectStore
        
        with tempfile.TemporaryDirectory() as temp_s3_dir:
            temp_s3_path = Path(temp_s3_dir)
            bucket_dir = temp_s3_path / "obsidian"
            bucket_dir.mkdir()
            doc_path = bucket_dir / "second-brain" / "wiki" / "webhook-test.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text("# Webhook Success\nSync from S3-compatible storage worked.", encoding="utf-8")
            
            app_with_s3 = create_app(
                secondbrain_repository=self.repository,
                homelab_repository=self.homelab_repository,
                embedder=FakeEmbedder(),
                object_store=LocalS3ObjectStore(temp_s3_path),
                allowed_bucket="obsidian",
            )
            client_s3 = TestClient(app_with_s3)
            token_s3 = client_s3.get("/api/auth/dev-token")
            auth_headers_s3 = {"Authorization": f"Bearer {token_s3.json()['access_token']}"}
            
            wh_res = client_s3.post(
                "/api/webhooks/n8n/secondbrain/obsidian-sync",
                headers={"X-Cortex-N8n-Token": "local-dev-token"},
                json={
                    "bucket": "obsidian",
                    "object_key": "second-brain/wiki/webhook-test.md",
                    "owner_id": "ignored-client-owner",
                },
            )
            self.assertEqual(wh_res.status_code, 202)
            self.assertEqual(wh_res.json()["status"], "accepted")
            job_id = wh_res.json()["job"]["id"]

            process_res = client_s3.post(
                f"/api/internal/secondbrain/ingestion-jobs/{job_id}/process",
                headers=auth_headers_s3,
                json={"owner_id": OWNER_ID},
            )
            self.assertEqual(process_res.status_code, 200)
            self.assertEqual(process_res.json()["result"]["status"], "indexed")
            self.assertEqual(process_res.json()["result"]["processed_files"], 1)


if __name__ == "__main__":
    unittest.main()
