#!/usr/bin/env python3
"""Narrow checks on the vendored Until Loop: each one fails for exactly one kind of drift, and none pins a release.

1. Provenance: the manifest's hashes match the shipped files and its version matches the adapter card.
2. Marketplace pin: catalog/external-plugins.json points at the commit and version the manifest vendors.
3. Packet contract: every key the runtime prints is a key ShipLoop accepts (and the reverse), so a runtime change
   that adds a packet field cannot silently break ShipLoop's terminal-packet checks.
4. No size cap: the runtime accepts a very long request, many exit checks and a very long report (owner, 2026-10-11).
5. Hook visibility: exit checks run only through the executor's own shell script, never inside the runtime.
6. Lean returns: a run with a receipt prints lean start and done returns within their byte bounds; the receipt keeps
   the full packet and next prints it whole.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "skills/improve/runtime/until-loop"
SCRIPT = RUNTIME_DIR / "scripts/until_loop_ephemeral.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_loops as loops  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402

spec = importlib.util.spec_from_file_location("until_loop_ephemeral_vendor", SCRIPT)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def start(workspace: str, **overrides):
    contract = {"workspace": workspace, "work": "w", "exit_condition": "e", "repeat_condition": "r",
                "context": {"request": "q", "scope": "s", "authority": "a", "environment": "e", "resources": []},
                **overrides}
    return runtime.start(contract)


class ProvenanceTests(unittest.TestCase):
    manifest = json.loads((RUNTIME_DIR / "PROVENANCE.json").read_text())

    def test_every_listed_file_matches_its_hash(self):
        for entry in self.manifest["default_ephemeral_runtime"]:
            data = (RUNTIME_DIR / entry["bundled_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"], entry["bundled_path"])

    def test_the_adapter_card_declares_the_manifest_version(self):
        adapter = (RUNTIME_DIR / "ADAPTER.md").read_text()
        self.assertIn(f"version: {self.manifest['upstream']['version']}\n", adapter)
        self.assertIn("start --isolated", adapter)

    def test_the_session_and_recovery_helpers_are_vendored(self):
        entries = {entry["bundled_path"] for entry in self.manifest["default_ephemeral_runtime"]}
        self.assertTrue({
            "scripts/until_loop_session.py",
            "scripts/until_loop_recover.py",
        }.issubset(entries))

    def test_the_marketplace_pin_is_the_vendored_commit(self):
        catalog = json.loads((ROOT / "catalog/external-plugins.json").read_text())
        pin = next(p for p in catalog["plugins"] if p["name"] == "until-loop")
        self.assertEqual(pin["source"]["sha"], self.manifest["upstream"]["commit"])
        self.assertEqual(pin["version"], self.manifest["upstream"]["version"])


class PacketContractTests(unittest.TestCase):
    def test_runtime_packet_keys_are_exactly_the_keys_shiploop_accepts(self):
        with tempfile.TemporaryDirectory() as workspace:
            packet = start(workspace)
        self.assertEqual(set(packet), set(loops._PACKET_KEYS))
        self.assertEqual(set(loops._PACKET_KEYS), set(standalone._TERMINAL_PACKET_FIELDS))

    def test_terminal_packet_keys_match_too(self):
        with tempfile.TemporaryDirectory() as workspace:
            packet = start(workspace)
            report = {"classification": "non-trivial", "exit_assessment": "satisfied",
                      "continuation_assessment": "allowed", "evidence": "e", "handoff": "h"}
            terminal = runtime.done(packet["state_file"], packet["done_argv"][-1].split("=", 1)[1], report)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(set(terminal), set(loops._PACKET_KEYS))


class NoSizeCapTests(unittest.TestCase):
    def test_a_huge_request_many_checks_and_a_huge_report_are_accepted(self):
        checks = [{"id": f"C{i}", "clause": "c" * 3000, "command": "true"} for i in range(80)]
        with tempfile.TemporaryDirectory() as workspace:
            packet = start(workspace, exit_checks=checks,
                           context={"request": "x" * 400_000, "scope": "s", "authority": "a",
                                    "environment": "e", "resources": []})
            self.assertEqual(packet["status"], "active")
            self.assertNotIn("MAX_STATE_BYTES", SCRIPT.read_text())

    def test_the_card_states_there_is_no_limit(self):
        self.assertIn("no size limit", (RUNTIME_DIR / "ADAPTER.md").read_text())


class HookVisibilityTests(unittest.TestCase):
    def test_the_runtime_never_executes_a_check(self):
        source = SCRIPT.read_text()
        self.assertNotIn("_run_checks", source)          # 0.8.0's runtime-run checks were removed for hooks
        self.assertNotIn('check["command"]], cwd', source)  # no subprocess is built from a check command

    def test_the_packet_hands_the_script_to_the_executor(self):
        with tempfile.TemporaryDirectory() as workspace:
            packet = start(workspace, exit_checks=[{"id": "A", "clause": "c", "command": "true"}])
        self.assertIn("record --state", packet["verify_script"])
        self.assertTrue(packet["verify_script"].startswith("/bin/sh <<'"))


class LeanReturnTests(unittest.TestCase):
    """A run started with --receipt prints lean returns from start and done; the receipt keeps the full packet and next
    prints it whole (skill-craft adaptation U21, recorded in PROVENANCE.json).

    The fixture is live-shaped: ShipLoop's own step-plan loop contract at a 163-character run directory (the live
    path length) and an 8 KB report.  Before the change this fixture printed start 11,515, a non-terminal done 22,709
    and a terminal done 13,447 characters (live: 13,098 at step-plan, 19 to 22 KB per non-terminal done, 6,984 terminal).
    """

    REPORT = {"classification": "non-trivial", "exit_assessment": "unsatisfied", "continuation_assessment": "allowed",
              "evidence": "E" * 3000, "handoff": "H" * 5000}

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="until-loop-lean-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.root = base / ("r" * max(1, 163 - len(str(base)) - 1))
        (self.root / "loops").mkdir(parents=True)
        self.assertEqual(len(str(self.root)), 163)
        state = {"repo": str(self.repo), "prompt": "Fix the defect so the parser round-trips its input. " * 40,
                 "run_id": "run-abc123", "stage": "inner-loop", "work_index": 0, "improve_skill": "",
                 "delegation": "inline", "work_items": [{"id": "W1", "title": "Fix the parser"}],
                 "inner_loops": {"W1": {"stage": "step-plan", "action": {"id": "A-step-plan"}}},
                 "history": [], "accepted": {}}
        self.contract = loops.contract_writes(self.root, state)[loops.contract_path("A-step-plan")]
        self.receipt = loops.receipt_path(self.root, "A-step-plan")

    def cli(self, *args: str, stdin: str = "") -> str:
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], input=stdin, text=True,
                              capture_output=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        return done.stdout

    def assert_lean(self, printed: dict, full: dict) -> None:
        self.assertEqual(set(printed), set(runtime.PRINTED_KEYS))
        self.assertEqual(set(full), set(loops._PACKET_KEYS), "the receipt keeps the full packet")
        for key in ("status", "state_file", "receipt", "next_argv", "done_argv", "verify_script"):
            self.assertEqual(printed[key], full[key], key)
        self.assertEqual(printed["conditions"], {"exit": full["conditions"]["exit"]})
        for absent in ("work", "context", "last_report", "status_semantics"):
            self.assertNotIn(absent, printed)

    def test_start_and_done_print_lean_returns_within_their_bounds_and_the_receipt_keeps_the_full_packet(self):
        raw = self.cli("start", "--receipt", str(self.receipt), stdin=self.contract)
        started = json.loads(raw)
        self.assert_lean(started, json.loads(self.receipt.read_text()))
        self.assertLessEqual(len(raw), 4096, "start return")
        self.assertIn("read it first on a fresh or compacted context", started["instruction"])
        self.assertIn(str(self.receipt), raw)

        raw = self.cli(*started["done_argv"][2:], stdin=json.dumps(self.REPORT))
        active = json.loads(raw)
        self.assertEqual(active["status"], "active")
        self.assert_lean(active, json.loads(self.receipt.read_text()))
        self.assertLessEqual(len(raw), 3072, "non-terminal done return")
        self.assertIn("Address and recheck the material observations", active["instruction"])

        cold = json.loads(self.cli(*active["next_argv"][2:]))
        self.assertEqual(cold, json.loads(self.receipt.read_text()), "next prints the full packet for recovery")

        raw = self.cli(*active["done_argv"][2:], stdin=json.dumps(
            dict(self.REPORT, classification="trivial", exit_assessment="satisfied")))
        terminal = json.loads(raw)
        self.assertEqual(terminal["status"], "complete")
        full = json.loads(self.receipt.read_text())
        self.assert_lean(terminal, full)
        self.assertLessEqual(len(raw), 4096, "terminal done return")
        self.assertIsNone(terminal["done_argv"])
        self.assertEqual(full["last_report"]["handoff"], "H" * 5000, "the final report stays in the receipt")

    def test_the_printed_report_fields_are_the_schema_fields_and_values(self):
        for has_checks in (False, True):
            schema = runtime._report_schema(has_checks)
            fields = runtime._report_fields(has_checks)
            self.assertEqual(set(fields), set(schema["properties"]))
            for name, prop in schema["properties"].items():
                if "enum" in prop:
                    self.assertEqual(fields[name].split("|"), prop["enum"], name)

    def test_a_run_without_a_receipt_prints_the_full_packet(self):
        """Without a receipt the printed packet is the only durable copy of the result, so it stays whole."""
        with tempfile.TemporaryDirectory() as workspace:
            contract = {"workspace": workspace, "work": "w", "exit_condition": "e", "repeat_condition": "r",
                        "context": {"request": "q", "scope": "s", "authority": "a", "environment": "e",
                                    "resources": []}}
            started = json.loads(self.cli("start", stdin=json.dumps(contract)))
            self.assertEqual(set(started), set(loops._PACKET_KEYS))
            terminal = json.loads(self.cli(*started["done_argv"][2:], stdin=json.dumps(
                dict(self.REPORT, exit_assessment="satisfied"))))
            self.assertEqual(terminal["status"], "complete")
            self.assertEqual(set(terminal), set(loops._PACKET_KEYS))


if __name__ == "__main__":
    unittest.main()
