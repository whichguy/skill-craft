#!/usr/bin/env python3
"""The seed seam: ``shiploop_navigator.accept_effects``, the after-gate half of ``complete`` that a seed shares with it.

A harness that records synthetic results with the pure ``apply`` skips the script-owned effects of the engine: the checks
validate-existing runs on entry, the item and step bases, the iteration record, the step's commit.  A stage's packet then
misses what those effects write (validate-existing says "results are below" with none), and a seed on to document gets a
``next`` that repairs the missing iteration record and leaves the step uncommitted.  ``accept_effects`` holds those effects
once; ``dispatch`` calls it after its gates, and a seed calls it after ``apply`` and skips the gates.  No model and no tool
beyond python3, git and sh are used; the checks the tests plant are ``grep`` and ``test``.

- Equivalence: a run walked to carry-forward is driven at every stage three ways from the same starting files: through the
  real ``complete``; through ``apply`` and ``accept_effects``, as a seed does; and through ``apply`` and the sequence
  ``complete`` ran before the seam held it, written out here (``reference_effects``), which a change inside
  ``accept_effects`` or in how ``dispatch`` calls it does not move.  The saved state, the files under the run directory, the
  commits, what the call printed and what it noted on stderr are the same.  The files only ``complete`` leaves are its
  packet (``emit``) and the records its gates write, which a seed skips by design.
- Effects the walk does not reach: a preparatory fix, which ``complete`` commits before the knowledge home and the step's
  base (three ways, with the paths the gate would hand over); the hooks' writes, which the caller's ``extra_writes`` win,
  the lint finish, the terminal close and a control verb's ``advance`` (``EffectTests``).  The step's commit and the skill
  commit are made when a review is imported, which the walk (like every fixture) does without ``complete``:
  ``ReachTests`` covers the step's commit through the seam, and ``ImproveImportTests`` the skill and knowledge commits
  through ``dispatch``, with the review's own runtime stubbed out.  Not pinned: the ``core`` an import passes, which
  nothing an import's transition reads (it starts no Improve stage); ``CoreTests`` pins it for a producer's ``complete``.
- Reach: seeding through the seam stands the run at validate-existing (with a planted failing expectation that its packet
  names), implement, test, document and carry-forward, and ``next`` prints a packet for that stage.  A seed that skips the
  effects does not name the planted fault at validate-existing.
- Recorded by script: with every planted expectation matching, the seed reaches validate-existing with the stage recorded
  done by script and the run already past it.  A seed detects that from the rows its call added to ``history``.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))
import git_fixture  # noqa: E402
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_packet_view as packet_view  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402

CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
PINNED_DATE = "2026-01-02T03:04:05+0000"   # commits made by the engine's hooks are the same object in every arm
PACKET_HEAD = "ShipLoop navigator |"      # what ``emit`` prints after the effects have printed theirs
ITEM = {"id": "W1", "title": "The whole request"}
SYNTHETIC = {"outcome": "done", "summary": "Synthetic: recorded by the seed without doing it."}

# The files only ``complete`` leaves: its packet (``emit`` runs after the effects) and the records a stage's gates write
# (the step proof, the base run, the mutation check, validate-existing's rerun of its checks), which a seed skips by design.
GATE_OWNED = re.compile(r"packets/|tests/|expectations/[^/]*-complete-")
# Files whose text is the runtime's own (session names, receipts, timestamps): their names are compared, not their text.
RUNTIME_OWNED = ("until-loop/", "timeline.json")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{4})?")
SESSION = re.compile(r"innerloop-[0-9a-z_]+\.json")


def expectation(ident: str, statement: str, check: str) -> dict:
    """A ``works`` expectation of step S1 over a.py, whose check ShipLoop runs on entry to validate-existing."""
    return {"id": ident, "state": "works", "statement": statement, "steps": ["S1"], "paths": ["a.py"], "check": check}


# a.py holds ``x = 1``: the first check matches its state, the second is the planted fault (the file does not hold 99).
MATCHING = expectation("E2", "a.py exists", "test -f a.py")
PLANTED = expectation("E1", "PLANTED-E1: a.py holds x = 99", "grep -q 'x = 99' a.py")


def reference_effects(core, run_dir, before, after, action, preparatory=()):
    """What an accepted ``complete`` did after its gates, in the order it did it before ``accept_effects`` held the
    sequence.  The specification the seam is held to, written out so that a change inside the seam shows as a difference."""
    after, writes, payload = nav._transition(core, run_dir, before, after)
    nav.save(run_dir, after, writes)
    nav._lint_finish(run_dir, payload)
    nav._preparatory_commit(run_dir, before, after, action, list(preparatory))
    nav._skill_commit(run_dir, before, after, action)
    nav._knowledge_close(before, after, run_dir)
    nav._iteration_entry(run_dir, before, after)


class SeamCase(fx.RunDriver):
    """A run in a Git checkout (``RunDriver``) that can be snapshotted, run several ways and read back."""

    def setUp(self) -> None:
        home = tempfile.TemporaryDirectory(prefix="shiploop-seam-home-")
        self.addCleanup(home.cleanup)
        git_fixture.isolate_git_environment(self, home.name)
        pinned = mock.patch.dict(os.environ, {"GIT_AUTHOR_DATE": PINNED_DATE, "GIT_COMMITTER_DATE": PINNED_DATE})
        pinned.start()
        self.addCleanup(pinned.stop)
        super().setUp()
        scratch = tempfile.TemporaryDirectory(prefix="shiploop-seam-snap-")
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)
        self.snapshots = 0
        self.compared = {}       # stage -> the three arms' results, for each ``complete`` that ``compare_each_complete`` ran
        self.preparatory = []    # the paths a ``complete`` hands the effects as validate-existing's preparatory fix

    # -- the run, read back

    def snapshot(self) -> Path:
        self.snapshots += 1
        saved = self.scratch / str(self.snapshots)
        shutil.copytree(self.base, saved, symlinks=True)
        return saved

    def restore(self, saved: Path) -> None:
        shutil.rmtree(self.base)
        shutil.copytree(saved, self.base, symlinks=True)

    def left(self, act, first: int) -> types.SimpleNamespace:
        """Run ``act`` with the action ids it makes numbered from ``first`` (the same for every arm of one call, new for
        each call, so no id repeats one an earlier call accepted) and say what it left: the saved state, the run
        directory's files, the commits and the working tree's changes, and what it printed and noted on stderr."""
        numbers = itertools.count(first)
        printed, noted = io.StringIO(), io.StringIO()
        with mock.patch.object(nav, "_new_action", lambda stage: {"id": "nav-%032x" % next(numbers), "stage": stage}), \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(noted):
            act()
        return types.SimpleNamespace(
            state=self.state(), out=printed.getvalue(), err=noted.getvalue(),
            files={str(path.relative_to(self.run_dir)): path.read_bytes()
                   for path in sorted(self.run_dir.rglob("*")) if path.is_file()},
            commits=fx.git(self.repo, "log", "--format=%H%x09%s%n%b", "--all"),
            tree=fx.git(self.repo, "status", "--porcelain"))

    def normal(self, text: bytes) -> str:
        return TIMESTAMP.sub("<time>", text.decode("utf-8", "replace").replace(str(self.base), "<base>"))

    def assert_same(self, expected, actual) -> None:
        self.assertEqual(actual.state, expected.state)
        self.assertEqual(actual.commits, expected.commits)
        self.assertEqual(actual.tree, expected.tree)
        # ``complete`` prints what the effects print, then the packet.
        self.assertEqual(actual.out.partition(PACKET_HEAD)[0], expected.out)
        self.assertEqual(actual.err, expected.err)
        names = {SESSION.sub("innerloop-ID.json", name): name for name in expected.files}
        wanted = {SESSION.sub("innerloop-ID.json", name): name for name in actual.files}
        self.assertEqual(sorted(set(names) - set(wanted)), [], "files only the expected arm wrote")
        owned = sorted(name for name in set(wanted) - set(names))
        self.assertTrue(all(GATE_OWNED.match(name) for name in owned), owned)
        for name in sorted(set(names) & set(wanted)):
            if not (GATE_OWNED.match(wanted[name]) or wanted[name].startswith(RUNTIME_OWNED)):
                self.assertEqual(self.normal(actual.files[wanted[name]]), self.normal(expected.files[names[name]]), name)

    def compare_each_complete(self):
        """A ``dispatch`` for ``mock.patch.object(nav, "dispatch", ...)``: each ``complete`` runs three ways from the files
        as they stand, then the real one's files stay, so the walk goes on as a real run.

        - reference: ``apply`` and ``reference_effects``;
        - seam: ``apply`` and ``accept_effects``, as a harness seed calls it;
        - real: ``dispatch`` itself, whose gates the other two skip.

        The reference is independent of ``accept_effects``, so the seam and the real call are each held to it.
        """
        real_dispatch = nav.dispatch

        def dispatch(core, run_dir, state, args):
            if args.command != "complete":
                return real_dispatch(core, run_dir, state, args)
            stage, action = nav.current_stage(state), args.action
            submitted = store.read_record(Path(args.result))
            saved = self.snapshot()
            arms = {
                "reference": lambda: reference_effects(core, run_dir, state, nav.apply(state, action, submitted), action,
                                                       self.preparatory),
                "seam": lambda: nav.accept_effects(core, run_dir, state, nav.apply(state, action, submitted),
                                                   action_id=action, preparatory=self.preparatory),
                "real": lambda: real_dispatch(core, run_dir, state, args)}
            first = 100 * self.snapshots   # new ids for each call (one snapshot each); the same for its arms
            left = {}
            for name, act in arms.items():
                self.restore(saved)
                left[name] = self.left(act, first)
            with self.subTest(stage=stage):
                self.assert_same(left["reference"], left["seam"])
                self.assert_same(left["reference"], left["real"])
            self.compared[stage] = types.SimpleNamespace(**left)
            return 0
        return dispatch

    # -- a seed through the seam

    def step_plan(self, expectations: list) -> dict:
        """A done step-plan result over the fixture's paths whose expectations are ``expectations``."""
        return fx.fill(self.state(), "step-plan", {"outcome": "done", "summary": "Synthetic step plan.",
                                                   "paths": list(self.PATHS), "expectations": expectations},
                       self.run_dir)

    def build(self) -> None:
        """What the implement stage leaves in the checkout: an edit to a.py and a new module, both in the step's paths."""
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "new_mod.py").write_text("def entry(value):\n    return value\n")

    def seed(self, stop: str, records: dict | None = None, *, effects: bool = True, core=fx.CORE):
        """Record the stages before ``stop`` as a harness seed does; returns ``(state, by_script)``.

        Each stage gets a synthetic result merged with ``records[stage]``, through the pure ``apply`` (and
        ``finish_improve`` when the stage starts an Improve stage), then, unless ``effects`` is false, the engine's effects
        through ``accept_effects`` over the whole change.  No gate runs.  ``by_script`` is true when the transition recorded
        ``stop`` as done by script: it is among the history rows the call added, and the run already stands past it.
        """
        records = records or {}
        state = self.state()
        for _ in range(40):
            stage = nav.current_stage(state)
            if stage == stop:
                return state, False
            action = str(nav.current_action(state)["id"])
            result = dict(SYNTHETIC)
            if stage == "plan":
                result["work_items"] = [ITEM]
            result.update(records.get(stage) or {})
            if stage == "implement":
                self.build()
            before = state
            state = nav.apply(before, action, result)
            if state["active_improve"] is not None:
                state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt."})
            if effects:
                with contextlib.redirect_stderr(io.StringIO()):   # the step's commit line
                    state = nav.accept_effects(core, self.run_dir, before, state, action_id=action)
            else:
                nav.save(self.run_dir, state)
            if stop in [row["stage"] for row in state["history"][len(before["history"]):]]:
                return state, True
        raise AssertionError("the seed did not reach " + stop)

    def next_packet(self) -> tuple[str, str, str]:
        """What ``shiploop next`` prints, the packet file it names (or the print, when whole) and its stderr."""
        # No host session's notice on stderr, and no progress observer left running beside the run directory.
        quiet = {"SHIPLOOP_KEEPALIVE": "off", "SHIPLOOP_PROGRESS": "off", "PYTHONDONTWRITEBYTECODE": "1"}
        done = subprocess.run([sys.executable, str(CLI), "next", "--run-dir=" + str(self.run_dir)],
                              capture_output=True, text=True, check=False, env={**os.environ, **quiet})
        self.assertEqual(done.returncode, 0, done.stderr)
        full = packet_view.head_packet_path(done.stdout)
        return done.stdout, full.read_text(encoding="utf-8") if full else done.stdout, done.stderr


