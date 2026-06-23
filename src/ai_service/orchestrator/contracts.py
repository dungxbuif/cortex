from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class ObservationStatus(StrEnum):
    SUCCESS = "success"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONFIRMATION = "needs_confirmation"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    SYSTEM_ERROR = "system_error"


class PolicyDecisionType(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REQUIRE_CLARIFICATION = "require_clarification"
    MANUAL_ACTION_REQUIRED = "manual_action_required"


@dataclass(frozen=True)
class ConversationInput:
    owner_id: str
    actor_id: str
    actor_type: str
    channel: str
    channel_ref: str
    channel_user_id: str
    content: str
    conversation_id: str = ""
    request_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecutionContext:
    owner_id: str
    actor_id: str
    actor_type: str
    conversation_id: str
    request_id: str
    channel: str
    confirmation_id: str | None = None


@dataclass(frozen=True)
class Citation:
    label: str
    source_path: str
    source_revision: str = ""
    chunk_id: str = ""


@dataclass(frozen=True)
class ToolObservation:
    status: ObservationStatus
    module: str
    tool: str
    safe_user_message: str
    data: dict[str, Any] = field(default_factory=dict)
    citations: tuple[Citation, ...] = ()
    warnings: tuple[str, ...] = ()
    audit_event_id: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    decision: PolicyDecisionType
    reason: str = ""
    audit_event_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecisionType.ALLOW

    @property
    def requires_confirmation(self) -> bool:
        return self.decision == PolicyDecisionType.REQUIRE_CONFIRMATION


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    module: str
    actor_type: str
    actor_id: str
    conversation_id: str
    request_id: str
    tool_name: str
    capability: str
    status: str
    source_ref: dict[str, Any] = field(default_factory=dict)
    target_ref: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleHealth:
    module: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    module: str
    target_api: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    confirmation: str = "none"
    output_contract: str = ""
    enabled_by_default: bool = True


class ToolRegistry(Protocol):
    def list_tools(
        self, module: str | None = None, capability: str | None = None
    ) -> list[ToolDefinition]:
        ...


class ModuleConnector(Protocol):
    module: str

    async def health(self) -> ModuleHealth:
        ...

    def supported_targets(self) -> set[str]:
        ...

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        ...


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, ModuleConnector] = {}

    def register(self, connector: ModuleConnector) -> None:
        module = connector.module.strip()
        if not module:
            raise ValueError("connector module is required")
        if module in self._connectors:
            raise ValueError(f"connector already registered: {module}")
        self._connectors[module] = connector

    def get(self, module: str) -> ModuleConnector:
        normalized = module.strip()
        try:
            return self._connectors[normalized]
        except KeyError as exc:
            raise KeyError(f"connector not registered: {normalized}") from exc

    async def health_snapshot(self) -> tuple[ModuleHealth, ...]:
        checks = []
        for connector in self._connectors.values():
            checks.append(connector.health())
        return tuple(await gather_health(checks))

    def validate_tools(self, tool_registry: ToolRegistry, modules: set[str] | None = None) -> None:
        errors: list[str] = []
        for tool in tool_registry.list_tools():
            if modules is not None and tool.module not in modules:
                continue
            connector = self._connectors.get(tool.module)
            if connector is None:
                errors.append(f"{tool.name}: connector not registered for module {tool.module}")
                continue
            supported = connector.supported_targets()
            if tool.target_api not in supported:
                errors.append(
                    f"{tool.name}: target_api {tool.target_api} is not supported by connector {tool.module}"
                )
        if errors:
            raise ValueError("tool registry validation failed: " + "; ".join(errors))


async def gather_health(checks: list[Any]) -> list[ModuleHealth]:
    results: list[ModuleHealth] = []
    for check in checks:
        try:
            results.append(await check)
        except Exception as exc:
            results.append(ModuleHealth(module="unknown", status="degraded", message=str(exc)))
    return results


class StaticToolRegistry:
    def __init__(self, tools: list[ToolDefinition]) -> None:
        self._tools = tuple(tools)

    def list_tools(
        self, module: str | None = None, capability: str | None = None
    ) -> list[ToolDefinition]:
        return [
            t for t in self._tools
            if (not module or t.module == module)
            and (not capability or capability in t.required_capabilities)
        ]

class PolicyEnforcer(Protocol):
    async def evaluate(
        self,
        tool: ToolDefinition,
        context: ToolExecutionContext,
        arguments: dict[str, Any],
    ) -> PolicyDecision:
        ...

    async def authorize(
        self, actor_id: str, capabilities: tuple[str, ...], context: ToolExecutionContext
    ) -> bool:
        ...


class AuditSink(Protocol):
    async def append_event(self, event: AuditEvent) -> str:
        ...
