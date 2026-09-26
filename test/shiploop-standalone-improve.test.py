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
sys.path.insert(0, str(SCRIPTS))
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402



def _receipt(binding):
    """The child receipt path ShipLoop prints; the runtime writes every packet there itself."""
    path = bridge.receipt_path(binding)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class StandaloneImproveBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-standalone-improve-")
        self.workspace = Path(self.temp.name) / "workspace"
        self.workspace.mkdir()
        self.state = {"run_id": "run01", "repo": str(self.workspace)}
        self.parent = "nav-test"
        self.ephemeral_skill = bridge.resolve_skill(str(IMPROVE))
        self.ephemeral_binding = bridge.binding(
            self.state, self.parent, "implement", {}, self.ephemeral_skill,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

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
            [sys.executable, "-B", self.ephemeral_skill["runtime_cli"], "start", "--receipt", str(_receipt(self.ephemeral_binding))],
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

    def test_an_unchanged_first_pass_imports_with_its_one_review(self) -> None:
        for args in (("init", "-q"), ("config", "user.email", "s@example.invalid"), ("config", "user.name", "S")):
            subprocess.run(["git", "-C", str(self.workspace), *args], check=True, capture_output=True)
        (self.workspace / "candidate.py").write_text("x = 1\n")
        subprocess.run(["git", "-C", str(self.workspace), "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.workspace), "commit", "-qm", "base"], check=True, capture_output=True)
        packet, _raw = self.ephemeral_start()
        packet, raw = self.ephemeral_done(packet, {
            "classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "allowed",
            "evidence": "One full review found nothing worth changing.", "handoff": "Nothing remains."})
        self.assertEqual(packet["status"], "complete")
        self.assertTrue(packet["progress"]["unchanged_first_pass"])
        self.save_terminal_packet(raw)
        self.write_evidence()
        one = dict(self.receipt(), review_refs=["review-a.md"])
        record, _writes = bridge.complete(self.ephemeral_binding, one)
        self.assertEqual(record["runtime_phase"], "complete")
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "ended on one unchanged trivial pass"):
            bridge.complete(self.ephemeral_binding, self.receipt())

    def test_created_plans_wait_for_two_reviews_after_material_repair(self) -> None:
        """Real callback/import mechanics; review judgments are synthetic, not LLM quality evidence."""
        for stage, successor in (("plan", "prepare"), ("step-plan", "test-spec")):
            with self.subTest(stage=stage):
                state = navigator.new_state(
                    str(self.workspace), "Create and review initial steps.",
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

    def test_ephemeral_bindings_are_independent_of_workspace_state_and_each_other(self) -> None:
        # A selected ephemeral runtime has a private tempfile and no ambient
        # workspace ownership relationship, even when an external Until Loop
        # installation left a .until-loop directory behind.
        stray = self.workspace / ".until-loop"
        stray.mkdir()
        (stray / "state.json").write_text("{}", encoding="utf-8")
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

    def test_ephemeral_terminal_receipt_survives_lost_stdout_and_never_follows_a_link(self) -> None:
        packet, raw = self.terminal_ephemeral()
        self.write_evidence()
        # The child started with --receipt: the runtime wrote the terminal packet
        # before deleting its state, so a host that lost stdout still has it.
        path = bridge.receipt_path(self.ephemeral_binding)
        self.assertFalse(Path(packet["state_file"]).exists())
        self.assertEqual(path.read_text(encoding="utf-8"), raw)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["receipt"], str(path))

        copied = self.workspace / "outside-packet.json"
        copied.write_text(raw, encoding="utf-8")
        path.unlink()
        path.symlink_to(copied.name)
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "cannot be a symlink"):
            bridge.complete(self.ephemeral_binding, self.receipt())

    def _improve_copy(self) -> Path:
        copied = self.workspace / "improve-copy"
        shutil.copytree(IMPROVE.parent, copied)
        return copied

    def test_selected_symlink_uses_documented_installed_layout_without_home_path(self) -> None:
        copied = self._improve_copy()
        selected = self.workspace / "selected-improve.md"
        selected.symlink_to(copied / "SKILL.md")
        resolved = bridge.resolve_skill(str(selected))
        runtime = copied / "runtime" / "until-loop"
        self.assertEqual(resolved["skill_card"], str((copied / "SKILL.md").resolve()))
        self.assertEqual(resolved["runtime_card"], str((runtime / "ADAPTER.md").resolve()))
        self.assertEqual(resolved["runtime_cli"],
                         str((runtime / "scripts" / "until_loop_ephemeral.py").resolve()))
        self.assertEqual(resolved["skill_version"], self.ephemeral_skill["skill_version"])
        self.assertEqual(resolved["runtime_version"], self.ephemeral_skill["runtime_version"])

    def test_non_ephemeral_or_example_layout_card_is_refused(self) -> None:
        refusal = "durable Until Loop runtimes are no longer supported; select the current Improve card"
        # A package whose adapter does not declare the ephemeral runtime.
        durable = self._improve_copy()
        adapter = durable / "runtime" / "until-loop" / "ADAPTER.md"
        adapter.write_text(
            "---\nname: until-loop\nversion: test-durable\n---\nUse scripts/until-loop v2.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(bridge.StandaloneImproveError, refusal):
            bridge.resolve_skill(str(durable / "SKILL.md"))
        # The pre-package example layout whose parent card is ../../SKILL.md.
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
        (runtime_root / "scripts" / "until_loop_ephemeral.py").write_text(
            "#!/usr/bin/env python3\n", encoding="utf-8",
        )
        with self.assertRaisesRegex(bridge.StandaloneImproveError, refusal):
            bridge.resolve_skill(str(card))
        # A saved binding that names a durable CLI cannot be completed.
        stale = copy.deepcopy(self.ephemeral_binding)
        stale["skill"]["runtime_cli"] = str(Path(stale["skill"]["runtime_cli"]).with_name("until-loop"))
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "differs from selected card"):
            bridge.complete(stale, self.receipt())

    def test_parent_lexical_workspace_locator_survives_physical_runtime_resolution(self) -> None:
        alias = Path(self.temp.name) / "workspace-alias"
        alias.symlink_to(self.workspace, target_is_directory=True)
        self.state["repo"] = str(alias)
        self.ephemeral_binding = bridge.binding(
            self.state, self.parent, "implement", {}, self.ephemeral_skill,
        )
        self.assertEqual(self.ephemeral_binding["workspace"], str(alias))
        # The runtime records the physical path, while the parent stores the
        # alias.  Import resolves the alias for validation without changing
        # the stored parent locator.
        _packet, raw = self.terminal_ephemeral()
        self.write_evidence()
        packet_path = self.save_terminal_packet(raw)
        self.assertEqual(packet_path.parent.parent.parent.parent, alias)
        receipt = self.receipt()
        receipt["review_refs"] = [str(alias / "review-a.md"), str(alias / "review-b.md")]
        receipt["check_refs"] = [str(alias / "check.md")]
        record, _writes = bridge.complete(self.ephemeral_binding, receipt)
        self.assertEqual(record["workspace"], str(self.workspace.resolve()))
        bad = self.receipt()
        bad["review_refs"] = ["review-a.md", "review-a.md"]
        with self.assertRaisesRegex(bridge.StandaloneImproveError, "distinct"):
            bridge.complete(self.ephemeral_binding, bad)


if __name__ == "__main__":
    unittest.main()
