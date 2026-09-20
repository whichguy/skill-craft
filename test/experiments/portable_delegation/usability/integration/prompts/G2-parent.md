Use the ask-agent skill to prepare, but not accept, a Git integration. You own target
selection, target movement, ordering and acceptance.

Parent checkout: <PARENT_CHECKOUT>
Initial explicit target SHA: <TARGET_A_SHA>
Worker checkout: <WORKER_CHECKOUT>
Worker target source remote: parent-target
Worker report path: <REPORT_PATH>
Frozen concrete child brief: <WORKER_BRIEF_PATH>
Target-B fixture patch: <TARGET_B_PATCH>
Isolated preview checkout: <PREVIEW_CHECKOUT>

Pass the frozen child brief unchanged to one native worker. After collection, apply and
commit TARGET_B_PATCH in the parent target, fetch the advertised worker branch into a
fixture-local ref, and make an isolated preview at PREVIEW_CHECKOUT. Run:

python3 -c 'from app.policy import retry_budget_ok; assert retry_budget_ok(), "retry budget exceeded"'

A clean textual merge is not acceptance. If this semantic check fails, abort/remove
preview, preserve parent target and record refresh/replan. Do not push.
