from __future__ import annotations

from dataclasses import dataclass, field
import html
import logging
import os
import re
from typing import Any, Protocol

from ai_service.orchestrator.contracts import ConversationInput


TELEGRAM_MAX_MESSAGE_CHARS = 4096
DEFAULT_CHUNK_TARGET_CHARS = 3500
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramActor:
    user_id: str
    chat_id: str
    owner_id: str
    username: str = ""


@dataclass(frozen=True)
class TelegramSettings:
    bot_token: str
    allowed_actors: tuple[TelegramActor, ...]
    parse_mode: str = "HTML"
    chunk_target_chars: int = DEFAULT_CHUNK_TARGET_CHARS

    @classmethod
    def from_env(cls) -> "TelegramSettings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        allowlist = os.getenv("TELEGRAM_ALLOWED_ACTORS", "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        actors = parse_allowed_actors(allowlist)
        if not actors:
            raise ValueError("TELEGRAM_ALLOWED_ACTORS must contain at least one chat:user:owner mapping")
        return cls(
            bot_token=token,
            allowed_actors=actors,
            chunk_target_chars=int(os.getenv("TELEGRAM_CHUNK_TARGET_CHARS", str(DEFAULT_CHUNK_TARGET_CHARS))),
        )

    def owner_for(self, chat_id: str, user_id: str) -> str | None:
        for actor in self.allowed_actors:
            if actor.chat_id == chat_id and actor.user_id == user_id:
                return actor.owner_id
        return None


@dataclass(frozen=True)
class TelegramInboundMessage:
    update_id: str
    chat_id: str
    user_id: str
    text: str
    username: str = ""
    message_id: str = ""


@dataclass(frozen=True)
class TelegramSendResult:
    chat_id: str
    text: str
    parse_mode: str


class TelegramOutbound(Protocol):
    async def send_chat_action(self, chat_id: str, action: str) -> None:
        ...

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> TelegramSendResult:
        ...


class TelegramOrchestrationHandler(Protocol):
    async def process(self, conversation_input: ConversationInput) -> str:
        ...


class TelegramAuthorizationError(PermissionError):
    pass


class TelegramUpdateIgnored(ValueError):
    pass


class TelegramHtmlSendError(ValueError):
    pass


class TelegramTransportAdapter:
    def __init__(
        self,
        settings: TelegramSettings,
        outbound: TelegramOutbound,
        handler: TelegramOrchestrationHandler,
    ) -> None:
        self.settings = settings
        self.outbound = outbound
        self.handler = handler

    async def handle_update(self, update: dict[str, Any]) -> list[TelegramSendResult]:
        inbound = parse_telegram_update(update)
        owner_id = self.settings.owner_for(inbound.chat_id, inbound.user_id)
        if owner_id is None:
            raise TelegramAuthorizationError(
                f"telegram actor is not allowed: chat_id={inbound.chat_id} user_id={inbound.user_id}"
            )

        await self.outbound.send_chat_action(inbound.chat_id, "typing")
        response = await self.handler.process(
            ConversationInput(
                owner_id=owner_id,
                actor_id=f"telegram:{inbound.user_id}",
                actor_type="telegram_user",
                channel="telegram",
                channel_ref=inbound.chat_id,
                channel_user_id=inbound.user_id,
                content=inbound.text,
                request_id=f"telegram-{inbound.update_id}",
                metadata={
                    "telegram_message_id": inbound.message_id,
                    "telegram_username": inbound.username,
                },
            )
        )

        rendered = render_telegram_html(response)
        sent: list[TelegramSendResult] = []
        if len(rendered.html_text) > TELEGRAM_MAX_MESSAGE_CHARS:
            for chunk in chunk_telegram_html(rendered.plain_text, self.settings.chunk_target_chars):
                sent.append(await self.outbound.send_message(inbound.chat_id, chunk, parse_mode=""))
            return sent

        sent.append(
            await self._send_with_plaintext_fallback(
                inbound.chat_id,
                rendered.html_text,
                rendered.plain_text,
            )
        )
        return sent

    async def _send_with_plaintext_fallback(
        self, chat_id: str, html_text: str, plain_text: str
    ) -> TelegramSendResult:
        try:
            return await self.outbound.send_message(chat_id, html_text, parse_mode=self.settings.parse_mode)
        except TelegramHtmlSendError:
            return await self.outbound.send_message(chat_id, plain_text, parse_mode="")


