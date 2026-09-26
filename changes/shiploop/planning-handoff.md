---
bump: patch
---
The stages that turn the accepted plan into work now receive it. `step-plan`,
`test-spec`, `system-test-author` and `release-plan` packets name the accepted
`spec` and `plan` results under "Current planning sources", beside the test
strategy source. Before, they carried only the previous stage's result and the
test strategy, so the requirements and the plan reached step creation only if
the model searched `state.md` for them. The step-plan and test-spec duties point
at those sources.
`system-test-author` and `release-plan` are now also told to register every
planning file they produce in `evidence_refs`, like the other planning stages.
