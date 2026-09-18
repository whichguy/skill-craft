# Environment lifecycle — Field Notes planning fixture

## Observed topology

- **Development/source:** `<study>/existing/product` is the explicit in-place isolated Git fixture. It is on `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`; tracked source is unchanged. Run-owned `.shiploop-improve/` metadata is untracked and excluded from product candidates/returns.
- **Local test:** the repository documents `node --check app.js` as its smoke command. It ran on unchanged source in this discovery stage and exited `0`; its stdout/stderr are `../../evidence/discovery-baseline-smoke.stdout` and `../../evidence/discovery-baseline-smoke.stderr`. No repository test runner, test directory, package manifest, CI configuration, or full suite was found by the bounded tracked-file scan.
- **Controlled target observation:** `python3 -B scripts/probe_environment.py` ran locally and reported `fieldnotes-embedded-v2`, same-origin script/style policy, no server runtime, no WebSockets, unavailable client persistent storage, and no draft API. This is controlled fixture evidence only, not a deployed endpoint or consumer receipt: `../../evidence/discovery-environment-probe.stdout`.
- **Delivery/promotion:** `git remote -v` returned no remotes and no branch/remote config was found. The direct initialized experiment has no workspace return path. Repository docs say there is no remote deployment access; no CI/deployment/promotion route is known for this fixture. These observations do not prove a real product has no release process.

## Consequential readiness and gaps

- The existing static target can call same-origin HTTPS APIs, but current facts cannot support reload-recoverable drafts: browser persistence is unavailable and no draft API exists. A later plan must choose and authorize a supported environment augmentation, such as an account-scoped server draft contract or an explicitly enabled target persistence capability; this run has not selected, provisioned, or tested either.
- The documented export contract permits visible polling and foreground reconciliation; persistent subscriptions are unsupported. A future in-app export-change notice can be planned only around authoritative reads in those lifecycle points. An OS/background notification channel is neither documented nor verified.
- Account identity is host-controlled. The user requirement that drafts are unreadable after logout/account change makes account scoping, clear-on-identity-change behavior, and server-side authorization consequential. The fixture exposes no draft storage/access contract to verify them.
- Existing note read/save routes are used by `app.js` but are not specified in `docs/api.md`; their request/response/conflict behavior remains an interface gap for later research/spec. The client currently aborts account/detail/save work when switching account, which is an observed mechanism rather than proof of draft isolation.
- No external access request is needed for local planning evidence. Any actual server draft endpoint, target storage-policy change, remote release, or consumer-browser verification requires a named target/owner and fresh authorization before the earliest dependent implementation or delivery check.

## Revalidation triggers

- Re-run the controlled probe before depending on target storage, API, CSP, or lifecycle facts after target configuration changes.
- Recheck Git/delivery topology before any source return, commit, deployment, or release planning.
- Recheck the API contract and selected account/identity boundary before authoring integration tests or product behavior that persists drafts.
