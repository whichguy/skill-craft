# W1 step plan: reload-persistent account-scoped drafts

## Outcome and disposition

This is an actual W1 step-plan producer result. No product source, test,
dependency, package, remote target, Git state, commit, or deployment was
changed.

The selected outcome is blocked. A reload-persistent draft needs a durable,
account-scoped carrier. The current controlled target is
fieldnotes-embedded-v2, whose current probe reports
client_persistent_storage: unavailable and draft_api: false. The static target
also has no server runtime. The selected item has no authorized supplier for
that missing target capability. A future implementation bullet cannot close
that gap.

The exact supplier and revalidation route are in
<study>/candidate-dependent/run/notes/environment-lifecycle.md.

## Current requirements and baseline

The applicable repository-owned sources were read and revalidated:

- product/README.md requires recoverable drafts across reloads, preservation of
  list/detail/edit/save/cancel/back behavior and visual identity, and
  account-to-account unreadability after logout. It also says not to assume the
  older environment note still holds.
- product/docs/design.md, sections UI identity and Previous environment
  assumption, preserves the native account selector, note list, stable textarea,
  focus/keyboard/touch/narrow layout, reading position, draft text, navy/amber
  skin, white cards, system body/Georgia display treatment, and no framework
  migration. Its v1 storage claim is historical only.
- product/docs/platform.md defines a static same-origin embedded artifact and
  prohibits a Node/server runtime in deployment. It states that a local preview
  proves only the constraints it reproduces.
- product/docs/api.md has note-save and export contracts but no draft storage
  endpoint. Existing server-confirmed notes remain server-owned.
- product/app.js currently holds only transient UI state. Its beginEditing,
  cancelEditing, saveEditing, and switchAccount functions are at lines
  213, 223, 233, and 288. The current account switch aborts detail/save work
  and returns to the list; it does not persist a draft.

The fixture archive has no .git directory. Its baseline is therefore the
observed content and commands in this evidence, not a branch, SHA, commit, or
workspace-return receipt.

The packet's alleged prior test-strategy result and prior Improve receipt were
not present:

- run/results/nav-ab6be5d6f26849acbb56f29eae5efe38.md is missing.
- run/improve/nav-765fb46d03694c98bb47a9c155dd30a8/receipt.md is missing.

The retained state and seed evidence mark all earlier predecessors synthetic.
They are context only, not producer, test, review, or availability evidence.
The missing test decision was reassessed below rather than guessed.

## Design basis, components, and interaction contract

The selected frontend-design guidance was read from
<study>/capabilities/frontend-design/SKILL.md
with SHA-256
1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd.
It supports preserving this established Field Notes identity instead of adding
a generic redesign. The conditional feature delta is deliberately small:
retain the existing cards, textarea, action bar, live status region, focus
behavior, and narrow layout.

Components:

- Keep #note-input as the stable working-text surface, #confirmed-note as the
  separate server-confirmed value, and #save-status as the accessible status
  surface. Do not present a recovered draft as confirmed content.
- Keep the existing account selector, note list, back/edit/cancel/save controls,
  keyboard focus behavior, and touch sizing. No framework, CDN, inline script,
  or inline style is needed or authorized.
- If the capability becomes ready, app.js is the expected implementation
  location. A narrowly scoped draft-provider interface belongs beside its
  callers and must state read, write, remove, account/identity scope, and
  failure behavior. The provider must be a target-supported source, not an
  invented localStorage fallback.

Interaction and state:

- User editing is a local presentation state. A conditional durable draft is
  a separate, not-yet-supplied carrier keyed by the actual authorized account
  identity plus note identity. A mere selector value or client-visible prefix
  cannot prove the logout/cross-account privacy requirement.
- Server-confirmed note data remains in state.record and is changed only by the
  existing note-save contract. A recovered draft may populate the working
  textarea with an explicit local-draft status; it must not overwrite
  #confirmed-note or claim a server save.
