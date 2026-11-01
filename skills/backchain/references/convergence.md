# Backchain standalone Until Loop binding

Backchain uses the selected actual **Until Loop** for repeated dependency review. Until Loop
owns the callbacks, the review gate, recovery and the terminal transition; `scripts/backchain.py`
writes the contract and keeps the run's records; the host does the reviews and the repairs.
Backchain implements no counter, scheduler, state file, callback protocol, or second loop.

## Binding marker and gate

Every complete Backchain planning invocation carries this marker in the Until Loop child request:

```text
Backchain standalone Until Loop binding: <binding-id>
```

The caller selects the review gate with a second marker line beside the binding marker in the
same child request; `backchain.py prepare --passes` records it, and `freeze` writes the marker and
its gate into the contract. Backchain never infers the choice from the plan, the candidate or its
own judgment.

Without a second line the default applies: by default the first complete trivial/no-change
dependency review completes the loop, `required_trivial_reviews: 1`. Its exit condition: A
complete dependency review/fix/check cycle found nothing to repair and changed nothing; no planning
gap remains (future execution blockers may remain as unresolved entries); the structural check and
the domain evidence check pass on the final candidate. A cycle that repaired anything is
non-trivial, so a fresh review always follows a repair. (Owner decision, 2026-11-01: in the
2026-10-16 study none of the 11 reviews that confirmed a trivial review changed anything.)

ShipLoop's plan packet asks for one pass by default, with this second marker line:

```text
Backchain passes: one
```

With `Backchain passes: one` beside the binding marker, the contract carries
`required_trivial_reviews: 0` and this exit condition: One complete dependency review/fix/check
cycle has run; every finding of that cycle is repaired within the edit bounds; every `Confirm by`
clause on a step this cycle may change meets the planning guide's Outcomes rule; the printed
`backchain-check` is ok on the final candidate and its receipt is cited; final candidate-specific
domain evidence is saved. (`backchain-check` is the structural check a ShipLoop packet prints, and
the Outcomes rule is the section of ShipLoop's `references/backchain-planning.md` that defines a
`Confirm by` clause; another caller names its own check of the exact candidate and its own
confirmation rule, and `freeze` binds its own `backchain-check`.) A pass that completes that cycle
reports `exit_assessment: satisfied` even when it repaired the candidate; Until Loop then
completes the child and no second review runs. An open gap is reported `unsatisfied` and the loop
continues; nothing adds a pass ceiling.

With `Backchain passes: converge` beside the binding marker, the contract carries
`required_trivial_reviews: 2`: two consecutive distinct complete trivial/no-change dependency
reviews and final candidate-specific domain evidence. Its exit condition: Two consecutive distinct
complete trivial/no-change dependency reviews have run; no planning gap remains; the structural
check and the domain evidence check pass on the final candidate.

## The contract

`freeze` writes the whole contract for the selected card's "Start from a parent-written contract"
route. Read the Until Loop card once, then start it with the printed `Contract:` and `Receipt:`;
the runtime writes every packet to the receipt, so the latest packet is always retained. Do not
build, edit, retype or re-serialize the contract, and do not start a second run for the same
receipt. The contract binds:

- the work (one cycle, below), the gate and exit condition above, and the repeat condition: repeat
  while an authorized in-scope repair or a required distinct review remains; stop incomplete
  (`blocked`) on a planning gap no authorized repair can close; no pass ceiling;
- the context: the request with both markers; the scope (the plan artifact and its planning
  companions only, the edit bounds, and read-only inputs, contract and cycle records); the authority
  (no commit, push, merge, project execution, installation, network access or contact with people
  or services, and no broadened scope); the environment; and every resource by its observed
  absolute locator: the original request and any inherited draft or caller packet, this skill's
  card, references and prompts, the Until Loop card and runtime, the candidate, the latest packet
  (the receipt), the domain evidence and the result destination;
- two frozen exit checks: `backchain-check` (the structural check on the final candidate) and
  `backchain-evidence` (`backchain.py verify`: every cycle record intact, no edit after the last
  record, obligations kept). A caller adds its own with `freeze --exit-check`. No exit check is
  ever repaired.

The frozen inputs and baseline, the authorized scope and bounds, the original request and the
governing source criteria stay fixed for the run. An authorized in-scope repair, its output
candidate, or newly gathered in-scope evidence stays in the same run; a material classification
resets the runtime gate. Start a new run, with a new binding, only when an external or unapproved
candidate/baseline substitution, a scope/bounds/request change, or a newer contradictory governing
source changes the criteria; no trivial-review state carries across that changed binding. A
missing selected card, runtime or required resource stops `prepare`; there is no substitute loop
and no ambient same-named runtime.

