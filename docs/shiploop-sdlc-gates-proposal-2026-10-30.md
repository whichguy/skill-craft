---
Execute: ask
Status: proposal; nothing built or run. Track A and SG1 need no model run; SG2 waits for D3.
Opened: 2026-10-30
Consumer: the owner, who approves, strikes or re-scopes each decision in §7 before anything is built or run; later,
  whoever proposes a ShipLoop gate from outside research and needs the bar it must meet
Journal: none yet; results go to test/shiploop_e2e/LEARNINGS.md and docs/experiments/sdlc-gates-20261030/
---

# Outside SDLC research: measure in the harness, gate on a live run — proposal, 2026-10-30 (awaiting the owner's decision)

Owner, 2026-10-30: "Is there something more I should be doing in shiploop stages in the SDLC for the planning, step
creation, inner loop, outer loop? Am I missing stages that should be fixed (ie enforced steps that must be run [for]
good practice?)", then: "Synthesize these, determine if we need side experiments to validate any of these or we have
sufficient evidence in the claims to move forward with a proposal. Provide the final plan." Nothing here is built.

The owner's rules this keeps:
- the script confirms each step's exit, and the model only reports (`shiploop-purpose`);
- loops end on their criteria, never on a count (test/shiploop_e2e/SPEC.md:245-256);
- a gate is added only when a live run shows the failure (CHANGELOG.md:96; docs/shiploop-plan-sizing-journal.md:210);
- unattended is the default, with no separate attended setting (P9, docs/shiploop-e2e-plan-2026-09-27.md:526-528);
- tests follow implement (docs/shiploop-inner-loop-stage-diagnosis-2026-10-10.md:141;
  docs/shiploop-review-after-tests-design-2026-10-27.md:11);
- acceptance stays scripted or rendered, never model taste (docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md:241);
- a default that breaks comparability with earlier evidence is the owner's (AGENTS.md:57).

## 1. The answer

**No stage is missing, and only one new gate meets the live-run rule.** ShipLoop's 23 stages cover more of the SDLC
than GitHub spec-kit, Kiro, BMAD or Anthropic's published long-running harness. The gates the research supports best
are already built: RED on the base, the mutation check, test floors, proofs the script runs, and `blocked` and
`send-back` as allowed exits (an allowed abort is the best-measured counter to test tampering, §2a).

The outside evidence (54 findings, §2a) is strong that coding agents edit tests, leak secrets, add invented packages,
break earlier features and pass reviews of their own work. It was measured on agents without ShipLoop's guards, and the
saved runs in this repository show almost none of it (§2b). But those copies keep about 3% of what the model wrote, so
for most of these "none seen" means "not measurable yet", not "absent".

So the plan has three tracks:
- **measure** in the E2E harness, with no ShipLoop change (§4);
- run **two side experiments** where the evidence is suggestive and a decision is waiting (§5);
- **drop** what the owner's earlier decisions, made on ShipLoop's own data, already settled (§3).

The one candidate that already fired live twice is a proof-order check at `step-plan` (SG1).

## 2. Evidence

### 2a. Outside research (2026-10-30)

Three research passes:
- papers and benchmarks;
- Reddit, which refuses this environment's crawler, so it was read through quoting pages, HN and GitHub issues;
- X, HN and practitioner blogs.

The numbers a decision here rests on:

| Failure mode | Evidence | Source |
|---|---|---|
| Agents edit tests to pass | ImpossibleBench: over 79% of Claude models' cheating was editing tests. An allowed abort cut GPT-5's cheating from 54% to 9%, with a smaller effect on Claude. Retries with feedback raised it from 33% to 38%. | https://arxiv.org/html/2510.20270v1 |
| Prompts don't stop it | "Do not cheat" moved o3 from 80% to 70% of runs | https://metr.org/blog/2025-06-05-recent-reward-hacking |
| Self-review is lenient | LLM judges favour their own output. A fresh same-model reviewer did about as well as a cross-model one, and one of each caught 56.7% of planted errors against 42.7% for two same-model reviews (a preprint). | https://papers.nips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html, https://arxiv.org/abs/2610.01471 |
| Insecure code, invented packages | Insecure code in 45% of tasks (Veracode 2025). 5.2% to 21.7% of suggested packages do not exist. Five refinement rounds raised critical vulnerabilities by 37.6%. | https://arxiv.org/abs/2406.10279v3, https://arxiv.org/abs/2506.11022v2 |
| Earlier features break | Existing tests kept passing in about 25–50% of tasks (FeatBench). Scores fall from over 80% on isolated tasks to 38% in continuous runs (SWE-Milestone). | https://arxiv.org/html/2509.22237v1, https://arxiv.org/abs/2603.13428 |
| Passing is not mergeable | About half of test-passing SWE-bench Verified PRs would not be merged | https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/ |
| Ambiguity | Up to +74% when models may ask, and they rarely ask unprompted | https://arxiv.org/abs/2502.13069v3 |

