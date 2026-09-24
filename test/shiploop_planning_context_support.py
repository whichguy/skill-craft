#!/usr/bin/env python3
"""Reusable fixture for navigator-v3 planning-context collection tests."""

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


class PlanningContextFixture(unittest.TestCase):
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
        if waiting["active_improve"] is None:
            # Not an Improve checkpoint: the result advanced directly.
            self.state = waiting
        else:
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
