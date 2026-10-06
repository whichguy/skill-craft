# ShipLoop planning review plan, 2026-10-05

Status: decided; I3, I0, I1 and I2 are built and landed (table under "Increments"). Owner request (2026-10-05): "yes,
do the planning review change", with a ceiling of 30 minutes for the planning window. The default flip (I5) is the
owner's later decision and is not part of this work. A review of the landed commits changed three statements of this
record, each marked where it stands and dated 2026-10-05: a `none` run must name its Improve card at its start (F1,
A2-10), the test-author probe reads a unittest module that cannot import as no test run (E1), and the Sonnet catch is
a related class, not the same defect (F5).

This is the design of a read-only investigation (four investigators, a draft design, two attacks, a revision), kept whole in `docs/experiments/shiploop-planning-review-20261005/` (`design-final.json`, the
draft it replaced, four reports, two attacks, the Sonnet commit and the E6b excerpt, `probe_judge.py` and `passes.py`
with their output). Labels: [M] was read or run, [I] is inferred, "unknown" was not measured. The sections below are
that design as the owner resolved it; where the code showed a statement of the design wrong, the section says so.

## Owner resolutions (2026-10-05)

| Decision | Resolution |
|---|---|
| D1 default and gate | The option is `--planning-review stage|none`, state key `planning_review`. The default stays `stage` **in code** until the owner flips it. The flip (I5) is its own later, dated SPEC commit plus one constant and is not part of this work. |
| D2 a review-preserving value | **Not built.** The merged `once` value and the `plan` value are out of scope; `PLANNING_REVIEW_MODES` grows only by a value that has its behaviour. |
| D3 the carve-out text | Accepted as the basis. It is the second S-10 carve-out in the SPEC (dated 2026-10-05). |
| D4 per-item merge (step-plan and test-spec reviewed once after test-spec) | **Rejected.** |
| D5 the test-author probe first | **Yes.** Landed as I3 before any option code. |
| D6 what the 30-minute ceiling counts | The window the journal defines: intake to the first `test-spec` accept. |
| D7 E2E recording of the mode | The exporter and baseline-row recording of `planning_review` is a **handoff to the Run Review session**, not edited here. |
| D8 release timing | The owner is told before any release. |
| D9 the end-of-work review carrying the planning documents | **Not in this change** (it touches another loop; cost unmeasured). Revisit after M2. |
| D10 lint-style document checks (L11), a cheaper revise path (L17), `--backchain-passes` defaults | **Out of scope.** |

## Summary

What changes. One run option, `--planning-review stage|none`, recorded in `state.md` for the whole run like
`backchain_passes`; a saved run without the key is refused with the fresh-run hint and nothing is migrated. `stage` is
today's behaviour and its packets stay byte-identical. `none` starts no Improve review after `spec`, `test-strategy`,
`plan`, `step-plan` or `test-spec`; the `system-test-author`, `release-plan` and last `carry-forward` reviews stay.

Minutes. Review is 54% (Luna xhigh) and 58% (Grok medium) of the planning window [M]. On Grok medium `none` leaves 26.8
to 30.3 of 72.7 minutes if no work moves into authoring, and about 40 to 44 if the first-pass review work does (the
five first passes took 13.3 minutes; the share that moves is unmeasured). On Luna xhigh it leaves 172.5 of 375.9 at
best; no review change reaches 30 there.

Quality. Nothing looks a second time at planning under `none`. Review caught five warranted fixes on Luna, 10 of 15
real plan-stage platform errors once the platform-claim bullet was added (Sonnet, condensed packets), and a missing
importable-server seam on a Sonnet battleship run, a related class [I] (Luna's defect was a focused suite importing a
file no step created, which cost 165.9 minutes of redo when review missed it). The rate at which defects escape without review is unknown.

What carries the exit criterion. ShipLoop's gates at `complete`; the test-author probe (I3); the later red, green and
regression gates. Whether the spec's criteria are complete and the oracles independent has **no script-run check in any
mode**. The SPEC carve-out says so. It strains the owner's rule that a step iterates until a stated check confirms each
exit criterion, and the enterprise-rigour rule.

