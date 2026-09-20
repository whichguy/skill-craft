# Service discovery implementation verification

## Scope and source

The implementation adds a maintained conditional service-discovery reference,
Salesforce illustration, selective v3 stage routes/duties and shared-reference
links. It keeps the existing stage sequence, result schema and callback model.
The generated ShipLoop plugin view is synchronized with the source.
The [installed Codex selection](evidence/installed-selection.json) resolves to a
separate coverage-release checkout and was not changed. Local source/plugin
completion does not claim installed-host activation or publication. A read-only
patch check failed on five differing release-checkout paths; integration there
requires reconciliation, and no release-checkout edits were made.

[Implementation plan](../../../docs/shiploop-service-discovery-implementation-plan-2026-09-19.md)
and [maintained guide](../../../skills/shiploop/references/service-discovery.md)
are the delivery artifacts. The earlier paired study remains separate historical
research; it is not evidence that this final prompt is generally superior.

## Mechanical verification

- Before implementation: 64 checks passed across v3 guidance, discovery,
  research-template, reference-routing and packet-bounds suites. The baseline
  summary is a coordinator attestation to the actual tool run, not a signed or
  independent execution receipt: [baseline.json](evidence/baseline.json).
- The independent expected-route test failed before routing was added:
  [retained RED](evidence/tests-red.log). It then passed.
- Frozen service candidate: **93 tests passed** across v3 guidance (19), packet
  bounds (7), navigator v3 (22), discovery (27), reference routing (8), and prompt
  integrity (10). [Counts, exit codes and raw log hashes](evidence/final-regression.json).
- Cold tests cover saved/reloaded producer and pending Improve packets, current
  route selection, exact accepted result/context replacement, noninheritance by
  a later local item, and relative-reference relocation. These prove mechanics,
  not model interpretation or actual Improve execution.
- [Generated plugin parity](evidence/final-plugin-check.log) passed. Nine generated
  source-copy paths changed; existing coverage artifacts were unchanged.
  [Before/final hashes](evidence/final-plugin-changes.json).
- [Prompt delta](evidence/final-prompt-delta.json) confirms unchanged stage
  sequences. The detailed guide is not inlined into packets: added duties range
  from 307 to 1,203 characters depending on the selected stage, plus one locator.

During the longer regression sweep, another task added current-system-baseline
guidance and three related checks in the shared checkout. Those edits were
preserved. The combined source passed **96 targeted tests** across the same six
suites, with unchanged source/test hashes throughout that run:
[combined regression](evidence/combined-regression.json). Generated plugin parity
also passed: [combined package check](evidence/combined-plugin-check.json).
Independent review found no conflicting routes, weakened service duties or
changed service guide. The earlier hashes and semantic snapshots remain historical candidate evidence.
Delivery review found concurrent baseline hunks in the retained selected-file
patch; that patch is not a service-only release diff. The frozen service guidance
and explicitly selected service tests define the later integration, and baseline
changes are not attributed to this implementation. The eight model exercises below were not
rerun against the combined source.

## Fresh-context exercises

The cases use actual rendered v3 packets after save/reload, frozen package
references and small synthetic repositories. Prior producer/Improve transitions
are synthetic fixture setup, not an executed model workflow. Fresh agents were
instructed to read only their assigned case and frozen guidance, run its small
baseline, and write a report without product edits or callbacks. Evaluation
criteria were withheld from participants and frozen before launches.

[Prelaunch rubric](evidence/semantic-rubric.json),
[first launch record](evidence/semantic-launch.json),
[refinement launch record](evidence/refined-launch.json), and
[final focused launch](evidence/final-launch.json) distinguish selected runs from
prepared but unexecuted cases. Model baselines and source-reading claims are
participant evidence; file hashes independently verify unchanged fixture inputs,
not a filesystem-read trace. This is a bounded qualitative exercise, not an A/B
comparison, statistical reliability estimate, or full ShipLoop application E2E.

| Case | Initial producer | After first refinement | Final focused check |
| --- | --- | --- | --- |
| Remote CRM discovery | Partial: interim access policy, schema-preservation handoff and conditional async ownership omitted | Cache, schema, reuse and file/check handoff passed; conditional async owner/acceptance gap remained | Partial: safe cache/reuse/file handoff retained; unrelated-field preservation and async acceptance/completion still omitted |
| Cold step planning with superseded cache decoy | All six criteria passed | Not rerun | Not rerun |
| Local authentication logging | Safe decisions; conditional emitter/test handoff incomplete | All four criteria passed | Not rerun |
| Local formatter control | All three criteria passed | All three criteria passed | Not rerun |

