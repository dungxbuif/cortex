from __future__ import annotations

import asyncio
import unittest
from typing import Any

from ai_service.orchestrator.config import OrchestratorConfig
from ai_service.orchestrator.contracts import (
    AuditEvent,
    ConnectorRegistry,
    ModuleHealth,
    PolicyDecision,
    PolicyDecisionType,
    ToolDefinition,
    ToolExecutionContext,
    ToolObservation,
    ObservationStatus,
)
from ai_service.orchestrator.executor import ToolAdapterExecutor


class FakeConnector:
    module = "finance"

    def __init__(self, fail: Exception | None = None) -> None:
        self.fail = fail
        self.calls = 0

    async def health(self) -> ModuleHealth:
        return ModuleHealth(module=self.module, status="ok")

    def supported_targets(self) -> set[str]:
        return {"GetNetWorth"}

    async def execute(self, tool_name: str, target_api: str, args: dict[str, Any], context: ToolExecutionContext) -> ToolObservation:
        self.calls += 1
        if self.fail:
            raise self.fail
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="ok",
            data={"value": 42},
        )


class FakePolicy:
    def __init__(self, decision: PolicyDecision | None = None) -> None:
        self.decision = decision or PolicyDecision(PolicyDecisionType.ALLOW, "ok")

    async def evaluate(self, tool: ToolDefinition, context: ToolExecutionContext, arguments: dict[str, Any]) -> PolicyDecision:
        return self.decision

    async def authorize(self, actor_id: str, capabilities: tuple[str, ...], context: ToolExecutionContext) -> bool:
        return self.decision.allowed


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append_event(self, event: AuditEvent) -> str:
        self.events.append(event)
        return f"audit-{len(self.events)}"


def tool_def() -> ToolDefinition:
    return ToolDefinition(
        name="finance_get_net_worth",
        module="finance",
        target_api="GetNetWorth",
        input_schema={"type": "object", "properties": {"currency": {"type": "string"}}, "required": ["currency"]},
        required_capabilities=("finance_read",),
    )


def context() -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id="owner",
        actor_id="actor",
        actor_type="user",
        conversation_id="conversation",
        request_id="request",
        channel="telegram",
    )


class ToolAdapterExecutorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.connector = FakeConnector()
        self.connectors = ConnectorRegistry()
        self.connectors.register(self.connector)
        self.audit = FakeAudit()

    async def test_rejects_invalid_arguments_before_policy_or_connector(self) -> None:
        executor = ToolAdapterExecutor(self.connectors, FakePolicy(), OrchestratorConfig(), self.audit)
        result = await executor.execute_tool(tool_def(), {}, context())

        self.assertEqual(result["status"], ObservationStatus.VALIDATION_ERROR)
        self.assertEqual(self.connector.calls, 0)
        self.assertEqual(self.audit.events, [])

    async def test_policy_deny_bypasses_connector_and_audits_denial(self) -> None:
        executor = ToolAdapterExecutor(
            self.connectors,
            FakePolicy(PolicyDecision(PolicyDecisionType.DENY, "no access", "policy-audit")),
            OrchestratorConfig(),
            self.audit,
        )

        result = await executor.execute_tool(tool_def(), {"currency": "VND"}, context())

        self.assertEqual(result["status"], ObservationStatus.PERMISSION_DENIED)
        self.assertEqual(self.connector.calls, 0)
        self.assertEqual(self.audit.events[0].event_type, "PermissionDenied")

    async def test_policy_confirmation_suspends_before_connector(self) -> None:
        executor = ToolAdapterExecutor(
            self.connectors,
            FakePolicy(PolicyDecision(PolicyDecisionType.REQUIRE_CONFIRMATION, "confirm first", "policy-audit")),
            OrchestratorConfig(),
            self.audit,
        )

        result = await executor.execute_tool(tool_def(), {"currency": "VND"}, context())

        self.assertTrue(result["suspend"])
        self.assertEqual(result["policy_decision"]["decision"], "require_confirmation")
        self.assertEqual(self.connector.calls, 0)

    async def test_successful_execution_emits_audit_event(self) -> None:
        executor = ToolAdapterExecutor(self.connectors, FakePolicy(), OrchestratorConfig(), self.audit)

        result = await executor.execute_tool(tool_def(), {"currency": "VND"}, context())

        self.assertEqual(result["status"], ObservationStatus.SUCCESS)
        self.assertEqual(result["audit_event_id"], "audit-1")
        self.assertEqual(self.audit.events[0].event_type, "ToolExecuted")
        self.assertEqual(self.audit.events[0].capability, "read")

    async def test_connector_timeout_maps_to_error_and_audit(self) -> None:
        connectors = ConnectorRegistry()
        connectors.register(FakeConnector(fail=asyncio.TimeoutError()))
        executor = ToolAdapterExecutor(connectors, FakePolicy(), OrchestratorConfig(), self.audit)

        result = await executor.execute_tool(tool_def(), {"currency": "VND"}, context())

        self.assertIn("Execution timed out", result["error"])
        self.assertEqual(self.audit.events[0].event_type, "ToolExecutionFailed")


if __name__ == "__main__":
    unittest.main()