Order and default. Probe (I3), SPEC carve-out (I0), option (I1), `none` (I2): all landed. The default stays `stage`.

## The two modes

| | `stage` (today, the default in code) | `none` |
|---|---|---|
| Improve children at `spec`, `test-strategy`, `plan`, `step-plan`, `test-spec` | one each, started when the producer's result is accepted into `active_improve` | none; each result is accepted at `complete` and the graph advances, as at `intake` or `prepare` |
| Children after `system-test-author`, `release-plan`, and the last item's `carry-forward` | yes | yes |
| Children in a two-item run [M, scratch walk of the pure navigator] | 10, five in the planning window | 3, none in the planning window |
| Packets | byte-identical to the tree before the option (golden, both delegations) | the Improve line says no child starts; five duty sentences and the plan purpose and test-facility sentences are swapped, only for a stage that starts no child, from one table with an import-time guard |
| Plan child's `improve-reconcile` route and the plan-time experiments it hosts | kept | do not exist (printed only in the child packet, so nothing dangles); the plan's assumption list is still checked at `complete` by `_check_submitted_assumptions` |
| Knowledge home (S-11) | spec and test strategy are committed after their review | committed when each is accepted (`_knowledge_close` follows any accepted stage that changed the home) and no Improve child reviews them afterwards, so later runs inherit them unreviewed |
| First Improve child, and the first loading of the Improve card | the `spec` child binds the card | the last item's `carry-forward` is the first child, but the first item's quality and test loops read the recorded card, so `init` and `workspace start` refuse `none` without `--improve-skill` and resolve the card there (**changed 2026-10-05, review finding F1**: the design called a missing card a recoverable stall at the end of the run, which was wrong: a run started without the card blocks at its first `static-checks`, and no verb binds a card without an active child) |
| `--backchain-passes none` together with `--planning-review none` | n/a | no model-run second look at the plan graph: the highest-risk combination; documented, not refused (KISS, as `--backchain-passes none` itself was not) |

Measured cost of `stage` (the control and the revert target): Grok medium (grok-4.7, 1.21.0): window 72.7 minutes,
Improve children 42.4 on the children clock (58%; spec 15.2, test-strategy 13.1, plan 5.2, step-plan 6.4, test-spec
2.5; 26 passes) and 45.88 on the exporter clock. Luna xhigh: window 375.9, children 203.4 (54%; spec 44.5,
test-strategy 61.1, plan 56.9, step-plan 26.7, test-spec 14.2; 22 passes). One run each; stage times vary about 2x
between runs of the same model. Sonnet 5.5: its five battleship planning children took 13 passes in 125 seconds, so
`none` would save about 2 of a 4.7 minute window there.

Adjustment from the design (the code showed a statement imprecise): the design said the spec and test strategy are
committed "before any review". `_knowledge_close` runs after any accepted stage; in `stage` the stage is accepted at
`improve-complete`, so the commit follows the review, and in `none` it follows `complete` with no review at all. The
SPEC and this record say that.

## What carries each exit criterion

"Script-run" means a check ShipLoop runs and records (S-9). "Semantic" means the condition is about meaning and no
script checks it in any mode. Under `stage`, a semantic condition is carried by the Improve child's review, a second
model look; the child's own S-9 evidence is loop mechanics the script counts (passes, the review streak, a Git
cross-check, the commit rule), never a check of the review's content. Under `none` that second look is gone and the
condition rests on the producer's own confirmation of the Done-when text the packet prints in every mode, on the
later gates, and on the end-of-work review.

