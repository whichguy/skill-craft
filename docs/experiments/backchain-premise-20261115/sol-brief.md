# Brief given to Sol 6.1 at max effort (verbatim)

Run: `ask.sh sol --json --effort max --profile consult --cwd <neutral export>`, 2026-11-15. The export held origin/main's
`skills/backchain`, the value study folder, the efficiency journal, ShipLoop's two Backchain references and Plan
Dispatcher's SKILL.md, with local account paths replaced (see README.md). Nothing from the private harness was sent.

```text
You are reviewing a planning skill called Backchain. Its owner asks, plainly: does it provide any value at all on
current frontier models (GPT-6.1 Sol, Grok 4.6, Claude Sonnet 5.5 and Opus 5.5), or is the construct and premise
itself too rudimentary, something these models already do on their own? Answer honestly; neither a defence nor a
dismissal is wanted, only the truth as the evidence supports it.

Everything is in the current directory (read-only; do not modify files):
- ./backchain/ is the skill package: SKILL.md, prompts/, references/, scripts/ (backchain.py, backchain_graph.py,
  check_preservation.py), evals/.
- ./shiploop-integration/ is how its main caller, a delivery harness called ShipLoop, used it (backchain-route.md,
  backchain-planning.md).
- ./plan-dispatcher/SKILL.md is a consumer that executes the dependency graphs Backchain produces.
- ./study/ is a pre-registered comparison of Backchain against no skill: 60 attempts over 10 cases on three models,
  blind graded twice by Claude Opus. RESULTS.md and PROTOCOL.md describe it; evidence/*.json holds every attempt, plan,
  grade and analysis; plan-format.md is the plan format both arms were asked for; value.py is the harness.
- ./journal.md records the earlier efficiency rounds of the skill and later decisions about it.

Please do the following, citing file paths and numbers for each claim and saying when a claim is your own reasoning
rather than something the files show:

1. State Backchain's premise in one paragraph: what failure of an unaided model it claims to fix, and the mechanism
   by which it claims to fix it.
2. Break the skill into its components (for example the backward-chaining prompts, the routes, any question or intake
   phase, the review and convergence loop, the deterministic graph checks, the caller contract with its edit bounds and
   preservation checks, the plan schema and export). For each component give: the failure it targets; whether a
   frontier model asked plainly for the same plan already avoids that failure, and what evidence shows it; its cost;
   and a verdict of keep, cut, or reduce to a script or schema.
3. Steelman the case for value before you conclude. In what kind of task would Backchain plausibly beat an unaided
   frontier model, and why? Is that kind of task common for the callers this skill actually has?
4. Critique the study. Can it answer the owner's question? Consider case difficulty and ceiling effects, the grader,
   and what was measured against what matters downstream (execution). Use the per-case and per-criterion grades in
   study/evidence to find any place where Backchain helped or hurt, and check whether the no-skill arm's plans fail
   the skill's own structural checks (you may run the scripts read-only, for example on plans extracted to a temporary
   directory outside this folder).
5. Name the single cheapest experiment that would change your verdict, and the result that would change it.
6. Give a bottom line. Keep two questions apart: whether the idea (planning backward from the goal through
   preconditions) is valuable, and whether this implementation adds value over a model that already has the idea.
```
