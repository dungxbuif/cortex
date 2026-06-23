import unittest
from unittest.mock import patch

from ai_service.orchestrator.contracts import ConversationInput
from ai_service.orchestrator.telegram import (
    InMemoryTelegramOutbound,
    TelegramActor,
    TelegramAuthorizationError,
    TelegramSettings,
    TelegramTransportAdapter,
    TelegramUpdateIgnored,
    chunk_telegram_html,
    escape_telegram_html,
    markdown_lite_to_plain_text,
    markdown_lite_to_telegram_html,
    parse_allowed_actors,
    parse_telegram_update,
)


class FakeTelegramHandler:
    def __init__(self, response: str) -> None:
        self.response = response
        self.inputs: list[ConversationInput] = []

    async def process(self, conversation_input: ConversationInput) -> str:
        self.inputs.append(conversation_input)
        return self.response


def _update(text: str = "hello") -> dict:
    return {
        "update_id": 123,
        "message": {
            "message_id": 456,
            "text": text,
            "chat": {"id": 999},
            "from": {"id": 111, "username": "dung"},
        },
    }


class TelegramTransportAdapterTest(unittest.IsolatedAsyncioTestCase):
    def settings(self) -> TelegramSettings:
        return TelegramSettings(
            bot_token="token",
            allowed_actors=(TelegramActor(user_id="111", chat_id="999", owner_id="owner-1"),),
        )

    async def test_normalizes_authorized_text_update_to_conversation_input(self) -> None:
        outbound = InMemoryTelegramOutbound()
        handler = FakeTelegramHandler("ok")
        adapter = TelegramTransportAdapter(settings=self.settings(), outbound=outbound, handler=handler)

        sent = await adapter.handle_update(_update("  note this  "))

        self.assertEqual(len(sent), 1)
        self.assertEqual(outbound.chat_actions, [("999", "typing")])
        self.assertEqual(handler.inputs[0].owner_id, "owner-1")
        self.assertEqual(handler.inputs[0].actor_id, "telegram:111")
        self.assertEqual(handler.inputs[0].channel, "telegram")
        self.assertEqual(handler.inputs[0].channel_ref, "999")
        self.assertEqual(handler.inputs[0].channel_user_id, "111")
        self.assertEqual(handler.inputs[0].content, "note this")
        self.assertEqual(handler.inputs[0].request_id, "telegram-123")

    async def test_rejects_unauthorized_actor_before_handler_call(self) -> None:
        outbound = InMemoryTelegramOutbound()
        handler = FakeTelegramHandler("should not run")
        adapter = TelegramTransportAdapter(settings=self.settings(), outbound=outbound, handler=handler)
        update = _update()
        update["message"]["from"]["id"] = 222

        with self.assertRaises(TelegramAuthorizationError):
            await adapter.handle_update(update)

        self.assertEqual(handler.inputs, [])
        self.assertEqual(outbound.sent_messages, [])

    async def test_escapes_and_chunks_html_responses(self) -> None:
        outbound = InMemoryTelegramOutbound()
        handler = FakeTelegramHandler("A <tag> & B\n\n" + ("word " * 1000))
        adapter = TelegramTransportAdapter(settings=self.settings(), outbound=outbound, handler=handler)

        sent = await adapter.handle_update(_update())

        self.assertGreater(len(sent), 1)
        self.assertTrue(all(len(message.text) <= 4096 for message in sent))
        self.assertIn("A  & B", sent[0].text)
        self.assertTrue(all(message.parse_mode == "" for message in sent))

    async def test_long_markdown_response_uses_plaintext_chunks(self) -> None:
        outbound = InMemoryTelegramOutbound()
        handler = FakeTelegramHandler("**Heading** " + ("long text " * 700))
        adapter = TelegramTransportAdapter(settings=self.settings(), outbound=outbound, handler=handler)

        sent = await adapter.handle_update(_update())

        self.assertGreater(len(sent), 1)
        self.assertTrue(all(len(message.text) <= 4096 for message in sent))
        self.assertTrue(all(message.parse_mode == "" for message in sent))
        self.assertTrue(sent[0].text.startswith("Heading"))
        self.assertNotIn("<b>", sent[0].text)

    async def test_falls_back_to_plain_text_when_html_send_fails(self) -> None:
        outbound = InMemoryTelegramOutbound(fail_html_once=True)
        handler = FakeTelegramHandler("Hello <b>world</b>")
        adapter = TelegramTransportAdapter(settings=self.settings(), outbound=outbound, handler=handler)

        sent = await adapter.handle_update(_update())

        self.assertEqual(sent[0].parse_mode, "")
        self.assertEqual(sent[0].text, "Hello world")


class TelegramHelpersTest(unittest.TestCase):
    def test_parse_allowed_actors(self) -> None:
        actors = parse_allowed_actors("999:111:owner-1, 888:222:owner-2")

        self.assertEqual(len(actors), 2)
        self.assertEqual(actors[0].chat_id, "999")
        self.assertEqual(actors[0].user_id, "111")
        self.assertEqual(actors[0].owner_id, "owner-1")

    def test_settings_from_env(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_ALLOWED_ACTORS": "999:111:owner-1",
                "TELEGRAM_CHUNK_TARGET_CHARS": "3000",
            },
            clear=False,
        ):
            settings = TelegramSettings.from_env()

        self.assertEqual(settings.bot_token, "token")
        self.assertEqual(settings.chunk_target_chars, 3000)
        self.assertEqual(settings.owner_for("999", "111"), "owner-1")

    def test_parse_update_ignores_non_text_messages(self) -> None:
        with self.assertRaises(TelegramUpdateIgnored):
            parse_telegram_update({"update_id": 1, "message": {"chat": {"id": 1}, "from": {"id": 2}}})

    def test_escape_html(self) -> None:
        self.assertEqual(escape_telegram_html("<a>&b"), "&lt;a&gt;&amp;b")

    def test_markdown_lite_to_telegram_html(self) -> None:
        rendered = markdown_lite_to_telegram_html(
            "**Bold** and *italic* with `code` and [link](https://example.com?a=1&b=2)"
        )

        self.assertIn("<b>Bold</b>", rendered)
        self.assertIn("<i>italic</i>", rendered)
        self.assertIn("<code>code</code>", rendered)
        self.assertIn('<a href="https://example.com?a=1&amp;b=2">link</a>', rendered)

    def test_markdown_lite_plain_text_removes_markup(self) -> None:
        plain = markdown_lite_to_plain_text("**Bold** `code` [link](https://example.com)")

        self.assertEqual(plain, "Bold code link (https://example.com)")

    def test_chunking_keeps_messages_under_telegram_limit(self) -> None:
        chunks = chunk_telegram_html("x " * 5000, target_chars=3500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 4096 for chunk in chunks))

    def test_chunking_avoids_html_entity_split(self) -> None:
        chunks = chunk_telegram_html(("x" * 4094) + "&lt;tail", target_chars=4096)

        self.assertEqual(len(chunks[0]), 4094)
        self.assertTrue(chunks[1].startswith("&lt;"))


if __name__ == "__main__":
    unittest.main()
