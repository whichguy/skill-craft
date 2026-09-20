# ShipLoop discovery handoff follow-up

```mermaid
flowchart LR
    A[Discovery packet] --> B[Paginated source inspection]
    B --> C[Exact completion result]
    C --> D[Accepted evidence references]
    D --> E[Planning context collector]
    E --> F[Fresh conditional planner]
```

The previous sample left ambiguity/pagination unexercised and omitted a receipt-log
locator. Existing policy already requires supporting locators; this follow-up
improves its placement and tests the actual producer-to-consumer boundary.

## Plan and implementation

The [retained plan](../test/experiments/shiploop_connected_knowledge_followup/control/PLAN.md)
compares the minimal change with adding more prose, a validator or another stage.
ShipLoop 0.18.13 directly routes the existing Discovery evidence handoff section
only to discovery and research. Discovery's existing handoff duty is a separate
paragraph from runtime-state guidance; research uses the same exact route label.
No new policy, schema, stage, connector or remote-fetch implementation is added.

The selective routing regression covers both relocated normal and pending-Improve
packets. The stronger fictional fixture exposes a paginated directory and
fetch-only readers, with the current Review Gateway record beyond the first page
and a same-name Analytics record on the first. Permitted response payloads are
retained so an independent consumer can inspect the source evidence.

The [predeclared protocol](../test/experiments/shiploop_connected_knowledge_followup/control/PROTOCOL.md)
requires the fresh reader's exact completion result, same run/action provenance,
actual local collection, a missing-receipt negative control and a cold consumer.
All Improve and intervening stages are synthetic experiment setup, not workflow
execution claims. The original 0.18.12 experiment remains unchanged.

## Evidence and limits

The unchanged baseline at `04c0c56e131bf1a12b115977da2bb06c30a57ece` passed
32 guidance tests, 8 reference-routing tests and the smoke aggregate. Preliminary
fixture calibration passed its 12 calls with input hashes unchanged. The fresh
fixture baseline passed its one narrow case-ID-normalization test; it proves no
remote behavior. Candidate checks passed: 33 guidance, 8 reference-routing and
9 planning-context tests, the smoke aggregate, generated-view parity and 20/20
marketplace checks. The tested source fingerprint stayed unchanged throughout.

The fresh producer followed the returned directory cursor and inspected both full
Orion definitions. It correctly selected the Review Gateway and approved manual
review policy while retaining the unavailable Teams reader and runtime/API gaps.
It explicitly declared the note, baseline and receipt log. The actual collector
accepted that exact result with matching action provenance and content hashes;
removing only the receipt in a disposable copy produced a missing-reference error.
The frozen 110-file package and protected fixture inputs remained unchanged.

The cold consumer retained the correct manual-review policy, Gateway state boundary,
Teams limitation and conditional implementation gates. It omitted the competing
Analytics definition and obsolete-proposal distinction: the consumer result is
**partial**, despite successful evidence transport. The unchanged output and
[independent assessment](../test/experiments/shiploop_connected_knowledge_followup/observed/ASSESSMENT.md)
retain those failed criteria. The consumer received generic synthetic W1 context
and a collected implementation brief, not an actual Navigator plan-stage packet.
Existing guidance already requires relevant definitions and decisions in affected
item context; this sample does not isolate a production planning defect or warrant
another prompt rule. A future study should exercise the real plan-stage boundary.
Full evidence is in the
[experiment record](../test/experiments/shiploop_connected_knowledge_followup/README.md).
The initial transport-helper calibration exposed missing synthetic setup result
records. The helper was corrected and calibrated before the participant's actual
transport; both failed and corrected calibration receipts are retained. No
participant output was repaired or supplemented.

MCP resources support paginated discovery and host-selected context interfaces;
that supports testing capability limits without hardcoding a universal reader.
[MCP resources specification](https://modelcontextprotocol.io/specification/2025-11-25/server/resources).
The new fixture and candidate are a follow-up, not an A/B comparison or measured
prompt-quality improvement. No live MCP protocol/authentication, corporate tenant
coverage, full ShipLoop/Improve execution or generated application is claimed.