## Obligations a candidate keeps

`freeze` and `record` compare the candidate with what it must keep, and `verify` repeats the
comparison as an exit check. An error refuses the command; a difference needs a finding in the
cycle's assessment, or for source-aware work an authorized old-to-new map that carries its
verification obligation.

| Compared with | Mode | Must keep |
| --- | --- | --- |
| A generated draft, at `freeze` (draft → enriched) | `legacy` | `goal_needs` exactly; an unchanged produce on its original step keeps its whole confirmation |
| An inherited draft or plan, without caller `edit_bounds` | `legacy` | the same, plus every inherited step ID and input edge |
| An inherited plan, with explicit caller `edit_bounds` | `source-aware` | `goal_needs` exactly; every other difference reported |
| The frozen baseline, every cycle | `source-aware` | `goal_needs` exactly; every confirmation difference reported |

`scripts/check_preservation.py` performs the confirmation and `goal_needs` comparison (exit 0
holds, 1 fails, 2 the baseline binding changed, 3 could not run); `backchain.py` adds the
inherited step IDs and input edges. Exit 0 cannot establish that a difference is justified:
account for every reported difference in the assessment (`moved_unchanged`, `added`,
`unchanged_produce_confirmation_changed`, `produce_text_absent`, multi-owner produces), or restore
it. A legitimate in-place produce rewrite or move grants no permission to narrow a seed or move its
work. A review may remove an edge or step this run itself generated when it finds it unjustified,
as a material repair with its reason; inherited content stays.

## Each cycle

Each Until Loop callback is one complete dependency-review/fix/check cycle. Read the packaged
`prompts/convergence-review.prompt.md` and perform its assessment for that cycle, including actual
reads of applicable or uncertain technical cards (`backchain.py lenses ID…`). The cycle performs a
fresh backward trace from every requested outcome and verification sink, a forward walk of
suppliers/consumers/new branches, the full lens applicability screen (shared exclusions may be
grouped), source and experiment identity review, authorized repair, and the post-repair check.
Source-aware work also uses `audit.prompt.md` and one bounds-respecting `revise.prompt.md`. Do not
recursively invoke whole Backchain or Until Loop. Skipped required reads or checks make the cycle
unresolved, even when no plan edit was made.

