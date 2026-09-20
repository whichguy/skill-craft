Assignment reminder: prepare `worker/retry-topic` against the explicitly named parent
target, resolving only its own conflict in this isolated worker checkout.

Worker checkout: `<WORKER_CHECKOUT>`
Required target SHA: `<TARGET_A_SHA>`
Target source remote: `<PARENT_TARGET_REMOTE>`
Report path outside this checkout: `<REPORT_PATH>`

Fetch and verify exactly that target. Merge or rebase it into the worker branch. The
`REQUIRED_APPROVERS` conflict must retain the explicit target's value. Run:

`python3 -c 'from app.policy import retry_budget_ok; assert retry_budget_ok(), "retry budget exceeded"'`

Write a self-contained factual report. Do not push, modify parent target, accept the
integration or claim the target will remain current. The final native receipt includes
assignment reminder, contribution, target/sync, conflict, commands/outcomes, prepared
state, report, recommended next action and unresolved decisions.