class EquivalenceTests(SeamCase):
    def test_the_seam_leaves_at_every_stage_what_complete_leaves(self):
        self.start()
        with mock.patch.object(nav, "dispatch", self.compare_each_complete()), contextlib.redirect_stderr(io.StringIO()):
            self.drive_to("carry-forward", improve_stage="carry-forward")
        compared = self.compared
        # Prelude stages (a reviewed one starts an Improve stage and its child), the inner stages and the end review.
        for stage in ("intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare", "step-plan",
                      "test-spec", "implement", "test", "document", "carry-forward"):
            self.assertIn(stage, compared)
        # The hooks the comparison reaches: prepare closes the knowledge and ShipLoop commits it; test-spec enters
        # validate-existing (every check matches, so it is recorded by script) and implement, where the step's base is
        # recorded after the call's commits.  The step's own commit is made when its review is imported, which this
        # walk (like every fixture) imports without ``complete``; ReachTests covers it through the seam.
        self.assertNotIn("docs(shiploop): record", compared["plan"].reference.commits)
        self.assertIn("docs(shiploop): record", compared["prepare"].reference.commits)
        self.assertIn("iterations/W1.json", compared["test-spec"].reference.files)
        self.assertNotIn("iterations/W1.json", compared["step-plan"].reference.files)

    def test_a_preparatory_fix_is_committed_before_the_step_base_is_recorded(self):
        """validate-existing is completed after the small fix its mismatch asked for.  The call commits the fix, then the
        knowledge home, then records the base of the implement step it enters: the last commit the call made."""
        self.start()
        state, by_script = self.seed("validate-existing", {"step-plan": self.step_plan([PLANTED, MATCHING])})
        self.assertFalse(by_script)
        (self.repo / "a.py").write_text("x = 99\n")   # the fix, inside E1's path
        fx.knowledge_support.write(state)             # and the knowledge home, which the call commits after the fix
        self.preparatory = ["a.py"]                   # what the gate hands the effects (the seam arms have no gate)
        with mock.patch.object(nav, "dispatch", self.compare_each_complete()), contextlib.redirect_stderr(io.StringIO()):
            self.complete(fx.DONE)
        arms = self.compared["validate-existing"]
        commits = arms.reference.commits
        self.assertIn("fix: preparatory fix for E1", commits)
        self.assertIn("knowledge after validate-existing", commits)
        self.assertLess(commits.index("knowledge after validate-existing"), commits.index("fix: preparatory fix"),
                        "the fix is committed first, then the knowledge home (the log lists the newest commit first)")
        state = self.state()
        self.assertEqual(nav.current_stage(state), "implement")
        iteration = nav.current_iteration(self.run_dir, state)
        self.assertIsNotNone(iteration)
        self.assertEqual(iteration.base, fx.git(self.repo, "rev-parse", "HEAD").strip())

    def test_a_control_verb_saves_the_same_state_without_the_advance_hooks(self):
        self.start()
        self.drive_to("discovery")
        for command in ("pause", "resume"):
            with self.subTest(command=command):
                args = types.SimpleNamespace(command=command, reason="The seam test pauses the run.")
                saved = self.snapshot()

                def changed():
                    state = self.state()
                    return state, nav.control(state, command, args.reason)

                def through_the_reference():
                    before, after = changed()
                    nav.save(self.run_dir, after)
                    nav._lint_finish(self.run_dir, None)
                    nav._knowledge_close(before, after, self.run_dir)
                    nav._iteration_entry(self.run_dir, before, after)

                def through_the_seam():
                    before, after = changed()
                    nav.accept_effects(fx.CORE, self.run_dir, before, after, advance=False)

                reference = self.left(through_the_reference, 1)
                self.restore(saved)
                seam = self.left(through_the_seam, 1)
                self.restore(saved)
                with mock.patch.object(nav, "accept_effects", wraps=nav.accept_effects) as effects:
                    real = self.left(lambda: nav.dispatch(fx.CORE, self.run_dir, self.state(), args), 1)
                self.assertEqual([call.kwargs.get("advance") for call in effects.call_args_list], [False])
                self.assert_same(reference, seam)
                self.assert_same(reference, real)
                self.assertEqual(real.state["status"], "paused" if command == "pause" else "active")


