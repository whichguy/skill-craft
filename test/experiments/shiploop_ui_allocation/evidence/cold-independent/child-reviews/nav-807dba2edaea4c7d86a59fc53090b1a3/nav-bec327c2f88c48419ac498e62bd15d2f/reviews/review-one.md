# Improve review one — material plan correction

Binding: `nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f`.
Candidate: the W1 `step-plan` producer result at
`<study>/cold-independent/run/inbox/nav-bec327c2f88c48419ac498e62bd15d2f.md`
and its explicitly named plan at
`<study>/cold-independent/run/notes/w1-step-plan.md`.

## Scope, history, and preserved input

- The fixture is a Git archive. `git --no-optional-locks -C product log -n 7`
  exited 128 with `fatal: not a git repository`; no reachable commit messages,
  HEAD, diff range, or index exists. No Git bootstrap was performed.
- Before and after the correction, the original submitted producer output has
  SHA-256 `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`.
  It was read but never edited or rerun.
- The plan's pre-review SHA-256 was
  `c6fd2db8c0d3dc19347f3be88bb0c6c3e84b32227319d07ba8a221d4377ec814`;
  its corrected SHA-256 is
  `3a1df372bec5483e0c7bd83d8787472606462032835f847e8dee139571ca14a3`.
- Product source, test, configuration, account, deployment, and parent state
  were out of scope and unchanged. Child evidence is confined to this
  `.shiploop-improve` directory.

## Sources revalidated

- `README.md:3` and `docs/design.md:3` preserve the existing Field Notes
  journeys, stable textarea, focus/touch/narrow-layout behavior, and navy/amber
  identity.
- `docs/platform.md:2` allows same-origin request/response but forbids a
  deployed server process, external/inline assets, persistent WebSockets, and
  provides no remote deployment access.
- `docs/api.md:2` supplies the export routes and recovery rules, but requires a
  `collectionId` without defining its source or mapping it to the host-owned
  account identity.
- The current probe still reports `fieldnotes-embedded-v2`, unavailable client
  persistent storage, `draft_api: false`, `server_runtime: false`, and
  `websocket: false`. The old v1 storage note remains historical only.

## Finding and decision

The prior plan correctly named the missing `collectionId` contract, but its test
table still described `EXP-002` as using a “fresh valid collection fixture” and
did not map the plan's independent outcomes to exact planned criteria. That
could let a future fake fixture mask the absent account-to-collection authority,
then present request/polling coverage as product-contract coverage. This is a
material planning defect because `POST /api/exports` cannot be formed safely
without that contract.

The authorized plan-only correction:

1. adds a plan-local `T-W1-00`–`T-W1-05` outcome/case matrix, explicitly marked
   as planning traceability rather than new accepted requirements or evidence;
2. adds `EXP-000` as the read-only collection-contract gate and makes it a hard
   prerequisite for request-fixture authoring and execution; and
3. changes `EXP-002` and the check section so a fake can only mirror a resolved
   authoritative mapping, while the current zero-test runner result is recorded
   as non-coverage.

No product code or future-stage work was attempted. The material correction
resets the runtime's qualifying-trivial streak. The next iteration must perform
a fresh independent-in-time review of the corrected plan.

## Review limitation

No separate read-only reviewer was used: this cold-independent delegation owns
only this fixture's review evidence and plan correction, and no independent
reviewer was available within that bounded task. This record is a self-review;
the later qualifying review is distinct but does not remove that limitation.

## Check evidence

See `checks.md` in this directory. The post-correction probe and JavaScript
syntax check passed; `node --test` exited 0 with zero tests, suites, passes, and
failures, so it is recorded as an empty-suite observation rather than behavior
coverage. The plan-marker/content check confirmed the new gate/matrix; hashes
confirmed the producer output and every product file recorded in the plan remain
unchanged.
