#!/usr/bin/env python3
"""Focused tests for navigator-v3 planning-context collection."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_planning_context as planning_context  # noqa: E402
import shiploop_store as store  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PlanningContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-planning-context-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        self.run = self.base / "run"
        self.run.mkdir()
        self.external = self.base / "planning inputs"
        self.external.mkdir()
        self.graph = {
            "version": 1,
            "steps": [
                {"id": "A", "deps": [], "contract": {"task": "A"}},
                {"id": "B", "deps": ["A"], "contract": {"task": "B"}},
            ],
        }
        self.graph_path = self.write_json("execution-graph.json", self.graph)
        self.graph_source = {"path": str(self.graph_path.resolve()), "sha256": digest(self.graph_path)}
        self.state = navigator.new_state(
            str(self.repo.resolve()),
            "ORIGINAL REQUEST SENTINEL must not appear in planning reference files.",
            bound_plan="Keep the reviewed graph unchanged and retain explicit planning references.",
            protocol_version=3,
        )
        self.actions: dict[str, list[str]] = {}

    def write_text(self, name: str, text: str) -> Path:
        path = self.external / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_json(self, name: str, value: dict) -> Path:
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def advance(
        self,
        *,
        evidence_refs: list[str] | None = None,
        outcome: str = "done",
        work_items: list[dict[str, str]] | None = None,
        choices: dict[str, bool] | None = None,
        summary: str | None = None,
    ) -> str:
        stage = navigator.current_stage(self.state)
        action = dict(navigator.current_action(self.state))["id"]
        result = {
            "outcome": outcome,
            "summary": summary or "Planner-authored summary for " + stage + ".",
            "evidence_refs": evidence_refs or [],
        }
        if work_items is not None:
            result["work_items"] = work_items
        if choices is not None:
            result["choices"] = choices
        waiting = navigator.apply(self.state, action, result)
        self.state = navigator.finish_improve(
            waiting,
            action,
            {
                "summary": "Accepted Improve evidence for " + stage + ".",
                "lessons": "Retain the decision from " + stage + ".",
                "review_refs": [str(self.write_text("reviews/" + action + ".md", "review\n"))],
                "check_refs": [str(self.write_text("checks/" + action + ".md", "check\n"))],
            },
        )
        navigator.save(self.run, self.state)
        self.actions.setdefault(stage, []).append(action)
        return action

    def to_implement(self, references: dict[str, list[str]] | None = None) -> None:
        supplied = references or {}
        while navigator.current_stage(self.state) != "implement":
            stage = navigator.current_stage(self.state)
            work_items = None
            if stage == "plan":
                work_items = [
                    {
                        "id": "W1",
                        "title": "Preserve reviewed planning material",
                        "context": "The worker needs the full planning pass, not only a task directive.",
                    }
                ]
            self.advance(evidence_refs=supplied.get(stage), work_items=work_items)

    def to_second_implement_with_document_choice(self) -> None:
        work_items = [
            {
                "id": "W1",
                "title": "First reviewed item",
                "context": "Its accepted documentation records a reusable decision.",
            },
            {
                "id": "W2",
                "title": "Current implementation item",
                "context": "This item receives the earlier planning references.",
            },
        ]
        while True:
            stage = navigator.current_stage(self.state)
            if stage == "implement" and self.state["work_index"] == 1:
                return
            self.advance(
                work_items=work_items if stage == "plan" else None,
                choices={"skill_required": False}
                if stage == "document" and self.state["work_index"] == 0 else None,
            )

    @staticmethod
    def file_bytes(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    @staticmethod
    def artifact(manifest: dict, path: Path) -> dict:
        resolved = str(path.resolve())
        return next(row for row in manifest["artifacts"] if row["path"] == resolved)

    def test_collects_v3_records_without_legacy_path_assumptions(self) -> None:
        requirements = self.write_text("specs/requirements.md", "Must retain requirements and constraints.\n")
        step_plan = self.write_text("plans/current-step.md", "Implement A before B.\n")
        resolved = self.write_text("plans/reviewed draft.md", "This file is intentionally snapshotted.\n")
        raw_fragment = str(requirements.resolve()) + "#requirements"
        self.to_implement(
            {
                "intake": [raw_fragment],
                "discovery": ["https://example.invalid/planning-source"],
                "research": ["reviewed draft.md"],
                "spec": [str(requirements.resolve())],
                "step-plan": [str(step_plan.resolve())],
                "test-spec": [str(step_plan.resolve())],
            }
        )
        before_state = copy.deepcopy(self.state)
        before_files = self.file_bytes(self.run)
        research_action = self.actions["research"][0]

        collected = planning_context.collect(
            self.run.resolve(),
            self.state,
            self.graph,
            self.graph_source,
            {
                "references": [
                    {
                        "action": research_action,
                        "index": 0,
                        "kind": "file",
                        "path": str(resolved.resolve()),
                        "snapshot": True,
                        "required_for": ["A"],
                    }
                ]
            },
        )

        self.assertEqual(self.state, before_state)
        self.assertEqual(self.file_bytes(self.run), before_files)
        self.assertEqual(collected["missing_required"], [])
        manifest = collected["manifest"]
        self.assertEqual(
            set(manifest),
            {"schema", "source", "graph", "briefing", "artifacts", "unresolved_refs", "reference_only"},
        )
        self.assertEqual(manifest["schema"], planning_context.SCHEMA)
        self.assertEqual(manifest["graph"], self.graph_source)
        self.assertEqual(manifest["source"]["run_id"], self.state["run_id"])
        self.assertEqual(manifest["source"]["action_id"], navigator.current_action(self.state)["id"])
        self.assertEqual(manifest["source"]["workitem"], "W1")
        self.assertEqual(manifest["source"]["revision"], self.state["revision"])
        self.assertEqual(manifest["unresolved_refs"], [])
        self.assertEqual(
            manifest["reference_only"],
            [
                {
                    "action": self.actions["discovery"][0],
                    "index": 0,
                    "text": "https://example.invalid/planning-source",
                    "kind": "url",
                    "value": "https://example.invalid/planning-source",
                    "required_for": [],
                }
            ],
        )

        requirements_entry = self.artifact(manifest, requirements)
        self.assertEqual(requirements_entry["classification"], "current")
        self.assertEqual(requirements_entry["required_for"], ["*"])
        self.assertEqual(
            {ref["text"] for ref in requirements_entry["references"]},
            {raw_fragment, str(requirements.resolve())},
        )
        step_entry = self.artifact(manifest, step_plan)
        self.assertEqual(len(step_entry["references"]), 2)
        self.assertEqual(set(step_entry["producers"]), {self.actions["step-plan"][0], self.actions["test-spec"][0]})

        snapshots = [entry for entry in manifest["artifacts"] if "planning-snapshot" in entry["roles"]]
        self.assertEqual(len(snapshots), 1)
        snapshot = snapshots[0]
        self.assertEqual(snapshot["required_for"], ["A"])
        self.assertEqual(snapshot["origin"], {"path": str(resolved.resolve()), "sha256": digest(resolved)})
        snapshot_relative = str(Path(snapshot["path"]).relative_to(self.run.resolve()))
        self.assertEqual(collected["files"][snapshot_relative], resolved.read_text(encoding="utf-8"))

        brief_relative = str(Path(manifest["briefing"]["path"]).relative_to(self.run.resolve()))
        brief = collected["files"][brief_relative]
        self.assertEqual(manifest["briefing"]["sha256"], hashlib.sha256(brief.encode("utf-8")).hexdigest())
        self.assertIn("# Planning reference statements", brief)
        self.assertIn("sole task prompt", brief)
        self.assertNotIn(self.state["prompt"], brief)
        self.assertIn("Preserve reviewed planning material", brief)
        self.assertIn("Planner-authored summary for step-plan.", brief)
        self.assertIn("Accepted Improve evidence for step-plan.", brief)
        self.assertIn(raw_fragment, brief)
        self.assertFalse((self.run / brief_relative).exists())
        brief_artifact = self.artifact(manifest, Path(manifest["briefing"]["path"]))
        self.assertEqual(brief_artifact["required_for"], ["*"])

        projection_relative = "chains/" + manifest["source"]["action_id"] + "/planning-projection.json"
        projection = json.loads(collected["files"][projection_relative])
        self.assertEqual(projection["schema"], "shiploop-planning-projection/v1")
        self.assertNotIn("prompt", projection)
        self.assertNotIn(self.state["prompt"], "\n".join(collected["files"].values()))
        self.assertEqual(projection["bound_plan"], self.state["bound_plan"])
        plan_record = next(row for row in projection["planning_records"] if row["action"] == self.actions["plan"][0])
        self.assertEqual(plan_record["work_items"][0]["title"], "Preserve reviewed planning material")
        self.assertNotIn('"status"', collected["files"][projection_relative])
        self.assertTrue(all(Path(entry["path"]).is_absolute() for entry in manifest["artifacts"]))
        self.assertEqual(
            len([entry for entry in manifest["artifacts"] if "accepted-result" in entry["roles"]]),
            len(self.state["history"]),
        )

    def test_current_missing_sources_are_visible_and_blocking(self) -> None:
        missing = self.external / "missing" / "required-spec.md"
        self.to_implement({"intake": [str(missing.resolve())]})
        spec_action = self.actions["spec"][0]
        (self.run / "results" / (spec_action + ".md")).unlink()

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(
            collected["manifest"]["unresolved_refs"],
            [
                {
                    "action": self.actions["intake"][0],
                    "index": 0,
                    "text": str(missing.resolve()),
                    "required_for": ["*"],
                }
            ],
        )
        failures = collected["missing_required"]
        self.assertTrue(any(row["kind"] == "accepted-result" and row["action"] == spec_action for row in failures))
        self.assertTrue(any(row["kind"] == "reference" and row["action"] == self.actions["intake"][0] for row in failures))

    def test_tampered_current_result_is_diagnosed_without_writing(self) -> None:
        self.to_implement()
        plan_action = self.actions["plan"][0]
        result_path = self.run / "results" / (plan_action + ".md")
        store.write_record(result_path, {"tampered": True}, title="Tampered result")
        before = self.file_bytes(self.run)

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(self.file_bytes(self.run), before)
        record_diagnostics = [row for row in collected["missing_required"] if row["kind"] == "accepted-result"]
        self.assertEqual(len(record_diagnostics), 1)
        self.assertEqual(record_diagnostics[0]["action"], plan_action)
        self.assertIn("does not match navigator state", record_diagnostics[0]["reason"])

    def test_accepted_document_choices_are_preserved_as_reference_material(self) -> None:
        self.to_second_implement_with_document_choice()

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(collected["missing_required"], [])
        projection_relative = "chains/" + navigator.current_action(self.state)["id"] + "/planning-projection.json"
        projection = json.loads(collected["files"][projection_relative])
        document = next(
            row for row in projection["planning_records"] if row["action"] == self.actions["document"][0]
        )
        self.assertEqual(document["classification"], "other-item")
        self.assertEqual(document["choices"], {"skill_required": False})
        brief_relative = str(Path(collected["manifest"]["briefing"]["path"]).relative_to(self.run.resolve()))
        brief = collected["files"][brief_relative]
        self.assertIn("Recorded choices:", brief)
        self.assertIn('"skill_required": false', brief)

    def test_current_free_text_can_be_explicitly_cataloged_but_file_lookalikes_cannot(self) -> None:
        self.to_implement({"intake": ["baseline checks passed"]})
        intake_action = self.actions["intake"][0]
        collected = planning_context.collect(
            self.run.resolve(),
            self.state,
            self.graph,
            self.graph_source,
            {
                "references": [
                    {
                        "action": intake_action,
                        "index": 0,
                        "kind": "statement",
                        "value": "Planner recorded the baseline outcome without a local artifact.",
                        "rationale": "This is a free-text evidence statement, not a file locator.",
                    }
                ]
            },
        )
        self.assertEqual(collected["missing_required"], [])
        self.assertEqual(
            collected["manifest"]["reference_only"],
            [
                {
                    "action": intake_action,
                    "index": 0,
                    "text": "baseline checks passed",
                    "kind": "statement",
                    "value": "Planner recorded the baseline outcome without a local artifact.",
                    "rationale": "This is a free-text evidence statement, not a file locator.",
                    "required_for": [],
                }
            ],
        )

        file_like_state = navigator.new_state(
            str(self.repo.resolve()), "File-like resolution fixture.", protocol_version=3
        )
        self.state = file_like_state
        self.actions = {}
        self.to_implement({"intake": ["docs/missing.md"]})
        with self.assertRaisesRegex(planning_context.PlanningContextError, "apparent local file"):
            planning_context.collect(
                self.run.resolve(),
                self.state,
                self.graph,
                self.graph_source,
                {
                    "references": [
                        {
                            "action": self.actions["intake"][0],
                            "index": 0,
                            "kind": "statement",
                            "value": "It is not a file after all.",
                            "rationale": "Attempted waiver.",
                        }
                    ]
                },
            )

    def test_real_improve_archives_are_hashed_without_reading_the_child_workspace(self) -> None:
        self.to_implement()
        action = self.actions["spec"][0]
        stage = "spec"
        archives: list[dict[str, str]] = []
        for index, name in enumerate(("review-a.md", "review-b.md", "checks.md"), start=1):
            relative = "improve/" + action + "/evidence/%02d-%s" % (index, name)
            path = self.run / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name + " evidence\n", encoding="utf-8")
            archives.append({"source": name, "archive": relative, "sha256": digest(path)})
        record = {
            "version": 1,
            "binding_id": self.state["run_id"] + "/" + action,
            "workspace": str((self.base / "deleted-child-workspace").resolve()),
            "action_id": action,
            "stage": stage,
            "skill": {"name": "synthetic"},
            "runtime_phase": "done",
            "identities": {"evidence_sha256": {row["source"]: row["sha256"] for row in archives}},
            "evidence": archives,
            "receipt": {
                "summary": "Imported planner review completed.",
                "review_refs": ["review-a.md", "review-b.md"],
                "check_refs": ["checks.md"],
                "lessons": "Preserve the reviewed design decision.",
            },
        }
        self.state["improve_results"][action] = {
            **record,
            "seed_result": self.state["improve_results"][action]["seed_result"],
        }
        receipt_path = self.run / "improve" / action / "receipt.md"
        store.write_record(receipt_path, record, title="ShipLoop standalone Improve receipt")
        navigator.save(self.run, self.state)

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(collected["missing_required"], [])
        evidence = [row for row in collected["manifest"]["artifacts"] if "improve-evidence" in row["roles"]]
        real_archives = [row for row in evidence if row.get("source_reference") in {"review-a.md", "review-b.md", "checks.md"}]
        self.assertEqual(len(real_archives), 3)
        self.assertTrue(all(row["required_for"] == ["*"] for row in real_archives))
        self.assertTrue(any("improve-receipt" in row["roles"] for row in collected["manifest"]["artifacts"]))
        projection_relative = "chains/" + navigator.current_action(self.state)["id"] + "/planning-projection.json"
        projection = json.loads(collected["files"][projection_relative])
        spec = next(row for row in projection["planning_records"] if row["action"] == action)
        self.assertEqual(spec["improve"]["evidence"], archives)
        self.assertEqual(spec["improve"]["receipt"]["lessons"], "Preserve the reviewed design decision.")
        self.assertNotIn("workspace", spec["improve"])
        self.assertNotIn("runtime_phase", spec["improve"])

        archive_path = self.run / archives[0]["archive"]
        archive_path.write_text("tampered\n", encoding="utf-8")
        tampered = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)
        self.assertTrue(any(row["kind"] == "improve-evidence" and row["action"] == action for row in tampered["missing_required"]))

    def test_run_state_cannot_be_bound_as_a_file_dependency(self) -> None:
        self.to_implement({"intake": [str((self.run / "state.md").resolve())]})

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(len(collected["manifest"]["unresolved_refs"]), 1)
        self.assertTrue(any("state.md must be projected" in row["reason"] for row in collected["missing_required"]))

    def test_large_inventory_is_not_truncated(self) -> None:
        references = []
        for index in range(160):
            references.append(str(self.write_text("large/%03d.md" % index, "planning input %d\n" % index).resolve()))
        self.to_implement({"intake": references})

        collected = planning_context.collect(self.run.resolve(), self.state, self.graph, self.graph_source)

        self.assertEqual(collected["missing_required"], [])
        artifact_paths = {entry["path"] for entry in collected["manifest"]["artifacts"]}
        self.assertTrue(all(reference in artifact_paths for reference in references))
        intake_refs = [
            entry for entry in collected["manifest"]["artifacts"]
            if self.actions["intake"][0] in entry["producers"] and "evidence-reference" in entry["roles"]
        ]
        self.assertEqual(len(intake_refs), len(references))


if __name__ == "__main__":
    unittest.main(verbosity=2)
