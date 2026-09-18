# Disposable remote-resident repeatability pilot

## Scope and identity

- Target alias: `disposable-head` (fresh standalone Apps Script project; no
  existing application was selected or changed).
- Authenticated API discovery succeeded before creation. The project was created
  with `webapp.executeAs=USER_ACCESSING` and `webapp.access=MYSELF`.
- The create response reported a project creation and remote runtime upload. A
  later status receipt reported a HEAD development deployment and exact local /
  remote agreement for 22 files, including both authored modules; it reported no
  local-only, remote-only, or modified files.
- Authored bytes uploaded unchanged:
  - `common-js/total-cents.gs`:
    `e6b7c2357ae307303cf2e8385a7a00553d33fc4449aa7b61d33e164fdf3f5715`
  - `common-js/remote-repeatable-tests.gs`:
    `fed8e8014bcdb31627cff729a0c4558757826776b01238651aab9840759520e4`
- The source-level test marker returned by every successful suite invocation was
  `sha256:853dc9df6047c8101179f769690fe63e0cfde98aed263af0f72190b392084914`.

## Executed results

The preview identified only the two authored modules as additions; the upload
then succeeded. Execution used the server-reported web-app fallback at HEAD, not a demonstrated
`scripts.run` path or a tested browser route. Every completed call used the remote CommonJS module
`common-js/remote-repeatable-tests` at HEAD.

| Selection | Remote result | Independent owned-state inspection |
| --- | --- | --- |
| `smoke` | 2 passed, 0 failed, 0 blocked; TC-03 setup and teardown passed | `count: 0` |
| `full`, first run | 4 passed, 0 failed, 0 blocked; both stateful cases cleaned up | `count: 0` |
| `full`, second run | 4 passed, 0 failed, 0 blocked; both stateful cases cleaned up | `count: 0` |
| explicit reverse TC-04, TC-03, TC-02, TC-01 | 4 passed, 0 failed, 0 blocked; selected/executed order matched | `count: 0` |
| focused TC-03, first run | 1 passed, 0 failed, 0 blocked; setup/teardown passed | `count: 0` |
| focused TC-03, second run | 1 passed, 0 failed, 0 blocked; reported cleanup removed | inspection timed out |

The completed remote calls established repeatable smoke, two full reruns, reverse
ordering, and one repeated focused stateful case. Their returned case records
include stable selected/executed IDs and passed teardown observations.

## Boundary and recovery result

The sixth post-run `inspectOwnedState` call hit the MCP client's 60-second
timeout. Its outcome is unknown; it was not retried. A subsequent `status` call
succeeded and showed the remote source still matched the local 22-file project.
A later reconciliation inspection received a definite pre-execution
browser-authorization requirement, so it did not run and could not observe
owned state. No browser consent, OAuth change, or new remote execution was
attempted.

Consequently, the following required cases remain unrun: setup-failure control,
assertion-failure control, unknown-ID rejection, final full-after-controls, and
the second focused run's independent empty-state confirmation. The timed-out
inspection must not be treated as teardown evidence.

After the local caller had exited and no known execution process remained, the
fresh project was soft-trashed successfully using the default recoverable route.
No staging promotion, production deployment, browser test, or existing-project
operation occurred.

Private MCP receipts are retained under `private/`; this report intentionally
contains no raw project identifiers, URLs, account data, or credentials.
