# Compact handoff experiments

## Implementation plan

Keep native dispatch, completion, collection and cancellation. Add a worker
output contract and parent file-consumption/cleanup instructions to the existing
prompt-only skill. Freeze the candidate before live execution. Use the same card
and task requests in Claude, Grok, Codex and OpenCode; retain each host's native
input and completion routes. Do not add dispatcher scripts, file watchers or
session drivers. Regenerate the ask-agent package from its source after review.

U10 remains the historical baseline. U11 version 0.2.0 was the initial handoff
candidate; U12 version 0.2.0 tested stricter reading instructions. U13 version
0.2.0 introduced flexibility after the user requested no agent
limits: compact handoff is a preference, not a word/line cap, and further native
delegation is permitted. U11's four-case campaign, U12's F1/F2 correction trials,
and U13's F2 trials were separately registered before execution. The strict cap
criteria below describe U11/U12, not U13; PLAN-U13.json defines its own criteria.
Current U14 preserves that flexible policy and adds an OpenCode-only fresh-task
argument hint, tested in its separately registered PLAN-U14.json F2 trial.
See [HANDOFF-RESULTS.md - candidates: hashes, registrations and outcomes](HANDOFF-RESULTS.md).
The original U11 protocol snapshot is retained with its registered hash in the
campaign's `operator/HANDOFF-CASES-U11.md`; this paragraph was clarified afterward
without changing the case prompts, oracles or grading criteria.
Results must identify the exact candidate, mode, model, input hashes,
parent/child native locators, and failures. No success is inferred from exit 0.

## Original U11/U12 cases

Each case runs once per host in a fresh disposable project; failures are retained
without replacement. An input-transport failure is invalid for responsiveness,
not a pass. Each participant has an eight-minute bound; one participant per host
at a time. These bounds and fixture restrictions are experiment controls, not
Ask Agent runtime limits. No model or authentication changes, installs or upgrades are allowed.

| Case | Action | Required evidence |
| --- | --- | --- |
| F1: substantial interactive return | Native invoice reviewer audits 36 invoices while parent computes $300. Operator sends an actual $6 follow-up after the parent result and before worker terminal. | Separate native background child; requested fresh route; receipt after report write; worker final <=100 words with status, path and temporary designation; actual $306 reply while original child is live; native completion followed by parent selective read and actual $4176.90 result; report deleted only after use. |
| F2: parallel success and blocker | Launch North's 24-invoice audit and South's 12-invoice audit before collection; complete independent $300 parent budget. Retain South's report for unresolved work. | Distinct native handles and report paths; North $2482.20/SUCCEEDED; South missing INV-08 rate/BLOCKED with no combined total; unfinished tasks stay pending; North report removed after use, South report retained and disclosed; user sentinel untouched. |
| F3: tiny result, writes forbidden | Delegate six times seven through the native harness, explicitly awaiting the answer; all writes forbidden. | Native child returns 42 concisely inline; no report required, no write attempted, no false artifact promise. This tests the prompt's fallback decision, not OS permission enforcement. |
| F4: receiver fault controls | Supply explicitly simulated receipts for a missing file and a report whose contents say BLOCKED despite a SUCCEEDED receipt. No agents run in this case. | Parent actually checks the assigned paths, distinguishes unverified completion from accepted result, reports both collection problems, preserves unresolved/user files, and does not invent contents or launch a replacement worker. This is receiving-policy coverage only. |

## Flexible criteria for U13/U14

These criteria were registered in PLAN-U13.json before execution. Reuse the
same task fixtures and prompts, but do not apply U11/U12's word or read limits:

- Observe separate native worker contexts using the requested fresh route;
  parent work follows confirmed launch and precedes collection.
- For F2, require North SUCCEEDED at $2482.20 and South BLOCKED for missing
  INV-08 rate without an aggregate; preserve pending tasks and blockers.