| Stage | Done-when condition | Script-run carrier, both modes | `stage` adds | `none` rests on |
|---|---|---|---|---|
| spec | every request outcome maps to an acceptance criterion; each criterion verifiable; non-functional requirements assessed | none for meaning; requirement-ID retention (an earlier ID may not be dropped) and the credential screen at `complete` (`knowledge_home.check`) | the review | producer confirmation, later gates, end review |
| spec | unaffected existing requirements preserved | requirement-ID retention (IDs, not their meaning) | the review | the same script check |
| test-strategy | every criterion maps to a check, its surface and its due stage; planned checks marked planned | none for meaning; the knowledge home's required files and credential screen | the review | producer confirmation; later gates |
| test-strategy | the harness is selected or revalidated | later: the probe at `test-author` (the focused command must run a test), then ShipLoop's own runs at `test-red`, `test-green` and `regression` | the review | the same later gates |
| plan | every criterion is owned by a work item; items in dependency order | queue shape only at `complete` (non-empty, unique IDs) and the record-only `backchain-check` where the Backchain loop runs; no check of ownership or order | the review | producer confirmation; later gates |
| plan | the assumption list is complete | `_check_submitted_assumptions`: each open assumption names a work item in the queue; cited files exist | the review | the same script check |
| step-plan | the opening sentence; steps; deps; commands; paths | steps in order with earlier deps only, `test_commands` and listing, criteria each named by a command, paths classified (`_check_submitted_test_commands`); not the opening sentence | the review | the same script checks |
| test-spec | every criterion has a test case; each case has an independent oracle and a RED and GREEN definition | none for coverage or for oracle independence; later: the test-author probe (a test the focused command runs), the `test-red` gate (the run fails as expected), `test-green` and `regression` | the review | the later gates |

The semantic rows are the unmet half of the rule that a step iterates until a stated check confirms each exit
criterion. A script-run requirement-ID presence check was considered and not recommended: the one traceability finding
identifiable was a wrong link, which an ID-presence check does not catch, and with no ID in the spec it would pass
having run nothing (S-9) [I; the Luna finding itself could not be read].

## Quality: what the review bought, and what it missed

Labels are judgement; there is no ground truth.

- Luna xhigh: 22 passes gave 5 warranted fixes, 5 minor, 2 corrections and 10 no change [ledger F10, interim]: the five
  were traceability, a fixture bypass of the real rules module, untested `/api/new` recovery, JSON content-type
  oracles and a W3 ready-check.
- Grok medium: 26 passes, 4 that fixed a real defect, 6 marginal, 4 churn, 12 no change [I, one investigation]; its spec
  review took 9 passes, four consecutive commits widening one import allow-list [M].
- 1.16.1 max: first passes found warranted defects in 6 of 9 children and 13 of 32 later passes changed something (3
  warranted, 7 marginal, 3 churn) [I, `docs/shiploop-fast-planning-plan-2026-10-04.md`, item c6].
- A measured catch of a related class [I] to the one review missed on Luna (both are a plan with no loadable seam; the
  Luna defect was a focused suite importing a file no step created, the Sonnet one a server that listens on import;
  the Sonnet run's Improve passes took about 4 s each and wrote about 270 B of review text, ledger F12, so it is not a
  like-for-like benchmark): a Sonnet 5.5 battleship run (skill-craft 1.16.0), commit
  `b1e196d` in its work repository, "Plan: add server entry guard so tests import without listening", message "Review:
  plan lacked an importable server design; tests needing a port would be flaky" [M, `sonnet-plan-review-b1e196d.txt`].
  Its planning commits span about 3.6 minutes, so `none` would save about 2 there and lose this catch.
- E6b: the planning review with the platform-claim bullet caught 10 of 15 real plan-stage platform errors against 0 of
  15 without it [M, `docs/shiploop-composition-state-experiments-2026-09-26.md`; limits: Sonnet, condensed packets,
  three trials per cell, the judge shares the gaps]. Under `none` that review does not run.
- What review missed: on Luna xhigh a plan that gave the tests no real module to load cost a 165.9-minute redo against
  99.2 the first time through those stages [M, ledger F9]; the 123-minute 1.16.1 case is an analogue (an implement
  revise), not the same defect. One missed event with review on, and one catch of a related class on another host [I].
- Break-even: `none` saves at most 203.4 minutes on Luna xhigh against an escape costing 66.7 (extra over the first
  pass) to 165.9: 1.2 to 3.0 extra escapes per run [I, arithmetic]. On Grok medium it saves at most 42.4 and the cost of
  an escape was never measured (the probe stopped before `test-red`): unknown. The escape rate with review off is
  unknown: no run without planning reviews exists.
- `none` also gives up plan reconcile and plan-time experiments, commits an unreviewed spec into the knowledge later
  runs inherit, and requires the Improve card at the start of the run (F1).

