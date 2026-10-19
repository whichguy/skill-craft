#!/usr/bin/env python3
"""The release slice of the E2E harness (test/shiploop_e2e/release_slice.py, run.py `--seed-at release-plan`), with no model, no
platform and no real `sf`.

A release slice starts a ShipLoop run at its release stages with an already-built product, to test deployment without paying for
the build. These checks cover, in order:

  SeedTest          the seed on the checkout's own ShipLoop CLI: the run stands at release-plan, every earlier stage accepted in graph
                    order, the case's product committed in the worktree after the item's base, the case's own knowledge home, the
                    records the skipped stages leave, and the input gates of release-plan (its packet quotes them; a model-shaped
                    result passes `complete --check-only`)
  CaseKeysTest      the case's seed_product, seed_home and seed_release keys, and the checks that wait for the return
  GradeTest         the release verdict on run folders made by hand: stages accepted, where the run stopped and why, and whether the
                    deploy fell in the release stage (guard-log time against stage acceptance)
  ModeTest          --platform-existing: who may use it, what the commands are told, what a resume keeps
  Rehearsal         the whole harness (run.main) with a fake Grok that drives ShipLoop's own navigator through the guarded `sf` wrapper
                    to a fake org (test/shiploop_e2e/fake_sf.py): fresh, update + keep, update + cleanup, and a run that stops early

Nothing here reaches an org: every sf call is the fake's, and the suite runs with no `sf` on PATH.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(E2E))
import environment  # noqa: E402
import hosts  # noqa: E402
import listeners  # noqa: E402
import release_slice  # noqa: E402
import run  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

CASE = "battleship-salesforce"
FIXTURES = E2E / "fixtures"
PRODUCT = FIXTURES / "battleship-salesforce-reference"
HOME = FIXTURES / "battleship-salesforce-home"
FAKE_SF = E2E / "fake_sf.py"
PRODUCT_FILES = release_slice.product_files(PRODUCT, ["README.md"])


def cases() -> dict:
    return json.loads((E2E / "cases.json").read_text())


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    return done.stdout.strip()


def state_of(run_dir: str | Path) -> dict:
    return store.read_record(Path(run_dir) / "state.md")


def shiploop(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    # A CI runner's system config declares Git LFS filters, which a managed workspace refuses; the case's own Git config only.
    done = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    if check and done.returncode:
        raise AssertionError(f"shiploop {' '.join(args[:2])} exited {done.returncode}:\n{done.stderr[-1500:]}{done.stdout[-1500:]}")
    return done


class Seeded:
    """One seeded run in a temporary folder: ``seed`` is what run.seed_run returned."""

    def __init__(self, stage: str):
        self.tmp = Path(tempfile.mkdtemp(prefix="release-slice-")).resolve()
        self.work = self.tmp / "work"
        self.work.mkdir()
        built = run.seed_materials(CASE, stage)
        self.seed = run.seed_run(CLI, self.work, self.tmp, cases()[CASE]["prompt"], stage, product=built["product"],
                                 home_fixture=built["home_fixture"], work_item=built["work_item"], records=built["records"],
                                 exclude=built["exclude"])
        self.run_dir = Path(self.seed["run_dir"])
        self.state = state_of(self.run_dir)
        self.worktree = Path(self.state["repo"])

    def close(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


class SeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.slice = Seeded("release-plan")
        cls.addClassCleanup(cls.slice.close)

    def test_the_run_stands_at_release_plan_with_every_earlier_stage_accepted_in_graph_order(self) -> None:
        state = self.slice.state
        graph = [*stage_spec.PRELUDE, *stage_spec.INNER, *stage_spec.OUTER[:stage_spec.OUTER.index("release-plan")]]
        self.assertEqual([row["stage"] for row in state["history"]], graph)
        self.assertEqual({row["outcome"] for row in state["history"]}, {"done"})
        self.assertEqual(self.slice.seed["skipped"], graph)
        self.assertEqual((run.metrics.current_stage(state), state["status"]), ("release-plan", "active"))
        self.assertEqual(self.slice.seed["stage"], "release-plan")
        self.assertEqual(state["completed_work_items"], ["W1"])
        self.assertEqual(state["work_items"][0]["id"], "W1")
        self.assertEqual((state["delegation"], state["execution_mode"]), ("inline", "navigator-worktree"))
        self.assertIsNone(state["active_improve"])

    def test_the_case_s_product_is_committed_in_the_worktree_after_the_item_base_and_not_in_the_source_checkout(self) -> None:
        worktree, work, seed = self.slice.worktree, self.slice.work, self.slice.seed
        self.assertEqual(git(worktree, "log", "--format=%s"), "feat: W1 Build and prove the Battleship game\nseed: baseline")
        self.assertEqual(git(worktree, "rev-parse", "HEAD"), seed["product"]["commit"])
        self.assertEqual(git(worktree, "rev-parse", "HEAD~1"), seed["start_head"])
        self.assertEqual(sorted(git(worktree, "diff", "--name-only", "HEAD~1", "HEAD").splitlines()), PRODUCT_FILES)
        self.assertEqual(seed["product"]["files"], len(PRODUCT_FILES))
        self.assertEqual(git(worktree, "status", "--porcelain"), "")
        self.assertFalse((worktree / "README.md").read_text().startswith("# battleship-salesforce-reference"))
        # The source checkout has only what the run started from: the return puts the product there.
        self.assertEqual(git(work, "rev-parse", "HEAD"), seed["start_head"])
        self.assertFalse((work / "force-app").exists() or (work / "sfdx-project.json").exists())
        # The item's base is the baseline: the product was built after it.
        base = store.read_record(self.slice.run_dir / "lint" / "items" / "W1.md")
        self.assertEqual(base["head"], seed["start_head"])
        self.assertEqual(seed["item_bases"], ["W1"])

    def test_the_fixture_s_own_files_never_reach_the_run(self) -> None:
        """The reference's README documents the harness (its checks, its self-test); a model must not read it."""
        for root in (self.slice.worktree, self.slice.work):
            self.assertFalse(list(root.rglob("battleship-salesforce-reference*")), root)
            for path in root.rglob("*"):
                if path.is_file() and ".git" not in path.parts:
                    text = path.read_text(errors="replace")
                    for needle in ("battleship_salesforce.py", "selftest", "the harness's own fixture", "oracle"):
                        self.assertNotIn(needle, text, f"{path.relative_to(root)} mentions {needle}")
        self.assertNotIn("README.md", git(self.slice.worktree, "diff", "--name-only", "HEAD~1", "HEAD").splitlines())

    def test_the_knowledge_home_is_the_case_s_own_and_records_json_stays_behind(self) -> None:
        worktree = self.slice.worktree
        for name in ("spec.md", "environment.md", "architecture.md"):
            self.assertEqual((worktree / "docs" / "shiploop" / name).read_text(), (HOME / name).read_text())
            self.assertIn(f"docs/shiploop/{name}", git(worktree, "show", "--name-only", "--format=", "HEAD~1").splitlines())
        self.assertEqual(sorted(path.name for path in (worktree / "docs" / "shiploop").iterdir()),
                         ["architecture.md", "environment.md", "spec.md"])
        self.assertEqual(self.slice.seed["home"], ["docs/shiploop/spec.md", "docs/shiploop/environment.md", "docs/shiploop/architecture.md"])
        self.assertEqual(self.slice.seed["home_fixture"], "battleship-salesforce-home")
        env = (HOME / "environment.md").read_text()
        for needle in ("--target-org de", "sf project deploy start --target-org de", "sf org assign permset --name SLBattle_Access",
                       "sf apex run test --target-org de --class-names SLBattleEngineTest"):
            self.assertIn(needle, env)
        spec = (HOME / "spec.md").read_text()
        self.assertEqual(re.findall(r"^### (R-\d+) ", spec, re.M), [f"R-{n}" for n in range(1, 13)])
        arch = (HOME / "architecture.md").read_text()
        self.assertEqual(re.findall(r"^### (AD-\d+) ", arch, re.M), [f"AD-{n}" for n in range(1, 5)])

    def test_the_skipped_stages_leave_the_records_the_later_stages_read(self) -> None:
        state = self.slice.state
        by_stage = {row["stage"]: state["accepted"][row["action"]] for row in state["history"]}
        plan = by_stage["step-plan"]
        self.assertEqual([c["id"] for c in plan["criteria"]], ["C1", "C2", "C3"])
        self.assertEqual({command["suite"] for command in plan["test_commands"]}, {"focused", "check"})
        self.assertIn("force-app/**", plan["paths"])
        known = ({f"R-{n}" for n in range(1, 13)} | {f"AD-{n}" for n in range(1, 5)})
        self.assertEqual(set(plan["follows"]), known)  # every entry the item follows exists in the home
        suite = by_stage["system-test-author"]
        self.assertEqual([command["suite"] for command in suite["system_commands"]], ["regression", "regression"])
        self.assertTrue(all("--target-org de" in command["command"] and "deploy" not in command["command"]
                            for command in suite["system_commands"]))  # the deploy is the release stage's, not the suite's
        self.assertEqual([(row["id"], row["disposition"], row["consumer"]) for row in suite["assumptions"]],
                         [("A1", "open", "release-plan")])
        for stage in ("system-test", "product-acceptance"):
            self.assertIn("without doing it", by_stage[stage]["summary"])
        self.assertEqual(by_stage["plan"]["work_items"][0]["title"], "Build and prove the Battleship game")

    def test_the_release_plan_packet_quotes_the_system_commands_and_the_open_item_and_lists_the_home(self) -> None:
        packet = shiploop("next", f"--run-dir={self.slice.run_dir}").stdout
        self.assertTrue(packet.startswith("ShipLoop navigator | release-plan |"), packet[:120])
        self.assertIn("sf apex run test --target-org de --class-names SLBattleEngineTest", packet)
        self.assertIn("- A1: SYS-ORG-SUITE", packet)
        for name in ("spec.md", "environment.md", "architecture.md"):
            self.assertIn(f"KNOWLEDGE/{name}", packet)
        self.assertNotIn("not written yet", packet)
        self.assertNotIn("not recorded by", packet)

    def test_a_model_shaped_release_plan_result_passes_every_script_gate_and_one_without_consumer_checks_does_not(self) -> None:
        action = str(run.metrics.engine_state(self.slice.run_dir)["action"]["id"])
        environment_md = self.slice.worktree / "docs" / "shiploop" / "environment.md"
        original = environment_md.read_text()
        self.addCleanup(environment_md.write_text, original)
        environment_md.write_text(original + "\n- Release plan: deploy, assign the permission set, run both test classes.\n")
        result = {"assumptions": [], "headline": "Release plan: deploy, assign, run the org tests", "outcome": "done",
                  "summary": "Plan only. Deploy with sf project deploy start --target-org de, assign SLBattle_Access, run both classes.",
                  "evidence_refs": [str(environment_md)],
                  "consumer_checks": [{"command": "sf apex run test --target-org de --class-names SLBattleGameTest --synchronous "
                                                  "--result-format human", "suite": "check"}],
                  "consumer_entry": {"how": "App Launcher, app SLBattle, tab SLBattle_Board",
                                     "sources": ["force-app/main/default/applications/SLBattle.app-meta.xml"]}}
        inbox = self.slice.run_dir / "inbox" / f"{action}.md"

        def submit(value: dict) -> subprocess.CompletedProcess:
            inbox.write_text("```shiploop-state\n" + json.dumps(value, indent=2) + "\n```\n")
            return shiploop("complete", f"--run-dir={self.slice.run_dir}", f"--action={action}", "--check-only", check=False)

        accepted = submit(result)
        self.assertEqual(accepted.returncode, 0, accepted.stderr + accepted.stdout)
        self.assertIn("every script gate for release-plan accepts this result", accepted.stdout)
        refused = submit({key: value for key, value in result.items() if key != "consumer_checks"})
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("consumer_checks", refused.stderr + refused.stdout)

    def test_the_return_plan_sees_exactly_the_product_as_the_delta(self) -> None:
        done = shiploop("workspace", "plan-return", f"--workspace-root={self.slice.run_dir.parent}")
        match = re.search(r"Undecided \((\d+)\): (.+)\.", done.stdout)
        self.assertIsNotNone(match, done.stdout)
        self.assertEqual(int(match.group(1)), len(PRODUCT_FILES))
        self.assertEqual(sorted(match.group(2).split(", ")), PRODUCT_FILES)

    def test_the_seed_prompt_names_the_stage_and_the_built_product_and_the_step_plan_one_is_unchanged(self) -> None:
        text = run.seed_prompt(CLI, "/r", "Build it.", "inline", "release-plan")
        self.assertIn("recorded its stages before release-plan without doing them", text)
        self.assertIn("already built and committed in the run's worktree", text)
        self.assertIn("with inline delegation", text)
        self.assertIn('next --run-dir "/r"', text)
        old = run.seed_prompt(CLI, "/r", "Build it.")
        self.assertIn("recorded its stages before step-plan without doing them, so the request itself is the specification", old)
        self.assertNotIn("already built", old)


