---
type: Specification
title: "Module Spec: Homelab Infrastructure Knowledge"
description: "Đặc tả nghiệp vụ và domain API cho Module Homelab, đồng bộ repo GitHub dungxbuif/Homelab, index markdown/IaC thành RAG, và chỉ hỗ trợ hỏi đáp read-only."
timestamp: 2026-06-16T00:00:00Z
---

# Module Spec: Homelab Infrastructure Knowledge

## 1. Mục tiêu (Objective)

Homelab module giúp Cortex hiểu, tra cứu và hỏi đáp về hạ tầng Homelab dựa trên repository chính:

- Repository: [dungxbuif/Homelab](https://github.com/dungxbuif/Homelab)
- Canonical source of truth: GitHub repository và commit history.
- Primary knowledge source: `AGENT.md`, `README.md`, `docs/`, `iac/`.
- RAG source: markdown/docs/config đã qua sync, parse, redact, index.

Module này là read-only knowledge module. Cortex chỉ được phép pull Git repository, parse/redact/index dữ liệu, cập nhật RAG, và trả lời câu hỏi dựa trên nguồn đã index. Cortex không được hỗ trợ chat-to-edit, không sửa markdown trong repo Homelab, không tạo patch, không commit, không push, không sửa config và không thực thi thao tác vận hành hạ tầng.

### 1.1. Source-of-Truth Declaration

```yaml
module: homelab
module_type: knowledge_module
canonical_source: github_repo_dungxbuif_homelab
capture_buffer: none
derived_sources:
  - app_git_mirror
  - metadata_index
  - redacted_search_index
  - redacted_rag_index
write_policy:
  chat_write: denied
  repo_write: denied
  runtime_action: denied
sync_policy:
  github_webhook: verify_then_enqueue
  git_pull: allowed_by_sync_worker
  index_after_redaction: required
```

## 2. Repo-Specific Context

Repo Homelab hiện mô tả mô hình **Hybrid Cloud-Edge Homelab** với **Portless Security Design**:

```text
Public Internet
  -> Cloud VPS Edge Gateway
  -> Rathole / WireGuard tunnel
  -> Raspberry Pi 5 Home Gateway
  -> MikroTik Core Router
  -> Proxmox VE
  -> Kubernetes HA Cluster
```

Các nguyên tắc hạ tầng chính đọc được từ repo:

- Portless security: không mở inbound port trên router nhà; traffic public đi qua VPS và tunnel.
- Raspberry Pi 5 là home gateway: Caddy, AdGuard, Rathole, Docker container stack, centralized PostgreSQL, RustFS/MinIO-like storage, registry, n8n.
- MikroTik hEX S là core router: PPPoE Viettel VLAN 35, DHCP, NAT, LAN routing.
- Proxmox VE host chạy VM và Kubernetes HA control-plane.
- Kubernetes HA dùng kubeadm, kube-vip, Cilium, Longhorn, Traefik.
- GitHub Actions + ARC + ArgoCD dùng cho CI/CD/GitOps.
- Sensitive values được kỳ vọng nằm trong `local_vars.json` hoặc `credentials/`, nhưng indexer vẫn phải scan/redact vì repo có thể chứa secret lộ trong docs/config.

## 3. Repository Layout Contract

### 3.1. Entry Points

Indexer và RAG phải ưu tiên đọc theo thứ tự:

1. `AGENT.md`
   - Gateway bắt buộc cho AI agents.
   - Chứa invariants, high-level snapshot, link directory, architecture decisions.
2. `README.md`
   - Public overview, topology, security principles, documentation directory.
3. `docs/MAIN.md`
   - System context, topology, network architecture, service export playbook.
4. Specialized docs:
   - `docs/PI.md`
   - `docs/MIKROTIK.md`
   - `docs/PROXMOX.md`
   - `docs/PRE_REQUIRE.md`
   - `docs/CONTEXT.md`
   - `docs/k8s/*.md`
5. `iac/README.md`
   - IaC runbook for Proxmox/Kubernetes.

### 3.2. Active Knowledge Paths

Default include:

```text
AGENT.md
README.md
docs/**/*.md
iac/README.md
iac/**/*.tf
iac/**/*.tfvars.example
iac/**/*.yml
iac/**/*.yaml
iac/**/*.sh
```

Default exclude:

```text
.git/
deprecated/**
credentials/**
local_vars.json
**/.env
**/*.key
**/*.pem
**/*secret*
**/*kubeconfig*
**/terraform.tfstate*
diagnostics/**/*.raw
diagnostics/**/*.out
```

Notes:

- `deprecated/**` is excluded from default RAG because it contains old selfhost/kubernetes versions and can pollute answers.
- `diagnostics/**` can be indexed only in diagnostic mode and must be redacted first.
- `docs/k8s/DB_INVENTORY.md` and similar inventory files must pass secret scanning before indexing.

### 3.3. Link Graph

The repo already links docs together through markdown links. Indexer must preserve:

- Relative markdown links: `[PI.md](./PI.md)`.
- Parent links: `[iac/README.md](../iac/README.md)`.
- Fragment links: `[Service Export Playbook](docs/MAIN.md#service-export-playbook-end-to-end)`.
- File links inside docs that point to IaC paths.

App should build a document graph:

```text
document -> outgoing_links
document -> backlinks
document -> related_by_path
document -> related_by_service
document -> related_by_component
```

## 4. Sync & Indexing Pipeline

### 4.1. Trigger

Preferred trigger:

```text
GitHub push webhook
  -> verify signature
  -> enqueue sync job
  -> worker fetch/pull
  -> diff changed files
  -> parse/redact/index changed docs
```

Webhook request must not run `git pull` synchronously. It only verifies and enqueues a job.

### 4.2. Git Mirror

The app maintains a local mirror/working tree:

```text
homelab_repo_mirror/
  .git/
  AGENT.md
  README.md
  docs/
  iac/
```

Each indexed document records:

- `repo_url`.
- `branch`.
- `commit_sha`.
- `file_path`.
- `content_hash`.
- `indexed_at`.
- `index_policy`.
- `redaction_status`.

RAG answers should cite file path and commit SHA where possible.

### 4.3. Indexing Modes

```text
normal
  -> active docs + safe IaC metadata

diagnostic
  -> include diagnostics after redaction

historical
  -> include deprecated paths when explicitly requested

security_review
  -> scan secrets/config risks, do not embed raw secrets
```

## 5. Parsers & Extraction

### 5.1. Markdown Parser

Extract:

- Title/headings.
- Sections.
- Code blocks.
- Tables.
- Markdown links.
- Component mentions: VPS, Pi 5, MikroTik, Proxmox, K8s, Longhorn, Traefik, Caddy, Rathole, WireGuard, PostgreSQL, n8n, Registry, RustFS/MinIO.
- Infrastructure invariants: portless, ARM64, no secret commit, no host port exposure.

### 5.2. IaC/YAML Parser

For YAML, Terraform and shell scripts, index metadata, not raw sensitive values.

Extract safe metadata:

- Kubernetes namespaces, services, ingresses, storage classes.
- Docker Compose service names, images, internal ports, networks, volumes.
- Terraform resource types and VM names.
- Ansible roles and playbooks.
- Script entrypoints and high-level purpose.

Do not embed:

- Tokens.
- Passwords.
- Private keys.
- Kubeconfigs.
- Provider secrets.
- `.env` values.

### 5.3. Service Catalog Extraction

Build a service catalog from docs and IaC:

```text
service_name
component_type: docker | k8s | vm | network | database | storage | ingress
host_layer: vps | pi | mikrotik | proxmox | k8s
domain
internal_target
ports_or_portless
source_files
last_seen_commit
```

Examples from current repo:

- `caddy`: Pi gateway ingress.
- `rathole`: tunnel client/server.
- `adguardhome`: LAN DNS resolver.
- `postgres`: centralized DB.
- `n8n`: automation workflow engine.
- `registry`: private Docker registry.
- `rustfs`: S3-compatible object storage.
- `traefik`: Kubernetes ingress.
- `longhorn`: Kubernetes storage.
- `argocd`: GitOps controller.
- `arc`: GitHub Actions Runner Controller.

## 6. RAG Source Policy

Default ranking:

1. `AGENT.md` for invariants and routing decisions.
2. `docs/MAIN.md` for topology/runbooks.
3. Specialized docs for component-specific questions.
4. `iac/README.md` and active IaC files for implementation details.
5. `docs/CONTEXT.md` for history/diagnostics.
6. `deprecated/**` only when user asks about legacy design.

Answer rules:

- Prefer current active docs over deprecated docs.
- Include source path and commit SHA.
- If docs conflict, report the conflict instead of guessing.
- If a file contains redacted content, say the sensitive value is redacted rather than reconstructing it.
- Never expose secrets in answer output.

Example response shape:

```text
Portainer/Traefik/etc. is described as ...
Source:
- docs/PI.md @ <commit_sha>
- docs/MAIN.md @ <commit_sha>
Confidence: high | medium | low
```

## 7. Read-Only Boundary

Homelab module chỉ có bề mặt read-only:

```text
Knowledge APIs
  -> read-only docs/search/RAG/catalog/sync status
```

Read-only RAG can answer:

- "Pi 5 đang chạy những service nào?"
- "Luồng public traffic vào app đi qua đâu?"
- "Cách expose service mới theo repo hiện tại là gì?"
- "K8s cluster dùng kube-vip như thế nào?"
- "Database tập trung nằm ở đâu?"

Chat must not perform or prepare edits:

- Không edit markdown trong repo Homelab.
- Không tạo patch hoặc pull request.
- Không commit/push lên repo.
- Không sửa IaC, YAML, Terraform, shell script hoặc config.
- Không chạy command vận hành.
- Không restart/deploy/rollback/apply manifest.
- Không sửa MikroTik/Proxmox/Caddy/Traefik/Kubernetes config.

If user asks to change Homelab, Cortex should only answer with guidance or point to the source file/section that the user can edit manually in the Homelab repo.

## 8. Homelab Domain APIs

### 8.1. Repo Sync APIs

- `HandleGithubWebhook(command)`: Verify GitHub webhook and enqueue sync job.
- `RunHomelabRepoSync(command)`: Fetch/pull repo mirror and index changed files.
- `GetHomelabSyncStatus(query)`: Show last sync, commit, job status, errors.
- `ListHomelabRepoChanges(query)`: Show changes between indexed commits.
- `ReindexHomelabRepo(scope)`: Reindex full repo, path prefix, or changed files.

### 8.2. Knowledge APIs

- `SearchHomelabDocs(query)`: RAG/search over indexed Homelab docs.
- `GetHomelabDocument(path, commit_sha)`: Read indexed document.
- `GetHomelabLinkGraph(query)`: Return docs/backlinks/related files.
- `GetHomelabRunbook(topic)`: Resolve runbook section for a task.
- `GetHomelabRecentDecisions(query)`: Read architecture/knowledge decisions from `AGENT.md` and `docs/CONTEXT.md`.

### 8.3. Catalog APIs

- `GetServiceCatalog(query)`: List services extracted from docs/IaC.
- `GetServiceDetail(service_name)`: Service metadata, source files, ingress path, host layer.
- `GetNetworkTopology(query)`: Network topology from `README.md`, `AGENT.md`, `docs/MAIN.md`.
- `GetDatabaseInventory(query)`: Database inventory with sensitive fields redacted.
- `GetK8sInventory(query)`: K8s nodes, ingress, storage, CI/CD components.

### 8.4. Validation & Security APIs

- `ScanHomelabRepoSecrets(scope)`: Scan repo content before indexing.
- `ValidateHomelabDocs(scope)`: Check broken links, stale docs, deprecated references.
- `ValidatePortlessInvariant(scope)`: Detect host port exposure in docs/IaC.
- `ValidateArm64Compatibility(scope)`: Flag images/components that may not support ARM64.
- `GetIndexRedactionReport(query)`: Show redacted files/fields and skipped files.

## 9. Business Rules & Invariants

- GitHub repo is Homelab source of truth.
- `AGENT.md` is the gateway context and must be indexed with highest priority.
- Active docs live mainly in `README.md`, `AGENT.md`, `docs/`, and `iac/`.
- `deprecated/**` is excluded from default RAG.
- Secret scanning/redaction is mandatory before indexing.
- RAG must not expose credentials, tokens, keys, kubeconfigs, or exact private values unless explicitly allowed by a separate secure policy.
- Every RAG answer should cite source path and commit SHA.
- GitHub webhook must be verified.
- Webhook must enqueue sync, not perform blocking sync inline.
- Homelab module is read-only from chat perspective.
- Chat cannot edit Homelab docs, IaC, configs, commits, pull requests, or runtime state.
- App can pull Git and update RAG index only.
- Runtime operations are out of scope for this module.
- Portless invariant must be preserved: no new host port exposure except documented exceptions.
- ARM64 compatibility must be checked for Pi 5 workloads.

## 10. API Command/Query Contracts

### 10.1. RunHomelabRepoSync Command

Input:

- `repo_url`.
- `branch`.
- `trigger`: webhook, manual, scheduled.
- `commit_sha` optional.
- `mode`: normal, diagnostic, historical, security_review.

Output:

- `sync_job_id`.
- `previous_commit_sha`.
- `current_commit_sha`.
- `changed_files`.
- `indexed_files`.
- `skipped_files`.
- `redacted_files`.
- `secret_findings_count`.
- `status`.

### 10.2. SearchHomelabDocs Query

Input:

- `query`.
- `mode`: normal, diagnostic, historical.
- `component_filter`.
- `path_filter`.
- `include_deprecated`: default false.
- `include_iac`: default true.

Output:

- Answer-ready context chunks.
- Source path.
- Commit SHA.
- Redaction status.
- Confidence.
- Related docs.

### 10.3. GetServiceDetail Query

Input:

- `service_name`.
- `as_of_commit` optional.

Output:

- Service metadata.
- Host layer.
- Ingress/domain.
- Runtime type.
- Source docs.
- Source IaC files.
- Knowledge notes.
- Known risks/warnings.

### 10.4. ValidatePortlessInvariant Query

Input:

- `scope`.
- `include_deprecated`: default false.

Output:

- Host port exposures detected.
- Allowed exceptions.
- Violations.
- Source files.
- Recommended remediation.

## 11. Audit, Events & Safety

Events:

- `HomelabWebhookReceived`.
- `HomelabRepoSyncQueued`.
- `HomelabRepoSynced`.
- `HomelabDocumentIndexed`.
- `HomelabDocumentSkipped`.
- `HomelabSecretFindingDetected`.
- `HomelabIndexRedactionApplied`.
- `HomelabRagQueryExecuted`.

Audit fields:

- Actor/source.
- Repo URL.
- Branch.
- Commit SHA.
- File path.
- Action type.
- Redaction summary.
- Timestamp.

Safety:

- Never log raw secrets.
- Never include secret snippets in embeddings.
- Keep redacted source separate from raw mirror.
- Store only safe chunks in RAG index.
- Do not execute runtime actions from chat.

## 12. Use Case Backlog

- Sync Homelab repo on GitHub push.
- Search current Homelab architecture.
- Ask "service X chạy ở đâu?".
- Ask "luồng public traffic vào app đi qua đâu?".
- Ask "cách expose service mới là gì?".
- Build service catalog from docs and IaC.
- Build network topology graph.
- Show recent architecture/knowledge decisions from `AGENT.md` and `docs/CONTEXT.md`.
- Validate broken markdown links.
- Validate portless invariant from Docker Compose/K8s manifests.
- Validate ARM64 compatibility for Pi workloads.
- Redact and skip secret-bearing docs before RAG.
- Compare indexed commit with latest repo commit.
- Answer with source path and commit SHA.
- Point user to source docs when they want to manually update Homelab repo.
