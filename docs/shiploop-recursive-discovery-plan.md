# ShipLoop recursive discovery and iteration handoff

Status: implemented and validated. Scope: generic ShipLoop guidance, question
continuation and one required per-Improve documentation/reuse action. No live
target, integration installation, credential change or deployment is authorized.

## Audit and decisions

### Q1 — Is a gateway inventory enough? (information gain 0.9)

No. `references/platform-discovery.md` already distinguishes interface identity,
authority, bootstrap and publication; `references/research-loop.md` has linked
roles, interfaces, interactions and open questions. The missing emphasis is
following relevant producers/consumers and storage/trust boundaries behind each
gateway, including alternative access routes and a justified stopping frontier.
Extend those existing records and rubrics, not a second discovery engine.

### Q2 — Why can an answered question appear to stop the run? (0.9)

The host conversation is not state. `shiploop_packets.render` suppresses the
callback while paused; protocol `resume` removes that overlay without completing
the action. The supported transition is answer → recover/resume current action →
finish its result/checks → exact `done` → follow the returned next packet. Teach
that explicitly; do not auto-approve research or bypass required checks.

### Q3 — Where must documentation and skill capture run? (0.9)

At the audit baseline, `improve-apply` selects `verify` directly. `carry-forward` follows
checks, and `post-inner` follows final verification, so neither is a safe place
to introduce unverified product edits. Add `iteration-document` between apply
and verify. Every new-run Improve pass must record documentation and local-skill
decisions, with concrete reasons even when no changes are justified. The initial
implementation always enters Improve; its documentation receives this gate too.

### Q4 — Must a baseline defect always be fixed before the requested bug? (0.8)

No: a deliberately failing regression for the requested bug is not an unrelated
readiness failure. Plan characterization and prerequisite checks first. A broken
foundation that blocks trustworthy work needs an explicit checked repair producer;
unrelated failures must not silently expand scope. Prefer the smallest reversible
migration units, with compatibility, fixture, interruption and recovery tests.

### Q5 — Does the checkpoint need another Until scheduler? (0.8)

No. It belongs to the existing product Improve owner and its embedded Until
convergence policy. The initial implementation enters Improve; each application
now reaches documentation, checks, carry-forward and its learning commit before
the pass can count. Documentation byte edits are conservatively material, so
the owning loop reviews the resulting artifacts again and requires two later
trivial-only passes. A second documentation scheduler would duplicate state and
handoffs without strengthening this guarantee.

## Implementation plan

1. Extend survey/research guidance: read repository README and existing local
   instructions/design/environment/skills; record current evidence and bounded
   recursive actor/data/authority contracts, experiments and stop reasons.
2. Carry that evidence into overall sequencing and every step plan/review/apply.
   Define baseline test decisions and incremental migration dependency placement.
3. Clarify question round-trip in skill, active/paused packets and protocol docs;
   prove resume and rejected/accepted completion through public CLI tests.
4. Require a structured skill selection/no-use assessment in versioned step-plan
   draft/revise results, retained with the bound candidate for fresh readers.
   Add a versioned `iteration-document` action, strict result and local path
   validation, receipt/source checks and material-change reset. Reuse existing
   Markdown results/iteration readers; no new journal or global skill installation.
5. Update graph, README, reference routing and artifact consumers. Keep old runs
   without the new marker on their existing graph rather than forging old proof.
6. Test negative transitions, replay, unsafe/missing skill references, stale
   source, commit learning, compatibility and normal traversal; independent review.

## Evidence-first decision