class EffectTests(SeamCase):
    """What the effects do that the run's stages do not show, put to ``accept_effects`` directly."""

    def accepted(self):
        state = self.state()
        action = nav.current_action(state)["id"]
        return state, nav.apply(state, action, SYNTHETIC), action

    def test_the_hooks_writes_are_saved_with_the_state_and_the_callers_win_a_clash(self):
        self.start()
        before, after, action = self.accepted()
        hooks = ({"hook.md": "from the hook\n", "both.md": "from the hook\n"}, None)
        with mock.patch.object(nav, "_lint_transition", return_value=hooks):
            nav.accept_effects(fx.CORE, self.run_dir, before, after, action_id=action,
                               extra_writes={"both.md": "from the caller\n"})
        self.assertEqual((self.run_dir / "hook.md").read_text(), "from the hook\n")
        self.assertEqual((self.run_dir / "both.md").read_text(), "from the caller\n")

    def test_the_lint_finish_gets_the_transitions_payload_once_the_state_is_saved(self):
        self.start()
        before, after, action = self.accepted()
        journal = self.run_dir / "lint" / "pending-A1.patch"
        journal.parent.mkdir()
        journal.write_bytes(b"journal\n")
        payload = {"pending": journal.name, "pending_sha256": hashlib.sha256(b"journal\n").hexdigest()}
        seen, finish = [], nav._lint_finish

        def finish_after_save(run_dir, given):
            seen.append((given, self.state()["revision"]))
            finish(run_dir, given)

        with mock.patch.object(nav, "_lint_transition", return_value=({}, payload)), \
                mock.patch.object(nav, "_lint_finish", finish_after_save):
            nav.accept_effects(fx.CORE, self.run_dir, before, after, action_id=action)
        self.assertEqual(seen, [(payload, after["revision"])])
        self.assertFalse(journal.exists(), "the finish removed the journal the transition named")

    def test_a_terminal_close_made_before_the_save_is_not_made_again_after_it(self):
        self.start()
        before, after, action = self.accepted()
        fx.knowledge_support.write(before)
        saved = self.snapshot()
        for closed in (True, False):
            with self.subTest(terminal_closed=closed):
                self.restore(saved)
                with contextlib.redirect_stderr(io.StringIO()):
                    nav.accept_effects(fx.CORE, self.run_dir, before, after, action_id=action, terminal_closed=closed)
                self.assertEqual("docs(shiploop)" in fx.git(self.repo, "log", "--format=%s"), not closed)

    def test_a_control_verb_runs_no_transition_hook_and_commits_no_accepted_result(self):
        self.start()
        state = self.state()
        paused = nav.control(state, "pause", "The seam test pauses the run.")
        with mock.patch.object(nav, "_transition") as transition, mock.patch.object(nav, "_preparatory_commit") as fix, \
                mock.patch.object(nav, "_skill_commit") as skill:
            nav.accept_effects(fx.CORE, self.run_dir, state, paused, advance=False)
        for hook in (transition, fix, skill):
            hook.assert_not_called()
        self.assertEqual(self.state()["status"], "paused")

    def test_advancing_without_the_accepted_action_id_is_refused(self):
        self.start()
        before, after, _action = self.accepted()
        with self.assertRaisesRegex(nav.NavigatorError, "needs the accepted action id"):
            nav.accept_effects(fx.CORE, self.run_dir, before, after)
        self.assertEqual(self.state(), before, "nothing was saved")


