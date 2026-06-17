from __future__ import annotations

import unittest
import os
from pathlib import Path

from secondbrain.config import SecondBrainSettings, load_env_file
from secondbrain.google_ai import GoogleAIClient


class GoogleAISmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_env_file(Path("src/secondbrain/.env.local"))
        cls.settings = SecondBrainSettings.from_env()
        if os.getenv("SECOND_BRAIN_RUN_GOOGLE_SMOKE") != "true":
            raise unittest.SkipTest("set SECOND_BRAIN_RUN_GOOGLE_SMOKE=true to call Google APIs")
        if not cls.settings.google_api_key:
            raise unittest.SkipTest("GOOGLE_API_KEY/GEMINI_API_KEY is not configured")

    def test_gemini_embedding_model_returns_configured_dimensions(self) -> None:
        client = GoogleAIClient(settings=self.settings)
        embedding = client.embed_text("task: search result | query: consistent hashing cache")

        self.assertEqual(len(embedding), self.settings.google_embedding_dimensions)
        self.assertTrue(any(value != 0 for value in embedding))

    def test_generation_model_returns_text(self) -> None:
        client = GoogleAIClient(settings=self.settings)
        text = client.generate_text("Reply with exactly: cortex-ok")

        self.assertIn("cortex-ok", text.lower())


if __name__ == "__main__":
    unittest.main()
