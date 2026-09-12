#!/usr/bin/env python3
"""Real-CLI acceptance tests for ShipLoop's planning convergence loops.

These fixtures deliberately keep the product repository small.  The assertions
exercise the public ``shiploop`` command and Markdown result records rather
than patching a planning cursor or calling private transition helpers.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
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
import shiploop_objectives as objectives  # noqa: E402


class PlanningLoopTests(unittest.TestCase):
    """Planning-loop gates using fresh public-CLI subprocesses."""

    BEHAVIOR_RUBRIC = (
        "requirements",
        "states",
        "transitions",
        "edge_conditions",
        "sequences",
        "test_mapping",
        "ambiguities",
    )
    SPEC_RUBRIC = BEHAVIOR_RUBRIC + ("clarity", "consistency", "feasibility")
    RESEARCH_RUBRIC = (
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

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-planning-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.records = self.root / "records"
        self.records.mkdir()
        self.run_dir = self.repo / ".shiploop"
        self.counter = 0
        self.env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            SHIPLOOP_BACKCHAIN_ROOT=str(ROOT / "test/fixtures/shiploop/backchain-leaf"),
        )
        self.git("init", "-q")
        self.git("config", "user.name", "ShipLoop Planning Test")
        self.git("config", "user.email", "planning@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")

    def git(self, *args: str, cwd: Path | None = None, code: int = 0) -> str:
        process = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process.stdout.strip()

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process

    def record(self, label: str, payload: dict) -> str:
        self.counter += 1
        path = self.records / f"{self.counter:02d}-{label}.md"
        store.write_record(path, payload, title=f"Planning test {label}")
        return str(path)

    def state(self) -> dict:
        return store.read_record(self.run_dir / "state.md")

    def make_old_run(self) -> dict:
        """Simulate a pre-planning-loop v3 state only for upgrade negatives."""
        state = self.state()
        state.pop("planning_protocol_version", None)
        store.write_record(self.run_dir / "state.md", state)
        return state

    def planning(self, kind: str) -> dict:
        return store.read_record(self.run_dir / "planning" / f"{kind}.md")

    def complete(
        self,
        payload: dict,
        *,
        action_id: str | None = None,
        code: int = 0,
        label: str = "result",
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        aid = action_id or self.state()["action"]["id"]
        result = self.record(label, payload)
        return (
            self.cli("complete", "--action", aid, "--result", result, code=code),
            result,
        )

    def assert_cursor(self, phase: str, stage: str) -> dict:
        state = self.state()
        self.assertEqual((state["phase"], state["stage"]), (phase, stage))
        self.assertEqual(state["action"]["stage"], stage)
        return state

    def machine_markdown(self) -> str:
        machine = {
            "kind": "greenfield",
            "augment": False,
            "references": [],
            "tools": [],
            "mcp": [],
            "mcp_considered": "none(local fixture)",
            "handles": [],
            "initiation": "none",
            "ui": False,
            "ui_craft": "none(local fixture)",
            "exclusive": [],
            "platform_discovery": {
                "version": 1,
                "applicable": False,
                "rationale": "This deterministic fixture has no external platform route.",
                "platforms": [],
            },
        }
        return "Fixture survey.\n\n## machine\n```json\n" + json.dumps(machine) + "\n```\n"

    def research_body(self, revision: str = "initial") -> str:
        return f"""# Fixture research ({revision})

## Question RQ-001

Can the local fixture validate exact output without a network dependency?

## Conclusion

The Python standard library and committed local repository provide the required
deterministic checks. Revalidate the local runtime before implementation.
"""

    def research_state(
        self,
        revision: str = "initial",
        *,
        status: str = "resolved",
        include_follow_up: bool = False,
        answer: str | None = None,
    ) -> dict:
        """Typed local-only evidence used by the research convergence fixture."""
        self.assertIn(status, {"resolved", "open", "blocked", "not-applicable"})
        source_id = "SRC-LOCAL-001"
        default_answers = {
            "resolved": "The local Python runtime can run deterministic exact-output checks.",
            "open": "The local runtime version still needs a fresh availability check.",
            "blocked": "The required local runtime probe is blocked pending operator access.",
            "not-applicable": "Not applicable: this local fixture has no external service dependency.",
        }
        question = {
            "id": "RQ-001",
            "question": "Can the local fixture validate exact output without a network dependency?",
            "origin": "prompt discovery: surveyed local fixture",
            "status": status,
            "answer": answer or default_answers[status],
            "sources": [] if status == "not-applicable" else [source_id],
            "revalidate": "Run the fixture's local lint and exact-output checks before implementation.",
            "rationale": "The fixture must remain deterministic and network-free.",
        }
        questions = [question]
        if include_follow_up:
            questions.append(
                {
                    "id": "RQ-002",
                    "question": "Does the fixture need an external invocation contract?",
                    "origin": "prompt discovery: surveyed local fixture",
                    "status": "resolved",
                    "answer": "No external invocation contract exists in this local-only fixture.",
                    "sources": [source_id],
                    "revalidate": "Confirm the planned steps remain local-only.",
                    "rationale": "A new service dependency would require a new research pass.",
                }
            )
        return {
            "questions": questions,
            "sources": [
                {
                    "id": source_id,
                    "reference": "test fixture local runtime record",
                    "authority": "local",
                    "version_or_observed_at": f"fixture-{revision}",
                    "supports": "The local deterministic exact-output research conclusion.",
                    "limitations": "This evidence does not claim any external service availability.",
                }
            ],
        }

    def behavior_body(self, revision: str = "initial") -> str:
        return f"""# Fixture behavior model ({revision})

## Requirements

R-01: A request can move from submitted to accepted only after validation.

## States

S-01 submitted; S-02 accepted; S-03 rejected.

## Transitions

T-01: submitted --valid request--> accepted; invalid request --> rejected.

## Edge conditions

Repeated submission is idempotent; an invalid request has no accepted-state side effect.

## Sequences

F-01: client submits, validator evaluates, observer receives accepted or rejected state.

## Test mapping

TC-01 covers valid acceptance; TC-02 covers invalid rejection and repeated submission.

## Ambiguities

None for this isolated fixture.
"""

    def spec_body(self, revision: str = "initial") -> str:
        return f"""# Fixture specification ({revision})

done_sentence: fixture request reaches accepted or rejected state with an observable result
checkable: true

## Requirements

R-01: A request can move from submitted to accepted only after validation.

## States and transitions

S-01 submitted; S-02 accepted; S-03 rejected. T-01 validates before acceptance.

## Edge conditions and sequences

Repeated submission is idempotent and invalid input has no accepted-state side effect.

## Test mapping

