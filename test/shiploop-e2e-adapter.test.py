#!/usr/bin/env python3
"""Hermetic tests of the ShipLoop adapter's facade (test/shiploop_e2e/adapter/facade.py). No model is called.

Plan: docs/closed-loop-phase2-plan-2026-11-15.md (version 3), gate G1. The tests build a throwaway source repository from the live
harness files (so a harness change that breaks the facade's contract fails here), clone it the way `facade.py setup` does, and drive
the facade's commands as closed_loop.py would: as a subprocess with CLOSED_LOOP_WORKSPACE and CLOSED_LOOP_CAMPAIGN set.

Run: python3 -B test/shiploop-e2e-adapter.test.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
FACADE = HARNESS / "adapter" / "facade.py"
sys.path.insert(0, str(HARNESS))
import learning_records  # noqa: E402  (the live harness: ledger rows in the tests are written by the real appender)

spec = importlib.util.spec_from_file_location("shiploop_facade", FACADE)
facade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facade)

# What a test copy of the harness leaves out at its top level: the logs, documents and data the facade never reads (every top-level
# .md, .jsonl and .html file except SPEC.md, which is inside the qualification snapshot), and the adapter itself. The suites do not read
# these files' real content, so none is named here: a file name in a suite's source makes the catalog list the suite as its reader.
KEEP = ("SPEC.md",)
SKIP_FOLDERS = ("adapter", "evidence")


def harness_ignore(directory, names):
    top = Path(directory) == HARNESS
    return [name for name in names if name == "__pycache__"
            or (top and (name in SKIP_FOLDERS or (name.endswith((".md", ".jsonl", ".html")) and name not in KEEP)))]
CONFIG = ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", str(repo), *CONFIG, *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {done.stderr}")
    return done.stdout.strip()


def commit_all(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def ledger_row(path, event, record, **fields):
    return learning_records.append(event, record, Path(path), **fields)


def opened(path, record, title, *, materiality="material", target="shiploop", case=None, exposure=None, confidence="high"):
    source = {"finding_id": "F1", "route": "implementation"}
    if case:
        source["case"] = case
    if exposure:
        source["exposure"] = exposure
    ledger_row(path, "opened", record, title=title, materiality=materiality, confidence=confidence, target=target, source=source)


def build_ledger(path):
    """One record per interesting folded status; ids are fixed so the tests can name them."""
    path.write_text("")
    opened(path, "LR-20261101-000001", "admitted on csv-report", case="csv-report")
    ledger_row(path, "admitted", "LR-20261101-000001", reason="supported")
    opened(path, "LR-20261101-000002", "owner held, no case")
    ledger_row(path, "owner", "LR-20261101-000002", reason="a material challenge")
    opened(path, "LR-20261101-000003", "deferred", case="hello")
    ledger_row(path, "deferred", "LR-20261101-000003", reason="not now", reopen_when="it recurs")
    opened(path, "LR-20261101-000004", "verified", case="hello")
    ledger_row(path, "admitted", "LR-20261101-000004", reason="supported")
    ledger_row(path, "verdict", "LR-20261101-000004", verdict="supported", outcome="verified", reason="epoch E promoted it")
    opened(path, "LR-20261101-000005", "a harness finding", target="harness")
    ledger_row(path, "deferred", "LR-20261101-000005", reason="evaluator experiment", reopen_when="registered")
    opened(path, "LR-20261101-000006", "minor", materiality="minor", case="hello")
    opened(path, "LR-20261101-000007", "admitted on battleship", case="battleship")
    ledger_row(path, "admitted", "LR-20261101-000007", reason="supported")
    opened(path, "LR-20261101-000008", "admitted as a confirmation case", case="csv-report", exposure="confirmation")
    ledger_row(path, "admitted", "LR-20261101-000008", reason="supported")
    opened(path, "LR-20261101-000009", "refuted", case="hello")
    ledger_row(path, "admitted", "LR-20261101-000009", reason="supported")
    ledger_row(path, "verdict", "LR-20261101-000009", verdict="contradicted", outcome="refuted", reason="the epoch refuted it")
    opened(path, "LR-20261101-000010", "open, never admitted")
    opened(path, "LR-20261101-000011", "rejected by the owner", case="hello")
    ledger_row(path, "owner", "LR-20261101-000011", outcome="reject", reason="not a defect")


def build_source(folder: Path, version="2.42.1"):
    """A throwaway repository holding a copy of the live harness (minus its heavy data), a skill, a candidate test file and a ledger."""
    src = folder / "src"
    src.mkdir()
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "gc.auto", "0")  # a background repack racing the first clone is the load flake of 2026-11-01
    git(src, "config", "maintenance.auto", "false")
    shutil.copytree(HARNESS, src / "test" / "shiploop_e2e", ignore=harness_ignore)
    # The harness imports ShipLoop's own scripts (shiploop_store, ...) by a repository-relative path, so the copy carries them.
    shutil.copytree(ROOT / "skills" / "shiploop" / "scripts", src / "skills" / "shiploop" / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (src / "skills" / "shiploop" / "SKILL.md").write_text("---\nname: shiploop\n---\nversion one\n")
    (src / "changes" / "shiploop").mkdir(parents=True)
    (src / "changes" / "shiploop" / ".keep").write_text("")
    (src / "test" / "shiploop-fake.test.py").write_text("print('a candidate test: its prefix is a filename pattern')\n")
    (src / "catalog").mkdir()
    (src / "catalog" / "skill-craft-plugin.json").write_text(json.dumps({"version": version}))
    (src / ".gitignore").write_text(".claude/worktrees/\n")
    build_ledger(src / "test" / "shiploop_e2e" / "learning-records.jsonl")
    (src / facade.BASELINES_REL).write_text("")
    return src, commit_all(src, "base")


def run_facade(*args, x=None, campaign=None, check=True):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
    if x is not None:
        env["CLOSED_LOOP_WORKSPACE"] = str(x)
    if campaign is not None:
        env["CLOSED_LOOP_CAMPAIGN"] = str(campaign)
    done = subprocess.run([sys.executable, "-B", str(FACADE), *args], capture_output=True, text=True, env=env, check=False)
    if check and done.returncode != 0:
        raise AssertionError(f"facade {' '.join(args)} exited {done.returncode}: {done.stderr}")
    return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else done


# One source repository and one shared evaluator clone for the whole module: building them is most of the run time.
STATE = {}


def setUpModule():
    STATE["folder"] = Path(tempfile.mkdtemp(prefix="shiploop-adapter-test-")).resolve()  # the facade resolves paths: so do the tests
    STATE["src"], STATE["base"] = build_source(STATE["folder"])
    STATE["shared_x"] = STATE["folder"] / "x-shared"
    STATE["setup_result"] = run_facade("setup", "--workspace", str(STATE["shared_x"]), "--base", STATE["base"],
                                       "--source", str(STATE["src"]))


def tearDownModule():
    shutil.rmtree(STATE["folder"], ignore_errors=True)


class Fixture(unittest.TestCase):
    """The shared clone serves the read-only tests; a test that changes X asks for its own."""

    folder = property(lambda self: STATE["folder"])
    src = property(lambda self: STATE["src"])
    base = property(lambda self: STATE["base"])
    shared_x = property(lambda self: STATE["shared_x"])
    setup_result = property(lambda self: STATE["setup_result"])

    def setUp(self):
        self.x = self.shared_x
        self.layout = facade.Layout(self.x)

    def use_fresh_x(self):
        """For a test that moves X's HEAD, writes its files or moves the tip ref."""
        self.x = self.folder / f"x-{self.id().rsplit('.', 1)[-1]}"
        run_facade("setup", "--workspace", str(self.x), "--base", self.base, "--source", str(self.src))
        self.layout = facade.Layout(self.x)

    def campaign_with_scope(self, cases):
        folder = self.folder / f"campaign-{self.id().rsplit('.', 1)[-1]}"
        folder.mkdir(exist_ok=True)
        (folder / "campaign.json").write_text(json.dumps({"scope": "S0", "scopes": [{"id": "S0", "cases": cases}]}))
        return folder

    def x_snapshot(self):
        """Everything a query must leave alone: X's HEAD and status, and the state folder's file list with sizes."""
        files = sorted((str(p.relative_to(self.layout.state)), p.stat().st_size) for p in self.layout.state.rglob("*")
                       if p.is_file() and p.suffix != ".lock")  # a lock file is coordination, not state: an operation that only reads may create one
        return git(self.x, "rev-parse", "HEAD"), git(self.x, "status", "--porcelain", "--untracked-files=all"), files


