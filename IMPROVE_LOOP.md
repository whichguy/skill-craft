# Improve Loop: ShipLoop scripts (skills/shiploop/scripts): defect-only code quality improvement

**Test command:** `test/run-all.sh --group quick --changed-from origin/main`
**Started:** 2026-10-11          **Status:** active
**Iteration counter:** 3
**Seed mode:** defect
**Product residual survey:** n/a (defect)
**Plan tier:** 2
**Spec validation:** pass
**Habitat claimed:** no
**Habitat probe:** n/a
**Habitat probe result:** n/a
**Habitat probe evidence:** none
**Operator done-when:** (none)
**Install mechanism:** n/a

## Campaign brief
- **Target:** skills/shiploop/scripts (Python 3.9-compatible CLI scripts); continue the 2026-10-11 quality pass (portability, argument checks, error context, comments, naming).
- **Problem / opportunity:** survey at a081f4c9 found one real defect (stale `__all__`), six context-free error messages, and 45 undocumented private functions of 25+ lines.
- **In scope:** skills/shiploop/scripts/*.py and shiploop; a change note under changes/shiploop/.
- **Out of scope / waived:** locking redesign (owner: no lock module); splitting large modules; test changes (owner: code only); unused-arg ARG001 on test-pinned or uniform-signature APIs (weak).
- **Constraints:** scripts must run on Python 3.9 (macOS system python): no zip(strict=), no match, lint with --target-version py39; no packet text or protocol change; run the quick tier once per cycle.
- **Criteria map:** C-defect: shiploop_quality __all__ -> promote; C-context: terse raises -> promote; C-comments: private fns -> promote (decompose by file); C-complexity: C901 -> P2 weak:multi-campaign.
- **T2 challenge:** native
- **Success / Done when:** residual x2 + green suite (skill law only)
- **Plan tier:** 2

## Spec validation
| ID | Intention | Kind | Artifact(s) | Proof | Status |
|---|---|---|---|---|---|
| V1 | n/a: item complete | L3-test | skills/shiploop/scripts/shiploop_quality.py | `python3 -c "import sys;sys.path.insert(0,'skills/shiploop/scripts');import shiploop_quality as q;assert all(hasattr(q,n) for n in q.__all__)"` exits 0 | n/a |
| V2 | Preserve: scripts run on Python 3.9 | prose-sweep | skills/shiploop/scripts | `for f in skills/shiploop/scripts/shiploop_*.py; do /usr/bin/python3 -B -c "import sys;sys.path.insert(0,'skills/shiploop/scripts');import $(basename ${f%.py})" || exit 1; done` exits 0 | pass |
| V3 | Regression: quick tier green | suite | test/run-all.sh | `test/run-all.sh --group quick --changed-from origin/main` exit 0 | pass |

## Backlog
- [ ] P1: [implementation] 26 private functions of 25+ lines still have no docstring (shiploop_workspace 6, shiploop_chain_handoff 5, shiploop_chain 3, others) — commenting criterion
  - Evidence: cycle 3 ran a write -> two-skeptic verify -> revise -> recheck workflow over 45; 19 passed and landed; 26 were rejected, but the objections were mostly "does not say X" omissions (about 5 per docstring) and only a handful were factual errors
  - Decision: rerun the 26 with the accuracy lens kept strict (every stated claim true) and the completeness lens narrowed to omissions that would mislead a caller or hide a raise or side effect, not exhaustiveness; allow up to 600 characters
  - Preserve: behaviour (docstring-only; verify by comparing the syntax tree with docstrings stripped)
  - Unknown: none
  - Acceptance: each remaining function has an accurate docstring or is dropped with a Notes line; quick tier green

## Deferred (P2)
- [ ] P2: reduce cyclomatic complexity of the 85 functions over McCabe 10 — weak:multi-campaign — behaviour-risky refactor, needs per-function design
- [ ] P2: ARG001 unused parameters on public or test-pinned APIs (render_lines, _require_retry_*) — weak:waived — tests call them with the extra arguments and test edits are out of scope

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)
- consecutive-non-material-cycles: 0

## Next
- **Action:** execute
- **Item:** P1:docstrings-private-25plus (remaining 26, narrowed completeness lens)
- **Why:** only open item; this is the last allowed cycle (4/4)

## Last cycle
**N:** 3
**Date:** 2026-10-15
**Thesis:** documenting the 45 private functions of 25+ lines is safest with an adversarial pipeline (draft, two skeptics with different lenses, revise, recheck) whose drafts are written to files by the agents themselves, so no docstring text is retyped
**Test result:** PASS
**Outcome:** partial
**Error signature:** none
**Committed:** yes
**Notes for next cycle:** 19 of 45 docstrings passed both skeptics and landed (9 files, 95 added lines); the syntax tree with docstrings stripped is identical to the previous commit in all 9 files, so the change is docstring-only. 26 rejected, mostly for omissions rather than errors. Quick tier PASS (42 suites); the background wrapper was killed (exit 144) but the orphaned runner finished and printed PASS. Two earlier workflow attempts hit the account's monthly spend limit (89 then 43 agents errored) before the weekly reset on Oct 15; resuming replayed cached agents. Spec sync n/a: plan unchanged in V-rows. open intent: docstrings | Decision: rerun 26 with narrowed completeness lens | Preserve: docstring-only.
