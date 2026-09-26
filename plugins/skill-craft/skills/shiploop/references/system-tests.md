# Global system-test catalog

The run-wide system-test catalog lists the whole-product cases that item tests
cannot cover: real integration, consumer, runtime, security, accessibility,
migration, compatibility and operational boundaries. It is planned at
`test-strategy`, authored at `system-test-author`, executed at `system-test`,
reconciled at `product-acceptance`, and, for cases that need the authorized
release first, observed at `release-verify`. Keep its run-wide test requirements
distinct from the
[maintained product requirements](project-knowledge.md#maintained-product-requirements):
cases cite the applicable product clauses, but the catalog is not a second
editable product spec or proof that those clauses passed.

The catalog lives in an ordinary durable test note named in the producing
result's `evidence_refs`, not in a separate state file, workflow, test runner or
authority to deploy. `system-test-author` retains it as the integrated test plan
through the
[OUTER test-planning handshake](repeatable-test-suites.md#outer-test-planning-handshake).

## Catalog shape

Record one row per case in a compact Markdown table:

| Field | Record |
|---|---|
| Case ID | A stable `SYS-...` identity that never changes meaning. |
| Phase | `pre-release` (the integrated candidate before release) or `post-release` (the released target, observed at `release-verify`). |
| Requirement | The product clause or `R-`/`T-` ID it exercises. |
| Expected outcome | An independent observable result, including absent side effects. |
| Environment and target | The authorized target, fixture and role; real versus simulated boundaries. |
| Prerequisites | The work items or readiness evidence the case consumes. |
| Executable reference | Test path/selector and command, or a reproducible manual procedure when automation is genuinely unavailable. |
| Owner | The stage that obtains the observation (`system-test` or `release-verify`). |

State for each phase whether it is required, or not applicable with a concrete
reason. When there is no deployment, pre-release means the integrated candidate
and post-release is not applicable for that stated reason. Both phases may be
not applicable only when their reasons show why no relevant integrated or
released boundary exists.

The catalog is deliberately small. The test code and its recorded run own
command details, observed results and log locations. A catalog row does not
prove that its test ran or that a remote target is the claimed build. The
environment field is descriptive; the check itself must inspect and assert the
actual selected target/build. A reused local or mock result cannot establish a
remote boundary.

## Placement and dependency rules

System cases are planned with the work queue, not added as extra graph stages.
A case whose fixture, harness or target setup needs real work gets an earlier
work item that produces it; that item follows the normal INNER stages.
`system-test-author` then authors or refines the whole-product cases and
fixtures from the assembled candidate, and `system-test` executes the
pre-release cases against the actual intended candidate.

Apply [repeatable test suites](repeatable-test-suites.md) to the tests and
fixtures owned by those cases, including the evidence needed to share expensive
fixtures and the distinction between focused, smoke and full evidence.

Plan execution location separately from target location: a local check, a local
client against a deployed target, or a remote-resident test executing within the
remote runtime. Discover the available framework, invocation/access and
deployment prerequisites. Retain remote test definitions/registration and their
repeatable authorized install, invocation, result retrieval and cleanup route.
The full suite may require both local and remote parts; a local pass cannot
satisfy an unavailable remote check. Keep missing readiness explicit at its
pre- or post-release boundary; do not invent another catalog or deploy to bypass
it.

Case prerequisites fan in: a case depends on every listed prerequisite as well
as any actual product/readiness producer it consumes. Do not serialize
independent cases merely because they appear in one catalog.

- A required pre-release case must pass at `system-test` before
  `product-acceptance` can declare pre-release readiness.
- A required post-release case stays pending with its owner through
  `product-acceptance` and is observed at `release-verify` after the authorized
  release.

Unknown target identity, unavailable access, missing authorization, or an
unresolved real boundary is not "not applicable". Record the blocker in the
run note, report `blocked` when the current stage cannot proceed, and seek the
needed authority.

## Example

`SYS-ORDER-CREATE` exercises order creation through the integrated pre-release
boundary. It depends on the work item that adds the order endpoint and on the
authorized prerelease fixture tenant. Its expected outcome is one created order
for a valid request and no order for an invalid one. `system-test` runs it
against the assembled candidate. If the delivery includes a release, a separate
post-release case such as `SYS-ORDER-VISIBLE` names `release-verify` as its
owner and the released target as its environment.

## Reassessment, change, and closure

Every `carry-forward` reassesses whether the catalog still matches the
delivery: no change, with the relevant case IDs and rationale, or a revision. A
revision that needs new fixture or setup work revises the future queue in that
same `carry-forward` result so the producer precedes its consumer. The last
carry-forward's Improve review covers the executed items together, including
their system-test implications. At outer stages, a needed catalog change is
corrective work through `replan`.

Completed or running case definitions stay immutable. Add a corrective case
for a changed requirement, target or executable assertion; do not rewrite a
completed row to make previous evidence appear current. A changed candidate
needs fresh execution of the cases it affects.

`product-acceptance` consumes the catalog, the executed pre-release results and
the pending post-release cases. It rejects missing, blocked, unrun or
mismatched required pre-release evidence; not-yet-due post-release cases remain
pending with their owner. The final report names the catalog and reports
bounded evidence and limitations; it does not infer a remote build identity
merely from a catalog field.

## Safety boundary

Use authorized, isolated fixtures and record the actual target identity in the
test's own command output/evidence. Inspect the real target rather than trusting
a claimed version string. Never automatically retry a deployment after an
uncertain result; inspect the external state and obtain authorization for any
recovery. Production tests, fuzzing, load, notification, or destructive checks
need explicit task-specific authorization, safe data, and cleanup. A local,
mock, or host-reported smoke result is evidence only for its actual boundary.

## Runtime and semantic boundary

The navigator records host-reported results and enforces stage order. It cannot
prove that a remote identity claim is true, that a test assertion has the
intended semantic meaning, that every relevant case was considered, or that an
external environment remains fresh after a check. The host must inspect the
actual target/build and evaluate assertion adequacy; do not replace that work
with a generic remote-attestation string or string-equality convention.
