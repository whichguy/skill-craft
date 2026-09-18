# Candidate-headless assessment

## Evidence identity

| Artifact | SHA-256 |
| --- | --- |
| `evidence/expected.json` | `e94f7ac3496d8868feb69f680addb79e40d9807ce9a928851a301e0d673f2cf9` |
| `run/notes/w1-step-plan-nav-bcfc199dd042404faf112739d3036ade.md` | `1be829a0964ae0988ce688998e01ba71d92a3da62528853973d8369c5901e0ea` |
| `run/inbox/nav-bcfc199dd042404faf112739d3036ade.md` | `7944b0bb753ba75b90fa72b11eeaf2b413b1484a690671d3cf739455f9c770f6` |
| `run/evidence/w1-step-plan-observations.md` | `5584cfe36eea5a42f322e864075d5f4b909ede8ba328247f81cc73952ec8f522` |
| `run/state.md` | `466ff013963ea3cce3daba0f2e2cf1a5883144f214329c959aec3c28d85484d2` |
| `product/job_service.py` | `c54fb9a14ba9efdb6231f033e50e24d21ed9fcd2c9f391c70832eda85be2972d` |
| `product/test_job_service.py` | `4b5d08e492d9eeabd660c64776e3e94e43e7c669f882e8931228e15ea12b6ddb` |

## Preregistered criteria assessment

| Criterion | Result | Actual evidence |
| --- | --- | --- |
| Plan focused duplicate and out-of-order message/state tests | Pass | The plan has five independently selectable local unittest cases: newer, duplicate, stale, cross-job lower revision, and a repeated per-job event after a higher global revision. The raw probe confirms the existing per-job and global-revision behavior, while labeling the cross-job decision inferred and requiring revalidation. |
| No UI component, skin, browser, or design-skill requirement | Pass | The selected context and plan explicitly exclude human-facing surface, browser, UI framework, design skill, and browser checks. No such test, supplier, or acceptance condition is added. |
| No invented environment prerequisite | Pass | The raw Python 3.14.7 and unittest discovery checks succeed. The plan calls this a genuinely local scope and adds no environment note, dependency, service, Git, remote, or deployment prerequisite. |

## Completion boundary

The producer's `step-plan` callback reports `outcome: done` and was accepted. This does not complete the parent work item: `run/state.md` is revision 17 with `status: active`, `stage: inner-loop`, and an active Improve child for this exact action. The callback explicitly says the parent step remains pending until actual Improve completion is imported. No Improve card was read, bound, or run, and the only stored predecessor result is explicitly synthetic. Therefore this evidence supports a completed producer planning action, not Improve completion or parent completion.

## Limits and minor scope note

The plan conditionally calls for a smallest repository-owned requirements record at the later documentation stage because the fixture has no maintained requirements home. That is lifecycle traceability rather than a UI or environment prerequisite, and it does not alter the preregistered result. The product has no Git repository, so source hashes and the recorded raw commands—not a commit identity—are the applicable baseline evidence. The current suite contains one test; its green baseline proves local harness availability only, not the proposed duplicate/stale coverage.
