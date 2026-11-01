# Backchain efficiency cohort — protocol (pre-registered 2026-11-01)

Written before the candidate is frozen and before any held-out case is opened by the candidate's author.

## Question

Does the candidate Backchain (skill-craft branch `backchain-eff-9aea18`, frozen at the commit recorded in
`freeze.json`: the shipped toolkit, the native card, the first-trivial-review gate and the lean synthesis prompts)
plan at least as well as the control (Backchain 0.6.6, skill-craft `e81fdb55d58bdb0bcc8c1643d93d5973709100e4`),
and if quality is near-identical, with fewer tokens, then in less time? Order of judgment, by the owner's rule and
rubric-eval SPEC section 8: a material quality difference decides; otherwise tokens; otherwise time.

## Arms and conditions

- **control**: `skills/backchain` and `skills/improve/runtime/until-loop` at e81fdb55.
- **candidate**: the same two trees at the frozen candidate commit. The Until Loop runtime is byte-identical in
  both (the candidate does not touch `skills/improve`); `freeze.json` records both trees' digests.
- Subject and grader: `gpt-6-astra`, reasoning effort medium, Codex CLI (version and binary SHA-256 recorded),
  with the 2026-10-16 study's isolation flags: ephemeral, no user config, memories, plugins, apps, skills search,
  multi-agent or web search; workspace-write sandbox for subjects, read-only with no shell for graders.
- Workspace: a fresh temporary directory per attempt, laid out like the plugin install
  (`resources/skills/backchain`, `resources/skills/improve/runtime/until-loop`), with `fixture/`, `request.md` and,
  per case, `inherited-plan.json` and `caller.json`.
- Subject prompt: one arm-neutral text for both arms (cohort.py `prompt_for`): the request, the selected skill
  card, the selected Until Loop card, the case's `Backchain passes` marker when its gate is `one`, the constraints
  (planning only, fixture and inputs read-only, no network, people, services, subagents or other models), and the
  two final destinations, `artifacts/plan.json` and `artifacts/result.json`. Unlike the 2026-10-16 study it supplies
  no bookkeeping destinations or check commands: each arm follows its own card, as a user's invocation would.
- No retries; failed, timed-out and malformed attempts stay in the denominator; 30-minute deadline per attempt.
  Arm order randomized within each case/repetition pair (seeded); two pairs run concurrently.

## Cases

Ten cases: the six of the 2026-10-16 study (its `cases.json`, unchanged) and four held-out cases designed blind by
a separate agent (`../heldout/`, MANIFEST.json SHA-256
`7c81681f9a1e558dfd5a4b0a06786943744abc07ce2d7b5fb02d7665b115e07a`), each with semantic criteria and mechanical
answer keys (`keys.py`). Three repetitions per arm: 60 attempts.

## Measures

Per attempt:
- **Outcome checks** (common to both arms; what a user receives): process ok; no input drift; `artifacts/plan.json`
  structurally valid under the 2026-10-16 arbiter (`check-plan.js` over the lib.js snapshot) with the case's
  expected completion; the actual Until Loop ran, and its terminal packet, read from the subject's own tool output,
  has the case's expected status; `artifacts/result.json` exists and claims converged planning only if that packet
  is `complete`; inherited content kept for draft cases and protected bounds kept for source cases (the 2026-10-16
  checks); the loop's gate is the arm's own for the case (control default 2, candidate default 1, `one` cases 0).
- **Quality**: three blind grading passes per attempt on the universal and case criteria, evidence first (quote,
  then grade `met`/`partial`/`missed`/`na`), with the rubric-eval quote check. The grader sees the request,
  fixture, sources and bounds, the final plan, and a normalized disposition (terminal status, planning gaps,
  execution blockers); never arm-specific artifacts.
- **Mechanical keys** (held-out cases): `keys.py` pass count over the final plan.
- **Cost**: input, cached, uncached and output tokens as the CLI reports them; wall seconds; commands;
  hand-written code blocks (Python or Node written and run by the subject).
- Protocol conformance of each arm to its own card is reported descriptively, not used in the decision.

