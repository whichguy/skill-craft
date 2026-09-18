#!/usr/bin/env python3
"""Focused compact-bundle evidence-retention checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from initialize import initialize


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generic_collect_under_test", HERE / "collect.py")
assert spec and spec.loader
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt(arm: str, operation: str, result: dict, *, path: str | None = None,
            argv: list[str] | None = None, error: bool = False) -> dict:
    arguments = {"operation": operation}
    if path is not None:
        arguments["path"] = path
    if argv is not None:
        arguments["argv"] = argv
    return {"arm": arm, "event": "workspace_call", "request": {"name": "workspace", "arguments": arguments},
            "result": result, "is_error": error}


def make_study(root: Path) -> Path:
    study = root / "study"
    candidate, plan = root / "candidate.md", root / "plan.md"
    candidate.write_text("candidate guide\n")
    plan.write_text("bounded test plan\n")
    initialize(study, candidate, plan, blind_seed=7)
    arms: dict[str, dict] = {}
    receipts: list[dict] = []
    for name, guide in (("arm-one", "BASELINE GUIDE CONTENT"), ("arm-two", "CANDIDATE GUIDE CONTENT")):
        workspace = study / "arms" / name / "workspace"
        (workspace / "guidance").mkdir(parents=True)
        (workspace / "README.md").write_text("COMMON-SOURCE\n", encoding="utf-8")
        (workspace / "probe.py").write_text("print('probe')\n", encoding="utf-8")
        (workspace / "guidance" / "research-loop.md").write_text(guide + "\n", encoding="utf-8")
        expected = {str(path.relative_to(workspace)): digest(path) for path in sorted(workspace.rglob("*")) if path.is_file()}
        (workspace.parent / "input-hashes.json").write_text(json.dumps(expected), encoding="utf-8")
        (workspace / "REPORT.md").write_text(f"# intact report {name}\n", encoding="utf-8")
        run = workspace.parent / "run"
        run.mkdir()
        metadata = {"completion": {"status": "completed"}, "fixture_edits": {},
                    "contexts": [{"exit_code": 0, "termination_reason": None, "elapsed_seconds": 1}],
                    "observed_actions": {"observed_unique": 6},
                    "gateway_ledger": {"records": [{"phase": "exploration"} for _ in range(6)]}}
        (run / "metadata.json").write_text(json.dumps(metadata))
        arms[name] = {"family": "f1", "repetition": 0}
        receipts += [
            receipt(name, "read", {"call": 1, "text": "COMMON-SOURCE\n"}, path="README.md"),
            receipt(name, "exec", {"call": 2, "exit_code": 0, "stdout": "PROBE_SUCCESS\n", "stderr": ""}, argv=["python3", "probe.py", "success"]),
            receipt(name, "exec", {"call": 3, "exit_code": 1, "stdout": "", "stderr": "PROBE_ERROR\n"}, argv=["python3", "probe.py", "failure"]),
            receipt(name, "read", {"call": 4, "text": guide}, path="guidance/research-loop.md"),
            receipt(name, "exec", {"call": 5, "exit_code": 0,
                                    "stdout": f"COMMON-SOURCE\nprint('probe')\n{guide}", "stderr": ""},
                    argv=["python3", "-c", "for path in ('README.md', 'probe.py', 'guidance/research-loop.md'): print(open(path).read())"]),
            receipt(name, "read", {"call": 6, "error": "missing source"}, path="missing.md", error=True),
        ]
    (study / "private" / "f1-r0-mapping.json").write_text(json.dumps({"Left": "arm-two", "Right": "arm-one"}), encoding="utf-8")
    state = json.loads((study / "study.json").read_text())
    state["arms"] = arms
    (study / "study.json").write_text(json.dumps(state), encoding="utf-8")
    (study / "receipts.jsonl").write_text("".join(json.dumps(item) + "\n" for item in receipts), encoding="utf-8")
    return study


class CompactBundleTest(unittest.TestCase):
    def test_retains_probe_results_hides_guidance_and_deduplicates_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = make_study(Path(temporary))
            bundle = collector.collect_compact(study, "f1")
            text = bundle.read_text(encoding="utf-8")
            self.assertEqual(text.count("COMMON-SOURCE"), 1)
            self.assertEqual(text.count("PROBE_SUCCESS"), 2)
            self.assertEqual(text.count("PROBE_ERROR"), 2)
            self.assertIn("missing source", text)
            self.assertNotIn("BASELINE GUIDE CONTENT", text)
            self.assertNotIn("CANDIDATE GUIDE CONTENT", text)
            self.assertNotIn("for path in ('README.md'", text)
            self.assertIn("guidance-reading argv withheld", text)
            self.assertIn("# intact report arm-one", text)
            self.assertIn("# intact report arm-two", text)
            self.assertEqual(json.loads((study / "private" / "f1-r0-mapping.json").read_text()), {"Left": "arm-two", "Right": "arm-one"})
            manifest = json.loads(bundle.with_name("bundle-compact-manifest.json").read_text())
            self.assertEqual(len(manifest["common_sources"]), 2)
            self.assertEqual(manifest["receipt_counts"], {"Left": 6, "Right": 6})

    def test_changed_input_fails_without_a_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            study = make_study(Path(temporary))
            (study / "arms" / "arm-one" / "workspace" / "README.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "input integrity failure"):
                collector.collect_compact(study, "f1")
            self.assertFalse((study / "blind" / "f1-r0" / "bundle-compact.md").exists())

    def test_failed_context_cannot_be_presented_as_valid_blind_evidence(self) -> None:
        for failed in ("nonzero_exit", "terminated", "incomplete", "fixture_edit"):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as temporary:
                study = make_study(Path(temporary))
                path = study / "arms/arm-one/run/metadata.json"
                value = json.loads(path.read_text())
                if failed == "nonzero_exit":
                    value["contexts"][0]["exit_code"] = 1
                elif failed == "terminated":
                    value["contexts"][0]["termination_reason"] = "deadline"
                elif failed == "incomplete":
                    value["completion"]["status"] = "incomplete"
                else:
                    value["fixture_edits_flagged"] = True
                path.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "inconclusive"):
                    collector.collect_compact(study, "f1")
                self.assertFalse((study / "blind/f1-r0/bundle-compact.md").exists())


if __name__ == "__main__":
    unittest.main()
