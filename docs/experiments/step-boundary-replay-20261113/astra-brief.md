# Astra brief 3: is this replay worth running, and is it designed right? (2026-11-13)

Read-only, max effort, checkout origin/main. Read `docs/experiments/step-boundary-replay-20261113/README.md`, the
registered design, and the prior evidence `docs/experiments/step-boundary-replan-20261112/README.md` (E1-E9, and your
two earlier reviews there). Fix forward shipped in shiploop 1.34.0. A send-back keeps done steps, the amended plan must
copy their rows marked done, and two step-plan refusals were added. The smoke round had no send-back.

Answer:
1. Given that fix forward and the two refusals shipped, which of Q1 and Q2 is still worth its cost? Q2's late faults
   were mostly plan-time faults, and a document send-back still redoes the current step. Say what you would cut or add.
2. Are the measures, predictions and decision rules sound? Are they decidable by script alone, with no model judging?
   Name any rule that the data could not settle, or that invites rescoring.
3. Case construction: what from a real run must a reconstructed state carry for the replay to be faithful (knowledge
   home, environment.md, the run guard, the Improve card, open items, lint base), and what may be synthetic?
4. The builder route `seed_route` (ordered results, per-entry overlays, after the default seed): any trap in driving a
   real run through `navigator.apply` and `accept_effects` with synthetic results for implement, test and document,
   for example step commits, lint bases, the iteration ledger, or automatic not-applicable documents?
5. Sample sizes: 4 per case for Q1, 3 per arm per case for Q2. Enough to decide the registered rules?

Return verdicts and concrete changes, with file and symbol citations where you rely on code.
