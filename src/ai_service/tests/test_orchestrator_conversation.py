from __future__ import annotations

from datetime import timedelta
import unittest

from ai_service.core.models import utc_now
from ai_service.orchestrator.conversation import (
    ConversationManager,
    PostgresPsqlConversationRepository,
    hash_tool_args,
)


OWNER_ID = "orchestrator-contract-owner"


class ConversationManagerPostgresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.repository = PostgresPsqlConversationRepository.from_env()
            cls.repository.ping()
        except RuntimeError as exc:
            raise unittest.SkipTest(f"PostgreSQL database is not reachable: {exc}") from exc

    def setUp(self) -> None:
        self.repository.clear_owner(OWNER_ID)
        self.manager = ConversationManager(repository=self.repository)

    def tearDown(self) -> None:
        self.repository.clear_owner(OWNER_ID)

    def test_load_save_and_trim_conversation_messages(self) -> None:
        context = self.manager.load_conversation(OWNER_ID, "telegram", "chat-1")
        self.assertEqual(context.conversation.owner_id, OWNER_ID)
        self.assertEqual(context.messages, ())

        for index in range(25):
            self.manager.save_message(
                context.conversation.id,
                role="user",
                content=f"message {index}",
                message_token_count=1,
            )

        reloaded = self.manager.load_conversation(OWNER_ID, "telegram", "chat-1")
        self.assertEqual(len(reloaded.messages), 20)
        self.assertEqual(reloaded.messages[0].content, "message 5")
        self.assertEqual(reloaded.messages[-1].content, "message 24")

    def test_context_window_respects_token_limit(self) -> None:
        context = self.manager.load_conversation(OWNER_ID, "telegram", "chat-2")
        limited = ConversationManager(
            repository=self.repository,
            context_message_limit=20,
            context_token_limit=6,
        )

        for index in range(5):
            limited.save_message(
                context.conversation.id,
                role="user",
                content=f"token message {index}",
                message_token_count=3,
            )

        reloaded = limited.load_conversation(OWNER_ID, "telegram", "chat-2")
        self.assertEqual([message.content for message in reloaded.messages], ["token message 3", "token message 4"])

    def test_inactive_conversation_starts_fresh_context_window(self) -> None:
        context = self.manager.load_conversation(OWNER_ID, "telegram", "chat-3")
        self.manager.save_message(context.conversation.id, "user", "old message")
        self.repository.set_last_active_at(context.conversation.id, utc_now() - timedelta(hours=25))

        reloaded = self.manager.load_conversation(OWNER_ID, "telegram", "chat-3")

        self.assertTrue(reloaded.reset_due_to_inactivity)
        self.assertEqual(reloaded.messages, ())

    def test_pending_confirmation_requires_same_channel_actor_and_hashes_args(self) -> None:
        context = self.manager.load_conversation(OWNER_ID, "telegram", "chat-4")
        args = {"amount_minor": 500000, "currency": "VND", "wallet": "VCB"}

        confirmation = self.manager.create_pending_confirmation(
            conversation_id=context.conversation.id,
            owner_id=OWNER_ID,
            channel="telegram",
            channel_ref="chat-4",
            channel_user_id="user-1",
            tool_name="finance_create_transaction",
            tool_args=args,
            policy_decision={"decision": "require_confirmation"},
            prompt_shown="Confirm transaction?",
            audit_event_id="audit-1",
        )

        self.assertEqual(confirmation.tool_args_hash, hash_tool_args(args))
        self.assertIsNone(
            self.manager.get_active_confirmation(
                context.conversation.id,
                channel="telegram",
                channel_ref="chat-4",
                channel_user_id="user-2",
            )
        )
        active = self.manager.get_active_confirmation(
            context.conversation.id,
            channel="telegram",
            channel_ref="chat-4",
            channel_user_id="user-1",
        )
        self.assertIsNotNone(active)
        self.assertEqual(active.id, confirmation.id)

        resolved = self.manager.resolve_confirmation(confirmation.id, "confirmed")
        self.assertEqual(resolved.status, "confirmed")
        self.assertIsNotNone(resolved.resolved_at)

    def test_expired_confirmation_is_not_returned(self) -> None:
        context = self.manager.load_conversation(OWNER_ID, "telegram", "chat-5")
        confirmation = self.manager.create_pending_confirmation(
            conversation_id=context.conversation.id,
            owner_id=OWNER_ID,
            channel="telegram",
            channel_ref="chat-5",
            channel_user_id="user-1",
            tool_name="finance_create_transaction",
            tool_args={"amount_minor": 1},
            policy_decision={"decision": "require_confirmation"},
            prompt_shown="Confirm?",
            ttl_seconds=-1,
        )

        active = self.manager.get_active_confirmation(
            context.conversation.id,
            channel="telegram",
            channel_ref="chat-5",
            channel_user_id="user-1",
        )

        self.assertIsNone(active)
        expired = self.repository.get_confirmation(confirmation.id)
        self.assertEqual(expired.status, "expired")


if __name__ == "__main__":
    unittest.main()
