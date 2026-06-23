from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from ai_service.orchestrator.config import OrchestratorConfig
from ai_service.orchestrator.contracts import (
    ConnectorRegistry,
    ConversationInput,
    PolicyEnforcer,
    ToolDefinition,
    ToolExecutionContext,
    ToolRegistry,
)
from ai_service.orchestrator.conversation import ConversationManager
from ai_service.orchestrator.executor import ToolExecutionEngine
from ai_service.orchestrator.messages import SystemMessage
from ai_service.orchestrator.registry import validate_schema

@dataclass
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class LLMResponse:
    text: str
    tool_calls: list[LLMToolCall] = field(default_factory=list)

class ProviderInterface(Protocol):
    async def generate_response(
        self,
        system_prompt: str,
        messages: tuple[Any, ...],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse:
        ...

logger = logging.getLogger(__name__)

class ReActOrchestrator:
    def __init__(
        self,
        conversation_manager: ConversationManager,
        tool_registry: ToolRegistry,
        connector_registry: ConnectorRegistry,
        provider: ProviderInterface,
        policy_enforcer: PolicyEnforcer,
        config: OrchestratorConfig | None = None,
        system_prompt: str = "You are Cortex, a helpful AI assistant.",
    ) -> None:
        self.conversation_manager = conversation_manager
        self.tool_registry = tool_registry
        self.connector_registry = connector_registry
        self.provider = provider
        self.policy_enforcer = policy_enforcer
        self.config = config or OrchestratorConfig()
        self.system_prompt = system_prompt
        
        self.tool_engine = ToolExecutionEngine(
            connector_registry=connector_registry,
            policy_enforcer=policy_enforcer,
            config=self.config,
        )

    async def process_input(self, user_input: ConversationInput) -> str:
        # Load conversation first to get the canonical database ID
        context = self.conversation_manager.load_conversation(
            owner_id=user_input.owner_id,
            channel=user_input.channel,
            channel_ref=user_input.channel_ref,
        )
        canonical_conversation_id = context.conversation.id

        # Check active confirmation first
        pending = self.conversation_manager.get_active_confirmation(
            conversation_id=canonical_conversation_id,
            channel=user_input.channel,
            channel_ref=user_input.channel_ref,
            channel_user_id=user_input.channel_user_id,
        )

        if pending:
            return await self._handle_confirmation(user_input, canonical_conversation_id, pending)

        # Save standard user message
        self.conversation_manager.save_message(
            conversation_id=canonical_conversation_id,
            role="user",
            content=user_input.content,
        )

        return await self._run_loop(user_input, canonical_conversation_id)

    async def _handle_confirmation(self, user_input: ConversationInput, canonical_conversation_id: str, pending: Any) -> str:
        self.conversation_manager.save_message(
            conversation_id=canonical_conversation_id,
            role="user",
            content=user_input.content,
        )

        is_confirmed = user_input.content.strip().lower() in ["yes", "y", "confirm", "ok", "approve"]
        if not is_confirmed:
            self.conversation_manager.resolve_confirmation(pending.id, "declined")
            declined_msg = SystemMessage.MSG_ACTION_CANCELLED.value
            self.conversation_manager.save_message(
                conversation_id=canonical_conversation_id,
                role="assistant",
                content=declined_msg,
            )
            return declined_msg

        # User approved
        self.conversation_manager.resolve_confirmation(pending.id, "confirmed")
        
        # Execute the tool
        tools = self.tool_registry.list_tools()
        tool_def = next((t for t in tools if t.name == pending.tool_name), None)
        if not tool_def:
            err = "Internal error: Confirmed tool no longer exists."
            self.conversation_manager.save_message(
                conversation_id=canonical_conversation_id,
                role="assistant",
                content=err,
            )
            return err

        ctx = ToolExecutionContext(
            owner_id=user_input.owner_id,
            actor_id=user_input.actor_id,
            actor_type=user_input.actor_type,
            conversation_id=canonical_conversation_id,
            request_id=user_input.request_id,
            channel=user_input.channel,
            confirmation_id=pending.id,
        )

        # Let ToolExecutionEngine handle policy re-check, execution and timeout
        result_data = await self.tool_engine.execute_tool(
            tool_def=tool_def,
            arguments=pending.tool_args,
            context=ctx,
            is_confirmation_resume=True,
        )
        result_data["id"] = "confirm_execution"
        
        # Handle the specific revoke error
        if result_data.get("error") == SystemMessage.ERR_PERMISSION_DENIED.value:
            self.conversation_manager.save_message(
                conversation_id=canonical_conversation_id,
                role="assistant",
                content=result_data["error"],
            )
            return result_data["error"]

        self.conversation_manager.save_message(
            conversation_id=canonical_conversation_id,
            role="tool",
            content="",
            tool_result={"results": [result_data]},
        )

        # Re-enter the loop so the LLM can synthesize the outcome
        return await self._run_loop(user_input, canonical_conversation_id)

    async def _call_llm(self, user_input: ConversationInput, tools: list[ToolDefinition]) -> LLMResponse | str:
        context = self.conversation_manager.load_conversation(
            owner_id=user_input.owner_id,
            channel=user_input.channel,
            channel_ref=user_input.channel_ref,
        )
        try:
            async with asyncio.timeout(self.config.llm_timeout_seconds):
                return await self.provider.generate_response(
                    system_prompt=self.system_prompt,
                    messages=context.messages,
                    tools=tools,
                )
        except asyncio.TimeoutError:
            logger.error("LLM Provider timed out")
            return SystemMessage.ERR_PROVIDER_TIMEOUT.value
        except Exception as exc:
            logger.error("LLM Provider failed", exc_info=True)
            return SystemMessage.ERR_PROVIDER_FAILED.value

    async def _run_loop(self, user_input: ConversationInput, canonical_conversation_id: str) -> str:
        turns = 0
        tools = self.tool_registry.list_tools()

        while turns < self.config.max_turns:
            turns += 1
            
            # 1. Observe & Think (Call LLM)
            llm_response = await self._call_llm(user_input, tools)
            if isinstance(llm_response, str): # Error occurred
                self.conversation_manager.save_message(
                    conversation_id=canonical_conversation_id, role="assistant", content=llm_response
                )
                return llm_response

            if not llm_response.tool_calls:
                self.conversation_manager.save_message(
                    conversation_id=canonical_conversation_id, role="assistant", content=llm_response.text
                )
                return llm_response.text

            # 2. Save intention
            self.conversation_manager.save_message(
                conversation_id=canonical_conversation_id,
                role="assistant",
                content=llm_response.text,
                tool_calls=[
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in llm_response.tool_calls
                ]
            )

            # 3. Validate & Act
            tool_results = []
            requires_confirmation = False
            confirmation_data = None

            for tcall in llm_response.tool_calls:
                tool_def = next((t for t in tools if t.name == tcall.name), None)
                if not tool_def:
                    tool_results.append({"id": tcall.id, "error": f"Tool {tcall.name} not found"})
                    continue

                errors = validate_schema(tool_def.input_schema, tcall.arguments)
                if errors:
                    tool_results.append({"id": tcall.id, "error": f"Validation failed: {errors}"})
                    continue

                ctx = ToolExecutionContext(
                    owner_id=user_input.owner_id,
                    actor_id=user_input.actor_id,
                    actor_type=user_input.actor_type,
                    conversation_id=canonical_conversation_id,
                    request_id=user_input.request_id,
                    channel=user_input.channel,
                )

                # Delegate to ToolExecutionEngine
                result = await self.tool_engine.execute_tool(tool_def, tcall.arguments, ctx)
                
                if result.pop("suspend", False):
                    requires_confirmation = True
                    confirmation_data = (result["tool_def"], result["arguments"])
                    break
                    
                result["id"] = tcall.id
                tool_results.append(result)

            # 4. Handle State Branching (Suspend or Loop)
            if requires_confirmation:
                tool_def, args = confirmation_data  # type: ignore
                prompt_shown = SystemMessage.MSG_CONFIRM_ACTION.value.format(tool_name=tool_def.name, args=args)
                self.conversation_manager.create_pending_confirmation(
                    conversation_id=canonical_conversation_id,
                    owner_id=user_input.owner_id,
                    channel=user_input.channel,
                    channel_ref=user_input.channel_ref,
                    channel_user_id=user_input.channel_user_id,
                    tool_name=tool_def.name,
                    tool_args=args,
                    policy_decision={"decision": "require_confirmation"},
                    prompt_shown=prompt_shown,
                )
                self.conversation_manager.save_message(
                    conversation_id=canonical_conversation_id, role="assistant", content=prompt_shown
                )
                return prompt_shown

            self.conversation_manager.save_message(
                conversation_id=canonical_conversation_id, role="tool", content="", tool_result={"results": tool_results}
            )

        # Max turns exceeded
        fallback_msg = SystemMessage.ERR_MAX_TURNS.value
        self.conversation_manager.save_message(
            conversation_id=canonical_conversation_id, role="assistant", content=fallback_msg
        )
        return fallback_msg
