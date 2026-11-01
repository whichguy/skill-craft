# User-listing Chain B: rules and offline coverage

Status: the Chain B apparatus is implemented and calibrated offline. No live model run, product change, promotion result, or cost-benefit claim is part of this slice.

## Cases and exact rules

The chain begins with the existing user-listing case and keeps its fixture unchanged.

1. **user-teams — light K2.** Store Engineering for Ada Lovelace and Grace Hopper, and Support for Alan Turing. A user must match both name and team filters. Team matching is exact and case-sensitive; an empty or unknown team returns no users. Apply filters before pagination. The exact query value include=team adds the stored team name to every list result, paged item, and by-id result. Every other include value is ignored, and the default user object stays unchanged. This base has only an in-memory store, routes, filters, and paging; the request adds no persistence, CLI, or audit subsystem.

2. **user-summary — K1.** Add GET /users/summary with total and by_team counts across all matching users, omitting groups with no matches. Use the same name and team filters GET /users applies, by explicit reference to the predecessor request. Ignore page, size, include, and other query parameters on this route, including invalid page or size values. Permit other response keys; no matches return total 0 and an empty by_team object.

3. **user-team-casefold — K3.** Replace only the case-sensitive team comparison. Both listing and summary now match a team name while ignoring letter case, and still require an exact name after that comparison. Stored names, returned team values, and by_team keys retain their original spelling. The request names the earlier rule and the tests that state it.

Every link says the existing project behavior and tests keep working. The inline probes use positive, correctly spelled values for K2 and K1; K3 adds a positive case-fold probe. The two strict-case hidden checks have separate IDs: team-filter-case-sensitive in K2 and summary-team-case-sensitive in K1. K3 removes only those IDs from the inherited acceptance. It retains all 11 original user-listing checks and every other K2/K1 check.

## Reference lineages and hidden coverage

The existing node-base fixture and user-listing acceptance are unchanged. Each link has two independent reference lineages:

- The reference starts from reference_user_listing.py and keeps its separated name filter and pagination helper.
- The alternative starts from the existing user-listing ALTERNATIVE, where listUsers accepts filters and the server owns paging. Its extra page metadata remains allowed.
- The summary and case-fold builders continue each lineage from its preceding reference. All new implementation fixtures live under test/fixtures/quality; none is shipped as product source.

The acceptance sets contain 15 checks for K2 (the original 11 plus four team checks), 20 for K1 (K2 plus five summary checks), and 23 for K3 (K1 minus the two retired strict-case checks plus five case-fold and spelling checks).

| Link | Frozen defect | Failed own probes | Failed hidden checks |
|---|---|---|---|
| K2 | base without teams | team filter; include | team-filter-exact; team-filter-case-sensitive; team-filters-combine-before-page; team-include-opt-in |
| K2 | team applied after pagination | node tests | team-filters-combine-before-page |
| K2 | team substring matching | node tests | team-filter-exact |
| K2 | case folding introduced early | node tests | team-filter-case-sensitive |
| K2 | team leaks into default objects | node tests; include probe | list-unchanged; user-by-id-unchanged; name-filter; page-envelope; partial-last-page; page-defaults; filter-then-page; size-bounds; team-filter-exact; team-filters-combine-before-page; team-include-opt-in |
| K1 | base without summary | summary probe | summary-total-by-team; summary-uses-user-filters; summary-unpaginated-ignores; summary-no-matches; summary-team-case-sensitive |
| K1 | summary drops filters | node tests; summary probe | summary-uses-user-filters; summary-no-matches; summary-team-case-sensitive |
| K1 | summary counts a page | node tests; summary probe | summary-unpaginated-ignores |
| K1 | summary validates ignored page | node tests; summary probe | summary-unpaginated-ignores |
| K1 | summary route is shadowed | node tests; summary probe | summary-total-by-team; summary-uses-user-filters; summary-unpaginated-ignores; summary-no-matches; summary-team-case-sensitive |
| K1 | empty team means all in summary | node tests | summary-no-matches |
| K3 | base with the old strict rule | case-fold probe | team-filter-casefold-listing; summary-team-casefold; team-response-spelling-preserved; summary-group-spelling-preserved |
| K3 | only listing ignores case | node tests; case-fold probe | summary-team-casefold; summary-group-spelling-preserved |
| K3 | team uses substring after case folding | node tests; case-fold probe | team-filter-exact; summary-no-matches; team-casefold-exact-match |
| K3 | returned team value is lowercased | node tests; case-fold probe | team-include-opt-in; team-response-spelling-preserved |
| K3 | summary group keys are lowercased | node tests; case-fold probe | summary-total-by-team; summary-uses-user-filters; summary-unpaginated-ignores; summary-team-casefold; summary-group-spelling-preserved |

