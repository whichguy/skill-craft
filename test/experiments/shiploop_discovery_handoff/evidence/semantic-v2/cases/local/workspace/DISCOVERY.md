# Discovery: name whitespace normalization

## Scope and evidence

The accepted incoming request is to normalize names by trimming edges and
collapsing repeated internal whitespace; it explicitly excludes implementation
([README.md](README.md):3). The existing local entry point is
`normalize_name(value)` in [src/app.py](src/app.py):1-2. It currently returns
`value.strip()`, which removes leading and trailing whitespace only.

A read-only runtime probe of `"  Ada    Lovelace  "` returned
`"Ada    Lovelace"`. This verifies the gap: internal repeated whitespace is
preserved today. The initial check passed, but it is one edge-trimming assertion
only; see [BASELINE.txt](BASELINE.txt) and
[test_fixture.py](test_fixture.py):4-6.

## Recovered current system

This is a dependency-free, local Python string helper. The only discovered
consumer is the unit-test import in [test_fixture.py](test_fixture.py):2.
[docs/environment.md](docs/environment.md):1-3 states that there are no remote
services, retained state, or deployment configuration. No UI, API, async worker,
identity, cache, persistence, or remote consumer was discovered in the
five-file workspace inventory. There is no repository-local skill package; a
normal helper-and-test change is sufficient.

The fixture directory is not a Git repository: `git status --short --branch`
exited 128. Together with the environment note, this leaves no discovered
source-return, CI, deployment, or release route. That is a local-fixture
observation, not evidence about any external source repository; recheck if a
future change is placed in one.

## Proposed product delta; not implemented

For string inputs, change the helper's output contract from “trim only” to
“one ASCII space between each non-whitespace token.” A standard-library
expression such as `" ".join(value.split())` is the likely implementation
shape because it both removes edges and collapses internal whitespace. This is
a proposal for the later specification/implementation step, not a code change.

Preserve the public function name and existing edge-trimming behavior. No
documented input-type contract exists beyond the current string fixture; retain
the current treatment of non-string values unless a later requirement changes
it. The exact treatment of tabs, newlines, and Unicode whitespace should be
made explicit in the specification. Python's default `str.split()` behavior
would normalize those forms too, which is consistent with the broad word
“whitespace” but is not yet separately tested.

## Required later verification

Before implementation, define cases for: unchanged single-token names; existing
edge trimming; repeated internal spaces; mixed internal tabs/newlines if the
broader whitespace rule is accepted; whitespace-only input producing an empty
string; and preservation of non-whitespace characters. The existing
`unittest discover` command can remain the local regression command, but the
current one-test baseline does not cover this delta.

Quality screening found no evidence of service availability, security,
accessibility, deployment, or data-migration requirements for this local
function. Relevant constraints are deterministic behavior, no new dependency,
Python compatibility (Python 3.14.7 observed), and executable unit coverage.
No performance target or supported-version matrix is documented; do not invent
one.

## Discovery status

The discovery output is complete for the local fixture: the observed behavior,
requested delta, test gap, and local environment boundary are recorded. Product
source and tests remain unchanged. The baseline is a passing narrow check, not
requested-feature verification.
