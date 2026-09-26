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

Design collection-based entry points. Inspect query/DML placement and
transaction-wide consumption under realistic bulk input, including existing
automation, ordering, duplicate handling, partial-success policy, and useful
errors. A single-record unit test cannot prove bulk safety.

In LWC, preserve public and wire-data ownership and use the actual cache-refresh
mechanism for the source. Check asynchronous success, failure, stale results,
and rendered states. JavaScript doubles do not establish Apex execution,
permission behavior, governor use, or org behavior; exercise those boundaries
in an identified disposable org when required.

Apex class, trigger and metadata API names are org-wide unless a package
namespace prefix qualifies them; check the org and installed packages for a
clash before choosing one. In a managed package, a `global` member is a
permanent contract once released, so prefer `public` until a subscriber needs
it. Without a package namespace, LWC components share the org's default `c`
namespace.

Model stored data in the org's schema: extend an existing standard or custom
object before creating one, and choose field types, required flags, uniqueness,
lookup or master-detail relationships and sharing deliberately; renaming a
custom field's API name breaks the code, reports and integrations that use it.
Keep configuration in custom metadata types, which deploy with the code, rather
than in records.

## Service discovery

Before choosing component, tab or app names, list what the target org already has
(`sf org list metadata --metadata-type LightningComponentBundle`, `CustomTab`,
`CustomApplication`). A Tooling query on `CustomTab.Name` returns INVALID_FIELD,
so use the metadata listing for tab evidence. Treat another ShipLoop run against
the same org as a naming constraint: pick names it does not use.
Separate the deploy from each visibility step (permission-set assignment, app or
tab access): each is its own command with its own authorization, planned by name
at release-plan.

When Salesforce is an affected service boundary, apply the conditional
[service discovery guide](../service-discovery.md). Record the observed selected
tool or supported route, current org/role evidence, and the separate authority
needed for metadata/schema, configuration, and record CRUD. An MCP inventory or
developer deployment identity does not establish the runtime caller's access.
For incremental work, reconcile prior accepted intent, current local source or
metadata definition, observed org state, and the requested delta; preserve
unrelated fields and automation. A safe authorized metadata/state read is
discovery evidence, not authority to mutate the org.

For each runtime read, record sharing, object CRUD, and field-level security
(FLS) separately. `with sharing` alone does not establish CRUD/FLS enforcement.
If caching is selected, identify its actual native owner and refresh mechanism:
do not attach generic invalidation plumbing to Apex wire results or Lightning
Data Service without verifying the selected source's supported refresh path.
For an asynchronous metadata deployment or background operation, an accepted
request/ID is not final status; retain the terminal status and authorized
read-back.

Example: before adding `ReviewStatus__c`, inspect the selected object's current
metadata and preserve an observed `Consent__c` field and automation. Plan an
additive change, keep remote records authoritative through the current runtime
adapter, leave a cache conditional on authorization/invalidation evidence, and
verify the final metadata/status read-back for the intended role.

Apply [target-native test selection](../repeatable-test-suites.md#select-target-native-tests)
to the affected repo/org metadata and actual deployment route. LWC Jest checks
components locally; Apex tests execute in the org; browser checks observe the
Lightning consumer. None substitutes for the others' required boundary.
Select Apex coverage for changed or affected Apex behavior, or when the actual
deployment/packaging/CI gate requires it. Check the payload, target environment,
effective test level and applicable coverage rule rather than inferring them
from an org label. A verified LWC-only development deployment with no affected
Apex and no Apex test gate may exclude Apex tests; do not add Apex or empty test
classes to fill an inventory. Reopen that exclusion when its basis changes.
[LWC testing](https://developer.salesforce.com/docs/platform/lwc/guide/testing)
and the [deployment command's test-level contract](https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_deploy_start.html)
are starting points; verify the rules for the operation actually selected.

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
