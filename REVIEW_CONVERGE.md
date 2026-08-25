# Review Converge: ShipLoop 0.8.4 env+MCP per implement iteration

**Target paths:** `skills/shiploop`, `docs/LOOP-ENGINEERING.md`, `skills/devloop/references/loop-engineering.md`, `plugins/devloop/skills/devloop/references/loop-engineering.md`, `test/shiploop.test.sh`, `test/fixtures/shiploop`, `plugins/shiploop`, `plugins/devloop`
**Test command:** `bash test/shiploop.test.sh`
**Started:** 2026-08-25          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 1
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.cursor/plans/env_mcp_per_iteration_8bb8291b.plan.md`
**Plan hash:** `e72f04f0bd647625a0fc3b72ce57db846965cac952274dd382c676b77e72768a`
**Base ref:** `9a1d4e5`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-08-25
**Review:** 0 material, 3 minor (new + carried)
**Material findings:**
- none
**Deferred (minor/P2):**
- [ ] P2: `forward_dest`'s `residual` branch has a dead conditional — `if plan_waiver(state): return "done"` is immediately followed by an unconditional `return "done"`, so the waiver check changes nothing about the returned destination (the real done-gate is still enforced downstream by `residual_gaps` / `recap_gaps` via `missing_for`) [skills/shiploop/scripts/shiploop:forward_dest] — code. Carried from the archived survey-before-spec campaign (`REVIEW_CONVERGE.archived-survey-before-spec-20260825.md`); still present and still not newly material (untouched by 0.8.4; nothing behavioral regresses).
- [ ] P2: plan §4 asked README / turn-packet to note in-flight `blocked → plan` recovery; that recovery lives in `plan.md` and in `dag_gaps` gap text, but README and turn-packet only describe the happy-path paste contract — docs. Not material: a failing dest implement already prints the recovery in Missing.
- [ ] P2: the Tools:-header gap names the missing line and the recovery, but not the exact `mcp_considered` token (the sibling token gap does). Plan prose said each gap should name the missing piece and the token. Tests assert the two messages separately; hosts who trip only the header gate still see recovery. — docs
**Git-history check:** Last 10 subjects: `be554b7` ShipLoop 0.8.4 frozen tools/MCP per implement /goal; `9a1d4e5` ignore `__pycache__` in the no-DevLoop grep (this campaign's Base ref; HEAD was this SHA before the ship commit); `df22fc7` hermetic wrappers for imported Cursor skills; `5584548` review-coverage /goal trailer stays reference-owned; `5f487ca` DevLoop 0.5.4 validate-spec first; `e04b930` new-project asks are greenfield; `092d05e` ignore session run dirs and archived ledgers; `c2d503d` ShipLoop 0.8.2 session rail / residual bind; `305a5a6` spec/plan/residual share one placement vocabulary; `3ea3cbc` deploy-prep / outer-loop publish / quality `/goal` at spec time. Those teach: one controller per session, no invented dest_contract JSON, fail-closed hashes, greenfield vs brownfield, archive a foreign terminal ledger rather than reopen it, and residual after drain — not a nested `/devloop`. Prior review-converge on this leaf (`671cc06` R4 complete, `c433018` R3 clean, `802aa8e` R2 inject-step citation exemption, `3394a66` R1 clean) already established seed-only citation and the `forward_dest` P2; this campaign reviews `9a1d4e5..be554b7` (uncommitted 0.8.3 + 0.8.4 shipped together) and does not re-open that completed survey-before-spec ledger (copied to `REVIEW_CONVERGE.archived-survey-before-spec-20260825.md`, gitignored).
**Plan:** n/a (clean)
**Plan review:** n/a
**Implementation:** none
**Lint:** skipped (none configured)
**Test result:** N/A (clean round)
**Outcome:** clean
**Error signature:** none
**Learnings:** A ship that already has hermetic layers for every spec anchor can honestly be clean on residual round 1 — manufacturing a material finding from the README recovery omission or from gap-text wording would be theater. The 0.8.4 contract is: dump-all `references[].path` stays; a sibling seed-only `Tools:` line check plus a literal `mcp_considered` substring (never `re.search`) fire even when `references: []`; `inject-step` stays script-exempt and still gets the Frozen envelope; dest_contract is still absent from `validate_machine`. Reverse of `9a1d4e5..be554b7` is the intended combined 0.8.3+0.8.4 review. Surprising part: the live `REVIEW_CONVERGE.md` was a different plan's Status `complete` (survey-before-spec); Phase B hard-stopped until that ledger was archived, matching `092d05e` and the prior campaign's own F25 note.
**Anchor evidence:**
- A1 → `test/shiploop.test.sh` LAYER: Tools: seed gate OK (pass multiline; fail no header; fail no token; fail mid-line `See Tools: below`)
- A2 → `test/shiploop.test.sh` LAYER: empty prompt + reference citation OK
- A3 → `test/shiploop.test.sh` LAYER: inject-step exempt from reference citation OK; `inject-step` writes `origin: discovered` (`scripts/shiploop:3201`)
- A4 → linear implement packet asserts `mcp-considered:` / `tools: (none)` / `mcp: (none)` and HOST FLAG then mcp-considered then stored prompt; two-root asserts two `mcp-considered:` lines
- A5 → implement Look here `required  …/environment.md` (`LAYER: linear implement packet OK`)
- A6 → `validate_machine` has no `dest_contract` key; `git grep dest_contract -- skills/shiploop test/shiploop.test.sh` empty; existing machine-shape layers still accept the fixture JSON
- A7 → `skills/shiploop/references/activities/plan.md:44` `Watch with:` plus Use / Don't use / Assume examples
- A8 → `diff -q docs/LOOP-ENGINEERING.md skills/devloop/references/loop-engineering.md` and plugin twin: both equal
- A9 → `skills/shiploop/SKILL.md` `version: 0.8.4`; `bash scripts/sync-plugin-views.sh --check shiploop devloop` CHECK OK
- A10 → Tools: seed gate empty-refs no header exits 2 with `line starting with Tools:`
- A11 → `implement.md:8-10` paste Frozen session environment + stored prompt; do not paste worktree/branch/HOST FLAG
- A12 → `LAYER: inject-step envelope reprint OK` (`mcp-considered: none(x)`)
- IQ1 → host paste contract in SKILL.md, implement.md, turn-packet.md, README; inject-step command says paste Frozen with the discovered prompt
- IQ2 → `dag_gaps` sibling `origin == seed` block: `re.match(r"^[ \t]*Tools:", line)` and `mcp_considered not in prompt` (no `re.search` on the token)
- IQ3 → discovered origin skips both script gates; envelope still reprints
- IQ4 → dest_contract absent from machine validation
**Consecutive clean rounds after this entry:** 1
**Committed:** yes
**Notes:** Fresh ledger for plan `env_mcp_per_iteration_8bb8291b` bound at campaign start (SHA-256 `e72f04f0…768a`). Prior foreign terminal ledger (survey-before-spec, Status `complete` at `671cc06`) archived to `REVIEW_CONVERGE.archived-survey-before-spec-20260825.md` (gitignored; not committed). First of two consecutive cleans; suite deferred to the second clean per Phase 2. Pathspec-only commit of this ledger; no `git add -A`. Implementation already landed as `be554b7` so Target paths were clean at Phase 0. Exactly one `/review-converge` this turn.
