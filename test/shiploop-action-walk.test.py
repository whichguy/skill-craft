#!/usr/bin/env python3
"""End-to-end action-walk acceptance coverage for the ShipLoop protocol.

The test deliberately uses the extensionless public CLI as a subprocess.  It
does not fake an action transition: each transition consumes a Markdown result
record, every check is a real ``python -B`` command, and every Improve commit
is made in the allocated Git worktree.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_store as store  # noqa: E402
import shiploop_history_policy as history_policy  # noqa: E402
import shiploop_objectives as objectives  # noqa: E402
import shiploop_step_planning as step_planning  # noqa: E402


def load_core():
    """Load the extensionless command module without invoking its CLI entrypoint."""
    loader = importlib.machinery.SourceFileLoader("shiploop_action_walk_core", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {CLI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


CORE = load_core()


class ShipLoopActionWalkFixture(unittest.TestCase):
    """Reusable real-CLI planning and execution fixture for ShipLoop tests."""

    product_one = "s1.txt contains exactly one line: first"
    product_two = "s2.txt contains exactly one line: second"
    product_research = "s3.txt contains exactly one line: research"
    done_sentence = product_two
    research_rubric = (
        "prompt_coverage",
        "environment_conditions",
        "source_quality",
        "contradictions",
        "best_practices",
        "access_readiness",
        "invocation_contracts",
        "test_deploy_feasibility",
        "remaining_unknowns",
    )
    step_plan_rubric = (
        "step_scope",
        "current_implementation",
        "environment",
        "dependencies",
        "flows",
        "edge_conditions",
        "second_order_effects",
        "implicit_requirements",
        "test_strategy",
        "documentation",
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-action-walk-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.run_dir = self.repo / ".shiploop"
        self.counter = 0
        self._trace_completed_actions = False
        self.transition_trace = []
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "ShipLoop Action Walk")
        self.git("config", "user.email", "shiploop-action-walk@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")
        self.bound_plan = self.root / "bound-plan.md"
        self.bound_plan.write_text(
            "# Fixture delivery plan\n\n"
            "## Review Coverage\n\n"
            "None — residual loop waived: this fixture exercises the action protocol, not a product review.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, cwd=None, code=0):
        process = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process.stdout.strip()

    def cli(self, *args, code=0, cwd=None):
        process = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process

    def record(self, label, payload):
        self.counter += 1
        path = self.records / f"{self.counter:02d}-{label}.md"
        store.write_record(path, payload, title=f"Action walk {label}")
        return str(path)

    def state(self):
        return store.read_record(self.run_dir / "state.md")

    def receipt(self, sid):
        return store.read_record(self.run_dir / "steps" / f"{sid}.md")

    def action_id(self):
        return self.state()["action"]["id"]

    def start_transition_trace(self):
        """Capture only accepted public callbacks that advance Markdown state."""
        self._trace_completed_actions = True
        self.transition_trace = []

    def record_completed_transition(self, before, after, action_id, *, source):
        self.assertGreater(after["revision"], before["revision"])
        self.assertIn(action_id, after["completed_actions"])
        completed_stage = before["stage"]
        if before["stage"] == "objective-finalize":
            # Objective finalization deliberately completes its owning base
            # stage through the protocol's internal stage override.  Do not
            # generalize this to another stage or caller-provided transition.
            binding = before.get("objective")
            self.assertIsInstance(binding, dict)
            self.assertIn(binding.get("kind"), objectives.KINDS)
            completed_stage = binding["base_stage"]
            self.assertEqual(
                completed_stage, objectives.BASE_STAGES[binding["kind"]]
            )
        self.assertEqual(after["last_completion"]["action"], action_id)
        self.assertEqual(after["last_completion"]["stage"], completed_stage)
        self.transition_trace.append(
            {
                "action": action_id,
                "source": source,
                "from_phase": before["phase"],
                "from_stage": before["stage"],
                "completed_stage": completed_stage,
                "from_step": before.get("active_step"),
                "to_phase": after["phase"],
                "to_stage": after["stage"],
                "to_step": after.get("active_step"),
                "revision": after["revision"],
            }
        )

    def authoritative_snapshot(self, *receipt_paths):
        """Return exact bytes for state, chronology, and selected receipts."""
        snapshot = {}
        for relative in ("state.md", "history.md", *receipt_paths):
            path = self.run_dir / relative
            self.assertTrue(path.is_file(), f"expected authoritative record: {path}")
            snapshot[relative] = path.read_bytes()
        return snapshot

    def assert_authority_unchanged(self, before, *receipt_paths):
        self.assertEqual(before, self.authoritative_snapshot(*receipt_paths))

    def cold_next_is_read_only(self, *receipt_paths):
        before = self.authoritative_snapshot(*receipt_paths)
        packet = self.cli("next", "--run-dir", str(self.run_dir), cwd=self.root).stdout
        self.assert_authority_unchanged(before, *receipt_paths)
        return packet

    def assert_stage_subsequence(self, stages, required):
        """Assert an ordered path while allowing required loop repetitions."""
        cursor = 0
        for stage in required:
            try:
                cursor = stages.index(stage, cursor) + 1
            except ValueError:
                self.fail(
                    f"missing required ordered stage {stage!r}; observed: {stages!r}"
                )

    def complete(
        self,
        payload,
        *,
        action_id=None,
        code=0,
        label="result",
        include_research_assessment=True,
    ):
        before = self.state() if self._trace_completed_actions else None
        if self.state().get("system_test_protocol_version") == 1 and self.state()["stage"] in ("carry-forward", "post-inner", "quality"):
            payload = dict(payload)
            payload.setdefault("system_test_review", {
                "decision": "no-change", "evidence": "SYS-INTEGRATED-001 remains mapped to the dependent S2 check after S1; no new global requirement or deployment boundary was discovered.",
                "discovery_ids": [],
            })
        if (
            include_research_assessment
            and self.state()["stage"] == "review"
            and "research_assessment" not in payload
        ):
            payload = dict(payload, research_assessment=self.research_assessment())
        aid = action_id or self.action_id()
        result = self.record(label, payload)
        process = self.cli(
            "complete", "--action", aid, "--result", result, code=code
        )
        if before is not None and process.returncode == 0:
            after = self.state()
            # A successful exact replay is intentionally idempotent; it is not
            # a new durable transition and therefore does not enter the trace.
            if after["revision"] > before["revision"]:
                self.record_completed_transition(
                    before, after, aid, source="public-cli"
                )
        return process, result

    def research_assessment(self, status="not-needed", *, questions=None):
        self.assertIn(status, {"not-needed", "resolved", "required", "blocked"})
        if status == "not-needed":
            return {
                "status": status,
                "summary": "The local fixture has no new research question for this review.",
                "evidence": [],
                "questions": [],
            }
        questions = questions or ["Does the local exact-output contract remain sufficient?"]
        return {
            "status": status,
            "summary": "The review records a scoped local research question.",
            "evidence": ["research-evidence.md#SRC-LOCAL-001"],
            "questions": questions,
        }

    def research_review(self):
        return {
            key: f"Reviewed {key} against the durable local research evidence."
            for key in self.research_rubric
        }

    def machine_markdown(self):
        machine = {
            "kind": "greenfield",
            "augment": False,
            "references": [],
            "tools": [],
            "mcp": [],
            "mcp_considered": "none(no external reader matched this increment)",
            "handles": [],
            "initiation": "none",
            "ui": False,
            "ui_craft": "none(no UI in scope)",
            "exclusive": [],
            "platform_discovery": {
                "version": 1,
                "applicable": False,
                "rationale": "This deterministic fixture has no external platform route.",
                "platforms": [],
            },
        }
        return (
            "Fixture survey.\n\n## machine\n```json\n"
            + json.dumps(machine, indent=2)
            + "\n```\n"
        )

    def step(self, sid, product, inputs, statement, *, activity=None):
        step = {
            "id": sid,
            "statement": statement,
            "prompt": "\n".join(
                [
                    "/goal",
                    "Do this activity until these conditions are met:",
                    f"- {product}",
                    "Keep the change scoped to this repository.",
                ]
            ),
            "produces": [product],
            "origin": "discovered",
            "inputs": inputs,
            "contract": self.step_contract(sid, product, statement),
        }
        if activity is not None:
            step["activity"] = activity
        return step

    def step_contract(self, sid, product, statement):
        """Return the explicit Ready/Done contract used by the real fixture DAG."""
        return {
            "objective": statement,
            "ready": [
                {
                    "id": f"R-{sid}",
                    "condition": f"{sid} has a current scoped step plan before edits.",
                    "evidence_method": "planning verify candidate check",
                }
            ],
            "done": [
                {
                    "id": f"D-{sid}",
                    "condition": f"{sid} exact-output artifact is integrated.",
                    "produces": [product],
                    "evidence_method": "exact-output verification",
                    "completion": "integrated",
                }
            ],
            "tests": [
                {
                    "id": f"T-{sid}",
                    "produces": [product],
                    "expected_outcome": product,
                    "surface": "local Python exact-output check",
                    "evidence_method": "exact-output verification",
                }
            ],
            "documentation": [
                {
                    "id": f"DOC-{sid}",
                    "condition": "Fixture README is unchanged because this local test artifact has no product README.",
                    "evidence_method": "manual fixture documentation review",
                }
            ],
        }

    def bound_step_contract(self, sid):
        """Read the current durable DAG so corrective steps retain their own contract."""
        plan = self.run_dir / "backchain" / "plan.md"
        dag = store.read_record(plan) if plan.is_file() else self.initial_dag()
        step = next((row for row in dag["steps"] if row["id"] == sid), None)
        self.assertIsNotNone(step, f"missing current DAG step {sid}")
        self.assertIsInstance(step.get("contract"), dict)
        return copy.deepcopy(step["contract"])

    def ready_evidence(self, sid):
        contract = self.bound_step_contract(sid)
        ready = contract["ready"][0]
        return {
            "ready": [
                {
                    "id": ready["id"],
                    "condition": ready["condition"],
                    "method": ready["evidence_method"],
                    "source": "verify-record",
                    "reference": f"check:{ready['id']}",
                    "observed": "The fresh step-plan candidate and dedicated readiness check passed before implementation.",
                }
            ]
        }

    def done_evidence(self, sid):
        contract = self.bound_step_contract(sid)
        done = contract["done"][0]
        test = contract["tests"][0]
        documentation = contract["documentation"][0]
        return {
            "done": [
                {
                    "id": done["id"],
                    "method": done["evidence_method"],
                    "source": "verify-record",
                    "reference": f"check:{test['id']}",
                    "observed": "The exact declared artifact passed the final verification check.",
                }
            ],
            "tests": [
                {
                    "id": test["id"],
                    "check_id": test["id"],
                    "expected_outcome": test["expected_outcome"],
                    "observed_outcome": "The local exact-output check passed with the declared artifact content.",
                    "source": "verify-record",
                }
            ],
            "documentation": [
                {
                    "id": documentation["id"],
                    "method": documentation["evidence_method"],
                    "source": "manual-observation",
                    "reference": "fixture documentation review",
                    "observed": "No product README exists for this local fixture, so the documented no-change rationale remains accurate.",
                }
            ],
        }

    def output_for(self, sid):
        outputs = {"S1": "first", "S2": "second", "S3": "research"}
        self.assertIn(sid, outputs)
        return outputs[sid]

    def product_for(self, sid):
        products = {
            "S1": self.product_one,
            "S2": self.product_two,
            "S3": self.product_research,
        }
        self.assertIn(sid, products)
        return products[sid]

    def markdown_lint_argv(self, candidate, *, state_record=False):
        """Lint one immutable Markdown candidate without re-entering ShipLoop."""
        lint = (
            "from pathlib import Path; "
            f"path = Path({str(candidate)!r}); "
            "text = path.read_text(encoding='utf-8'); lines = text.splitlines(); "
            "assert path.is_file() and not path.is_symlink(); "
            "assert text.strip(); "
            "assert all(line == line.rstrip(' \\t') for line in lines)"
        )
        if state_record:
            lint = (
                "import json; "
                + lint
                + "; assert lines.count('```shiploop-state') == 1 and lines[-1] == '```'; "
                "start = lines.index('```shiploop-state'); assert start > 0; "
                "json.loads('\\n'.join(lines[start + 1:-1]))"
            )
        return [sys.executable, "-B", "-c", lint]

    def activity_for(self, sid):
        dag = store.read_record(self.run_dir / "backchain" / "plan.md")
        return next(step.get("activity") for step in dag["steps"] if step["id"] == sid)

    def initial_dag(self):
        return {
            "contract_version": 1,
            "system_tests": {
                "version": 1,
                "phases": {
                    "pre_deployment": {"status": "required", "reason": "The dependent output must be verified after the first artifact is integrated."},
                    "post_deployment": {"status": "not-applicable", "reason": "This local protocol fixture has no deployment boundary."},
                },
                "cases": [{
                    "id": "SYS-INTEGRATED-001", "phase": "pre_deployment",
                    "requirement": "The dependent artifact passes after the first artifact is integrated.",
                    "expected_outcome": self.product_two, "environment": "isolated local worktree",
                    "prerequisites": ["S1"], "test_step": "S2", "test_id": "T-S2",
                    "deployment_step": None,
                }],
            },
            "goal": self.done_sentence,
            "initial_state": ["repository exists"],
            "steps": [
                self.step(
                    "S1",
                    self.product_one,
                    [{"need": "repository exists", "from": None}],
                    "Create the first verified artifact",
                ),
                self.step(
                    "S2",
                    self.product_two,
                    [{"need": self.product_one, "from": "S1"}],
                    "Create the dependent verified artifact",
                    activity="system-test-pre",
                ),
            ],
            "unresolved": [],
        }

    def plan_markdown(self, suffix=""):
        return (
            "# Fixture sequence\n\n"
            f"done_sentence: {self.done_sentence}\n\n"
            "## Review Coverage\n\n"
            "None — residual loop waived: fixture-bound coverage policy.\n" + suffix
        )

    def planning_body(self, kind, revision="initial"):
        if kind == "research":
            return f"""# Fixture research ({revision})

