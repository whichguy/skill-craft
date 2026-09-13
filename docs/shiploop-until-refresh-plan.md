# ShipLoop: validated Until-Loop refresh

## Scope and evidence

Implement the accepted findings from Until-Loop 0.2.1 at `7d24bbc`, including
runtime integration safeguards in `4430f89`, against ShipLoop `656fc7e`.
The earlier repeat/verify policy remains attributed to Until-Loop 0.1.3 at
`7fb7057056552438fa39ccf11b70fa7c63f80077`; this is a selective adaptation, not
a replacement runtime or automatic synchronization of the installed skill.

The review reproduced three failures in an isolated repository: conflicting
`state.md.prompt` and `prompt.md` were both served; preexisting hard links at
the Git-ignore and verifier-log destinations allowed collateral writes; and
a separate `--prompt '--help'` argument was rejected while `--prompt='--help'`
round-tripped. These concrete failures justify the runtime changes below.

## Plan and acceptance criteria

| Slice | Change | Required evidence |
| --- | --- | --- |
| Original intent | Validate settled prompt bytes after transaction recovery and before packet/context reads or advancement. Refuse disagreement rather than choosing or rewriting a copy. | Red/green tests for both copies, missing/unsafe files, Unicode and CRLF, unchanged state on rejection, pending recovery, and legacy migration. |
| File safety | Reject unsafe script-owned ignore/log targets before content reads or truncation; retain the worktree-ignore invariant and actual Git metadata resolution. | Alias sentinels retain content and permissions; safe regular-file writes/retries and linked worktrees still work. |
| Literal transport | Use one `--name=value` argument for arbitrary text, with structured argv or correct shell quoting. Preserve original literal bytes. | Real CLI round trips for option-like text, quotes, shell metacharacters, multiline text and Unicode; no accidental shell execution. |
| Action guidance | Every ordinary action starts cold. Reassess the current unmet criterion, choose useful work within the assigned stage, distinguish missing evidence from success, and persist compact learnings in existing Markdown results. | Packet bounds/routing and existing callback/convergence tests; an independent bounded forward pilot with hidden outcome criteria. |
| Documentation and distribution | Explain adopted changes, intentional differences, cold-context ownership, and pilot limits. Refresh only the ShipLoop packaged view. | Current relative links, syntax/lint, targeted and broader ShipLoop suites, and source/package parity. |

No new state store, model pin, integration, dependency, scheduler, or mandatory
evaluation service is added. Scripts continue to select transitions. The LLM
judges the assigned candidate and returns evidence, not a next-stage decision.
Initial work remains a candidate followed by review/plan/apply/check/learning
commit cycles. Two consecutive completed trivial-only reviews, fixes included,
and fresh final checks are required; material changes reset convergence.
Operational callbacks do not start recursive improvement loops, and external
effects are not repeated merely to count review passes.

## Validation strategy

Start with tests that fail on the observed defects, then rerun them after the
fix. Exercise fresh subprocess reads/callbacks and transaction recovery, not
just helper wording. Run the existing convergence, packet, protocol, evidence,
migration and end-to-end action-walk tests before closeout. Preserve unrelated
Review Coverage edits in the shared checkout. Final residual reviews use an
isolated pinned snapshot, with explicit process exit status.

The independent intent pilot receives only its task, current action guidance
and raw fixture artifacts. Expected findings stay with the grader. Grade the
observed decision/evidence, not phrase matching. One pilot demonstrates only
that case, not general model reliability or execution on other hosts.

