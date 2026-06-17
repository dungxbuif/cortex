---
artifact_type: requirement_spec
id: REQ-MASTER
status: draft
owner: human
human_fields: [product_summary, goals, non_goals, users_and_stakeholders, acceptance_criteria]
ai_fields: [functional_requirements, non_functional_requirements, constraints, linked_decisions]
shared_fields: [status, trace]
---

# Product Specification

## Field Ownership

- Human owns product intent, goals, non-goals, users, and acceptance criteria.
- AI may draft requirements, constraints, and linked decisions for review.

## Product Summary

Cortex is a personal AI system accessed through Open WebUI. It routes chat requests into deterministic domain APIs for personal finance, second-brain knowledge, and homelab knowledge. The Finance module is the first write-capable business module and uses PostgreSQL as its canonical source of truth.

## Goals

- Record and query personal finance data through stable Finance Domain APIs.
- Keep Finance business rules deterministic and outside LLM/orchestrator logic.
- Track wallets, categories, transactions, investments, reports, and net worth.
- Model investments so buying an asset moves value from cash to holdings instead of appearing as living expense.

## Non-Goals

- Direct bank/broker/provider sync in the current Finance service epic.
- OCR or receipt extraction inside the Finance module.
- Tax-lot reporting beyond weighted-average cost basis.
- Direct UI forms outside Open WebUI/chat for the current product direction.

## Users And Stakeholders

- TBD

## Functional Requirements

- Finance must support wallet/account CRUD, balance queries, archive state, and total wallet calculations.
- Finance must support income, expense, and transfer transactions.
- Finance transfer transactions must be stored as paired `transfer_out` and `transfer_in` rows sharing one `transfer_group_id`.
- Finance must support categories with parent/child structure and aliases.
- Finance must support investment asset master data with asset type, symbol, name, currency, unit, price source, and active state.
- Finance must support asset transactions for buy, sell, transfer in/out, dividend, stock dividend, split, and manual adjustment.
- Finance must preserve asset price history and calculate current holdings, weighted-average cost basis, current value, realized gain, and unrealized gain.
- Finance must track money I owe and money other people owe me, including counterparty, principal, paid/collected amount, remaining amount, due date, note, and status.
- Finance must link debt repayment or debt collection to cash transactions so wallet balances and debt balances do not diverge.
- Finance must calculate net worth from included cash wallets plus current asset values plus receivables minus debts/liabilities.
- Finance must generate structured report data for income, expense, category breakdown, wallet breakdown, and excluded amounts.
- Finance reports must separate ordinary living cashflow from investment buys, sells, and dividends by default.
- Finance reports must use business-effective timestamps such as `occurred_at`, `paid_at`, `priced_at`, and `as_of`; `created_at` is the system record creation time and must not drive financial period reports.
- Finance holdings must be rebuildable from historical asset transactions and market price history.

## Non-Functional Requirements

- Domain modules must not contain LLM prompts, OpenAI schemas, ReAct loops, chat history, or response synthesis.
- Finance money amounts, prices, balances, and valuation fields must not use floating point representation.
- Finance persisted money fields must use integer minor units; asset quantity fields must use fixed precision decimals.
- Investment buys must be excluded from living-expense reporting while still affecting cash and net worth.
- Debt records with direction `i_owe` are liabilities; records with direction `owed_to_me` are receivable assets.
- Finance persisted tables must carry auditable fields for actor and timestamp metadata: `created_at`, `created_by`, `updated_at`, and `updated_by` for all finance tables, plus `deleted_at` and `deleted_by` only where soft delete is supported.
- Finance soft-delete fields are limited to correction-oriented tables; soft-deleted records must be excluded from reporting, valuation rebuilds, and debt settlement calculations.
- Audit fields answer who touched a row and when; audit events answer what changed before/after and why.
- Sensitive finance data must not be written to logs or error messages as raw payloads.

## Constraints

- PostgreSQL is the canonical Finance data store.
- Open WebUI remains the primary user interface through the OpenAI-compatible proxy.
- Provider-based market price sync is future scope; manual or internal price updates are allowed in the service design.

## Acceptance Criteria

- Wallet, category, transaction, asset, reporting, and net-worth service tickets have planned validation rows.
- Asset valuation distinguishes historical transaction prices from current market prices.
- Net worth output includes current asset value and realized/unrealized gain/loss where asset data exists.

## Linked Decisions

- [ADR-001: Go Modular Monolith](../decisions/ADR-001-go-modular-monolith.md)
- [ADR-002: Module Boundary Principle](../decisions/ADR-002-module-boundary-principle.md)
