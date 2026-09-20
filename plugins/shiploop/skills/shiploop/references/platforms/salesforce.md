# Salesforce development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when
the runtime or boundary changes. Identify the Apex/LWC boundary, transaction
entry point, API version, and permission context. Verify the selected API
version and supported access mode before relying on a default; do not copy an
obsolete assumption that all work is system mode. Record sharing, object
permissions, and field permissions as separate requirements. Use supported
user-mode operations or deliberate field-sanitization and error behavior as
appropriate; `with sharing`, a visible control, or a passing mock alone does
not establish CRUD/FLS enforcement. [Salesforce's secure Apex guidance](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security.html)
is the version-sensitive starting point.

For org identity or access discovery, use supported non-mutating Salesforce
CLI/API probes and approved sanitized preflight records. Builders and reviewers
must not read local auth/session stores (including `.sfdx/*.json` and `.sf` auth
files), decode them, or retain or report token-bearing contents. Tool
configuration metadata without session material remains permitted.

Design collection-based entry points. Inspect query/DML placement and
transaction-wide consumption under realistic bulk input, including existing
automation, ordering, duplicate handling, partial-success policy, and useful
errors. A single-record unit test cannot prove bulk safety.

In LWC, preserve public and wire-data ownership and use the actual cache-refresh
mechanism for the source. Check asynchronous success, failure, stale results,
and rendered states. JavaScript doubles do not establish Apex execution,
permission behavior, governor use, or org behavior; exercise those boundaries
in an identified disposable org when required.