class SystemTestAuthorSeedTest(unittest.TestCase):
    def test_a_seed_at_the_first_outer_stage_records_the_whole_inner_loop_and_commits_the_product(self) -> None:
        slice_ = Seeded("system-test-author")
        self.addCleanup(slice_.close)
        state = slice_.state
        self.assertEqual(run.metrics.current_stage(state), "system-test-author")
        self.assertEqual([row["stage"] for row in state["history"]], [*stage_spec.PRELUDE, *stage_spec.INNER])
        self.assertEqual(len(git(slice_.worktree, "diff", "--name-only", "HEAD~1", "HEAD").splitlines()), len(PRODUCT_FILES))
        self.assertEqual(release_slice.graded_stages("system-test-author"), stage_spec.OUTER)
        packet = shiploop("next", f"--run-dir={slice_.run_dir}").stdout
        self.assertTrue(packet.startswith("ShipLoop navigator | system-test-author |"), packet[:120])


class CaseKeysTest(unittest.TestCase):
    def case(self) -> dict:
        return copy.deepcopy(cases()[CASE])

    def test_the_case_declares_a_valid_product_home_and_release(self) -> None:
        case = cases()[CASE]
        self.assertEqual(release_slice.validate_case(CASE, case), [])
        self.assertEqual((case["seed_product"], case["seed_home"]), ("battleship-salesforce-reference", "battleship-salesforce-home"))
        self.assertEqual(case["seed_release"]["source_checks"], ["project"])
        self.assertEqual(case["seed_release"]["operation"]["argv"], ["project", "deploy", "start"])
        self.assertEqual(case["seed_release"]["operation"]["stage"], "release")
        self.assertEqual(run.seed_materials(CASE, None), None)
        self.assertEqual(run.seed_materials(CASE, "step-plan"), None)
        built = run.seed_materials(CASE, "release-plan")
        self.assertEqual((built["product"], built["home_fixture"], built["exclude"]), (PRODUCT, HOME, ["README.md"]))
        self.assertEqual(built["work_item"]["id"], "W1")

    def test_every_other_case_has_nothing_to_validate_and_is_refused_a_release_slice_by_name(self) -> None:
        for name, case in cases().items():
            if name != CASE:
                self.assertEqual(release_slice.validate_case(name, case), [], name)
        with self.assertRaises(SystemExit) as raised:
            run.seed_materials("hello", "release-plan")
        self.assertIn("seed_product", str(raised.exception))
        self.assertIn("case 'hello'", str(raised.exception))
        with self.assertRaises(SystemExit) as raised:
            run.seed_materials("custom", "release-plan")
        self.assertIn("custom --prompt", str(raised.exception))

    def test_a_malformed_case_is_refused_with_every_problem_named(self) -> None:
        def broken(edit) -> str:
            case = self.case()
            edit(case)
            return "; ".join(release_slice.validate_case(CASE, case))

        self.assertIn("seed_release is missing", broken(lambda c: c.pop("seed_release")))
        self.assertIn("seed_product is missing", broken(lambda c: c.pop("seed_product")))
        self.assertIn("seed_home is missing", broken(lambda c: c.pop("seed_home")))
        self.assertIn("is not a folder", broken(lambda c: c.update(seed_product="nope")))
        self.assertIn("name of a folder", broken(lambda c: c.update(seed_home="../x")))
        self.assertIn("source_checks names 'tests2'", broken(lambda c: c["seed_release"].update(source_checks=["tests2"])))
        self.assertIn("product_exclude names 'NOPE.md'", broken(lambda c: c["seed_release"].update(product_exclude=["NOPE.md"])))
        self.assertIn("operation is {name, stage, log, argv}", broken(lambda c: c["seed_release"]["operation"].pop("log")))
        self.assertIn("must be an OUTER stage that another OUTER stage precedes",
                      broken(lambda c: c["seed_release"]["operation"].update(stage="system-test-author")))
        self.assertIn("must be an OUTER stage that another OUTER stage precedes",
                      broken(lambda c: c["seed_release"]["operation"].update(stage="verify")))
        self.assertIn("path relative to the run's output folder",
                      broken(lambda c: c["seed_release"]["operation"].update(log="/etc/passwd")))
        self.assertIn("seed_release must be an object", broken(lambda c: c.update(seed_release=[])))

    def test_a_home_fixture_missing_a_file_or_naming_a_stage_that_does_not_exist_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixtures = Path(raw)
            shutil.copytree(HOME, fixtures / "home")
            shutil.copytree(PRODUCT, fixtures / "product")
            (fixtures / "home" / "architecture.md").unlink()
            records = json.loads((fixtures / "home" / "records.json").read_text())
            records["results"]["nonsense"] = {}
            del records["work_item"]["title"]
            (fixtures / "home" / "records.json").write_text(json.dumps(records))
            case = dict(self.case(), seed_product="product", seed_home="home")
            with mock.patch.object(release_slice, "FIXTURES", fixtures):
                problems = "; ".join(release_slice.validate_case(CASE, case))
        self.assertIn("seed_home has no architecture.md", problems)
        self.assertIn("results names 'nonsense', which is not a stage", problems)
        self.assertIn("needs a work_item with an id and a title", problems)

    def test_the_checks_that_read_the_source_wait_for_the_return_and_the_fixture_s_own_files_do_not_count(self) -> None:
        checks = cases()[CASE]["checks"]
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            (work / "README.md").write_text("# a source checkout before the return\n")
            run_these, left = release_slice.split_checks(checks, ["project"], work, PRODUCT, ["README.md"])
            self.assertEqual(len(run_these), 4)
            self.assertEqual([item["command"] for item in left], [checks[0]])
            self.assertIn("has not been returned", left[0]["reason"])
            self.assertIn("force-app", left[0]["reason"])
            self.assertNotIn("README.md", left[0]["reason"])
            (work / "docs" / "shiploop").mkdir(parents=True)
            (work / "docs" / "shiploop" / "spec.md").write_text("the seed's own home is not the product\n")
            self.assertEqual(len(release_slice.split_checks(checks, ["project"], work, PRODUCT, ["README.md"])[1]), 1)
            (work / "sfdx-project.json").write_text("{}")  # one file of the product is enough: the return puts them all there
            run_these, left = release_slice.split_checks(checks, ["project"], work, PRODUCT, ["README.md"])
            self.assertEqual((run_these, left), (checks, []))  # returned (committed or not): every check runs
            self.assertEqual(release_slice.split_checks(checks, [], work, PRODUCT, ["README.md"]), (checks, []))


