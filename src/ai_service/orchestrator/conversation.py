from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
import uuid
from typing import Any

from ai_service.core.config import AIServiceSettings
from ai_service.core.migrations import apply_migrations
from ai_service.core.models import utc_now
from ai_service.core.repository import PsqlRepositoryBase, jsonb_literal, sql_literal, sql_nullable


DEFAULT_CONTEXT_MESSAGE_LIMIT = 20
DEFAULT_CONTEXT_TOKEN_LIMIT = 8000
DEFAULT_INACTIVE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_CONFIRMATION_TTL_SECONDS = 5 * 60


@dataclass(frozen=True)
class Conversation:
    id: str
    owner_id: str
    channel: str
    channel_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    last_active_at: datetime


@dataclass(frozen=True)
class ConversationMessage:
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    message_token_count: int | None
    created_at: datetime


@dataclass(frozen=True)
class ConversationContext:
    conversation: Conversation
    messages: tuple[ConversationMessage, ...]
    reset_due_to_inactivity: bool = False


@dataclass(frozen=True)
class PendingConfirmation:
    id: str
    conversation_id: str
    owner_id: str
    channel: str
    channel_ref: str
    channel_user_id: str
    tool_name: str
    tool_args: dict[str, Any]
    tool_args_hash: str
    policy_decision: dict[str, Any]
    audit_event_id: str | None
    prompt_shown: str
    status: str
    created_at: datetime
    expires_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True)
class ConfirmationResolution:
    confirmation: PendingConfirmation
    status: str


@dataclass(frozen=True)
class ConversationManager:
    repository: "PostgresPsqlConversationRepository"
    context_message_limit: int = DEFAULT_CONTEXT_MESSAGE_LIMIT
    context_token_limit: int = DEFAULT_CONTEXT_TOKEN_LIMIT
    inactive_ttl_seconds: int = DEFAULT_INACTIVE_TTL_SECONDS
    confirmation_ttl_seconds: int = DEFAULT_CONFIRMATION_TTL_SECONDS

    def load_conversation(self, owner_id: str, channel: str, channel_ref: str) -> ConversationContext:
        conversation = self.repository.get_or_create_conversation(owner_id, channel, channel_ref)
        reset_due_to_inactivity = _is_inactive(conversation.last_active_at, self.inactive_ttl_seconds)
        if reset_due_to_inactivity:
            self.repository.touch_conversation(conversation.id)
            conversation = self.repository.get_conversation(conversation.id) or conversation
            return ConversationContext(conversation=conversation, messages=(), reset_due_to_inactivity=True)

        messages = self.repository.list_recent_messages(conversation.id, limit=self.context_message_limit)
        trimmed = _trim_messages_by_token_limit(messages, self.context_token_limit)
        return ConversationContext(conversation=conversation, messages=tuple(trimmed))

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
        message_token_count: int | None = None,
    ) -> ConversationMessage:
        token_count = message_token_count if message_token_count is not None else estimate_token_count(content)
        message = ConversationMessage(
            id=f"msg_{uuid.uuid4().hex}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_result=tool_result,
            message_token_count=token_count,
            created_at=datetime.now(UTC),
        )
        saved = self.repository.save_message(message)
        self.repository.touch_conversation(conversation_id)
        return saved

    def create_pending_confirmation(
        self,
        conversation_id: str,
        owner_id: str,
        channel: str,
        channel_ref: str,
        channel_user_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        policy_decision: dict[str, Any],
        prompt_shown: str,
        ttl_seconds: int | None = None,
        audit_event_id: str | None = None,
    ) -> PendingConfirmation:
        ttl = ttl_seconds if ttl_seconds is not None else self.confirmation_ttl_seconds
        now = utc_now()
        self.repository.expire_active_confirmations(conversation_id)
        confirmation = PendingConfirmation(
            id=f"confirm_{uuid.uuid4().hex}",
            conversation_id=conversation_id,
            owner_id=owner_id,
            channel=channel,
            channel_ref=channel_ref,
            channel_user_id=channel_user_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_args_hash=hash_tool_args(tool_args),
            policy_decision=policy_decision,
            audit_event_id=audit_event_id,
            prompt_shown=prompt_shown,
            status="pending",
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            resolved_at=None,
        )
        return self.repository.save_pending_confirmation(confirmation)

    def get_active_confirmation(
        self,
        conversation_id: str,
        channel: str,
        channel_ref: str,
        channel_user_id: str,
    ) -> PendingConfirmation | None:
        confirmation = self.repository.get_active_confirmation(
            conversation_id=conversation_id,
            channel=channel,
            channel_ref=channel_ref,
            channel_user_id=channel_user_id,
        )
        if confirmation is None:
            return None
        if confirmation.expires_at <= utc_now():
            self.repository.resolve_confirmation(confirmation.id, "expired")
            return None
        return confirmation

    def resolve_confirmation(self, confirmation_id: str, status: str) -> PendingConfirmation:
        if status not in {"confirmed", "declined", "expired"}:
            raise ValueError(f"unsupported confirmation status: {status}")
        resolved = self.repository.resolve_confirmation(confirmation_id, status)
        if resolved is None:
            raise KeyError(f"confirmation not found: {confirmation_id}")
        return resolved


