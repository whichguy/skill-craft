# Local formatter discovery report

## Discovery and preserved contract

The requested delta is to preserve all-uppercase acronym tokens (for example,
`API`) while retaining whitespace normalization.  The current implementation
splits on whitespace, applies `capitalize()` to every token, and joins with one
space, so `"  client API  "` currently becomes `"Client Api"`
([src/title_formatter.py:1](src/title_formatter.py#L1)).  Whitespace
normalization is an existing requirement: it is stated in
([README.md:3-4](README.md#L3-L4)) and exercised by
([test_fixture.py:10-11](test_fixture.py#L10-L11)).  This is a local-string
utility with no service, authentication, or operator-event boundary
([docs/scope.md:3-4](docs/scope.md#L3-L4)).

No separate maintained product requirement was present in the supplied
workspace.  The original request is therefore the decision basis for the new
acronym behavior; existing whitespace behavior remains preserved.  This follows
the frozen reconciliation guidance
(`/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-refined/source-snapshot/skills/shiploop/references/requirements-definition.md:30-48`)
and its proportional quality assessment
(`.../requirements-definition.md:56-100`).

## Proposed implementation and tests

Change only `src/title_formatter.py`: continue using `value.split()` and
`" ".join(...)`; transform each token with `capitalize()` unless it is
all-uppercase, in which case preserve the token.  Python's `token.isupper()` is
the proposed predicate because it directly expresses the stated rule and keeps
the current whitespace path intact.  No product files were edited during this
exercise.

Update `test_fixture.py` with independent assertions for:

1. `"  client API  "` producing `"Client API"` (the regression and existing
   whitespace behavior together).
2. Mixed whitespace such as `"client\\tAPI\\nportal"` producing
   `"Client API Portal"` (normalization remains one space).
3. A non-acronym control such as `"client portal"` producing `"Client Portal"`.

Those cases are unit-surface checks; no service or deployment check is
applicable to the documented local scope.  They follow the frozen test-case
guidance that requires exact expected outcomes and a regression that separates
broken from intended behavior
(`/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-refined/source-snapshot/skills/shiploop/references/testing-and-documentation.md:267-319`).

## Unknowns and revalidation

`isupper()` would also preserve tokens containing uppercase letters plus digits
or punctuation (for example, `API2` or `API,`).  The supplied request only
settles ordinary all-uppercase tokens such as `API`; clarify or add cases before
claiming a policy for punctuation, hyphenated tokens, Unicode, or one-letter
uppercase words.  Empty/whitespace-only input retains its current `split()`
behavior unless a later requirement changes it.

## Baseline and handoff

On unchanged fixture content, from this workspace, I ran:

```sh
python3 -B -m unittest discover -v
```

It passed: 1 test ran, 0 failures.  This is deliberately narrow fixture smoke
coverage, not evidence for unspecified token forms or a remote boundary, as
also constrained by the frozen baseline guidance
(`/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-refined/source-snapshot/skills/shiploop/references/execution-planning.md:3-31`).

Implementation handoff: edit `src/title_formatter.py`, then
`test_fixture.py`; rerun the same command from the workspace after the edit.
No callback, run-state file, product file, network, account, dependency, or
deployment action was performed.
