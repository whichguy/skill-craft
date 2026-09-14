#!/usr/bin/env python3
"""Public-CLI boundary tests for the mandatory Improve documentation action.

The fixture is intentionally seeded at an already-allocated Improve boundary.
It verifies the script-owned ``iteration-document -> verify`` transition and
its durable fingerprint guard without rerunning the expensive whole action
walk.  It is not evidence that the preceding planning or implementation loops
were executed by this test.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
ACTION_WALK = ROOT / "test" / "shiploop-action-walk.test.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_action_walk_fixture():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_iteration_docs_action_fixture", str(ACTION_WALK)
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

import shiploop_evidence as evidence  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402


class IterationDocumentationProtocolTests(ACTION.ShipLoopActionWalkFixture):
    """Use real CLI callbacks against a small, versioned active-step fixture."""

    def _seed_improve_boundary(
        self, marker: int | None = 1, *, stage: str = "improve-apply"
    ) -> tuple[dict, Path]:
        self.cli(
            "init",
            "--repo",
            str(self.repo),
            "--bound-plan",
            str(self.bound_plan),
            "--execution-mode",
            "legacy",
            "--prompt",
            "Exercise the versioned documentation checkpoint through public callbacks.",
        )
        state = self.state()
        run_id = state["run_id"]
        # State uses the resolved repository spelling; preserve it exactly for
        # active()'s foreign-worktree defense on macOS /private aliases.
        worktree = Path(state["repo_root"]) / ".worktrees" / "shiploop" / run_id / "S1"
        branch = f"shiploop/{run_id}/S1"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        self.git("worktree", "add", "-b", branch, str(worktree), "HEAD")
        baseline = self.git("rev-parse", "HEAD", cwd=worktree)
        initial_fingerprint = evidence.fingerprint(worktree, excluded=[])

        # The packet renderer needs the selected step's contract, but this
        # boundary test deliberately does not claim to have run its predecessor.
        (self.run_dir / "backchain").mkdir(exist_ok=True)
        store.write_record(
            self.run_dir / "backchain" / "plan.md",
            self.initial_dag(),
            title="Seeded action-walk dependency plan",
        )
        receipt = {
            "id": "S1",
            "run_id": run_id,
            "worktree": str(worktree),
            "branch": branch,
            "base_sha": baseline,
            "allocation": "ready",
            "inner": "B",
            "iteration": {
                "id": f"{run_id}-S1-I1",
                "applied_fingerprint": initial_fingerprint,
            },
        }
        (self.run_dir / "steps").mkdir(exist_ok=True)
        store.write_record(
            self.run_dir / "steps" / "S1.md", receipt,
            title="Seeded active Improve receipt",
        )
        state.update(
            phase="implement",
            stage=stage,
            active_step="S1",
            action={"id": f"{stage}-seed", "stage": stage},
            revision=state["revision"] + 1,
        )
        if marker is None:
            state.pop("iteration_documentation_protocol_version", None)
        else:
            state["iteration_documentation_protocol_version"] = marker
        store.write_record(self.run_dir / "state.md", state, title="Seeded Improve state")
        return state, worktree

    def _complete_seeded_improve_apply(self) -> None:
        """Exercise the durable transition while stubbing only prior plan proof.

        The preceding step-plan certificate and platform/revalidation guards
        are separately covered by the action-walk suites. This focused boundary
        keeps a real state/action, result record, receipt, persist transaction,
        and successor selection rather than simulating the transition itself.
        """
        state = self.state()
        action = state["action"]["id"]
        with (
            patch.object(protocol, "step_plan_validate_execution_proof", return_value=None),
            patch.object(protocol, "require_platform_route_for_active_step", return_value=None),
            patch.object(protocol, "require_platform_revalidation", return_value=None),
        ):
            protocol.complete(
                object(),
                self.run_dir,
                state,
                action,
                {
                    "summary": "The scoped Improve application is already represented by the seeded worktree.",
                    "material": False,
                    "test_changes": "No test bytes changed in this focused routing fixture.",
                    "learnings": "Improve application must route through the version-selected documentation gate.",
                },
            )

    def _document_payload(self, *, updated: bool) -> dict:
        documentation = {
            "decision": "updated" if updated else "not-needed",
            "rationale": (
                "The current README records the reusable local verification boundary."
                if updated
                else "The fixture has no documentation byte change to record."
            ),
            "paths": ["README.md"] if updated else [],
            "references": ["README.md"] if updated else [],
        }
        return {
            "summary": "The required documentation and reusable-skill decision is recorded before verification.",
            "documentation": documentation,
            "reusable_skill": {
                "decision": "not-needed",
                "rationale": "This fixture does not expose a reusable workflow beyond the existing ShipLoop package.",
                "paths": [],
                "references": [],
            },
            "material": False,
            "learnings": "Documentation and reusable-skill decisions are bound before verification and commit.",
        }

    def test_versioned_document_stage_rejects_incomplete_result_binds_changes_and_guards_verify(self) -> None:
        _, worktree = self._seed_improve_boundary()
        self._complete_seeded_improve_apply()
        self.assertEqual(self.state()["stage"], "iteration-document")
        action = self.action_id()
        before_incomplete = self.state()["revision"]
        packet = self.cli("next").stdout
        self.assertIn("Stage: iteration-document", packet)
        self.assertIn("Call this when done:", packet)

        self.complete({"summary": "Missing mandatory documentation decision."}, code=2, label="missing-docs")
        self.assertEqual(self.state()["stage"], "iteration-document")
        self.assertEqual(self.action_id(), action)
        self.assertEqual(self.state()["revision"], before_incomplete)

        (worktree / "README.md").write_text(
            "# Fixture\n\nDocumentation changed before verification.\n", encoding="utf-8"
        )
        payload = self._document_payload(updated=True)
        _, result_path = self.complete(payload, action_id=action, label="documented")
        self.assertEqual(self.state()["stage"], "verify")
        documented = self.receipt("S1")["iteration"]["documentation"]
        self.assertTrue(documented["material"], documented)
        self.assertEqual(documented["documentation"]["paths"], ["README.md"])

        revision = self.state()["revision"]
        self.cli("complete", "--action", action, "--result", result_path)
        self.assertEqual(self.state()["stage"], "verify")
        self.assertEqual(self.state()["revision"], revision)

        (worktree / "README.md").write_text(
            "# Fixture\n\nLate documentation drift after the checkpoint.\n", encoding="utf-8"
        )
        rejected, _ = self.complete(
            {"summary": "Claim verification without a fresh check."},
            code=2,
            label="late-doc-drift",
        )
        self.assertIn("worktree changed after iteration-document; repair and restart review", rejected.stderr)
        self.assertEqual(self.state()["stage"], "verify")

    def test_absent_marker_is_legacy_compatible_and_invalid_marker_is_rejected(self) -> None:
        self._seed_improve_boundary(marker=None)
        self._complete_seeded_improve_apply()
        # A real legacy improve-apply transition bypasses the new mandatory
        # stage; it does not manufacture a documentation receipt.
        self.assertEqual(self.state()["stage"], "verify")
        self.assertNotIn("iteration_documentation_protocol_version", self.state())
        self.assertNotIn("documentation", self.receipt("S1")["iteration"])

        state = self.state()
        state["iteration_documentation_protocol_version"] = 99
        store.write_record(self.run_dir / "state.md", state, title="Invalid iteration-documentation marker")
        invalid = self.cli("next", code=2)
        self.assertIn("iteration_documentation_protocol_version", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
