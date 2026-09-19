# Incorporating implementation chains into ShipLoop

## Decision and bounds

**Decision: pilot the integrated candidate; defer merge into the current
Ask-Agent 0.4 workflow.** The complete candidate is implemented on the ShipLoop
0.17.0 integration branch and has a completed native pilot with explicitly
selected Ask-Agent 0.3.1. The working Ask-Agent 0.4 contract requires a different
handoff adapter; this is a concrete incorporation prerequisite, not a request to
silently select the older package. Keep the contribution reviewable in
[skill-craft PR 8](https://github.com/whichguy/skill-craft/pull/8) and its
[dispatcher prerequisite PR 2](https://github.com/whichguy/backchain/pull/2).

Retain normal navigator ownership and the existing mandatory Improve handoffs.
A chain stays inside one current `implement` action; it does not parallelize the
full SDLC or launch model processes from ShipLoop. Neither draft PR establishes
installation, marketplace activation or release of ShipLoop 0.17.0.

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
| C: current Ask-Agent compatibility | S,D | selected 0.4 contract and explicit task-baseline semantics | parent import adapter, adversarial handoff checks and a fresh native 0.4 pilot |
| R: incorporation | H,N,D,C | reviewed candidate and verified dependency | scoped commits and integration receipts; documentation distinguishes source, install and live-host coverage |

S and D may proceed independently. H and N may run concurrently after their
dependencies are ready. S and D are implemented; the 0.3.1-scoped N passed. C is
planned below and remains unimplemented. A failed check remains a prerequisite
to R.

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

The production-only dispatcher port is `0a11b1a`: all five package files match
the selected native-pilot package. Its required host gate reports `PASS_CLEAN`,
167 passed / 0 failed, run `20260919T033133Z-80dbdd`. Its stderr-volume warning
was inspected: installation help, intentional negative controls and ordinary
runner output explain the signal. The `Codex/Hermes: skipped` text is installer
help about agent-card destinations, not a skipped test. The harness also retained
an existing temporary-fixture cleanup note; it found no product-file changes.

Full ShipLoop qualification results are recorded after the remaining shards
finish. The first shard-3 attempt failed a brittle discovery prose assertion;
`19ee7ad` changes it to check the two required cues independently. All 27 discovery
tests passed on the repair, and the entire affected shard is rerun. The original
failure remains in its log; it is not counted as a passing run.

### Completed native pilot

The [retained evidence summary](shiploop-chain-native-evidence-2026-09-18.json)
records exact workspaces, commits, verification digests and final state. Raw local
evidence is retained at `/private/tmp/shiploop-chain-017-20260918`; these paths are
local reproduction evidence, not downloadable files in the repository.

| Task | Native result and parent acceptance | Native type | Role substitution |
| --- | --- | --- | --- |
| A: implement addition | SUCCEEDED; independently accepted `6c039f7` | default | none |
| B: implement normalization | SUCCEEDED; independently accepted `0ad03a7` | default | none |
| J: join exact A/B commits | SUCCEEDED; independently accepted `c1ebd17` | default | none |

A and B were launched through native fresh contexts before either was collected;
the saved pending view showed both running and J waiting on both. Native final
notifications returned to the parent; no native collection call was rejected,
and no native worker remains pending. The immutable external oracle and parent
Git inspection checked actual output, contribution scope, clean worktrees and
exact supplier ancestry. J's combined check produced `result 5` from addition
and normalization. Guarded `finish` then fast-forwarded only the initiating
feature worktree to `c1ebd17`; primary stayed at `4ddd07d`. All three worker
checkouts and the target are non-nested siblings under external `.work-trees`.

The final state has accepted A/B/J, no pending steps and no active attempts.
All 24 history events captured before acceptance remain unchanged, as a prefix
of the final 46 events. Worker worktrees and result files remain retained for
reproduction; the parent owns later cleanup after the evidence is no longer
needed. This fixture return is complete; the product PRs remain unmerged.

The first parent start calls accidentally overlapped while their shell commands
were still running. The manual driver's command-log slot collided after durable
start. No native B worker had been launched; its uncertain attempt was preserved,
explicitly retried after non-launch confirmation, and replaced by the accepted B
attempt above. The original evidence and retried state remain. The pilot README
now requires waiting for each parent command to finish before the next command;
only native workers run concurrently. This recovery is not a claim that the
single-parent pilot driver supports concurrent callers.

Pilot selection: ShipLoop runtime `4471993`, Ask-Agent 0.3.1 card SHA-256
`c8db5bd2cff132a38ffbac8e2604b6d779c4947c7bb04c1caeda0cbb53da80c1`,
Git reference SHA-256
`127e0fad5af53067360e3429fd319870fec4f08f09a2f697bc6ccd4f533321fd`.
Navigation and initial Improve evidence in this fixture were synthetic. The
pilot exercised real workers, Git and verification after that prepared entry.

### Ask-Agent 0.4 adapter plan

The working 0.4 card inspected during this assessment has SHA-256
`a1c08aa2a966b51103793e8432a0ad184f31fcdb088ec3c4186c812571f52bb5`;
its Git reference has SHA-256
`557880e53a0e69a2a8ce599f368bedeacf42d95158ebc6593e03c7e35908c9e7`.
These working changes belong to a separate ongoing Ask-Agent contribution and
were not copied or published by this port.

That contract requires inline native launch instructions, a verified caller-state
baseline and all worker result/scratch files inside the worker checkout. Current
dispatcher packets tell workers to publish external result/envelope files, while
ShipLoop's contribution gate requires a clean worker HEAD. Merely redirecting
those files into the checkout would fail the clean-worktree gate. Selecting and
hashing 0.4 alone does not adapt this protocol; the current helper does not reject
that semantic incompatibility at bind time. Do not use this draft with 0.4 yet.

| Step | Depends on | Required result |
| --- | --- | --- |
| C1: baseline and handoff contract | S,D | Explicitly reconcile the task-pinned base with Ask-Agent's caller-state rule: roots use the frozen clean target; dependent bases include accepted suppliers. Record exact base, target, supplier commits and ownership. |
| C2: inline packet and parent import | C1 | Parent places objective, relevant inputs, permitted actions, worktree identity and output contract directly in the native launch prompt; no generated prompt file. Worker returns a declared temporary handoff inside its own worktree. |
| C3: verification and cleanup regressions | C2 | Parent safely preserves the exact handoff into a digest-bound external import, publishes the existing report and removes only declared owned temporary files before clean contribution inspection. |
| C4: native 0.4 qualification | C2,C3 | Fresh A/B fan-out and dependency join with the selected 0.4 package; root and dependent baseline checks; independent verification; guarded return. |

Keep the existing report/observe/settle APIs and accepted-state authority. The
worker deliverable stays distinct from the parent-authored import artifact and
immutable control receipt. Do not add shared ignore configuration, commit scratch
files, introduce another scheduler, or let workers edit parent state. Preserve
returned files before cleanup; an unknown file, symlink, path escape or digest
mismatch leaves the attempt unresolved and its files intact.

Focused acceptance cases: exact root and dependent baselines; inline launch
assignment; worker-local handoff; no worker publication outside its checkout;
successful import and exact-path cleanup; import replay without duplicate state
transitions; interruption before/after preservation and before report; refusal
without deletion for unknown files, links, wrong attempt or bad digests; frozen
package drift; native 0.3 compatibility and serial no-agent regressions. Run
chain/Git tests and generated-package parity before the fresh 0.4 pilot. Only
then reconsider R, publish the prerequisite first and activate the selected
packages separately from source merge.

No claim of host restart recovery, exactly-once external effects, manual Git
writer exclusion, full live SDLC completion or cross-host qualification follows
from the bounded chain tests. Review judgments in hermetic Improve tests are
synthetic; they verify callback/gate mechanics and evidence transfer.
