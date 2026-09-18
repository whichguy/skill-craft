"""Calibration tests for the external Tic-Tac-Toe UI-driver oracle.

The temporary driver below is a test double, never a claim that the verifier
can drive an arbitrary GAS app.  It independently models the public protocol
so these tests exercise the adapter boundary and demonstrate that plausible
behavioral mutants are rejected.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grading  # noqa: E402
import verify_tictactoe as oracle  # noqa: E402


DRIVER_SOURCE = r'''
import json
import sys
import time

mode = sys.argv[1]
request = json.load(sys.stdin)
if mode == "timeout-mutant":
    time.sleep(10)
    raise SystemExit(0)
if mode == "oversized-output-mutant":
    while True:
        sys.stdout.write("x" * 512)
        sys.stdout.flush()
        time.sleep(0.005)
board = [""] * 9
active = "X"
outcome = "playing"
lines = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
         (2, 5, 8), (0, 4, 8), (2, 4, 6))

def winner(values):
    for a, b, c in lines:
        if values[a] and values[a] == values[b] == values[c]:
            return values[a]
    return None

def outcome_for(values):
    return winner(values) or ("draw" if all(values) else "playing")

def wins_for(player):
    result = []
    for cell, value in enumerate(board):
        if value:
            continue
        candidate = list(board)
        candidate[cell] = player
        if winner(candidate) == player:
            result.append(cell)
    return result

def recommendation(legal):
    own = wins_for(active)
    other = wins_for("O" if active == "X" else "X")
    return (own or other or legal)[0]

observations = []
for action in request["actions"]:
    if action["type"] == "reset":
        board = [""] * 9
        active = "X"
        outcome = "playing"
    elif action["type"] == "move" and outcome == "playing":
        cell = action["cell"]
        if board[cell] == "":
            board[cell] = active
            outcome = outcome_for(board)
            if outcome == "playing":
                active = "O" if active == "X" else "X"
            else:
                active = None
        elif mode == "occupied-mutant":
            board[cell] = active
    legal = [cell for cell, value in enumerate(board) if not value] if outcome == "playing" else []
    highlights = list(range(9)) if mode == "highlight-mutant" else legal
    move = recommendation(legal) if legal else None
    if mode == "hint-mutant" and legal:
        move = legal[-1]
    if mode == "terminal-guidance-mutant" and outcome != "playing":
        highlights = [cell for cell, value in enumerate(board) if not value]
        move = highlights[0] if highlights else None
    observed_active = "O" if mode == "terminal-player-mutant" and outcome != "playing" else active
    observations.append({"board": list(board), "active_player": observed_active, "outcome": outcome,
                         "legal_highlights": highlights, "recommended_move": move})
if mode == "count-mutant":
    observations.pop()
print(json.dumps({"observations": observations}))
'''


CHECK_BY_STEP = {
    "ttt-create": "ttt-base-game",
    "ttt-guidance": "ttt-turn-indicator-and-legal-highlights",
    "ttt-best-move": "ttt-best-move-hint",
}


class TicTacToeOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.driver = self.root / "mock_driver.py"
        self.driver.write_text(textwrap.dedent(DRIVER_SOURCE), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _run(
        self, step_id: str, mode: str, *, timeout: float | None = None,
        max_output_bytes: int | None = None,
    ) -> tuple[int, dict, Path, dict]:
        scenario = oracle._scenario_step(step_id)
        trial = self.root / f"trial-{step_id}-{mode}"
        repo = self.root / f"repo-{step_id}-{mode}"
        evidence = trial / "verification"
        trial.mkdir()
        repo.mkdir()
        evidence.mkdir()
        baseline = None if step_id == "ttt-create" else "b" * 64
        result = {"trial_id": trial.name, "step_id": step_id, "candidate_digest": "c" * 64,
                  "baseline_digest": baseline, "required_checks": scenario["required_checks"]}
        (trial / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (trial / "manifest.json").write_text(json.dumps({"scenario": scenario}), encoding="utf-8")
        environment = {"SHIPLOOP_E2E_TRIAL": str(trial), "SHIPLOOP_E2E_REPO": str(repo),
                       "SHIPLOOP_E2E_EVIDENCE": str(evidence)}
        output = io.StringIO()
        argv = [sys.executable, str(self.driver), mode]
        verifier_args = ["--driver", json.dumps(argv)]
        if timeout is not None:
            verifier_args.extend(["--timeout", str(timeout)])
        if max_output_bytes is not None:
            verifier_args.extend(["--max-output-bytes", str(max_output_bytes)])
        with patch.dict(os.environ, environment, clear=False), redirect_stdout(output):
            code = oracle.main(verifier_args)
        return code, json.loads(output.getvalue()), evidence, result

    @staticmethod
    def _row(receipt: dict, check_id: str) -> dict:
        return next(row for row in receipt["checks"] if row["id"] == check_id)

    def test_good_adapter_calibrates_each_public_behavior(self) -> None:
        for step_id, check_id in CHECK_BY_STEP.items():
            with self.subTest(step_id=step_id):
                code, receipt, evidence, result = self._run(step_id, "good")
                self.assertEqual(code, 0)
                target = self._row(receipt, check_id)
                self.assertEqual(target["status"], "pass")
                self.assertEqual(len(target["evidence"]), 1)
                trace = evidence / target["evidence"][0]["path"]
                self.assertTrue(trace.is_file())
                self.assertEqual(json.loads(trace.read_text(encoding="utf-8"))["issues"], [])
                self.assertEqual(receipt["incremental_review"]["status"], "unverified")
                if step_id != "ttt-create":
                    baseline_row = self._row(receipt, "previous-behavior-preserved")
                    self.assertEqual(baseline_row["status"], "unverified")
                    self.assertIn("pre-feature UI-driver trace", baseline_row["details"])
                grade = grading.validate_receipt(
                    receipt, trial_id=result["trial_id"], candidate_digest=result["candidate_digest"],
                    required_checks=result["required_checks"], evidence_root=evidence,
                    baseline_digest=result["baseline_digest"],
                )
                self.assertEqual(grade["required_checks"][check_id]["status"], "pass")
                self.assertEqual(grade["product_status"], "unverified")

    def test_terminal_guidance_does_not_offer_moves_after_win(self) -> None:
        for step in ("ttt-guidance", "ttt-best-move"):
            with self.subTest(step=step):
                _code, receipt, _evidence, _result = self._run(step, "terminal-guidance-mutant")
                self.assertEqual(self._row(receipt, CHECK_BY_STEP[step])["status"], "fail")

    def test_occupied_cell_mutant_fails_base_game_trace(self) -> None:
        _code, receipt, evidence, _result = self._run("ttt-create", "occupied-mutant")
        row = self._row(receipt, "ttt-base-game")
        self.assertEqual(row["status"], "fail")
        trace = json.loads((evidence / row["evidence"][0]["path"]).read_text(encoding="utf-8"))
        self.assertTrue(any(issue["field"] == "board" for issue in trace["issues"]))

    def test_terminal_active_player_display_is_not_constrained(self) -> None:
        _code, receipt, _evidence, _result = self._run("ttt-create", "terminal-player-mutant")
        self.assertEqual(self._row(receipt, "ttt-base-game")["status"], "pass")

    def test_highlight_mutant_fails_guidance_trace(self) -> None:
        _code, receipt, evidence, _result = self._run("ttt-guidance", "highlight-mutant")
        row = self._row(receipt, "ttt-turn-indicator-and-legal-highlights")
        self.assertEqual(row["status"], "fail")
        trace = json.loads((evidence / row["evidence"][0]["path"]).read_text(encoding="utf-8"))
        self.assertTrue(any(issue["field"] == "legal_highlights" for issue in trace["issues"]))

    def test_bad_immediate_hint_mutant_fails_refinement_trace(self) -> None:
        _code, receipt, evidence, _result = self._run("ttt-best-move", "hint-mutant")
        row = self._row(receipt, "ttt-best-move-hint")
        self.assertEqual(row["status"], "fail")
        trace = json.loads((evidence / row["evidence"][0]["path"]).read_text(encoding="utf-8"))
        missed = {issue["index"] for issue in trace["issues"]
                  if issue["reason"] == "missed-immediate-win-or-block"}
        self.assertTrue({4, 9}.issubset(missed))

    def test_incomplete_external_trace_is_unverified_not_invented(self) -> None:
        _code, receipt, evidence, _result = self._run("ttt-create", "count-mutant")
        row = self._row(receipt, "ttt-base-game")
        self.assertEqual(row["status"], "unverified")
        trace = json.loads((evidence / "tictactoe" / "ttt-create-trace.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["reason"], "driver-observation-count-mismatch")

    def test_timed_out_driver_is_bounded_and_unverified(self) -> None:
        started = time.monotonic()
        _code, receipt, evidence, _result = self._run("ttt-create", "timeout-mutant", timeout=0.08)
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(self._row(receipt, "ttt-base-game")["status"], "unverified")
        trace = json.loads((evidence / "tictactoe" / "ttt-create-trace.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["reason"], "driver-timeout")

    def test_oversized_driver_stream_is_bounded_and_unverified(self) -> None:
        started = time.monotonic()
        _code, receipt, evidence, _result = self._run(
            "ttt-create", "oversized-output-mutant", max_output_bytes=1_024,
        )
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(self._row(receipt, "ttt-base-game")["status"], "unverified")
        trace = json.loads((evidence / "tictactoe" / "ttt-create-trace.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["reason"], "driver-output-exceeded-bound")


if __name__ == "__main__":
    unittest.main()