## Question RQ-001

Can the local fixture use deterministic exact-output checks without a network dependency?

## Conclusion

The committed local repository and Python standard library provide the required
test surface. Revalidate the local runtime before implementation.
"""
        if kind == "behavior":
            return f"""# Fixture behavior model ({revision})

## Requirements

R-01: The fixture has two dependent exact-output artifacts.

## States and transitions

S-01 baseline; S-02 S1 complete; S-03 S2 complete.
T-01: baseline --S1 verified--> S1 complete; S1 complete --S2 verified--> S2 complete.

## Edge conditions and sequences

A dependent artifact cannot begin before its producer is merged.

## Test mapping

TC-01 maps S1 to its exact-output check; TC-02 maps S2 to its exact-output check.

## Ambiguities

None for this local fixture.
"""
        return f"""# Fixture specification ({revision})

done_sentence: {self.done_sentence}
checkable: true

## Requirements, states, transitions, and edge conditions

R-01 requires both exact-output artifacts. T-01 requires S1 verification before S2.

## Test mapping

TC-01 and TC-02 map the two exact-output acceptance criteria to durable checks.
"""

    def planning_research_state(self, revision="initial"):
        return {
            "questions": [
                {
                    "id": "RQ-001",
                    "question": "Can the local fixture use deterministic exact-output checks without a network dependency?",
                    "origin": "prompt discovery: local fixture test surface",
                    "status": "resolved",
                    "answer": "The local Python runtime can execute the fixture's deterministic checks.",
                    "sources": ["SRC-LOCAL-001"],
                    "revalidate": "Run the local lint and exact-output checks before implementation.",
                    "rationale": "The fixture intentionally has no external service dependency.",
                    "parents": [],
                    "contract_refs": [],
                    "role_refs": ["ROLE-local"],
                    "interface_refs": [],
                }
            ],
            "sources": [
                {
                    "id": "SRC-LOCAL-001",
                    "reference": "action-walk local runtime fixture",
                    "authority": "local",
                    "version_or_observed_at": f"fixture-{revision}",
                    "supports": "The local deterministic exact-output conclusion.",
                    "limitations": "This source says nothing about external services.",
                }
            ],
            "system_context": {
                "version": 1,
                "scope": "local-only",
                "rationale": "Only local fixture code is in scope.",
                "roles": [
                    {
                        "id": "ROLE-local",
                        "label": "local fixture role",
                        "status": "observed",
                        "permitted_actions": "Run deterministic local checks.",
                        "isolation": "No remote data or mutation.",
                        "platform_refs": [],
                        "source_refs": ["SRC-LOCAL-001"],
                        "revalidate": "Recheck the local runtime before implementation.",
                    }
                ],
                "interfaces": [],
                "interactions": [],
                "observations": [
                    {
                        "id": "OBS-code",
                        "kind": "code",
                        "status": "observed",
                        "summary": "The fixture uses committed local code.",
                        "source_refs": ["SRC-LOCAL-001"],
                        "role_refs": [],
                        "interface_refs": [],
                    },
                    {
                        "id": "OBS-state",
                        "kind": "state",
                        "status": "not-applicable",
                        "summary": "No persisted business state exists.",
                        "source_refs": [],
                        "role_refs": [],
                        "interface_refs": [],
                    },
                    {
                        "id": "OBS-system",
                        "kind": "system",
                        "status": "not-applicable",
                        "summary": "No separate system boundary exists.",
                        "source_refs": [],
                        "role_refs": [],
                        "interface_refs": [],
                    },
                    {
                        "id": "OBS-role",
                        "kind": "environment-role",
                        "status": "observed",
                        "summary": "The local fixture role is available.",
                        "source_refs": ["SRC-LOCAL-001"],
                        "role_refs": ["ROLE-local"],
                        "interface_refs": [],
                    },
                ],
            },
        }

    def planning_lifecycle(self):
        preparation = getattr(self, "fixture_preparation", "none")
        return {
            "acceptance": [self.product_one, self.product_two],
            "preparation": preparation,
            "publish": "none",
            "quality": True,
            "reason": (
                "The fixture requires a bounded outer readiness observation before allocation."
                if preparation == "outer-before"
                else "Local files require no outer preparation or publication."
            ),
            "risk_policy": {
                "risk_policy_version": 1,
                "security": {
                    "decision": "not-applicable",
                    "rationale": "The isolated local fixture exposes no security boundary.",
                },
                "fuzz": {
                    "decision": "not-applicable",
                    "rationale": "The deterministic fixture has no parser or external input surface.",
                },
                "maintenance": {
                    "decision": "not-applicable",
                    "rationale": "The fixture declares no deployable dependency maintenance path.",
                },
            },
        }

    def planning_rubric(self, kind):
        dimensions = list(self.research_rubric) if kind == "research" else [
            "requirements",
            "states",
            "transitions",
            "edge_conditions",
            "sequences",
            "test_mapping",
            "ambiguities",
        ]
        if kind == "spec":
            dimensions += ["clarity", "consistency", "feasibility"]
        return {
            dimension: f"Reviewed {dimension} against the durable {kind} candidate."
            for dimension in dimensions
        }

    def planning_manifest(self, kind):
        candidate = (
            "research.md"
            if kind == "research"
            else "behavior.md"
            if kind == "behavior"
            else "spec-draft.md"
        )
        acceptance = (
            "research evidence"
            if kind == "research"
            else "behavior model"
            if kind == "behavior"
            else "specification"
        )
        if kind == "research":
            check = (
                "from pathlib import Path; "
                "research = Path('.shiploop/research.md').read_text(); "
                "evidence = Path('.shiploop/research-evidence.md').read_text(); "
                "assert 'RQ-001' in research; assert 'SRC-LOCAL-001' in evidence"
            )
        else:
            check = (
                "from pathlib import Path; "
                f"text = Path('.shiploop/{candidate}').read_text(); "
                "assert 'Test mapping' in text; assert 'T-01' in text"
            )
        return {
            "checks": [
                {
                    "id": "planning-lint",
                    "kind": "lint",
                    "argv": self.markdown_lint_argv(self.run_dir / candidate),
                    "acceptance": [],
                },
                {
                    "id": f"{kind}-candidate",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", check],
                    "acceptance": [acceptance],
                },
            ]
        }

    def planning_receipt(self, kind):
        return store.read_record(self.run_dir / "planning" / f"{kind}.md")

    def planning_audit_commit(self, kind, review_learning, apply_learning):
        iteration = self.planning_receipt(kind)["current_iteration"]["id"]
        message = "\n".join(
            [
                f"Planning {kind} {iteration}",
                "",
                "Review:",
                "Read current Git history and the durable planning finding ledger.",
                "",
                "Changes:",
                "Recorded an audit-only planning pass without product-tree changes.",
                "",
                "Validation:",
                "Fresh candidate-bound lint and planning tests passed.",
                "",
                "Key learnings:",
                review_learning,
                apply_learning,
                "",
                f"ShipLoop-Iteration: {iteration}",
            ]
        )
        self.git("commit", "--allow-empty", "--only", "-m", message)
        return self.git("rev-parse", "HEAD")

    def run_planning_iteration(self, kind, number):
        self.assertEqual(self.state()["stage"], f"{kind}-review")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        finding = f"{kind[:1].upper()}-T-{number}"
        review_learning = f"Review {finding} before changing the planning candidate."
        review = {
            "summary": f"Review records and resolves trivial planning finding {finding}.",
            "findings": [
                {
                    "id": finding,
                    "severity": "trivial",
                    "summary": f"Trivial {kind} fixture wording improvement",
                }
            ],
            "test_review": "A candidate-bound planning manifest will assert the current Markdown artifact.",
            "learnings": review_learning,
        }
        review["coverage_review"] = self.planning_rubric(kind)
        self.complete(review, action_id=review_action, label=f"{kind}-{number}-review")
        self.assertEqual(self.state()["stage"], f"{kind}-plan")
        self.complete(
            {
                "summary": f"The plan addresses {finding} without weakening the candidate check.",
                "body": f"# {kind} plan\n\nAddress {finding} and retain its explicit test mapping.\n",
                "addresses": [finding],
            },
            label=f"{kind}-{number}-plan",
        )
        self.assertEqual(self.state()["stage"], f"{kind}-apply")
        apply_learning = f"Apply {finding} as a complete {kind} candidate replacement."
        applied = {
            "summary": f"The full replacement candidate resolves {finding}.",
            "body": self.planning_body(kind, finding),
            "material": False,
            "resolutions": [{"id": finding, "evidence": f"Candidate revision names {finding}."}],
            "test_changes": "The candidate-bound lint and test checks remain active.",
            "learnings": apply_learning,
        }
        if kind == "research":
            applied["research_state"] = self.planning_research_state(finding)
        elif kind == "spec":
            applied["lifecycle"] = self.planning_lifecycle()
        self.complete(applied, label=f"{kind}-{number}-apply")
        self.assertEqual(self.state()["stage"], f"{kind}-verify")
        verify_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            verify_action,
            "--manifest",
            self.record(f"{kind}-{number}-checks", self.planning_manifest(kind)),
        )
        self.complete(
            {"summary": "Fresh planning lint and candidate assertion evidence passed."},
            action_id=verify_action,
            label=f"{kind}-{number}-verify",
        )
        self.assertEqual(self.state()["stage"], f"{kind}-commit")
        commit = self.planning_audit_commit(kind, review_learning, apply_learning)
        self.complete(
            {"summary": "A verbose audit-only commit records this planning pass.", "commit": commit},
            label=f"{kind}-{number}-commit",
        )

    def converge_planning(self, kind):
        self.assertEqual(self.state()["stage"], kind)
        initial = {
            "summary": f"The initial {kind} candidate maps states, transitions, and exact tests.",
            "body": self.planning_body(kind),
        }
        if kind == "research":
            initial["research_state"] = self.planning_research_state()
        elif kind == "spec":
            initial["lifecycle"] = self.planning_lifecycle()
        self.complete(initial, label=f"{kind}-initial")
        self.assertEqual(self.state()["stage"], f"{kind}-review")
        self.run_planning_iteration(kind, 1)
        self.assertEqual(self.planning_receipt(kind)["streak"], 1)
        self.assertEqual(self.state()["stage"], f"{kind}-review")
        self.run_planning_iteration(kind, 2)
        self.assertEqual(self.planning_receipt(kind)["streak"], 2)
        self.assertEqual(self.state()["stage"], f"{kind}-finalize")
        final_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            final_action,
            "--manifest",
            self.record(f"{kind}-final-checks", self.planning_manifest(kind)),
        )
        self.complete(
            {"summary": "Fresh checks passed for the unchanged final planning candidate."},
            action_id=final_action,
            label=f"{kind}-finalize",
        )

    def objective_binding(self):
        binding = self.state().get("objective")
        self.assertIsInstance(binding, dict)
        self.assertEqual(binding.get("status"), "active")
        self.assertIn(binding.get("kind"), objectives.KINDS)
        return binding

    def objective_receipt(self):
        binding = self.objective_binding()
        return store.read_record(self.run_dir / binding["receipt"])

    def objective_assessment(self, kind):
        return {
            key: f"Reviewed {key} against the bounded {kind} objective candidate."
            for key in objectives.ASSESSMENT_KEYS
        }

    def objective_history(self):
        """Durably read the current policy-owned page before objective review."""
        action = self.action_id()
        history_limit = history_policy.required_limit(self.state())
        output = self.cli(
            "history", "--action", action, "--limit", str(history_limit), "--skip", "0", "--full"
        ).stdout
        self.assertIn("Git history", output)
        receipt = self.objective_receipt()
        current = receipt["current_pass"]
        self.assertEqual(current["history"]["required_limit"], history_limit)
        archive = self.run_dir / objectives.history_page_name(
            receipt["loop_id"], current["id"], 0
        )
        self.assertTrue(archive.is_file())

    def read_context_record(self, section):
        """Read every current context page through the public bounded CLI."""
        offset = 0
        digest = None
        pages = []
        total = None
        while True:
            args = [
                "context",
                "--section",
                section,
                "--offset",
                str(offset),
                "--limit",
                "8000",
            ]
            if digest is not None:
                args.extend(["--digest", digest])
            output = self.cli(*args).stdout
            header, body = output.split("\n", 1)
            match = re.fullmatch(
                rf"Context {re.escape(section)}; digest ([0-9a-f]{{64}}); characters (\d+):(\d+)/(\d+)",
                header,
            )
            self.assertIsNotNone(match, output)
            page_digest, start, end, page_total = match.groups()
            start, end, page_total = int(start), int(end), int(page_total)
            self.assertEqual(start, offset)
            self.assertEqual(digest or page_digest, page_digest)
            self.assertLessEqual(end, page_total)
            if total is None:
                total = page_total
                digest = page_digest
            else:
                self.assertEqual(total, page_total)
            pages.append(body[: end - start])
            if end == page_total:
                self.assertNotIn("Continue: --offset", body[end - start :])
                break
            continuation = re.search(
                r"Continue: --offset (\d+) --limit 8000 --digest ([0-9a-f]{64})",
                body[end - start :],
            )
            self.assertIsNotNone(continuation, output)
            self.assertEqual(continuation.group(2), digest)
            offset = int(continuation.group(1))
        text = "".join(pages)
        self.assertEqual(len(text), total)
        return store.loads(text)

    def read_outer_work_context(self):
        """Read every current outer-work page through the public bounded CLI."""
        return self.read_context_record("outer-work")

    def read_outer_work_if_required(self):
        """Satisfy an outer-stage read gate only when this run has a journal."""
        state = self.state()
        stage = state["stage"]
        if objectives.is_objective_stage(stage):
            stage = state.get("objective", {}).get("kind")
        if state.get("outer_work_sha256") and stage in ("quality", "publish", "handoff"):
            return self.read_outer_work_context()
        return None

    def local_quality_outer_request(self, context):
        """Populate the printed append template with one local quality obligation."""
        request = copy.deepcopy(context["append_template"])
        request.update(
            entry_id="OW-QUALITY-LOCAL-001",
            dedupe_key="fixture-local-whole-product-check",
            required_action="Review the local whole-product check and final verification observation.",
            target_stage="quality",
            target_alias="local-fixture-quality",
            prerequisites=[
                "Both fixture artifacts are merged into the local repository.",
                "The final local whole-product exact-output check is available.",
            ],
            expected_outcome="The quality review records whether the local whole-product checks and final verification evidence are complete.",
            evidence="The local whole-product exact-output check and final verification record are available at quality.",
            authority_limitations="This journal records a local quality observation and does not authorize an external effect.",
            rationale="The final whole-product check is observable only after both local implementation steps are merged.",
        )
        return request

    def objective_manifest(self, kind, *, fail=False):
        receipt = self.objective_receipt()
        candidate = self.run_dir / receipt["candidate_path"]
        state = self.state()
        if kind == "post-inner":
            acceptance = [self.product_for(state["active_step"])]
        elif kind == "quality":
            acceptance = [self.product_one, self.product_two]
        else:
            acceptance = [f"objective {kind}"]
        candidate_check = (
            "from pathlib import Path; "
            f"text = Path({str(candidate)!r}).read_text(encoding='utf-8'); "
            "assert text.strip()"
        )
        if fail:
            candidate_check += "; raise SystemExit(1)"
        return {
            "checks": [
                {
                    "id": "objective-lint",
                    "kind": "lint",
                    "argv": self.markdown_lint_argv(candidate, state_record=True),
                    "acceptance": [],
                },
                {
                    "id": "objective-candidate",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", candidate_check],
                    "acceptance": acceptance,
                },
            ]
        }

    def objective_repo(self):
        state = self.state()
        return self.worktree(state["active_step"]) if state.get("active_step") else self.repo

    def objective_audit_commit(self, kind):
        receipt = self.objective_receipt()
        current = receipt["current_pass"]
        review = current["review"]["learnings"]
        plan = current["plan"]["learnings"]
        applied = current["apply"]["learnings"]
        message = "\n".join(
            [
                f"Objective {kind} {current['id']}",
                "",
                "Review:",
                review,
                "",
                "Changes:",
                "Recorded the candidate plan and its scoped resolution without product-tree changes.",
                "",
                "Validation:",
                "Fresh objective lint and candidate-bound checks passed.",
                "",
                "Key learnings:",
                review,
                plan,
                applied,
                "",
                f"ShipLoop-Iteration: {current['id']}",
            ]
        )
        repo = self.objective_repo()
        self.git("commit", "--allow-empty", "--only", "-m", message, cwd=repo)
        return self.git("rev-parse", "HEAD", cwd=repo)

    def start_objective(self, candidate, *, label):
        base_stage = self.state()["stage"]
        kind = objectives.kind_for_base_stage(base_stage)
        self.assertIsNotNone(kind)
        self.read_outer_work_if_required()
        self.complete(candidate, label=label)
        self.assertEqual(self.state()["stage"], "objective-review")
        binding = self.objective_binding()
        self.assertEqual(binding["kind"], kind)
        self.assertEqual(binding["base_stage"], base_stage)
        return kind

    def run_objective_pass(self, kind, number, candidate, *, material=False, fail_verify=False):
        self.assertEqual(self.state()["stage"], "objective-review")
        self.objective_history()
        finding_id = f"OBJ-{kind}-{number}"
        review_learning = (
            f"The {kind} objective review read the complete current Git history and durable context."
        )
        self.read_outer_work_if_required()
        self.complete(
            {
                "summary": "The objective review records an explicit finding against every required dimension.",
                "findings": [
                    {
                        "id": finding_id,
                        "severity": "material" if material else "trivial",
                        "category": "other",
                        "summary": "The fixture objective keeps its candidate, checks, and completion evidence explicit.",
                    }
                ],
                "assessment": self.objective_assessment(kind),
                "history_assessment": "All currently available full commit bodies were read before this objective decision.",
                "test_review": "The objective candidate check keeps the expected acceptance visible without changing product files.",
                "learnings": review_learning,
            },
            label=f"{kind}-objective-{number}-review",
        )
        self.assertEqual(self.state()["stage"], "objective-plan")
        plan_learning = (
            f"The {kind} objective plan resolves its stable finding without broadening the original candidate."
        )
        self.read_outer_work_if_required()
        self.complete(
            {
                "summary": "The objective plan addresses every open finding with a bounded durable change.",
                "addresses": [finding_id],
                "body": f"# {kind} objective plan\n\nAddress {finding_id} without changing product files.\n",
                "learnings": plan_learning,
            },
            label=f"{kind}-objective-{number}-plan",
        )
        self.assertEqual(self.state()["stage"], "objective-apply")
        applied_candidate = copy.deepcopy(candidate)
        if material:
            applied_candidate["summary"] += " The material fixture correction is now explicit."
        apply_learning = (
            f"The {kind} objective apply result retains the complete original-stage candidate and its explicit check."
        )
        self.read_outer_work_if_required()
        self.complete(
            {
                "summary": "The objective apply result resolves the finding without an external effect.",
                "candidate": applied_candidate,
                "material": material,
                "addresses": [finding_id],
                "resolutions": [
                    {
                        "id": finding_id,
                        "evidence": "The complete candidate preserves its declared outcome, test, and documentation decision.",
                    }
                ],
                "test_changes": "The candidate-bound objective test remains active; no expected outcome was removed.",
                "learnings": apply_learning,
            },
            label=f"{kind}-objective-{number}-apply",
        )
        self.assertEqual(self.state()["stage"], "objective-verify")
        verify_action = self.action_id()
        if fail_verify:
            self.cli(
                "planning-verify",
                "--action",
                verify_action,
                "--manifest",
                self.record(
                    f"{kind}-objective-{number}-failed-checks",
                    self.objective_manifest(kind, fail=True),
                ),
                code=2,
            )
            self.assertEqual(self.state()["stage"], "objective-verify")
            self.assertEqual(self.action_id(), verify_action)
        verify_args = [
            "planning-verify",
            "--action",
            verify_action,
            "--manifest",
            self.record(
                f"{kind}-objective-{number}-checks", self.objective_manifest(kind)
            ),
        ]
        if fail_verify or kind == "post-inner":
            verify_args.extend(
                [
                    "--reason",
                    (
                        "Restore the candidate acceptance command after the failed objective check; no acceptance was weakened."
                        if fail_verify
                        else "The per-step post-inner acceptance target changed from the prior completed step; retain the exact declared product check."
                    ),
                ]
            )
        self.cli(*verify_args)
        self.read_outer_work_if_required()
        self.complete(
            {"summary": "Fresh objective lint and candidate acceptance checks passed."},
            action_id=verify_action,
            label=f"{kind}-objective-{number}-verify",
        )
        self.assertEqual(self.state()["stage"], "objective-commit")
        commit_action = self.action_id()
        commit = self.objective_audit_commit(kind)
        self.read_outer_work_if_required()
        self.complete(
            {
                "summary": "An audit-only direct-child commit records the objective review, plan, apply, and validation learnings.",
                "commit": commit,
            },
            action_id=commit_action,
            label=f"{kind}-objective-{number}-commit",
        )
        return applied_candidate

    def converge_objective(
        self,
        candidate,
        *,
        label,
        material_first=False,
        started=False,
        fail_first_verify=False,
        final_code=0,
    ):
        """Converge one universal outer objective through real CLI actions."""
        if started:
            binding = self.objective_binding()
            kind = binding["kind"]
            self.assertEqual(kind, label)
            self.assertEqual(self.state()["stage"], "objective-review")
        else:
            kind = self.start_objective(candidate, label=label)
        # Continue from the accepted candidate, including versioned fixture
        # acknowledgements, not the caller's pre-submission object.
        candidate = store.read_record(self.run_dir / self.objective_receipt()["candidate_path"])
        current = self.run_objective_pass(
            kind,
            1,
            candidate,
            material=material_first,
            fail_verify=fail_first_verify,
        )
        self.assertEqual(self.state()["stage"], "objective-review")
        current = self.run_objective_pass(kind, 2, current)
        if material_first:
            self.assertEqual(self.state()["stage"], "objective-review")
            current = self.run_objective_pass(kind, 3, current)
        self.assertEqual(self.state()["stage"], "objective-finalize")
        finalize_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            finalize_action,
            "--manifest",
            self.record(f"{kind}-objective-final-checks", self.objective_manifest(kind)),
        )
        self.read_outer_work_if_required()
        final_process, _ = self.complete(
            {"summary": "Fresh final objective lint and candidate acceptance checks passed."},
            action_id=finalize_action,
            code=final_code,
            label=f"{kind}-objective-finalize",
        )
        self.last_objective_final = final_process
        if final_code:
            self.assertEqual(self.state()["stage"], "objective-finalize")
            return current
        binding = self.state()["objective"]
        self.assertEqual(binding["status"], "finalized")
        self.assertTrue((self.run_dir / binding["certificate"]).is_file())
        return current

    def step_plan_loop(self, sid):
        binding = self.receipt(sid).get("step_plan")
        self.assertIsInstance(binding, dict)
        self.assertIsInstance(binding.get("loop_id"), str)
        return binding["loop_id"]

    def step_plan_receipt(self, sid):
        loop = self.step_plan_loop(sid)
        return store.read_record(self.run_dir / step_planning.receipt_name(loop))

    def step_plan_parent_ids(self, sid):
        if (
            self.state()["stage"] != "improve-plan"
            and self.receipt(sid).get("step_plan", {}).get("route") != "improve"
        ):
            return []
        context = self.cli(
            "context", "--section", "step-context", "--offset", "0", "--limit", "8000"
        ).stdout
        return sorted(set(re.findall(r"PARENT-[0-9a-f]{16}", context)))

    def step_plan_candidate(self, sid, revision, *, parent_ids=()):
        product = self.product_for(sid)
        parent_section = (
            "## Enclosing review findings\n\n"
            + "\n".join(
                f"- {finding_id}: Address this enclosing review finding in the scoped plan."
                for finding_id in parent_ids
            )
            + "\n\n"
            if parent_ids
            else ""
        )
        return f"""# Step plan {sid} ({revision})

