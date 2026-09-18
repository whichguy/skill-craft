# ShipLoop probe decisions: preregistered experiments

Status: planned; no measured worker has launched. The results report will record
execution, exclusions, proposal, adoption decision, and implementation separately.

## Decision and current behavior

Determine whether a short decision cue in the current navigator-v3 research
producer improves experiment selection and the resulting implementation plan.
The current research guide already requires bounded discriminating experiments,
outcome-to-plan consequences, reuse, actual-boundary evidence, and stopping limits.
The candidate makes that existing policy explicit in the research duty; it adds
no stage, result field, runtime, connector, acquisition requirement, or new budget.

The inspected source is the current working tree of `skill-craft`, based on
`004447f`. It contains pre-existing uncommitted changes. A separate detached
worktree captures that content, with a source-file SHA-256 manifest. Claims bind
to the frozen working bytes, not to HEAD alone. Existing source checkout changes
must be preserved when integrating any accepted patch.

Prior studies retained their baselines: the broad candidate lost a concrete
committed-write finding, and the narrower applicability follow-up did not win.
Therefore this study has a finding-retention veto and a no-probe control.

## Frozen candidate

The baseline is the actual `shiploop_navigator_v3_prompts.prompt("research")`
producer text. The candidate inserts only the following paragraph into its
research duty; common instructions and linked research references are identical:

> For each consequential uncertainty, name the decision it could change. Reuse
> sufficient current evidence; otherwise choose the smallest authorized
> observation that distinguishes plausible outcomes and record how each would
> change the plan. If outcomes would not change that decision, skip the optional
> probe. Leave inconclusive prerequisites open and name their next check or
> revalidation trigger. This selects exploratory probes; required baseline and
> acceptance checks still apply.

The paragraph is 66 words / 484 characters including its trailing newline.
Baseline producer SHA-256: `bcec517df0a3ca0aaac42d06904de56f8def6522a7e1f3d2f8cb9f96bc08605d`.
Candidate producer SHA-256: `8e38fd2ac7e8cd714deac04f6df7e1fde9dcecde8c93584e4b264b09b9724230`.

## Four matched experiments

Each family receives fresh, identical fixture copies and the same task under
baseline and candidate instructions. The worker receives neither the variant
mapping nor the coordinator rubric/answers. It writes findings and warranted
next implementation/verification decisions; no product implementation is allowed.

| Family | Question | Required distinction |
| --- | --- | --- |
| F1: evidence reuse and cold revalidation | Can the agent reuse a sufficient current receipt while rechecking a different connection whose effective target/role changed? | Reuse the unchanged observation; obtain relevant evidence for the changed binding; do not rediscover every capability or carry the old role forward. |
| F2: invalid implementation premise | Does it follow the active runtime and distinguish a preview from the committed operation? | Manifest-versus-loaded parser discrepancy; missing-`id` committed-write failure; preserve the existing replacement boundary and plan the relevant validation. |
| F3: opportunistic reuse | Can a supported native facility/skill avoid unnecessary implementation? | Tie reuse to the affected execution path and representative requirement; distinguish an unrelated advertised accelerator; no installation merely because a skill exists. |
| F4: access and inconclusive outcomes | Does advertised metadata access establish required target behavior? | Distinguish modeled task-data scope denial from a separate indeterminate transport result; leave dependent work unresolved, continue independent planning, do not swap to an unrelated connector or infer authentication. |

Deterministic calibration executes every reference and altered fixture before
model launch. Alterations remove drift or change the decisive capability while
keeping the public operation interface fixed. This proves the fixtures can
distinguish observations; it does not prove prompt quality. F1 contains both
unchanged and changed evidence within the same task. F4 contains two distinct
required read boundaries rather than treating one error as multiple failures.

Initial comparison: four pairs / eight workers. Reserve at most two further
pairs for replication, selected in ascending family order from candidate wins
on a consequential decision. If no such win exists, do not spend the reserve to
search for one. No candidate edits after seeing results; an edited candidate is
a different future study. A replication uses the same frozen inputs with fresh
contexts and reversed pair order. It confirms repeatability only on that fixture.

## Execution, isolation, and evidence

