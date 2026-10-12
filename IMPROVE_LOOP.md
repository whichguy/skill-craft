# Improve Loop: ShipLoop scripts (skills/shiploop/scripts): defect-only code quality improvement

**Test command:** `test/run-all.sh --group quick --changed-from origin/main`
**Started:** 2026-10-11          **Status:** active
**Iteration counter:** 2
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
- [ ] P1: [implementation] 45 private functions of 25+ lines have no docstring (shiploop_chain*.py, shiploop_lint.py and others) — commenting criterion
  - Evidence: bigundoc scan lists 45 at 25+ lines after the first pass documented the 40 largest
  - Decision: document all 45 in one cycle via a write -> adversarial-verify workflow (names are unique per file, so insertion is by name); each docstring is checked against the function body by two independent verifiers before it is applied
  - Preserve: code behaviour (docstring-only change)
  - Unknown: none
  - Acceptance: every private function of 25+ lines in the batch has an accurate docstring and the quick tier is green

## Deferred (P2)
- [ ] P2: reduce cyclomatic complexity of the 85 functions over McCabe 10 — weak:multi-campaign — behaviour-risky refactor, needs per-function design
- [ ] P2: ARG001 unused parameters on public or test-pinned APIs (render_lines, _require_retry_*) — weak:waived — tests call them with the extra arguments and test edits are out of scope

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)
- consecutive-non-material-cycles: 0

## Next
- **Action:** execute
- **Item:** P1:docstrings-private-25plus (all 45, workflow)
- **Why:** last open item; ultracode workflow with adversarial verify keeps accuracy high

## Last cycle
**N:** 2
**Date:** 2026-10-11
**Thesis:** six error messages (five _UnsafeSource in shiploop_progress_data._read_beneath, one ValueError in navigator_dry_run.run_scenario) name no file, limit or type; adding them gives a reader the context where the error was observed
**Test result:** PASS
**Outcome:** confirmed
**Error signature:** none
**Committed:** yes
**Notes for next cycle:** quick tier exit 0 (27 suites). Probed: message for a 50-byte file with limit 10 reads "'big.txt' is 50 bytes, over its read limit of 10", same for str and Path input (os.fspath). Spec sync n/a: plan unchanged since iter 1 (no V-row tied to this item). Replan: native, one open P1 remains; streak 0. open intent: docstrings | Decision: all 45 in one cycle via workflow | Preserve: behaviour (docstring-only).
