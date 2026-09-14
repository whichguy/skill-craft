# Navigator experiments: criteria fixed before execution

Baseline: skill-craft `1e81cdafb4d8bb316f2d9e258419921e889e0949`.
These are opt-in experiments outside the production navigator. Simulation and
interpretation do not establish actual delivery. No new service or dependency.

## Cold interpretation

Two fresh-context agents receive three disjoint rendered packets each. They may
read the references explicitly named by their packets but may not execute the
work or mutate files. Each response is graded semantically against the five
criteria below; equivalent valid approaches count. Conflicts/unknowns should
be disclosed. This six-case pilot is not a reliability estimate or cross-model
benchmark; each panel retains context between its three cases.

| Case | Five criteria |
| --- | --- |
| plan | Correct stage/action; plan-only scope; one clean review is insufficient; whole internal campaign with current checks and notes; one completion after two distinct clean reviews, no standalone child loop. |
| product | Correct stage/action; material change invalidates earlier clean streak/checks; refresh affected checks; review/record complete cycles internally; no done until two new clean reviews and no unresolved material issue. |
| verify | Correct stage/action; old green report is stale; execute appropriate current tests/linters; fix code or explicitly justify invalid-test correction and recheck; no publication or inferred success. |
| release | Correct stage/action; no external action; no unnecessary permission request; honest not-applicable disposition allowed; a proposed done summary must not assert actual publication or consumer verification. |
| queue | Correct stage/action; W1 stays completed; W2 stays current until this completion; future-only queue places W4 before W3; no arbitrary successor field or replay of completed/current work. |
| blocked | Correct stage/action; do not complete; no waiver of required staging checks; no resume before the stated condition changes; distinguish the later resume control from an accepted work result. |

## Mechanical boundaries

Fixed-seed generated sequences use independent expected routing and check
immutability, action identity, legal controls, terminal behavior, work queues,
and replay. CLI process-boundary and concurrent callback trials must retain
exactly one accepted transition. Lock contention may require a documented retry;
it is not itself a duplicate transition or data-loss defect. The original
canonical callback must remain usable after cold recovery. Report actual sample
counts and any failed oracle assumptions before calling a failure a product bug.

## Whole-action Improve fixture

The worker receives only the actual product-improve packet and its allowed
fixture scope. Initial tests cover empty input and ordinary overlap. The fixture
has five deliberately flawed behavior families: touching endpoints, contained
ranges, caller mutation, reversed-range handling, and invalid endpoint handling.
PLAN.md and test cases also require improvement. SPEC.md is fixed.

The independently prepared `oracle.py` uses ten explicit cases and 200 fixed-seed
half-integer-grid union cases; it must fail on the seeded candidate and pass on
a valid candidate. The worker is not shown this oracle or its outputs before
completion. No hidden requirement may exceed SPEC.md.

Success requires correct behavior, an improved plan and meaningful tests,
unchanged SPEC.md, checks bound to the final candidate, history inspection,
durable records of material reset plus two distinct clean review cycles, and
exactly one successful product-improve completion. The next stage must remain
unexecuted. Local fixture commits are allowed; publication is forbidden.
An independent reviewer assesses the evidence. Agent claims alone do not prove
successful execution. One successful campaign is a pilot, not proof of general
convergence reliability or a comparison against single-pass editing.

Before either execution outcome was observed, add a matched single-pass
control from the same initial four files and history message. It gets the same
scope and specification, but performs one review/plan/apply/check pass without
an Improve campaign or independent reviewer. Debugging failed checks within
that pass is allowed. Grade both final candidates with the same unseen oracle.
This compares two workflows on one fixture, not isolated causal effects of a
single prompt sentence; report a tie or counter-evidence honestly.

## Decision rule

Adopt only narrow changes supported by a reproduced local failure or a concrete
coverage gap. Preserve prompt/LLM execution freedom. A passing pilot supports
retaining the current boundary; it does not justify another runtime gate.
Defer broad rewrites, new integrations, and cross-host claims without evidence.

## Recorded protocol amendments

- Packet-export correction: initial exploratory readers received internal
  `render(None)` exports with a relative executable locator. Preserve those
  exploratory observations separately; primary readers receive actual public
  CLI `next` output. This corrects the experiment adapter, not production.
- Boundary clarification: both initial execution workflows interpreted touching
  integer ranges as integer adjacency. The initial oracle assumed continuous
  intervals with shared endpoints. An independent reader found both readings
  reasonable. Do not count that disagreement as an agent defect. Before the
  repeated trials, `--explicit-boundary` adds a positive shared-endpoint example
  and a negative integer-gap example to both identical fixture specifications.
  Keep the original oracle and retain the initial results as evidence of task
  ambiguity. Use fresh agents for the clarified comparison.
- Post-run independent review identified missing tuple and float coverage in
  the oracle. Preserve the original 210-case scores; `--extended` adds six
  separately reported tuple/float/boolean endpoint checks to all four unchanged
  final candidates. This is a post-hoc coverage supplement, not preregistered
  evidence or another agent trial.
