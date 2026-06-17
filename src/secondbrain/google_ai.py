from __future__ import annotations

import json
import time
import urllib.request
import urllib.error

from .config import SecondBrainSettings


class GoogleAIClient:
    def __init__(self, settings: SecondBrainSettings | None = None) -> None:
        self.settings = settings or SecondBrainSettings.from_env()
        if not self.settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required")

    def embed_text(self, text: str) -> tuple[float, ...]:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.google_embedding_model}:embedContent"
        )
        payload = {
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": self.settings.google_embedding_dimensions,
        }
        response = self._post_json(endpoint, payload)
        values = response.get("embedding", {}).get("values")
        if not isinstance(values, list):
            embeddings = response.get("embeddings")
            if isinstance(embeddings, list) and embeddings:
                values = embeddings[0].get("values")
        if not isinstance(values, list):
            raise RuntimeError("Google embedding response did not include embedding values")
        return tuple(float(value) for value in values)

    def generate_text(self, prompt: str) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.google_generation_model}:generateContent"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = self._post_json(endpoint, payload)
        candidates = response.get("candidates", [])
        if not candidates:
            raise RuntimeError("Google generation response did not include candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(str(part.get("text", "")) for part in parts).strip()

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.settings.google_api_key or "",
            },
            method="POST",
        )
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                error_body = e.read().decode("utf-8")
                try:
                    error_json = json.loads(error_body)
                    message = error_json.get("error", {}).get("message", "unknown Google API error")
                except json.JSONDecodeError:
                    message = error_body
                raise RuntimeError(f"Google API request failed: {message}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                reason = getattr(e, "reason", str(e))
                raise RuntimeError(f"Google API request failed: {reason}")
