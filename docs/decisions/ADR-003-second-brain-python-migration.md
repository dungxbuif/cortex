---
artifact_type: decision_record
id: ADR-003
title: Use Python for Orchestrator and AI-heavy processing, Go for API-heavy components
status: approved
owner: human
human_fields: [approval, tradeoff_acceptance]
ai_fields: [context, options, decision, consequences]
shared_fields: [status, linked_components]
---

# ADR-003: Use Python for Orchestrator and AI-heavy processing, Go for API-heavy components

## Approval

- **Status**: Approved
- **Approver**: dungxbuif
- **Date**: 2026-06-17

## Context

The Second Brain module was initially built as part of the Go Modular Monolith. However, implementing robust RAG (Retrieval-Augmented Generation) pipelines and Document Understanding requires significant NLP capabilities:
1. **Markdown & Frontmatter Processing:** Obsidian Vaults contain complex markdown with nested blocks, wikilinks, and YAML frontmatter. Tools like `python-frontmatter` and `markdown-it-py` are far more mature than Go equivalents.
2. **Quality Evaluation:** Our strategy requires strict "golden testing", 6-layer evaluations, and custom metrics (Zero RAG leak, citation coverage). Python's ecosystem (e.g., `pytest`, Ragas, LangSmith) is the industry standard for LLM/RAG evaluation.
3. **Advanced RAG Features:** Features like semantic chunking, graph extraction, and re-ranking are significantly easier to implement using Python libraries.

The Go implementation resulted in brittle string manipulation for chunking and lacks the robust ecosystem needed to hit our strict Quality Gates for personal data safety.

## Options Considered

1. **Option 1: Build everything from scratch in Go.** (Original approach)
   - *Pros:* Keeps the entire Cortex system as a single monolithic binary.
   - *Cons:* Extremely high effort to build robust markdown splitters, evaluators, and YAML parsers. Ecosystem is small.
2. **Option 2: Migrate Second Brain to Python, called via Go Orchestrator over REST.**
   - *Pros:* Access to the entire Python ML/NLP ecosystem. Clean boundary mapping. Go still controls routing, authentication, and orchestration.
   - *Cons:* Adds a second service to the deployment stack (requires Docker Compose or multiple processes).
3. **Option 3: Use Go for API-heavy components, Python for AI-heavy components, and connect them through internal gRPC.**
   - *Pros:* Keeps public/API-heavy components in Go, uses Python where AI/RAG ecosystem matters, and gives Go/Python a typed internal contract that is safer than ad hoc REST JSON.
   - *Cons:* Requires protobuf definitions, generated clients/servers, and local dev tooling for gRPC.
4. **Option 4: Use Python for Orchestrator + AI-heavy services, Go for API-heavy deterministic components, and connect runtimes through internal gRPC.**
   - *Pros:* Puts LLM orchestration, tool routing, provider SDKs, evals, and RAG in Python where the ecosystem is strongest, while preserving Go for public API gateways and deterministic high-throughput APIs.
   - *Cons:* Moves the main runtime away from the original Go modular-monolith plan and requires explicit service contracts for Go domain components.

## Decision

We will adopt **Option 4**.

Python owns the **Orchestrator / LLM Tool Runtime** and AI-heavy services. This includes intent handling, context planning, provider integration, tool-call parsing, RAG coordination, prompt/context assembly, response synthesis, and AI evaluation.

Go is preferred for API-heavy and deterministic service components: public API gateway surfaces, stable domain APIs, high-throughput request handling, Finance business APIs, Homelab API adapters, and other components where strict typing/concurrency/simple deployment matter more than AI ecosystem depth.

Go and Python communicate through internal **gRPC** contracts. REST/FastAPI may still exist for local debugging, development smoke tests, or administrative probes, but gRPC is the durable service boundary between Go and Python.

### Integration Strategy
- **Go API Gateway / Domain Services:** Go may expose the OpenAI-compatible HTTP surface and deterministic domain APIs. Go services expose internal gRPC contracts to Python when the Python Orchestrator needs Finance, Homelab, audit, or other API-heavy capabilities.
- **Python Orchestrator:** Owns chat runtime, LLM provider calls, tool registry, context planning, tool-call parsing, permission orchestration, and response synthesis.
- **Python AI Services:** Expose gRPC services for Capture, Sync, Indexing, and RAG Retrieval. FastAPI is optional and non-authoritative for dev/debug.
- **Database:** The Python app will connect directly to the shared PostgreSQL instance (`pgvector` support via SQLAlchemy/SQLModel).
- **Asynchronous Workers:** Background synchronization and indexing of the Vault will be handled by Python workers (Celery/RQ or simple background tasks).

## Consequences

- **Positive:** We can implement the full 9-phase RAG Mental Model and evaluation strategy effectively.
- **Positive:** We gain access to Python's immense ML ecosystem for future features (rerankers, knowledge graphs).
- **Positive:** gRPC gives Python Orchestrator, Python AI services, and Go domain/API services typed contracts, generated clients, stable request/response schemas, and clearer compatibility boundaries.
- **Negative:** Increased operational complexity (need to manage Python environment/Docker image alongside the Go binary).
- **Negative:** gRPC adds protobuf generation and contract-versioning workflow.
- **Negative:** Original Go modular-monolith assumption no longer applies to the Orchestrator; docs and future tickets must treat Orchestrator as Python-owned.
- **Mitigation:** Use `uv` or `poetry` for Python dependency management and Docker Compose for seamless local development.
- **Mitigation:** Keep `.proto` files as the source of truth for cross-language internal contracts and test Go/Python compatibility with contract tests.

## Linked Components
- Second Brain RAG Pipeline
- Orchestrator Tool Routing
