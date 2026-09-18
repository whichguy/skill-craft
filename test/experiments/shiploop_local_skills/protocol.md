# Trial protocol and fixed criteria

The fixed fixture uses release receipts where identity, target, and latest numeric
attempt matter. The contract is authoritative; local prompt skills should point to
it rather than reproduce its defaults. `docs/lessons.md` records the stale-pass /
later-failed-retry recurrence that motivates reuse.

| Trial | Frozen input | Fixed deterministic result |
| --- | --- | --- |
| initial | v1 candidate alpha, staging default | release `blocked` |
| reuse | v1 candidate bravo, production override | release `clear`; prior skill package preserved |
| evolve | v2 freshness maximum 3, one passing receipt age 5 | release `blocked`; v1 compatibility remains `clear` |
| fork | incident receipt includes a failed check | incident `investigate`; v1 compatibility remains `clear` |
| noop | ordinary v1 bundle plus README prose typo | release `clear`; local skill packages unchanged |
| relocate | unchanged v1 contract moved to `specs/`, old skill link stale | same v1 decision; new contract location preserved and local links resolve |

`oracle.py` contains the exact output objects and compares them outside the
agent-visible fixture. It records whole-package skill digests before and after.
Digest change is evidence to review, not proof that a skill evolved correctly;
unchanged digest can be sound when the original skill reads the current authority.
For evolve and fork, preserving the v1 contract and exercising its compatibility
bundle are mandatory. A fork is not forced when a compatible existing skill can
serve both contracts without changing retained release behavior.

This is an observational capability study, not a preregistered comparison. The
method and oracle were refined during apparatus bringup, and initial agents began
before the final oracle, calibration, and documentation were complete. Preserve
their raw outputs and report that timing with any results. The study makes no claim
about model-wide reliability, global automatic discovery, token efficiency, or
causal superiority of a packet or prompt. No LLM mock or launcher is part of it.

The initial incident fixture left the selected receipt row shape unspecified,
while the oracle expected a projection. Preserve that failed exact-output grade
as an apparatus ambiguity. The amended fresh trial explicitly defines the row
projection; the oracle expectation is unchanged. The freshness trial demonstrated
unchanged reuse rather than requiring a skill edit. The subsequent relocation
trial was added to exercise a concrete stale reference, followed by another fresh
reuse trial. These are adaptive experiments.

Task-output grades are distinct from lifecycle observations. Record actual
created/changed/preserved skill files, hashes, index links and semantic review
before claiming creation, evolution or a separate skill. The oracle does not
force creation or a specific name simply to earn a passing task-output grade.
