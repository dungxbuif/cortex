from __future__ import annotations

from typing import Any

from ai_service.orchestrator.contracts import ToolDefinition, ToolRegistry


def validate_schema(schema: dict[str, Any], data: Any, path: str = "") -> list[str]:
    """
    Lightweight JSON Schema validator for tool arguments.
    Supports basic type checking, required fields, and nested objects/arrays.
    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []
    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(data, dict):
            errors.append(f"Expected object at '{path}', got {type(data).__name__}")
            return errors

        required_fields = schema.get("required", [])
        for req in required_fields:
            if req not in data:
                errors.append(f"Missing required field '{req}' in '{path}'")

        properties = schema.get("properties", {})
        for key, val in data.items():
            if key in properties:
                new_path = f"{path}.{key}" if path else key
                errors.extend(validate_schema(properties[key], val, new_path))
            else:
                new_path = f"{path}.{key}" if path else key
                errors.append(f"Unknown property '{new_path}' not defined in schema")

    elif expected_type == "array":
        if not isinstance(data, list):
            errors.append(f"Expected array at '{path}', got {type(data).__name__}")
            return errors
        
        items_schema = schema.get("items")
        if items_schema:
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                errors.extend(validate_schema(items_schema, item, new_path))

    elif expected_type == "string":
        if not isinstance(data, str):
            errors.append(f"Expected string at '{path}', got {type(data).__name__}")
    
    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errors.append(f"Expected integer at '{path}', got {type(data).__name__}")
    
    elif expected_type == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"Expected number at '{path}', got {type(data).__name__}")

    elif expected_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"Expected boolean at '{path}', got {type(data).__name__}")

    return errors


def to_provider_format(tool: ToolDefinition) -> dict[str, Any]:
    """
    Converts a ToolDefinition into the standard JSON Schema format expected by
    OpenAI and Google Gemini function calling APIs.
    """
    return {
        "name": tool.name,
        "description": tool.output_contract,  # using output_contract as description for the LLM
        "parameters": tool.input_schema,
    }


class DefaultToolRegistry(ToolRegistry):
    def __init__(self) -> None:
        self._tools = [
            *_finance_tools(),
            *_second_brain_tools(),
            *_homelab_tools(),
        ]

    def list_tools(
        self, module: str | None = None, capability: str | None = None
    ) -> list[ToolDefinition]:
        return [
            t for t in self._tools
            if (not module or t.module == module)
            and (not capability or capability in t.required_capabilities)
        ]


def _finance_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="finance_get_net_worth",
            module="finance",
            target_api="GetNetWorth",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            required_capabilities=("finance_read",),
            confirmation="none",
            output_contract="Returns the current net worth broken down by accounts.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="finance_create_transaction",
            module="finance",
            target_api="CreateTransaction",
            input_schema={
                "type": "object",
                "properties": {
                    "amount_minor": {"type": "integer", "description": "Amount in minor units (e.g. cents)"},
                    "currency": {"type": "string", "description": "3-letter currency code"},
                    "description": {"type": "string", "description": "Transaction description"},
                    "wallet_id": {"type": "string", "description": "Target wallet ID"}
                },
                "required": ["amount_minor", "currency", "description", "wallet_id"]
            },
            required_capabilities=("finance_write",),
            confirmation="require_confirmation",
            output_contract="Creates a new financial transaction.",
            enabled_by_default=True,
        ),
    ]


def _second_brain_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="secondbrain_search_knowledge",
            module="second_brain",
            target_api="SearchKnowledge",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max number of results"}
                },
                "required": ["query"]
            },
            required_capabilities=("secondbrain_read",),
            confirmation="none",
            output_contract="Returns markdown snippets from Second Brain matching the query.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="secondbrain_get_sync_status",
            module="second_brain",
            target_api="GetSyncStatus",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            required_capabilities=("secondbrain_read",),
            confirmation="none",
            output_contract="Returns Second Brain indexed document and chunk counts.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="secondbrain_list_captures",
            module="second_brain",
            target_api="ListCaptures",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            required_capabilities=("secondbrain_read",),
            confirmation="none",
            output_contract="Lists recent Second Brain capture inbox records.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="secondbrain_capture_note",
            module="second_brain",
            target_api="CreateCapture",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Markdown content to capture"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags"}
                },
                "required": ["content"]
            },
            required_capabilities=("secondbrain_write",),
            confirmation="none",
            output_contract="Captures a new note to the Second Brain inbox.",
            enabled_by_default=True,
        ),
    ]


def _homelab_tools() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="homelab_get_sync_status",
            module="homelab",
            target_api="GetSyncStatus",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            },
            required_capabilities=("homelab_read",),
            confirmation="none",
            output_contract="Returns Homelab indexed document and chunk counts.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="homelab_search_knowledge",
            module="homelab",
            target_api="SearchKnowledge",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for Homelab docs"},
                    "limit": {"type": "integer", "description": "Max number of results"}
                },
                "required": ["query"]
            },
            required_capabilities=("homelab_read",),
            confirmation="none",
            output_contract="Returns redacted Homelab markdown snippets matching the query.",
            enabled_by_default=True,
        ),
        ToolDefinition(
            name="homelab_validate_links",
            module="homelab",
            target_api="ValidateLinks",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Local Homelab mirror path to validate"}
                },
                "required": ["repo_path"]
            },
            required_capabilities=("homelab_read",),
            confirmation="none",
            output_contract="Returns broken markdown links in a local Homelab mirror.",
            enabled_by_default=True,
        ),
    ]