The frozen matrix is in EXPECTED in test/shiploop-e2e-user-chain.test.py. The starting base is included as a negative control when checking that every new acceptance ID can fail; targeted defects are graded against the same full set. Both correct lineages pass every link's own probes and acceptance. K3 also passes the complete inherited inline regression and retention checks on both corresponding lineages. The two retired strict-case IDs pass against K1 and fail against a correct K3 delivery.

## Retention and semantic review

For this pilot, the file-retention check verifies prior project files remain present and requires the three living files. It is scoped to these preservation prompts, not a general rule about allowed file organization. Other retention checks compare dependencies and require every prior R and AD ID to remain, including IDs under Retired or Superseded. A prior architecture with zero AD IDs is valid.

Retention does not require a new ID, keyword, file, or larger test count. The test demonstrates that an in-place rewrite, a new ID with the old ID retired, and stale active text all pass mechanical ID retention. The delta output distinguishes changed, retired, and untouched entries, but it is only a locator. A reviewer must check whether the live requirement and decision actually changed as requested; the harness does not claim to grade semantic retirement.

K2 delta patterns quote the two prior user-listing clauses narrowed by include=team. K3 uses team as the locator in spec.md and architecture.md. The K1 acceptance source quotes its exact predecessor-reference sentence and the earlier check clauses it reuses. The dated 2026-11-01 SPEC amendment governs this explicit reference and requires predecessor review before a dependent run.

## Verification and live-run boundary

The focused suite is:

    python3 test/shiploop-e2e-user-chain.test.py
    python3 test/shiploop-e2e-learning-records.test.py

The first command runs declaration, retention-control, two-lineage calibration, defect-matrix, and chain-regression checks. The second checks probe-term registration. Both calibration and retention are registered in suite_catalog.py; the parent owns integration; these cases are not added to an automatic campaign.

This checkout's apparatus source began at 49d21bc5bd3c76dfd5a3a9b1c88a840c022bb019. The post-change harness commit/tree is pending parent integration. Any later live chain keeps the subject pinned to published release 9273b4cfda87761f4ad002324b238e6d8f755bfb (skill-craft 2.32.1 / ShipLoop 1.30.2), separate from the apparatus revision. The frozen subject plugin hash is not measured here and must be recorded by the live-run coordinator. The new catalog cases are not in that published subject. Build and select the pinned subject explicitly from its clean published source with --plugin-dir; a preflight-only run is not evidence that the selected plugin matches the frozen subject.

The previous live Chain A runs used Terra xhigh while the approved Chain B plan calls for high, so their run numbers are not comparable. No source-retrieval evidence was collected here; an eventual run must report retrieval as unknown if that evidence is absent.

Raw development runs were retained outside this checkout under /Users/dadleet/e2e-runs/2026-11-01/incremental-implementation-6vr1vrbo/chain-b-development. The final 19/19 result is in user-chain-test-gFsb2X/user-chain.test.log, and the probe-term check is in probe-terms-S7rD1g/probe-terms.test.log. Earlier failed diagnostics remain in their own uniquely named directories, including user-chain-test-v0EB3g, user-chain-test-mrqmnG, user-chain-test-OsBy1D, and user-chain-test-zyaMKJ; none was overwritten.


Independent verification after implementation passed 193 tests: this chain (19), unchanged brownfield behavior (24), delta/inheritance (80), probe-purpose checks (13), expectation-source contracts (5), and suite registration (52). Source identity stayed unchanged throughout that run. Raw proof is in ../chain-b-verification-01 under the external evidence root named above. The published locator was refreshed after this no-model verification, before any live run; this documentation update changes no checked code.

A second independent verification passed 165 additional tests (153 quality checks and 12 suite/boundary checks) after registering the complete withheld calibration inputs. Its source identity stayed unchanged; proof is in the external chain-b-verification-02 directory. The old catalog entries retain their original formatting and semantics.
