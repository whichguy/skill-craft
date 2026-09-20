# Replaying the compact handoff cases

These are prompt/input fixtures, not a dispatcher. Run them through the normal
native parent harness. Use the registered [case protocol](../HANDOFF-CASES.md)
and report all dimensions separately, including retained failures.

The current skill source is [skills/ask-agent/SKILL.md](../../../../../skills/ask-agent/SKILL.md).
This campaign's frozen U14 card has SHA-256
`a7fd14ba19cb00bd011980ac00334ab2a719040b0ca7b6d9034a074cdfe191d3` and is frozen at
[frozen-U14/ask-agent/SKILL.md](/Users/dadleet/Documents/Codex/experiments/ask-agent-handoff-20260918T171044Z/frozen-U14/ask-agent/SKILL.md).
The nearby `usability/ask-agent/SKILL.md` is a historical U9 fixture and must not
be used as the current handoff candidate.

Before each campaign, freeze the intended skill, record its SHA-256, host version/model,
exact prompts and input hashes, and register the outcomes and time limit.
Expose that frozen card using the host's supported discovery mechanism in a
fresh disposable project for each case. Keep oracles and event exports outside
the participant inputs. Do not place this README or the grading protocol in the
participant project: they contain expected outcomes.

For every case, copy `preserve.txt` to the project root. Use the exact matching
request from `prompts/`; do not append the expected answers.

| Case | Project setup | Operator interaction |
| --- | --- | --- |
| F1 | Copy both `tasks/` files to the root and all 36 `fixtures/invoices/` files to `invoices/`; create empty `handoffs/`. | Start an interactive parent with `prompts/F1.txt`. After its actual $300 result and before the worker finishes, submit `prompts/F1-followup.txt` using native user input. If that window is missed, mark responsiveness unobserved; do not send a late message and count it as overlap. |
| F2 | Copy `parent-task.md` to the root. Put `worker-task.md` and invoices 01–24 under `north/`; put the same worker task and invoices 01–12 under `south/`. Replace only South INV-08's `Tax rate: 5%` with `Tax rate: NOT PROVIDED`. Create empty `handoffs/`. | Submit `prompts/F2.txt`; keep the parent alive through both actual returns. |
| F3 | Only the sentinel is needed. | Submit `prompts/F3.txt`; observe native delegation, inline 42, and absence of model writes. |
| F4 | Copy `controls/inconsistent.md` to `handoffs/inconsistent.md`. Copy `controls/simulated-receipts.md` to the root, replacing `<CASE_ROOT>` with this project's absolute path. Leave `handoffs/missing.md` absent. | Submit `prompts/F4.txt`. This is a simulated receiver control and must launch no worker. |

Use one participant per host at a time, at most eight minutes per participant,
and one executed attempt per registered row. Use native cancellation for owned
tasks that exceed the bound. A correction requires a newly frozen candidate
and separate registration; it never replaces a failed original row.
These are operator experiment controls; Ask Agent imposes no such runtime caps.
The invoice task's no-further-agents restriction is a fixture constraint, not a
skill default. U13 permits further native delegation in ordinary work, but this
campaign does not exercise nested workers.

Record native parent/child locators, observable messages/tool calls and outputs,
report-write/completion/read/deletion timing, final receipt word counts, and
how many detail rows entered the parent. Exclude private reasoning from evidence
projections. Confirm input hashes and sentinel contents afterward. Retain blocked
reports, participant outputs and failure evidence; remove only experiment-owned
temporary discovery/trust bindings and terminate only owned sessions.

OpenCode 1.18.31 requires its process-local experimental background feature and
persistent TUI for F1/F2 in the observed configuration. A headless process exit
does not prove a later callback. See the [host evidence](../HANDOFF-RESULTS.md)
for candidate-specific observations and limitations.