class SetupTests(Fixture):
    def test_setup_clones_x_detached_at_the_base_and_keeps_its_state_beside_it(self):
        self.assertEqual(git(self.x, "rev-parse", "HEAD"), self.base)
        self.assertEqual(git(self.x, "rev-parse", "--abbrev-ref", "HEAD"), "HEAD")  # detached
        self.assertEqual(git(self.x, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertTrue(self.layout.chain_file.is_file())
        self.assertEqual(self.layout.state, self.x.parent / (self.x.name + ".facade"))
        self.assertFalse((self.x / ".facade").exists(), "no facade file lives inside X")
        self.assertEqual(self.setup_result["base"], self.base)
        self.assertEqual(facade.published_tip(self.layout), self.base)
        self.assertEqual(git(self.x, "for-each-ref", "refs/shiploop-loop"), "", "no other session's loop ref comes along")

    def test_setup_never_reuses_a_folder_and_needs_a_released_base(self):
        again = run_facade("setup", "--workspace", str(self.x), "--base", self.base, "--source", str(self.src), check=False)
        self.assertEqual(again.returncode, 2)
        self.assertIn("not empty", again.stderr)
        (self.folder / "old").mkdir(exist_ok=True)
        old_src, old_base = build_source(self.folder / "old", version="2.41.1")
        refused = run_facade("setup", "--workspace", str(self.folder / "x-old"), "--base", old_base, "--source", str(old_src), check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("minimum is 2.42.0", refused.stderr)
        self.assertFalse((self.folder / "x-old").exists(), "a refused base creates nothing")

    def test_an_unset_up_workspace_is_refused_by_every_query(self):
        stray = self.folder / "stray"
        stray.mkdir()
        refused = run_facade("identity", x=stray, check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("setup", refused.stderr)


class CasesTests(Fixture):
    def test_cases_lists_the_allowlist_with_style_and_cost_from_the_base_commit(self):
        cases = {case["id"]: case for case in run_facade("cases", x=self.x)["cases"]}
        self.assertEqual(sorted(cases), ["battleship", "csv-report", "hello", "seat-reservations"])
        self.assertEqual(cases["hello"]["dimensions"], {"style": "smoke"})
        self.assertEqual(cases["csv-report"]["dimensions"], {"style": "cli-files"})
        self.assertEqual({name: case["requires"] for name, case in cases.items()},
                         {"battleship": ["browser"], "csv-report": [], "hello": [], "seat-reservations": []},
                         "the harness catalog's `needs` is the case's authority requirement, and the manifest makes a browser case owner-only")
        self.assertTrue(all(case["hosted"] is False for case in cases.values()))
        self.assertLess(cases["hello"]["cost"], cases["csv-report"]["cost"])

    def test_the_orchestrator_gates_the_browser_case_and_releases_the_others(self):
        """The real orchestrator, with the real manifest's authority block and the facade's catalog: `init --cases battleship` is refused until
        the owner approves the case, and `hello` is not."""
        manifest = json.loads((HARNESS / "adapter" / "adapter.json").read_text())
        manifest["execution"]["pin"] = [str(FACADE), str(HARNESS / "adapter" / "allowlist.json")]
        manifest["execution"]["cwd"] = str(self.folder)
        for name in ("cases", "records", "identity", "step", "probe"):
            manifest["commands"][name][1] = str(FACADE)
        manifest["execution"]["cleanup"][1] = str(FACADE)
        path = self.folder / "gate-adapter.json"
        path.write_text(json.dumps(manifest))
        orchestrator = ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py"

        def init(cases, extra=()):
            return subprocess.run([sys.executable, "-B", str(orchestrator), "init", "--manifest", str(path), "--campaign",
                                   str(self.folder / f"campaign-{cases}-{len(extra)}"), "--workspace", str(self.x), "--cases", cases,
                                   "--budget", "seconds=60,runs=1", *extra], capture_output=True, text=True, check=False,
                                  env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")})
        refused = init("battleship")
        self.assertNotEqual(refused.returncode, 0, refused.stdout)
        self.assertIn("owner", (refused.stdout + refused.stderr).lower())
        self.assertEqual(init("battleship", ("--approve-case", "battleship", "--yes-owner-approved")).returncode, 0)
        self.assertEqual(init("hello").returncode, 0)

    def test_a_case_the_catalog_lacks_or_restyles_is_refused(self):
        listed = json.loads(facade.ALLOWLIST.read_text())
        for label, change in (("missing", {"nope": {"style": "smoke", "cost": 1}}),
                              ("restyled", {"hello": {"style": "cli-files", "cost": 1}})):
            with self.subTest(label):
                custom = self.folder / f"allowlist-{label}.json"
                custom.write_text(json.dumps({"cases": {**listed["cases"], **change}}))
                original = facade.ALLOWLIST
                facade.ALLOWLIST = custom
                try:
                    with self.assertRaises(facade.FacadeError):
                        facade.load_allowlist(self.layout)
                finally:
                    facade.ALLOWLIST = original

    def test_a_negative_cost_is_refused(self):
        custom = self.folder / "allowlist-cost.json"
        custom.write_text(json.dumps({"cases": {"hello": {"style": "smoke", "cost": -1}}}))
        original = facade.ALLOWLIST
        facade.ALLOWLIST = custom
        try:
            with self.assertRaises(facade.FacadeError):
                facade.load_allowlist(self.layout)
        finally:
            facade.ALLOWLIST = original


class IdentityTests(Fixture):
    def test_scoring_is_the_harness_snapshot_and_the_adapter_files_do_not_change_it(self):
        import boundary
        live = boundary.qualification_snapshot(HARNESS, None)["sha256"]  # the live harness, with its adapter/ folder
        self.assertTrue((HARNESS / "adapter" / "facade.py").is_file())
        self.assertEqual(run_facade("identity", x=self.x)["scoring"], live)

    def test_the_build_token_moves_only_with_a_candidate_edit(self):
        self.use_fresh_x()
        before = run_facade("identity", x=self.x)["build"]
        self.assertTrue(before.startswith("b-"))
        # A learning commit (the ledger and the loop's journal, whose path is the harness's own constant) and a harness edit are not the candidate.
        import cycle
        (self.x / cycle.JOURNAL).write_text("# a learning\n")
        (self.x / "test" / "shiploop_e2e" / "cycle.py").write_text((self.x / "test" / "shiploop_e2e" / "cycle.py").read_text() + "\n# harness\n")
        learned = commit_all(self.x, "learning and a harness edit")
        git(self.x, "update-ref", facade.TIP_REF, learned)
        self.assertEqual(run_facade("identity", x=self.x)["build"], before)
        # The skill, its change notes and a filename-pattern test (`test/shiploop-`) are the candidate.
        for path in ("skills/shiploop/SKILL.md", "test/shiploop-fake.test.py", "changes/shiploop/note.md"):
            with self.subTest(path):
                target = self.x / path
                target.write_text(target.read_text() + "x\n" if target.exists() else "a note\n")
                moved = commit_all(self.x, f"candidate edit {path}")
                git(self.x, "update-ref", facade.TIP_REF, moved)
                after = run_facade("identity", x=self.x)["build"]
                self.assertNotEqual(after, before)
                before = after

    def test_queries_read_the_published_tip_not_the_checked_out_head(self):
        self.use_fresh_x()
        base_build = run_facade("identity", x=self.x)["build"]
        (self.x / "skills" / "shiploop" / "SKILL.md").write_text("version two\n")
        moved = commit_all(self.x, "a candidate")
        self.assertEqual(run_facade("identity", x=self.x)["build"], base_build, "HEAD moved; the tip ref did not")
        git(self.x, "update-ref", facade.TIP_REF, moved)
        self.assertNotEqual(run_facade("identity", x=self.x)["build"], base_build)

    def test_a_filename_pattern_prefix_is_judged_by_the_harness_predicate(self):
        entries = facade.tree_entries(self.layout, self.base)
        paths = [path for _, _, path in entries]
        chosen = set(facade.bridge(self.layout, "candidate_paths", {"paths": paths})["candidate"])
        self.assertIn("test/shiploop-fake.test.py", chosen)
        self.assertIn("skills/shiploop/SKILL.md", chosen)
        self.assertNotIn("test/shiploop_e2e/cycle.py", chosen)


class RecordsTests(Fixture):
    def records(self, scope):
        campaign = self.campaign_with_scope(scope)
        return {rec["id"]: rec for rec in run_facade("records", x=self.x, campaign=campaign)["records"]}

    def test_every_engine_status_maps_to_one_orchestrator_status(self):
        got = self.records(["hello", "csv-report"])
        expect = {"LR-20261101-000001": ("admitted", True, "subject"),      # admitted, found on a scope case
                  "LR-20261101-000002": ("owner", True, "subject"),         # owner held
                  "LR-20261101-000003": ("deferred", True, "subject"),
                  "LR-20261101-000004": ("verified", True, "subject"),
                  "LR-20261101-000005": ("deferred", True, "adapter"),      # a harness finding never blocks a subject certificate
                  "LR-20261101-000006": ("owner", False, "subject"),        # minor: open, so it waits and is not material
                  "LR-20261101-000007": ("owner", True, "subject"),         # admitted, but only found on battleship: not offerable here
                  "LR-20261101-000008": ("owner", True, "subject"),         # a confirmation case is never offered to a cycle
                  "LR-20261101-000009": ("refuted", True, "subject"),
                  "LR-20261101-000010": ("owner", True, "subject"),         # opened and never admitted: only a judge or the owner moves it
                  "LR-20261101-000011": ("rejected", True, "subject")}
        self.assertEqual({rid: (rec["status"], rec["material"], rec["target"]) for rid, rec in got.items()}, expect)

    def test_a_resolved_status_carries_its_evidence_and_a_deferred_one_its_reopening_condition(self):
        got = self.records(["hello"])
        self.assertEqual(got["LR-20261101-000004"]["evidence"], "epoch E promoted it")
        self.assertEqual(got["LR-20261101-000009"]["evidence"], "the epoch refuted it")
        self.assertEqual(got["LR-20261101-000003"]["reopen_when"], "it recurs")
        self.assertEqual(got["LR-20261101-000003"]["cases"], ["hello"])

    def test_admitted_is_actionable_only_for_a_record_the_current_scope_can_reach(self):
        self.assertEqual(self.records(["csv-report"])["LR-20261101-000001"]["status"], "admitted")
        self.assertEqual(self.records(["hello"])["LR-20261101-000001"]["status"], "owner", "found on csv-report, not in this scope")
        self.assertEqual(self.records([])["LR-20261101-000001"]["status"], "owner", "no scope yet: nothing is offerable")
        self.assertEqual(self.records(["battleship"])["LR-20261101-000007"]["status"], "admitted")

    def test_a_caseless_admitted_record_is_offerable_to_any_exposing_case(self):
        self.use_fresh_x()
        ledger = self.layout.x / "test" / "shiploop_e2e" / "learning-records.jsonl"
        opened(ledger, "LR-20261101-000012", "a seeded record, no case")
        ledger_row(ledger, "admitted", "LR-20261101-000012", reason="supported")
        moved = commit_all(self.x, "a seeded record")
        git(self.x, "update-ref", facade.TIP_REF, moved)
        self.assertEqual(self.records(["hello"])["LR-20261101-000012"]["status"], "admitted")
        self.assertEqual(self.records(["hello"])["LR-20261101-000012"]["cases"], [])

    def test_records_read_the_ledger_at_the_published_tip_without_a_checkout(self):
        self.use_fresh_x()
        ledger = self.x / "test" / "shiploop_e2e" / "learning-records.jsonl"
        opened(ledger, "LR-20261101-000013", "found by a step")
        moved = commit_all(self.x, "a learning commit")
        before = self.records(["hello"])
        self.assertNotIn("LR-20261101-000013", before, "HEAD has it, the published tip does not")
        git(self.x, "update-ref", facade.TIP_REF, moved)
        self.assertIn("LR-20261101-000013", self.records(["hello"]))

    def test_the_orchestrator_reads_the_record_shape_it_validates(self):
        for rec in self.records(["hello"]).values():
            self.assertIsInstance(rec["id"], str)
            self.assertIsInstance(rec["status"], str)
            self.assertIsInstance(rec["material"], bool)
            self.assertIn(rec["target"], ("subject", "adapter"))
            self.assertIsInstance(rec["cases"], list)

    def test_the_material_words_are_the_harness_own(self):
        self.assertEqual(tuple(facade.fold_ledger(self.layout, self.base)["material_words"]), facade.MATERIAL_WORDS)
        self.assertEqual(learning_records.MATERIAL, facade.MATERIAL_WORDS)

    def test_the_mapping_agrees_with_the_harness_selection_rule(self):
        """On a ledger holding one record, the facade calls an admitted record actionable exactly when the harness's own select()
        offers it to some exposing case of the scope."""
        full = learning_records.rows(self.x / "test" / "shiploop_e2e" / "learning-records.jsonl")
        for scope in (["csv-report"], ["hello"], ["battleship"], ["hello", "csv-report"]):
            got = self.records(scope)
            for rid, rec in got.items():
                if rec["engine_status"] != "admitted":
                    continue
                alone = self.folder / f"alone-{rid}.jsonl"
                alone.write_text("".join(json.dumps(row) + "\n" for row in full if row["record"] == rid))
                offered = any(learning_records.select(alone, case, None) == rid for case in scope)
                self.assertEqual(rec["status"] == "admitted", offered, (scope, rid, rec["status"]))


class BacklogAndDecisionTests(Fixture):
    """The owner's decisions: `backlog` lists what waits, `decide` writes the decision into the ledger at the published tip (plan appendix A)."""

    UNRESOLVED = frozenset({"LR-20261101-000001", "LR-20261101-000002", "LR-20261101-000003", "LR-20261101-000007", "LR-20261101-000008",
                            "LR-20261101-000010"})

    def test_backlog_is_the_material_unresolved_subject_records(self):
        found = run_facade("backlog", x=self.x)
        self.assertEqual({item["id"] for item in found["records"]}, self.UNRESOLVED)
        self.assertEqual(found["count"], 6)
        self.assertEqual(len(found["markdown"].splitlines()), 2 + 6, "a header, a rule and one row each")
        by_id = {item["id"]: item for item in found["records"]}
        self.assertEqual(by_id["LR-20261101-000002"]["options"], "accept (it becomes admitted) | reject | defer")
        self.assertEqual(by_id["LR-20261101-000003"]["reopen_when"], "it recurs")
        for gone in ("LR-20261101-000004", "LR-20261101-000005", "LR-20261101-000006", "LR-20261101-000009", "LR-20261101-000011"):
            self.assertNotIn(gone, by_id, "a verified, harness, minor, refuted or rejected record is not the owner's to decide")

    def decide(self, record, outcome, reason="the owner's words", *more, check=True):
        return run_facade("decide", "--record", record, "--outcome", outcome, "--reason", reason, *more, x=self.x, check=check)

    def test_an_accept_reaches_the_ledger_at_the_tip_and_leaves_the_checkout_alone(self):
        self.use_fresh_x()
        before = self.x_snapshot()
        done = self.decide("LR-20261101-000002", "accept", "Accepted: a real defect the next cycle may fix")
        self.assertEqual(done["event"], "owner")
        self.assertEqual(git(self.x, "rev-parse", facade.TIP_REF), done["tip"])
        self.assertEqual(git(self.x, "rev-parse", f"{done['tip']}^"), self.base, "one commit on top of the tip it replaced")
        self.assertEqual((git(self.x, "rev-parse", "HEAD"), git(self.x, "status", "--porcelain", "--untracked-files=all")), before[:2],
                         "the commit is built from Git objects: no checkout, no index, no working file")
        rows = [json.loads(line) for line in git(self.x, "show", f"{done['tip']}:{facade.LEDGER_REL}").splitlines()]
        self.assertEqual((rows[-1]["event"], rows[-1]["outcome"]), ("owner", "accept"))
        self.assertEqual(rows[-1]["owner_decision"], "Accepted: a real defect the next cycle may fix")
        by_id = {item["id"]: item for item in run_facade("records", x=self.x)["records"]}
        self.assertEqual(by_id["LR-20261101-000002"]["status"], "admitted", "an accepted record with no case can be offered to any scope")
        self.assertEqual(learning_records.select(self.tip_ledger(done["tip"]), "hello", None), "LR-20261101-000002")
        listed = {item["id"]: item for item in run_facade("backlog", x=self.x)["records"]}
        self.assertEqual((listed["LR-20261101-000002"]["engine_status"], listed["LR-20261101-000002"]["options"]),
                         ("admitted", "none needed: it waits for an exposing case in a scope"))

    def tip_ledger(self, rev):
        path = self.folder / f"ledger-{rev[:8]}.jsonl"
        path.write_text(git(self.x, "show", f"{rev}:{facade.LEDGER_REL}") + "\n")
        return path

    def test_a_reject_is_resolved_with_the_owners_words_as_its_evidence(self):
        self.use_fresh_x()
        self.decide("LR-20261101-000010", "reject", "Not a defect: the behaviour is intended")
        by_id = {item["id"]: item for item in run_facade("records", x=self.x)["records"]}
        self.assertEqual((by_id["LR-20261101-000010"]["status"], by_id["LR-20261101-000010"]["evidence"]),
                         ("rejected", "Not a defect: the behaviour is intended"))
        self.assertNotIn("LR-20261101-000010", {item["id"] for item in run_facade("backlog", x=self.x)["records"]})

    def test_a_deferral_needs_the_condition_that_brings_the_record_back(self):
        self.use_fresh_x()
        refused = self.decide("LR-20261101-000010", "defer", check=False)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("--reopen-when", refused.stderr)
        self.decide("LR-20261101-000010", "defer", "later", "--reopen-when", "a cycle can run on csv-report")
        by_id = {item["id"]: item for item in run_facade("records", x=self.x)["records"]}
        self.assertEqual(by_id["LR-20261101-000010"]["status"], "deferred")
        self.assertEqual(by_id["LR-20261101-000010"]["reopen_when"], "a cycle can run on csv-report")

    def test_decisions_that_cannot_be_recorded_are_refused_and_change_nothing(self):
        self.use_fresh_x()
        before = self.x_snapshot()
        for args, text in ((("LR-20991231-ffffff", "accept"), "is not a record"), (("LR-20261101-000002", "accept", " "), "owner's words")):
            with self.subTest(args=args):
                refused = self.decide(*args, check=False)
                self.assertEqual(refused.returncode, 2)
                self.assertIn(text, refused.stderr)
        self.assertEqual(self.x_snapshot(), before)
        self.assertEqual(facade.published_tip(self.layout), self.base)


class ManifestTests(unittest.TestCase):
    """The manifest the owner ratifies: the orchestrator accepts it, it pins the facade and its allowlist, and every argument list it holds
    parses with the facade's own command line."""

    MANIFEST = HARNESS / "adapter" / "adapter.json"

    def test_the_orchestrator_accepts_the_manifest(self):
        done = subprocess.run([sys.executable, "-B", str(ROOT / "skills" / "closed-loop" / "scripts" / "closed_loop.py"), "adapter-check",
                               "--manifest", str(self.MANIFEST)], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(json.loads(done.stdout)["ok"])

    def test_the_facade_and_its_allowlist_are_pinned_and_nothing_else_is_executed(self):
        manifest = json.loads(self.MANIFEST.read_text())
        self.assertEqual(manifest["execution"]["pin"], ["facade.py", "allowlist.json"])
        for name in manifest["execution"]["pin"]:
            self.assertTrue((self.MANIFEST.parent / name).is_file(), name)
        argv_lists = [*manifest["commands"].values(), manifest["execution"]["cleanup"]]
        self.assertTrue(all(argv[:2] == ["python3", "facade.py"] for argv in argv_lists), "every command is the one pinned program")

    def test_every_argument_list_parses_with_the_facades_command_line(self):
        manifest = json.loads(self.MANIFEST.read_text())
        parser = facade.build_parser()
        commands = manifest["commands"]
        step = commands["step"][2:]
        for tail in (["start", "--key", "k", "--scope", "s", "--cases", "hello", "--mode", "iterate", "--base", "b", "--out", "o"],
                     ["poll", "--handle", "k"], ["cancel", "--handle", "k"]):
            self.assertEqual(parser.parse_args(step + tail).verb, "step")
        for claim in manifest["claims"]:
            self.assertEqual(parser.parse_args(commands["probe"][2:] + [claim]).verb, "probe")
        for verb in ("cases", "records", "identity"):
            self.assertEqual(parser.parse_args(commands[verb][2:]).verb, verb)
        self.assertEqual(parser.parse_args(manifest["execution"]["cleanup"][2:] + ["--keys", "a,b"]).verb, "cleanup")
        profile = parser.parse_args(step + ["poll", "--handle", "k"])
        self.assertEqual((profile.host, profile.model, profile.effort, profile.tolerance, profile.attempts, profile.parallel),
                         ("codex", "gpt-6.1-terra", "high", 0.45, 3, 2))

    def test_the_claims_are_the_ones_the_facade_can_prove_and_the_start_rule_needs(self):
        claims = json.loads(self.MANIFEST.read_text())["claims"]
        kinds = {claim.split(":")[0] for claim in claims}
        self.assertTrue({"cases.runs", "grading.scores", "improver.bounded"} <= kinds, "the start rule needs these three")
        self.assertEqual(claims["cases.runs:hello"]["effect"], "effectful")
        self.assertEqual(claims["grading.scores"]["effect"], "read-only")
        self.assertNotIn("grading.sensitive", " ".join(claims), "no whole-run measure has been shown to separate known-bad from known-good")


class QueryTests(Fixture):
    def test_queries_write_nothing_and_move_nothing(self):
        campaign = self.campaign_with_scope(["hello"])
        before = self.x_snapshot()
        for verb in ("cases", "records", "identity"):
            run_facade(verb, x=self.x, campaign=campaign)
        self.assertEqual(self.x_snapshot(), before)
        self.assertEqual(list(campaign.iterdir()), [campaign / "campaign.json"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
