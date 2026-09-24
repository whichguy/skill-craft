#!/usr/bin/env python3
"""Contract tests for the read-only standalone Improve import bridge."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
IMPROVE = ROOT / "skills" / "improve" / "SKILL.md"
LEGACY_RUNTIME = ROOT / "skills" / "improve" / "runtime" / "until-loop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402


class StandaloneImproveBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-standalone-improve-")
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.state = {"run_id": "run01", "repo": str(self.workspace)}
        self.parent = "nav-test"
        self.skill = self._legacy_skill()
        self.binding = bridge.binding(self.state, self.parent, "implement", {}, self.skill)
        self.ephemeral_skill = bridge.resolve_skill(str(IMPROVE))
        self.ephemeral_binding = bridge.binding(
            self.state, self.parent, "implement", {}, self.ephemeral_skill,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _legacy_skill(self) -> dict[str, str]:
        """Create an explicit selected legacy card, independent of the default package."""
        root = self.workspace / "legacy-improve"
        runtime = root / "runtime" / "until-loop"
        scripts = runtime / "scripts"
        scripts.mkdir(parents=True)
        (root / "SKILL.md").write_text(
            "---\nname: improve\nversion: test-legacy\n---\nUse the bundled until-loop adapter.\n",
            encoding="utf-8",
        )
        (runtime / "ADAPTER.md").write_text(
            "---\nname: until-loop\nversion: test-legacy\n---\nUse the durable v2 adapter.\n",
            encoding="utf-8",
        )
        for name in ("until-loop", "until_loop_packet.py", "until_loop_v2.py"):
            shutil.copy2(LEGACY_RUNTIME / name, scripts / name)
        shutil.copytree(LEGACY_RUNTIME.parent / "references", runtime / "references")
        return bridge.resolve_skill(str(root / "SKILL.md"))

    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", self.skill["runtime_cli"], *args], text=True,
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

    def ephemeral_start(self, *, required_reviews: int = 2,
                        marker: str | None = None) -> tuple[dict[str, object], str]:
        contract = {
            "workspace": str(self.workspace),
            "work": "Perform one complete Improve review and applicable checks.",
            "exit_condition": "Two qualifying trivial reviews and current evidence establish completion.",
            "repeat_condition": "Continue while an authorized improvement or evidence gap remains.",
            "required_trivial_reviews": required_reviews,
            "context": {
                "request": "Improve this ShipLoop action.\n" + (
                    marker if marker is not None else self.ephemeral_binding["contract_marker"]
                ),
                "scope": "Only the ShipLoop action's candidate and listed evidence files.",
                "authority": "Do not commit, merge, push, or broaden the parent scope.",
                "environment": "Python is available; checks are recorded in check.md.",
                "resources": [{
                    "purpose": "selected Improve card",
                    "locator": self.ephemeral_skill["skill_card"],
                }],
            },
        }
        completed = subprocess.run(
            [sys.executable, "-B", self.ephemeral_skill["runtime_cli"], "start"],
            input=json.dumps(contract), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout), completed.stdout

    def ephemeral_done(self, packet: dict[str, object], report: dict[str, str]) -> tuple[dict[str, object], str]:
        argv = packet["done_argv"]
        self.assertIsInstance(argv, list)
        completed = subprocess.run(
            argv, input=json.dumps(report), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout), completed.stdout

    def terminal_ephemeral(self, *, required_reviews: int = 2) -> tuple[dict[str, object], str]:
        packet, _raw = self.ephemeral_start(required_reviews=required_reviews)
        for index in range(required_reviews):
            packet, raw = self.ephemeral_done(packet, {
                "classification": "trivial",
                "exit_assessment": "satisfied" if index == required_reviews - 1 else "unsatisfied",
                "continuation_assessment": "allowed",
                "evidence": f"distinct qualifying review {index + 1} found no material issue",
                "handoff": (
                    "Objective and scope remain unchanged; review " + str(index + 1)
                    + " found no material issue; check.md is the current check record."
                ),
            })
        self.assertEqual(packet["status"], "complete")
        self.assertFalse(Path(packet["state_file"]).exists(), "terminal runtime state must be deleted")
        return packet, raw

    def save_terminal_packet(self, raw: str) -> Path:
        path = bridge.receipt_path(self.ephemeral_binding)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw, encoding="utf-8")
        return path

    def write_evidence(self) -> None:
        for name in ("review-a.md", "review-b.md", "check.md"):
            (self.workspace / name).write_text(name, encoding="utf-8")

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

    def test_selected_package_runs_real_ephemeral_runtime_and_archives_terminal_packet(self) -> None:
        self.assertEqual(Path(self.ephemeral_skill["runtime_cli"]).name, "until_loop_ephemeral.py")
        packet, raw = self.terminal_ephemeral()
        self.write_evidence()
        packet_path = self.save_terminal_packet(raw)
        self.assertEqual(
            packet_path,
            self.workspace / ".shiploop-improve" / "run01" / "nav-test" / "packet.json",
        )
        record, writes = bridge.complete(self.ephemeral_binding, self.receipt())
        self.assertEqual(record["runtime_phase"], "complete")
        self.assertEqual(record["binding_id"], "run01/nav-test")
        self.assertIn("improve/nav-test/terminal.json", writes)
        self.assertEqual(writes["improve/nav-test/terminal.json"], raw)
        self.assertFalse(any(path.endswith("state.json") for path in writes))
        self.assertEqual(record["identities"]["terminal_packet_sha256"], hashlib.sha256(raw.encode()).hexdigest())
        # Import is a pure reader; duplicate protection remains ShipLoop's
        # existing ledger/transaction responsibility rather than a second
        # bridge-owned state machine.
        self.assertEqual((record, writes), bridge.complete(self.ephemeral_binding, self.receipt()))
        self.assertEqual(packet["last_report"]["classification"], "trivial")

    def test_created_plans_wait_for_two_reviews_after_material_repair(self) -> None:
        """Real callback/import mechanics; review judgments are synthetic, not LLM quality evidence."""
        for stage, successor in (("plan", "prepare"), ("step-plan", "test-spec")):
            with self.subTest(stage=stage):
                state = navigator.new_state(
                    str(self.workspace), "Create and review initial steps.", protocol_version=3,
                )
                # Only preceding stages use synthetic receipts to reach the boundary.
                while navigator.current_stage(state) != stage:
                    action = navigator.current_action(state)
                    result = {"outcome": "done", "summary": "Synthetic prerequisite."}
                    state = navigator.apply(state, action["id"], result)
                    if state.get("active_improve") is not None:
                        state = navigator.finish_improve(state, action["id"], self.receipt())

                action = dict(navigator.current_action(state))
                plan_path = self.workspace / f"{stage}-plan.md"
                plan_path.write_text("Draft: implement feature; prerequisite missing.\n", encoding="utf-8")
                seed = {
                    "outcome": "done", "summary": "Initial steps created; review pending.",
                    "evidence_refs": [plan_path.name],
                }
                if stage == "plan":
                    seed["work_items"] = [{"id": "DRAFT", "title": "Unreviewed feature"}]
                waiting = navigator.apply(state, action["id"], seed)
                self.ephemeral_binding = bridge.binding(
                    waiting, action["id"], stage, seed, self.ephemeral_skill,
                )
                waiting["active_improve"] = self.ephemeral_binding
                navigator.validate(waiting)
                before = copy.deepcopy(waiting)
                packet, raw = self.ephemeral_start()
                self.addCleanup(Path(packet["state_file"]).unlink, missing_ok=True)
                self.write_evidence()

                # An early clean review cannot survive an intervening material repair.
                sequence = (("trivial", 1), ("non-trivial", 0), ("trivial", 1), ("trivial", 2))
                for index, (classification, streak) in enumerate(sequence):
                    if classification == "non-trivial":
                        plan_path.write_text(
                            "Revised: create prerequisite, then implement feature, then verify.\n",
                            encoding="utf-8",
                        )
                    packet, raw = self.ephemeral_done(packet, {
                        "classification": classification,
                        # Even a declared pass cannot bypass the consecutive-review gate.
                        "exit_assessment": "satisfied" if classification == "trivial" else "unsatisfied",
                        "continuation_assessment": "allowed",
                        "evidence": f"Synthetic review {index + 1} of {plan_path.name}: {classification}.",
                        "handoff": "Retain planning-only scope and review the current plan again if pending.",
                    })
                    self.assertEqual(packet["progress"]["trivial_streak"], streak)
                    self.save_terminal_packet(raw)
                    if index < 3:
                        self.assertEqual(packet["status"], "active")
                        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not complete"):
                            bridge.complete(self.ephemeral_binding, self.receipt())
                        self.assertEqual(navigator.apply(waiting, action["id"], seed), before)
                        self.assertEqual(waiting, before)
                        self.assertEqual(navigator.current_stage(waiting), stage)
                        self.assertEqual(navigator.current_action(waiting), action)
                        self.assertEqual(waiting["work_items"], state["work_items"])
                        self.assertNotIn(action["id"], waiting["accepted"])

                self.assertEqual(packet["status"], "complete")
                self.assertFalse(Path(packet["state_file"]).exists())
                final_result = copy.deepcopy(seed)
                final_result["summary"] = "Reviewed steps include the missing prerequisite."
                if stage == "plan":
                    final_result["work_items"] = [
                        {"id": "SETUP", "title": "Create prerequisite"},
                        {"id": "FEATURE", "title": "Implement and verify feature"},
                    ]
                receipt = dict(self.receipt(), final_result=final_result)
                record, archives = bridge.complete(self.ephemeral_binding, receipt)
                self.assertEqual(archives[f"improve/{action['id']}/terminal.json"], raw)
                advanced = navigator.finish_improve(
                    waiting, action["id"], record, record["receipt"]["final_result"],
                )
                self.assertEqual(navigator.current_stage(advanced), successor)
                self.assertIsNone(advanced["active_improve"])
                self.assertEqual(advanced["accepted"][action["id"]], final_result)
                if stage == "plan":
                    self.assertEqual(advanced["work_items"], final_result["work_items"])
                self.assertEqual(
                    navigator.finish_improve(advanced, action["id"], record, final_result), advanced,
                    "completion replay must not advance another stage",
                )

    def test_ephemeral_bindings_are_independent_of_durable_state_and_each_other(self) -> None:
        # An unrelated durable child still blocks a legacy binding, but a
        # selected ephemeral runtime has a private tempfile and no ambient
        # .until-loop ownership relationship.
        self.initialize(marker="ShipLoop standalone Improve binding: foreign/action")
        first = bridge.binding(self.state, self.parent, "implement", {}, self.ephemeral_skill)
        second = bridge.binding(
            {"run_id": "run02", "repo": str(self.workspace)}, "nav-other", "document", {},
            self.ephemeral_skill,
        )
        self.assertEqual(first["binding_id"], "run01/nav-test")
        self.assertEqual(second["binding_id"], "run02/nav-other")
        self.assertNotEqual(bridge.receipt_path(first), bridge.receipt_path(second))
        self.assertEqual(
            bridge.receipt_path(second),
            self.workspace / ".shiploop-improve" / "run02" / "nav-other" / "packet.json",
        )

    def test_ephemeral_terminal_requires_two_review_minimum_even_when_runtime_gate_is_one(self) -> None:
        packet, raw = self.terminal_ephemeral(required_reviews=1)
        self.assertEqual(packet["progress"]["required_trivial_reviews"], 1)
        self.write_evidence()
        self.save_terminal_packet(raw)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "two-review minimum"):
            bridge.complete(self.ephemeral_binding, self.receipt())

    def test_ephemeral_terminal_rejects_wrong_status_context_and_progress(self) -> None:
        packet, raw = self.terminal_ephemeral()
        self.write_evidence()
        path = self.save_terminal_packet(raw)

        bad_status = copy.deepcopy(packet)
        bad_status["status"] = "stopped"
        path.write_text(json.dumps(bad_status), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not complete"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        active = copy.deepcopy(packet)
        active["status"] = "active"
        path.write_text(json.dumps(active), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not complete"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        bad_context = copy.deepcopy(packet)
        bad_context["context"]["request"] = "Improve this action.\nShipLoop standalone Improve binding: foreign/action"
        path.write_text(json.dumps(bad_context), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "not bound"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        bad_counter = copy.deepcopy(packet)
        bad_counter["progress"]["trivial_streak"] = True
        path.write_text(json.dumps(bad_counter), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "integer"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        incoherent = copy.deepcopy(packet)
        incoherent["progress"]["trivial_streak"] = incoherent["progress"]["action_number"] + 1
        path.write_text(json.dumps(incoherent), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "incoherent"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        malformed = copy.deepcopy(packet)
        malformed.pop("last_report")
        path.write_text(json.dumps(malformed), encoding="utf-8")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "unsupported schema"):
            bridge.complete(self.ephemeral_binding, self.receipt())

    def test_ephemeral_terminal_receipt_is_required_and_never_follows_a_link(self) -> None:
        packet, raw = self.terminal_ephemeral()
        self.write_evidence()
        # The runtime's deleted tempfile is not evidence of completion.  A
        # host that lost the terminal stdout packet leaves the parent blocked.
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "unavailable"):
            bridge.complete(self.ephemeral_binding, self.receipt())

        path = self.save_terminal_packet(raw)
        copied = self.workspace / "outside-packet.json"
        copied.write_text(raw, encoding="utf-8")
        path.unlink()
        path.symlink_to(copied.name)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "cannot be a symlink"):
            bridge.complete(self.ephemeral_binding, self.receipt())

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
