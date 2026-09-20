# Ask Agent Git integration and resumable handoff

## Candidate and scope

Current implementation: Ask Agent 0.3.0, candidate U17. The Git campaign below
ran on frozen U15; M1 records frozen U16 monitoring evidence, and M2 is the
separate U17 follow-up. The
[main card](../../../../skills/ask-agent/SKILL.md) adds conditional Git delegation
and self-contained completion reminders. The
[Git reference](../../../../skills/ask-agent/references/git-integration.md) assigns
integration target/order/acceptance to the parent, supports delegated execution,
and distinguishes isolated, shared-checkout and report-only work.

The returned receipt reminds the parent of the assignment and recommends a next
action and owner. Its report retains the contribution, checked target, conflict
and validation state, unresolved decisions and exact artifact/revision references.
The parent verifies that recommendation against live state before acting and
retains pending handoffs. No runtime scripts or fixed agent limits were added.

U15 frozen main SHA-256:
`4ac0eb3f701f07d78d4bb2f96bd7a0fa7131cd48910582df3a6794befa6345ce`.
Frozen Git reference SHA-256:
`127e0fad5af53067360e3429fd319870fec4f08f09a2f697bc6ccd4f533321fd`.
The full package is frozen under
`/Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/frozen-U15/ask-agent/`.

## Experiment protocol

The [implementation plan](INTEGRATION-PLAN.md) and
[case recipes](integration/README.md) define three real-Git scenarios. G1 has two
separate native parent invocations; G2 and G3 each have one. The campaign registers
four parent rows on each of Claude, Grok, Codex and OpenCode: 16 rows total.
The [registration](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/PLAN-U15.json>)
freezes 19 case files. The protocol also requires per-host concrete paths,
Git SHAs, rendered prompts and launch arguments before invocation; missing
receipts are disclosed in the results. Only native
parent CLIs and native worker facilities perform model execution.

- **G1 prepare / fresh parent:** the designated local target is ahead of the
  worker's configured remote upstream. A native worker synchronizes and returns
  a pending handoff. A new parent receives only the skill, report path and fixture
  root and must reconstruct, verify and complete local integration.
- **G2 conflict and semantic gate:** the worker repairs a target-A conflict.
  Target B advances before acceptance; a textually clean preview fails a behavior
  assertion. The parent must leave it unaccepted and report the next action.
  This checks rejection of an invalid combined candidate; target B itself also
  violates that assertion, so it does not establish a two-valid-contributions
  interaction defect.
- **G3 shared checkout:** separate editor and read-only auditor workers operate
  with distinct ownership. The parent verifies the intended edit while preserving
  unrelated staged, unstaged and untracked sentinel state. No branch merge applies.

The independent reviewer physically exercised all three final fixture mechanisms
before model runs. Draft setup errors were corrected before registration;
post-freeze clarification edits were archived and restored to registered bytes.
See [mechanics receipt](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/fixture-mechanics-review.md>)
and [restoration record](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/FIXTURE-RESTORATION.json>).
These are setup checks, not native-harness outcomes.

## Native results

The registered rows ran once. Functional Git results and case-specific
conformance are graded separately: a correct Git outcome does not erase an
uncollected callback, a rejected wait call, or a registered-input deviation.
U15 is therefore not an all-host pass.

| Host | G1 prepare / fresh parent | G2 conflict and semantic gate | G3 shared checkout | U15 boundary |
| --- | --- | --- | --- | --- |
| Claude Code | Functional PASS: prepared handoff remained pending, then a fresh parent accepted and revalidated it locally. The fresh-parent row made a rejected `ScheduleWakeup` call and falsely reported no collection error. | Functional PASS: Target B remained unaccepted after the required semantic rejection. The worker ref differed from the registered fixture-local locator, the preview was removed without explicit `git merge --abort`, and `tasks/` appeared after baseline. | Git-state PASS: exact owned edit and sentinels/diffs/refs were retained. Lifecycle/hygiene FAIL: no editor notification, a rejected `ScheduleWakeup`, new `tasks/`, and a final response that omitted those defects. | Functional Git evidence is useful, but the retained U15 conformance defects prevent a full host pass. |
| Grok | PASS: fresh worker prepared a durable pending handoff; fresh parent reconstructed, integrated, validated, and did not push. | PASS: Target-B gate failed as expected; worker remained unaccepted with refresh/replan. | PASS: concurrent editor/auditor preserved the shared state and made only the owned edit. | All four functional rows passed. Full rendered briefs were forwarded and parent policy reads were observed; direct generic skill/reference reads by children are **UNOBSERVED**, not inferred. |
| Codex | Functional PASS: child preparation and a distinct fresh-parent acceptance/revalidation both reached their expected Git states. | PASS: Target-B semantic gate rejected the otherwise clean preview and left it unaccepted. | PASS: both child completions and required preservation checks were observed. | Four functional rows passed. Recorded dispatch metadata fails the **registered-case exact-brief/path** check; the public projection does not establish whether relevant policy was propagated in paraphrase, so no blanket policy-propagation failure is claimed. |
| OpenCode | Qualified G1 result: prepare and fresh-parent local acceptance were observed, but exact pre-launch argv was not retained. | No functional worker run: three native `Task` requests used invented UUID `task_id` values and were rejected; no child or Target-B attempt followed. | Children completed and collection events were observed, but immutable before-sentinel evidence and a final parent synthesis/acceptance capture are absent. | Partial evidence only; G2 and the G3 parent-endpoint gap prevent a full host pass. |

