# Independent assessment — connected discovery follow-up

This is a read-only assessment of one offline fixture attempt against the
predeclared protocol. It does not treat the sample as an A/B comparison, a
model-compliance result, or proof of a live enterprise/runtime workflow.

| Boundary / required observation | Assessment | Evidence |
| --- | --- | --- |
| Candidate routing change is direct and selective | Supported | The rendered discovery packet includes `Discovery evidence handoff`; the production catalog routes it only for discovery and research. [PACKET.md](producer/PACKET.md), [shiploop_navigator_v3_prompts.py](../../../../skills/shiploop/scripts/shiploop_navigator_v3_prompts.py) |
| Frozen packet and bounded producer use pagination, permitted readers, contrasting records, and retain source limits | Supported | The producer exhausted the returned cursor, fetched Analytics, the historic proposal, Gateway, ADR and pinned snapshot, and recorded Teams/public limits. [DISCOVERY.md](producer/DISCOVERY.md), [receipts.jsonl](producer/receipts.jsonl) |
| Exact producer result is accepted without repaired references | Supported | The accepted discovery record has the same declared references and the transport check records unchanged result bytes. [RESULT.json](producer/RESULT.json), [accepted-discovery.md](transport/accepted-discovery.md), [checks.json](transport/checks.json) |
| Actual collector preserves declared local evidence, source action and content identities | Supported | The collector reports no missing required inputs and records the note, index, baseline and receipt as evidence-reference artifacts tied to the discovery action and hashes. [collection.json](transport/collection.json) |
| Missing declared receipt blocks the transport | Supported | Removing only the copied receipt yields the expected missing-reference diagnostic. [negative-missing-receipt.json](transport/negative-missing-receipt.json) |
| Cold plan preserves both Orion definitions and the historic-proposal distinction | Failed | The plan retains Gateway policy and gates but omits Orion Analytics/Rina and does not state that the automatic-approval item was an unapproved historic proposal. Both were available in the declared discovery evidence that the consumer opened. [PLAN.md](cold/PLAN.md), [planning-brief.md](transport/planning-brief.md) |
| Cold plan retains approved policy, provenance/Teams limits, and conditional implementation gates | Supported | It identifies ADR-042/manual review, marks the snapshot non-live, keeps Teams and runtime limits, and gates interface, authorization, idempotency, UI and integration evidence. [PLAN.md](cold/PLAN.md) |
| Original 0.18.12 experiment is unchanged | Supported | Integrity records no prior-experiment changes. [integrity.json](integrity.json) |

The cold-plan failure is a participant outcome, not evidence of a production
plan-stage defect. The transport deliberately supplied generic synthetic W1
context and the cold reader did not receive an actual Navigator plan-stage
packet. Existing handoff policy already requires definitions, decisions and open
questions in work-item context and consumer reopening. This single result
therefore supports retaining the explicit discovery/research route and reporting
the cold outcome as partial; it does not justify a new rule, checklist, schema or
production prompt change.

The production diff remains proportionate: it adds the existing handoff locator
to discovery/research, separates the already-existing handoff paragraph from
runtime-state wording, and has selective relocated/pending-Improve routing
coverage. The retained candidate-check evidence is supportive verification, but
does not establish live MCP, authorization, Improve, DAG, or application behavior.
