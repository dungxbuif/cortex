from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from ai_service.orchestrator.presentation import (
    SERVICE_UNAVAILABLE_MESSAGE,
    STALE_INDEX_WARNING,
    graceful_degradation_message,
    render_citations,
    render_finance_data,
    render_tool_results_for_chat,
    stale_index_warning,
)


class PresentationTest(unittest.TestCase):
    def test_renders_deduplicated_citations_with_code_paths(self) -> None:
        rendered = render_citations(
            [
                {"label": "README", "source_path": "README.md", "source_revision": "abc123", "chunk_id": "c1"},
                {"label": "README", "source_path": "README.md", "source_revision": "abc123", "chunk_id": "c1"},
                {"label": "Notes <b>", "source_path": "notes/a<b>.md", "source_revision": "", "chunk_id": ""},
            ]
        )

        self.assertIn("Sources:", rendered)
        self.assertEqual(rendered.count("README.md @ abc123 #c1"), 1)
        self.assertIn("Notes &lt;b&gt;", rendered)
        self.assertIn("<code>notes/a&lt;b&gt;.md</code>", rendered)

    def test_finance_net_worth_uses_pre_block(self) -> None:
        rendered = render_finance_data(
            {
                "cash_total_minor": 1000,
                "asset_value_minor": 5000,
                "liability_minor": 200,
                "receivable_minor": 300,
                "net_worth_minor": 6100,
            }
        )

        self.assertTrue(rendered.startswith("<pre>"))
        self.assertIn("Net worth", rendered)
        self.assertIn("Total", rendered)
        self.assertTrue(rendered.endswith("</pre>"))

    def test_finance_report_uses_pre_block(self) -> None:
        rendered = render_finance_data(
            {
                "income_total_minor": 5000,
                "expense_total_minor": 2000,
                "net_cashflow_minor": 3000,
            }
        )

        self.assertIn("<pre>Financial report", rendered)
        self.assertIn("Income", rendered)
        self.assertIn("Net cashflow", rendered)

    def test_stale_index_warning_after_24_hours(self) -> None:
        now = datetime(2026, 6, 24, tzinfo=UTC)
        stale = (now - timedelta(hours=25)).isoformat()

        self.assertEqual(stale_index_warning({"indexed_at": stale}, now=now), STALE_INDEX_WARNING)
        self.assertEqual(stale_index_warning({"indexed_at": now.isoformat()}, now=now), "")

    def test_graceful_degradation_for_grpc_unavailable(self) -> None:
        result = {"error": "Execution failed: StatusCode.UNAVAILABLE failed to connect"}

        self.assertEqual(graceful_degradation_message(result), SERVICE_UNAVAILABLE_MESSAGE)

    def test_render_tool_results_combines_warnings_and_sources(self) -> None:
        rendered = render_tool_results_for_chat(
            [
                {
                    "data": {"indexed_at": "2026-06-20T00:00:00+00:00"},
                    "safe_message": "Found 1 result",
                    "citations": [{"label": "Doc", "source_path": "doc.md", "source_revision": "rev"}],
                    "warnings": ["partial result"],
                }
            ]
        )

        self.assertIn("Found 1 result", rendered)
        self.assertIn("partial result", rendered)
        self.assertIn("Sources:", rendered)


if __name__ == "__main__":
    unittest.main()