- Substantial evidence must be written before the worker's native final receipt,
  which supplies task, status, outcome and report reference. Measure receipt
  length descriptively; do not impose a word or line cap.
- The parent checks the returned report and uses evidence appropriate to its
  task. Record read volume without a fixed ceiling or an automatic failure for
  reading a full report. Large reads still matter when assessing context cost.
- Delete the completed owned temporary report after use; keep and disclose the
  blocked report. Preserve the sentinel and inputs.
- Use native dispatch and completion/collection, with no custom notification or
  dispatcher scripts. Distinguish native joins from automatic notifications.

U14's OpenCode confirmation additionally checks that a fresh launch omits
`task_id`; record every rejected call and recovery. Current flexible-policy
execution covers F2 once on each of four hosts under U13, plus that single
OpenCode U14 confirmation. F1/F3/F4 were not rerun against the flexible policy.
Nested delegation is permitted by the skill but was not exercised because the
invoice fixture explicitly forbids it. Broader or longer work is allowed by the
skill, but this bounded experiment does not establish unlimited host capacity.

## Native surfaces

F1 requires an interactive parent (Claude native streaming input is also valid
when labelled). OpenCode 1.18.31 requires its process-local native background flag
and the persistent normal TUI for F1/F2. Other hosts may use their tested native
headless join for F2. F3/F4 may use headless parents. Do not count a headless join
as automatic notification or input that was merely queued as an answered request.

## Oracles and historical strict context evidence

The durable invoice fixtures are in `handoff/fixtures/invoices/`; parent and worker
task text is frozen per participant. F1 uses all 36, North uses 01–24, and South
uses 01–12 with INV-08's tax rate replaced by NOT PROVIDED. Using decimal cents
and half-up tax, independent oracles are $4176.90, $2482.20 and BLOCKED respectively.
The F1 invoice split is 17 clean and 19 discrepant. Parent budget is
18 × $12.50 + $85 − $10 = $300; the actual follow-up adds $6 = $306.

Measure worker final text separately from harness notification wrappers. Extract
native parent tool outputs and completion messages without private reasoning.
The remaining strict consumption rules in this section apply to U11/U12;
U13/U14 use the flexible criteria above.
Grade these separately: compact receipt; detailed file created before terminal;
actual receipt/path delivery; parent reads selected sections; result accuracy;
cleanup timing; native async responsiveness. The complete invoice detail table
must not be pasted into the worker final, parent final, parent-directed progress,
or parent read output. Selected evidence reads are allowed when needed to verify
a claim; record how many invoice rows reached parent context. Do not claim total
token savings from receipt word counts alone, or full isolation from a child ID.

An initial file-read tool may still return the whole report despite a brief
notification: that fails selective consumption. Any missing report, premature
deletion, full inline fallback dump or wrong numeric result remains a failure
even if native completion works. Report path, native status and worker text are
evidence, not proof that the requested task succeeded.

## Setup, suites and teardown

Copy one frozen card into each host's tested discovery location and copy fixtures
into each participant. Shared frozen input files are read-only to participants;
each receives its own working copies and report directory. Keep expected totals,
native event exports and grading receipts in the operator area, outside worker
inputs. Snapshot all input hashes before launch and check afterward. Preserve
`preserve.txt` as a user-file sentinel. Record parent-generated deliverables apart
from temporary worker reports.

Focused smoke: F1 on one host. Full handoff suite: F1–F4 on all four hosts (16
rows, including four explicitly simulated receiver controls). These are opt-in
live experiments, not part of the hermetic CI aggregate. Existing core packaging
tests and generated-view parity remain separate checks.

After native collection, terminate only owned participant sessions. Record
worker report cleanup performed by the parent, independently of later operator
cleanup. Remove any exact temporary skill binding/trust addition owned by the
experiment and preserve preexisting settings. Retain blocked reports, immutable
inputs, native evidence and failure receipts. Do not delete a user deliverable
or unresolved report merely to make the directory empty.
