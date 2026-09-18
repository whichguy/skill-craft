# Disposable Apps Script remote-test invocation contract

## Purpose and boundary

This is the execution contract for one owned, newly created Apps Script project
used to demonstrate that a retained test suite can run inside the remote Apps
Script runtime. It is not authorization to inspect, push to, deploy, or execute
against an existing application.

Use the local stdio MCP server already present at:

```text
<deployment-server-checkout>/dist/server.js
```

The client must connect with the Model Context Protocol SDK's
`StdioClientTransport`, using `process.execPath` and the server path above.
Use the existing SDK installation at:

```text
<deployment-server-checkout>/node_modules/@modelcontextprotocol/sdk/
```

No package installation, OAuth configuration change, token export, or browser
automation is part of this pilot.

## Preconditions

1. Immediately before `create`, make one narrowly scoped read-only authenticated
   operation such as `ls({query:"__shiploop_auth_probe__"})`. It must succeed;
   retain only its count, never returned project identities. Then confirm that
   `auth({action:"status"})` reports an authenticated session in its message.
   The tool's structured status payload does not expose `authenticated` or
   `tokenValid` booleans, so do not gate on invented fields.
2. The caller must use a fresh, uniquely titled standalone project, with a title
   such as `shiploop-repeatable-tests-YYYYMMDD-random`.
3. The local directory must be under this task's `remote/` directory and must
   contain no existing `.clasp.json` before `create`.
4. Store the raw `scriptId` only in task-local receipt material. Published
   evidence may retain a hash of the identifier and the project title.
5. Do not use `ls`, `pull`, `status`, `push`, `exec`, `deploy`, `project_copy`,
   `fork`, or `trash` with an existing project identifier.

## Required tool sequence

| Step | MCP tool and arguments | Required receipt | Stop condition |
| --- | --- | --- | --- |
| Authenticate | `auth({action:"status"})` | redacted authentication capability fields | no valid token |
| Create | `create({title,localDir,webapp:{executeAs:"USER_ACCESSING",access:"MYSELF"}})` | returned title, task-local `scriptId`, local directory, runtime-included flag, and execution mode hint | create failure or unexpected project path |
| Write tests | local files only | source hash and declared test IDs | test runner is not remote-resident |
| Preview upload | `push({scriptId, localDir, action:"preview"})` | planned changed-file list | unexpected files or validation failure |
| Upload | `push({scriptId, localDir})` | source hash and pushed-file list | upload failure or unknown outcome |
| Execute | `exec({scriptId, localDir, target:"head", module:"common-js/remote-repeatable-tests", function:"runRepeatableTests", args:[selection], timeoutMs:30000})` | structured per-case result, remote target/revision marker, execution disposition | error or `unknown` disposition |
| Rerun | repeat `exec` with the same selection, then an alternate order when supported | matching stable case identifiers and cleanup observations | state leaks or mismatched results |
| Confirm identity | `status({scriptId, localDir})` | current remote/source identity and no unexpected deployment claim | mismatch |
| Clean up | `trash({scriptId})` | soft-trash success and hashed identity | cleanup failure |

The experiment does not need an explicit staging deployment: execution at HEAD
is the intended remote-runtime check. `create` has no schema option that disables
its scripts.run probe. If that probe fails, the server may create a HEAD web-app
fallback deployment in order to make `exec` available. Its `webapp` option only
sets `executeAs` and `access`; it does not suppress fallback setup. Record that
effect when it occurs, but do not claim browser, served web-app, staging, or
production behavior from this experiment. A separate application-route experiment
would need an explicit `deploy`, retained staging candidate receipt, and direct
route verification.

## Remote test-runner contract

Author `common-js/remote-repeatable-tests.gs`, registered as a normal CommonJS
module. Use this exact shape; do not rely on `exec`'s module-omitted
`runner-api` fallback and do not make a top-level product function:

```javascript
function _main(module = globalThis.__getCurrentModule(), exports = module.exports) {
  function runRepeatableTests(selection) {
    // Return the suite result described below.
  }

  module.exports = { runRepeatableTests };
}
__defineModule__(_main);
```

The file path derives the remote module name
`common-js/remote-repeatable-tests`. The invocation in the table calls
`require('common-js/remote-repeatable-tests').runRepeatableTests(selection)`.
The runner returns a JSON-serializable object with these fields:

```json
{
  "suiteId": "shiploop-remote-repeatability-v1",
  "sourceRevision": "sha256:<local source digest>",
  "selection": "smoke|full|explicit",
  "cases": [
    {"id": "...", "outcome": "passed|failed|blocked", "setup": "...", "teardown": "..."}
  ],
  "summary": {"passed": 0, "failed": 0, "blocked": 0}
}
```

The smallest meaningful suite has three cases:

1. A stateless pure-function case that declares no setup or teardown.
2. A stateful case whose setup creates project-local fixture state and whose
   `finally` teardown removes it.
3. A controlled setup or assertion failure case that proves teardown still
   removes its sentinel and reports failure rather than a false pass.

Every case must have a stable ID. The runner must reject an unknown selected ID,
must not silently skip a selected case, and must run teardown in `finally`.
Avoid calls that create external resources, send mail, write to user documents,
or add triggers. A project-local script property is acceptable only when it is
cleared by both normal and failure teardown.

## Execution safeguards

- `exec` at `target:"head"` may auto-push. Always make the explicit preview and
  upload calls first, then compare the returned source identity before execution.
- An `exec` timeout or reset is an unknown outcome. Inspect `status` and the
  runner's observable cleanup marker before deciding whether a repeat is safe.
- Use default `trash` only; never set `permanent:true`.
- End after soft-trash. Do not promote, retain a reusable deployment, or reuse
  the project for another trial.

## Current preflight state

The local server exposed all 16 expected tools. A narrowly scoped read-only
`ls({query:"__shiploop_auth_probe__"})` call succeeded and returned zero matches;
no project title or identifier was retained. That call also established that the
cached PKCE session silently refreshed. The immediately following `auth(status)`
reported an authenticated session with about 58 minutes remaining. The server's
structured status payload does not expose boolean `authenticated` or `tokenValid`
fields, so the status message and successful authenticated API call are the
evidence for availability.

Creation, remote execution, and cleanup may proceed after the independent author
has created the local remote test assets under this directory. This contract does
not ask for or initiate login, scope changes, or new OAuth configuration.
