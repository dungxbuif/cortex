---
artifact_type: adr
id: ADR-002
status: accepted
owner: human
human_fields: [decision, alternatives_considered]
ai_fields: [context, consequences, linked_docs]
shared_fields: [status]
---

# ADR-002: Module Boundary Principle

## Context
Cortex utilizes LLMs (Large Language Models) as the primary interaction interface. Because LLMs are non-deterministic and can generate unpredictable outputs, there is a risk of AI logic bleeding into business logic, making the system untestable, hard to maintain, and prone to silent data corruption. 

## Decision
We enforce a strict **Module Boundary Principle**:
1. **Domain modules** (Finance, Second Brain, Homelab) must NOT contain LLM prompts, ReAct loops, OpenAI schemas, or chat history management.
2. They expose deterministic, stable **Domain APIs** with strict business validation.
3. The **Orchestrator Layer** (above the domain modules) is exclusively responsible for interpreting intent, extracting structured parameters via LLM tool calls, and requesting confirmation from users when confidence is low.
4. The Orchestrator interacts with domain modules merely by invoking these Domain APIs via a Tool Adapter.

## Alternatives Considered
- **LLM logic inside each module**: Allowing each module (e.g., Finance) to have its own internal LLM agent to process natural language. Rejected because it duplicates LLM orchestration logic, makes unit testing business logic nearly impossible without mocking LLMs, and violates separation of concerns.

## Consequences
- **Positive**: Domain logic is highly testable without LLMs. It is easy to swap the LLM provider or the orchestration framework later. The business rules remain deterministic and safe.
- **Negative**: The Orchestrator layer (written in Python) has to be generic and powerful enough to map dynamic LLM outputs to strict gRPC schemas / API request parameters for the Go-based domain APIs, requiring a robust Tool Adapter layer.

## Linked Docs
- `docs/raw_spec/spec.md`
- `docs/architecture/ARCHITECTURE.md`
