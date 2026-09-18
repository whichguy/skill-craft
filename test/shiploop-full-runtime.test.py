#!/usr/bin/env python3
"""Public protocol-v3 runtime composition with synthetic fixture judgments.

Every state transition in this test goes through the copied public ShipLoop
CLI, and every child reaches ``done`` through the selected copied Improve
package's bundled Until Loop CLI.  The producer results, review records, and
Until Loop assessments are deliberately synthetic fixture observations.  They
prove wiring, durable recovery, and callback behavior; they do not claim a
model reviewed code or that a product was delivered.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHIPLOOP = ROOT / "skills" / "shiploop"
SOURCE_IMPROVE = ROOT / "skills" / "improve"
GENERATED_SHIPLOOP = ROOT / "plugins" / "shiploop" / "skills" / "shiploop"
GENERATED_IMPROVE = ROOT / "plugins" / "improve" / "skills" / "improve"


# This expectation is intentionally independent of the prompt catalog and
# navigator implementation.  A changed graph must update this public-contract
# test deliberately instead of silently changing its own oracle.
EXPECTED_PRELUDE = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
)
EXPECTED_INNER = (
    "select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "document", "skill-assess",
    "skill-validate", "static-checks", "verify", "integrate", "integration-verify",
    "carry-forward",
)
EXPECTED_OUTER = (
    "system-test-author", "system-test", "product-acceptance", "release-plan",
    "release-check", "release", "release-verify", "operations", "handoff",
)
EXPECTED_STAGES = EXPECTED_PRELUDE + EXPECTED_INNER + EXPECTED_OUTER
COLD_RECOVERY_STAGES = {"discovery", "implement", "release-check"}


def _delivery_contract(*, candidate: str = "candidate-v1") -> dict:
    """Return a synthetic opt-in delivery declaration for CLI composition."""
    return {
        "consumer": "synthetic private fixture",
        "target": "fixture-head",
        "behavior": "a synthetic dragged fixture visibly follows the pointer",
        "candidate": candidate,
        "operation": "sync the approved synthetic fixture target",
        "necessity": "required",
        "basis": "The synthetic runtime fixture requires current delivery declarations.",
        "exclusions": ["public access", "live deployment"],
        "authority": {
            "status": "approved",
            "kind": "repo-policy",
            "reference": "SYNTHETIC-SHIPLOOP.md#fixture-update",
            "approval_ref": "Synthetic fixture authority only; no user delivery claim.",
            "target": "fixture-head",
            "operation": "sync the approved synthetic fixture target",
        },
        "obligations": [
            {
                "id": "pre-drag",
                "consumer": "synthetic private fixture",
                "target": "fixture-head",
                "kind": "pre-update",
                "phase": "system-test",
                "expected": "synthetic move checks pass for the current candidate",
                "required": True,
            },
            {
                "id": "update-effect",
                "consumer": "synthetic private fixture",
                "target": "fixture-head",
                "kind": "effect",
                "phase": "release",
                "expected": "the synthetic approved update is recorded",
                "required": True,
            },
            {
                "id": "update-identity",
                "consumer": "synthetic private fixture",
                "target": "fixture-head",
                "kind": "identity",
                "phase": "release",
                "expected": "the target identifies the current synthetic candidate",
                "required": True,
            },
            {
                "id": "visual-drag",
                "consumer": "synthetic private fixture",
                "target": "fixture-head",
                "kind": "behavior",
                "phase": "release-verify",
                "expected": "a synthetic dragged fixture visibly follows the pointer",
                "required": True,
            },
        ],
    }


def _record_text(value: object, title: str = "Runtime composition fixture") -> str:
    """Write a protocol-shaped external callback without importing ShipLoop."""
    return (
        f"# {title}\n\n```shiploop-state\n"
        + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n"
    )


def _read_record(path: Path) -> dict:
    """Read the stable Markdown callback shape emitted by the public CLI."""
    text = path.read_text(encoding="utf-8")
    marker = "```shiploop-state\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n```", start)
    value = json.loads(text[start:end])
    if not isinstance(value, dict):
        raise AssertionError(f"record is not an object: {path}")
    return value


def _write_record(path: Path, value: object, title: str = "Runtime composition fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_record_text(value, title), encoding="utf-8")


def _fingerprint(root: Path) -> dict[str, str]:
    """Confirm a relocated selected package remains read-only during a run."""
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


class FullRuntimeCompositionTests(unittest.TestCase):
    """Exercise a complete script-owned graph through fresh public processes."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-full-runtime-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.unrelated_cwd = self.base / "unrelated invocation directory"
        self.unrelated_cwd.mkdir()
        self.payload_root = self.base / "relocated payloads"
        self.source_shiploop, self.source_improve = self._copy_payload(
            "source", SOURCE_SHIPLOOP, SOURCE_IMPROVE
        )
        self.generated_shiploop, self.generated_improve = self._copy_payload(
            "generated", GENERATED_SHIPLOOP, GENERATED_IMPROVE
        )
        self.source_fingerprint = {
            "shiploop": _fingerprint(self.source_shiploop),
            "improve": _fingerprint(self.source_improve),
        }
        self.generated_fingerprint = {
            "shiploop": _fingerprint(self.generated_shiploop),
            "improve": _fingerprint(self.generated_improve),
        }
        self.trace_path = self.base / "runtime-composition-trace.json"
        self.trace: dict[str, object] = {
            "schema": "shiploop-full-runtime-composition/v1",
            "review_judgments": "synthetic fixture observations; no live semantic review claim",
            "imports": [],
            "cold_recoveries": [],
            "rejections": [],
        }
        self.environment = {
            **os.environ,
            "DEVELOPER_DIR": "/Library/Developer/CommandLineTools",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }

    def _copy_payload(self, label: str, shiploop: Path, improve: Path) -> tuple[Path, Path]:
        self.assertTrue(shiploop.is_dir(), shiploop)
        self.assertTrue(improve.is_dir(), improve)
        destination = self.payload_root / label / "skills"
        copied_shiploop = destination / "shiploop"
        copied_improve = destination / "improve"
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
        shutil.copytree(shiploop, copied_shiploop, ignore=ignore)
        shutil.copytree(improve, copied_improve, ignore=ignore)
        return copied_shiploop.resolve(), copied_improve.resolve()

    @staticmethod
    def _script(package: Path) -> Path:
        return package / "scripts" / "shiploop"

    @staticmethod
    def _card(package: Path) -> Path:
        return package / "SKILL.md"

    @staticmethod
    def _until(package: Path) -> Path:
        return package / "runtime" / "until-loop" / "scripts" / "until-loop"

    def _run(self, executable: Path, *args: object, code: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-B", str(executable), *map(str, args)],
            cwd=self.unrelated_cwd,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def _git(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            cwd=self.unrelated_cwd,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def _flush_trace(self) -> None:
        self.trace_path.write_text(
            json.dumps(self.trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _state(self, run: Path) -> dict:
        return _read_record(run / "state.md")

    @staticmethod
    def _cursor(state: dict) -> tuple[str, dict]:
        if state["stage"] == "inner-loop":
            item = state["work_items"][state["work_index"]]["id"]
            loop = state["inner_loops"][item]
            return loop["stage"], loop["action"]
        return state["stage"], state["action"]

    @staticmethod
    def _delivery_anchor(state: dict) -> str:
        """Find the accepted contract anchor without importing ShipLoop code."""
        for row in reversed(state["history"]):
            result = state["accepted"][row["action"]]
            assessment = result.get("delivery_assessment")
            if isinstance(assessment, dict) and assessment.get("kind") == "contract":
                return row["action"]
        raise AssertionError("no accepted delivery contract anchor")

    def _delivery_observation(
        self, state: dict, *identifiers: str, candidate: str = "candidate-v1"
    ) -> dict:
        return {
            "kind": "observation",
            "contract_anchor": self._delivery_anchor(state),
            "observations": [
                {
                    "obligation_id": identifier,
                    "status": "passed",
                    "candidate": candidate,
                    "target": "fixture-head",
                    "evidence_refs": [
                        f"fixture://delivery/{candidate}/{identifier}/synthetic-observation"
                    ],
                }
                for identifier in identifiers
            ],
        }

    def _new_source_repository(self, label: str) -> Path:
        source = self.base / label / "source repository"
        source.mkdir(parents=True)
        self._git(source, "init", "-q")
        self._git(source, "branch", "-M", "main")
        self._git(source, "config", "user.name", "ShipLoop Runtime Fixture")
        self._git(source, "config", "user.email", "shiploop-runtime@example.invalid")
        self._git(source, "config", "commit.gpgsign", "false")
        self._git(source, "config", "core.hooksPath", os.devnull)
        (source / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        self._git(source, "add", "baseline.txt")
        self._git(source, "commit", "-qm", "baseline")
        return source

    def _start_workspace(self, *, delivery_contract: bool = False) -> tuple[Path, Path, Path]:
        source = self._new_source_repository("workspace composition")
        workspace = self.base / "workspace composition" / "isolated"
        command: list[object] = [
            "workspace", "start", "--repo", source, "--workspace-root", workspace,
            "--prompt", "Synthetic protocol composition fixture; no product claim.",
            "--improve-skill", self._card(self.source_improve),
        ]
        if delivery_contract:
            command.append("--delivery-contract")
        self._run(self._script(self.source_shiploop), *command)
        return source, workspace, workspace / "run"

    def _start_direct(self, label: str, shiploop: Path, improve: Path) -> tuple[Path, Path]:
        repo = self.base / label / "ordinary repository"
        repo.mkdir(parents=True)
        run = self.base / label / "run"
        self._run(
            self._script(shiploop),
            "init", "--repo", repo, "--run-dir", run,
            "--prompt", "Synthetic protocol composition fixture; no product claim.",
            "--improve-skill", self._card(improve),
        )
        return repo, run

    def _begin_stage(
        self,
        *,
        shiploop: Path,
        improve: Path,
        repo: Path,
        run: Path,
        expected_stage: str,
        payload: dict | None = None,
    ) -> dict:
        state = self._state(run)
        stage, action = self._cursor(state)
        self.assertEqual(stage, expected_stage)
        self.assertIsInstance(action, dict)
        action_id = action["id"]
        producer = {
            "outcome": "done",
            "summary": f"Synthetic producer callback for {stage}; no semantic claim.",
            "evidence_refs": [f"fixture://producer/{stage}/{action_id}"],
        }
        if payload:
            producer.update(payload)
        result_path = run / "inbox" / f"{action_id}.md"
        _write_record(result_path, producer, "Synthetic ShipLoop producer callback")
        self._run(
            self._script(shiploop), "done", "--run-dir", run,
            "--action", action_id, "--result", result_path,
        )
        waiting = self._state(run)
        waiting_stage, waiting_action = self._cursor(waiting)
        self.assertEqual((waiting_stage, waiting_action["id"]), (stage, action_id))
        self.assertEqual(waiting["active_improve"]["action_id"], action_id)
        self._run(
            self._script(shiploop), "improve-bind", "--run-dir", run,
            "--action", action_id, "--skill-card", self._card(improve),
        )
        bound = self._state(run)["active_improve"]
        self.assertEqual(Path(bound["skill"]["skill_card"]), self._card(improve).resolve())
        self.assertEqual(Path(bound["skill"]["runtime_cli"]), self._until(improve).resolve())
        return {
            "stage": stage,
            "action": action_id,
            "producer": producer,
            "producer_path": result_path,
            "binding": bound,
            "repo": repo,
            "run": run,
            "shiploop": shiploop,
            "improve": improve,
        }

    def _start_child(self, context: dict, *, marker: str | None = None) -> dict:
        repo = context["repo"]
        binding = context["binding"]
        contract = {
            "version": 1,
            "policy": "decision-rubric/2",
            "original_request": (
                "Synthetic runtime composition only; do not infer semantic review.\n"
                + (marker if marker is not None else binding["contract_marker"])
            ),
            "interpretation": "Reach a mechanically valid terminal child callback.",
            "criteria": [{
                "id": "C1",
                "text": "Synthetic fixture evidence exists.",
                "basis": {"kind": "request", "reference": "runtime composition fixture"},
            }],
        }
        contract_path = self.base / "contracts" / f"{context['action']}.json"
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(json.dumps(contract, sort_keys=True), encoding="utf-8")
        command: list[object] = [
            "v2", "init", "--repo", repo, "--contract-file", contract_path,
        ]
        if (repo / ".until-loop" / "state.json").exists():
            command.append("--force")
        self._run(self._until(context["improve"]), *command)
        child = json.loads((repo / ".until-loop" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(child["phase"], "active")
        self.assertIn(contract["original_request"].splitlines()[-1], child["contract"]["original_request"])
        return child

    def _receipt(self, context: dict, *, final_result: dict | None = None) -> Path:
        repo = context["repo"]
        action = context["action"]
        review_root = repo / ".until-loop" / "reviews"
        review_root.mkdir(parents=True, exist_ok=True)
        reviews = [review_root / f"{action}-review-a.md", review_root / f"{action}-review-b.md"]
        check = review_root / f"{action}-checks.md"
        for index, path in enumerate((*reviews, check), start=1):
            path.write_text(
                f"Synthetic fixture observation {index} for {context['stage']}; no semantic review claim.\n",
                encoding="utf-8",
            )
        receipt: dict[str, object] = {
            "summary": f"Actual runtime completed a synthetic {context['stage']} fixture.",
            "review_refs": [str(path) for path in reviews],
            "check_refs": [str(check)],
            "lessons": "This record proves callback composition, not review quality.",
        }
        if final_result is not None:
            receipt["final_result"] = final_result
        receipt_path = context["run"] / "inbox" / f"{action}-improve.md"
        _write_record(receipt_path, receipt, "Synthetic Improve terminal receipt")
        return receipt_path

    def _submit_child(self, context: dict, child: dict) -> None:
        action = child["action"]
        assessment = {
            "action_id": action["id"],
            "contract_revision": child["contract"]["revision"],
            "decision": "complete",
            "criteria": [{
                "id": "C1", "status": "satisfied",
                "evidence": "Synthetic protocol fixture receipt.",
            }],
            "next_action": None,
            "blocker": None,
        }
        result_path = Path(action["result_path"])
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(assessment, sort_keys=True), encoding="utf-8")
        self._run(
            self._until(context["improve"]), "v2", "submit",
            "--repo", context["repo"], "--action-id", action["id"],
        )
        completed = json.loads((context["repo"] / ".until-loop" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(completed["phase"], "done")
        (context["repo"] / ".until-loop" / "working.md").write_text(
            f"Synthetic working notebook for {context['stage']}.\n", encoding="utf-8"
        )

    def _reject_import(self, context: dict, receipt: Path, label: str) -> None:
        before = (context["run"] / "state.md").read_bytes()
        self._run(
            self._script(context["shiploop"]), "improve-complete", "--run-dir", context["run"],
            "--action", context["action"], "--result", receipt, code=2,
        )
        self.assertEqual(before, (context["run"] / "state.md").read_bytes())
        self.trace["rejections"].append({
            "stage": context["stage"], "action": context["action"], "kind": label,
        })
        self._flush_trace()

    def _import_child(self, context: dict, receipt: Path) -> dict:
        self._run(
            self._script(context["shiploop"]), "improve-complete", "--run-dir", context["run"],
            "--action", context["action"], "--result", receipt,
        )
        state = self._state(context["run"])
        self.assertIsNone(state["active_improve"])
        self.assertIn(context["action"], state["improve_results"])
        record = state["improve_results"][context["action"]]
        self.assertEqual(record["runtime_phase"], "done")
        self.assertTrue((context["run"] / "improve" / context["action"] / "state.json").is_file())
        self.trace["imports"].append({
            "stage": context["stage"],
            "parent_action": context["action"],
            "terminal_result_sha256": record["identities"]["result_sha256"],
            "outcome": state["accepted"][context["action"]]["outcome"],
            "selected_skill": record["skill"]["skill_card"],
            "runtime": record["skill"]["runtime_cli"],
        })
        self._flush_trace()
        return state

    def _correct_missing_delivery_import(
        self, context: dict, child: dict, corrected_result: dict
    ) -> dict:
        """Keep a completed child parked when its fresh observation is absent."""
        receipt = self._receipt(context)
        self._submit_child(context, child)
        state_before = (context["run"] / "state.md").read_bytes()
        child_before = (context["repo"] / ".until-loop" / "state.json").read_bytes()
        failed = self._run(
            self._script(context["shiploop"]), "improve-complete", "--run-dir", context["run"],
            "--action", context["action"], "--result", receipt, code=2,
        )
        self.assertIn("pre-update", failed.stdout + failed.stderr)
        self.assertEqual(state_before, (context["run"] / "state.md").read_bytes())
        self.assertEqual(child_before, (context["repo"] / ".until-loop" / "state.json").read_bytes())
        parked = self._state(context["run"])
        self.assertEqual(parked["active_improve"]["action_id"], context["action"])
        self.assertEqual(parked["active_improve"]["binding_id"], context["binding"]["binding_id"])
        self.trace["rejections"].append({
            "stage": context["stage"],
            "action": context["action"],
            "kind": "missing-fresh-delivery-observation",
        })
        self._flush_trace()
        corrected_receipt = self._receipt(context, final_result=corrected_result)
        return self._import_child(context, corrected_receipt)

    def _cold_recover(self, context: dict) -> None:
        before = (context["run"] / "state.md").read_bytes()
        result = self._run(self._script(context["shiploop"]), "next", "--run-dir", context["run"])
        self.assertEqual(before, (context["run"] / "state.md").read_bytes())
        self.assertIn(context["binding"]["binding_id"], result.stdout)
        self.trace["cold_recoveries"].append({
            "stage": context["stage"], "action": context["action"],
        })
        self._flush_trace()

    def _accept_stage(
        self,
        *,
        shiploop: Path,
        improve: Path,
        repo: Path,
        run: Path,
        stage: str,
        payload: dict | None = None,
        final_result: dict | None = None,
        rejection: str | None = None,
        before_import=None,
    ) -> tuple[dict, dict]:
        context = self._begin_stage(
            shiploop=shiploop, improve=improve, repo=repo, run=run,
            expected_stage=stage, payload=payload,
        )
        if stage in COLD_RECOVERY_STAGES:
            self._cold_recover(context)
        if rejection == "stale":
            receipt = self._receipt(context, final_result=final_result)
            self._reject_import(context, receipt, "stale-terminal-child")
            child = self._start_child(context)
        elif rejection == "foreign":
            foreign = "ShipLoop standalone Improve binding: foreign/action"
            self._start_child(context, marker=foreign)
            receipt = self._receipt(context, final_result=final_result)
            self._reject_import(context, receipt, "foreign-child")
            child = self._start_child(context)
        else:
            child = self._start_child(context)
            receipt = self._receipt(context, final_result=final_result)
            if rejection == "unfinished":
                self._reject_import(context, receipt, "unfinished-child")
        self._submit_child(context, child)
        if before_import is not None:
            before_import(context, receipt)
        state = self._import_child(context, receipt)
        return state, context

    def _assert_exact_replay(self, context: dict) -> None:
        """Accepted producer, child, and parent callbacks are replay-safe."""
        run = context["run"]
        state_before = (run / "state.md").read_bytes()
        child_before = (context["repo"] / ".until-loop" / "state.json").read_bytes()
        child = json.loads(child_before)
        self._run(
            self._until(context["improve"]), "v2", "submit", "--repo", context["repo"],
            "--action-id", child["last_assessment"]["action_id"],
        )
        self.assertEqual(child_before, (context["repo"] / ".until-loop" / "state.json").read_bytes())
        receipt = run / "inbox" / f"{context['action']}-improve.md"
        self._run(
            self._script(context["shiploop"]), "improve-complete", "--run-dir", run,
            "--action", context["action"], "--result", receipt,
        )
        self._run(
            self._script(context["shiploop"]), "done", "--run-dir", run,
            "--action", context["action"], "--result", context["producer_path"],
        )
        self.assertEqual(state_before, (run / "state.md").read_bytes())

    def _checkpoint(self, run: Path, repo: Path) -> tuple[Path, Path]:
        checkpoint = self.base / "late-outer-checkpoint"
        run_copy = checkpoint / "run"
        child_copy = checkpoint / "until-loop"
        shutil.copytree(run, run_copy)
        shutil.copytree(repo / ".until-loop", child_copy)
        return run_copy, child_copy

    def _restore_checkpoint(self, run: Path, repo: Path, checkpoint: tuple[Path, Path]) -> None:
        """Reuse a real pre-operations subprocess state, never a hand-written fixture."""
        run_copy, child_copy = checkpoint
        run.rename(self.base / "completed-baseline-run")
        (repo / ".until-loop").rename(self.base / "completed-baseline-until-loop")
        shutil.copytree(run_copy, run)
        shutil.copytree(child_copy, repo / ".until-loop")

    def _return_final_workspace(self, workspace: Path, source: Path, context: dict, _receipt: Path) -> None:
        self._run(self._script(context["shiploop"]), "workspace", "plan-return", "--workspace-root", workspace)
        plan_path = workspace / "return-plan.md"
        plan = _read_record(plan_path)
        self.assertTrue(plan["paths"])
        self.assertTrue(any(row["path"] == "delivered.txt" for row in plan["paths"]))
        self.assertTrue(all(".until-loop" not in Path(row["path"]).parts for row in plan["paths"]))
        for row in plan["paths"]:
            row["disposition"] = "keep"
        _write_record(plan_path, plan, "ShipLoop workspace return plan")
        self._run(self._script(context["shiploop"]), "workspace", "return", "--workspace-root", workspace)
        self.assertEqual((source / "delivered.txt").read_text(encoding="utf-8"), "returned candidate\n")

    def test_full_v3_runtime_composition_and_recovery_variants(self) -> None:
        """Exercise all stages, then a delayed contract correction and recovery."""
        self.assertEqual(len(EXPECTED_STAGES), 34)
        source, workspace, run = self._start_workspace(delivery_contract=True)
        repo = workspace / "worktree"
        state = self._state(run)
        self.assertEqual(state["delivery_contract_version"], 1)
        observed: list[str] = []
        checkpoint: tuple[Path, Path] | None = None
        first_context: dict | None = None

        for stage in EXPECTED_STAGES:
            if stage == "implement":
                (repo / "delivered.txt").write_text("returned candidate\n", encoding="utf-8")
            if stage == "operations":
                checkpoint = self._checkpoint(run, repo)
            payload = None
            if stage == "plan":
                payload = {
                    "work_items": [{"id": "W1", "title": "Synthetic item"}],
                    "delivery_assessment": {"kind": "contract", "contract": _delivery_contract()},
                }
            elif stage == "system-test":
                payload = {
                    "delivery_assessment": self._delivery_observation(state, "pre-drag"),
                }
            elif stage == "release":
                payload = {
                    "delivery_assessment": self._delivery_observation(
                        state, "update-effect", "update-identity"
                    ),
                }
            elif stage == "release-verify":
                payload = {
                    "delivery_assessment": self._delivery_observation(state, "visual-drag"),
                }
            before_import = None
            if stage == "handoff":
                def before_import(context, receipt):
                    self._return_final_workspace(workspace, source, context, receipt)
            state, context = self._accept_stage(
                shiploop=self.source_shiploop, improve=self.source_improve,
                repo=repo, run=run, stage=stage, payload=payload,
                rejection={"intake": "unfinished", "discovery": "foreign", "research": "stale"}.get(stage),
                before_import=before_import,
            )
            observed.append(stage)
            if stage == "intake":
                first_context = context
                self._assert_exact_replay(context)

        self.assertEqual(tuple(observed), EXPECTED_STAGES)
        self.assertIsNotNone(first_context)
        self.assertIsNotNone(checkpoint)
        self.assertEqual(state["status"], "done")
        self.assertEqual(len(state["history"]), 34)
        self.assertEqual(len(state["improve_results"]), 34)
        self.assertEqual([row["stage"] for row in state["history"]], list(EXPECTED_STAGES))

        # Re-enter a real checkpoint recorded immediately before a late outer
        # callback.  This avoids fabricating a state to test replan behavior.
        self._restore_checkpoint(run, repo, checkpoint)
        checkpoint_state = self._state(run)
        self.assertEqual(self._cursor(checkpoint_state)[0], "operations")
        previous_actions = set(checkpoint_state["improve_results"])
        state, replan_context = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="operations",
            final_result={
                "outcome": "replan",
                "summary": "Synthetic late outer correction requires a second work item.",
                "work_items": [{"id": "W2", "title": "Synthetic corrective item"}],
            },
        )
        self.assertEqual(self._cursor(state)[0], "select-work")
        self.assertEqual(state["completed_work_items"], ["W1"])
        self.assertEqual([item["id"] for item in state["work_items"]], ["W1", "W2"])
        self.assertTrue(previous_actions.issubset(state["improve_results"]))
        self.assertTrue((run / "improve" / replan_context["action"] / "evidence").is_dir())

        state, repeat_context = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="select-work",
            final_result={
                "outcome": "repeat",
                "summary": "Synthetic Improve correction requests another selection attempt.",
            },
        )
        repeated_stage, repeated_action = self._cursor(state)
        self.assertEqual(repeated_stage, "select-work")
        self.assertNotEqual(repeated_action["id"], repeat_context["action"])
        self.assertEqual(state["accepted"][repeat_context["action"]]["outcome"], "repeat")
        self.assertIn(replan_context["action"], state["improve_results"])

        state, _ = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="select-work",
        )
        self.assertEqual(self._cursor(state)[0], "step-plan")

        # The first late replan has no correction.  Its successor receives a
        # delayed v2 contract from system-test and must still complete a new
        # release plan without retaining a stale replanning barrier.
        for stage in EXPECTED_INNER[1:]:
            state, _ = self._accept_stage(
                shiploop=self.source_shiploop, improve=self.source_improve,
                repo=repo, run=run, stage=stage,
            )
        self.assertEqual(self._cursor(state)[0], "system-test-author")
        delayed_contract_context: dict | None = None
        for stage in ("system-test-author", "system-test", "product-acceptance", "release-plan"):
            payload = None
            if stage == "system-test":
                prior_anchor = self._delivery_anchor(state)
                payload = {
                    "delivery_assessment": {
                        "kind": "contract",
                        "contract": _delivery_contract(candidate="candidate-v2"),
                        "supersedes": prior_anchor,
                        "observations": self._delivery_observation(
                            state, "pre-drag", candidate="candidate-v2"
                        )["observations"],
                    },
                }
            state, context = self._accept_stage(
                shiploop=self.source_shiploop, improve=self.source_improve,
                repo=repo, run=run, stage=stage, payload=payload,
            )
            if stage == "system-test":
                delayed_contract_context = context
        self.assertIsNotNone(delayed_contract_context)
        self.assertNotIn(
            "Delivery replanning required:",
            self._run(self._script(self.source_shiploop), "next", "--run-dir", run).stdout,
        )
        prior_anchor = self._delivery_anchor(state)
        state, delayed_replan_context = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="release-check",
            final_result={
                "outcome": "replan",
                "summary": (
                    "Synthetic late contract correction requires a third work item "
                    "and fresh current-candidate evidence."
                ),
                "evidence_refs": ["fixture://delivery/late-contract-correction"],
                "work_items": [{"id": "W3", "title": "Synthetic current-candidate item"}],
                "delivery_assessment": {
                    "kind": "contract",
                    "contract": _delivery_contract(candidate="candidate-v3"),
                    "supersedes": prior_anchor,
                },
            },
        )
        self.assertEqual(self._cursor(state)[0], "select-work")
        self.assertEqual(state["completed_work_items"], ["W1", "W2"])
        self.assertEqual([item["id"] for item in state["work_items"]], ["W1", "W2", "W3"])
        blocked_packet = self._run(
            self._script(self.source_shiploop), "next", "--run-dir", run
        ).stdout
        self.assertIn("Delivery replanning required:", blocked_packet)
        self.assertIn("accepted outer replan edge", blocked_packet)

        for stage in EXPECTED_INNER:
            state, _ = self._accept_stage(
                shiploop=self.source_shiploop, improve=self.source_improve,
                repo=repo, run=run, stage=stage,
            )
        self.assertEqual(self._cursor(state)[0], "system-test-author")
        state, _ = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="system-test-author",
        )
        before_fresh_system_test = state
        missing_context = self._begin_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, expected_stage="system-test",
        )
        missing_child = self._start_child(missing_context)
        state = self._correct_missing_delivery_import(
            missing_context,
            missing_child,
            {
                "outcome": "done",
                "summary": "Synthetic Improve correction supplies the fresh pre-update observation.",
                "evidence_refs": ["fixture://delivery/candidate-v3/pre-drag"],
                "delivery_assessment": self._delivery_observation(
                    before_fresh_system_test, "pre-drag", candidate="candidate-v3"
                ),
            },
        )
        self.assertEqual(self._cursor(state)[0], "product-acceptance")
        state, _ = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="product-acceptance",
        )
        state, _ = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="release-plan",
        )
        recovered_packet = self._run(
            self._script(self.source_shiploop), "next", "--run-dir", run
        ).stdout
        self.assertNotIn("Delivery replanning required:", recovered_packet)
        state, recovered_check_context = self._accept_stage(
            shiploop=self.source_shiploop, improve=self.source_improve,
            repo=repo, run=run, stage="release-check",
        )
        self.assertEqual(self._cursor(state)[0], "release")
        self.trace["delivery_recovery"] = {
            "initial_late_replan_action": replan_context["action"],
            "delayed_contract_after_replan_action": delayed_contract_context["action"],
            "late_contract_replan_action": delayed_replan_context["action"],
            "missing_fresh_observation_action": missing_context["action"],
            "recovered_release_check_action": recovered_check_context["action"],
        }

        self._flush_trace()
        trace = json.loads(self.trace_path.read_text(encoding="utf-8"))
        baseline = trace["imports"][:34]
        self.assertEqual([row["stage"] for row in baseline], list(EXPECTED_STAGES))
        self.assertEqual(len({row["parent_action"] for row in baseline}), 34)
        self.assertEqual({row["stage"] for row in trace["cold_recoveries"]}, COLD_RECOVERY_STAGES)
        self.assertEqual(
            {row["kind"] for row in trace["rejections"]},
            {
                "unfinished-child",
                "foreign-child",
                "stale-terminal-child",
                "missing-fresh-delivery-observation",
            },
        )
        self.assertEqual(
            set(trace["delivery_recovery"]),
            {
                "initial_late_replan_action",
                "delayed_contract_after_replan_action",
                "late_contract_replan_action",
                "missing_fresh_observation_action",
                "recovered_release_check_action",
            },
        )
        self.assertEqual(self.source_fingerprint["shiploop"], _fingerprint(self.source_shiploop))
        self.assertEqual(self.source_fingerprint["improve"], _fingerprint(self.source_improve))

    def test_generated_payload_binds_its_own_selected_improve_runtime(self) -> None:
        """A copied generated payload must not fall back to an ambient skill path."""
        repo, run = self._start_direct("generated payload smoke", self.generated_shiploop, self.generated_improve)
        state, context = self._accept_stage(
            shiploop=self.generated_shiploop, improve=self.generated_improve,
            repo=repo, run=run, stage="intake",
        )
        self.assertEqual(self._cursor(state)[0], "discovery")
        record = state["improve_results"][context["action"]]
        self.assertEqual(Path(record["skill"]["skill_card"]), self._card(self.generated_improve).resolve())
        self.assertEqual(Path(record["skill"]["runtime_cli"]), self._until(self.generated_improve).resolve())
        self.assertEqual(self.generated_fingerprint["shiploop"], _fingerprint(self.generated_shiploop))
        self.assertEqual(self.generated_fingerprint["improve"], _fingerprint(self.generated_improve))


if __name__ == "__main__":
    unittest.main(verbosity=2)
