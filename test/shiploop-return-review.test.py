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
        self.env = {
            **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "SHIPLOOP_PROGRESS": "off",
            "SHIPLOOP_KEEPALIVE": "off", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        }
        patched = mock.patch.dict(os.environ, self.env)
        patched.start()
        self.addCleanup(patched.stop)
        self.fresh_repo("source repository")

    def fresh_repo(self, name: str) -> Path:
        """A source repository with one baseline commit; later calls give a scenario a clean source of its own."""
        self.repo = self.base / name
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("branch", "-M", "main")
        self.git("config", "user.name", "Return Review Test")
        self.git("config", "user.email", "return-review@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)
        (self.repo / "existing.txt").write_text("existing\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "baseline")
        return self.repo

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

    @staticmethod
    def tree(root: Path) -> dict:
        """Every file under ``root`` outside .git, with its bytes."""
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*"))
                if path.is_file() and ".git" not in path.relative_to(root).parts}

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
        self.assertIn(navigator.REVIEW_RETURN_RULE, planned)
        self.assertIn("Return policy: fast-forward only", planned)
        # A cleared context needs the next command last: while paths are undecided that is the review, not the return.
        self.assertTrue(planned.splitlines()[-1].startswith("Decide them with: "), planned.splitlines()[-1])
        self.assertNotIn("Review all keep/exclude dispositions", planned)

    def test_review_return_records_decisions_and_the_return_then_succeeds_without_a_hand_edit(self) -> None:
        root, _, _ = self.candidate("record decisions")
        self.plan_return(root)
        plan_before = (root / "return-plan.md").read_bytes()
        reviewed = self.review(root, "--keep", "app.js", "docs/guide.md", "--exclude", "scratch.log").stdout
        self.assertIn("Recorded: kept app.js, docs/guide.md.", reviewed)
        self.assertIn("Recorded: excluded 1 (every exclude a review decided is listed below).", reviewed)
        self.assertEqual(reviewed.count("scratch.log"), 1)  # listed once, under Excluded by review
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
        self.assertEqual(reviewed.splitlines()[-1], "Decide them with: " + self.review_command(root)
                         + " --keep <paths> --exclude <paths>")
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

    def test_a_hand_edited_status_is_refused_naming_the_allowed_values_and_the_verb(self) -> None:
        # Battleship invented the status 'reviewed' and then grepped the engine source for the allowed ones.
        root, _, _ = self.candidate("bad status")
        self.plan_return(root)
        plan = self.plan(root)
        plan["status"] = "reviewed"
        store.write_record(root / "return-plan.md", plan, "ShipLoop return plan")
        first = self.do_return(root, code=2).stderr.splitlines()[0]
        for part in ("return plan has an invalid status 'reviewed'", "pending", "ready", "review-return"):
            self.assertIn(part, first)

    def test_the_handoff_refusal_names_plan_return_then_review_return_then_return(self) -> None:
        root, _, run = self.candidate("handoff text")
        action = navigator.current_action(store.read_record(run / "state.md"))
        result = run / "inbox" / f"{action['id']}.md"
        store.write_record(result, {"outcome": "done", "summary": "Rejected without a return."}, "ShipLoop navigator result")
        refused = self.cli("complete", "--run-dir", str(run), "--action", action["id"], "--result", str(result), code=2)
        text = refused.stderr
        self.assertIn("handoff requires a verified workspace return", text)
        parts = ("workspace plan-return --workspace-root", "workspace review-return --workspace-root",
                 "--keep <paths> --exclude <paths>", "workspace return --workspace-root")
        for part in parts:
            self.assertIn(part, text)
        positions = [text.index(part) for part in parts]
        self.assertEqual(positions, sorted(positions))

    def test_the_whole_printed_output_is_one_budget_with_the_next_command_last_and_a_directory_decides_the_rest(self) -> None:
        # Hosts cut a long output near 20,000 characters, and the command is what a cleared context needs, so every
        # command's output (not each of its lists) stays within PRINT_LIMIT and ends with that command.  Three
        # directories of long names are each longer than the limit alone, so the review below holds a long kept list,
        # a long excluded list and a long undecided list in one output.
        root, worktree = self.start("many paths")
        for folder in ("keep-me", "drop-me", "wait-me"):
            for index in range(100):
                self.write(worktree, f"{folder}/module-{index:04d}-" + "x" * 180 + ".js")
        self.commit(worktree)
        self.at(root, "handoff")

        def within(text: str, last: str) -> None:
            self.assertLessEqual(len(text), navigator.PRINT_LIMIT, len(text))
            self.assertTrue(text.splitlines()[-1].startswith(last), text.splitlines()[-1][:120])

        within(self.plan_return(root).stdout, "Decide them with: ")
        refused = self.do_return(root, code=2).stderr
        first = refused.splitlines()[0]
        self.assertIn("300 undecided return paths", first)
        self.assertIn(", and ", first)  # a cut list counts the rest
        self.assertIn(" more", first)
        self.assertIn("Run: ", refused)
        self.assertLessEqual(len(refused), navigator.PRINT_LIMIT)
        excluded = self.review(root, "--exclude", "drop-me").stdout
        within(excluded, "Decide them with: ")
        self.assertIn("Recorded: excluded 100", excluded)
        # The reviewed excludes are listed once, with the other excludes a review decided, not again under Recorded.
        self.assertEqual(excluded.count("drop-me/module-0000"), 1)
        replanned = self.plan_return(root).stdout
        within(replanned, "Decide them with: ")
        self.assertIn("Excluded by review: drop-me/module-0000", replanned)  # a carried exclude stays visible
        three = self.review(root, "--keep", "keep-me").stdout
        within(three, "Decide them with: ")
        for part in ("Recorded: kept keep-me/module-0000", "Excluded by review: drop-me/module-0000",
                     "Undecided (100): wait-me/module-0000"):
            self.assertIn(part, three)
        last = self.review(root, "--keep", "wait-me").stdout
        within(last, "Nothing is undecided; run: ")
        self.assertIn("Recorded: kept wait-me/module-0000", last)
        self.assertEqual(sorted(set(self.dispositions(root).values())), ["exclude", "keep"])
        self.assertEqual(sum(value == "keep" for value in self.dispositions(root).values()), 200)
        self.assertIn("Verified workspace return", self.do_return(root).stdout)

    def test_an_unsafe_or_empty_path_is_refused_with_the_undecided_paths_and_the_command_not_the_generic_trailer(self) -> None:
        root, worktree, _ = self.candidate("unsafe paths")
        self.plan_return(root)
        before = (root / "return-plan.md").read_bytes()
        self.assertIn("relative to the execution checkout", navigator.REVIEW_RETURN_RULE)
        for words in (("--keep", str(worktree / "app.js")), ("--exclude", "../app.js"), ("--keep", "")):
            with self.subTest(words=words):
                refused = self.review(root, *words, code=2).stderr
                lines = refused.splitlines()
                self.assertTrue(lines[0].startswith("ShipLoop workspace blocked: "), lines[0])
                self.assertIn("relative to the execution checkout", lines[0])
                self.assertIn("Undecided (3): app.js, docs/guide.md, scratch.log.", refused)
                self.assertIn("Run: " + self.review_command(root) + " --keep <paths> --exclude <paths>", refused)
                self.assertIn(navigator.REVIEW_RETURN_RULE, refused)
                self.assertNotIn("Preserve the workspace", refused)  # nothing was put at risk by a mistyped path
                self.assertEqual((root / "return-plan.md").read_bytes(), before)

    def test_plan_return_and_review_return_take_the_workspace_lock(self) -> None:
        # A writer verb now sits beside plan_return, so neither may run while another ShipLoop command holds the workspace.
        import fcntl
        root, _, _ = self.candidate("locked")
        workspace.plan_return(root)
        before = (root / "return-plan.md").read_bytes()
        with (root / ".workspace.lock").open("rb") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(workspace.WorkspaceError, "busy"):
                workspace.plan_return(root)
            with self.assertRaisesRegex(workspace.WorkspaceError, "busy"):
                workspace.review_return(root, keep=["app.js"])
        self.assertEqual((root / "return-plan.md").read_bytes(), before)
        workspace.review_return(root, keep=["app.js"])  # control: the same call works once the lock is free
        self.assertEqual(self.dispositions(root)["app.js"], "keep")


class ReturnRouteTests(ReturnReviewCase):
    """The route a return takes, said before it happens, and the rollback that undoes each route."""

    def prepare(self, name: str, **options) -> tuple[Path, Path]:
        root = self.base / name
        record = workspace.prepare(self.repo, root, **options)
        return root, Path(record["worktree"])

    def review_all(self, root: Path, exclude: tuple[str, ...] = ()) -> None:
        workspace.plan_return(root)
        plan = store.read_record(root / "return-plan.md")
        keep = [row["path"] for row in plan["paths"] if row["path"] not in exclude and row["disposition"] == "pending"]
        workspace.review_return(root, keep=keep, exclude=exclude)

    def test_the_expected_return_matches_the_actual_return_for_each_route(self) -> None:
        # One predicate decides the route (execute_return follows it, expected_return reports it); this guards the
        # extraction against drift for every route a return can take, including the two follow-ups.
        with self.subTest("clean start, every path kept: fast-forward, and its follow-up"):
            self.fresh_repo("ff source")
            root, worktree = self.prepare("ff")
            self.write(worktree, "app.js")
            self.commit(worktree)
            self.review_all(root)
            self.assertEqual(workspace.expected_return(root), "fast-forward-merge")
            self.assertEqual(workspace.execute_return(root)["kind"], "fast-forward-merge")
            self.write(worktree, "fix.js")
            self.commit(worktree, "a fix after the return")
            self.review_all(root)
            self.assertEqual(workspace.expected_return(root), "fast-forward-merge")  # a follow-up keeps the route
            self.assertEqual(workspace.execute_return(root)["kind"], "fast-forward-merge")
        with self.subTest("clean start, a committed path excluded: working-tree return, and its follow-up"):
            self.fresh_repo("excluded source")
            root, worktree = self.prepare("excluded")
            self.write(worktree, "app.js")
            self.write(worktree, "scratch.log")
            self.commit(worktree)
            self.review_all(root, exclude=("scratch.log",))
            self.assertEqual(workspace.expected_return(root), "working-tree-return")
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
            self.write(worktree, "fix.js")
            self.commit(worktree, "a fix after the return")
            self.review_all(root, exclude=("scratch.log",))
            self.assertEqual(workspace.expected_return(root), "working-tree-return")
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
        with self.subTest("a follow-up keeps the route of the return it follows, even when the plan would now allow another"):
            # The excluded committed path makes the first return a working-tree return; keeping it afterwards makes
            # every history path kept, which a first return would fast-forward.  A follow-up still applies to the
            # source working tree, and expected_return must say so (the prior-kind rule, not the fresh rule).
            self.fresh_repo("route source")
            root, worktree = self.prepare("route")
            self.write(worktree, "app.js")
            self.write(worktree, "scratch.log")
            self.commit(worktree)
            self.review_all(root, exclude=("scratch.log",))
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
            self.write(worktree, "fix.js")
            self.commit(worktree, "a fix after the return")
            workspace.plan_return(root)
            workspace.review_return(root, keep=["fix.js", "scratch.log"])
            self.assertEqual(workspace.expected_return(root), "working-tree-return")
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
        with self.subTest("dirty start: working-tree return"):
            self.fresh_repo("dirty source")
            (self.repo / "existing.txt").write_text("edited by the user\n", encoding="utf-8")
            root, worktree = self.prepare("dirty")
            self.write(worktree, "app.js")
            self.commit(worktree)
            self.review_all(root)
            self.assertEqual(workspace.expected_return(root), "working-tree-return")
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
        with self.subTest("nothing to return"):
            self.fresh_repo("nothing source")
            root, worktree = self.prepare("nothing")
            self.review_all(root)
            self.assertEqual(workspace.expected_return(root), "no-change-return")
            self.assertEqual(workspace.execute_return(root)["kind"], "no-change-return")
        with self.subTest("undecided paths: no route yet"):
            self.fresh_repo("undecided source")
            root, worktree = self.prepare("undecided")
            self.write(worktree, "app.js")
            self.commit(worktree)
            workspace.plan_return(root)
            self.assertIsNone(workspace.expected_return(root))

    def test_review_return_says_the_expected_return_once_nothing_is_undecided(self) -> None:
        root, worktree = self.start("expected line")
        self.write(worktree, "app.js")
        self.write(worktree, "scratch.log")
        self.commit(worktree)
        self.at(root, "handoff")
        self.plan_return(root)
        partial = self.review(root, "--keep", "app.js").stdout
        self.assertNotIn("Expected return", partial)
        done = self.review(root, "--exclude", "scratch.log").stdout
        self.assertIn("Expected return: working-tree-return", done)
        self.assertIn("no Git merge or commit", done)
        self.assertIn("the return itself still refuses a moved source", done)
        self.assertEqual(self.do_return(root).stdout.splitlines()[0], "Verified workspace return: working-tree-return.")
        # A follow-up whose only new path is decided by a rule leaves nothing undecided already at plan-return: it
        # says the route then too, without a review-return call.
        self.write(worktree, "SHIPLOOP.md", "index\n")
        self.commit(worktree, "knowledge after the return")
        replanned = self.plan_return(root).stdout
        self.assertIn("0 undecided", replanned)
        self.assertIn("Expected return: working-tree-return", replanned)
        self.assertIn("Nothing is undecided; run: ", replanned)

    def sh(self, command: str) -> None:
        result = subprocess.run(["sh", "-c", command], cwd=self.base, text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, 0, command + "\n" + result.stdout + result.stderr)

    @staticmethod
    def recipe(root: Path, containing: str) -> str:
        """The command inside backticks on the one rollback line that holds ``containing``."""
        found = [line for line in workspace.rollback_lines(root) if containing in line]
        assert len(found) == 1, (containing, workspace.rollback_lines(root))
        return found[0].split("`")[1]

    def snapshot(self) -> dict:
        return {"head": self.git("rev-parse", "HEAD").stdout, "status": self.git("status", "--porcelain=v1",
                "--untracked-files=all").stdout, "tree": ReturnReviewCase.tree(self.repo)}

    def test_the_printed_rollback_restores_the_source_for_each_return_kind(self) -> None:
        with self.subTest("fast-forward over a merge commit, nothing on top: reset --keep"):
            self.fresh_repo("rb-ff source")
            root, worktree = self.prepare("rb-ff")
            before = self.snapshot()
            self.write(worktree, "app.js")
            self.commit(worktree)
            run_branch = self.git("rev-parse", "--abbrev-ref", "HEAD", cwd=worktree).stdout.strip()
            self.git("checkout", "-q", "-b", "side", cwd=worktree)  # a merge commit in the run's history
            self.write(worktree, "side.js")
            self.commit(worktree, "side work")
            self.git("checkout", "-q", run_branch, cwd=worktree)
            self.write(worktree, "main-line.js")
            self.commit(worktree, "main line work")
            self.git("merge", "--no-ff", "-q", "-m", "integrate side", "side", cwd=worktree)
            self.review_all(root)
            self.assertEqual(workspace.execute_return(root)["kind"], "fast-forward-merge")
            self.assertTrue((self.repo / "side.js").is_file())
            self.sh(self.recipe(root, "reset --keep"))
            self.assertEqual(self.snapshot(), before)
        with self.subTest("fast-forward, later commits on top: restore the recorded tree and commit"):
            self.fresh_repo("rb-top source")
            root, worktree = self.prepare("rb-top")
            base_tree = self.git("rev-parse", "HEAD^{tree}").stdout
            self.write(worktree, "app.js")
            self.commit(worktree)
            self.review_all(root)
            self.assertEqual(workspace.execute_return(root)["kind"], "fast-forward-merge")
            (self.repo / "later.txt").write_text("a later commit by the user\n", encoding="utf-8")
            self.git("add", "later.txt")
            self.git("commit", "-qm", "user work on top")
            self.sh(self.recipe(root, "restore --source"))
            self.assertEqual(self.git("rev-parse", "HEAD^{tree}").stdout, base_tree)  # added files are gone too
            self.assertEqual(self.git("status", "--porcelain=v1", "--untracked-files=all").stdout, "")
        with self.subTest("fast-forward, later commits on top, keeping their changes: reverse only the run's files"):
            self.fresh_repo("rb-keep source")
            root, worktree = self.prepare("rb-keep")
            self.write(worktree, "app.js")
            self.commit(worktree)
            self.review_all(root)
            self.assertEqual(workspace.execute_return(root)["kind"], "fast-forward-merge")
            (self.repo / "later.txt").write_text("a later commit by the user\n", encoding="utf-8")
            self.git("add", "later.txt")
            self.git("commit", "-qm", "user work on top")
            head = self.git("rev-parse", "HEAD").stdout
            self.sh(self.recipe(root, "apply -R").replace("<kept paths>", "app.js"))
            self.assertFalse((self.repo / "app.js").exists())
            self.assertTrue((self.repo / "later.txt").is_file())  # what the later commit changed stays
            self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)  # and the reversal is left uncommitted
        with self.subTest("working-tree return after an excluded committed path: reverse the kept diff"):
            self.fresh_repo("rb-wt source")
            root, worktree = self.prepare("rb-wt")
            before = self.snapshot()
            self.write(worktree, "app.js")
            self.write(worktree, "scratch.log")
            self.commit(worktree)
            self.review_all(root, exclude=("scratch.log",))
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
            self.assertTrue((self.repo / "app.js").is_file())
            self.sh(self.recipe(root, "apply -R").replace("<kept paths>", "app.js"))
            self.assertEqual(self.snapshot(), before)
        with self.subTest("dirty start: reverse the kept diff, and the user's own edit stays"):
            self.fresh_repo("rb-dirty source")
            (self.repo / "existing.txt").write_text("edited by the user\n", encoding="utf-8")
            root, worktree = self.prepare("rb-dirty")
            before = self.snapshot()
            self.write(worktree, "app.js")
            self.write(worktree, "existing.txt", "edited by the user and then by the run\n")
            self.commit(worktree)
            self.review_all(root)
            self.assertEqual(workspace.execute_return(root)["kind"], "working-tree-return")
            self.assertEqual((self.repo / "existing.txt").read_text(encoding="utf-8"),
                             "edited by the user and then by the run\n")
            self.sh(self.recipe(root, "apply -R").replace("<kept paths>", "app.js existing.txt"))
            self.assertEqual(self.snapshot(), before)
            self.assertEqual((self.repo / "existing.txt").read_text(encoding="utf-8"), "edited by the user\n")

    def test_the_rollback_anchors_come_from_workspace_md_even_after_a_follow_up_return(self) -> None:
        root, worktree = self.prepare("rb-anchor")
        manifest = store.read_record(root / "workspace.md")
        self.write(worktree, "app.js")
        self.commit(worktree)
        self.review_all(root)
        first = workspace.execute_return(root)
        self.write(worktree, "fix.js")
        self.commit(worktree, "a fix after the return")
        self.review_all(root)
        second = workspace.execute_return(root)
        self.assertEqual(second["source_before"]["head"], first["expected_source"]["head"])  # the previous result
        lines = "\n".join(workspace.rollback_lines(root))
        self.assertIn(manifest["source_head"], lines)
        self.assertNotIn(second["source_before"]["head"], lines)
        self.sh(self.recipe(root, "reset --keep"))
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), manifest["source_head"])

    def test_the_restore_recipe_says_it_also_undoes_the_later_commits_and_when_the_diff_recipe_is_better(self) -> None:
        # `restore --source` makes the tree equal to the pre-return tree, so it undoes what later commits changed too.
        root, _ = self.prepare("rb-wording")
        lines = workspace.rollback_lines(root)
        line = next(item for item in lines if "restore --source" in item)
        for part in ("later commits on top", "also undoes what those later commits changed",
                     "to keep their changes, reverse only the run's files with the last recipe instead"):
            self.assertIn(part, line)
        self.assertLess(lines.index(line), next(index for index, item in enumerate(lines) if "apply -R" in item))

    def test_the_rollback_names_no_absolute_run_path_but_the_source_checkout_for_its_git_calls(self) -> None:
        root, worktree = self.prepare("rb-paths")
        text = "\n".join(workspace.rollback_lines(root))
        self.assertNotIn(str(root), text)  # the worktree and run directory never appear in a durable plan
        self.assertIn("git -C " + shlex.quote(str(self.repo.resolve())), text)
        for token in ("{", "}"):
            self.assertNotIn(token, text)

    def render(self, root: Path, stage: str) -> str:
        run = root / "run"
        return navigator.render(None, run, advance_to(store.read_record(run / "state.md"), stage))

    def test_the_release_duties_tell_the_model_to_use_the_route_the_packet_states(self) -> None:
        # Wording-level check: the duty text is what makes a model write and verify the rollback it is shown.
        root, _ = self.start("duties")
        plan = " ".join(self.render(root, "release-plan").split())  # the duty text is wrapped
        check = " ".join(self.render(root, "release-check").split())
        self.assertEqual(plan.count("write the rollback for the source return the packet states"), 1)
        self.assertNotIn("run the packet's plan-return and review-return commands now", plan)
        for part in ("run the packet's plan-return and review-return commands now as a dry run of the return",
                     "plan-return may commit leftover product files to the run branch",
                     "compare the expected return review-return reports with the rollback in release-plan.md",
                     "after any such correction run plan-return again"):
            self.assertEqual(check.count(part), 1, part)
        self.assertNotIn("write the rollback for the source return the packet states", check)

    def test_worktree_packets_state_the_run_route_from_workspace_md_and_only_release_plan_and_check_carry_the_rollback(self) -> None:
        clean_root, _ = self.start("packet clean")
        (self.repo / "existing.txt").write_text("edited by the user\n", encoding="utf-8")
        dirty_root, _ = self.start("packet dirty")
        self.git("checkout", "-q", "--", "existing.txt")
        manifest = store.read_record(clean_root / "workspace.md")
        for stage in ("intake", "implement", "release-plan", "release-check", "release", "handoff"):
            with self.subTest(stage=stage, start="clean"):
                packet = self.render(clean_root, stage)
                self.assertEqual(packet.count("Return route (from workspace.md): this run started from a clean main"), 1)
                self.assertNotIn("A dirty-source working-tree return is not a Git merge or commit", packet)
                self.assertEqual("Rollback of the return" in packet, stage in ("release-plan", "release-check"))
                if stage in ("release-plan", "release-check"):
                    self.assertEqual(packet.count("Return route (from workspace.md)"), 1)  # not repeated in the rollback
                    self.assertIn("reset --keep " + manifest["source_head"], packet)
                    self.assertIn("apply -R", packet)
                    self.assertIn("plain `git` commands run from the repository root", packet)
        with self.subTest("dirty start"):
            packet = self.render(dirty_root, "release-plan")
            self.assertIn("Return route (from workspace.md): this run started from a dirty main", packet)
            self.assertIn("it is not a Git merge or commit", packet)
            self.assertIn("apply -R", packet)
            self.assertNotIn("reset --keep", packet)  # a working-tree return never moved the branch
        with self.subTest("an unreadable workspace.md is said to be unknown, never guessed or omitted"):
            (clean_root / "workspace.md").write_text("not a record\n", encoding="utf-8")
            packet = self.render(clean_root, "release-plan")
            self.assertIn("Return route unknown: workspace.md cannot be read", packet)
            self.assertNotIn("Rollback of the return", packet)


    def test_the_route_sentence_says_plan_return_commits_files_left_uncommitted_and_plan_return_does_exactly_that(self) -> None:
        """Batch 1010 A2: the sentence a model reads before the return must not leave a model hand-committing a leftover.

        The sentence used to say the fast-forward needs "the candidate is committed" and that the plan "leaves a file
        uncommitted" otherwise, and never that plan-return commits such a file first.  In the Battleship round-2 run the
        model read that line through a ``cut`` of 250 characters and committed a late-written file by hand, and its
        outcome note kept the false rule "commit them before the return".  So the clause that matters comes straight
        after the first sentence, and each thing it says is held against the real verb below.
        """
        root, worktree = self.start("route leftovers")
        self.write(worktree, "app.js", "product\n")
        self.commit(worktree, "work item")
        self.write(worktree, "late.js", "written after the last work item\n")
        self.write(worktree, "settings.env", "Authorization: Bearer 0123456789abcdefghij\n")
        self.write(worktree, ".shiploop-improve/child/review.md", "run evidence\n")
        self.at(root, "release-plan")

        def route(of: Path) -> str:
            return next(line for line in self.render(of, "release-plan").splitlines()
                        if line.startswith("Return route (from workspace.md)"))

        clause = ("plan-return commits files left uncommitted, so commit nothing for the return except a file it "
                  "reports as not committed.")
        with self.subTest("the clean-start sentence"):
            line = route(root)
            self.assertIn(clause, line)
            self.assertEqual(line.count("plan-return"), 1)
            # It follows the first sentence and comes before the fast-forward rule, and ends inside the 250
            # characters the Battleship run read of this line.
            self.assertLess(line.index(clause), line.index("The return fast-forwards"))
            self.assertLessEqual(line.index(clause) + len(clause), 250)
        with self.subTest("the dirty-start sentence says it too: the hazard does not depend on the route"):
            (self.repo / "existing.txt").write_text("edited by the user\n", encoding="utf-8")
            dirty_root, _ = self.start("route leftovers dirty")
            self.git("checkout", "-q", "--", "existing.txt")
            line = route(dirty_root)
            self.assertIn("this run started from a dirty main", line)
            self.assertIn(clause, line)
            self.assertLess(line.index(clause), line.index("The return applies only the kept files"))
        with self.subTest("plan-return commits the late file, screens the credential-like one and skips run evidence"):
            out = self.plan_return(root).stdout
            self.assertIn("ShipLoop committed these files that were left uncommitted (no action needed): late.js", out)
            self.assertIn("Not committed, they look like they hold a credential: settings.env", out)
            self.assertEqual(self.git("ls-files", cwd=worktree).stdout.split(), ["app.js", "existing.txt", "late.js"])
        with self.subTest("the exception is real: the file it reports as not committed keeps the return off the branch"):
            self.review(root, "--keep", "app.js", "late.js", "settings.env")
            self.assertEqual(workspace.expected_return(root), "working-tree-return")
        with self.subTest("committing that file as the report says (value replaced) restores the fast-forward"):
            self.write(worktree, "settings.env", "Authorization: set from the environment\n")
            self.git("add", "settings.env", cwd=worktree)  # only that file: `add -A` would take the run evidence too
            self.git("commit", "-qm", "reference the credential, not its value", cwd=worktree)
            self.plan_return(root)  # the earlier keep decisions carry, so nothing is left to decide
            self.assertEqual(workspace.expected_return(root), "fast-forward-merge")


if __name__ == "__main__":
    unittest.main()
