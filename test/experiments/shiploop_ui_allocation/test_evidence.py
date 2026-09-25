from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[2] / "skills" / "shiploop"
SPEC = importlib.util.spec_from_file_location("ui_allocation_evidence", HERE / "evidence.py")
evidence = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def test_selected_navigator_import_restores_module_cache(self) -> None:
        names = ("shiploop_navigator", "shiploop_navigator_v3_prompts", "shiploop_consumer_delivery", "shiploop_planning_revision", "shiploop_privacy", "shiploop_store")
        before = {name: sys.modules.get(name) for name in names}
        navigator = evidence._load_navigator(PACKAGE)
        self.assertEqual(Path(navigator.__file__).resolve(), PACKAGE / "scripts" / "shiploop_navigator.py")
        self.assertEqual({name: sys.modules.get(name) for name in names}, before)

    def write_state(self, root: Path, imports: dict | None = None) -> Path:
        store = evidence._load_store(PACKAGE)
        navigator = evidence._load_navigator(PACKAGE)
        state = navigator.new_state(str(root), "Synthetic navigator fixture")
        self.import_action = None
        self.import_binding = None
        if imports:
            # Improve records exist only at checkpoint stages; reach spec first.
            while navigator.current_stage(state) != "spec":
                state = navigator.apply(state, navigator.current_action(state)["id"], {
                    "outcome": "done", "summary": "Synthetic accepted producer result.", "evidence_refs": [],
                })
            action = state["action"]["id"]
            record = next(iter(imports.values()))
            if record.get("kind") != "synthetic-fixture-predecessor":
                record["binding_id"] = state["run_id"] + "/" + action
                self.import_binding = record["binding_id"]
            state = navigator._apply_result(state, action, {
                "outcome": "done", "summary": "Synthetic accepted producer result.", "evidence_refs": [],
            }, improve_record=record)
            self.import_action = action
        store.write_record(root / "run" / "state.md", state, "synthetic fixture state")
        return root

    def imported_record(self) -> dict:
        return {"binding_id": "", "runtime_phase": "complete",
                "identities": {}, "receipt": {"review_refs": ["a", "b"], "check_refs": ["c"]}}

    def write_terminal(self, root: Path, *, status: str = "complete", marker: bool = True) -> None:
        marker_text = f"ShipLoop standalone Improve binding: {self.import_binding}"
        request = f"fixture request\n{marker_text}" if marker else "fixture request"
        terminal = {"status": status, "progress": {"action_number": 2, "trivial_streak": 2, "required_trivial_reviews": 2}, "context": {"request": request}}
        path = root / "run" / "improve" / self.import_action / "terminal.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(terminal), encoding="utf-8")

    def seal(self, root: Path, record: dict, *, evidence_file: bool = False) -> None:
        terminal = root / "run" / "improve" / self.import_action / "terminal.json"
        record["identities"] = {"terminal_packet_sha256": hashlib.sha256(terminal.read_bytes()).hexdigest()}
        if evidence_file:
            archive = root / "run" / "improve" / self.import_action / "evidence" / "01-review.md"
            archive.parent.mkdir(parents=True)
            archive.write_text("synthetic archived review\n", encoding="utf-8")
            record["evidence"] = [{"source": "reviews/review.md", "archive": f"improve/{self.import_action}/evidence/01-review.md", "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}]

    def persist_record(self, root: Path, record: dict) -> None:
        store = evidence._load_store(PACKAGE)
        state = store.read_record(root / "run" / "state.md")
        state["improve_results"][self.import_action] = record
        store.write_record(root / "run" / "state.md", state)

    def test_missing_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = evidence.inspect_case(temp, PACKAGE)
        self.assertFalse(report["structurally_valid"])
        self.assertEqual(report["kind"], "missing-state")

    def test_no_import_is_reported_without_claiming_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.write_state(Path(temp))
            report = evidence.inspect_case(root, PACKAGE)
        self.assertTrue(report["structurally_valid"])
        self.assertFalse(report["semantic_verification"])
        self.assertEqual(report["import_status"], "no-import-yet")
        self.assertEqual(report["accepted_stage_record_count"], 0)

    def test_real_import_requires_terminal_marker_and_review_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            record = self.imported_record()
            root = self.write_state(Path(temp), {"nav-test": record})
            self.write_terminal(root)
            self.seal(root, record, evidence_file=True)
            self.persist_record(root, record)
            report = evidence.inspect_case(root, PACKAGE)
        self.assertTrue(report["structurally_valid"], report)
        self.assertEqual(report["imports"][0]["binding_id"], record["binding_id"])
        self.assertEqual(report["accepted_stage_record_count"], 4)  # intake..spec accepted; Improve at spec
        self.assertIn("reported evidence", report["callback_content"])

    def test_missing_terminal_fails_closed_for_real_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.write_state(Path(temp), {"nav-test": self.imported_record()})
            report = evidence.inspect_case(root, PACKAGE)
        self.assertFalse(report["structurally_valid"])
        self.assertIn("no terminal.json", " ".join(report["errors"]))

    def test_corrupt_terminal_marker_fails_closed_and_cli_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            record = self.imported_record()
            root = self.write_state(Path(temp), {"nav-test": record})
            self.write_terminal(root, marker=False)
            self.seal(root, record)
            self.persist_record(root, record)
            completed = subprocess.run([sys.executable, str(HERE / "evidence.py"), str(root), "--package", str(PACKAGE)], text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["structurally_valid"])

    def test_synthetic_predecessors_are_not_real_imports_and_inner_action_is_derived(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self.write_state(Path(temp), {"nav-old": {"kind": "synthetic-fixture-predecessor", "claim": "No runtime.", "stage": "spec", "seed_result": {"outcome": "done"}}})
            report = evidence.inspect_case(root, PACKAGE)
        self.assertTrue(report["structurally_valid"], report)
        self.assertEqual(report["stage"], "test-strategy")
        self.assertIsNotNone(report["action_identity"]["id"])
        self.assertEqual(report["imports"], [])
        self.assertEqual(len(report["synthetic_predecessors"]), 1)
        self.assertEqual(report["accepted_stage_record_count"], 4)  # intake..spec accepted; Improve at spec

    def test_bad_archived_evidence_digest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            record = self.imported_record()
            root = self.write_state(Path(temp), {"nav-test": record})
            self.write_terminal(root)
            self.seal(root, record, evidence_file=True)
            record["evidence"][0]["sha256"] = "x" * 64
            self.persist_record(root, record)
            report = evidence.inspect_case(root, PACKAGE)
        self.assertFalse(report["structurally_valid"])
        self.assertIn("evidence", " ".join(report["errors"]))

    def test_traversing_archived_evidence_reference_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            record = self.imported_record()
            root = self.write_state(Path(temp), {"nav-test": record})
            self.write_terminal(root)
            self.seal(root, record, evidence_file=True)
            record["evidence"][0]["archive"] = "../outside.md"
            self.persist_record(root, record)
            report = evidence.inspect_case(root, PACKAGE)
        self.assertFalse(report["structurally_valid"])
        self.assertIn("unsafe", " ".join(report["errors"]))

    def test_terminal_content_tamper_fails_matching_digest_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            record = self.imported_record()
            root = self.write_state(Path(temp), {"nav-test": record})
            self.write_terminal(root)
            self.seal(root, record)
            self.persist_record(root, record)
            terminal = root / "run" / "improve" / self.import_action / "terminal.json"
            terminal.write_text(terminal.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            report = evidence.inspect_case(root, PACKAGE)
        self.assertFalse(report["structurally_valid"])
        self.assertIn("digest disagrees", " ".join(report["errors"]))

    def test_symlinked_terminal_and_archive_fail_even_with_matching_external_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            record = self.imported_record()
            root = self.write_state(base / "terminal-case", {"nav-test": record})
            self.write_terminal(root)
            terminal = root / "run" / "improve" / self.import_action / "terminal.json"
            outside = base / "outside-terminal.json"
            outside.write_bytes(terminal.read_bytes())
            terminal.unlink()
            os.symlink(outside, terminal)
            record["identities"] = {"terminal_packet_sha256": hashlib.sha256(outside.read_bytes()).hexdigest()}
            self.persist_record(root, record)
            terminal_report = evidence.inspect_case(root, PACKAGE)
            self.assertFalse(terminal_report["structurally_valid"])
            self.assertIn("terminal archive path contains a symlink", " ".join(terminal_report["errors"]))

            record = self.imported_record()
            root = self.write_state(base / "archive-case", {"nav-test": record})
            self.write_terminal(root)
            self.seal(root, record, evidence_file=True)
            archive = root / "run" / "improve" / self.import_action / "evidence" / "01-review.md"
            outside = base / "outside-review.md"
            outside.write_bytes(archive.read_bytes())
            archive.unlink()
            os.symlink(outside, archive)
            record["evidence"][0]["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
            self.persist_record(root, record)
            archive_report = evidence.inspect_case(root, PACKAGE)
        self.assertFalse(archive_report["structurally_valid"])
        self.assertIn("imported evidence archive path contains a symlink", " ".join(archive_report["errors"]))


if __name__ == "__main__":
    unittest.main()
