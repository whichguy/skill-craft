# Parallel dispatch and integration test plan

Prove that every completion settles its own attempt, immediately exposes ready
successors, and preserves every accepted contribution on the invoking target.
Keep deterministic lifecycle checks separate from native host qualification.

| Case | Setup and execution | Required evidence | Suite |
| --- | --- | --- | --- |
| Required contributions | Real code modules; delete an expected module | Verifier rejects the missing file instead of skipping its checks | Focused lifecycle |
| Completion order | Independent temporary Git fixture for A-first, B-first, and burst delivery; controlled worker release | Correct step/attempt settlement, C refill as soon as A is accepted, join only after both suppliers, contiguous target commits, all source ancestors and composed behavior | Full lifecycle |
| Superseded B result | Reject B, retry and accept its replacement, then deliver the old B result | Old attempt cannot advance target, alter accepted state, or unlock the join | Focused lifecycle |
| Native overlap observer | Typed traces with A/B and B/C intervals; negative missing/coarse/incompatible/nonoverlapping intervals | Strict overlap for both pairs; dispatch order or delayed settlement alone cannot pass | Fast trace suite |
| Native scheduling and integration | External Grok experiment; fixture prepares disposable workspaces; B waits after real code checks until C launch is registered | Actual host receipts and overlapping task lifetimes, code from A/B/C/J integrated and independently checked, worktrees removed | Opt-in live qualification |

Each lifecycle case owns its temporary Git repositories and worker processes.
Cleanup terminates remaining fixture workers before removing their worktrees.
The opt-in native run retains its isolated directory, logs, failed evidence, and
final receipts for inspection. It never changes a production project or launches
models from the ShipLoop skill. Its barrier is experiment-only and does not prove
simultaneous code-writing. Fixture workspace creation does not qualify the
installed Ask-Agent contract or other native hosts.

Baseline before edits: 34 trace tests and the existing real-Git fanout and
rejected/retried-worker cases passed. The pilot adapter has a separate baseline
before its barrier changes.

Verification order: focused regression failures, focused green runs, full trace
and native adapter suites, full lifecycle suite, independent diff review, then
live native qualification. Record actual outcomes and unresolved host limitations
without treating offline fixtures as live-agent evidence.

Implementation keeps production ShipLoop and Dispatcher unchanged. The lifecycle
verifier now requires the explicit expected modules before importing them. A
prepared candidate must include the current accepted contributions as well as
the new worker's dependency closure; final verification requires the full graph.
Refused stale callbacks preserve target HEAD, status, dispatcher bytes, ledger,
worktree registration, and workspace presence.

Independent review strengthened the native observer against malformed or lossy
timestamps, ambiguous repeated CLI identities, unknown parent tools, and work
inserted between the initial A/B launches. Known read tools, the host's own
checklist, and exact driver help are permitted without granting lifecycle steps.
The test-only barrier publishes its release atomically and supports sequential
replay. Parent driver calls remain serial, as required by the pilot contract.

The first live attempt composed multiple help commands and was stopped before
launching any worker; its trace is retained as a failed attempt. The wrapper now
states the one-driver-command rule explicitly, including help. Live qualification
still rejects shell composition rather than treating this failed attempt as a pass.

The selected installed Ask-Agent 0.3.1 fails the bridge's required 0.4.x contract
preflight. Live qualification therefore uses the explicitly selected 0.4 fixture,
with the current installed Plan Dispatcher. It cannot establish production
Ask-Agent compatibility, prompt-driven workspace creation, or Claude/Codex
native-host behavior.

Verified local results:

- Full real-Git lifecycle suite: 32 tests passed in 807.311 seconds.
- Native trace observer: 55 tests passed, including resolution-aware overlap and
  the new rejection controls.
- Grok root-session adapter: 10 tests passed, including interleaved child events
  and independently bound terminal completion.
- Native pilot adapter: 7 tests passed after fixing a timing-dependent launch
  replay bug. Replay retains the original handle receipt timestamp and emits no
  duplicate launch event; the test forces a different timestamp without sleeping.
- A-first, B-first, burst, and stale-retry cases against a hash-recorded snapshot
  of installed Dispatcher commit `38c6b44a239a2d82949a3b161a343796ff863c9d`:
  4 tests passed in 226.967 seconds.
- Test inventory/shard checks: 3 tests passed; the Grok adapter is included in
  the normal full suite and its disjoint CI shards.

Live Grok qualification completed with real native A/B/C/J code contributions.
All four were integrated into the invoking feature branch, independently
verified, and their worktrees removed. The primary branch stayed unchanged.
The corrected root-session audit passed with guaranteed A/B overlap of 202
seconds and B/C overlap of 71 seconds, accounting conservatively for the host's
whole-second event timestamps. A fresh-process final integration audit also
passed. The B hold establishes overlapping task lifetimes, not simultaneous
code-writing.

The live run started with the previous stdout-only observer. Its original
wrapper result remains failed because worker events were incorrectly classified
as parent actions. The retained evidence was independently re-audited with the
corrected root-session adapter; earlier failures were preserved, not overwritten.
The audit binds the host summary's root identity and cwd, the matching prompt
context cwd, every root update's session identity, all four host child mappings,
and the separately observed root terminal event. Future wrapper runs bind their
root session explicitly before launch and retain that transcript automatically.

The passing evidence is in `native-run-2/root-audit-1/evaluation-final.json` and
`native-run-2/root-audit-1/final-integration-audit.json` under the directory below.

Local evidence is retained outside the checkout at
`/Users/dadleet/Documents/Codex/experiments/shiploop-parallel-tests-20260920/`.
