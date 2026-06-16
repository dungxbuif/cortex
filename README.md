# Cortex Platform

Cortex is a personal AI system designed to operate via a Chat UI. It provides capabilities for querying, capturing, analyzing, and taking controlled actions across personal domains (modules).

## Architecture & Core Modules

Cortex uses a **Modular Monolith** architecture built in **Go**. It exposes an OpenAI-compatible API to integrate seamlessly with Open WebUI. The system coordinates LLMs and tool calls at the runtime layer, interacting with underlying modules via stable domain APIs.

The system initially supports three core modules:
1. **[Finance Module](docs/origin_spec/modules/finance.md)**: Personal finance, cash flow, asset management, and reporting.
2. **[Second-Brain Module](docs/origin_spec/modules/second-brain.md)**: Personal knowledge management based on a local Obsidian Vault. Supports inbox capture and RAG-based query.
3. **[Homelab Module](docs/origin_spec/modules/homelab.md)**: Read-only Q&A against the Homelab repository.

For the full system specification, refer to the [Origin Spec](docs/raw_spec/spec.md).

## Harness Framework

This repository uses the **Harness** markdown-first framework to guide AI coding agents (like Claude or Gemini) through the Software Development Life Cycle (SDLC). The repository structure enforces phase gates, testing, documentation reconciliation, and execution verification for all changes.

- SDLC workflow mapping: `Hydration -> Detail Design -> Execution & Test -> Reconciliation -> Dehydration`
- Detailed framework documentation: [docs/README.md](docs/README.md)
- AI Agent rules & system guidelines: [AGENTS.md](AGENTS.md)

## Tech Stack

- **Interface**: Open WebUI (Local Docker)
- **Backend**: Go Modular Monolith, OpenAI-compatible API server
- **AI Model**: Gemini / OpenAI-compatible provider
- **Database**: PostgreSQL with pgvector
- **Automation**: N8n for background integrations and webhooks
