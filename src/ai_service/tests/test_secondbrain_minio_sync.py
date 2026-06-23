from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_service.secondbrain.object_store import LocalS3ObjectStore
from ai_service.secondbrain.repository import SqliteSecondBrainRepository
from ai_service.secondbrain.service import SecondBrainService


class FakeEmbedder:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return tuple(0.01 if i == 0 else 0.0 for i in range(768))

    def embed_batch(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [self.embed_text(text) for text in texts]


class SecondBrainMinIOSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.bucket = "obsidian"
        self.bucket_root = self.root / self.bucket
        self.bucket_root.mkdir()
        self.repo = SqliteSecondBrainRepository()
        self.service = SecondBrainService(
            repository=self.repo,
            embedder=FakeEmbedder(),
            object_store=LocalS3ObjectStore(self.root),
            allowed_bucket=self.bucket,
        )

    def tearDown(self) -> None:
        self.repo.close()
        self.temp_dir.cleanup()

    def test_indexes_markdown_object_under_second_brain_prefix(self) -> None:
        object_key = "second-brain/wiki/minio-sync.md"
        self._write_object(
            object_key,
            """---
type: wiki
title: "MinIO Sync"
tags: [second-brain, sync]
---

# MinIO Sync

Local S3 simulation indexes Obsidian markdown through the Second Brain pipeline.
""",
        )

        result = self.service.sync_minio_object(self.bucket, object_key, owner_id="minio-owner")

        self.assertEqual(result["status"], "indexed")
        self.assertEqual(result["processed_files"], 1)
        status = self.service.get_sync_status(owner_id="minio-owner")
        self.assertEqual(status.indexed_documents, 1)
        self.assertGreater(status.total_chunks, 0)
        results = self.service.search_knowledge("local s3 simulation obsidian", owner_id="minio-owner")
        self.assertEqual(results[0].document.vault_path, "wiki/minio-sync.md")

    def test_replayed_object_is_idempotent_by_checksum(self) -> None:
        object_key = "second-brain/wiki/idempotent.md"
        self._write_object(object_key, "---\ntype: wiki\ntitle: Idempotent\n---\n# Idempotent\nSame content")

        first = self.service.sync_minio_object(self.bucket, object_key, owner_id="minio-owner")
        second = self.service.sync_minio_object(self.bucket, object_key, owner_id="minio-owner")

        self.assertEqual(first["status"], "indexed")
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(second["message"], "unchanged content")
        status = self.service.get_sync_status(owner_id="minio-owner")
        self.assertEqual(status.total_documents, 1)

    def test_skips_out_of_prefix_and_non_markdown_objects(self) -> None:
        self._write_object("other/wiki.md", "# Outside")
        self._write_object("second-brain/assets/image.png", "not markdown")

        outside = self.service.sync_minio_object(self.bucket, "other/wiki.md", owner_id="minio-owner")
        asset = self.service.sync_minio_object(self.bucket, "second-brain/assets/image.png", owner_id="minio-owner")

        self.assertEqual(outside["status"], "skipped")
        self.assertEqual(outside["message"], "object outside second-brain prefix")
        self.assertEqual(asset["status"], "skipped")
        self.assertEqual(asset["message"], "object is not markdown")
        status = self.service.get_sync_status(owner_id="minio-owner")
        self.assertEqual(status.total_documents, 0)

    def test_rejects_wrong_bucket_and_traversal_key(self) -> None:
        with self.assertRaises(ValueError):
            self.service.sync_minio_object("wrong", "second-brain/wiki/a.md", owner_id="minio-owner")
        with self.assertRaises(ValueError):
            self.service.sync_minio_object(self.bucket, "second-brain/../secret.md", owner_id="minio-owner")

    def test_submit_event_queues_job_and_worker_processes_it(self) -> None:
        object_key = "second-brain/wiki/async-job.md"
        self._write_object(object_key, "# Async Job\nWorker indexes queued object.")

        job = self.service.submit_minio_event(self.bucket, object_key, owner_id="minio-owner")

        self.assertEqual(job.status, "queued")
        self.assertEqual(job.event_type, "upsert")

        result = self.service.process_ingestion_job(job.id, owner_id="minio-owner")
        processed = self.repo.get_ingestion_job("minio-owner", job.id)

        self.assertEqual(result["status"], "indexed")
        self.assertIsNotNone(processed)
        self.assertEqual(processed.status, "succeeded")
        self.assertEqual(processed.attempts, 1)

    def test_delete_event_removes_document_and_chunks_from_search(self) -> None:
        object_key = "second-brain/wiki/delete-me.md"
        self._write_object(
            object_key,
            "# Delete Me\nThis document contains a unique stale phrase for removal.",
        )
        indexed = self.service.sync_minio_object(self.bucket, object_key, owner_id="minio-owner")
        self.assertEqual(indexed["status"], "indexed")
        self.assertTrue(self.service.search_knowledge("unique stale phrase", owner_id="minio-owner"))

        delete_job = self.service.submit_minio_event(
            self.bucket,
            object_key,
            owner_id="minio-owner",
            event_name="s3:ObjectRemoved:Delete",
        )
        result = self.service.process_ingestion_job(delete_job.id, owner_id="minio-owner")

        self.assertEqual(result["status"], "deleted")
        self.assertEqual(self.service.search_knowledge("unique stale phrase", owner_id="minio-owner"), [])

    def test_repeated_delete_event_is_idempotent_skip(self) -> None:
        object_key = "second-brain/wiki/missing-delete.md"
        delete_job = self.service.submit_minio_event(
            self.bucket,
            object_key,
            owner_id="minio-owner",
            event_name="s3:ObjectRemoved:Delete",
        )

        result = self.service.process_ingestion_job(delete_job.id, owner_id="minio-owner")

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["message"], "document not found")

    def _write_object(self, object_key: str, content: str) -> None:
        path = self.bucket_root / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
