Assignment reminder: prepare worker/audit-topic for the named parent target. Do not
accept it into the parent checkout.

Worker checkout: <WORKER_CHECKOUT>
Required target SHA: <TARGET_SHA>
Target source remote: <PARENT_TARGET_REMOTE>
Report path outside this checkout: <REPORT_PATH>

Your configured upstream is deliberately not the integration target. Fetch the named
remote, verify the exact target object, then merge or rebase that SHA into your worker
branch and record which operation you chose. Resolve only conflicts you own. Run:

python3 -c 'from app.audit import ENABLE_AUDIT; from app.retry import RETRY_MODE; assert ENABLE_AUDIT is True and RETRY_MODE == "bounded"'

Write a self-contained report at the report path. It must name this worker assignment,
worker checkout/source path, advertised worker ref refs/heads/worker/audit-topic,
worker HEAD, target SHA, source remote, chosen sync operation, contribution, validation
outcome, prepared (not accepted) state, recommended next action and unresolved decisions.
Do not push, modify parent checkout, accept integration or claim target currency beyond
observed state.

In the native final receipt, briefly include the same assignment reminder, contribution,
requested/actual target, sync/conflict/tests, prepared state, report reference, next
action and unresolved decisions. Do not invent commands or unverified success.
