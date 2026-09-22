# Experiment-informed planning: results

The implemented candidate adds an explicit navigator-v4 planning return path;
v3 remains the default. Plan Improve uses its existing Until Loop to investigate
assumptions exposed by a draft plan. A stopped child can return evidence to the
earliest affected planning stage before preparation or dispatch. It cannot pass
through the successful Improve importer.

This implements the [authorized plan](shiploop-planning-experiments-plan-2026-09-21.md).
The [operating guide](../skills/shiploop/references/planning-experiments.md)
describes the bounded experiment cycle, ownership, and recovery behavior.

## What the comparison establishes

The preregistered [pilot protocol and reproducible probes](../test/experiments/shiploop_planning_experiments/README.md)
separate two questions: whether explicit experiment guidance improves decisions,
and whether ShipLoop can safely incorporate findings that invalidate earlier
planning artifacts. Both arms found the same two planted mistakes, and the independent grader found
no candidate-only consequential improvement. That does
not justify changing the default on planning-quality grounds.

| Case | Required observation or decision | Baseline and candidate observation |
| --- | --- | --- |
| A: shared seeded SQLite state | Independent worker processes must see the coordinator's rows. | Separate `:memory:` databases did not share rows. Research and plan need correction. The baseline also ran a named-file positive control. |
| B: no-overwrite publication | Existing destination bytes must survive a failed publication attempt. | `Path.rename` returned successfully while replacing destination bytes. Test strategy and plan need correction. |
| C: sufficient supplied evidence | Reuse current same-target evidence without a redundant probe. | No target execution; reused the supplied fixture. |
| D: target unavailable | Keep the premise unresolved. | No target execution; incomplete outcome. |

Both arms used one actual probe per A/B case, zero new probes for C, and no
target execution for D. A and B used actual native model work, local probes, and the selected Improve/
Until callbacks. Their prior ShipLoop stages used explicitly synthetic receipts
to reach the component under examination. All four A/B children returned actual
`stopped` packets with non-trivial, unsatisfied, cancelled reports; neither
claimed successful convergence. C and D are decision controls using fixture
inputs, not independent live-system measurements.

The actual baseline parent CLI rejected both stopped packets with `Until Loop
terminal packet is not complete`, leaving parent state unchanged. This is the
correct v3 behavior and demonstrates the missing early-return operation. V4 adds
a separate operation with immutable archives, an append-only event, and a fresh
upstream action. It preserves the successful importer's completion requirements.

## Evidence and limitations

The frozen baseline is commit
`f14103d20e2219cd14f652f91dbc1725908464f2`. Native pilot source snapshots,
case inputs, commands, outputs, packets, parent callbacks, and source manifests
are retained locally under
`/tmp/shiploop-planning-experiments-20260922/`. These temporary evidence paths
are audit locators for this run, not a portable archive or a repository test
dependency. The checked-in probe reproduces the SQLite and rename mechanisms.

This is a component pilot, not a generated-product run, complete ShipLoop
lifecycle, or cross-host certification. The host did not supply comparable model
token counts or active execution costs. Wall times overlap and cannot establish
the preregistered overhead gate. A default switch would require two distinct,
replicated decision improvements and comparable cost evidence; those claims
remain unproven.

After the frozen native trials began, `main` advanced to `c2d4fc1` with Improve
learning-handoff and scoped-commit policy changes. Integration preserves those
changes, including frozen child authority. The trials use their recorded source
snapshots and explicit no-commit scope; final hermetic and installed-consumer
checks cover the merged implementation.

The importer checks a stopped runtime packet and local evidence identities. The
parent must collect or cancel the actual native worker first; packet contents do
not independently authenticate worker death. Investigation allowances remain
host-accounted Markdown guidance, not a new runtime budget counter.

## Problems found and fixed

- Copying the entire approximately 14.5 KB review prompt into Until's contract
  exceeded its 16 KiB state limit. The pilot retained those rejected starts,
  then used compact continuity context with references to the complete prompt.
  The operating guide now makes that recovery pattern explicit.
- The first baseline parent attempt used macOS `/tmp` aliases while the CLI
  canonicalized paths to `/private/tmp`. It failed path preflight. The retained
  canonical-path attempts exercised the actual stopped-packet rejection.
- Review found that the new evidence importer read evidence twice. A concurrent
  change could make the digest disagree with the archived bytes. It now hashes
  and archives one snapshot, with a regression test.
- Review required preserving the exported default protocol policy and binding
  archive checks to the opened file rather than a preceding path check.
- The first native candidate parent callback found a real path-alias mismatch:
  the bridge canonicalized the workspace to `/private/tmp`, while a valid saved
  binding used `/tmp`. Parent state was preserved. The fix compares the bound
  workspace using the bridge's canonical identity; a different workspace still
  fails. The frozen failed attempt remains part of the experiment evidence.

The initial stopped-bridge test runner also used the wrong working directory;
no tests ran in that attempt. Its corrected invocation passed all seven tests
against an unchanged source fingerprint. A later integrated-check dispatch was
cancelled before execution when its source fingerprint changed. Neither setup
attempt is counted as test evidence. The first focused navigator-v4 suite then
reported seven passes and two failures: one fixture supplied an alias rather
than its printed receipt path, and the race fixture expected a later rejection
message instead of the earlier valid single-link rejection. Those fixture
issues are distinct from the native trial's workspace-comparison defect.

## Verification and release

Before implementation, the existing smoke suite and focused navigator-v3,
standalone-Improve, planning-context, and chain-context suites passed. Final
candidate verification and release identities are recorded here when complete.
