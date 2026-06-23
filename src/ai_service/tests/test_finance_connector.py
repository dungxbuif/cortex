from __future__ import annotations

import unittest
from ai_service.orchestrator.connectors import FinanceConnector
from ai_service.orchestrator.contracts import ConnectorRegistry, ObservationStatus, ToolExecutionContext
from ai_service.tests.fakes import FakeFinanceGrpcClient
from ai_service.orchestrator.registry import DefaultToolRegistry


def tool_context(owner_id: str = "finance-owner") -> ToolExecutionContext:
    return ToolExecutionContext(
        owner_id=owner_id,
        actor_id="telegram-user",
        actor_type="user",
        conversation_id="conversation-id",
        request_id="request-id",
        channel="telegram",
    )


class FinanceConnectorTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = FakeFinanceGrpcClient()
        self.connector = FinanceConnector(self.client)
        self.context = tool_context()

    async def test_list_wallets_success(self) -> None:
        self.client.wallets = [
            {
                "id": "wal_1",
                "owner_id": self.context.owner_id,
                "name": "Cash Wallet",
                "type": "basic",
                "currency": "VND",
                "initial_balance_minor": 10000,
                "current_balance_minor": 15000,
                "include_in_total": True,
                "status": "active",
                "created_at": "2026-06-24T00:00:00Z",
                "updated_at": "2026-06-24T00:00:00Z",
            }
        ]

        observation = await self.connector.execute(
            "finance_list_wallets",
            "ListWallets",
            {},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(len(observation.data["wallets"]), 1)
        self.assertEqual(observation.data["wallets"][0]["id"], "wal_1")
        self.assertIn("Found 1 wallet(s)", observation.safe_user_message)

    async def test_list_categories_success(self) -> None:
        self.client.categories = [
            {
                "id": "cat_1",
                "owner_id": self.context.owner_id,
                "parent_id": None,
                "name": "Food",
                "type": "expense",
                "aliases": "grocery",
                "status": "active",
                "created_at": "2026-06-24T00:00:00Z",
                "updated_at": "2026-06-24T00:00:00Z",
            }
        ]

        observation = await self.connector.execute(
            "finance_list_categories",
            "ListCategories",
            {},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(len(observation.data["categories"]), 1)
        self.assertEqual(observation.data["categories"][0]["id"], "cat_1")

    async def test_get_financial_report_missing_dates(self) -> None:
        observation = await self.connector.execute(
            "finance_get_financial_report",
            "GetFinancialReport",
            {},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.VALIDATION_ERROR)
        self.assertIn("required", observation.safe_user_message)

    async def test_get_financial_report_success(self) -> None:
        self.client.report = {
            "period_start": "2026-06-01T00:00:00Z",
            "period_end": "2026-07-01T00:00:00Z",
            "group_by": "none",
            "income_total_minor": 5000,
            "expense_total_minor": 2000,
            "net_cashflow_minor": 3000,
            "transfer_in_total_minor": 0,
            "transfer_out_total_minor": 0,
            "excluded_total_minor": 0,
            "investment_cash_movement_total_minor": 0,
            "by_category": {"cat_1": -2000},
            "by_wallet": {"wal_1": 3000},
            "by_period": {"all": 3000},
            "warnings": [],
        }

        observation = await self.connector.execute(
            "finance_get_financial_report",
            "GetFinancialReport",
            {
                "period_start": "2026-06-01T00:00:00Z",
                "period_end": "2026-07-01T00:00:00Z",
            },
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(observation.data["income_total_minor"], 5000)
        self.assertEqual(observation.data["by_category"]["cat_1"], -2000)

    async def test_get_net_worth_success(self) -> None:
        self.client.net_worth = {
            "as_of": "2026-06-24T00:00:00Z",
            "cash_total_minor": 15000,
            "asset_value_minor": 50000,
            "liability_minor": 5000,
            "receivable_minor": 1000,
            "net_worth_minor": 61000,
            "realized_gain_minor": 0,
            "unrealized_gain_minor": 0,
            "warnings": [],
        }

        observation = await self.connector.execute(
            "finance_get_net_worth",
            "GetNetWorth",
            {"as_of": "2026-06-24T00:00:00Z"},
            self.context,
        )

        self.assertEqual(observation.status, ObservationStatus.SUCCESS)
        self.assertEqual(observation.data["net_worth_minor"], 61000)

    async def test_unsupported_write_unmapped(self) -> None:
        observation = await self.connector.execute(
            "finance_create_transaction",
            "CreateTransaction",
            {"amount_minor": 5000, "currency": "USD"},
            self.context,
        )
        self.assertEqual(observation.status, ObservationStatus.VALIDATION_ERROR)
        self.assertIn("Unsupported target API for finance: CreateTransaction", observation.safe_user_message)


    def test_registry_validation_for_finance_targets(self) -> None:
        registry = ConnectorRegistry()
        registry.register(self.connector)