class CoreTests(SeamCase):
    def test_core_is_read_only_for_the_package_root_an_improve_stage_names(self):
        """``None`` and a package root give the same state; the Improve opening, which names callbacks, is what differs."""
        self.start()
        self.drive_to("spec")
        state = self.state()
        action = nav.current_action(state)["id"]
        started = nav.apply(state, action, {**SYNTHETIC, "primary": ["R-1"]})
        self.assertIsNotNone(started["active_improve"])
        saved = self.snapshot()
        openings = {}
        for label, core in (("none", None), ("package", fx.CORE)):
            self.restore(saved)
            after = self.left(lambda: nav.accept_effects(core, self.run_dir, state, started, action_id=action), 1)
            child = after.state["active_improve"]
            openings[label] = (after.state, standalone.receipt_path(child).with_name("parent-return.md").read_text())
        self.assertEqual(openings["none"][0], openings["package"][0])
        command = str(fx.PACKAGE / "scripts" / "shiploop")
        self.assertIn(command, openings["package"][1])
        self.assertNotIn(command, openings["none"][1])


class ImproveImportTests(SeamCase):
    """The Improve site of ``dispatch``: the import of an end review, with the review's own runtime and gates stubbed out
    (the Improve suites own them) and the effects it hands ``accept_effects`` left real."""

    def import_review(self, state: dict) -> str:
        """Import the Improve stage the run stands at through ``dispatch``; returns what it printed."""
        args = types.SimpleNamespace(command="complete", action=nav.improve_id(state), result=None, final_result=None)
        record = {"summary": "Synthetic Improve.", "review_refs": ["synthetic://r"], "check_refs": ["synthetic://c"]}
        printed = io.StringIO()
        with mock.patch.object(nav, "_skill_call_gate", return_value=None), \
                mock.patch.object(nav, "_derived_improve_receipt", return_value={"summary": "Synthetic review."}), \
                mock.patch.object(nav, "_improve_change_gate"), mock.patch.object(nav, "_duplicate_review_gate"), \
                mock.patch.object(standalone, "complete", return_value=(record, {})), \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(io.StringIO()):
            nav.dispatch(fx.CORE, self.run_dir, state, args)
        return printed.getvalue()

    def test_the_end_reviews_import_commits_the_skill_and_the_knowledge_it_accepted(self):
        """The last item's carry-forward is accepted when its end review is imported; the import then commits the skill the
        result created and the knowledge home as the stage left it, and saves the passes file with the state."""
        self.start()
        state, _by_script = self.seed("carry-forward", {"step-plan": self.step_plan([MATCHING])})
        skill = self.repo / ".claude" / "skills" / "review" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: review\ndescription: Review a change.\n---\n")
        action = str(nav.current_action(state)["id"])
        created = {"decision": "create", "reason": "The same review ran in two steps.",
                   "path": ".claude/skills/review/SKILL.md", "evidence": ["S1 and S2"]}
        before = state
        state = nav.apply(before, action, {**SYNTHETIC, "assumptions": [], "skill": created})
        with contextlib.redirect_stderr(io.StringIO()):   # the review is started, not finished
            state = nav.accept_effects(fx.CORE, self.run_dir, before, state, action_id=action)
        self.assertEqual(state["active_improve"]["stage"], "carry-forward")
        self.assertNotIn("feat(skill)", fx.git(self.repo, "log", "--format=%s"), "the result is accepted at the import")
        fx.knowledge_support.write(state)
        printed = self.import_review(state)
        log = fx.git(self.repo, "log", "--format=%s")
        self.assertIn("feat(skill): create review", log)
        self.assertIn("knowledge after carry-forward", log)
        self.assertLess(log.index("knowledge after carry-forward"), log.index("feat(skill)"),
                        "the skill is committed first, then the knowledge home (the log lists the newest commit first)")
        self.assertIn("ShipLoop committed the review skill as", printed)
        self.assertEqual(fx.git(self.repo, "status", "--porcelain", ".claude", "docs"), "")
        saved = self.state()
        self.assertIsNone(saved["active_improve"])
        self.assertIn(action, saved["accepted"])
        self.assertTrue((self.run_dir / "improve" / action / nav.PASSES_FILE).is_file())


