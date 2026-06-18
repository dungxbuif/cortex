from __future__ import annotations

import hmac
import tempfile
import unittest
from pathlib import Path

from ai_service.core.models import IndexStatus, utc_now
from ai_service.homelab.link_validator import gfm_slugify, validate_markdown_links
from ai_service.homelab.markdown import chunk_homelab_markdown
from ai_service.homelab.models import HomelabDocument
from ai_service.homelab.redaction import checksum_text, redact_secrets, verify_signature
from ai_service.secondbrain.markdown import build_document, chunk_markdown


class DomainHelperTest(unittest.TestCase):
    def test_secondbrain_chunk_markdown_returns_raw_chunks_without_embedding(self) -> None:
        document = build_document("owner", "wiki/test.md", "# Test\nFirst paragraph\n\n## Next\nSecond paragraph")
        chunks = chunk_markdown("owner", document, "# Test\nFirst paragraph\n\n## Next\nSecond paragraph")

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "First paragraph")
        self.assertFalse(hasattr(chunks[0], "embedding"))
        self.assertEqual(chunks[1].heading_chain, ("Test", "Next"))

    def test_homelab_chunk_markdown_returns_raw_chunks_without_embedding(self) -> None:
        document = HomelabDocument(
            id="doc",
            owner_id="owner",
            repo_url="repo",
            branch="main",
            commit_sha="sha",
            file_path="README.md",
            checksum="checksum",
            index_status=IndexStatus.INDEXED,
            indexed_at=utc_now(),
        )
        chunks = chunk_homelab_markdown("owner", document, "# Homelab\nGateway config\n\n## Network\nTunnel setup")

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].content, "Gateway config")
        self.assertFalse(hasattr(chunks[0], "embedding"))
        self.assertEqual(chunks[1].heading_chain, ("Homelab", "Network"))

    def test_redaction_checksum_and_signature_helpers(self) -> None:
        raw_text = "password: supersecret\nWAN 171.229.241.103 LAN 192.168.1.10"
        redacted = redact_secrets(raw_text)

        self.assertIn("password: <REDACTED_SECRET>", redacted)
        self.assertIn("<REDACTED_IP>", redacted)
        self.assertIn("192.168.1.10", redacted)
        self.assertEqual(checksum_text("abc"), checksum_text("abc"))

        secret = "hook-secret"
        payload = b"{\"ok\":true}"
        digest = hmac.new(secret.encode("utf-8"), payload, "sha256").hexdigest()
        self.assertTrue(verify_signature(payload, f"sha256={digest}", secret))
        self.assertFalse(verify_signature(payload, "sha1=bad", secret))

    def test_link_validator_detects_missing_file_and_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs").mkdir()
            (root / "README.md").write_text(
                "# Home\n"
                "[ok](./docs/guide.md#setup)\n"
                "[missing](./missing.md)\n"
                "[bad-anchor](./docs/guide.md#does-not-exist)\n"
            )
            (root / "docs" / "guide.md").write_text("# Guide\n## Setup\n")

            broken = validate_markdown_links(temp_dir)
            broken_targets = {row["raw_link"] for row in broken}

        self.assertEqual(gfm_slugify("## Setup!"), "setup")
        self.assertEqual(broken_targets, {"./missing.md", "./docs/guide.md#does-not-exist"})


if __name__ == "__main__":
    unittest.main()
