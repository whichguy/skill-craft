#!/usr/bin/env python3
"""Hermetic real-Git tests for how a model reviews and returns an isolated run's candidate.

The first real return of both round-1 runs on 1.24.0 (Node Battleship, Node Checkers) was refused with "return plan has
unresolved path dispositions" and no path, and the model then hand-edited the script-owned return-plan.md (7 and 8 calls,
a blanket ``sed -i`` in one run, an invented status in the other).  These tests drive the real CLI through that route:
the plan names what is undecided, one script verb records the decisions, and the return then succeeds with no hand edit.

Every Git call here ignores the machine's Git configuration (a CI runner's global config carries git-lfs filters, which
the workspace refuses).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
GIT = shutil.which("git")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def advance_to(state: dict, stage: str) -> dict:
    """Apply synthetic results (no host work, no Improve runtime) until ``stage`` is the current stage."""
    while navigator.current_stage(state) != stage:
        action = navigator.current_action(state)
        result: dict = {"outcome": "done", "summary": "Synthetic transition for the return-review tests."}
        if action["stage"] == "plan":
            result["work_items"] = [{"id": "W1", "title": "One synthetic item", "context": "Only test the return."}]
        state = navigator.apply(state, action["id"], result)
        if state["active_improve"] is not None:
            state = navigator.finish_improve(state, action["id"], {
                "summary": "Synthetic Improve for " + action["stage"] + ".", "review_refs": [], "check_refs": [],
                "lessons": "Only test the return."})
    return state


class ReturnReviewCase(unittest.TestCase):
    """A disposable source repository, an isolated run started through the CLI, and Git run without user config."""

    def setUp(self) -> None:
        if GIT is None:
            self.fail("Git must be available on PATH")
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-return-review-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "source repository"
        self.repo.mkdir()
        self.env = {
            **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "SHIPLOOP_PROGRESS": "off",
            "SHIPLOOP_KEEPALIVE": "off", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        }
        patched = mock.patch.dict(os.environ, self.env)
        patched.start()
        self.addCleanup(patched.stop)
        self.git("init", "-q")
        self.git("branch", "-M", "main")
        self.git("config", "user.name", "Return Review Test")
        self.git("config", "user.email", "return-review@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)
        (self.repo / "existing.txt").write_text("existing\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "baseline")

    def git(self, *args: str, cwd: Path | None = None, code: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run([str(GIT), "-C", str(cwd or self.repo), *args], text=True, capture_output=True,
                                timeout=60, env=self.env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, "-B", str(CLI), *args], cwd=self.base, text=True,
                                capture_output=True, timeout=120, env=self.env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def start(self, name: str, *extra: str) -> tuple[Path, Path]:
        """Start an isolated run through the CLI; return its workspace root and execution worktree."""
        root = self.base / name
        self.cli("workspace", "start", "--repo", str(self.repo), "--workspace-root", str(root),
                 "--prompt", "Exercise the return review.", *extra)
        return root, root / "worktree"

    def write(self, worktree: Path, relative: str, content: str = "content\n") -> None:
        path = worktree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, worktree: Path, message: str = "work") -> str:
        self.git("add", "-A", cwd=worktree)
        self.git("commit", "-qm", message, cwd=worktree)
        return self.git("rev-parse", "HEAD", cwd=worktree).stdout.strip()

    def at(self, root: Path, stage: str) -> Path:
        """Save the run at ``stage`` (release and handoff allow a return) and return its run directory."""
        run = root / "run"
        navigator.save(run, advance_to(store.read_record(run / "state.md"), stage))
        return run

    def plan_return(self, root: Path, code: int = 0) -> subprocess.CompletedProcess:
        return self.cli("workspace", "plan-return", "--workspace-root", str(root), code=code)

    def review(self, root: Path, *words: str, code: int = 0) -> subprocess.CompletedProcess:
        return self.cli("workspace", "review-return", "--workspace-root", str(root), *words, code=code)

    def do_return(self, root: Path, code: int = 0) -> subprocess.CompletedProcess:
        return self.cli("workspace", "return", "--workspace-root", str(root), code=code)

    @staticmethod
    def plan(root: Path) -> dict:
        return store.read_record(root / "return-plan.md")

    def dispositions(self, root: Path) -> dict:
        return {row["path"]: row["disposition"] for row in self.plan(root)["paths"]}

    def review_command(self, root: Path) -> str:
        return shlex.join(["python3", str(CLI), "workspace", "review-return", "--workspace-root", str(root)])


class ReviewReturnTests(ReturnReviewCase):
    def candidate(self, name: str) -> tuple[Path, Path, Path]:
        """A run at handoff whose candidate holds two product files and one transient file, all committed."""
        root, worktree = self.start(name)
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "docs/guide.md", "guide\n")
        self.write(worktree, "scratch.log", "transient\n")
        self.commit(worktree, "work item")
        return root, worktree, self.at(root, "handoff")

    def test_a_blocked_return_names_the_undecided_paths_and_the_review_verb_on_its_first_line(self) -> None:
        root, _, _ = self.candidate("blocked first line")
        self.plan_return(root)
        refused = self.do_return(root, code=2)
        lines = refused.stderr.splitlines()
        # A model reads the first line through filters such as `head -1 | cut -c1-250`: the verb, the count and the
        # paths must be on it, and the exact command (not a copy-paste keep-all) on the next.
        self.assertTrue(lines[0].startswith("ShipLoop workspace blocked: review-return is needed for 3 undecided "
                                            "return paths: "), lines[0])
        for path in ("app.js", "docs/guide.md", "scratch.log"):
            self.assertIn(path, lines[0][:250])
        self.assertEqual(lines[1], "Run: " + self.review_command(root) + " --keep <paths> --exclude <paths>")
        self.assertNotIn("app.js", lines[1])  # the model supplies the judgement; the script supplies the verb
        self.assertIn("--keep", lines[2])
        self.assertIn("--exclude", lines[2])
        self.assertNotIn("Preserve the workspace", refused.stderr)  # nothing was put at risk by this refusal
        self.assertFalse((root / "return-receipt.md").exists())

    def test_plan_return_prints_the_tally_the_undecided_paths_and_the_review_command(self) -> None:
        root, worktree = self.start("plan tally")
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "scratch.log", "transient\n")
        self.commit(worktree, "work item")
        self.write(worktree, "late.js", "written after the last work item\n")  # left uncommitted
        self.at(root, "handoff")
        planned = self.plan_return(root).stdout
        self.assertIn("ShipLoop committed these files that were left uncommitted (no action needed): late.js", planned)
        self.assertNotIn("left uncommitted in the candidate", planned)  # the old line read as an instruction
        self.assertIn(f"Return plan {root / 'return-plan.md'}: 3 paths, 0 keep, 0 exclude, 3 undecided.", planned)
        self.assertIn("Undecided (3): app.js, late.js, scratch.log.", planned)
        self.assertIn("Decide them with: " + self.review_command(root) + " --keep <paths> --exclude <paths>", planned)
        self.assertIn("A directory decides every undecided path beneath it", planned)
        self.assertIn("Return policy: fast-forward only", planned)
        self.assertIn("workspace return --workspace-root", planned.splitlines()[-1])
        self.assertNotIn("Review all keep/exclude dispositions", planned)

    def test_review_return_records_decisions_and_the_return_then_succeeds_without_a_hand_edit(self) -> None:
        root, _, _ = self.candidate("record decisions")
        self.plan_return(root)
        plan_before = (root / "return-plan.md").read_bytes()
        reviewed = self.review(root, "--keep", "app.js", "docs/guide.md", "--exclude", "scratch.log").stdout
        self.assertIn("Recorded: kept app.js, docs/guide.md; excluded scratch.log.", reviewed)
        self.assertIn("0 undecided", reviewed)
        self.assertIn("Excluded by review: scratch.log.", reviewed)
        self.assertIn("workspace return --workspace-root", reviewed.splitlines()[-1])
        self.assertNotEqual((root / "return-plan.md").read_bytes(), plan_before)
        plan = self.plan(root)
        self.assertEqual(plan["status"], "ready")  # the script's own label: a model never edits it
        self.assertEqual(self.dispositions(root), {"app.js": "keep", "docs/guide.md": "keep", "scratch.log": "exclude"})
        returned = self.do_return(root)
        self.assertIn("Verified workspace return", returned.stdout)
        self.assertEqual((self.repo / "app.js").read_text(encoding="utf-8"), "product\n")
        self.assertEqual((self.repo / "docs" / "guide.md").read_text(encoding="utf-8"), "guide\n")
        self.assertFalse((self.repo / "scratch.log").exists())

    def test_review_return_leaves_the_other_undecided_paths_pending_and_says_which(self) -> None:
        root, _, _ = self.candidate("partial decisions")
        self.plan_return(root)
        reviewed = self.review(root, "--keep", "app.js").stdout
        self.assertIn("1 keep, 0 exclude, 2 undecided", reviewed)
        self.assertIn("Undecided (2): docs/guide.md, scratch.log.", reviewed)
        self.assertIn("Decide them with: " + self.review_command(root), reviewed)
        self.assertEqual(self.plan(root)["status"], "pending")
        blocked = self.do_return(root, code=2)
        self.assertIn("2 undecided return paths: docs/guide.md, scratch.log", blocked.stderr.splitlines()[0])

    def test_a_directory_decides_only_the_undecided_paths_beneath_it_and_an_exact_path_wins(self) -> None:
        root, worktree = self.start("directory decisions")
        for name in ("src/a.js", "src/b.js", "src/tmp/cache.js", "other.js"):
            self.write(worktree, name)
        self.commit(worktree)
        self.at(root, "handoff")
        self.plan_return(root)
        self.review(root, "--exclude", "src/b.js")
        self.review(root, "--keep", "src", "--exclude", "src/tmp")
        self.assertEqual(self.dispositions(root), {"other.js": "pending", "src/a.js": "keep", "src/b.js": "exclude",
                                                   "src/tmp/cache.js": "exclude"})
        self.review(root, "--keep", "src/b.js")  # an exact path overrides what was recorded
        self.assertEqual(self.dispositions(root)["src/b.js"], "keep")
        self.assertEqual(self.dispositions(root)["other.js"], "pending")

    def test_review_return_refuses_a_protected_or_caller_excluded_keep_and_a_knowledge_exclude_naming_the_path(self) -> None:
        root, worktree = self.start("rule refusals", "--exclude", "vendor")
        self.write(worktree, "app.js")
        self.write(worktree, "docs/shiploop/README.md", "knowledge\n")
        self.commit(worktree)
        self.write(worktree, "vendor/lib.js")  # caller-excluded, so never committed by ShipLoop
        self.write(worktree, ".shiploop-improve/child/evidence.md")  # run evidence: protected
        self.at(root, "handoff")
        self.plan_return(root)
        self.assertEqual(self.dispositions(root)["vendor/lib.js"], "exclude")
        self.assertEqual(self.dispositions(root)["docs/shiploop/README.md"], "keep")
        before = (root / "return-plan.md").read_bytes()
        for words, path, rule in (
                (("--keep", "vendor/lib.js"), "vendor/lib.js", "caller-excluded"),
                (("--keep", ".shiploop-improve/child/evidence.md"), ".shiploop-improve/child/evidence.md",
                 "protected runtime path"),
                (("--exclude", "docs/shiploop/README.md"), "docs/shiploop/README.md", "knowledge")):
            with self.subTest(path=path):
                refused = self.review(root, *words, code=2)
                self.assertIn(path, refused.stderr)
                self.assertIn(rule, refused.stderr)
                self.assertEqual((root / "return-plan.md").read_bytes(), before)
        # A refusal records nothing: the valid half of a mixed call is not applied either.
        self.review(root, "--keep", "app.js", "vendor/lib.js", code=2)
        self.assertEqual((root / "return-plan.md").read_bytes(), before)

    def test_review_return_refuses_an_unknown_path_a_conflicting_pair_and_a_stale_plan_with_the_next_action(self) -> None:
        root, worktree, _ = self.candidate("other refusals")
        refused = self.review(root, "--keep", "app.js", code=2)  # no plan yet
        self.assertIn("plan-return", refused.stderr)
        self.plan_return(root)
        before = (root / "return-plan.md").read_bytes()
        unknown = self.review(root, "--keep", "app.js", "nope.txt", code=2)
        self.assertIn("nope.txt", unknown.stderr)
        self.assertIn("not a path in the return plan", unknown.stderr)
        self.assertIn("docs/guide.md", unknown.stderr)  # the undecided list, so the model can correct the name
        both = self.review(root, "--keep", "app.js", "--exclude", "app.js", code=2)
        self.assertIn("app.js", both.stderr)
        self.assertIn("both --keep and --exclude", both.stderr)
        self.assertEqual((root / "return-plan.md").read_bytes(), before)
        self.write(worktree, "late.js")  # the candidate moved after the plan was made
        stale = self.review(root, "--keep", "app.js", code=2)
        self.assertIn("stale", stale.stderr)
        self.assertIn("run plan-return again", stale.stderr)
        self.assertIn("decisions already recorded are kept", stale.stderr)
        self.assertEqual((root / "return-plan.md").read_bytes(), before)

    def test_a_stale_plan_at_return_names_plan_return_as_the_next_action(self) -> None:
        root, worktree, _ = self.candidate("stale at return")
        self.plan_return(root)
        self.review(root, "--keep", "app.js", "docs/guide.md", "--exclude", "scratch.log")
        self.write(worktree, "late.js")
        stale = self.do_return(root, code=2)
        self.assertIn("run plan-return again", stale.stderr)
        self.assertIn("decisions already recorded are kept", stale.stderr)

    def test_plan_return_again_keeps_recorded_decisions_for_unchanged_paths_and_leaves_new_paths_pending(self) -> None:
        root, worktree, _ = self.candidate("carry over")
        self.plan_return(root)
        self.review(root, "--keep", "app.js", "docs/guide.md", "--exclude", "scratch.log")
        self.write(worktree, "extra.js")
        self.commit(worktree, "one more file")
        replanned = self.plan_return(root).stdout
        self.assertEqual(self.dispositions(root), {"app.js": "keep", "docs/guide.md": "keep", "extra.js": "pending",
                                                   "scratch.log": "exclude"})
        self.assertEqual(self.plan(root)["status"], "pending")
        self.assertIn("Undecided (1): extra.js.", replanned)
        # A model that lost its context cannot see an earlier exclude except through this line.
        self.assertIn("Excluded by review: scratch.log.", replanned)
        self.review(root, "--keep", "extra.js")
        self.assertIn("Verified workspace return", self.do_return(root).stdout)
        self.assertFalse((self.repo / "scratch.log").exists())

    def test_a_decision_is_not_carried_for_a_path_commit_leftovers_skipped_and_an_unreadable_plan_carries_none(self) -> None:
        root, worktree, _ = self.candidate("carry limits")
        self.plan_return(root)
        self.review(root, "--keep", "app.js", "docs/guide.md", "scratch.log")
        with mock.patch.dict(os.environ, self.env):
            plan = workspace.plan_return(root, fresh=["app.js"])  # as if it had been skipped as credential-like
        self.assertEqual({row["path"]: row["disposition"] for row in plan["paths"]},
                         {"app.js": "pending", "docs/guide.md": "keep", "scratch.log": "keep"})
        (root / "return-plan.md").write_text("not a record\n", encoding="utf-8")
        with mock.patch.dict(os.environ, self.env):
            plan = workspace.plan_return(root)
        self.assertEqual({row["disposition"] for row in plan["paths"]}, {"pending"})

    def test_a_very_long_undecided_list_is_bounded_and_a_directory_decides_the_rest(self) -> None:
        root, worktree = self.start("many paths")
        names = [f"bulk/module-{index:04d}-with-a-rather-long-descriptive-file-name.js" for index in range(700)]
        for name in names:
            self.write(worktree, name)
        self.commit(worktree)
        self.at(root, "handoff")
        planned = self.plan_return(root).stdout
        refused = self.do_return(root, code=2).stderr
        for text in (planned, refused):
            self.assertLessEqual(max(len(line) for line in text.splitlines()), navigator.PRINT_LIMIT)
        self.assertIn("and ", refused.splitlines()[0])
        self.assertIn(" more", refused.splitlines()[0])
        self.assertIn("700 undecided return paths", refused.splitlines()[0])
        self.assertLessEqual(len(refused.splitlines()[0]), 250 + navigator.PRINT_LIMIT)
        self.review(root, "--keep", "bulk")
        self.assertEqual(set(self.dispositions(root).values()), {"keep"})
        self.assertIn("Verified workspace return", self.do_return(root).stdout)


if __name__ == "__main__":
    unittest.main()
