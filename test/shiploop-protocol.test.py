#!/usr/bin/env python3
"""Behavioral acceptance tests for the Markdown-authoritative ShipLoop CLI."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shiploop_test_support import report_advisory_size

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
CLI = SCRIPTS / "shiploop"


class ProtocolTests(unittest.TestCase):
    def assert_guidance_path(self, packet, guidance, reference):
        """Resolve shared-directory guidance to the same concrete source file."""
        candidate = Path(guidance.split("read only ", 1)[1].split("#", 1)[0])
        if not candidate.is_absolute():
            directory = next(line for line in packet.splitlines()
                             if line.startswith("Guidance directory: "))
            directory = directory.removeprefix("Guidance directory: ").removesuffix(
                " (resolve the following filenames here)."
            )
            self.assertTrue(Path(directory).is_absolute())
            candidate = Path(directory) / candidate
        self.assertEqual(candidate, reference)
        self.assertTrue(candidate.is_file())

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
        args = list(args)
        if args[:1] == ["init"] and not any(
            arg == "--execution-mode" or arg.startswith("--execution-mode=")
            for arg in args
        ):
            args.extend(("--execution-mode", "managed"))
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

    def bind_current_local_environment(self, state):
        """Bind a valid local-only environment for current-protocol packets."""
        machine = {
            "kind": "greenfield",
            "augment": False,
            "references": [],
            "tools": [],
            "mcp": [],
            "mcp_considered": "none(local packet fixture)",
            "handles": [],
            "initiation": "none",
            "ui": False,
            "ui_craft": "none(local packet fixture)",
            "exclusive": [],
            "platform_discovery": {
                "version": 1,
                "applicable": False,
                "rationale": "This packet fixture changes only local repository artifacts.",
                "platforms": [],
            },
        }
        body = (
            "Current local packet fixture.\n\n## machine\n```json\n"
            + json.dumps(machine)
            + "\n```\n"
        )
        path = self.run_dir / "environment.md"
        path.write_text(body, encoding="utf-8")
        state["environment_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    def converge_approach_objective(self, candidate, *, label):
        """Finalize an imported approach through the public objective actions.

        The draft-deletion fixtures below deliberately use this rather than
        bypassing the new generic objective.  That keeps their durable-record
        assertion meaningful: the original result draft may disappear while
        the candidate snapshot, two audited passes, and fresh final check
        remain sufficient to apply the approach exactly once.
        """
        import shiploop_objectives as objectives
        import shiploop_store

        def complete(value, name):
            self.cli(
                "complete",
                "--action",
                self.state()["action"]["id"],
                "--result",
                self.record(name, value),
            )

        def manifest(name):
            return self.record(
                name,
                {
                    "checks": [
                        {
                            "id": "objective-lint",
                            "kind": "lint",
                            "argv": ["/usr/bin/true"],
                            "acceptance": ["objective approach"],
                        },
                        {
                            "id": "objective-acceptance",
                            "kind": "test",
                            "argv": ["/usr/bin/true"],
                            "acceptance": ["objective approach"],
                        },
                    ]
                },
            )

        for number in (1, 2):
            state = self.state()
            self.assertEqual(state["stage"], "objective-review")
            self.cli(
                "history",
                "--run-dir",
                str(self.run_dir),
                "--action",
                state["action"]["id"],
                "--limit",
                "10",
                "--skip",
                "0",
                "--full",
            )
            review_learning = (
                f"{label} objective review {number} read the current full Git history "
                "and durable approach candidate."
            )
            complete(
                {
                    "summary": f"{label} objective review {number} is complete.",
                    "findings": [],
                    "assessment": {
                        key: f"{key} was inspected against the durable approach candidate."
                        for key in objectives.ASSESSMENT_KEYS
                    },
                    "history_assessment": "All currently available full commit bodies were read before this decision.",
                    "test_review": "A local lint and acceptance check cover the frozen approach candidate.",
                    "learnings": review_learning,
                },
                f"{label}-objective-{number}-review.md",
            )
            self.assertEqual(self.state()["stage"], "objective-plan")
            plan_learning = (
                f"{label} objective plan {number} retains the frozen candidate because "
                "there are no open findings."
            )
            complete(
                {
                    "summary": f"{label} objective plan {number} is complete.",
                    "addresses": [],
                    "body": "# Objective plan\n\nNo open findings require a candidate change.\n",
                    "learnings": plan_learning,
                },
                f"{label}-objective-{number}-plan.md",
            )
            self.assertEqual(self.state()["stage"], "objective-apply")
            apply_learning = (
                f"{label} objective apply {number} retains the exact imported "
                "approach candidate without product changes."
            )
            complete(
                {
                    "summary": f"{label} objective apply {number} retains the candidate.",
                    "candidate": dict(candidate),
                    "material": False,
                    "addresses": [],
                    "resolutions": [],
                    "test_changes": "The existing local objective lint and acceptance checks remain sufficient.",
                    "learnings": apply_learning,
                },
                f"{label}-objective-{number}-apply.md",
            )
            self.assertEqual(self.state()["stage"], "objective-verify")
            verify_action = self.state()["action"]["id"]
            self.cli(
                "planning-verify",
                "--run-dir",
                str(self.run_dir),
                "--action",
                verify_action,
                "--manifest",
                manifest(f"{label}-objective-{number}-checks.md"),
            )
            complete(
                {"summary": f"{label} objective checks {number} pass."},
                f"{label}-objective-{number}-verify.md",
            )
            self.assertEqual(self.state()["stage"], "objective-commit")
            state = self.state()
            receipt = shiploop_store.read_record(
                self.run_dir / state["objective"]["receipt"]
            )
            current = receipt["current_pass"]
            message = "\n\n".join(
                (
                    f"Objective approach audit {number}",
                    "Review:\n" + review_learning,
                    "Changes:\n" + plan_learning + "\n" + apply_learning,
                    "Validation:\nThe local lint and acceptance commands passed without source changes.",
                    "Key learnings:\n" + review_learning + "\n" + plan_learning + "\n" + apply_learning,
                    "ShipLoop-Iteration: " + current["id"],
                )
            )
            self.git("commit", "--allow-empty", "--only", "-m", message)
            commit = self.git("rev-parse", "HEAD")
            complete(
                {
                    "summary": f"{label} objective audit {number} is recorded.",
                    "commit": commit,
                },
                f"{label}-objective-{number}-commit.md",
            )

        self.assertEqual(self.state()["stage"], "objective-finalize")
        final_action = self.state()["action"]["id"]
        self.cli(
            "planning-verify",
            "--run-dir",
            str(self.run_dir),
            "--action",
            final_action,
            "--manifest",
            manifest(f"{label}-objective-final-checks.md"),
        )
        complete(
            {"summary": f"{label} fresh final objective check passes."},
            f"{label}-objective-finalize.md",
        )
        self.assertEqual(self.state()["stage"], "survey")

    def test_new_run_is_markdown_authoritative_and_compact(self):
        out = self.cli(
            "init", "--repo", str(self.repo), "--prompt", "Build a tested file"
        ).stdout
        self.assertTrue((self.run_dir / "state.md").is_file())
        self.assertFalse((self.run_dir / "state.json").exists())
        self.assertEqual(self.state()["stage"], "preflight")
        report_advisory_size("bootstrap packet", out, 7000)
        before = self.state()["action"]["id"]
        self.cli("next")
        self.assertEqual(self.state()["action"]["id"], before)

    def test_legacy_upstream_research_next_enables_the_future_step_gate_without_repair(self):
        """A missing per-step marker cannot replay or repair work before allocation."""
        import shiploop_protocol
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        before = self.state()
        legacy = dict(before)
        legacy.update(
            phase="validate-spec",
            stage="research",
            action={"id": "legacy-research", "stage": "research"},
        )
        legacy.pop("step_planning_protocol_version", None)
        shiploop_store.write_record(self.run_dir / "state.md", legacy)

        packet = self.cli("next").stdout
        after = self.state()
        self.assertEqual(after["stage"], "research")
        self.assertEqual(after["action"], legacy["action"])
        self.assertFalse(after.get("active_step"))
        self.assertEqual(
            after["step_planning_protocol_version"],
            shiploop_protocol.STEP_PLANNING_PROTOCOL_VERSION,
        )
        self.assertEqual(after["revision"], before["revision"] + 1)
        self.assertNotIn("repair", packet.lower())
        history = shiploop_store.read_record(self.run_dir / "history.md")
        self.assertEqual(history[-1]["event"], "step-plan-legacy-enable-upstream")

    def test_legacy_active_read_only_commands_do_not_create_a_gate_or_move_cursor(self):
        """Inspection must not turn a legacy active implement into a new action."""
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()
        run_id = state["run_id"]
        worktree = Path(state["repo_root"]) / ".worktrees" / "shiploop" / run_id / "S1"
        worktree.mkdir(parents=True)
        (self.run_dir / "steps").mkdir()
        shiploop_store.write_record(
            self.run_dir / "steps/S1.md",
            {
                "id": "S1",
                "run_id": run_id,
                "worktree": str(worktree),
                "branch": f"shiploop/{run_id}/S1",
                "base_sha": self.git("rev-parse", "HEAD"),
            },
        )
        state.update(
            active_step="S1",
            phase="implement",
            stage="implement",
            action={"id": "legacy-implement", "stage": "implement"},
        )
        state.pop("step_planning_protocol_version", None)
        shiploop_store.write_record(self.run_dir / "state.md", state)
        before = (self.run_dir / "state.md").read_bytes()

        self.cli("status")
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        self.cli("context", "--section", "prompt", "--offset", "0", "--limit", "4000")
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        self.cli("plan-status", "--loop", "legacy-loop", code=2)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before)
        self.assertNotIn("step_planning_protocol_version", self.state())
        self.assertEqual(self.state()["action"], state["action"])

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
        command = [
            sys.executable, str(CLI), "init", "--repo", str(self.repo),
            "--execution-mode", "managed",
        ]
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
            (self.run_dir / "planning-history" / aid / "revisit-survey" / "environment.md").read_text(),
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
        self.assertIn("carry-forward", prompt)
        self.assertIn("ShipLoop-Iteration", prompt)

    def test_carry_forward_prompt_requires_a_safe_explicit_checkpoint(self):
        import shiploop_protocol

        prompt = shiploop_protocol.PROMPTS["carry-forward"]
        self.assertIn("discoveries", prompt)
        self.assertIn("learnings", prompt)
        self.assertIn("explicit []", prompt)
        self.assertIn("credential", prompt)
        self.assertIn("pause", prompt)
        self.assertNotIn("knowledge_revision", prompt)

    def test_implement_packet_only_requires_knowledge_after_initialization(self):
        import contextlib
        import io
        import runpy
        from types import SimpleNamespace

        import shiploop_knowledge
        import shiploop_protocol
        import shiploop_store

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        current = self.state()
        run_id = current["run_id"]
        worktree = (
            Path(current["repo_root"])
            / ".worktrees"
            / "shiploop"
            / run_id
            / "S1"
        )
        (self.run_dir / "steps").mkdir()
        shiploop_store.write_record(
            self.run_dir / "steps/S1.md",
            {
                "id": "S1",
                "run_id": run_id,
                "worktree": str(worktree),
                "branch": f"shiploop/{run_id}/S1",
                "base_sha": self.git("rev-parse", "HEAD"),
            },
        )
        current.update(
            active_step="S1",
            phase="implement",
            stage="implement",
            action={"id": "current-implement", "stage": "implement"},
        )
        core = SimpleNamespace(**runpy.run_path(str(CLI)))

        # A mapped future obligation remains visible, but it is no longer an
        # unmapped post-inner blocker. Build it through the public ledger
        # primitives so this packet fixture stays structurally realistic.
        def source(action):
            return {
                "action": action,
                "iteration": "I1",
                "check_action": "check-I1",
                "worktree_fingerprint": "fixture-fingerprint",
                "step": "S1",
                "reported_by": "host",
                "recorded_at": "2026-09-11T00:00:00Z",
            }

        checkpoint = shiploop_knowledge.validate_result(
            {
                "summary": "Schedule the future contract check.",
                "knowledge_revision": 0,
                "learnings": "Keep the scheduled future check visible.",
                "discoveries": [
                    {
                        "id": "future-contract-check",
                        "domain": "invocation-contract",
                        "observation": "S2 needs a fresh contract check.",
                        "evidence": "fixture receipt",
                        "scope": ["S2"],
                        "disposition": "pending-replan",
                        "rationale": "Schedule the check before S2.",
                        "revalidate": "Confirm the contract in S2.",
                    }
                ],
            },
            expected_revision=0,
            step_ids={"S1", "S2"},
        )
        ledger = shiploop_knowledge.apply_result(
            shiploop_knowledge.empty_ledger(), checkpoint, source("checkpoint")
        )
        ledger = shiploop_knowledge.map_pending_obligations(
            ledger,
            {"future-contract-check": ["S2"]},
            source("knowledge-map"),
        )
        body = shiploop_knowledge.render(ledger)
        (self.run_dir / "knowledge.md").write_text(body)
        current.update(
            knowledge_revision=ledger["revision"],
            knowledge_sha256=shiploop_knowledge.sha256_bytes(body.encode()),
            knowledge_action_id="knowledge-map",
        )
        self.bind_current_local_environment(current)

        legacy = dict(current)
        for key in (
            "carry_forward_protocol_version",
            "knowledge_revision",
            "knowledge_sha256",
            "knowledge_action_id",
            "platform_revalidation_protocol_version",
        ):
            legacy.pop(key, None)
        legacy["action"] = {"id": "legacy-implement", "stage": "implement"}
        # Model the old initial implementation packet precisely: it has no
        # ledger file or state binding, so the generic prompt must not issue
        # an impossible knowledge-context command.
        (self.run_dir / "knowledge.md").unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            shiploop_protocol.packet(core, self.run_dir, legacy)
        legacy_packet = output.getvalue()
        self.assertIn("Carry-forward protocol is absent", legacy_packet)
        self.assertNotIn("context --section knowledge", legacy_packet)

        (self.run_dir / "knowledge.md").write_text(body)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            shiploop_protocol.packet(core, self.run_dir, current)
        current_packet = output.getvalue()
        self.assertIn("Cold-start requirement: read current knowledge", current_packet)
        self.assertIn("context --section knowledge", current_packet)
        self.assertIn(
            "unmapped obligations 0 | scheduled obligations 1", current_packet
        )

    def test_current_packet_blocks_without_a_frozen_environment(self):
        import contextlib
        import io
        import runpy
        from types import SimpleNamespace

        import shiploop_protocol

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        state = self.state()
        state.update(phase="test", stage="prepare")
        state["action"] = {"id": "current-missing-environment", "stage": "prepare"}
        core = SimpleNamespace(**runpy.run_path(str(CLI)))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            shiploop_protocol.packet(core, self.run_dir, state)
        packet = output.getvalue()

        self.assertIn(
            "Blocked: current platform revalidation requirements cannot be read safely",
            packet,
        )
        self.assertIn("missing", packet)
        self.assertNotIn("Call this when done:", packet)
        self.assertIn("No completion callback is valid", packet)

    def test_implementation_test_context_returns_none_without_an_accepted_action(self):
        import shiploop_protocol

        self.run_dir.mkdir()
        state = {"completed_actions": {}}
        rec = {"id": "S1"}

        self.assertIsNone(
            shiploop_protocol.implementation_test_context(self.run_dir, state, rec)
        )
        self.assertFalse((self.run_dir / "results").exists())

    def test_implementation_test_context_projects_bound_historical_notes_read_only(self):
        import shiploop_protocol
        import shiploop_store

        self.run_dir.mkdir()
        action = "initial-implement"
        result = {
            "summary": "Initial implementation test notes were recorded.",
            "test_review": "T-API-001 passed in the target test environment.",
        }
        result_path = self.run_dir / "results" / f"{action}.md"
        result_path.parent.mkdir()
        shiploop_store.write_record(result_path, result)
        state = {"completed_actions": {action: shiploop_protocol.digest(result)}}
        rec = {"implementation_check_action": action}
        before_state = json.loads(json.dumps(state))
        before_rec = dict(rec)
        before_markdown = result_path.read_text()

        context = shiploop_protocol.implementation_test_context(
            self.run_dir, state, rec
        )

        self.assertEqual(
            context,
            {
                "action": action,
                "source": f"results/{action}.md",
                "status": "historical host-reported notes; recheck current code and tests",
                "summary": result["summary"],
                "test_review": result["test_review"],
            },
        )
        self.assertEqual(state, before_state)
        self.assertEqual(rec, before_rec)
        self.assertEqual(result_path.read_text(), before_markdown)

    def test_implementation_test_context_rejects_tampered_or_unsafe_records(self):
        import shiploop_protocol
        import shiploop_store

        self.run_dir.mkdir()
        action = "initial-implement"
        rec = {"implementation_check_action": action}
        with self.assertRaisesRegex(
            shiploop_protocol.ProtocolError, "accepted implementation test result is missing"
        ):
            shiploop_protocol.implementation_test_context(
                self.run_dir, {"completed_actions": {}}, rec
            )

        result_path = self.run_dir / "results" / f"{action}.md"
        result_path.parent.mkdir()
        accepted = {
            "summary": "Accepted initial implementation notes.",
            "test_review": "T-UI-001 was recorded.",
        }
        shiploop_store.write_record(result_path, accepted)
        state = {"completed_actions": {action: shiploop_protocol.digest(accepted)}}
        shiploop_store.write_record(
            result_path,
            {
                "summary": "Tampered initial implementation notes.",
                "test_review": accepted["test_review"],
            },
        )
        with self.assertRaisesRegex(
            shiploop_protocol.ProtocolError, "digest mismatch"
        ):
            shiploop_protocol.implementation_test_context(self.run_dir, state, rec)

        with self.assertRaisesRegex(
            shiploop_protocol.ProtocolError, "action is invalid"
        ):
            shiploop_protocol.implementation_test_context(
                self.run_dir,
                {"completed_actions": {}},
                {"implementation_check_action": "../outside"},
            )

        symlink_root = self.root / "symlink-run"
        symlink_root.mkdir()
        external_results = self.root / "external-results"
        external_results.mkdir()
        (symlink_root / "results").symlink_to(
            external_results, target_is_directory=True
        )
        with self.assertRaisesRegex(
            shiploop_protocol.ProtocolError, "run path contains a symlink"
        ):
            shiploop_protocol.implementation_test_context(
                symlink_root,
                {"completed_actions": {}},
                rec,
            )

    def test_outer_quality_prompt_names_its_exact_acceptance_source(self):
        import shiploop_protocol

        prompt = shiploop_protocol.PROMPTS["quality"]
        self.assertIn("lifecycle.acceptance", prompt)
        self.assertIn("context --section lifecycle", prompt)
        self.assertIn("exact", prompt)

    def test_test_refinement_prompts_keep_cases_adequate_and_acceptance_intact(self):
        import re

        import shiploop_protocol

        implementation = shiploop_protocol.PROMPTS["implement"].lower()
        code = implementation.index("code")
        post_code = implementation.index("post-code")
        author = implementation.index("then author", post_code)
        executable_tests = implementation.index("executable tests")
        execute = implementation.index("execute")
        fix = implementation.index("fix")
        self.assertLess(code, post_code)
        self.assertLess(post_code, author)
        self.assertLess(author, executable_tests)
        self.assertLess(executable_tests, execute)
        self.assertLess(execute, fix)
        self.assertIn("implementation learnings", implementation)

        review = shiploop_protocol.PROMPTS["review"]
        self.assertRegex(review, re.compile(r"missing.{0,80}tests?", re.IGNORECASE))
        self.assertIn("adequacy", review.lower())

        apply = shiploop_protocol.PROMPTS["improve-apply"].lower()
        for concept in (
            "authored",
            "updated",
            "reused",
            "test correction",
            "old/new expectation",
            "independent requirement evidence",
            "preserved coverage",
            "never weaken acceptance",
        ):
            self.assertIn(concept, apply)

        verify = shiploop_protocol.PROMPTS["verify"].lower()
        for concept in ("failed", "blocked", "unrun", "weaken", "acceptance"):
            self.assertIn(concept, verify)

    def test_packet_routes_testing_docs_guidance_without_expanding_contract(self):
        import contextlib
        import io
        import re
        import runpy
        from types import SimpleNamespace

        import shiploop_protocol

        expected = {
            "managed-improve": ("managed-improve-checkpoints",),
            "preflight": ("surface-selection",),
            "survey": ("surface-selection",),
            "prepare": ("surface-selection",),
            "research": ("surface-selection",),
            "research-review": ("iteration",),
            "research-plan": ("iteration",),
            "research-apply": ("iteration",),
            "research-verify": ("test-cases",),
            "research-commit": ("iteration",),
            "research-finalize": ("test-cases",),
            "spec": ("test-cases", "surface-selection"),
            "behavior-review": ("iteration",),
            "behavior-plan": ("iteration",),
            "behavior-apply": ("iteration",),
            "behavior-verify": ("test-cases",),
            "behavior-commit": ("iteration",),
            "behavior-finalize": ("test-cases",),
            "spec-review": ("iteration",),
            "spec-plan": ("iteration",),
            "spec-apply": ("iteration",),
            "spec-verify": ("test-cases",),
            "spec-commit": ("iteration",),
            "spec-finalize": ("test-cases",),
            "sequence": ("test-cases", "documentation"),
            "step-plan": ("implementation-constitution",),
            "step-plan-review": ("implementation-constitution",),
            "step-plan-revise": ("implementation-constitution",),
            "implement": ("iteration", "implementation-constitution"),
            "review": ("iteration", "implementation-constitution"),
            "improve-plan": ("iteration", "implementation-constitution"),
            "improve-plan-verify": ("managed-improve-checkpoints", "implementation-constitution"),
            "improve-apply": ("iteration", "implementation-constitution"),
            "test-refine": ("managed-improve-checkpoints", "implementation-constitution"),
            "test-author": ("managed-improve-checkpoints", "implementation-constitution"),
            "skill-validate": ("managed-improve-checkpoints", "implementation-constitution"),
            "iteration-document": ("iteration-documentation-and-reuse", "implementation-constitution"),
            "carry-forward": ("iteration",),
            "commit": ("iteration",),
            "post-inner": ("iteration",),
            "verify": ("test-cases", "implementation-constitution"),
            "final-verify": ("test-cases",),
            "quality": ("deployment-and-handoff",),
            "publish": ("deployment-and-handoff",),
            "handoff": ("deployment-and-handoff",),
        }
        no_guidance = {
            "approach",
            "behavior",
            "merge",
            "coverage",
            "objective-review",
            "objective-plan",
            "objective-apply",
            "objective-verify",
            "objective-commit",
            "objective-finalize",
            "step-plan-disposition",
            "step-plan-verify",
            "step-plan-commit",
            "step-plan-finalize",
        }
        self.assertEqual(shiploop_protocol.TEST_DOC_SECTIONS, expected)
        self.assertEqual(
            set(shiploop_protocol.PROMPTS), set(expected) | no_guidance
        )

        core = SimpleNamespace(**runpy.run_path(str(CLI)))
        reference = core.REF_DIR / "testing-and-documentation.md"
        self.assertEqual(
            reference, SCRIPTS.parent / "references/testing-and-documentation.md"
        )
        self.assertTrue(reference.is_file())
        available_anchors = {
            re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", reference.read_text())
        }
        expected_anchors = {anchor for anchors in expected.values() for anchor in anchors}
        self.assertTrue(expected_anchors <= available_anchors)

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        base = self.state()
        planning_stages = {
            "research",
            "research-review",
            "research-plan",
            "research-apply",
            "research-verify",
            "research-commit",
            "research-finalize",
            "behavior",
            "behavior-review",
            "behavior-plan",
            "behavior-apply",
            "behavior-verify",
            "behavior-commit",
            "behavior-finalize",
            "spec",
            "spec-review",
            "spec-plan",
            "spec-apply",
            "spec-verify",
            "spec-commit",
            "spec-finalize",
            "step-plan",
            "step-plan-review",
            "step-plan-disposition",
            "step-plan-revise",
            "step-plan-verify",
            "step-plan-commit",
            "step-plan-finalize",
            "objective-review",
            "objective-plan",
            "objective-apply",
            "objective-verify",
            "objective-commit",
            "objective-finalize",
        }
        state_bound_stages = {"managed-improve", "sequence", "commit", "final-verify"}
        for stage in shiploop_protocol.PROMPTS:
            with self.subTest(stage=stage):
                # Planning packets need a real planning receipt; their bounded
                # Objective/Until contract is exercised through public CLI in
                # shiploop-planning.test.py.  This table still locks their
                # reference routing to the shared prompt map.
                if stage in planning_stages | state_bound_stages:
                    continue
                state = dict(base)
                # This table isolates static guidance routing for the legacy
                # packet shape. Current runs have a separate missing-
                # environment block assertion above.
                state.pop("platform_revalidation_protocol_version")
                state.update(phase="test", stage=stage)
                state["action"] = {"id": f"packet-{stage}", "stage": stage}
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    shiploop_protocol.packet(core, self.run_dir, state)
                packet = output.getvalue()
                guidance = [
                    line
                    for line in packet.splitlines()
                    if line.startswith("Testing/docs guidance:")
                ]

                report_advisory_size(f"packet stage {stage}", packet, 7000)
                self.assertIn(f"Action: packet-{stage}", packet)
                self.assertIn("Bounded context:", packet)
                self.assertIn("Result format:", packet)
                self.assertIn("When done:", packet)
                self.assertIn(f"--action packet-{stage}", packet)
                self.assertIn(
                    f"--result {self.run_dir / 'inbox' / f'packet-{stage}.md'}",
                    packet,
                )
                if stage in expected:
                    self.assertEqual(len(guidance), 1)
                    report_advisory_size(f"testing/docs guidance {stage}", guidance[0], 500)
                    self.assert_guidance_path(packet, guidance[0], reference)
                    self.assertEqual(
                        set(re.findall(r"#([a-z0-9-]+)", guidance[0])),
                        set(expected[stage]),
                    )
                else:
                    self.assertEqual(guidance, [])

    def test_approach_test_docs_record_survives_draft_deletion_across_processes(self):
        self.cli(
            "init", "--repo", str(self.repo), "--execution-mode", "legacy",
            "--prompt", "Build",
        )
        preflight = self.state()["action"]["id"]
        self.cli(
            "complete",
            "--action",
            preflight,
            "--result",
            self.record(
                "preflight.md",
                {"summary": "Committed baseline is available", "baseline": "committed-head"},
            ),
        )
        self.assertEqual(self.state()["stage"], "approach")

        approach_body = """## Test case