The host records retain native IDs, safe event timing, input integrity, Git state,
and the stated limitations without exporting private reasoning:

- [Claude RESULTS.md - U15 functional rows and retained lifecycle defects](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/claude/RESULTS.md>)
- [Grok RESULTS.md - four functional passes and child-read observation boundary](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/grok/RESULTS.md>)
- [Codex RESULTS.md - functional outcomes and exact-brief dispatch conformance boundary](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/codex/RESULTS.md>)
- [OpenCode RESULTS.md - rejected G2 dispatches and incomplete G3 parent capture](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/opencode/RESULTS.md>)

## U16 M1 monitoring regression

This section is separate from the unchanged U15 matrix. U16, version 0.3.0,
used frozen main-card SHA-256
`cd3d4fc04cceef1c1364be99432ba2a66cdbf55a91583cc484d8162844793699`;
its Git reference remained the U15 hash
`127e0fad5af53067360e3429fd319870fec4f08f09a2f697bc6ccd4f533321fd`.

| Host | Observed M1 lifecycle | Waiting / provenance grade | Current boundary |
| --- | --- | --- | --- |
| Claude Code | PASS: actual `claude-sonnet-5` parent read frozen policy, launched two fresh general-purpose workers into one pending collection, continued useful work, then collected both reports and wrote a synthesis. | **FAIL:** an eligible pending-only silence lasted 179.764 seconds; no visible status/progress or native status wakeup occurred. | One observed run; tool parity and global source-workspace isolation remain unobserved. |
| OpenCode | PASS: queue, native completion returns, report verification, and final synthesis were observed. | **FAIL:** an eligible pending-only silence lasted 198.598 seconds. Transient copied-reference provenance is **UNOBSERVED** because no retained prelaunch hash, symlink-target, or inode receipt ties it to frozen U16. | This is scoped evidence only; the parent-reported absent join/periodic route does not repair the silent interval. |
| Codex | PASS: two pending jobs, continuation, returns, report verification and final synthesis on Astra. It completed before the user model-change request. | Waiting status PASS with qualified timing during a natural 7m38s wait. A nested `review-skeptic` violates broad general-purpose selection. Exact brief/policy forwarding and full tool parity remain UNOBSERVED. | Functional lifecycle and report recovery passed; nested-role selection is a retained conformance failure. |
| Grok | PASS: frozen policy reads, two pending fresh native workers, useful parent continuation, both report returns and final synthesis. | Waiting-status mechanism observed: positive native observation waits followed by truthful visible updates. Actual delivery/processing times are retained. | Scoped supplied-input integrity passed; no global isolation or full tool-parity claim. Compatible appended handoff policy preserves the unchanged brief content. |

The completed host receipts are:

- [Claude U16 M1 RESULTS.md - successful collection/synthesis and 179.764-second silence](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/claude/U16-M1/RESULTS.md>)
- [OpenCode U16 M1 RESULTS.md - observed lifecycle, 198.598-second silence, and reference-provenance boundary](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/opencode/U16-M1/RESULTS.md>)
- [Codex U16 M1 RESULTS.md - lifecycle, waiting evidence and nested-role deviation](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/codex/U16-M1/RESULTS.md>)
- [Grok U16 M1 RESULTS.md - native joins, visible status and collected reports](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/grok/U16-M1/RESULTS.md>)

## U17 candidate and M2 native follow-up

U17 is the current implementation. Its main-card SHA-256 is
`462583a2ac85f7fe4b4945a3859dc05a788b1f7e1ad41275ec21bfdc27966b40`;
the Git reference is unchanged at
`127e0fad5af53067360e3429fd319870fec4f08f09a2f697bc6ccd4f533321fd`.
The campaign comprises 25 native parent attempts: 16 U15 Git rows, four U16
monitoring rows, four U17 M2 rows and the separately registered Codex M2b
correction. This is an attempt count, not a pass count; the interrupted Codex
M2 attempt remains in the record.

M2 requires an explicit pre-idle choice: a native timed wait with visible
status, a supported native current-session status wakeup, or a disclosure before
idle that no periodic native route is available. The user-selected parents are
Claude Sonnet, OpenCode `xai/grok-4.6`, Codex `gpt-5.6-luna` at `xhigh`, and
the unchanged Grok host default. The Codex model change is a confound and cannot
be attributed to the U17 wording alone. See [monitoring-followup/README.md - M2 pre-idle selection and observation rules](monitoring-followup/README.md), [CANDIDATE-U17.json - frozen U17 main and unchanged reference hashes](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/CANDIDATE-U17.json>), and [PLAN-U17-M2.json - registered hosts and selected parent models](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/PLAN-U17-M2.json>).