class ReachTests(SeamCase):
    def test_seeding_through_the_seam_reaches_each_stage_and_next_prints_its_packet(self):
        self.start()
        records = {"step-plan": self.step_plan([PLANTED, MATCHING])}
        for stage in ("validate-existing", "implement", "test", "document", "carry-forward"):
            with self.subTest(stage=stage):
                state, by_script = self.seed(stage, records)
                self.assertFalse(by_script)
                self.assertEqual(nav.current_stage(state), stage)
                head, packet, stderr = self.next_packet()
                self.assertIn("ShipLoop navigator | " + stage + " |", head)
                self.assertEqual(stderr, "", "the seed left nothing for the next call to repair")
                if stage == "validate-existing":
                    # The checks ran on entry, so the packet carries the planted fault and leaves the control alone.
                    self.assertRegex(packet, r"E1 works\s+PLANTED-E1: a\.py holds x = 99.*-> DOES NOT MATCH, exit 1")
                    self.assertRegex(packet, r"E2 works\s+a\.py exists.*-> MATCHES")
                if stage == "document":
                    # The step has a change to document and an iteration record to commit it from.
                    self.assertIsNotNone(nav.current_iteration(self.run_dir, state))
                if stage == "carry-forward":
                    # The document stage's review was imported by the seed, and the step's commit made with it.
                    self.assertIn("feat(W1/S1)", fx.git(self.repo, "log", "--format=%s"))

    def test_a_seed_without_the_effects_misses_what_they_write(self):
        """The control for the planted signal: the pure ``apply`` seed reaches validate-existing, and its packet lacks
        the results the checks write, which is what the seam exists to supply."""
        self.start()
        state, _by_script = self.seed("validate-existing", {"step-plan": self.step_plan([PLANTED])}, effects=False)
        self.assertEqual(nav.current_stage(state), "validate-existing")
        _head, packet, _stderr = self.next_packet()
        self.assertNotIn("DOES NOT MATCH", packet)
        self.assertNotIn("PLANTED-E1", packet)


class RecordedByScriptTests(SeamCase):
    def test_every_expectation_matching_records_validate_existing_done_without_a_packet(self):
        self.start()
        state, by_script = self.seed("validate-existing", {"step-plan": self.step_plan([MATCHING])})
        self.assertTrue(by_script)
        rows = [row for row in state["history"] if row["stage"] == "validate-existing"]
        self.assertEqual([row["outcome"] for row in rows], ["done"])
        self.assertIn("ShipLoop ran every expectation check", rows[0]["summary"])
        self.assertEqual(nav.current_stage(state), "implement", "the run is already past the stage")
        self.assertFalse((self.run_dir / "packets" / (rows[0]["action"] + ".md")).exists(), "no packet was issued")
        head, _packet, _stderr = self.next_packet()
        self.assertIn("ShipLoop navigator | implement |", head)

    def test_a_planted_mismatch_leaves_the_stage_to_the_model(self):
        self.start()
        state, by_script = self.seed("validate-existing", {"step-plan": self.step_plan([PLANTED, MATCHING])})
        self.assertFalse(by_script)
        self.assertNotIn("validate-existing", [row["stage"] for row in state["history"]])
        self.assertEqual(nav.current_stage(state), "validate-existing")


if __name__ == "__main__":
    unittest.main()
