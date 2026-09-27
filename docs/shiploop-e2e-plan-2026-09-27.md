# ShipLoop plan after E2E runs 1-8b (2026-09-27, revision 4)

Execute: ask

Supersedes the open items of `shiploop-e2e-verification-plan-2026-09-26.md`.
Governed by `test/shiploop_e2e/SPEC.md`: ShipLoop is a general SDLC execution
engine (Purpose). Every item below went through Change admission in order:
adversarial evaluation first (each consequence mitigated, accepted or the
change rejected), then anchor, non-regression and evidence. E2E work runs
depth-first in focused suites, confirmed by a breadth suite.

## Audit behind this plan

- The 1.7.0 lifecycle rule is phrased in game/technology terms.
- Tool knowledge sits in script logic (per-runner test-count parsers, the
  `npm run lint` / `make lint` fallback).
- The harness core recognises test runs by tool name and copies the
  requirement-ID pattern.
- Four commit code paths (three identity copies, one without a fallback, none
  screening for secrets); three hand-built loop contracts; Improve packets
  carry text for steps the scripts now perform.
- All eight live runs probed one style (browser UI over an HTTP service).

## Suites

| Suite | Style | Cases | Use |
|---|---|---|---|
| `web-service` (focused) | browser UI over an HTTP service; follow-on in the same repository | battleship, battleship-scoring | depth loop for P3-P5; baselines from runs 7, 8b |
| `cli-files` (focused) | command-line tool over input files, report output, no server | new case | baseline in P6 |
| `stateful-service` (focused) | service with persistent state and concurrent writers | new case | baseline in P6 |
| `breadth` | one case per style | battleship, cli case, stateful case | generality gate before a release is called good |

## Items

### P1 Harness suites (harness only)
Change: `cases.json` gains `style`; suites named per style plus `breadth`;
`run.py --suite <name>` runs a suite's cases in order, chaining follow-on cases
from their predecessor; each result appends a summary row to a committed
per-case baseline file keyed by case and ShipLoop version.

Adversarial evaluation:
- *Baselines drift silently when ShipLoop changes* -> **mitigated**: rows are
  keyed by ShipLoop version; comparisons state both versions.
- *A committed baseline file conflicts with concurrent sessions* ->
  **mitigated**: rows only append, one line per run, written in the same
  learnings commit (already one commit per run).
- *A follow-on runs on a failed predecessor and blames ShipLoop* ->
  **mitigated**: the suite skips the follow-on with the predecessor's result
  as the reason; tested.
- *Suites encourage skipping breadth* -> **mitigated**: SPEC promotion rule;
  a release is not called good without a breadth row per style.
- *`--case` behaviour changes* -> **mitigated**: unchanged path, self-test pins it.

Anchor: SPEC "E2E suites"; eight runs of one style cannot show S-13.
Non-regression: no ShipLoop code touched; result.json fields keep meaning.
Evidence: self-test (order, chaining, skip on failed predecessor, baseline
append); a fake-host `--suite web-service` run.

### P2 Case-agnostic harness core and a glue metric (harness only)
Change: count test runs from ShipLoop's verify records; reuse ShipLoop's
requirement-ID pattern; add `model_glue` (shell writes into ShipLoop-owned
paths, hand-built loop JSON, commit/rename/mkdir commands there).

Adversarial evaluation:
- *`test_runs` changes meaning and breaks comparison with runs 6-8b* ->
  **mitigated**: recompute the old runs that still exist and record both
  definitions; where an old run is gone, the comparison says so.
- *Glue metric counts product work (tests that write files)* -> **mitigated**:
  only ShipLoop-owned paths and ShipLoop mechanics count; the matching commands
  are listed for review.
- *Glue metric misses glue done differently (Python writing a receipt)* ->
  **accepted**: the metric is a signal, not proof; the review question for
  S-4/S-5 stays.
- *Importing ShipLoop's pattern couples the harness to engine internals* ->
  **accepted**: S-12 prefers one definition; a rename fails the self-test
  loudly.

Anchor: SPEC harness rule (case-agnostic core); S-4, S-5 measurable; S-12.
Non-regression: metric names kept; only `test_runs`' source changes, recorded.
Evidence: self-test on synthetic events; recomputed old runs.

### P3 One commit path with a secret screen (ShipLoop)
Change: one `commit_paths` helper for the knowledge-home commit, the integrate
commit, `improve-commit` and workspace bootstrap; skips and names text files
the privacy screen flags; configured identity, else the workspace identity.

Adversarial evaluation:
- *A skipped file is one the product needs; the stage passes, the returned
  product is broken* -> **mitigated**: skipped paths are printed at the
  commit, recorded in the run, and remain uncommitted, so the return plan
  lists them and the harness `committed` verdict fails; tested.
- *False positives on fixture tokens* -> **mitigated**: skip that file only,
  never fail the transition; the model sanitises and recommits.
- *False negatives (a secret the screen misses)* -> **accepted**: defence in
  depth with `.gitignore` and the existing knowledge screen; the screen is not
  a guarantee (stated in the handoff).
- *Scanning large/binary files is slow* -> **mitigated**: text files only,
  size-capped.
- *The knowledge commit's behaviour changes* -> **mitigated**: it only gains
  the identity fallback it lacked (a failure fixed); success path identical,
  tested.
- *Fallback author "ShipLoop Workspace" in user history* -> **accepted**: only
  when no identity is configured (Git refuses otherwise); stated in handoff.
- *Bootstrap's empty commit goes through a helper built for paths* ->
  **mitigated**: explicit `allow_empty` path, tested.

