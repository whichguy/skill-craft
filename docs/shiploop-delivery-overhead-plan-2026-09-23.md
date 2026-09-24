# ShipLoop delivery-overhead plan

Date: 2026-09-23. Branch: `feat/shiploop-inline-default`. ShipLoop 0.20.0.

This plan turns a real run's feedback, a packet trace, and a code-grounded
design review into ordered, independently shippable work. Phase 0 ships with
this branch; later phases need their own review and release.

## Problem

A one-module work item (one rules file, one test file) walked about eighteen
stages. Every producer parked the parent and started a fresh Improve run that
re-read the skill, started Until Loop and produced two trivial reviews: 7–17
minutes and 40–100 tool calls each, often re-running the same test at the same
commit. A cancelled subagent left no receipt, and the delivery target was never
reached. The strict parts worked: import refused a buried binding line, local
tests could not stand in for a signed-in consumer move, source `main` stayed
untouched, and one Improve pass found real rule bugs.

The generic causes, verified in code:

| Cause | Evidence |
|---|---|
| Every v3/v4 producer, including a justified "nothing to validate", gets a full two-review Improve child | `apply()` parks every non-reconcile result; import requires exactly two review refs and a streak ≥ 2 |
| A fixed 34-stage walk with no applicability | INNER has 18 stages per item regardless of size |
| Delegation per stage | INNER producers preferred a native fresh worker; every Improve child preferred Ask Agent's consumer-owned worker |
| Large, repetitive packets | Dry run: 68 packets, ~1.0 MB per single-item delivery; ~35% is paragraphs repeated in ≥ 10 packets. A real worktree run is ~102 packets, ~2.0–2.1 MB; a bound v4 plan Improve packet is ~41 KB |
| Fragile child handoff | The binding line is copied by hand; raw packets are saved by the host; nothing records a check result at a commit |

## Decisions (2026-09-23)

- **Inline is the default** for new protocol 3/4 runs; Ask-Agent delegation is
  a per-run opt-in (`--delegation ask-agent`, or `shiploop delegation --set`).
- **Clear once per work item.** The `select-work` packet is the only INNER
  context boundary. A model cannot clear its own context in Claude Code (packet
  text reset 0/2; host `/clear` 3/3), so a host without a callable reset pauses
  once per item instead of about eighteen times.
- **Inline implement uses no chain.** Reviewed steps run directly, in
  dependency order, in the execution checkout. Chains stay on the ask-agent route.
- **The toggle is a top-level `delegation` key**, not part of a future
  init-fixed `run_profile`: it can change during a run, and mutable run data
  stays top-level. Pins and features added later belong in `run_profile`.

## Phase 0: inline default (this branch)

Shipped:

- State key `delegation` (`inline` | `ask-agent`); a saved run without it keeps
  its recorded ask-agent route. `init` and `workspace start` take
  `--delegation`; `shiploop delegation --run-dir RUN --set VALUE` applies from the
  next issued action. The pending action and its Improve checkpoint keep their
  issued route (`delegation_hold`), so a worker, bound child or chain that may
  already own it is never re-routed; only terminal and pre-v3 runs refuse.
