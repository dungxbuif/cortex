from __future__ import annotations

import unittest

from ai_service.grpc import cortex_pb2
from ai_service.orchestrator.contracts import (
    AuditEvent,
    PolicyDecisionType,
    ToolDefinition,
    ToolExecutionContext,
)
from ai_service.orchestrator.policy import GrpcAuditSink, GrpcPolicyEnforcer, map_registry_capability


class FakePolicyStub:
    def __init__(self, response: cortex_pb2.EvaluatePolicyResponse) -> None:
        self.response = response
        self.requests: list[cortex_pb2.EvaluatePolicyRequest] = []

    def EvaluatePolicy(self, request: cortex_pb2.EvaluatePolicyRequest) -> cortex_pb2.EvaluatePolicyResponse:
        self.requests.append(request)
        return self.response


class FakeAuditStub:
    def __init__(self) -> None:
        self.requests: list[cortex_pb2.AppendAuditEventRequest] = []

    def AppendAuditEvent(self, request: cortex_pb2.AppendAuditEventRequest) -> cortex_pb2.AppendAuditEventResponse:
        self.requests.append(request)
        return cortex_pb2.AppendAuditEventResponse(audit_event_id="audit-123")


class GrpcPolicyClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_grpc_policy_enforcer_maps_decision_and_capability(self) -> None:
        stub = FakePolicyStub(
            cortex_pb2.EvaluatePolicyResponse(
                decision="require_confirmation",
                reason="finance write requires confirmation",
                audit_event_id="audit-policy",
            )
        )
        enforcer = GrpcPolicyEnforcer(stub)  # type: ignore[arg-type]
        decision = await enforcer.evaluate(
            ToolDefinition(
                name="finance_create_transaction",
                module="finance",
                target_api="CreateTransaction",
                required_capabilities=("finance_write",),
                confirmation="require_confirmation",
            ),
            ToolExecutionContext(
                owner_id="owner",
                actor_id="actor",
                actor_type="user",
                conversation_id="conversation",
                request_id="request",
                channel="telegram",
            ),
            {"amount_minor": 100},
        )

        self.assertEqual(decision.decision, PolicyDecisionType.REQUIRE_CONFIRMATION)
        self.assertEqual(decision.audit_event_id, "audit-policy")
        self.assertEqual(stub.requests[0].module, "finance")
        self.assertEqual(stub.requests[0].capability, "write_app_db")
        self.assertTrue(stub.requests[0].high_impact)

    async def test_grpc_audit_sink_appends_event(self) -> None:
        stub = FakeAuditStub()
        sink = GrpcAuditSink(stub)  # type: ignore[arg-type]

        audit_id = await sink.append_event(
            AuditEvent(
                event_type="ToolExecuted",
                module="second_brain",
                actor_type="user",
                actor_id="actor",
                conversation_id="conversation",
                request_id="request",
                tool_name="secondbrain_capture_note",
                capability="capture",
                status="success",
                metadata={"result": "ok"},
            )
        )

        self.assertEqual(audit_id, "audit-123")
        self.assertEqual(stub.requests[0].event_type, "ToolExecuted")
        self.assertEqual(stub.requests[0].metadata[0].key, "result")

    def test_registry_capability_mapping(self) -> None:
        self.assertEqual(map_registry_capability("finance", "finance_write"), ("finance", "write_app_db"))
        self.assertEqual(map_registry_capability("second_brain", "secondbrain_write"), ("second_brain", "capture"))
        self.assertEqual(map_registry_capability("homelab", "homelab_read"), ("homelab", "read"))


if __name__ == "__main__":
    unittest.main()