def parse_allowed_actors(raw: str) -> tuple[TelegramActor, ...]:
    actors: list[TelegramActor] = []
    for entry in raw.split(","):
        stripped = entry.strip()
        if not stripped:
            continue
        parts = [part.strip() for part in stripped.split(":")]
        if len(parts) != 3 or not all(parts):
            raise ValueError("TELEGRAM_ALLOWED_ACTORS entries must be chat_id:user_id:owner_id")
        chat_id, user_id, owner_id = parts
        actors.append(TelegramActor(user_id=user_id, chat_id=chat_id, owner_id=owner_id))
    return tuple(actors)


def parse_telegram_update(update: dict[str, Any]) -> TelegramInboundMessage:
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        raise TelegramUpdateIgnored("telegram update has no message")

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        raise TelegramUpdateIgnored("telegram message has no text")

    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        raise TelegramUpdateIgnored("telegram message lacks chat or sender")

    chat_id = chat.get("id")
    user_id = sender.get("id")
    if chat_id is None or user_id is None:
        raise TelegramUpdateIgnored("telegram chat or sender id is missing")

    username = sender.get("username")
    message_id = message.get("message_id")
    return TelegramInboundMessage(
        update_id=str(update.get("update_id", "")),
        chat_id=str(chat_id),
        user_id=str(user_id),
        username=str(username or ""),
        message_id=str(message_id or ""),
        text=text.strip(),
    )


def escape_telegram_html(text: str) -> str:
    return html.escape(text, quote=False)


@dataclass(frozen=True)
class TelegramRenderedText:
    html_text: str
    plain_text: str


def render_telegram_html(text: str) -> TelegramRenderedText:
    return TelegramRenderedText(
        html_text=markdown_lite_to_telegram_html(text),
        plain_text=markdown_lite_to_plain_text(text),
    )


def markdown_lite_to_telegram_html(text: str) -> str:
    placeholders: dict[str, str] = {}

    def stash(value: str) -> str:
        key = f"\x00{len(placeholders)}\x00"
        placeholders[key] = value
        return key

    working = text

    working = re.sub(
        r"```(?:[A-Za-z0-9_-]+)?\n?(.*?)```",
        lambda match: stash(f"<pre>{escape_telegram_html(match.group(1).strip())}</pre>"),
        working,
        flags=re.DOTALL,
    )
    working = re.sub(
        r"`([^`\n]+)`",
        lambda match: stash(f"<code>{escape_telegram_html(match.group(1))}</code>"),
        working,
    )
    working = re.sub(
        r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)",
        lambda match: stash(
            f'<a href="{html.escape(match.group(2), quote=True)}">{escape_telegram_html(match.group(1))}</a>'
        ),
        working,
    )

    escaped = escape_telegram_html(working)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"__([^_\n]+)__", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<i>\1</i>", escaped)

    for key, value in placeholders.items():
        escaped = escaped.replace(key, value)
    return escaped


def markdown_lite_to_plain_text(text: str) -> str:
    plain = re.sub(r"```(?:[A-Za-z0-9_-]+)?\n?(.*?)```", lambda match: match.group(1).strip(), text, flags=re.DOTALL)
    plain = re.sub(r"`([^`\n]+)`", r"\1", plain)
    plain = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r"\1 (\2)", plain)
    plain = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", plain)
    plain = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", plain)
    plain = re.sub(r"__([^_\n]+)__", r"\1", plain)
    plain = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", plain)
    return html.unescape(strip_html_tags(plain))