def make_run(root: Path, accepted: list[tuple[str, int]], *, status: str = "active", stage: str | None = None, reason: str | None = None,
             now: float = 1_800_000_000.0) -> Path:
    """A run folder holding only what the verdict reads: state.md with a history, and timeline.json. ``accepted`` is
    [(stage, seconds after ``now`` it was accepted)] in order."""
    run_dir = root / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    history = [{"stage": name, "outcome": "done", "summary": "s", "workitem": None, "action": f"nav-{index:032x}"}
               for index, (name, _) in enumerate(accepted)]
    state = {"status": status, "stage": stage or (accepted[-1][0] if accepted else "release-plan"), "history": history,
             "accepted": {}, **({"status_reason": reason} if reason else {})}
    store.write_record(run_dir / "state.md", state)
    stamps = {row["action"]: datetime.fromtimestamp(now + offset, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
              for row, (_, offset) in zip(history, accepted)}
    (run_dir / "timeline.json").write_text(json.dumps({"accepted": stamps}))
    return run_dir


def guard_line(offset: float, argv: list[str], *, call: str, decision: str = "allowed", exit: int | None = 0,
               now: float = 1_800_000_000.0) -> str:
    """What the guard logs for one call: a decision line and, for an allowed call that finished, its end line (two lines)."""
    stamp = datetime.fromtimestamp(now + offset).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    lines = [json.dumps({"ts": stamp, "call": call, "org": "de", "prefix": "SLBattle", "argv": argv, "decision": decision, "reason": "x"})]
    if decision == "allowed" and exit is not None:
        lines.append(json.dumps({"ts": stamp, "call": call, "end": True, "exit": exit, "stderr_head": "", "interrupted": False}))
    return "\n".join(lines)


DEPLOY = ["project", "deploy", "start", "--target-org", "de"]
SIX = ["release-plan", "release-check", "release", "release-verify", "operations", "handoff"]


class GradeTest(unittest.TestCase):
    """The release verdict, from files only: ShipLoop's state and timeline, and the guard log."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)
        (self.out / "platform").mkdir()
        self.case = cases()[CASE]
        self.seeded = {"stage": "release-plan"}

    def log(self, *lines: str) -> None:
        (self.out / "platform" / "sf-calls.jsonl").write_text("\n".join(lines) + "\n")

    def grade(self, run_dir: Path, **extra) -> dict:
        state = run.metrics.engine_state(run_dir)
        return release_slice.grade(seeded=self.seeded, run_dir=run_dir, state=state, out=self.out, case=self.case,
                                   skipped_checks=extra.pop("skipped_checks", []), **extra)

    def finished(self, **kw) -> Path:
        return make_run(self.out, [(name, 10 * (index + 1)) for index, name in enumerate(SIX)], status="done", stage="done", **kw)

    def test_every_stage_accepted_and_the_deploy_inside_the_release_stage_passes(self) -> None:
        self.log(guard_line(-5, ["org", "list", "--json"], call="a1"), guard_line(25, DEPLOY, call="b2"))
        graded = self.grade(self.finished())
        self.assertTrue(graded["pass"], graded)
        self.assertEqual([(row["stage"], row["accepted"]) for row in graded["stages"]], [(name, True) for name in SIX])
        self.assertIsNone(graded["stopped"])
        operation = graded["operation"]
        self.assertTrue(operation["pass"], operation)
        self.assertEqual((operation["stage"], operation["after"]), ("release", "release-check"))
        self.assertEqual([call["at"] for call in operation["calls"]], ["in"])
        self.assertIn("1 deploy call(s), all inside the release stage, 1 exit 0", operation["reason"])

    def test_the_ends_of_the_window_belong_to_it(self) -> None:
        for offset in (20, 30):  # release-check was accepted at +20, release at +30
            with self.subTest(offset=offset):
                self.log(guard_line(offset, DEPLOY, call="b2"))
                self.assertTrue(self.grade(self.finished())["operation"]["pass"])

    def test_a_deploy_before_release_check_was_accepted_fails_the_verdict_and_names_it(self) -> None:
        self.log(guard_line(15, DEPLOY, call="early"), guard_line(25, DEPLOY, call="b2"))
        graded = self.grade(self.finished())
        self.assertFalse(graded["pass"])
        self.assertFalse(graded["operation"]["pass"])
        self.assertEqual([call["at"] for call in graded["operation"]["calls"]], ["before", "in"])
        self.assertIn("deploy outside the release stage: 1 before release-check was accepted (of 2)", graded["operation"]["reason"])
        self.assertIsNone(graded["stopped"])  # every stage was accepted: only the deploy is wrong

    def test_a_help_or_dry_run_of_the_deploy_command_is_not_a_deploy(self) -> None:
        """Live release slice 2026-10-18 (bs-release-update-436528): `sf project deploy start --help` during release-check was
        counted as a deploy outside the release stage, though the one real deploy fell inside it."""
        self.log(guard_line(15, ["project", "deploy", "start", "--help"], call="help"),
                 guard_line(16, [*DEPLOY, "--dry-run"], call="dry"), guard_line(25, DEPLOY, call="b2"))
        graded = self.grade(self.finished())
        self.assertTrue(graded["operation"]["pass"], graded["operation"])
        self.assertEqual([call["call"] for call in graded["operation"]["calls"]], ["b2"])

    def test_a_deploy_after_release_was_accepted_fails(self) -> None:
        self.log(guard_line(25, DEPLOY, call="b2"), guard_line(45, DEPLOY, call="late"))
        graded = self.grade(self.finished())
        self.assertFalse(graded["pass"])
        self.assertEqual([call["at"] for call in graded["operation"]["calls"]], ["in", "after"])
        self.assertIn("1 after release was accepted", graded["operation"]["reason"])

    def test_a_deploy_that_failed_or_was_cut_off_is_not_a_deploy_that_happened(self) -> None:
        """In update mode the kept app answers every check, so a deploy that did not work must fail the verdict on its own."""
        for exit_code, words in ((1, "exit 1"), (None, "no end line")):
            with self.subTest(exit=exit_code):
                self.log(guard_line(25, DEPLOY, call="b2", exit=exit_code))
                graded = self.grade(self.finished())
                self.assertFalse(graded["pass"])
                self.assertEqual([call["at"] for call in graded["operation"]["calls"]], ["in"])
                self.assertIn(f"no deploy succeeded in the release stage (1 call(s): {words})", graded["operation"]["reason"])
        self.log(guard_line(22, DEPLOY, call="try", exit=1), guard_line(25, DEPLOY, call="again", exit=0))  # a retry in the stage is fine
        graded = self.grade(self.finished())
        self.assertTrue(graded["pass"], graded)
        self.assertIn("2 deploy call(s), all inside the release stage, 1 exit 0", graded["operation"]["reason"])

    def test_no_allowed_deploy_fails_and_a_denied_one_or_another_command_does_not_count(self) -> None:
        self.log(guard_line(25, DEPLOY, call="no", decision="denied"), guard_line(26, ["project", "deploy", "validate", "--source-dir", "force-app",
                                                                                     "--target-org", "de"], call="dry"))
        graded = self.grade(self.finished())
        self.assertFalse(graded["pass"])
        self.assertEqual(graded["operation"]["calls"], [])
        self.assertIn("holds no allowed deploy (project deploy start)", graded["operation"]["reason"])

    def test_the_harness_s_own_preflight_calls_are_not_the_model_s(self) -> None:
        self.log(guard_line(0, DEPLOY, call="pre"), guard_line(25, DEPLOY, call="b2"))
        graded = self.grade(self.finished(), preflights=[(0, 2)])  # the preflight's call is lines 0 and 1: its decision and its end
        self.assertTrue(graded["pass"], graded)
        self.assertEqual([call["call"] for call in graded["operation"]["calls"]], ["b2"])

    def test_a_run_that_stopped_says_where_and_why(self) -> None:
        run_dir = make_run(self.out, [("release-plan", 10)], status="blocked", stage="release-check",
                           reason="access: the org alias de is not connected")
        self.log(guard_line(11, DEPLOY, call="x"))
        graded = self.grade(run_dir)
        self.assertFalse(graded["pass"])
        self.assertEqual([row["accepted"] for row in graded["stages"]], [True, False, False, False, False, False])
        self.assertEqual(graded["stopped"], {"stage": "release-check", "engine_status": "blocked", "engine_stage": "release-check",
                                              "reason": "access: the org alias de is not connected"})
        self.assertEqual([call["at"] for call in graded["operation"]["calls"]], ["before"])  # release-check was never accepted
        lines = release_slice.lines(graded)
        self.assertEqual(lines[0], "1/6 stages accepted from release-plan: release-plan")
        self.assertIn("stopped at release-check: access: the org alias de is not connected", lines)

    def test_an_active_run_that_the_host_left_is_named_and_a_run_that_never_began_accepts_nothing(self) -> None:
        graded = self.grade(make_run(self.out, [("release-plan", 10), ("release-check", 20)], status="active", stage="release"))
        self.assertEqual(graded["stopped"]["stage"], "release")
        self.assertEqual(graded["stopped"]["reason"], "ShipLoop was active at release, so release was not accepted")
        empty = self.out / "empty"
        empty.mkdir()
        graded = self.grade(make_run(empty, [], status="active", stage="release-plan"))
        self.assertEqual((graded["stopped"]["stage"], [row["accepted"] for row in graded["stages"]]), ("release-plan", [False] * 6))

    def test_a_seed_at_the_first_outer_stage_grades_the_stages_before_the_release_too(self) -> None:
        self.seeded = {"stage": "system-test-author"}
        names = list(stage_spec.OUTER)
        run_dir = make_run(self.out, [(name, 10 * (index + 1)) for index, name in enumerate(names)], status="done", stage="done")
        self.log(guard_line(10 * (names.index("release") + 1) - 5, DEPLOY, call="b2"))
        graded = self.grade(run_dir)
        self.assertEqual([row["stage"] for row in graded["stages"]], names)
        self.assertTrue(graded["pass"], graded)

    def test_a_case_without_an_operation_is_graded_on_the_stages_alone(self) -> None:
        self.case = copy.deepcopy(self.case)
        del self.case["seed_release"]["operation"]
        graded = self.grade(self.finished())
        self.assertTrue(graded["pass"])
        self.assertNotIn("operation", graded)

    def test_the_skipped_checks_ride_along_and_show_in_the_report_lines(self) -> None:
        left = [{"command": "check project", "reason": "the product has not been returned"}]
        self.log(guard_line(25, DEPLOY, call="b2"))
        graded = self.grade(self.finished(), skipped_checks=left)
        self.assertEqual(graded["skipped_checks"], left)
        self.assertIn("left out: check project (the product has not been returned)", release_slice.lines(graded))


class ModeTest(unittest.TestCase):
    """--platform-existing: which cases may use it, what the commands are told, and that a resume keeps its run's mode."""

    SPEC_UPDATE = {"existing": ["update"], "cleanup": "x"}

    def test_a_case_that_lists_the_mode_may_use_it_and_the_default_is_fresh(self) -> None:
        self.assertEqual(run.platform_existing_mode(None, "c", self.SPEC_UPDATE), "fresh")
        self.assertEqual(run.platform_existing_mode("fresh", "c", None), "fresh")
        self.assertEqual(run.platform_existing_mode("update", "c", self.SPEC_UPDATE), "update")

    def test_a_case_that_does_not_list_it_or_has_no_platform_is_refused_by_name(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            run.platform_existing_mode("update", "chess-salesforce", {"cleanup": "x"})
        self.assertIn("case 'chess-salesforce' does not list 'update' in its platform.existing", str(raised.exception))
        with self.assertRaises(SystemExit) as raised:
            run.platform_existing_mode("update", "hello", None)
        self.assertIn("case 'hello' has no platform", str(raised.exception))
        for name in ("chess-salesforce", "hello"):
            self.assertNotIn("existing", (cases()[name].get("platform") or {}))

    def test_a_resume_keeps_its_run_s_mode(self) -> None:
        self.assertEqual(run.platform_existing_mode(None, "c", self.SPEC_UPDATE, earlier="update"), "update")
        self.assertEqual(run.platform_existing_mode("update", "c", self.SPEC_UPDATE, earlier="update"), "update")
        self.assertEqual(run.platform_existing_mode(None, "c", self.SPEC_UPDATE, earlier="fresh"), "fresh")
        for asked, earlier in (("fresh", "update"), ("update", "fresh")):
            with self.subTest(asked=asked, earlier=earlier), self.assertRaises(SystemExit) as raised:
                run.platform_existing_mode(asked, "c", self.SPEC_UPDATE, earlier=earlier)
            self.assertIn(f"started in {earlier} mode, and a resume keeps its run's mode", str(raised.exception))

    def test_the_commands_are_told_the_mode_only_when_it_is_not_fresh(self) -> None:
        base = {"PATH": "/usr/bin"}
        self.assertNotIn("E2E_PLATFORM_EXISTING", run.platform_env(base, Path("/p")))
        self.assertNotIn("E2E_PLATFORM_EXISTING", run.platform_env(base, Path("/p"), "fresh"))
        env = run.platform_env(base, Path("/p"), "update")
        self.assertEqual((env["E2E_PLATFORM_EXISTING"], env["E2E_PLATFORM_DIR"], env["E2E_CHECKS"]), ("update", "/p", str(E2E / "checks")))

    def test_a_malformed_existing_list_is_refused(self) -> None:
        good = cases()[CASE]["platform"]
        self.assertEqual(run.validate_platform(CASE, good)["existing"], ["update"])
        for bad in ("update", ["fresh"], ["update", "update"], [3], ["adopt"]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform(CASE, dict(good, existing=bad))
            self.assertIn("existing must be a list of the extra modes", str(raised.exception))

    def test_the_resume_command_carries_the_flag_only_for_update(self) -> None:
        args = run.parser().parse_args(["--case", CASE, "--host", "grok", "--model", "m", "--platform-existing", "update"])
        self.assertIn("--platform-existing update", run.resume_command(Path("/o"), args))
        for mode in ("fresh", None):
            args.platform_existing = mode
            self.assertNotIn("--platform-existing", run.resume_command(Path("/o"), args))

    def test_the_new_seed_stages_are_accepted_and_a_stage_after_the_release_check_is_not(self) -> None:
        parser = run.parser()
        self.assertEqual(run.SEED_STAGES, ("step-plan", "system-test-author", "release-plan"))
        for stage in run.SEED_STAGES:
            self.assertEqual(parser.parse_args(["--seed-at", stage]).seed_at, stage)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--seed-at", "release"])

    def test_main_refuses_a_misuse_before_it_makes_a_folder_or_touches_a_platform(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            for argv, words in ((["--case", "hello", "--seed-at", "release-plan"], "seed_product"),
                                (["--prompt", "do it", "--seed-at", "release-plan"], "custom --prompt"),
                                (["--case", "hello", "--platform-existing", "update"], "has no platform"),
                                (["--case", "chess-salesforce", "--platform-existing", "update"], "does not list 'update'"),
                                (["--suite", "focused", "--platform-existing", "update"], "does not go with --suite")):
                out = Path(raw) / "never"
                with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
                    run.main([*argv, "--output", str(out)])
                self.assertIn(words, str(raised.exception))
                self.assertFalse(out.exists())


FAKE_GROK = """#!@PY@
import json, os, subprocess, sys, time
from pathlib import Path
argv = sys.argv[1:]
home = Path(os.environ["HOME"])
registry = home / ".grok" / "fake-plugins.txt"
if argv[:2] == ["plugin", "install"]:
    registry.write_text("  skill-craft-1: skill-craft [local: %s]\\n" % Path(argv[2]).resolve())
    copy = home / ".grok" / "installed-plugins" / "skill-craft-1"
    copy.mkdir(parents=True, exist_ok=True)
    if not (copy / "skills").exists():
        (copy / "skills").symlink_to(Path(os.environ["REAL_SKILLS"]))
    print("Installed 1 plugin(s)")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    print(registry.read_text() if registry.exists() else "")
    sys.exit(0)
os.chdir(argv[argv.index("--cwd") + 1])
work = Path.cwd()
out = work.parent
run_dir = out / ".shiploop-runs" / "seed" / "run"
worktree = out / ".shiploop-runs" / "seed" / "worktree"
sys.path.insert(0, os.environ["REAL_SCRIPTS"])
import shiploop_navigator as nav, shiploop_store as store
wrapper = os.environ["PATH"].split(os.pathsep)[0] + "/sf"


def say(command):
    print(json.dumps({"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {"command": command}}), flush=True)


print(json.dumps({"type": "available_commands", "tools": [], "commands": ["shiploop", "improve"]}), flush=True)
for step in json.loads(os.environ.get("SLICE_STEPS", "[]")):
    kind = step[0]
    if kind == "accept":  # what a model does by finishing a stage: ShipLoop's own navigator accepts it
        state = store.read_record(run_dir / "state.md")
        stage, action = nav.current_stage(state), str(nav.current_action(state)["id"])
        state = nav.apply(state, action, {"outcome": "done", "summary": "A fake host accepted " + stage + "."})
        if state["active_improve"] is not None:
            state = nav.finish_improve(state, action, {"summary": "A fake Improve receipt."})
        nav.save(run_dir, state, {})
    elif kind == "sf":  # a guarded sf call from the worktree, as the model's shell makes it
        say("sf " + " ".join(step[1]))
        subprocess.run([wrapper, *step[1]], cwd=worktree, capture_output=True, text=True)
    elif kind == "write":
        target = worktree / step[1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(step[2])
    elif kind == "env":  # a variable for the calls that follow (the fake org's failure switches)
        os.environ[step[1]] = step[2]
    elif kind == "sleep":
        time.sleep(step[1])
    elif kind == "return":  # the workspace return, as a fast-forward of the source branch to the run branch
        branch = subprocess.run(["git", "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(work), "-c", "user.name=fake", "-c", "user.email=fake@example.invalid", "merge", "--ff-only", branch],
                       check=True, capture_output=True, text=True)
print(json.dumps({"type": "end", "stopReason": "cancelled", "sessionId": "sess-1", "num_turns": 4, "total_cost_usd": 0.01}))
"""

DEPLOY_STEP = ["sf", ["project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", "--json"]]
ASSIGN_STEP = ["sf", ["org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", "de", "--json"]]
ACCEPT = ["accept"]
# A model that finishes the release as ShipLoop lays it out: plan, check, deploy and assign, release, verify, operations, handoff,
# then the workspace return into the source checkout.
FULL_RELEASE = [ACCEPT, ACCEPT, DEPLOY_STEP, ASSIGN_STEP, ACCEPT, ACCEPT, ACCEPT, ACCEPT, ["return"]]


class Rehearsal(unittest.TestCase):
    """The whole harness (run.main) on the real case's platform commands, guard and checks' plumbing, with a fake Grok that drives
    ShipLoop's navigator and calls the guarded `sf` of a fake org. Only the case's own checks are swapped for trivial ones."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.real_home = self.tmp / "real-home"
        self.real_home.mkdir()
        shim = self.tmp / "shim"
        shim.mkdir()
        (shim / "sf").write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(FAKE_SF))} \"$@\"\n")
        (shim / "sf").chmod(0o755)
        self.org_state, self.org_log = self.tmp / "org.json", self.tmp / "org-calls.jsonl"
        import fake_sf as fk
        self.fk = fk
        self.set_org(dict(fk.default_state(), alias="de"))
        grok = self.tmp / "grok"
        grok.write_text(FAKE_GROK.replace("@PY@", sys.executable))
        grok.chmod(0o755)
        self.grok = grok
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        (self.plugin / "skills").symlink_to(ROOT / "skills")
        auth = self.tmp / "auth.json"
        auth.write_text("{}")
        saved, hosts.GROK_AUTH = hosts.GROK_AUTH, auth
        self.addCleanup(setattr, hosts, "GROK_AUTH", saved)
        # The real case, with the checks swapped for trivial ones that keep the words the case's rules name.
        case = copy.deepcopy(cases()[CASE])
        case["checks"] = ["test -f sfdx-project.json && echo project", "echo deployed", "echo tests", "echo access", "echo rules"]
        case["platform"] = json.loads(json.dumps(case["platform"]).replace("python3", sys.executable))
        path = self.tmp / "cases.json"
        path.write_text(json.dumps({CASE: case, "hello": cases()["hello"]}))
        self.rows = self.tmp / "rows.jsonl"  # the --baseline file a seeded run must not write
        for patch in (mock.patch.object(run, "CASES", path), mock.patch.object(listeners, "observe", return_value=[]),
                      mock.patch.object(environment, "autodetect_browser", return_value=None),
                      mock.patch.dict(os.environ, {"HOME": str(self.real_home), "PATH": f"{shim}:/usr/bin:/bin",
                                                   "FAKE_SF_STATE": str(self.org_state), "FAKE_SF_LOG": str(self.org_log),
                                                   "FAKE_SF_ORGS": "de", "REAL_SKILLS": str(ROOT / "skills"),
                                                   "REAL_SCRIPTS": str(SCRIPTS)})):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(os.environ.pop, "SLICE_STEPS", None)
        self.assertIsNone(shutil.which("sf", path="/usr/bin:/bin"))

    # ---- the fake org
    def org(self) -> dict:
        return json.loads(self.org_state.read_text())

    def set_org(self, state: dict) -> None:
        self.org_state.write_text(json.dumps(state))

    def org_calls(self) -> list[dict]:
        return [json.loads(line) for line in self.org_log.read_text().splitlines()] if self.org_log.exists() else []

    def model_calls(self, verb: str) -> list[dict]:
        """The org calls the fake model made from the worktree (through the guard) that began with ``verb`` words, refused or not."""
        return [call for call in self.org_calls() if call["argv"][:len(verb.split())] == verb.split() and "worktree" in call["cwd"]]

    def sf(self, *argv: str, cwd: Path | None = None) -> None:
        done = subprocess.run(["sf", *argv, "--json"], capture_output=True, text=True, cwd=str(cwd or self.tmp))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def keep_the_app(self, assigned: bool) -> None:
        """An earlier run's kept app in the org: the reference deployed (assigned or not), on the dates of an earlier day."""
        self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=PRODUCT)
        if assigned:
            self.sf("org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", "de")
        state = self.org()
        state["dates"] = {kind: {n: d for n, d in names.items() if not n.startswith(("SLBattle", "slBattle"))}
                          for kind, names in state["dates"].items()}
        self.set_org(state)
        self.org_log.unlink(missing_ok=True)

    def baseline_again(self) -> None:
        state = self.org()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(self.fk.BASELINE_APEX), sorted(self.fk.BASELINE_LWC)))
        self.assertEqual((state["assignments"], state["tab_settings"]), ([], []))

    # ---- one harness invocation
    def invoke(self, steps: list, *extra: str, tag: str = "a") -> tuple[int, dict, str, Path]:
        os.environ["SLICE_STEPS"] = json.dumps(steps)
        out = self.tmp / f"out-{tag}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--case", CASE, "--host", "grok", "--grok-bin", str(self.grok), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.rows), "--max-resumes", "0",
                             "--seed-at", "release-plan", *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue(), out

    def test_a_fresh_release_slice_passes_deploys_in_the_release_stage_and_cleans_the_org(self) -> None:
        code, result, printed, out = self.invoke(FULL_RELEASE)
        self.assertEqual(code, 0, printed)
        self.assertTrue(result["pass"], printed)
        release = result["release_slice"]
        self.assertTrue(release["pass"], release)
        self.assertEqual([(row["stage"], row["accepted"]) for row in release["stages"]], [(name, True) for name in SIX])
        self.assertEqual([call["at"] for call in release["operation"]["calls"]], ["in"])
        self.assertEqual(release["skipped_checks"], [])  # the product was returned, so the source check ran
        self.assertEqual([c["command"] for c in result["checks"]][0], "test -f sfdx-project.json && echo project")
        self.assertTrue(all(check["pass"] for check in result["checks"]))
        self.assertIsNone(result["chain"])  # a release slice has no implementation chain to grade
        self.assertEqual(result["seeded"]["stage"], "release-plan")
        self.assertEqual(result["seeded"]["product"]["files"], len(PRODUCT_FILES))
        self.assertEqual(result["seeded"]["delegation"], "inline")
        self.assertTrue(result["committed"]["pass"], result["committed"])
        self.assertEqual(result["shiploop"]["status"], "done")
        self.assertTrue(result["platform"]["cleanup"]["ran"] and result["platform"]["cleanup"]["ok"])
        self.assertNotIn("existing", result["platform"])
        self.assertEqual([call["refused"] for call in self.model_calls("project deploy start")], [False])  # it reached the org
        self.assertEqual([call["refused"] for call in self.model_calls("org assign permset")], [False])
        removed = {row["name"] for row in json.loads((out / "platform" / "cleanup.json").read_text())["removed"]}
        self.assertGreaterEqual(removed, {"SLBattleEngine", "SLBattleController", "slBattleBoard", "SLBattle_Access", "SLBattle"})
        self.baseline_again()  # fresh: the cleanup removed what the run deployed
        self.assertFalse(self.rows.exists())  # a seeded run is not a baseline row
        self.assertIn("release   PASS  6/6 stages accepted from release-plan", printed)
        self.assertIn("deploy: 1 deploy call(s), all inside the release stage, 1 exit 0", printed)
        self.assertNotIn("existing", json.loads((out / "platform" / "before.json").read_text()))
        self.assertEqual(json.loads((out / "invocation.json").read_text())["seeded"]["product"]["commit"], result["seeded"]["product"]["commit"])

    def test_a_fresh_run_refuses_an_org_that_holds_the_kept_app_and_starts_no_model(self) -> None:
        self.keep_the_app(assigned=True)
        os.environ["SLICE_STEPS"] = json.dumps(FULL_RELEASE)
        out = self.tmp / "out-refused"
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            run.main(["--case", CASE, "--host", "grok", "--grok-bin", str(self.grok), "--output", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.rows), "--seed-at", "release-plan"])
        self.assertIn("platform preflight refused the run before any model started", str(raised.exception))
        self.assertIn("is not clean", str(raised.exception))
        self.assertFalse((out / "events.jsonl").exists())
        self.assertFalse((out / ".shiploop-runs").exists())  # not even the seed
        self.assertIn("SLBattleEngine", self.org()["apex_classes"])  # and nothing was removed

    def test_update_mode_with_keep_deploys_over_the_kept_app_and_removes_nothing(self) -> None:
        self.keep_the_app(assigned=False)
        before_classes = sorted(self.org()["apex_classes"])
        code, result, printed, out = self.invoke(FULL_RELEASE, "--platform-existing", "update", "--keep-platform")
        self.assertEqual(code, 0, printed)
        self.assertTrue(result["pass"], printed)
        self.assertEqual(result["platform"]["existing"], "update")
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["existing"], "update")
        self.assertTrue(result["platform"]["cleanup"].get("kept"))
        self.assertFalse(result["platform"]["cleanup"].get("ran"))
        snapshot = json.loads((out / "platform" / "before.json").read_text())
        self.assertEqual(snapshot["existing"], "update")  # the harness told the case's own snapshot command
        self.assertIn("PermissionSet SLBattle_Access", snapshot["baseline_prefixed"])
        state = self.org()
        self.assertEqual(sorted(state["apex_classes"]), before_classes)  # nothing removed
        self.assertEqual(len(state["assignments"]), 1)  # and the model's assignment stays
        self.assertEqual(state["dates"]["ApexClass"]["SLBattleEngine"], self.fk.DEPLOY_DATE)  # deployed over in place
        self.assertIn("update mode: items already there are the baseline", printed)
        self.assertIn("PLATFORM KEPT", printed)
        self.assertIn("--platform-existing update", printed)  # the resume command
        self.assertTrue(result["release_slice"]["pass"])

    def test_a_failed_deploy_over_the_kept_app_fails_the_run_though_every_check_finds_the_app(self) -> None:
        """The reason the verdict reads the deploy's exit: the kept app answers deployed, tests and rules by itself."""
        self.keep_the_app(assigned=True)
        steps = [ACCEPT, ACCEPT, ["env", "FAKE_SF_DEPLOY_PROBLEM", "ApexClass|SLBattleEngine|Compile error"], DEPLOY_STEP, ACCEPT, ACCEPT,
                 ACCEPT, ACCEPT, ["return"]]
        code, result, printed, out = self.invoke(steps, "--platform-existing", "update", "--keep-platform")
        self.assertEqual(code, 1)
        self.assertTrue(all(check["pass"] for check in result["checks"]), result["checks"])
        release = result["release_slice"]
        self.assertFalse(release["pass"])
        self.assertTrue(all(row["accepted"] for row in release["stages"]))  # the model finished every stage all the same
        self.assertEqual([(call["at"], call["exit"] != 0) for call in release["operation"]["calls"]], [("in", True)])
        self.assertIn("no deploy succeeded in the release stage (1 call(s): exit 1)", printed)
        self.assertTrue(result["platform"]["cleanup"].get("kept"))  # the app answers the checks, so it is kept; the run is not a pass

    def test_update_mode_without_keep_removes_only_what_the_run_added(self) -> None:
        self.keep_the_app(assigned=False)
        extra = ["write", "force-app/main/default/classes/SLBattleExtra.cls", "public class SLBattleExtra {}\n"]
        meta = ["write", "force-app/main/default/classes/SLBattleExtra.cls-meta.xml",
                (PRODUCT / "force-app/main/default/classes/SLBattleEngine.cls-meta.xml").read_text()]
        code, result, printed, out = self.invoke([ACCEPT, ACCEPT, extra, meta, DEPLOY_STEP, ASSIGN_STEP, ACCEPT, ACCEPT, ACCEPT, ACCEPT,
                                                  ["return"]], "--platform-existing", "update")
        self.assertEqual(code, 0, printed)
        cleanup = result["platform"]["cleanup"]
        self.assertTrue(cleanup["ran"] and cleanup["ok"], cleanup)
        self.assertIn("update mode: 8 baseline item(s) kept", cleanup["output"])
        state = self.org()
        self.assertNotIn("SLBattleExtra", state["apex_classes"])  # what the run added went
        self.assertEqual(sorted(n for n in state["apex_classes"] if n.startswith("SLBattle")),
                         ["SLBattleController", "SLBattleEngine", "SLBattleEngineTest", "SLBattleGameTest"])
        self.assertIn("SLBattle_Access", state["types"]["PermissionSet"])
        self.assertEqual(state["assignments"], [])  # the run's assignment went, the permission set stayed
        record = json.loads((out / "platform" / "cleanup.json").read_text())
        self.assertEqual([r["name"] for r in record["removed"]], ["SLBattleExtra"])
        self.assertTrue(result["pass"], printed)

    def test_a_run_that_stops_after_the_plan_says_where_and_why_leaves_the_source_check_out_and_cleans(self) -> None:
        code, result, printed, out = self.invoke([ACCEPT])
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"])
        release = result["release_slice"]
        self.assertFalse(release["pass"])
        self.assertEqual([row["accepted"] for row in release["stages"]], [True, False, False, False, False, False])
        self.assertEqual(release["stopped"]["stage"], "release-check")
        self.assertEqual(release["stopped"]["engine_status"], "active")
        self.assertIn("ShipLoop was active at release-check, so release-check was not accepted", release["stopped"]["reason"])
        self.assertEqual(release["operation"]["calls"], [])
        self.assertFalse(release["operation"]["pass"])
        # The product never reached the source checkout, so the check that reads it is left out, not failed.
        self.assertEqual([item["command"] for item in release["skipped_checks"]], ["test -f sfdx-project.json && echo project"])
        self.assertEqual(len(result["checks"]), 4)
        self.assertTrue(all(check["pass"] for check in result["checks"]))
        self.assertTrue(result["platform"]["cleanup"]["ok"])
        self.baseline_again()
        self.assertIn("stopped at release-check: ShipLoop was active at release-check", printed)
        self.assertIn("release_slice", (out / "mismatch.md").read_text())

    def test_a_deploy_before_release_check_was_accepted_fails_the_run_even_though_ShipLoop_finished(self) -> None:
        steps = [ACCEPT, DEPLOY_STEP, ["sleep", 1.2], ACCEPT, ASSIGN_STEP, ACCEPT, ACCEPT, ACCEPT, ACCEPT, ["return"]]
        code, result, printed, out = self.invoke(steps)
        self.assertEqual(code, 1)
        self.assertEqual(result["shiploop"]["status"], "done")
        release = result["release_slice"]
        self.assertFalse(release["pass"])
        self.assertIsNone(release["stopped"])  # every stage was accepted: only the deploy came too early
        self.assertEqual([call["at"] for call in release["operation"]["calls"]], ["before"])
        self.assertIn("deploy outside the release stage: 1 before release-check was accepted", printed)
        self.assertTrue(all(row["accepted"] for row in release["stages"]))
        self.assertIn("release_slice", (out / "mismatch.md").read_text())
        self.baseline_again()

    def test_a_resume_keeps_the_mode_and_refuses_the_other(self) -> None:
        self.keep_the_app(assigned=False)
        code, result, printed, out = self.invoke([ACCEPT], "--platform-existing", "update")
        self.assertEqual(code, 1)
        self.assertIn("--platform-existing update", printed)  # the resume line names the mode
        self.assertTrue(result["platform"]["cleanup"]["ok"])
        self.assertIn("SLBattleEngine", self.org()["apex_classes"])  # the baseline stayed
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
        for flag, words in (("fresh", "started in update mode, and a resume keeps its run's mode"),):
            with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.object(run, "released_versions", return_value=released):
                run.main(["--host", "grok", "--grok-bin", str(self.grok), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                          "--baseline", str(self.rows), "--max-resumes", "0", "--platform-existing", flag])
            self.assertIn(words, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
