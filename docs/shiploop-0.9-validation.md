# ShipLoop 0.9 validation

**Historical validation record — delivered in `68324cf`.** Counts, source
locations and operator observations below belong to that revision, not a new
verification run. See the [proposal disposition index](shiploop-proposal-closeout.md)
and current command contract (removed in ShipLoop 0.23.0).

Date: 2026-09-11. Starting revision: `f68f033c939bc36c104a27ca7d699d5d7103c6f4`.

## Delivered contract

The canonical skill is `skills/shiploop`; the local Grok and Codex skill
links both resolve there. The packaged ShipLoop copy is generated from that
source. This change does not install an integration, select a model, push a
branch, or publish a product.

- Markdown is the authoritative store, including structured fenced payloads.
  There is no active JSON sidecar fallback. Locked, recoverable transactions
  protect multi-file changes, and explicit migration backs up legacy records.
- One durable action ID selects the next prompt. Context is paginated;
  completion replays are idempotent and conflicting or stale results fail.
- Preflight, approach, survey, research, spec, dependency review, and optional
  outer preparation precede execution. Native sequence planning avoids a
  mandatory large external template load.
- Every step has acceptance-mapped tests. Implementation, each Improve pass,
  final verification, and outer quality require script-run lint and tests.
  Failure, missing evidence, stale fingerprints, and changed check manifests
  cannot silently satisfy those gates.
- Every Improve pass records current Git history, review, a fix plan, applied
  changes, verification, and a distinct primary learning commit. Commits must
  contain the recorded learnings and exact iteration trailer. Honest no-edit
  iterations can use an allow-empty audit commit.
- Two consecutive trivial-only passes are required; material findings or
  changes reset the count. Final checks run after the last trivial fixes.
  There is no maximum-cycle success escape.
- After each converged step, an explicit broader-plan decision precedes merge.
  Validated revisions may change pending work, not completed/running steps.
  Outer defects re-enter execution as corrective steps.
- Generic harness improvement proposals accumulate in a durable journal and
  appear in the final handoff. They do not automatically modify the skill.

## Automated verification

All commands below passed against the implementation worktree:

```sh
bash test/run-all.sh
ruff check --select F,E9 skills/shiploop/scripts/shiploop skills/shiploop/scripts/*.py test/shiploop-*.py
shellcheck test/shiploop.test.sh test/shiploop-walk-journal.test.sh
bash scripts/sync-plugin-views.sh --check shiploop devloop
git diff --cached --check
```

The ShipLoop suites contain 79 passing tests: 7 storage, 8 evidence, 39
retained validator, 18 protocol, and 7 multi-action walk tests. Coverage
includes transaction interruption/recovery, unsafe paths, initialization
races, failed/stale verification, commit/history gates, two-pass convergence,
plan revisions, final checks, journal persistence, merge/base drift,
planning correction, migrations, and executable documentation examples.

Full repository output was retained locally at
`/tmp/shiploop-validation.1pyyn5/full-suite-final.log`. The repository-wide run
includes the user's existing uncommitted Review Coverage changes; those files
are excluded from this implementation commit. The shared loop-engineering
document was updated in its two existing DevLoop mirrors without changing
DevLoop behavior.

## Cold operator evaluation

A fresh operator was restricted to the skill, its references, and printed
actions, without reading implementation code or tests. It built a tiny Python
whitespace normalizer in an isolated Git repository using Ruff and four
behavioral unit tests. No real project, installation, or remote publication
was involved.

The evaluation caught issues that hermetic unit tests alone had not exposed:
unavailable context sections advertised by prompts, incomplete survey schema
examples, an oversized external planning handoff, no safe pre-execution
planning correction path, an unstated verbatim-learning commit rule, and a
ledger parser that rejected the guide's documented plain committed marker.
The quality packet also failed to name its whole-product acceptance source;
it now explicitly points to `lifecycle.acceptance` and its bounded context.
Those issues were fixed and protected by regression checks.

Final cold-run outcome: **done / done, revision 27**, verified by the public
`status` command. The scratch repository is clean. The run completed two
inner trivial-only iterations, fresh final verification, a broader-plan
no-change decision, local merge, two separate post-merge outer coverage
rounds, whole-product verification, and handoff. Every verification ran Ruff
and the four behavioral tests. One grouped generic improvement proposal was
retained and printed by the terminal packet; this run did not self-apply it.

The scratch run remains available locally at
`/private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-cold-smoke.ZxQ22pekVR/.shiploop`.
Its durable `handoff.md`, `steps/S1.md`, `history.md`, check records, and
`shiploop-improvements.md` provide the detailed trace. Git evidence:

- Inner I1: `784edd92adb35183ac16d02ddadb37c3a3faa0e8`.
- Inner I2: `f90aa3dd5100edb600a4a3a28a5de1eb420acd3b`.
- Local merge: `962b88aae072902714c961305196e3848b9a455d`.
- Outer round 1: `f8117da002a455b8bf113d57d941022800a80763`.
- Outer round 2 and final HEAD:
  `33a9a88c70b511f51b05bbdc51a7f8204126ff92`.

This was an iterative usability smoke, not an unattended first-attempt success:
the operator paused at genuine prompt/validator mismatches and resumed after
the harness fixes. Independent read-only review found no remaining
high-severity defect in the reviewed protocol and planning-correction paths.

## Boundaries and migration

This is a breaking protocol update. Existing JSON-only runs require explicit
`migrate`; unbound completion without the current action/result and the former
step/update shortcuts were removed. The action-bound `complete` command remains
supported, with `done` as its compatible alias; its name was not removed.
Migration preserves existing work and backs up recognized legacy records;
it does not certify old prose as fresh verification evidence.

The protocol verifies observable evidence and transition constraints, not the
semantic adequacy of a test or the truth of an external delivery claim. Hosts
remain responsible for meaningful tests, honest severity classification,
reading relevant history, review quality, and authorized publication.
Prompts are bounded by characters, not a guaranteed token count. The cold
evaluation does not certify a particular tiny context limit or the behavior
of a live Grok/Hermes/Claude model. Structured Markdown may contain sensitive
evidence; logs are not a secret-redaction system.

The full contract and recovery commands are in
`skills/shiploop/SKILL.md` and
`skills/shiploop/references/action-protocol.md`.
