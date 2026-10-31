#!/usr/bin/env python3
"""Small offline tests for the live Battleship UI evaluator's acceptance contract."""
from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui.py"
CASES = ROOT / "test" / "shiploop_e2e" / "cases.json"
spec = importlib.util.spec_from_file_location("battleship_ui", CHECK)
ui = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ui)


def full_game_observation(prefix="SLBattle"):
    results = [
        "miss", "hit", "hit", "hit", "sunk", "miss", "hit", "hit", "sunk",
        "miss", "hit", "hit", "sunk", "miss", "hit", "hit", "hit", "sunk",
        "miss", "hit", "hit", "sunk",
    ]
    shots = []
    controller_shots = []
    ships_left = 5
    sunk_ships = iter((
        ("carrier", 5), ("battleship", 4), ("cruiser", 3),
        ("submarine", 3), ("destroyer", 2),
    ))
    for index, result in enumerate(results, start=1):
        if result == "sunk":
            ships_left -= 1
            ship, size = next(sunk_ships)
        else:
            ship, size = None, None
        row = (index - 1) // 10
        column = (index - 1) % 10
        shots.append({
            "shot_index": index,
            "row": row,
            "column": column,
            "duration_ms": 120 + index,
            "result": result,
            "ships_left_after": ships_left,
            "unfired_cells_after": 100 - index,
            "fired_cell_disabled": True,
        })
        controller_shots.append({
            "method": "fire", "request_id": f"shot-{index};a", "response_id": f"shot-{index};a",
            "row": row, "column": column,
            "last_shot": {"row": row, "col": column, "result": result, "ship": ship, "size": size},
            "shots": index, "ships_left": ships_left, "game_over": ships_left == 0,
        })
    return {
        "initial_cells": 100, "initial_unique_cells": 100,
        "initial_labels_matched": True, "initial_all_enabled": True,
        "initial_shots": 0, "initial_ships": 5,
        "shots_played": len(shots), "sink_count": 5, "hit_or_sunk_shots": 17,
        "final_ships_left": 0, "final_unfired_cells": 100 - len(shots),
        "shot_observations": shots,
        "game_over_initial_message_count": 1,
        "game_over_after_fourth_sink_message_count": 1,
        "game_over_after_fourth_sink_new_message_count": 0,
        "game_over_final_message_count": 2,
        "game_over_final_new_message_count": 1,
        "game_over_new_message_observed": True,
        "game_over_after_reset_message_count": 1,
        "game_over_after_reset_matches_initial": True,
        "reset_cells": 100, "reset_unique_cells": 100,
        "reset_labels_matched": True, "reset_all_enabled": True,
        "reset_cell_enabled": True, "reset_shots": 0, "reset_ships": 5,
        "route_host": "example.lightning.force.com",
        "route_path": f"/lightning/n/{prefix}_Board",
        "controller_proof_scope": "apex-controller-and-dom",
        "controller_proof": {
            "controller_class": f"{prefix}Controller",
            "new_game": {
                "method": "newGame", "request_id": "new-game;1", "response_id": "new-game;1",
                "last_shot": None, "shots": 0, "ships_left": 5, "game_over": False,
            },
            "shots": controller_shots,
        },
        "browser_version": "Chrome 139",
    }