This approach is informed by the concrete upstream implementation and
[Python's argument parsing contract](https://docs.python.org/3/library/argparse.html#option-value-syntax).
[Anthropic's harness study](https://www.anthropic.com/engineering/harness-design-long-running-apps)
supports artifact-based handoffs and separate evaluation, while also reporting
extra cost, evaluation bias and cases where later iterations were not better.
That is evidence for a bounded pilot, not a claim that repetition proves perfection.

## Execution record

Validated during implementation:

- Reread the latest seven full main-branch Git messages before closeout:
  `656fc7e`, `31f8a03`, `ac6cb43`, `414b3e9`, `c548bc9`, `2153514`, `f47dcfa`.
  Carry forward their distinction between readiness and final success,
  source-bound proof, executable recovery, bounded packets and explicitly
  attributed component/sharded validation.
- Literal entry regression: the documented old form failed for `--help` and
  `--repo=...`; the new form passes five literal payloads. The same payloads
  round-trip through `pause --reason=...` without advancing the action or
  executing shell text.
- Prompt-integrity tests initially produced nine failures across seven
  methods. Follow-up cases exposed acceptance of a hardlinked prompt and
  unbounded reading of an oversized sidecar; both are now rejected before
  payload access. The CLI convenience wrappers also have rejection coverage.
- The initial filesystem regression produced six failures: ignore symlink/
  hardlink aliases, a symlinked ancestor, hardlinked log truncation/chmod, and
  evidence-directory creation through a symlink. Final results follow below.
- Packet regressions caught growth beyond the existing 7,000-character gate.
  Repeated wording was shortened, preserving the gate, result headings,
  microplan/test criteria, full-history readers and callback identities.
- Broader planning coverage exposed a second overrun: the cold behavior-review
  packet measured 7,217 characters at the original baseline and 7,421 after the
  refresh. Reusing the packet's existing full context command for section
  reads, removing a duplicate worktree path and tightening sample/lint prose
  reduced it to 6,827 in the same isolated-path fixture. The unchanged test
  passed both there and at the longer canonical source path; no check or
  required coverage dimension was removed.
- Independent forward pilot: a fresh agent received only the skill/run locator
  and raw local fixture artifacts. It read durable preflight context, retained
  absent owner-input and protected-file prerequisites, and submitted exactly
  one approach result. The real callback advanced revision 1 to 2 at
  `objective-review`, not terminal success. The product baseline commit stayed
  unchanged and the owner file stayed untracked/unmodified. The result retained
  all four incoming requirement clauses. Fixture: `/tmp/shiploop-until-pilot.WO76WQ`;
  accepted action `20260913T141606Z-b9ca131d-321e28415ab0`. This is one qualitative
  forward case, not an A/B improvement measurement or cross-host benchmark.
- Independent review requested consistent `--name=value` synopsis forms,
  reason-transport and convenience-wrapper coverage, and explicit filesystem
  threat limits. These were addressed and the ShipLoop package synchronized.
- Residual review 1 on isolated commit `5086626` found only remaining literal
  reason examples. Residual review 2 on `52cb075` found only a stale unconditional
  ten-commit instruction. Both were documentation-only; all trivial fixes were
  applied. The reviewer checked the final delta at `dbfcbf9` and confirmed the
  issue closed without a new contradiction. Reviews were static evidence, not
  claims that the separately running test suite had passed.
- The later packet overrun reopened review. Two fresh residual passes of the
  compaction delta, ending at `5723d38`, found no actionable issue: the single
  full bounded context command, available sections, direct blocked-recovery
  commands, lint authority and no-install constraint remained intact.

Threat boundary: detect preexisting unsafe aliases, use descriptor validation
before reads/truncation, and preserve state on refusal. A same-permission actor
concurrently replacing directories/inodes or rewriting both intent records is
not contained by these checks; protected isolation is required for that threat.
No claim of a new filesystem sandbox is made.

## Final validation

Coverage follows all 35 suites enumerated by `test/shiploop.test.sh`. Its
initial serial run at isolated `5086626` completed 31 suites / 342 methods
successfully. Once the long knowledge suite passed, the remaining planning,
Until, step-planning and action-walk suites were delegated against
snapshot `dbfcbf9`. The redundant serial process was deliberately terminated
(exit 143); it is not claimed as a completed, exit-zero harness run. Combined
isolated/component coverage passed **409 methods across all 35 suites**:
342 in the first 31 suites, 13 action-walk, 28 planning, 9 Until and 17
step-planning methods. Interrupted and failed attempts are retained but are
not counted as passes.

The action-walk suite passed all 13 methods at `dbfcbf9` in three disjoint
per-test-fixture shards (4 + 5 + 4), each exit zero; the selector union covers
the suite exactly once. Log: `/tmp/slr.7LRwao/action-walk-final.log` with all
three `SHARD_EXIT` values zero. Its original serial attempt was replaced
(exit 130) and is not counted. No source or Git changes occurred in that
validation checkout.

After the packet-bound failure, planning validation was restarted against
corrected snapshot `5723d38`: all 28 planning methods passed in two disjoint
14-selector shards, with every selector and both groups exiting zero. Logs:
`/tmp/slr.7LRwao/planning-corrected-a.log`, `planning-corrected-b.log`, and
`planning-corrected-shards-summary.log` in the same directory. The replaced
partial corrected serial attempt is explicitly marked not passed; the original
failed 28-method run remains in `planning-final.log` for the red/green record.

Until passed 9/9 and step planning passed 17/17 on `5723d38`. Step planning
used disjoint 12-record and 5-CLI selector groups; every selector, group and
logging pipeline exited zero. Logs: `until-corrected.log`,
`step-planning-corrected-record.log` and `step-planning-corrected-cli.log` under
`/tmp/slr.7LRwao/`. The final validation checkout remained clean and pinned.

Later runtime-file differences consist only of
the quoted recovery-command placeholder and packet prose compaction described
above; other changes correct documentation examples and the bound 7/10 history
policy. No transition, counter, schema or verifier logic changed after
`5086626`. Initial serial log:
`/tmp/slr.7LRwao/shiploop-suite.log` (temporary validation evidence).

Additional checks:

- All 98 methods in the packet, protocol, file-safety, prompt-integrity,
  literal-transport and Until decision suites passed at `dbfcbf9`
  (`FINAL_FOCUSED_EXIT=0`).
- After compaction, all 87 packet/protocol/discovery methods plus the measured
  cold-planning regression passed at `5723d38` (`COMPACT_FOCUSED_EXIT=0` for
  the 87-method group; the separate unchanged planning test also exited zero).
- The 27 file-safety, prompt-integrity, literal-transport and evidence methods
  also passed again on `5723d38` (`FINAL_INTEGRITY_EXIT=0`).
- Ruff `F,E9`, shell syntax, repository frontmatter validation (17 skills),
  whitespace/diff checks and scoped source/plugin parity passed. A read-only
  link check found all 162 relative local file links across 34 ShipLoop
  Markdown files resolve; this was not a browser rendering or anchor audit.
- The generic skill validator could not start because PyYAML is
  absent from both existing Python runtimes. No dependency was installed.
  The repository-native frontmatter validator above passed instead.

The independent fresh-context case described above passed its specific
held-out criteria. No A/B quality uplift, multi-host certification, remote
deployment or protection against a same-permission filesystem adversary is
claimed. Unrelated Review Coverage edits and standalone Until-Loop's existing
untracked task artifacts were left unchanged.

Readers: the implementing agent, independent reviewers, and the final user
handoff. Runtime packets do not load this development-only plan.
