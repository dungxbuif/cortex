import asyncio
import logging
from typing import Any

from ai_service.orchestrator.config import OrchestratorConfig
from ai_service.orchestrator.contracts import (
    ConnectorRegistry,
    ObservationStatus,
    PolicyEnforcer,
    ToolDefinition,
    ToolExecutionContext,
)
from ai_service.orchestrator.messages import SystemMessage

logger = logging.getLogger(__name__)

class ToolExecutionEngine:
    def __init__(
        self,
        connector_registry: ConnectorRegistry,
        policy_enforcer: PolicyEnforcer,
        config: OrchestratorConfig,
    ) -> None:
        self.connector_registry = connector_registry
        self.policy_enforcer = policy_enforcer
        self.config = config

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
        # 1. Policy Guard
        if tool_def.required_capabilities:
            authorized = await self.policy_enforcer.authorize(
                actor_id=context.actor_id,
                capabilities=tool_def.required_capabilities,
                context=context,
            )
            if not authorized:
                if is_confirmation_resume:
                    return {"error": SystemMessage.ERR_PERMISSION_DENIED.value}
                return {"error": "Permission denied"}

        # 2. Confirmation Guard
        if tool_def.confirmation == "require_confirmation" and not is_confirmation_resume:
            return {
                "suspend": True,
                "tool_def": tool_def,
                "arguments": arguments,
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
            return {
                "status": observation.status,
                "data": observation.data,
                "safe_message": observation.safe_user_message,
            }
        except asyncio.TimeoutError:
            logger.error(f"Connector execution timed out for {tool_def.name}")
            return {"error": "Execution timed out"}
        except Exception as exc:
            logger.error(f"Connector execution failed for {tool_def.name}", exc_info=True)
            return {"error": f"Execution failed: {exc}"}
