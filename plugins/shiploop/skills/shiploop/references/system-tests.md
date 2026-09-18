# Global system-test catalog

This is the retained managed/legacy catalog contract. Navigator v3 uses its
[test and outer stages](navigator.md) with ordinary notes/results instead.
Keep the catalog's run-wide test requirements distinct from the
[maintained product requirements](project-knowledge.md#maintained-product-requirements):
cases cite the applicable product clauses, but a derived test view is not a
second editable product spec or proof that those clauses passed.

`backchain/plan.md` is the authoritative Markdown home for the run-wide
system-test catalog. It is part of the accepted DAG, not a second workflow,
test runner, mutable checklist, or authority to deploy. The protocol may derive
a readable `system-test-requirements.md` view from that catalog, but the derived
view is never edited and is not an independent source of state.

This contract applies only to new runs carrying
`system_test_protocol_version: 1`.
An older run with an absent marker remains compatible but is **un-certified**
against this global catalog until it supplies one through its supported planning
route. An unknown marker version fails closed. Do not insert catalog rows into
a legacy plan, infer missing IDs, or claim a historical run satisfied this gate.

## Catalog shape

The accepted DAG has `system_tests` with this closed shape:

```json
{
  "version": 1,
  "phases": {
    "pre_deployment": {
      "status": "required",
      "reason": "The integrated prerelease target exercises the shared authorization boundary."
    },
    "post_deployment": {
      "status": "not-applicable",
      "reason": "This delivery has no deployment; the integrated prerelease target is the final runnable boundary."
    }
  },
  "cases": [
    {
      "id": "SYS-ORDER-CREATE",
      "phase": "pre_deployment",
      "requirement": "Exercise order creation through the integrated prerelease boundary.",
      "expected_outcome": "A valid request creates one visible order and an invalid request leaves no order.",
      "environment": "authorized prerelease fixture tenant",
      "prerequisites": ["S2"],
      "test_step": "S7",
      "test_id": "T-SYSTEM-ORDER-CREATE",
      "deployment_step": null
    }
  ]
}
```

`version` is exactly `1`. Each phase has exactly `status` and `reason`;
`status` is `required` or `not-applicable`, and the reason is always concrete.
Each case has exactly the fields shown. `id` is a stable `SYS-...` identity,
`phase` is `pre_deployment` or `post_deployment`, `prerequisites` is a unique
list of DAG step IDs, `test_step` names its owner step, and `test_id`
names the exact `T-...` test contract in that step. `deployment_step` is a DAG
step ID or `null`.

The catalog is deliberately small and typed. Its prose explains intent, but the
step contract and verification manifest still own executable command details,
exact acceptance strings, observed result, and local log paths. A catalog row
does not prove that its test ran or that a remote target is the claimed build.
`environment` is descriptive; actual check authors must inspect and assert the
actual selected target/build. A reused local or mock result cannot establish a
remote boundary.

## Placement and dependency rules

`system-test-pre` and `system-test-post` are ordinary DAG activities, not new
ShipLoop stages. They use the normal step lifecycle:

```text
step-plan -> implement tests/refinements -> verify/fix -> Improve review
-> plan using the last seven full commit messages -> apply -> lint/tests
-> two applied trivial passes with commits -> merge
```

The normal step-plan must define Ready/Done criteria, the exact `T-` contract,
fixtures, target/environment limits, expected outcomes, and documentation
effects before product edits. After implementation learning, author or refine
the real tests; run the declared manifest, retain failures, fix justified
defects, and rerun. A grouped test step is valid when its cases share an
honest fixture/boundary and its step contract names every included case.
Apply [repeatable test suites](repeatable-test-suites.md) to the tests and
fixtures owned by those cases, including the evidence needed to share expensive
fixtures and the distinction between focused, smoke and full evidence. This
guidance does not change the catalog shape or extend the protocol to a legacy
run without its marker.

Plan execution location separately from target location: a local check, a local
client against a deployed target, or a remote-resident test executing within the
remote runtime. Discover the available framework, invocation/access and deployment
prerequisites. Retain remote test definitions/registration and their repeatable
authorized install, invocation, result retrieval and cleanup route. The full suite
may require both local and remote parts; a local pass cannot satisfy an unavailable
remote check. Keep missing readiness/availability explicit at its existing
pre/post-deployment boundary; do not invent another catalog or deploy to bypass it.

Case prerequisites fan in: the `test_step` for a case depends on every listed
DAG step ID, as well as any actual product/readiness producer it consumes. Do
not serialize independent cases merely because they appear in one catalog list.

- A required pre-deployment case uses `activity: system-test-pre`. Its step must
  complete before the DAG publication step.
- A required post-deployment case uses `activity: system-test-post`. Its step
  depends on the DAG publication and declared target-readiness producers.
- Required real post-deployment testing requires `lifecycle.publish: dag`.
  `publish: outer-loop` is unsuitable: it is host-reported publication evidence,
  not an authoring or system-test gate.
- When there is no deployment, `pre_deployment` means the integrated prerelease
  target and `post_deployment` must be `not-applicable` with that concrete
  reason. Both phases may be `not-applicable` only when their reasons show why
  no relevant integrated or released boundary exists.

Unknown target identity, unavailable access, missing authorization, or an
unresolved real boundary is not `not-applicable`. Record the blocker through the
existing pause/knowledge/replan route and seek the needed authority.

## Example: one case in an ordinary DAG

`SYS-ORDER-CREATE` above depends on `S2`. Its `S7` owner step has test contract
`T-SYSTEM-ORDER-CREATE`, selects the authorized prerelease tenant, and
asserts both one created order and no invalid-request side effect. If publication
is out of scope, this is the integrated prerelease target and the catalog's
post-deployment phase is N/A for the stated reason. In a separate deployment
example, this case may set `deployment_step: "S8"` and precede `S8`
(`activity: publish`); an added post-deployment case would instead name `S9`,
whose inputs include `S8` and target readiness. This is one fan-in graph, not a
separate deployment pipeline.

## Reassessment, change, and closure

Every carry-forward, post-inner, and quality review records this strict
`system_test_review` object:

```json
{
  "decision": "no-change",
  "evidence": "SYS-ORDER-CREATE: the selected integrated boundary and case mapping remain unchanged.",
  "discovery_ids": []
}
```

The object has exactly `decision`, `evidence`, and `discovery_ids`. `decision`
is exactly `no-change` or `revise`; `evidence` names relevant case IDs plus
concrete rationale/deltas; and `discovery_ids` is always a list. A
`no-change` decision has `[]`. A carry-forward `revise` names the current
`test-strategy`/`pending-replan` discoveries or already-open obligations that
require change. Its IDs persist in script-owned `state.system_test_pending`, and
cold `context --section system-test-requirements` exposes the outstanding IDs.
A post-inner `revise`—or an outer replan when its `system_test_review` says
`revise`—requires a pending DAG/plan revision. Quality remains blocked until
each pending ID is mapped to its typed system-test owner; unrelated work cannot
discharge it.

`context --section system-test-requirements` renders the current authoritative
plan even if a derived `system-test-requirements.md` view is altered, missing, or
out of date. A new fact is recorded first through the existing bounded knowledge
ledger; a future catalog/test need is a `pending-replan` obligation. An inner
action may also record a later external dependency through the outer-work side
journal, but that journal is never system-test evidence and cannot make a failed
test pass.

Catalog changes use pending-only DAG/plan replan. Completed or running case
definitions—its test step, exact `T-` test, and deployment linkage—remain
immutable. Add a corrective case and/or corrective steps for a changed
requirement, target, or executable assertion; do not rewrite a completed row to
make previous evidence appear current. This resets the affected convergence and
requires fresh verification.

The revised catalog must contain a changed or new `SYS-...` case with a changed
or new pending typed system-test owner, and every pending mapping must reach
that owner through the DAG. A prose case-ID mention, evidence string, or a
completed unrelated step is not a mapping and cannot close the obligation.

Quality consumes the accepted catalog, all finished case-step receipts and their
contract evidence, the latest global reassessment, and current
`lifecycle.acceptance` checks. It validates each immutable historical case
against the target epoch saved with its proof; it does not compare an old
certificate to current knowledge merely because corrective work now exists. A
changed current requirement instead needs a newly completed corrective case.
Quality rejects missing, blocked, unrun, altered, or mismatched required proof.
The final report identifies the catalog in its source inventory and reports
bounded evidence/limitations; it
does not infer a remote build identity merely from a catalog field.

## Safety boundary

Use authorized, isolated fixtures and record the actual target identity in the
test's own command output/evidence. Inspect the real target rather than trusting
a claimed version string. Never automatically retry a deployment after an
uncertain result; inspect the external state and obtain authorization for any
recovery. Production tests, fuzzing, load, notification, or destructive checks
need explicit task-specific authorization, safe data, and cleanup. A local,
mock, or host-reported smoke result is evidence only for its actual boundary.

## Runtime and semantic boundary

The runtime can prove the accepted graph, required case IDs, bound receipts and
digests, and that declared checks executed with their recorded outcomes. It
cannot prove that a remote identity claim is true, that a test assertion has the
intended semantic meaning, or that an external environment remains fresh after a
check. Evidence strings and case-ID mentions remain host judgment: schema
validation cannot prove comprehension, assertion adequacy, or that every
relevant case was considered. The host must inspect the actual target/build and
evaluate assertion adequacy; do not replace that work with a generic
remote-attestation string or string-equality convention.