TC-01 validates acceptance; TC-02 validates rejection and repetition.
"""

    def lifecycle(self) -> dict:
        return {
            "acceptance": [
                "fixture request reaches accepted or rejected state with an observable result"
            ],
            "preparation": "none",
            "publish": "none",
            "quality": False,
            "reason": "The fixture has no deployment boundary.",
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

    def sequence_payload(self) -> dict:
        goal = "fixture request reaches accepted or rejected state with an observable result"
        return {
            "summary": "The sequence keeps the fixture transition checkable after planning convergence.",
            "dependency_review": "The single fixture step consumes only the established repository baseline.",
            "plan": "# Fixture sequence\n\ndone_sentence: " + goal + "\n\n## Review Coverage\n\nNone — fixture-only planning regression.\n",
            "dag": {
                "contract_version": 1,
                "goal": goal,
                "initial_state": ["repository exists"],
                "steps": [
                    {
                        "id": "S1",
                        "statement": "Create the fixture transition artifact",
                        "prompt": "/goal\nDo this activity until these conditions are met:\n- fixture transition artifact exists\n",
                        "produces": ["fixture transition artifact exists"],
                        "origin": "discovered",
                        "inputs": [{"need": "repository exists", "from": None}],
                        "contract": {
                            "objective": "Create the fixture transition artifact",
                            "ready": [
                                {
                                    "id": "R-S1",
                                    "condition": "S1 has a current scoped step plan before edits.",
                                    "evidence_method": "planning verify candidate check",
                                }
                            ],
                            "done": [
                                {
                                    "id": "D-S1",
                                    "condition": "S1 transition artifact is integrated.",
                                    "produces": ["fixture transition artifact exists"],
                                    "evidence_method": "exact-output verification",
                                    "completion": "integrated",
                                }
                            ],
                            "tests": [
                                {
                                    "id": "T-S1",
                                    "produces": ["fixture transition artifact exists"],
                                    "expected_outcome": "fixture transition artifact exists",
                                    "surface": "local Python exact-output check",
                                    "evidence_method": "exact-output verification",
                                }
                            ],
                            "documentation": [
                                {
                                    "id": "DOC-S1",
                                    "condition": "Fixture README is unchanged because this planning-only fixture has no product README.",
                                    "evidence_method": "manual fixture documentation review",
                                }
                            ],
                        },
                    }
                ],
                "unresolved": [],
            },
        }

    def bootstrap_to_research(self) -> None:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--prompt",
            "Plan a fixture with explicit states, transitions, and edge conditions.",
        )
        self.complete(
            {"summary": "A committed local baseline and Python runtime are available.", "baseline": "committed-head"},
            label="preflight",
        )
        self.converge_objective(
            {
                "summary": "The approach identifies a validation state transition and repeat-event risk.",
                "body": "# Approach\n\nModel the request state transition before implementation.\n",
            },
            label="approach",
        )
        self.assert_cursor("validate-spec", "survey")
        self.converge_objective(
            {
                "summary": "The fixture is greenfield and has no external surface.",
                "body": self.machine_markdown(),
            },
            label="survey",
        )
        self.assert_cursor("validate-spec", "research")

    def bootstrap_to_behavior(self) -> None:
        self.bootstrap_to_research()
        self.converge_research()
        self.assert_cursor("validate-spec", "behavior")
        self.assertEqual(self.state().get("planning_protocol_version"), 2)

    def start_candidate(self, kind: str) -> None:
        self.assert_cursor("validate-spec", kind)
        if kind == "research":
            payload = {
                "summary": "The initial research candidate records typed local evidence and a revalidation plan.",
                "body": self.research_body(),
                "research_state": self.research_state(),
            }
        elif kind == "behavior":
            payload = {
                "summary": "The initial behavior model covers requirements, states, transitions, and edge conditions.",
                "body": self.behavior_body(),
            }
        else:
            payload = {
                "summary": "The initial specification maps the behavior model to checkable acceptance.",
                "body": self.spec_body(),
                "lifecycle": self.lifecycle(),
            }
        self.complete(payload, label=f"{kind}-initial")
        self.assert_cursor("validate-spec", f"{kind}-review")

    def coverage_review(self, kind: str) -> dict[str, str]:
        dimensions = (
            self.RESEARCH_RUBRIC
            if kind == "research"
            else self.BEHAVIOR_RUBRIC
            if kind == "behavior"
            else self.SPEC_RUBRIC
        )
        return {
            dimension: f"Reviewed {dimension} against the current {kind} candidate."
            for dimension in dimensions
        }

    def history(self) -> None:
        self.cli(
            "history",
            "--action",
            self.state()["action"]["id"],
            "--limit",
            "10",
            "--skip",
            "0",
            "--full",
        )

    def objective_receipt(self) -> tuple[dict, dict]:
        state = self.state()
        binding = state.get("objective")
        self.assertIsInstance(binding, dict)
        self.assertEqual(binding.get("status"), "active")
        return state, store.read_record(self.run_dir / binding["receipt"])

    def objective_manifest(self, kind: str) -> dict:
        _, receipt = self.objective_receipt()
        candidate = self.run_dir / receipt["candidate_path"]
        check = (
            "from pathlib import Path; "
            f"assert Path({str(candidate)!r}).read_text(encoding='utf-8').strip()"
        )
        return {
            "checks": [
                {
                    "id": "objective-lint",
                    "kind": "lint",
                    "argv": [sys.executable, "-B", "-c", "raise SystemExit(0)"],
                    "acceptance": [],
                },
                {
                    "id": "objective-candidate",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", check],
                    "acceptance": [f"objective {kind}"],
                },
            ]
        }

    def objective_audit_commit(self, kind: str) -> str:
        _, receipt = self.objective_receipt()
        current = receipt["current_pass"]
        review = current["review"]["learnings"]
        plan = current["plan"]["learnings"]
        apply = current["apply"]["learnings"]
        message = "\n".join(
            [
                f"Objective {kind} {current['id']}",
                "",
                "Review:",
                review,
                "",
                "Changes:",
                plan,
                apply,
                "",
                "Validation:",
                "Fresh local lint and candidate acceptance checks passed.",
                "",
                "Key learnings:",
                review,
                plan,
                apply,
                "",
                f"ShipLoop-Iteration: {current['id']}",
            ]
        )
        self.git("commit", "--allow-empty", "--only", "-m", message)
        return self.git("rev-parse", "HEAD")

    def converge_objective(
        self,
        candidate: dict,
        *,
        label: str,
        material_first: bool = False,
        final_code: int = 0,
    ) -> dict:
        """Exercise a base-stage objective loop through its public CLI actions."""
        self.complete(candidate, label=f"{label}-objective-draft")
        state, receipt = self.objective_receipt()
        kind = receipt["kind"]
        self.assertEqual(kind, label)
        self.assertEqual(state["stage"], "objective-review")
        current_candidate = copy.deepcopy(candidate)
        passes = 3 if material_first else 2
        for number in range(1, passes + 1):
            self.assertEqual(self.state()["stage"], "objective-review")
            review_action = self.state()["action"]["id"]
            self.cli(
                "history",
                "--action",
                review_action,
                "--limit",
                "10",
                "--skip",
                "0",
                "--full",
            )
            material = material_first and number == 1
            finding_id = f"OBJ-{kind}-{number}"
            review_learning = f"Objective review {finding_id} read the current full Git history."
            self.complete(
                {
                    "summary": "The bounded objective has a complete current review.",
                    "findings": [
                        {
                            "id": finding_id,
                            "severity": "material" if material else "trivial",
                            "category": "other",
                            "summary": "The fixture keeps each objective outcome and evidence explicit.",
                        }
                    ],
                    "assessment": {
                        key: f"Reviewed {key} against the durable {kind} candidate."
                        for key in objectives.ASSESSMENT_KEYS
                    },
                    "history_assessment": "The current complete Git bodies were read before this objective decision.",
                    "test_review": "A candidate-bound lint and acceptance check remains required.",
                    "learnings": review_learning,
                },
                action_id=review_action,
                label=f"{label}-objective-{number}-review",
            )
            self.assertEqual(self.state()["stage"], "objective-plan")
            plan_learning = f"Objective plan {finding_id} retains the bounded candidate."
            self.complete(
                {
                    "summary": "The plan addresses the complete objective finding set.",
                    "addresses": [finding_id],
                    "body": f"# {kind} objective plan\n\nAddress {finding_id} without changing product files.\n",
                    "learnings": plan_learning,
                },
                label=f"{label}-objective-{number}-plan",
            )
            self.assertEqual(self.state()["stage"], "objective-apply")
            apply_learning = f"Objective apply {finding_id} preserves the complete original-stage result."
            self.complete(
                {
                    "summary": "The complete original-stage candidate resolves the bounded finding.",
                    "candidate": current_candidate,
                    "material": material,
                    "addresses": [finding_id],
                    "resolutions": [
                        {
                            "id": finding_id,
                            "evidence": "The candidate retains its stated outcome and candidate-bound check.",
                        }
                    ],
                    "test_changes": "The candidate acceptance check remains active.",
                    "learnings": apply_learning,
                },
                label=f"{label}-objective-{number}-apply",
            )
            self.assertEqual(self.state()["stage"], "objective-verify")
            verify_action = self.state()["action"]["id"]
            self.cli(
                "planning-verify",
                "--action",
                verify_action,
                "--manifest",
                self.record(
                    f"{label}-objective-{number}-checks", self.objective_manifest(kind)
                ),
            )
            self.complete(
                {"summary": "Fresh objective lint and candidate checks passed."},
                action_id=verify_action,
                label=f"{label}-objective-{number}-verify",
            )
            self.assertEqual(self.state()["stage"], "objective-commit")
            commit_action = self.state()["action"]["id"]
            commit = self.objective_audit_commit(kind)
            self.complete(
                {
                    "summary": "An audit-only commit records review, plan, apply, and validation learnings.",
                    "commit": commit,
                },
                action_id=commit_action,
                label=f"{label}-objective-{number}-commit",
            )
        self.assertEqual(self.state()["stage"], "objective-finalize")
        final_action = self.state()["action"]["id"]
        self.cli(
            "planning-verify",
            "--action",
            final_action,
            "--manifest",
            self.record(f"{label}-objective-final-checks", self.objective_manifest(kind)),
        )
        final_process, _ = self.complete(
            {"summary": "Fresh final objective checks passed after the required trivial passes."},
            action_id=final_action,
            code=final_code,
            label=f"{label}-objective-finalize",
        )
        self.last_objective_final = final_process
        return current_candidate

    def paged_context(self, section: str, *, limit: int = 40) -> tuple[str, int]:
        """Read an advertised context selector through its public continuation."""
        output = self.cli(
            "context", "--section", section, "--offset", "0", "--limit", str(limit)
        ).stdout
        pages = [output]
        digest_match = re.search(rf"Context {re.escape(section)}; digest ([0-9a-f]+)", output)
        self.assertIsNotNone(digest_match, output)
        digest = digest_match.group(1)
        while continuation := re.search(r"Continue: --offset (\d+)", output):
            output = self.cli(
                "context",
                "--section",
                section,
                "--offset",
                continuation.group(1),
                "--limit",
                str(limit),
                "--digest",
                digest,
            ).stdout
            pages.append(output)
        return "\n".join(pages), len(pages)

    def begin_iteration(
        self,
        kind: str,
        *,
        finding_id: str,
        material: bool,
        candidate_body: str | None = None,
        research_state: dict | None = None,
        stop_at: str = "verify",
    ) -> tuple[str, str]:
        """Run review/plan/apply with a current result, optionally stop before verify."""
        self.assert_cursor("validate-spec", f"{kind}-review")
        self.history()
        review_learning = f"Review {finding_id} before changing the {kind} candidate."
        review = {
            "summary": f"Review records {finding_id} and every required rubric dimension.",
            "findings": [
                {
                    "id": finding_id,
                    "severity": "material" if material else "trivial",
                    "summary": f"{finding_id} fixture planning finding",
                }
            ],
            "test_review": "The planning manifest will assert the durable candidate, not a future product test.",
            "learnings": review_learning,
        }
        review["coverage_review"] = self.coverage_review(kind)
        self.complete(review, label=f"{kind}-{finding_id}-review")
        self.assert_cursor("validate-spec", f"{kind}-plan")
        self.complete(
            {
                "summary": f"The plan addresses the open finding {finding_id}.",
                "body": f"# {kind} improvement\n\nAddress {finding_id} without weakening the planning check.\n",
                "addresses": [finding_id],
            },
            label=f"{kind}-{finding_id}-plan",
        )
        self.assert_cursor("validate-spec", f"{kind}-apply")
        apply_learning = f"Apply {finding_id} with a complete candidate replacement and retain its test mapping."
        payload = {
            "summary": f"The replacement candidate resolves {finding_id}.",
            "body": candidate_body
            if candidate_body is not None
            else (
                self.research_body(finding_id)
                if kind == "research"
                else (
                self.behavior_body(finding_id)
                if kind == "behavior"
                else self.spec_body(finding_id)
                )
            ),
            "material": material,
            "resolutions": [{"id": finding_id, "evidence": f"Candidate revision records {finding_id}."}],
            "test_changes": "The candidate assertion continues to cover the planning artifact.",
            "learnings": apply_learning,
        }
        if kind == "research":
            payload["research_state"] = research_state or self.research_state(finding_id)
        elif kind == "spec":
            payload["lifecycle"] = self.lifecycle()
        self.complete(payload, label=f"{kind}-{finding_id}-apply")
        self.assert_cursor("validate-spec", f"{kind}-verify")
        return review_learning, apply_learning

    def planning_manifest(self, kind: str, *, failure: bool = False, mutate: bool = False) -> dict:
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
        if failure:
            test = "raise SystemExit(1)"
        elif mutate:
            test = "from pathlib import Path; Path('planning-check-mutated.txt').write_text('changed\\n')"
        elif kind == "research":
            test = (
                "from pathlib import Path; "
                "research = Path('.shiploop/research.md').read_text(); "
                "evidence = Path('.shiploop/research-evidence.md').read_text(); "
                "assert 'RQ-001' in research; assert 'SRC-LOCAL-001' in evidence"
            )
        else:
            test = (
                "from pathlib import Path; "
                f"text = Path('.shiploop/{candidate}').read_text(); "
                "assert 'T-01' in text; assert 'Test mapping' in text or 'Test mapping' in text"
            )
        return {
            "checks": [
                {
                    "id": "planning-lint",
                    "kind": "lint",
                    "argv": [sys.executable, "-B", "-c", "raise SystemExit(0)"],
                    "acceptance": [],
                },
                {
                    "id": f"{kind}-candidate",
                    "kind": "test",
                    "argv": [sys.executable, "-B", "-c", test],
                    "acceptance": [acceptance],
                },
            ]
        }

    def verify_iteration(
        self,
        kind: str,
        *,
        code: int = 0,
        label: str = "checks",
        reason: str = "",
    ) -> None:
        self.assert_cursor("validate-spec", f"{kind}-verify")
        args = [
            "planning-verify",
            "--action",
            self.state()["action"]["id"],
            "--manifest",
            self.record(label, self.planning_manifest(kind)),
        ]
        if reason:
            args.extend(["--reason", reason])
        self.cli(*args, code=code)

    def iteration_id(self, kind: str) -> str:
        current = self.planning(kind)["current_iteration"]
        self.assertIsInstance(current, dict)
        self.assertIsInstance(current.get("id"), str)
        return current["id"]

    def audit_message(self, kind: str, review_learning: str, apply_learning: str) -> str:
        iteration = self.iteration_id(kind)
        return "\n".join(
            [
                f"Planning {kind} iteration {iteration}",
                "",
                "Review:",
                "Read current Git history and the durable planning finding ledger.",
                "",
                "Changes:",
                "Recorded the audit-only planning iteration without product-tree changes.",
                "",
                "Validation:",
                "Fresh candidate-bound planning lint and test evidence passed.",
                "",
                "Key learnings:",
                review_learning,
                apply_learning,
                "",
                f"ShipLoop-Iteration: {iteration}",
            ]
        )

    def audit_commit(
        self, kind: str, review_learning: str, apply_learning: str, *, change_tree: bool = False
    ) -> str:
        if change_tree:
            (self.repo / "planning-tree-drift.txt").write_text("drift\n", encoding="utf-8")
            self.git("add", "planning-tree-drift.txt")
        args = ["commit", "--allow-empty"]
        if not change_tree:
            args.append("--only")
        args.extend(["-m", self.audit_message(kind, review_learning, apply_learning)])
        self.git(*args)
        return self.git("rev-parse", "HEAD")

    def finish_iteration(self, kind: str, review_learning: str, apply_learning: str) -> None:
        self.verify_iteration(kind, label=f"{kind}-checks")
        check_action = self.state()["action"]["id"]
        self.complete(
            {"summary": "Fresh planning lint and candidate assertions passed."},
            action_id=check_action,
            label=f"{kind}-verify-result",
        )
        self.assert_cursor("validate-spec", f"{kind}-commit")
        sha = self.audit_commit(kind, review_learning, apply_learning)
        self.complete(
            {"summary": "A distinct audit-only learning commit records the planning pass.", "commit": sha},
            label=f"{kind}-commit-result",
        )

    def run_iteration(
        self,
        kind: str,
        finding_id: str,
        *,
        material: bool,
        candidate_body: str | None = None,
        research_state: dict | None = None,
    ) -> None:
        review_learning, apply_learning = self.begin_iteration(
            kind,
            finding_id=finding_id,
            material=material,
            candidate_body=candidate_body,
            research_state=research_state,
        )
        self.finish_iteration(kind, review_learning, apply_learning)

    def finalize(self, kind: str) -> None:
        self.assert_cursor("validate-spec", f"{kind}-finalize")
        action = self.state()["action"]["id"]
        self.cli(
            "planning-verify",
            "--action",
            action,
            "--manifest",
            self.record(f"{kind}-final-checks", self.planning_manifest(kind)),
        )
        self.complete(
            {"summary": "Fresh checks passed for the unchanged final planning candidate."},
            action_id=action,
            label=f"{kind}-finalize-result",
        )

    def converge_research(self) -> None:
        self.start_candidate("research")
        self.run_iteration("research", "R-T-01", material=False)
        self.assertEqual(self.planning("research")["streak"], 1)
        self.run_iteration("research", "R-T-02", material=False)
        self.assert_cursor("validate-spec", "research-finalize")
        self.assertEqual(self.planning("research")["streak"], 2)
        self.finalize("research")

    def test_real_cli_converges_research_then_behavior_and_spec_before_sequence(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-M-01", material=True)
        self.assert_cursor("validate-spec", "behavior-review")
        self.assertEqual(self.planning("behavior")["streak"], 0)
        self.run_iteration("behavior", "B-T-01", material=False)
        self.assert_cursor("validate-spec", "behavior-review")
        self.assertEqual(self.planning("behavior")["streak"], 1)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.assert_cursor("validate-spec", "behavior-finalize")
        self.assertEqual(self.planning("behavior")["streak"], 2)
        self.finalize("behavior")
        self.assert_cursor("validate-spec", "spec")
        self.assertTrue((self.run_dir / "behavior.md").is_file())

        self.start_candidate("spec")
        self.run_iteration("spec", "S-T-01", material=False)
        self.assert_cursor("validate-spec", "spec-review")
        self.run_iteration("spec", "S-T-02", material=False)
        self.assert_cursor("validate-spec", "spec-finalize")
        self.finalize("spec")
        self.assert_cursor("plan", "sequence")
        self.assertTrue((self.run_dir / "spec.md").is_file())
        self.assertTrue((self.run_dir / "lifecycle.md").is_file())
        for kind in ("research", "behavior", "spec"):
            receipt = self.planning(kind)
            self.assertEqual(receipt["version"], 2)
            self.assertEqual(receipt["kind"], kind)
            self.assertTrue(receipt["candidate_sha256"])
            self.assertTrue(receipt["candidate_components"])
            self.assertEqual(receipt["streak"], 2)
            self.assertFalse(
                [row for row in receipt["findings"] if row.get("status") == "open"]
            )
            self.assertTrue(receipt["completed_iterations"])
            self.assertTrue((self.run_dir / "planning" / f"{kind}-certificate.md").is_file())
        state = self.state()
        self.assertTrue(state["research_sha256"])
        self.assertTrue(state["research_certificate_sha256"])
        self.assertTrue(state["research_as_of"])
        self.assertTrue(self.planning("behavior")["research_binding"])
        self.assertTrue(self.planning("spec")["research_binding"])

    def test_research_requires_typed_sources_before_entering_its_loop(self) -> None:
        self.bootstrap_to_research()
        rejected, _ = self.complete(
            {
                "summary": "The historical one-shot research result has no typed evidence.",
                "body": self.research_body("missing-state"),
            },
            code=2,
            label="research-missing-state",
        )
        self.assertIn("research_state", rejected.stderr)
        self.assert_cursor("validate-spec", "research")

        missing_freshness = self.research_state()
        missing_freshness["sources"][0].pop("version_or_observed_at")
        rejected, _ = self.complete(
            {
                "summary": "The source omits the required freshness record.",
                "body": self.research_body("missing-freshness"),
                "research_state": missing_freshness,
            },
            code=2,
            label="research-missing-freshness",
        )
        self.assertIn("research source", rejected.stderr)
        self.assert_cursor("validate-spec", "research")

        initial = {
            "summary": "The typed research candidate records local source evidence.",
            "body": self.research_body(),
            "research_state": self.research_state(),
        }
        initial_action = self.state()["action"]["id"]
        _, initial_result = self.complete(initial, label="research-initial")
        self.assert_cursor("validate-spec", "research-review")
        # A successful result remains safely replayable after a cold restart.
        self.cli("complete", "--action", initial_action, "--result", initial_result)
        receipt = self.planning("research")
        self.assertEqual(receipt["version"], 2)
        self.assertEqual(receipt["kind"], "research")
        self.assertTrue(receipt["candidate_sha256"])
        self.assertIn("research.md", receipt["candidate_components"])
        self.assertIn("research-evidence.md", receipt["candidate_components"])
        self.assertTrue((self.run_dir / "research-evidence.md").is_file())
        cold = self.cli(
            "context", "--section", "research", "--offset", "0", "--limit", "4000"
        ).stdout
        self.assertIn("RQ-001", cold)
        packet = self.cli("next").stdout
        self.assertIn("research-evidence", packet)
        evidence_context, evidence_pages = self.paged_context("research-evidence")
        self.assertGreater(evidence_pages, 1)
        self.assertIn("SRC-LOCAL-001", evidence_context)
        self.assertIn("version_or_observed_at", evidence_context)
        planning_context = self.cli(
            "context", "--section", "planning", "--offset", "0", "--limit", "4000"
        ).stdout
        self.assertIn("SRC-LOCAL-001", planning_context)

        self.begin_iteration("research", finding_id="R-T-STALE", material=False)
        self.verify_iteration("research", label="research-stale-check")
        check_action = self.state()["action"]["id"]
        evidence_path = self.run_dir / "research-evidence.md"
        evidence_bytes = evidence_path.read_bytes()
        evidence_path.write_bytes(evidence_bytes + b"\nOut-of-band stale evidence.\n")
        rejected, _ = self.complete(
            {"summary": "Stale research check evidence cannot certify a changed candidate."},
            action_id=check_action,
            code=2,
            label="research-stale-evidence",
        )
        self.assertIn("planning candidate changed outside", rejected.stderr)
        evidence_path.write_bytes(evidence_bytes)

    def test_research_apply_retains_question_inventory_and_material_deltas_reset(self) -> None:
        self.bootstrap_to_research()
        initial_state = self.research_state(include_follow_up=True)
        self.complete(
            {
                "summary": "Two typed research questions start the local candidate.",
                "body": self.research_body("two-questions"),
                "research_state": initial_state,
            },
            label="research-two-questions",
        )
        self.history()
        self.complete(
            {
                "summary": "The review opens a trivial research wording finding.",
                "findings": [
                    {
                        "id": "R-T-OMIT",
                        "severity": "trivial",
                        "summary": "Retain every prior research question.",
                    }
                ],
                "coverage_review": self.coverage_review("research"),
                "test_review": "The research candidate check covers the report and typed evidence.",
                "learnings": "Question identifiers remain durable across research applies.",
            },
            label="research-omit-review",
        )
        self.complete(
            {
                "summary": "The plan addresses the retained research question inventory.",
                "body": "# Research plan\n\nKeep both question records.\n",
                "addresses": ["R-T-OMIT"],
            },
            label="research-omit-plan",
        )
        rejected, _ = self.complete(
            {
                "summary": "This apply illegally omits RQ-002.",
                "body": self.research_body("omitted-question"),
                "research_state": self.research_state("omitted-question"),
                "material": False,
                "resolutions": [
                    {"id": "R-T-OMIT", "evidence": "The report was updated."}
                ],
                "test_changes": "The typed research check remains active.",
                "learnings": "Omission must fail before a research candidate is replaced.",
            },
            code=2,
            label="research-omitted-question",
        )
        self.assertIn("cannot remove prior questions", rejected.stderr)
        self.assert_cursor("validate-spec", "research-apply")

        retained = self.research_state("source-refresh", include_follow_up=True)
        self.complete(
            {
                "summary": "The apply keeps every question and only refreshes source freshness.",
                "body": self.research_body("source-refresh"),
                "research_state": retained,
                "material": False,
                "resolutions": [
                    {"id": "R-T-OMIT", "evidence": "Both durable question IDs remain in evidence."}
                ],
                "test_changes": "The typed research check remains active.",
                "learnings": "A source freshness refresh preserves stable question evidence.",
            },
            label="research-retained-questions",
        )
        self.finish_iteration(
            "research",
            "Question identifiers remain durable across research applies.",
            "A source freshness refresh preserves stable question evidence.",
        )
        self.assertEqual(self.planning("research")["streak"], 1)

        changed = self.research_state(
            "new-conclusion",
            include_follow_up=True,
            answer="A new conclusion changes the required local exact-output contract.",
        )
        self.run_iteration(
            "research",
            "R-T-MATERIAL",
            material=False,
            candidate_body=self.research_body("new-conclusion"),
            research_state=changed,
        )
        receipt = self.planning("research")
        self.assertEqual(receipt["streak"], 0)
        self.assertEqual(receipt["completed_iterations"][-1]["outcome"], "material")

    def test_open_then_blocked_research_questions_cannot_reach_finalization(self) -> None:
        self.bootstrap_to_research()
        self.complete(
            {
                "summary": "The first question remains open until the local probe is reviewed.",
                "body": self.research_body("open"),
                "research_state": self.research_state("open", status="open"),
            },
            label="research-open-initial",
        )
        blocked = self.research_state("blocked", status="blocked")
        self.run_iteration(
            "research",
            "R-M-OPEN",
            material=False,
            candidate_body=self.research_body("blocked"),
            research_state=blocked,
        )
        self.run_iteration(
            "research",
            "R-M-BLOCKED",
            material=False,
            candidate_body=self.research_body("blocked-repeat"),
            research_state=blocked,
        )
        receipt = self.planning("research")
        self.assertEqual(receipt["research_state"]["questions"][0]["status"], "blocked")
        self.assertEqual(receipt["streak"], 0)
        self.assert_cursor("validate-spec", "research-review")

    def test_material_after_trivial_resets_planning_streak(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.assertEqual(self.planning("behavior")["streak"], 1)
        self.run_iteration("behavior", "B-M-02", material=True)
        self.assert_cursor("validate-spec", "behavior-review")
        self.assertEqual(self.planning("behavior")["streak"], 0)
        self.run_iteration("behavior", "B-T-03", material=False)
        self.assertEqual(self.planning("behavior")["streak"], 1)
        self.run_iteration("behavior", "B-T-04", material=False)
        self.assert_cursor("validate-spec", "behavior-finalize")
        self.assertEqual(self.planning("behavior")["streak"], 2)

    def test_candidate_identity_binds_literal_crlf_bytes_and_rejects_newline_drift(self) -> None:
        self.bootstrap_to_behavior()
        self.assert_cursor("validate-spec", "behavior")
        imported = self.behavior_body("crlf-import").strip().replace("\n", "\r\n")
        self.complete(
            {
                "summary": "The imported behavior candidate deliberately retains CRLF bytes.",
                "body": imported,
            },
            label="crlf-behavior-initial",
        )
        candidate_path = self.run_dir / "behavior.md"
        self.assertEqual(candidate_path.read_bytes(), imported.encode("utf-8"))
        receipt = self.planning("behavior")
        self.assertEqual(
            receipt["candidate_components"]["behavior.md"],
            hashlib.sha256(imported.encode("utf-8")).hexdigest(),
        )

        # Completing review reads the durable candidate through the public protocol;
        # it must still match the CRLF digest minted during import.
        self.begin_iteration("behavior", finding_id="B-T-01", material=False)
        self.verify_iteration("behavior", label="lf-candidate-check")
        check_action = self.state()["action"]["id"]
        self.assertTrue(
            store.read_record(self.run_dir / "checks" / f"{check_action}.md")["planning_passed"]
        )

        lf_bytes = candidate_path.read_bytes()
        self.assertNotIn(b"\r\n", lf_bytes)
        crlf_bytes = lf_bytes.replace(b"\n", b"\r\n")
        self.assertNotEqual(crlf_bytes, lf_bytes)
        candidate_path.write_bytes(crlf_bytes)
        blocked, _ = self.complete(
            {"summary": "Attempt to certify checks after an out-of-band newline rewrite."},
            action_id=check_action,
            code=2,
            label="crlf-candidate-drift",
        )
        self.assertIn("planning candidate changed outside", blocked.stderr)
        self.assert_cursor("validate-spec", "behavior-verify")

    def test_spec_finalization_promotes_literal_crlf_candidate_bytes(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.finalize("behavior")

        self.start_candidate("spec")
        self.run_iteration("spec", "S-T-01", material=False)
        crlf_spec = self.spec_body("crlf-final").strip().replace("\n", "\r\n")
        review_learning, apply_learning = self.begin_iteration(
            "spec",
            finding_id="S-T-02",
            material=False,
            candidate_body=crlf_spec,
        )
        self.finish_iteration("spec", review_learning, apply_learning)
        self.assert_cursor("validate-spec", "spec-finalize")
        self.assertEqual(
            (self.run_dir / "spec-draft.md").read_bytes(), crlf_spec.encode("utf-8")
        )
        self.finalize("spec")
        self.assert_cursor("plan", "sequence")
        self.assertEqual(
            (self.run_dir / "spec.md").read_bytes(), crlf_spec.encode("utf-8")
        )
        self.assertEqual(
            self.state()["spec_sha256"], hashlib.sha256(crlf_spec.encode("utf-8")).hexdigest()
        )

    def test_review_plan_and_apply_preserve_open_findings_and_refuse_bad_results(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.history()
        incomplete = self.coverage_review("behavior")
        incomplete.pop("edge_conditions")
        self.complete(
            {
                "summary": "This review is intentionally incomplete.",
                "findings": [{"id": "B-M-01", "severity": "material", "summary": "Missing edge review"}],
                "coverage_review": incomplete,
                "test_review": "Not sufficient while a required rubric dimension is missing.",
                "learnings": "Coverage must enumerate every dimension.",
            },
            code=2,
            label="incomplete-rubric",
        )
        self.assert_cursor("validate-spec", "behavior-review")

        self.history()
        self.complete(
            {
                "summary": "The full review records two material findings.",
                "findings": [
                    {"id": "B-M-01", "severity": "material", "summary": "Missing edge review"},
                    {"id": "B-M-02", "severity": "material", "summary": "Open transition recovery review"},
                ],
                "coverage_review": self.coverage_review("behavior"),
                "test_review": "The planning check will cover the durable candidate.",
                "learnings": "An open material finding must remain addressable.",
            },
            label="complete-rubric",
        )
        self.assert_cursor("validate-spec", "behavior-plan")
        self.complete(
            {"summary": "The plan omits its open finding." , "body": "# Incomplete plan\n"},
            code=2,
            label="missing-address",
        )
        self.complete(
            {
                "summary": "The plan addresses every open finding.",
                "body": "# Complete plan\n",
                "addresses": ["B-M-01", "B-M-02"],
            },
            label="complete-address",
        )
        self.assert_cursor("validate-spec", "behavior-apply")
        self.complete(
            {
                "summary": "The apply result tries to resolve an unknown finding.",
                "body": self.behavior_body("bad-resolution"),
                "material": True,
                "resolutions": [{"id": "unknown", "evidence": "not in the ledger"}],
                "test_changes": "No check was removed.",
                "learnings": "Unknown resolutions are invalid.",
            },
            code=2,
            label="unknown-resolution",
        )
        self.complete(
            {
                "summary": "The apply result resolves only one recorded finding.",
                "body": self.behavior_body("resolved"),
                "material": True,
                "resolutions": [{"id": "B-M-01", "evidence": "The replacement includes the edge condition."}],
                "test_changes": "The planning candidate check remains active.",
                "learnings": "Use stable ledger IDs for resolutions and retain unresolved findings.",
            },
            label="known-resolution",
        )
        self.assert_cursor("validate-spec", "behavior-verify")
        self.verify_iteration("behavior", label="open-finding-check")
        self.complete(
            {"summary": "Fresh candidate-bound planning checks passed."},
            label="open-finding-verify",
        )
        self.assert_cursor("validate-spec", "behavior-commit")
        commit = self.audit_commit(
            "behavior",
            "An open material finding must remain addressable.",
            "Use stable ledger IDs for resolutions and retain unresolved findings.",
        )
        self.complete(
            {"summary": "The audit records a pass that still has an open finding.", "commit": commit},
            label="open-finding-commit",
        )
        self.assert_cursor("validate-spec", "behavior-review")
        self.history()
        self.complete(
            {
                "summary": "An omitted old finding remains open in the stable ledger.",
                "findings": [],
                "coverage_review": self.coverage_review("behavior"),
                "test_review": "The candidate check remains active while B-M-02 is unresolved.",
                "learnings": "Omission from a later review cannot close a prior finding.",
            },
            label="omitted-open-finding",
        )
        receipt = self.planning("behavior")
        remaining = {row["id"]: row["status"] for row in receipt["findings"]}
        self.assertEqual(remaining["B-M-02"], "open")
        self.assertEqual(receipt["streak"], 0)

        review_learning = "Omission from a later review cannot close a prior finding."
        apply_learning = (
            "Retain the ledger severity through apply so a host cannot classify this "
            "resolution as trivial."
        )
        self.assert_cursor("validate-spec", "behavior-plan")
        self.complete(
            {
                "summary": "The follow-up plan addresses the retained material finding.",
                "body": "# Resolve retained material finding\n\nAddress B-M-02 with durable evidence.\n",
                "addresses": ["B-M-02"],
            },
            label="carryover-material-plan",
        )
        self.complete(
            {
                "summary": "The replacement resolves the carried-forward material finding.",
                "body": self.behavior_body("carryover-material-resolution"),
                "material": False,
                "resolutions": [
                    {
                        "id": "B-M-02",
                        "evidence": "The replacement retains the transition recovery condition.",
                    }
                ],
                "test_changes": "The candidate-bound planning assertion remains active.",
                "learnings": apply_learning,
            },
            label="carryover-material-apply",
        )
        self.verify_iteration("behavior", label="carryover-material-check")
        self.complete(
            {"summary": "Fresh planning lint and candidate assertions passed."},
            label="carryover-material-verify",
        )
        self.assert_cursor("validate-spec", "behavior-commit")
        commit = self.audit_commit("behavior", review_learning, apply_learning)
        self.complete(
            {
                "summary": "The audit records resolution of the carried-forward material finding.",
                "commit": commit,
            },
            label="carryover-material-commit",
        )
        receipt = self.planning("behavior")
        self.assertEqual(receipt["streak"], 0)
        self.assertEqual(receipt["completed_iterations"][-1]["outcome"], "material")
        self.assert_cursor("validate-spec", "behavior-review")

    def test_planning_verify_is_artifact_bound_and_rejects_failed_stale_or_mutating_checks(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.begin_iteration("behavior", finding_id="B-T-01", material=False)
        action = self.state()["action"]["id"]
        self.cli(
            "planning-verify",
            "--action",
            action,
            "--manifest",
            self.record("failed-check", self.planning_manifest("behavior", failure=True)),
            code=2,
        )
        self.complete({"summary": "A failed planning check cannot certify this candidate."}, code=2, label="failed-claim")

        self.cli(
            "planning-verify",
            "--action",
            action,
            "--manifest",
            self.record("mutating-check", self.planning_manifest("behavior", mutate=True)),
            "--reason",
            "Exercise mutation detection with a deliberately different fixture manifest.",
            code=2,
        )
        changed = self.repo / "planning-check-mutated.txt"
        self.assertTrue(changed.exists())
        changed.unlink()

        self.verify_iteration(
            "behavior",
            label="good-check",
            reason="Restore the valid candidate assertion after the deliberate mutation check.",
        )
        candidate = self.run_dir / "behavior.md"
        original = candidate.read_text(encoding="utf-8")
        candidate.write_text(original + "\nOut-of-band mutation.\n", encoding="utf-8")
        self.complete({"summary": "The stale evidence is intentionally rejected."}, code=2, label="stale-candidate")
        candidate.write_text(original, encoding="utf-8")
        self.verify_iteration(
            "behavior",
            label="fresh-after-restore",
            reason="Record fresh valid evidence after restoring the candidate bytes.",
        )
        self.complete({"summary": "Fresh candidate-bound planning checks passed."}, label="fresh-claim")
        self.assert_cursor("validate-spec", "behavior-commit")
        self.cli(
            "planning-verify",
            "--action",
            action,
            "--manifest",
            self.record("replayed-check", self.planning_manifest("behavior")),
            code=2,
        )

    def test_finalization_cannot_replace_checked_candidate(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.assert_cursor("validate-spec", "behavior-finalize")
        action = self.state()["action"]["id"]
        self.cli(
            "planning-verify",
            "--action",
            action,
            "--manifest",
            self.record("final-checks", self.planning_manifest("behavior")),
        )
        candidate = self.run_dir / "behavior.md"
        original = candidate.read_text(encoding="utf-8")
        self.complete(
            {"summary": "Attempt to replace the checked candidate.", "body": self.behavior_body("replacement")},
            action_id=action,
            code=2,
            label="replacement-finalize",
        )
        self.assertEqual(candidate.read_text(encoding="utf-8"), original)
        self.assert_cursor("validate-spec", "behavior-finalize")
        self.complete(
            {"summary": "The checked candidate is frozen without replacement."},
            action_id=action,
            label="proper-finalize",
        )
        self.assert_cursor("validate-spec", "spec")

    def test_missing_behavior_certificate_blocks_spec_authoring(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.finalize("behavior")
        self.assert_cursor("validate-spec", "spec")
        certificate = self.run_dir / "planning" / "behavior-certificate.md"
        self.assertTrue(certificate.is_file())
        certificate.unlink()
        blocked, _ = self.complete(
            {
                "summary": "Attempt to author a specification without the frozen behavior proof.",
                "body": self.spec_body("missing-certificate"),
                "lifecycle": self.lifecycle(),
            },
            code=2,
            label="missing-behavior-certificate",
        )
        self.assertIn("certificate", blocked.stderr)
        self.assert_cursor("validate-spec", "spec")

    def test_corrupt_spec_certificate_blocks_downstream_sequence(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.finalize("behavior")
        self.start_candidate("spec")
        self.run_iteration("spec", "S-T-01", material=False)
        self.run_iteration("spec", "S-T-02", material=False)
        self.finalize("spec")
        self.assert_cursor("plan", "sequence")
        certificate = self.run_dir / "planning" / "spec-certificate.md"
        certificate.write_text("corrupt planning certificate\n", encoding="utf-8")
        before_state = (self.run_dir / "state.md").read_bytes()
        blocked = self.cli("next", code=2)
        self.assertRegex(blocked.stderr, r"certificate|shiploop-state fence")
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before_state)
        self.assert_cursor("plan", "sequence")

    def test_behavior_finalization_identity_drift_blocks_initial_spec(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.finalize("behavior")
        self.assert_cursor("validate-spec", "spec")
        (self.repo / "after-behavior-finalization.txt").write_text("drift\n", encoding="utf-8")
        self.git("add", "after-behavior-finalization.txt")
        self.git("commit", "-m", "Drift after behavior finalization")
        blocked, _ = self.complete(
            {
                "summary": "Attempt to author the initial specification after behavior identity drift.",
                "body": self.spec_body("drift"),
                "lifecycle": self.lifecycle(),
            },
            code=2,
            label="behavior-finalization-drift",
        )
        self.assertIn("after finalization", blocked.stderr)
        self.assert_cursor("validate-spec", "spec")

    def test_research_certificate_drift_blocks_behavior_spec_and_sequence(self) -> None:
        self.bootstrap_to_behavior()
        certificate = self.run_dir / "planning" / "research-certificate.md"
        pristine = certificate.read_bytes()
        certificate.write_bytes(pristine + b"\nresearch certificate drift\n")
        blocked, _ = self.complete(
            {
                "summary": "Attempt to author behavior against drifted research evidence.",
                "body": self.behavior_body("research-drift"),
            },
            code=2,
            label="research-drift-behavior",
        )
        self.assertIn("research certificate hash drift", blocked.stderr)
        self.assert_cursor("validate-spec", "behavior")
        certificate.write_bytes(pristine)

        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-RESEARCH-01", material=False)
        self.run_iteration("behavior", "B-T-RESEARCH-02", material=False)
        self.finalize("behavior")
        certificate.write_bytes(pristine + b"\nresearch certificate drift\n")
        blocked, _ = self.complete(
            {
                "summary": "Attempt to author specification against drifted research evidence.",
                "body": self.spec_body("research-drift"),
                "lifecycle": self.lifecycle(),
            },
            code=2,
            label="research-drift-spec",
        )
        self.assertIn("research certificate hash drift", blocked.stderr)
        self.assert_cursor("validate-spec", "spec")
        certificate.write_bytes(pristine)

        self.start_candidate("spec")
        self.run_iteration("spec", "S-T-RESEARCH-01", material=False)
        self.run_iteration("spec", "S-T-RESEARCH-02", material=False)
        self.finalize("spec")
        certificate.write_bytes(pristine + b"\nresearch certificate drift\n")
        blocked, _ = self.complete(
            self.sequence_payload(),
            code=2,
            label="research-drift-sequence",
        )
        self.assertIn("research certificate hash drift", blocked.stderr)
        self.assert_cursor("plan", "sequence")

    def test_revisit_research_preserves_survey_and_archives_downstream_candidates(self) -> None:
        self.bootstrap_to_behavior()
        survey = (self.run_dir / "environment.md").read_bytes()
        self.start_candidate("behavior")
        revisit_action = self.state()["action"]["id"]
        self.cli(
            "revisit",
            "--action",
            revisit_action,
            "--to",
            "research",
            "--reason",
            "The survey remains valid but the research conclusions must be rechecked.",
        )
        self.assert_cursor("validate-spec", "research")
        self.assertEqual((self.run_dir / "environment.md").read_bytes(), survey)
        archive = Path(self.state()["previous_planning"])
        for path in (
            "research.md",
            "research-evidence.md",
            "behavior.md",
            "planning/research.md",
            "planning/research-certificate.md",
            "planning/behavior.md",
        ):
            self.assertTrue((archive / path).is_file(), path)
        self.assertFalse((self.run_dir / "research.md").exists())
        self.assertFalse((self.run_dir / "research-evidence.md").exists())
        self.assertFalse((self.run_dir / "behavior.md").exists())

    def test_spec_finalization_identity_drift_blocks_initial_sequence(self) -> None:
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        self.run_iteration("behavior", "B-T-01", material=False)
        self.run_iteration("behavior", "B-T-02", material=False)
        self.finalize("behavior")
        self.start_candidate("spec")
        self.run_iteration("spec", "S-T-01", material=False)
        self.run_iteration("spec", "S-T-02", material=False)
        self.finalize("spec")
        self.assert_cursor("plan", "sequence")
        (self.repo / "after-spec-finalization.txt").write_text("drift\n", encoding="utf-8")
        self.git("add", "after-spec-finalization.txt")
        self.git("commit", "-m", "Drift after specification finalization")
        self.converge_objective(
            self.sequence_payload(),
            label="sequence",
            final_code=2,
        )
        self.assertIn(
            "sequence objective audit chain does not start at the certified spec proof",
            self.last_objective_final.stderr,
        )
        self.assert_cursor("plan", "objective-finalize")

    def test_audit_only_commit_preserves_unrelated_staged_files(self) -> None:
        self.bootstrap_to_research()
        (self.repo / "unrelated-staged.txt").write_text("preserve\n", encoding="utf-8")
        self.git("add", "unrelated-staged.txt")
        staged_before = self.git("diff", "--cached", "--name-only")
        self.converge_research()
        self.assert_cursor("validate-spec", "behavior")
        self.start_candidate("behavior")
        review_learning, apply_learning = self.begin_iteration(
            "behavior", finding_id="B-T-01", material=False
        )
        self.verify_iteration("behavior", label="audit-check")
        self.complete({"summary": "Fresh candidate-bound planning checks passed."}, label="audit-verify")
        self.assert_cursor("validate-spec", "behavior-commit")
        tree_before = self.git("rev-parse", "HEAD^{tree}")
        sha = self.audit_commit("behavior", review_learning, apply_learning)
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}"), tree_before)
        self.assertEqual(self.git("diff", "--cached", "--name-only"), staged_before)
        self.complete(
            {"summary": "The audit-only commit did not consume unrelated staged work.", "commit": sha},
            label="audit-commit",
        )
        self.assert_cursor("validate-spec", "behavior-review")

    def test_audit_commit_rejects_product_tree_drift(self) -> None:
        """A structurally valid message cannot bless a product-tree mutation."""
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        review_learning, apply_learning = self.begin_iteration(
            "behavior", finding_id="B-T-02", material=False
        )
        self.verify_iteration("behavior", label="tree-drift-check")
        self.complete({"summary": "Fresh candidate-bound planning checks passed."}, label="tree-drift-verify")
        self.assert_cursor("validate-spec", "behavior-commit")
        bad_sha = self.audit_commit(
            "behavior", review_learning, apply_learning, change_tree=True
        )
        self.complete(
            {"summary": "Attempt to count a tree-changing planning audit.", "commit": bad_sha},
            code=2,
            label="tree-drift-commit",
        )
        self.assert_cursor("validate-spec", "behavior-commit")

    def test_audit_commit_rejects_tree_identical_merge_commit(self) -> None:
        """The audit must be a single-parent commit, not a tree-identical merge."""
        self.bootstrap_to_behavior()
        self.start_candidate("behavior")
        review_learning, apply_learning = self.begin_iteration(
            "behavior", finding_id="B-T-03", material=False
        )
        self.verify_iteration("behavior", label="merge-parent-check")
        self.complete({"summary": "Fresh candidate-bound planning checks passed."}, label="merge-parent-verify")
        self.assert_cursor("validate-spec", "behavior-commit")
        baseline = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", "HEAD^{tree}")
        other = self.git("commit-tree", tree, "-p", baseline, "-m", "unrelated audit parent")
        message_path = self.root / "merge-audit-message.txt"
        message_path.write_text(
            self.audit_message("behavior", review_learning, apply_learning),
            encoding="utf-8",
        )
        merge_sha = self.git(
            "commit-tree",
            tree,
            "-p",
            baseline,
            "-p",
            other,
            "-F",
            str(message_path),
        )
        self.git("update-ref", "HEAD", merge_sha)
        blocked, _ = self.complete(
            {"summary": "Attempt to count a tree-identical two-parent audit.", "commit": merge_sha},
            code=2,
            label="merge-parent-commit",
        )
        self.assertIn("single", blocked.stderr)
        self.assert_cursor("validate-spec", "behavior-commit")

    def test_cold_context_repair_revisit_and_old_run_safety(self) -> None:
        self.bootstrap_to_behavior()
        cold_body = self.behavior_body("cold").strip().replace("\n", "\r\n")
        behavior_result = self.record(
            "cold-behavior",
            {"summary": "Durable behavior candidate.", "body": cold_body},
        )
        self.cli("complete", "--action", self.state()["action"]["id"], "--result", behavior_result)
        Path(behavior_result).unlink()
        packet = self.cli("next").stdout
        self.assertIn("Objective:", packet)
        self.assertIn("Until:", packet)
        self.assertIn("Continue while:", packet)
        self.assertIn("Evidence required:", packet)
        self.assertIn("streak", packet.lower())
        self.assertIn("Planning-loop guidance: read only", packet)
        self.assertIn("planning-loops.md#review", packet)
        self.assertLess(len(packet), 7000)
        self.assertNotIn(".until-loop", packet)
        context = self.cli("context", "--section", "behavior", "--offset", "0", "--limit", "4000").stdout
        self.assertIn("Fixture behavior model (cold)", context)

        self.history()
        self.complete(
            {
                "summary": "A material issue starts an abandoned planning pass.",
                "findings": [{"id": "B-M-01", "severity": "material", "summary": "Repair fixture"}],
                "coverage_review": self.coverage_review("behavior"),
                "test_review": "No planning checks have run for the abandoned pass.",
                "learnings": "Repair restarts a planning review from durable state.",
            },
            label="repair-review",
        )
        self.assert_cursor("validate-spec", "behavior-plan")
        self.cli(
            "repair",
            "--action",
            self.state()["action"]["id"],
            "--reason",
            "Restart the planning pass after a host correction.",
        )
        self.assert_cursor("validate-spec", "behavior-review")
        self.assertEqual(self.planning("behavior")["streak"], 0)
        self.assertTrue(list((self.run_dir / "planning" / "behavior-iterations").glob("*.md")))

        self.cli(
            "revisit",
            "--action",
            self.state()["action"]["id"],
            "--to",
            "behavior",
            "--reason",
            "Reopen behavioral discovery before any execution.",
        )
        self.assert_cursor("validate-spec", "behavior")
        self.assertTrue(self.state().get("previous_planning"))
        archived = Path(self.state()["previous_planning"])
        self.assertEqual((archived / "behavior.md").read_bytes(), cold_body.encode("utf-8"))
        self.assertFalse((self.run_dir / "behavior.md").exists())
        self.assertFalse((self.run_dir / "planning" / "behavior.md").exists())

        state = self.make_old_run()
        state_before_next = (self.run_dir / "state.md").read_bytes()
        history_before_next = (self.run_dir / "history.md").read_bytes()
        packet = self.cli("next").stdout
        self.assertIn("planning-upgrade", packet)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before_next)
        self.assertEqual((self.run_dir / "history.md").read_bytes(), history_before_next)
        blocked = self.cli(
            "complete",
            "--action",
            state["action"]["id"],
            "--result",
            self.record(
                "blocked-old-run",
                {"summary": "An old run must upgrade before it can author a candidate.", "body": self.behavior_body("blocked")},
            ),
            code=2,
        )
        self.assertIn("upgrade required", blocked.stderr)
        self.cli("planning-upgrade", "--action", state["action"]["id"])
        self.assertEqual(self.state().get("planning_protocol_version"), 2)
        self.assert_cursor("validate-spec", "research")
        self.assertFalse((self.run_dir / "planning" / "behavior.md").exists())
        self.assertFalse((self.repo / ".until-loop").exists())

    def test_old_preflight_upgrade_keeps_preflight_gate(self) -> None:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--prompt",
            "Upgrade a historical preflight run without skipping its gate.",
        )
        state = self.make_old_run()
        self.cli("planning-upgrade", "--action", state["action"]["id"])
        self.assert_cursor("intake", "preflight")
        self.assertEqual(self.state().get("planning_protocol_version"), 2)

    def test_old_approach_upgrade_keeps_approach_gate_and_artifact(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Upgrade approach")
        self.complete(
            {"summary": "A committed baseline exists.", "baseline": "committed-head"},
            label="old-approach-preflight",
        )
        approach = "# Earlier approach\n\nKeep this upstream gate.\n"
        self.converge_objective(
            {"summary": "Earlier approach is durable.", "body": approach},
            label="approach",
        )
        stored_approach = (self.run_dir / "approach.md").read_text(encoding="utf-8")
        # Return to the historical action cursor rather than treating the newly
        # advanced survey action as evidence that the approach was bypassed.
        state = self.state()
        state.update(phase="intake", stage="approach")
        state["action"] = {"id": "old-approach-upgrade", "stage": "approach"}
        state.pop("objective", None)
        state.pop("planning_protocol_version", None)
        store.write_record(self.run_dir / "state.md", state)
        self.cli("planning-upgrade", "--action", "old-approach-upgrade")
        self.assert_cursor("intake", "approach")
        self.assertEqual(self.state().get("planning_protocol_version"), 2)
        self.assertEqual(
            (self.run_dir / "approach.md").read_text(encoding="utf-8"),
            stored_approach,
        )

    def test_v1_research_upgrade_archives_one_shot_report_and_restarts_research(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Upgrade research")
        self.complete(
            {"summary": "A committed baseline exists.", "baseline": "committed-head"},
            label="old-research-preflight",
        )
        self.converge_objective(
            {"summary": "Approach is durable.", "body": "# Approach\n\nPreserve upstream work.\n"},
            label="approach",
        )
        survey = self.machine_markdown()
        self.converge_objective(
            {"summary": "Survey is durable.", "body": survey},
            label="survey",
        )
        stored_survey = (self.run_dir / "environment.md").read_text(encoding="utf-8")
        research = "# Earlier research\n\nPreserve this gate before behavior convergence.\n"
        (self.run_dir / "research.md").write_text(research, encoding="utf-8")
        state = self.state()
        state.update(phase="validate-spec", stage="research")
        state["action"] = {"id": "old-research-upgrade", "stage": "research"}
        state.pop("objective", None)
        state["planning_protocol_version"] = 1
        store.write_record(self.run_dir / "state.md", state)
        self.cli("planning-upgrade", "--action", "old-research-upgrade")
        self.assert_cursor("validate-spec", "research")
        self.assertEqual(self.state().get("planning_protocol_version"), 2)
        self.assertEqual(
            (self.run_dir / "environment.md").read_text(encoding="utf-8"),
            stored_survey,
        )
        self.assertEqual(
            (self.run_dir / "planning-history" / "old-research-upgrade" / "upgrade" / "research.md").read_text(encoding="utf-8"),
            research,
        )
        self.assertFalse((self.run_dir / "research.md").exists())
        self.assertFalse((self.run_dir / "research-evidence.md").exists())

    def test_v1_upgrade_refuses_an_allocated_step_receipt_without_replaying_work(self) -> None:
        self.bootstrap_to_research()
        state = self.state()
        state["planning_protocol_version"] = 1
        store.write_record(self.run_dir / "state.md", state)
        steps = self.run_dir / "steps"
        steps.mkdir(exist_ok=True)
        store.write_record(
            steps / "S1.md",
            {"id": "S1", "status": "running", "allocation": "ready"},
            title="Allocated legacy step receipt",
        )
        state_before = (self.run_dir / "state.md").read_bytes()
        blocked = self.cli("planning-upgrade", "--action", state["action"]["id"], code=2)
        self.assertIn("step receipts exist", blocked.stderr)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), state_before)
        self.assertTrue((steps / "S1.md").is_file())

    def test_old_spec_upgrade_archives_unconverged_candidates_then_restarts_research(self) -> None:
        self.bootstrap_to_behavior()
        old_spec = self.spec_body("legacy")
        old_lifecycle = store.dumps(self.lifecycle(), "Legacy lifecycle")
        (self.run_dir / "spec.md").write_text(old_spec, encoding="utf-8")
        (self.run_dir / "lifecycle.md").write_text(old_lifecycle, encoding="utf-8")
        state = self.state()
        state.update(phase="validate-spec", stage="spec")
        state["action"] = {"id": "old-spec-upgrade", "stage": "spec"}
        state.pop("planning_protocol_version", None)
        store.write_record(self.run_dir / "state.md", state)
        self.cli("planning-upgrade", "--action", "old-spec-upgrade")
        self.assert_cursor("validate-spec", "research")
        archive = self.run_dir / "planning-history" / "old-spec-upgrade" / "upgrade"
        self.assertEqual((archive / "spec.md").read_text(encoding="utf-8"), old_spec)
        self.assertEqual((archive / "lifecycle.md").read_text(encoding="utf-8"), old_lifecycle)
        self.assertFalse((self.run_dir / "spec.md").exists())
        self.assertFalse((self.run_dir / "lifecycle.md").exists())
        self.assertTrue((self.run_dir / "environment.md").is_file())
        self.assertFalse((self.run_dir / "research.md").exists())

    def test_old_sequence_upgrade_archives_plan_then_restarts_research(self) -> None:
        self.bootstrap_to_behavior()
        old_plan = "# Earlier sequence\n\nThis plan is not certified by the new loops.\n"
        old_dag = "# Earlier DAG\n\nArchive rather than replay this work.\n"
        (self.run_dir / "plan.md").write_text(old_plan, encoding="utf-8")
        (self.run_dir / "backchain").mkdir()
        (self.run_dir / "backchain" / "plan.md").write_text(old_dag, encoding="utf-8")
        state = self.state()
        state.update(phase="plan", stage="sequence")
        state["action"] = {"id": "old-sequence-upgrade", "stage": "sequence"}
        state.pop("planning_protocol_version", None)
        store.write_record(self.run_dir / "state.md", state)
        self.cli("planning-upgrade", "--action", "old-sequence-upgrade")
        self.assert_cursor("validate-spec", "research")
        archive = self.run_dir / "planning-history" / "old-sequence-upgrade" / "upgrade"
        self.assertEqual((archive / "plan.md").read_text(encoding="utf-8"), old_plan)
        self.assertEqual((archive / "backchain" / "plan.md").read_text(encoding="utf-8"), old_dag)
        self.assertFalse((self.run_dir / "plan.md").exists())
        self.assertFalse((self.run_dir / "backchain" / "plan.md").exists())
        self.assertTrue((self.run_dir / "environment.md").is_file())
        self.assertFalse((self.run_dir / "research.md").exists())

    def test_revisit_behavior_refuses_to_skip_survey_and_research(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "No behavior shortcut")
        action = self.state()["action"]["id"]
        blocked = self.cli(
            "revisit",
            "--action",
            action,
            "--to",
            "behavior",
            "--reason",
            "Attempt to skip required discovery gates.",
            code=2,
        )
        self.assertIn("revisit is only for planning", blocked.stderr)
        self.assert_cursor("intake", "preflight")

    def test_old_schedule_next_is_read_only_until_upgrade(self) -> None:
        """A legacy schedule cursor must not allocate a worktree before upgrade."""
        self.cli("init", "--repo", str(self.repo), "--prompt", "No legacy schedule side effect")
        state = self.make_old_run()
        state.update(phase="implement", stage="schedule")
        state["action"] = {"id": "old-schedule-next", "stage": "schedule"}
        store.write_record(self.run_dir / "state.md", state)
        before_state = (self.run_dir / "state.md").read_bytes()
        before_history = (self.run_dir / "history.md").read_bytes()
        packet = self.cli("next").stdout
        self.assertIn("allocate only the next dependency-ready step", packet)
        self.assertIn("No completion callback is valid for schedule.", packet)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before_state)
        self.assertEqual((self.run_dir / "history.md").read_bytes(), before_history)
        self.assertFalse(list((self.run_dir / "steps").glob("*.md")))
        self.assertFalse((self.repo / ".worktrees" / "shiploop").exists())


if __name__ == "__main__":
    unittest.main()
