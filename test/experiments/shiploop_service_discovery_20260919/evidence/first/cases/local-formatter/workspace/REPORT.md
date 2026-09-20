# Local formatter discovery and implementation handoff

## Discovery and baseline

This exercise is planning-only; no product, test, dependency, run-state, or
delivery artifact was changed. The formatter is a local string utility with no
service, authentication, or operator-event boundary ([scope.md - local-only
boundary](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-formatter/workspace/docs/scope.md:3)). Therefore no account, network, API, browser, cache, observability, or deployment check is applicable to this delta.

The existing implementation splits on whitespace, capitalizes every resulting
token, then joins them with one space ([title_formatter.py - `format_title`
implementation](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-formatter/workspace/src/title_formatter.py:1)). The concrete current trace is `"  client API  "` -> `"Client Api"`, confirmed both by the unchanged runtime observation and the existing assertion ([test_fixture.py - current whitespace fixture oracle](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-formatter/workspace/test_fixture.py:11)).

Baseline run, before any edit: `python3 -B -m unittest discover -v`, in this
workspace, under Python 3.14.7. Result: 1 test passed, 0 failed. This is only
the deliberately narrow fixture smoke route ([README.md - required baseline and
coverage limit](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-formatter/workspace/README.md:3)); it does not yet assert the requested result. The workspace is not a Git repository, so the starting code/test identities were SHA-256 `80cedc1d82d80aa82ccf03199c16b57af0cb943daed92e18ab3325bb2a582bcb` (`src/title_formatter.py`) and `c18a110514467419e0f9f58ce050f52f04f2a99c91ce546dd0b4762ad3a43147` (`test_fixture.py`).

## Proposed change and decisions

The request-backed requirement is: normalize arbitrary whitespace exactly as
today, while leaving all-uppercase whitespace-delimited tokens unchanged (for
example, `API`). Proposed implementation: retain the existing `split()` /
`" ".join()` flow; for each token, return it unchanged when `part.isupper()` is
true, otherwise use `part.capitalize()`.

This is a deliberate mechanical definition of “all-uppercase,” not an acronym
dictionary: it preserves `API`, `HTTP`, and `API2`; it does not preserve `iOS` or
`API-v2` because Python's `str.isupper()` returns false for those examples. Keep
mixed-case branded words outside this request unless a later instruction expands
scope. Non-uppercase tokens should retain the observed title-casing behavior.

No maintained requirements document appears in the allowed workspace; the README
only records the test route and `SHIPLOOP.md` only tells readers to inspect current
source/decisions ([SHIPLOOP.md - project-knowledge direction](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/cases/local-formatter/workspace/SHIPLOOP.md:3)). At a permitted documentation step, record the accepted behavior in the repository's authoritative requirements home; if none is selected, the frozen policy proposes `docs/requirements.md` ([project-knowledge.md - requirements-home fallback](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/source-snapshot/skills/shiploop/references/project-knowledge.md:176)). That file is planned, not created here.

## File and check handoff

| Role | Planned action |
| --- | --- |
| `src/title_formatter.py` | Make the one-token preservation change above. |
| `test_fixture.py` | Replace the legacy `"Client Api"` oracle with `"Client API"`; add independent cases for leading/trailing/repeated whitespace, multiple uppercase tokens, ordinary lowercase words, and whitespace-only input. |
| authoritative requirements home | Add the request-backed clause and link its tests once that home is selected. |

After implementation, rerun `python3 -B -m unittest discover -v` from this
workspace and record the exact result. Use the same native unittest harness; it
is the existing available route, while its smoke result must remain labeled as
partial coverage ([repeatable-test-suites.md - harness and smoke limits](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic/source-snapshot/skills/shiploop/references/repeatable-test-suites.md:9)). Revalidate the `isupper()` choice if the intended treatment of Unicode, punctuation, digits, or mixed-case product names differs. No remote or deployment revalidation is needed for the documented local-only boundary.