The default is one constant for every host. So a flip to `none` removes a small, measured catch from fast hosts for
about two minutes saved (D1). The owner decides that with M1 and M2 in hand.

## Change admission

The SPEC asks for each negative consequence to be sought and given a disposition: mitigated, accepted or change
rejected. First the SPEC's own questions, then every finding of the two attacks, then the owner's rules.

### The SPEC's questions

| Consequence sought | Disposition |
|---|---|
| Weakens S-9, S-10 or the owner's step rule | **Accepted**, for the five planning stages in `none` only, by an owner decision with an anchor (the 30-minute rule) and a carve-out that names what remains uncovered. Every Improve child that starts is unchanged, so S-10 holds for each loop that runs. |
| Weakens S-11 (knowledge retained) | **Mitigated**: the commit follows any accepted stage; a `none` test asserts the spec is committed after the `spec` stage through the real CLI (I2). The unreviewed content is stated in the carve-out. |
| Weakens S-7, S-8, S-12, S-13 | **Mitigated**: one swap table with an import-time guard (not scattered edits, S-12); one shared retry helper for the option guard (no third copy of the lint and backchain guards); no `--set` verb and no environment variable (S-13, no new surface); text is mode-neutral and names no platform (S-8). |
| Breaks another host, style or platform | **Mitigated** by the default staying `stage`; **accepted** for the flip: Sonnet-class hosts lose the `b1e196d` catch for about two minutes, an owner decision at I5. |
| Fails silently or passes tests while failing live | **Accepted and measured later**: a host that claims a review ran under `none` is not caught (the packet says not to claim one); a `none` run that still starts a child is refused by state. M1 to M4 read live behaviour. The probe's first design did fail silently (see A2-1) and was corrected before it landed. |
| Adds glue, refusals, dead ends, waits | **Mitigated**: the probe refusal names its exit (`revise` after `MAX_REFUSED_RUNS`, never gated on `revise` or `blocked`); a `none` run without `--improve-skill` is refused at its start, so no run stalls on a missing card (F1). The plan child commits by raw git in every mode today and is unchanged. |
| Enlarges packet or filed text | **Mitigated**: `none` packets are shorter in bytes at all five planning stages (33 to 944 bytes, `inline`, at `f6ed230f`) but not in words at `step-plan` and `test-spec` (5 and 1 words longer) [M, review finding F3]; `stage` packets are byte-identical to the tree before I1; I3 added three generic sentences (two in the `test-author` duty, one in the `step-plan` duty). |
| Leaks secrets or touches user work | None new: the same knowledge commits as today. |
| Breaks saved runs and pinned behaviour | **Mitigated by design**: a saved run without the key is refused with the fresh-run hint (one supported version); the owner is told before release (D8). The tests that pin the schedule keep passing while the default is `stage`; the flip is where 177 assertions in 17 of 22 schedule-sensitive suites need the old mode pinned (A2-5). |
| Costs more than it saves | **Accepted with arithmetic** (Quality, above). The probe costs one focused-command run at `test-author`'s done, the path ShipLoop already runs at `test-red`. |
| Gamed: a metric improves while behaviour worsens | **Mitigated** by measurement: report both windows (wide: intake to the first `test-spec` accept, the owner's; narrow: intake to `plan` accept), each with its clock, and never claim the 30-minute target met from a window alone; the first-pass review work moving into authoring is measured (M1 item 3). |

### Attack 1 (measurement, decision record and text), nine findings

| # | Sev | Finding | Disposition and evidence |
|---|---|---|---|
| A1-1 | major | The default flip is not gated on any measurement; revert criteria cannot be evaluated; ship `none` as an opt-in as `a34a6ee6` shipped Backchain `none` | **Accepted in part.** The flip is gated by M1 and M2 and is its own dated SPEC commit plus one constant; the code default stays `stage`; the revert rule is restated in observables that exist. **Rejected**: the precedent claim. `a89135f7` recorded the new behaviour (one pass) as the default in the same release and `0df9b0c4` made it print; `none` was the non-default flag [M, commits]. **Rejected**: "E2E has no channel for a stage control"; `run.py --source checkout` builds this checkout, so control and treatment run from the same code (the treatment is the flag in the case prompt or `DEFAULT_PLANNING_REVIEW='none'` as an uncommitted edit [I]). |
| A1-2 | major | "`once` cannot meet 30 on Grok" holds only for the widest window; one clock must be used | **Rejected in part.** The journal fixes the owner's window as intake to the first `test-spec` accept [M, LEARNINGS "Planning time"], which D6 confirms; on it `once` cannot reach 30 (at least 36.5 even if free). **Accepted**: figures are stated per window and per clock (for the global trio, spec to plan: 33.5 minutes on the children clock and 36.16 on the exporter clock; for all five children 42.4 and 45.88): `none` on the narrow window (to `plan` accept, 57.8) leaves 21.6 to 24.3. `once` is not built (D2). |
| A1-3 | major | The quality statement omits `b1e196d` and E6b | **Accepted.** Both are [M] in this record, the SPEC Basis, the journal and the evidence directory, with the E6b limits. "Whether Sonnet loses anything: unmeasured" became "one catch measured, about two minutes saved". |
| A1-4 | major | `stage` is not byte-identical: the draft reworded the shared Improve sentences for every mode | **Accepted.** `guidance.prompt` takes `planning_review` keyword-only with the literal default `stage`, and the swap is made only for a stage that starts no child; every planning-stage packet and the plan Improve packet, both delegations, are compared with a golden captured before each increment (the 20-of-20 method of `a34a6ee6`). |
| A1-5 | minor | I0 states what open decisions decide; the table-row edit (c) is untrue | **Accepted.** This record was written after D1 to D3; the carve-out says the default is a later decision and names no `once` value; edit (c) is dropped (no harness code except `workflow_review` reads the mode); the probe landed first. |
| A1-6 | minor | `once` (I4) is deferred or its dependency removed; I1 records values the engine ignores | **Accepted.** `once` is not built (D2); I5 does not depend on it; I1 registers `stage` only and each later increment adds its value with its behaviour. |
| A1-7 | minor | I3, I4, I5 omit the verbose commit and journal obligations | **Accepted.** Every increment carries a verbose commit and a `Planning review` journal bullet. |
| A1-8 | minor | The `none` sentence repeats the Done-when text every mode prints | **Accepted.** Trimmed to what is new; this record and the SPEC say the stand-in is the producer's own confirmation, a model judgement, not a new check. |
| A1-9 | minor | L2 and L1's replacement review are not recorded as considered; D9 should be explicit | **Accepted.** Both are in "Alternatives" below; D9 is an explicit reject for this change (owner). |

### Attack 2 (engine correctness), ten findings

| # | Sev | Finding | Disposition and evidence |
|---|---|---|---|
| A2-1 | major | The probe judged in red mode accepts an exit-0 run that ran nothing and an exit-0 run whose listed IDs never appear | **Accepted; built in I3** (`e11b86ef`): exit 0 is judged in passing mode, a non-zero exit in red mode, accepted `passed` and `red`. Reproduced on seven recorded outputs [M, `probe_judge.py` and `probe_judge.out`; the rows are `PROBE_CASES` in `test/shiploop-test-loop.test.py`]. |
| A2-2 | minor | The probe's refusal text says the opposite of the placeholder rule | **Accepted; built in I3**: its own header (reworded in the review fixes from "did not run a test", which was false for a run in which tests ran, to "did not show a usable test run") and a closing sentence with `PROBE_RULE`. `test-author` may create the smallest loadable placeholder named in the step plan's paths (D5). |
| A2-3 | minor | Under `once` the repeat clause collides with in-place repair | **Moot while `once` is not built** (D2). Recorded as a requirement should `once` ever be built: reword the planning repeat clause so a defect the child can repair in place is repaired and only an unrepairable premise takes the `cancelled` route. |
| A2-4 | minor | The plan child prints no `improve-commit` route | **Rejected for `stage` and `none`**: the plan child omits it in every run today [M, `_render_improve` planning-reconcile branch], the commit gate needs no change [M, `improve_changes` snapshots the tree at bind], and raw-git glue exists today. Accepted for `once` only (not built). |
| A2-5 | minor | The default flip breaks 17 suites and `make_packet_frame.py` | **Accepted for whoever flips the default (I5, not this work)**: pin `planning_review='stage'` in every fixture that finishes a child at `spec` and in `skills/rubric-eval/suites/architecture-v4/make_packet_frame.py`; widen the file list to the measured set; one commit with the flip so main never has a red suite [M, attack logs re-summed: 177 added failures in 17 of 22 suites, a lower bound]. |
| A2-6 | minor | Several listed tests pass on the unchanged tree | **Accepted.** Every increment's tests are split into fail-first tests and labelled guards, and I2 pins both routes (a forged child at `spec` under `none` is refused at load; `improve-bind` on a `none` run with no child gets "no matching active Improve parent"). I3's tests were split this way. |
| A2-7 | minor | The packet scan uses three phrases; a `none` packet names Improve in 8 to 15 sentences | **Accepted** (I2): the scan is derived from the real render for every mode, delegation and planning stage; every sentence naming Improve is allowlisted with a reason or absent when the mode starts no child; the `str.replace` special case becomes one mode-neutral sentence; the table guard fires on an edited old sentence. Stage-mode packets have 11, 12, 20, 12 and 11 such sentences at the five stages [M]. |
| A2-8 | minor | `stage` is not byte-identical; baseline rows lack the mode | **Accepted** (byte-identity, as A1-4); recording `planning_review` in baseline rows and the Run Review export is a **handoff** (D7). |
| A2-9 | minor | Sequencing: the carve-out names the probe, which may land after the option | **Accepted**: the probe landed first; I1 registers `stage` only; no released tree carries a recorded option the engine ignores. |
| A2-10 | minor | Under `none` the first Improve binding moves to the end of the run | **Rejected as an engine change, accepted as a recorded limit: superseded 2026-10-05 by review finding F1.** The attack found no engine change needed and called the stall recoverable; it is not: the quality and test loops of the first item read `improve_skill`, which only the first `improve-bind` records, and no verb binds without an active child, so a `none` run started without the card blocks at its first `static-checks` (reproduced on the pure navigator: stage prints "Bound Until Loop card", none prints "Unavailable: no Improve card is bound to this run"). Built: `init` and `workspace start` refuse `none` without `--improve-skill` and resolve the card there, before anything is created. |

### The owner's rules

| Rule | How this change meets it |
|---|---|
| KISS: change only what the increment needs | Two values, one key, one retry helper, one swap table; `once`, `plan`, the per-item merge and the carry-forward scope change are not built. |
| One supported version | A saved run without `planning_review` is refused by the existing missing-fields check with the fresh-run hint; no migration, shim or alias. |
| Prompts concise and aimed at meaningful change | The `none` sentence says only what is new; no justified obligation is deleted; text is changed only for a stage that starts no child. |
| Stage packets byte-identical | A golden of every planning-stage packet and the plan Improve packet, both delegations, captured before each increment and compared after. |
| Fail first, through the real gates | Each increment's new tests are shown failing on the unchanged tree for the right reason; guards are labelled. |
| Content pins, not whole-text goldens | Only the byte-identity golden is a whole-text comparison. |
| Unmeasured is unknown, never zero | The escape rate, the share of pass 1 that moves to authoring, and Grok's escape cost are stated as unknown. |
| Journals and verbose prompt-change commits | `test/shiploop_e2e/LEARNINGS.md` entry `Planning review`; commits state the key learning, the evidence and the related commits. |

## Alternatives considered, and why each is out of scope

Savings below are [ledger, `docs/experiments/shiploop-planning-time-20261005/ledger-account-final.json`] unless noted.

| Alternative | Why not in this change |
|---|---|
| L1 replacement review: no model-run Improve at planning, replaced by script-run checks plus one review after the first RED or at the end | `none` is the first half. The compensating review is D9: not in this change, cost unmeasured, it touches another loop; revisit after M2. |
| L2 single pass: keep open, pass 1 and close, drop passes 2 to N | Saves 100.3 minutes gross on Luna and gives up 2 of 5 warranted fixes; an engine change (`required_trivial_reviews`, the import validator, an S-10 amendment). On Grok its pass-1 cost leaves the window above 30 [I], so it does not meet the owner's rule either. |
| L3 one review over all planning documents at the end of planning | Cascade cost unmeasured; strains the iterate-until-confirmed rule and S-11; at best 118 to 178 minutes on Luna. |
| `once`: one review of spec, test-strategy and plan together at `plan` | Even if free it leaves at least 36.5 of Grok's 72.7 minutes, so it cannot meet 30 on the owner's window; largest increment; open design problems (A2-3, A2-4). D2: not built. |
| `plan`: children at `plan`, `step-plan` and `test-spec` only | D2: not built. A one-line schedule, 42.6 to 44.4 minutes on Grok on the wide window, 27.7 to 29.5 on the narrow one. |
| Per-item merge (`step-plan` and `test-spec` reviewed once after `test-spec`) | D4: rejected. A child bound to `test-spec` cannot amend the step plan's steps, commands, criteria or paths, so a structural fix becomes a revise and a re-authoring pass (the Luna redo's `step-plan` took 120.1 minutes against 38.7), and it saves only the `test-spec` child (2.5 to 3.0 minutes on Grok, 14.2 on Luna). |
| L7 lazy per-item planning | Relabels time: wall to green is unchanged unless the step plan is derived after RED, which changes the stage graph. |
| L11 script lint of documents, L17 a cheaper revise path, `--backchain-passes none` as the default (L13) | D10: out of scope. They are the only levers that reach 30 minutes on Luna xhigh. |
| A host-sensitive default (`none` for slow hosts) | A new surface in the engine; pass `none` by the case prompt instead. |
| Resolve the Improve card at `init` under `none` | **Built after review (F1)**, for `none` only: the stall A2-10 called recoverable is a block at the first `static-checks`. `stage` keeps binding at the `spec` child. |
| Static import analysis for the missing-module defect | Language-specific (S-8); the probe runs the real focused command instead. |

