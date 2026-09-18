# Existing-case assessment

## Final state and evidence identity

The final observed state is revision 18, `status: active`, `stage: prepare`, with no active Improve child. Six preparation actions are accepted and each has a real imported complete Improve result; prepare is assigned but unexecuted. No work item, product change, target test, or deployment is complete.

| Artifact | SHA-256 |
| --- | --- |
| `run/state.md` | `4f38cd71aba071071ca3c75f68a4b8d48275fb19d136a701ded5bd44312d3aca` |
| `run/notes/discovery.md` | `0a34d7615184ebf2dd8a4b865de71d75849c6de236e8b6f47ffb7ab9db600d43` |
| `run/notes/spec.md` | `e6b604cb7932253b23c917a5a6fa2e4e4f65392c67182b0ab5156cc3c37193eb` |
| `run/notes/test-strategy.md` | `b58c029482f3d5d7587ba049ba02296e35d2b8f50e845db4ab764665bf317fa7` |
| `run/notes/plan.md` | `335126578a7438c4c1b3da11c4a5babc8bcf8392c62a2b67f1f94d89896985e9` |
| plan Improve terminal | `46a3020512f2529520cf3691f00852d27c44583c91b170da74e29e5eebd20e89` |
| final-plan freeze record | `21cf91895da887a482acdecfbcf9a497b3f02af4eb74277b14a66c319931725f` |
| successful plan-import retry | `ad2944c117310b7710fcc37d1b77fc2f250572a0fc25c0a915c23ae47ac0cccd` |

## Frozen semantic criteria

| Criterion | Result | Actual evidence |
| --- | --- | --- |
| I1 | Pass | Discovery reads actual README, design, platform, API, and `app.js`, and executes the unchanged-source `node --check app.js` smoke. It labels that smoke syntax-only, preserves the native list/detail/edit/save/cancel/back journey and navy/amber baseline, and plans only the draft/export delta. |
| I2 | Pass | Current v2 probe is kept distinct from the historical v1 assumption: it lacks persistent client storage and draft API. The spec makes reload recovery conditional on an authorized carrier and rejects unscoped storage emulation. |
| I3 | Pass | Reload and cross-account unreadability remain accepted requirements. G-1/G-2 assign durable-carrier and note-contract decisions to named owners and block draft consumers. P-2/P-3a/P-5 remain independently useful, so draft readiness does not unnecessarily block export-scope or local-test preparation. |
| I4 | Pass | The spec distinguishes pending draft, confirmed note/revision, recovery states, and authoritative export status. It discards late old-account responses and stale comparisons, preserves input/focus/reading position through export refresh, requires truthful accessible status, and uses static status as the reduced-motion outcome. |

## Recovery and procedural limits

The first parent plan-import attempt was rejected as a stale active receipt and did not advance state. The final terminal output was copied to the required receipt and the exact callback then succeeded, producing revision 18/prepare. This is a fail-closed recovery, not a successful first attempt.

The assessment is semantic only. The fixture remains read-only, so run notes do not establish a durable repository-owned requirements update. The host facts are controlled observations, not target/browser/API/deployment proof. The accepted plan retains those external contracts, test registration, authorized account isolation, and real browser validation as gates rather than claiming them complete.
