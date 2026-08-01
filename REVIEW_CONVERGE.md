# Review Converge: clean-laptop devloop pin+sha bootstrap residual×2

**Target paths:** `skills/devloop-run`, `plugins/devloop-run`, `scripts/package-devloop-engine.sh`, `test/devloop-run.test.sh`, `test/fixtures`, `docs/ARCHITECTURE.md`, `.gitignore`
**Test command:** `bash test/devloop-run.test.sh && bash test/run-all.sh`
**Started:** 2026-08-01          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 0
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.grok/sessions/%2FUsers%2Fdadleet%2Fsrc%2Fc-thru/019fbde0-486f-7183-9153-ca1ea9f4c9a1/plan.md`
**Plan hash:** `b1e0fbf4bba0ebb33c4fa8670152f0095aeb4b857676515d2203e951c555742f`
**Base ref:** `b64bf55627ce793a78047e3b821e7796737c8619`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-08-01
**Review:** 2 material, 2 minor
**Material findings:**
- P0-5 concurrent `--setup` hermetic case missing (plan anchor; only serial D8) [test/devloop-run.test.sh] — tests
- Bootstrap lock waiters re-download without post-lock re-check; second process can wipe a just-installed host-local engine [skills/devloop-run/scripts/devloop-run bootstrap_engine] — logic-flow / race
**Deferred (minor/P2):**
- [ ] P2: P0-9 market tag-pin is Phase 3 follow-on — not residual of implement ship — docs/process
- [ ] P2: Plan wording said flock; implementation uses portable mkdir lock (equivalent if double-check present) — docs
**Git-history check:** Implement `bd6470a` landed pin/sha/safe-extract/mkdir-lock/D1–D12; prior multi-host `6cd0c94`; residual must close concurrent gap called out in plan 1.8 / P0-5
**Plan:**
- P0: After bootstrap lock acquire, if not `--force-bootstrap` and dest is already a valid engine root, return 0 (won race)
- P0: Add D13: two parallel `--setup` both exit 0 with one host-local engine + marker
- P1: Document post-lock re-check on bootstrap.md; sync plugin view
**Plan review:** native — keep pathspec to devloop-run card + tests; do not touch market pins this round
**Implementation:** skills/devloop-run/scripts/devloop-run, skills/devloop-run/references/bootstrap.md, test/devloop-run.test.sh, plugins/devloop-run/* via native + sync-plugin-views
**Lint:** skipped (none configured)
**Test result:** PASS
**Outcome:** fixed
**Error signature:** none
**Learnings:** Portable mkdir locks serialize bootstrap but are incomplete without a post-lock double-check — the second waiter can re-extract and `rm -rf` dest after the first finished. Plan P0-5 concurrent case is load-bearing, not optional polish. Pin bootstrap + sha/tarbomb/self-contained paths (D8–D12) held; residual closed the race + D13.
**Anchor evidence:**
- P0-1 → skills/devloop-run/references/engine-pin.json keys version/url/sha256
- P0-2 → D8 empty HOME + pin fixture `--setup`
- P0-3 → D9 sha mismatch exit 2
- P0-4 → D10 tarbomb refused
- P0-5 → D13 concurrent setup (this round)
- P0-6 → D11 card copy from /
- P0-7 → SKILL.md Truth table
- P0-8 → test/run-all.sh PASS
**Consecutive clean rounds after this entry:** 0
**Committed:** yes
**Notes:** New campaign for clean-laptop plan (supersedes prior review-coverage skill residual ledger Status complete)
