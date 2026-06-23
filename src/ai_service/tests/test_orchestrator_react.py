import asyncio
import unittest
from typing import Any
import uuid
import datetime

from ai_service.core.models import utc_now
from ai_service.orchestrator.contracts import (
    ConnectorRegistry,
    ConversationInput,
    Citation,
    ModuleConnector,
    ModuleHealth,
    ObservationStatus,
    PolicyEnforcer,
    ToolDefinition,
    ToolExecutionContext,
    ToolObservation,
    StaticToolRegistry,
)
from ai_service.orchestrator.conversation import (
    Conversation,
    ConversationContext,
    ConversationManager,
    ConversationMessage,
    PendingConfirmation,
)
from ai_service.orchestrator.react import LLMResponse, LLMToolCall, ProviderInterface, ReActOrchestrator
from ai_service.orchestrator.registry import DefaultToolRegistry


def write_capable_registry() -> StaticToolRegistry:
    return StaticToolRegistry(
        [
            *DefaultToolRegistry().list_tools(),
            ToolDefinition(
                name="finance_create_transaction",
                module="finance",
                target_api="CreateTransaction",
                input_schema={
                    "type": "object",
                    "properties": {
                        "amount_minor": {"type": "integer"},
                        "currency": {"type": "string"},
                        "description": {"type": "string"},
                        "wallet_id": {"type": "string"},
                    },
                    "required": ["amount_minor", "currency", "description", "wallet_id"],
                },
                required_capabilities=("finance_write",),
                confirmation="require_confirmation",
            ),
        ]
    )


class FakeProvider(ProviderInterface):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    async def generate_response(
        self,
        system_prompt: str,
        messages: tuple[ConversationMessage, ...],
        tools: list[ToolDefinition],
    ) -> LLMResponse:
        if self.call_count >= len(self.responses):
            raise RuntimeError("FakeProvider ran out of responses")
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp

    async def health(self) -> ModuleHealth:
        return ModuleHealth(module="provider", status="ok")


class FakeConnector(ModuleConnector):
    module = "finance"

    async def health(self) -> ModuleHealth:
        return ModuleHealth(module=self.module, status="ok")

    def supported_targets(self) -> set[str]:
        return {"GetNetWorth", "CreateTransaction"}

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="Fake executed",
            data={"target": target_api, "args": args},
        )


class FailingConnector(FakeConnector):
    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        raise RuntimeError("StatusCode.UNAVAILABLE failed to connect")


class CitedConnector(FakeConnector):
    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="Found 1 result",
            data={"indexed_at": "2026-06-20T00:00:00+00:00"},
            citations=(Citation(label="Doc", source_path="doc.md", source_revision="rev"),),
        )


class FakeConversationManager(ConversationManager):
    def __init__(self) -> None:
        self.messages: list[ConversationMessage] = []
        self.pending: PendingConfirmation | None = None
        self.resolved_status: str | None = None

    def load_conversation(self, owner_id: str, channel: str, channel_ref: str) -> ConversationContext:
        conv = Conversation(
            id="fake_conv_id",
            owner_id=owner_id,
            channel=channel,
            channel_ref=channel_ref,
            metadata={},
            created_at=utc_now(),
            last_active_at=utc_now(),
        )
        return ConversationContext(conversation=conv, messages=tuple(self.messages))

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
        message_token_count: int | None = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            id=f"msg_{uuid.uuid4().hex}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_result=tool_result,
            message_token_count=message_token_count or 1,
            created_at=utc_now(),
        )
        self.messages.append(msg)
        return msg

    def get_active_confirmation(self, conversation_id: str, channel: str, channel_ref: str, channel_user_id: str) -> PendingConfirmation | None:
        return self.pending

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
        self.pending = PendingConfirmation(
            id="fake_conf_id",
            conversation_id=conversation_id,
            owner_id=owner_id,
            channel=channel,
            channel_ref=channel_ref,
            channel_user_id=channel_user_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_args_hash="hash",
            policy_decision=policy_decision,
            audit_event_id=audit_event_id,
            prompt_shown=prompt_shown,
            status="pending",
            created_at=utc_now(),
            expires_at=utc_now() + datetime.timedelta(minutes=5),
            resolved_at=None,
        )
        return self.pending

    def resolve_confirmation(self, confirmation_id: str, status: str) -> PendingConfirmation:
        self.resolved_status = status
        self.pending = None
        return PendingConfirmation(
            id=confirmation_id,
            conversation_id="", owner_id="", channel="", channel_ref="", channel_user_id="",
            tool_name="", tool_args={}, tool_args_hash="", policy_decision={}, audit_event_id="",
            prompt_shown="", status=status, created_at=utc_now(), expires_at=utc_now(), resolved_at=utc_now()
        )


