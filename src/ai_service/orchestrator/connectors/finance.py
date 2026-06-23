from __future__ import annotations

import asyncio
from typing import Any, Protocol

from ai_service.orchestrator.contracts import (
    ModuleHealth,
    ObservationStatus,
    ToolExecutionContext,
    ToolObservation,
)
from .helpers import _unsupported

class FinanceClientProtocol(Protocol):
    def list_wallets(self, owner_id: str) -> list[dict[str, Any]]: ...
    def list_categories(self, owner_id: str) -> list[dict[str, Any]]: ...
    def get_financial_report(
        self,
        owner_id: str,
        period_start: str,
        period_end: str,
        wallet_id: str | None = None,
        category_id: str | None = None,
        include_investment: bool = False,
        group_by: str = "none",
        use_created_at_audit_date: bool = False,
    ) -> dict[str, Any]: ...
    def get_net_worth(self, owner_id: str, as_of: str | None = None) -> dict[str, Any]: ...

class FinanceConnector:
    module = "finance"

    def __init__(self, client: FinanceClientProtocol) -> None:
        self.client = client
        self._handlers = {
            "ListWallets": self._list_wallets,
            "ListCategories": self._list_categories,
            "GetFinancialReport": self._get_financial_report,
            "GetNetWorth": self._get_net_worth,
            "CreateTransaction": self._create_transaction,
        }

    async def health(self) -> ModuleHealth:
        try:
            if hasattr(self.client, "stub") and hasattr(self.client.stub, "HealthCheck"):
                from ai_service.grpc import cortex_pb2
                await asyncio.to_thread(self.client.stub.HealthCheck, cortex_pb2.HealthCheckRequest())
            status_msg = "ok"
        except Exception as exc:
            return ModuleHealth(module=self.module, status="degraded", message=str(exc))
        return ModuleHealth(module=self.module, status="ok", message=status_msg)

    def supported_targets(self) -> set[str]:
        return {"ListWallets", "ListCategories", "GetFinancialReport", "GetNetWorth", "CreateTransaction"}

    async def execute(
        self,
        tool_name: str,
        target_api: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        handler = self._handlers.get(target_api)
        if handler is None:
            return _unsupported(self.module, tool_name, target_api)
        return await asyncio.to_thread(handler, tool_name, args, context)

    def _list_wallets(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        wallets = self.client.list_wallets(owner_id=context.owner_id)
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(wallets)} wallet(s).",
            data={"wallets": wallets},
        )

    def _list_categories(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        categories = self.client.list_categories(owner_id=context.owner_id)
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message=f"Found {len(categories)} category/categories.",
            data={"categories": categories},
        )

    def _get_financial_report(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        period_start = str(args.get("period_start", ""))
        period_end = str(args.get("period_end", ""))
        if not period_start or not period_end:
            return ToolObservation(
                status=ObservationStatus.VALIDATION_ERROR,
                module=self.module,
                tool=tool_name,
                safe_user_message="Both period_start and period_end are required and must be valid ISO8601 strings.",
            )

        report = self.client.get_financial_report(
            owner_id=context.owner_id,
            period_start=period_start,
            period_end=period_end,
            wallet_id=args.get("wallet_id"),
            category_id=args.get("category_id"),
            include_investment=bool(args.get("include_investment", False)),
            group_by=str(args.get("group_by", "none")),
            use_created_at_audit_date=bool(args.get("use_created_at_audit_date", False)),
        )
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="Financial report generated successfully.",
            data=report,
        )

    def _get_net_worth(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        net_worth = self.client.get_net_worth(
            owner_id=context.owner_id,
            as_of=args.get("as_of"),
        )
        return ToolObservation(
            status=ObservationStatus.SUCCESS,
            module=self.module,
            tool=tool_name,
            safe_user_message="Net worth report retrieved successfully.",
            data=net_worth,
        )

    def _create_transaction(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolObservation:
        return ToolObservation(
            status=ObservationStatus.VALIDATION_ERROR,
            module=self.module,
            tool=tool_name,
            safe_user_message="Write operations are unsupported in the read-only Finance scope.",
            warnings=("Write operations are future-scope.",),
        )



