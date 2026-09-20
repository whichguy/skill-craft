# Remote-service discovery pilot, 2026-09-19

Purpose: help design ShipLoop's first-part discovery contract for remote metadata,
business services, optional caches and asynchronous cooperation. This is a
two-case, four-agent synthetic drafting study with two independent blind judges.
It does not invoke the ShipLoop runtime, execute cache/application code, connect
to a remote account, or establish production readiness.

- `candidate-cue.md`: exact proposed addition; not active skill guidance.
- `proposed-entry-cue.md`, `proposed-reference.md`: later unmeasured revisions,
  including local/remote observability ownership, authentication event coverage
  and reuse of existing logging. They do not change the frozen experiment.
- `case-schema.md`, `case-async.md`: hypothetical case facts, each with a local-only
  negative control.
- `PROTOCOL.md`: predeclared comparison scope and eight-criterion rubric.
- `frozen/`: current duty/reference slice, baseline plus cue, full v3 stage strings
  for audit, selected source hashes, case/protocol copies.
- `arms/01` through `arms/04`: neutral launch instructions, exact inputs and actual
  agent-written reports. Each agent started without parent conversation history.
- `review/`: paired neutral report bundles and independent judgments. Candidate
  appears second for the schema case and first for the async case.
- `coordinator/`: input/report hashes, assignment map and coordinator attestations
  of actual native completion. These records are not cryptographic host receipts.
- `RESULTS.md`: findings and limitations, populated after judgments complete.

The frozen baseline contains 43,480 characters. The cue adds 3,587 characters
(about 8.25%). This is prompt text size, not measured token usage. The baseline
is a focused discovery/research duty and reference slice; it is not an exact
assembled v3 action packet. No performance or general-superiority conclusion
is justified. Both cases explicitly supply the defects to reason about, so this
study tests synthesis/coverage more than unaided discovery of hidden defects.

To inspect or repeat, read the protocol, create a new study directory, and give
fresh agents the same input bytes with new report destinations. Do not overwrite
these measured reports or reinterpret a later cue as the measured candidate.
Reports and judgment prose are model outputs requiring substantive review.

The initial existing-code baseline passed 42 tests:

```sh
python3 -B test/shiploop-discovery.test.py
python3 -B test/shiploop-research-template.test.py
python3 -B test/shiploop-reference-routing.test.py
```

Run those commands from the skill-craft repository root. They are scoped code
checks, not proof that the proposed prompt improves discovery or that remote
services behave as described. Active skill source was only read by this task.
