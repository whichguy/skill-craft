# Local password-auth diagnostics discovery

## Scope and baseline

This is a read/planning handoff for “Map maintainable diagnostics and authentication logging for the local password-auth service.” No product source, tests, dependencies, configuration, run state, or external system was changed.

Baseline passed on the unchanged fixture:

- Command/cwd: `python3 -B -m unittest discover -v` in this workspace, using Python 3.14.7.
- Result: 1 test passed: `ExistingAuthBehaviorTest.test_failed_password_attempt_is_logged_without_session`.
- Limit: this is the README-designated narrow fixture smoke test, not evidence of an `app.audit` collector, deployed service, account identity, retention, or remote delivery. The workspace is not a Git repository, so no revision, source-return, CI, or deployment route was observable.

## Concrete discovery

`PasswordAuth.authenticate()` has two local paths. With `valid=False`, it calls the injected logger with `login_failed` and structured `subject`/`method` fields, then raises `PermissionError`; it does not call the injected session issuer. With `valid=True`, it directly issues a session and has no local log call. See [auth_service.py - PasswordAuth.authenticate: failure event, rejection, and success route](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-auth/workspace/src/auth_service.py:5).

The existing fixture observes only the event name and absence of issued sessions. Its `Logger` is a capture fake; it neither proves Python logging `extra` handling nor that the injected object is the documented `app.audit` logger. See [test_fixture.py - ExistingAuthBehaviorTest: current narrow failure-path oracle](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-auth/workspace/test_fixture.py:26).

The repository's operational note says the structured `app.audit` logger feeds an existing operator sink, treats failed passwords as ordinary authentication outcomes unless incident rules say otherwise, and prohibits passwords, tokens, and session contents in logs. See [operations.md - Local operations: current logging and secret-data policy](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-auth/workspace/docs/operations.md:3). The README documents the established smoke command and its coverage limit; `SHIPLOOP.md` supplies no additional requirements or decision links. See [README.md - Local password-auth diagnostics: baseline command and limit](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-auth/workspace/README.md:3) and [SHIPLOOP.md - Project knowledge: current index content](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-auth/workspace/SHIPLOOP.md:1).

## Decisions for a later authorized plan

1. Reuse the documented `app.audit`/operator-sink path if its real configuration and retrieval route are confirmed. Do not propose a second logger, audit store, or incident mechanism merely from this local code.
2. Preserve the documented secret-data exclusion. Treat `login_failed` as an authentication outcome; do not make it an incident or alert without a separate rule.
3. Keep successful-login coverage, logger-sink failure behavior, and the raw `subject` field as unresolved design/requirements questions. Do not infer that the current injected fake covers platform or identity-provider events.

These choices follow the frozen observability guidance to map the authoritative emitter, sink, access, retention, and delivery before adding instrumentation, and to cover both successful and failed authentication appropriately ([service-discovery.md - Observability coverage: reuse, auth events, redaction, and sink behavior](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/source-snapshot/skills/shiploop/references/service-discovery.md:138)).

## Unknowns and required revalidation

- No source identifies whether `app.audit` is configured for this service, who retrieves it, its access control/retention/sampling, or whether sink failure should preserve `PermissionError` or fail closed.
- There is no evidence whether success events come from an identity provider, whether this service owns them, or whether raw usernames meet privacy policy.
- `docs/operations.md` is an operational constraint but does not label itself as the maintained requirements authority. Before implementation, reconcile a durable observable contract rather than treating code or the one passing test as approval.
- No actual operator sink, remote endpoint, credentials, browser flow, or deployment target was inspected; those checks remain unverified by design.

## File and check handoff

| Role | Locator | Next verification need |
| --- | --- | --- |
| Auth emitter | `src/auth_service.py:5-11` | Failure event fields, rejection, and no session; decide success-event ownership. |
| Operations constraint | `docs/operations.md:3-5` | Confirm actual `app.audit` sink, retrieval, redaction, retention, and failure policy. |
| Unit seam | `test_fixture.py:9-32` | Add planned cases for safe structured fields, valid login, sink failure policy, and no secret leakage once the contract is accepted. |
| Baseline route | `README.md:3-4` | Rerun this smoke command after authorized changes; retain its narrow-coverage limit. |

For test planning, retain distinct expected cases and actual evidence; a unit pass cannot establish a required service destination ([testing-and-documentation.md - Test cases: case records and surface limits](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/source-snapshot/skills/shiploop/references/testing-and-documentation.md:267)).
