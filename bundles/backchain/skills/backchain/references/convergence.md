# Backchain standalone Until Loop binding

Backchain uses the selected actual **Until Loop** card for repeated dependency planning.
It does not implement a counter, scheduler, state file, callback protocol, or terminal
transition. The selected card's package-relative ephemeral adapter is the sole CLI,
recovery, consecutive-trivial counter, and terminal authority.

## Binding marker and resolution

Every complete Backchain planning invocation carries this marker in the Until Loop child
request:

```text
Backchain standalone Until Loop binding: <binding-id>
```

Physically resolve and read the selected Until Loop `SKILL.md` and its package-relative
`references/runtime-ephemeral.md` in full, then resolve `scripts/until_loop_ephemeral.py`.
Record observed
absolute locators and selected-card identity in `context.resources`. Do not substitute an
ambient same-named runtime. If the selected card, adapter, Python, explicit plan candidate,
or required context resource is unavailable, return incomplete with recovery action; do
not start a substitute loop. No Git history prerequisite exists unless the planning task
itself requires repository evidence.

Before handoff, actually check each required input locator exists and read its intended
content. Until Loop's adapter reference belongs to the selected Until Loop root;
Backchain's binding is this `references/convergence.md`, not an invented Backchain
`references/runtime-ephemeral.md`. Mark future packet/receipt destinations as outputs
and verify their writable parent directories; their absence before creation is normal.

## Frozen plan-only child contract

Hand the loaded Until Loop card the following natural-language work and constraints.
That card interprets the contract, starts its own adapter, and is the sole CLI caller;
Backchain must not construct or replay callbacks itself. Supply one dependency-planning
work cycle, an exit condition
requiring two consecutive distinct complete trivial/no-change dependency reviews **and**
final candidate-specific domain evidence, a repeat condition covering useful authorized
planning repair or required distinct review, and `required_trivial_reviews: 2`. The child
scope includes only the plan artifact and permitted planning companions. It must retain:

- original request; sources with authority/currentness/identity; 42-lens resources;
  dependency neighborhood, evidence, and selected technical findings;
- caller action/action ID/owner/workflow-stage bindings and candidate input/output identity
  for `backchain-caller/v1`; and
- exact edit bounds and provisional/protected/running/completed items, plus `no commit`,
  `no push`, `no merge`, no project execution, and no broadened scope.

Before start, retain actual locators in `context.resources` for the parent request,
latest-packet output, exact parent return route, and terminal-receipt output. For a
standalone Backchain call, the return route is the requested plan/companion artifact or
host response destination; do not invent an outer CLI callback. Save full runtime stdout
packets at the declared locations. Recovery uses the issued `next_argv`; reporting uses
only the current packet's exact `done_argv`, through the selected Until Loop adapter.
The initial candidate/baseline,
authorized scope/bounds, original request, and governing source criteria are frozen. An
authorized in-scope repair, its output candidate identity, or newly gathered in-scope
evidence is recorded in the callback report/handoff and remains in the same run; a material
classification resets the runtime gate. Cancel and bind a new run only when an external or
unapproved candidate/baseline substitution, scope/bounds/request change, or newer
contradictory governing source changes the criteria. Do not carry a trivial-review state
across that changed binding.

Each Until Loop callback is one complete dependency-review/fix/check cycle. Read the
packaged `prompts/convergence-review.prompt.md` and perform its assessment for that
cycle, including actual reads of applicable or uncertain technical cards/interactions.
Retain the full-category applicability screen with inspected reasons (shared exclusions
may be grouped), specific graph/source findings, and actual check results in the review
evidence. Skipped required reads/checks make the cycle unresolved, even when no plan edit
was made. The cycle performs a
fresh backward trace from every requested outcome and verification sink, a forward walk of
suppliers/consumers/new branches, all-42-lens applicability screen, source and experiment
identity review, authorized repair, and appropriate checks. Source-aware work also uses `audit.prompt.md`
and one bounds-respecting `revise.prompt.md`. Do not recursively invoke whole Backchain or
Until Loop. Legacy elaboration still preserves inherited seed/null edges and `goal_needs`.

Before submitting each cycle's `done` report, retain its original review observations
in a stable, host-readable record; do not overwrite an earlier qualifying record.
Use existing host evidence or planning companions, not another loop state or counter.
Each rolling `handoff` carries exact record locators and observed record, candidate, and
context identities for the qualifying reviews since the run began, or since the latest
material or unresolved reset, whichever is later, plus that reset's record when applicable.
The records retain the
full applicability screen (grouped exclusions are allowed), required card/read locators,
graph findings, source/experiment dispositions, and actual checks. Identical findings
may result from fresh reviews; copied verdicts, different labels, or a count alone do
not establish that those distinct reviews occurred.

Classify obligation, supplier, edge, branch, ordering, verification, source, experiment,
or protected-bound changes as `non-trivial`, even if repaired. Only verified nonsemantic
presentation/no-change cycles are `trivial`; unknown impact is `unresolved`. Missing
normative sources, forbidden necessary repairs, stale identity, or architecture-determining
experiment outcomes are planning gaps. Known future external prerequisites may remain
execution blockers. A graph revision clears `parallel_groups` and leaves structural status
unknown until a deterministic receipt validates that exact output digest.

## Terminal evidence and recovery

Backchain reports converged planning only with both the exact selected Until Loop terminal
`complete` packet and candidate-specific domain evidence: final output identity, no planning
gaps, final source assessment when applicable, protected-bound disposition, and any claimed
deterministic validation receipt. The adapter validates callback shape and transitions, not
that semantic evidence is true.

The final handoff and `domain_evidence` must retain access to both original qualifying
review records since the run began or latest reset, whichever is later, and their observed
identities. Reopen and check those records
before reporting converged planning: either unavailable, overwritten, or mismatched record
leaves planning incomplete even when the exact runtime receipt says `complete`. Terminal
state deletion and a latest-only report must not erase the evidence for the earlier review.

Treat `blocked`, `stopped`, `cancelled`, missing/damaged state, unavailable resource, lost
terminal stdout, or absent domain evidence as incomplete. Preserve the exact terminal packet
outside the ephemeral state file for cold recovery; Backchain never derives success from
copied text, structural validity alone, or a model-written counter.

Return `{plan, convergence}` for compatibility-native planning and `{plan, review}` with
`review.convergence` for source-aware planning. This is a binding record, never a new plan
schema field or homemade pass history:

```json
{
  "binding_id": "stable selected binding identifier",
  "owner": "selected Until Loop binding",
  "candidate": {"input_sha256": "observed", "output_sha256": "observed"},
  "resources": [{"purpose": "selected Until Loop card", "resolved_locator": "/observed/path"}],
  "terminal_receipt": {"resolved_locator": "/observed/packet", "opaque": true},
  "domain_evidence": ["actual source/bounds/validation companion locators"],
  "planning_gaps": [],
  "execution_blockers": [],
  "next_action": "specific recovery action when incomplete"
}
```

`run-prompt.sh --prompt`, `--from-draft`, and `--package-only` remain one-shot generation
or structural primitives; none starts Until Loop or produces a terminal receipt.
