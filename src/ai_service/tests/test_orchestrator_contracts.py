from __future__ import annotations

import unittest
import asyncio

from ai_service.orchestrator.contracts import (
    ConnectorRegistry,
    ModuleHealth,
    ObservationStatus,
    StaticToolRegistry,
    ToolDefinition,
    ToolExecutionContext,
    ToolObservation,
)


class FakeConnector:
    module = "second_brain"

    async def health(self) -> ModuleHealth:
        return ModuleHealth(module=self.module, status="ok")

    def supported_targets(self) -> set[str]:
        return {"SearchKnowledge"}

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict,
        context: ToolExecutionContext,
    ) -> ToolObservation:
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="ok",
            data={"target_api": target_api, "args": args, "request_id": context.request_id},
        )


class ConnectorRegistryTest(unittest.TestCase):
    def test_register_retrieve_and_validate_supported_tool(self) -> None:
        registry = ConnectorRegistry()
        connector = FakeConnector()
        registry.register(connector)

        self.assertIs(registry.get("second_brain"), connector)

        tools = StaticToolRegistry(
            [
                ToolDefinition(
                    name="secondbrain_search_knowledge",
                    module="second_brain",
                    target_api="SearchKnowledge",
                )
            ]
        )
        registry.validate_tools(tools)

    def test_rejects_duplicate_connector(self) -> None:
        registry = ConnectorRegistry()
        registry.register(FakeConnector())

        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register(FakeConnector())

    def test_validation_fails_when_connector_missing(self) -> None:
        registry = ConnectorRegistry()
        tools = StaticToolRegistry(
            [
                ToolDefinition(
                    name="finance_get_net_worth",
                    module="finance",
                    target_api="GetNetWorth",
                )
            ]
        )

        with self.assertRaisesRegex(ValueError, "connector not registered"):
            registry.validate_tools(tools)

    def test_validation_fails_when_target_not_supported(self) -> None:
        registry = ConnectorRegistry()
        registry.register(FakeConnector())
        tools = StaticToolRegistry(
            [
                ToolDefinition(
                    name="secondbrain_capture_note",
                    module="second_brain",
                    target_api="CreateCapture",
                )
            ]
        )

        with self.assertRaisesRegex(ValueError, "not supported"):
            registry.validate_tools(tools)

    def test_health_snapshot_collects_connector_health(self) -> None:
        registry = ConnectorRegistry()
        registry.register(FakeConnector())

        health = asyncio.run(registry.health_snapshot())

        self.assertEqual(len(health), 1)
        self.assertEqual(health[0].module, "second_brain")
        self.assertEqual(health[0].status, "ok")


if __name__ == "__main__":
    unittest.main()