Limits:
- No benchmark ran ShipLoop's guards.
- Three practitioner claims were seen only second-hand: the Claude Code team's review-round cap, OpenAI's harness post
  and Kiro's mandatory phase review.
- 2610.01471 is a preprint.

### 2b. Base rates in the saved runs (audit, 2026-10-30)

**Corpus:**
- the 14 fidelity runs (test/fixtures/fidelity/);
- 7 scorecard runs;
- the per-step pilot;
- the measured-width and validation experiments (8 runs);
- the 25-run improve-value set;
- the one full run directory, v9 (docs/experiments/shiploop-eff-evidence-20261017/).

None of these keeps a worktree, git history or product diff. The fidelity events keep the content of 6 of about 200
product and test writes. The owner's full saved runs, outside this repository, may keep more.

| What | Count | Reading |
|---|---|---|
| Suppression comments added | 0 | Not measurable: write content is cut |
| Earlier tests rewritten | 11 of 28 test files were rewritten, all inside the item that made them: test-refine by design, static-checks, test-red. No later item did it in the fidelity runs. One Grok follow-on run rewrote both earlier test files, +134/−36 lines, 12 tests before and after (docs/experiments/e2e-grok-gate-2132-20261026/retention-test-count.txt). | Floors held: no fall in 221 comparisons of the same command. Weakened assertions are not measurable. |
| Files outside `paths` | 0 in 28 step commits, by design: `commit_scope` leaves undeclared files for plan-return, which no fixture keeps. The model hand-committed files ShipLoop skipped in 7 of 12 fidelity runs (README.md in 5, test/system.test.js in 4). In 3 of 8 runs that reached release, it answered a refused return by rewriting every `pending` disposition to `keep` (test/fixtures/fidelity/v1230-battleship-sonnet/events.jsonl:864). | A live sign of rubber-stamping; harm not shown |
| Same-reason refusal streaks | 32 refusals on 25 of 422 actions. Longest streak 2 (5 actions), all ended done. Causes: GNU `sed -i` on macOS, the model's own `grep` piped to `cut` hiding the listed files, the same wrong path twice. | A lower bound: refusals inside cut heredocs are lost |
| New dependencies | 0. No install command in 13 event streams, and the package.json files hold only scripts and engines. | The cases need no third-party package |
| Secrets | 0 in 1,571 files. The credential screen in place before D-10 refused 6 writes; their values were not kept. | — |
| Late catches | product-acceptance add-work in 0 of 8 fidelity runs and release-verify failures in 0 of 8. In the improve-value set, release-verify added work in 1 of 22 runs (a README claim the code did not keep). | The outer loop rarely finds what the inner loop missed |
| Document-stage reviews | 5, all in the per-step pilot. Inline and old route: 3 reviews, one trivial pass each, no file changed. Ask-agent: 2 reviews, both changed files (50 and 8 lines). | n = 5, and the routes differ in more than context |

## 3. Verdicts

Legend: 📏 measure (§4) · 🔵 side experiment (§5) · ⚪ owner decision only · ⚫ drop or defer · ↪ already in flight.