- Inline packets: `select-work` begins "Clear and then execute the prompt."
  with the once-per-item route; other INNER producers begin "Continue in this
  context and execute the prompt."; Improve packets run the selected Improve
  card's whole-skill subcall in the parent conversation without handing it to
  Ask Agent or a native worker and without `host-owner.md` (read-only scoped
  reviewers under Improve's review policy remain available); step-plan records
  ordered steps; implement executes them directly; `chain bind` refuses fresh
  bindings.
- Ask-agent packets keep their delegated wording; the packet-contract fixes
  below apply to both routes.
- `graph-dry-run --delegation`; `test/shiploop-delegation.test.py` (31 tests,
  including a bound-Improve sweep of every v3/v4 stage with a delegated-route
  positive control); route-aware Improve CLI tests with an ask-agent subclass.
- An adversarial review (six lenses, two verifiers each) confirmed 27 findings;
  all were fixed or are listed below.

Packet-contract fixes shipped with Phase 0: see [Packet fixes](#packet-fixes).

## Later phases

Each phase is independently shippable with its own tests. Savings are
estimates for the described run (baseline ≈ 5.3 h); they overlap and are
replaced by measurements once Phase 1 records action timing.

| Phase | Scope | Feedback item | Depends on | Estimated saving |
|---|---|---|---|---|
| 1 Foundations | Graph pin in a new `run_profile` for new runs; one `shiploop_candidate` identity module (fingerprint + manifest + diff); action timing events; pin the Improve card's logical path, realpath and digest at bind and auto-bind from it; compact packet layout slice 1; a strict-parts pin suite | 9, 6 | Phase 0 | 15–25 min |
| 2 Child durability | One Until Loop release (from the pinned 0.4.0-rc.2 source) adding `start --binding` (runtime writes and validates the binding line) and `--receipt` (runtime writes every packet atomically); `inspect_child` routing in `next`; `improve-retire` for lost or invalid children | 2, 8 | 1 | 30–50 min |
| 3 Confirm route | Script-observed gate: when the candidate is byte-identical to the last converged review and no check changed, close the step with one ShipLoop confirmation instead of an Improve child (select-work, test-refine, document, skill-assess, skill-validate); code-changing stages always get a full child | 1 | 1 | 20–35 min |
| 4 Check ledger and footprint testing | `shiploop check run/lookup` records command, commit, tree digest, exit code and counts in the run directory; reviews consult it instead of rerunning; the confirm gate extends to baseline, test-green, regression and static-checks. Stage guidance selects checks from the candidate's changed paths (the suites that execute or pin them); the full suite runs once at the initial baseline, integration-verify and system-test, not at every stage | 3, 1 | 3 | 25–35 min |
| 5 Compact item profile | Per-item profile chosen at step-plan with script-checked eligibility (one checkout, bounded files, no deploy): spec → failing test → implement → green → done; pinned per item; the long ladder stays for multi-branch and deploying work | 7 | 1 (graph pin) | 30–45 min |
| 6 Review integrity | Review provenance labels; the second of the two reviews comes from a second context on code-changing stages and receives the diff and command output, not the whole skill | 4 | 2, 4 | +5–12 min (buys back independence) |
| 7 Decisions ledger | Append-only run decisions (grants, declines, revocations with source and scope); producers and each Improve cycle re-read it; import refuses a stale decision view | 5 | 2, 3 | ≈ 0 min; correct deploy authority |
| 8 Cards and delegated track | Move stable text into cards loaded by stage; host-neutral native-worker contract (worker cwd = Child workspace, no extra worktree) for the ask-agent route | 6, 9 | 5 | 5–15 min |

Estimated total for the same scope: about 5.3 h → 1.7–1.9 h.

Rejected: a one-review Improve tier. It weakens the import contract and
duplicates the confirm route, which skips Improve only when the script observes
nothing reviewable changed. Improve keeps two consecutive trivial reviews.

## Packet fixes

From the packet trace (148 verified findings; every locator, template and
callback already resolves and parses, and no validator needs Ask-Agent
evidence).

Shipped with Phase 0 (both routes unless noted):

| Fix | Why |
|---|---|
| Binding line printed with an exact-line rule ("verbatim, exactly once, alone on its own line…; import matches the whole line"), plus a `Start inputs` line (`required_trivial_reviews 2`) | The run's import refusal came from a marker buried in a sentence; the runtime default is 0 reviews |
| v4 plan child freezes the rule to stop with `continuation_assessment cancelled` when an accepted premise breaks | A `blocked` stop cannot reconcile or import, leaving only halt |
| Restart route for a stopped child that cannot be reconciled (archive `packet.json` as `packet.stopped-<UTC>.json`, start a new child with the same binding line) and "pause, never report cancelled" | A user stop, now visible to the inline loop, otherwise dead-ends the run; pinned by a real-runtime stop → restart → import test |
| `final_result` shape stated; import refuses a plan/carry-forward `final_result` that drops the reviewed `work_items` | Omitting them silently kept the old queue |
| Allowed-outcomes line from the validator's rules; blocked/repeat still pass through Improve | Hosts guessed outcomes and resume timing |
| `ShipLoop skill card:` locator and a `Current item step-plan source` projection on later INNER stages | After a clear, the contract and the item's ordered steps were not reachable from the packet |
| Dedicated context-boundary pause command at inline `select-work`; halt labelled terminal and irreversible; shell-quoted `<why>` reasons | The manual-clear route needs a ready command; halt was easy to misuse |
| integrate states direct (inline) versus chain assembly | Inline runs have no chain finish commit |
| Inline Improve packets link the `improve-context.md` default-route section and read the card once per context | Avoids re-reading the whole skill at every checkpoint |

Follow-up pull requests:

1. **Format and contracts** — stale legacy references, OUTER test-plan
   projection, worktree return lifecycle after a verified return, template
   placeholders and receipt polish, first-line orientation block.
2. **Efficiency** (re-measure on real bound packets first; the review measured
   about 1.19 MB of packet text per inline work item, 88% repeated lines) — auto-bind Improve
   at `complete` (−333 K and −34 CLI calls per run), stage-gated COMMON and
   Improve guidance, worktree block only where it is used, collapsed recovery
   prose, compact Backchain native text. Target: ~2.0 MB → ~1.2–1.4 MB per item.
3. **Ask-agent chain route** — rejected-then-retried step deadlock, worker
   handoff template, dispatcher control fields leaking through bridge responses,
   typed inputs for every chain action.

## Follow-up: skill-scoped changes and tests

After this fix lands, scope both the change sets and their verification per skill.

- **Change sets.** Ship each phase as a pull request that touches one skill package
  plus its own tests and generated plugin copy: ShipLoop-only phases (1, 3, 4, 5, 7),
  one Improve/Until Loop release (Phase 2, with Phase 6's review fields batched in),
  and an Ask-Agent/chain-route PR (Phase 8 and the chain packet fixes). Installed
  skills are symlinks to canonical `main`, so every Improve or Until Loop publish
  changes the package under running children; batching those edits limits that.
- **Tests.** The suite catalog has 133 hermetic suites (102 ShipLoop), and
  `test/ci_policy.py plan` chooses only smoke (documentation-only) or full, so any
  code change in any skill runs all of them. Add an ownership map to
  `test/suite_catalog.py` (each suite's owning skill and the skills it consumes) and
  a changed-path selector: a change under `skills/<leaf>/` runs that skill's suites
  plus declared consumer suites (Ask-Agent → ShipLoop composition; Improve → ShipLoop
  Improve boundaries); shared paths (`install.sh`, `scripts/`, test runners, the
  catalog) still select full. Local verification uses the same selector; CI keeps a
  full run on `main`.

## Invariants that no phase may weaken

- Import refuses a binding line that is not exactly its own line.
- Exactly two distinct review references and `required_trivial_reviews ≥ 2`.
- Local checks never satisfy a required consumer, identity or deployed observation.
- Workspace return leaves the source branch untouched and waits for the final
  handoff Improve child.
- test-author, test-red and implement always get a full Improve child.
- Saved runs never silently migrate; new behaviour applies to new runs or an
  explicit, recorded opt-in.

## Open owner decisions

| # | Question | Recommended default |
|---|---|---|
| 1 | Add a second inline context boundary at the first OUTER stage (`system-test-author`)? PRELUDE and OUTER otherwise run in one context. | Yes, same once-per-boundary route |
| 2 | Auto-bind Improve at `complete` (efficiency item: −333 K packet text and −34 CLI calls per run)? A switch already applies from the next action, so binding earlier does not narrow it. | Yes |
| 3 | Pin the Improve package by digest or by copy under symlinked installs? | Digest in Phase 1, copy for new runs in Phase 2 |
| 4 | Confirm-route defaults | On for new runs; `blocked`/`repeat` stay full; a first-ever passing check is not a transition |
| 5 | Compact profile | Automatic eligibility for new runs; explicit upgrade only |
