# Later remote execution — NOT RUN during authoring

Owner: the later authorized disposable-project operator. Execution location:
Apps Script V8 at HEAD; target: one fresh project owned by this pilot. Node/VM
results are simulation evidence only. PLATFORM.md is the authoritative route.
Its historical preflight is not current authentication or availability evidence.

## Prerequisites and retained definitions

Run `node scripts/verify.cjs` locally first. Retained definitions are
`common-js/total-cents.gs` and `common-js/remote-repeatable-tests.gs`; both use
the platform's CommonJS registration. The test module exposes
`runRepeatableTests` and read-only `inspectOwnedState`. No existing project,
production application, browser route or served web-app is a target here.

The later operator must have the existing MCP server, SDK, authenticated session,
project creation/upload/HEAD execution/soft-trash capability and V8 CommonJS
runtime available. Nothing about these capabilities was checked in this action.
Do not install dependencies, change OAuth configuration, export tokens or launch
a browser. Do not use existing project identifiers.

Connect using the existing SDK's `Client` and `StdioClientTransport`. The required
transport configuration is:

```javascript
// Later execution only, using the existing SDK under:
// <deployment-server-checkout>/node_modules/@modelcontextprotocol/sdk/
const transport = new StdioClientTransport({
  command: process.execPath,
  args: ['<deployment-server-checkout>/dist/server.js'],
});
await client.connect(transport);
// Each tool(name, arguments) below means:
// await client.callTool({name, arguments});
```

Choose a fresh title `shiploop-repeatable-tests-YYYYMMDD-<random>` and an owned
empty `localDir` under this task's `remote/` directory (for example a new
`remote/author/remote-run-<random>`). It must have no existing `.clasp.json`.
The operator must verify the resolved directory, ownership, and freshness.

## Exact later tool calls and receipts

The following are deferred tool arguments, not authoring-time commands. `title`,
`localDir` and `scriptId` refer only to the new project. Retain the raw scriptId
only in task-local receipts; publish only its hash and title.

1. Immediately before creation, call
   `ls({query:"__shiploop_auth_probe__"})`; require success and retain only its
   count, never returned project identities. Then call `auth({action:"status"})`;
   require an authenticated-session message, not invented boolean fields.
2. `create({title,localDir,webapp:{executeAs:"USER_ACCESSING",access:"MYSELF"}})`. Retain title, task-local scriptId, exact returned
   directory, runtime-included flag and execution-mode hint. Stop on failure or
   unexpected directory. Record any HEAD web-app fallback created by its probe;
   there is no option to suppress that probe in this contract.
3. Copy the two retained `common-js/*.gs` files into the corresponding paths in
   that localDir, preserving the generated runtime/manifest. Record SHA-256 of
   each exact copied file and the retained Git revision. Do not reauthor tests
   in the remote project. The expected module path is
   `common-js/remote-repeatable-tests`, not the module-omitted fallback.
4. `push({scriptId,localDir,action:"preview"})`. Inspect the entire planned file
   list; only generated runtime files and these two definitions are expected.
   Stop on unexpected changes or validation failure.
5. `push({scriptId,localDir})`. Retain pushed files and source identity. Stop on
   failure or unknown outcome; `exec` may auto-push, so an explicit successful
   preview/upload and identity comparison must precede it.
6. For each selection in the table, invoke this exact call, substituting the
   literal selection into `args:[selection]`:

   ```javascript
   exec({scriptId,localDir,target:"head",
     module:"common-js/remote-repeatable-tests",function:"runRepeatableTests",
     args:[selection],timeoutMs:30000})
   ```

   | Selection | Expected selected/executed IDs | Expected summary |
   | --- | --- | --- |
   | `"smoke"` | TC-01, TC-03 | passed 2, failed 0, blocked 0 |
   | `"full"` twice | TC-01, TC-02, TC-03, TC-04 | passed 4, failed 0, blocked 0 each time |
   | `["TC-04","TC-03","TC-02","TC-01"]` | same explicit order | passed 4, failed 0, blocked 0 |
   | `["TC-03"]` twice | TC-03 | passed 1, failed 0, blocked 0 each time |
   | `["NC-01"]` then `["NC-02"]`, separately | the one selected control | passed 0, failed 1, blocked 0 each; intentional setup/assertion error and passed teardown |
   | `["UNKNOWN"]` | rejected before cases/state access | explicit unknown-ID error; never a successful zero-case result |

   Record structured results, selected/executed IDs, per-case setup/teardown,
   summaries, cleanup observations, target, test-definition marker, actual
   uploaded file hashes and execution disposition for every call. A controlled
   failure is an expected negative result only when the intended phase failed
   and cleanup passed. A transport error, blocked case, unexpected assertion or
   unknown disposition is not a successful negative control.
7. After each stateful/control invocation call:

   ```javascript
   exec({scriptId,localDir,target:"head",
     module:"common-js/remote-repeatable-tests",function:"inspectOwnedState",
     args:[],timeoutMs:30000})
   ```

   Require `count:0` and `keys:[]`. Repeat full after controls to demonstrate
   recovery. Inspect only suite-owned names; this call makes no property writes.
8. `status({scriptId,localDir})`. Compare actual remote/source identity with the
   uploaded bytes; do not infer code identity solely from the returned marker.
   Record target HEAD and no application deployment claim.
9. On success, or failure once no execution can still be active, call
   `trash({scriptId})` using default soft-trash only. Retain success and hashed
   identity. End the experiment; do not reuse, promote or retain a deployment.
   A trash failure remains an unresolved cleanup obligation.

## Isolation, interruption and recovery limits

Stateful cases own one invocation-and-case-specific property key. They remove
only that key in `finally`, including after partial setup or assertions fail.
Do not share mutable case fixtures. Pure cases need no setup/teardown. A suite
scan reports all keys beginning `__shiploop_repeatable_v1__`, so prior interrupted
invocations can be detected without sweeping another invocation's keys.
Normal full selection excludes both negative controls. Run remote invocations
serially for this pilot; local interleaving checks cannot establish remote quota
or scheduler behavior. A remote run has a 30-second request timeout; no latency
guarantee is inferred from the local tests.

A timeout/reset is an unknown execution outcome. `finally` cannot guarantee
cleanup after forced termination. Do not retry blindly: first inspect `status`
and, once execution has settled and identity is known, `inspectOwnedState`.
An empty scan while an earlier invocation is still active does not prove its
cleanup. Retain any residual keys/unknown liveness as unresolved, stop reruns,
and use the disposable project's authorized soft-trash route after quiescence.
Never delete all script properties or remove another invocation's keys.

No remote actions, remote result receipts, service quotas, actual Apps Script
compilation, live concurrency, fallback mode, timeout cleanup or project
soft-trash have been validated here. Required remote execution and identity
receipts remain NOT RUN for the later operator. The combined local-plus-remote
regression suite remains NOT RUN even when every local check passes.