- On a same-account reload, the provider would be read only after the current
  note is known. A matching draft restores working text. A missing draft leaves
  the current confirmed note unchanged. A failed or unavailable read leaves the
  in-tab state usable and reports an actionable status without a false recovery
  claim.
- On edit input, a successful provider acknowledgment may say Draft saved
  locally. Before acknowledgment, use a truthful pending status; after a
  failed write, retain current in-tab text and say it may not survive reload.
  The existing polite live region is the durable cue, not a transient toast.
- On successful server save, remove only the matching account/note draft after
  the matching save response is accepted. On failed or conflicted save, retain
  draft and working text. Cancel removes only the current draft after a
  successful local removal and restores the confirmed text. Account change,
  logout, back navigation, abort, or late old-account callbacks must never
  render or clear a new account's draft.
- If a crash occurs after a provider acknowledges a write but before the UI
  processes it, the next same-account load must recover it. If it crashes
  before acknowledgment, the UI must not have shown a saved-local claim. This
  is a planned recovery check, not a current implementation claim.
- Export notifications, WebSockets, and new background processing are outside
  this selected item. The target says WebSockets are unsupported; the current
  export API does not expand W1.

Skin and async feedback:

- Preserve navy #15324f, amber #c08722, white cards, existing typography, and
  the current calm field-notebook layout. No visual redesign is planned.
- Use concise status wording that distinguishes Recovering local draft,
  Draft saved locally, Draft could not be retained, Saving changes, and Changes
  saved. Status remains visible in #save-status until superseded by a relevant
  action so a failure is not lost after a transient animation.
- Default to a static text/status cue. If a small restrained pending marker is
  later added, the reduced-motion alternative is the same static status with no
  animation. Preserve focus, typed text, and reading position throughout.

## Conditional implementation microplan

These are bounded future changes only after the environment definition of ready
is met; they are not authorization to implement now.

1. Re-run product/scripts/probe_environment.py and validate the supplier's
   current contract. Confirm that the source may call its read/write/remove
   interface under the static CSP and that account identity isolation is
   enforced by the actual runtime.
2. Extend product/app.js with the smallest readable draft-provider adapter for
   the approved interface. Retain current AbortController and request-generation
   protections. Scope every provider operation to the account and note captured
   at its start; ignore late completions whose account, note, generation, or
   lifecycle no longer matches.
3. Load a recovered local draft after the authoritative note load, retain its
   base-revision/recovery metadata, and visibly keep it separate from confirmed
   content. Do not choose a conflict resolution rule silently: a changed
   confirmed revision must preserve the draft for review and expose the actual
   server-save conflict behavior.
4. Persist edit changes through the approved provider, then synchronize removal
   only after save/cancel outcomes for the matching scope. Preserve user text on
   provider or server failure. Do not add retries or background workers without
   a provider contract that supports them.
5. Update product/docs/design.md for the accepted UI state contract and
   product/docs/platform.md or product/docs/api.md only if the supplier changes
   that target contract. Update product/README.md with observable recovery,
   privacy, and limitation behavior. Link durable accepted behavior through
   product/SHIPLOOP.md if a new maintained requirement home is created.

Failure and diagnostics obligations for a future implementation:

- Validate provider return shapes and operation scope before modifying UI state.
  Keep the original provider/server failure available to diagnostics and do not
  mask it with cleanup errors.
- The current product has no debug control. Do not introduce broad logging only
  for this feature. If an approved repository debug facility exists later, emit
  bounded, redacted operation/account/note identifiers and outcome categories;
  never dump note content or account data.
- User-facing errors remain specific, non-secret, and actionable. They must
  distinguish local retention failure from server save failure and never claim
  persistence, privacy, or confirmation that has not occurred.

## Backchain dependency audit

Claim: a user can recover an unsaved note after reload only for the same
authorized account, while server-confirmed content remains distinct and a later
account cannot read the draft.

