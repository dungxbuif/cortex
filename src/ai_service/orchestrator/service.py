from __future__ import annotations

from dataclasses import dataclass
import time
import uuid

from ai_service.homelab.service import HomelabService
from ai_service.secondbrain.service import SecondBrainService


DEFAULT_OWNER_ID = "owner"


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    name: str = ""


@dataclass(frozen=True)
class ChatChoice:
    index: int
    message: ChatMessage
    finish_reason: str


@dataclass(frozen=True)
class ChatCompletion:
    id: str
    object: str
    created: int
    model: str
    choices: list[ChatChoice]


class OrchestratorService:
    """Deterministic chat router over existing domain services.

    This layer intentionally avoids prompts and provider-specific tool-call
    schemas. It gives Epic 4 a complete transport path while keeping the full
    LLM planning loop for the later orchestrator phase.
    """

    def __init__(self, secondbrain_service: SecondBrainService, homelab_service: HomelabService) -> None:
        self.secondbrain_service = secondbrain_service
        self.homelab_service = homelab_service

    def chat_completions(
        self,
        messages: list[ChatMessage],
        owner_id: str = DEFAULT_OWNER_ID,
        conversation_id: str = "",
        request_id: str = "",
    ) -> ChatCompletion:
        user_text = _latest_user_text(messages)
        if not user_text:
            raise ValueError("at least one user message is required")

        owner = owner_id or DEFAULT_OWNER_ID
        answer = self._route(user_text, owner)
        completion_id = request_id or f"chatcmpl-{uuid.uuid4()}"
        return ChatCompletion(
            id=completion_id,
            object="chat.completion",
            created=int(time.time()),
            model="cortex-orchestrator-router",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=answer),
                    finish_reason="stop",
                )
            ],
        )

    def _route(self, user_text: str, owner_id: str) -> str:
        normalized = user_text.lower()
        if _is_capture_intent(normalized):
            capture = self.secondbrain_service.create_capture(
                raw_text=user_text,
                source="chat",
                owner_id=owner_id,
            )
            return "\n".join(
                [
                    "Da ghi vao Second Brain capture inbox.",
                    f"- capture_id: `{capture.id}`",
                    f"- status: `{capture.status.value}`",
                    "- vault_write: `false`",
                ]
            )

        if _is_homelab_intent(normalized):
            results = self.homelab_service.search_knowledge(user_text, owner_id=owner_id, top_k=3)
            return _format_search_answer("Homelab", results)

        results = self.secondbrain_service.search_knowledge(user_text, owner_id=owner_id, top_k=3)
        if results:
            return _format_search_answer("Second Brain", results)

        homelab_results = self.homelab_service.search_knowledge(user_text, owner_id=owner_id, top_k=3)
        if homelab_results:
            return _format_search_answer("Homelab", homelab_results)

        return "Khong tim thay ngu canh phu hop trong Second Brain hoac Homelab."


def _latest_user_text(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content.strip()
    return ""


def _is_capture_intent(text: str) -> bool:
    markers = ("capture", "ghi lai", "ghi lại", "luu lai", "lưu lại", "note lai", "note lại")
    return any(marker in text for marker in markers)


def _is_homelab_intent(text: str) -> bool:
    markers = ("homelab", "rathole", "vps", "tunnel", "nginx", "docker", "server", "repo")
    return any(marker in text for marker in markers)


def _format_search_answer(label: str, results) -> str:
    if not results:
        return f"Khong tim thay ket qua trong {label}."

    lines = [f"Ket qua tu {label}:"]
    for index, result in enumerate(results, start=1):
        document = result.document
        chunk = result.chunk
        path = getattr(document, "vault_path", None) or getattr(document, "file_path", "")
        snippet = " ".join(str(chunk.content).split())
        if len(snippet) > 240:
            snippet = snippet[:237].rstrip() + "..."
        lines.append(f"{index}. `{path}` score={result.score:.3f}")
        lines.append(f"   {snippet}")
    return "\n".join(lines)
