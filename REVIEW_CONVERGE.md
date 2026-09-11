# Review Converge: ShipLoop 0.8.35 Frozen always reprints the lint oracle

**Target paths:** `skills/shiploop/scripts/shiploop`, `skills/shiploop/references/activities/plan.md`, `skills/shiploop/README.md`, `skills/shiploop/SKILL.md`, `test/shiploop.test.sh`, `test/shiploop-testkit.sh`, `docs/LOOP-ENGINEERING.md`, `skills/devloop/references/loop-engineering.md`, `plugins/devloop/skills/devloop/references/loop-engineering.md`, `plugins/shiploop/`
**Test command:** `bash test/shiploop.test.sh && ./scripts/sync-plugin-views.sh --check shiploop`
**Started:** 2026-09-11          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 1
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.grok/sessions/%2FUsers%2Fdadleet%2Fsrc%2Ftic-tac-toe-oneshot/01a090ba-11f0-7a22-b13e-9a1caf7126bd/plan.md`
**Plan hash:** `283b7384a7f957b231d30bcc6a207815a2c513f421a4720e81b6edfb8fc17f87`
**Base ref:** `3d7ab97bc512c1b264fed5c614fe295a3240cedc`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Deferred (minor/P2)
(none)

## Log
### Round 1 — 2026-09-11
**Review:** 0 material, 0 minor
**Material findings:** none
**Deferred (minor/P2):** (none)
**Git-history check:** Archived prior complete 0.8.34 campaign (`REVIEW_CONVERGE.archived-shiploop-0.8.34-every-available-20260911.md`). Product land is `2c45165` vs Base `3d7ab97`. Closer append-not-infix and dest-identity carve-out stay un-infixed.
**Plan:** n/a (clean)
**Plan review:** n/a
**Implementation:** n/a
**Lint:** n/a
**Test result:** N/A (clean round)
**Outcome:** clean
**Error signature:** none
**Learnings:** Forward A1–A6 hold in `2c45165`: Frozen prints `LINT_ORACLE_LINE` after Exclusive `(none)` and legacy not-recorded; dest-blocked stays Exclusive-rows-only; activity Frozen prose no longer says rows-only; testkit exports `PYTHONDONTWRITEBYTECODE=1`; `transitions.json` untouched; suite + plugin `--check shiploop` passed at product land. Reverse vs `3d7ab97` is the intended printer + activity/docs + tests + LOOP-ENGINEERING pin.
**Anchor evidence:**
- A1 → `test/shiploop.test.sh` Exclusive none `$out_imp` requires `Lint oracle:` and `every available`; forbids `If the writer above fails`
- A2 → missing-exclusive Frozen unit asserts `Lint oracle:` in out after `Exclusive: (not recorded`
- A3 → `print(DEST_BLOCKED_LINE)` more indented than `print(LINT_ORACLE_LINE)` in `print_frozen_session_env`; Exclusive-rows `$out_pbfz` still has dest-blocked
- A4 → `plan.md` `always prints the Lint oracle`; no `When Exclusive rows exist it also prints`; no `^## `; no `Key learnings:`
- A5 → `test/shiploop-testkit.sh` `export PYTHONDONTWRITEBYTECODE=1`
- A6 → `VERSION = "0.8.35"`; suite PASS at product land; `--check shiploop` OK
**Consecutive clean rounds after this entry:** 1
**Committed:** yes
**Notes:** Prior complete ledger archived (gitignored) so this campaign could start.
