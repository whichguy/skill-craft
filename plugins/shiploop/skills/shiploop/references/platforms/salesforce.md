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

For a Lightning consumer, distinguish the org/instance identity from the
feature's authenticated entry: an app, custom tab, component or other supported
page. Use supported navigation (for example a generated `PageReference` URL)
and verify the destination after redirects, with the intended user's role,
visible feature and required interactions. Preserve a non-secret usable route
in the handoff; an instance home alone is not the app link. A custom tab in an
existing shell can be correct; verify a particular app/navigation identity when
the accepted design requires it, without inventing an org-wide branding rule.
Do not hard-code a Salesforce hostname as the universal consumer boundary.
[Salesforce navigation](https://developer.salesforce.com/docs/platform/lwc/guide/use-navigate-basic.html)
and [page types](https://developer.salesforce.com/docs/platform/lwc/guide/reference-page-reference-type.html)
define the supported navigation contract. This supplements the generic
[browser evidence guidance](../testing-and-documentation.md#lightweight-and-browser-checks).
