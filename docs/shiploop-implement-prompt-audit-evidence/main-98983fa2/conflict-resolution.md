# Effort-experiment reconciliation on main

The existing effort experiment is restored on main `98983fa276ffe4f2f3995ed2acd7985110773f23`. Four files were applied only after their
pre-write bytes matched the saved expectations and their replacements matched the tested snapshot. The existing
session logger, effort planner and experiment measurement helper retained their bytes. Unrelated rubric-eval work
and all saved stashes remain. No commit or push was made.

| Conflict or integration fault | Reconciled behavior | Concrete source and regression |
|---|---|---|
| Main's timing/resume changes overlapped the effort scheduler | Keep monotonic deadlines, unlimited defaults and stall handling while restoring scheduled launches and effort records | [run.py — resume loop](/Users/dadleet/src/skill-craft/test/shiploop_e2e/run.py:4348); [unlimited-default regression](/Users/dadleet/src/skill-craft/test/shiploop-e2e.test.py:3727) |
| Zero ordinary resumes suppressed a pending effort boundary | A scheduled boundary can restart without spending the ordinary-resume budget | [zero-budget regression](/Users/dadleet/src/skill-craft/test/shiploop-e2e.test.py:3750) |
| Slice's effort string shadowed its imported module, and launch metadata could use the host default | Separate `effort_level` from the module; record the schedule's D effort and pass the planner to the first launch | [slice.py — schedule setup](/Users/dadleet/src/skill-craft/test/shiploop_e2e/slice.py:376); [flow regression](/Users/dadleet/src/skill-craft/test/shiploop-e2e-slice.test.py:1404) |
| After a clear, a scheduled Grok session could reuse the prior session's ID before reporting its own | Choose a new ID for every fresh launch and read only events from that launch onward | [slice.py — session identity](/Users/dadleet/src/skill-craft/test/shiploop_e2e/slice.py:391); the same flow regression checks clear → effort change → ordinary resume and the shared deadline |

The initial conflict stages are recorded in [snapshot.json](snapshot.json). The first attempted checks exposed a
real zero-budget failure, an incorrect test wrapper and an omitted fixture dependency; their failure evidence is
retained in [the initial receipt](checks-initial/receipt.json). The corrected candidate passed the full harness and
slice suites at `5d3628b0`, then all **716 selected tests** after main's prepare-evidence change at `891be21e`.
[Final commands, exits, counts and logs](checks-main-891be21e/receipt.json).

Subsequent upstream commits change documentation and the separate suite-group runner. The direct commands used
here do not call that runner. [Source comparison](tested-delivered-source-identity.json) checks 4,334 captured
source/test files against the delivered checkout, excluding the named unrelated runner/documentation changes and
pre-existing rubric edits. All four applied files match the tested bytes. These are local harness and engine checks;
no live model, Salesforce org, installed marketplace consumer or performance experiment was run.

[Application hashes and retained stashes](conflict-resolution.json) · [complete tracked experiment overlay](effort-experiment-tracked-overlay.patch) · [seven experiment file hashes](effort-experiment-file-hashes.json)
