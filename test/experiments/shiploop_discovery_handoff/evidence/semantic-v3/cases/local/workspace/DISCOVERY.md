# Name normalization discovery

## Requested outcome

Discover the change needed for name normalization to trim edge whitespace and collapse repeated internal whitespace. This is a discovery result only; no product source or test was changed.

## Verified current behavior

`normalize_name` currently returns `value.strip()` ([src/app.py: normalize_name](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/src/app.py:1)). That meets the existing edge-trimming fixture ([test_fixture.py: Baseline.test_edges](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/test_fixture.py:4)), but does not normalize whitespace inside a name.

Observed local trace: input `"  Ada   Lovelace  "` reaches `strip()` and produces `"Ada   Lovelace"`; the three internal spaces remain. The unchanged-content baseline passed with `python3 -B -m unittest discover -v`; its command, output, and coverage limit are retained in [BASELINE.txt](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/BASELINE.txt:1).

## Proposed change for a later implementation step

Make the helper return a single-space join of its whitespace-delimited tokens. In Python terms, the intended normalization rule is equivalent to `" ".join(value.split())`: it trims edges and turns each run of whitespace into one ordinary space. Under that rule, the trace above would return `"Ada Lovelace"`; an all-whitespace string would return `""`.

The current helper has no type validation, and its existing `strip()` call already requires a string-like input. Preserve that boundary unless a separate requirement expands it; this discovery found no basis to add coercion or error handling.

## Tests needed before implementation is considered complete

Retain the edge test and add examples for repeated internal spaces, a leading/trailing plus repeated-space combination, and whitespace-only input. Add mixed whitespace only if the product definition intends "whitespace" to include tabs and newlines, which Python's `split()` does. Non-string behavior should be characterized before any deliberate change, because it is outside the stated requirement.

## Boundaries and remaining evidence

The fixture is a local pure-Python helper with no remote service, retained state, or deployment configuration ([docs/environment.md: Existing environment](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/docs/environment.md:1)). The README also marks remote observations as synthetic ([README.md: baseline instructions](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/README.md:3)). No integration, consumer, credential, deployment, or source-branch-return check applies to this supplied fixture. The directory is not a Git worktree, so the baseline is identified by command and its retained output rather than a commit.
