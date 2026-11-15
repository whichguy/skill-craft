# ShipLoop E2E improvement loop: skill name, effectiveness gaps, generic vs specific (draft, 2026-11-15)

Owner question (2026-11-15): a runner in the ShipLoop E2E harness that (1) starts a ShipLoop run, (2) lets it go
through its stages, (3) inspects every stage, file and journal for effectiveness and efficiency, (4) uses
higher-reasoning advisors to evaluate and find improvements, then repeats. Asked: does it exist, what should the
named skill be called, what else would make it more effective, and what part could be generalized.

## What exists (verified at origin/main 7fb5ba64)

- `test/shiploop_e2e/iterate.py` (525 lines), the exploration loop: per iteration, in its own worktree, build the
  worktree's plugin → `run.py` the case → `review.py` (reviewer, Codex Astra high) → `judge.py` (fresh judge, Astra
  high) admits material findings → commit LEARNINGS + evidence export + learning records → improver (Sol 6.1 max since
  7fb5ba64) edits `skills/shiploop` → quick tier. Stops on --iterations, two clean passing reviews, two idle improvers,
  evaluator-boundary crossing, out-of-scope edits, red suite, or a run that never reached the skill. Its final
  candidate is "unevaluated" (iteration-result.json).
- `iterate.py --qualify` → `cycle.py` (992 lines), the qualified loop: one learning record → one candidate → purpose
  check → promotion/5 epoch (candidate vs loop tip, attempts per arm on the exposing case and a case of another style,
  tolerance from an A/A calibration) → PROMOTE keeps it, DROP/UNDECIDED parks it under `refs/shiploop-loop/...`.
  Stops after `NON_PROMOTE_STOP` cycles without PROMOTE or when no admitted record remains after exploring.
- Evaluator boundary (`boundary.py`): improver may write only the candidate paths; held-out files withheld; digests of
  harness, checks/ and case entry must not change.
- Learning records (`learning-records.jsonl`, `learning_records.py`): 24 records since 2026-10-30. Latest state:
  8 open, 3 admitted (waiting for a cycle), 5 with the owner, 5 deferred (separate evaluator experiments), 1 accepted,
  1 promoted and verified, 1 dropped and refuted. Promotion decisions ever: 2 PROMOTE, 1 DROP, 2 UNDECIDED (both
  UNDECIDEDs later re-decided), all on `hello` (hook continuation). Last record event 2026-11-11.
- No named skill launches either loop. `/skill-craft:shiploop-e2e-audit` binds a separate, older Grok-only harness
  bundled in its package (`skills/shiploop-e2e-audit/harness/`, 61 files; its run.py 1,658 lines vs the main harness's
  5,082) and treats a campaign as manual checkpoints. `/skill-craft:shiploop-run-review` reviews one run for the owner;
  iterate.py only prints the `advise` command after each iteration.

## 1. The skill's name

Recommendation: **`shiploop-e2e-iterate`** (`/skill-craft:shiploop-e2e-iterate`).

- It names the script it drives (`iterate.py`) and the harness's existing unit ("iteration", "qualified iteration"),
  so one term per concept holds (glossary rule). Its modes are the script's: explore (default) and `qualify`.
- `shiploop-e2e-` puts it in the harness family beside `shiploop-e2e-audit`: it improves ShipLoop, it is not part of
  ShipLoop.