The first refinement required safe interim policy-enforced reads/denial,
preservation/reconciliation/read-back, and conditional file/test changes for
unknown ownership or coverage. The final refinement explicitly calls for the
processor/recovery owner and durable acceptance/completion boundary only when
an affected flow depends on asynchronous work. It does not require a broker or
block unrelated work.

The current decision note survived the old shared-cache decoy in the cold-plan
case: the agent chose a policy-enforcing direct read or denial, preserved remote
fields, kept polling and used the existing application audit sink. That case
was tested before the later discovery-only cue refinements; its accepted note
and stage duty were unchanged. Local-auth proposed a success event after session
creation only if adequate existing coverage did not already own the outcome.
The formatter stayed local with no service, authentication, cache or telemetry
addition. Its refined report has a minor citation error: it attributes whitespace
normalization to README, while the fixture test and source establish it. That
raw report is preserved rather than silently repaired.

[First independent assessment](evidence/first/review.json) and
[refined independent assessment](evidence/refined/review.json), and
[final independent assessment](evidence/final/review.json) retain partials.
Across eight actual reader reports, final remote discovery still missed explicit
unrelated-field preservation and the async acceptance/completion boundary. Its
diagram also inferred a caller edge absent from the fixture. The guide and stage
cues explicitly require the missing contracts, but this study does **not** prove
reliable first-pass completeness or prompt superiority. Normal Improve must
review actual decisions and unresolved boundaries; a locator is not compliance.
No further prompt tuning was selected from this small unpaired sample.
Reports, launch text, packets, source selections and fixture inputs are retained
under the corresponding evidence directories. Raw reports keep their original
absolute observation paths. Full frozen packages and detailed diagnosis logs
remain at `/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/`;
manifests retain their exact hashes. The generator can create a fresh exercise
from current source, but cannot imply that a rerun used historical source bytes.

## Broader regression limits

The optional broader sweep was stopped after the user questioned the need for
whole CI on this prompt enhancement. The targeted checks above are the
appropriate verification surface for the change. Of the 90-suite inventory,
**89 suites completed: 87 passed and two failed**. The last legacy
`shiploop-action-walk.test.py` suite was intentionally interrupted; its nonzero
exit is not a third defect. The sweep is partial, and spans source refinements
and concurrent checkout changes rather than one frozen final source snapshot.

The initial sequential run stopped at `shiploop-capability-runtime.test.py`;
the remaining inventory was then attempted without stopping at individual
failures. [Final accounting](evidence/broader-accounting.json) distinguishes
the intentional interruption from failures. The continuation runner's raw
completed/failed wording counts subprocess exits, so its totals require that
qualification. Both raw logs are retained with hashes.

Two failures have been observed outside the owned change:

1. `shiploop-capability-runtime.test.py`: a gateway child returned empty stdout
   during shared-ledger initialization. The gateway is byte-identical to HEAD;
   focused repetitions reproduced the intermittent failure. Inspection identifies
   a create-before-complete-JSON race and an uncaught ledger error path. Successful
   retries do not erase the initial failure.
2. `shiploop-discovery-decision-followup.test.py`: two expected-error assertions
   received an external-study calibration error instead of the expected generic
   audit error. Targeted retries passed. Investigation points to fixture/module
   isolation, but the precise failing process state was not retained; that cause
   remains an inference. These pre-existing experiment files were not changed.

[Independent file hashes](evidence/unrelated-suite-files.json) distinguish the
tracked unchanged gateway from existing untracked experiment fixtures. Those
unrelated harness issues were not repaired under this service-prompt change.
No clean aggregate pass is claimed. No remote org, actual authorization change,
cache invalidation mechanism, notification delivery or deployed log retrieval
was tested by these exercises.


## Git delivery candidate

The user subsequently authorized commit, merge and push. The isolated candidate
ports only service additions onto `73ed1462d527ae25f829616164378a8fdfb3c4ca`,
preserving newer upstream guidance and versioning ShipLoop `0.18.9`.
[Delivery verification](evidence/delivery/verification.json) records **105 targeted
tests passed**, package metadata checks and full generated-view parity, with
unchanged source/test inputs. The v3 guidance suite contains 26 upstream tests
plus four service tests. Independent diff review found no blocking issue.
This is integration verification; the earlier model-study observations remain
bound to their original frozen packets. No full CI or model study was rerun.
