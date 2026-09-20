# Connected discovery and evidence handoff follow-up

A new, single-attempt offline sample for ShipLoop 0.18.13. This tests a real
Navigator discovery packet and the actual local planning-context collector with
fictional paginated internal knowledge. It does not modify the earlier experiment
or establish an A/B effect from the prompt change.

## Planned change and experiment

[PLAN.md](control/PLAN.md) records the alternatives and minimal routing decision.
[PROTOCOL.md](control/PROTOCOL.md) defines observations, bounds and the cold-consumer
boundary before the attempt. The only production change directly routes the
existing Discovery evidence handoff section to discovery and research and separates
that completion duty from conditional runtime-state guidance.

The fixture uses a directory search with two pages and fetch-only Slack, intranet
and private-Git readers. The first page contains Orion Analytics and an obsolete
proposal; the current Orion Review Gateway appears on page two. Teams is unavailable.
All source content and identities are fictional. Returned payloads are expressly
permitted to remain in this fixture's receipts.

## Observed evidence

| Boundary | Outcome | Decisive retained evidence |
| --- | --- | --- |
| Reader calibration | Supported: 12 calls cover pagination, full payload retention, unsupported operations, Teams gap, invalid cursor and rejected public route | [Reader preflight](observed/calibration/reader-preflight.json) |
| Fresh local baseline | Supported: one case-ID normalization test passed; four initial inputs unchanged; no adapter call | [Baseline](observed/producer/BASELINE.txt) |
| Actual packet producer | Supported: both pages and full contrasting entity records inspected; current approved manual-review policy selected; provenance, Teams and implementation gaps retained | [Discovery](observed/producer/DISCOVERY.md), [receipts](observed/producer/receipts.jsonl), [packet](observed/producer/PACKET.md) |
| Evidence handoff | Supported: index points to exact note heading, note identifies source/receipt locators, result explicitly declares required local files | [Index](observed/producer/SHIPLOOP.md), [exact result](observed/producer/RESULT.json) |
| Actual collection | Supported: exact accepted result, declared artifacts, action provenance and hashes; no missing required material; producer inputs unchanged | [Checks](observed/transport/checks.json), [manifest](observed/transport/collection.json), [accepted discovery](observed/transport/accepted-discovery.md) |
| Missing-receipt control | Supported: deleting only the copied receipt produces only the expected missing-reference diagnostic | [Negative control](observed/transport/negative-missing-receipt.json) |
| Cold consumer | Partial: correct policy, state boundary and implementation gates retained; competing Analytics definition and obsolete-proposal distinction omitted | [Cold launch](observed/cold/LAUNCH.md), [unchanged plan](observed/cold/PLAN.md), [independent assessment](observed/ASSESSMENT.md) |

The first **helper calibration** failed because synthetic setup transitions were not
saved individually. It is retained in [failed calibration](observed/calibration/transport-calibration.json).
The corrected helper saves each synthetic transition and remaps copied result
records for the negative control; [corrected calibration](observed/calibration/transport-calibration-fixed.json)
passed before actual producer transport. Calibration uses handcrafted output and
is not participant/model evidence. The participant's output was never repaired.

The candidate passed 33 guidance tests, 8 routing tests, 9 planning-context tests,
the smoke aggregate, generated-package parity and all 20 marketplace checks.
[Check summaries](observed/checks/candidate-checks.json) retain raw-log hashes and
tails; [identity comparison](observed/checks/candidate-identity.txt) proves the frozen
candidate did not change during checks. [Integrity](observed/integrity.json) confirms
the 110-file frozen package, protected fixture inputs and original experiment
bytes, and records hashes of retained outputs. Only the experiment helper/report
and observed artifacts were finalized after candidate tests; production/test files
are identical to the tested candidate.

The independent assessment accepts the routing change and actual transport proof,
but scores the cold output partial. Its 336-word plan omits Analytics/Rina and the
historical unapproved proposal, although it opened the supporting evidence. Those
predeclared consumer criteria failed. No participant was retried or repaired.
The consumer used generic synthetic W1 context and a collected implementation
briefing, not the actual Navigator plan-stage packet; this cannot isolate a
production plan-stage defect. Existing guidance already requires relevant
definitions and decisions in affected item context. No further production change
is warranted by this single sample; a future study should exercise that real
planning boundary before attributing omissions to the production architecture.

## Reproducing a new attempt

Use a new external directory, not this immutable observed tree. Copy `fixture/` and
`control/` together to that directory. Running `control/preflight.py` creates a new
`calibration/` sibling and refuses an existing one. Then run `control/prepare.py`
with `--source /absolute/repo/skills/shiploop`, `--fixture /absolute/copied/fixture`
and `--output /new/external/sample`. The source must be in this monorepo because
preparation reuses the existing handoff experiment's packet-positioning helper.

Supply a fresh fixture baseline before executing the generated participant launch.
Run one isolated reader using the actual packet and record its own actions; do not
copy these observed answers. Once it finishes, `control/collect.py --sample
/absolute/new/sample` submits its exact result, performs synthetic transport setup
and invokes the real collector. It must not be rerun on an already advanced sample.
Give a separate fresh consumer the generated brief and declared artifact paths;
record its own plan without providing expected answers or discovery conversation.

Retained outputs preserve their original absolute paths and bytes, including one
whitespace-only raw baseline-output line flagged by `git diff --check`. All other
staged files pass the whitespace check. For reading this
archive, original `sample/case/workspace/*` files map to `observed/producer/*`, the
original `sample/case/receipts.jsonl` maps to `observed/producer/receipts.jsonl`, and
the generated brief maps to `observed/transport/planning-brief.md`. Those original
external paths are observation locators, not portable replay inputs.

## Limits

The candidate and fixture changed together; this demonstrates a successful
producer/transport path and a partial cold-consumer outcome, not measured quality
improvement or general model compliance.
Prelude/intervening Navigator stages and every Improve receipt are synthetic setup.
No live MCP protocol, authentication, corporate coverage, full DAG, standalone
Improve, generated application, or remote state-management behavior is proven.
The cold plan must remain conditional because the actual Gateway API, authorization,
acknowledgement, idempotency, UI and integration-test contracts are not available.
