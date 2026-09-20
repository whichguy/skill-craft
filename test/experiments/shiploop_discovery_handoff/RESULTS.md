# Discovery handoff experiment results — 2026-09-20

Mechanical verification passed. Semantic acceptance is **mixed**, and the retained
failed outputs have not been repaired. The implementation adopts the architectural
and handoff guidance; these samples do not qualify autonomous remote execution.

## Mechanical evidence

| Run | Outcome | Scope |
| --- | --- | --- |
| Unchanged upstream baseline | PASS | 45 focused tests and smoke aggregate; clean source identity |
| First candidate checks | INCOMPLETE / observed test FAIL | Three suites passed; new relative-path assertion failed on macOS `/var` versus `/private/var`; later checks stopped |
| Revised candidate checks | PASS | 7 research, 8 routing, 31 guidance, 9 planning-context and 15 chain-context tests; smoke; generated parity; package checks |
| Final wording checks | PASS | 46 focused tests; smoke; generated parity; 20/20 package checks |

The test repair canonicalized the test's run root with `resolve()`; it changed no
production filesystem behavior. The last wording edits left the collector/chain
implementation and its tests unchanged, so those 24 integration checks were not
repeated. Every suite run pinned the base revision and matching pre/post file
fingerprint. Final test snapshot fingerprint:
`9a255033007e335edd751fb20fb62acddc74a9e3cc6e1b06942d0096665cad37`.
The baseline is `98c72b65bdd3bae624bb4939497a58d0fdd25621`. Documentation and retained
evidence were added after the final checks; the checked production/test files are
verified unchanged before commit. Smoke is a subset, not the complete repository
suite. Source/package verification is not installation or release verification.

Calibration initially used a literal packet-label assertion that did not match
the rendered format; the authoritative saved-state API verified the discovery
stage instead. A final test-helper preflight also initially encountered a gitlink
directory; its file-only calculation then matched the supplied manifest. Neither
helper correction is described as a product failure. The original candidate test
failure remains in the checked-in log.

## Fresh reader samples

All readers were fresh native contexts. Discovery outputs were bounded to eight
minutes, 24 host actions and 900 words; cold outlines to five minutes and 600
words. These are instructions, not runtime watchdogs. Probe receipts count CLI
invocations, not every host action. Source/packet digests and protected inputs
were checked separately. The fixture and acceptance protocol stayed fixed.

| Sample | Observed result |
| --- | --- |
| v1 local | Narrow discovery PASS; missing index-to-note link FAIL |
| v1 remote | Native-state limits PASS; missing investigation plan and end-user role FAIL |
| v1 cold plan | Index/receipt recovery and conditional prerequisites PASS; explicit independent-research eligibility FAIL |
| v2 local | PASS against the declared local criteria |
| v2 remote | Visible plan and state limits PASS; missing owner/bounds and end-user role FAIL; rejected target-free read after identity |
| v3 local | Local scope/direct approach PASS; Codex UI `file:line` link is not a portable handoff locator FAIL |
| final remote | Plan fields/native state/index handoff PASS; target ordering/propagation, end-user role and chronology failures retained |
| final cold plan | PASS: index/receipt recovery, scoped prerequisites, independent research eligibility and revalidation |

The v3 local snapshot differs from the shipped snapshot only by the subsequent
remote-target-passing clarification; the coordinator told it to keep using its
frozen local sample. It is not a blinded comparison. The unused v3 remote and
final local prepared cases were not run. Variant diffs and manifests identify
exact source changes; each retained assessment describes its limits.

These observations justify conditional discovery planning, explicit runtime-state
and role questions, and exact evidence handoffs. They do **not** show that prompts
alone reliably enforce ordering, permission reasoning or portable locators.
Current-target guards and later review/revalidation remain necessary. A separate
mandatory discovery scheduler would not itself repair these observed omissions.
Further cross-host or live-platform qualification remains separate work, using
real target authorization, restart/concurrency/recovery checks and actual
callback/Improve acceptance.

## Evidence layout and reproduction

- `evidence/checks/`: raw suite logs, reports and pre/post identity summaries.
- `evidence/semantic-*/`: raw notes, index, baseline, packets, launches, probe
  receipts, source-hash manifests, protected-input checks and assessments.
- `evidence/cold-*/`: rendered plan packet, launch, input hashes and checks; the
  resulting PLAN.md resides with its discovery case.
- `evidence/variant-*.diff`: prompt differences between retained snapshots.

Raw samples preserve their original absolute temporary paths and are historical
evidence, not runnable instructions or a portable project index. To inspect a
captured path, map its `semantic-*`/`cold-*` suffix into `evidence/`. Source trees
and transient Navigator run directories are deliberately not copied into the
repository. The final source is committed beside the tests; manifests/diffs
identify earlier bytes. Use the apparatus in README to create a new external
workspace and render new packets for another sample. The preparer's manifest
limit statement describes preparation only, before the human-orchestrated reader
runs. No live Salesforce, Google, SAP, AWS or other remote account was used.
