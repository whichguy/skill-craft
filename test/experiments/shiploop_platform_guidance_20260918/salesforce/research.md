# Salesforce platform guidance: bounded research and local experiment

Date: 2026-09-18
Decision under study: whether ShipLoop should offer a compact, conditional Salesforce card during planning and review when a task touches Apex or Lightning Web Components (LWC).

## Recommendation: pilot a narrow conditional card

Adopt nothing globally yet. Pilot a compact card only when the workspace contains `sfdx-project.json`, `force-app`, Apex, or LWC changes. It names three platform-specific concerns that are not explicit in the generic ShipLoop security, state, and test cards:

1. the independent Apex dimensions of record sharing, CRUD/FLS, access mode, and API version;
2. transaction-wide SOQL/DML budgets under bulk invocation; and
3. LWC identity reactivity plus post-mutation cache invalidation and async test boundaries.

The current candidate guidance is intentionally conditional and warns against needless layers. A Salesforce card should preserve that shape: it is a retrieval cue and evidence checklist, not a demand for a framework, a code analyzer, an MCP server, or new dependencies.

## Proposed pilot card

Use this text only as experiment material until worker trials and real-org evidence support a broader change.

> **Salesforce (Apex/LWC)** — First record the project API version, entry point, and the exact data/cache boundary affected. For Apex reads and writes, distinguish record sharing from object/field permissions and state the chosen access mode. For API 67+ defaults, write an explicit mode at consequential boundaries when it clarifies the contract; for older APIs, use an explicit user-mode or deliberate graceful-degradation approach. Any system-mode or `without sharing` path needs a narrow authorization reason and a real-org denial/allow test. Treat triggers as a separate system-context case. For triggered or collection input, collect IDs/work, query once, mutate collections, and issue DML outside loops; prove the budget at both ordinary and 200-record scale in Apex tests. For LWC complex state, replace the object/array identity (or justify `@track`), await the mutation before invalidating the affected cache, choose `refreshApex` for an Apex wire result and `notifyRecordUpdateAvailable` for LDS-record freshness, and test success, error, and async rendered-state boundaries with the actual LWC Jest runtime.

This card deliberately says **choose the affected cache**. A component with both an Apex wire and LDS record consumers can require both invalidations; a component with only one must not receive a blanket extra call merely to satisfy a checklist.

## Evidence

### Apex access context

The current Salesforce LWC security guide says API version 67.0 and later defaults Apex data operations to user mode and classes to sharing enforcement, while API 66.0 and earlier defaulted to elevated system behavior. It still recommends explicit declarations/access modes for maintainability. It also distinguishes `with sharing`/`without sharing` as record-level only; those keywords alone do not enforce object permissions or FLS. [Secure Apex Classes — API-version and security-dimension rules](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security)

