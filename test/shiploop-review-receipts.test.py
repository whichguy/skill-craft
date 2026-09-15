#!/usr/bin/env python3
"""Regression coverage for opt-in navigator Improve review receipts.

The tests use only temporary run directories and ordinary non-Git repositories.
They deliberately assert the public receipt boundaries rather than duplicating
the navigator's routing implementation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import os
from pathlib import Path
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

import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


REVIEW_FIELDS = {
    "candidate_before",
    "candidate_after",
    "classification",
    "checks",
    "improvements_complete",
    "open_findings",
}


def generic_result(
    outcome: str = "done", summary: str = "Synthetic navigator result.", **extra: object
) -> dict[str, object]:
    return {"outcome": outcome, "summary": summary, **extra}


def review_result(
    before: str,
    after: str,
    *,
    classification: str = "trivial",
    checks: str = "passed",
    improvements_complete: bool = True,
    open_findings: list[str] | None = None,
    **extra: object,
) -> dict[str, object]:
    return generic_result(
        evidence_refs=["notes/review-receipt.md"],
        review={
            "candidate_before": before,
            "candidate_after": after,
            "classification": classification,
            "checks": checks,
            "improvements_complete": improvements_complete,
            "open_findings": [] if open_findings is None else open_findings,
        },
        **extra,
    )


def all_object_keys(value: object) -> set[str]:
    """Collect object keys only; receipt prose is not an implementation detail."""
    if isinstance(value, dict):
        return set(value) | set().union(*(all_object_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(all_object_keys(item) for item in value))
    return set()


class ReviewReceiptCase(unittest.TestCase):
    """Small pure-API fixture, deliberately never initialized as a Git repo."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-review-receipts-")
        self.base = Path(self.temp.name)
        self.run_dir = self.base / "run"
        self.run_dir.mkdir()
        self.repo = self.base / "ordinary-project"
        self.repo.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def v2_state(self) -> dict[str, object]:
        return navigator.new_state(
            str(self.repo), "Deliver bounded review receipt coverage.", review_receipts=True
        )

    def apply(self, state: dict[str, object], result: dict[str, object]) -> dict[str, object]:
        before = copy.deepcopy(state)
        action = state["action"]
        self.assertIsInstance(action, dict)
        updated = navigator.apply(state, action["id"], result)
        self.assertEqual(state, before)
        navigator.validate(updated)
        return updated

    def ordinary(self, state: dict[str, object], stage: str, **extra: object) -> dict[str, object]:
        self.assertEqual(state["stage"], stage)
        return self.apply(state, generic_result(**extra))

    def to_research_improve(self) -> dict[str, object]:
        state = self.v2_state()
        for stage in ("intake", "discovery", "research"):
            state = self.ordinary(state, stage)
        self.assertEqual(state["stage"], "research-improve")
        return state

    def review(
        self,
        state: dict[str, object],
        before: str,
        after: str,
        **extra: object,
    ) -> dict[str, object]:
        self.assertIn(state["stage"], {
            "research-improve",
            "spec-improve",
            "plan-improve",
            "step-plan-improve",
            "product-improve",
            "outer-improve",
        })
        return self.apply(state, review_result(before, after, **extra))

    def finish_campaign(
        self,
        state: dict[str, object],
        label: str,
        *,
        first_before: str | None = None,
        first_extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Complete two eligible receipts without asserting the whole graph."""
        stage = state["stage"]
        before = first_before or f"{label}-candidate-0"
        state = self.review(
            state, before, f"{label}-candidate-1", **(first_extra or {})
        )
        self.assertEqual(state["stage"], stage)
        return self.review(
            state, f"{label}-candidate-1", f"{label}-candidate-2",
            classification="none",
        )


class ReviewReceiptSchemaTests(ReviewReceiptCase):
    def test_research_adapter_distinguishes_campaign_from_iteration(self) -> None:
        adapter = (ROOT / "skills/shiploop/references/research-loop.md").read_text(
            encoding="utf-8"
        ).split("## Navigator execution mode adapter", 1)[1].split("## Decision boundaries", 1)[0]
        self.assertIn("Protocol 1", adapter)
        self.assertIn("Protocol 2", adapter)
        self.assertIn("one complete iteration", adapter)
        self.assertIn("review receipt", adapter)
        self.assertNotIn("An Improve node owns its entire", adapter)

    def test_default_v1_remains_generic_and_review_receipts_are_opt_in(self) -> None:
        state = navigator.new_state(str(self.repo), "Keep legacy navigator behavior.")
        self.assertEqual(state["navigator_protocol_version"], 1)
        self.assertNotIn("review_receipts", state)

        for stage in ("intake", "discovery", "research"):
            state = self.ordinary(state, stage)
        self.assertEqual(state["stage"], "research-improve")
        state = self.apply(state, generic_result())
        self.assertEqual(state["stage"], "spec")

        v1 = navigator.new_state(str(self.repo), "Review is not a v1 field.")
        before = copy.deepcopy(v1)
        with self.assertRaises(navigator.NavigatorError):
            self.apply(v1, review_result("legacy-before", "legacy-after"))
        self.assertEqual(v1, before)

    def test_v2_requires_exact_review_schema_only_for_improve_done(self) -> None:
        state = self.to_research_improve()
        action = state["action"]["id"]

        malformed: dict[str, dict[str, object]] = {
            "missing review": generic_result(evidence_refs=["notes/missing.md"]),
            "empty evidence": generic_result(
                evidence_refs=[],
                review=review_result("a", "b")["review"],
            ),
            "extra counter": generic_result(
                evidence_refs=["notes/counter.md"],
                review={**review_result("a", "b")["review"], "streak": 99},
            ),
            "blank candidate": generic_result(
                evidence_refs=["notes/blank.md"],
                review={**review_result("a", "b")["review"], "candidate_before": "   "},
            ),
            "non-string finding": generic_result(
                evidence_refs=["notes/finding.md"],
                review={**review_result("a", "b")["review"], "open_findings": [7]},
            ),
        }
        for label, payload in malformed.items():
            with self.subTest(label=label):
                before = copy.deepcopy(state)
                with self.assertRaises(navigator.NavigatorError):
                    navigator.apply(state, action, payload)
                self.assertEqual(state, before)

        initial = self.v2_state()
        initial_before = copy.deepcopy(initial)
        with self.assertRaises(navigator.NavigatorError):
            self.apply(initial, review_result("wrong-stage-before", "wrong-stage-after"))
        self.assertEqual(initial, initial_before)

        accepted = self.review(state, "research-0", "research-1")
        result = accepted["accepted"][action]
        self.assertEqual(set(result["review"]), REVIEW_FIELDS)
        self.assertTrue(
            {"streak", "trivial_streak", "review_streak"}.isdisjoint(
                all_object_keys(accepted)
            )
        )


class ReviewReceiptReducerTests(ReviewReceiptCase):
    def test_one_done_is_one_review_iteration_and_two_eligible_reviews_advance(self) -> None:
        state = self.to_research_improve()
        first_action = state["action"]["id"]
        state = self.review(state, "research-0", "research-1", classification="trivial")
        self.assertEqual(state["stage"], "research-improve")
        self.assertNotEqual(state["action"]["id"], first_action)
        self.assertEqual(len(state["history"]), 4)

        state = self.review(state, "research-1", "research-2", classification="none")
        self.assertEqual(state["stage"], "spec")

    def test_disqualifying_receipts_are_accepted_but_reset_the_campaign(self) -> None:
        disqualifiers = (
            ("material", {"classification": "material"}),
            ("uncertain", {"classification": "uncertain"}),
            ("failed checks", {"checks": "failed"}),
            ("stale checks", {"checks": "stale"}),
            ("incomplete checks", {"checks": "incomplete"}),
            ("unfinished improvements", {"improvements_complete": False}),
            ("open findings", {"open_findings": ["F-001 remains open"]}),
        )
        for label, fault in disqualifiers:
            with self.subTest(label=label):
                state = self.to_research_improve()
                state = self.review(state, "candidate-0", "candidate-1")
                fault_action = state["action"]["id"]
                state = self.review(state, "candidate-1", "candidate-2", **fault)
                self.assertEqual(state["stage"], "research-improve")
                self.assertIn(fault_action, state["accepted"])
                self.assertEqual(
                    state["accepted"][fault_action]["review"]["candidate_after"],
                    "candidate-2",
                )
                # A fresh eligible pass is only the first post-reset pass.
                state = self.review(state, "candidate-2", "candidate-3")
                self.assertEqual(state["stage"], "research-improve")

    def test_candidate_drift_resets_before_the_new_review_can_count(self) -> None:
        state = self.to_research_improve()
        state = self.review(state, "candidate-0", "candidate-1")
        state = self.review(state, "different-candidate", "candidate-2")
        self.assertEqual(state["stage"], "research-improve")

        state = self.review(state, "candidate-2", "candidate-3")
        self.assertEqual(state["stage"], "spec")

    def test_repeat_and_blocked_reset_but_pause_resume_preserves_an_actual_pass(self) -> None:
        for outcome in ("repeat", "blocked"):
            with self.subTest(outcome=outcome):
                state = self.to_research_improve()
                state = self.review(state, "candidate-0", "candidate-1")
                state = self.apply(
                    state,
                    generic_result(outcome, f"Synthetic {outcome} interruption."),
                )
                self.assertEqual(state["stage"], "research-improve")
                if outcome == "blocked":
                    state = navigator.control(state, "resume", "Synthetic blocker resolved.")
                state = self.review(state, "candidate-1", "candidate-2")
                self.assertEqual(state["stage"], "research-improve")
                state = self.review(state, "candidate-2", "candidate-3")
                self.assertEqual(state["stage"], "spec")

        state = self.to_research_improve()
        state = self.review(state, "pause-0", "pause-1")
        history_before_pause = copy.deepcopy(state["history"])
        action_before_pause = state["action"]
        state = navigator.control(state, "pause", "Cold context handoff.")
        state = navigator.control(state, "resume", "Cold context restored.")
        self.assertEqual(state["history"], history_before_pause)
        self.assertEqual(state["action"], action_before_pause)
        state = self.review(state, "pause-1", "pause-2")
        self.assertEqual(state["stage"], "spec")

    def test_stage_and_work_item_campaigns_cannot_borrow_a_prior_clean_streak(self) -> None:
        state = self.to_research_improve()
        state = self.review(state, "research-0", "shared-stage-candidate")
        state = self.review(state, "shared-stage-candidate", "research-2", classification="none")
        self.assertEqual(state["stage"], "spec")

        state = self.ordinary(state, "spec")
        # The matching descriptor deliberately removes candidate drift as an
        # explanation for why the new stage still needs its own first pass.
        state = self.review(state, "research-2", "spec-1")
        self.assertEqual(state["stage"], "spec-improve")
        state = self.review(state, "spec-1", "spec-2", classification="none")
        state = self.ordinary(state, "test-strategy")
        work_items = [
            {"id": "W1", "title": "First bounded work item"},
            {"id": "W2", "title": "Second bounded work item"},
        ]
        state = self.ordinary(state, "plan", work_items=work_items)
        self.assertEqual(state["stage"], "plan-improve")

        updated_queue = [
            *work_items,
            {"id": "W3", "title": "Added during the accepted plan review"},
        ]
        state = self.review(
            state, "plan-0", "plan-1", work_items=updated_queue
        )
        self.assertEqual([row["id"] for row in state["work_items"]], ["W1", "W2", "W3"])
        self.assertEqual(state["stage"], "plan-improve")
        state = self.review(state, "plan-1", "plan-2", classification="none")
        self.assertEqual((state["stage"], state["work_items"][state["work_index"]]["id"]), ("step-plan", "W1"))

        state = self.ordinary(state, "step-plan")
        state = self.review(state, "step-0", "step-shared")
        self.assertEqual(state["stage"], "step-plan-improve")
        state = self.review(state, "step-shared", "step-w1-final", classification="none")
        for stage in ("implement", "test-refine", "test-author"):
            state = self.ordinary(state, stage)
        state = self.ordinary(state, "document", choices={"skill_required": False})
        state = self.ordinary(state, "verify")
        state = self.finish_campaign(state, "product-w1")
        state = self.ordinary(state, "integrate")
        state = self.ordinary(state, "carry-forward")
        self.assertEqual((state["stage"], state["work_items"][state["work_index"]]["id"]), ("step-plan", "W2"))

        state = self.ordinary(state, "step-plan")
        # The same descriptor must not let W2 inherit W1's step-plan campaign.
        state = self.review(state, "step-w1-final", "step-w2-first")
        self.assertEqual(state["stage"], "step-plan-improve")


class ReviewReceiptCLITests(unittest.TestCase):
    """Fresh-process public CLI coverage with no Git repository or commits."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-review-receipts-cli-")
        self.base = Path(self.temp.name)
        self.run_dir = self.base / "run"
        self.repo = self.base / "zero-git-project"
        self.repo.mkdir()
        self.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def process(self, argv: list[str], *, code: int = 0) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            argv,
            cwd=self.repo,
            env=self.env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if code == 0:
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        else:
            self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        return self.process([sys.executable, "-B", str(CLI), *args], code=code)

    def state(self) -> dict[str, object]:
        return store.read_record(self.run_dir / "state.md")

    def start(self) -> str:
        packet = self.cli(
            "init",
            "--repo", str(self.repo),
            "--run-dir", str(self.run_dir),
            "--prompt", "Exercise result-only navigator review receipts.",
            "--review-receipts",
        ).stdout
        self.assertEqual(self.state()["navigator_protocol_version"], 2)
        self.assertFalse((self.repo / ".git").exists())
        return packet

    def callback(self, packet: str) -> tuple[Path, list[str]]:
        callback_path = Path(
            packet.split("Write the structured result to: ", 1)[1].splitlines()[0]
        )
        command = shlex.split(
            packet.split("Call this when done:\n", 1)[1].splitlines()[0]
        )
        self.assertEqual(command[0], "python3")
        self.assertIn(command[2], {"done", "complete"})
        self.assertFalse(any(part == "--action" or part.startswith("--action=") for part in command))
        self.assertTrue(any(part == "--run-dir" or part.startswith("--run-dir=") for part in command))
        self.assertTrue(any(part == "--result" or part.startswith("--result=") for part in command))
        self.assertEqual(callback_path.parent, self.run_dir.resolve() / "inbox")
        self.assertTrue(callback_path.name.startswith("nav-"))
        self.assertEqual(callback_path.suffix, ".md")
        return callback_path, [sys.executable, *command[1:]]

    def submit(self, packet: str, result: dict[str, object]) -> tuple[subprocess.CompletedProcess[str], Path, list[str]]:
        callback, command = self.callback(packet)
        store.write_record(callback, result, title="Synthetic navigator receipt")
        return self.process(command), callback, command

    def to_research_improve(self) -> str:
        packet = self.start()
        for stage in ("intake", "discovery", "research"):
            self.assertEqual(self.state()["stage"], stage)
            packet, _, _ = self.submit(packet, generic_result(summary=f"Finished {stage}."))
            packet = packet.stdout
        self.assertEqual(self.state()["stage"], "research-improve")
        return packet

    def test_v1_cli_still_rejects_a_result_only_callback_without_mutation(self) -> None:
        legacy_run = self.base / "legacy-v1-run"
        packet = self.cli(
            "init",
            "--repo", str(self.repo),
            "--run-dir", str(legacy_run),
            "--prompt", "Keep the legacy navigator callback binding.",
        ).stdout
        state = store.read_record(legacy_run / "state.md")
        self.assertEqual(state["navigator_protocol_version"], 1)
        callback = Path(
            packet.split("Write the structured result to: ", 1)[1].splitlines()[0]
        )
        command = shlex.split(
            packet.split("Call this when done:\n", 1)[1].splitlines()[0]
        )
        action_flag = next(
            part for part in command if part == "--action" or part.startswith("--action=")
        )
        self.assertTrue(action_flag)
        store.write_record(callback, generic_result(), title="Legacy callback")
        without_action = [part for part in command if part != action_flag]
        if action_flag == "--action":
            without_action.remove(command[command.index(action_flag) + 1])
        before = (legacy_run / "state.md").read_bytes()
        self.process([sys.executable, *without_action[1:]], code=1)
        self.assertEqual((legacy_run / "state.md").read_bytes(), before)
        self.process([sys.executable, *command[1:]])

    def test_review_receipts_flag_never_changes_legacy_or_other_execution_modes(self) -> None:
        for mode in ("managed", "legacy"):
            with self.subTest(mode=mode):
                rejected_run = self.base / f"{mode}-review-receipts"
                self.cli(
                    "init",
                    "--repo", str(self.repo),
                    "--run-dir", str(rejected_run),
                    "--prompt", "Reject an incompatible receipt mode.",
                    "--review-receipts",
                    "--execution-mode", mode,
                    code=1,
                )
                self.assertFalse(rejected_run.exists())

        legacy_run = self.base / "existing-v1-run"
        self.cli(
            "init",
            "--repo", str(self.repo),
            "--run-dir", str(legacy_run),
            "--prompt", "Existing v1 navigator state must not be upgraded.",
        )
        before = {
            str(path.relative_to(legacy_run)): path.read_bytes()
            for path in legacy_run.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        self.cli(
            "init",
            "--repo", str(self.repo),
            "--run-dir", str(legacy_run),
            "--prompt", "Existing v1 navigator state must not be upgraded.",
            "--review-receipts",
            code=1,
        )
        after = {
            str(path.relative_to(legacy_run)): path.read_bytes()
            for path in legacy_run.rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        self.assertEqual(after, before)

    def test_result_only_public_flow_pause_replay_and_artifact_retention(self) -> None:
        packet = self.to_research_improve()
        self.assertIn("Current node: research-improve", packet)
        self.assertIn("Action: " + self.state()["action"]["id"], packet)
        callback, command = self.callback(packet)
        before_missing = (self.run_dir / "state.md").read_bytes()
        store.write_record(
            callback,
            generic_result(summary="This v2 Improve result omits its review."),
            title="Missing v2 review",
        )
        self.process(command, code=1)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), before_missing)

        first = review_result("research-0", "research-1")
        store.write_record(callback, first, title="First v2 review")
        first_completion = self.process(command)
        packet = first_completion.stdout
        after_first = self.state()
        first_action = callback.stem
        self.assertEqual(after_first["stage"], "research-improve")
        result_record = self.run_dir / "results" / f"{first_action}.md"
        self.assertEqual(store.read_record(result_record)["result"], first)

        # Result-only replay is idempotent even when the old callback is stale.
        accepted_bytes = (self.run_dir / "state.md").read_bytes()
        self.process(command)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), accepted_bytes)
        self.process([*command, "--action", first_action])
        self.assertEqual((self.run_dir / "state.md").read_bytes(), accepted_bytes)
        self.process([*command, "--action", "nav-00000000000000000000000000000000"], code=1)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), accepted_bytes)

        store.write_record(
            callback,
            review_result("research-0", "changed-replay"),
            title="Conflicting stale v2 review",
        )
        self.process(command, code=1)
        self.assertEqual((self.run_dir / "state.md").read_bytes(), accepted_bytes)

        self.cli("pause", "--run-dir", str(self.run_dir), "--reason", "Cold context handoff.")
        cold_pause = self.cli("next", "--run-dir", str(self.run_dir)).stdout
        self.assertIn("Paused, unfinished", cold_pause)
        self.assertNotIn("Call this when done:", cold_pause)
        resumed = self.cli("resume", "--run-dir", str(self.run_dir)).stdout
        second_callback, second_command = self.callback(resumed)
        self.assertNotEqual(second_callback.stem, first_action)
        store.write_record(
            second_callback,
            review_result("research-1", "research-2", classification="none"),
            title="Second v2 review after cold resume",
        )
        self.process(second_command)
        self.assertEqual(self.state()["stage"], "spec")
        self.assertFalse((self.repo / ".git").exists())

        self.cli("halt", "--run-dir", str(self.run_dir), "--reason", "Retain the partial review receipt report.")
        report = (self.run_dir / "report.html").read_text(encoding="utf-8")
        self.assertIn("research-improve", report)
        self.assertIn("notes/review-receipt.md", report)
        self.assertEqual(store.read_record(result_record)["result"], first)

    def test_two_concurrent_duplicate_callbacks_accept_one_review_iteration(self) -> None:
        packet = self.to_research_improve()
        callback, command = self.callback(packet)
        store.write_record(
            callback,
            review_result("concurrent-0", "concurrent-1"),
            title="Concurrent duplicate v2 review",
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            completed = list(executor.map(lambda _: self.process(command), range(2)))
        self.assertTrue(all(result.returncode == 0 for result in completed))
        state = self.state()
        reviews = [entry for entry in state["history"] if entry["stage"] == "research-improve"]
        self.assertEqual(len(reviews), 1)
        self.assertEqual(state["stage"], "research-improve")
        self.assertNotEqual(state["action"]["id"], callback.stem)

    def test_fresh_process_v2_walk_reaches_handoff_and_retains_every_receipt(self) -> None:
        """Drive current packets, not an independently duplicated stage list."""
        packet = self.start()
        review_number: dict[str, int] = {}
        candidate_after: dict[str, str] = {}
        iterations = 0
        improve_stages = {
            "research-improve",
            "spec-improve",
            "plan-improve",
            "step-plan-improve",
            "product-improve",
            "outer-improve",
        }
        while self.state()["status"] != "done":
            iterations += 1
            self.assertLess(iterations, 48, "v2 public walk did not converge to handoff")
            stage = self.state()["stage"]
            if stage in improve_stages:
                number = review_number.get(stage, 0) + 1
                review_number[stage] = number
                before = candidate_after.get(stage, f"{stage}-candidate-0")
                after = f"{stage}-candidate-{number}"
                candidate_after[stage] = after
                payload = review_result(
                    before,
                    after,
                    classification="trivial" if number == 1 else "none",
                )
            elif stage == "document":
                payload = generic_result(choices={"skill_required": False})
            else:
                payload = generic_result(summary=f"Completed public v2 {stage}.")
            completed, _, _ = self.submit(packet, payload)
            packet = completed.stdout

        state = self.state()
        self.assertEqual((state["stage"], state["status"]), ("done", "done"))
        report = (self.run_dir / "report.html").read_text(encoding="utf-8")
        self.assertIn("Outcome: complete", report)
        self.assertIn("handoff", report)
        result_records = list((self.run_dir / "results").glob("*.md"))
        self.assertEqual(len(result_records), len(state["history"]))
        self.assertTrue(all(store.read_record(path)["result"] for path in result_records))
        self.assertFalse((self.repo / ".git").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
