# prepare: re-cut draft (worker A)

## 1. Goal (R1)

Ready the development and test environment the plan named: record its readiness, or a justified not-applicable, in
HOME/environment.md, and cite the runner output that shows each planned check starts in `evidence_refs`.

## 2. Duty

1. Prepare or verify the development and test environments that FEATURE/plan.md and HOME/test-strategy.md name
   (Environment preparation guidance). Use what the repository already declares. Install nothing without authority.
2. Confirm with safe observations: isolation, runtime, configuration and data safety, access, fixture readiness, and
   the baseline identity (Workspace and return guidance).
3. Start each planned check's runner, the configured linters and the fixtures, and save the output. Put each output
   file in `evidence_refs`.
4. When setup or access blocked the initial baseline (Initial repository baseline guide), prepare only the approved
   prerequisite, keep the original observation, and rerun the original initial check against the unchanged product
   and tests before any dependent feature edit. Never replace it with an easier route or call the blocked baseline
   passed.
5. Recheck the source-return trigger that discovery recorded, and the authorized delivery and verification route
   from the execution checkout, before its first dependent work. When the source return must precede a required
   consumer check, record the ordering conflict in `summary` as unresolved. Never return early, deploy, or bypass the
   final-handoff return guard to make local work possible.
6. Record readiness under HOME/environment.md ## Targets and runtimes and ## Commands: what was prepared, the commands
   that start each runner, and the observations. Record a not-applicable there only when this candidate needs no
   preparation, with what you assessed. Missing required access or setup is blocked, not not-applicable.

## 3. Checked by

- A HOME or FEATURE file that this close requires missing or empty: HOME/README.md, HOME/spec.md,
  HOME/test-strategy.md, HOME/architecture.md, HOME/environment.md, FEATURE/spec.md, FEATURE/plan.md.

## 4. Guides to keep

- Environment preparation guidance (environment-lifecycle.md#plan-preparation-before-its-first-consumer): item 1.
  Today's text never cites it; item 1 now does.
- Workspace and return guidance (workspace-lifecycle.md#entry-identity-and-storage): item 2. Today's text never cites
  it; item 2 now does.
- Drop (never cited): UI planning ownership when applicable.
- Policy the prose names: Initial repository baseline guide (item 4).

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| PR1 Prepare or verify the approved environment and prerequisites. | Item 1 |
| PR2 Confirm isolation, safety, access, fixtures, baseline identity with safe observations. | Item 2 |
| PR3 Justified N/A only when no preparation is needed; missing access or setup is blocked. | Item 6 |
| PR4 Recheck the source-return trigger and the delivery/verification route before first dependent work. | Item 5 |
| PR5 Source return before a consumer check: record the conflict, unresolved; no early return, deploy or bypass. | Item 5 (`summary`) |
| PR6 Use the Initial repository baseline guide. | Item 4 |
| PR7 Setup-blocked baseline: approved prerequisite only, keep the observation, rerun the original check first. | Item 4 |
| PR8 No easier route; never call the blocked baseline passed. | Item 4 |
| PR9 Record readiness or N/A in HOME/environment.md; cite runner output per planned check. | Items 3, 6; Goal |
| Develop: use what the repository declares; install nothing without authority. | Item 1 |
| Test: confirm the test runner and fixtures start. | Item 3 |
| Deploy: prepare the development and test environments the plan named. | Item 1 |
| Tools: confirm the configured linters and the test runner run. | Item 3 |
| _PLANNING_HANDOFF 1 (summary and registered material). | Items 3, 5, 6 |
| _PLANNING_HANDOFF 2-3 (plan and step-plan only). | CUT (R3) |
| _PLANNING_HANDOFF 4 (absolute evidence_refs). | Item 3. Unsure: prepare is not a planning pass; the block applies only because prepare is in PRELUDE |

## 6. Size

- Today: 2,019 characters.
- Proposed: 2,065 characters (102%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.


## Tightened (pass 2)

Duty size (inline): 1,646 -> 1,500 characters (-9%). Goal: 'Ready the development and test environment; record readiness in HOME/environment.md and runner output in `evidence_refs`.'; short goal: 'prepare the environment'.

Text now in `DUTIES['prepare']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Prepare or verify the development and test environments the plan's items and HOME/environment.md name
   (Environment preparation guidance), using what the repository declares. Install nothing without authority.
2. Confirm by safe observation: isolation, runtime, configuration and data safety, access, fixture readiness,
   baseline identity (Workspace and return guidance).
3. Start each planned check's runner, the linters and the fixtures; save the output and list each file in
   `evidence_refs`.
4. Baseline blocked by setup or access (Initial repository baseline guide): prepare only the approved prerequisite,
   keep the original observation, and rerun the original initial check on the unchanged product and tests before any
   dependent feature edit. Never replace it with an easier route or call the blocked baseline passed.
5. Recheck discovery's source-return trigger and the authorized delivery and verification route from the execution
   checkout before the first dependent work. If the return must precede a consumer check, record the ordering
   conflict in `summary` as unresolved. Never return early, deploy, or bypass the final-handoff return guard.
6. Record readiness under HOME/environment.md ## Targets and runtimes and ## Commands: what was prepared, the
   commands that start each runner, the observations. Record not-applicable only when this candidate needs no
   preparation, with what you assessed. Missing required access or setup is blocked, not not-applicable.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
