# Compact completion-driven dispatch

## Outcome

At initialization and after every event, process the exact returned attempt,
accept only verified completion, and fill all safely available execution slots.
A slow sibling never becomes a wave barrier. New invocations select current
published source instead of historical release worktrees.

## Smallest implementation

1. Reuse the existing claim/start/report/verify/settle loop and its durable state.
   Order eligible starts and claims before potentially waiting observations.
   Keep parent recovery, resource conflicts, planning prerequisites and capacity
   reservations authoritative. Serial mode retains capacity one.
2. Make branch identity visible without a new event schema: retain Dispatcher
   report/receipt envelopes and detailed settlement attempt records; add the
   settlement's authoritative `step`. Add `step` beside every ShipLoop navigation
   and callback-result `attempt`, including cleanup and recovery. Derive identities from durable
   records; never trust arrival order or a caller-supplied branch label.
3. Keep one scheduler and no additional queue, ledger, polling service or mutable
   completion cache. `next` derives the frontier from accepted dependencies;
   existing exact continuations, owner fences, receipts and append-only history
   support cold recovery, duplicate delivery and out-of-order results.
4. Merge into current remote main, verify the combined code, push, then activate
   from a clean rolling main checkout with the existing installers. Preserve
   unrelated dirty checkouts. Refresh copied installs when main is updated.
   Recorded identities/hashes inside an active run are recovery evidence, not
   installation release pins, and remain enforced.

   Local source links follow the commit present in the rolling main checkout.
   A later remote publication still requires `git pull --ff-only` and the
   installer to refresh copied packages; no background updater is implied.

## Alternatives rejected

A new scheduler or shared cross-repository library would duplicate durable state
and weaken portable packages. Renaming the existing settlement `attempt` object
to a scalar would break consumers for no scheduling benefit. A new required
capability gate is unnecessary for additive labels derived by each package.
Future capacity and host adapters can use the existing claim/start boundary;
unknown future requirements do not justify new persistent machinery today.

## Verification and delivery

Baseline: existing Dispatcher CLI 24 groups pass before the additive identity
change; the earlier implementation audit records the original lifecycle baseline.
Verify copied Dispatcher CLI accepted/rejected/replay/cascade identities; ShipLoop
navigation identities across parallel, serial, recovery and cleanup paths; eager
refill and join gating; current Dispatcher cross-package real-Git integration;
bounded packets and generated package parity. Run the required Backchain hygiene
gate and independent review. Native workers in these tests are deterministic
fixtures, not a claim of live model compliance.

Commit only task files from isolated branches, integrate current main without
discarding concurrent work, push both repositories, and read back remote SHAs and
installed paths. Installation freshness is distinct from durable run identity.

## Latest-source activation

The local delivery uses `/Users/dadleet/src/skill-craft-latest`, a clean clone
whose `main` tracks `origin/main`, and `/Users/dadleet/src/backchain` on `main`.
After publication, fast-forward those checkouts and run the existing installers:

```sh
git -C /Users/dadleet/src/skill-craft-latest pull --ff-only
git -C /Users/dadleet/src/backchain pull --ff-only
bash /Users/dadleet/src/skill-craft-latest/install.sh --skill shiploop --all --relink
bash /Users/dadleet/src/skill-craft-latest/install.sh --skill improve --all --relink
bash /Users/dadleet/src/skill-craft-latest/install.sh --skill ask-agent --all --relink
bash /Users/dadleet/src/backchain/install.sh --skill plan-dispatcher --all --relink
bash /Users/dadleet/src/skill-craft-latest/install.sh --from /Users/dadleet/src/backchain/skills/plan-dispatcher --cursor-only --relink
```

ShipLoop, Improve and Ask-Agent use source links on Claude, Grok, Codex and
Cursor, and refreshed managed copies on Hermes. Dispatcher uses its supported
source links. Historical release worktrees are no longer selected by these
leaf installs. Marketplace release catalogs and active-run evidence hashes are
separate from this local source track and are not silently rewritten.

Compatibility boundary: published Ask-Agent remains 0.3.1. The current ShipLoop
per-step adapter requires 0.4.x and its declared workspace/ownership contract;
the 0.4 test fixture is not a production install. The user's separate Ask-Agent
workspace task is developing 0.5.0. Publishing these dispatcher changes does
not qualify that unfinished package or enable a live per-step chain without a
compatible selected adapter. Keep the explicit preflight refusal.

## Verified result

Dispatcher commit `38c6b44` passed the required `make test-dispatcher` hygiene
gate: `PASS_CLEAN`, all 12 dispatcher suites, 103 harness-parsed named checks,
including 24 copied-package CLI groups. It was fast-forwarded and pushed to main.

ShipLoop was merged with main `6037e01`, retaining the newer baseline and service
discovery guidance. All 27 lifecycle cases passed, including out-of-order
completion/refill, joins, serial execution, owner fencing, interrupted imports,
integration and cleanup recovery, and caller-supplied step rejection without
mutation. A further real-Git fan-out/join integration passed against Dispatcher
`38c6b44`. Guidance, packet-bound, prompt-integrity and reference-routing suites
passed 55 tests. Total for this final ShipLoop check: 83 tests. Generated views
and the ShipLoop package payload check passed; independent review found no
remaining correctness issue in the change. No live native model was tested.