class PostgresPsqlConversationRepository(PsqlRepositoryBase):
    def __init__(
        self,
        settings: AIServiceSettings | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ) -> None:
        self.settings = settings or AIServiceSettings.from_env()
        postgres = self.settings.postgres
        self.host = host or postgres.host
        self.port = port or postgres.port
        self.database = database or postgres.database
        self.user = user or postgres.user
        self.password = password or postgres.password
        apply_migrations(self, self.settings.migrations_path)

    @classmethod
    def from_env(cls) -> "PostgresPsqlConversationRepository":
        return cls(settings=AIServiceSettings.from_env())

    def ping(self) -> bool:
        try:
            self._query("SELECT 1;")
        except RuntimeError:
            return False
        return True

    def clear_owner(self, owner_id: str) -> None:
        self._execute(
            f"""
            DELETE FROM conversations
            WHERE owner_id = {sql_literal(owner_id)};
            """
        )

    def get_or_create_conversation(self, owner_id: str, channel: str, channel_ref: str) -> Conversation:
        existing = self.find_conversation(owner_id, channel, channel_ref)
        if existing is not None:
            return existing
        conversation = Conversation(
            id=f"conv_{uuid.uuid4().hex}",
            owner_id=owner_id,
            channel=channel,
            channel_ref=channel_ref,
            metadata={},
            created_at=utc_now(),
            last_active_at=utc_now(),
        )
        self._execute(
            f"""
            INSERT INTO conversations (
              id, owner_id, channel, channel_ref, metadata, created_at, last_active_at
            ) VALUES (
              {sql_literal(conversation.id)},
              {sql_literal(conversation.owner_id)},
              {sql_literal(conversation.channel)},
              {sql_literal(conversation.channel_ref)},
              {jsonb_literal(conversation.metadata)},
              {sql_literal(conversation.created_at.isoformat())}::timestamptz,
              {sql_literal(conversation.last_active_at.isoformat())}::timestamptz
            )
            ON CONFLICT (owner_id, channel, channel_ref) DO NOTHING;
            """
        )
        return self.find_conversation(owner_id, channel, channel_ref) or conversation

    def find_conversation(self, owner_id: str, channel: str, channel_ref: str) -> Conversation | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'channel', channel,
              'channel_ref', channel_ref,
              'metadata', metadata,
              'created_at', created_at,
              'last_active_at', last_active_at
            )
            FROM conversations
            WHERE owner_id = {sql_literal(owner_id)}
              AND channel = {sql_literal(channel)}
              AND channel_ref = {sql_literal(channel_ref)};
            """
        )
        return conversation_from_json(rows[0]) if rows else None

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'owner_id', owner_id,
              'channel', channel,
              'channel_ref', channel_ref,
              'metadata', metadata,
              'created_at', created_at,
              'last_active_at', last_active_at
            )
            FROM conversations
            WHERE id = {sql_literal(conversation_id)};
            """
        )
        return conversation_from_json(rows[0]) if rows else None

    def touch_conversation(self, conversation_id: str) -> None:
        self._execute(
            f"""
            UPDATE conversations
            SET last_active_at = now()
            WHERE id = {sql_literal(conversation_id)};
            """
        )

    def set_last_active_at(self, conversation_id: str, last_active_at: datetime) -> None:
        self._execute(
            f"""
            UPDATE conversations
            SET last_active_at = {sql_literal(last_active_at.isoformat())}::timestamptz
            WHERE id = {sql_literal(conversation_id)};
            """
        )

    def save_message(self, message: ConversationMessage) -> ConversationMessage:
        self._execute(
            f"""
            INSERT INTO conversation_messages (
              id, conversation_id, role, content, tool_calls, tool_result,
              message_token_count, created_at
            ) VALUES (
              {sql_literal(message.id)},
              {sql_literal(message.conversation_id)},
              {sql_literal(message.role)},
              {sql_literal(message.content)},
              {jsonb_nullable(message.tool_calls)},
              {jsonb_nullable(message.tool_result)},
              {sql_int_nullable(message.message_token_count)},
              {sql_literal(message.created_at.isoformat())}::timestamptz
            );
            """
        )
        return message

    def list_recent_messages(self, conversation_id: str, limit: int) -> list[ConversationMessage]:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'conversation_id', conversation_id,
              'role', role,
              'content', content,
              'tool_calls', tool_calls,
              'tool_result', tool_result,
              'message_token_count', message_token_count,
              'created_at', created_at
            )
            FROM (
              SELECT *
              FROM conversation_messages
              WHERE conversation_id = {sql_literal(conversation_id)}
              ORDER BY created_at DESC
              LIMIT {int(limit)}
            ) recent
            ORDER BY created_at ASC;
            """
        )
        return [message_from_json(row) for row in rows]

    def save_pending_confirmation(self, confirmation: PendingConfirmation) -> PendingConfirmation:
        self._execute(
            f"""
            INSERT INTO pending_confirmations (
              id, conversation_id, owner_id, channel, channel_ref, channel_user_id,
              tool_name, tool_args, tool_args_hash, policy_decision, audit_event_id,
              prompt_shown, status, created_at, expires_at, resolved_at
            ) VALUES (
              {sql_literal(confirmation.id)},
              {sql_literal(confirmation.conversation_id)},
              {sql_literal(confirmation.owner_id)},
              {sql_literal(confirmation.channel)},
              {sql_literal(confirmation.channel_ref)},
              {sql_literal(confirmation.channel_user_id)},
              {sql_literal(confirmation.tool_name)},
              {jsonb_literal(confirmation.tool_args)},
              {sql_literal(confirmation.tool_args_hash)},
              {jsonb_literal(confirmation.policy_decision)},
              {sql_nullable(confirmation.audit_event_id)},
              {sql_literal(confirmation.prompt_shown)},
              {sql_literal(confirmation.status)},
              {sql_literal(confirmation.created_at.isoformat())}::timestamptz,
              {sql_literal(confirmation.expires_at.isoformat())}::timestamptz,
              NULL
            );
            """
        )
        return confirmation

    def get_active_confirmation(
        self,
        conversation_id: str,
        channel: str,
        channel_ref: str,
        channel_user_id: str,
    ) -> PendingConfirmation | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'conversation_id', conversation_id,
              'owner_id', owner_id,
              'channel', channel,
              'channel_ref', channel_ref,
              'channel_user_id', channel_user_id,
              'tool_name', tool_name,
              'tool_args', tool_args,
              'tool_args_hash', tool_args_hash,
              'policy_decision', policy_decision,
              'audit_event_id', audit_event_id,
              'prompt_shown', prompt_shown,
              'status', status,
              'created_at', created_at,
              'expires_at', expires_at,
              'resolved_at', resolved_at
            )
            FROM pending_confirmations
            WHERE conversation_id = {sql_literal(conversation_id)}
              AND channel = {sql_literal(channel)}
              AND channel_ref = {sql_literal(channel_ref)}
              AND channel_user_id = {sql_literal(channel_user_id)}
              AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1;
            """
        )
        return confirmation_from_json(rows[0]) if rows else None

    def expire_active_confirmations(self, conversation_id: str) -> None:
        self._execute(
            f"""
            UPDATE pending_confirmations
            SET status = 'expired',
                resolved_at = now()
            WHERE conversation_id = {sql_literal(conversation_id)}
              AND status = 'pending';
            """
        )

    def resolve_confirmation(self, confirmation_id: str, status: str) -> PendingConfirmation | None:
        self._execute(
            f"""
            UPDATE pending_confirmations
            SET status = {sql_literal(status)},
                resolved_at = now()
            WHERE id = {sql_literal(confirmation_id)};
            """
        )
        return self.get_confirmation(confirmation_id)

    def get_confirmation(self, confirmation_id: str) -> PendingConfirmation | None:
        rows = self._query_json_lines(
            f"""
            SELECT jsonb_build_object(
              'id', id,
              'conversation_id', conversation_id,
              'owner_id', owner_id,
              'channel', channel,
              'channel_ref', channel_ref,
              'channel_user_id', channel_user_id,
              'tool_name', tool_name,
              'tool_args', tool_args,
              'tool_args_hash', tool_args_hash,
              'policy_decision', policy_decision,
              'audit_event_id', audit_event_id,
              'prompt_shown', prompt_shown,
              'status', status,
              'created_at', created_at,
              'expires_at', expires_at,
              'resolved_at', resolved_at
            )
            FROM pending_confirmations
            WHERE id = {sql_literal(confirmation_id)};
            """
        )
        return confirmation_from_json(rows[0]) if rows else None


