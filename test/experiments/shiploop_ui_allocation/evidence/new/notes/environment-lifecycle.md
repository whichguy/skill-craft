# Environment lifecycle — Archive Exports client

## Observed topology

| Boundary | Current evidence | Status and revalidation |
| --- | --- | --- |
| Development source | Explicit in-place experiment repository `<study>/new/product`, `main` at `ec3243d658e24304b306749bc361869154fc4660`. | Available for local planning only. The case authority forbids product implementation, commits, and source return. Recheck before any later authorized edit. |
| Local build | No package manifest, build configuration, or existing UI exists. Node `v25.9.0` and Python `3.14.7` are locally available, but availability does not select a product technology or authorize an installation. | Unresolved. Later plan must select a static, self-contained asset route compatible with the target CSP and verify it locally. |
| Local test | No test runner, suite, fixture, or client behavior exists. `scripts/probe_environment.py` is an existing safe controlled-host probe, not a product test. | Missing baseline coverage. Plan the first executable checks/test bootstrap before feature work; distinguish local preview from embedded-target proof. |
| Integration / consumer target | The documented target is a static embedded host using same-origin HTTPS API calls; no server runtime or WebSocket is allowed. The host controls account identity and can suspend hidden pages. | Controlled fixture facts are available locally. There is no remote deployment access or authorized consumer session in this experiment. |
| Delivery / promotion | `git remote -v` and local branch/remote config produced no project route; no repository CI/deployment configuration or non-sample hook was found. The direct in-place experiment has no workspace return operation, and commits/pushes/deployments are prohibited. | Actual delivery/promotion route and authority are unresolved, not N/A. A later release plan must obtain target/operation authority if delivery becomes in scope. |

## Preparation obligations before dependent feature work

1. Select and verify a static client asset/build approach that emits same-origin bundled script/style/font/image files without inline code or external CDN assets.
2. Establish the first repeatable local client test route and an explicit browser/manual target-check boundary; no existing harness can establish keyboard, narrow-screen, live-region, or reduced-motion behavior.
3. Obtain or retain an explicit API-contract/fixture gap for collection data, status/error semantics, operation lookup, duplicate request behavior, and download/error cases. Do not substitute a synthetic live API claim.
4. Keep target deployment and consumer verification blocked without an authorized target and a real candidate; no setup/deployment action is authorized in this planning experiment.

The note records topology and pending work only. It does not authorize installation, provisioning, deployment, remote access, or product edits.
