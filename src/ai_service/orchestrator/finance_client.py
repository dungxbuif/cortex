from __future__ import annotations

from typing import Any
import grpc
from ai_service.grpc import cortex_pb2, cortex_pb2_grpc


class FinanceGrpcClient:
    def __init__(self, stub: cortex_pb2_grpc.FinanceServiceStub, channel: grpc.Channel | None = None, timeout_seconds: float = 5.0) -> None:
        self.stub = stub
        self.channel = channel
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_address(cls, address: str, timeout_seconds: float = 5.0) -> "FinanceGrpcClient":
        channel = grpc.insecure_channel(address)
        stub = cortex_pb2_grpc.FinanceServiceStub(channel)
        return cls(stub, channel, timeout_seconds)

    def close(self) -> None:
        if self.channel:
            self.channel.close()

    def list_wallets(self, owner_id: str) -> list[dict[str, Any]]:
        resp = self.stub.ListWallets(
            cortex_pb2.ListWalletsRequest(owner_id=owner_id),
            timeout=self.timeout_seconds,
        )
        return [
            {
                "id": w.id,
                "owner_id": w.owner_id,
                "name": w.name,
                "type": w.type,
                "currency": w.currency,
                "initial_balance_minor": w.initial_balance_minor,
                "current_balance_minor": w.current_balance_minor,
                "include_in_total": w.include_in_total,
                "status": w.status,
                "created_at": w.created_at,
                "updated_at": w.updated_at,
            }
            for w in resp.wallets
        ]

    def list_categories(self, owner_id: str) -> list[dict[str, Any]]:
        resp = self.stub.ListCategories(
            cortex_pb2.ListCategoriesRequest(owner_id=owner_id),
            timeout=self.timeout_seconds,
        )
        return [
            {
                "id": c.id,
                "owner_id": c.owner_id,
                "parent_id": c.parent_id if c.HasField("parent_id") else None,
                "name": c.name,
                "type": c.type,
                "aliases": c.aliases,
                "status": c.status,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in resp.categories
        ]

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
    ) -> dict[str, Any]:
        req = cortex_pb2.GetFinancialReportRequest(
            owner_id=owner_id,
            period_start=period_start,
            period_end=period_end,
            include_investment=include_investment,
            group_by=group_by,
            use_created_at_audit_date=use_created_at_audit_date,
        )
        if wallet_id is not None:
            req.wallet_id = wallet_id
        if category_id is not None:
            req.category_id = category_id

        resp = self.stub.GetFinancialReport(req, timeout=self.timeout_seconds)
        return {
            "period_start": resp.period_start,
            "period_end": resp.period_end,
            "group_by": resp.group_by,
            "income_total_minor": resp.income_total_minor,
            "expense_total_minor": resp.expense_total_minor,
            "net_cashflow_minor": resp.net_cashflow_minor,
            "transfer_in_total_minor": resp.transfer_in_total_minor,
            "transfer_out_total_minor": resp.transfer_out_total_minor,
            "excluded_total_minor": resp.excluded_total_minor,
            "investment_cash_movement_total_minor": resp.investment_cash_movement_total_minor,
            "by_category": dict(resp.by_category),
            "by_wallet": dict(resp.by_wallet),
            "by_period": dict(resp.by_period),
            "warnings": list(resp.warnings),
        }

    def get_net_worth(self, owner_id: str, as_of: str | None = None) -> dict[str, Any]:
        req = cortex_pb2.GetNetWorthRequest(owner_id=owner_id)
        if as_of is not None:
            req.as_of = as_of
        resp = self.stub.GetNetWorth(req, timeout=self.timeout_seconds)
        return {
            "as_of": resp.as_of,
            "cash_total_minor": resp.cash_total_minor,
            "asset_value_minor": resp.asset_value_minor,
            "liability_minor": resp.liability_minor,
            "receivable_minor": resp.receivable_minor,
            "net_worth_minor": resp.net_worth_minor,
            "realized_gain_minor": resp.realized_gain_minor,
            "unrealized_gain_minor": resp.unrealized_gain_minor,
            "warnings": list(resp.warnings),
        }


