# Incorporating implementation chains into ShipLoop

## Decision and bounds

Incorporate the complete chain candidate as an explicitly selected capability
in ShipLoop 0.17.0. Retain normal navigator ownership and the existing mandatory
Improve handoffs. A chain stays inside one current `implement` action; it does
not parallelize the full SDLC or launch model processes from ShipLoop.

The source integration starts at published skill-craft `1e31cd8`, carries only
the chain contribution from `c444c02` and planning-review increment `76facd5`,
and preserves current coding/platform guidance, Ask-Agent 0.3.1 and smoke/full
test selection. The canonical checkout's unrelated working changes are excluded.
Authoring and verification use external sibling worktrees.

Plan Dispatcher 0.1.1 is the serial-mode prerequisite. Port its production
executor/receipt changes and tests onto published Backchain `6ce94ef`; keep the
ledger-derived-state experiment outside that contribution. Callers select the
complete dispatcher package explicitly. Installing or discovering a card does
not establish native execution, and ShipLoop does not install dependencies.

## Implementation and qualification plan

| Step | Dependencies | Ready condition | Completion evidence |
| --- | --- | --- | --- |
| S: reconcile ShipLoop | none | clean checkout of published source | chain commands plus planning gate; current guidance and no-model-launch boundary retained; generated packages match |
| D: port dispatcher | none | clean checkout of published Backchain | production serial executor and native compatibility tests; required repository gate passes |
| H: hermetic qualification | S | frozen integrated candidate | focused chain/planning checks, core group and all current ShipLoop suites pass; checkout remains clean |
| N: native qualification | S,D | exact selected cards and disposable Git fixture | native fan-out, collection, independent acceptance, join and return using sibling worktrees; package identities retained |
| R: incorporation | H,N,D | reviewed candidate and verified dependency | scoped commits and integration receipts; documentation distinguishes source, install and live-host coverage |

S and D may proceed independently. H and N may run concurrently after their
dependencies are ready. A failed check remains a prerequisite to R.

## Preserved contracts

- Create initial steps and graph before their actual Improve review. Material
  repairs reset its two-review streak. New or revised graphs need review before
  binding; the host verifies semantic review and the helper freezes structure.
- Parallel mode uses Ask-Agent's native fresh contexts. Serial mode uses one
  main-context executor and no native handle. Both modes use the same accepted
  transition, dependency graph and guarded return to the initiating checkout.
- Every worker checkout is a sibling under an external `.work-trees` container.
  The initiating checkout may itself be a worktree. It is the return target;
  the repository's primary checkout is not an implicit destination.
- Reports are evidence, not acceptance. Verify stopped execution, exact worker
  results and the combined candidate before accepting or returning them.
- `history` is append-only audit history; `pending` derives current dispatcher
  state. Neither mutates completion or creates another scheduler. The separate
  event-replay prototype does not become production state authority here.

## Evidence and remaining bounds

The original candidate's 33 chain and 9 Git tests passed again before this port.
Published-source navigator baseline passed 22 tests. A protocol run overlapped
conflict resolution and is invalid as baseline evidence; its clean, separate
published-source rerun passed all 35 tests. Historical 93-suite and native-pilot
results remain scoped to their original candidate. Current upstream removed
three host-controller suites: this integration registers 90 ShipLoop suites.

Final integrated checks and native receipts will be recorded here after they run.
No claim of host restart recovery, exactly-once external effects, manual Git
writer exclusion, full live SDLC completion or cross-host qualification follows
from the bounded chain tests. Review judgments in hermetic Improve tests are
synthetic; they verify callback/gate mechanics and evidence transfer.