Needs:

1. A durable target-supported draft carrier or an authoritative draft API.
2. A real account/identity isolation contract, not only a selector namespace.
3. Source changes in app.js and durable documentation for the selected carrier.
4. A target-compatible browser check that observes same-account reload and
   cross-account/logout isolation.

Supply:

- product/docs/design.md supplies only a historical v1 observation, explicitly
  not current availability.
- The current v2 probe supplies negative evidence: storage unavailable and no
  draft API.
- product/docs/api.md and app.js supply no draft carrier.
- The current run has one W1 item and no preparation supplier or named owner.

Pull:

- The W1 test-author, implementation, and verification work need an actual
  carrier and target-compatible browser result. Node syntax or source checks
  cannot supply that runtime behavior.

Resolution:

- Keep W1 blocked. The target/platform owner or user must identify and supply
  the capability, then the ShipLoop recovery/correction route must revalidate
  it before implementation. Embedded Backchain reasoning was used because no
  run note selects and binds a source-aware-native Backchain card and caller
  resource.

## Test plan and current check evidence

Current harness decision:

- No package manifest, lockfile, existing test/spec file, or repository test
  runner was found. Node v25.9.0 is available.
- The smallest available baseline is a direct Node syntax check plus a
  read-only source-boundary assertion and the controlled target probe.
- These baseline checks are not an automated regression suite and cannot
  establish actual browser persistence. No dependency or test framework was
  installed.
- There is no target-accessible browser/service route in this experiment.
  A future rendered test is required but blocked until the supplier makes a
  target-compatible environment and non-secret identity/fixture route available.

Planned cases after readiness:

| Case | Preconditions and stimulus | Independent expected outcome | Planned surface and lifecycle |
| --- | --- | --- | --- |
| W1-ENV | Current target probe | Exact approved carrier and identity contract reported for the same target | Focused probe; setup none, read-only, teardown none |
| W1-RECOVER | Authorized account A, one note, provider write acknowledged, then real page reload | Working textarea restores A's draft; confirmed note remains separate; status says local draft recovered | Required target browser journey; isolated A/note fixture, clear owned draft at teardown |
| W1-ISOLATE | Seed A draft, then perform the real account/logout transition to B | B cannot read or overwrite A's draft; no late A callback changes B UI | Required target browser/provider check; isolated A/B fixtures and verified cleanup |
| W1-SAVE | Recovered draft and matching server save success | Confirmed record updates and only the matching draft is removed after acceptance | Unit plus target browser integration; stub only for unit diagnosis, real boundary remains required |
| W1-FAIL | Provider rejection, save error, or revision conflict | Working text and recoverable draft stay intact; status is actionable; no saved claim | Unit plus required target browser error path; teardown validates isolation |
| W1-STALE | Delay an old-account provider response, then switch account or navigate away | Old response does not mutate or clear the new account/note state | Unit race fixture plus browser interaction |
| W1-ACK-CRASH | Provider acknowledgment, then reload before UI completion | Same-account reload can recover the acknowledged draft; pre-ack failure never displayed success | Required target-compatible interruption procedure or automated browser case |
| W1-A11Y | Keyboard edit/save/cancel path, narrow layout, assistive status observation, reduced motion | Focus and working text persist; status text exposes actual state without required animation | Required browser/manual accessibility procedure; target identity and candidate recorded |

Provisional code/test locations, subject to the actual provider contract and
test-spec selection:

- product/app.js for the adapter and UI integration.
- product/test/draft-store.test.mjs for isolated provider/scope rules if a
  Node built-in test seam is justified.
- product/test/drafts.browser.mjs for a registered target-browser journey only
  after an actual browser runner and target route are selected.

Provisional focused command after tests exist:

    node --test test/draft-store.test.mjs