Adopt scoped discovery and experiments; defer installing any new MCP until a
concrete target gap and permission are established. The
[MCP registry overview](https://modelcontextprotocol.io/registry/about) provides
discovery metadata, not task-specific access proof. Its
[security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
documents risks at proxy/downstream authorization boundaries. Gateway availability
must not be treated as permission across those boundaries.

Prefer small compatible migration steps where they reduce coupled failures.
[Parallel Change](https://martinfowler.com/bliki/ParallelChange.html) describes
expansion, migration and contraction; [Evolutionary Database Design](https://martinfowler.com/articles/evodb.html)
grounds versioned incremental database evolution. These are options, not a
mandate to introduce migration machinery for a docs-only or stateless change.
A bulk move may be simpler under actual constraints, but needs an explicit
blast-radius/recovery rationale. A hypothetical rollback is not recovery proof.

## Done criteria

- New-run traversal cannot omit documentation/reuse assessment before checks and
  commit. Useful local skill creation is conditional, not checklist work.
- Generated skills/docs have named readers, safe repo-local references and
  validation; future plans are directed to discover/reuse them.
- Missing owner answers, authorization and required tests remain blockers;
  answered questions do not end the run when the current action can proceed.
- Research depth is justified by causal risk, not arbitrary depth or exhaustive
  enumeration of unrelated systems. No new state taxonomy or nested scheduler.
- Existing Markdown authority, two-trivial-pass Until policy, fresh checks,
  verbose learning commits and unrelated worktree edits are preserved.

## Validation and closeout

Implemented all six plan items. New runs select the documentation gate with
`iteration_documentation_protocol_version: 1`; old unmarked runs retain their
original graph and cannot claim retroactive documentation evidence. The latest
step-plan skill assessment survives candidate revisions and cold pass resets.
The primary commit packet supplies documentation learnings verbatim, and the
commit gate rejects substitution. Product/source changes after the checkpoint
require repair, renewed review/documentation and fresh checks.

Validation used immutable snapshot `247cf47b83f05353845a15fbaf303b39c4a8103a`,
based on `ff114d2d67ce46331e44237d575c9020646de2f5`. All **501 distinct test
methods across 49 suites** passed across the full sweep and corrected-fixture
reruns. The expensive workflow suites were split into independent unittest
selections (107 jobs total); this is not a claim that the serial shell entrypoint
passed unchanged in one attempt.

- The frozen sweep passed 498 methods, including all 13 action-walk-suite methods
  (with the complete delivery traversal),
  39 packet tests, the question-resume CLI test, both documentation-boundary tests,
  the seven documentation-validator tests, and the 35 protocol tests.
- Three pre-existing fixture assumptions failed under the new contract. Two
  step-plan scenarios omitted the now-required `skill_assessment`; their complete
  corrected scenarios passed together. A carry-forward fault-injection test
  expected the later drift guard to run first; the corrected scenario passed
  after explicitly checking the documentation guard, then independently reaching
  the carry-forward guard. No production code was relaxed to satisfy these tests.
- A final seven-method unit rerun also passed after adding control-root,
  symlinked-directory and invalid-UTF-8 cases within existing methods. These
  reruns are not added again to the 501 distinct-method total.
- All 132 canonical-skill and mirrored-plugin files were byte-compared with the
  frozen snapshot: identical. Subsequent changes were limited to those three
  test files and this audit closeout. Scoped Ruff (`F,E9`), shell syntax,
  `git diff --check`, 227 local Markdown destinations across ten changed skill
  documents, native frontmatter validation for 17 skills, and ShipLoop plugin
  parity checks passed. README line-specific protocol links were checked too.
- Independent review found and resolved stale commit instructions, missing cold
  packet context/provenance, stale skill-selection projection and narrow path
  coverage gaps. The final review and test-only followup found no material issue.

The earlier snapshot `d180c5e` passed the serial 13-method action-walk wrapper;
its broader aggregate had obsolete fixture failures and was stopped after the
final-source sweep superseded it. It is **not** counted as a passing aggregate.
Local evidence is retained under the temporary validation directories
`shiploop-recursive-final-aunuHC` (per-job logs, `final-results.json`, and corrected
knowledge/step-plan logs) and `shiploop-recursive-validation-HojN5n` (earlier logs).
To reproduce all current cases serially, run `bash test/shiploop.test.sh`.

Limits: the optional skill-creator `quick_validate.py` could not run because this
Python environment lacks PyYAML; no dependency was installed, and the repository's
native frontmatter validator passed instead. The documentation boundary tests
seed a current Improve state and stub earlier plan/platform proof; the separate
full CLI walk covers actual traversal. Structural receipts do not prove semantic
research exhaustiveness, a useful reusable skill, full Agent Skills schema
compliance, or real remote behavior. No live server was installed, credential
changed, app deployed, or external experiment run. The existing Grok and Codex
ShipLoop symlinks resolve to the canonical source; the plugin view was synchronized.

Review of the last seven full Git messages (`ff114d2` through `115240e`) reinforced
three constraints: schema examples must match the selected version; accepted
actions and whole-loop convergence are different; evidence must be bound to
unchanged sources and reported with its actual validation limits. The new stage
therefore uses a version marker and existing result/iteration records rather
than another scheduler, and documentation edits cannot reuse stale checks.