TC-context-docs: Given a fresh process after its approach draft is deleted,
`context --section approach` returns the saved expected outcome and docs decision.
Expected outcome: the durable Markdown record remains readable without JSON state.

## Documentation decision

Document the behavior beside the existing protocol guidance; no separate result
schema or sidecar is needed.
""".strip()
        approach_candidate = {
            "summary": "Stored test case and documentation decision",
            "body": approach_body,
        }
        approach_draft = Path(self.record("approach-draft.md", approach_candidate))
        self.cli(
            "complete",
            "--action",
            self.state()["action"]["id"],
            "--result",
            str(approach_draft),
        )
        state = self.state()
        self.assertEqual(state["stage"], "objective-review")
        candidate_path = self.run_dir / state["objective"]["candidate"]
        self.assertTrue(candidate_path.is_file())

        approach_draft.unlink()
        self.assertFalse(approach_draft.exists())
        self.assertTrue(candidate_path.is_file())
        self.converge_approach_objective(approach_candidate, label="test-docs")
        self.assertEqual((self.run_dir / "approach.md").read_text(), approach_body)
        packet = self.cli("next").stdout
        self.assertIn("Action:", packet)
        self.assertIn("Testing/docs guidance:", packet)
        self.assertIn("#surface-selection", packet)

        context = self.cli(
            "context", "--section", "approach", "--offset", "0", "--limit", "4000"
        ).stdout
        self.assertIn("TC-context-docs", context)
        self.assertIn("Expected outcome:", context)
        self.assertIn("no separate result", context)
        self.assertNotIn("shiploop-state", (self.run_dir / "approach.md").read_text())
        self.assertFalse((self.run_dir / "state.json").exists())
        self.assertFalse((self.run_dir / "approach.json").exists())

    def test_packet_routes_behavior_model_guidance_without_expanding_contract(self):
        import contextlib
        import io
        import re
        import runpy
        from types import SimpleNamespace

        import shiploop_protocol

        expected = {
            "approach": ("discovery-and-research",),
            "survey": ("discovery-and-research",),
            "behavior": ("behavior-model",),
            "behavior-review": ("traceability-and-review",),
            "behavior-plan": ("traceability-and-review",),
            "behavior-apply": ("traceability-and-review",),
            "behavior-verify": ("traceability-and-review",),
            "behavior-commit": ("traceability-and-review",),
            "behavior-finalize": ("traceability-and-review",),
            "spec": ("behavior-model",),
            "spec-review": ("traceability-and-review",),
            "spec-plan": ("traceability-and-review",),
            "spec-apply": ("traceability-and-review",),
            "spec-verify": ("traceability-and-review",),
            "spec-commit": ("traceability-and-review",),
            "spec-finalize": ("traceability-and-review",),
            "sequence": ("traceability-and-review",),
            "implement": ("traceability-and-review",),
            "review": ("traceability-and-review",),
            "improve-plan": ("traceability-and-review",),
            "improve-apply": ("traceability-and-review",),
            "iteration-document": ("traceability-and-review",),
            "verify": ("traceability-and-review",),
            "carry-forward": ("traceability-and-review",),
            "final-verify": ("traceability-and-review",),
            "post-inner": ("traceability-and-review",),
            "quality": ("traceability-and-review",),
            "handoff": ("traceability-and-review",),
        }
        no_guidance = {
            "managed-improve",
            "preflight",
            "prepare",
            "research",
            "research-review",
            "research-plan",
            "research-apply",
            "research-verify",
            "research-commit",
            "research-finalize",
            "commit",
            "merge",
            "coverage",
            "publish",
            "objective-review",
            "objective-plan",
            "objective-apply",
            "objective-verify",
            "objective-commit",
            "objective-finalize",
            "step-plan",
            "step-plan-review",
            "step-plan-disposition",
            "step-plan-revise",
            "step-plan-verify",
            "step-plan-commit",
            "step-plan-finalize",
            "improve-plan-verify",
            "test-refine",
            "test-author",
            "skill-validate",
        }
        self.assertEqual(shiploop_protocol.BEHAVIOR_SECTIONS, expected)
        self.assertEqual(
            set(shiploop_protocol.PROMPTS), set(expected) | no_guidance
        )

        core = SimpleNamespace(**runpy.run_path(str(CLI)))
        reference = core.REF_DIR / "behavioral-requirements.md"
        self.assertEqual(
            reference, SCRIPTS.parent / "references/behavioral-requirements.md"
        )
        self.assertTrue(reference.is_file())
        available_anchors = {
            re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", reference.read_text())
        }
        expected_anchors = {anchor for anchors in expected.values() for anchor in anchors}
        self.assertTrue(expected_anchors <= available_anchors)

        self.cli("init", "--repo", str(self.repo), "--prompt", "Build")
        base = self.state()
        planning_stages = {
            "research",
            "research-review",
            "research-plan",
            "research-apply",
            "research-verify",
            "research-commit",
            "research-finalize",
            "behavior",
            "behavior-review",
            "behavior-plan",
            "behavior-apply",
            "behavior-verify",
            "behavior-commit",
            "behavior-finalize",
            "spec",
            "spec-review",
            "spec-plan",
            "spec-apply",
            "spec-verify",
            "spec-commit",
            "spec-finalize",
            "step-plan",
            "step-plan-review",
            "step-plan-disposition",
            "step-plan-revise",
            "step-plan-verify",
            "step-plan-commit",
            "step-plan-finalize",
            "objective-review",
            "objective-plan",
            "objective-apply",
            "objective-verify",
            "objective-commit",
            "objective-finalize",
        }
        state_bound_stages = {"managed-improve", "sequence", "commit", "final-verify"}
        for stage in shiploop_protocol.PROMPTS:
            with self.subTest(stage=stage):
                if stage in planning_stages | state_bound_stages:
                    continue
                state = dict(base)
                # This table isolates static guidance routing for the legacy
                # packet shape. Current runs have a separate missing-
                # environment block assertion above.
                state.pop("platform_revalidation_protocol_version")
                state.update(phase="test", stage=stage)
                state["action"] = {"id": f"behavior-{stage}", "stage": stage}
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    shiploop_protocol.packet(core, self.run_dir, state)
                packet = output.getvalue()
                guidance = [
                    line
                    for line in packet.splitlines()
                    if line.startswith("Behavior-model guidance:")
                ]

                report_advisory_size(f"behavior packet stage {stage}", packet, 7000)
                self.assertIn(f"Action: behavior-{stage}", packet)
                self.assertIn("Bounded context:", packet)
                self.assertIn("Result format:", packet)
                self.assertIn("When done:", packet)
                self.assertIn(f"--action behavior-{stage}", packet)
                self.assertIn(
                    f"--result {self.run_dir / 'inbox' / f'behavior-{stage}.md'}",
                    packet,
                )
                if stage in expected:
                    self.assertEqual(len(guidance), 1)
                    report_advisory_size(f"behavior-model guidance {stage}", guidance[0], 500)
                    self.assertTrue(
                        guidance[0].startswith("Behavior-model guidance: read only ")
                    )
                    self.assert_guidance_path(packet, guidance[0], reference)
                    self.assertEqual(
                        set(re.findall(r"#([a-z0-9-]+)", guidance[0])),
                        set(expected[stage]),
                    )
                else:
                    self.assertEqual(guidance, [])

    def test_planning_loop_guidance_routes_one_bounded_section_per_planning_stage(self):
        import re

        import shiploop_protocol

        expected = {
            "research": ("loop-contract",),
            "research-review": ("review",),
            "research-plan": ("plan-and-apply",),
            "research-apply": ("plan-and-apply",),
            "research-verify": ("checks-and-commits",),
            "research-commit": ("checks-and-commits",),
            "research-finalize": ("finalization-and-recovery",),
            "behavior": ("loop-contract",),
            "behavior-review": ("review",),
            "behavior-plan": ("plan-and-apply",),
            "behavior-apply": ("plan-and-apply",),
            "behavior-verify": ("checks-and-commits",),
            "behavior-commit": ("checks-and-commits",),
            "behavior-finalize": ("finalization-and-recovery",),
            "spec": ("loop-contract",),
            "spec-review": ("review",),
            "spec-plan": ("plan-and-apply",),
            "spec-apply": ("plan-and-apply",),
            "spec-verify": ("checks-and-commits",),
            "spec-commit": ("checks-and-commits",),
            "spec-finalize": ("finalization-and-recovery",),
        }
        self.assertEqual(shiploop_protocol.PLANNING_SECTIONS, expected)
        self.assertEqual(
            set(expected),
            {
                stage
                for stage in shiploop_protocol.PROMPTS
                if stage == "research"
                or stage.startswith("research-")
                or stage == "behavior"
                or stage.startswith("behavior-")
                or stage == "spec"
                or stage.startswith("spec-")
            },
        )
        reference = SCRIPTS.parent / "references/planning-loops.md"
        self.assertTrue(reference.is_file())
        anchors = {
            re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", reference.read_text())
        }
        expected_anchors = {anchor for anchors in expected.values() for anchor in anchors}
        self.assertTrue(expected_anchors <= anchors)

    def test_recursive_research_guidance_routes_to_investigation_and_inner_readers(self):
        import re

        import shiploop_protocol

        expected = {
            "research": ("draft", "decision-boundaries", "recursive-discovery-and-experiments"),
            "research-review": ("review", "decision-boundaries", "recursive-discovery-and-experiments"),
            "research-plan": ("review", "decision-boundaries", "recursive-discovery-and-experiments"),
            "research-apply": ("draft", "decision-boundaries", "recursive-discovery-and-experiments"),
            "research-verify": ("evidence-and-freshness",),
            "research-commit": ("evidence-and-freshness",),
            "research-finalize": ("evidence-and-freshness",),
            "review": ("later-discoveries", "recursive-discovery-and-experiments"),
            "improve-plan": ("later-discoveries", "recursive-discovery-and-experiments"),
            "improve-apply": ("later-discoveries", "recursive-discovery-and-experiments"),
            "iteration-document": ("later-discoveries",),
            "carry-forward": ("later-discoveries",),
            "post-inner": ("later-discoveries",),
        }
        self.assertEqual(shiploop_protocol.RESEARCH_SECTIONS, expected)
        self.assertTrue(set(expected) <= set(shiploop_protocol.PROMPTS))
        reference = SCRIPTS.parent / "references/research-loop.md"
        anchors = {
            re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", reference.read_text())
        }
        self.assertTrue({anchor for values in expected.values() for anchor in values} <= anchors)

    def test_step_planning_guidance_routes_only_the_current_bounded_section(self):
        import re

        import shiploop_protocol

        expected = {
            "step-plan": ("loop-contract", "cold-start-evidence", "local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "step-plan-review": ("review-rubric", "cold-start-evidence", "local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "step-plan-disposition": ("contract-disposition",),
            "step-plan-revise": ("revise-and-verify", "local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "step-plan-verify": ("revise-and-verify",),
            "step-plan-commit": ("revise-and-verify",),
            "step-plan-finalize": ("loop-contract",),
            "improve-plan": ("phase-specific-emphasis", "local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "implement": ("local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "research-plan": ("phase-specific-emphasis",),
            "behavior-plan": ("phase-specific-emphasis",),
            "spec-plan": ("phase-specific-emphasis",),
            "sequence": ("phase-specific-emphasis", "baseline-tests-and-migrations"),
            "review": ("phase-specific-emphasis", "baseline-tests-and-migrations"),
            "improve-apply": ("phase-specific-emphasis", "local-microplan-and-backchain", "baseline-tests-and-migrations"),
            "iteration-document": ("phase-specific-emphasis",),
            "post-inner": ("phase-specific-emphasis",),
            "quality": ("phase-specific-emphasis",),
        }
        self.assertEqual(shiploop_protocol.STEP_PLANNING_SECTIONS, expected)
        self.assertTrue(set(expected) <= set(shiploop_protocol.PROMPTS))

        reference = SCRIPTS.parent / "references/execution-planning.md"
        self.assertTrue(reference.is_file())
        anchors = {
            re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")
            for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", reference.read_text())
        }
        expected_anchors = {anchor for values in expected.values() for anchor in values}
        self.assertTrue(expected_anchors <= anchors)

    def test_behavioral_requirements_survive_draft_deletion_across_processes(self):
        self.cli(
            "init", "--repo", str(self.repo), "--execution-mode", "legacy",
            "--prompt", "Build",
        )
        preflight = self.state()["action"]["id"]
        self.cli(
            "complete",
            "--action",
            preflight,
            "--result",
            self.record(
                "behavior-preflight.md",
                {"summary": "Committed baseline is available", "baseline": "committed-head"},
            ),
        )
        self.assertEqual(self.state()["stage"], "approach")

        approach_body = """## Behavioral requirements