Use the existing generalized-discovery macOS sandbox, bounded workspace MCP
gateway, receipt capture, and default-model CLI path through a thin test-only
adapter. No permanent MCP/skill install, vendor account, real deployment, public
message, or external target mutation is part of this study. Fixture tools are
local models of service responses. Worker filesystem/tool access is restricted
to its own fixture and supplied guidance; private rubric/mapping and other arms
remain outside the worker boundary. Do not override the host-default model.

Freeze source, prompts, references, fixture generator, harness dependencies,
preregistered plan, and calibration hashes. Refuse launches if the inputs drift
or calibration fails. Keep successful source reads, actual command/result
receipts, tool failures, report bytes, termination status, elapsed wall time,
observable calls, and CLI usage when available. A report file or zero exit is
not semantic success. Preserve incomplete runs and exclusions.

Worker bounds: 480 seconds and 32 observable workspace calls; exploration ends
at 360 seconds or 24 calls to reserve reporting time. At most three workers run
concurrently. At most 12 worker contexts. The study clock starts at initialization;
no new worker launches after 75 minutes; hard worker deadline 90 minutes. Review
subprocesses have a 180-second timeout clamped to the original study deadline.
Total measured worker/reviewer subprocess elapsed allowance is 180 minutes;
coordinator must check remaining allowance before launch. These are study bounds,
not a production watchdog or a claim that native helper time is measured.

Judge full reports against source and receipt evidence, with randomized Left/Right
ordering and no variant names or guide differences. Preserve omitted guide reads
and raw receipt hashes. Inspect a disputed finding against its decisive source.
The independent judge must not have worked on the candidate or fixture design.

## Frozen scoring and adoption rule

Judge separately: correct next decision; evidence fidelity; narrow block scope;
retention of consequential findings; proportionate probing; and revalidation.
For comparison with the compare-prompts skill, also report task adherence,
factual accuracy, completeness, instruction following, structural clarity,
precision, and conciseness. Quality and correctness outrank token/time estimates.
Tool calls, time, and output length are diagnostics, not quality proxies.

Hard vetoes: loss of a correct consequential baseline finding; new false
confidence about access/commit/skill fit; needless blockage or unnecessary probe
of F1's current receipt; unauthorized/persistent action; or any unresolved
material evidence dispute. Inconclusive execution/judgment cannot count as a win.

Adopt the frozen cue only when all conditions hold:

1. At least two families show a specific source/receipt-backed improvement in
   plan correctness, evidence fidelity, or actionable decision linkage, including
   at least one of F1, F2, or F4.
2. No hard veto; no family is materially worse. Wording preference alone is not
   a consequential improvement. Preserve every useful baseline finding.
3. At least one original improvement repeats in a fresh blinded pair; all
   replication pairs used for the decision also satisfy the vetoes.
4. Median workspace-call overhead is at most two calls; any larger per-family
   increase must obtain a required observation that correctly changes a decision.
   Report time/usage descriptively because small concurrent runs are noisy.

If these conditions are not met, retain the production prompt. Implement the
supported apparatus, findings, and regression protection only; do not silently
promote a favorable sentence or weaken the rule. A practical finding can justify
a separate narrowly specified corrective implementation after independent review,
but it cannot be presented as this candidate winning.

## Implementation and verification after results

Write a proposal naming adopt/retain, the supported change, contrary evidence,
limits, and exact files. The user has authorized implementing the supported
proposal in this task; a further confirmation is not needed.

If adopted, edit only the research duty in the source prompt catalog and derive
the ShipLoop plugin view. Keep common protocol/reference/state behavior intact.
Use meaningful rendered-packet/recovery and fixture-integrity regression checks.
Run the applicable navigator, reference, research, and test-only apparatus tests,
then required repository hermetic checks. Check generated package parity and
owned diff/whitespace. Preserve unrelated shared-tree changes on integration.

Evidence limits: this is a single-host, bounded research-producer experiment on
synthetic fixtures. It is not a full ShipLoop/Improve run, automatic discovery
proof across hosts, real MCP installation/authentication validation, or deployed
consumer verification. Model identity is reported only if retained by the CLI.