## U17 native observations

| Host / attempt | Outcome | Remaining limit |
| --- | --- | --- |
| Claude M2, Sonnet | PASS in this run: two fresh native general-purpose workers, parent continuation, both reports, verification and final synthesis. Timed `TaskOutput` produced a visible pending update after 143.701 seconds. | Timing is approximate; full tool parity remains unobserved. |
| OpenCode M2, Grok | Queue/returns/final synthesis and pre-idle unsupported disclosure observed. Periodic updates are **UNSUPPORTED** in this exposed tool interface. | Final/pending records incorrectly label the 183.560-second interval condition-not-triggered; this is a retained reporting failure, despite the correct pre-idle disclosure. |
| Grok M2, Grok 4.6 | PASS for fresh native launches, two pending jobs, continuation, both returns, report checks and final synthesis. | Waiting-status **FAIL**: a 303-second visible gap (19:47:09–19:52:12 UTC) occurred while native snapshots still showed pending work. |
| Codex M2 | **INTERRUPTED:** parent Luna/xhigh, but direct child turn records Terra/max due separate local child defaults. | Not a completed Luna-worker result. Nested specialist/inherited-context deviations retained. |
| Codex M2b, Luna/xhigh | Fresh native launches, two pending jobs, continuation, visible timed-wait updates, both returns, report checks and final synthesis observed. Effective parent and both direct workers verified Luna/xhigh; no nested spawn occurred. | Final prose incorrectly calls the observed waiting interval not-a-pass; reviewer task status conflates a completed review with conditional acceptance. Explicit native-type/substitution fields are absent from the final table. Worker-policy forwarding and full tool parity remain unobserved; recovered noncollection tool errors are retained. |

See [Claude U17 results](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/claude/U17-M2/RESULTS.md>),
[OpenCode U17 results](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/opencode/U17-M2/RESULTS.md>)
and its [independent audit](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/U17-opencode-independent.md>),
plus [Grok U17 results - completed lifecycle and retained status failure](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/grok/U17-M2/RESULTS.md>).
See [Codex M2b results - verified Luna/xhigh lifecycle and output deviations](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/codex/U17-M2b/RESULTS.md>)
and the [Codex M2b independent audit - effective settings, native returns and reporting boundaries](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/U17-codex-M2b-independent.md>).
The [model-selection correction](MODEL-SELECTION.md) documents the Codex configuration
precedence, interruption, per-invocation fix and preserved attempt boundary.
All U17 participant runs are terminal; owned temporary discovery bindings and
Codex trust entries were cleaned up. Evidence and reports remain retained outside
the source checkout. No global model defaults were changed.

## Package and repository checks

Scoped Ask Agent source/generated-package parity, its reference links, generated
catalog metadata and whitespace checks passed. An independent review found no
material contradiction in the frozen U15 prompts. Two independent U16 contract
reviews also found no material defects. U17 was independently reviewed after
its pre-idle clarification; source/package hashes match the frozen candidate.
Runtime adherence remains an
empirical question. See [prompt review](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/campaign/operator/u15-prompt-review.md>).

The generic Codex quick validator could not run because neither available Python
runtime has PyYAML. Its inspected schema also excludes this portable repository's
`version`/`platforms` metadata. The applicable repository metadata checks passed.
See [U17 package checks](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/PACKAGE-CHECKS-U17.json>)
and the [final parity receipt - unchanged source, generated package and five M2 case files](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/FINAL-PARITY-U17.json>).

The full hermetic aggregate finished with exit 1: `sync-plugin-views` and
`native-marketplace-adapters` failed on unrelated ShipLoop source/package drift,
and `improve` failed on an unrelated `__pycache__` artifact. The serial ShipLoop
suite itself passed. Ask Agent's final scoped parity/metadata checks passed.
See the [aggregate receipt](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/HERMETIC-RESULT.json>).
The [full log](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/operator/hermetic-all.log>)
retains all outcomes; unrelated source/package work is not altered to obtain a pass.

## Evidence boundaries

The skill supplies prompt guidance and cannot mechanically guarantee model
compliance. Exact target revisions, actual commands, actual file/Git state and
native completion/collection events are evaluated separately. Correct prose,
process exit, a clean merge or a worker success label is not sufficient evidence.
These tests do not publish changes or test survival after an abandoned native
session. Earlier U11–U14 handoff results remain evidence for their frozen versions.

The current skill provides a common native-delegation convention, but the evidence
does not establish uniform monitoring reliability across hosts. Periodic updates
are approximate where observed and explicitly unsupported where the exposed
native interface cannot provide them. An honest fallback is useful behavior, not
proof of the missing capability. Retain model noncompliance as a runtime failure
rather than adding a prohibited dispatcher or treating repeated attempts as one
successful run.

## Development coordination

The [shared task charters](../../../../docs/ask-agent-backchain-coordination-2026-09-18.md)
assign native delegation and qualification to the Ask Agent task, and planning,
durable dispatch/receipt state, dependency acceptance and concrete integration
to the Backchain task. This coordination does not change the frozen candidates
or the outcomes above.
