#!/usr/bin/env python3
"""Hermetic tests for Backchain's command line (skills/backchain/scripts/backchain.py), run as a subprocess.

check and package are judged against the lib.js verdicts in test/fixtures/backchain-check; export against the
graphs the Backchain checkout's JS exporter recorded in test/fixtures/backchain-export, and against Plan
Dispatcher's own validate-graph.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/backchain/scripts/backchain.py"
CORPUS = ROOT / "test/fixtures/backchain-check"
GOLDENS = ROOT / "test/fixtures/backchain-export"
DISPATCH = ROOT / "skills/plan-dispatcher/scripts/dispatch.js"
sys.path.insert(0, str(CLI.parent))
import backchain_graph as graph  # noqa: E402


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(CLI), *args], capture_output=True, text=True,
                          cwd=str(cwd), timeout=120)


def corpus_inputs() -> list:
    return sorted(path for path in CORPUS.rglob("*.json") if not path.name.endswith(".verdict.json")
                  and path.name not in ("sources.json", "manifest.json", "ecmascript-whitespace.json"))


def verdict(path: Path) -> dict:
    """The lib.js verdict, read with JS number semantics like the port (12345678901234567000 is a float there)."""
    return graph.loads(path.with_name(path.name.replace(".json", ".verdict.json")).read_bytes())


def canon(value) -> str:
    return json.dumps(value, sort_keys=True)


class CheckTests(unittest.TestCase):
    def test_the_receipt_reproduces_every_recorded_lib_js_verdict(self):
        inputs = corpus_inputs()
        self.assertEqual(len(inputs), 88)
        for path in inputs:
            recorded = verdict(path)
            with self.subTest(path.relative_to(CORPUS).as_posix()):
                done = run("check", str(path))
                receipt = graph.loads(done.stdout.encode("utf-8"))
                self.assertEqual(done.returncode, 0 if recorded["ok"] else 1, done.stderr)
                self.assertEqual(receipt["schema"], "backchain-check/v1")
                self.assertEqual(receipt["plan_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                for key in ("ok", "failures", "completion", "parallel_groups", "packaged_sha256", "unconfirmed_produces"):
                    self.assertEqual(canon(receipt[key]), canon(recorded[key]), key)
                self.assertIn("backchain check: " + ("valid" if recorded["ok"] else "invalid"), done.stderr)

    def test_unreadable_or_non_json_input_could_not_run(self):
        with tempfile.TemporaryDirectory(prefix="backchain-toolkit-") as temp:
            for name, data in (("broken.json", b'{"goal": '), ("nan.json", b'{"goal": NaN}'),
                               ("latin1.json", b'"\xe9"')):
                path = Path(temp) / name
                path.write_bytes(data)
                with self.subTest(name):
                    done = run("check", str(path))
                    self.assertEqual((done.returncode, done.stdout), (3, ""))
                    self.assertIn("could not run", done.stderr)
                    self.assertIn("this is not a finding about the plan", done.stderr)
            missing = run("check", str(Path(temp) / "absent.json"))
            self.assertEqual((missing.returncode, missing.stdout), (3, ""))

    def test_a_usage_error_could_not_run(self):
        self.assertEqual(run("check").returncode, 3)
        self.assertEqual(run("nonesuch").returncode, 3)
        self.assertEqual(run("--help").returncode, 0)


class PackageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="backchain-toolkit-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_the_packaged_plan_carries_recomputed_groups_and_validates(self):
        source = CORPUS / "edge/inv6-stored-groups.json"
        out = self.base / "packaged.json"
        done = run("package", str(source), "--out", str(out))
        self.assertEqual(done.returncode, 0, done.stderr)
        packaged = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(packaged, graph.package(graph.loads(source.read_bytes())))
        self.assertEqual(packaged["parallel_groups"], [["S1", "S2"]])
        receipt = json.loads(done.stdout)
        self.assertEqual((receipt["output"], receipt["output_sha256"]),
                         (str(out), hashlib.sha256(out.read_bytes()).hexdigest()))
        self.assertTrue(run("check", str(out)).returncode == 0)

    def test_packaging_is_idempotent_atomic_and_keeps_the_file_mode(self):
        plan = self.base / "plan.json"
        plan.write_bytes((CORPUS / "luna/plan-final.json").read_bytes())
        os.chmod(plan, 0o640)
        self.assertEqual(run("package", str(plan), "--out", str(plan)).returncode, 0)
        first = plan.read_bytes()
        self.assertEqual(run("package", str(plan), "--out", str(plan)).returncode, 0)
        self.assertEqual(plan.read_bytes(), first)
        self.assertEqual(plan.stat().st_mode & 0o777, 0o640)
        fresh = self.base / "fresh.json"
        self.assertEqual(run("package", str(plan), "--out", str(fresh)).returncode, 0)
        self.assertEqual(fresh.stat().st_mode & 0o777, 0o644)
        self.assertEqual(sorted(path.name for path in self.base.iterdir()), ["fresh.json", "plan.json"])

    def test_an_invalid_plan_is_still_packaged_and_reported(self):
        out = self.base / "orphan.json"
        done = run("package", str(CORPUS / "edge/inv4-orphan.json"), "--out", str(out))
        self.assertEqual(done.returncode, 1)
        self.assertTrue(out.is_file())
        self.assertEqual([f["invariant"] for f in json.loads(done.stdout)["failures"]], [4])


class ExportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="backchain-toolkit-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)

    def test_the_goldens_are_the_recorded_js_exports(self):
        manifest = json.loads((GOLDENS / "MANIFEST.json").read_text(encoding="utf-8"))
        names = sorted({path.name.split(".")[0] for path in GOLDENS.glob("*.plan.json")})
        self.assertEqual(names, ["confirmed", "diamond", "fan-in"])
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((GOLDENS / name).read_bytes()).hexdigest(), digest, name)
        for name in names:
            with self.subTest(name):
                done = run("export", str(GOLDENS / f"{name}.plan.json"))
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout),
                                 json.loads((GOLDENS / f"{name}.graph.json").read_text(encoding="utf-8")))

    def test_done_strings_carry_each_confirm_level(self):
        exported = json.loads(run("export", str(GOLDENS / "confirmed.plan.json")).stdout)
        done = [line for step in exported["steps"] for line in step["contract"]["done"]]
        self.assertTrue(any(line.endswith("; pass when all 6 cases pass") for line in done))
        self.assertTrue(any(line.endswith("(inspection is sufficient)") for line in done))
        self.assertTrue(any("Confirm by: unconfirmable here — " in line for line in done))

    def test_every_valid_complete_corpus_plan_exports_and_plan_dispatcher_accepts_it(self):
        exported = refused = 0
        for path in corpus_inputs():
            plan = graph.package(graph.loads(path.read_bytes()))
            structure = graph.validate_structure(plan)
            exportable = (structure["ok"] and graph.completion_status(plan, structure)["status"] == "complete"
                          and bool(plan["steps"]))
            with self.subTest(path.relative_to(CORPUS).as_posix()):
                out = self.base / (path.stem + ".graph.json")
                done = run("export", str(path), "--out", str(out))
                if not exportable:
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("error", json.loads(done.stderr.strip().splitlines()[-1]))
                    self.assertFalse(out.exists())
                    refused += 1
                    continue
                self.assertEqual(done.returncode, 0, done.stderr)
                request = self.base / (path.stem + ".validate.json")
                request.write_text(json.dumps({"graph": json.loads(out.read_text(encoding="utf-8"))}), encoding="utf-8")
                accepted = subprocess.run(["node", str(DISPATCH), "validate-graph", str(request)],
                                          capture_output=True, text=True, timeout=60)
                self.assertEqual(accepted.returncode, 0, accepted.stderr)
                exported += 1
        # The JS exporter, run on each packaged input on 2026-11-01, gave the same verdict for all 88 and the same
        # graph for the 33 it exported (journal, Round 1).
        self.assertEqual((exported, refused), (33, 55))

    def test_an_incomplete_plan_is_refused_with_its_open_needs(self):
        done = run("export", str(CORPUS / "luna/plan-final.json"))
        self.assertEqual((done.returncode, done.stdout), (1, ""))
        self.assertIn("Backchain plan is incomplete", json.loads(done.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
