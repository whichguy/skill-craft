#!/usr/bin/env python3
"""Regression coverage for ShipLoop's durable environment, spec, and DAG gates.

These tests deliberately import the command module without invoking ``main``.
They exercise the validator boundary directly and write the dependency plan through
``shiploop_store`` so the Markdown record is the only DAG authority under test.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.machinery
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
SCRIPTS_DIR = SCRIPT.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

LOADER = importlib.machinery.SourceFileLoader("shiploop_validators_core", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None:
    raise RuntimeError(f"could not load {SCRIPT}")
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
LOADER.exec_module(core)
store = core.store


DONE_SENTENCE = "result.txt contains exactly one line: ok"
MCP_CONSIDERED = "none(no external reader matched this increment)"


def canonical_machine(**overrides: Any) -> Dict[str, Any]:
    machine: Dict[str, Any] = {
        "kind": "greenfield",
        "augment": False,
        "references": [],
        "tools": [],
        "mcp": [],
        "mcp_considered": MCP_CONSIDERED,
        "handles": [],
        "initiation": "none",
        "ui": False,
        "ui_craft": "none(no UI in scope)",
        "exclusive": [],
    }
    machine.update(overrides)
    return machine


def writer_machine(**overrides: Any) -> Dict[str, Any]:
    machine = canonical_machine(
        references=[{"path": "docs/writer.md", "why": "writer and route contract"}],
        tools=["git", "writer-cli", "alt-cli"],
        exclusive=[
            {
                "artifact": "deployed application",
                "use": "writer-cli",
                "dont_use": ["alt-cli"],
            }
        ],
        layout={"reserved": ["runtime/"], "product": ["app/"]},
        routing={
            "user_entrypoint": "/app",
            "reserved_routes": ["/"],
            "confirmation": "GET /app returns the product",
            "source": "docs/writer.md",
        },
    )
    machine.update(overrides)
    return machine


def prompt_for(
    produces: List[str],
    *,
    writer: bool = False,
    include_goal: bool = True,
    include_until: bool = True,
    include_produces: bool = True,
    include_tools: bool = True,
    include_reference: bool = True,
    include_reserved: bool = True,
    use: Optional[str] = None,
    dont_use: Optional[str] = None,
) -> str:
    lines: List[str] = []
    if include_goal:
        lines.append("/goal")
    if include_until:
        lines.append("Do this activity until these conditions are met:")
    if include_produces:
        lines.extend(f"- {item}" for item in produces)
    if writer and include_reference:
        lines.append("Read docs/writer.md before choosing the route.")
    if include_tools:
        lines.extend(
            [
                "Tools:",
                f"Watch with: {MCP_CONSIDERED}",
                f"Use: {use if use is not None else ('writer-cli' if writer else 'none')}",
                f"Don't use: {dont_use if dont_use is not None else ('alt-cli' if writer else 'none')}",
            ]
        )
        if writer and include_reserved:
            lines.append("Don't write: runtime/")
    return "\n".join(lines)


class ShipLoopValidatorCase(unittest.TestCase):
    """Fresh durable run files for each independent validator assertion."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name) / ".shiploop"
        self.run.mkdir()
        self.write_environment()
        self.write_spec()
        self.write_wrapper()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_environment(
        self,
        machine: Optional[Dict[str, Any]] = None,
        *,
        brief: str = "Survey findings.",
    ) -> None:
        payload = json.dumps(
            machine if machine is not None else canonical_machine(), indent=2
        )
        (self.run / "environment.md").write_text(
            f"{brief}\n\n## machine\n```json\n{payload}\n```\n", encoding="utf-8"
        )

    def write_spec(
        self,
        *,
        done_sentence: str = DONE_SENTENCE,
        checkable: str = "true",
        ask_user: Optional[str] = None,
        verify_hint: Optional[str] = None,
    ) -> None:
        lines = [f"done_sentence: {done_sentence}", f"checkable: {checkable}"]
        if ask_user is not None:
            lines.append(f"ask_user: {ask_user}")
        if verify_hint is not None:
            lines.append(f"verify_hint: {verify_hint}")
        (self.run / "spec.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_wrapper(self, done_sentence: str = DONE_SENTENCE) -> None:
        (self.run / "plan.md").write_text(
            f"# Delivery plan\n\ndone_sentence: {done_sentence}\n", encoding="utf-8"
        )

    def base_dag(
        self,
        *,
        prompt: Optional[str] = None,
        produces: Optional[List[str]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        unresolved: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        products = produces or ["result.txt exists"]
        return {
            "goal": DONE_SENTENCE,
            "initial_state": ["repository exists"],
            "steps": steps
            or [
                {
                    "id": "S1",
                    "statement": "Create the result file",
                    "prompt": prompt or prompt_for(products),
                    "produces": products,
                    "origin": "seed",
                    "inputs": [{"need": "repository exists", "from": None}],
                }
            ],
            "unresolved": unresolved if unresolved is not None else [],
        }

    def write_dag(self, dag: Dict[str, Any]) -> Path:
        path = self.run / "backchain" / "plan.md"
        path.parent.mkdir(exist_ok=True)
        store.write_record(path, dag, title="ShipLoop dependency plan")
        return path

    def dag_gaps(self, dag: Dict[str, Any]) -> List[str]:
        self.write_dag(dag)
        spec, gaps = core.load_spec(self.run)
        self.assertFalse(gaps, gaps)
        return core.dag_gaps(self.run, spec)

    def assert_gap(self, gaps: List[str], phrase: str) -> None:
        self.assertTrue(
            any(phrase in gap for gap in gaps), f"{phrase!r} not in {gaps!r}"
        )

    def assert_blocked(self, state: Dict[str, Any], dest: str) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                core.check_frozen_hashes(state, self.run, dest)
        self.assertEqual(raised.exception.code, core.EXIT_BLOCKED)


class EnvironmentValidationTests(ShipLoopValidatorCase):
    def test_load_environment_accepts_canonical_machine(self) -> None:
        machine, gaps = core.load_environment(self.run)
        self.assertEqual(gaps, [])
        self.assertEqual(machine, canonical_machine())

    def test_load_environment_requires_one_machine_heading_and_brief(self) -> None:
        (self.run / "environment.md").write_text("brief only\n", encoding="utf-8")
        _, gaps = core.load_environment(self.run)
        self.assert_gap(gaps, "missing a '## machine' section")

        (self.run / "environment.md").write_text(
            "## machine\n```json\n{}\n```\n\n## machine\n```json\n{}\n```\n",
            encoding="utf-8",
        )
        _, gaps = core.load_environment(self.run)
        self.assert_gap(gaps, "exactly one '## machine' section")

    def test_load_environment_refuses_unclosed_or_non_json_machine_fence(self) -> None:
        (self.run / "environment.md").write_text(
            "Brief.\n\n## machine\n```json\n{not JSON}\n```\n", encoding="utf-8"
        )
        _, gaps = core.load_environment(self.run)
        self.assert_gap(gaps, "machine fence is not valid JSON")

        (self.run / "environment.md").write_text(
            "Brief.\n\n## machine\n```json\n{}\n", encoding="utf-8"
        )
        _, gaps = core.load_environment(self.run)
        self.assert_gap(gaps, "machine fence is not closed")

    def test_validate_machine_rejects_kind_augment_and_brownfield_reference_mismatch(
        self,
    ) -> None:
        gaps = core.validate_machine(canonical_machine(kind="greenfield", augment=True))
        self.assert_gap(gaps, "augment must be false when kind is greenfield")

        gaps = core.validate_machine(canonical_machine(kind="brownfield", augment=True))
        self.assert_gap(gaps, "references must be nonempty when kind is brownfield")

    def test_validate_machine_rejects_invalid_handle_and_initiation_contracts(
        self,
    ) -> None:
        gaps = core.validate_machine(
            canonical_machine(
                handles=[
                    {
                        "source": "git",
                        "need": "repository",
                        "resolve": "inspect",
                        "value": "",
                    }
                ],
                initiation="needed",
            )
        )
        self.assert_gap(gaps, "value required (inspect, non-credential)")
        self.assert_gap(gaps, "needed requires >=1 handle with resolve=create")

        gaps = core.validate_machine(
            canonical_machine(
                handles=[
                    {
                        "source": "git",
                        "need": "repository",
                        "resolve": "create",
                        "value": "",
                    }
                ],
                initiation="none",
            )
        )
        self.assert_gap(gaps, "none/done forbids resolve=create handles")

    def test_validate_machine_rejects_ui_craft_shape_mismatch(self) -> None:
        gaps = core.validate_machine(
            canonical_machine(ui=True, ui_craft="none(no design)")
        )
        self.assert_gap(gaps, "must not be none(...)")

        gaps = core.validate_machine(
            canonical_machine(ui=False, ui_craft="frontend-design")
        )
        self.assert_gap(gaps, "must be none(...)")

    def test_validate_machine_rejects_uninventoried_or_unsafe_exclusive_rows(
        self,
    ) -> None:
        gaps = core.validate_machine(
            canonical_machine(
                tools=["git"],
                exclusive=[{"artifact": "app", "use": "ghost", "dont_use": ["git;rm"]}],
            )
        )
        self.assert_gap(gaps, "must be an inventoried tools or mcp name")
        self.assert_gap(gaps, "must not contain a semicolon or newline")


class SpecAndWrapperValidationTests(ShipLoopValidatorCase):
    def test_load_spec_uses_only_unquoted_unfenced_labels(self) -> None:
        (self.run / "spec.md").write_text(
            "```md\ndone_sentence: forged\ncheckable: false\n```\n"
            "> done_sentence: also forged\n"
            f"done_sentence: {DONE_SENTENCE}\ncheckable: true\n"
            "verify_hint: python3 -m unittest\n",
            encoding="utf-8",
        )
        spec, gaps = core.load_spec(self.run)
        self.assertEqual(gaps, [])
        self.assertEqual(spec["done_sentence"], DONE_SENTENCE)
        self.assertTrue(spec["checkable"])
        self.assertEqual(spec["verify_hint"], "python3 -m unittest")

    def test_load_spec_requires_checkable_and_singleton_labels(self) -> None:
        (self.run / "spec.md").write_text(
            f"done_sentence: {DONE_SENTENCE}\n", encoding="utf-8"
        )
        _, gaps = core.load_spec(self.run)
        self.assert_gap(gaps, "missing labeled checkable")

        (self.run / "spec.md").write_text(
            f"done_sentence: {DONE_SENTENCE}\ndone_sentence: duplicate\ncheckable: true\n",
            encoding="utf-8",
        )
        _, gaps = core.load_spec(self.run)
        self.assert_gap(gaps, "must appear exactly once")

    def test_load_spec_requires_question_for_uncheckable_work(self) -> None:
        self.write_spec(checkable="false")
        _, gaps = core.load_spec(self.run)
        self.assert_gap(gaps, "ask_user required")

        self.write_spec(
            checkable="false", ask_user="Which live account should validate it?"
        )
        spec, gaps = core.load_spec(self.run)
        self.assertEqual(gaps, [])
        self.assertFalse(spec["checkable"])

    def test_wrapper_pair_requires_one_matching_done_sentence(self) -> None:
        spec, gaps = core.load_spec(self.run)
        self.assertEqual(gaps, [])
        self.assertEqual(core.wrapper_pair(self.run, spec), [])

        self.write_wrapper("a different outcome")
        gaps = core.wrapper_pair(self.run, spec)
        self.assert_gap(gaps, "must equal spec.md")

    def test_wrapper_pair_rejects_duplicate_done_sentence(self) -> None:
        spec, _ = core.load_spec(self.run)
        (self.run / "plan.md").write_text(
            f"done_sentence: {DONE_SENTENCE}\ndone_sentence: {DONE_SENTENCE}\n",
            encoding="utf-8",
        )
        gaps = core.wrapper_pair(self.run, spec)
        self.assert_gap(gaps, "must appear exactly once")


class DestinationIdentityTests(ShipLoopValidatorCase):
    def test_unresolved_environment_handles_block_destination_planning(self) -> None:
        machine = canonical_machine(
            handles=[
                {
                    "source": "hosting account",
                    "need": "project id",
                    "resolve": "ask",
                    "value": "",
                }
            ]
        )
        gaps = core.handles_block_plan(machine)
        self.assert_gap(gaps, "resolve=ask blocks dest plan")

    def test_exclusive_gaps_requires_explicit_empty_or_structured_exclusive_key(
        self,
    ) -> None:
        machine = canonical_machine()
        machine.pop("exclusive")
        gaps = core.exclusive_gaps(machine)
        self.assert_gap(gaps, "machine.exclusive must be a list")

    def test_exclusive_gaps_require_refs_layout_and_routing_for_destination_writer(
        self,
    ) -> None:
        machine = canonical_machine(
            tools=["writer-cli"],
            exclusive=[{"artifact": "app", "use": "writer-cli", "dont_use": []}],
        )
        gaps = core.exclusive_gaps(machine)
        self.assert_gap(gaps, "references must be nonempty")
        self.assert_gap(gaps, "machine.layout required")
        self.assert_gap(gaps, "machine.routing required")

    def test_exclusive_gaps_reject_competing_or_opposing_writer_routes(self) -> None:
        machine = writer_machine(
            tools=["writer-a", "writer-b"],
            exclusive=[
                {"artifact": "a", "use": "writer-a", "dont_use": ["writer-b"]},
                {"artifact": "b", "use": "writer-b", "dont_use": ["writer-a"]},
            ],
        )
        gaps = core.exclusive_gaps(machine)
        self.assert_gap(gaps, "single exclusive writer")
        self.assert_gap(gaps, "opposing writers")

    def test_destination_route_source_must_be_a_survey_reference(self) -> None:
        machine = writer_machine(
            routing={
                "user_entrypoint": "/app",
                "reserved_routes": ["/"],
                "confirmation": "GET /app",
                "source": "not-in-references.md",
            }
        )
        gaps = core.exclusive_gaps(machine)
        self.assert_gap(gaps, "routing.source must name a references[].path")

    def test_ui_craft_requires_its_reference_path(self) -> None:
        machine = canonical_machine(
            ui=True,
            ui_craft="frontend-design",
            references=[{"path": "docs/product.md", "why": "product facts"}],
        )
        gaps = core.ui_craft_gaps(machine)
        self.assert_gap(gaps, "ui_craft must appear in a references[].path")


class MarkdownDagValidationTests(ShipLoopValidatorCase):
    def test_valid_dag_is_loaded_from_markdown_authority_without_json_twin(
        self,
    ) -> None:
        dag = self.base_dag()
        path = self.write_dag(dag)
        self.assertTrue(path.is_file())
        self.assertFalse((self.run / "backchain" / "plan.json").exists())
        self.assertEqual(core.load_dag(self.run), dag)
        spec, spec_gaps = core.load_spec(self.run)
        self.assertEqual(spec_gaps, [])
        self.assertEqual(core.dag_gaps(self.run, spec), [])

    def test_dag_rejects_unresolved_work_before_implementation(self) -> None:
        gaps = self.dag_gaps(
            self.base_dag(unresolved=["identify the production endpoint"])
        )
        self.assert_gap(gaps, "unresolved must be empty")

    def test_dag_rejects_unsafe_and_duplicate_step_ids(self) -> None:
        unsafe = self.base_dag()
        unsafe["steps"][0]["id"] = "../outside"
        gaps = self.dag_gaps(unsafe)
        self.assert_gap(gaps, "unsafe or missing step id")

        duplicate = self.base_dag()
        second = copy.deepcopy(duplicate["steps"][0])
        second["statement"] = "Duplicate id"
        duplicate["steps"].append(second)
        gaps = self.dag_gaps(duplicate)
        self.assert_gap(gaps, "duplicate step id S1")

    def test_dag_rejects_unknown_dependencies_and_cycles(self) -> None:
        dangling = self.base_dag()
        dangling["steps"][0]["inputs"] = [{"need": "missing", "from": "S9"}]
        gaps = self.dag_gaps(dangling)
        self.assert_gap(gaps, "is not an existing id")

        cycle = self.base_dag(
            steps=[
                {
                    "id": "S1",
                    "statement": "first",
                    "prompt": prompt_for(["first exists"]),
                    "produces": ["first exists"],
                    "origin": "seed",
                    "inputs": [{"need": "second exists", "from": "S2"}],
                },
                {
                    "id": "S2",
                    "statement": "second",
                    "prompt": prompt_for(["second exists"]),
                    "produces": ["second exists"],
                    "origin": "seed",
                    "inputs": [{"need": "first exists", "from": "S1"}],
                },
            ]
        )
        gaps = self.dag_gaps(cycle)
        self.assert_gap(gaps, "committed cycle")

    def test_dag_rejects_initial_state_claims_without_a_source(self) -> None:
        dag = self.base_dag()
        dag["steps"][0]["inputs"] = [{"need": "unknown fact", "from": None}]
        gaps = self.dag_gaps(dag)
        self.assert_gap(gaps, "from:null need not in initial_state")

    def test_dag_requires_goal_until_clause_and_each_declared_product(self) -> None:
        dag = self.base_dag(
            produces=["result.txt exists", "tests pass"],
            prompt=prompt_for(
                ["result.txt exists", "tests pass"],
                include_goal=False,
                include_until=False,
                include_produces=False,
            ),
        )
        gaps = self.dag_gaps(dag)
        self.assert_gap(gaps, "line starting with /goal")
        self.assert_gap(
            gaps, "must contain 'Do this activity until these conditions are met:'"
        )
        self.assert_gap(gaps, "until-clause must name produces 'result.txt exists'")
        self.assert_gap(gaps, "until-clause must name produces 'tests pass'")

    def test_seed_dag_requires_tools_line_and_reference_citation(self) -> None:
        self.write_environment(writer_machine())
        no_tools = self.base_dag(
            prompt=prompt_for(["result.txt exists"], writer=True, include_tools=False)
        )
        gaps = self.dag_gaps(no_tools)
        self.assert_gap(gaps, "line starting with Tools:")

        missing_reference = self.base_dag(
            prompt=prompt_for(
                ["result.txt exists"], writer=True, include_reference=False
            )
        )
        gaps = self.dag_gaps(missing_reference)
        self.assert_gap(gaps, "must cite environment reference docs/writer.md")

    def test_writer_prompt_requires_designated_use_and_every_dont_use_token(
        self,
    ) -> None:
        self.write_environment(writer_machine())
        dag = self.base_dag(
            prompt=prompt_for(
                ["result.txt exists"], writer=True, use="git", dont_use="none"
            )
        )
        gaps = self.dag_gaps(dag)
        self.assert_gap(gaps, "exclusive dont_use alt-cli")
        self.assert_gap(gaps, "exclusive use writer-cli")

    def test_seed_writer_prompt_protects_reserved_destination_paths(self) -> None:
        self.write_environment(writer_machine())
        dag = self.base_dag(
            prompt=prompt_for(
                ["result.txt exists"], writer=True, include_reserved=False
            )
        )
        gaps = self.dag_gaps(dag)
        self.assert_gap(gaps, "must have a Don't write: line")

        dag = self.base_dag(
            prompt=(
                prompt_for(["result.txt exists"], writer=True, include_reserved=False)
                + "\nDon't write: generated/"
            )
        )
        gaps = self.dag_gaps(dag)
        self.assert_gap(gaps, "reserved path runtime/")

    def test_ui_dag_requires_a_design_seed(self) -> None:
        self.write_environment(
            canonical_machine(
                ui=True,
                ui_craft="frontend-design",
                references=[
                    {"path": "skills/frontend-design/README.md", "why": "visual system"}
                ],
            )
        )
        gaps = self.dag_gaps(self.base_dag())
        self.assert_gap(gaps, "ui requires a design-producing seed")

    def test_ui_design_seed_must_feed_another_seed(self) -> None:
        self.write_environment(
            canonical_machine(
                ui=True,
                ui_craft="frontend-design",
                references=[
                    {"path": "skills/frontend-design/README.md", "why": "visual system"}
                ],
            )
        )
        design = {
            "id": "S1",
            "statement": "Design the application",
            "prompt": (
                prompt_for(["visual identity exists"])
                + "\nRead skills/frontend-design/README.md for the visual system."
            ),
            "produces": ["visual identity exists"],
            "origin": "seed",
            "inputs": [{"need": "repository exists", "from": None}],
        }
        gaps = self.dag_gaps(self.base_dag(steps=[design]))
        self.assert_gap(gaps, "ui design seed must feed another seed")

    def test_ui_design_dependency_is_accepted(self) -> None:
        self.write_environment(
            canonical_machine(
                ui=True,
                ui_craft="frontend-design",
                references=[
                    {"path": "skills/frontend-design/README.md", "why": "visual system"}
                ],
            )
        )
        design = {
            "id": "S1",
            "statement": "Design the application",
            "prompt": (
                prompt_for(["visual identity exists"])
                + "\nRead skills/frontend-design/README.md for the visual system."
            ),
            "produces": ["visual identity exists"],
            "origin": "seed",
            "inputs": [{"need": "repository exists", "from": None}],
        }
        build = {
            "id": "S2",
            "statement": "Build the application",
            "prompt": (
                prompt_for(["result.txt exists"])
                + "\nRead skills/frontend-design/README.md for the visual system."
            ),
            "produces": ["result.txt exists"],
            "origin": "seed",
            "inputs": [{"need": "visual identity exists", "from": "S1"}],
        }
        self.assertEqual(self.dag_gaps(self.base_dag(steps=[design, build])), [])


class FrozenArtifactValidationTests(ShipLoopValidatorCase):
    def bound_state(self) -> Dict[str, Any]:
        dag = self.base_dag()
        path = self.write_dag(dag)
        return {
            "environment_sha256": core.environment_sha256_of(self.run),
            "spec_sha256": core.spec_sha256_of(self.run),
            "plan_sha256": core.sha256_file(path),
        }

    def test_frozen_hashes_accept_unchanged_authoritative_files(self) -> None:
        core.check_frozen_hashes(self.bound_state(), self.run, "implement")

    def test_frozen_environment_drift_is_blocked(self) -> None:
        state = self.bound_state()
        with (self.run / "environment.md").open("a", encoding="utf-8") as handle:
            handle.write("\nchanged after freeze\n")
        self.assert_blocked(state, "implement")

    def test_frozen_spec_drift_is_blocked(self) -> None:
        state = self.bound_state()
        with (self.run / "spec.md").open("a", encoding="utf-8") as handle:
            handle.write("verify_hint: changed after freeze\n")
        self.assert_blocked(state, "implement")

    def test_frozen_markdown_dag_drift_is_blocked(self) -> None:
        state = self.bound_state()
        changed = self.base_dag()
        changed["steps"][0]["statement"] = "Changed after freeze"
        self.write_dag(changed)
        self.assert_blocked(state, "implement")

    def test_blocked_transition_is_the_intentional_drift_rebind_hatch(self) -> None:
        state = self.bound_state()
        (self.run / "environment.md").write_text("changed\n", encoding="utf-8")
        (self.run / "spec.md").write_text("changed\n", encoding="utf-8")
        self.write_dag({"changed": True})
        core.check_frozen_hashes(state, self.run, "blocked")


class LedgerLandingValidationTests(ShipLoopValidatorCase):
    """A ledger claim is not proof until its exact file is committed and clean."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "ShipLoop tests")
        self.git("config", "user.email", "shiploop-tests@example.invalid")
        (self.repo / "README.md").write_text("baseline\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "baseline")
        self.bound_plan = Path(self.temp.name) / "bound-plan.md"
        self.bound_plan.write_text("# Bound plan\n", encoding="utf-8")
        self.state = {
            "repo_root": str(self.repo),
            "bound_plan": str(self.bound_plan),
            "bound_plan_hash": core.sha256_file(self.bound_plan),
        }

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def ledger_text(self, round_number: int = 2) -> str:
        return (
            "**Status:** complete\n"
            f"**Plan contract:** `{self.bound_plan}`\n"
            f"**Plan hash:** `{self.state['bound_plan_hash']}`\n\n"
            f"### Round {round_number} —\n"
            "**Committed:** yes\n"
            f"review-converge: round {round_number} —\n"
        )

    def test_untracked_or_dirty_ledger_cannot_claim_landed_review_coverage(
        self,
    ) -> None:
        ledger = self.repo / "REVIEW_CONVERGE.md"
        ledger.write_text(self.ledger_text(), encoding="utf-8")
        report = core.ledger_report(self.repo, self.state)
        self.assertTrue(report["bound"], report)
        self.assertFalse(report["landed"], report)
        self.assert_gap(core.residual_gaps(self.state, "done"), "not landed")

        self.git("add", "REVIEW_CONVERGE.md")
        self.git("commit", "-qm", "review-converge: round 2 —")
        report = core.ledger_report(self.repo, self.state)
        self.assertTrue(report["landed"], report)
        self.assertEqual(core.residual_gaps(self.state, "done"), [])

        with ledger.open("a", encoding="utf-8") as handle:
            handle.write("\npost-commit alteration\n")
        report = core.ledger_report(self.repo, self.state)
        self.assertFalse(report["landed"], report)
        self.assert_gap(core.residual_gaps(self.state, "done"), "not landed")

    def test_latest_round_commit_must_contain_the_current_ledger_blob(self) -> None:
        ledger = self.repo / "REVIEW_CONVERGE.md"
        ledger.write_text(self.ledger_text(), encoding="utf-8")
        self.git("add", "REVIEW_CONVERGE.md")
        self.git("commit", "-qm", "save coverage ledger")
        self.git("commit", "--allow-empty", "-qm", "review-converge: round 2 —")

        report = core.ledger_report(self.repo, self.state)
        self.assertFalse(report["landed"], report)

        with ledger.open("a", encoding="utf-8") as handle:
            handle.write("\nEvidence: committed final ledger blob\n")
        self.git("add", "REVIEW_CONVERGE.md")
        self.git("commit", "-qm", "review-converge: round 2 —")
        report = core.ledger_report(self.repo, self.state)
        self.assertTrue(report["landed"], report)

    def test_plain_documented_committed_marker_matches_bold_grammar(self) -> None:
        ledger = self.repo / "REVIEW_CONVERGE.md"
        for marker, expected in (
            ("Committed: no", False),
            ("Committed: yes", True),
            ("**Committed:** no", False),
            ("**Committed:** yes", True),
        ):
            with self.subTest(marker=marker):
                ledger.write_text(
                    self.ledger_text().replace("**Committed:** yes", marker),
                    encoding="utf-8",
                )
                self.git("add", "REVIEW_CONVERGE.md")
                self.git("commit", "-qm", "review-converge: round 2 — marker test")
                report = core.ledger_report(self.repo, self.state)
                self.assertEqual(report["landed"], expected, report)


class PlanWaiverValidationTests(ShipLoopValidatorCase):
    def test_only_a_hashed_bound_review_coverage_section_can_waive_outer_ledger(
        self,
    ) -> None:
        bound = Path(self.temp.name) / "bound-plan.md"
        bound.write_text(
            "# Delivery\n\n## Review Coverage\n\n"
            "None — residual loop waived: no executable production surface exists\n",
            encoding="utf-8",
        )
        state = {
            "bound_plan": str(bound),
            "bound_plan_hash": core.sha256_file(bound),
        }
        self.assertEqual(
            core.plan_waiver(state), "no executable production surface exists"
        )
        self.assertEqual(core.residual_gaps(state, "done"), [])

        bound.write_text(
            "# Delivery\n\nNone — residual loop waived: outside review coverage\n",
            encoding="utf-8",
        )
        state["bound_plan_hash"] = core.sha256_file(bound)
        self.assertIsNone(core.plan_waiver(state))


if __name__ == "__main__":
    unittest.main(verbosity=2)
