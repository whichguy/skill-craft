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

For shared mutable data, use the supported lock scope only around the critical
section and release it on failure. Define retry identity and partial-commit
recovery separately: a lock is not a transaction or an exactly-once guarantee.
Caches are expendable derivatives, not authority. Small read-only work does not
automatically need a lock, cache, or queue. Verify host-only behavior in an
authorized disposable project.