- Rejected: `shiploop-improve-loop` / `shiploop-improve` ("improve" already names ShipLoop's own Improve stage, the
  `improve` skill and the separate `improve-loop` campaign skill: three meanings already); `shiploop-self-improve`
  (ShipLoop does not improve itself: a separate improver model does, under an evaluator boundary, and "self" hides
  that); `shiploop-e2e-loop` ("loop" is already ShipLoop's own name and its inner loops, S-10).
- The description should still carry the owner's words ("self-improving loop", "run, review, improve, repeat") so the
  host matches the request to it.
- It is repository-bound, unlike the other two: the loop commits to a skill-craft worktree and builds from it, so the
  skill must resolve a skill-craft checkout and refuse elsewhere.

## 2. What would make it more effective (ranked by expected gain on ShipLoop's code production)

1. **Settle the three open loop decisions and unblock the measured calibration** (owner decisions; nothing to build
   first). D1 (attempts and tolerance): the 2026-11-01 calibration measured that one build's processed tokens span
   17.7M to 44.1M (csv-report) and 22.1M to 50.4M (seat-reservations); at 3 attempts per arm 0.45 on tokens (0.30 on
   turns, 0.40 at 4 attempts) keeps false calls at or under 10%, while the stated 0.25 calls noise a change in 28-36%
   of re-deals. D3 (cycle resources) and D4 (review every attempt: 24 of ~38 sessions a cycle) are open.
   `cycle.load_calibration` refuses that measured calibration on main because the scoring digest covers all of
   `checks/`, so any new check file stales every calibration; narrowing it to the calibrated cases' checks is a
   separate owner decision. Until these settle, every qualified cycle runs on a stated, unmeasured tolerance, and its
   efficiency verdicts are mostly noise.
2. **Pick the instrument per learning record, not one heavy cycle for all.** Whole runs can only see large effects
   (above, a 2.5x token spread within one build). The 10-31 decision already said: correctness and large effects on
   full runs; efficiency lessons on step slices (experiment.py). Today's owner feedback (cheapest instrument first)
   adds: a small reference-text fix is settled by reading the failing runs' upstream records and running the real
   case to the stage and stopping it. cycle.py has none of this routing: every record gets a full promotion epoch
   (~38 sessions at 3 attempts, about two hours). Proposed: the prediction already names measure and stage; add the
   instrument (stop-at-stage real run, step slice, full epoch) to it, chosen by the smallest one that can see the
   predicted effect, and record why.
3. **Put the advisors where the loop actually stalls: owner-routed design challenges.** 5 records sit with the owner
   and 5 deferred; the judge routes every design challenge (the "higher logic" findings) out of the loop by design.
   An `/advisors` panel (Opus, Astra, Grok, Kimi; two passes) per owner-routed record would write a recommendation
   with options onto the Run Review page so the owner decides in one look; the owner still decides (a ShipLoop
   behaviour trade-off is one-way). Advisors seats have write tools by default, so as evaluators they must run
   read-only. Per-attempt advisors instead of the single Astra judge would multiply ~12
   judgments a cycle by four seats with no evidence they judge better (3 decided records is too few to measure).
4. **Give the reviewer a comparator.** review.py hands the reviewer one run (transcript, events, product, run state,
   metrics.json) and the last three commit messages, but no baseline for the same case and host, so "efficiency gain"
   is judged from one run without a reference. Add the case's `baselines.jsonl` rows (same host and model) and the
   run's Run Review `facts.md` to the reviewer's evidence list.
5. **Close the publish step for promoted work only.** Both loops end on an unpublished branch. Publishing a release
   after preflight and CI is routine (owner, 2026-10-28), so the skill may land a PROMOTE'd commit on main, release
   and refresh hosts. Exploration-loop commits are unevaluated and stay off main (AGENTS: "Unaccepted candidate code
   stays out of main"), so the skill's explore mode produces learning records, and only qualify mode produces code
   that can land.
6. **Run it visibly and safely beside other sessions.** Launch as a background task, check for live runs first (no
   tier beside live runs; machine-wide port leases and case locks refuse overlaps), and publish each iteration's Run
   Review page.
7. **Vary the example.** The exploration default is one case (battleship); qualify takes a generality case. Rotate
   cases across loops (SDLC fidelity over sample fitting).

Not recommended: more review layers, more gates, or a generic framework now (S-12, KISS; the machinery has outgrown
its use: 2 promotions in 16 days while most ShipLoop gains since 11-01 came from targeted manual sessions).

## 3. Generic vs specific

Generic (subject-agnostic in substance, if not yet in code):
- the loop controller: worktree per loop, iterate with stop rules, journal and learning commits, branch output,
  nothing published unasked;
- role profiles and host adapters (`hosts.py`: isolated HOME, Grok/Claude/Codex argv, stream translation, effort
  carried to native children);
- the evaluator boundary (candidate-path allowlist, held-out files, grader digests);
- the learning-record ledger (open → admit → predict → decide → verdict; owner routing);
- prediction, promotion and A/A calibration statistics (`prediction.py`, `promotion.py`, `spread.py`, `epoch.py`);
- the review → independent judge → improver pipeline with fail-closed validity and sealed review hashes.

ShipLoop-specific (the subject adapter):
- `run.py`: build the plugin, launch `/shiploop` in an empty directory, find the `.shiploop` run directory, grade with
  the case's `checks/`, `cases.json`, fixtures, ports and oracles;
- `metrics.py` counters (packets, stages, fresh starts, model glue, S-clause rows);
- `SPEC.md`'s S-clauses and the PREMISE the reviewer checks conformance against;
- candidate paths (`skills/shiploop`, `changes/shiploop`) and the release preflight's E2E-round rule;
- step slices and the stage suite (ShipLoop's stage graph);
- the Run Review exporter (reads ShipLoop's run records).

What already exists generically (survey of 13 skills, 2026-11-15): no skill is a subject-agnostic run → review →
judge → improve → rerun loop with an evaluator boundary. The pieces are spread out: `until-loop` (frozen exit checks,
trivial-streak counting; the worker also runs its checks, no model judge), `improve-loop` (generic campaign with an
advisor panel; advisors told in words not to edit, no held-out graders), `rubric-eval` (strong isolation and a
statistical A/B rule, but a person drives iterations), `model-eval` (hidden-test guard), `prompt-research-cycle` /
`autonomous-prompt-research` (Adopt/Try/Defer commit journal, anti-flap rule), `advisors` (four-seat two-pass panel;
seats have write tools by default). The ShipLoop harness is the only place where all of these meet.

Recommendation: do not generalize now. The owner scopes work to generic ShipLoop and its generic E2E test, and there
is one consumer. Do keep the seam: the generic parts should not import ShipLoop names, so that a second subject
(Backchain, Plan Dispatcher or Improve, all skills in this repository) would need only a new adapter. Generalize when
that second subject is real.

## Unknowns

- Whether max effort on the improver changes the quality of applied changes (unmeasured).
- Whether a multi-model judge would admit better than one Astra judge (3 decided records; unmeasurable now).
- Wall time of a full qualified cycle on Grok 4.6 xhigh (never measured live; "about two hours" rests on Terra runs).
