#!/usr/bin/env python3
"""Contract tests for the read-only standalone Improve import bridge."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
IMPROVE = ROOT / "skills" / "improve" / "SKILL.md"
UNTIL = ROOT / "skills" / "improve" / "runtime" / "until-loop" / "scripts" / "until-loop"
sys.path.insert(0, str(SCRIPTS))
import shiploop_standalone_improve as bridge  # noqa: E402


class StandaloneImproveBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-standalone-improve-")
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.state = {"run_id": "run01", "repo": str(self.workspace)}
        self.skill = bridge.resolve_skill(str(IMPROVE))
        self.parent = "nav-test"
        self.binding = bridge.binding(self.state, self.parent, "implement", {}, self.skill)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(UNTIL), *args], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def initialize(self, *, marker: str | None = None, verify: bool = False) -> None:
        request = "Improve this action.\n" + (marker if marker is not None else self.binding["contract_marker"])
        contract = {
            "version": 1,
            "policy": "decision-rubric/2",
            "original_request": request,
            "interpretation": "Review the action until the recorded criterion has evidence.",
            "criteria": [{"id": "C1", "text": "Record review evidence", "basis": {"kind": "request", "reference": "review"}}],
        }
        path = self.workspace / "contract.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        args = ["v2", "init", "--repo", str(self.workspace), "--contract-file", str(path)]
        if verify:
            args.extend(["--verify", f"{sys.executable} -c 'pass'"])
        result = self.command(*args)
        self.assertEqual(result.returncode, 0, result.stderr)

    def finish(self) -> None:
        state_path = self.workspace / ".until-loop" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        action = state["action"]
        result = {
            "action_id": action["id"],
            "contract_revision": state["contract"]["revision"],
            "decision": "complete",
            "criteria": [{"id": "C1", "status": "satisfied", "evidence": "review-a.md and review-b.md"}],
            "next_action": None,
            "blocker": None,
        }
        Path(action["result_path"]).write_text(json.dumps(result), encoding="utf-8")
        done = self.command("v2", "submit", "--repo", str(self.workspace), "--action-id", action["id"])
        self.assertEqual(done.returncode, 0, done.stderr)
        run = self.workspace / ".until-loop"
        (run / "working.md").write_text("two review passes\n", encoding="utf-8")
        for name in ("review-a.md", "review-b.md", "check.md"):
            (self.workspace / name).write_text(name, encoding="utf-8")

    def receipt(self) -> dict[str, object]:
        return {
            "summary": "The actual Improve child completed.",
            "review_refs": ["review-a.md", "review-b.md"],
            "check_refs": ["check.md"],
            "lessons": "Keep the focused test before implementation.",
        }

    def test_real_v2_completion_imports_read_only_archives(self) -> None:
        self.assertNotEqual(self.skill["skill_version"], "unversioned")
        self.assertNotEqual(self.skill["runtime_version"], "unversioned")
        self.initialize(verify=True)
        self.finish()
        record, writes = bridge.complete(self.binding, self.receipt())
        self.assertEqual(record["runtime_phase"], "done")
        self.assertEqual(record["binding_id"], "run01/nav-test")
        self.assertIn("improve/nav-test/state.json", writes)
        self.assertIn("improve/nav-test/working.md", writes)
        self.assertIn("improve/nav-test/history.jsonl", writes)
        self.assertIn("improve/nav-test/result.json", writes)
        self.assertIn("improve/nav-test/receipt.md", writes)
        evidence = record["evidence"]
        self.assertEqual(len(evidence), 3)
        for item in evidence:
            self.assertEqual(writes[item["archive"]], (self.workspace / item["source"]).read_text(encoding="utf-8"))

    def test_selected_symlink_uses_documented_installed_layout_without_home_path(self) -> None:
        runtime_root = self.workspace / "runtime-root"
        installed = runtime_root / "examples" / "improve"
        installed.mkdir(parents=True)
        (runtime_root / "scripts").mkdir()
        card = installed / "SKILL.md"
        card.write_text(
            "---\nname: improve\n---\nRead ../../SKILL.md and use until-loop.\n",
            encoding="utf-8",
        )
        (runtime_root / "SKILL.md").write_text("---\nname: until-loop\n---\n", encoding="utf-8")
        cli = runtime_root / "scripts" / "until-loop"
        cli.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        selected = self.workspace / "selected-improve.md"
        selected.symlink_to(card)
        resolved = bridge.resolve_skill(str(selected))
        self.assertEqual(resolved["skill_card"], str(card.resolve()))
        self.assertEqual(resolved["runtime_card"], str((runtime_root / "SKILL.md").resolve()))
        self.assertEqual(resolved["runtime_cli"], str(cli.resolve()))
        self.assertEqual(resolved["skill_version"], "unversioned")
        self.assertEqual(resolved["runtime_version"], "unversioned")

    def test_nonterminal_or_foreign_child_does_not_release_parent(self) -> None:
        self.initialize(marker="ShipLoop standalone Improve binding: foreign/action")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not bound"):
            bridge.binding(self.state, self.parent, "implement", {}, self.skill)

    def test_matching_nonterminal_child_does_not_release_parent(self) -> None:
        self.initialize()
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not completed"):
            bridge.complete(self.binding, self.receipt())

    def test_pending_or_unsafe_state_needs_runtime_recovery(self) -> None:
        self.initialize()
        pending = self.workspace / ".until-loop" / ".pending-v2.json"
        pending.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "pending journal"):
            bridge.complete(self.binding, self.receipt())

    def test_terminal_runtime_result_must_match_the_accepted_assessment(self) -> None:
        self.initialize()
        self.finish()
        state = json.loads((self.workspace / ".until-loop" / "state.json").read_text(encoding="utf-8"))
        result = self.workspace / ".until-loop" / "results" / (state["last_assessment"]["action_id"] + ".json")
        result.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "does not match"):
            bridge.complete(self.binding, self.receipt())

    def test_parent_lexical_workspace_locator_survives_physical_runtime_resolution(self) -> None:
        alias = Path(self.temp.name) / "workspace-alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        self.state["repo"] = str(alias)
        self.binding = bridge.binding(self.state, self.parent, "implement", {}, self.skill)
        self.assertEqual(self.binding["workspace"], str(alias))
        # Until Loop records the physical path, while the parent stores the
        # alias.  Import resolves the alias for validation without changing
        # the stored parent locator.
        self.initialize()
        self.finish()
        receipt = self.receipt()
        receipt["review_refs"] = [str(alias / "review-a.md"), str(alias / "review-b.md")]
        receipt["check_refs"] = [str(alias / "check.md")]
        record, _writes = bridge.complete(self.binding, receipt)
        self.assertEqual(record["workspace"], str(self.workspace.resolve()))

    def test_symlinked_runtime_state_and_tampered_terminal_history_are_rejected(self) -> None:
        self.initialize()
        self.finish()
        run = self.workspace / ".until-loop"
        history = run / "history.jsonl"
        rows = history.read_text(encoding="utf-8").splitlines()
        payload = json.loads(rows[-1])
        payload["state_digest"] = "0" * 64
        history.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "terminal history"):
            bridge.complete(self.binding, self.receipt())
        # A runtime state must remain a real single-link file, even if its
        # target itself is otherwise a valid completion record.
        state = run / "state.json"
        saved = run / "saved-state.json"
        state.replace(saved)
        state.symlink_to(saved.name)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "cannot be a symlink"):
            bridge.complete(self.binding, self.receipt())

    def test_sequential_settled_child_allows_new_binding_and_unsafe_receipt_fails(self) -> None:
        self.initialize()
        self.finish()
        imported, _writes = bridge.complete(self.binding, self.receipt())
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "was not imported"):
            bridge.binding(self.state, "nav-next", "document", {}, self.skill)
        self.state["improve_results"] = {self.parent: imported}
        second = bridge.binding(self.state, "nav-next", "document", {}, self.skill)
        self.assertEqual(second["binding_id"], "run01/nav-next")
        bad = self.receipt()
        bad["review_refs"] = ["review-a.md", "review-a.md"]
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "distinct"):
            bridge.complete(self.binding, bad)


if __name__ == "__main__":
    unittest.main()
