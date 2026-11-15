# Backchain value study: Backchain against the same model without it (pre-registration, 2026-11-15)

Written and committed before any attempt runs. A later report that disagrees with this file is a finding about the
report, not a reason to edit this file. Owner request, 2026-11-15: "whether Backchain is as effective with the most
recent models or it's not nearly as valuable", on "Grok 4.6 on extra high, GPT Sol 6.1 on medium, and Sonnet 5.5 on
high".

## Question

For each model: does a planner that runs Backchain 0.7.0 (the released skill, its toolkit and its Until Loop
review) produce better dependency plans than the same model given the same request, the same inputs and the same
plan format, but no Backchain skill? And what does Backchain cost in tokens and time?

## Why it is open

No measurement compares Backchain with no Backchain on current models. The evidence there is:

- 2026-07-25 (`backchain/docs/experiments/phase0b-discriminating-power-2026-07-25.md`): on July's models, the unaided
  model already handled several cases well, and the skill's cases told the arms apart poorly.
- 2026-07-26 (`plan-value-n2-2026-07-26.md`), n = 2: with a plan, an implementer did more, at an unmeasured cost.
- The 2026-10-16 study and the 2026-11 cohort compared Backchain versions only.
- Since 2026-11-02, 0 of 13 real ShipLoop plan stages started a Backchain child.

## Arms

- **backchain:** the workspace holds the released skill files under `resources/skills/` (`skills/backchain` and the
  bundled Until Loop, from the frozen origin/main commit). The prompt is the 2026-11 cohort's subject prompt
  (`cohort.py` `prompt_for`), unchanged: execute the selected Backchain skill and deliver `artifacts/plan.json` and
  `artifacts/result.json`.
- **none:** the same workspace without `resources/`. The prompt asks for a dependency-aware plan of the request in the
  format `plan-format.md` describes, under the same constraints. It also asks for `artifacts/result.json` with
  `status` (complete or incomplete), `planning_gaps` and `execution_blockers`.
- **Both arms** get the same request, fixture files, inherited plan and caller packet (`caller.json`, with its edit
  bounds and sources), and `plan-format.md`. That file is the released SKILL.md's "Plan document shape" section, so
  output format is not what differs.
  - The none arm's caller packet drops `selection`, which names the skill file.

## Models and hosts

Each model runs through the E2E harness's host layer (`test/shiploop_e2e/hosts.py`, at the frozen commit), with
permission mode `auto`. Each attempt gets its own throwaway profile. No plugin is installed in either arm.

| Model | Host | Setting |
|---|---|---|
| Grok 4.6 | Grok CLI | `--reasoning-effort xhigh` |
| GPT Sol 6.1 | Codex CLI | `model_reasoning_effort=medium` |
| Sonnet 5.5 | Claude Code | `--effort high`, `--setting-sources project,local` |

## Cases

The 2026-11 cohort's 10 cases (`backchain/results/backchain-efficiency-20261101/cohort/cases.json`, hash-pinned at
freeze): 6 from 2026-10-16 and the 4 former held-out cases, which are now development cases. There is 1 run per case,
arm and model: 60 attempts. A pilot of 6 (one case, `stale-build-receipt-identity`, both arms, three models) runs first
and checks only the harness. Its attempts are not analysed.

Criteria are the cohort's, with three study changes fixed here:

1. **The universal `terminal-disposition`** is worded without a runtime, since the none arm has none: "Completion
   reflects planning evidence. Missing planning prerequisites remain planning gaps; future approvals may remain
   execution blockers. A stop is correct when it names a gap the plan cannot close; the plan and its final status do
   not claim unsupported completion."
2. **orders-cancel-rpc**, owner decision D-B (2026-11-01): Backchain's contract forbids moving inherited seed work, so
   stopping with the bundling named is correct, and a plan that makes the split is correct too.
   - `store-split-from-docs` (critical): either S3 consumes a separately checkable SetStatus supplier with no path to
     the API-reference work, or the plan keeps S2 whole and names the bundling as an open gap, instead of silently
     ordering S3 after the docs.
   - `bundle-claim-consistent` (non-critical): if a store supplier is split out, S2 consumes it.
3. **library-reminders:** completing with a stated sequential-caller scope and stopping on the atomic-claim gap are
   both acceptable, under `terminal-disposition` as worded above.

