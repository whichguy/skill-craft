# Conditional platform guidance candidate

Status: research-stage additions to the coding-guidance candidate, not installed ShipLoop policy. These cards express platform contracts and checks; local mechanism probes do not establish that adding the words improves model performance. The study harness should provide only the selector and relevant cards below, excluding this observer status. Existing project conventions and accepted requirements remain authoritative.

## Selector

Identify the actual runtime, deployment artifact and affected boundary. Load only the relevant platform card; a mixed application may need more than one. Record the installed/supported version and source locator, the applicable contract, and the check that can observe it. Reuse the project's existing tools before proposing another dependency. Preserve the main coding core and active stage's authority.

## UI development

Preserve the accepted component structure, interaction behavior and visual system. Separate editable drafts, request state and accepted server state; identify which result may update each surface. For overlapping requests or changing identity, prevent superseded results and errors from replacing the latest accepted state. Cancellation alone does not undo a server effect.

Prefer native controls or maintained accessible primitives before custom interaction code. Verify accessible names, keyboard operation, focus ownership/return, pending/error states and applicable reduced-motion behavior in the composed UI. Test visible outcomes through stable semantic queries and controlled response completion; avoid arbitrary sleeps and implementation selectors where a user-facing contract exists. DOM or ARIA assertions are not a complete accessibility audit.

Keep feature responsibilities and dependency direction explicit without copying a whole application's folder tree. Start with local state when appropriate; introduce shared stores, memoization or virtualization only for a demonstrated need. Validate the production artifact's assets, routing and host restrictions where relevant; a development server is not deployment evidence.

## Google Apps Script development

Identify server-side Apps Script, HTML Service client code and their serialization/RPC boundary. Treat `google.script.run` as asynchronous: define success, failure and superseded-response handling, and exchange supported plain data. Keep authority and validation on the server. Record web-app execution identity, required OAuth scopes, trigger context and the specific deployment being exercised; do not infer these from local JavaScript tests.

Minimize expensive service round trips by reading and writing suitable ranges in batches, preserving formulas, shape and unrelated data. Bound work for the applicable quotas/runtime and retain restart progress when the operation requires it. Measure service-call reduction separately from hosted latency and quota success.

For shared mutable data, use the appropriate supported lock scope around the critical section and release it on failure. Specify retry identity and partial-commit recovery separately: a lock is not a transaction or a durable exactly-once guarantee. Caches are expendable accelerators, not authoritative storage. Small read-only work does not automatically need caching, locks or a queue. Verify host-only behavior in a disposable authorized Apps Script project.

## Salesforce development

Identify the Apex/LWC boundary, API version, transaction entry point and permission context. Treat record sharing, object permissions and field permissions as distinct requirements. Select supported user-mode operations or deliberate field sanitization/error behavior as appropriate; `with sharing`, a visible control or a passing mock does not alone prove CRUD/FLS enforcement. Keep required system-mode work narrowly justified.

Design collection-based entry points: inspect query/DML placement and transaction-wide consumption under realistic bulk input, including interactions with existing automation. Preserve ordering, duplicate handling, partial-success policy and useful error details. A single-record unit test cannot prove bulk safety, and a generic enterprise framework is not required to process a collection.

In LWC, respect public/wire data ownership and the actual cache-refresh mechanism for the data source. Test asynchronous success, failure, stale results and rendered states. Jest/JavaScript doubles establish client behavior, not Apex execution, platform limits or org security. Complete those checks in an identified disposable org with deliberate permission fixtures and actual Apex assertions; retain unexecuted boundaries explicitly.

## Python development

Use the supported interpreter and repository's existing packaging, test, lint and type-checking conventions. Define mutable state ownership, iterator consumption, exception contracts and resource lifetime where they affect callers. Use context managers or an appropriate cleanup stack so partial setup and failures release already acquired resources; avoid shared mutable defaults and leaked test state.

Prefer argument-list subprocess APIs when a shell is unnecessary. Check status and timeouts and preserve relevant failure causes. Async code must preserve cancellation and bounded task ownership; cleanup must not silently convert failure into success. Test the actual boundary with representative malformed inputs, cancellation/failure paths and isolated temporary resources.

Use parameterized or property/state-based tests when their invariant and independent oracle are meaningful. Do not require another framework for a few concrete cases. Treat lint, typing and behavioral tests as complementary. Inspect automated fixes against the accepted contract, including empty inputs, iteration side effects and errors; unsafe fixes require explicit review and relevant tests. Select rules deliberately instead of enabling every rule as a universal standard.

## Bash script development

Declare and verify the intended shell/version and external-command assumptions. Preserve argument boundaries with quoted expansions and arrays where the dialect supports them; avoid string-built commands, `eval`, and parsing human-formatted output. Test spaces, wildcard characters, empty arguments, newlines and leading-option values where relevant. Do not assume GNU utility options or a recent Bash on every host.

Handle expected failure explicitly, including pipeline components and functions invoked in conditionals. `set -e` has contextual exceptions; `set -euo pipefail` is not a proof that every error aborts or that every nonzero status is an error. Preserve the meaningful exit status through cleanup, send diagnostics to stderr, and keep machine-readable stdout usable.

Use isolated temporary directories and scoped traps for resources the script owns. Verify cleanup after controlled failures and signals where required; no trap guarantees cleanup after every termination. Run the existing static checker and actual shell tests, including negative controls. Keep orchestration small; reconsider Python or another existing runtime when parsing, state or recovery complexity outweighs shell's simplicity.
