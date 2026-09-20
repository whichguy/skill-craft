Use the ask-agent skill to launch two separate general-purpose native workers for
read-only reviews. Do not edit any source or production file.

Inputs:
- Integration fixture root: <INTEGRATION_ROOT>
- Frozen U17 main path: <U17_MAIN_PATH>
- Frozen U17 reference path: <U17_REFERENCE_PATH>
- Fixture-auditor brief: <FIXTURE_AUDITOR_BRIEF_PATH>
- Handoff-reviewer brief: <HANDOFF_REVIEWER_BRIEF_PATH>
- Worker report paths outside source: <FIXTURE_REPORT_PATH>, <HANDOFF_REPORT_PATH>
- Parent pending record outside source: <PARENT_PENDING_RECORD_PATH>

Before dispatch, read and apply the frozen U17 main and reference at the paths
above, even if an installed skill with the same name is present.

Launch the fixture auditor first and retain its native handle. After confirmed launch,
write the pending record and explain, based only on supplied text, why a prepared worker
report is not parent acceptance: parent must still verify live target, validation and
policy before accepting an integration.

While the first task remains pending, launch the handoff reviewer and add it to the same
pending collection when native capabilities permit. Pass each frozen worker brief unchanged.
Do not force timing, delay work, sleep, poll, create busywork, use a custom driver, or
downgrade/mask the available general-purpose agent.

Continue useful parent work, then collect actual results by native notification or
join/wait. Before becoming idle, use U17's native timed-wait/status-wakeup route
or disclose that periodic updates are UNSUPPORTED if neither native facility nor
equivalent visible native progress is available. If a natural waiting-only interval
of roughly two minutes occurs, record its start/end, lack of independent parent
work and actual status updates. Use UNOBSERVED/CONDITION-NOT-TRIGGERED only for a
shorter/non-triggered interval; do not relabel an observed long silent interval.
Do not treat a short wait as passing. Verify report paths and cited hashes before final
synthesis. Return each task status, actual report result, collection route, remaining
pending state, and unresolved next action. Do not read the M2 monitoring operator oracle.