The SOQL reference recommends `WITH USER_MODE` over `WITH SECURITY_ENFORCED`, explains that user mode applies CRUD/FLS and sharing, and notes the different sharing-keyword role in system mode. [SOQL `WITH` clause — user/system mode semantics](https://developer.salesforce.com/docs/platform/salesforce-soql-sosl/guide/sforce-api-calls-soql-select-with.html)

Concrete maintained recipe code shows the same distinction: Apex Recipes' `DMLRecipes` exposes both `as user` and system-mode calls, and its `StripInaccessibleRecipes` demonstrates graceful removal of inaccessible fields before reads/writes. These are patterns to select based on the desired failure behavior, not a mandate to copy either helper. [Apex Recipes `DMLRecipes` — explicit access-level DML examples](https://github.com/trailheadapps/apex-recipes/blob/main/force-app/main/default/classes/Data%20Recipes/DMLRecipes.cls) and [Apex Recipes `StripInaccessibleRecipes` — graceful field/object sanitization](https://github.com/trailheadapps/apex-recipes/blob/main/force-app/main/default/classes/Security%20Recipes/StripInaccessibleRecipes.cls)

The local DX project declares `sourceApiVersion` 67.0. Its currently checked source has no Apex classes or triggers, so this experiment does not imply a current production security defect. The no-Apex result is itself a reason for a conditional card rather than a blanket requirement. [Local DX project — API 67.0 declaration](/Users/dadleet/src/sf-tic-tack-toe/sfdx-project.json:11)

### Bulkification and budgets

Salesforce's developer guidance gives a transaction budget of 100 SOQL queries and 150 DML statements and explains that exceeding a governor limit raises a runtime exception. [Working with Salesforce Records — governor-limit examples](https://developer.salesforce.com/blogs/2022/08/working-with-salesforce-records-using-soql-and-dml)

The platform's developer checklist independently calls for no SOQL/DML in loops, bulkified helpers, and tests that include bulk scenarios. It also warns against using async merely because a transactional refactor is harder. [Developer Best Practices Checklist — bulk and test review cues](https://developer.salesforce.com/blogs/2022/01/drive-consistency-and-grow-developer-skills-with-a-developer-best-practices-checklist)

Apex Recipes' account trigger handler shows the useful narrow case: it builds `Task` records in a loop and performs one `insert` afterward, while noting that changing the current trigger record in a before context needs no DML. [Apex Recipes `AccountTriggerHandler` — collection then one DML and before-trigger boundary](https://github.com/trailheadapps/apex-recipes/blob/main/force-app/main/default/classes/Trigger%20Recipes/AccountTriggerHandler.cls)

The exact 100/150 limits do not justify a fixed universal internal budget. Other automation, recursion, query selectivity, record locks, flow, package code, synchronous versus async context, and the transaction entry point matter. The card therefore asks the task to name and prove its own expected budget instead of claiming that a textual scan proves a safe transaction.

### LWC state, cache, and tests

LWC tracks object/array fields shallowly by identity. The framework documents that a complex value must be assigned a new object/array for change detection unless deep tracking is deliberately used with `@track`; it further distinguishes non-trackable values such as `Date`, `Set`, and `Map`. [LWC reactivity — identity and `@track` limits](https://developer.salesforce.com/docs/platform/lwc/guide/reactivity-fields.html)

For stale data, Salesforce differentiates an Apex wire result from LDS records. `refreshApex()` refreshes a prior Apex-wire result; `notifyRecordUpdateAvailable()` tells LDS that a record changed outside LDS mechanisms, and it returns a Promise that completes after affected wire adapters process the update. [Apex result caching — `refreshApex` boundary](https://developer.salesforce.com/docs/platform/lwc/guide/apex-result-caching) and [LDS notification API — record-id shape and completion promise](https://developer.salesforce.com/docs/platform/lwc/guide/reference-notify-record-update.html)

The official recipes make the separation concrete. `ldsDeleteRecord` retains the Apex-wire result and awaits `refreshApex` after deletion. `ldsNotifyRecordUpdateAvailable` awaits its imperative Apex update, then tells LDS which record changed. Its Jest test emits a wire value, drains async work, verifies the mock call, success and error paths, and DOM cleanup. [LWC Recipes `ldsDeleteRecord` — wired-Apex refresh](https://github.com/trailheadapps/lwc-recipes/blob/main/force-app/main/default/lwc/ldsDeleteRecord/ldsDeleteRecord.js), [LWC Recipes `ldsNotifyRecordUpdateAvailable` — imperative update plus LDS notification](https://github.com/trailheadapps/lwc-recipes/blob/main/force-app/main/default/lwc/ldsNotifyRecordUpdateAvailable/ldsNotifyRecordUpdateAvailable.js), and [LWC Recipes notification test — controlled wire, async, success/error checks](https://github.com/trailheadapps/lwc-recipes/blob/main/force-app/main/default/lwc/ldsNotifyRecordUpdateAvailable/__tests__/ldsNotifyRecordUpdateAvailable.test.js)

Salesforce's Jest guidance says component rerendering is asynchronous and recommends waiting for the state change before asserting DOM results. It also emphasizes isolation/mocks for dependencies. [Jest Test Patterns — async rerender and mock boundary](https://developer.salesforce.com/docs/platform/lwc/guide/unit-testing-using-jest-patterns.html)

The local Tic-Tac-Toe LWC already assigns a replacement game state (`this.game = play(...)`), and `play()` copies the board before applying a legal move. That aligns with the identity rule, but it is a local in-memory game with no wire, DML, or cache invalidation path. [Local `ticTacToe` — state replacement assignment](/Users/dadleet/src/sf-tic-tack-toe/force-app/main/default/lwc/ticTacToe/ticTacToe.js:27) and [local `play()` — copied board transition](/Users/dadleet/src/sf-tic-tack-toe/force-app/main/default/lwc/ticTacToe/game.js:43)

### Contrary evidence and complexity cost

The Apex Enterprise Patterns common library provides a useful counterexample to blanket framework adoption. Its Unit of Work can coordinate bulk DML and relationships, but the core class has multiple interfaces/maps/work queues, a broad PMD suppression, and a default DML implementation explicitly running in system mode. It may fit a complex transactional domain; it is not justified by this small state-only LWC or by a generic no-SOQL-in-loop rule. [FFLib Unit of Work — scope and system-mode default](https://github.com/apex-enterprise-patterns/fflib-apex-common/blob/master/sfdx-source/apex-common/main/classes/fflib_SObjectUnitOfWork.cls)

No new analyzer is recommended either. Salesforce's Graph Engine can identify data-access paths, but the installed CLI reports `code-analyzer` as an uninstalled JIT plugin. Installing it would add a persistent dependency and still would not replace a permission-denial test in a real org. The static fixtures below are intentionally transparent and disposable instead.

## Local experiment and findings

The local runner deliberately uses independent seed/reference/mutant inputs:

| Hypothesis | Seed | Reference | Mutant | Measured local result |
| --- | --- | --- | --- | --- |
| Visible Apex access intent helps review | `with sharing` with no explicit user-mode syntax | sharing plus `WITH USER_MODE` and `AccessLevel.USER_MODE` | `without sharing` plus system-mode syntax | Scanner accepted reference and rejected seed/mutant. It proves only text discrimination; API 67 defaults mean seed is not thereby proven insecure. |
| Collection shape detects obvious budget hazards | SOQL and DML in a trigger loop | collect IDs, one query, one DML outside the loop | query outside loop but DML inside a loop | Scanner accepted reference and rejected both anti-patterns. It did not execute Apex or count governor limits. |
| Immutable state plus correct async invalidation produces an observable contract | mutates input and invalidates before mutation resolves | creates object/array/record identities, waits for mutation, selects cache adapter | mutates nested records and chooses the wrong adapter | Node 25 built-in tests passed; the model detects both distinct bad cases. It is not LWC Jest/LDS/browser evidence. |

The `results.json` records exact commands and observed runtime versions. `run_checks.py` has no Salesforce authentication or remote command path.

## Exact follow-up required for genuine Salesforce evidence

Do these only in an approved disposable scratch org or sandbox after authority for org changes/testing is granted. None were performed here.

1. **Freeze platform assumptions.** Capture the target org's API version, sharing defaults, relevant profiles/permission sets, object CRUD, field FLS, sharing model, automation, packages, and source hash. Confirm the reviewed entry point is an actual Apex controller/service/trigger rather than a local LWC-only path.
2. **Prove access behavior in that org.** Deploy a narrow test-only fixture with an approved low-privilege user/permission configuration. Execute positive and denial cases under the intended user context, including a record the user must not see and a field/object action they must not perform. Assert the expected user-mode exception or `stripInaccessible` result and confirm that no protected side effect occurs. Treat `System.runAs` as part of the scenario, not proof by itself; the permission-set/profile metadata must make the denial real.
3. **Prove bulk transaction behavior.** In an Apex test create both 1 and 200 input records, invoke the real trigger/service exactly as production does, bracket the unit under test with `Test.startTest()`/`Test.stopTest()`, assert business output, and assert deltas from `Limits.getQueries()` and `Limits.getDmlStatements()` against a declared budget. Repeat with expected automation enabled so a passing isolated helper is not mistaken for a transaction proof.
4. **Run the actual LWC Jest suite.** In an isolated checkout, install only the project's declared dev dependencies, then run its real LWC command (`npm test` or `sf force lightning lwc test run`). Add tests that mock the relevant Apex/LDS adapter, cover loading/success/error, wait for rerender, assert cache invalidation after a completed mutation, and clean up the DOM. A Jest pass remains isolated UI evidence; follow it with a browser/org validation of the user-visible flow.
5. **Retain a receipt.** Save org type/alias (without credentials), source commit/hash, command lines, test class names, test output, API version, data/permission fixture description, `Limits` deltas, and any known automation. Only this receipt can promote the card from pilot evidence to an adopted policy.

## Recommendation decision

| Candidate | Decision | Reason |
| --- | --- | --- |
| Conditional Salesforce planning/review card | **Pilot** | High signal for platform-specific data/security/cache boundaries; local corpus is discriminating but does not establish a model-effectiveness rate or real org behavior. |
| Explicit access-mode and sharing review | **Pilot** | Official guidance supports the distinctions, while API-version defaults and justified system-mode paths require task-specific judgment. |
| Bulkification/budget review | **Pilot** | Strong platform constraint and a good static screening signal; only real Apex tests prove the transaction budget. |
| LWC immutable-state/async cache review | **Pilot** | Strong official semantics and runnable JS model; needs actual LWC Jest/browser evidence for adoption. |
| FFLIB, a global trigger framework, Graph Engine, or an MCP server | **Reject for this experiment** | No local need justifies a new persistent component; each adds complexity or permissions and does not replace the required runtime evidence. |