The full-suite command and browser invocation are intentionally unresolved:
the repository has no registered suite and the target does not yet expose the
required carrier. Test-spec must select supported setup, independent oracle,
teardown, focused/smoke/full membership, real browser target, and cleanup
before those files or commands are claimed executable. Shared A/B data is not
assumed safe; each case owns isolated account/note fixtures unless the provider
documents and verifies noninterference.

## Raw commands and outputs

All commands below were run read-only in the assigned fixture, except ShipLoop's
read-only recovery rendering. Empty output is recorded explicitly.

1. Selected CLI binding:

    python3 <study>/candidate-1/shiploop/scripts/shiploop --help

    exit 0
    usage: shiploop [-h] {workspace,drive,managed-graph-dry-run,graph-dry-run,init,improve-bind,improve-complete,next,status,report,plan-status,context,complete,done,verify,planning-verify,planning-upgrade,history,journal,halt,pause,resume,repair,merge-recover,replan,revisit,migrate} ...
    Markdown-authoritative, action-oriented session harness

2. Current packet recovery:

    python3 <study>/candidate-1/shiploop/scripts/shiploop next --run-dir=<study>/candidate-dependent/run

    exit 0
    ShipLoop navigator | step-plan | revision 16
    Phase: inner | Run status: active
    Current: step-plan (assigned; execution unproven).
    Owner: W1.
    The complete rendered packet is retained at evidence/initial-packet.txt.

3. Current controlled target probe:

    python3 scripts/probe_environment.py

    exit 0
    {"client_persistent_storage": "unavailable", "draft_api": false, "observation_scope": "controlled fixture target facts; not a live deployment", "observation_sha256": "40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878", "script_src": ["self"], "server_runtime": false, "style_src": ["self"], "target": "fieldnotes-embedded-v2", "websocket": false}

4. Existing source syntax baseline:

    node --check app.js

    exit 0
    stdout: empty

5. Read-only source boundary assertion:

    node -e 'const fs=require("fs"); const source=fs.readFileSync("app.js", "utf8"); const forbidden=[/localStorage/,/sessionStorage/,/indexedDB/,/\/api\/.*draft/i]; const hits=forbidden.filter((pattern)=>pattern.test(source)); if(hits.length){ throw new Error("unexpected persistent-draft implementation: "+hits); } if(!source.includes("function switchAccount()") || !source.includes("state.account = elements.account.value")){ throw new Error("account switch contract is absent"); } console.log("PASS: no client persistent-draft implementation or draft API call; account switch resets local detail state.");'

    exit 0
    PASS: no client persistent-draft implementation or draft API call; account switch resets local detail state.

6. Runtime and harness inspection:

    node --version

    exit 0
    v25.9.0

    rg --files -g package.json -g package-lock.json -g npm-shrinkwrap.json -g yarn.lock -g pnpm-lock.yaml -g '*test*' -g '*spec*' .

    output: empty; no matching package, lock, test, or spec path in product.

7. Fixture Git check:

    git status --short --branch

    exit 128
    fatal: not a git repository (or any of the parent directories): .git

8. Capability identities:

    shasum -a 256 <study>/capabilities/frontend-design/SKILL.md

    exit 0
    1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd  <study>/capabilities/frontend-design/SKILL.md

    shasum -a 256 <study>/candidate-1/shiploop/SKILL.md

    exit 0
    be8340413f5ad72792da14d5f6719a98a8cbebc89a8531ad139e2c5dbc52c269  <study>/candidate-1/shiploop/SKILL.md

## Revalidation before any future action

Reopen this evidence, the environment note, product/README.md,
product/docs/design.md, product/docs/platform.md, product/docs/api.md, and
product/scripts/probe_environment.py. Confirm the current action/repository
identity with ShipLoop next. Re-run the target probe and the source baseline
after a supplier change. Do not treat this blocked plan, the historical v1
observation, a local preview, or a future generic test file as proof that the
requested target can persist drafts.
