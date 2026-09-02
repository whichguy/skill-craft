# Review Converge: ShipLoop 0.8.19 residual dest reread / unfreeze

**Target paths:** `skills/shiploop/references/activities/residual.md`, `skills/shiploop/references/activities/residual-waived.md`, `skills/shiploop/references/activities/validate-spec.md`, `skills/shiploop/scripts/shiploop`, `skills/shiploop/README.md`, `skills/shiploop/references/turn-packet.md`, `test/shiploop.test.sh`, `plugins/shiploop`
**Test command:** `bash test/shiploop.test.sh`
**Started:** 2026-09-02          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 0
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.grok/sessions/%2FUsers%2Fdadleet%2Fsrc%2Ftic-tac-toe-oneshot/01a06260-d265-7681-b3da-e7e0c522a839/plan.md`
**Plan hash:** `fa0d151e0cfda421b0843c1cf8baec056817b56231695d20d9b37100eb728e36`
**Base ref:** `d495ab1409a6bd1fc3cd26b4e23b5582b4f4271a`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-09-02
**Review:** 2 material, 3 minor
**Material findings:**
- Residual Next said "Frozen `mcp:`/`tools`" / "Frozen watch MCP". Residual packets do not print the implement Frozen reprint. Hosts look for a heading that is not there; Q3 watch MCP belongs in frozen `environment.md` `mcp:`/`tools`. [`skills/shiploop/references/activities/residual.md`] — logic-flow
- Residual Look here listed spec but not `environment.md`. Dest-reread reads routing + mcp from that file. Implement already requires it as frozen survey. [`skills/shiploop/scripts/shiploop` residual Look here] — docs
**Deferred (minor/P2):**
- [ ] P2: README §5 still says "do only what the frozen spec named" without dest-reread. Live Next is residual.md. Overview grain. — docs
- [ ] P2: `PHASE_FINISH["residual"]` Progress line still "quality /goal and outer-loop publish if named" without dest-reread. Next is SoT; Progress is glanceable. — docs
- [ ] P2: Q3 pin `**user** entrypoint` also matches the earlier `done_sentence` line in validate-spec.md, so it does not uniquely prove the Q3 one-liner. `watch MCP for that check` does. — tests
**Git-history check:** Prior live ledger was Status `complete` for plan `env_mcp_per_iteration_8bb8291b` (0.8.4). Archived to `REVIEW_CONVERGE.archived-env-mcp-per-iteration-20260902.md` (gitignored). Last 10 subjects: `b892afa` ShipLoop 0.8.19 residual compose; `d495ab1` Implement git closer argv (this campaign Base ref); `2ba61a1` Progress Finish legal complete; `e48af96` When-done legal argv; `cae2add` When-done names --inner-loop; `83ce08a` design seed consumer pin; `0209063` plan reads all placement answers; `14ab811` 0.8.18 early design seed; `a1926f4` dest-discovery keys; `54e4d13` drop envelope clones. Those teach: packet closer copies must be paste-legal; inventory is not use; Look here is the pointer channel; Frozen reprint is implement-only. Do not re-open the archived 0.8.4 ledger.
**Plan:**
- P1: residual.md + residual-waived.md name frozen `{{ENV_MD}}` `mcp:`/`tools` for stay-frozen, dest-block, and quality play-through — never the implement "Frozen" heading
- P1: residual Look here requires `environment.md` as frozen survey (dest reread); pin live dest-residual and waived packets; README matrix + turn-packet
**Plan review:** native — scope stays residual dest-reread; do not bump version again; do not change dest-done quality gate; leave README §5 / PHASE_FINISH as P2
**Implementation:** residual.md, residual-waived.md, scripts/shiploop Look here, README matrix, turn-packet.md, test/shiploop.test.sh pins, plugin twin via native
**Lint:** skipped (none configured)
**Test result:** PASS
**Outcome:** fixed
**Error signature:** none
**Learnings:** 0.8.19 put dest-reread in residual Next but still said "Frozen watch MCP." Residual has no Frozen reprint — that heading is implement. The oneshot's chrome-devtools-in-brief failure is exactly "look for Frozen, miss environment.md mcp." Naming `{{ENV_MD}}` and pointing Look here at that file is the same inventory-is-not-use lesson as dest-discovery, applied to the pointer channel the host still has after context loss. Compose vs unfreeze itself held (A1–A6); this round is the residual packet agreeing with itself about where frozen routing/mcp live.
**Anchor evidence:**
- A1 → residual.md dest-reread compose `routing.user_entrypoint`; pin `routing.user_entrypoint`
- A2 → `--resume-to validate-spec` + `dest-hit was never frozen` + `Q2 mismatches the walk` + `watch MCP not in frozen`
- A3 → `Do not write those URLs into {{ENV_MD}}`
- A4 → validate-spec `re-reads live dest URLs` + `watch MCP for that check`
- A5 → vendor-free grep on residual/validate-spec activities empty
- A6 → done.md still host-owned quality; no dest-done quality script gate added
- M1 → residual.md / residual-waived.md have no "Frozen" heading token; watch MCP names `{{ENV_MD}}`
- M2 → `LAYER: dest residual bound_plan bind OK` packet `required  …/environment.md`; waived residual Look here same pin
**Consecutive clean rounds after this entry:** 0
**Committed:** yes
**Notes:** Fresh ledger. Prior foreign terminal ledger archived to `REVIEW_CONVERGE.archived-env-mcp-per-iteration-20260902.md` (gitignored; not committed). Pathspec-only. Exactly one review-converge this turn.