| # | Candidate | Verdict | Why |
|---|---|---|---|
| 1 | Diff audit: suppression comments, skip/only markers, edits to earlier tests, swallowed errors | 📏 P1, P2, P7 | Floors already refuse removed and newly skipped tests (skills/shiploop/references/test-loop.md:49). No run shows a suppression. The Grok follow-on rewrite is the case the floors cannot read. |
| 2 | Secret scan, new-dependency check, SAST | ⚪ D4 (keep D-10); 📏 P5, P6 | D-10 removed the credential refusal at the owner's request because it refused ordinary prose (docs/shiploop-efficiency-plan-2026-10-16.md:643). 0 secrets and 0 dependencies in the corpus. |
| 3 | Improve review in a fresh context | 🔵 SG2 | Recall is unmeasured (docs/shiploop-improve-value-journal.md:455). Fresh reviews were dropped as the default on 2026-09-24 for cost: 7–17 min and 40–100 tool calls per run (docs/shiploop-delivery-overhead-plan-2026-09-23.md:11-16, 149-160). Pilot hint: fresh document reviews changed files 2 of 2, inline 0 of 3. |
| 4 | Acceptance tests written before the build | ⚫ Drop | "Tests follow implement" (2026-10-10, 2026-10-27). Tests-first redos cost 123 and 165.9 min (docs/shiploop-batch-1008a-journal-2026-10-08.md:30-34). Late catches: 0 of 8. |
| 5 | Rerun earlier items' tests once per item | 📏 P4 | The full regression runs at each item's last step, and a gate refuses a focused command that only reruns an earlier item's IDs (skills/shiploop/scripts/shiploop_navigator.py:2789). No escaped regression found. |
| 6 | Refuse changed files outside `paths` | 📏 P3 | The owner asked for width measured from what each step changed, not predicted by the plan (2026-10-27, LEARNINGS.md:3988). The audit's live signal is hand commits and bulk dispositions, not wide steps. |
| 7 | Escalate when the same failure repeats | ⚪ D5 (do not adopt V4 now) | Three no-count rulings (SPEC.md:245-256). V4 (docs/shiploop-owed-outcome-journal.md:311, 363) would have fired on the 5 two-refusal streaks if their trees were unchanged, and all 5 passed on the next try. |
| 8 | Ask one-way questions at intake; spec lint | ⚫ Drop | P9. Proposed principle D1 that checks never judge prose (docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md:193). Unmeasurable criteria are already an Improve duty. |
| 9 | Maintainer-merge rubric | ⚫ Drop | CODE_CRAFT already says "Write for the next maintainer" (skills/shiploop/scripts/shiploop_prompts.py:600). P4: never model taste. |
| 10 | Fresh context per work item | ⚫ Drop | G1 "Adopt (a2)" (2026-10-29). In the pilot, the item level took 17.3 min and 19.94 M input tokens against inline's 5.3 min and 8.06 M (test/shiploop_e2e/LEARNINGS.md:4300-4312). |
| 11 | `--approve` human checkpoint | ⚫ Drop | P9. Owner notes steer a live run (docs/shiploop-owner-notes-design-2026-10.md). |
| 12 | Structural and behavioural steps (Tidy First) | ⚫ Defer | No sign of the problem |
| 13 | Property-based cases for stated invariants | ⚫ Defer | The mutation check is the instrument that would show weak tests (LEARNINGS.md:3982, 4055) |
| 14 | Small-change lane | ↪ F1 | The owner's open question (LEARNINGS.md:4062) rides on F1's stage, bundle and none comparison (docs/shiploop-improve-value-journal.md:468) |
| 15 | Seams first | ⚫ Watch | The missing-module failure has not recurred since 0.55.0 |
| 16 | **Proof order at `step-plan`** (new) | 🔵 SG1, then D6 | Fired live twice: DeepSeek W1's Proof ran a test file only the later test stage writes, costing a send-back (LEARNINGS.md:3652). In Grok chess 5b, S3's proof needed castling "before S4 adds castling" (docs/shiploop-improve-schedule-proposal-2026-10-25.md:62). No check at step-plan reads the Proof's paths today. |

## 4. Track A — measure in the E2E harness

**First, keep the evidence.** Make sure each finished E2E run keeps what the probes read: each ShipLoop commit's
diff, any commit ShipLoop did not make, the return plan and its dispositions, and the review texts. The copies in this
repository do not (§2b). If the owner's full saved runs do, run the probes over them first, for base rates without a
model run.

Then seven probes in a new harness module beside `audit_probes.py`. Each writes a descriptive scorecard line outside
the grading digest and is never scored:

| Probe | Detects | For |
|---|---|---|
| P1 | Suppression comments the run added (`# noqa`, `eslint-disable`, `@ts-ignore`, `type: ignore`, `pylint: disable`, `//nolint`) | #1 |
| P2 | An edit to a test file an earlier step or item created, with assertions removed or loosened | #1, #5 |
| P3 | Commits ShipLoop did not make; return dispositions flipped in one edit; kept paths in a transient path class | #6 and §2b |
| P4 | An earlier item's test IDs missing from a later item's full regression output | #5 |
| P5 | New dependencies, and whether each exists in its registry | #2 |
| P6 | Secret-like strings in commits: known key formats and private-key blocks only | #2 |
| P7 | Swallowed errors in product code (`except: pass`, an empty `catch`, `\|\| true`) | #1 |

**How a probe becomes a gate:**
1. The probe fires on a live run, and the finding is confirmed real.
2. A replay of the gate on every saved run shows it would refuse no honest run, the method of
   docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md §0.
