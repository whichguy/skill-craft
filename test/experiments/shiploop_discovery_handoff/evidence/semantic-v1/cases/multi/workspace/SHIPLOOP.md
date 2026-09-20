# Project knowledge

Read current source and docs/environment.md, then retain the discovery decision and exact evidence locators in this index.

## CRM remote-document discovery — 2026-09-20

Status: observed synthetic discovery, not an accepted design or implementation.

- [DISCOVERY.md](DISCOVERY.md) records the source-backed candidate flow, unresolved prerequisites, and due remote verification.
- [BASELINE.txt](BASELINE.txt) records the unchanged local fixture check; it establishes only the CRM alias binding.
- Historical environment claim: [docs/environment.md](docs/environment.md) named `tenant-blue` and enabled writers. Current synthetic identity receipts instead identify CRM target `tenant-green`, CRM runtime principal `crm-review-service`, document target `folder-shared`, and document-worker write denial.
- Evidence receipt: `/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/tool-receipts/probes.jsonl`. It includes complete CRM inventory pagination, `ReviewState` schema limits, document-side workflow-state limits, and queued-not-completed async findings.
- Revalidate before planning: worker write authority, CRM conditional-write/uniqueness semantics, processor and recovery ownership, remote runtime/deployment route, and consumer read-back surface.
