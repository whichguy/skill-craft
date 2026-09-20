# Discovery: name normalization

## Scope and current baseline

The current request is to normalize names by trimming edges and collapsing
repeated internal whitespace; it explicitly excludes implementation
([README.md](README.md):3). The affected entry point is the local Python helper
`normalize_name` in [src/app.py](src/app.py):1-2. It currently returns
`value.strip()`, which removes leading and trailing whitespace but preserves
repeated whitespace between name parts.

The existing test fixture only asserts edge trimming
([test_fixture.py](test_fixture.py):4-6). Its required pre-change execution was
recorded in [BASELINE.txt](BASELINE.txt): `python3 -B -m unittest discover -v`
exited 0 with one passing test. That check is evidence of the old behavior only;
it does not cover the requested internal-collapse behavior.

The documented runtime is a local, pure-Python string helper with no remote
services, retained state, or deployment configuration
([docs/environment.md](docs/environment.md):1-3). `git status` also reported
that this fixture directory is not a Git worktree. Service, storage, remote
access, delivery, and source-return investigation are therefore not applicable
to this scoped change; no remote fixture or configuration was consulted.

## Discovery decision

Use the existing helper and make the smallest semantic extension: normalize a
string by splitting on whitespace and joining the parts with one ASCII space
(for example, `"  Ada   Lovelace  "` becomes `"Ada Lovelace"`). In Python, the
natural proposed expression is `" ".join(value.split())`; it trims edges and
collapses runs of spaces, tabs, and newlines without adding a dependency. This
is a proposal only—no source, test, dependency, or configuration file was
changed during discovery.

The preserved behavior is that a one-part name remains unchanged and an empty
or whitespace-only string normalizes to `""`. The existing implicit input-type
contract is preserved; this request does not add coercion or a new error policy.
The intended interpretation of “whitespace” is Python's ordinary whitespace
splitting behavior. If a product contract later needs a narrower character set,
that is a specification decision before implementation rather than a reason to
invent a separate normalizer now.

## Planned verification and handoff

Before implementation, extend the current fixture with focused cases for a
single internal space, repeated spaces, mixed tabs/newlines, empty input, and
whitespace-only input. Keep the existing edge-trim assertion. After the scoped
edit, rerun `python3 -B -m unittest discover -v`; it remains a local unit check,
not evidence of any remote or consumer deployment.

Direct inspection was sufficient under the frozen discovery guidance
([research-loop.md - Plan the investigation: direct-path rule](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/source-snapshot/skills/shiploop/references/research-loop.md:210)). The local/stateless classification follows
([service-discovery.md - Select scope: local changes stay local](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/source-snapshot/skills/shiploop/references/service-discovery.md:12)). No experiment, remote read, implementation, callback, Improve action, or delivery operation was performed.
