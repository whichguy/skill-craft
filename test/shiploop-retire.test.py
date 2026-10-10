#!/usr/bin/env python3
"""Hermetic tests of the handoff retire (owner decision D3, plan 0a): the terminal close that removes a run's feature spec.

ShipLoop's terminal close commits the pending knowledge, retires the run's feature spec (``knowledge.retire``), returns what
those commits added, and then prints what happened.  The first class drives ``navigator._knowledge_close`` against a real
Git repository with the workspace calls stood in; the second drives the real CLI through each return route, with a real
isolated workspace.  The pieces of the retire itself (the ID check, the commit, the failure paths) are in
test/shiploop-knowledge.test.py; the route reader is in test/shiploop-workspace.test.py.

Every Git call here ignores the machine's Git configuration (a CI runner's global config carries git-lfs filters, which the
workspace refuses).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
for entry in (SCRIPTS, ROOT / "test"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kt = _load("shiploop_retire_knowledge_cases", "shiploop-knowledge.test.py")
rr = _load("shiploop_retire_return_review_cases", "shiploop-return-review.test.py")
git = kt.git

LIVING = "# Living spec\n\n- R-1 one\n- R-2 two\n"
FEATURE_SPEC = "# Feature spec\nAdds: R-1, R-2. Modifies: none. Retires: none.\n"


class TerminalCloseTests(kt.HomeCase):
    """``_knowledge_close(terminal=True)`` on a real repository: the order, the messages, and what a failure does."""

    def setUp(self) -> None:
        super().setUp()
        self.planned_home(living=LIVING, feature_spec=FEATURE_SPEC)
        self.write("docs/shiploop/environment.md", "# env\n")
        self.assertTrue(knowledge.commit(self.state, "prepare").commit)
        self.spec = self.repo / self.feature() / "spec.md"

    def close(self, mode: str = "navigator", *, terminal: bool = True) -> tuple[str, str]:
        after = dict(self.state, execution_mode=mode, history=[{"stage": "handoff", "outcome": "done"}])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            navigator._knowledge_close({"history": []}, after, Path("/ws/run"), terminal=terminal)
        return out.getvalue(), err.getvalue()

    def subjects(self) -> list[str]:
        return git(self.repo, "log", "--format=%s", "-3").splitlines()

    def worktree_run(self, kind, follow_up):
        """A worktree run whose recorded return is ``kind`` and whose follow-up return is ``follow_up`` (a result or an error)."""
        events: list[str] = []

        def follow(root):
            events.append("follow-up")
            events.append(git(self.repo, "log", "-1", "--format=%s").strip())     # what the follow-up could carry
            if isinstance(follow_up, BaseException):
                raise follow_up
            return follow_up

        patches = (mock.patch.object(workspace, "return_kind", return_value=kind),
                   mock.patch.object(workspace, "follow_up_knowledge_return", side_effect=follow))
        return events, patches

    def test_an_own_checkout_commits_the_pending_knowledge_then_retires_and_says_so_once(self) -> None:
        self.write("docs/shiploop/environment.md", "# env\n\nA late edit at the handoff.\n")      # pending at the handoff
        out, err = self.close()
        self.assertEqual(self.subjects()[:2], [knowledge.retire_subject(self.state),
                                              knowledge.knowledge_subject(self.state, "handoff")])
        self.assertFalse(self.spec.exists())
        retired = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertEqual(out, "ShipLoop knowledge: committed the removal of the feature spec " + str(self.spec) + " in "
                         + retired[:12] + "; its last version is in that commit's parent.\n")
        self.assertEqual(err, "")

    def test_a_worktree_run_commits_and_retires_before_the_follow_up_return_and_reports_it_returned(self) -> None:
        events, (kind, follow) = self.worktree_run("fast-forward-merge", {"kind": "fast-forward-merge"})
        with kind, follow:
            out, err = self.close("navigator-worktree")
        self.assertEqual(events, ["follow-up", knowledge.retire_subject(self.state)])    # the removal existed when it ran
        self.assertEqual(out.splitlines(), [
            "ShipLoop knowledge: returned the knowledge commit with the earlier work (fast-forward-merge).",
            "ShipLoop knowledge: committed the removal of the feature spec " + str(self.spec) + " in "
            + git(self.repo, "rev-parse", "HEAD").strip()[:12] + " and returned it; its last version is in that commit's parent."])
        self.assertEqual(err, "")

    def test_the_removal_is_not_reported_returned_when_the_follow_up_returned_nothing(self) -> None:
        events, (kind, follow) = self.worktree_run("fast-forward-merge", None)
        with kind, follow:
            out, _ = self.close("navigator-worktree")
        self.assertIn(" on the run branch, not yet on your branch; ", out)
        self.assertNotIn("and returned it", out)

    def test_a_follow_up_that_fails_after_only_the_retire_commit_does_not_replace_the_guards_commands(self) -> None:
        """Audit (batch 1012): raising here replaced the handoff guard's plan-return/review-return/return commands with an
        error that names none and repeats on the retry; the guard refuses a stale return by itself."""
        events, (kind, follow) = self.worktree_run("fast-forward-merge", workspace.WorkspaceError("source checkout changed"))
        with kind, follow:
            out, err = self.close("navigator-worktree")                       # does not raise
        self.assertIn(" on the run branch, not yet on your branch; ", out)
        self.assertNotIn("and returned it", out)
        self.assertEqual(err, "ShipLoop knowledge: the follow-up return was not made (source checkout changed); "
                              "handoff will ask for it.\n")
        self.assertFalse(self.spec.exists())
        events, (kind, follow) = self.worktree_run("fast-forward-merge", workspace.WorkspaceError("source checkout changed"))
        with kind, follow:
            out, err = self.close("navigator-worktree")                       # the retry: nothing left to retire, still no raise
        self.assertEqual(out, "")
        self.assertIn("handoff will ask for it", err)

    def test_a_follow_up_that_fails_after_a_knowledge_commit_made_at_the_handoff_still_refuses(self) -> None:
        """Guard (passes on the base too): today's fail-closed behaviour (plan P11) is kept when a knowledge commit was made at
        this handoff."""
        self.write("docs/shiploop/environment.md", "# env\n\nA late edit at the handoff.\n")
        events, (kind, follow) = self.worktree_run("fast-forward-merge", workspace.WorkspaceError("source checkout changed"))
        with kind, follow:
            with self.assertRaisesRegex(navigator.NavigatorError,
                                        r"the follow-up return was not made \(source checkout changed\); handoff remains pending"):
                self.close("navigator-worktree")

    def test_a_working_tree_or_no_change_return_keeps_the_file_and_says_why(self) -> None:
        for kind_name in ("working-tree-return", "no-change-return"):
            with self.subTest(kind=kind_name):
                events, (kind, follow) = self.worktree_run(kind_name, None)
                with kind, follow:
                    out, _ = self.close("navigator-worktree")
                self.assertEqual(out, "ShipLoop knowledge: kept the feature spec " + str(self.spec) + ": "
                                 + knowledge.KEPT_AFTER_ROUTE + ".\n")
                self.assertTrue(self.spec.is_file())
                self.assertEqual(self.subjects()[0], knowledge.knowledge_subject(dict(self.state), "prepare"))

    def test_before_any_return_the_route_is_unknown_and_nothing_is_said(self) -> None:
        """Guard (passes on the base too): the retire is deferred until the return, and says nothing before it."""
        events, (kind, follow) = self.worktree_run(None, None)
        with kind, follow:
            out, err = self.close("navigator-worktree")
        self.assertEqual((out, err), ("", ""))
        self.assertTrue(self.spec.is_file())

    def test_ids_the_living_spec_lacks_keep_the_file_with_one_notice_and_never_refuse_the_handoff(self) -> None:
        self.write(self.feature() + "/spec.md", FEATURE_SPEC + "Also R-9.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "the feature spec names an ID the living spec lacks")
        out, _ = self.close()                                                   # no exception: the handoff is not refused
        self.assertEqual(out, "ShipLoop knowledge: kept the feature spec " + str(self.spec) + ": R-9 is not in the living spec "
                         + str(self.repo / "docs/shiploop/spec.md") + ".\n")
        self.assertTrue(self.spec.is_file())

    def test_a_retire_that_cannot_commit_refuses_the_handoff_with_the_file_in_place(self) -> None:
        with mock.patch.object(kt.shiploop_git, "commit_paths", side_effect=kt.shiploop_git.CommitError("cannot commit it")):
            with self.assertRaisesRegex(navigator.NavigatorError, "cannot commit it; handoff remains pending"):
                self.close()
        self.assertTrue(self.spec.is_file())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_a_list_that_is_not_shiploops_is_named_in_one_notice_and_left_alone(self) -> None:
        listed = self.repo / knowledge.FEATURE_LIST
        listed.write_text("My own notes about the features.\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "the user takes over the list")
        out, _ = self.close()
        self.assertEqual(out.splitlines()[0], "ShipLoop knowledge: left " + str(listed) + " as it is (it does not begin with "
                         "ShipLoop's generated header, so it is not ShipLoop's list); the list of the feature folders is not written.")
        self.assertEqual(listed.read_text(), "My own notes about the features.\n")
        self.assertFalse(self.spec.exists())                                                  # the retire itself went ahead

    def test_only_the_terminal_close_retires(self) -> None:
        """Guard (passes on the base too): a close that is not the terminal handoff never retires."""
        out, err = self.close(terminal=False)
        self.assertEqual((out, err), ("", ""))
        self.assertTrue(self.spec.is_file())

    def test_the_run_commits_reach_the_branch_by_mode_and_by_the_recorded_return(self) -> None:
        in_place, isolated = {"execution_mode": "navigator"}, {"execution_mode": "navigator-worktree"}
        self.assertTrue(navigator._run_commits_reach_branch(in_place, Path("/ws/run")))
        self.assertTrue(navigator._run_commits_reach_branch(in_place, None))
        self.assertIsNone(navigator._run_commits_reach_branch(isolated, None))
        for kind, expected in (("fast-forward-merge", True), ("working-tree-return", False), ("no-change-return", False),
                               (None, None)):
            with self.subTest(kind=kind):
                with mock.patch.object(workspace, "return_kind", return_value=kind) as read:
                    self.assertEqual(navigator._run_commits_reach_branch(isolated, Path("/ws/run")), expected)
                    read.assert_called_once_with(Path("/ws"))


class RetireThroughTheCli(rr.ReturnReviewCase):
    """The real CLI: an isolated workspace, a real return, and ``complete`` on the handoff."""

    def candidate(self, name: str, *, dirty_start: bool = False):
        if dirty_start:
            (self.repo / "scratch-note.txt").write_text("the user's uncommitted work\n")
        root, worktree = self.start(name)
        state = store.read_record(root / "run" / "state.md")
        self.feature = knowledge.feature_dir(state)
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "docs/shiploop/spec.md", LIVING)
        self.write(worktree, self.feature + "/spec.md", FEATURE_SPEC)
        self.write(worktree, self.feature + "/plan.md", "# Plan\n")
        self.commit(worktree, "work item and knowledge")
        return root, worktree, self.at(root, "handoff")

    def return_all(self, root: Path) -> None:
        self.plan_return(root)
        self.review(root, "--keep", *self.dispositions(root))
        self.do_return(root)

    def complete(self, run: Path, code: int = 0):
        state = store.read_record(run / "state.md")
        action = navigator.current_action(state)
        result = run / "inbox" / f"{action['id']}.md"
        store.write_record(result, {"outcome": "done", "summary": "Handed off."}, "ShipLoop navigator result")
        return self.cli("complete", "--run-dir", str(run), "--action", action["id"], "--result", str(result), code=code)

    def retire_commits(self, worktree: Path) -> list[str]:
        return self.git("log", "--format=%H", "--grep=its requirement IDs are in the living spec", cwd=worktree).stdout.split()

    def test_a_fast_forward_return_retires_the_feature_spec_and_returns_the_removal(self) -> None:
        root, worktree, run = self.candidate("fast forward retire")
        self.return_all(root)
        self.assertTrue((self.repo / self.feature / "spec.md").is_file())
        done = self.complete(run)
        state = store.read_record(run / "state.md")
        self.assertEqual(state["status"], "done")
        self.assertIn("committed the removal of the feature spec " + str(worktree / self.feature / "spec.md"), done.stdout)
        self.assertIn(" and returned it; its last version is in that commit's parent.", done.stdout)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), knowledge.retire_subject(state))
        self.assertFalse((self.repo / self.feature / "spec.md").exists())
        self.assertIn("(" + self.feature.rsplit("/", 1)[-1] + "/plan.md)",
                      (self.repo / knowledge.FEATURE_LIST).read_text())
        self.assertIn("Adds: R-1", self.git("show", "HEAD^:" + self.feature + "/spec.md").stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_a_working_tree_return_keeps_the_feature_spec_and_says_why(self) -> None:
        root, worktree, run = self.candidate("working tree keep", dirty_start=True)
        self.return_all(root)
        self.assertEqual(workspace.return_kind(root), "working-tree-return")
        done = self.complete(run)
        self.assertIn("kept the feature spec " + str(worktree / self.feature / "spec.md") + ": " + knowledge.KEPT_AFTER_ROUTE,
                      done.stdout)
        self.assertTrue((worktree / self.feature / "spec.md").is_file())
        self.assertTrue((self.repo / self.feature / "spec.md").is_file())
        self.assertEqual(self.retire_commits(worktree), [])
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")

    def test_a_no_change_return_keeps_the_feature_spec_and_the_notice_stays_true_after_the_follow_up_returned_it(self) -> None:
        """Audit (batch 1012): the retire reads the route before the follow-up return, which recomputes a no-change return as
        a fast-forward and puts the knowledge commit on the branch; the notice used to say the commits do not reach it."""
        root, worktree = self.start("no change keep")
        self.feature = knowledge.feature_dir(store.read_record(root / "run" / "state.md"))
        run = self.at(root, "handoff")
        self.plan_return(root)
        self.do_return(root)                                                               # nothing to return
        self.assertEqual(workspace.return_kind(root), "no-change-return")
        self.write(worktree, "docs/shiploop/spec.md", LIVING)                              # written at the handoff
        self.write(worktree, self.feature + "/spec.md", FEATURE_SPEC)
        done = self.complete(run)
        self.assertEqual(workspace.return_kind(root), "fast-forward-merge")                 # the follow-up recomputed the route
        self.assertIn("(fast-forward-merge).", done.stdout.split("kept the feature spec")[0])    # and returned the commit first
        self.assertEqual(self.git("show", "HEAD:" + self.feature + "/spec.md").stdout, FEATURE_SPEC)   # it IS on the branch now
        self.assertIn("kept the feature spec " + str(worktree / self.feature / "spec.md") + ": " + knowledge.KEPT_AFTER_ROUTE,
                      done.stdout)
        self.assertNotIn("do not reach your branch", done.stdout)                           # nothing printed says the opposite
        self.assertEqual(self.retire_commits(worktree), [])
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")

    def test_a_handoff_before_the_return_is_refused_and_leaves_the_feature_spec_until_the_return(self) -> None:
        root, worktree, run = self.candidate("before the return")
        refused = self.complete(run, code=2)
        self.assertIn("handoff requires a verified workspace return", refused.stderr)
        self.assertNotIn("feature spec", refused.stdout)                                   # the route is unknown: nothing said
        self.assertTrue((worktree / self.feature / "spec.md").is_file())
        self.assertEqual(self.retire_commits(worktree), [])
        self.return_all(root)
        self.complete(run)
        self.assertFalse((self.repo / self.feature / "spec.md").exists())
        self.assertEqual(len(self.retire_commits(worktree)), 1)

    def test_a_handoff_refused_after_the_retire_is_retried_with_exactly_one_retire_commit(self) -> None:
        root, worktree, run = self.candidate("guard after retire")
        self.return_all(root)
        self.write(worktree, "late.js", "written after the return\n")                      # uncommitted: the follow-up cannot carry it
        refused = self.complete(run, code=2)
        self.assertIn("handoff requires", refused.stderr)
        self.assertIn(" on the run branch, not yet on your branch; ", refused.stdout)
        self.assertEqual(len(self.retire_commits(worktree)), 1)
        self.assertEqual(store.read_record(run / "state.md")["status"], "active")
        self.return_all(root)                                                              # plan-return commits late.js, then returns
        retried = self.complete(run)
        self.assertNotIn("kept the feature spec", retried.stdout)                          # a retry says nothing about a file that is gone
        self.assertNotIn("committed the removal", retried.stdout)
        self.assertEqual(len(self.retire_commits(worktree)), 1)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")
        self.assertFalse((self.repo / self.feature / "spec.md").exists())

    def test_a_follow_up_the_source_refuses_leaves_the_guards_commands_and_the_retry_after_the_fix_succeeds(self) -> None:
        root, worktree, run = self.candidate("source drift")
        self.return_all(root)
        (self.repo / "user-note.txt").write_text("the user kept working\n")                # the source moved after the return
        refused = self.complete(run, code=2)
        lines = refused.stderr.splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop knowledge: the follow-up return was not made ("), lines[0])
        self.assertIn("handoff requires a current workspace return, and the recorded one is stale", refused.stderr)   # the guard's
        for command in ("workspace plan-return", "workspace review-return", "workspace return"):                       # own commands
            self.assertIn(command, refused.stderr)
        self.assertIn(" on the run branch, not yet on your branch; ", refused.stdout)
        self.assertEqual(len(self.retire_commits(worktree)), 1)
        (self.repo / "user-note.txt").unlink()                                             # the fix
        done = self.complete(run)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")
        self.assertEqual(len(self.retire_commits(worktree)), 1)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(),
                         knowledge.retire_subject(store.read_record(run / "state.md")))
        self.assertNotIn("committed the removal", done.stdout)


if __name__ == "__main__":
    unittest.main()
