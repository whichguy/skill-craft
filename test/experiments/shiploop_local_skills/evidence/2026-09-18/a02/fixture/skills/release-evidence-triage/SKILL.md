---
name: release-evidence-triage
description: Triage a local release-evidence bundle against this repository's authoritative contract.
---

# Release evidence triage

Use this repository-local prompt skill when deciding whether a release-evidence
bundle is clear or blocked.

1. Read [the release-evidence contract](../../docs/release-contract.md) as the
   decision authority, then read `data/bundle.json` and relevant durable lessons.
2. Resolve the request and select receipts only as the contract directs. Match the
   requested identity before comparing attempts, and preserve required-check
   order in the result.
3. Treat the highest numeric matching attempt as current evidence. A pass from an
   earlier attempt does not override a later failure or block.
4. Write the exact contract-shaped `output/decision.json`, then validate both its
   JSON structure and the receipt-selection result. Keep the local decision
   distinct from deployment authorization.

The contract is authoritative for request defaults, field values, and decision
semantics; do not duplicate those defaults here.
