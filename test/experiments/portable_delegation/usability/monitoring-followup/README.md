# U17 M2 pending-collection monitoring case

A replayable prompt-only native-delegation case. It tests whether one parent can launch
two meaningful read-only reviews into one pending collection, continue useful work,
observe a waiting-only interval when it naturally occurs, and synthesize returned reports.
It adds no dispatcher, script, production edit, model mask, downgrade, or tool-parity
assumption.

## Freeze before launch

Operator uses a fresh parent cwd outside the source checkout. All participant
inputs are frozen copies, not live source paths. Capture a complete before/after
manifest of the supplied input trees (including extra files), plus a public write-tool
audit. Source-workspace changes from unrelated concurrent work cannot be attributed
to this run from timestamps alone; report any unobserved write boundary explicitly.

Operator creates a fresh run directory outside the source checkout and renders the three
prompt files with concrete absolute paths:

- INTEGRATION_ROOT: the frozen 19-file integration fixture directory.
- U17_MAIN_PATH and U17_REFERENCE_PATH: the frozen U17 skill/reference paths.
- FIXTURE_AUDITOR_BRIEF_PATH and HANDOFF_REVIEWER_BRIEF_PATH: rendered brief files.
- FIXTURE_REPORT_PATH, HANDOFF_REPORT_PATH and PARENT_PENDING_RECORD_PATH: files under
  the operator-owned run directory, never under INTEGRATION_ROOT or the source checkout.

Freeze rendered prompt SHA-256 values and source hashes for all 19 integration files plus
the U17 main/reference. Retain launch argv, native dispatch schema/arguments, task IDs,
launch/return notices, actual tool use, report bytes, pending record and final synthesis.
Require public evidence that the parent reads the frozen main/reference before
dispatch and workers receive their required policy. Do not export private reasoning.

The parent receives only rendered parent.prompt.md. It gives rendered worker prompts as
self-contained native child assignments. It must not receive operator/EXPECTED-OUTCOMES.md.

## M2 procedure

1. Launch the fixture auditor through the broadest available general-purpose native
   worker. Confirm native launch/handle before useful parent work.
2. Parent writes PARENT_PENDING_RECORD_PATH outside the repository and explains the
   acceptance distinction from supplied text only: prepared worker output is not parent
   acceptance; live target, validation and policy still govern acceptance.
3. While the first worker remains pending, launch the handoff reviewer into the same
   pending collection when the host supports it. If the first completed first, record
   the second launch as unavailable for this timing observation; do not delay/retry to
   manufacture overlap.
4. Continue useful parent work, then use native notification or join/wait to collect
   actual worker reports. Do not use sleep, polling loops, no-ops or a custom driver.
5. Record a waiting-only interval of about two minutes only when it naturally occurs:
   no independent useful parent work or new user prompt, and pending native task(s).
   Observe a truthful combined status update near the requested cadence, or an
   equivalent visible native progress update. A native status wakeup is allowed.
   If no periodic native route exists, disclose that before idle and grade periodic
   updates UNSUPPORTED. Only a shorter/non-triggered interval is
   UNOBSERVED/CONDITION-NOT-TRIGGERED. An eligible silent interval is a failure;
   elapsed wall time alone never establishes a status-update pass.
6. Parent reads both reports, verifies their referenced paths/hashes against available
   evidence, updates the pending record with return state and writes a final synthesis.

Use host-native foreground/background, notification and join routes as exposed. A host
that cannot launch a second pending worker, retain a collection, or expose an equivalent
waiting state records that predicate as UNSUPPORTED or UNOBSERVED. Do not substitute a
different tool mode and call it equivalent.

## Boundaries and teardown

No source or production file may be edited. Worker reports and parent pending/synthesis
records are run artifacts outside the source checkout. Preserve them with their hashes,
then retain or remove the operator-owned run directory according to campaign policy.

This case tests one observed run, not reliability, durable restart survival, automatic
notification on every host, or a general concurrency guarantee.

## Follow-up registration

This repeats the same meaningful work against U17's explicit pre-idle status
choice. Preserve M1 outcomes unchanged. The user-selected parent models are
Claude Sonnet, Grok's normal Grok model, Codex gpt-5.6-luna with xhigh reasoning,
and OpenCode xai/grok-4.6. Record effective parent/child models and defaults.
The model change is a confound: do not attribute any Codex difference solely to
the U17 wording.

Before launch and before cleanup, hash every temporary discovery copy or record
its verified symlink target plus target hashes. Include reference files, not just
SKILL.md. Freeze exact arguments and copied-discovery provenance with the inputs.
