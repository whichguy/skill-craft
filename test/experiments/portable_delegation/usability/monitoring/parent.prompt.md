Use the ask-agent skill to launch two separate general-purpose native workers for
read-only reviews. Do not edit any source or production file.

Inputs:
- Integration fixture root: <INTEGRATION_ROOT>
- Frozen U16 main path: <U16_MAIN_PATH>
- Frozen U16 reference path: <U16_REFERENCE_PATH>
- Fixture-auditor brief: <FIXTURE_AUDITOR_BRIEF_PATH>
- Handoff-reviewer brief: <HANDOFF_REVIEWER_BRIEF_PATH>
- Worker report paths outside source: <FIXTURE_REPORT_PATH>, <HANDOFF_REPORT_PATH>
- Parent pending record outside source: <PARENT_PENDING_RECORD_PATH>

Before dispatch, read and apply the frozen U16 main and reference at the paths
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
join/wait. If a natural waiting-only interval of roughly two minutes occurs, record its
start/end, lack of independent parent work and actual status updates; otherwise say UNOBSERVED/CONDITION-NOT-TRIGGERED.
Do not treat a short wait as passing. Verify report paths and cited hashes before final
synthesis. Return each task status, actual report result, collection route, remaining
pending state, and unresolved next action. Do not read the M1 monitoring operator oracle.
