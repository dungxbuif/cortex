---
artifact_type: adr
id: ADR-006
status: accepted
owner: shared
human_fields:
  - decision_context
ai_fields:
  - consequences
shared_fields:
  - decision
  - trace_links
---

# ADR-006: Telegram Bot Library For Epic 7 Transport

## Context

Epic 7 makes Telegram the single user-facing chat surface. The Telegram transport needs webhook/polling integration, text update handling, typing actions, outbound message sending, and HTML parse-mode support without hand-rolling Telegram's network protocol.

## Decision

Use `python-telegram-bot` for the real Telegram network boundary, while keeping Cortex's Telegram transport core independent and unit-testable through local adapter protocols.

The core adapter owns Cortex-specific behavior: allowlist authorization, `ConversationInput` normalization, Markdown-lite rendering into Telegram-safe HTML for short messages, plaintext chunking for long responses, environment settings, and plain-text fallback. `python-telegram-bot` is used only by the optional application builder that connects this core adapter to Telegram.

## Alternatives Considered

- Hand-written Telegram HTTP calls: rejected because Telegram update/send semantics, bot lifecycle, and handler wiring are better delegated to a maintained library.
- Hard dependency inside all adapter code: rejected because unit tests and local non-Telegram development should not require network setup.
- Postpone library choice until deployment: rejected because the transport boundary shape affects CTX-704 code and tests now.

## Consequences

- Positive: Telegram runtime code can use a maintained library for bot lifecycle and API calls.
- Positive: Core behavior remains testable without Telegram network access.
- Negative: Adds a Python runtime dependency that must be installed for real Telegram execution.
- Neutral: Webhook/polling deployment details remain outside CTX-704 and can be finalized in a later runtime/deployment slice.

## Trace Links

- Requirement: `REQ-006`
- Phase: `docs/work/phases/PHASE-7-orchestrator-completion.md`
- Ticket: `docs/work/tickets/epic-7/CTX-704.md`
- Detail design: `docs/work/tickets/epic-7/DETAIL_DESIGN.md`
- Validation: `docs/work/VALIDATION_MATRIX.md`
- Release notes: `docs/releases/CHANGELOG.md`