Anchor: S-12 (four copies), S-11 (commits never carry secrets to the user's
branch), S-5. Non-regression: identical staged paths and messages for clean
files. Evidence: per-caller tests; token file skipped and named; `web-service`
focused suite keeps `committed` and glue 0.

### P4 One loop-contract builder (ShipLoop)
Change: test loop, quality loop and Improve contracts come from one module;
the Improve exit condition includes the stage's own `done_when`. Start
mechanisms unchanged (`loop-start` verb deferred: zero start failures in runs
7/8b).

Adversarial evaluation:
- *Test/quality contracts change subtly* -> **mitigated**: tests assert they
  are byte-identical to today's.
- *Longer exit text is reprinted by the Until Loop on every pass, growing
  context (S-7)* -> **mitigated**: done_when bullets are short; measure the
  contract size delta and keep it under ~500 characters; if larger, reference
  the packet's done-when section instead.
- *Stricter exit criteria add review passes and cost* -> **accepted**: S-10
  asks for checkable, stage-specific exits; cost change attributed in the
  suite comparison.
- *A done_when item is not checkable inside a review loop (it needs a later
  stage)* -> **mitigated**: include only the stage's own done_when (they are
  written for that stage); review loops confirm by recorded checks.
- *Saved runs' contracts* -> **mitigated**: frozen on disk; only new contracts
  use the builder.

Anchor: S-12; S-10. Non-regression: test/quality byte identity; Improve keeps
every field. Evidence: contract tests; `web-service` focused suite turns/cost
vs runs 7/8b.

### P5 Improve packets state each obligation once (ShipLoop)
Change: remove text describing steps the scripts now perform (hand-freezing
context fields, resource lists, runtime start syntax, rename steps); keep what
the model must still do, once each.

Adversarial evaluation:
- *Conflicts with the owner's "never trim guidance" rule* -> **mitigated**:
  only superseded text is removed, each removal citing the script function
  that now performs that step; no remaining guidance is shortened.
- *An obligation disappears and a model skips it after context loss (S-6)* ->
  **mitigated**: an obligation list is asserted by a packet-contract test.
- *Models trained on earlier packets in the same run* -> **accepted**: one
  supported version; new runs only.
- *Delegated (ask-agent) route still needs the manual steps* -> **mitigated**:
  inline route only; delegated packets unchanged, tested.

Anchor: S-7, S-6. Non-regression: obligation list; stage packets untouched.
Evidence: packet-contract, delegation, v3-guidance suites; packet sizes;
`web-service` focused suite.

### P6 Baselines for the new styles (harness + runs)
Change: write `cli-files` and `stateful-service` cases (product checks only in
`cases.json`), run each focused suite once on the current release.

Adversarial evaluation:
- *Cases need tools the machine lacks (a database, a package manager)* ->
  **mitigated**: dependency-free prompts; stdlib only; a different language
  from the web case to vary the stack.
- *Concurrency checks are flaky and blame ShipLoop* -> **mitigated**:
  deterministic invariants (N parallel writes -> exactly N records), no
  timing assertions; a flaky check is a harness defect.
- *A case fails for product reasons* -> **accepted**: product defects are
  evidence only; review against the spec.
- *Cost of two more runs (~$25-35 each)* -> **accepted**: required for S-13.

Anchor: SPEC "E2E suites"; Purpose. Non-regression: new cases only.
Evidence: two runs with baseline rows.

### P7 Release and breadth gate
Change: one release for P3-P5 after the full hermetic tier; host updates;
`web-service` focused suite until it passes; then `breadth`.

Adversarial evaluation:
- *release.py ships another session's pending notes* -> **mitigated**: list
  `changes/` before release; only intended notes, otherwise coordinate.
- *A verb or text change breaks pinned adapters/fixtures (as in 1.5.0)* ->
  **mitigated**: full tier locally before release.
- *Breadth failure after release* -> **mitigated**: the release is not called
  good; fix in the failing style's focused suite, then re-run breadth.

Acceptance: every verdict passes in every style; 0 ShipLoop command failures;
glue 0 for mechanical steps; per-case cost no worse than baseline, or the
increase attributed to a stated intended change.

### P8 Engine neutrality (ShipLoop prompts/cards; owner review first)
Change: restate the 1.7.0 lifecycle rule in SDLC terms with at most one
labelled example; vary one-domain illustrations.

Adversarial evaluation:
- *The rubric-tuned wording loses measured safeguards* -> **mitigated**:
  owner review; rerun the architecture-rubric scenarios; no regression allowed.
- *Neutral wording is vaguer and models decide worse* -> **mitigated**: the
  rubric rerun and breadth suite measure it; revert if worse.
- *Test churn from pinned wording* -> **mitigated**: update pins in the same
  commit; full tier.

Anchor: S-8, S-13, Purpose. Evidence: rubric rerun; breadth suite.

### Later, each through Change admission when planned
- Tool knowledge into one catalog (S-8), behaviour-preserving.
- Grok refusal probe; any outcome host-neutral (S-8, S-13).
- Until Loop short output upstream (S-7); owner decision.

### Rejected after evaluation
- Skipping skill stages: 2-6 turns; a new rule costs more than it saves.
- Trimming planning: planning size is fine in files (S-7).
- `--always-approve`: tests an unrealistic host; unrestricted shell.
- Printing whole packets: contradicts S-7.
- A Battleship-specific hidden-state check: product-specific (S-13);
  replaced by a generic review question and case-level checks only where a
  request has hidden information.
- A `loop-start` verb now: no evidence of a start problem; churn and adapter
  risk without an anchor in run evidence.

## Order

P1 -> P2 -> P6 -> P3 -> P4 -> P5 (each iterated on the `web-service` focused
suite) -> P7 -> P8 -> later items.
