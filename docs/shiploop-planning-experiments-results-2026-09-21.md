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
planning artifacts. Both arms found the same two planted mistakes, and the
independent grader found no candidate-only consequential improvement. That does
not justify changing the default on planning-quality grounds.

| Case | Required observation or decision | Baseline and candidate observation |
| --- | --- | --- |
| A: shared seeded SQLite state | Independent worker processes must see the coordinator's rows. | Separate `:memory:` databases did not share rows. Research and plan need correction. The baseline also ran a named-file positive control. |
| B: no-overwrite publication | Existing destination bytes must survive a failed publication attempt. | `Path.rename` returned successfully while replacing destination bytes. Test strategy and plan need correction. |
| C: sufficient supplied evidence | Reuse current same-target evidence without a redundant probe. | No target execution; reused the supplied fixture. |
| D: target unavailable | Keep the premise unresolved. | No target execution; incomplete outcome. |

Both arms used one actual probe per A/B case, zero new probes for C, and no
target execution for D. A and B used actual native model work, local probes, and
the selected Improve/Until callbacks. Their prior ShipLoop stages used explicitly synthetic receipts
to reach the component under examination. All four A/B children returned actual
`stopped` packets with non-trivial, unsatisfied, cancelled reports; none
claimed successful convergence. C and D are decision controls using fixture
inputs, not independent live-system measurements.

The actual baseline parent CLI rejected both stopped packets with `Until Loop
terminal packet is not complete`, leaving parent state unchanged. This is the
correct v3 behavior and demonstrates the missing early-return operation. V4 adds
a separate operation with immutable archives, an append-only event, and a fresh
upstream action. It preserves the successful importer's completion requirements.

After the workspace-identity fix, the parent executed the actual reconciliation
CLI against the retained native child receipts:

| Check | Case A | Case B |
| --- | --- | --- |
| First reconciliation | Exit 0; fresh `research` action | Exit 0; fresh `test-strategy` action |
| Accepted event | One stopped-child reconciliation | One stopped-child reconciliation |
| Exact replay and cold `next` | Exit 0; state bytes unchanged | Exit 0; state bytes unchanged |
| Successful-import replay at its proper inbox path | Exit 2; stopped-record guard; unchanged state | Exit 2; stopped-record guard; unchanged state |

These parent operations used revised source
`836a1d99ec94e94ae3c9361fe449ca1df9287f2c`, with the source fingerprint
`17ae1ce91ed444ade034f2f564f4930c85c3a59420d55647bc7e42bef1bd43a3`.
They did not rewrite the earlier failed attempt, rerun the child, or claim the
frozen candidate snapshot already worked. The independent supplemental review
accepted this narrow opt-in transition/recovery evidence and retained its
no-default-switch decision.

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
standalone-Improve, planning-context, and chain-context suites passed. The final
source's focused navigator-v4 suite passes 10 tests and its consumer-boundary
suite passes four. These cover actual stopped-runtime settlement, transaction
recovery, repeated reconciliation, source supersession, v3 rejection/reading,
authority preservation, and dispatch readiness.

A read-only copy of the generated package, installed into a disposable directory
containing spaces and invoked from an unrelated consumer directory, successfully
initialized and recovered saved v3 and v4 states. The old frozen reader rejected
v4 with `unsupported navigator protocol version`. Package bytes and recovered
state bytes were unchanged. This proves copied-package invocation, not host
catalog activation. Both Mermaid flow diagrams were rendered and visually
inspected for readable labels and correct branches.

The complete catalog now has passing coverage: **28 core suites and 101
ShipLoop suites**, including all 13 action-walk scenarios. The broad run used
the unchanged `836a1d9` source and fingerprint recorded above. Shards 2 and 3
passed. Core initially failed its stale suite-count/smoke-list expectations;
shard 1 stopped at an error-message assertion that omitted newly supported
protocol 4. Those failed invocations remain recorded as failures.

After correcting only those test expectations and the test README, the affected
suites passed (19 inventory tests and six consumer-CLI test methods). The 27
other core suites, shard 1's ten preceding suites and separately executed 23
remaining suites, plus shards 2 and 3 account for every catalog entry. Runtime
and generated-package files remained unchanged during these repairs. The
documentation whitespace check also caught and prompted removal of a trailing
blank line. This is composed full-catalog evidence, not a claim that the
original failed aggregate invocation passed.

Raw regression logs are retained in
`/tmp/shiploop-qualification-20260922-193012/`,
`/tmp/shiploop-planning-experiments-shard1-remaining-POmx7Z/`, and
`/tmp/shiploop-planning-experiments-20260922-fixture-checks-202009/`.
The final test/documentation snapshot has fingerprint
`13ec6d8197dda5cf888260ce723897248e1c46fa8c521d3dfeb462c7c15aaf16`;
the fingerprint excludes the report itself. The pull request records the
separate Linux smoke CI and merge outcome:
[#17](https://github.com/whichguy/skill-craft/pull/17).