## Scope

Implement only {sid}; preserve its declared output and dependency boundary.

## Current implementation and environment

Inspect the active worktree, current Git head, local Python runtime, and the
frozen behavior, specification, environment, plan, and knowledge records.

## Dependencies and flows

{sid} consumes only its declared prerequisites and must preserve the observable
producer-to-consumer sequence without adding an implicit side effect.

## Edge conditions and second-order effects

An exact-output failure must not be hidden by a weaker assertion or a changed
expected outcome. Repeated execution must not alter an already valid artifact.

## Implicit requirements

Keep the implementation scoped to the active step; do not change frozen
contracts, pending steps, credentials, or deployment state.

## Test cases

TC-{sid}-exact: Given the active fixture, run the local exact-output check.
Expected outcome: {product}.

## Documentation

The fixture has no product README; retain this explicit no-change decision and
document any future function-contract or README impact before implementation.

{parent_section}"""

    def step_plan_coverage(self):
        return {
            key: f"Reviewed {key} against the active step, durable inputs, and current worktree."
            for key in self.step_plan_rubric
        }

    def step_plan_context_evidence(self, sid):
        evidence = {
            "step": f"context --section step identified {sid} and its declared produces.",
            "implementation": "context --section step-context bound the current worktree and Git head.",
            "environment": "The frozen environment and local Python runtime remain the selected test environment.",
            "dependencies": "The direct supplier and consumer records were inspected from the bounded step context.",
        }
        selected = self.read_context_record("step-context")["step"]["system_context"]["projection"]
        self.assertIsInstance(selected, dict)
        evidence["system_context"] = {
            "context_sha256": selected["context_sha256"],
            "role_ids": [row["id"] for row in selected["roles"]],
            "interface_ids": [row["id"] for row in selected["interfaces"]],
            "interaction_ids": [row["id"] for row in selected["interactions"]],
            "question_ids": [row["id"] for row in selected["questions"]],
            "observation_ids": [row["id"] for row in selected["observations"]],
            "source_ids": [row["id"] for row in selected["sources"]],
        }
        return evidence

    def step_plan_manifest(self, sid):
        receipt = self.step_plan_receipt(sid)
        candidate = self.run_dir / receipt["candidate_path"]
        expected = self.product_for(sid)
        test = (
            "from pathlib import Path; "
            f"text = Path({str(candidate)!r}).read_text(encoding='utf-8'); "
            f"assert 'TC-{sid}-exact' in text; "
            f"assert {expected!r} in text; "
            "assert 'Expected outcome:' in text"
        )
        return {
            "checks": [
                {
                    "id": "step-plan-lint",
                    "kind": "lint",
                    "argv": self.markdown_lint_argv(candidate),
                    "acceptance": [],
                },
                {
                    "id": "step-plan-candidate",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", test],
                    "acceptance": ["step plan"],
                },
                {
                    "id": f"R-{sid}",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", test],
                    "acceptance": ["step plan"],
                },
            ]
        }

    def step_plan_commit(self, sid, *, staged_product_path=None):
        receipt = self.step_plan_receipt(sid)
        current = receipt["current_pass"]
        review = current["review"]["learnings"]
        revise = current["revise"]["learnings"]
        message = "\n".join(
            [
                f"Step-plan {sid} {current['id']}",
                "",
                "Review:",
                "Read current Git history, bounded step context, and the durable risk ledger.",
                "",
                "Changes:",
                "Recorded the bounded plan candidate and findings without changing product content.",
                "",
                "Validation:",
                "Fresh lint and candidate-bound expected-outcome checks passed.",
                "",
                "Key learnings:",
                review,
                revise,
                "",
                f"ShipLoop-Iteration: {current['id']}",
            ]
        )
        worktree = self.worktree(sid)
        if staged_product_path is not None:
            self.git("add", staged_product_path, cwd=worktree)
        self.git("commit", "--allow-empty", "--only", "-m", message, cwd=worktree)
        return self.git("rev-parse", "HEAD", cwd=worktree)

    def run_step_plan_pass(
        self,
        sid,
        number,
        *,
        material=False,
        finding_id=None,
        staged_product_path=None,
    ):
        self.assertEqual(self.state()["stage"], "step-plan-review")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        knowledge_read = self.read_knowledge(sid)
        finding_id = finding_id or f"SP-{sid}-{number}"
        review_learning = (
            "The plan review used current Git history, active implementation, environment, direct dependencies, and durable knowledge."
        )
        review = {
            "summary": "The bounded step-plan review records an explicit risk and every required dimension.",
            "findings": [
                {
                    "id": finding_id,
                    "severity": "material" if material else "trivial",
                    "category": "implementation",
                    "summary": "The exact-output boundary requires a documented, checked plan adjustment.",
                }
            ],
            "coverage_review": self.step_plan_coverage(),
            "context_evidence": self.step_plan_context_evidence(sid),
            "test_review": "TC exact-output asserts the declared result; the plan check asserts its expected outcome remains explicit.",
            "learnings": review_learning,
            "knowledge_read": knowledge_read,
        }
        self.complete(review, action_id=review_action, label=f"{sid}-step-plan-{number}-review")
        self.assertEqual(self.state()["stage"], "step-plan-revise")
        revise_learning = (
            "Every open plan finding is resolved with a concrete candidate, test, and documentation decision."
        )
        self.complete(
            {
                "summary": "The revised candidate resolves every open step-plan finding without weakening expected outcomes.",
                "body": self.step_plan_candidate(
                    sid,
                    f"pass {number}",
                    parent_ids=self.step_plan_parent_ids(sid),
                ),
                "material": material,
                "addresses": [finding_id],
                "resolutions": [
                    {
                        "id": finding_id,
                        "evidence": "The candidate names the exact-output case, boundary, and documentation decision.",
                    }
                ],
                "test_changes": "The candidate-bound test asserts the explicit expected output; no acceptance condition was removed.",
                "learnings": revise_learning,
            },
            label=f"{sid}-step-plan-{number}-revise",
        )
        self.assertEqual(self.state()["stage"], "step-plan-verify")
        check_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            check_action,
            "--manifest",
            self.record(f"{sid}-step-plan-{number}-checks", self.step_plan_manifest(sid)),
        )
        self.complete(
            {"summary": "Fresh lint and exact candidate expected-outcome checks passed without changing the plan context."},
            action_id=check_action,
            label=f"{sid}-step-plan-{number}-verify",
        )
        self.assertEqual(self.state()["stage"], "step-plan-commit")
        commit_action = self.action_id()
        commit = self.step_plan_commit(sid, staged_product_path=staged_product_path)
        _, result = self.complete(
            {
                "summary": "A distinct audit-only commit records the current review, revision, validation, and key learnings.",
                "commit": commit,
            },
            action_id=commit_action,
            label=f"{sid}-step-plan-{number}-commit",
        )
        return {
            "review_action": review_action,
            "check_action": check_action,
            "commit_action": commit_action,
            "commit": commit,
            "result": result,
            "finding_id": finding_id,
        }

    def start_step_plan(self, sid):
        self.assertIn(self.state()["stage"], ("step-plan", "improve-plan"))
        route = "initial" if self.state()["stage"] == "step-plan" else "improve"
        self.complete(
            {
                "summary": "The plan candidate explicitly covers current code, environment, dependencies, flows, risks, tests, and documentation.",
                "body": self.step_plan_candidate(
                    sid,
                    "draft",
                    parent_ids=(
                        self.step_plan_parent_ids(sid)
                        if route == "improve"
                        else []
                    ),
                ),
            },
            label=f"{sid}-{route}-step-plan-draft",
        )
        self.assertEqual(self.state()["stage"], "step-plan-review")
        return route

    def converge_step_plan(self, sid, *, material_first=False, staged_product_path=None):
        """Converge an initial or Improve plan through fresh, replay-safe CLI actions."""
        if self.state()["stage"] in ("step-plan", "improve-plan"):
            route = self.start_step_plan(sid)
        else:
            self.assertEqual(self.state()["stage"], "step-plan-review")
            route = self.step_plan_receipt(sid)["route"]
        first = self.run_step_plan_pass(
            sid,
            1,
            material=material_first,
            staged_product_path=staged_product_path,
        )
        self.assertEqual(len(self.step_plan_receipt(sid)["completed_passes"]), 1)
        self.assertEqual(
            self.step_plan_receipt(sid)["completed_passes"][0]["outcome"],
            "material" if material_first else "trivial",
        )
        self.assertEqual(self.state()["stage"], "step-plan-review")
        second = self.run_step_plan_pass(sid, 2, material=False)
        if material_first:
            self.assertEqual(self.state()["stage"], "step-plan-review")
            third = self.run_step_plan_pass(sid, 3, material=False)
        else:
            third = None
        self.assertEqual(self.state()["stage"], "step-plan-finalize")
        final_action = self.action_id()
        self.cli(
            "planning-verify",
            "--action",
            final_action,
            "--manifest",
            self.record(f"{sid}-{route}-step-plan-final-checks", self.step_plan_manifest(sid)),
        )
        final_result = {
            "summary": "A fresh final lint and candidate expected-outcome check passed after two trivial passes."
        }
        if route == "initial":
            final_result["ready_evidence"] = self.ready_evidence(sid)
        self.complete(
            final_result,
            action_id=final_action,
            label=f"{sid}-{route}-step-plan-finalize",
        )
        receipt = self.step_plan_receipt(sid)
        self.assertEqual(receipt["route"], route)
        self.assertGreaterEqual(len(receipt["completed_passes"]), 2)
        self.assertEqual(self.state()["stage"], receipt["return_stage"])
        self.cli("plan-status", "--loop", receipt["loop_id"])
        self.assertFalse((self.repo / ".until-loop").exists())
        self.assertFalse((self.run_dir / ".until-loop").exists())
        self.assertFalse((self.run_dir / "state.json").exists())
        self.assertEqual(list((self.run_dir / "step-planning").rglob("*.json")), [])
        return first, second, third, receipt

    def bootstrap_to_first_step_plan(self):
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--prompt",
            "Build two tested fixture artifacts through the durable ShipLoop protocol.",
        )
        self.complete(
            {
                "summary": "Repository has a committed baseline and a local Python runtime.",
                "baseline": "committed-head",
            },
            label="preflight",
        )
        self.converge_objective(
            {
                "summary": "The approach separates initial delivery, per-step verification, and outer checks.",
                "body": "# Approach\n\nCreate two dependent files with exact-output tests and review each increment.\n",
            },
            label="approach",
        )
        self.assertEqual(self.state()["stage"], "survey")
        self.converge_objective(
            {
                "summary": "Survey captured a greenfield fixture and no external routes.",
                "body": self.machine_markdown(),
            },
            label="survey",
        )
        self.assertEqual(self.state()["stage"], "research")
        self.converge_planning("research")
        self.assertEqual(self.state()["stage"], "behavior")
        self.converge_planning("behavior")
        self.assertEqual(self.state()["stage"], "spec")
        self.converge_planning("spec")
        self.assertEqual(self.state()["stage"], "sequence")
        self.converge_objective(
            {
                "summary": "The dependency sequence creates S1 before S2 and maps tests to both outputs.",
                "dependency_review": "Backward prerequisite audit: S2 consumes S1 output; S1 consumes the established repository baseline; no missing producers or cycles.",
                "plan": self.plan_markdown(),
                "dag": self.initial_dag(),
            },
            label="sequence",
        )
        if self.state()["stage"] == "prepare":
            self.converge_objective(
                {
                    "summary": "The local fixture readiness observation is complete before allocation.",
                    "evidence": "The committed baseline and local Python runtime remain available for the declared exact-output checks.",
                },
                label="preparation-readiness",
            )
        state = self.state()
        self.assertEqual(
            (state["phase"], state["stage"], state["active_step"]),
            ("implement", "step-plan", "S1"),
        )
        return state

    def bootstrap_to_first_implementation(self):
        self.bootstrap_to_first_step_plan()
        self.converge_step_plan("S1")
        state = self.state()
        self.assertEqual(
            (state["phase"], state["stage"], state["active_step"]),
            ("implement", "implement", "S1"),
        )
        return state

    def worktree(self, sid):
        receipt = self.receipt(sid)
        path = Path(receipt["worktree"])
        self.assertTrue(path.is_dir(), f"missing allocated worktree for {sid}: {path}")
        return path

    def write_implementation(self, sid, *, wrong_output=False):
        wt = self.worktree(sid)
        word = self.output_for(sid)
        (wt / f"{sid.lower()}.py").write_text(f"VALUE = {word!r}\n", encoding="utf-8")
        output = "not-the-declared-output" if wrong_output else word
        (wt / f"{sid.lower()}.txt").write_text(output + "\n", encoding="utf-8")
        self.git("add", f"{sid.lower()}.py", f"{sid.lower()}.txt", cwd=wt)
        self.git("commit", "-m", f"Implement {sid} fixture artifact", cwd=wt)

    def manifest_for(self, sid, *, quality=False):
        if quality:
            source_names = ["s1.py", "s2.py"]
            command = (
                "from pathlib import Path; "
                "assert Path('s1.txt').read_text() == 'first\\n'; "
                "assert Path('s2.txt').read_text() == 'second\\n'"
            )
            products = [self.product_one, self.product_two]
            lint = "from pathlib import Path; " + "; ".join(
                f"compile(Path({name!r}).read_text(), {name!r}, 'exec')"
                for name in source_names
            )
        else:
            word = self.output_for(sid)
            filename = f"{sid.lower()}.py"
            textfile = f"{sid.lower()}.txt"
            products = [self.product_for(sid)]
            lint = f"from pathlib import Path; compile(Path({filename!r}).read_text(), {filename!r}, 'exec')"
            command = f"from pathlib import Path; assert Path({textfile!r}).read_text() == {word + chr(10)!r}"
        return {
            "checks": [
                {
                    "id": "syntax",
                    "kind": "lint",
                    "argv": [sys.executable, "-B", "-c", lint],
                    "acceptance": [],
                },
                {
                    "id": f"T-{sid}" if not quality else "exact-output",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", command],
                    "acceptance": products,
                },
            ]
        }

    def verify_current(self, manifest, *, code=0, label="checks"):
        path = self.record(label, manifest)
        return self.cli(
            "verify", "--action", self.action_id(), "--manifest", path, code=code
        )

    def read_knowledge(self, sid):
        """Read every bounded knowledge page and return its review acknowledgment."""
        output = self.cli(
            "context", "--section", "knowledge", "--offset", "0", "--limit", "8000"
        ).stdout
        first_page = output
        digest_match = re.search(r"Context knowledge; digest ([0-9a-f]+)", output)
        self.assertIsNotNone(digest_match, output)
        digest = digest_match.group(1)
        while continuation := re.search(r"Continue: --offset (\d+)", output):
            output = self.cli(
                "context",
                "--section",
                "knowledge",
                "--offset",
                continuation.group(1),
                "--limit",
                "8000",
                "--digest",
                digest,
            ).stdout
        if sid == "S2":
            self.assertGreater(self.state()["knowledge_revision"], 0)
            self.assertTrue(list((self.run_dir / "knowledge-history").glob("*.md")))
            self.assertIn("knowledge_revision", first_page)
        return {
            "revision": self.state()["knowledge_revision"],
            "digest": digest,
            "scope": ["all", sid],
        }

    def carry_forward_payload(
        self,
        *,
        learnings="No new non-secret project knowledge was discovered in this iteration.",
        discoveries=None,
        resolutions=None,
    ):
        payload = {
            "summary": "The verified iteration has an explicit carry-forward checkpoint.",
            "knowledge_revision": self.state()["knowledge_revision"],
            "learnings": learnings,
            "discoveries": [] if discoveries is None else discoveries,
        }
        if resolutions is not None:
            payload["resolutions"] = resolutions
        return payload

    def formatted_commit(
        self,
        sid,
        iteration,
        verification_action,
        review_learning,
        apply_learning,
        carry_learning,
        *,
        allow_empty=True,
        include_plan_learnings=True,
    ):
        wt = self.worktree(sid)
        plan_learnings = iteration.get("plan_learnings", [])
        self.assertIsInstance(plan_learnings, list)
        self.assertTrue(all(isinstance(item, str) and item for item in plan_learnings))
        message = "\n".join(
            [
                f"Improve {sid} {iteration['id']}",
                "",
                "Review:",
                "Read the current Git history page and the recorded review findings.",
                "",
                "Changes:",
                "Recorded the scoped improvement described by the active iteration.",
                "",
                "Validation:",
                f"Fresh lint and exact-output checks passed for action {verification_action}.",
                "",
                "Key learnings:",
                review_learning,
                apply_learning,
                carry_learning,
                *(plan_learnings if include_plan_learnings else []),
                "",
                f"ShipLoop-Iteration: {iteration['id']}",
            ]
        )
        args = ["commit"]
        if allow_empty:
            args.append("--allow-empty")
        args.extend(["-m", message])
        self.git(*args, cwd=wt)
        return self.git("rev-parse", "HEAD", cwd=wt)

    def run_improve_iteration(
        self,
        sid,
        *,
        material,
        invalid_commit_first=False,
        missing_learning_first=False,
        missing_plan_learning_first=False,
        stop_at_carry_forward=False,
        carry_payload=None,
    ):
        """Exercise history -> plan -> apply -> checks -> carry-forward -> commit."""
        self.assertEqual(self.state()["stage"], "review")
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        knowledge_read = self.read_knowledge(sid)
        review_learning = "Commit history is read before each improvement decision."
        apply_learning = "Classifying material findings resets convergence even when the patch is small."
        findings = [
            {
                "severity": "material" if material else "trivial",
                "summary": "Material fixture audit note"
                if material
                else "Trivial fixture wording audit",
            }
        ]
        review = {
            "summary": "History and the current worktree were reviewed before planning improvements.",
            "findings": findings,
            "test_review": "The exact-output test covers the declared product and syntax check covers source parsing.",
            "learnings": review_learning,
            "knowledge_read": knowledge_read,
        }
        if self.activity_for(sid) == "research":
            review["research_review"] = self.research_review()
        self.complete(
            review,
            action_id=review_action,
            label=f"{sid}-review",
        )
        self.assertEqual(self.state()["stage"], "improve-plan")
        self.complete(
            {
                "summary": "The plan maps the review finding to one scoped adjustment and keeps the test intact.",
                "body": self.step_plan_candidate(
                    sid,
                    "improve draft",
                    parent_ids=self.step_plan_parent_ids(sid),
                ),
            },
            label=f"{sid}-improve-plan",
        )
        self.assertEqual(self.state()["stage"], "step-plan-review")
        self.converge_step_plan(sid)
        self.assertEqual(self.state()["stage"], "improve-apply")
        wt = self.worktree(sid)
        if material:
            with (wt / f"{sid.lower()}.py").open("a", encoding="utf-8") as handle:
                handle.write("# Material review note retained for the fixture.\n")
        self.complete(
            {
                "summary": "The planned improvement was applied without weakening its checks.",
                "material": material,
                "test_changes": "The exact-output test remains active; no acceptance condition was removed.",
                "learnings": apply_learning,
            },
            label=f"{sid}-improve-apply",
        )
        self.assertEqual(self.state()["stage"], "verify")
        verification_action = self.action_id()
        self.verify_current(self.manifest_for(sid), label=f"{sid}-fresh-checks")
        self.complete(
            {
                "summary": "Fresh lint and exact-output evidence is recorded for this improvement iteration."
            },
            action_id=verification_action,
            label=f"{sid}-verify-result",
        )
        self.assertEqual(self.state()["stage"], "carry-forward")
        carry_action = self.action_id()
        receipt = self.receipt(sid)
        iteration = copy.deepcopy(receipt["iteration"])
        if stop_at_carry_forward:
            return {
                "iteration": iteration,
                "verification_action": verification_action,
                "review_learning": review_learning,
                "apply_learning": apply_learning,
                "carry_action": carry_action,
                "knowledge_read": knowledge_read,
            }
        if carry_payload is None:
            carry_payload = self.carry_forward_payload()
        carry_learning = carry_payload["learnings"]
        self.complete(
            carry_payload,
            action_id=carry_action,
            label=f"{sid}-carry-forward",
        )
        self.assertEqual(self.state()["stage"], "commit")
        if invalid_commit_first:
            self.git("add", f"{sid.lower()}.py", cwd=wt)
            self.git("commit", "-m", "unstructured attempted primary commit", cwd=wt)
            bad_sha = self.git("rev-parse", "HEAD", cwd=wt)
            _, bad_result = self.complete(
                {
                    "summary": "Attempt to record an unstructured primary commit.",
                    "commit": bad_sha,
                },
                code=2,
                label=f"{sid}-bad-primary",
            )
            self.assertEqual(self.state()["stage"], "commit")
            self.assertEqual(self.receipt(sid)["improve_cycles"], [])
            self.assertTrue(Path(bad_result).is_file())
        else:
            self.git("add", f"{sid.lower()}.py", cwd=wt)
        if missing_learning_first:
            missing_sha = self.formatted_commit(
                sid,
                iteration,
                verification_action,
                "A different review learning that was not recorded in the result.",
                apply_learning,
                carry_learning,
            )
            rejected, _ = self.complete(
                {
                    "summary": "Attempt to record a structurally valid commit with a substituted learning.",
                    "commit": missing_sha,
                },
                code=2,
                label=f"{sid}-missing-learning",
            )
            self.assertIn("verbatim", rejected.stderr)
            self.assertEqual(self.state()["stage"], "commit")
            self.assertEqual(self.receipt(sid)["improve_cycles"], [])
        if missing_plan_learning_first:
            self.assertTrue(iteration.get("plan_learnings"))
            missing_plan_sha = self.formatted_commit(
                sid,
                iteration,
                verification_action,
                review_learning,
                apply_learning,
                carry_learning,
                include_plan_learnings=False,
            )
            missing_body = self.git(
                "show", "-s", "--format=%B", missing_plan_sha, cwd=wt
            )
            self.assertNotIn(iteration["plan_learnings"][0], missing_body)
            rejected, _ = self.complete(
                {
                    "summary": "Attempt to record a primary commit that omits nested plan learnings.",
                    "commit": missing_plan_sha,
                },
                code=2,
                label=f"{sid}-missing-plan-learning",
            )
            self.assertIn("primary commit must include", rejected.stderr)
            self.assertEqual(self.state()["stage"], "commit")
            self.assertEqual(self.receipt(sid)["improve_cycles"], [])
        primary = self.formatted_commit(
            sid,
            iteration,
            verification_action,
            review_learning,
            apply_learning,
            carry_learning,
        )
        commit_action = self.action_id()
        commit_payload = {
            "summary": "A verbose primary commit captures the review, changes, validation, and learning.",
            "commit": primary,
        }
        _, commit_result = self.complete(
            commit_payload, action_id=commit_action, label=f"{sid}-primary"
        )
        return commit_action, commit_result, primary

    def start_step(self, sid, *, exercise_failed_and_stale=False):
        self.assertEqual(self.state()["active_step"], sid)
        self.assertEqual(self.state()["stage"], "implement")
        self.write_implementation(sid, wrong_output=exercise_failed_and_stale)
        implement_action = self.action_id()
        if exercise_failed_and_stale:
            # An unverified or failed action cannot be certified by an arbitrary result.
            self.complete(
                {
                    "summary": "Claim completion without evidence.",
                    "test_review": "No check result exists.",
                },
                action_id=implement_action,
                code=2,
                label=f"{sid}-missing-evidence",
            )
            self.verify_current(
                self.manifest_for(sid), code=2, label=f"{sid}-failed-checks"
            )
            self.complete(
                {
                    "summary": "Claim completion after a failed check.",
                    "test_review": "The failed test was observed.",
                },
                action_id=implement_action,
                code=2,
                label=f"{sid}-failed-evidence",
            )
            wt = self.worktree(sid)
            expected = self.output_for(sid)
            (wt / f"{sid.lower()}.txt").write_text(expected + "\n", encoding="utf-8")
            self.git("add", f"{sid.lower()}.txt", cwd=wt)
            self.git(
                "commit",
                "-m",
                "Repair fixture output after failed exact-output check",
                cwd=wt,
            )
        self.verify_current(
            self.manifest_for(sid), label=f"{sid}-implementation-checks"
        )
        self.complete(
            {
                "summary": "Implementation has fresh lint and exact-output evidence.",
                "test_review": "The declared output is asserted exactly and source syntax is compiled without bytecode files.",
            },
            action_id=implement_action,
            label=f"{sid}-implementation",
        )
        self.assertEqual(self.state()["stage"], "review")
        if exercise_failed_and_stale:
            self.cli(
                "verify",
                "--action",
                implement_action,
                "--manifest",
                self.record(f"{sid}-stale-manifest", self.manifest_for(sid)),
                code=2,
            )

    def finish_step(
        self,
        sid,
        *,
        revise=False,
        material_first=False,
        merge=True,
        exercise_failure=None,
    ):
        if exercise_failure is None:
            exercise_failure = sid == "S1"
        self.start_step(sid, exercise_failed_and_stale=exercise_failure)
        action_one, result_one, primary_one = self.run_improve_iteration(
            sid, material=material_first, invalid_commit_first=material_first
        )
        after_first = self.receipt(sid)
        self.assertEqual(len(after_first["improve_cycles"]), 1)
        self.assertEqual(
            after_first["improve_cycles"][0]["outcome"],
            "material" if material_first else "trivial",
        )
        self.assertEqual(self.state()["stage"], "review")
        # A replay of the same completed commit action cannot create another cycle.
        self.cli("complete", "--action", action_one, "--result", result_one)
        self.assertEqual(len(self.receipt(sid)["improve_cycles"]), 1)
        action_two, _, primary_two = self.run_improve_iteration(sid, material=False)
        after_two = self.receipt(sid)
        self.assertEqual(len(after_two["improve_cycles"]), 2)
        self.assertEqual(
            self.state()["stage"], "final-verify" if not material_first else "review"
        )
        primary_three = None
        if material_first:
            _, _, primary_three = self.run_improve_iteration(sid, material=False)
            self.assertEqual(self.state()["stage"], "final-verify")
        primaries = [
            row["primary_commit"] for row in self.receipt(sid)["improve_cycles"]
        ]
        self.assertEqual(len(primaries), len(set(primaries)))
        self.assertIn(primary_one, primaries)
        self.assertIn(primary_two, primaries)
        if primary_three:
            self.assertIn(primary_three, primaries)
        final_action = self.action_id()
        self.verify_current(self.manifest_for(sid), label=f"{sid}-final-checks")
        self.complete(
            {
                "summary": "Fresh final checks passed after both trivial-only iterations.",
                "done_evidence": self.done_evidence(sid),
            },
            action_id=final_action,
            label=f"{sid}-final-verify",
        )
        self.assertEqual(self.state()["stage"], "post-inner")
        before_post_inner = copy.deepcopy(self.receipt(sid))
        if revise:
            revised = self.initial_dag()
            revised["steps"][1]["statement"] = (
                "Create the dependent artifact after the broader-plan review"
            )
            revised["steps"][1]["contract"]["objective"] = revised["steps"][1][
                "statement"
            ]
            revised["steps"][1]["prompt"] += (
                "\nApply the recorded broader-plan learning."
            )
            post_payload = {
                "summary": "Broader learning adjusts only the pending dependent step.",
                "plan_decision": "revise",
                "plan_reason": "The completed first step exposed a clearer description for the pending dependent activity.",
                "plan": self.plan_markdown(
                    "\nBroader-plan revision: clarify S2 without changing its dependency.\n"
                ),
                "dag": revised,
                "journal": [
                    {
                        "title": "Keep action receipts compact",
                        "evidence": "This walk needed only the current action, a receipt, and one history page.",
                        "impact": "Small contexts can resume without replaying the entire transcript.",
                        "proposal": "Keep packet output limited to the active action and durable artifact paths.",
                        "test_idea": "Assert a resumed packet names one action and does not embed all history.",
                    }
                ],
            }
        else:
            post_payload = {
                "summary": "No broader dependency, preparation, or test strategy change is needed.",
                "plan_decision": "no-change",
                "plan_reason": "The dependent sequence and outer waiver remain applicable after the recorded reviews.",
                "journal": [],
            }
        self.converge_objective(post_payload, label=f"{sid}-post-inner")
        after_post_inner = self.receipt(sid)
        self.assertEqual(
            after_post_inner["improve_cycles"], before_post_inner["improve_cycles"]
        )
        self.assertEqual(after_post_inner["worktree"], before_post_inner["worktree"])
        self.assertEqual(after_post_inner["status"], "running")
        self.assertEqual(self.state()["stage"], "merge")
        if not merge:
            return before_post_inner
        self.complete(
            {"summary": "Merge the converged step into the session checkout."},
            label=f"{sid}-merge",
        )
        next_state = self.state()
        if next_state.get("stage") == "step-plan":
            self.converge_step_plan(next_state["active_step"])
        return before_post_inner

class ShipLoopActionWalkTests(ShipLoopActionWalkFixture):
    """One real two-step walk plus narrow protocol-negatives."""

    def test_action_walk_enforces_evidence_history_commits_revision_and_terminal_journal(
        self,
    ):
        # Select the optional pre-allocation preparation branch through the
        # lifecycle candidate.  The caller still receives only the current
        # action; it never names a next workflow stage.
        self.fixture_preparation = "outer-before"
        self.start_transition_trace()
        initial_implementation = self.bootstrap_to_first_implementation()
        self.assertTrue((self.run_dir / "preparation.md").is_file())
        self.assertEqual(
            store.read_record(self.run_dir / "preparation.md")["evidence"],
            "The committed baseline and local Python runtime remain available for the declared exact-output checks.",
        )
        self.assertEqual(
            [entry["kind"] for entry in initial_implementation["objective_preallocation_bridge"]["entries"]],
            ["sequence", "preparation-readiness"],
        )

        # A context-reset host can ask for the next packet without mutating
        # the authoritative state or allocated receipt.
        cold_implementation = self.cold_next_is_read_only("steps/S1.md")
        self.assertIn(initial_implementation["action"]["id"], cold_implementation)
        self.assertIn("Call this when done:", cold_implementation)

        # No caller-facing transition command can select a later state.
        before_unknown_transition = self.authoritative_snapshot("steps/S1.md")
        unknown_transition = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "transition",
                "--run-dir",
                str(self.run_dir),
                "--to",
                "quality",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(unknown_transition.returncode, 2)
        self.assertIn("invalid choice", unknown_transition.stderr)
        self.assert_authority_unchanged(before_unknown_transition, "steps/S1.md")

        # Nor can an unallocated action ID cause the script to advance from
        # implementation; this synthetic result is not durable run evidence.
        before_unknown_action = self.authoritative_snapshot("steps/S1.md")
        rejected_unknown_action, _ = self.complete(
            {"summary": "Synthetic unbound callback."},
            action_id=initial_implementation["action"]["id"] + "-not-allocated",
            code=2,
            label="unknown-action",
        )
        self.assertIn("stale action ID; run next", rejected_unknown_action.stderr)
        self.assert_authority_unchanged(before_unknown_action, "steps/S1.md")

        append_context = self.read_outer_work_context()
        self.assertEqual(append_context["revision"], 0)
        append = self.local_quality_outer_request(append_context)
        self.cli(
            "journal",
            "--target",
            "outer",
            "--operation",
            "append",
            "--action",
            initial_implementation["action"]["id"],
            "--result",
            self.record("inner-quality-observation", append),
        )
        after_append = self.state()
        self.assertEqual(after_append["action"], initial_implementation["action"])
        self.assertEqual(after_append["stage"], "implement")
        self.assertEqual(after_append["outer_work_revision"], 1)
        outer_ledger = store.read_record(self.run_dir / "outer-work.md")
        self.assertEqual(outer_ledger["entries"][0]["id"], "OW-QUALITY-LOCAL-001")
        self.assertEqual(outer_ledger["entries"][0]["target_stage"], "quality")
        self.assertEqual(outer_ledger["entries"][0]["status"], "planned")
        s1_implementation_action = initial_implementation["action"]["id"]
        s1_before = self.finish_step("S1", revise=True, material_first=True)
        state_after_s1 = self.state()
        self.assertEqual(state_after_s1["active_step"], "S2")
        self.assertEqual(state_after_s1["stage"], "implement")
        s1 = self.receipt("S1")
        self.assertEqual(s1["status"], "complete")
        self.assertEqual(s1["improve_cycles"], s1_before["improve_cycles"])
        self.assertEqual((self.repo / "s1.txt").read_text(encoding="utf-8"), "first\n")
        self.assertFalse(
            (self.repo / "s2.txt").exists(), "S2 must not run before the S1 merge"
        )
        plan = store.read_record(self.run_dir / "backchain" / "plan.md")
        self.assertEqual(plan["steps"][0], self.initial_dag()["steps"][0])
        self.assertEqual(
            plan["steps"][1]["inputs"], [{"need": self.product_one, "from": "S1"}]
        )
        self.assertEqual(state_after_s1["plan_revision"], 1)

        # S1's once-valid implementation callback cannot be repurposed after
        # the script allocated S2: a different result is rejected as a
        # conflicting replay before any state or receipt mutation.
        before_stale_action = self.authoritative_snapshot("steps/S1.md", "steps/S2.md")
        rejected_stale_action, _ = self.complete(
            {"summary": "Synthetic stale S1 callback."},
            action_id=s1_implementation_action,
            code=2,
            label="stale-s1-action",
        )
        self.assertIn(
            "conflicting replay of a completed action", rejected_stale_action.stderr
        )
        self.assert_authority_unchanged(
            before_stale_action, "steps/S1.md", "steps/S2.md"
        )
        cold_s2 = self.cold_next_is_read_only("steps/S1.md", "steps/S2.md")
        self.assertIn(self.action_id(), cold_s2)

        self.finish_step("S2", revise=False, material_first=False)
        self.assertEqual((self.repo / "s2.txt").read_text(encoding="utf-8"), "second\n")
        self.assertEqual(self.state()["stage"], "coverage")
        self.converge_objective(
            {
                "summary": "The explicit bound-plan waiver permits the fixture to finish outer coverage."
            },
            label="coverage",
        )
        self.assertEqual(self.state()["stage"], "quality")
        cold_quality = self.cold_next_is_read_only()
        self.assertIn(self.action_id(), cold_quality)
        self.verify_current(
            self.manifest_for("S2", quality=True), label="whole-product-checks"
        )
        quality_candidate = {
            "summary": "Whole-product lint and exact-output checks passed after both merges.",
            "test_review": "Both declared lifecycle acceptance criteria are covered by an exact-output check.",
            "quality_review": "The merged fixture remains limited to its two declared exact-output acceptance criteria.",
        }
        missing_outer_read, _ = self.complete(
            quality_candidate,
            code=2,
            label="quality-missing-outer-read",
        )
        self.assertIn(
            "outer stage requires reading context --section outer-work",
            missing_outer_read.stderr,
        )
        self.assertEqual(self.state()["stage"], "quality")
        quality_context = self.read_outer_work_context()
        self.assertEqual(
            [entry["id"] for entry in quality_context["due"]],
            ["OW-QUALITY-LOCAL-001"],
        )
        unresolved_outer_work, _ = self.complete(
            quality_candidate,
            code=2,
            label="quality-unresolved-outer-work",
        )
        self.assertIn(
            "unresolved outer work blocks quality: OW-QUALITY-LOCAL-001",
            unresolved_outer_work.stderr,
        )
        resolution = copy.deepcopy(quality_context["resolve_template"])
        resolution.update(
            entry_id="OW-QUALITY-LOCAL-001",
            evidence="The final local exact-output check passed for both merged fixture artifacts.",
            reason="The quality-stage observation now has the required whole-product and final verification evidence.",
        )
        self.cli(
            "journal",
            "--target",
            "outer",
            "--operation",
            "resolve",
            "--action",
            self.action_id(),
            "--result",
            self.record("quality-observation-resolved", resolution),
        )
        self.assertEqual(self.state()["outer_work_revision"], 2)
        refreshed_quality_context = self.read_outer_work_context()
        self.assertEqual(refreshed_quality_context["due"], [])
        self.assertEqual(refreshed_quality_context["entries"][0]["status"], "resolved")
        self.converge_objective(
            quality_candidate,
            label="quality",
        )
        self.assertEqual(self.state()["stage"], "handoff")
        # A fresh host uses only the printed callback, including its run/result
        # locators, even when its cwd is no longer the product repository. The
        # callback starts the final handoff objective rather than bypassing it.
        handoff_context = self.read_outer_work_context()
        self.assertEqual(handoff_context["due"], [])
        handoff_packet = self.cold_next_is_read_only()
        callbacks = [
            line.removeprefix("Call this when done: ")
            for line in handoff_packet.splitlines()
            if line.startswith("Call this when done: ")
        ]
        self.assertEqual(len(callbacks), 1)
        callback = shlex.split(callbacks[0])
        handoff_action = callback[callback.index("--action") + 1]
        result_path = Path(callback[callback.index("--result") + 1])
        handoff_candidate = {
            "summary": "The fixture is complete with durable journal proposals available for later skill maintenance.",
            "journal": [],
        }
        store.write_record(result_path, handoff_candidate)
        handoff_before = self.state()
        handed_off = subprocess.run(
            callback, cwd=self.root, capture_output=True, text=True, env=self.env
        )
        self.assertEqual(handed_off.returncode, 0, handed_off.stdout + handed_off.stderr)
        self.record_completed_transition(
            handoff_before,
            self.state(),
            handoff_action,
            source="printed-callback",
        )
        self.assertIn(f"Last accepted: {handoff_action}", handed_off.stdout)
        self.assertEqual(self.state()["stage"], "objective-review")
        self.converge_objective(handoff_candidate, label="handoff", started=True)
        self.assertIn("It's all complete.", self.last_objective_final.stdout)
        terminal = self.state()
        self.assertEqual((terminal["phase"], terminal["stage"]), ("done", "done"))
        self.assertNotIn("active_step", terminal)
        report = self.run_dir / "report.html"
        self.assertTrue(report.is_file())
        report_html = report.read_text(encoding="utf-8")
        self.assertIn('data-outcome="complete"', report_html)
        self.assertIn("Derived report — not authoritative state.", report_html)
        self.assertEqual(terminal["report"]["path"], "report.html")
        self.assertEqual(
            terminal["report"]["sha256"],
            hashlib.sha256(report.read_bytes()).hexdigest(),
        )
        self.assertTrue(terminal["report"]["evidence_complete"])
        for section in ("overview", "timeline", "outputs", "tests"):
            self.assertIn(f'id="{section}"', report_html)

        # The in-test trace records only public callbacks that advanced the
        # run.  Match it to script-written Markdown chronology rather than
        # trusting the test hook by itself.
        history = store.read_record(self.run_dir / "history.md")
        self.assertEqual(history[0]["event"], "init")
        durable_completed_stages = [
            entry["event"].removeprefix("complete:")
            for entry in history
            if entry.get("event", "").startswith("complete:")
        ]
        traced_completed_stages = [
            entry["completed_stage"] for entry in self.transition_trace
        ]
        self.assertEqual(traced_completed_stages, durable_completed_stages)
        traced_stages = [entry["from_stage"] for entry in self.transition_trace]
        self.assertEqual(self.transition_trace[-1]["to_stage"], "done")
        self.assertTrue(
            any(
                entry["source"] == "printed-callback"
                for entry in self.transition_trace
            ),
            "handoff must use the exact callback printed by ShipLoop",
        )

        # The selected preparation branch precedes allocated steps.  Then the
        # script requires each inner and outer state-machine owner in order.
        self.assert_stage_subsequence(
            traced_stages,
            [
                "preflight",
                "approach",
                "survey",
                "research",
                "behavior",
                "spec",
                "sequence",
                "prepare",
                "step-plan",
                "implement",
                "coverage",
                "quality",
                "handoff",
                "objective-finalize",
            ],
        )
        for sid, expected_outcomes in (
            ("S1", ["material", "trivial", "trivial"]),
            ("S2", ["trivial", "trivial"]),
        ):
            step_stages = [
                entry["from_stage"]
                for entry in self.transition_trace
                if entry["from_step"] == sid
            ]
            # The initial plan plus one nested plan per improvement cycle must
            # all finish before final verification can advance the step.
            self.assertGreaterEqual(
                step_stages.count("step-plan-finalize"), len(expected_outcomes) + 1
            )
            self.assert_stage_subsequence(
                step_stages,
                [
                    "step-plan",
                    "step-plan-review",
                    "step-plan-revise",
                    "step-plan-verify",
                    "step-plan-commit",
                    "step-plan-finalize",
                    "implement",
                    "review",
                    "improve-plan",
                    "improve-apply",
                    "verify",
                    "carry-forward",
                    "commit",
                    "final-verify",
                    "post-inner",
                    "merge",
                ],
            )
            receipt = self.receipt(sid)
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(
                [cycle["outcome"] for cycle in receipt["improve_cycles"]],
                expected_outcomes,
            )
            self.assertTrue(
                all(cycle.get("primary_commit") for cycle in receipt["improve_cycles"])
            )

        # HTML is disposable; losing a result draft or damaging the view must
        # neither lose accepted Markdown evidence nor falsely certify success.
        result_path.unlink()
        report.write_text("damaged derived view", encoding="utf-8")
        damaged = self.cli("next", "--run-dir", str(self.run_dir), cwd=self.root).stdout
        self.assertNotIn("It's all complete.", damaged)
        self.assertIn("Recovery:", damaged)
        self.assertEqual(self.state(), terminal)
        prior_history = store.read_record(self.run_dir / "history.md")
        regenerated = self.cli("report", "--run-dir", str(self.run_dir), cwd=self.root).stdout
        repaired = self.state()
        self.assertIn("It's all complete.", regenerated)
        self.assertEqual(repaired["revision"], terminal["revision"] + 1)
        for key in ("phase", "stage", "action", "completed_actions"):
            self.assertEqual(repaired[key], terminal[key])
        current_history = store.read_record(self.run_dir / "history.md")
        self.assertEqual(current_history[:-1], prior_history)
        self.assertEqual(current_history[-1]["event"], "report-regenerated")
        self.assertNotEqual(repaired["report"]["source_digest"], terminal["report"]["source_digest"])
        self.assertEqual(repaired["report"]["sha256"], hashlib.sha256(report.read_bytes()).hexdigest())
        self.assertIn("report-regenerated", report.read_text(encoding="utf-8"))
        self.assertEqual((self.repo / "s1.txt").read_text(encoding="utf-8"), "first\n")
        self.assertEqual((self.repo / "s2.txt").read_text(encoding="utf-8"), "second\n")
        journal = store.read_record(self.run_dir / "shiploop-improvements.md")
        self.assertEqual(len(journal), 1)
        self.assertEqual(journal[0]["title"], "Keep action receipts compact")
        self.assertTrue((self.run_dir / "handoff.md").is_file())
        self.assertFalse(
            Path(s1_before["worktree"]).exists(),
            "journal must survive disposable worktree removal",
        )

    def test_preparation_readiness_objective_extends_the_preallocation_audit_bridge(self):
        self.fixture_preparation = "outer-before"
        state = self.bootstrap_to_first_step_plan()
        self.assertEqual((state["phase"], state["stage"], state["active_step"]), ("implement", "step-plan", "S1"))
        self.assertEqual(
            store.read_record(self.run_dir / "preparation.md")["evidence"],
            "The committed baseline and local Python runtime remain available for the declared exact-output checks.",
        )
        bridge = state["objective_preallocation_bridge"]
        self.assertEqual(
            [row["kind"] for row in bridge["entries"]],
            ["sequence", "preparation-readiness"],
        )

    def test_post_convergence_commit_with_green_checks_requires_inner_repair(self):
        """Fresh passing tests cannot replace review of the accepted revision."""
        self.bootstrap_to_first_implementation()
        self.start_step("S1")
        self.run_improve_iteration("S1", material=False)
        self.run_improve_iteration("S1", material=False)
        self.assertEqual(self.state()["stage"], "final-verify")
        self.assertTrue(CORE.improve_two_clean(self.receipt("S1")))
        accepted_primary = self.receipt("S1")["improve_cycles"][-1]["primary_commit"]
        worktree = self.worktree("S1")
        source = worktree / "s1.py"
        changed_source = source.read_text(encoding="utf-8") + (
            "\ndef unreviewed_late_function():\n    return 'not reviewed'\n"
        )
        source.write_text(changed_source, encoding="utf-8")
        self.git("add", "s1.py", cwd=worktree)
        self.git("commit", "-m", "late source change outside Improve", cwd=worktree)
        late_head = self.git("rev-parse", "HEAD", cwd=worktree)
        self.assertNotEqual(late_head, accepted_primary)

        final_action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="late-source-green-checks")
        before = {
            name: (self.run_dir / name).read_bytes()
            for name in ("state.md", "steps/S1.md", "history.md")
        }
        rejected, _ = self.complete(
            {
                "summary": "New source passes checks but never received Improve review.",
                "done_evidence": self.done_evidence("S1"),
            },
            action_id=final_action,
            code=2,
            label="late-source-finalization",
        )
        self.assertIn("new source revision appeared", rejected.stderr)
        self.assertEqual(
            {name: (self.run_dir / name).read_bytes() for name in before}, before
        )
        self.assertFalse((self.run_dir / "results" / f"{final_action}.md").exists())

        self.cli(
            "repair", "--action", final_action,
            "--reason", "Retain the late source commit and restart its full Improve review.",
        )
        repaired = self.receipt("S1")
        self.assertEqual(self.state()["stage"], "review")
        self.assertNotEqual(self.action_id(), final_action)
        self.assertEqual(repaired["improve_cycles"][-1]["kind"], "repair-checkpoint")
        self.assertFalse(CORE.improve_two_clean(repaired))
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=worktree), late_head)
        self.assertEqual(source.read_text(encoding="utf-8"), changed_source)

    def test_twelve_material_cycles_do_not_converge(self):
        receipt = {
            "improve_cycles": [
                {"outcome": "material", "primary_commit": f"c{i}"} for i in range(12)
            ]
        }
        self.assertFalse(CORE.improve_two_clean(receipt))

    def test_fixture_markdown_lint_rejects_malformed_or_trailing_whitespace(self):
        candidate = self.records / "candidate.md"
        store.write_record(candidate, {"summary": "A valid immutable candidate."}, title="Candidate")
        argv = self.markdown_lint_argv(candidate, state_record=True)
        self.assertNotIn(str(CLI), argv)
        valid = subprocess.run(argv, capture_output=True, text=True, env=self.env)
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

        plain = self.records / "plain-candidate.md"
        plain.write_text("# Candidate\n\n## Scope\n\nBounded Markdown body.\n", encoding="utf-8")
        plain_valid = subprocess.run(
            self.markdown_lint_argv(plain), capture_output=True, text=True, env=self.env
        )
        self.assertEqual(plain_valid.returncode, 0, plain_valid.stdout + plain_valid.stderr)

        empty = self.records / "empty-candidate.md"
        empty.write_text("", encoding="utf-8")
        empty_result = subprocess.run(
            self.markdown_lint_argv(empty), capture_output=True, text=True, env=self.env
        )
        self.assertNotEqual(empty_result.returncode, 0)

        candidate.write_text(
            "# Candidate \n\n```shiploop-state\n{}\n```\n", encoding="utf-8"
        )
        invalid = subprocess.run(argv, capture_output=True, text=True, env=self.env)
        self.assertNotEqual(invalid.returncode, 0)

    def test_objective_cold_resume_failed_checks_and_material_reset(self):
        """A generic outer loop is durable, fail-closed, and resets on material work."""
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--prompt",
            "Exercise a durable objective loop.",
        )
        self.complete(
            {
                "summary": "The committed fixture baseline and local runtime are available.",
                "baseline": "committed-head",
            },
            label="objective-cold-preflight",
        )
        candidate = {
            "summary": "The approach retains a bounded tested delivery sequence.",
            "body": "# Approach\n\nUse durable evidence and exact-output checks for each fixture transition.\n",
        }
        self.complete(candidate, label="objective-cold-approach-draft")
        self.assertEqual(self.state()["stage"], "objective-review")
        binding = copy.deepcopy(self.objective_binding())
        action_before = self.action_id()
        cold_packet = self.cli("next").stdout
        self.assertEqual(self.action_id(), action_before)
        self.assertTrue((self.run_dir / binding["receipt"]).is_file())
        self.assertTrue((self.run_dir / binding["candidate"]).is_file())
        self.assertIn("objective-review", cold_packet)

        self.converge_objective(
            candidate,
            label="approach",
            material_first=True,
            started=True,
            fail_first_verify=True,
        )
        receipt = store.read_record(self.run_dir / binding["receipt"])
        self.assertEqual(
            [row["outcome"] for row in receipt["completed_passes"]],
            ["material", "trivial", "trivial"],
        )
        self.assertEqual(self.state()["stage"], "survey")

    def test_primary_commit_cannot_substitute_recorded_learnings(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        self.run_improve_iteration("S1", material=False, missing_learning_first=True)
        cycles = self.receipt("S1")["improve_cycles"]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["outcome"], "trivial")

    def test_primary_commit_cannot_omit_nested_step_plan_learnings(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        self.run_improve_iteration(
            "S1", material=False, missing_plan_learning_first=True
        )
        cycles = self.receipt("S1")["improve_cycles"]
        self.assertEqual(len(cycles), 1)
        self.assertTrue(cycles[0]["plan_learnings"])

    def test_execution_research_assessment_requires_full_later_resolution(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        review_action = self.action_id()
        self.cli(
            "history", "--action", review_action, "--limit", "10", "--skip", "0", "--full"
        )
        knowledge_read = self.read_knowledge("S1")
        review = {
            "summary": "The review identifies a scoped research question before a fixture adjustment.",
            "findings": [],
            "test_review": "The exact-output test remains the active local evidence.",
            "learnings": "Research follow-up must be resolved before this iteration can converge.",
            "knowledge_read": knowledge_read,
        }
        rejected, _ = self.complete(
            review,
            action_id=review_action,
            code=2,
            label="missing-research-assessment",
            include_research_assessment=False,
        )
        self.assertIn("research_assessment", rejected.stderr)
        questions = [
            "Does the local exact-output contract remain sufficient?",
            "Does the fixture require a new local research report?",
        ]
        review["research_assessment"] = self.research_assessment(
            "required", questions=questions
        )
        self.complete(review, action_id=review_action, label="required-research-assessment")
        self.assertEqual(self.state()["stage"], "improve-plan")
        self.complete(
            {
                "summary": "The plan resolves the exact research questions before verification.",
                "body": self.step_plan_candidate("S1", "research improve draft")
                + "\n\n## Research resolution\n\nResolve both local research questions without weakening the check.\n",
            },
            label="required-research-plan",
        )
        self.assertEqual(self.state()["stage"], "step-plan-review")
        self.converge_step_plan("S1")
        self.assertEqual(self.state()["stage"], "improve-apply")
        apply = {
            "summary": "The local evidence resolves the required research questions.",
            "material": False,
            "test_changes": "The exact-output test remains active.",
            "learnings": "A required research assessment makes this otherwise trivial iteration material.",
            "research_assessment": self.research_assessment(
                "resolved", questions=questions[:1]
            ),
        }
        rejected, _ = self.complete(
            apply,
            code=2,
            label="partial-research-resolution",
        )
        self.assertIn("retain every prior required question", rejected.stderr)
        apply["research_assessment"] = self.research_assessment(
            "resolved", questions=questions
        )
        self.complete(apply, label="full-research-resolution")
        self.assertEqual(self.state()["stage"], "verify")
        verification_action = self.action_id()
        self.verify_current(self.manifest_for("S1"), label="research-resolution-checks")
        self.complete(
            {"summary": "Fresh local checks confirm the resolved research assessment."},
            action_id=verification_action,
            label="research-resolution-verify",
        )
        self.assertEqual(self.state()["stage"], "carry-forward")
        carry_learning = "The resolved local research questions remain attached to this material iteration."
        self.complete(
            {
                "summary": "The verified iteration records its required carry-forward checkpoint.",
                "knowledge_revision": self.state()["knowledge_revision"],
                "learnings": carry_learning,
                "discoveries": [],
            },
            label="research-resolution-carry-forward",
        )
        receipt = self.receipt("S1")
        wt = self.worktree("S1")
        self.git("add", "s1.py", cwd=wt)
        commit = self.formatted_commit(
            "S1",
            receipt["iteration"],
            verification_action,
            review["learnings"],
            apply["learnings"],
            carry_learning,
        )
        self.complete(
            {
                "summary": "The primary commit retains the resolved research assessment learning.",
                "commit": commit,
            },
            label="research-resolution-commit",
        )
        cycle = self.receipt("S1")["improve_cycles"][-1]
        self.assertEqual(cycle["outcome"], "material")
        self.assertEqual(cycle["research_assessment"]["status"], "resolved")

    def test_review_requires_the_bound_full_history_page_not_a_subject_index(self):
        self.bootstrap_to_first_implementation()
        state_before_status = (self.run_dir / "state.md").read_bytes()
        history_before_status = (self.run_dir / "history.md").read_bytes()
        self.cli("status")
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_status)
        self.assertEqual(
            (self.run_dir / "history.md").read_bytes(), history_before_status
        )
        self.start_step("S1", exercise_failed_and_stale=False)
        action = self.action_id()
        context = self.cli(
            "context", "--section", "iteration", "--offset", "0", "--limit", "40"
        ).stdout
        self.assertIn("Context iteration; digest", context)
        self.assertIn("Continue: --offset 40", context)
        self.assertNotIn("improve_cycles", context)
        checksum = context.split("digest ", 1)[1].split()[0].rstrip(";")
        continued = self.cli(
            "context",
            "--section",
            "iteration",
            "--offset",
            "40",
            "--limit",
            "40",
            "--digest",
            checksum,
        ).stdout
        self.assertNotIn("improve_cycles", continued)
        self.cli("history", "--action", action, "--limit", "1", "--skip", "0")
        knowledge_read = self.read_knowledge("S1")
        rejected, _ = self.complete(
            {
                "summary": "A one-commit page was reviewed.",
                "findings": [],
                "test_review": "The implementation check remains the active evidence.",
                "learnings": "One page does not cover all available commit bodies.",
                "knowledge_read": knowledge_read,
            },
            action_id=action,
            code=2,
            label="partial-history-review",
        )
        self.assertIn("read current Git history", rejected.stderr)
        self.assertEqual(self.state()["stage"], "review")
        history_limit = history_policy.required_limit(self.state())
        self.cli(
            "history", "--action", action, "--limit", str(history_limit), "--skip", "0", "--full"
        )
        self.complete(
            {
                "summary": "The complete current policy-owned history page was reviewed before the decision.",
                "findings": [],
                "test_review": "The implementation check remains the active evidence.",
                "learnings": "A full current history page is durable evidence, while its subject index is only navigation.",
                "knowledge_read": knowledge_read,
            },
            action_id=action,
            label="complete-history-review",
        )
        self.assertEqual(self.state()["stage"], "improve-plan")

    def test_foreign_worktree_receipt_is_rejected_without_status_mutation(self):
        self.bootstrap_to_first_implementation()
        state_before = (self.run_dir / "state.md").read_bytes()
        history_before = (self.run_dir / "history.md").read_bytes()
        repo_status_before = self.git("status", "--porcelain")
        original = self.receipt("S1")
        forged = dict(original, worktree=str(self.repo))
        store.write_record(
            self.run_dir / "steps" / "S1.md", forged, title="Forged receipt"
        )
        blocked = self.cli("status")
        self.assertIn("foreign worktree", blocked.stdout)
        self.assertIn("No completion callback is valid", blocked.stdout)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before)
        self.assertEqual((self.run_dir / "history.md").read_bytes(), history_before)
        self.assertTrue(Path(original["worktree"]).is_dir())
        self.assertEqual(self.git("status", "--porcelain"), repo_status_before)

    def test_session_head_drift_blocks_merge_without_completing_the_receipt(self):
        self.bootstrap_to_first_implementation()
        self.finish_step("S1", merge=False, exercise_failure=False)
        self.assertEqual(self.state()["stage"], "merge")
        receipt_before = self.receipt("S1")
        state_before = (self.run_dir / "state.md").read_bytes()
        receipt_before_bytes = (self.run_dir / "steps" / "S1.md").read_bytes()
        (self.repo / "session-baseline-note.txt").write_text(
            "new session baseline\n", encoding="utf-8"
        )
        self.git("add", "session-baseline-note.txt")
        self.git("commit", "-m", "Advance session baseline independently")
        merge_action = self.action_id()
        blocked, _ = self.complete(
            {
                "summary": "Attempt to merge a previously converged step after the session baseline changed."
            },
            action_id=merge_action,
            code=2,
            label="drifted-merge",
        )
        self.assertIn("session baseline changed", blocked.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before)
        self.assertEqual(
            (self.run_dir / "steps" / "S1.md").read_bytes(), receipt_before_bytes
        )
        receipt_after = self.receipt("S1")
        self.assertEqual(receipt_after["status"], "running")
        self.assertNotIn("merged_sha", receipt_after)
        self.assertNotIn("merge_target", receipt_after)
        self.assertTrue(Path(receipt_before["worktree"]).is_dir())
        self.git(
            "merge-base", "--is-ancestor", receipt_before["branch"], "HEAD", code=1
        )

    def test_outer_replan_starts_a_corrective_pending_step_and_keeps_completed_receipts(
        self,
    ):
        self.bootstrap_to_first_implementation()
        self.finish_step("S1", exercise_failure=False)
        completed_s1 = copy.deepcopy(self.receipt("S1"))
        self.finish_step("S2", exercise_failure=False)
        completed_s2 = copy.deepcopy(self.receipt("S2"))
        self.assertEqual(self.state()["stage"], "coverage")
        self.converge_objective(
            {
                "summary": "The explicit bound-plan waiver permits the fixture to enter the outer quality review."
            },
            label="outer-replan-coverage",
        )
        self.assertEqual(self.state()["stage"], "quality")
        self.complete(
            {
                "summary": "A newly observed outer quality concern needs a corrective pending step.",
                "test_review": "The existing whole-product exact-output checks identify the corrective gap.",
                "quality_review": "The pending corrective work belongs in the DAG rather than an untracked outer edit.",
            },
            label="outer-replan-quality-draft",
        )
        self.assertEqual(self.state()["stage"], "objective-review")
        quality_objective = copy.deepcopy(self.state()["objective"])
        quality_receipt_path = self.run_dir / quality_objective["receipt"]
        self.assertTrue(quality_receipt_path.is_file())
        self.objective_history()
        self.complete(
            {
                "summary": "The outer-quality candidate is reviewed before its corrective replan is proposed.",
                "findings": [
                    {
                        "id": "OBJ-quality-replan",
                        "severity": "material",
                        "category": "implementation",
                        "summary": "The quality review found a product defect that requires a new pending DAG step.",
                    }
                ],
                "assessment": self.objective_assessment("quality"),
                "history_assessment": "The full current history page was read before deciding that corrective work is required.",
                "test_review": "Whole-product exact-output coverage identifies the missing corrective behavior.",
                "learnings": "A discovered outer defect must be preserved as corrective work, not converged inside the quality objective.",
            },
            label="outer-replan-quality-review",
        )
        self.assertEqual(self.state()["stage"], "objective-plan")
        reviewed_quality_pass = self.objective_receipt()["current_pass"]
        revised = self.initial_dag()
        revised["steps"].append(
            self.step(
                "S3",
                "correction.txt contains exactly one line: repaired",
                [{"need": self.product_two, "from": "S2"}],
                "Apply the corrective action identified by the outer quality review",
            )
        )
        replan_action = self.action_id()
        result = self.record(
            "outer-replan",
            {
                "summary": "Outer quality learning adds one corrective step without rewriting completed work.",
                "plan_decision": "revise",
                "plan_reason": "The correction is additional work discovered after the original two-step walk drained.",
                "plan": self.plan_markdown(
                    "\nOuter corrective step S3 was added after the quality review.\n"
                ),
                "dag": revised,
                "journal": [],
            },
        )
        self.cli("replan", "--action", replan_action, "--result", result)
        abandoned_quality = store.read_record(quality_receipt_path)
        self.assertEqual(abandoned_quality["status"], "abandoned")
        self.assertIn(
            "Corrective pending DAG work",
            abandoned_quality["abandonment"]["reason"],
        )
        self.assertNotIn("certificate", abandoned_quality)
        archived_quality_pass = abandoned_quality["abandoned_passes"][-1]
        self.assertEqual(archived_quality_pass["id"], reviewed_quality_pass["id"])
        self.assertEqual(
            archived_quality_pass["reason"],
            abandoned_quality["abandonment"]["reason"],
        )
        self.assertIn("review", archived_quality_pass)
        self.assertEqual(
            archived_quality_pass["review"]["learnings"],
            "A discovered outer defect must be preserved as corrective work, not converged inside the quality objective.",
        )
        abandoned_archive = self.run_dir / objectives.abandoned_name(
            quality_objective["loop_id"], archived_quality_pass["id"]
        )
        self.assertTrue(abandoned_archive.is_file())
        self.assertEqual(store.read_record(abandoned_archive), archived_quality_pass)
        state = self.state()
        self.assertEqual(
            (state["phase"], state["stage"], state["active_step"]),
            ("implement", "step-plan", "S3"),
        )
        self.converge_step_plan("S3")
        self.assertEqual(self.state()["stage"], "implement")
        self.assertEqual(self.receipt("S1")["status"], "complete")
        self.assertEqual(self.receipt("S2")["status"], "complete")
        self.assertEqual(
            self.receipt("S1")["improve_cycles"], completed_s1["improve_cycles"]
        )
        self.assertEqual(
            self.receipt("S2")["improve_cycles"], completed_s2["improve_cycles"]
        )
        s3 = self.receipt("S3")
        self.assertEqual(s3["status"], "running")
        self.assertTrue(Path(s3["worktree"]).is_dir())
        plan = store.read_record(self.run_dir / "backchain" / "plan.md")
        self.assertEqual(plan["steps"][-1]["id"], "S3")
        self.assertEqual(
            plan["steps"][-1]["inputs"], [{"need": self.product_two, "from": "S2"}]
        )


if __name__ == "__main__":
    unittest.main()
