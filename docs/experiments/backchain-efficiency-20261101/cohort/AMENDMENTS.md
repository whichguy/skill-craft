# Cohort amendments (recorded during the runs, before any grading or analysis)

## A1 — packaging-normalized structure, and a criterion sensitivity (2026-11-01, about 09:50)

Observed: the first control attempt (`known-external-approval-blocker-control-r2`) failed `plan_structure` and
`plan_completion`: "Stored parallel_groups does not match recomputed longest-path depth groups". Its plan keeps
`parallel_groups: []`, as Backchain 0.6.6's own card instructs: "Keep `parallel_groups: []` in the canonical plan
until that receipt exists", where the receipt is a deterministic validator's, which 0.6.6 does not ship. The
2026-10-16 study gave every subject `check-plan.js` and the command that packages and checks the plan. This cohort's
prompt deliberately gives neither, so a 0.6.6 run that follows its card cannot pass the registered structure check.
That is the journal's Round 0 finding R0-6, observed live.

Kept as registered: the outcome checks, qualification, the grading packet (graders see each plan as delivered) and
the decision rule. Added, decided before any grade or analysis exists:
1. **Packaging-normalized structure.** For every attempt of both arms, `plan_structure` and `plan_completion` are also
   evaluated on a packaged copy of `artifacts/plan.json`. That is lib.js `packagePlan`, which recomputes only
   `parallel_groups` and changes no step, edge or confirmation. This gives a second, packaging-normalized
   qualification.
2. **Blocks under both definitions.** The qualification block, the mechanical-key block and finding F7's pooled
   block are evaluated under the registered qualification and under the packaging-normalized one. A block that fires
   under either definition blocks a candidate win. This is stricter on the candidate than the registered rule.
3. **Criterion sensitivity.** The quality comparison is reported twice: as registered, and without
   `dependency-logic`, the only universal criterion that mentions parallelism. A decision that differs between the
   two is reported to the owner as not robust to how graders treat `parallel_groups: []`. Grader quotes that mention
   `parallel_groups` are counted per arm.
4. Both qualification definitions are reported, with how much of the control's registered failures packaging alone
   explains.

None of this changes a frozen input. `cohort.py`, `PROTOCOL.md` and the cases are untouched; the extra analyses run
as a separate script over the retained attempts after `analyze`.

## A2 — post-hoc regrade R1 without `parallel_groups` (2026-11-01, about 11:50, after the registered analysis)

Registered result (`analysis.json`): inconclusive. Quality, candidate minus control, was −1.19 points, 95% [−8.85, +6.26],
Wilcoxon p = 0.75, with grader noise ±1.05, so there is no winner. Tokens (−630k per cell, 30 of 30 cells lower,
p = 0.005) and time (−124 s, 30 of 30 lower) favoured the candidate, but they decide only when quality is
near-identical. A1: packaging-normalized qualification 19 of 30 in both arms; F7's pooled block fires under it
(candidate 6/9, control 9/9).

What prompts the regrade, found after seeing the grades (post-hoc):
- Graders mention `parallel_groups` in 76 candidate criterion rows and in 0 control rows.
- All 49 of the partial or missed ones are in the two edit-bounded repair cases: bounded-source-edge-repair
  (candidate −26.6 points) and revenue-export-lineage (−9.1).
- There, graders read the candidate's recomputed `parallel_groups` (from the inherited `[]` to
  `[["S1","S3"]]`) as a change outside the caller's bounds ("no-out-of-bounds-changes": missed). The candidate's
  toolkit recomputes this derived field on every save; 0.6.6 keeps `[]`.
- The candidate's three F7 non-qualifications are those bounded-repair attempts.

R1, fixed before it runs:
- **What changes.** Exactly the registered grader packets, minus `parallel_groups` in `final_plan` and
  `inherited_draft`, for every attempt of both arms. `parallel_groups` is derived from the steps' inputs, which
  stay in the packet.
- **What stays.** The same rubric, grader, model, effort, three passes and decision rule (cohort.py
  `build_report`), and the same quote check. The script is `regrade_r1.py`, writing `grades-r1/` and
  `r1-analysis.json`.
- **How it reports.** R1 is a post-hoc sensitivity analysis. The registered decision stays "inconclusive";
  R1's result goes to the owner, who decides adoption.
- **How it reads.** If R1's quality is near-identical (inside its own grader noise), the cost results stand as
  the difference between the arms. If R1 still shows a material quality difference, that difference is not a
  `parallel_groups` artifact.