After the cycle's last edit, save the assessment JSON and run `backchain.py record --run DIR
--review FILE --exit E --continuation C`. It checks the assessment, the structure and the
obligations; writes the cycle's review, plan, check, comparison and report under `DIR/cycles/NN`,
never overwriting an earlier record; and rolls `DIR/evidence.json` forward with every record's
locator and identity. Then run the packet's `verify_script` unchanged, make no further edit, and
submit the report `record` printed through the packet's `done_argv` on stdin.

A step this cycle may change is one whose exact ID is provisional in the caller `edit_bounds` and
that is not running, completed, or protected; with no caller `edit_bounds`, it is any step that is
not running or completed. On such a step, a produce with no confirmation, a confirmation that
checks only part of its produce, or an unjustified `unconfirmable` marker (on a produce an
available check could confirm, or whose `by` does not name what would) is a material planning gap.
On any other step it is advisory; it is not a planning gap or a forbidden necessary repair. Apply
the implementable-chunk review below on every cycle, including after enrichment, insertion, or
other repair.

Classify obligation, supplier, edge, branch, ordering, verification, source, experiment, or
protected-bound changes as material (`non-trivial`), even if repaired. Only verified nonsemantic
presentation/no-change cycles are `trivial`; unknown impact is `unresolved`. `record` also measures
it: a cycle whose packaged plan changed is non-trivial whatever its assessment says. Missing
normative sources, forbidden necessary repairs, stale identity, or architecture-determining
experiment outcomes are planning gaps. Known future external prerequisites may remain execution
blockers. Every revision is repackaged by `record`, so `parallel_groups` and the structural verdict
always belong to the exact recorded candidate.

### Implementable chunks

Inspect every scoped work step, not just the last edit. Each must describe a deliverable
that an implementer can establish and confirm using its declared suppliers. A shared feature
name or final end-to-end check does not justify bundling separately useful deliverables.
Split when parts have different prerequisites, expose a useful intermediate artifact, or
can be implemented and checked independently as useful deliverables. A separately checkable
assertion or file edit alone is not a useful delivery boundary. Keep fragments together when
they share prerequisites, implementation boundary, and postcondition family and have no
useful independent result; merely finer decomposition is advisory. File count, step count,
estimated duration, or desired parallelism alone do not justify a split.

For each necessary split, identify the resulting deliverables, their confirmations, and
which outputs each consumer needs. Preserve all requested outcomes, `goal_needs`, and
verification coverage. Add serial edges only where one chunk consumes another's output;
independent chunks can branch after a shared supplier, and real integration/verification
work consumes all outputs it needs. Record shared-file/resource coordination needs in review
evidence rather than inventing data dependencies. Each moved part has one implementation
owner. A retained or new join must establish a distinct integration condition or preserve
whole-feature verification beyond its inputs' confirmations; it cannot duplicate the moved
work or merely restate that its suppliers finished. After repair, the active callback checks
the resulting chunks, confirmations, and affected consumers against the request and input
plan before submitting the cycle. This is the cycle's check, not another review cycle or an
independent-review claim.

A necessary split on a step this cycle may change, as defined above, is a material planning
gap until repaired. Determine that scope before classifying a split. Chunk-boundary findings
on unrelated non-provisional context work are advisory for that work's owner, even when its
parts are independently useful. Inclusion in the dependency neighborhood alone does not
bring that work's delivery boundaries into scope; do not block scoped work on that observation.
Independent missing outcomes or suppliers still follow the existing gap rules.
This review scope does not grant edit authority.
Legacy elaboration preserves inherited identities, seed/null edges, and existing confirmation
entries: it cannot narrow a seed's work or move its confirmations off that seed, even with
no inherited edges. Keeping its ID, produces, and confirmations while transferring its
implementation to discovered steps and turning it into a verification join is also narrowing.
Discovered prerequisites may supply genuinely missing inputs; they may not take over inherited
seed work. Source-aware revise still requires explicit exact provisional step/edge
and affected-consumer bounds plus new-step/new-edge permissions; absent `edit_bounds` does
not authorize that revise. If a necessary split cannot be completed within the selected
route's limits, retain the candidate and report a planning gap with the concrete recovery:
obtain the required source-aware bounds, or return to the caller to regenerate the draft.
A replacement draft requires a new run and binding; do not substitute it inside the
frozen run, make a partial split that leaves invalid consumers, or retry an unavailable
repair as though authority will appear. Until Loop owns the blocked/incomplete disposition.

Record the inspected boundaries and split/keep rationale in the cycle's assessment, with
old-to-new mappings linked to the original request or applicable sources for repairs. No new
plan fields, size score, or loop machinery is required. Structural validity alone does not
prove chunk suitability.

## Terminal evidence and recovery

After the loop ends, `backchain.py finish` writes `DIR/result.json`. It reports converged planning
only with both the exact selected Until Loop terminal `complete` packet (the receipt) and
candidate-specific domain evidence: every cycle record intact and matching, the final output
identity, a structurally valid candidate, and no planning gap. The adapter validates callback shape
and transitions, not that semantic evidence is true.

`record` keeps every cycle's original review record with its observed candidate identity, and
`finish` reopens them all; the evidence set that converged planning needs depends on the gate. By
default it is the completing cycle's trivial review record, with every earlier cycle's. With
`Backchain passes: one`, the evidence set is the one review record of the cycle and the
`backchain-check` receipt on the final candidate. With `Backchain passes: converge`, it is both
original qualifying review records since the run began or the latest reset, whichever is later. An
unavailable, overwritten, or mismatched record leaves planning incomplete even when the exact
runtime receipt says `complete`.

Treat `blocked`, `stopped`, `cancelled`, missing or damaged state, an unavailable resource, or absent
domain evidence as incomplete; `finish` then writes the honest incomplete record with its next
action. For cold recovery, the receipt holds the latest packet (an `active` one supplies
`next_argv`), and `DIR/evidence.json` and `DIR/cycles/` hold every record. Backchain never derives
success from copied text, structural validity alone, or a model-written counter.

Return `{plan, convergence}` for compatibility-native planning and `{plan, review}` with
`review.convergence` for source-aware planning. This is a binding record, never a new plan
schema field or homemade pass history; `finish` writes it:

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

The development checkout's `run-prompt.sh --prompt`, `--from-draft`, and `--package-only` remain
one-shot generation or structural primitives; none starts Until Loop or produces a terminal
receipt.