The mechanical keys of the 4 former held-out cases are reported descriptively only. Known defects: billing's
selectors fail the pretest-hook design (journal R10-5), and orders-cancel-rpc's keys encode the split.

## Grading

- **Grader:** Opus (`ask.sh opus`, `--no-tools`, effort medium), blind, 2 passes per attempt, with the cohort's
  rubric (`grader-rubric.md`) and quote check.
- **Packet:** the request, fixture files, inherited draft, sources, requirements, edit bounds, criteria, the final plan
  and a normalized final record: status complete or incomplete, planning gaps and execution blockers. Backchain's
  `converged` counts as complete.
- **Blinding:** `parallel_groups` is stripped from both plans (journal R9-5). The cohort's redactor removes workspace
  paths, skill paths, planning-tool names and bookkeeping file names. No loop status, review record or run file is
  shown.
- **Score:** met 2, partial 1, missed 0, `na` left out; percent of the points, averaged over the 2 passes.

## Analysis and reading, per model

- **Difference:** for each case, backchain minus none. Its mean and a 95% bootstrap interval are taken over the 10
  cases.
  - **valuable:** the interval's low end is above 0;
  - **no meaningful edge:** the interval's high end is below +5 (the owner's δ);
  - **the skill costs quality:** the high end is below 0;
  - **inconclusive:** anything else. At 10 cases the interval is expected to be about ±5 to ±8, so only a large edge
    can show.
- **Also reported:**
  - attempts with a critical criterion missed in both passes;
  - structurally valid plans (the released `backchain.py check`) and complete ones;
  - mechanical key rates;
  - processed and output tokens and wall time per arm, with the paired differences;
  - the grader's pass-to-pass difference.
- **Failures:** an attempt that fails for infrastructure (host crash, no model turn) is retried once before grading. A
  case still missing an arm is dropped for that model and reported. A model with fewer than 8 complete pairs reads
  inconclusive. A model failure is scored as delivered: no plan scores 0.

## What it does not establish

- Downstream value: whether a better plan changes what gets built.
- Models or efforts other than the three above.
- Backchain inside ShipLoop, where the host plans with ShipLoop's own guide either way.

## Amendments from the harness pilot (2026-11-15, before the study's freeze; no study attempt had run)

The 6-run pilot (`stale-build-receipt-identity`, both arms, three models; not analysed) found three harness defects.
All three are fixed before the study is frozen, and a second pilot checks the fixes.

- **A1, format knowledge.** The no-skill Sonnet plan failed only invariant 7, eight times (`from: null` inputs not
  declared in `initial_state`). That rule sits in SKILL.md's "Structural invariants", which the first
  `plan-format.md` (the "Plan document shape" section, copied) left out. The study measures the procedure, not
  knowledge of the format.
- **A2, permissions.** Grok's `auto` permission mode refused the subject's own `cp` and `rm` inside its workspace ("a
  headless run cannot ask for approval"), so no `result.json` was written. Grok and Claude now run with
  `bypassPermissions`, as Codex already runs with full access. Each workspace is a throwaway temporary directory, and
  the prompt forbids network access, contact and other models.
- **A3, isolation.** The no-skill Grok subject ran `backchain.py package` and `check` from a sibling attempt's
  workspace in `$TMPDIR` (the Backchain Sonnet attempt's `resources/`). The copied shape section named `check`,
  `freeze` and `record`, and the subject went looking for them. Fixes:
  - (a) `plan-format.md` is a hand-written restatement of the two sections with no tool or procedure name, committed
    in this directory and given to both arms.
  - (b) Every workspace sits under a root its owner cannot list (mode 0300), so a subject cannot see other attempts.
    The Backchain arm's `resources/` is deleted as soon as its attempt ends.
  - (c) Both prompts add the same constraint: use only the files in this workspace, and do not read, search or run
    files outside it.
  - (d) A no-skill attempt whose stream shows Backchain files (`backchain.py`, `skills/backchain/`, the Until Loop
    runtime) is *contaminated*: it is rerun once. If it is contaminated again, it is excluded from grading and its
    case drops for that model, and the report names it.
  - Structural validity is checked on a packaged copy, because `parallel_groups` is derived and `[]` fails invariant
    6 until packaged (the 2026-11 cohort's amendment A1).

Nothing else changes: question, arms, models, cases, criteria, grading, analysis and reading stand as above.
