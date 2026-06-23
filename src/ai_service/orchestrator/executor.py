import asyncio
import logging
from typing import Any

from ai_service.orchestrator.config import OrchestratorConfig
from ai_service.orchestrator.contracts import (
    AuditEvent,
    AuditSink,
    ConnectorRegistry,
    ObservationStatus,
    PolicyDecision,
    PolicyDecisionType,
    PolicyEnforcer,
    ToolDefinition,
    ToolExecutionContext,
)
from ai_service.orchestrator.messages import SystemMessage
from ai_service.orchestrator.policy import NoopAuditSink, map_registry_capability
from ai_service.orchestrator.registry import validate_schema

logger = logging.getLogger(__name__)

class ToolExecutionEngine:
    def __init__(
        self,
        connector_registry: ConnectorRegistry,
        policy_enforcer: PolicyEnforcer,
        config: OrchestratorConfig,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.connector_registry = connector_registry
        self.policy_enforcer = policy_enforcer
        self.config = config
        self.audit_sink = audit_sink or NoopAuditSink()

    async def execute_tool(
        self,
        tool_def: ToolDefinition,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
        is_confirmation_resume: bool = False,
    ) -> dict[str, Any]:
        """
        Executes a single tool call through the Policy -> Timeout -> Connector pipeline.
        Returns a dictionary representing the tool result or error.
        """
        validation_errors = validate_schema(tool_def.input_schema, arguments)
        if validation_errors:
            return {
                "status": ObservationStatus.VALIDATION_ERROR,
                "error": f"Validation failed: {validation_errors}",
            }

        # 1. Policy Guard
        policy_decision = await self._evaluate_policy(tool_def, arguments, context)
        if policy_decision.decision == PolicyDecisionType.DENY:
            await self._audit(tool_def, context, "PermissionDenied", "denied", arguments, {
                "reason": policy_decision.reason,
                "policy_audit_event_id": policy_decision.audit_event_id or "",
            })
            if is_confirmation_resume:
                return {"error": SystemMessage.ERR_PERMISSION_DENIED.value}
            return {
                "status": ObservationStatus.PERMISSION_DENIED,
                "error": policy_decision.reason or "Permission denied",
                "audit_event_id": policy_decision.audit_event_id,
            }

        if policy_decision.requires_confirmation and not is_confirmation_resume:
            return {
                "suspend": True,
                "tool_def": tool_def,
                "arguments": arguments,
                "policy_decision": {
                    "decision": policy_decision.decision.value,
                    "reason": policy_decision.reason,
                    "audit_event_id": policy_decision.audit_event_id,
                },
            }

        # 2. Confirmation Guard
        if tool_def.confirmation == "require_confirmation" and not is_confirmation_resume:
            return {
                "suspend": True,
                "tool_def": tool_def,
                "arguments": arguments,
                "policy_decision": {
                    "decision": "require_confirmation",
                    "reason": "tool requires confirmation",
                    "audit_event_id": policy_decision.audit_event_id,
                },
            }

        # 3. Execution with Timeout Guard
        connector = self.connector_registry.get(tool_def.module)
        try:
            async with asyncio.timeout(self.config.tool_timeout_seconds):
                observation = await connector.execute(
                    tool_name=tool_def.name,
                    target_api=tool_def.target_api,
                    args=arguments,
                    context=context,
                )
            status = "success" if observation.status == ObservationStatus.SUCCESS else "failed"
            audit_id = await self._audit(
                tool_def,
                context,
                "ToolExecuted",
                status,
                arguments,
                {"observation_status": observation.status.value},
            )
            return {
                "status": observation.status,
                "data": observation.data,
                "safe_message": observation.safe_user_message,
                "citations": [citation.__dict__ for citation in observation.citations],
                "warnings": list(observation.warnings),
                "audit_event_id": observation.audit_event_id or audit_id,
            }
        except asyncio.TimeoutError:
            logger.error(f"Connector execution timed out for {tool_def.name}")
            await self._audit(tool_def, context, "ToolExecutionFailed", "failed", arguments, {"error": "timeout"})
            return {"error": "Execution timed out"}
        except Exception as exc:
            logger.error(f"Connector execution failed for {tool_def.name}", exc_info=True)
            await self._audit(tool_def, context, "ToolExecutionFailed", "failed", arguments, {"error": str(exc)})
            return {"error": f"Execution failed: {exc}"}

    async def _evaluate_policy(
        self,
        tool_def: ToolDefinition,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> PolicyDecision:
        if not tool_def.required_capabilities:
            return PolicyDecision(PolicyDecisionType.ALLOW, "no capability required")
        evaluate = getattr(self.policy_enforcer, "evaluate", None)
        if callable(evaluate):
            decision = await evaluate(tool_def, context, arguments)
            if isinstance(decision, PolicyDecision):
                return decision
        authorized = await self.policy_enforcer.authorize(
            actor_id=context.actor_id,
            capabilities=tool_def.required_capabilities,
            context=context,
        )
        if authorized:
            return PolicyDecision(PolicyDecisionType.ALLOW, "authorized")
        return PolicyDecision(PolicyDecisionType.DENY, "Permission denied")

    async def _audit(
        self,
        tool_def: ToolDefinition,
        context: ToolExecutionContext,
        event_type: str,
        status: str,
        arguments: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        capability = tool_def.required_capabilities[0] if tool_def.required_capabilities else ""
        _, mapped_capability = map_registry_capability(tool_def.module, capability)
        try:
            return await self.audit_sink.append_event(
                AuditEvent(
                    event_type=event_type,
                    module=tool_def.module,
                    actor_type=context.actor_type,
                    actor_id=context.actor_id,
                    conversation_id=context.conversation_id,
                    request_id=context.request_id,
                    tool_name=tool_def.name,
                    capability=mapped_capability,
                    status=status,
                    target_ref={"target_api": tool_def.target_api},
                    metadata={**metadata, "arguments": _safe_metadata(arguments)},
                )
            )
        except Exception:
            logger.error("Audit event append failed for %s", tool_def.name, exc_info=True)
            return ""


def _safe_metadata(arguments: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in arguments.items() if "secret" not in str(key).lower()}


ToolAdapterExecutor = ToolExecutionEngine
