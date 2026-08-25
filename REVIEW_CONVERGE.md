# Review Converge: ShipLoop 0.8.4 env+MCP per implement iteration

**Target paths:** `skills/shiploop`, `docs/LOOP-ENGINEERING.md`, `skills/devloop/references/loop-engineering.md`, `plugins/devloop/skills/devloop/references/loop-engineering.md`, `test/shiploop.test.sh`, `test/fixtures/shiploop`, `plugins/shiploop`, `plugins/devloop`
**Test command:** `bash test/shiploop.test.sh`
**Started:** 2026-08-25          **Status:** complete
**Round counter:** 2
**Consecutive clean rounds:** 2
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

### Round 2 — 2026-08-25
**Review:** 0 material, 0 minor (new)
**Material findings:**
- none
**Deferred (minor/P2):**
- [ ] P2: `forward_dest`'s `residual` branch has a dead conditional — `if plan_waiver(state): return "done"` is immediately followed by an unconditional `return "done"`, so the waiver check changes nothing about the returned destination (the real done-gate is still enforced downstream by `residual_gaps` / `recap_gaps` via `missing_for`) [skills/shiploop/scripts/shiploop:forward_dest] — code. Carried from R1 / archived survey-before-spec campaign; still present, still untouched, still not newly material.
- [ ] P2: plan §4 asked README / turn-packet to note in-flight `blocked → plan` recovery; that recovery lives in `plan.md` and in `dag_gaps` gap text, but README and turn-packet only describe the happy-path paste contract — docs. Re-checked this round: `transitions.json` has `blocked → plan` (`need: reason`), so the CLI recovery is a real edge, not a lie. Still not material: Missing already prints it.
- [ ] P2: the Tools:-header gap names the missing line and the recovery, but not the exact `mcp_considered` token (the sibling token gap does). Carried from R1; still accurate; still not material.
**Git-history check:** Diff vs Base ref is still `9a1d4e5..be554b7` plus R1's ledger commit `5688d36`. No product-path commit landed between R1 and this review (`git diff --stat 5688d36 HEAD -- <Target paths>` empty). Last 10 subjects unchanged except R1 now sits on top (`5688d36`, `be554b7`, `9a1d4e5`, `df22fc7`, `5584548`, `5f487ca`, `e04b930`, `092d05e`, `c2d503d`, `305a5a6`). Prior converge history (`671cc06` / `c433018` / `802aa8e`) already settled seed-only citation; this round does not re-raise that. **Forward (re-derived from the bound plan, not from R1's restated wording):** plan §3 requires `print_packet` to reprint frozen env via `load_environment` and still print the stored prompt if the file is invalid — `print_frozen_session_env` prints the Frozen header + gap lines then returns, and the caller still prints `step["prompt"]`. Plan §4 requires a sibling `origin == seed` Tools: line match plus literal `mcp_considered in prompt`, inject-step exempt — `dag_gaps` 1338–1357 and `inject-step` `origin: discovered` still match. Plan §4 recovery `blocked then dest plan` is a legal transition (not invented). dest_contract is still absent. Intent Q1–Q4 still hold on the same files R1 named. **Reverse:** `git diff 9a1d4e5..be554b7` is the intended combined 0.8.3+0.8.4 ship; no new regression surface since R1. Section 5's "all refs + token, no Tools: line" combo is not a dedicated fixture — it is the same Tools: branch A10 already exercises with empty refs; not a new material gap.
**Plan:** n/a (clean)
**Plan review:** n/a
**Implementation:** none
**Lint:** skipped (none configured)
**Test result:** PASS (terminal clean)
**Outcome:** clean
**Error signature:** none
**Learnings:** The thesis that R1 was an honest first clean, not a rubber stamp waiting to be undone, held: an independent re-read of the bound plan against `dag_gaps` / `print_frozen_session_env` / `transitions.json` found the same contract, and `bash test/shiploop.test.sh` PASSed (Tools: seed gate, citation, inject-step exemption, inject envelope reprint, linear/two-root packets). Surprising-but-settling: the in-flight recovery sentence is not documentation theater — `blocked → plan` is a first-class edge — so leaving it out of README remains a P2, not a broken hatch. No Outcome: fixed in this campaign; residual×2 completed on two consecutive cleans.
**Anchor evidence:**
- A1 → this turn's suite `LAYER: Tools: seed gate OK`
- A2 → `LAYER: empty prompt + reference citation OK`
- A3 → `LAYER: inject-step exempt from reference citation OK`
- A4 → linear + two-root layers in the same PASS
- A5 → implement Look here `required  …/environment.md` still printed in linear packet
- A6 → `git grep dest_contract -- skills/shiploop test/shiploop.test.sh plugins/shiploop` empty; machine-shape layer still in PASS
- A7 → `plan.md` still has Watch with / Use / Don't use / Assume
- A8 → `diff -q` docs vs skills/devloop vs plugin twin: equal
- A9 → SKILL.md `0.8.4`; sync-plugin-views not re-run (no product edit this round); R1 already CHECK OK and tree unchanged
- A10 → empty-refs no Tools: still in Tools: seed gate layer
- A11 → implement.md / SKILL.md paste Frozen + stored prompt
- A12 → `LAYER: inject-step envelope reprint OK`
- IQ1–IQ4 → re-derived above; no drift
**Consecutive clean rounds after this entry:** 2
**Committed:** yes
**Notes:** Second consecutive clean; recorded Test command PASS (`bash test/shiploop.test.sh`, EXIT 0, no TARGET_PATHS porcelain delta). Status `complete`. artifact failed: Artifact publish tool not available on this host. Pathspec-only commit of this ledger; no `git add -A`. Exactly one `/review-converge` this turn.
