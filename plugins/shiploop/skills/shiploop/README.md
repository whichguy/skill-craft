# ShipLoop 0.9

ShipLoop is a Markdown-authoritative session harness for delivering one bounded
piece of work through a complete SDLC loop. It turns a long-running request into
small, durable actions so a host with a short context window can resume from
recorded evidence rather than chat memory.

It does **not** implement product changes, decide whether tests are meaningful,
or prove a human-facing, remote, or deployed outcome. The host performs those
judgments and records evidence; ShipLoop persists the result, checks transition
preconditions, and refuses unsafe or stale transitions.

## Table of contents

- [What ShipLoop is and is not](#what-shiploop-is-and-is-not)
- [Start or resume a run](#start-or-resume-a-run)
- [Seven explanatory phases and current stored states](#seven-explanatory-phases-and-current-stored-states)
- [Requirements modeling and traceability](#requirements-modeling-and-traceability)
- [Execution-plan, per-step evidence, tests, and documentation](#execution-plan-per-step-evidence-tests-and-documentation)
- [Ownership, context, and recovery](#ownership-context-and-recovery)
- [Current limitations and proposed safeguards](#current-limitations-and-proposed-safeguards)
- [Command reference](#command-reference)
- [Related references](#related-references)

## What ShipLoop is and is not

The full operator loop is intentionally broader than a single implementation
task. P1–P7 below are explanatory groups for people; they are **not** additional
CLI phases, JSON fields, or DAG nodes.

```mermaid
flowchart TD
    P1["P1: Frame work and establish baseline"] --> P2["P2: Survey and converge research and behavior"]
    P2 -->|Research evidence and behavior baselines accepted| P3["P3: Converge spec, sequence, and prepare"]
    P3 --> P4["P4: Select, converge a plan, and implement one ready step"]
    P4 -->|Step checked| P5["P5: Improve, learn, and merge"]
    P5 -->|Return to scheduler| P4
    P4 -->|DAG drained| P6["P6: Review the whole product"]
    P6 -->|Corrective step needed| P4
    P6 -->|Acceptance evidence complete| P7["P7: Deliver if authorized and hand off"]
```

The diagram is an operator map:

- ShipLoop's **stored phase and stage** choose one current action and protect
  its transition.
- The plan **DAG** orders work products and prerequisites; it does not describe
  runtime behavior in the product.
- A product **state or sequence diagram** describes what the product does for a
  user, client, service, or data object. It is neither a ShipLoop stage nor a
  ShipLoop DAG step.

For example, a product transition such as `Queued → Running → Timed out` can
be a requirement. A DAG may contain a step that implements it and another that
tests it. The harness will still move through stages such as `implement`,
`review`, and `verify` while doing that work. Do not turn product transitions
into invented harness stages or mistake a dependency edge for a product state
transition.

### Current controls, host duties, and proposals

| Status | Meaning |
|---|---|
| **Current control** | The script and authoritative Markdown currently store state, issue one action ID, validate declared result/evidence shape, gate research/behavior/specification candidates, and converge each initial or Improve execution plan with durable finding ledgers, fresh planning checks, and audit commits. |
| **Required host duty** | The host must make scoped edits, select meaningful tests, interpret evidence, review semantics, preserve unrelated work, and verify external effects. The script cannot mechanically prove these judgments. |
| **Proposed safeguard** | A documented improvement idea that is not a current stage, result field, or enforced gate. It must not be described as implemented. |
| **Known limitation** | A current state-machine or recovery gap. Follow the safe operating discipline and report the limitation; do not claim that the harness already closes it. |

The current packet and [action protocol](references/action-protocol.md) govern
when they conflict with an older guide. Capture a documentation mismatch in the
generic ShipLoop journal rather than improvising a transition.

## Start or resume a run

Choose a repository and a **fresh, dedicated** run directory. Starting from the
repository makes paths and Git evidence easier to interpret:

```sh
REPO=/absolute/path/to/repository
RUN_DIR="$REPO/.shiploop"
SKILL_ROOT=/absolute/path/to/shiploop

cd "$REPO"
python3 "$SKILL_ROOT/scripts/shiploop" init \
  --repo "$REPO" --run-dir "$RUN_DIR" --prompt "Implement …"
```

The first packet requests `preflight`. Inspect the committed Git baseline,
preserve unrelated dirt, identify the available runtime and checks, and assess
non-secret preparation needs. Put the requested result in the packet's inbox
path, with exactly one `shiploop-state` fence:

````markdown
# Preflight result

```shiploop-state
{
  "summary": "Committed baseline selected; unrelated dirty notes are excluded.",
  "baseline": "committed-head",
  "readiness": "The repository test command and runtime are available.",
  "prep_findings": "No environment preparation is needed before planning."
}
```
````

Then use the packet's exact command and action ID:

```sh
python3 "$SKILL_ROOT/scripts/shiploop" complete \
  --run-dir "$RUN_DIR" --action "$ACTION" --result /absolute/preflight-result.md
```

The JSON is structured content **inside** authoritative Markdown, not
permission to create a writable `state.json` or another sidecar. The action ID
is single-use: a stale action or a changed replay is refused. Use `next` to
resume the durable action after a cold context, not a fresh `init`.

## Seven explanatory phases and current stored states

The stored `phase` and `stage` pair is assigned by the script with a new action
ID. Numbered explanatory phases, DAG step IDs, and Improve iteration IDs are
different identifiers.

| Explanatory phase | Exact current stored phase | Exact current stage or stages | Outcome before the next explanatory phase |
|---|---|---|---|
| **P1 — Frame work and establish a baseline** | `intake` | `preflight`, `approach` | A selected committed baseline and an initial delivery approach. |
| **P2 — Survey and converge research and behavior** | `validate-spec` | `survey`, `research`, `research-review`, `research-plan`, `research-apply`, `research-verify`, `research-commit`, `research-finalize`, `behavior`, `behavior-review`, `behavior-plan`, `behavior-apply`, `behavior-verify`, `behavior-commit`, `behavior-finalize` | An as-of research evidence baseline and a frozen behavior model, with material ambiguity resolved or explicitly paused. |
| **P3 — Converge specification, sequence dependencies, and prepare** | `validate-spec`, then `plan` | `spec`, `spec-review`, `spec-plan`, `spec-apply`, `spec-verify`, `spec-commit`, `spec-finalize`, then `sequence` and conditional `prepare` | A frozen specification/lifecycle, validated dependency plan, and only authorized outer-before preparation. |
| **P4 — Select, plan, and implement one ready step** | `implement` | script-driven `schedule`, then `step-plan`, `step-plan-review`, `step-plan-revise`, `step-plan-verify`, `step-plan-commit`, `step-plan-finalize`, and `implement` | One active branch/worktree, a freshly finalized execution plan, step output, and fresh check evidence. |
| **P5 — Improve repeatedly, learn, and merge** | `implement` | `review`, `improve-plan`, then the same nested `step-plan-review`/`step-plan-revise`/`step-plan-verify`/`step-plan-commit`/`step-plan-finalize` stages, `improve-apply`, `verify`, `carry-forward`, `commit`, `final-verify`, `post-inner`, `merge` | A converged, locally merged step, current knowledge checkpoint, and broader-plan decision. |
| **P6 — Review the whole product** | `residual` | `coverage`, `quality` | Bound coverage and whole-product acceptance/integration evidence, or a corrective replan. |
| **P7 — Deliver if authorized and hand off** | `residual`, then `done` | conditional `publish`, `handoff`, then `done` | Actual delivery facts when applicable, limitations, handoff, and the terminal `done` state. |

`halted` / `halted` is an unfinished terminal exit outside P1–P7. `pause` is a
flag over the pending action, not a successful phase or stage. `schedule` is
script-driven: the host does not author a `schedule` result; the scheduler
selects a dependency-ready step or routes a drained plan to P6.

Approach, survey, sequence, authorized preparation, post-inner, coverage, and
quality are also substantive objectives. Each candidate is refined through
`objective-review → objective-plan → objective-apply → objective-verify →
objective-commit → objective-finalize` before the exact certified candidate is
applied once to its original activity. The generic loop is therefore part of
P1/P3/P5/P6, not an optional workflow beside the diagram.

### P1 — Frame work and establish a baseline

`init` captures the original request in a dedicated run directory. `preflight`
records the committed baseline, user dirt to preserve, available checks, runtime,
and preparation candidates without installing tools, changing shared
environments, or publishing. `approach` then creates the initial high-level
scope, risks, milestones, preparation candidates, and acceptance strategy.

The approach comes before the detailed specification. It is an initial delivery
direction, not an executable plan or blanket authority for later external work.

### P2 — Survey and converge research and behavior

`survey` records facts that later actions need without repeatedly rescanning the
repository: relevant references, permitted tools, writer routes, layout,
reserved paths, UI surfaces, test environments, and documentation conventions.
Never record secrets.

If a client will call a service, freeze the actual invocation contract before
authoring communication: the operations the service exposes and the
client/HTML conventions that call them. Test the real client path, not only a
convenient direct call to an internal helper. An exclusive destination writer
that fails is a blocker, not a license to silently choose another writer.

`research` submits a report `body` and typed `research_state`; the script imports
the paired `research.md` and `research-evidence.md` candidates. Each question has
a stable source-backed status and a revalidation policy. The mandatory research
loop is:

```text
research → research-review → research-plan → research-apply → research-verify
→ research-commit → (another research-review or research-finalize)
```

Research finalizes only after two fully recorded trivial-only passes, no open
findings or open/blocked questions, and a fresh candidate-bound check with the
exact acceptance `research evidence`. `research-finalize` records an as-of
certificate for the accepted paired candidates; it does not assert that a remote
source, credential, or deployment will remain current. Use the detailed
[draft schema](references/research-loop.md#draft),
[review rubric](references/research-loop.md#review), and
[evidence-and-freshness boundary](references/research-loop.md#evidence-and-freshness)
rather than inventing a parallel report format.

Research uses in-scope evidence and safe read-only probes. It does not require a
particular provider or a new tool, and it does not authorize installation,
configuration changes, destructive experiments, or publication. After
`research-finalize`, the mandatory behavior loop begins:

```text
behavior → behavior-review → behavior-plan → behavior-apply → behavior-verify
→ behavior-commit → (another behavior-review or behavior-finalize)
```

`behavior` drafts the requirement/flow/state/transition model from the durable
prompt and accepted research baseline; it is not frozen merely because a first
candidate exists.
At each loop pass, `behavior-review` reads current Git history and the bounded
candidate/ledger context, `behavior-plan` addresses every open finding,
`behavior-apply` imports the complete replacement candidate, `behavior-verify`
runs a planning-artifact lint/test manifest, and `behavior-commit` creates a
distinct verbose audit-only learning commit. The commit must preserve the
product tree, have the iteration baseline as its direct parent, and contain
`Review:`, `Changes:`, `Validation:`, `Key learnings:`, and the exact
`ShipLoop-Iteration:` trailer.

Each research, behavior, and specification planning-iteration packet makes its
terminal contract explicit:

- **Objective:** converge the current research, behavior, or specification
  candidate, not merely produce another draft.
- **Until:** two consecutive fully completed trivial-only passes, no open
  findings, and a fresh final check of the exact candidate.
- **Continue while:** an open finding, material change, repair, failed/stale
  check, or candidate/ledger/baseline drift remains.
- **Evidence required:** the durable review rubric, finding ledger, plan and
  resolutions, candidate- and ledger-bound planning checks, and audit commit.

Material findings, material application, or a repair reset the streak; a
trivial pass still needs a real review, checks, and commit. `behavior-finalize`
runs fresh checks without accepting a replacement candidate, then freezes the
checked behavior model. A material unresolved policy blocks finalization: pause
or seek user direction rather than guessing it. The three loops are bounded
operational convergence rules, not proof of semantic exhaustiveness.

The upstream packet contract uses the same objective/until/continue vocabulary
as `until-loop`. ShipLoop incorporates the standalone 0.1.3
repeat/verify/continue decision as the pure internal
`scripts/shiploop_until.py` policy used by specialized planning, per-step
Improve planning, and universal substantive-objective loops; it does not run or
modify the external skill or its CLI. ShipLoop remains the only runtime, lock,
transaction, and Markdown state authority—there is no JSON sidecar or second
loop session. Research/behavior/spec mechanics remain in
`scripts/shiploop_planning.py`; generic base activities use the objective-loop
receipt. See
[Planning convergence loops](references/planning-loops.md#until-loop-incorporation-boundary),
[Execution-plan convergence](references/execution-planning.md), and the
[universal substantive-objective loop](references/objective-loops.md).

### P3 — Converge specification, sequence dependencies, and prepare

After `behavior-finalize`, `spec` creates `spec-draft.md` and
`lifecycle-draft.md`. They are candidates, not the frozen `spec.md` and
`lifecycle.md` contract. The mandatory spec loop is:

```text
spec → spec-review → spec-plan → spec-apply → spec-verify → spec-commit
→ (another spec-review or spec-finalize) → sequence
```

It uses the same two-trivial-pass, no-open-findings, fresh planning-check, and
verbose audit-only commit gate as the behavior loop. Its rubric additionally
tests clarity, consistency, and feasibility. `spec-finalize` accepts no new
body or lifecycle candidate: it verifies the exact final draft and last audited
history, then atomically promotes the checked `spec-draft.md` and
`lifecycle-draft.md` to `spec.md` and `lifecycle.md`. There is no direct
draft-to-`sequence` shortcut.

The planning loops enforce their recorded candidate gates, but semantic breadth
review remains a current host duty: perform it on every research/behavior/spec
review, at `sequence`, on every affected P5 Improve cycle, and again at P6
outer quality. `sequence`, post-inner, coverage, and quality now use the same
script-enforced generic objective convergence stage; the distinct P4/P5
execution-plan loop remains the gate for source edits.

The frozen lifecycle record answers placement before coding:

- `preparation: none | dag | outer-before`
- `publish: none | dag | outer-loop`
- `quality: true | false`
- `acceptance: [...]`

At `sequence`, make a short forward draft, audit every prerequisite backward,
add missing producers or leave facts unresolved, then validate the acyclic DAG.
The human `plan.md` and imported `backchain/plan.md` must agree. Include Review
Coverage and map expected cases, checks, documentation, preparation, deployment,
and readiness to concrete outputs.

`prepare` appears only for authorized `outer-before` preparation. Other
preparation belongs in explicit dependency-ordered DAG steps, or it is `none`.
Preflight's readiness assessment is not permission to make unapproved
environment changes.

Before the first step is allocated, the finalized spec's Git baseline and
product-tree fingerprint must still match. Outer-before preparation may ready
the environment; changes to product files belong in explicit DAG steps. Later
authorized execution does not have to keep the historical planning HEAD current.

For acceptance that depends on a real deployment, plan authorized deployment or
readiness and dependent checks **before** outer `quality`. An `outer-loop`
publication can add a final delivery smoke check, but it cannot retroactively
satisfy deployment-dependent acceptance. A `dag` publication is a normal,
ordered implementation step; it does not create the outer `publish` stage.

### P4 — Select, plan, and implement one ready step

ShipLoop schedules one ready DAG step at a time and allocates its isolated
worktree and branch. Work there, not in the session checkout. Scheduling opens
`step-plan`; it does not authorize a source edit. The initial execution-plan
loop is:

```mermaid
flowchart TD
    S[Schedule ready step] --> D[Draft step plan]
    D --> R[Review and revise actual step context]
    R --> V[Lint and test plan artifact]
    V --> C[Audit-only plan commit]
    C --> G{Two trivial passes and no gaps?}
    G -->|No| R
    G -->|Yes| F[Fresh plan check and finalize]
    F --> I[Implement exact checked plan]
```

`step-plan-review` reads bounded `step-context`, `step-plan`, and current
`iteration` state, then current Git history. It inspects the actual worktree's
relevant code, interfaces, call sites, tests, configuration, documentation,
and diff; the frozen environment plus current non-secret observations; and
direct suppliers and consumers. Its full rubric asks about scope, current
implementation, environment, dependencies, flows, edge conditions,
second-order effects, implicit requirements, test strategy, and documentation.
The review persists compact evidence references instead of relying on the LLM's
memory or dumping raw source into the run. If audit-only plan commits fill the
normal history window, it also uses a scoped path/symbol investigation to
inspect the relevant older implementation or decision commit.

Each pass follows `step-plan-review → step-plan-revise → step-plan-verify →
step-plan-commit`. A material finding/revision resets the streak; the
incorporated continuation policy permits fresh finalization only after two
unique checked/audited trivial passes, all trivial fixes applied, and no open
findings. `step-plan-finalize` releases only the exact freshly checked plan to
`implement`. The audit commits preserve the product tree and do not count as
Improve iterations or replace the later primary step commit.

Implement only the declared `produces` after that finalization, update relevant
tests and documentation, lint after production edits, and run `verify` with an
explicit manifest. The script retains command logs, before/after fingerprints,
and failed attempts; it rejects non-zero, timed-out, stale, or changed-tree
evidence. It does not decide whether the selected tests actually prove the
intended behavior. A passing initial implementation starts P5; it is not
permission to merge.

### P5 — Improve repeatedly, learn, and merge

One Improve iteration is `review` through `carry-forward` and `commit`. Each
iteration has its own recorded history review, findings, a separately converged
post-review plan, application, fresh checks, current knowledge checkpoint, and
primary learning commit. Nested plan passes are evidence for the next edit; they
do not count as Improve iterations.

```mermaid
flowchart TD
    I1["5.1: Read knowledge, Git history, and research assessment"] --> I2["5.2: Draft Improve plan"]
    I2 --> I3["5.3: Converge nested Improve plan"]
    I3 --> I4["5.4: Apply finalized fixes and test changes"]
    I4 --> I5["5.5: Verify lint and required tests"]
    I5 -->|Failure or stale evidence| F["5.5a: Fix and rerun checks"]
    F --> I5
    F -.->|Plan invalid; repair| I1
    I5 -->|Passing evidence| I6["5.6: Carry-forward checkpoint"]
    I6 -->|Informational| I7["5.7: Record primary learning commit"]
    I6 -->|Current-step repair| I1
    I6 -->|Pending replan| P["Retain obligation for post-inner mapping"]
    P --> I7
    I6 -->|Pause| B["Record blocker and pause"]
    B -->|No-contract-change resolution| I6
    I7 --> G{"Two consecutive trivial-only iterations?"}
    G -->|No| I1
    G -->|Yes| I8["5.8: Fresh final verification"]
    I8 -->|Pass| I9["5.9: Broader-plan review"]
    I9 --> I10["5.10: Local merge"]
```

Before completing `review`, fully page the bounded `knowledge` selection and
run `history`; inspect the full bodies for the latest ten commits (or all
available), one body at a time when needed. If audit-only plan commits dominate
that window, also inspect the relevant older implementation or decision commit
through a scoped path/symbol investigation. The review result binds the
knowledge revision, digest, and scope it read. It also records the structured
`research_assessment` disposition (`not-needed`, `resolved`, `required`, or
`blocked`) with its summary, safe evidence references, and questions. A
non-`not-needed` assessment, including `resolved`, is material and resets the
streak. `required` or `blocked` cannot finish an Improve cycle; a prior required
assessment needs a resolved assessment in `improve-apply` that retains its
required/blocked question strings. `resolved` records investigation completed in
this pass; a later unchanged pass uses `not-needed` rather than repeating it.
Review code, tests, regressions, expected-versus-observed
cases, selected surfaces, changed function contracts, product README accuracy,
and prior learnings. Missing relevant tests or materially misleading
documentation are material findings. See
[later research discoveries](references/research-loop.md#later-discoveries) for
the route rather than silently rewriting a planning baseline.

At `improve-plan`, draft a plan that addresses every finding with fixes, test
work, documentation work or an explicit no-change reason, and prevention. It
first reads the `enclosing_review` block within the `step-context` section,
which projects the enclosing product review with stable `PARENT-…` finding
IDs. The draft must explicitly retain every printed parent ID. That is a
coverage proof for the plan—not a
claim that a product finding is fixed before application. It then enters the
nested plan loop:

```text
improve-plan → step-plan-review → step-plan-revise → step-plan-verify
→ step-plan-commit → (another review or step-plan-finalize) → improve-apply
```

Every nested review repeats the ten-dimensional execution-plan rubric against
the current worktree and current environment/dependency evidence. It records
stable findings, compact `context_evidence`, current knowledge binding, and
history before revision. It runs a plan-artifact lint/test manifest with exact
acceptance `step plan`, then makes a verbose audit-only commit. Only two
consecutive trivial-only nested passes, no open findings, and a fresh final
check release `improve-apply`. The later primary Improve commit remains
mandatory. On this route, ShipLoop carries deduplicated nested review/revise
learnings into the enclosing iteration so that commit preserves both the plan
investigation and the actual code/test learnings.

At `improve-apply`, make the finalized changes without weakening expectations
just to obtain green. At `verify`, run fresh lint and required tests. A passing
local result is evidence only for that local run; it does not prove a remote,
deployed, or external effect.

For an ordinary failed or stale check, make the already-authorized correction,
then rerun lint and the required tests. If that result invalidates the finalized
plan rather than merely needing a check retry, use `repair` and return to
`review`; do not jump back into an older nested plan pass.

Before `commit`, `carry-forward` is mandatory. It records either explicit
`discoveries: []` or bounded non-secret discoveries in the current knowledge
ledger, without changing the approved environment, behavior, specification,
lifecycle, or DAG. `informational` observations can continue; a
`current-step-repair` returns to review, `pending-replan` retains a durable
obligation for mandatory post-inner mapping, and `pause` records a blocker that
`resume` cannot bypass. Only a later `no-contract-change` result resolution can
clear a false alarm or clarification. A current-step repair must scope exactly
the active step; future/completed/frozen impacts use pending replan or pause.
For a `research`-domain pending obligation, post-inner must schedule an explicit
`activity: research` producer before every affected consumer; mapping means
scheduled work, not a solved research question.
The checkpoint's nonempty `learnings` string is copied verbatim into the primary
commit. See
[Carry-forward checkpoint](references/carry-forward.md) for the exact schema
and impact routes.

At `commit`, create the distinct primary commit on the step branch with
`Review:`, `Changes:`, `Validation:`, `Key learnings:`, and the exact
`ShipLoop-Iteration:` trailer. Its body must include the ordinary review,
deduplicated nested Improve-plan review/revise, application, and carry-forward
learnings verbatim. An honest audit-only empty commit is allowed when it
contains concrete evidence.

Two consecutive fully recorded trivial-only iterations are necessary, not
sufficient. Material findings, material application, or late edits while
obtaining green reset the streak. `final-verify` is a separate fresh gate.
`post-inner` records whether only pending plan steps need revision, reviews the
generic ShipLoop proposal journal, and, when obligations exist, provides
`pending_obligation_map` entries with nonempty changed or newly added pending
step IDs. Those entries schedule future work; they do not prove it fixed or
verified. `merge` is local only: it is not a push, publication, or proof of
remote delivery.

**Current repair boundary.** Before a merge intent has started, a real defect
found after an iteration, final verification, or post-inner review can use
`repair` to record the reason, reset convergence, and return to `review`. Once
the merge intent is recorded, current `repair` rejects the request. Inspect Git
and reconcile or retry the merge as appropriate; do not promise that
repair-after-merge-intent works. This is one of the known limitations below.

### P6 — Review the whole product

P6 evaluates the integrated product, not merely the last step's checks. Defects
must return through a corrective pending DAG step and the ordinary P4–P5 loop.

```mermaid
flowchart TD
    C1["6.1: Review Coverage"] --> C2["6.2: Whole-product acceptance and quality"]
    C1 -->|Product defect| R["Replan corrective pending step"]
    C2 -->|Product defect| R
    R --> W["P4-P5: Implement, Improve, verify, and merge"]
    W --> C1
    C2 -->|Acceptance checks pass| D["P7: Authorized delivery and handoff"]
```

At `coverage`, complete the plan-bound Review Coverage activity and retain its
actual tracked clean ledger, or the pre-existing explicit plan waiver. At
`quality`, run fresh whole-product lint and acceptance/integration tests mapped
to every exact `lifecycle.acceptance` string. When `quality: false`, the extra
semantic-review field is omitted; acceptance and integration checks remain
required.

Reassess browser, service, and API views for the whole product. Required failed,
blocked, or unrun checks remain unfinished. The required practice is to use
`replan` at `coverage` or `quality` to add a corrective pending step, not to
patch the outer checkout around P5. Current enforcement has a known gap, so the
host must uphold this discipline.

### P7 — Deliver if authorized and hand off

When `publish: outer-loop`, `publish` occurs after `quality` only with user
authorization. Inspect the existing delivery before retrying an uncertain
external operation. Record the artifact, actual entrypoint verification, tested
environment, and evidence; a local green suite cannot prove publication.

When `publish: dag`, publication is an explicitly ordered P4–P5 step. When
`publish: none`, ShipLoop proceeds from `quality` to `handoff` and does not
authorize delivery. The current `publish: none` validation gap is listed below,
so follow the frozen lifecycle and user authority even if an inconsistent plan
appears to validate.

At `handoff`, record checked acceptance, actual delivery facts, limitations,
unresolved concerns, and the prioritized generic ShipLoop proposal list. Use an
explicit `[]` journal after a no-new-proposals review. A handoff is an honest
report of evidence and uncertainty, not an inference from a green local suite.

## Requirements modeling and traceability

Use the [Discovery and research](references/behavioral-requirements.md#discovery-and-research),
[Behavior model](references/behavioral-requirements.md#behavior-model), and
[Traceability and review](references/behavioral-requirements.md#traceability-and-review)
sections together:

```mermaid
flowchart TD
    P["Prompt"] --> R["Research"]
    R --> M["Flows and states"]
    M --> C["Test cases"]
    C --> E["Evidence"]
    E --> L["Learnings"]
```

1. During P2, assign stable `R-` IDs to atomic requested behavior and research
   deeply where it is uncertain or consequential. Trace an outcome forward from
   its trigger through callers, public boundaries, state writes, and external
   effects, then backward through its prerequisites. Read relevant
   implementation, tests, documentation, history, and primary platform
   contracts; distinguish observed facts, inferences, proposals, and unknowns.
2. `behavior` drafts the model. Use `F-` IDs for required flows and `T-` IDs
   for applicable state transitions. Cover required in-scope valid **and**
   invalid events, guards, permissions, state ownership, invariants, outputs,
   errors, and effects. Assess retry/idempotency, cancellation, timeout,
   partial failure, compensation, concurrency, stale callbacks, and recovery
   when the product makes them relevant; record a justified exclusion rather
   than filling a generic checklist.
3. The behavior loop reviews that candidate against its rubric until it has two
   complete trivial-only passes, no open findings, fresh planning evidence, and
   its final audit history. A material unresolved policy blocks
   `behavior-finalize` and therefore `spec`; do not invent a rule for a
   cancellation/completion race, ownership conflict, permission, or recovery
   boundary merely to mark `checkable: true`.
4. During P3, the spec loop maps the frozen `R-/F-/T-` model to acceptance
   criteria, case IDs, DAG outputs, environments, and checks before sequence.
   During P4–P7, retain the link from requirement to expected outcome, selected
   test, observation, evidence, and any remaining limitation.

Product diagrams belong to the behavior model. A product sequence diagram says
which actor sends which request and what the product observes. A product state
diagram says which product states and transitions are valid. By contrast,
ShipLoop's `phase/stage` cursor controls the delivery harness, while the DAG
orders implementation work. They may reference each other, but none substitutes
for another.

A compact generic trace is enough when the executable test already shows the
detail:

| Trace item | Example |
|---|---|
| Requirement and model | `R-07: an invalid update from an active record is rejected and the record remains unchanged.` `F-07` is the exposed update flow; `T-07` records the guarded rejection, unchanged-state invariant, and caller-visible error. |
| Case design | `TC-07: given an active record, submit an invalid update through the real exposed boundary; expect the defined validation error and unchanged stored state.` |
| Planning gate | The behavior/spec planning loop checks that the modeled `T-07` and `TC-07` links remain complete; that is planning-artifact evidence, not a claim the future product test passed. |
| Planned work | The implementation step produces the `T-07` validation contract and `TC-07`; the sequence places any service readiness before the selected test. |
| Observation | The later `verify` result links `R-07/F-07/T-07` and `TC-07`, runner/environment, checked revision, actual status, and retained evidence. Until then it is `not-run`, not passed. |

This is a modeling and traceability example, not a new universal schema. Keep
case intent compact, use the existing result fields, and leave detailed
assertions in the executable test where they belong.

## Execution-plan, per-step evidence, tests, and documentation

The execution-plan loop turns a ready DAG step or Improve finding into an
ordered, checkable edit/test/documentation plan before product source changes.
It records target symbols/interfaces, prerequisites, expected outcomes, case
IDs, relevant browser/service/API coverage, documentation decisions, risk
controls, and revalidation triggers. Its `planning-verify` evidence validates
that plan artifact with exact acceptance `step plan`; it never substitutes for
the later source lint/tests or for a live deployment observation.

For universal objective candidates, any exact persisted-byte rewrite—including
whitespace-only editing—is conservatively material. Only retaining the exact
candidate can count as a trivial Apply. This can create extra passes because
ShipLoop has no semantic-equivalence oracle; it is a deliberate quality guard,
not a claim that every byte edit changes product behavior. Specialized
research/behavior/spec loops continue to use their own rubric-based materiality
rules.

### Authoring a valid per-step Ready/Done contract

New runs require `contract_version: 1`; legacy work receives no retrospective
Ready/Done proof. In this version, every DAG step must author a
`contract` object with exactly `objective`, `ready`, `done`, `tests`, and
`documentation`. Its `objective` exactly equals the step `statement`; stable
IDs use `R-`, `D-`, `T-`, and `DOC-`; and every exact `produces` value appears
in both `done[].produces` and `tests[].produces`. Ready rows contain
`id`, `condition`, and `evidence_method`; done rows also declare `produces` and
`completion: "integrated"|"deployed"`; test rows declare `produces`, an exact
`expected_outcome`, `surface`, and `evidence_method`; documentation rows contain
`id`, `condition`, and `evidence_method` (an unchanged claim must say why).

This authored contract is not the later evidence payload. Before source edits,
public `ready_evidence` has only `ready` rows. After verification, public
`done_evidence` has only `done`, `tests`, and `documentation` rows. The script
keeps selected head, environment, artifact, contract, and check identities in
its private durable envelope. See the complete
[authoring example](references/activities/plan.md#versioned-per-step-contract)
and [evidence boundary](references/action-protocol.md#per-step-ready-and-done-contract).

The host selects tests by the changed behavior, surface, and risk. Browser,
service, and API checks overlap; they are not a mandatory three-level ladder.
Record each as selected, not applicable with a reason, or required but blocked.
A health check proves readiness, not necessarily the behavior or side effect at
risk.

Every implementation and Improve verification has a concrete lint check and at
least one test check. Each exact `produces` string belongs in a test check's
`acceptance` list:

````markdown
```shiploop-state
{
  "checks": [
    {
      "id": "lint",
      "kind": "lint",
      "argv": ["npm", "run", "lint"],
      "acceptance": []
    },
    {
      "id": "unit",
      "kind": "test",
      "argv": ["npm", "test", "--", "widget"],
      "acceptance": ["src/widget.ts", "widget behavior"]
    }
  ]
}
```
````

`argv` is an argument list, never shell prose. If a later iteration changes
coverage, use `verify --reason` to record why. Failed attempts remain in
`check-attempts/`; do not erase them to make a final pass appear first-try.

Use the existing result `body`, `plan`, `test_review`, `test_changes`,
`learnings`, and `summary` fields to link cases, documentation decisions, and
evidence. Do not create a parallel case-result sidecar. Expected outcomes and
actual observations are separate: a required unavailable check is blocked, not
`N/A` or passed by prose.

Testing and documentation are duties inside the current stages, not a late
separate phase:

| Workflow point | Test responsibility | Documentation responsibility |
|---|---|---|
| P2 survey/research/behavior loops | Identify relevant environments and observable expected outcomes; verify research question/source integrity and review the model's case mapping on every behavior pass. | Inspect conventions and identify product or interface guidance that will need change. |
| P3 spec loop/sequence | Confirm acceptance/case mapping during spec convergence, then map stable cases and checks to exact outputs; order fixtures, readiness, and deployment dependencies. | Plan concise function/interface contracts, case guidance, and relevant README changes. |
| P4 execution plan and implementation | Before source edits, map outputs/transitions to stable cases, expected outcomes, surfaces, fixtures/readiness, and plan-artifact checks; after finalization, add executable success, invalid, boundary, and regression coverage when relevant. | Before source edits, name the affected non-obvious contracts, README instructions, examples, and links; update them in the worktree before source checks, or explain why unchanged. |
| P5 Improve | Converge the post-review plan, then compare expected and observed outcomes, reassess coverage, and rerun current checks. | Converge documentation work with the Improve plan; review README and contracts each iteration, update them or record a no-change reason. |
| P6–P7 outer closure | Check whole-product behavior in the relevant actual environment. | Hand off usage, interface references, tested outcomes, and operational limitations. |

The [testing and documentation contract](references/testing-and-documentation.md)
defines the compact case record, surface decisions, product README review,
iteration duties, and deployment/handoff rules. Read only the section named by
the packet. Product documentation belongs in the product worktree and Git, not
in ShipLoop session state.

## Ownership, context, and recovery

The script, Markdown files, Git, check tools, and host have different jobs:

```mermaid
sequenceDiagram
    participant H as Host and fresh LLM context
    participant S as ShipLoop scripts
    participant M as Authoritative Markdown
    participant G as Git and check tools
    H->>S: next with run locator
    S->>M: Load and recover durable state
    S-->>H: Current action and bounded pointers
    H->>S: Retrieve relevant context section
    S-->>H: Current facts and artifact excerpts
    H->>G: Perform scoped work and required checks
    H->>S: complete exact action with Markdown result
    S->>M: Validate and persist accepted transition
    S-->>H: Next action or unfinished blocker
```

| Authority | Owns | Does not prove |
|---|---|---|
| Scripts and Markdown | Current phase/stage, action identity, planning candidates and finding ledgers, accepted results, current knowledge overlay, plan, receipts, evidence references, and generic journal. | Conversation recollection or semantic correctness. |
| Git | Product history, step branches, local merge ancestry, and per-iteration learning commits. | Remote publication or external acceptance. |
| Check tools and retained logs | Command execution and observable pass/fail evidence in a specific environment. | Complete test adequacy or every possible defect. |
| Host | Scoped changes, semantic review, test adequacy, evidence interpretation, and external verification. | A deterministic correctness oracle. |

One context only needs to survive until its required facts are durable. The next
context should assume that prior conversation is gone:

```mermaid
flowchart TD
    A["Accepted action writes durable Markdown"] --> B["Context can be discarded"]
    B --> C["Fresh host runs next"]
    C --> D["Read prompt, planning, iteration, and phase-selected candidate"]
    D --> E["Resume the exact printed action"]
    E --> A
    X["Interrupted work or lost context"] --> C
```

Current behavior: `next` reconstructs the action from Markdown, and `context`
retrieves bounded `prompt`, `step`, `iteration`, `knowledge`, `behavior`,
`spec-draft`, `lifecycle-draft`, `planning`, `spec`, `environment`, `plan`,
`lifecycle`, `journal`, `approach`, `research`, `research-evidence`,
`step-context`, or `step-plan` sections. The limit is characters, not a
guarantee of model tokens. A research cold context reads its report and evidence
candidates, planning receipt, and current iteration rather than every historical
pass. An execution-plan cold context reads the selected step's compact
implementation/environment/dependency evidence, current candidate/ledger, and
current nested pass—not archived plan passes or an assumed prior conversation.
`context environment` keeps the
frozen baseline visible and labels the current knowledge overlay as
authoritative state for host-reported observations but not authority to change
that baseline. After a cold start during execution, read the scoped
`knowledge` selection before the current `iteration`; it includes active-step
and `all` entries plus every open or scheduled obligation and open blocker,
rather than every historical checkpoint. Do not load every old pass: Markdown
receipts link completed iterations while the packet gives the current bounded
slice. If interrupted halfway through an iteration, inspect uncommitted work and
resume the persisted action; the interruption earns no clean iteration and
invents no commit.

Each multi-file state update uses a write-ahead `transaction.md` and the next
locked command rolls it forward. Do not delete it or edit state by hand to
bypass a gate. Use `pause` for a recoverable user/external blocker, `resume`
after resolution, and `halt` for a terminal unfinished exit. A carry-forward
blocker remains active after `resume`: only a later checkpoint with a
`no-contract-change` resolution can clear a false alarm or clarification, and
no resolution can rewrite an approved contract. Before any step receipt or active
work exists, `revisit --to survey|research|behavior|spec` archives superseded
planning inputs instead of erasing evidence: `research` preserves the surveyed
environment while archiving the research pair, behavior/spec/sequence downstream
artifacts, and their planning receipts/certificates/bindings; `behavior` and
`spec` retain their accepted research proof; `survey` archives all planning,
including the environment contract. Each target then issues a new action rather
than reusing an archived clean pass.

For a legacy run with `state.json` but no `state.md`, use `migrate` explicitly.
It archives only known legacy ShipLoop files, preserves code/branches/worktrees,
marks the planning protocol while restarting at preflight, and therefore reaches
the new planning checkpoints normally. It is not a way to resurrect deleted
Markdown authority or initialize a normal new run.

### Earlier Markdown runs and planning-protocol upgrade

New runs carry `planning_protocol_version: 2`. A pre-v2 Markdown run (including
a missing marker) is deliberately fail-closed: `next`, `status`, and bounded
`context` are diagnostic, while `pause`, `resume`, and `halt` remain lifecycle
controls. Other workflow mutation is blocked until the packet's exact command:

```sh
shiploop planning-upgrade --run-dir RUN --action CURRENT_ACTION
```

The upgrade requires that exact action, no `steps/*.md` receipt, and no active
step. Otherwise it refuses all old executed runs and requires a fresh run; it
preserves the existing work rather than deleting, replaying, or certifying
execution. With no step receipt, it archives `research.md`,
`research-evidence.md`, every planning artifact, and downstream contracts under
`planning-history/<action>/upgrade`, clears research/behavior/spec/lifecycle/plan
hashes, increments the planning epoch, and records the v2 marker. The archive is
evidence of earlier planning, **not** proof that its research, behavior, or
specification converged.

An old cursor can remain at `preflight`, `approach`, `survey`, or `research` when
that earlier gate is still present; a preserved research cursor gets fresh
candidates because its old pair was archived. Any later cursor restarts at
`research` when `environment.md` exists, or `survey` when it does not. It
preserves product code, branches, and worktrees in every case; no upgrade can be
used to skip the mandatory research, behavior, or specification loops.

### Existing runs and the execution-plan marker

New runs also carry `step_planning_protocol_version: 1`. A v3 run missing that
marker does not gain a retrospective certificate for prior direct implementation
or an already-written Improve draft. At the safe `schedule`, `implement`, or
`improve-plan` boundary, ShipLoop records the marker and sends the next product
edit through the appropriate nested plan loop. If the active action is later in
execution, use the existing `repair` route to record the interrupted work and
restart review; do not edit Markdown state to pretend the plan gate ran.
Read-only `status`, `context`, and `plan-status` inspection remain available.

## Current limitations and proposed safeguards

### Three known current implementation gaps

The diagrams and required operating discipline do not claim that every
state-machine gate is watertight. These defects remain outstanding:

| Gap | Affected boundary | Operator consequence |
|---|---|---|
| Rejected merge intent can block the documented repair route. | P5 `merge` / `repair` | Once merge intent starts, inspect Git and reconcile the merge; current `repair` is intentionally unavailable there. |
| A full Git commit body is not bounded by the history item count. | P2–P3 planning reviews, P5 `review`, and small-context retrieval | Retrieve bodies one at a time and keep context pressure visible. |
| Legacy migration does not reconstruct the original prompt file. | Cold-start recovery after migration | Recover with available durable artifacts and resolve missing intent before relying on a cold restart. |

The final-verify convergence binding now rejects post-convergence product edits,
and outer closure now requires a clean checkout descending from every integrated
step receipt (apart from a certified Review Coverage ledger). Lifecycle
validation also rejects a marked DAG step when its activity is `none`, or is
placed outside the DAG (`preparation: outer-before`, `publish: outer-loop`).
These safeguards do not add a semantic correctness
oracle; the remaining limits above still require careful host judgment.

### Carry-forward is current; unrestricted rebasing is deferred

The `verify → carry-forward → commit` checkpoint and bounded current knowledge
overlay are current behavior. They preserve non-secret operational learning,
pending obligations, and safe pause resolution while leaving the approved
baseline unchanged. Unrestricted environment or requirements rebasing,
generalized credential detail, and arbitrary-stage observation remain deferred;
an incompatible discovery pauses for direction and a real contract change needs
a new explicitly scoped run.

### Current sequence and outer objective convergence

The mandatory research, behavior, specification, execution-plan, and generic
objective loops are current. `sequence`, authorized preparation, post-inner,
coverage, and quality retain a Markdown candidate, stable findings, bound
context, candidate-bound checks, full-body Git-history evidence, audit-only
learning commits, and a certificate after two trivial verified passes and a
fresh final check.

```mermaid
flowchart TD
    Q1["Load the current sequence or outer candidate"] --> Q2["Review with fixed rubric and findings"]
    Q2 --> Q3["Plan and apply justified improvements"]
    Q3 --> Q4["Verify criteria and applicable checks"]
    Q4 -->|Failure| Q3
    Q4 -->|Pass| Q5["Persist evidence and cycle outcome"]
    Q5 --> Q6{"Two trivial-only cycles and no open material findings?"}
    Q6 -->|No| Q1
    Q6 -->|Yes| Q7["Fresh final check and apply exact candidate once"]
```

Objective certificates bind the candidate, ledger, context, final check and
audit history, so a changed artifact cannot inherit a clean result. A material
finding or candidate rewrite resets the trivial streak; no cycle limit or LLM
completion claim is success. New product work found by coverage or quality is
corrective pending DAG work through `replan`, not an outer-checkout patch.

This convergence discipline still does not prove semantic correctness, test
adequacy, live external state, or user acceptance. The host must evaluate those
questions and record honest limitations; the generic ShipLoop journal remains
proposal-only and does not modify the harness.

## Command reference

The compact stdout packet is authoritative for the current action. The command
surface is:

```sh
shiploop init     --repo REPO [--run-dir RUN] --prompt TEXT
shiploop next     --run-dir RUN
shiploop status   --run-dir RUN
shiploop report   --run-dir RUN
shiploop plan-status --run-dir RUN --loop STEP_PLAN_LOOP
shiploop context  --run-dir RUN --section SECTION --offset 0 --limit 4000 [--digest SHA256]
shiploop complete --run-dir RUN --action ACTION --result RESULT.md
shiploop verify   --run-dir RUN --action ACTION --manifest CHECKS.md [--reason TEXT]
shiploop planning-verify  --run-dir RUN --action ACTION --manifest CHECKS.md [--reason TEXT] [--timeout N]
shiploop planning-upgrade --run-dir RUN --action ACTION
shiploop history  --run-dir RUN --action ACTION --limit 1 --skip N [--full]
shiploop journal  --run-dir RUN --action ACTION --result PROPOSALS.md
shiploop repair   --run-dir RUN --action ACTION --reason TEXT
shiploop replan   --run-dir RUN --action ACTION --result CORRECTIVE_PLAN.md
shiploop revisit  --run-dir RUN --action ACTION --to survey|research|behavior|spec --reason TEXT
shiploop pause    --run-dir RUN --reason TEXT
shiploop resume   --run-dir RUN
shiploop halt     --run-dir RUN --reason TEXT
shiploop migrate  --run-dir RUN
```

Use absolute paths for `--result` and `--manifest` when the working directory is
ambiguous. `verify`, `planning-verify`, `history`, `journal`, `repair`,
`replan`, `revisit`, and `planning-upgrade` require the exact printed action
when that command is valid for the current stage. Do not use old
inferred-completion commands, bare `complete`, or a hand-constructed stage
transition. `plan-status` is read-only: it can confirm only an exact finalized
execution-plan handoff before its target product action begins; it does not
advance work or bless drift.

`report` performs presentation-only regeneration for an already terminal run.
It rewrites the derived [terminal report](references/report.md) and its
integrity metadata without changing the terminal outcome, product worktree, or
authoritative Markdown evidence.

## Related references

- [Action protocol](references/action-protocol.md): action IDs, result fields,
  command semantics, evidence, convergence, corrective replan, and migration.
- [Survey guide](references/survey.md) and
  [validate-spec activity](references/activities/validate-spec.md): environment,
  writer, routing, UI, and client–service constraints.
- [Planning activity](references/activities/plan.md): one validated DAG,
  prerequisite audit, lifecycle placement, and Review Coverage.
- [Planning convergence loops](references/planning-loops.md): mandatory
  research/behavior/spec candidate loops, rubric/finding evidence, planning
  checks, audit-only commits, finalization, and upgrade behavior.
- [Execution-plan convergence](references/execution-planning.md): current
  nested planning gate before initial source edits and Improve applications,
  its ten-dimensional review, cold-context packets, audit passes, and
  incorporated until-loop policy.
- [Universal substantive-objective loop](references/objective-loops.md): the
  ten-history, two-trivial-pass refinement applied to substantive outer stages.
- [Research loop](references/research-loop.md#draft): typed research candidate
  schema; see its [review](references/research-loop.md#review),
  [freshness](references/research-loop.md#evidence-and-freshness), and
  [later-discovery](references/research-loop.md#later-discoveries) contracts.
- [Implementation activity](references/activities/implement.md): worktree,
  lint, tests, evidence, and commit discipline.
- [Carry-forward checkpoint](references/carry-forward.md): current knowledge
  ledger, bounded cold-start retrieval, impact routes, and safe observations.
- [Testing and documentation contract](references/testing-and-documentation.md):
  case records, surface selection, compact contracts, README review, and
  deployment evidence.
- [Behavioral requirements contract](references/behavioral-requirements.md):
  evidence-led discovery, product flows and states, `R-/F-/T-` traceability,
  breadth review, and model-to-case links.
- [State-file guide](references/state-files.md): durable run files and recovery
  inspection.
- [Offline terminal report](references/report.md): generated `report.html`, its
  integrity binding, evidence boundary, and regeneration behavior.
- [Host matrix](references/host-matrix.md): host-specific invocation
  constraints; it is a reference, not mutable run state.

If this guide, a historical run, and the current packet differ, follow the
packet and [action protocol](references/action-protocol.md), preserve the
evidence, and record the documentation issue as a generic ShipLoop proposal.