3. The gate then goes to the owner as its own proposal.

**Cost:** test/ only, so no change note and no ShipLoop release. Hermetic tests run on synthetic diffs.

## 5. Track B — side experiments

### SG1. Proof order at step-plan (replay, no model)

**Claim.** A static check at `step-plan` catches a step whose Proof cannot run when `implement` completes. Today that
is found only by the step-proof gate at `implement`, after a whole Until Loop.

**Candidate check.** Refuse a done step plan when a step's Proof names either of these:
- a path in the tests class that the item base lacks (the test stage writes it later);
- a path that only a later step's `paths` declares.

**Corpus.** Every step plan the full saved runs keep, replayed with ShipLoop's own readers, as `ts1_in1_replay.py` did.

**Bar** (set before the replay):
- DeepSeek W1 is flagged.
- Grok chess 5b is flagged if its Proof names a path that only S4 declares, and reported either way.
- No step whose Proof passed at `implement` is flagged.

**Then:** met → D6. Missed → record the check's limits and close.

### SG2. Review recall: inline against fresh (seeded-defect stage slices)

**Question** (docs/shiploop-improve-value-journal.md:455): do step reviews find defects that exist, and does a fresh
context find more?

**Corpus.** The four seeded-defect step cases in test/shiploop_e2e/step_cases.json:
- `node-seeded-case-compare`;
- `node-seeded-numeric-sort`;
- `node-seeded-empty-guard`;
- `node-seeded-early-validation`.

The cases' own checks miss each defect, so the review is the last line. `seeded_defects.py score` reads the final tree,
and arms.py already turns it into `seeded_defect_caught`.

Optional, before the run: two more seeds of the classes the research names, a swallowed error and a test that asserts
the implementation rather than the spec. Each needs `verify` to tell naive from fixed.

**Arms**, each slice seeded at the step's review and stopped after it:
- A (control): `delegation: inline`.
- B: `delegation: ask-agent`, so the review runs in one fresh worker.

**Subject.** Codex Terra 6.1 at xhigh with hooks on, the current default, so no new baseline cell. 4 samples per arm
per case (experiment.py's default): 32 slices after a 2-case smoke that measures minutes per slice.

**Metric.** Catch rate per arm; minutes, turns and tokens per review.

**Bar** (set before the run): B is promoted on a catch-rate gain larger than the A/A spread (control samples 1–2
against 3–4), unless its minutes per review exceed 1.5 times control's.

**Then:**
- Met → D3b proposes the fresh review as the default for step reviews. This reverses the 2026-09-24 split's default.
- Not met → the recall of each route is recorded, which closes the journal's open question, and inline stays.

**Limit.** A seeded slice gives the inline reviewer the stage's records, not a long producer conversation, so it
understates the self-review the research describes. A gain under that handicap counts for more, not less.

SG4 (same failure on an unchanged tree) was planned and is dropped: the audit in §2b answered it.

## 6. Order of work

1. Track A: keep the evidence, then P1–P7 with hermetic tests. No model run.
2. SG1 replay. No model run. Then D6.
3. SG2 after D3: the 2-case smoke for cost, then the 32 slices. Then D3b.
4. Anything that changes ShipLoop takes the usual path: a change note, an E2E round after the change, and the release
   preflight.

## 7. Decisions for the owner

- **D1. The principle.** Outside research justifies measuring a failure mode; a gate still waits for a live ShipLoop
  run that shows it (CHANGELOG.md:96). Agree, or name a class to gate on outside evidence alone.
- **D2. Track A.** Keep each E2E run's evidence and build probes P1–P7 as descriptive scorecard lines.
- **D3. SG2.** Run the review-recall slices on Terra: a 2-case smoke, then 32 slices.
  - **D3b.** If B meets its bar, make the fresh step review the default.
- **D4. D-10.** Recommended: keep it. 0 secrets were found, and the screen it removed refused prose; P6 watches. The
  alternative is a scan limited to the commits ShipLoop makes, known key formats only, never results or prose, shipped
  only after a replay with zero false refusals. Irreversibility is the one argument for it: a pushed secret has to be
  rotated.
- **D5. V4.** Recommended: do not adopt it now. Its trigger would have sent 5 actions back to planning that each passed
  on the next try. STUCK_FIX stays the stopping criterion.
- **D6. Proof order.** If SG1 meets its bar, add the step-plan refusal. It has already fired live twice.
- **D7. The drops.** Confirm the drops and deferrals in §3 (4, 8–13, 15), or name one to reopen.
- **D8. The small lane.** Leave it to F1.
