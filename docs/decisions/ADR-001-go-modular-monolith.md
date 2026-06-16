---
artifact_type: adr
id: ADR-001
status: accepted
owner: human
human_fields: [decision, alternatives_considered]
ai_fields: [context, consequences, linked_docs]
shared_fields: [status]
---

# ADR-001: Use Go Modular Monolith

## Context
Cortex is a personal AI system managing domains like Finance, Second Brain, and Homelab. It needs to expose an OpenAI-compatible API to interact with Open WebUI, handle LLM orchestrations, process RAG indexes, and provide stable domain APIs for data persistence. We need to decide on the architecture and tech stack for the core backend.

## Decision
We will build the Cortex Backend as a **Modular Monolith** using **Go**.
- **Go** is chosen for its high performance, strong concurrency model (useful for background syncing/indexing and API orchestration), and static typing.
- **Modular Monolith** is chosen over microservices to avoid operational overhead, latency from network calls, and complex deployments, while still enforcing strict boundaries between domains (Finance, Homelab, Second Brain).

## Alternatives Considered
- **Python/FastAPI**: Popular for AI, but often harder to maintain cleanly as a strict modular monolith, and slower for concurrent sync/indexing jobs without complex async patterns.
- **Node.js/TypeScript**: Good ecosystem, but Go offers a more robust concurrency model and simpler single-binary deployment for homelab self-hosting.
- **Microservices**: Overkill for a personal system, leading to unnecessary complexity in managing inter-service communication and distributed tracing.

## Consequences
- **Positive**: Simple single-binary deployment, great performance, strict compile-time boundaries between modules.
- **Negative**: Go's ecosystem for AI/LLM orchestration is less mature than Python's, so we may need to build or adapt custom LLM orchestrator logic (or rely on generic API clients).

## Linked Docs
- `docs/raw_spec/spec.md`
- `docs/architecture/ARCHITECTURE.md`
