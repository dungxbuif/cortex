from __future__ import annotations

import asyncio
from typing import Any

from ai_service.grpc import cortex_pb2, cortex_pb2_grpc
from ai_service.orchestrator.contracts import (
    AuditEvent,
    PolicyDecision,
    PolicyDecisionType,
    ToolDefinition,
    ToolExecutionContext,
)


class StaticPolicyEnforcer:
    async def evaluate(
        self,
        tool: ToolDefinition,
        context: ToolExecutionContext,
        arguments: dict[str, Any],
    ) -> PolicyDecision:
        return PolicyDecision(PolicyDecisionType.ALLOW, "static allow")

    async def authorize(
        self,
        actor_id: str,
        capabilities: tuple[str, ...],
        context: ToolExecutionContext,
    ) -> bool:
        return True


class GrpcPolicyEnforcer:
    def __init__(self, stub: cortex_pb2_grpc.PolicyServiceStub) -> None:
        self.stub = stub

    async def evaluate(
        self,
        tool: ToolDefinition,
        context: ToolExecutionContext,
        arguments: dict[str, Any],
    ) -> PolicyDecision:
        decisions: list[PolicyDecision] = []
        for capability in tool.required_capabilities or ("",):
            module, mapped_capability = map_registry_capability(tool.module, capability)
            response = await asyncio.to_thread(
                self.stub.EvaluatePolicy,
                cortex_pb2.EvaluatePolicyRequest(
                    module=module,
                    capability=mapped_capability,
                    actor_type=context.actor_type,
                    actor_id=context.actor_id,
                    conversation_id=context.conversation_id,
                    request_id=context.request_id,
                    tool_name=tool.name,
                    high_impact=tool.confirmation == "require_confirmation",
                    ambiguous=bool(arguments.get("ambiguous")),
                    low_confidence=bool(arguments.get("low_confidence")),
                    money_movement=tool.module == "finance" and tool.confirmation == "require_confirmation",
                    metadata=_dict_to_entries({"registry_capability": capability}),
                ),
            )
            decisions.append(
                PolicyDecision(
                    decision=_policy_decision_type(response.decision),
                    reason=response.reason,
                    audit_event_id=response.audit_event_id or None,
                )
            )
        return _strictest_decision(decisions)

    async def authorize(
        self,
        actor_id: str,
        capabilities: tuple[str, ...],
        context: ToolExecutionContext,
    ) -> bool:
        for capability in capabilities:
            module, mapped_capability = infer_module_capability(capability)
            response = await asyncio.to_thread(
                self.stub.EvaluatePolicy,
                cortex_pb2.EvaluatePolicyRequest(
                    module=module,
                    capability=mapped_capability,
                    actor_type=context.actor_type,
                    actor_id=actor_id,
                    conversation_id=context.conversation_id,
                    request_id=context.request_id,
                ),
            )
            if response.decision != PolicyDecisionType.ALLOW.value:
                return False
        return True


class GrpcAuditSink:
    def __init__(self, stub: cortex_pb2_grpc.AuditServiceStub) -> None:
        self.stub = stub

    async def append_event(self, event: AuditEvent) -> str:
        response = await asyncio.to_thread(
            self.stub.AppendAuditEvent,
            cortex_pb2.AppendAuditEventRequest(
                event_type=event.event_type,
                module=event.module,
                actor_type=event.actor_type,
                actor_id=event.actor_id,
                conversation_id=event.conversation_id,
                request_id=event.request_id,
                tool_name=event.tool_name,
                capability=event.capability,
                status=event.status,
                source_ref=_dict_to_entries(event.source_ref),
                target_ref=_dict_to_entries(event.target_ref),
                metadata=_dict_to_entries(event.metadata),
            ),
        )
        return response.audit_event_id


class NoopAuditSink:
    async def append_event(self, event: AuditEvent) -> str:
        return ""


def map_registry_capability(module: str, capability: str) -> tuple[str, str]:
    if capability == "finance_read":
        return "finance", "read"
    if capability == "finance_write":
        return "finance", "write_app_db"
    if capability == "secondbrain_read":
        return "second_brain", "read"
    if capability == "secondbrain_write":
        return "second_brain", "capture"
    if capability == "homelab_read":
        return "homelab", "read"
    if capability:
        return module, capability
    return module, "read"


def infer_module_capability(capability: str) -> tuple[str, str]:
    for prefix, module in (
        ("finance_", "finance"),
        ("secondbrain_", "second_brain"),
        ("homelab_", "homelab"),
    ):
        if capability.startswith(prefix):
            return map_registry_capability(module, capability)
    return "", capability


def _policy_decision_type(value: str) -> PolicyDecisionType:
    try:
        return PolicyDecisionType(value)
    except ValueError:
        return PolicyDecisionType.DENY


def _strictest_decision(decisions: list[PolicyDecision]) -> PolicyDecision:
    if not decisions:
        return PolicyDecision(PolicyDecisionType.ALLOW, "no capability required")
    for decision_type in (
        PolicyDecisionType.DENY,
        PolicyDecisionType.MANUAL_ACTION_REQUIRED,
        PolicyDecisionType.REQUIRE_CLARIFICATION,
        PolicyDecisionType.REQUIRE_CONFIRMATION,
    ):
        for decision in decisions:
            if decision.decision == decision_type:
                return decision
    return decisions[0]


def _dict_to_entries(values: dict[str, Any]) -> list[cortex_pb2.StringMapEntry]:
    return [
        cortex_pb2.StringMapEntry(key=str(key), value=str(value))
        for key, value in values.items()
        if value is not None
    ]


__all__ = [
    "GrpcAuditSink",
    "GrpcPolicyEnforcer",
    "NoopAuditSink",
    "StaticPolicyEnforcer",
    "infer_module_capability",
    "map_registry_capability",
]
