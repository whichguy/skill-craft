#!/usr/bin/env python3
"""End-to-end action-walk acceptance coverage for the ShipLoop protocol.

The test deliberately uses the extensionless public CLI as a subprocess.  It
does not fake an action transition: each transition consumes a Markdown result
record, every check is a real ``python -B`` command, and every Improve commit
is made in the allocated Git worktree.
"""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
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


class ShipLoopActionWalkTests(unittest.TestCase):
    """One real two-step walk plus narrow protocol-negatives."""

    product_one = "s1.txt contains exactly one line: first"
    product_two = "s2.txt contains exactly one line: second"
    done_sentence = product_two

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-action-walk-")
        self.root = Path(self.temp.name)
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

    def complete(self, payload, *, action_id=None, code=0, label="result"):
        aid = action_id or self.action_id()
        result = self.record(label, payload)
        return self.cli(
            "complete", "--action", aid, "--result", result, code=code
        ), result

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
        }
        return (
            "Fixture survey.\n\n## machine\n```json\n"
            + json.dumps(machine, indent=2)
            + "\n```\n"
        )

    def step(self, sid, product, inputs, statement):
        return {
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
        }

    def initial_dag(self):
        return {
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

    def bootstrap_to_first_implementation(self):
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
        self.complete(
            {
                "summary": "The approach separates initial delivery, per-step verification, and outer checks.",
                "body": "# Approach\n\nCreate two dependent files with exact-output tests and review each increment.\n",
            },
            label="approach",
        )
        self.complete(
            {
                "summary": "Survey captured a greenfield fixture and no external routes.",
                "body": self.machine_markdown(),
            },
            label="survey",
        )
        self.complete(
            {
                "summary": "No external research is needed for this local fixture.",
                "body": "The fixture uses Python standard library checks and Git worktrees.\n",
            },
            label="research",
        )
        self.complete(
            {
                "summary": "The target is checkable by exact file contents.",
                "body": f"done_sentence: {self.done_sentence}\ncheckable: true\n",
                "lifecycle": {
                    "acceptance": [self.product_one, self.product_two],
                    "preparation": "none",
                    "publish": "none",
                    "quality": True,
                    "reason": "Local files require no outer preparation or publication.",
                },
            },
            label="spec",
        )
        self.complete(
            {
                "summary": "The dependency sequence creates S1 before S2 and maps tests to both outputs.",
                "dependency_review": "Backward prerequisite audit: S2 consumes S1 output; S1 consumes the established repository baseline; no missing producers or cycles.",
                "plan": self.plan_markdown(),
                "dag": self.initial_dag(),
            },
            label="sequence",
        )
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
        word = "first" if sid == "S1" else "second"
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
            word = "first" if sid == "S1" else "second"
            filename = f"{sid.lower()}.py"
            textfile = f"{sid.lower()}.txt"
            products = [self.product_one if sid == "S1" else self.product_two]
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
                    "id": "exact-output",
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

    def formatted_commit(
        self,
        sid,
        iteration,
        verification_action,
        review_learning,
        apply_learning,
        *,
        allow_empty=True,
    ):
        wt = self.worktree(sid)
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
        self, sid, *, material, invalid_commit_first=False, missing_learning_first=False
    ):
        """Exercise history -> plan -> apply -> fresh checks -> primary commit."""
        self.assertEqual(self.state()["stage"], "review")
        review_action = self.action_id()
        self.cli("history", "--action", review_action, "--limit", "7", "--skip", "0")
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
        self.complete(
            {
                "summary": "History and the current worktree were reviewed before planning improvements.",
                "findings": findings,
                "test_review": "The exact-output test covers the declared product and syntax check covers source parsing.",
                "learnings": review_learning,
            },
            action_id=review_action,
            label=f"{sid}-review",
        )
        self.assertEqual(self.state()["stage"], "improve-plan")
        self.complete(
            {
                "summary": "The plan maps the review finding to one scoped adjustment and keeps the test intact.",
                "body": "# Improve plan\n\nPreserve exact-output coverage and record the scoped learning.\n",
            },
            label=f"{sid}-improve-plan",
        )
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
        self.assertEqual(self.state()["stage"], "commit")
        receipt = self.receipt(sid)
        iteration = copy.deepcopy(receipt["iteration"])
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
        primary = self.formatted_commit(
            sid, iteration, verification_action, review_learning, apply_learning
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
            expected = "first" if sid == "S1" else "second"
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
                "summary": "Fresh final checks passed after both trivial-only iterations."
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
        self.complete(post_payload, label=f"{sid}-post-inner")
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
        return before_post_inner

    def test_action_walk_enforces_evidence_history_commits_revision_and_terminal_journal(
        self,
    ):
        self.bootstrap_to_first_implementation()
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

        self.finish_step("S2", revise=False, material_first=False)
        self.assertEqual((self.repo / "s2.txt").read_text(encoding="utf-8"), "second\n")
        self.assertEqual(self.state()["stage"], "coverage")
        self.complete(
            {
                "summary": "The explicit bound-plan waiver permits the fixture to finish outer coverage."
            },
            label="coverage",
        )
        self.assertEqual(self.state()["stage"], "quality")
        self.verify_current(
            self.manifest_for("S2", quality=True), label="whole-product-checks"
        )
        self.complete(
            {
                "summary": "Whole-product lint and exact-output checks passed after both merges.",
                "test_review": "Both declared lifecycle acceptance criteria are covered by an exact-output check.",
                "quality_review": "The merged fixture remains limited to its two declared exact-output acceptance criteria.",
            },
            label="quality",
        )
        self.assertEqual(self.state()["stage"], "handoff")
        self.complete(
            {
                "summary": "The fixture is complete with durable journal proposals available for later skill maintenance.",
                "journal": [],
            },
            label="handoff",
        )
        terminal = self.state()
        self.assertEqual((terminal["phase"], terminal["stage"]), ("done", "done"))
        self.assertNotIn("active_step", terminal)
        journal = store.read_record(self.run_dir / "shiploop-improvements.md")
        self.assertEqual(len(journal), 1)
        self.assertEqual(journal[0]["title"], "Keep action receipts compact")
        self.assertTrue((self.run_dir / "handoff.md").is_file())
        self.assertFalse(
            Path(s1_before["worktree"]).exists(),
            "journal must survive disposable worktree removal",
        )

    def test_twelve_material_cycles_do_not_converge(self):
        receipt = {
            "improve_cycles": [
                {"outcome": "material", "primary_commit": f"c{i}"} for i in range(12)
            ]
        }
        self.assertFalse(CORE.improve_two_clean(receipt))

    def test_primary_commit_cannot_substitute_recorded_learnings(self):
        self.bootstrap_to_first_implementation()
        self.start_step("S1", exercise_failed_and_stale=False)
        self.run_improve_iteration("S1", material=False, missing_learning_first=True)
        cycles = self.receipt("S1")["improve_cycles"]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["outcome"], "trivial")

    def test_review_requires_every_available_history_body_not_only_first_page(self):
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
        rejected, _ = self.complete(
            {
                "summary": "A one-commit page was reviewed.",
                "findings": [],
                "test_review": "The implementation check remains the active evidence.",
                "learnings": "One page does not cover all available commit bodies.",
            },
            action_id=action,
            code=2,
            label="partial-history-review",
        )
        self.assertIn("latest seven", rejected.stderr)
        self.assertEqual(self.state()["stage"], "review")
        self.cli("history", "--action", action, "--limit", "1", "--skip", "1")
        self.complete(
            {
                "summary": "Every available commit body was reviewed through bounded pages.",
                "findings": [],
                "test_review": "The implementation check remains the active evidence.",
                "learnings": "Paged history can cover the complete available history without a large packet.",
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
        blocked = self.cli("status", code=2)
        self.assertIn("foreign worktree", blocked.stderr)
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
        self.complete(
            {
                "summary": "The explicit bound-plan waiver permits the fixture to enter the outer quality review."
            },
            label="outer-replan-coverage",
        )
        self.assertEqual(self.state()["stage"], "quality")
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
        state = self.state()
        self.assertEqual(
            (state["phase"], state["stage"], state["active_step"]),
            ("implement", "implement", "S3"),
        )
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
