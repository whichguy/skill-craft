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

A consumer entry is source metadata, not a side effect. `lightning__Tab` in a
component's `js-meta.xml` only makes the component eligible for a tab; it creates
no tab anyone can open. Plan the entry as files at step-plan: a `CustomTab`
(`tabs/<Name>.tab-meta.xml`) and, when the design needs one, an app
(`applications/<Name>.app-meta.xml`) that lists the tab, plus the permission set
or profile visibility that shows them. Confirm the tab with
`sf org list metadata --metadata-type CustomTab --target-org <alias>` and look
for its API name. The Tooling `CustomTab` query returns no rows for a Lightning
component tab and would stay red after a good deploy. Run that confirm once at
release-check, beside `sf project deploy validate` (the dry-run), so its
"not there yet" output is on record before the real deploy. At release-plan,
`consumer_entry.how` names the App Launcher entry and its URL path
(`/lightning/n/<TabApiName>` for a component tab), and `sources` lists the tab
and app files.

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

ShipLoop judges a focused Apex test from the runner's own pass or fail mark on
the line that names it, so record the command with a reporter it can read:
`sf apex run test --target-org <alias> --class-names <TestClass> --synchronous
--result-format tap` prints an `ok` or `not ok` line per test, while the default
table and `--result-format human` put the outcome word after the test name,
which ShipLoop does not read, so a focused command that uses them is refused as
unread. An Apex test runs the code already in the org, so on the item's base it
cannot fail unless the command deploys the tree first: name each new org-bound
test in the test result's `red_na` with that reason, and let the candidate run
and the mutation check carry the proof.

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

Open that browser session from the org's existing CLI authentication rather than
asking the user to sign in: `sf org open --target-org <alias> --url-only --path
<page>` prints a one-time front-door URL for the page, which a browser tool can
open directly. At discovery, run it once (without opening the page) to prove the
route, and record the alias and page path. Keep the URL out of evidence and
logs: it is a session credential. Ask the user only when the CLI has no working
authentication for the target org.

## Tool state

The `sf` CLI writes its own state inside the project: `.sf/` (org source tracking, caches) and `.sfdx/`. Both belong in
`.gitignore`, never in a commit. `sf project generate` writes a `.gitignore` that lists them; a project written by hand
adds the two lines itself. Unignored, they change whenever an `sf` command runs, and ShipLoop's checks read them as
product changes (a live run's Improve review was refused for `.sf/orgs/<id>/localSourceTracking` files).

## Consumer entry access (read-only probe)

A deployed tab or app is hidden from a user whom no profile or permission set
grants it: the URL path answers "Page does not exist" and App Launcher lists
nothing, although the metadata is in the org. Probe it read-only and grant
nothing; a missing grant is a prerequisite with its owner, not a step to take.

At prepare, name the consumer user and what they hold:
`sf data query --target-org <alias> --query "SELECT Id, Username, Profile.Name FROM User WHERE Username = '<username>'"`
(the username `sf org list` shows for the alias; not `sf org display`, whose
output can carry a session token), then
`sf data query --target-org <alias> --query "SELECT PermissionSet.Name, PermissionSet.IsOwnedByProfile FROM PermissionSetAssignment WHERE AssigneeId = '<user id>'"`
(the profile appears as the permission set it owns). A new tab or app is
visible only through a profile or permission set that names it: record that
grant under ## Access and accounts, with who may create and assign it.

At release-check, rerun both and query the tab's visibility for those
permission sets:
`sf data query --target-org <alias> --query "SELECT Name, Visibility, Parent.Name FROM PermissionSetTabSetting WHERE Name = '<TabApiName>' AND ParentId IN (SELECT PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId = '<user id>')"`.
`DefaultOn` or `DefaultOff` is visible; no row is hidden, so after the release
the user cannot open the tab unless the release itself grants it (a permission
set in the candidate and its assignment, each planned by name at release-plan).
Check the app and the Apex classes the page calls the same way, through
`SetupEntityAccess` rows (`SetupEntityType` `TabSet` for an app, `ApexClass`
for a class) for those permission sets. Field names move between API versions:
confirm them with `sf sobject describe --sobject <Object> --target-org <alias>`
before relying on a query. A gap the run may not fix stays open with its
owner, and release-verify's person ask starts there: step 1 is the App
Launcher entry and its URL path, and what to answer when the page does not
exist.