def estimate_token_count(content: str) -> int:
    return max(1, (len(content.split()) * 4 + 2) // 3) if content else 0


def hash_tool_args(tool_args: dict[str, Any]) -> str:
    canonical = json.dumps(tool_args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def conversation_from_json(row: dict[str, Any]) -> Conversation:
    return Conversation(
        id=str(row["id"]),
        owner_id=str(row["owner_id"]),
        channel=str(row["channel"]),
        channel_ref=str(row["channel_ref"]),
        metadata=dict(row.get("metadata") or {}),
        created_at=parse_datetime(row["created_at"]),
        last_active_at=parse_datetime(row["last_active_at"]),
    )


def message_from_json(row: dict[str, Any]) -> ConversationMessage:
    return ConversationMessage(
        id=str(row["id"]),
        conversation_id=str(row["conversation_id"]),
        role=str(row["role"]),
        content=str(row["content"]),
        tool_calls=row.get("tool_calls"),
        tool_result=row.get("tool_result"),
        message_token_count=row.get("message_token_count"),
        created_at=parse_datetime(row["created_at"]),
    )


def confirmation_from_json(row: dict[str, Any]) -> PendingConfirmation:
    return PendingConfirmation(
        id=str(row["id"]),
        conversation_id=str(row["conversation_id"]),
        owner_id=str(row["owner_id"]),
        channel=str(row["channel"]),
        channel_ref=str(row["channel_ref"]),
        channel_user_id=str(row["channel_user_id"]),
        tool_name=str(row["tool_name"]),
        tool_args=dict(row["tool_args"]),
        tool_args_hash=str(row["tool_args_hash"]),
        policy_decision=dict(row["policy_decision"]),
        audit_event_id=row.get("audit_event_id"),
        prompt_shown=str(row["prompt_shown"]),
        status=str(row["status"]),
        created_at=parse_datetime(row["created_at"]),
        expires_at=parse_datetime(row["expires_at"]),
        resolved_at=parse_datetime(row["resolved_at"]) if row.get("resolved_at") else None,
    )


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _trim_messages_by_token_limit(
    messages: list[ConversationMessage],
    token_limit: int,
) -> list[ConversationMessage]:
    selected: list[ConversationMessage] = []
    total = 0
    for message in reversed(messages):
        count = message.message_token_count if message.message_token_count is not None else estimate_token_count(message.content)
        if selected and total + count > token_limit:
            break
        selected.append(message)
        total += count
    return list(reversed(selected))


def _is_inactive(last_active_at: datetime, inactive_ttl_seconds: int) -> bool:
    return utc_now() - last_active_at > timedelta(seconds=inactive_ttl_seconds)


def jsonb_nullable(value: Any | None) -> str:
    return "NULL" if value is None else jsonb_literal(value)


def sql_int_nullable(value: int | None) -> str:
    return "NULL" if value is None else str(int(value))