Secondary measures, added 2026-11-01 after the adversarial review of the candidate (`../adversarial/sol/findings.md`)
and before the freeze:
- **Confirming-review yield (finding F6).** D1 drops the confirming review. In every control attempt, each Until Loop
  report the subject submits after its first trivial report is a confirming review. From the subject's own tool calls
  (its event log), count them and the ones classified non-trivial, and examine each non-trivial one by hand against
  the request: did it repair a real material defect? Reported beside the 2026-10-16 prior (0 of 11 confirming reviews
  changed anything). Not in the decision rule, because D1 is the owner's decision: a real material defect that only a
  confirming review found is reported to the owner as evidence on D1. Limitation: the control's confirming review runs
  in the same session as its first review, as 0.6.6 runs it, not with an independently contextualized reviewer.
- **Per-family quality (finding F7).** Qualification, score and mechanical keys are reported per case. The three cases
  where the lean prompts qualified less often on 2026-10-16 (bounded source-edge repair 2/3 against 1/3, known
  external approval blocker 3/3 against 1/3, missing normative redaction source 2/3 against 0/3) are also reported
  pooled, 9 cells per arm.

Score = percent of available rubric points (met 2, partial 1, missed 0; `na` excluded), mean over the three passes.
An attempt **qualifies** when every outcome check passes and no critical criterion is graded missed by a majority of
the passes.

## Runner implementation notes (2026-11-01, before the freeze)

`cohort.py` (built by a separate agent from `BUILD-BRIEF.md`; dry run 48 expectations, 0 problems; 48 unit tests on
Python 3.15.1 and 3.9.6) deviates from the 2026-10-16 study's code in these ways, all accepted before the freeze and
applied identically to both arms:
1. Terminal-packet extraction also counts the output of a helper script that a command naming the runtime or
   `done_argv` wrote, when that script runs later. This is the 2026-10-16 study's own post-hoc correction of
   `known-external-approval-blocker-current-r2` (its action-scope audit), now applied up front; with it the
   extraction matches all 36 retained receipts, and the confirming-review count reproduces 11 and 0 non-trivial.
   The miss it fixes falls mostly on the control, whose hand-built route uses helper scripts.
2. A source-repair case's `caller.json` points at `inherited-plan.json`; `artifacts/` starts empty.
3. The input one-liners drop their bookkeeping destinations and the old prompt's hints about each case's trap.
4. The grader packet also carries the inherited draft and the requirements; the quote check searches the packet
   without the criteria; a grader call is retried up to 3 times (a process failure or any tool action is a
   malformed reply), with a 900 s deadline.
5. An attempt with no readable plan scores 0 without a grader call; any missing attempt means no decision; a graded
   attempt missing a valid verdict in any pass blocks a candidate win.
6. `result.json` claims converged planning when its planning gaps are empty and it states no other terminal or
   planning status (the control's binding record has no status field).
7. Subjects and graders run without Until Loop session-key variables; workspaces are `backchain-cohort-*`, naming
   neither arm nor case.
8. `preserved_edge_keys` is not checked (the old check never read it).

## Decision rule (rubric-eval SPEC section 8)

Paired on case × repetition cells; 95% percentile bootstrap (4,000 resamples) clustered by case; Wilcoxon
signed-rank over per-case mean differences. Significant = both agree on a direction.
1. Quality near-identical when the whole score interval lies within ± the round's grader noise (mean pairwise
   difference between passes divided by √3). Then tokens (input + output) decide, then wall time; a tie keeps the
   control.
2. Otherwise a significant quality difference decides.
3. Otherwise inconclusive: no decision.

Blocks on a candidate win: qualification rate or mechanical-key pass rate lower (paired interval below zero);
qualification in the three previously losing cases, pooled, lower than the control's (finding F7); grader noise
unmeasured; fewer than 8 cases compared.

## Order of work

1. Smoke pilot: the candidate arm on the six old cases, one repetition each (excluded from the cohort). Fix only
   defects that stop the workflow; any fix is committed before the freeze.
2. Adversarial review of the candidate diff by another model family; each substantive finding becomes a check or an
   experiment before the freeze. Done 2026-11-01 (codex:gpt-6.1-sol, medium; `../adversarial/dispositions.md`):
   F1–F5 and F8 fixed with fail-first tests in skill-craft 26d4785541fedbfba91bb32e61d525ed8f4a19f2; F6 and F7 are
   the secondary measures and the added block above. A second round on those fixes (same reviewer;
   `../adversarial/round2/dispositions.md`) found five more; all are fixed with fail-first tests before the pilot,
   in the commit the journal's Round 5 names. The pilot then runs that commit.
3. Freeze (`cohort.py freeze`), then run all 60 attempts, then the three grading passes, then the analysis.
4. No candidate change after the freeze; a revised candidate is a new cohort.
