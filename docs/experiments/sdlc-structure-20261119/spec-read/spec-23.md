# Help desk ticket service

## Requirements

### R-1 Response deadline
Basis: November 21, 2026 due-time request S2-S4. New tickets use their creation timestamp plus 4, 24, 72 or 168 elapsed hours for urgent, high, normal or low. Environment overrides accept positive whole hours. Invalid values identify the setting at startup. A priority edit or a later process using other hours preserves an assigned due. HTTP writes reject client-provided due under the existing field-validation rule. Confirm with config and HTTP tests against the manual clock, followed by restart on the same file.

### R-2 Due-time visibility and filtering
Basis: S5 and S7. With exact DUE_TIMES=on, the API includes UTC ISO due on list, create, get, patch and transition. The human CLI can display due with the switch; raw output retains four columns. In the API, only overdue=true adds the overdue predicate, requiring open or in_progress and due strictly before now. Apply it before cursor pagination and in conjunction with the existing status/priority matching. Without the switch, omit due and ignore overdue, including for older clients using it as an unknown key. Confirm with deterministic HTTP and CLI tests.

### R-3 File preparation and rollback
Basis: S6-S8 and decision 8. On startup, assign deadlines only to tickets still missing them using their persisted created timestamp and priority. When there is a data file, finish an atomic version-1 save before listening. Invalid data or failed backfill prevents startup. A second startup preserves stored due, ids, audit, outbox, numbering and unrelated fields. Actual 1.4.0 reads this file and serves every ticket. After 1.4.0 rewrites the file, re-upgrade can recover previously assigned due from a pre-rollback backup, preserving new 1.4.0 activity and deriving due for tickets created during rollback. Confirm through old/new startup and writes on a disposable copy. Live production rollout requires the service owner.

### R-4 Existing service and test contract
Basis: S1, S9-S10 and CONTRIBUTING.md. Retain dependency-free Node startup using PORT, current CLI commands, existing lifecycle, outbox and audit behavior, and default API shapes. Preserve all existing tests and add node:test regressions under test/. Confirm with npm test and local process smoke.

## Non-functional requirements

Use the established single writer and whole-file replacement; backfill must preserve the previous complete file on error. Use standard library only, keep the existing simple terminal layout and fixed raw columns, and use the injected clock once per overdue listing. No new identity, network service, retention policy or graphical interface.

## Retired

None.
