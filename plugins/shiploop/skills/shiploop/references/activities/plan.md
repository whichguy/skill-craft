# Native bounded dependency planning

Sequence planning is native ShipLoop work, not a required external Backchain
skill or template load. It selectively adapts Backchain source prompts reviewed
at commit `8278e27` through
[Backchain planning in ShipLoop](../backchain-planning.md#owner-binding). It
does not invoke an external runtime or import raw Backchain JSON/schema, model,
benchmark, or evaluator. Make a short forward draft, audit every step backwards,
then import only a validated compatible DAG.

During execution, the [carry-forward checkpoint](../carry-forward.md) may expose
new prerequisites or invalidate assumptions used by pending steps. Treat the
frozen plan as a versioned approved baseline: change it only through the existing
validated pending-only revision path. Map each outstanding knowledge obligation
to the affected pending work; an unrelated plan edit is not resolution. Preserve
running/completed receipts and pause for incompatible scope or permission changes.

Initial sequencing consumes a converged research baseline, not merely an existing
`research.md`. If a new question changes that baseline before any step receipt,
use `revisit --to research` and reconverge dependent planning. For later compatible
research, use the [research follow-up contract](../research-loop.md#later-discoveries).
An `activity: research` step must produce a checkable report/decision artifact;
every affected consumer must depend on it, directly or transitively. A report
scheduled after its consumers cannot satisfy their knowledge prerequisite.

Sequence is not a substitute for the later per-step plan loop. It establishes
the dependency graph and frozen delivery boundary; each selected step still
converges an execution plan against the actual worktree before the first source
edit or any Improve application. See
[Execution-plan convergence](../execution-planning.md).

## Sequence result

Provide summary, concise plan, nonempty dependency_review string, and exactly
one of dag or dag_file. Plan repeats the exact spec done_sentence, has Review
Coverage, and links planned test/documentation work without adding result
fields. dependency_review records the forward draft, backwards prerequisites,
supplier/initial-state source, missing producers, unresolved facts, and cycle
check; it may point to a durable draft.

dag is the compatible object. dag_file is an absolute Markdown draft with one
shiploop-state object fence; raw JSON is refused. A draft is not authoritative
until import writes backchain/plan.md, and an edit after resolution is a
conflicting replay.

### Versioned per-step contract

For a contract-enabled sequence, set the DAG's top-level
`contract_version: 1`. Every step then has a `contract` with exactly
`objective`, `ready`, `done`, `tests`, and `documentation`; `objective` exactly
equals that step's `statement`. Criterion IDs are globally unique and use
`R-`, `D-`, `T-`, and `DOC-` prefixes. Every exact step `produces` value must
be covered by both a `done[].produces` entry and a `tests[].produces` entry.
Use `integrated` or `deployed` explicitly for `done[].completion`; deployment
is still host-reported rather than a local success claim.

```json
{
  "contract_version": 1,
  "steps": [{
    "id": "S1", "statement": "The checked widget outcome is available",
    "produces": ["checked widget outcome"], "inputs": [], "origin": "seed",
    "prompt": "<stored bounded prompt>",
    "contract": {
      "objective": "The checked widget outcome is available",
      "ready": [{"id":"R-WIDGET-ENV","condition":"The selected test environment is available","evidence_method":"planning verify"}],
      "done": [{"id":"D-WIDGET-OUTCOME","condition":"The widget exposes the declared outcome","produces":["checked widget outcome"],"evidence_method":"accepted test","completion":"integrated"}],
      "tests": [{"id":"T-WIDGET-OUTCOME","produces":["checked widget outcome"],"expected_outcome":"The declared observable outcome occurs","surface":"selected component or API surface","evidence_method":"accepted test"}],
      "documentation": [{"id":"DOC-WIDGET-README","condition":"README usage is updated or unchanged because no user-facing instruction changed","evidence_method":"documentation check"}]
    }
  }]
}
```

This is authoring schema, not a result payload. Later public
`ready_evidence` is only `{ready:[...]}` and public `done_evidence` is only
`{done:[...],tests:[...],documentation:[...]}`; the script binds Git,
environment, artifact, and check identities internally. See
[Per-step Ready and Done contract](../action-protocol.md#per-step-ready-and-done-contract).

~~~json
{
  "summary": "Sequence audited before import.",
  "plan": "done_sentence: <exact spec sentence>\n\n## Review Coverage\n<activity>",
  "dependency_review": "Forward S1; backwards inputs supplied by initial state; no cycle.",
  "dag_file": "/absolute/path/sequence-draft.md"
}
~~~

## Bounded method

1. Read the durable prompt, converged research/behavior/spec slices, current
   survey/environment contract, relevant Git history, and the actual existing
   implementation, interfaces, call sites, tests, configuration, and docs that
   a step would affect. Git explains prior decisions; it does not replace an
   inspection of the current tree or current environment.
   Always inspect README or record absence, follow applicable existing AGENTS.md,
   architecture/design/environment notes and local skill indexes. Use
   [baseline tests and migrations](../execution-planning.md#baseline-tests-and-migrations)
   to order prerequisite health checks, necessary repairs and small compatible
   data migrations. An intentionally failing target regression is not a foundation
   failure; unrelated defects do not automatically expand the assignment.
2. **Before drafting**, reread the original request and the approved
   `spec.md`/`lifecycle.md` acceptance and case requirements. Cover every
   required, negative, and conditional outcome, then map each independently
   checkable outcome to a planned observation. As the draft adds steps,
   record the mapping in the existing contract/case rows. This is the native
   representation of upstream goal needs and verification sinks, not a new goal
   catalog. Related assertions may share one coherent DAG step; divergent
   prerequisites or deliverables should not. See
   [outcomes](../backchain-planning.md#outcomes).
3. Record an initial fact only when the request or an actual inspection proves
   it. Then draft the smallest forward path of **postconditions** from those
   facts: `statement` and `produces` say what will be true, while the existing
   stored `prompt` holds tactics and authorized Tools. Keep the local microplan
   in the existing `plan`/`body` Markdown, not a new schema. See
   [sequence](../backchain-planning.md#sequence) and
   [step plans](../backchain-planning.md#step-plans).
4. For every draft step, including unchanged seeds, and every added or widened
   supplier, apply the complete
   **CLAIM / NEEDS / SUPPLY / PULL / RESOLVE** audit. SUPPLY inspects every
   relevant producer and established fact, not merely adjacent rows; PULL
   tests the committed consumers and can expose a supplier gap. Do not treat a
   tool, assumption, unanswered question, or a matching label as evidence. See
   [dependency audit](../backchain-planning.md#dependency-audit).
5. Resolve each need through inspectable evidence at the exact required layer
   and carrier. Give actual shared state one suitable direct supplier for its
   consumers, rather than an adjacency chain or arbitrary god-step. Retain
   safe unique IDs, exact need-to-producer links, consumer ordering,
   compatibility boundaries, shared-resource effects, and cycles; then make
   one forward check from established facts to the planned observations. Plan
   per-outcome verification in the existing contract/case rows, with the
   existing plan's evidence method, target, selector/command, and documentation
   check. See
   [replanning](../backchain-planning.md#replanning) for later facts.
6. Give every step concrete produces, a stored goal/until/Tools prompt, and a
   meaningful test plan for every produces value. Map stable case IDs to exact
   output or lifecycle-acceptance strings and plan selectors/commands and
   documentation checks through [Test cases](../testing-and-documentation.md#test-cases).
7. When a client will call a service, a step must produce the frozen
   invocation contract (visible operations plus client/HTML call conventions)
   before any step that authors a call site. See
   [Client–service invocation](../survey.md#clientservice-invocation).
8. Select local, browser, service, and API coverage from the actual risk and
   surface—not a mandatory ladder—and record target environment/readiness.
   A relevant required surface without access or readiness is a blocked
   dependency, not `N/A` or a pass; see
   [Surface selection](../testing-and-documentation.md#surface-selection).
9. When acceptance requires a real deployment, sequence authorized
   deployment/readiness and dependent checks as DAG producers/consumers before
   outer quality. An outer-loop publication is limited to final delivery-smoke
   evidence, not delayed acceptance.
10. Plan affected product README updates or a per-iteration unchanged rationale,
   concise public/non-obvious function contracts, runnable-example/link
   verification, and the associated product artifacts. Never plan ShipLoop
   session state into product documentation; see
   [Documentation](../testing-and-documentation.md#documentation).
11. Trace every required product flow and transition to implementing steps,
   case IDs and enduring model documentation. Audit missing/reversed
   prerequisites, negative/recovery paths, and important cross-step behavior
   using [Traceability and review](../behavioral-requirements.md#traceability-and-review).
   Product event order is not the same as the delivery DAG; keep both explicit.
12. Trace newly required environmental/best-practice questions to research
   producers and their affected consumers. Plan source/applicability/freshness
   evidence and report checks. Preserve the distinction between a research
   conclusion, a user policy decision and authorization for an external change.
   Include consequential upstream/downstream actors, storage and trust boundaries
   behind gateways, plus experiments that could change these decisions; use
   [recursive discovery](../research-loop.md#recursive-discovery-and-experiments).
   Plan reusable context capture and future skill readers when useful; do not
   create a skill or integration merely to fill a category.

Record only compact current-tree and environment evidence in the sequence
result—symbols, case IDs, test selectors, source references, or non-secret
probe records. The later step-plan loop uses that context as a starting point,
then re-inspects the selected worktree, supplier/consumer edges, state flows,
edge cases, second-order effects, and implicit requirements. Do not claim that
the sequence itself has completed the per-step two-trivial-pass convergence.

Seed prompts cite every environment reference and its exact mcp_considered
token. Preserve the exclusive writer in Use, every conflicting tool in Don't
use, and every reserved path in Don't write. UI work needs an early design
producer consumed by a later seed. Mark lifecycle DAG prep/publish activity.

Goal equals spec done_sentence; unresolved is empty before schedule. A step has
id, statement, origin, prompt, produces, and inputs:

~~~json
{"goal":"<exact spec done_sentence>","initial_state":["<established fact>"],
 "unresolved":[],"steps":[{"id":"S1","statement":"The exact checked outcome is available",
 "origin":"seed","produces":["<exact checked outcome>"],"inputs":[],
 "prompt":"/goal\nDo this activity until these conditions are met:\n- <exact checked outcome>\n\nTools:\nWatch with: <frozen mcp_considered>\nUse: <tool>\nDon't use: none\nDon't write: none\nAssume: <facts>"}]}
~~~

If the user explicitly requests an external planner, follow that choice; do
not silently substitute one. If the choice is unclear, pause for it. Its output
remains a non-authoritative Markdown draft and gets the same audit.
Post-inner/outer replan changes only pending steps; each corrective step runs
the full inner loop.
