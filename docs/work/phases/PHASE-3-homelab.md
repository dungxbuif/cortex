---
artifact_type: phase
id: PHASE-3
status: done
owner: human
human_fields:
  - goal
  - scope
  - out_of_scope
  - priority
  - success_criteria
ai_fields:
  - risks
  - dependencies
  - verification_plan
  - completion_summary
shared_fields:
  - status
  - trace
  - tickets_and_bugs
trace:
  backlog_items:
    - BL-005
  roadmap: ROADMAP
  requirements: []
  tickets:
    - ../tickets/epic-3/CTX-301.md
    - ../tickets/epic-3/CTX-302.md
---

# PHASE-3: Homelab Readonly QA

## Goal
Implement a read-only RAG search and link verification system for the Homelab repository.

## Scope
- Syncing Homelab repository and indexing markdown files into PostgreSQL (pgvector).
- Exposing RAG queries citing source path and commit SHA.
- Scanning relative markdown links and checking for broken links/headings.

## Out of Scope
- IaC / service catalog parsing (since structure is undetermined).
- Modifying documents, code, or settings in the Homelab repository.
- Running infrastructure provisioning or deployment commands.
