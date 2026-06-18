from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import grpc

from ai_service.grpc import cortex_pb2, cortex_pb2_grpc
from ai_service.grpc_server import create_server
from ai_service.homelab.repository import SqliteHomelabRepository
from ai_service.homelab.service import HomelabService
from ai_service.secondbrain.object_store import LocalS3ObjectStore
from ai_service.secondbrain.repository import SqliteSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


class GrpcRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.sb_repo = SqliteSecondBrainRepository()
        self.hl_repo = SqliteHomelabRepository()
        embedder = FakeEmbedder()
        self.server = create_server(
            secondbrain_service=SecondBrainService(repository=self.sb_repo, embedder=embedder),
            homelab_service=HomelabService(repository=self.hl_repo, embedder=embedder),
            max_workers=2,
        )
        port = self.server.add_insecure_port("127.0.0.1:0")
        self.server.start()
        self.channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        self.sb = cortex_pb2_grpc.SecondBrainServiceStub(self.channel)
        self.hl = cortex_pb2_grpc.HomelabServiceStub(self.channel)
        self.orch = cortex_pb2_grpc.OrchestratorServiceStub(self.channel)

    def tearDown(self) -> None:
        self.channel.close()
        self.server.stop(0)
        self.sb_repo.close()
        self.hl_repo.close()

    def test_secondbrain_capture_list_status_and_search(self) -> None:
        health = self.sb.HealthCheck(cortex_pb2.HealthCheckRequest())
        self.assertEqual(health.status, "ok")

        created = self.sb.CreateCapture(
            cortex_pb2.CreateCaptureRequest(owner_id="grpc-owner", source="test", raw_text="Capture qua grpc")
        )
        self.assertEqual(created.capture.status, "captured")
        self.assertIn("rag: false", created.capture.normalized_markdown)

        listed = self.sb.ListCaptures(cortex_pb2.ListCapturesRequest(owner_id="grpc-owner"))
        self.assertEqual(len(listed.captures), 1)

        status = self.sb.GetSyncStatus(cortex_pb2.GetSyncStatusRequest(owner_id="grpc-owner"))
        self.assertEqual(status.total_documents, 0)

        search = self.sb.SearchSecondBrain(cortex_pb2.SearchRequest(owner_id="grpc-owner", query="Capture grpc", top_k=5))
        self.assertEqual(len(search.results), 0)

    def test_secondbrain_sync_minio_object_indexes_local_s3_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            object_path = root / "obsidian" / "second-brain" / "wiki" / "grpc-minio.md"
            object_path.parent.mkdir(parents=True)
            object_path.write_text(
                "---\ntype: wiki\ntitle: gRPC MinIO\n---\n# gRPC MinIO\nObsidian sync over local S3 action.",
                encoding="utf-8",
            )
            service = SecondBrainService(
                repository=self.sb_repo,
                embedder=FakeEmbedder(),
                object_store=LocalS3ObjectStore(root),
                allowed_bucket="obsidian",
            )
            self.server.stop(0)
            self.channel.close()
            self.server = create_server(
                secondbrain_service=service,
                homelab_service=HomelabService(self.hl_repo, embedder=FakeEmbedder()),
                max_workers=2,
            )
            port = self.server.add_insecure_port("127.0.0.1:0")
            self.server.start()
            self.channel = grpc.insecure_channel(f"127.0.0.1:{port}")
            self.sb = cortex_pb2_grpc.SecondBrainServiceStub(self.channel)

            sync = self.sb.SyncSecondBrainObject(
                cortex_pb2.SyncSecondBrainObjectRequest(
                    bucket="obsidian",
                    object_key="second-brain/wiki/grpc-minio.md",
                    owner_id="grpc-minio",
                )
            )
            self.assertEqual(sync.status, "indexed")
            self.assertEqual(sync.processed_files, 1)

            replay = self.sb.SyncSecondBrainObject(
                cortex_pb2.SyncSecondBrainObjectRequest(
                    bucket="obsidian",
                    object_key="second-brain/wiki/grpc-minio.md",
                    owner_id="grpc-minio",
                )
            )
            self.assertEqual(replay.status, "skipped")
            self.assertEqual(replay.message, "unchanged content")

    def test_homelab_sync_search_and_validate_links(self) -> None:
        health = self.hl.HealthCheck(cortex_pb2.HealthCheckRequest())
        self.assertEqual(health.status, "ok")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Homelab\nRathole tunnel forwarding\n[missing](./missing.md)\n")

            sync = self.hl.SyncHomelab(
                cortex_pb2.SyncHomelabRequest(
                    owner_id="grpc-homelab",
                    repo_path=temp_dir,
                    repo_url="repo",
                    branch="main",
                    commit_sha="sha",
                )
            )
            self.assertEqual(sync.processed_files, 1)

            search = self.hl.SearchHomelab(
                cortex_pb2.SearchRequest(owner_id="grpc-homelab", query="rathole tunnel", top_k=5)
            )
            self.assertEqual(len(search.results), 1)
            self.assertEqual(search.results[0].document.file_path, "README.md")

            validation = self.hl.ValidateLinks(cortex_pb2.ValidateLinksRequest(repo_path=temp_dir))
            self.assertEqual(validation.status, "completed")
            self.assertEqual(len(validation.broken_links), 1)

    def test_invalid_capture_maps_to_invalid_argument(self) -> None:
        with self.assertRaises(grpc.RpcError) as raised:
            self.sb.CreateCapture(cortex_pb2.CreateCaptureRequest(owner_id="grpc-owner", raw_text=" "))
        self.assertEqual(raised.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    def test_orchestrator_chat_routes_to_existing_services(self) -> None:
        capture = self.orch.ChatCompletions(
            cortex_pb2.ChatCompletionsRequest(
                owner_id="grpc-orchestrator",
                request_id="chatcmpl-test",
                messages=[cortex_pb2.ChatMessage(role="user", content="Ghi lai y tuong routing module cu")],
            )
        )
        self.assertEqual(capture.id, "chatcmpl-test")
        self.assertIn("capture inbox", capture.choices[0].message.content)
        listed = self.sb.ListCaptures(cortex_pb2.ListCapturesRequest(owner_id="grpc-orchestrator"))
        self.assertEqual(len(listed.captures), 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("# Homelab\nRathole tunnel forwarding\n")
            self.hl.SyncHomelab(
                cortex_pb2.SyncHomelabRequest(
                    owner_id="grpc-orchestrator",
                    repo_path=temp_dir,
                    repo_url="repo",
                    branch="main",
                    commit_sha="sha",
                )
            )
            search = self.orch.ChatCompletions(
                cortex_pb2.ChatCompletionsRequest(
                    owner_id="grpc-orchestrator",
                    messages=[cortex_pb2.ChatMessage(role="user", content="homelab rathole tunnel")],
                )
            )
            self.assertIn("Ket qua tu Homelab", search.choices[0].message.content)
            self.assertIn("README.md", search.choices[0].message.content)


if __name__ == "__main__":
    unittest.main()
