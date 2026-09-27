# Google Apps Script development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when
the runtime or boundary changes. Identify Apps Script server code, HTML Service
client code, and their serialization/RPC boundary. Treat `google.script.run` as
asynchronous: exchange supported plain data and define success, failure, and
superseded-response handling. Keep validation and authority on the server.
Record the exercised web-app identity, OAuth scopes, trigger context, and
deployment; local JavaScript tests do not establish them.

Minimize service crossings by batching compatible range reads and writes while
preserving formulas, shape, and unrelated data. [Apps Script best practices](https://developers.google.com/apps-script/guides/support/best-practices)
and current [service quotas](https://developers.google.com/apps-script/guides/services/quotas)
inform the applicable budget; do not hard-code remembered limits. Bound work
and retain restart progress when an operation requires it.

Executions of one script run concurrently: two users' `google.script.run` calls
can overlap, up to a [per-user cap on simultaneous executions](https://developers.google.com/apps-script/guides/services/quotas),
and nothing serializes them per project. Properties are not documented as
atomic, so a read-modify-write of a counter, a game state or a seat count is a
race unless it runs inside a [LockService](https://developers.google.com/apps-script/reference/lock)
lock (`getScriptLock`, `getUserLock` or `getDocumentLock`, then `tryLock` or
`waitLock`); properties also have per-value, per-store and daily
[quotas](https://developers.google.com/apps-script/guides/services/quotas).
`google.script.run` is [asynchronous](https://developers.google.com/apps-script/guides/html/reference/run):
results arrive in a success or failure handler, and a `Date`, function or DOM
element (other than a form) cannot cross it. For identity,
[`Session.getActiveUser()`](https://developers.google.com/apps-script/reference/base/session)
returns a blank email wherever the script runs without that user's
authorization, including a web app deployed to execute as the developer, simple
triggers and custom functions; in a web app executing as the developer,
`getEffectiveUser()` is the developer. Google publishes no full table of results
for every deployment and account type, so probe the deployed identity rather
than assuming it.

For shared mutable data, use the supported lock scope only around the critical
section and release it on failure. Define retry identity and partial-commit
recovery separately: a lock is not a transaction or an exactly-once guarantee.
Caches are expendable derivatives, not authority. Small read-only work does not
automatically need a lock, cache, or queue. Verify host-only behavior in an
authorized disposable project.

Every server file in a project shares one global scope, so a top-level name in
one file can silently replace another; keep top-level code to declarations and
group related functions under one namespace object or a clear prefix. A
function name ending in `_` is private: `google.script.run` and library users
cannot call it. A library is reached only through its chosen identifier, so
check that identifier against the project's own globals. HTML Service client
code has a separate browser global scope.

When a sheet holds data, its header row is the schema: address columns by
header name, not position, and add a column through the same header change the
readers expect. Properties are small string key-value stores scoped to the
script, user or document; choose the scope deliberately, prefix the keys, and
keep large or tabular data out of them.

## Projects deployed with mcp-gas-deploy

A project deployed with mcp-gas-deploy carries a vendored layer. `require.gs`
loads modules declared as `_main(module, exports)` with `__defineModule__`;
`module.exports.__events__` routes `doGet`, `doPost` and triggers to module
handlers that pass on requests they do not own; pages include
`common-js/gas_client` and call the server as `srv.<module>.<fn>()`; and
`ConfigManager` wraps script, user and document properties. New code follows
these forms.

The `srv` proxy is not a trust boundary. It sends a client-built dispatch
expression to the top-level `apiExec`, which runs it with `new Function`, so
anyone who can open the web app can run any server code as the identity the
deployment executes as, including reading every stored game or record. Checks
inside module functions do not stop a caller who skips them. When the product
must keep information from a user or enforce per-user authority, the plan names
how callers are kept from running arbitrary code and a probe that sends a raw
`apiExec` call as an ordinary user and must fail to read hidden data. If the
plan cannot close it, report that requirement blocked instead of planning
around it.