def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text)


def chunk_telegram_html(text: str, target_chars: int = DEFAULT_CHUNK_TARGET_CHARS) -> list[str]:
    if len(text) <= TELEGRAM_MAX_MESSAGE_CHARS:
        return [text]

    target = max(1, min(target_chars, TELEGRAM_MAX_MESSAGE_CHARS))
    chunks: list[str] = []
    remaining = text
    while len(remaining) > TELEGRAM_MAX_MESSAGE_CHARS:
        split_at = _best_split_index(remaining, target)
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _best_split_index(text: str, target: int) -> int:
    split_candidates = [
        text.rfind("\n\n", 0, target),
        text.rfind("\n", 0, target),
        text.rfind(" ", 0, target),
    ]
    for candidate in split_candidates:
        if candidate > 0:
            return _avoid_entity_split(text, candidate)
    return _avoid_entity_split(text, target)


def _avoid_entity_split(text: str, index: int) -> int:
    ampersand = text.rfind("&", 0, index)
    semicolon_after = text.find(";", index, min(len(text), ampersand + 12) if ampersand >= 0 else index)
    if ampersand >= 0 and semicolon_after != -1 and index - ampersand <= 10:
        return ampersand
    return index


@dataclass
class InMemoryTelegramOutbound:
    sent_messages: list[TelegramSendResult] = field(default_factory=list)
    chat_actions: list[tuple[str, str]] = field(default_factory=list)
    fail_html_once: bool = False

    async def send_chat_action(self, chat_id: str, action: str) -> None:
        self.chat_actions.append((chat_id, action))

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> TelegramSendResult:
        if self.fail_html_once and parse_mode == "HTML":
            self.fail_html_once = False
            raise TelegramHtmlSendError("telegram rejected HTML")
        result = TelegramSendResult(chat_id=chat_id, text=text, parse_mode=parse_mode)
        self.sent_messages.append(result)
        return result


class PythonTelegramRuntimeFactory:
    def __init__(self, settings: TelegramSettings, handler: TelegramOrchestrationHandler) -> None:
        self.settings = settings
        self.handler = handler

    def build_application(self) -> Any:
        try:
            from telegram import Update
            from telegram.constants import ChatAction
            from telegram.error import BadRequest
            from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install python-telegram-bot to run the Telegram transport") from exc

        application = ApplicationBuilder().token(self.settings.bot_token).build()

        class PythonTelegramOutbound:
            async def send_chat_action(self, chat_id: str, action: str) -> None:
                await application.bot.send_chat_action(chat_id=chat_id, action=action)

            async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> TelegramSendResult:
                try:
                    await application.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode or None)
                except BadRequest as exc:
                    if parse_mode:
                        raise TelegramHtmlSendError(str(exc)) from exc
                    raise
                return TelegramSendResult(chat_id=chat_id, text=text, parse_mode=parse_mode)

        adapter = TelegramTransportAdapter(
            settings=self.settings,
            outbound=PythonTelegramOutbound(),
            handler=self.handler,
        )

        async def on_text(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
            if update.message is None:
                return
            raw_update = update.to_dict()
            try:
                await adapter.handle_update(raw_update)
            except TelegramAuthorizationError:
                await application.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
                await application.bot.send_message(chat_id=update.message.chat_id, text="Unauthorized.")
            except TelegramUpdateIgnored:
                return
            except Exception:
                logger.exception("Telegram update handling failed")
                await application.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Hệ thống đang bận hoặc gặp lỗi. Vui lòng thử lại sau.",
                )

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        return application


def build_python_telegram_application(settings: TelegramSettings, handler: TelegramOrchestrationHandler) -> Any:
    return PythonTelegramRuntimeFactory(settings=settings, handler=handler).build_application()