class BattleshipUiContractTests(unittest.TestCase):
    def test_accepts_complete_live_observation(self):
        observation = full_game_observation()
        self.assertEqual([], ui.validate_observation(observation, expected_host="example.lightning.force.com", prefix="SLBattle"))

    def test_accepts_enabled_fired_cell(self):
        observation = full_game_observation()
        observation["shot_observations"][0]["fired_cell_disabled"] = False
        self.assertEqual([], ui.validate_observation(observation, expected_host="example.lightning.force.com", prefix="SLBattle"))

    def test_rejects_missing_cells_and_nonfunctional_reset(self):
        observation = full_game_observation()
        observation.update(initial_cells=99, reset_cell_enabled=False,
                           route_host="other.lightning.force.com")
        errors = ui.validate_observation(observation, expected_host="example.lightning.force.com", prefix="SLBattle")
        self.assertIn("ui-initial-cells-mismatch", errors)
        self.assertIn("ui-reset-cell-disabled", errors)
        self.assertIn("ui-route-host-mismatch", errors)

    def test_rejects_missing_or_wrong_full_game_evidence(self):
        cases = (
            ("missing-shots", lambda value: value.pop("shot_observations"), "ui-shot-observations-missing"),
            ("sink-count", lambda value: value.update(sink_count=4), "ui-sink-count-mismatch"),
            ("hit-count", lambda value: value.update(hit_or_sunk_shots=16), "ui-hit-or-sunk-shots-mismatch"),
            ("final-ships", lambda value: value.update(final_ships_left=1), "ui-final-ships-left-mismatch"),
            ("game-over", lambda value: value.update(game_over_new_message_observed=False,
                                                       game_over_final_new_message_count=0),
             "ui-game-over-observation-mismatch"),
            ("reset-state", lambda value: value.update(reset_ships=4), "ui-reset-ships-mismatch"),
            ("premature-game-over", lambda value: value.update(game_over_after_fourth_sink_new_message_count=1),
             "ui-game-over-observation-mismatch"),
        )
        for name, mutate, expected_error in cases:
            with self.subTest(name=name):
                observation = full_game_observation()
                mutate(observation)
                errors = ui.validate_observation(
                    observation, expected_host="example.lightning.force.com", prefix="SLBattle")
                self.assertIn(expected_error, errors)

    def test_rejects_missing_or_mismatched_controller_proof(self):
        cases = (
            ("missing-proof", lambda value: value.pop("controller_proof"), "controller-proof-missing"),
            ("wrong-scope", lambda value: value.update(controller_proof_scope="dom-only"),
             "controller-proof-missing"),
            ("wrong-class", lambda value: value["controller_proof"].update(controller_class="OtherController"),
             "controller-config-invalid"),
            ("missing-initial-call", lambda value: value["controller_proof"].pop("new_game"),
             "controller-new-game-missing"),
            ("missing-fire-proof", lambda value: value["controller_proof"].pop("shots"),
             "controller-fire-missing"),
            ("response-id", lambda value: value["controller_proof"]["shots"][0].update(response_id="other;a"),
             "controller-response-id-mismatch"),
            ("request-coordinate", lambda value: value["controller_proof"]["shots"][0].update(row=9),
             "controller-coordinate-mismatch"),
            ("returned-coordinate", lambda value: value["controller_proof"]["shots"][0]["last_shot"].update(col=9),
             "controller-last-shot-coordinate-mismatch"),
            ("counter", lambda value: value["controller_proof"]["shots"][0].update(shots=99),
             "controller-counters-mismatch"),
            ("ships-left-counter", lambda value: value["controller_proof"]["shots"][0].update(ships_left=3),
             "controller-counters-mismatch"),
            ("result", lambda value: value["controller_proof"]["shots"][0]["last_shot"].update(result="hit"),
             "controller-last-shot-mismatch"),
            ("initial-state", lambda value: value["controller_proof"]["new_game"].update(ships_left=4),
             "controller-initial-state-mismatch"),
            ("final-game-over", lambda value: value["controller_proof"]["shots"][-1].update(game_over=False),
             "controller-game-over-mismatch"),
        )
        for name, mutate, expected_error in cases:
            with self.subTest(name=name):
                observation = full_game_observation()
                mutate(observation)
                errors = ui.validate_observation(
                    observation, expected_host="example.lightning.force.com", prefix="SLBattle")
                self.assertIn(expected_error, errors)

    def test_rejects_per_shot_counter_and_duplicate_coordinate_errors(self):
        observation = full_game_observation()
        observation["shot_observations"][0]["ships_left_after"] = 4
        errors = ui.validate_observation(observation, expected_host="example.lightning.force.com", prefix="SLBattle")
        self.assertIn("ui-ship-counter-sequence-mismatch", errors)

        observation = full_game_observation()
        observation["shot_observations"][1]["row"] = observation["shot_observations"][0]["row"]
        observation["shot_observations"][1]["column"] = observation["shot_observations"][0]["column"]
        errors = ui.validate_observation(observation, expected_host="example.lightning.force.com", prefix="SLBattle")
        self.assertIn("ui-shot-cell-repeat", errors)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the browser contract helper")
    def test_button_name_contract_covers_grid_and_rejects_format_drift(self):
        module = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui_contract.cjs"
        program = "const c=require(process.argv[1]);const names=[];for(let r=0;r<10;r++)for(let x=0;x<10;x++)names.push(c.cellName(r,x,'unfired'));const pattern=c.cellNamePattern('unfired');const good=names.every(n=>pattern.test(n))&&new Set(names).size===100;const badFormat=pattern.test('Battle cell row 0, column 0: unfired');process.stdout.write(JSON.stringify({good,badFormat,count:names.length}));"
        done = subprocess.run([shutil.which("node"), "-e", program, str(module)], capture_output=True,
                              text=True, check=True, timeout=10)
        observed = json.loads(done.stdout)
        self.assertTrue(observed["good"])
        self.assertFalse(observed["badFormat"])
        self.assertEqual(100, observed["count"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the browser helper contract")
    def test_browser_helper_exports_board_exercise_for_local_rehearsal(self):
        module = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui_browser.cjs"
        program = (
            "const h=require(process.argv[1]);"
            "process.stdout.write(JSON.stringify({"
            "exerciseBoard:typeof h.exerciseBoard,"
            "hasGameOverMarker:typeof h.hasGameOverMarker,"
            "playwrightModule:typeof h.playwrightModule,"
            "browserExecutable:typeof h.browserExecutable}));"
        )
        done = subprocess.run([shutil.which("node"), "-e", program, str(module)], capture_output=True,
                              text=True, check=True, timeout=10)
        self.assertEqual({"exerciseBoard": "function", "hasGameOverMarker": "function", "playwrightModule": "function",
                          "browserExecutable": "function"}, json.loads(done.stdout))

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the pure game-over matcher")
    def test_game_over_matcher_requires_affirmative_completion_phrase(self):
        module = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui_browser.cjs"
        samples = [
            "Game over: every ship is sunk.", "Game is over.", "The game is over!",
            "Game over — you sank the fleet!", "You win!", "You won.", "Victory!",
            "No winner yet — Game over!", "No winner yet (n shots).", "No victory yet.",
            "The game is not over.", "The game isn't over.", "A winner will be chosen later.",
            "Winner has not been determined.", "Victory will be declared later.",
            "You win when every ship is sunk.", "Winner!",
        ]
        program = (
            "const h=require(process.argv[1]);"
            f"const samples=JSON.parse({json.dumps(json.dumps(samples))});"
            "process.stdout.write(JSON.stringify(samples.map(h.hasGameOverMarker)));"
        )
        done = subprocess.run([shutil.which("node"), "-e", program, str(module)], capture_output=True,
                              text=True, check=True, timeout=10)
        self.assertEqual([True, True, True, True, True, True, True, True,
                          False, False, False, False, False, False, False, False, False],
                         json.loads(done.stdout))

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for safe browser stage parity")
    def test_python_and_browser_helper_allow_the_same_safe_codes(self):
        module = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui_browser.cjs"
        program = "const h=require(process.argv[1]);process.stdout.write(JSON.stringify({stages:[...h.SAFE_STAGES],reasons:[...h.SAFE_REASONS]}));"
        done = subprocess.run([shutil.which("node"), "-e", program, str(module)], capture_output=True,
                              text=True, check=True, timeout=10)
        observed = json.loads(done.stdout)
        self.assertEqual(ui.SAFE_BROWSER_STAGES, set(observed["stages"]))
        self.assertEqual(ui.SAFE_BROWSER_REASONS, set(observed["reasons"]))

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the controller contract tests")
    def test_browser_controller_contract_suite_passes_with_measured_tests(self):
        module = ROOT / "test" / "shiploop_e2e" / "checks" / "battleship_ui_controller_contract.test.cjs"
        done = subprocess.run([shutil.which("node"), "--test", str(module)], cwd=ROOT,
                              capture_output=True, text=True, timeout=30, check=False)
        output = done.stdout + done.stderr
        self.assertEqual(0, done.returncode, output)
        summary = re.search(r"(?m)^(?:#\s*|ℹ\s*)?tests\s+(\d+)\s*$", output)
        if not summary:
            summary = re.search(r"(?m)^1\.\.(\d+)\s*$", output)
        self.assertIsNotNone(summary, output)
        self.assertGreater(int(summary.group(1)), 0, output)

    def test_mocked_run_check_receipt_contains_full_game_observations(self):
        observation = full_game_observation()
        expected_host = observation["route_host"]
        identity = {"alias": "de", "org_id": "00D000000000001", "lightning_host": expected_host}
        browser_requests = []

        # Unknown adapter fields are deliberately present; the Python receipt projection must drop them.
        observation["raw_game"] = "SECRET_RAW_GAME"
        observation["fleet"] = ["SECRET_FLEET"]
        observation["login_url"] = "https://SECRET_LOGIN_URL/frontdoor"
        observation["headers"] = {"authorization": "SECRET_HEADER"}
        observation["controller_proof"]["raw_game"] = "SECRET_CONTROLLER_GAME"
        observation["controller_proof"]["fleet"] = ["SECRET_CONTROLLER_FLEET"]
        observation["controller_proof"]["request_url"] = "https://SECRET_CONTROLLER_URL/aura"
        observation["controller_proof"]["shots"][0]["headers"] = {"authorization": "SECRET_SHOT_HEADER"}
        with tempfile.TemporaryDirectory() as temp_dir:
            platform_dir = Path(temp_dir) / "run" / "platform"
            platform_dir.mkdir(parents=True)

            def fake_browser(command, *, input, **kwargs):
                request = json.loads(input)
                browser_requests.append(request)
                Path(request["screenshot"]).write_bytes(b"local screenshot bytes")
                Path(request["game_over_screenshot"]).write_bytes(b"local game-over screenshot bytes")
                return SimpleNamespace(returncode=0, stdout=json.dumps(observation))

            output = io.StringIO()
            with mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(platform_dir), "NODE_BINARY": "/usr/bin/node",
                                              "E2E_CHECK_PHASE": "final"}), \
                 mock.patch.object(ui, "org_identity", return_value=identity), \
                 mock.patch.object(ui, "candidate_fingerprint", return_value=("head", "metadata-hash")), \
                 mock.patch.object(ui, "frontdoor_url", return_value="https://example.com/frontdoor"), \
                 mock.patch.object(ui.subprocess, "run", side_effect=fake_browser), \
                 mock.patch.object(sys, "stdout", output):
                self.assertEqual(0, ui.run_check("de", "SLBattle"))

            receipt_path = next(platform_dir.rglob("observation.json"))
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual("shiploop-battleship-ui-observation/3", receipt["schema"])
            self.assertEqual("final", receipt["phase"])
            self.assertEqual("SLBattleController", browser_requests[0]["controller_class"])
            self.assertIs(True, browser_requests[0]["require_controller"])
            self.assertEqual("apex-controller-and-dom", receipt["controller_proof_scope"])
            self.assertEqual(observation["shot_observations"], receipt["observations"]["shot_observations"])
            self.assertTrue(receipt["observations"]["game_over_new_message_observed"])
            self.assertTrue(receipt["observations"]["game_over_after_reset_matches_initial"])
            self.assertEqual(64, len(receipt["game_over_screenshot_sha256"]))
            self.assertTrue(Path(platform_dir / receipt["game_over_screenshot_path"]).is_file())
            self.assertIn("complete game: 22 shots, 5 sinks, game over shown, New game reset", output.getvalue())
            printed = re.search(r"battleship-ui: receipt=(\S+) sha256=([0-9a-f]{64})", output.getvalue())
            self.assertIsNotNone(printed)
            self.assertEqual(receipt_path.relative_to(platform_dir).as_posix(), printed.group(1))
            self.assertEqual(hashlib.sha256(receipt_path.read_bytes()).hexdigest(), printed.group(2))
            proof = receipt["controller_proof"]
            self.assertEqual({"controller_class", "new_game", "shots"}, set(proof))
            self.assertEqual({"method", "request_id", "response_id", "last_shot", "shots", "ships_left", "game_over"},
                             set(proof["new_game"]))
            self.assertEqual({"method", "request_id", "response_id", "row", "column", "last_shot",
                              "shots", "ships_left", "game_over"}, set(proof["shots"][0]))
            self.assertEqual({"row", "col", "result", "ship", "size"}, set(proof["shots"][0]["last_shot"]))
            self.assertNotRegex(json.dumps(receipt),
                                r"SECRET_(?:RAW_GAME|FLEET|LOGIN_URL|HEADER|CONTROLLER_GAME|CONTROLLER_FLEET|CONTROLLER_URL|SHOT_HEADER)")

    def test_mocked_run_check_separates_phase_artifacts_and_bounds_unknown_phase(self):
        observation = full_game_observation("SLNavUi")
        identity = {"alias": "de", "org_id": "00D000000000001",
                    "lightning_host": observation["route_host"]}

        def fake_browser(command, *, input, **kwargs):
            request = json.loads(input)
            Path(request["screenshot"]).write_bytes(b"local screenshot bytes")
            Path(request["game_over_screenshot"]).write_bytes(b"local game-over screenshot bytes")
            return SimpleNamespace(returncode=0, stdout=json.dumps(observation))

        with tempfile.TemporaryDirectory() as temp_dir:
            platform_dir = Path(temp_dir) / "run" / "platform"
            platform_dir.mkdir(parents=True)
            receipts = {}
            with mock.patch.object(ui, "org_identity", return_value=identity), \
                 mock.patch.object(ui, "candidate_fingerprint", return_value=("head", "metadata-hash")), \
                 mock.patch.object(ui, "frontdoor_url", return_value="https://example.com/frontdoor"), \
                 mock.patch.object(ui.subprocess, "run", side_effect=fake_browser):
                for requested_phase, expected_phase in (
                    ("builder", "builder"),
                    ("final", "final"),
                    ("product_at_stop", "product_at_stop"),
                    ("not-a-harness-phase", "unknown"),
                ):
                    output = io.StringIO()
                    with mock.patch.dict(os.environ, {
                        "E2E_PLATFORM_DIR": str(platform_dir), "NODE_BINARY": "/usr/bin/node",
                        "E2E_CHECK_PHASE": requested_phase,
                    }), mock.patch.object(sys, "stdout", output):
                        self.assertEqual(0, ui.run_check("de", "SLNavUi"))
                    printed = re.search(r"battleship-ui: receipt=(\S+) sha256=([0-9a-f]{64})", output.getvalue())
                    self.assertIsNotNone(printed)
                    receipt_path = platform_dir / printed.group(1)
                    receipt = json.loads(receipt_path.read_text())
                    self.assertEqual(expected_phase, receipt["phase"])
                    self.assertEqual(expected_phase, receipt_path.parent.parent.name)
                    self.assertEqual(hashlib.sha256(receipt_path.read_bytes()).hexdigest(), printed.group(2))
                    receipts.setdefault(expected_phase, []).append(receipt_path)

            self.assertEqual({"builder", "final", "product_at_stop", "unknown"}, set(receipts))
            self.assertEqual(4, len({path.parent.parent for paths in receipts.values() for path in paths}))

    def test_mocked_failed_run_check_prints_phase_receipt_hash(self):
        identity = {"alias": "de", "org_id": "00D000000000001",
                    "lightning_host": "example.lightning.force.com"}

        def failed_browser(command, *, input, **kwargs):
            return SimpleNamespace(returncode=1, stdout=json.dumps({
                "status": "failed", "stage": "play", "reason": "shot-count-mismatch",
            }))

        with tempfile.TemporaryDirectory() as temp_dir:
            platform_dir = Path(temp_dir) / "run" / "platform"
            platform_dir.mkdir(parents=True)
            output = io.StringIO()
            with mock.patch.dict(os.environ, {
                "E2E_PLATFORM_DIR": str(platform_dir), "NODE_BINARY": "/usr/bin/node",
                "E2E_CHECK_PHASE": "product_at_stop",
            }), mock.patch.object(ui, "org_identity", return_value=identity), \
                 mock.patch.object(ui, "candidate_fingerprint", return_value=("head", "metadata-hash")), \
                 mock.patch.object(ui, "frontdoor_url", return_value="https://example.com/frontdoor"), \
                 mock.patch.object(ui.subprocess, "run", side_effect=failed_browser), \
                 mock.patch.object(sys, "stderr", output):
                self.assertEqual(1, ui.run_check("de", "SLNavUi"))

            printed = re.search(r"battleship-ui: receipt=(\S+) sha256=([0-9a-f]{64})", output.getvalue())
            self.assertIsNotNone(printed)
            receipt_path = platform_dir / printed.group(1)
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual("shiploop-battleship-ui-observation/3", receipt["schema"])
            self.assertEqual("product_at_stop", receipt["phase"])
            self.assertEqual("failed", receipt["status"])
            self.assertEqual(hashlib.sha256(receipt_path.read_bytes()).hexdigest(), printed.group(2))

    def test_builder_cannot_override_ui_org_or_prefix(self):
        base = ["--org", "de", "--prefix", "SLBattle"]
        self.assertEqual([], ui.scope_errors(base))
        final_args, final_errors = ui.parse_scope(base + ["--final", "--check-name", "battleship-ui"])
        self.assertEqual([], final_errors)
        self.assertTrue(final_args.final)
        self.assertIn("duplicate-scope-option", ui.scope_errors(base + ["--org", "other"]))
        self.assertIn("duplicate-scope-option", ui.scope_errors(base + ["--prefix", "SLBattle"]))
        self.assertIn("invalid-options", ui.scope_errors(base + ["--target-org", "other"]))
        self.assertIn("check-name-mismatch", ui.scope_errors(base + ["--check-name", "other"]))

    def test_builder_runtime_overrides_cannot_capture_the_login_url(self):
        sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
        import run as runner
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            trusted = folder / "trusted"
            trusted.mkdir()
            capture = folder / "captured.txt"
            marker = "CANARY123"
            fake_sf = trusted / "sf"
            fake_sf.write_text(
                "#!" + sys.executable + "\nimport json,sys\n"
                "value = {'nonScratchOrgs':[{'alias':'de','orgId':'00D000000000001AAA',"
                "'instanceUrl':'https://canary.my.salesforce.com'}]} if sys.argv[1:3] == ['org','list'] "
                "else {'url':'https://canary.my.salesforce.com/secur/frontdoor.jsp?otp=CANARY123'}\n"
                "print(json.dumps({'status':0,'result':value}))\n")
            fake_sf.chmod(0o755)
            safe_node = trusted / "node"
            safe_node.write_text(
                "#!" + sys.executable + "\nimport os,sys\ntext=sys.stdin.read()\n"
                "if any(k.startswith(('NODE_','PLAYWRIGHT_')) or k=='BROWSER_EXECUTABLE_PATH' for k in os.environ):\n"
                "    open(os.environ['GRAB_OUT'],'w').write(text)\n"
                "print('{\"status\":\"failed\",\"stage\":\"browser\"}')\nsys.exit(1)\n")
            safe_node.chmod(0o755)
            attacker = folder / "grab"
            attacker.write_text(
                "#!" + sys.executable + "\nimport os,sys\n"
                "open(os.environ['GRAB_OUT'],'w').write(sys.stdin.read())\n"
                "print('{\"status\":\"failed\",\"stage\":\"browser\"}')\nsys.exit(1)\n")
            attacker.chmod(0o755)
            work = folder / "work"
            (work / "force-app").mkdir(parents=True)
            (work / "force-app/X.cls").write_text("public class X {}")
            platform_dir = folder / "platform"
            trusted_path = str(trusted) + os.pathsep + os.environ.get("PATH", os.defpath)
            with mock.patch.dict(os.environ, {"PATH": trusted_path}):
                bins = runner.write_model_bin(
                    {"battleship-ui": 'python3 "$E2E_CHECKS/battleship_ui.py" --org de --prefix SLTest'},
                    platform_dir, Path.home())
            env = dict(os.environ, PATH=trusted_path, GRAB_OUT=str(capture), NODE_BINARY=str(attacker),
                       NODE_OPTIONS="--require=/untrusted/hook.js", PLAYWRIGHT_NODE_PATH="/untrusted/module",
                       BROWSER_EXECUTABLE_PATH="/untrusted/browser")
            done = subprocess.run([bins["battleship-ui"]], cwd=work, env=env, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(done.returncode, 0, "the no-browser stand-in must fail the UI check")
            self.assertNotIn(marker, done.stdout + done.stderr)
            leaked = capture.read_text() if capture.exists() else ""
            self.assertNotIn(marker, leaked, "model-selected runtime captured the session-bearing URL")

    def test_main_uses_case_baked_nondefault_prefix(self):
        argv = ["--org", "de", "--prefix", "SLBtl7391"]
        args, errors = ui.parse_scope(argv)
        self.assertEqual([], errors)
        self.assertEqual("SLBtl7391", args.prefix)
        with mock.patch.object(sys, "argv", ["battleship_ui.py", *argv]), \
             mock.patch.object(ui, "run_check", return_value=0) as run_check, \
             mock.patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(0, ui.main())
        run_check.assert_called_once_with("de", "SLBtl7391")

    def test_command_reports_one_real_unittest_result_and_preserves_failure(self):
        count_spec = importlib.util.spec_from_file_location(
            "ui_test_counts", ROOT / "skills/shiploop/scripts/shiploop_test_counts.py")
        counts = importlib.util.module_from_spec(count_spec)
        count_spec.loader.exec_module(counts)
        for status in (0, 1):
            output = io.StringIO()
            with self.subTest(status=status), \
                 mock.patch.object(sys, "argv", ["battleship_ui.py", "--org", "de", "--prefix", "SLTest"]), \
                 mock.patch.object(ui, "run_check", return_value=status), \
                 mock.patch.object(sys, "stderr", output):
                self.assertEqual(status, ui.main())
            measured = counts.count(output.getvalue(), status)
            self.assertEqual((measured["ran"], measured["failed"]), (1, status))
            self.assertEqual(counts.outcomes(output.getvalue(), ["test_deployed_open_fire_reset"]),
                             {"test_deployed_open_fire_reset": "passed" if status == 0 else "failed"})

    def test_salesforce_ui_case_requires_builder_command_and_final_check(self):
        case = json.loads(CASES.read_text())["battleship-salesforce-ui"]
        command = 'python3 "$E2E_CHECKS/battleship_ui.py" --org de --prefix SLNavUi'
        final_command = command + " --final --check-name battleship-ui"
        self.assertIn(final_command, case["checks"])
        self.assertEqual(command, case["platform"]["model_bin"]["battleship-ui"])
        self.assertNotIn("seed_product", case)
        self.assertNotIn("seed_release", case)
        self.assertIn("battleship-ui", case["platform"]["keep_checks"])
        self.assertIn("run the provided `battleship-ui` command", case["prompt"])
        self.assertIn("Battle cell row <row> column <column>", case["prompt"])
        self.assertIn("All unfired cells must be enabled when the game opens and after New game", case["prompt"])


if __name__ == "__main__":
    unittest.main()
