#!/usr/bin/env python3
"""Behavioral acceptance tests for the Markdown-authoritative ShipLoop CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
CLI = SCRIPTS / "shiploop"


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-protocol-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "Protocol Test")
        self.git("config", "user.email", "protocol@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")
        self.run_dir = self.repo / ".shiploop"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        p = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            capture_output=True,
            text=True,
            env=getattr(self, "env", None),
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def cli(self, *args, code=0):
        p = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return p

    def record(self, name, data):
        import shiploop_store

        path = self.root / name
        shiploop_store.write_record(path, data)
        return str(path)

    def state(self):
        import shiploop_store

        return shiploop_store.read_record(self.run_dir / "state.md")

    def test_new_run_is_markdown_authoritative_and_compact(self):
        out = self.cli(
            "init", "--repo", str(self.repo), "--prompt", "Build a tested file"
        ).stdout
        self.assertTrue((self.run_dir / "state.md").is_file())
        self.assertFalse((self.run_dir / "state.json").exists())
        self.assertEqual(self.state()["stage"], "preflight")
        self.assertLess(len(out), 7000)
        before = self.state()["action"]["id"]
        self.cli("next")
        self.assertEqual(self.state()["action"]["id"], before)

    def test_stale_and_replayed_completion(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build a tested file")
        action = self.state()["action"]["id"]
        result = self.record(
            "preflight.md",
            {
                "summary": "Use committed baseline; runtime available",
                "baseline": "committed-head",
            },
        )
        self.cli("complete", "--action", "stale", "--result", result, code=2)
        self.cli("complete", "--action", action, "--result", result)
        revision = self.state()["revision"]
        self.cli("complete", "--action", action, "--result", result)
        self.assertEqual(self.state()["revision"], revision)
        other = self.record(
            "conflict.md", {"summary": "different", "baseline": "committed-head"}
        )
        self.cli("complete", "--action", action, "--result", other, code=2)

    def test_bare_complete_cannot_certify_work(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build a tested file")
        self.cli("complete", code=2)
        self.assertEqual(self.state()["stage"], "preflight")

    def test_json_cannot_override_markdown(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build a tested file")
        (self.run_dir / "state.json").write_text(json.dumps({"phase": "done"}))
        self.cli("next")
        self.assertEqual(self.state()["phase"], "intake")

    def test_missing_authority_is_not_replaced_by_json(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build a tested file")
        (self.run_dir / "state.json").write_text(json.dumps({"phase": "done"}))
        (self.run_dir / "state.md").unlink()
        self.cli("next", code=2)

    def test_deleted_authority_cannot_be_reinitialized(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Preserve this run")
        (self.run_dir / "state.md").unlink()
        self.cli("init", "--repo", str(self.repo), "--prompt", "Do not replace", code=2)
        self.assertIn("Preserve", (self.run_dir / "prompt.md").read_text())

    def test_pause_resume_preserves_action_and_no_fake_success(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        action = self.state()["action"]["id"]
        self.cli("pause", "--reason", "Runtime needs user input")
        result = self.record(
            "ready.md", {"summary": "ready", "baseline": "committed-head"}
        )
        self.cli("complete", "--action", action, "--result", result, code=2)
        self.cli("next")
        self.assertEqual(action, self.state()["action"]["id"])
        self.cli("resume")
        self.cli("complete", "--action", action, "--result", result)
        self.assertEqual(self.state()["stage"], "approach")

    def test_init_repo_selects_its_run_directory(self):
        other = self.root / "other-repo"
        other.mkdir()
        self.cli("init", "--repo", str(other), "--prompt", "Build there")
        self.assertTrue((other / ".shiploop/state.md").is_file())
        self.assertFalse((self.run_dir / "state.md").exists())

    def test_concurrent_init_keeps_one_run_and_original_prompt(self):
        command = [sys.executable, str(CLI), "init", "--repo", str(self.repo)]
        one = subprocess.Popen(
            command + ["--prompt", "first"],
            cwd=self.repo,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        two = subprocess.Popen(
            command + ["--prompt", "second"],
            cwd=self.repo,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out1, err1 = one.communicate(timeout=15)
        out2, err2 = two.communicate(timeout=15)
        self.assertEqual(one.returncode, 0, err1)
        self.assertEqual(two.returncode, 0, err2)
        self.assertIn(self.state()["action"]["id"], out1)
        self.assertIn(self.state()["action"]["id"], out2)
        self.assertEqual(
            (self.run_dir / "prompt.md").read_text().strip(), self.state()["prompt"]
        )

    def test_explicit_migration_archives_all_legacy_sidecars(self):
        self.run_dir.mkdir()
        old = {
            "version": 2,
            "run_id": "legacy-01",
            "phase": "intake",
            "repo_root": str(self.repo),
            "prompt": "old",
        }
        (self.run_dir / "state.json").write_text(json.dumps(old))
        (self.run_dir / "spec.json").write_text('{"legacy":true}')
        (self.run_dir / "package.json").write_text('{"name":"user-owned"}')
        (self.run_dir / "history.jsonl").write_text('{"event":"init"}\n')
        self.cli("next", code=2)
        self.cli("migrate")
        self.assertEqual(self.state()["stage"], "preflight")
        self.assertEqual(
            json.loads((self.run_dir / "legacy-backup/state.json").read_text()), old
        )
        self.assertTrue((self.run_dir / "legacy-backup/spec.json").exists())
        self.assertFalse((self.run_dir / "spec.json").exists())
        self.assertEqual(
            (self.run_dir / "package.json").read_text(), '{"name":"user-owned"}'
        )
        self.assertFalse((self.run_dir / "history.jsonl").exists())
        (self.run_dir / "state.md").unlink()
        (self.run_dir / "state.json").write_text(json.dumps(old))
        self.cli("migrate", code=2)

    def test_corrupt_active_step_path_is_rejected(self):
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()
        state.update(active_step="../../outside", phase="implement", stage="review")
        state["action"]["stage"] = "review"
        shiploop_store.write_record(self.run_dir / "state.md", state)
        result = self.cli("next", code=2)
        self.assertIn("unsafe active step", result.stderr)

    def test_corrupt_action_path_is_rejected_before_filesystem_work(self):
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()
        state["action"]["id"] = "../../outside"
        shiploop_store.write_record(self.run_dir / "state.md", state)
        result = self.cli("next", code=2)
        self.assertIn("unsafe action ID", result.stderr)
        self.assertFalse((self.root / "outside").exists())

    def test_force_does_not_destroy_journal_or_run(self):
        self.cli("init", "--repo", str(self.repo), "--prompt", "Original")
        original = self.state()
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--prompt",
            "Replacement",
            "--force",
            code=2,
        )
        self.assertEqual(self.state(), original)

    def test_init_does_not_overwrite_unrelated_run_directory_files(self):
        self.run_dir.mkdir()
        (self.run_dir / "prompt.md").write_text("user-owned existing notes")
        self.cli("init", "--repo", str(self.repo), "--prompt", "Overwrite?", code=2)
        self.assertEqual(
            (self.run_dir / "prompt.md").read_text(), "user-owned existing notes"
        )

    def test_planning_revisit_archives_inputs_without_erasing_journal(self):
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        aid = self.state()["action"]["id"]
        self.cli(
            "complete",
            "--action",
            aid,
            "--result",
            self.record("ready.md", {"summary": "ready", "baseline": "committed-head"}),
        )
        aid = self.state()["action"]["id"]
        (self.run_dir / "environment.md").write_text("prior survey to preserve")
        before = (self.run_dir / "shiploop-improvements.md").read_text()
        self.cli(
            "revisit",
            "--action",
            aid,
            "--to",
            "survey",
            "--reason",
            "Correct an incomplete schema before execution",
        )
        self.assertEqual(self.state()["stage"], "survey")
        self.assertFalse((self.run_dir / "environment.md").exists())
        self.assertEqual(
            (self.run_dir / "planning-history" / aid / "environment.md").read_text(),
            "prior survey to preserve",
        )
        self.assertEqual(
            (self.run_dir / "shiploop-improvements.md").read_text(), before
        )
        # Once any work has a receipt, this escape hatch cannot rewrite contracts.
        shiploop_store.write_record(
            self.run_dir / "steps/S1.md", {"status": "complete"}
        )
        self.cli(
            "revisit",
            "--action",
            self.state()["action"]["id"],
            "--to",
            "survey",
            "--reason",
            "unsafe",
            code=2,
        )

    def test_documented_machine_and_dag_templates_validate(self):
        import re
        import runpy
        import shiploop_store

        core = runpy.run_path(str(CLI))
        survey = (SCRIPTS.parent / "references/survey.md").read_text()
        machine = json.loads(re.search(r"~~~json\n(.*?)\n~~~", survey, re.S).group(1))
        self.assertEqual(core["validate_machine"](machine), [])
        self.assertEqual(core["exclusive_gaps"](machine), [])
        self.assertEqual(core["ui_craft_gaps"](machine), [])
        plan = (SCRIPTS.parent / "references/activities/plan.md").read_text()
        blocks = re.findall(r"~~~json\n(.*?)\n~~~", plan, re.S)
        dag = json.loads(
            blocks[1].replace("<frozen mcp_considered>", machine["mcp_considered"])
        )
        fixture = self.root / "documented-templates"
        fixture.mkdir()
        (fixture / "environment.md").write_text(
            "Valid example.\n\n## machine\n~~~json\n" + json.dumps(machine) + "\n~~~\n"
        )
        shiploop_store.write_record(fixture / "backchain/plan.md", dag)
        self.assertEqual(core["dag_gaps"](fixture, {"done_sentence": dag["goal"]}), [])

    def test_commit_action_states_exact_learning_gate(self):
        import shiploop_protocol

        prompt = shiploop_protocol.PROMPTS["commit"]
        self.assertIn("verbatim", prompt)
        self.assertIn("review.learnings", prompt)
        self.assertIn("applied.learnings", prompt)
        self.assertIn("ShipLoop-Iteration", prompt)

    def test_outer_quality_prompt_names_its_exact_acceptance_source(self):
        import shiploop_protocol

        prompt = shiploop_protocol.PROMPTS["quality"]
        self.assertIn("lifecycle.acceptance", prompt)
        self.assertIn("context --section lifecycle", prompt)
        self.assertIn("exact", prompt)

    def test_client_service_invocation_is_frozen_before_communication(self):
        import shiploop_protocol

        survey_guide = (SCRIPTS.parent / "references/survey.md").read_text()
        self.assertIn("## Client–service invocation", survey_guide)
        self.assertIn("before authoring any communication", survey_guide)
        self.assertIn("Service-visible operations", survey_guide)
        self.assertIn("Client call conventions", survey_guide)
        self.assertIn("HTML-style client", survey_guide)
        self.assertIn("substitute exec", survey_guide)

        survey = shiploop_protocol.PROMPTS["survey"]
        self.assertIn("invocation protocol", survey)
        self.assertIn("client/HTML call conventions", survey)
        self.assertIn("before any communication is authored", survey)
        self.assertIn("references/survey.md", survey)

        research = shiploop_protocol.PROMPTS["research"]
        self.assertIn("invocation contract", research)
        self.assertIn("do not author communication yet", research)

        sequence = shiploop_protocol.PROMPTS["sequence"]
        self.assertIn("invocation contract", sequence)
        self.assertIn("before the step that authors call sites", sequence)

        implement = shiploop_protocol.PROMPTS["implement"]
        self.assertIn("real client/HTML invocation path", implement)
        self.assertIn("substitute exec", implement)


if __name__ == "__main__":
    unittest.main()
