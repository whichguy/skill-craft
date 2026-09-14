#!/usr/bin/env python3
"""Real-CLI walk for ShipLoop's managed Improve child route.

The parent Markdown cursor remains parked while the child owns its review
passes.  This deliberately exercises the public commands and real Python test
files; it neither patches authority files nor simulates child transitions.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_managed_action_walk_fixture", str(ACTION_WALK)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {ACTION_WALK}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


ACTION = load_action_walk_fixture()
store = ACTION.store

import shiploop_improve_bridge as improve_bridge  # noqa: E402
import shiploop_delivery as delivery  # noqa: E402


class ManagedShipLoopWalkFixture(ACTION.ShipLoopActionWalkFixture):
    """Use the legacy fixture's real repository with a managed child overlay."""

    execution_mode = "managed"

    def setUp(self):
        super().setUp()
        self.managed_children = []

    def durable_parent_state(self):
        """Read the actual parent record without its child execution overlay."""
        return store.read_record(self.run_dir / "state.md")

    def state(self):
        """Use the bridge projection so every callback names the child action."""
        return improve_bridge.project(self.run_dir, self.durable_parent_state())

    def managed_binding(self):
        binding = self.durable_parent_state().get("managed_improve")
        self.assertIsInstance(binding, dict)
        return binding

    def managed_child_record(self):
        binding = self.managed_binding()
        path = self.run_dir / binding["receipt"]
        self.assertTrue(path.is_file(), f"missing managed child receipt: {path}")
        return store.read_record(path)

    def managed_child(self):
        record = self.managed_child_record()
        child = record.get("child")
        self.assertIsInstance(child, dict)
        return child

    def assert_parent_parked(self, profile=None):
        """Prove the child advances while the durable parent callback does not."""
        parent = self.durable_parent_state()
        binding = self.managed_binding()
        self.assertEqual(parent["stage"], "managed-improve")
        self.assertEqual(parent["action"]["stage"], "managed-improve")
        self.assertEqual(parent["action"]["id"], binding["parent_action"])
        self.assertEqual(binding["status"], "active")
        if profile is not None:
            self.assertEqual(binding["profile"], profile)
        child = self.managed_child()
        self.assertEqual(child["status"], "active")
        self.assertEqual(child["current_phase"], self.state()["stage"])
        self.managed_children.append(binding["receipt"])
        return parent, binding, child

    def assert_child_resume_is_read_only(self):
        """A cold packet resumes a Markdown child without moving the parent."""
        parent, binding, child = self.assert_parent_parked()
        before_parent = (self.run_dir / "state.md").read_bytes()
        before_child = (self.run_dir / binding["receipt"]).read_bytes()
        packet = self.cli("next").stdout
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before_parent)
        self.assertEqual((self.run_dir / binding["receipt"]).read_bytes(), before_child)
        self.assertIn(self.state()["action"]["id"], packet)
        self.assertIn("Managed Improve binding:", packet)
        self.assertEqual(self.managed_child(), child)
        self.assertEqual(self.durable_parent_state(), parent)
        return packet

    def exercise_step_plan_scope_disposition_recovery(self, sid):
        """Keep a repaired scope finding at disposition until it is resolved."""
        self.assertEqual(self.state()["stage"], "step-plan-review")
        self.assert_parent_parked("step-plan")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        finding_id = f"SP-{sid}-SCOPE-RECOVERY"
        self.complete(
            {
                "summary": "A material scope finding requires an explicit frozen-contract disposition before plan revision.",
                "findings": [
                    {
                        "id": finding_id,
                        "severity": "material",
                        "category": "scope",
                        "summary": "The review flags a proposed requirement outside the frozen exact-output contract.",
                    }
                ],
                "coverage_review": self.step_plan_coverage(),
                "context_evidence": self.step_plan_context_evidence(sid),
                "test_review": "The existing exact-output case remains planned, but it cannot authorize a new scope.",
                "learnings": "A material scope finding must remain at explicit disposition after interruption and cold recovery.",
                "knowledge_read": self.read_knowledge(sid),
            },
            action_id=review_action,
            label=f"{sid}-scope-review-before-repair",
        )
        self.assertEqual(self.state()["stage"], "step-plan-disposition")
        self.assert_parent_parked("step-plan")

        disposition_action = self.action_id()
        reason = "The fixture interrupts the material scope disposition and must not bypass its frozen-contract resolution."
        self.cli(
            "repair",
            "--run-dir",
            str(self.run_dir),
            "--action",
            disposition_action,
            "--reason",
            reason,
            cwd=self.root,
        )
        parked = self.durable_parent_state()
        binding = parked["managed_improve"]
        self.assertEqual(parked["stage"], "managed-improve")
        self.assertEqual(binding["profile"], "step-plan")
        self.assertEqual(binding["status"], "active")
        self.assertIsInstance(parked.get("paused"), str)
        interrupted = store.read_record(self.run_dir / binding["receipt"])["child"]
        self.assertEqual(interrupted["status"], "active")
        self.assertEqual(interrupted["current_phase"], "step-plan-disposition")
        self.assertTrue(interrupted["paused"])
        self.assertEqual(interrupted["phase_records"][-1]["kind"], "repair")

        packet = self.cold_next_is_read_only(binding["receipt"])
        self.assertIn("step-plan-disposition", packet)
        self.cli("resume", "--run-dir", str(self.run_dir), cwd=self.root)
        self.assertEqual(self.state()["stage"], "step-plan-disposition")
        self.assert_parent_parked("step-plan")
        self.assertFalse(self.managed_child()["paused"])
        self.assert_child_resume_is_read_only()

        rejected, _ = self.complete(
            {"summary": "A stale review callback cannot bypass the required disposition."},
            action_id=review_action,
            code=2,
            label=f"{sid}-scope-stale-review-rejected",
        )
        self.assertIn("action", rejected.stdout + rejected.stderr)
        self.assertEqual(self.state()["stage"], "step-plan-disposition")
        self.complete(
            {
                "summary": "The frozen exact-output contract proves the scope finding was a false positive.",
                "disposition": "no-contract-change",
                "resolutions": [
                    {
                        "id": finding_id,
                        "evidence": "The frozen declared output and planned exact-output case exclude the proposed broader requirement.",
                    }
                ],
            },
            label=f"{sid}-scope-disposition-resolved",
        )
        self.assertEqual(self.state()["stage"], "step-plan-review")

    def complete(self, payload, **kwargs):
        """Assert every child callback preserves the parent wait cursor."""
        before = self.durable_parent_state()
        binding = before.get("managed_improve")
        process, result = super().complete(payload, **kwargs)
        if process.returncode == 0 and isinstance(binding, dict):
            after = self.durable_parent_state()
            active = after.get("managed_improve")
            if isinstance(active, dict):
                self.assertEqual(after["stage"], "managed-improve")
                self.assertEqual(after["action"]["id"], binding["parent_action"])
                self.assertEqual(active["id"], binding["id"])
                self.assertEqual(active["binding_sha256"], binding["binding_sha256"])
        return process, result

    def verify_current(self, manifest, *, code=0, label="checks", reason=None):
        """Allow a documented retry after this walk intentionally changes a manifest."""
        path = self.record(label, manifest)
        args = ["verify", "--action", self.action_id(), "--manifest", path]
        if reason is not None:
            args.extend(["--reason", reason])
        return self.cli(*args, code=code)

    def local_test_plan(self, sid):
        product = self.product_for(sid)
        return {
            "cases": [
                {
                    "case_id": f"CASE-{sid}-EXACT",
                    "contract_id": f"T-{sid}",
                    "requirement": f"Persist the declared exact-output artifact for {sid}.",
                    "inputs": [f"isolated {sid} fixture worktree"],
                    "expected_outcome": product,
                    "test_selectors": [
                        f"tests/test_{sid.lower()}.py::test_{sid.lower()}_exact_output"
                    ],
                    "check_ids": [f"T-{sid}"],
                    "environment": "isolated local Python worktree",
                    "fixture": f"the committed {sid} fixture artifact",
                }
            ],
            "coverage": [
                {
                    "surface": "unit",
                    "disposition": "selected",
                    "reason": "The exact output is a deterministic local unit boundary.",
                },
                {
                    "surface": "mock_fake",
                    "disposition": "not-applicable",
                    "reason": "The fixture has no external collaborator to fake.",
                },
                {
                    "surface": "integration",
                    "disposition": "not-applicable",
                    "reason": "The fixture has no separate local process or service boundary.",
                },
                {
                    "surface": "end_to_end",
                    "disposition": "not-applicable",
                    "reason": "The fixture exposes no user journey beyond the declared file output.",
                },
                {
                    "surface": "browser_service_api",
                    "disposition": "not-applicable",
                    "reason": "The fixture has no browser, service, or API surface.",
                },
            ],
        }

    def start_step_plan(self, sid):
        self.assertIn(self.state()["stage"], ("step-plan", "improve-plan"))
        route = "initial" if self.state()["stage"] == "step-plan" else "improve"
        payload = {
            "summary": "The candidate binds scope, implementation evidence, cases, checks, and documentation.",
            "body": self.step_plan_candidate(
                sid,
                "draft",
                parent_ids=self.step_plan_parent_ids(sid) if route == "improve" else [],
            ),
            "skill_assessment": self.skill_assessment(),
            "test_plan": self.local_test_plan(sid),
        }
        self.complete(payload, label=f"{sid}-{route}-managed-step-plan-draft")
        self.assertEqual(self.state()["stage"], "step-plan-review")
        self.assert_parent_parked("step-plan")
        return route

    def run_step_plan_pass(
        self,
        sid,
        number,
        *,
        material=False,
        finding_id=None,
        staged_product_path=None,
    ):
        """Keep the legacy local-plan evidence, adding the managed case matrix."""
        self.assertEqual(self.state()["stage"], "step-plan-review")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        knowledge_read = self.read_knowledge(sid)
        finding_id = finding_id or f"SP-{sid}-{number}"
        review = {
            "summary": "The local-plan review retains the exact outcome and every current coverage dimension.",
            "findings": [
                {
                    "id": finding_id,
                    "severity": "material" if material else "trivial",
                    "category": "implementation",
                    "summary": "The exact-output boundary needs a checked local plan record.",
                }
            ],
            "coverage_review": self.step_plan_coverage(),
            "context_evidence": self.step_plan_context_evidence(sid),
            "test_review": "The independent expected output remains mapped to its selected executable check.",
            "learnings": "The plan review used current context, history, and the declared test boundary.",
            "knowledge_read": knowledge_read,
        }
        self.complete(review, action_id=review_action, label=f"{sid}-managed-plan-{number}-review")
        self.assertEqual(self.state()["stage"], "step-plan-revise")
        self.complete(
            {
                "summary": "The revised candidate retains the complete local case matrix and resolves the scoped finding.",
                "body": self.step_plan_candidate(sid, f"managed pass {number}"),
                "test_plan": self.local_test_plan(sid),
                "material": material,
                "addresses": [finding_id],
                "resolutions": [
                    {
                        "id": finding_id,
                        "evidence": "The candidate names the exact case, independent outcome, check, and documentation decision.",
                    }
                ],
                "test_changes": "The plan retains its exact independent output oracle.",
                "learnings": "The revised plan keeps every required case and prevents an untested output rewrite.",
                "skill_assessment": self.skill_assessment(),
            },
            label=f"{sid}-managed-plan-{number}-revise",
        )
        self.assertEqual(self.state()["stage"], "step-plan-verify")
        check_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            check_action,
            "--manifest",
            self.record(f"{sid}-managed-plan-{number}-checks", self.step_plan_manifest(sid)),
        )
        self.complete(
            {"summary": "The fresh candidate lint and exact expected-outcome checks passed."},
            action_id=check_action,
            label=f"{sid}-managed-plan-{number}-verify",
        )
        self.assertEqual(self.state()["stage"], "step-plan-commit")
        commit_action = self.action_id()
        commit = self.step_plan_commit(sid, staged_product_path=staged_product_path)
        _, result = self.complete(
            {
                "summary": "The audit commit records the reviewed local plan without changing product content.",
                "commit": commit,
            },
            action_id=commit_action,
            label=f"{sid}-managed-plan-{number}-commit",
        )
        return {
            "review_action": review_action,
            "check_action": check_action,
            "commit_action": commit_action,
            "commit": commit,
            "result": result,
            "finding_id": finding_id,
        }

    def start_step(self, sid, *, exercise_failed_and_stale=False):
        """Preserve a real baseline failure before the product child starts."""
        self.assertEqual(self.state()["active_step"], sid)
        self.assertEqual(self.state()["stage"], "implement")
        self.write_implementation(sid, wrong_output=exercise_failed_and_stale)
        implement_action = self.action_id()
        baseline_manifest = ACTION.ShipLoopActionWalkFixture.manifest_for(self, sid)
        if exercise_failed_and_stale:
            self.verify_current(baseline_manifest, code=2, label=f"{sid}-managed-baseline-failed")
            self.complete(
                {
                    "summary": "A failed baseline cannot be treated as implementation evidence.",
                    "test_review": "The exact-output check failed before the declared artifact was repaired.",
                },
                action_id=implement_action,
                code=2,
                label=f"{sid}-managed-baseline-rejected",
            )
            worktree = self.worktree(sid)
            (worktree / f"{sid.lower()}.txt").write_text(
                self.output_for(sid) + "\n", encoding="utf-8"
            )
            self.git("add", f"{sid.lower()}.txt", cwd=worktree)
            self.git("commit", "-m", "Repair managed fixture output after a failed test", cwd=worktree)
        self.verify_current(baseline_manifest, label=f"{sid}-managed-baseline-green")
        self.complete(
            {
                "summary": "The baseline source and exact-output checks are current.",
                "test_review": "The declared artifact is checked exactly before the managed product review begins.",
            },
            action_id=implement_action,
            label=f"{sid}-managed-implementation",
        )
        self.assertEqual(self.state()["stage"], "review")
        self.assert_parent_parked("product")

    def write_product_test(self, sid):
        worktree = self.worktree(sid)
        tests = worktree / "tests"
        tests.mkdir(exist_ok=True)
        target = tests / f"test_{sid.lower()}.py"
        target.write_text(
            "from pathlib import Path\n\n"
            f"def test_{sid.lower()}_exact_output():\n"
            f"    assert Path({sid.lower() + '.txt'!r}).read_text(encoding='utf-8') == {self.output_for(sid) + chr(10)!r}\n\n"
            "if __name__ == '__main__':\n"
            f"    test_{sid.lower()}_exact_output()\n",
            encoding="utf-8",
        )
        return target

    def assert_bound_product_test_rejects_wrong_output(self, sid):
        """Prove the exact argv executes its generated assertion."""
        worktree = self.worktree(sid)
        output = worktree / f"{sid.lower()}.txt"
        original = output.read_bytes()
        output.write_text("wrong-output\n", encoding="utf-8")
        try:
            process = subprocess.run(
                [sys.executable, "-B", f"tests/test_{sid.lower()}.py"],
                cwd=worktree,
                capture_output=True,
                text=True,
                env=self.env,
            )
        finally:
            output.write_bytes(original)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("AssertionError", process.stderr)

    def assert_bound_skill_example_rejects_wrong_input(self, sid):
        """Prove the selected skill example executes its entrypoint assertion."""
        process = subprocess.run(
            [sys.executable, "-B", "tests/test_skill_example.py"],
            cwd=self.worktree(sid),
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("AssertionError", process.stderr)

    def managed_manifest_for(self, sid, *, include_skill=None):
        worktree = self.worktree(sid)
        test_path = f"tests/test_{sid.lower()}.py"
        if include_skill is None:
            include_skill = (worktree / "tests" / "test_skill_example.py").is_file()
        checks = [
            {
                "id": "syntax",
                "kind": "lint",
                "argv": [
                    sys.executable,
                    "-B",
                    "-c",
                    f"from pathlib import Path; compile(Path({sid.lower() + '.py'!r}).read_text(), {sid.lower() + '.py'!r}, 'exec')",
                ],
                "acceptance": [],
            },
            {
                "id": f"T-{sid}",
                "kind": "test",
                "argv": [sys.executable, "-B", test_path],
                "acceptance": [self.product_for(sid)],
            },
        ]
        if include_skill:
            checks.append(
                {
                    "id": "skill-example",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "tests/test_skill_example.py"],
                    "acceptance": [],
                }
            )
        self.assertTrue((worktree / test_path).is_file())
        return {"checks": checks}

    def managed_manifest_reason(self, sid):
        return (
            f"The managed {sid} verification replaces the baseline output probe with "
            "the frozen direct test binding and retains its independent expected outcome."
        )

    def managed_test_bindings(self, sid):
        """Bind the planned selector to the exact real test command."""
        test_path = f"tests/test_{sid.lower()}.py"
        selector = f"{test_path}::test_{sid.lower()}_exact_output"
        return {
            "bindings": [
                {
                    "check_id": f"T-{sid}",
                    "argv": [sys.executable, "-B", test_path],
                    "case_ids": [f"CASE-{sid}-EXACT"],
                    "selectors": [selector],
                    "selection": {
                        "mode": "direct",
                        "evidence": "The exact command directly runs the planned fixture test file.",
                    },
                }
            ]
        }

    def retained_skill_examples(self, receipt):
        """Read selected skill evidence from completed cycles and the current pass."""
        iterations = receipt.get("improve_cycles", [])
        self.assertIsInstance(iterations, list)
        current = receipt.get("iteration")
        self.assertIsInstance(current, dict)
        examples = []
        by_check_id = {}
        for iteration in [*iterations, current]:
            self.assertIsInstance(iteration, dict)
            skill = iteration.get("skill_validation")
            if skill is None:
                continue
            self.assertIsInstance(skill, dict)
            result = skill.get("result")
            self.assertIsInstance(result, dict)
            for example in result.get("executable_examples", []):
                self.assertIsInstance(example, dict)
                check_id = example["check_id"]
                argv = [sys.executable, "-B", example["path"]]
                prior = by_check_id.get(check_id)
                if prior is not None:
                    self.assertEqual(prior["argv"], argv)
                    continue
                row = {"id": check_id, "argv": argv}
                by_check_id[check_id] = row
                examples.append(row)
        return examples

    def managed_release_checks(self):
        """Build current test bindings plus historical selected skill checks."""
        checks = []
        check_ids = set()
        skill_checks = {}
        for sid in ("S1", "S2"):
            receipt = self.receipt(sid)
            plan = receipt["sdlc"]["test_plan"]
            cases = {row["case_id"]: row for row in plan["cases"]}
            authored = receipt["iteration"]["test_refinement"]
            for binding in authored["bindings"]["bindings"]:
                check_id = binding["check_id"]
                self.assertNotIn(check_id, check_ids)
                check_ids.add(check_id)
                checks.append(
                    {
                        "id": check_id,
                        "kind": "test",
                        "argv": list(binding["argv"]),
                        "acceptance": [
                            cases[case_id]["expected_outcome"]
                            for case_id in binding["case_ids"]
                        ],
                    }
                )

            for example in self.retained_skill_examples(receipt):
                check_id = example["id"]
                prior = skill_checks.get(check_id)
                if prior is not None:
                    self.assertEqual(prior["argv"], example["argv"])
                    continue
                self.assertNotIn(check_id, check_ids)
                check_ids.add(check_id)
                row = {
                    "id": check_id,
                    "kind": "test",
                    "argv": example["argv"],
                    "acceptance": [],
                }
                skill_checks[check_id] = row
                checks.append(row)
        return checks

    def selected_skill_example_check(self, checks):
        """Find the one historical selected-skill command in an outer check set."""
        matches = [row for row in checks if row["id"] == "skill-example"]
        self.assertEqual(len(matches), 1)
        check = matches[0]
        self.assertEqual(check["kind"], "test")
        self.assertEqual(
            check["argv"], [sys.executable, "-B", "tests/test_skill_example.py"]
        )
        return check

    def add_managed_release_checks(self, manifest):
        checks = manifest["checks"]
        check_ids = {row["id"] for row in checks}
        self.assertEqual(len(check_ids), len(checks))
        retained = self.managed_release_checks()
        self.assertFalse(check_ids.intersection(row["id"] for row in retained))
        checks.extend(retained)
        self.assertEqual(len({row["id"] for row in checks}), len(checks))
        return manifest

    def managed_quality_manifest(self):
        """Re-run each completed local binding and selected skill example."""
        return self.add_managed_release_checks(
            copy.deepcopy(
                ACTION.ShipLoopActionWalkFixture.manifest_for(self, "S2", quality=True)
            )
        )

    def objective_manifest(self, kind, *, fail=False):
        manifest = super().objective_manifest(kind, fail=fail)
        if kind == "quality" and not fail:
            self.add_managed_release_checks(manifest)
        return manifest

    def create_fixture_skill(self, sid):
        worktree = self.worktree(sid)
        skill_dir = worktree / "skills" / "fixture-output"
        skill_dir.mkdir(parents=True, exist_ok=True)
        entrypoint = skill_dir / "SKILL.md"
        entrypoint.write_text(
            "---\n"
            "name: fixture-output\n"
            "description: Check the deterministic fixture exact-output contract.\n"
            "---\n\n"
            "Use this local skill when validating the fixture output and its executable example.\n",
            encoding="utf-8",
        )
        index = worktree / "skills" / "INDEX.md"
        index.write_text(
            "# Fixture skills\n\n[fixture output](fixture-output/SKILL.md)\n",
            encoding="utf-8",
        )
        example = worktree / "tests" / "test_skill_example.py"
        example.write_text(
            "from pathlib import Path\n\n"
            "def test_skill_entrypoint_is_indexed():\n"
            "    entrypoint = Path('skills/fixture-output/SKILL.md')\n"
            "    assert entrypoint.is_file()\n"
            "    assert 'Use this local skill when validating the fixture output' in entrypoint.read_text(encoding='utf-8')\n"
            "    assert 'fixture-output/SKILL.md' in Path('skills/INDEX.md').read_text(encoding='utf-8')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    test_skill_entrypoint_is_indexed()\n",
            encoding="utf-8",
        )
        return entrypoint, index, example

    def documentation_payload(self, *, select_skill):
        reusable = {
            "decision": "not-needed",
            "rationale": "The later fixture pass has no new reusable workflow beyond the already validated local skill.",
            "paths": [],
            "references": [],
        }
        if select_skill:
            reusable = {
                "decision": "created",
                "rationale": "The deterministic output check is reusable by later fixture maintenance work.",
                "paths": ["skills/fixture-output/SKILL.md"],
                "references": ["skills/INDEX.md"],
                "purpose": "Preserve the local exact-output validation procedure.",
                "when": "Use before changing a fixture output contract.",
                "how": "Read the entrypoint and run the listed local example.",
                "inputs": "The fixture worktree and declared exact-output artifact.",
                "validation": "The indexed entrypoint and executable example are checked by the bound manifest.",
            }
        return {
            "summary": "The documentation and reusable-skill decision is recorded before verification.",
            "documentation": {
                "decision": "not-needed",
                "rationale": "This isolated fixture has no product README to update.",
                "paths": [],
                "references": [],
            },
            "reusable_skill": reusable,
            "material": False,
            "learnings": "Documentation and reuse decisions remain bound to the verified candidate.",
        }

    def skill_validation_payload(self):
        return {
            "skill_validation": {
                "decision": "created",
                "rationale": "The local skill has a future fixture-maintenance audience and a real checked example.",
                "entrypoint": "skills/fixture-output/SKILL.md",
                "index": "skills/INDEX.md",
                "executable_examples": [
                    {
                        "path": "tests/test_skill_example.py",
                        "check_id": "skill-example",
                        "purpose": "Prove the local index exposes the concrete skill entrypoint.",
                    }
                ],
                "failure_recovery": "Restore the indexed local entrypoint and rerun the named example check.",
                "host_limitations": "The example validates local discovery only and does not install a global skill.",
            }
        }

    def exercise_product_repair_pause_resume(self, sid):
        """Use the public recovery commands before product code/test authoring."""
        self.assertEqual(self.state()["stage"], "improve-apply")
        before = copy.deepcopy(self.managed_binding())
        child_id = before["id"]
        repair_reason = (
            "The fixture restarts the checked product pass before Apply so repair "
            "cannot inherit an unfinished convergence claim."
        )
        self.cli(
            "repair",
            "--run-dir",
            str(self.run_dir),
            "--action",
            self.action_id(),
            "--reason",
            repair_reason,
            cwd=self.root,
        )
        self.assertEqual(self.managed_binding()["id"], child_id)
        self.assertEqual(self.state()["stage"], "review")
        self.assert_parent_parked("product")
        repaired = self.managed_child()
        self.assertEqual(repaired["phase_records"][-1]["kind"], "repair")
        self.assertEqual(repaired["passes"], [])
        self.assert_child_resume_is_read_only()

        pause_reason = (
            "The fixture pauses the repaired child before test authoring to prove "
            "that resume restores the same durable child cursor."
        )
        self.cli(
            "pause",
            "--run-dir",
            str(self.run_dir),
            "--reason",
            pause_reason,
            cwd=self.root,
        )
        paused = self.durable_parent_state()
        self.assertEqual(paused["managed_improve"]["id"], child_id)
        self.assertEqual(paused["managed_improve"]["status"], "blocked")
        paused_child = store.read_record(
            self.run_dir / paused["managed_improve"]["receipt"]
        )["child"]
        self.assertEqual(paused_child["status"], "blocked")
        self.assertEqual(paused_child["phase_records"][-1]["kind"], "blocked")
        self.cold_next_is_read_only(paused["managed_improve"]["receipt"])
        paused_sdlc = self.cli(
            "context",
            "--run-dir",
            str(self.run_dir),
            "--section",
            "sdlc",
            "--limit",
            "8000",
            cwd=self.root,
        ).stdout
        continuation = re.search(
            r"Continue: --offset (\d+) --limit \d+ --digest ([0-9a-f]+)",
            paused_sdlc,
        )
        self.assertIsNotNone(continuation, paused_sdlc)
        paused_sdlc += self.cli(
            "context",
            "--run-dir",
            str(self.run_dir),
            "--section",
            "sdlc",
            "--offset",
            continuation.group(1),
            "--limit",
            "8000",
            "--digest",
            continuation.group(2),
            cwd=self.root,
        ).stdout
        for fact in (
            '"current_stage": "managed-improve"',
            '"profile": "product"',
            '"status": "blocked"',
            '"stage": "review"',
            '"number": 36',
        ):
            self.assertIn(fact, paused_sdlc)

        self.cli("resume", "--run-dir", str(self.run_dir), cwd=self.root)
        self.assertEqual(self.managed_binding()["id"], child_id)
        self.assertEqual(self.state()["stage"], "review")
        self.assert_parent_parked("product")
        resumed = self.managed_child()
        self.assertEqual(resumed["phase_records"][-1]["kind"], "resume")
        self.assert_child_resume_is_read_only()

    def run_managed_product_iteration(
        self,
        sid,
        *,
        material,
        select_skill=False,
        reject_missing_plan=False,
        fail_check_first=False,
        exercise_recovery=False,
        exercise_selected_skill_failure=False,
    ):
        """Drive one real product child pass without a nested plan campaign."""
        self.assertEqual(self.state()["stage"], "review")
        self.assert_parent_parked("product")
        review_action = self.action_id()
        self.cli("history", "--action", review_action, "--limit", "10", "--skip", "0", "--full")
        knowledge_read = self.read_knowledge(sid)
        review_learning = "The managed child reviewed current history, code, tests, and the declared exact-output boundary."
        apply_learning = "Material work resets convergence even when its implementation delta is small."
        self.complete(
            {
                "summary": "The product review records one current scoped finding and the retained exact-output test need.",
                "findings": [
                    {
                        "severity": "material" if material else "trivial",
                        "summary": "Material fixture correction" if material else "Trivial fixture review note",
                    }
                ],
                "test_review": "The planned case remains independently observable through a real Python test file.",
                "learnings": review_learning,
                "knowledge_read": knowledge_read,
                "research_assessment": self.research_assessment(),
            },
            action_id=review_action,
            label=f"{sid}-managed-product-review",
        )
        self.assertEqual(self.state()["stage"], "improve-plan")

        plan_payload = {
            "summary": "The pass plan preserves every parent finding, selected test, outcome, and satisfied prerequisite.",
            "body": self.step_plan_candidate(
                sid, "managed product plan", parent_ids=self.step_plan_parent_ids(sid)
            ),
            "test_plan": self.local_test_plan(sid),
            "coverage_review": self.step_plan_coverage(),
            "context_evidence": self.step_plan_context_evidence(sid),
            "prerequisites": [],
            "learnings": "The per-iteration plan is checked once before Apply without starting a second plan campaign.",
            "skill_assessment": self.skill_assessment(),
        }
        if reject_missing_plan:
            before_parent = (self.run_dir / "state.md").read_bytes()
            binding = self.managed_binding()
            before_child = (self.run_dir / binding["receipt"]).read_bytes()
            missing = dict(plan_payload)
            missing.pop("test_plan")
            rejected, _ = self.complete(
                missing,
                code=2,
                label=f"{sid}-managed-plan-missing-test-plan",
            )
            self.assertIn("test_plan", rejected.stdout + rejected.stderr)
            self.assertEqual((self.run_dir / "state.md").read_bytes(), before_parent)
            self.assertEqual((self.run_dir / binding["receipt"]).read_bytes(), before_child)
            self.assertEqual(self.state()["stage"], "improve-plan")
        self.complete(plan_payload, label=f"{sid}-managed-product-plan")
        self.assertEqual(self.state()["stage"], "improve-plan-verify")
        plan_check_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            plan_check_action,
            "--manifest",
            self.record(f"{sid}-managed-product-plan-checks", self.step_plan_manifest(sid)),
        )
        self.complete(
            {"summary": "The bounded per-iteration plan checks passed on the current candidate."},
            action_id=plan_check_action,
            label=f"{sid}-managed-product-plan-verify",
        )
        self.assertEqual(self.state()["stage"], "improve-apply")
        if exercise_recovery:
            self.exercise_product_repair_pause_resume(sid)
            return self.run_managed_product_iteration(
                sid,
                material=material,
                select_skill=select_skill,
                fail_check_first=fail_check_first,
                exercise_selected_skill_failure=exercise_selected_skill_failure,
            )

        worktree = self.worktree(sid)
        if material:
            with (worktree / f"{sid.lower()}.py").open("a", encoding="utf-8") as handle:
                handle.write("# Managed material correction retained by the fixture.\n")
        self.complete(
            {
                "summary": "The checked plan was applied without weakening the declared output oracle.",
                "material": material,
                "test_changes": "The planned test remains required and will be authored before the real check runs.",
                "learnings": apply_learning,
            },
            label=f"{sid}-managed-product-apply",
        )
        self.assertEqual(self.state()["stage"], "test-refine")
        self.complete(
            {
                "summary": "Post-code inspection retained the independent exact-output outcome and selected one executable test.",
                "test_plan": self.local_test_plan(sid),
                "refinement_reason": "The implementation adds no new observable boundary beyond the declared exact output.",
            },
            label=f"{sid}-managed-test-refine",
        )
        self.assertEqual(self.state()["stage"], "test-author")
        test_path = self.worktree(sid) / "tests" / f"test_{sid.lower()}.py"
        existed = test_path.exists()
        self.write_product_test(sid)
        if fail_check_first:
            self.assert_bound_product_test_rejects_wrong_output(sid)
        refinement = {
            "case_id": f"CASE-{sid}-EXACT",
            "disposition": "reused" if existed else "authored",
            "test_paths": [f"tests/test_{sid.lower()}.py"],
            "check_ids": [f"T-{sid}"],
            "coverage": "Checks the declared exact-output result in the active worktree.",
            "oracle": {"decision": "unchanged"},
        }
        if existed:
            refinement["adequacy_reason"] = "The existing real test still maps the complete retained case to the current output check."
        self.complete(
            {
                "summary": "A real Python test maps the planned case to the current exact-output check.",
                "test_refinement": {
                    "cases": [refinement]
                },
                "test_bindings": self.managed_test_bindings(sid),
            },
            label=f"{sid}-managed-test-author",
        )
        self.assertEqual(self.state()["stage"], "iteration-document")
        if select_skill:
            self.create_fixture_skill(sid)
        self.complete(
            self.documentation_payload(select_skill=select_skill),
            label=f"{sid}-managed-iteration-document",
        )
        if select_skill:
            self.assertEqual(self.state()["stage"], "skill-validate")
            self.complete(
                {"summary": "The selected local skill has an indexed entrypoint and a real example check.", **self.skill_validation_payload()},
                label=f"{sid}-managed-skill-validate",
            )
        self.assertEqual(self.state()["stage"], "verify")
        verification_action = self.action_id()
        if exercise_selected_skill_failure:
            self.assertTrue(select_skill)
            entrypoint = worktree / "skills" / "fixture-output" / "SKILL.md"
            original = entrypoint.read_text(encoding="utf-8")
            expected = "Use this local skill when validating the fixture output"
            self.assertIn(expected, original)
            entrypoint.write_text(
                original.replace(
                    expected,
                    "This fixture deliberately supplies an invalid selected-skill input",
                    1,
                ),
                encoding="utf-8",
            )
            self.assert_bound_skill_example_rejects_wrong_input(sid)
            failed_checks = self.verify_current(
                self.managed_manifest_for(sid),
                code=2,
                label=f"{sid}-managed-selected-skill-failed-test",
                reason=self.managed_manifest_reason(sid),
            )
            self.assertIn("Checks FAIL", failed_checks.stdout + failed_checks.stderr)
            failed_record = store.read_record(
                self.run_dir / "checks" / f"{verification_action}.md"
            )
            self.assertFalse(failed_record["results"]["all_passed"])
            failed_skill = next(
                row
                for row in failed_record["results"]["checks"]
                if row["id"] == "skill-example"
            )
            self.assertEqual(failed_skill["status"], "failed")
            self.assertNotEqual(failed_skill["exit"], 0)
            self.assertIn(
                "AssertionError",
                Path(failed_skill["stderr_log"]).read_text(encoding="utf-8"),
            )
            rejected, _ = self.complete(
                {"summary": "A failed selected-skill example cannot satisfy the managed verification action."},
                action_id=verification_action,
                code=2,
                label=f"{sid}-managed-selected-skill-failed-result",
            )
            self.assertIn("repair", rejected.stdout + rejected.stderr)
            self.assertEqual(self.state()["stage"], "verify")
            self.cli(
                "repair",
                "--run-dir",
                str(self.run_dir),
                "--action",
                verification_action,
                "--reason",
                "The selected skill entrypoint changed after documentation and its real executable assertion failed; restart the pass and revalidate it.",
                cwd=self.root,
            )
            self.assertEqual(self.state()["stage"], "review")
            self.assert_parent_parked("product")
            self.assertEqual(self.managed_child()["phase_records"][-1]["kind"], "repair")
            return self.run_managed_product_iteration(
                sid,
                material=material,
                select_skill=select_skill,
            )
        self.verify_current(
            self.managed_manifest_for(sid),
            label=f"{sid}-managed-real-tests",
            reason=self.managed_manifest_reason(sid),
        )
        self.complete(
            {"summary": "The bound lint, exact-output test, and selected skill example all passed."},
            action_id=verification_action,
            label=f"{sid}-managed-verify-result",
        )
        self.assertEqual(self.state()["stage"], "carry-forward")
        carry_payload = self.carry_forward_payload(
            learnings="The managed pass retains the real test, documentation, and skill evidence for later review."
        )
        self.complete(carry_payload, label=f"{sid}-managed-carry-forward")
        self.assertEqual(self.state()["stage"], "commit")
        iteration = copy.deepcopy(self.receipt(sid)["iteration"])
        self.git("add", "-A", cwd=worktree)
        primary = self.formatted_commit(
            sid,
            iteration,
            verification_action,
            review_learning,
            apply_learning,
            carry_payload["learnings"],
        )
        self.complete(
            {
                "summary": "The primary commit retains review, plan, test, documentation, and carry-forward learnings.",
                "commit": primary,
            },
            label=f"{sid}-managed-primary",
        )
        return primary

    def post_inner_candidate(self):
        return {
            "summary": "No broader dependency, preparation, or test strategy change is required.",
            "plan_decision": "no-change",
            "plan_reason": "The completed fixture still satisfies the frozen dependency and system-test contract.",
            "journal": [],
        }

    def finalize_managed_product_child(self, sid):
        """Require a fresh final check before releasing a converged product child."""
        self.assertEqual(self.state()["stage"], "final-verify")
        final_action = self.action_id()
        self.verify_current(self.managed_manifest_for(sid), label=f"{sid}-managed-final-fresh-check")
        self.complete(
            {
                "summary": "Fresh final checks passed after two distinct trivial managed passes.",
                "done_evidence": self.done_evidence(sid),
            },
            action_id=final_action,
            label=f"{sid}-managed-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")

    def exercise_post_inner_cross_profile_recovery(self, sid):
        """Abandon a post-inner objective and bind its evidence to a fresh product child."""
        self.assertEqual(self.state()["stage"], "post-inner")
        kind = self.start_objective(
            self.post_inner_candidate(), label=f"{sid}-post-inner-recovery"
        )
        self.assertEqual(kind, "post-inner")
        self.assertEqual(self.state()["stage"], "objective-review")
        self.assert_parent_parked("objective")
        source_binding = copy.deepcopy(self.managed_binding())
        source_action = self.action_id()
        reason = (
            "The fixture deliberately abandons the post-inner objective so a new "
            "product child must consume its durable replan handoff."
        )
        self.cli(
            "repair",
            "--run-dir",
            str(self.run_dir),
            "--action",
            source_action,
            "--reason",
            reason,
            cwd=self.root,
        )

        source_receipt = self.run_dir / source_binding["receipt"]
        source_receipt_bytes = source_receipt.read_bytes()
        source_record = store.read_record(source_receipt)
        source_child = source_record["child"]
        self.assertEqual(source_child["status"], "needs-replan")
        self.assertIsNone(source_child["current_phase"])
        self.assertEqual(source_child["phase_records"][-1]["kind"], "needs-replan")
        self.assertFalse(
            (self.run_dir / "managed-improve" / f"{source_binding['id']}-certificate.md").exists()
        )

        parked = self.durable_parent_state()
        recovery = parked[improve_bridge.RECOVERY_KEY]
        successor = parked["managed_improve"]
        self.assertEqual(recovery["from_child"], source_binding["id"])
        self.assertEqual(recovery["from_parent_action"], source_binding["parent_action"])
        self.assertEqual(recovery["status"], "needs-replan")
        self.assertEqual(recovery["reason"], reason)
        self.assertEqual(recovery["to_child"], successor["id"])
        self.assertTrue(recovery["evidence_refs"])
        self.assertNotEqual(successor["id"], source_binding["id"])
        self.assertEqual(successor["profile"], "product")
        self.assert_parent_parked("product")
        fresh_child = self.managed_child()
        self.assertEqual(fresh_child["current_phase"], "review")
        self.assertEqual(fresh_child["passes"], [])
        self.assertEqual(fresh_child["phase_records"], [])

        packet = self.assert_child_resume_is_read_only()
        self.assertIn("Required recovery handoff:", packet)
        self.assertIn("Required recovery evidence:", packet)
        for fact in (
            reason,
            source_binding["id"],
            source_binding["parent_action"],
            successor["id"],
        ):
            self.assertIn(fact, packet)
        for reference in recovery["evidence_refs"]:
            path = self.run_dir / reference
            self.assertTrue(path.is_file(), f"missing recovery evidence: {path}")
            self.assertIn(str(path), packet)
        return {
            "recovery": copy.deepcopy(recovery),
            "source_binding": source_binding,
            "source_receipt_bytes": source_receipt_bytes,
            "successor": copy.deepcopy(successor),
        }

    def assert_cross_profile_recovery_imported(self, handoff):
        """A finished successor consumes the active marker but retains proof."""
        source_binding = handoff["source_binding"]
        successor = handoff["successor"]
        recovery = handoff["recovery"]
        source_receipt = self.run_dir / source_binding["receipt"]
        self.assertNotIn(improve_bridge.RECOVERY_KEY, self.durable_parent_state())
        self.assertEqual(source_receipt.read_bytes(), handoff["source_receipt_bytes"])
        source_record = store.read_record(source_receipt)
        self.assertEqual(source_record["child"]["status"], "needs-replan")

        successor_record = store.read_record(self.run_dir / successor["receipt"])
        recovery_input = successor_record["input_identity"]["recovery"]
        self.assertEqual(recovery_input["from_child"], source_binding["id"])
        self.assertEqual(
            recovery_input["from_parent_action"], source_binding["parent_action"]
        )
        self.assertEqual(recovery_input["status"], "needs-replan")
        self.assertEqual(
            recovery_input["reason_sha256"],
            hashlib.sha256(recovery["reason"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            recovery_input["source_receipt_sha256"],
            hashlib.sha256(handoff["source_receipt_bytes"]).hexdigest(),
        )
        self.assertEqual(
            [row["path"] for row in recovery_input["evidence"]],
            recovery["evidence_refs"],
        )
        for evidence in recovery_input["evidence"]:
            self.assertEqual(
                evidence["sha256"],
                hashlib.sha256((self.run_dir / evidence["path"]).read_bytes()).hexdigest(),
            )
        certificate = self.run_dir / "managed-improve" / f"{successor['id']}-certificate.md"
        self.assertTrue(certificate.is_file())

    def finish_managed_step(
        self,
        sid,
        *,
        exercise_failure,
        select_skill_first,
        exercise_product_recovery=False,
        exercise_cross_profile_recovery=False,
    ):
        self.start_step(sid, exercise_failed_and_stale=exercise_failure)
        material = self.run_managed_product_iteration(
            sid,
            material=True,
            select_skill=select_skill_first,
            reject_missing_plan=True,
            fail_check_first=True,
            exercise_recovery=exercise_product_recovery,
            exercise_selected_skill_failure=select_skill_first,
        )
        self.assertEqual(self.state()["stage"], "review")
        first_child = self.managed_child()
        self.assertEqual(first_child["passes"][-1]["outcome"], "material")
        trivial_one = self.run_managed_product_iteration(sid, material=False)
        self.assertEqual(self.state()["stage"], "review")
        trivial_two = self.run_managed_product_iteration(sid, material=False)
        self.assertEqual(self.state()["stage"], "final-verify")
        child = self.managed_child()
        self.assertEqual([row["outcome"] for row in child["passes"]], ["material", "trivial", "trivial"])
        self.assertEqual(len({row["commit"] for row in child["passes"]}), 3)
        # The child receipt is the canonical convergence owner.  A legacy
        # receipt may retain typed pass evidence for compatibility, but it
        # cannot be used as an alternate completion signal.
        self.assertEqual(child["current_phase"], "final-verify")

        self.finalize_managed_product_child(sid)
        if exercise_cross_profile_recovery:
            recovery_handoff = self.exercise_post_inner_cross_profile_recovery(sid)
            first_recovered = self.run_managed_product_iteration(sid, material=False)
            second_recovered = self.run_managed_product_iteration(sid, material=False)
            self.assertEqual(self.state()["stage"], "final-verify")
            recovered_child = self.managed_child()
            self.assertEqual(
                [row["outcome"] for row in recovered_child["passes"]],
                ["trivial", "trivial"],
            )
            self.finalize_managed_product_child(sid)
            self.assert_cross_profile_recovery_imported(recovery_handoff)
            self.assertTrue(first_recovered)
            self.assertTrue(second_recovered)
        self.converge_objective(
            self.post_inner_candidate(),
            label=f"{sid}-post-inner",
        )
        self.assertEqual(self.state()["stage"], "merge")
        self.complete({"summary": "Integrate the verified managed worktree."}, label=f"{sid}-managed-merge")
        return material, trivial_one, trivial_two

    def assert_terminal_managed_certificate(self):
        """Require the durable terminal proof and reject a changed certificate."""
        terminal = self.durable_parent_state()
        self.assertFalse(
            any(key.startswith("_") for key in terminal),
            "terminal parent state retained transient bridge metadata",
        )
        imported = terminal.get(improve_bridge.IMPORT_KEY)
        self.assertIsInstance(imported, dict)
        checked = improve_bridge.validate_imported_certificate(self.run_dir, terminal)
        self.assertIsNotNone(checked)
        self.assertEqual(checked["certificate_sha256"], imported["certificate_sha256"])
        self.assertTrue(delivery.valid_complete_report(self.run_dir, terminal))

        certificate_path = self.run_dir / imported["certificate"]
        original = certificate_path.read_bytes()
        certificate = store.read_record(certificate_path)
        certificate["certificate_sha256"] = "0" * 64
        store.write_record(
            certificate_path,
            certificate,
            title=improve_bridge.CERTIFICATE_TITLE,
        )
        try:
            self.assertFalse(delivery.valid_complete_report(self.run_dir, terminal))
            before_state = (self.run_dir / "state.md").read_bytes()
            rejected = self.cli(
                "next", "--run-dir", str(self.run_dir), code=2, cwd=self.root
            )
            self.assertIn("certificate", rejected.stdout + rejected.stderr)
            self.assertEqual((self.run_dir / "state.md").read_bytes(), before_state)
        finally:
            certificate_path.write_bytes(original)
        self.assertTrue(delivery.valid_complete_report(self.run_dir, terminal))


class ManagedShipLoopWalkTests(ManagedShipLoopWalkFixture):
    def test_managed_child_owns_plan_product_tests_skill_and_outer_completion(self):
        """Walk one small repository from planning through terminal handoff."""
        self.bootstrap_to_first_step_plan()
        self.assertEqual((self.state()["phase"], self.state()["stage"], self.state()["active_step"]), ("implement", "step-plan", "S1"))

        self.start_step_plan("S1")
        self.assert_child_resume_is_read_only()
        parent_action = self.durable_parent_state()["action"]["id"]
        before = {
            name: (self.run_dir / name).read_bytes()
            for name in ("state.md", self.managed_binding()["receipt"])
        }
        rejected, _ = self.complete(
            {"summary": "A parent callback cannot complete an active child."},
            action_id=parent_action,
            code=2,
            label="managed-parent-callback-rejected",
        )
        self.assertIn("action", rejected.stdout + rejected.stderr)
        self.assertEqual(
            {name: (self.run_dir / name).read_bytes() for name in before}, before
        )

        self.exercise_step_plan_scope_disposition_recovery("S1")
        self.converge_step_plan("S1")
        self.assertEqual(self.state()["stage"], "implement")
        self.finish_managed_step(
            "S1",
            exercise_failure=True,
            select_skill_first=True,
            exercise_product_recovery=True,
            exercise_cross_profile_recovery=True,
        )
        self.assertEqual(self.state()["active_step"], "S2")
        self.assertEqual(self.state()["stage"], "step-plan")

        self.start_step_plan("S2")
        self.converge_step_plan("S2")
        self.assertEqual(self.state()["stage"], "implement")
        self.finish_managed_step("S2", exercise_failure=False, select_skill_first=False)
        self.assertEqual(self.state()["stage"], "coverage")

        self.converge_objective(
            {"summary": "The planned system-test and release coverage is complete for the local fixture."},
            label="coverage",
        )
        self.assertEqual(self.state()["stage"], "quality")
        quality_manifest = self.managed_quality_manifest()
        selected_skill = self.selected_skill_example_check(quality_manifest["checks"])
        quality_action = self.action_id()
        self.verify_current(
            quality_manifest,
            label="managed-whole-product-checks",
            reason=(
                "The final assembled-tree check expands the active local manifest "
                "to cover both retained direct test bindings and the selected "
                "skill example alongside whole-product acceptance."
            ),
        )
        quality_checks = store.read_record(
            self.run_dir / "checks" / f"{quality_action}.md"
        )["results"]["checks"]
        executed_skill = self.selected_skill_example_check(quality_checks)
        self.assertEqual(executed_skill["argv"], selected_skill["argv"])
        self.assertEqual((executed_skill["status"], executed_skill["exit"]), ("passed", 0))
        self.converge_objective(
            {
                "summary": "The merged artifacts pass whole-product syntax and exact-output checks.",
                "test_review": "The system test and both local output contracts are covered by real commands.",
                "quality_review": "No external deployment boundary exists for this local fixture.",
            },
            label="quality",
        )
        quality_certificate = store.read_record(
            self.run_dir / self.state()["objective"]["certificate"]
        )
        objective_checks = store.read_record(
            self.run_dir / "checks" / f"{quality_certificate['final_check_action']}.md"
        )["results"]["checks"]
        objective_skill = self.selected_skill_example_check(objective_checks)
        self.assertEqual(objective_skill["argv"], selected_skill["argv"])
        self.assertEqual((objective_skill["status"], objective_skill["exit"]), ("passed", 0))
        self.assertEqual(self.state()["stage"], "handoff")
        self.converge_objective(
            {
                "summary": "The durable handoff names the checked local artifacts, test evidence, and recovery limits.",
                "journal": [],
            },
            label="handoff",
        )
        self.assertEqual((self.state()["phase"], self.state()["stage"]), ("done", "done"))
        self.assertTrue((self.run_dir / "report.html").is_file())
        self.assert_terminal_managed_certificate()
        self.assertTrue(self.managed_children)
        self.assertTrue(
            all((self.run_dir / path).is_file() for path in set(self.managed_children)),
            "child Markdown receipts remain durable after parent completion",
        )


if __name__ == "__main__":
    unittest.main()
