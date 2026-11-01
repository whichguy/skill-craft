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
