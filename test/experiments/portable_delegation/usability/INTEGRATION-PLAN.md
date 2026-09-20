# Ask Agent integration and resumable handoff plan

## Outcome and boundaries

Add a prompt-only integration contract to Ask Agent. The parent owns target,
order and acceptance; workers prepare changes, reconcile against the designated
target and repair conflicts. Delegating integration execution remains possible.
Keep fresh native agents, asynchronous parent continuation, native completion,
compact file handoffs and flexible work/output/delegation unchanged.

Each returned result also reminds the parent of its assignment and recommends
the next action with enough state and artifact references to resume without
remembering the launch conversation. Recommendations remain subject to current
instructions and current repository state.

No dispatcher, custom runtime scripts, new harness configuration, automatic
source-repository pull/merge, or arbitrary agent limits are part of this change.
Existing unrelated work and the shared source checkout's index remain untouched.

## Implementation order

1. Extend the main card's dispatch and handoff guidance; add a conditional Git
   reference for workspace topology, synchronization, conflict repair, receipt
   evidence, serialized target updates and combined validation.
2. Create replayable prompt/input cases and explicit independent acceptance
   criteria for actual Git behavior, including failure and recovery boundaries.
3. Freeze the exact candidate and case inputs before native parent trials.
   Exercise Claude, Grok and Codex independently; exercise OpenCode with its
   available native background facilities and report availability separately.
4. Audit observable native calls, filesystem/Git outcomes and returned receipts.
   Preserve failed attempts. Correct material prompt defects with a newly frozen
   candidate and a separate regression trial rather than replacing evidence.
5. Regenerate only the Ask Agent package where possible, verify metadata/catalog
   parity and relevant repository checks, then independently review the result.

## Acceptance

- No automatic worker merge into a shared destination; ownership can explicitly
  delegate execution without losing parent acceptance.
- Named integration target and exact checked revision survive the handoff.
  Wrong upstream, unpublished local target movement, and stale evidence do not
  become an unqualified clean/current claim.
- Worker conflict repair preserves intended behavior and is followed by checks;
  clean textual merges still require relevant combined behavior validation.
- Shared-checkout and report-only cases preserve unrelated staged, unstaged and
  untracked inputs and avoid unnecessary Git integration.
- Worker completion receipts state assignment, actual result, recommended next
  action/owner and report reference. Reports preserve current state and pending
  obligations until integration is complete.
- Evidence distinguishes source conformance, native launch/return, worker result
  correctness, integration, validation and availability. No claim transfers from
  earlier handoff campaigns to the changed candidate without a new observation.

See [integration cases](integration/README.md) for setup, isolated fixtures,
exact prompts, expected outcomes and teardown. Results will record the frozen
candidate, versions, actual commands, native identities and retained limitations.

## U16 monitoring and capability extension

Treat each Ask Agent call as adding to the initiating parent's pending jobs.
Announce confirmed launches and reported returns, then preserve next actions
until results have been accepted. While only waiting, summarize all jobs about
every two minutes unless equivalent progress is already visible from the harness.
Use native observation waits or supported current-session wakeups, with honest
delivery limits. A wakeup is not completion, and no custom scheduler is introduced.

Default to the broadest general-purpose native worker; use role labels in its
prompt. Inherit parent capabilities where supported without adding tool masks,
model downgrades or delegation limits. Preserve fresh contexts, actual host
permissions, task scope and file ownership. Disclose host-filtered tools and use
a native parent-operation request when useful and available.

Freeze U16 and one new [monitoring case](monitoring/README.md) before four native
parent runs. Record queue membership, launch/return notices, parent continuation,
observed waiting intervals, actual worker roles/tools and final collection. Do
not force elapsed time or count a short run as proof of a periodic status update.
Keep U15 timer/conformance failures under its original policy; U16 does not
retroactively repair those observations.

## U17 pre-idle status correction

U16 native evidence showed eligible silence in Claude (179.764 seconds) and
OpenCode (198.598 seconds), despite successful native returns. Require the parent
to choose its timed observation/status wakeup mechanism before idle, or disclose
that no periodic native route exists. Completion-only callbacks do not satisfy
periodic monitoring. Updating an internal record is not a user-visible notice.

M2 repeats the meaningful read-only review case on all four hosts with frozen
inputs and independent event timing. Use Sonnet for Claude, Grok for OpenCode,
and gpt-5.6-luna with xhigh reasoning for Codex as requested; Grok is unchanged.
Codex's model change prevents attributing differences solely to the prompt.
Hash every temporary discovery copy/reference before launch and cleanup, and
retain all earlier outcomes. No custom scheduler or runtime is introduced.