R-01: A fresh host can reconstruct the intended behavior from durable Markdown.
F-01: Deleting an authored result draft does not erase the imported requirement.
T-01: context --section approach exposes the persisted requirement identifiers.

## Uncertainty and evidence

Uncertainty: semantic completeness remains unassessed in this planning record.
Evidence: the imported approach record and a fresh-process context read.
This is not a semantic-completeness claim.
""".strip()
        approach_candidate = {
            "summary": "Stored behavioral requirements with uncertainty",
            "body": approach_body,
        }
        approach_draft = Path(
            self.record("behavior-approach-draft.md", approach_candidate)
        )
        self.cli(
            "complete",
            "--action",
            self.state()["action"]["id"],
            "--result",
            str(approach_draft),
        )
        state = self.state()
        self.assertEqual(state["stage"], "objective-review")
        candidate_path = self.run_dir / state["objective"]["candidate"]
        self.assertTrue(candidate_path.is_file())

        approach_draft.unlink()
        self.assertFalse(approach_draft.exists())
        self.assertTrue(candidate_path.is_file())
        self.converge_approach_objective(
            approach_candidate, label="behavioral-requirements"
        )
        self.assertEqual((self.run_dir / "approach.md").read_text(), approach_body)
        packet = self.cli("next").stdout
        reference = SCRIPTS.parent / "references/behavioral-requirements.md"
        self.assertIn("Action:", packet)
        self.assertIn("Behavior-model guidance: read only", packet)
        guidance = next(line for line in packet.splitlines()
                        if line.startswith("Behavior-model guidance: read only "))
        self.assert_guidance_path(packet, guidance, reference)
        self.assertIn("#discovery-and-research", guidance)

        context = self.cli(
            "context", "--section", "approach", "--offset", "0", "--limit", "4000"
        ).stdout
        self.assertIn("R-01", context)
        self.assertIn("F-01", context)
        self.assertIn("T-01", context)
        self.assertIn("Uncertainty:", context)
        self.assertIn("Evidence:", context)
        self.assertIn("not a semantic-completeness claim", context)
        self.assertNotIn("shiploop-state", (self.run_dir / "approach.md").read_text())
        self.assertFalse((self.run_dir / "state.json").exists())
        self.assertFalse((self.run_dir / "approach.json").exists())

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
        self.assertIn("When the step authors client–service calls", implement)
        self.assertIn("real client/HTML invocation path", implement)
        self.assertIn("mocks or internal substitutes", implement)


if __name__ == "__main__":
    unittest.main()
