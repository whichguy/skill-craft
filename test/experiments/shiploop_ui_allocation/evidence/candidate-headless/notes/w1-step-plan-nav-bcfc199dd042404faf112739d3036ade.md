# W1 step plan: duplicate job-event filtering and monotonic revision

Producer action: nav-bcfc199dd042404faf112739d3036ade (step-plan)

Status: planning only. This producer made no product, test, dependency, package, remote, Git, or deployment change.

## Scope and observed baseline

The explicit user requirement is duplicate-event filtering for incoming job messages while preserving a monotonic in-memory revision, with no human-facing interface. Source: <study>/candidate-headless/evidence/request.md:3.

The selected W1 context limits work to state/message behavior in product/job_service.py and product/test_job_service.py; it rules out browser, UI framework, design-skill, and environment-preparation work. Sources: <study>/candidate-headless/evidence/seed-claims.md:16-19 and <study>/candidate-headless/evidence/host-facts.md:3.

Current source already gets the prior record by job_id, rejects equal/lower revisions without mutation, and sets the service revision to the maximum accepted revision. Source: <study>/candidate-headless/product/job_service.py:9-17. The existing unittest covers only an initial accepted event. Source: <study>/candidate-headless/product/test_job_service.py:6-13.

Product contains only those two files. No README, AGENTS.md, SHIPLOOP.md, test configuration, or maintained requirements home was found. The user request is the accepted source for this delta; code behavior is observed evidence only. At its assigned documentation stage, create the smallest repository-owned requirements record if the product still lacks an existing home.

Git is not available for product (fatal: not a git repository), so source hashes in the observations log are the baseline identity. Do not initialize Git.

## Design basis and boundary

D-JOB-001 is an inferred design decision, not an accepted requirement: compare revisions per job_id, while JobService.revision remains the maximum revision accepted for any job. It is the narrowest reading of the existing state shape and current probe: a lower event for another job applies without lowering the service-wide revision. Revalidate this during test-spec and Improve; a contrary user clarification or maintained requirement replaces it.

The interaction is synchronous and local: a caller passes one mapping to handle, and the service owns jobs plus its service-wide revision. There is no connection, acknowledgement, queue, persistence, or recovery protocol. A crash-after-acknowledgement-before-processing test is therefore not applicable without expanding scope.

No debug control exists. Do not add logging, configuration, retries, persistence, validation policy, or malformed-message behavior for this work. If code must change, preserve current exception behavior and document the state invariant concisely beside the non-obvious logic.

## Planned tests

All cases are planned, not executed evidence. Add independently selectable unittest methods in product/test_job_service.py. Each creates its own JobService; setup is a fresh instance and teardown is none because no external/shared fixture exists.

| Case | Stimulus | Expected oracle | Planned selector |
| --- | --- | --- | --- |
| TC-JOB-001 | Accept job-1 revision 1, then revision 3 with a new status. | Both results apply; stored state is revision 3/new status and service revision is 3. | test_newer_job_event_updates_in_memory_state |
| TC-JOB-002 | Accept job-1 revision 2/running, then same revision with another status. | Second result is rejected; job stays revision 2/running and service revision stays 2. | test_duplicate_revision_is_ignored_without_mutating_job |
| TC-JOB-003 | Accept job-1 revision 3/running, then revision 1/stale. | Second result is rejected; job and service revision remain at the higher state. | test_stale_revision_is_ignored_without_mutating_job |
| TC-JOB-004 | Accept job-1 revision 5, then job-2 revision 1. | job-2 applies; service revision remains 5. | test_other_job_can_apply_below_global_revision |
| TC-JOB-005 | Establish job-1 revision 2 and job-2 revision 7, then repeat job-1 revision 2. | Rejected result reports revision 7; neither job changes. | test_rejected_event_reports_current_global_revision |

Malformed mapping keys, revision type/domain validation, concurrency, transport retries, acknowledgements, persistence, remote delivery, and UI are outside the accepted request. Do not claim them passed or add new behavior to cover them.

## Ordered local microplan

1. Test-spec records the explicit request, D-JOB-001, and the five case oracles. A cross-job ordering conflict uses the current correction/revision route before edits.
2. Test author adds only these state-transition cases to product/test_job_service.py and retains the current unittest route.
3. Test-red runs the new tests before production edits. They may be green immediately because current source already appears to meet the planned cases; do not manufacture a RED source change.
4. Implement changes product/job_service.py only if an exact planned case fails. Preserve the mapping input/result shape and per-job/global invariant.
5. Test-green/refine reruns changed selectors and the full discovery suite. Review any diff for response-shape drift, stale-event mutation, decreasing service revision, hidden validation, or needless abstraction.
6. Documentation adds a compact handle docstring/comment only if the method changes. At the assigned documentation stage, add a minimal requirements home if still absent; no user-facing documentation is implied.

## Harness, checks, and delivery boundary

The verified local harness is Python unittest on Python 3.14.7. The full currently discoverable suite command is:

    env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v

Run it from <study>/candidate-headless/product. Focused future commands use:

    env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_job_service.JobServiceTests.<selector>

No lint, packaging, CI, browser, remote-resident test, remote target, account, or deployment route exists in the fixture; do not install a tool or create an environment note for this genuinely local scope. Security/fuzz work is not selected for this in-memory transition; that is a scope disposition, not a security claim.

## Embedded Backchain audit

Mode: embedded, not a source-aware native Backchain invocation. The run has no run/notes selection for source-aware-native. Source: <study>/candidate-2/shiploop/references/backchain-planning.md#navigator-planning and #step-plans.

- CLAIM: same-job duplicate/stale events leave the job untouched, while accepted events cannot lower service revision.
- NEEDS: current JobService, local unittest, five independent oracles, and revalidation of D-JOB-001.
- SUPPLY: current source and Python 3.14.7/unittest provide behavior and local execution. The packet-named test-strategy result and prior Improve receipt do not exist, so they are not evidence.
- PULL: later test-spec, test-author, implementation, regression, documentation, and Improve consume this plan, source locators, and observed baseline.
- RESOLVE: test-author supplies coverage; revalidate D-JOB-001 during test-spec/Improve. No UI, external access, environment, migration, Git, or release supplier is needed.

Earlier accepted stages are explicitly synthetic. No earlier producer/model/semantic review/Improve runtime is claimed. The absent paths are:
- <study>/candidate-headless/run/results/nav-cfea7bc9643f43a48e14a5f3d8dd48cd.md
- <study>/candidate-headless/run/improve/nav-0396ef5e879c442bbf5ca59a36de76b9/receipt.md

## Evidence handoff

- Raw commands, outputs, source identities, and limits: <study>/candidate-headless/run/evidence/w1-step-plan-observations.md.
- User request: <study>/candidate-headless/evidence/request.md:3.
- Source/test: <study>/candidate-headless/product/job_service.py:9-17 and <study>/candidate-headless/product/test_job_service.py:6-13.
- Harness lifecycle policy: <study>/candidate-2/shiploop/references/repeatable-test-suites.md#select-or-revalidate-the-harness and #give-each-case-a-lifecycle.
- Requirement/handoff policy: <study>/candidate-2/shiploop/references/project-knowledge.md#maintained-product-requirements and #reference-handoffs-and-destinations.

