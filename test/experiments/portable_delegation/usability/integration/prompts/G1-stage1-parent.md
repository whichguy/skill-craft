Use the ask-agent skill to delegate preparation of a Git integration. You own the
target, ordering and acceptance decision. Do not accept or push in this stage.

Parent checkout: <PARENT_CHECKOUT>
Parent branch: integration-target
Explicit target SHA: <TARGET_SHA>
Worker checkout: <WORKER_CHECKOUT>
Target source remote in worker: parent-target
Worker report path outside both checkouts: <REPORT_PATH>
Frozen concrete child brief: <WORKER_BRIEF_PATH>

The target is intentionally ahead of origin/main; do not replace it with a worker
upstream. Pass the frozen child brief at WORKER_BRIEF_PATH unchanged to one native
worker. After it returns, verify receipt/report references, retain assignment,
contribution, target, sync, validation and unresolved decisions in the handoff, and
state PREPARED_PENDING_ACCEPTANCE. Do not merge, fast-forward or push. A later fresh
parent must reconstruct work from report rather than launch memory.