## Measurement plan and the revert rule

Quality first, then tokens, then time (the owner's eval priority); unmeasured is unknown. Baselines: the two 1.21.0
battleship runs, n=1 each, stage times varying about 2x. They ran 1.21.0, not the tree under test, so the control for
any comparison is a `stage` run of the same checkout. No new channel is needed: E2E builds this checkout with
`--source checkout`.

- **M1** (gate for any flip). A Grok medium planning-only probe stopping at the first `test-spec` accept as the 1.21.0
  probe did: `none` twice, `stage` once. Read (1) the planning window and minutes per stage against 72.7 and against the
  control; (2) Improve children in the window (expect 0 at `none`) and Improve minutes elsewhere; (3) authoring minutes
  per stage (stage minutes minus Improve minutes) against the 1.21.0 baseline (spec 4.0, test-strategy 5.5, plan 6.2,
  step-plan 2.7, test-spec 1.5; 26.8 in all): growth means first-pass review work moved into authoring; (4) document
  bytes against the baseline (spec 19,151, test-strategy 20,880, test-spec 11,162); (5) `planning_review` recorded in
  `state.md`.
- **M2** (gate for any flip). A post-hoc review as the escape proxy: on a scratch copy of each probe's repository run the
  `stage`-mode review, one Improve child per planning document, outside the run and on the same host, and count findings
  by class (warranted, minor, none) per document; compare with the Luna five and with E6b's platform-claim class.
- **M3** (needs the owner's go; the Grok baseline stopped at `test-spec`). To-green runs at `none` and `stage` on the same
  cell: revise count and minutes, the first-RED outcome, whether the test-author probe fired and what it said, `test-red`
  outcomes, and which defect classes reach a later gate that the review caught at `stage`.
- **M4.** One Luna xhigh run at `none`: the planning window and the first work item's `test-red` outcome.

Revert rule, comparisons only, no invented numbers. (a) If the Grok medium `none` window is over the owner's 30 minutes,
the review change has done what it can and the remainder is authoring and Backchain, so the owner's rule says rethink
planning; this is not by itself a revert. (b) Revert the default to `stage` (one constant, one pin) if M2 finds warranted
fixes at `none` that the control's reviewed documents do not need, if M3 shows more revises or more minutes to green at
`none` than at `stage` on the same cell, or if a defect class reaches a later gate that review caught at `stage`. Report
the window per definition, wide and narrow, each with its clock.

## Increments

| Id | What | State |
|---|---|---|
| I3 | The test-author probe: a script-run check that a test can load, where it can be fixed (independent of the option) | landed, `e11b86ef`, journal correction `7ad157cb` |
| I0 | SPEC carve-out, this record, the evidence directory, the journal, supersession marks | landed, `6db8ef7a` |
| I1 | The option, value `stage` only, recorded like `backchain_passes`; every packet byte-identical | landed, `7317f458` |
| I2 | `none`: mode-aware validation, stage-identical text, docs and oracles (`dag_replay.py`, `workflow_review.py`) | landed, `f6ed230f` |
| R1 | Review fixes: unittest load failures count as no test ran (E1); a `none` run names and resolves its Improve card at its start (F1); document scan scoped by sentence and the unqualified sentences qualified (F2); two review-promising sentences swapped for `none` (E3); wording and record corrections | the commit after `f6ed230f` |
| I4 | `once` | not built (D2) |
| I5 | The default flip: its own dated SPEC commit stating the default and the measured basis, then one constant and its pins. With `none` as the default every new run must name its Improve card (F1), so the flip also makes `--improve-skill` required for a plain `init` or `workspace start`: decide that with the flip | the owner's later decision (D1); not part of this work |

## Known limits

- A command that runs a failing test and also has a module that cannot load, with no ID listed for that module, is
  accepted by the test-author probe: a count cannot tell (the SPEC carve-out says so).

- `none` with `--backchain-passes none` leaves no model-run look at the plan graph.
- The plan child commits by raw git in every mode today, which the E2E metrics count as model glue (S-4, S-5); unchanged.
- The test-author probe does not cover a test that contradicts its own helper (the 1.16.1 implement revise looks RED at
  `test-red`), and protects the run total, not the planning window.
- Whether the host obeys the new `none` packet sentences, and follows the probe's placeholder rule, needs live runs.
- A saved 1.21.x run, including both 1.21.0 battleship run directories, is refused after the option lands; no E2E
  process was running when this was checked.

## Statements superseded

- `docs/shiploop-fast-planning-plan-2026-10-04.md`: item c6 ("keep") and decision D4 ("revisit as its own option") for
  Improve's planning-stage passes. This is that option. Marked in place, dated 2026-10-05.
- `docs/shiploop-delivery-overhead-plan-2026-09-23.md`: the invariant "Every planning result gets its own Improve child".
  Under `--planning-review none` the five planning results get none. Marked in place, dated 2026-10-05.
- Commit `9747d769`'s sentence "Improve's planning-stage passes stay (3 warranted, 7 marginal, 3 churn of 13 changing
  later passes)" is superseded here; a commit message is not edited.
- Run Review item a24 ("compare Improve's planning passes on the next Luna run") in `docs/shiploop-run-review-journal.md`
  is answered by M1 to M4; that file belongs to the Run Review session, so it is a handoff, not edited here.

## Evidence

`docs/experiments/shiploop-planning-review-20261005/`: `README.md`, `design-final.json`, `design-draft.json`, the four
reports (`report-engine.txt`, `report-consumers.txt`, `report-value.txt`, `report-rules-and-wording.txt`), the two
attacks (`attack-measurement-and-text.json`, `attack-engine-correctness.json`), `sonnet-plan-review-b1e196d.txt`,
`e6b-excerpt.md`, `probe_judge.py` and `probe_judge.out`, `passes.py` and `passes.out`. The run data these rest on is in
`docs/experiments/shiploop-planning-time-20261005/`. Related commits: `9747d769` (the first S-10 carve-out and its
evidence), `a89135f7` (the `backchain_passes` option, the precedent), `0df9b0c4` (one-pass text), `a34a6ee6` (the 20-of-20
render check), `2f091a35`, `a9f592a3` (planning time on Luna and Grok), `4484b25a`, `e11b86ef` (the probe).
