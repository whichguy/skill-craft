#!/usr/bin/env python3
"""Pure durable-record tests for ShipLoop's generic objective convergence."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_objectives as objectives  # noqa: E402
import shiploop_evidence as evidence  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402
import shiploop_store as store  # noqa: E402


CLI = SCRIPTS / "shiploop"


class GitCore:
    """Minimal real-Git adapter for protocol helper tests."""

    @staticmethod
    def git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )


class ObjectiveRecordTests(unittest.TestCase):
    """The generic loop must be receipt-derived, not host-claim-derived."""

    BODY = "# Candidate\n\nThe durable approach covers the bounded fixture.\n"

    @staticmethod
    def context() -> dict[str, str]:
        return {
            "git_baseline": "a" * 40,
            "committed_tree_sha256": "b" * 40,
            "worktree_fingerprint": "c" * 64,
            "status_sha256": "d" * 64,
            "spec_sha256": "e" * 64,
            "environment_sha256": "f" * 64,
            "behavior_sha256": "1" * 64,
            "plan_sha256": "2" * 64,
            "knowledge_sha256": "3" * 64,
        }

    def receipt(self) -> dict:
        loop = objectives.loop_id("20260912T012900Z-192c6d00", "approach")
        return objectives.new_receipt(
            loop=loop,
            kind="approach",
            base_stage="approach",
            candidate_body=self.BODY,
            context=self.context(),
        )

    @staticmethod
    def finding(
        finding_id: str = "F-001", *, severity: str = "material"
    ) -> dict[str, str]:
        return {
            "id": finding_id,
            "severity": severity,
            "category": "edge-condition",
            "summary": "The bounded workflow must state its empty-input outcome.",
        }

    def write_receipt(self, root: Path, receipt: dict) -> None:
        candidate = root / receipt["candidate_path"]
        candidate.parent.mkdir(parents=True)
        candidate.write_text(self.BODY, encoding="utf-8")
        store.write_record(root / objectives.receipt_name(receipt["loop_id"]), receipt)

    def test_candidate_and_context_are_bound_to_markdown_receipt(self) -> None:
        receipt = self.receipt()
        with tempfile.TemporaryDirectory(prefix="shiploop-objective-") as raw:
            root = Path(raw)
            self.write_receipt(root, receipt)
            self.assertEqual(
                objectives.assert_receipt(root, store.read_record(root / objectives.receipt_name(receipt["loop_id"])))["context"],
                self.context(),
            )
            (root / receipt["candidate_path"]).write_text(self.BODY + "drift\n", encoding="utf-8")
            with self.assertRaises(objectives.ObjectiveError):
                objectives.assert_receipt(root, receipt)

    def test_review_requires_full_body_history_and_preserves_open_findings(self) -> None:
        receipt = self.receipt()
        with self.assertRaises(objectives.ObjectiveError):
            objectives.record_history(
                receipt,
                [{"sha": "a" * 40, "subject": "subject only"}],
                head="a" * 40,
                skip=0,
            )
        objectives.record_history(
            receipt,
            [{"sha": "a" * 40, "body": "A complete verbose commit body."}],
            head="a" * 40,
            skip=0,
        )
        objectives.apply_review(receipt, [self.finding()])
        objectives.apply_review(receipt, [])
        self.assertEqual(objectives.open_ids(receipt), {"F-001"})

    def test_two_verified_trivial_audits_are_only_ready(self) -> None:
        receipt = self.receipt()
        for number, commit in enumerate(("a" * 40, "b" * 40), start=1):
            current = receipt["current_pass"]
            current.update(
                review={"learnings": f"Review learning {number}."},
                plan={"learnings": f"Plan learning {number}."},
                apply={"learnings": f"Apply learning {number}."},
            )
            completed = objectives.complete_pass(
                receipt,
                commit=commit,
                outcome="trivial",
            )
            self.assertTrue(completed["verified"])
            if number == 1:
                objectives.start_next_pass(receipt, context=self.context())
        self.assertEqual(objectives.decide(receipt), {"phase": "ready", "trivial_streak": 2})
        self.assertFalse(receipt.get("certificate"))

    def test_material_review_resets_until_streak_and_all_open_findings_need_evidence(self) -> None:
        receipt = self.receipt()
        objectives.apply_review(receipt, [self.finding()])
        with self.assertRaises(objectives.ObjectiveError):
            objectives.resolve_findings(receipt, [], ["F-001"])
        objectives.resolve_findings(
            receipt,
            [{"id": "F-001", "evidence": "Candidate adds the expected empty-input outcome."}],
            ["F-001"],
        )
        receipt["current_pass"].update(
            review={"learnings": "Review records the material edge condition."},
            plan={"learnings": "Plan covers the material edge condition."},
            apply={"learnings": "Apply records the material correction."},
        )
        objectives.complete_pass(receipt, commit="a" * 40, outcome="material")
        self.assertEqual(objectives.decide(receipt), {"phase": "active", "trivial_streak": 0})

    def test_abandoned_objective_cannot_be_certified(self) -> None:
        receipt = self.receipt()
        archived = objectives.abandon_objective(
            receipt,
            reason="The pre-contract environment changed and needs a fresh pass.",
            context=self.context(),
        )
        self.assertEqual(archived["status"], "abandoned")
        self.assertEqual(receipt["status"], "abandoned")
        with self.assertRaises(objectives.ObjectiveError):
            objectives.certificate(
                receipt,
                final_check_action="objective-final",
                final_check_sha256="f" * 64,
                audit_head="a" * 40,
            )


class FullHistoryPagingTests(unittest.TestCase):
    """Normal review helpers share the objective last-ten body contract."""

    def test_index_alone_is_rejected_but_ten_one_commit_pages_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-history-pages-") as raw:
            repo = Path(raw) / "repo"
            root = repo / ".shiploop"
            repo.mkdir()
            root.mkdir()
            env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
            for args in (
                ("init", "-q"),
                ("config", "user.name", "History Test"),
                ("config", "user.email", "history@example.invalid"),
            ):
                process = subprocess.run(
                    ["git", "-C", str(repo), *args], capture_output=True, text=True, env=env
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            for number in range(10):
                process = subprocess.run(
                    ["git", "-C", str(repo), "commit", "--allow-empty", "-qm", f"history {number}"],
                    capture_output=True,
                    text=True,
                    env=env,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            index_rows = evidence.history(repo, 10, 0)
            (root / "history-pages").mkdir()
            (root / "history-pages/index-only.md").write_text(
                store.dumps(index_rows, "Git history — full commit bodies"), encoding="utf-8"
            )
            iteration: dict = {}
            with self.assertRaises(protocol.ProtocolError):
                protocol.require_full_history(GitCore(), root, iteration, repo, label="test review")
            head = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                env=env,
                check=True,
            ).stdout.strip()
            for skip in range(10):
                rows = evidence.history(repo, 1, skip)
                path = f"history-pages/page-{skip}.md"
                protocol.record_full_history_page(
                    iteration,
                    rows,
                    head=head,
                    skip=skip,
                    limit=1,
                    archive_path=path,
                )
                (root / path).write_text(
                    store.dumps(rows, "Git history — full commit bodies"), encoding="utf-8"
                )
            protocol.require_full_history(GitCore(), root, iteration, repo, label="test review")


class FinalVerifyBindingTests(unittest.TestCase):
    """Fresh final checks cannot replace the converged inner-cycle proof."""

    def test_late_commit_or_staged_edit_is_rejected_before_final_check(self) -> None:
        class FinalCore(GitCore):
            @staticmethod
            def improve_two_clean(rec: dict) -> bool:
                return True

        def command(repo: Path, *args: str) -> str:
            process = subprocess.run(
                ["git", "-C", str(repo), *args], capture_output=True, text=True
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            return process.stdout.strip()

        for mode in ("commit", "staged"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                prefix="shiploop-final-binding-"
            ) as raw:
                repo = Path(raw) / "repo"
                root = repo / ".shiploop"
                repo.mkdir()
                command(repo, "init", "-q")
                command(repo, "config", "user.name", "Final Binding Test")
                command(repo, "config", "user.email", "final-binding@example.invalid")
                command(repo, "commit", "--allow-empty", "-qm", "baseline")
                baseline = command(repo, "rev-parse", "HEAD")
                (repo / "fixture.txt").write_text("verified\n", encoding="utf-8")
                command(repo, "add", "fixture.txt")
                root.mkdir()
                manifest = {
                    "checks": [
                        {
                            "id": "lint",
                            "kind": "lint",
                            "argv": [sys.executable, "-B", "-c", "raise SystemExit(0)"],
                            "acceptance": [],
                        },
                        {
                            "id": "acceptance",
                            "kind": "test",
                            "argv": [sys.executable, "-B", "-c", "raise SystemExit(0)"],
                            "acceptance": ["fixture product"],
                        },
                    ]
                }
                check_action = "final-binding-check"
                results = evidence.run_checks(
                    repo, manifest, root / "logs" / check_action, check_action
                )
                store.write_record(
                    root / "checks" / f"{check_action}.md",
                    {"manifest": manifest, "results": results},
                )
                iteration_id = "final-binding-iteration"
                message = "\n\n".join(
                    (
                        "Primary fixture commit",
                        "Review:\nReviewed the fixture before committing.",
                        "Changes:\nAdded the verified fixture artifact.",
                        "Validation:\nThe local lint and acceptance commands passed.",
                        "Key learnings:\nFinal proof remains bound to this exact primary commit.",
                        f"ShipLoop-Iteration: {iteration_id}",
                    )
                )
                command(repo, "commit", "-m", message)
                primary = command(repo, "rev-parse", "HEAD")
                state = {"repo_root": str(repo), "active_step": None}
                store.write_record(
                    root / "lifecycle.md", {"acceptance": ["fixture product"]}
                )
                rec = {
                    "worktree": str(repo),
                    "improve_cycles": [
                        {
                            "id": iteration_id,
                            "outcome": "trivial",
                            "primary_commit": primary,
                            "previous_sha": baseline,
                            "check_action": check_action,
                        }
                    ],
                }
                protocol.require_final_verify_convergence_bound(
                    FinalCore(), root, state, rec
                )
                if mode == "commit":
                    command(repo, "commit", "--allow-empty", "-qm", "late revision")
                    expected = "new source revision appeared"
                else:
                    (repo / "fixture.txt").write_text("late staged edit\n", encoding="utf-8")
                    command(repo, "add", "fixture.txt")
                    expected = "staged or uncommitted source changes appeared"
                with self.assertRaisesRegex(protocol.ProtocolError, expected):
                    protocol.require_final_verify_convergence_bound(
                        FinalCore(), root, state, rec
                    )


class ObjectiveProtocolSmokeTests(unittest.TestCase):
    """One public transition proves base results become tentative Markdown."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-objective-cli-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run = self.repo / ".shiploop"
        self.records = self.root / "records"
        self.records.mkdir()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "-q")
        self.git("config", "user.name", "Objective Test")
        self.git("config", "user.email", "objective@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", "/dev/null")
        self.git("commit", "--allow-empty", "-qm", "baseline")

    def git(self, *args: str) -> None:
        process = subprocess.run(
            ["git", "-C", str(self.repo), *args], capture_output=True, text=True, env=self.env
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        process = subprocess.run(
            [sys.executable, str(CLI), *args], cwd=self.repo, capture_output=True, text=True, env=self.env
        )
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return process

    def state(self) -> dict:
        return store.read_record(self.run / "state.md")

    def result(self, name: str, value: dict) -> str:
        path = self.records / f"{name}.md"
        store.write_record(path, value, title=f"Objective {name}")
        return str(path)

    def complete(self, value: dict, name: str, *, code: int = 0) -> subprocess.CompletedProcess[str]:
        return self.cli(
            "complete",
            "--action",
            self.state()["action"]["id"],
            "--result",
            self.result(name, value),
            code=code,
        )

    def objective_receipt(self) -> tuple[dict, dict]:
        state = self.state()
        binding = state["objective"]
        return state, store.read_record(self.run / binding["receipt"])

    def history_for_objective(self) -> None:
        state = self.state()
        self.assertEqual(state["stage"], "objective-review")
        self.cli(
            "history",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--limit",
            "10",
            "--skip",
            "0",
            "--full",
        )

    @staticmethod
    def review_result(label: str) -> dict:
        return {
            "summary": f"{label} review is complete.",
            "findings": [],
            "assessment": {
                key: f"{key} was inspected against the bounded local fixture."
                for key in objectives.ASSESSMENT_KEYS
            },
            "history_assessment": "The complete current Git body set contains the audit context.",
            "test_review": "The objective manifest runs a local lint and acceptance test.",
            "learnings": f"{label} review learning remains concrete.",
        }

    def enter_objective_apply(self, label: str) -> None:
        self.history_for_objective()
        action_id = self.state()["action"]["id"]
        self.complete(self.review_result(label), f"{label}-review")
        self.assertEqual(self.state()["last_completion"]["action"], action_id)
        self.assertEqual(self.state()["last_completion"]["stage"], "objective-review")
        self.assertEqual(self.state()["stage"], "objective-plan")
        self.complete(
            {
                "summary": f"{label} plan is complete.",
                "addresses": [],
                "body": f"# {label} plan\n\nNo open findings require a candidate correction.\n",
                "learnings": f"{label} plan learning remains concrete.",
            },
            f"{label}-plan",
        )
        self.assertEqual(self.state()["stage"], "objective-apply")

    def trivial_objective_pass(self, label: str) -> None:
        self.enter_objective_apply(label)
        self.complete(
            {
                "summary": f"{label} candidate is retained.",
                "candidate": {
                    "summary": "Approach captures the bounded test objective.",
                    "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
                },
                "material": False,
                "addresses": [],
                "resolutions": [],
                "test_changes": "Existing local lint and acceptance checks already cover this candidate.",
                "learnings": f"{label} apply learning remains concrete.",
            },
            f"{label}-apply",
        )
        self.assertEqual(self.state()["stage"], "objective-verify")
        manifest = {
            "checks": [
                {
                    "id": "lint",
                    "kind": "lint",
                    "argv": ["/usr/bin/true"],
                    "acceptance": ["objective approach"],
                },
                {
                    "id": "acceptance",
                    "kind": "test",
                    "argv": ["/usr/bin/true"],
                    "acceptance": ["objective approach"],
                },
            ]
        }
        manifest_path = self.result(f"{label}-manifest", manifest)
        state, receipt = self.objective_receipt()
        self.cli(
            "planning-verify",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--manifest",
            manifest_path,
        )
        self.complete({"summary": f"{label} checks pass."}, f"{label}-verify")
        self.assertEqual(self.state()["stage"], "objective-commit")
        state, receipt = self.objective_receipt()
        current = receipt["current_pass"]
        body = "\n\n".join(
            (
                f"Objective {label} audit",
                "Review:\n" + current["review"]["learnings"],
                "Changes:\n" + current["plan"]["learnings"] + "\n" + current["apply"]["learnings"],
                "Validation:\nThe local lint and acceptance commands passed without source changes.",
                "Key learnings:\n" + current["review"]["learnings"] + "\n" + current["plan"]["learnings"] + "\n" + current["apply"]["learnings"],
                "ShipLoop-Iteration: " + current["id"],
            )
        )
        self.git("commit", "--allow-empty", "--only", "-m", body)
        commit = subprocess.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            env=self.env,
            check=True,
        ).stdout.strip()
        self.complete(
            {"summary": f"{label} audit commit is recorded.", "commit": commit},
            f"{label}-commit",
        )

    def finalize_approach_objective(self) -> None:
        self.trivial_objective_pass("first")
        self.assertEqual(self.state()["stage"], "objective-review")
        self.trivial_objective_pass("second")
        self.assertEqual(self.state()["stage"], "objective-finalize")
        state = self.state()
        manifest_path = self.result(
            "final-manifest",
            {
                "checks": [
                    {
                        "id": "lint",
                        "kind": "lint",
                        "argv": ["/usr/bin/true"],
                        "acceptance": ["objective approach"],
                    },
                    {
                        "id": "acceptance",
                        "kind": "test",
                        "argv": ["/usr/bin/true"],
                        "acceptance": ["objective approach"],
                    },
                ]
            },
        )
        self.cli(
            "planning-verify",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--manifest",
            manifest_path,
        )
        self.complete({"summary": "Fresh final objective check passes."}, "finalize")
        self.assertEqual(self.state()["stage"], "survey")

    def test_approach_is_tentative_until_generic_objective_finalization(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Bounded objective smoke test.")
        state = self.state()
        self.assertEqual(state["objective_protocol_version"], objectives.VERSION)
        self.assertEqual(state["step_contract_protocol_version"], 1)
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.assertEqual(self.state()["stage"], "approach")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        state = self.state()
        self.assertEqual(state["stage"], "objective-review")
        binding = state["objective"]
        self.assertEqual(binding["kind"], "approach")
        self.assertTrue((self.run / binding["candidate"]).is_file())
        receipt = store.read_record(self.run / binding["receipt"])
        self.assertEqual(receipt["base_stage"], "approach")
        self.assertEqual(receipt["completed_passes"], [])
        self.cli(
            "history",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--limit",
            "10",
            "--skip",
            "0",
        )
        page = self.run / objectives.history_page_name(
            binding["loop_id"], receipt["current_pass"]["id"], 0
        )
        index = self.run / objectives.history_index_name(
            binding["loop_id"], receipt["current_pass"]["id"], 0
        )
        self.assertFalse(page.exists())
        self.assertTrue(index.is_file())

    def test_history_index_does_not_satisfy_objective_review(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Objective history index test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        state, receipt = self.objective_receipt()
        self.cli(
            "history",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--limit",
            "10",
            "--skip",
            "0",
        )
        self.assertFalse(
            (self.run / objectives.history_page_name(
                state["objective"]["loop_id"], receipt["current_pass"]["id"], 0
            )).exists()
        )
        failed = self.complete(self.review_result("index"), "index-review", code=2)
        self.assertIn("full-body history", failed.stderr)
        self.assertEqual(self.state()["stage"], "objective-review")

    def test_single_commit_full_pages_cover_the_latest_ten_objective_bodies(self) -> None:
        for number in range(9):
            self.git("commit", "--allow-empty", "-qm", f"history body {number}")
        self.cli("init", "--repo", str(self.repo), "--prompt", "Objective paged history test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        state = self.state()
        # Subject-only navigation is intentionally not proof.  A tiny context
        # may then retrieve the same current ten bodies one page at a time.
        self.cli(
            "history", "--run-dir", str(self.run), "--action", state["action"]["id"],
            "--limit", "10", "--skip", "0",
        )
        for skip in range(10):
            self.cli(
                "history", "--run-dir", str(self.run), "--action", state["action"]["id"],
                "--limit", "1", "--skip", str(skip), "--full",
            )
        review_action = self.state()["action"]["id"]
        self.complete(self.review_result("paged"), "paged-review")
        self.assertEqual(self.state()["stage"], "objective-plan")
        self.assertEqual(self.state()["last_completion"]["action"], review_action)
        self.assertEqual(self.state()["last_completion"]["stage"], "objective-review")

    def test_candidate_rewrite_cannot_claim_a_trivial_objective_apply(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Objective material apply test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        self.enter_objective_apply("material")
        _, receipt = self.objective_receipt()
        original = receipt["candidate_sha256"]
        for number in (1, 2):
            failed = self.complete(
                {
                    "summary": f"Rewrite {number} is proposed.",
                    "candidate": {
                        "summary": f"Approach rewrite {number} changes the candidate.",
                        "body": f"# Approach\n\nMeaningful candidate rewrite {number}.\n",
                    },
                    "material": False,
                    "addresses": [],
                    "resolutions": [],
                    "test_changes": "No test command changes are proposed.",
                    "learnings": "A candidate rewrite must be treated as material.",
                },
                f"rewrite-{number}",
                code=2,
            )
            self.assertIn("candidate changes are material", failed.stderr)
            self.assertEqual(self.state()["stage"], "objective-apply")
            _, after = self.objective_receipt()
            self.assertEqual(after["candidate_sha256"], original)

    def test_approach_repair_archives_the_pass_and_rebinds_fresh_context(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Objective repair test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        state, receipt = self.objective_receipt()
        pass_id = receipt["current_pass"]["id"]
        self.cli(
            "repair",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--reason",
            "The local pre-contract environment changed before review.",
        )
        after_state, after = self.objective_receipt()
        self.assertEqual(after_state["stage"], "objective-review")
        self.assertEqual(after["status"], "active")
        self.assertEqual(after["epoch"], 2)
        self.assertEqual(after["abandoned_passes"][-1]["id"], pass_id)
        self.assertTrue(
            (self.run / objectives.abandoned_name(after_state["objective"]["loop_id"], pass_id)).is_file()
        )

    def test_objective_start_snapshots_an_imported_dag_without_its_draft_path(self) -> None:
        class GitCore:
            @staticmethod
            def git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["git", "-C", str(repo), *args],
                    capture_output=True,
                    text=True,
                )

        self.run.mkdir()
        draft = self.records / "sequence-draft.md"
        original_dag = {"goal": "Snapshot the imported sequence.", "steps": []}
        changed_dag = {"goal": "Mutated after candidate snapshot.", "steps": []}
        store.write_record(draft, original_dag, title="Sequence draft")
        state = {
            "run_id": "20260912T012900Z-abc12345",
            "repo_root": str(self.repo),
            "objective_epoch": 0,
            "phase": "plan",
            "stage": "sequence",
            "action": {"id": "draft-snapshot", "stage": "sequence"},
        }
        writes: dict[str, str] = {}
        protocol.objective_start(
            GitCore(),
            self.run,
            state,
            "sequence",
            {
                "summary": "The imported DAG is ready for objective review.",
                "dag": original_dag,
                "dag_file": str(draft),
            },
            writes,
        )
        store.write_record(draft, changed_dag, title="Sequence draft")
        candidate = store.loads(writes[state["objective"]["candidate"]])
        self.assertEqual(candidate["dag"], original_dag)
        self.assertNotIn("dag_file", candidate)

    def test_survey_revisit_archives_the_active_objective_pass(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Objective revisit archive test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        self.finalize_approach_objective()
        self.complete(
            {
                "summary": "Survey is ready for objective review.",
                "body": "# Survey\n\nThe local environment is still under review.\n",
            },
            "survey",
        )
        state, receipt = self.objective_receipt()
        binding = dict(state["objective"])
        pass_id = receipt["current_pass"]["id"]
        self.cli(
            "revisit",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--to",
            "survey",
            "--reason",
            "The survey inputs changed before the objective review was complete.",
        )
        after = self.state()
        self.assertEqual(after["stage"], "survey")
        self.assertNotIn("objective", after)
        abandoned = store.read_record(self.run / binding["receipt"])
        self.assertEqual(abandoned["status"], "abandoned")
        self.assertEqual(abandoned["abandoned_passes"][-1]["id"], pass_id)
        archive = self.run / objectives.abandoned_name(binding["loop_id"], pass_id)
        self.assertTrue(archive.is_file())
        self.assertEqual(store.read_record(archive), abandoned["abandoned_passes"][-1])

    def test_two_trivial_audited_passes_need_a_fresh_final_check_before_approach_applies(self) -> None:
        self.cli("init", "--repo", str(self.repo), "--prompt", "Bounded objective convergence test.")
        self.complete({"summary": "Baseline is committed.", "baseline": "committed-head"}, "preflight")
        self.complete(
            {
                "summary": "Approach captures the bounded test objective.",
                "body": "# Approach\n\nUse durable Markdown evidence before every transition.\n",
            },
            "approach",
        )
        self.trivial_objective_pass("first")
        self.assertEqual(self.state()["stage"], "objective-review")
        self.trivial_objective_pass("second")
        self.assertEqual(self.state()["stage"], "objective-finalize")
        state = self.state()
        manifest_path = self.result(
            "final-manifest",
            {
                "checks": [
                    {
                        "id": "lint",
                        "kind": "lint",
                        "argv": ["/usr/bin/true"],
                        "acceptance": ["objective approach"],
                    },
                    {
                        "id": "acceptance",
                        "kind": "test",
                        "argv": ["/usr/bin/true"],
                        "acceptance": ["objective approach"],
                    },
                ]
            },
        )
        self.cli(
            "planning-verify",
            "--run-dir",
            str(self.run),
            "--action",
            state["action"]["id"],
            "--manifest",
            manifest_path,
        )
        self.complete({"summary": "Fresh final objective check passes."}, "finalize")
        self.assertEqual(self.state()["stage"], "survey")
        self.assertTrue((self.run / "approach.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
