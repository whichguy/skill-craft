#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's port of Backchain's structural check and the backchain-check verb.

test/fixtures/backchain-check holds verdicts that make_corpus.js recorded from the Backchain checkout's
harness/lib.js, the arbiter; the port must reproduce every one exactly.
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
SCRIPTS = ROOT / "skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
CORPUS = ROOT / "test/fixtures/backchain-check"
sys.path.insert(0, str(SCRIPTS))
import shiploop_backchain_graph as graph  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402

# One violating graph per invariant; edge/<name>.fixed.json is the same graph after the fix.
SINGLE_INVARIANT = {
    "inv1-schema": 1, "inv2-cycle": 2, "inv2-circular": 2, "inv3-dangling": 3, "inv4-orphan": 4,
    "inv5-double-booked": 5, "inv6-unknown-step": 6, "inv7-null-origin": 7,
}


def canon(value) -> str:
    return json.dumps(value, sort_keys=True)


def corpus_plan(relative: str):
    return graph.loads((CORPUS / relative).read_bytes())


def invariants(result: dict) -> list:
    return [failure["invariant"] for failure in result["failures"]]


def port_verdict(data: bytes) -> dict:
    plan = graph.loads(data)
    packaged = graph.package(plan)
    structure = graph.validate_structure(packaged)
    raw = graph.validate_structure(plan)
    return {
        "ok": structure["ok"],
        "failures": structure["failures"],
        "completion": graph.completion_status(packaged)["status"],
        "parallel_groups": graph.compute_parallel_groups(packaged),
        "packaged_sha256": graph._sha256(graph.js_stringify(packaged).encode("utf-8")),
        "unconfirmed_produces": graph.unconfirmed_produces(packaged),
        "raw": {"ok": raw["ok"], "failures": raw["failures"], "completion": graph.completion_status(plan)["status"]},
    }


class CorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
        self.verdicts = sorted(CORPUS.rglob("*.verdict.json"))

    def test_every_recorded_lib_js_verdict_is_reproduced(self):
        for path in self.verdicts:
            recorded = graph.loads(path.read_bytes())
            data = (CORPUS / recorded["input"]).read_bytes()
            with self.subTest(recorded["input"]):
                self.assertEqual(graph._sha256(data), recorded["input_sha256"])
                self.assertEqual(recorded["lib_js_sha256"], self.manifest["lib_js_sha256"])
                for key, value in port_verdict(data).items():
                    self.assertEqual(canon(value), canon(recorded[key]), key)

    def test_the_corpus_holds_every_input_with_a_verdict(self):
        inputs = sorted(path.relative_to(CORPUS).as_posix() for path in CORPUS.rglob("*.json")
                        if not path.name.endswith(".verdict.json")
                        and path.name not in ("sources.json", "manifest.json", "ecmascript-whitespace.json"))
        self.assertEqual(inputs, sorted(entry["input"] for entry in self.manifest["inputs"]))
        self.assertEqual(sorted(path.with_name(path.name.replace(".verdict.json", ".json")) for path in self.verdicts),
                         sorted(CORPUS / name for name in inputs))
        counts = [sum(name.startswith(prefix) for name in inputs)
                  for prefix in ("structural/good/", "structural/bad/", "luna/")]
        self.assertEqual(counts, [23, 28, 5])

    def test_luna_plan_candidates_pass_packaged_and_step_plans_fail_on_d1(self):
        for name in ("plan-pre-loop", "plan-after-pass-1", "plan-final", "step-plan-review-01", "step-plan-final"):
            with self.subTest(name):
                plan = corpus_plan(f"luna/{name}.json")
                packaged = graph.validate_structure(graph.package(plan))
                if name.startswith("plan-"):
                    self.assertTrue(packaged["ok"], packaged["failures"])
                else:
                    self.assertEqual([(f["invariant"], f["detail"]) for f in packaged["failures"]],
                                     [(4, {"stepId": "D1"})])
                # Backchain keeps parallel_groups: [] in the file, so every raw candidate fails invariant 6.
                raw = graph.validate_structure(plan)
                self.assertEqual(plan["parallel_groups"], [])
                self.assertIn(6, invariants(raw))
                self.assertEqual(set(invariants(raw)) - {4}, {6})

    def test_the_whitespace_class_is_ecmascript_whitespace(self):
        recorded = json.loads((CORPUS / "ecmascript-whitespace.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(map(ord, graph.JS_WHITESPACE)), recorded["code_points"])


class InvariantTests(unittest.TestCase):
    def test_each_invariant_fails_alone_and_passes_after_the_fix(self):
        for name, invariant in SINGLE_INVARIANT.items():
            with self.subTest(name):
                broken = graph.validate_structure(graph.package(corpus_plan(f"edge/{name}.json")))
                self.assertFalse(broken["ok"])
                self.assertEqual(set(invariants(broken)), {invariant}, broken["failures"])
                fixed = graph.validate_structure(graph.package(corpus_plan(f"edge/{name}.fixed.json")))
                self.assertTrue(fixed["ok"], fixed["failures"])

    def test_stored_groups_fail_raw_and_pass_once_packaged(self):
        plan = corpus_plan("edge/inv6-stored-groups.json")
        self.assertEqual(invariants(graph.validate_structure(plan)), [6])
        self.assertTrue(graph.validate_structure(graph.package(plan))["ok"])
        self.assertEqual(graph.package(plan)["parallel_groups"], [["S1", "S2"]])
        self.assertTrue(graph.validate_structure(corpus_plan("edge/inv6-stored-groups.fixed.json"))["ok"])

    def test_a_discovered_step_that_delivers_a_goal_need_needs_no_consumer(self):
        for name in ("inv4-goal-need", "inv4-goal-sentence"):
            with self.subTest(name):
                result = graph.validate_structure(graph.package(corpus_plan(f"edge/{name}.json")))
                self.assertTrue(result["ok"], result["failures"])
        orphan = graph.validate_structure(graph.package(corpus_plan("edge/inv4-orphan.json")))
        self.assertEqual(orphan["failures"][0]["detail"], {"stepId": "D1"})

    def test_completion_status(self):
        self.assertEqual(graph.completion_status(graph.package(corpus_plan("edge/inv3-dangling.fixed.json")))["status"],
                         "complete")
        unresolved = graph.completion_status(graph.package(corpus_plan("edge/inv5-double-booked.fixed.json")))
        self.assertEqual((unresolved["status"], unresolved["unresolved_count"]), ("incomplete", 1))
        self.assertEqual(graph.completion_status(corpus_plan("edge/inv3-dangling.json"))["status"], "invalid")


class WhitespaceTests(unittest.TestCase):
    def test_js_trim_and_normalization_use_ecmascript_whitespace(self):
        for char in "\x1c\x1d\x1e\x1f\x85":  # whitespace to Python, text to JS
            with self.subTest(hex(ord(char))):
                self.assertEqual(graph.js_trim(char + "a" + char), char + "a" + char)
                self.assertEqual(graph.normalize_need_string(f"a {char} b"), f"a {char} b")
        for char in "﻿  　":  # whitespace to JS; U+FEFF is text to Python
            with self.subTest(hex(ord(char))):
                self.assertEqual(graph.js_trim(char + "a" + char), "a")
                self.assertEqual(graph.normalize_need_string(f"a{char}\t{char}b"), "a b")

    def test_null_origin_needs_match_initial_state_by_js_rules(self):
        python_only = graph.validate_structure(graph.package(corpus_plan("edge/ws-python-only.json")))
        self.assertEqual(invariants(python_only), [7, 7, 7, 7])
        self.assertTrue(graph.validate_structure(graph.package(corpus_plan("edge/ws-js-only.json")))["ok"])

    def test_blank_confirm_and_goal_need_use_js_trim(self):
        result = graph.validate_structure(graph.package(corpus_plan("edge/ws-confirm-and-goal-needs.json")))
        self.assertEqual([f["message"] for f in result["failures"]], [
            "steps[0].confirm[0].by must be a non-blank string",
            "goal_needs[1] must be non-empty after whitespace normalization",
        ])


DETERMINISM = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_backchain_graph as graph
corpus = Path(sys.argv[2])
for path in sorted(corpus.rglob("*.json")):
    if path.name.endswith(".verdict.json") or path.name in ("sources.json", "manifest.json", "ecmascript-whitespace.json"):
        continue
    record = graph.receipt(path.read_bytes(), path.relative_to(corpus).as_posix())
    raw = graph.validate_structure(graph.loads(path.read_bytes()))
    sys.stdout.write(graph.receipt_text(record) + json.dumps(raw) + "\\n")
"""


class DeterminismTests(unittest.TestCase):
    def test_identical_output_across_hash_seeds(self):
        outputs = []
        for seed in ("0", "1", "0"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            completed = subprocess.run([sys.executable, "-c", DETERMINISM, str(SCRIPTS), str(CORPUS)],
                                       capture_output=True, text=True, env=env, check=True, timeout=120)
            outputs.append(completed.stdout)
        self.assertGreater(len(outputs[0]), 50_000)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0], outputs[2])


RECEIPT_KEYS = ["schema", "candidate", "candidate_sha256", "packaged_sha256", "ok", "failures", "completion",
                "parallel_groups", "counts", "unconfirmed_produces"]


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-backchain-check-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo, self.run, self.elsewhere = self.base / "repo", self.base / "run", self.base / "elsewhere"
        self.repo.mkdir()
        self.elsewhere.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "SHIPLOOP_KEEPALIVE": "off"}
        self.env.pop("GROK_AGENT", None)
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True, env=self.env)
        init = self.cli("init", "--repo", str(self.repo), "--run-dir", str(self.run), "--prompt=Backchain check fixture.")
        self.assertEqual(init.returncode, 0, init.stderr)
        self.action = navigator.current_action(store.read_record(self.run / "state.md"))["id"]

    def cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=self.env,
                              cwd=str(cwd or self.elsewhere), timeout=120)

    def check(self, candidate: Path, *extra: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return self.cli("backchain-check", "--candidate", str(candidate), *extra, cwd=cwd)

    def files(self, root: Path) -> dict:
        return {path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in sorted(root.rglob("*")) if path.is_file()}

    def test_exit_codes_follow_lint(self):
        valid = self.check(CORPUS / "luna/plan-final.json", "--run-dir", str(self.run))
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertIn("ShipLoop backchain-check: valid, incomplete; 20 steps", valid.stderr)
        invalid = self.check(CORPUS / "luna/step-plan-final.json", "--run-dir", str(self.run))
        self.assertEqual(invalid.returncode, 1, invalid.stderr)
        self.assertIn("invalid, 1 failure(s) on invariant(s) 4", invalid.stderr)
        for name, data in (("broken.json", b'{"goal": '), ("bom.json", b'\xef\xbb\xbf{}'), ("latin1.json", b'"\xe9"'),
                           ("nan.json", b'{"goal": NaN}')):
            path = self.base / name
            path.write_bytes(data)
            with self.subTest(name):
                unavailable = self.check(path, "--run-dir", str(self.run))
                self.assertEqual(unavailable.returncode, 3)
                self.assertEqual(unavailable.stdout, "")
                self.assertIn("could not run", unavailable.stderr)
                self.assertIn("this is not a finding", unavailable.stderr)
        missing = self.check(self.base / "absent.json", "--run-dir", str(self.run))
        self.assertEqual((missing.returncode, missing.stdout), (3, ""))
        self.assertEqual(len(list((self.run / "backchain" / self.action).iterdir())), 4)

    def test_the_receipt_reports_the_packaged_check(self):
        candidate = CORPUS / "luna/step-plan-final.json"
        completed = self.check(candidate, "--run-dir", str(self.run))
        receipt = json.loads(completed.stdout)
        self.assertEqual(list(receipt), RECEIPT_KEYS)
        data = candidate.read_bytes()
        self.assertEqual(receipt["schema"], "shiploop-backchain-check/v1")
        self.assertEqual(receipt["candidate"], str(candidate))
        self.assertEqual(receipt["candidate_sha256"], hashlib.sha256(data).hexdigest())
        recorded = json.loads((CORPUS / "luna/step-plan-final.verdict.json").read_text(encoding="utf-8"))
        for key in ("ok", "failures", "completion", "parallel_groups", "packaged_sha256", "unconfirmed_produces"):
            self.assertEqual(canon(receipt[key]), canon(recorded[key]), key)
        self.assertEqual(receipt["counts"]["steps"], 20)
        self.assertEqual(receipt["counts"]["discovered"],
                         sum(step["origin"] == "discovered" for step in json.loads(data)["steps"]))

    def test_snapshot_and_receipt_are_written_once_under_the_action(self):
        candidate = self.base / "candidate.json"
        candidate.write_bytes((CORPUS / "luna/plan-pre-loop.json").read_bytes())
        first = self.check(candidate, "--run-dir", str(self.run))
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()[:12]
        directory = self.run / "backchain" / self.action
        self.assertEqual(sorted(path.name for path in directory.iterdir()),
                         [f"candidate-{digest}.json", f"check-{digest}.json"])
        self.assertEqual((directory / f"candidate-{digest}.json").read_bytes(), candidate.read_bytes())
        self.assertEqual((directory / f"check-{digest}.json").read_text(encoding="utf-8"), first.stdout)
        self.assertIn(f"receipt {directory / f'check-{digest}.json'}", first.stderr)
        before = self.files(directory)
        again = self.check(candidate, "--run-dir", str(self.run))
        self.assertEqual(again.stdout, first.stdout)
        self.assertEqual(self.files(directory), before)
        # A revision gets its own pair; the earlier snapshot stays.
        candidate.write_bytes((CORPUS / "luna/plan-final.json").read_bytes())
        self.assertEqual(self.check(candidate, "--run-dir", str(self.run)).returncode, 0)
        self.assertEqual(len(list(directory.iterdir())), 4)
        self.assertEqual(self.files(directory).items() & before.items(), before.items())

    def test_no_run_state_is_touched(self):
        before = {name: value for name, value in self.files(self.run).items()}
        for name in ("plan-final", "step-plan-final"):
            self.check(CORPUS / f"luna/{name}.json", "--run-dir", str(self.run))
        after = {name: value for name, value in self.files(self.run).items() if not name.startswith("backchain/")}
        self.assertEqual(after, before)

    def test_without_a_run_it_prints_the_receipt_and_writes_nothing(self):
        completed = self.check(CORPUS / "luna/plan-final.json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(list(json.loads(completed.stdout)), RECEIPT_KEYS)
        self.assertIn("not recorded: no ShipLoop run at", completed.stderr)
        self.assertEqual(list(self.elsewhere.iterdir()), [])
        self.assertFalse((self.run / "backchain").exists())

    def test_help_lists_the_verb(self):
        self.assertIn("backchain-check", self.cli("--help").stdout)


class PacketLineTests(unittest.TestCase):
    def test_the_line_is_in_backchain_producer_routes_only(self):
        for stage in prompts.DUTIES:
            for delegation in prompts.DELEGATIONS:
                with self.subTest(stage=stage, delegation=delegation):
                    expected = int(stage in prompts.BACKCHAIN_STAGES)
                    self.assertEqual(prompts.prompt(stage, delegation=delegation).count(prompts.BACKCHAIN_CHECK),
                                     expected)
                    self.assertNotIn("backchain-check", prompts.improve_prompt(stage, delegation=delegation))

    def test_the_line_size_is_pinned(self):
        self.assertEqual(prompts.BACKCHAIN_CHECK.count("\n"), 1)
        self.assertEqual(len(prompts.BACKCHAIN_CHECK.encode("utf-8")), 131)


if __name__ == "__main__":
    unittest.main()
