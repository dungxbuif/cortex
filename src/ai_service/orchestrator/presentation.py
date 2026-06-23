from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ai_service.orchestrator.telegram import escape_telegram_html, sanitize_telegram_html


SERVICE_UNAVAILABLE_MESSAGE = "Dịch vụ tạm thời không khả dụng. Vui lòng thử lại sau hoặc kiểm tra dịch vụ liên quan."
STALE_INDEX_WARNING = "Index có thể đã cũ; dữ liệu đồng bộ gần nhất quá 24 giờ."


def render_tool_results_for_chat(results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    citations: list[dict[str, Any]] = []
    warnings: list[str] = []

    for result in results:
        fallback = graceful_degradation_message(result)
        if fallback:
            return fallback

        data = result.get("data")
        if isinstance(data, dict):
            rendered_data = render_finance_data(data)
            if rendered_data:
                parts.append(rendered_data)

            stale_warning = stale_index_warning(data)
            if stale_warning:
                warnings.append(stale_warning)

        safe_message = result.get("safe_message")
        if isinstance(safe_message, str) and safe_message and not parts:
            parts.append(safe_message)

        raw_warnings = result.get("warnings")
        if isinstance(raw_warnings, list):
            warnings.extend(str(item) for item in raw_warnings if item)

        raw_citations = result.get("citations")
        if isinstance(raw_citations, list):
            citations.extend(item for item in raw_citations if isinstance(item, dict))

    if warnings:
        parts.append(render_warnings(warnings))
    if citations:
        parts.append(render_citations(citations))

    return "\n\n".join(part for part in parts if part).strip()


def render_finance_data(data: dict[str, Any]) -> str:
    if _has_any(data, ("net_worth_minor", "cash_total_minor", "asset_value_minor", "liability_minor")):
        return _render_net_worth(data)
    if _has_any(data, ("income_total_minor", "expense_total_minor", "net_cashflow_minor")):
        return _render_financial_report(data)
    if "wallets" in data and isinstance(data["wallets"], list):
        return _render_records("Wallets", data["wallets"], ("name", "currency", "current_balance_minor", "status"))
    if "categories" in data and isinstance(data["categories"], list):
        return _render_records("Categories", data["categories"], ("name", "type", "status"))
    return ""


def render_citations(citations: list[dict[str, Any]]) -> str:
    lines = ["Sources:"]
    seen: set[tuple[str, str, str]] = set()
    for citation in citations:
        label = str(citation.get("label") or citation.get("source_path") or "source")
        source_path = str(citation.get("source_path") or label)
        revision = str(citation.get("source_revision") or "")
        chunk_id = str(citation.get("chunk_id") or "")
        key = (source_path, revision, chunk_id)
        if key in seen:
            continue
        seen.add(key)
        suffix = f" @ {revision}" if revision else ""
        chunk = f" #{chunk_id}" if chunk_id else ""
        lines.append(f"- {escape_telegram_html(label)}: <code>{escape_telegram_html(source_path + suffix + chunk)}</code>")
    return sanitize_telegram_html("\n".join(lines))


def render_warnings(warnings: list[str]) -> str:
    unique: list[str] = []
    for warning in warnings:
        if warning and warning not in unique:
            unique.append(warning)
    return "\n".join(f"- {warning}" for warning in unique)


def stale_index_warning(data: dict[str, Any], now: datetime | None = None) -> str:
    raw = (
        data.get("last_synced_at")
        or data.get("synced_at")
        or data.get("indexed_at")
        or data.get("last_indexed_at")
    )
    if not isinstance(raw, str) or not raw.strip():
        return ""
    parsed = _parse_datetime(raw)
    if parsed is None:
        return STALE_INDEX_WARNING
    current = now or datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return STALE_INDEX_WARNING if current - parsed > timedelta(hours=24) else ""


def graceful_degradation_message(result: dict[str, Any]) -> str:
    error = result.get("error")
    if not isinstance(error, str):
        return ""
    lowered = error.lower()
    offline_markers = (
        "unavailable",
        "connection refused",
        "failed to connect",
        "deadline exceeded",
        "grpc",
        "transport is closing",
        "service unavailable",
        "policy service unavailable",
        "audit service unavailable",
        "finance service unavailable",
    )
    return SERVICE_UNAVAILABLE_MESSAGE if any(marker in lowered for marker in offline_markers) else ""


def append_tool_context_to_response(response: str, tool_results: list[dict[str, Any]]) -> str:
    warnings, citations = extract_warnings_and_citations(tool_results)
    additions: list[str] = []
    if warnings and not _contains_any(response, warnings):
        additions.append(render_warnings(warnings))
    if citations and "Sources:" not in response:
        additions.append(render_citations(citations))
    if not additions:
        return response
    return "\n\n".join([response.strip(), *additions]).strip()


def extract_warnings_and_citations(tool_results: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    warnings: list[str] = []
    citations: list[dict[str, Any]] = []
    for result in tool_results:
        data = result.get("data")
        if isinstance(data, dict):
            warning = stale_index_warning(data)
            if warning:
                warnings.append(warning)
        raw_warnings = result.get("warnings")
        if isinstance(raw_warnings, list):
            warnings.extend(str(item) for item in raw_warnings if item)
        raw_citations = result.get("citations")
        if isinstance(raw_citations, list):
            citations.extend(item for item in raw_citations if isinstance(item, dict))
    return _unique_strings(warnings), citations


def _render_net_worth(data: dict[str, Any]) -> str:
    lines = [
        "Net worth",
        _money_line("Cash", data.get("cash_total_minor")),
        _money_line("Assets", data.get("asset_value_minor")),
        _money_line("Liabilities", data.get("liability_minor")),
        _money_line("Receivables", data.get("receivable_minor")),
        _money_line("Total", data.get("net_worth_minor")),
    ]
    return _pre_block("\n".join(line for line in lines if line))


def _render_financial_report(data: dict[str, Any]) -> str:
    lines = [
        "Financial report",
        _money_line("Income", data.get("income_total_minor")),
        _money_line("Expense", data.get("expense_total_minor")),
        _money_line("Net cashflow", data.get("net_cashflow_minor")),
        _money_line("Transfers in", data.get("transfer_in_total_minor")),
        _money_line("Transfers out", data.get("transfer_out_total_minor")),
    ]
    return _pre_block("\n".join(line for line in lines if line))


def _render_records(title: str, records: list[Any], columns: tuple[str, ...]) -> str:
    rows = [title]
    for record in records[:20]:
        if not isinstance(record, dict):
            continue
        cells = [str(record.get(column, "")) for column in columns if record.get(column) not in (None, "")]
        if cells:
            rows.append("- " + " | ".join(cells))
    return _pre_block("\n".join(rows))


def _money_line(label: str, value: Any) -> str:
    if value is None:
        return ""
    return f"{label:<14} {value}"


def _pre_block(value: str) -> str:
    return sanitize_telegram_html(f"<pre>{escape_telegram_html(value)}</pre>")


def _has_any(data: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in data for key in keys)


def _contains_any(text: str, values: list[str]) -> bool:
    return any(value in text for value in values)


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value and value not in unique:
            unique.append(value)
    return unique


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
