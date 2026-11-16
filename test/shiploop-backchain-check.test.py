#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's record-only backchain-check verb.

The structural check itself is skills/shiploop/scripts/backchain_graph.py (Backchain's check, moved into ShipLoop when
the Backchain skill was retired on 2026-11-16); test/backchain-graph.test.py
holds its parity tests against the lib.js verdicts in test/fixtures/backchain-check.
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
import shiploop_backchain_graph as verb  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402


def canon(value) -> str:
    return json.dumps(value, sort_keys=True)


class LocationTests(unittest.TestCase):
    def test_the_verb_checks_with_the_validator_beside_it(self):
        # One validator: the verb imports the module beside it, never a copy of its own.
        expected = (prompts.plugin_skills_root() / "shiploop" / "scripts" / "backchain_graph.py").resolve()
        self.assertEqual(Path(verb.graph.__file__).resolve(), expected)
        self.assertFalse(hasattr(verb, "validate_structure"))


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
                # A model that checked a prose plan learned the schema by reading this checker's source (batch 1009
                # BC1); the message names the document that defines it instead.
                self.assertIn('the Backchain planning guide, "Plan graph format"', unavailable.stderr)
                self.assertIn("not a prose plan", unavailable.stderr)
        missing = self.check(self.base / "absent.json", "--run-dir", str(self.run))
        self.assertEqual((missing.returncode, missing.stdout), (3, ""))
        self.assertEqual(len(list((self.run / "backchain" / self.action).iterdir())), 4)

    def test_a_markdown_candidate_is_told_it_must_be_the_plan_graph_json_and_where_the_shape_is_defined(self):
        # Both round-1 runs passed the Markdown plan note and read "not JSON: Expecting value" with no way forward.
        note = self.base / "plan.md"
        note.write_text("# Plan\n\n1. Build the thing.\n", encoding="utf-8")
        refused = self.check(note, "--run-dir", str(self.run))
        self.assertEqual((refused.returncode, refused.stdout), (3, ""))
        self.assertIn("could not run: not JSON", refused.stderr)
        self.assertIn("the plan graph as a JSON file, not a Markdown plan note", refused.stderr)
        guide = prompts.plugin_skills_root() / "shiploop" / "references" / "backchain-planning.md"
        self.assertIn(f"{guide}#plan-graph-format", refused.stderr)
        self.assertIn("## Plan graph format\n", guide.read_text(encoding="utf-8"))
        self.assertIn("this is not a finding", refused.stderr)
        absent = self.check(self.base / "absent.json", "--run-dir", str(self.run))
        self.assertEqual(absent.returncode, 3)
        self.assertNotIn("generator.v1.md", absent.stderr)  # only a file that is not JSON is told what to write instead

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
        """Every Backchain producer route whose check stands on its own carries the check sentence once; an inline
        step-plan or carry-forward and product-acceptance print no route paragraph, and no Improve packet names the
        check.  No route requests a Backchain child (Backchain retired, owner decision 2026-11-16)."""
        check = prompts._BACKCHAIN_CHECK
        reads = "The printed `backchain-check` reads only a candidate graph"
        for stage in prompts.DUTIES:
            for delegation in prompts.DELEGATIONS:
                with self.subTest(stage=stage, delegation=delegation):
                    no_paragraph = (stage in prompts.INLINE_AUDIT_STAGES and delegation == prompts.INLINE
                                    or stage in prompts.AUDIT_LINE_STAGES)
                    # The spec and plan duties fold the Backchain item (packet re-cut, 2026-10-11): the check
                    # instruction is a duty item there, and prompt() prints no second copy of the route paragraph.
                    folded = stage in prompts.BACKCHAIN_FOLDED_STAGES
                    packet = prompts.prompt(stage, delegation=delegation)
                    in_backchain = stage in prompts.BACKCHAIN_STAGES
                    self.assertEqual(packet.count(check), int(in_backchain and not no_paragraph and not folded))
                    self.assertEqual(" ".join(packet.split()).count(reads), int(in_backchain and not no_paragraph))
                    if folded:
                        self.assertIn("receipt", packet)
                    self.assertNotIn("backchain-check", prompts.improve_prompt(stage, delegation=delegation))


if __name__ == "__main__":
    unittest.main()
