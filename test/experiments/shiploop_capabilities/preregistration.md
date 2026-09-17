# Capability selection study: execution protocol

Prepared before worker trials on September 14, 2026. The parent plan is
`docs/shiploop-capability-experiment-plan-2026-09-14.md`, frozen in the task-owned
study root with its SHA-256. Baseline is `a813561bd024ca47b504f0448445866eba685f6e`.
The candidate instruction is extracted verbatim from the plan. No production
ShipLoop prompt, installed skill, or global integration is changed by this study.

## Pre-run clarifications

- The execution MCP named `workspace` is experiment instrumentation, not a
  capability selected by the worker. Do not count using this mandatory adapter
  as evidence that an agent discovered or benefited from an MCP. Count optional
  filesystem-MCP probes and actual Apps Script operations separately.
- The launcher restricts workers to its supplied adapter. Its command sandbox
  must deny the coordinator, oracle, other arms, and private evaluation files.
  Path checks alone are insufficient; calibration must attempt a denied read
  through both direct file operations and a subprocess. Any remaining bypass
  makes the affected result exploratory, not controlled evidence.
- Prepared earlier ShipLoop transitions, existing fixture code, initial state,
  and supplied notes are synthetic setup. A public CLI packet is real protocol
  output but does not prove that preceding delivery work ran.
- The worker receives a behavioral SPEC, not the coordinator's mutant inventory
  or a switch to disable defects. Faults are baked into exported source. Correct
  alternate branches and mutant generators remain outside worker-readable roots.
  TEST workers receive fixed correct source and may change only tests and notes;
  the grader applies unseen mutants after execution.
- Cached filesystem-MCP 2026.8.31 bytes from the prior experiment are reused
  identically across paired local arms. Their provenance and hashes are retained.
  This is package reuse, not fresh download/acquisition evidence. Native access
  is allowed and receives equal credit for the same correct observable result.
- Existing `plan-test` and `skill-interop` skill bodies are pinned from the local
  source. An explicitly synthetic obsolete client skill is a negative candidate.
  Skill availability and contents are equal across arms except the preregistered
  D3 procedure-body ablation. A skill read alone does not establish useful use.
- The INNER skill holdout adds a restart-between-retry question; the TEST skill
  holdout starts with an ordinary black-turn check and a cache-priming example.
  They preserve the same server behavior contract. The timing changed case
  reveals a service-authorization question at its second checkpoint; the stable
  case repeats the same environment question with sufficient existing evidence.
- D4 is conditional on preflight establishing a named capability gap. Do not
  invent a restriction solely to force acquisition. If every relevant local
  observation is available through existing routes, mark that mechanism untested.
- Apps Script passed a bounded real project-metadata preflight. The fixed selected
  project is a read-only research example, not an authorized new deployment
  target. Salesforce lacks an established authorized org/target; its two planned
  transfer arms remain blocked and unrun unless that external condition changes.
- The same configured model, `gpt-6-astra` with medium reasoning, runs each arm.
  This fixes the prior experiment setting; it is not a model recommendation.
  Each arm starts fresh; timing arms use two fresh contexts with one cumulative
  allowance. There is no inherited parent conversation or oracle input.

## Outcome criteria

Use the plan's D1–D5 decisions, with evidence fidelity reported independently:
local source, actual local framework, real local HTTP, real MCP invocation,
real service read, deployed behavior, and intended-user behavior. None implies
the next. Preserve zero-benefit results and correct native-tool solutions.

ENV must support its eight-area findings, actual access claim, and distinction
between inspection and application RPC. INNER must pass the specification-derived
oracle on its final source, not merely its own tests. OUTER and OUTER_HOLDOUT
must identify the served candidate mismatch or effective authorization gap and
make the correct readiness decision without asserting a deployment. TEST requires
no false failures on the correct reference and detection of distinct faulty
behavior families; import/setup failures do not count as detections.

`oracle-review.md` freezes the independent cases and any calibration amendments
before worker outputs. Its expected outcomes derive from SPEC, not from the
reference implementation. A reference pass plus corresponding seeded failures
are required before the comparison. Later evaluator corrections are reported
separately and cannot silently replace the preregistered results.

## Limits and retention

The conservative study start is 22:41 UTC, setup stops at 23:11 UTC, no new arm
starts after 01:11 UTC, and the final ceiling is 01:41 UTC on September 15.
Per arm: 900 elapsed seconds, at most 64 observed actions, exploration cutoff at
780 seconds or 56 actions, two candidate capabilities and three experiments.
The final reserve is for reporting and cleanup. No budget resets at handoff.
Four simultaneous workers maximum. Preserve partial results and cleanup receipts.

Record adapter/host-action counts separately from nested MCP/API requests. If
complete nested-request instrumentation is unavailable, state that limitation;
do not infer an HTTP-request or token budget from the host-action cap. Record
actual available usage telemetry; no text-length proxy is total token usage.

Do not retry a worker to obtain a desired outcome. A calibration or launcher
defect may be fixed before worker trials. Any interrupted or invalid actual
trial remains in the inventory with its cause and counts against the run cap.
Keep frozen inputs, invocation metadata, tool receipts, independent grades,
final source hashes, and redacted reports. Do not preserve credentials or private
platform source in repository artifacts.
