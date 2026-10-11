#!/usr/bin/env python3
"""Narrow checks on the vendored Until Loop: each one fails for exactly one kind of drift, and none pins a release.

1. Provenance: the manifest's hashes match the shipped files and its version matches the adapter card.
2. Marketplace pin: catalog/external-plugins.json points at the commit and version the manifest vendors.
3. Packet contract: every key the runtime prints is a key ShipLoop accepts (and the reverse), so a runtime change
   that adds a packet field cannot silently break ShipLoop's terminal-packet checks.
4. No size cap: the runtime accepts a very long request, many exit checks and a very long report (owner, 2026-10-11).
5. Hook visibility: exit checks run only through the executor's own shell script, never inside the runtime.
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


if __name__ == "__main__":
    unittest.main()