class FakePolicyEnforcer(PolicyEnforcer):
    def __init__(self) -> None:
        self.deny_next = False

    async def authorize(self, actor_id: str, capabilities: tuple[str, ...], context: ToolExecutionContext) -> bool:
        if self.deny_next:
            self.deny_next = False
            return False
        return True


class ReActOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.manager = FakeConversationManager()
        self.registry = DefaultToolRegistry()
        self.connectors = ConnectorRegistry()
        self.connectors.register(FakeConnector())
        self.policy = FakePolicyEnforcer()
        
        self.input = ConversationInput(
            owner_id="user1",
            actor_id="actor1",
            actor_type="user",
            channel="telegram",
            channel_ref="chat1",
            channel_user_id="telegram_user_1",
            content="Hello",
            conversation_id="",
        )

    async def test_successful_one_shot_response(self) -> None:
        provider = FakeProvider([LLMResponse(text="Hi there!")])
        orchestrator = ReActOrchestrator(self.manager, write_capable_registry(), self.connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)
        
        self.assertEqual(res, "Hi there!")
        self.assertEqual(len(self.manager.messages), 2)  # 1 user, 1 assistant
        self.assertEqual(self.manager.messages[-1].role, "assistant")

    async def test_tool_execution_flow(self) -> None:
        provider = FakeProvider([
            LLMResponse(text="Checking...", tool_calls=[
                LLMToolCall(id="call1", name="finance_get_net_worth", arguments={})
            ]),
            LLMResponse(text="Your net worth is 1M.")
        ])
        orchestrator = ReActOrchestrator(self.manager, write_capable_registry(), self.connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)
        
        self.assertEqual(res, "Your net worth is 1M.")
        self.assertEqual(len(self.manager.messages), 4)
        self.assertIn("Fake executed", self.manager.messages[2].content)

    async def test_final_response_appends_tool_warnings_and_citations(self) -> None:
        connectors = ConnectorRegistry()
        connectors.register(CitedConnector())
        provider = FakeProvider([
            LLMResponse(text="Searching...", tool_calls=[
                LLMToolCall(id="call1", name="finance_get_net_worth", arguments={})
            ]),
            LLMResponse(text="Found it."),
        ])
        orchestrator = ReActOrchestrator(self.manager, self.registry, connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)

        self.assertIn("Found it.", res)
        self.assertIn("Index có thể đã cũ", res)
        self.assertIn("Sources:", res)
        self.assertIn("doc.md @ rev", res)

    async def test_health_snapshot_includes_provider_health(self) -> None:
        provider = FakeProvider([LLMResponse(text="unused")])
        orchestrator = ReActOrchestrator(self.manager, self.registry, self.connectors, provider, self.policy)

        health = await orchestrator.health_snapshot()

        self.assertTrue(any(item.module == "finance" and item.status == "ok" for item in health))
        self.assertTrue(any(item.module == "provider" and item.status == "ok" for item in health))

    async def test_grpc_unavailable_returns_controlled_fallback(self) -> None:
        connectors = ConnectorRegistry()
        connectors.register(FailingConnector())
        provider = FakeProvider([
            LLMResponse(text="Checking...", tool_calls=[
                LLMToolCall(id="call1", name="finance_get_net_worth", arguments={})
            ]),
            LLMResponse(text="Should not be called"),
        ])
        orchestrator = ReActOrchestrator(self.manager, self.registry, connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)

        self.assertIn("Dịch vụ tạm thời không khả dụng", res)
        self.assertEqual(provider.call_count, 1)

    async def test_policy_denial(self) -> None:
        self.policy.deny_next = True
        provider = FakeProvider([
            LLMResponse(text="Fetching net worth...", tool_calls=[
                LLMToolCall(id="call1", name="finance_get_net_worth", arguments={})
            ]),
            LLMResponse(text="I am not allowed to do that.")
        ])
        orchestrator = ReActOrchestrator(self.manager, self.registry, self.connectors, provider, self.policy)
        
        res = await orchestrator.process_input(self.input)
        self.assertEqual(res, "I am not allowed to do that.")
        
        # Tool results should contain permission denied
        tool_msg = self.manager.messages[2]
        self.assertEqual(tool_msg.role, "tool")
        self.assertIn("Permission denied", tool_msg.tool_result["results"][0]["error"])

    async def test_tool_validation_failure(self) -> None:
        # Invalid arguments for transaction (missing required amount)
        provider = FakeProvider([
            LLMResponse(text="", tool_calls=[
                LLMToolCall(id="call1", name="finance_create_transaction", arguments={"currency": "USD"})
            ]),
            LLMResponse(text="I need an amount to proceed.")
        ])
        orchestrator = ReActOrchestrator(self.manager, self.registry, self.connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)
        self.assertEqual(res, "I need an amount to proceed.")

    async def test_confirmation_flow(self) -> None:
        # Step 1: LLM wants to execute a write tool
        provider = FakeProvider([
            LLMResponse(text="Preparing to send money", tool_calls=[
                LLMToolCall(id="call1", name="finance_create_transaction", arguments={
                    "amount_minor": 100, "currency": "USD", "description": "Test", "wallet_id": "W1"
                })
            ]),
            # This second response won't be called in Step 1 because it suspends for confirmation
            LLMResponse(text="Should not reach here yet")
        ])
        orchestrator = ReActOrchestrator(self.manager, write_capable_registry(), self.connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)
        self.assertIn("confirm the action", res)
        self.assertIsNotNone(self.manager.pending)

        # Step 2: User confirms
        provider.responses[1] = LLMResponse(text="Transaction successful.")
        confirm_input = ConversationInput(
            owner_id="user1", actor_id="actor1", actor_type="user",
            channel="telegram", channel_ref="chat1", channel_user_id="telegram_user_1",
            content="yes", conversation_id="fake_conv_id",
        )
        res = await orchestrator.process_input(confirm_input)
        
        self.assertEqual(res, "Transaction successful.")
        self.assertEqual(self.manager.resolved_status, "confirmed")

    async def test_confirmation_revoked(self) -> None:
        provider = FakeProvider([
            LLMResponse(text="", tool_calls=[
                LLMToolCall(id="call1", name="finance_create_transaction", arguments={
                    "amount_minor": 100, "currency": "USD", "description": "Test", "wallet_id": "W1"
                })
            ]),
            LLMResponse(text="Transaction complete")
        ])
        orchestrator = ReActOrchestrator(self.manager, write_capable_registry(), self.connectors, provider, self.policy)

        # First step: trigger the confirmation
        await orchestrator.process_input(self.input)
        
        # Now the confirmation is pending. Revoke permission.
        self.policy.deny_next = True

        confirm_input = ConversationInput(
            owner_id="user1",
            actor_id="actor1",
            actor_type="user",
            channel="telegram",
            channel_ref="chat1",
            channel_user_id="telegram_user_1",
            content="Yes",
            conversation_id="",
        )
        res = await orchestrator.process_input(confirm_input)
        self.assertIn("Permission denied. Your access was revoked before confirmation.", res)

    async def test_max_turns_enforced(self) -> None:
        # Provider keeps calling tools indefinitely
        infinite_responses = [
            LLMResponse(text="Loop", tool_calls=[
                LLMToolCall(id=f"c{i}", name="finance_get_net_worth", arguments={})
            ])
            for i in range(10)
        ]
        provider = FakeProvider(infinite_responses)
        orchestrator = ReActOrchestrator(self.manager, self.registry, self.connectors, provider, self.policy)

        res = await orchestrator.process_input(self.input)
        self.assertIn("too many steps", res)

    async def test_llm_provider_timeout(self) -> None:
        class TimeoutProvider(ProviderInterface):
            async def generate_response(self, system_prompt: str, messages: list[Any], tools: list[ToolDefinition] | None = None) -> LLMResponse:
                raise asyncio.TimeoutError()
        
        orchestrator = ReActOrchestrator(self.manager, self.registry, self.connectors, TimeoutProvider(), self.policy)
        res = await orchestrator.process_input(self.input)
        self.assertIn("took too long to respond", res)

    async def test_connector_timeout(self) -> None:
        class TimeoutConnector(FakeConnector):
            async def execute(self, tool_name: str, target_api: str, args: dict[str, Any], context: ToolExecutionContext) -> ToolObservation:
                raise asyncio.TimeoutError()
                
        timeout_connectors = ConnectorRegistry()
        timeout_connectors.register(TimeoutConnector())
        
        provider = FakeProvider([
            LLMResponse(text="", tool_calls=[
                LLMToolCall(id="call1", name="finance_get_net_worth", arguments={})
            ]),
            LLMResponse(text="Fallback response after tool failure")
        ])
        
        orchestrator = ReActOrchestrator(self.manager, self.registry, timeout_connectors, provider, self.policy)
        res = await orchestrator.process_input(self.input)
        self.assertEqual(res, "Fallback response after tool failure")
        
        tool_msg = self.manager.messages[2]
        self.assertEqual(tool_msg.role, "tool")
        self.assertIn("Execution timed out", tool_msg.tool_result["results"][0]["error"])

if __name__ == "__main__":
    unittest.main()
