from typing import Any

class FakeFinanceGrpcClient:
    def __init__(self) -> None:
        self.wallets: list[dict[str, Any]] = []
        self.categories: list[dict[str, Any]] = []
        self.report: dict[str, Any] = {}
        self.net_worth: dict[str, Any] = {}

    def list_wallets(self, owner_id: str) -> list[dict[str, Any]]:
        return self.wallets

    def list_categories(self, owner_id: str) -> list[dict[str, Any]]:
        return self.categories

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
        return self.report

    def get_net_worth(self, owner_id: str, as_of: str | None = None) -> dict[str, Any]:
        return self.net_worth
