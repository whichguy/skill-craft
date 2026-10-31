#!/usr/bin/env python3
"""The stage suite's scenarios and builder (test/shiploop_e2e/stage_suite/stage_build.py; docs/plans/shiploop-stage-suite.md), no model.

Small scenario sets in temporary folders, on the node-base fixture (plain files); every check that runs code is ``grep``, ``test``
or a ``python3 -c``, so the suite needs no other runtime. The runs it builds are real ShipLoop runs (about a second each).

- Schema: a good scenario validates, and each distinct kind of malformed one is reported by its own sentence, several at once.
  ``discover`` sorts by stage order (an Improve stage last) and name, and raises one ScenarioError that lists every problem of
  every scenario; ``load`` takes ``<stage>/<name>``.
- Trees: ``compose_seed_tree`` lays the fixture, then ``repo/``, then ``worktree/``; a reference output is the seed tree with its
  ``tree/`` laid over it and the paths of ``deleted.txt`` removed, and the oracle passes the good one and fails each bad one.
- Builds, through the engine's seam (``navigator.accept_effects``):
  - validate-existing with one planted failing expectation: the packet names the expectation and its mismatch, which the harness's
    own seed cannot give (test/shiploop-seed-seam.test.py pins the contrast), and the stage is issued;
  - validate-existing with every expectation matching (the fault repaired by ``repo/``): the engine settles the stage by script, no
    packet is issued, and the run stands at implement;
  - document: ``worktree/`` was laid before implement was recorded, so the stage has a change to document and an iteration record;
  - carry-forward: the step was committed by the seed's effects; ``options.delegation`` reaches the run.
- A ``worktree/`` is refused for a stage at or before validate-existing (the checks run on entry come before the seed point).
- Safety: ``run.SEED_SCRIPT`` is the harness's own again after a build, also when the build raises and when threads build at
  once (the substitution holds a lock); the seed child does not import from the working directory; a render whose packet file
  is missing says so; a build writes only below its ``out`` folder; a build leaves the evaluator digest where it was; improve@ and outer-stage scenarios load and validate but do not
  build.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(HARNESS / "stage_suite"))
sys.path.insert(0, str(HARNESS))
import boundary  # noqa: E402
import run  # noqa: E402
import stage_build as sb  # noqa: E402
import stage_oracle  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GONE = object()  # a key to remove from a scenario

# The scenario every malformed one is a mutation of: it plants P1 (a fault in src/strings.js that the stage must repair) and
# the control C1 (src/paginate.js is left alone), proves each in its oracle, and holds a good output and a bad one per id.
GOOD = {
    "stage": "validate-existing", "about": "A works expectation is broken on the base by a small fault.",
    "tags": ["catch", "prep-fix"], "fixture": "node-base", "request_from": "node-fix-bug",
    "options": {"delegation": "inline"},
    "planted": [{"id": "P1", "what": "src/strings.js lacks the repair", "signature": "PLANTED-E1"}],
    "controls": [{"id": "C1", "what": "src/paginate.js is left alone"}],
    "render": [{"proves": "P1", "packet_contains": "DOES NOT MATCH"}],
    "oracle": [{"proves": "P1", "outcome": ["done"]},
               {"proves": "P1", "file": "src/strings.js", "contains": "REPAIRED"},
               {"proves": "C1", "file": "src/paginate.js", "unchanged": True}],
    "live": {"samples": 3, "pass": "all"}}
GOOD_FILES = {
    "reference/good/result.json": json.dumps({"outcome": "done", "summary": "Repaired."}),
    "reference/good/tree/src/strings.js": "// REPAIRED\nmodule.exports = {};\n",
    "reference/bad-unrepaired/result.json": json.dumps({"outcome": "send-back"}),
    "reference/bad-unrepaired/meta.json": json.dumps({"fails": ["P1"], "why": "reports the fault, repairs nothing"}),
    "reference/bad-touched/result.json": json.dumps({"outcome": "done"}),
    "reference/bad-touched/tree/src/strings.js": "// REPAIRED\nmodule.exports = {};\n",
    "reference/bad-touched/tree/src/paginate.js": "module.exports = {};\n",
    "reference/bad-touched/meta.json": json.dumps({"fails": ["C1"]})}
# A scenario that needs no reference or oracle: it is checked at the render tier only.
LIGHT = {"stage": "validate-existing", "about": "x", "fixture": "node-base", "request_from": "node-fix-bug", "tiers": ["render"],
         "planted": [{"id": "P1", "what": "w"}], "render": [{"proves": "P1", "packet_contains": "x"}]}

E1 = {"id": "E1", "state": "works", "statement": "PLANTED-E1: src/strings.js holds GOOD", "steps": ["S1"],
      "paths": ["src/strings.js"], "check": "grep -q GOOD src/strings.js"}
E2 = {"id": "E2", "state": "works", "statement": "src/paginate.js exists", "steps": ["S1"], "paths": ["src/paginate.js"],
      "check": "test -f src/paginate.js"}


def lay(base: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_text(text)
    return base


def scenario(cases: Path, stage: str, name: str, data: dict | None = None, files: dict | None = None, **changes) -> Path:
    """Write ``<cases>/<stage>/<name>/`` with `data` (default GOOD, `changes` applied; GONE removes a key) and `files`."""
    data = copy.deepcopy(GOOD if data is None else data)
    data["stage"] = stage
    for key, value in changes.items():
        if value is GONE:
            data.pop(key, None)
        else:
            data[key] = value
    folder = cases / stage / name
    lay(folder, {"scenario.json": json.dumps(data), **(GOOD_FILES if files is None else files)})
    return folder


def snapshot(folder: Path) -> dict[str, bytes]:
    return {path.relative_to(folder).as_posix(): path.read_bytes() for path in sorted(folder.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True, text=True, env=GIT_ENV).stdout


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="stage-build-")
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.cases = self.temp / "cases"
        self.cases.mkdir()

    def folder(self, name: str) -> Path:
        path = self.temp / name
        path.mkdir()
        return path


# ----------------------------------------------------------------------------------------------------------------- schema

class Schema(Temp):
    def test_a_good_scenario_has_no_problems(self):
        folder = scenario(self.cases, "validate-existing", "good")
        self.assertEqual(sb.validate(GOOD, folder), [])
        self.assertEqual(sb.validate(json.loads((folder / "scenario.json").read_text()), folder), [])

    def test_the_minimal_scenarios_are_valid(self):
        for label, data, files in (("render only", LIGHT, {}),
                                   ("verify only", {**GOOD, "tiers": ["verify"], "request_from": GONE}, GOOD_FILES)):
            with self.subTest(label):
                data = {key: value for key, value in data.items() if value is not GONE}
                folder = scenario(self.cases, "validate-existing", label.replace(" ", "-"), data, files)
                self.assertEqual(sb.validate(data, folder), [])

    def test_an_improve_stage_validates(self):
        folder = scenario(self.cases, "improve@spec", "missing-outcome")
        self.assertEqual(sb.validate(json.loads((folder / "scenario.json").read_text()), folder), [])

    def test_each_kind_of_malformed_scenario_is_reported_by_its_own_sentence(self):
        def remove(path):
            return lambda data, folder: shutil.rmtree(folder / path) if (folder / path).is_dir() else (folder / path).unlink()

        def edit(path, text):
            return lambda data, folder: (folder / path).write_text(text)

        def reference(*names):
            return lambda data, folder: [shutil.rmtree(folder / "reference" / name) for name in names]

        cases = [
            ("not an object", None, "must be an object"),
            ("unknown key", lambda d, f: d.update(bogus=1), "unknown key 'bogus'"),
            ("unknown stage", lambda d, f: d.update(stage="nope"), "stage 'nope'"),
            ("unknown improve stage", lambda d, f: d.update(stage="improve@nope"), "stage 'improve@nope'"),
            ("no about", lambda d, f: d.pop("about"), "about is required"),
            ("tags not words", lambda d, f: d.update(tags=["a b"]), "tags must be a list of words"),
            ("a tag twice", lambda d, f: d.update(tags=["a", "a"]), "tags names a tag twice"),
            ("unknown tier", lambda d, f: d.update(tiers=["verify", "soak"]), "unknown tier 'soak'"),
            ("no tiers", lambda d, f: d.update(tiers=[]), "tiers must be a non-empty list"),
            ("a tier twice", lambda d, f: d.update(tiers=["verify", "verify"]), "tiers names a tier twice"),
            ("no fixture", lambda d, f: d.pop("fixture"), "fixture is required"),
            ("fixture that is not there", lambda d, f: d.update(fixture="no-such-fixture"), "fixture 'no-such-fixture'"),
            ("fixture that climbs out", lambda d, f: d.update(fixture="../fixtures"), "fixture is required"),
            ("unknown request", lambda d, f: d.update(request_from="no-such-case"), "request_from 'no-such-case'"),
            ("a request the render tier needs", lambda d, f: d.pop("request_from"), "request_from is required"),
            ("unknown option", lambda d, f: d.update(options={"lint": "on"}), "options: unknown key 'lint'"),
            ("unknown delegation", lambda d, f: d.update(options={"delegation": "fan-out"}), "options.delegation"),
            ("records of an unknown stage", lambda d, f: d.update(seed_records={"nope": {}}), "seed_records: 'nope'"),
            ("records that are not fields", lambda d, f: d.update(seed_records={"step-plan": []}), "seed_records.step-plan"),
            ("unknown worktree mode", lambda d, f: d.update(worktree_mode="staged"), "worktree_mode must be one of"),
            ("planted id of a control", lambda d, f: d["planted"][0].update(id="C9"), "planted[0]: id 'C9'"),
            ("planted id without a number", lambda d, f: d["planted"][0].update(id="P"), "planted[0]: id 'P'"),
            ("control id of a planted one", lambda d, f: d["controls"][0].update(id="P7"), "controls[0]: id 'P7'"),
            ("an id used twice", lambda d, f: d["controls"].append({"id": "C1", "what": "again"}), "id C1 is already used"),
            ("a planted condition without what", lambda d, f: d["planted"][0].pop("what"), "planted[0]: what must be"),
            ("an unknown key of a planted condition", lambda d, f: d["planted"][0].update(why="x"), "planted[0]: unknown key"),
            ("a malformed oracle check", lambda d, f: d["oracle"].append({"outcome": []}), "oracle[3]: outcome must be"),
            ("a render check of no known id", lambda d, f: d["render"][0].update(proves="P9"), "render[0]: proves 'P9'"),
            ("a check list that is not a list", lambda d, f: d.update(oracle={}), "oracle must be a list"),
            ("a planted condition no check proves", lambda d, f: d["planted"].append({"id": "P2", "what": "w"}),
             "P2 is proven by no check in oracle"),
            ("a stand-in that is not there", lambda d, f: d["oracle"].append(
                {"stand_in": "stand_ins/empty", "command": "true", "kills": True}), "stand-in folder 'stand_ins/empty'"),
            ("live that is not an object", lambda d, f: d.update(live=3), "live must be an object"),
            ("no samples", lambda d, f: d.update(live={"samples": 0}), "live.samples"),
            ("a pass rule above the samples", lambda d, f: d.update(live={"samples": 2, "pass": 3}), "live.pass"),
            ("an unknown live key", lambda d, f: d.update(live={"budget": 1}), "live: unknown key 'budget'"),
            ("repo that is a file", lambda d, f: lay(f, {"repo": "x"}), "repo must be a folder"),
            ("a worktree before implement", lambda d, f: lay(f, {"worktree/src/strings.js": "x\n"}),
             "worktree/ is for a stage after validate-existing"),
            ("no good output", reference("good"), "reference/good is missing"),
            ("no bad output for a planted condition", reference("bad-unrepaired"), "P1 is failed by no reference/bad-*"),
            ("no bad output for a control", reference("bad-touched"), "C1 is failed by no reference/bad-*"),
            ("a result that is not JSON", edit("reference/good/result.json", "{"), "reference/good/result.json is not valid JSON"),
            ("a result without an outcome", edit("reference/good/result.json", "{}"), "an object with an \"outcome\""),
            ("no result", remove("reference/good/result.json"), "reference/good/result.json is missing"),
            ("no meta", remove("reference/bad-touched/meta.json"), "reference/bad-touched/meta.json is missing"),
            ("a meta that is not JSON", edit("reference/bad-touched/meta.json", "["), "meta.json is not valid JSON"),
            ("a meta without fails", edit("reference/bad-touched/meta.json", "{}"), "meta.json must be an object with"),
            ("a meta that fails an unknown id", edit("reference/bad-touched/meta.json", '{"fails": ["C1", "P8"]}'),
             "fails 'P8', which is not a planted or control id"),
            ("a reference folder of another kind", lambda d, f: lay(f, {"reference/maybe/result.json": "{}"}),
             "a reference folder is good or bad-<slug>"),
            ("a deleted.txt that climbs out", lambda d, f: lay(f, {"reference/good/deleted.txt": "../x\n"}),
             "deleted.txt: '../x' climbs out"),
        ]
        for number, (label, mutate, wanted) in enumerate(cases):
            with self.subTest(label):
                folder = scenario(self.folder(f"s{number}"), "validate-existing", "s")
                data = copy.deepcopy(GOOD)
                if mutate is None:
                    data = []
                else:
                    mutate(data, folder)
                problems = sb.validate(data, folder)
                self.assertTrue(any(wanted in problem for problem in problems), f"{wanted!r} not in {problems}")

    def test_a_worktree_is_for_a_stage_after_validate_existing(self):
        # The checks validate-existing runs on entry come before the seed point, so a worktree/ at or before it would be laid
        # after they ran and the packet would describe a tree the model does not get.
        for stage in stage_spec.STAGES:
            for name in (stage, "improve@" + stage):
                data = {**copy.deepcopy(LIGHT), "stage": name}
                folder = scenario(self.folder(name.replace("@", "-")), name, "s", data, {"worktree/extra.txt": "x\n"})
                found = [problem for problem in sb.validate(data, folder) if "worktree/" in problem]
                early = stage_spec.STAGES.index(stage) <= stage_spec.STAGES.index("validate-existing")
                with self.subTest(stage=name):
                    self.assertEqual(bool(found), early, found)
                    if early:
                        self.assertIn("put these files in repo/", found[0])
        # repo/ is what such a scenario uses, and an empty worktree/ folder is no overlay either way
        data = {**copy.deepcopy(LIGHT), "stage": "validate-existing"}
        folder = scenario(self.folder("repo-only"), "validate-existing", "s", data, {"repo/extra.txt": "x\n"})
        self.assertEqual(sb.validate(data, folder), [])

    def test_several_problems_are_reported_at_once(self):
        folder = scenario(self.cases, "validate-existing", "many")
        data = copy.deepcopy(GOOD)
        data.update(bogus=1, tiers=["verify", "soak"], fixture="no-such-fixture")
        data["planted"][0]["id"] = "X1"
        shutil.rmtree(folder / "reference" / "good")
        problems = sb.validate(data, folder)
        for wanted in ("unknown key 'bogus'", "unknown tier", "fixture 'no-such-fixture'", "planted[0]: id 'X1'",
                       "reference/good is missing"):
            self.assertTrue(any(wanted in problem for problem in problems), f"{wanted!r} not in {problems}")

    def test_the_tiers_a_scenario_is_not_in_do_not_ask_for_what_they_would_need(self):
        data = {**copy.deepcopy(GOOD), "tiers": ["render"], "oracle": []}
        folder = scenario(self.folder("render-only"), "validate-existing", "s", data, {})
        self.assertEqual(sb.validate(data, folder), [], "no oracle, reference or live samples are asked of a render-only scenario")
        data["tiers"] = ["verify", "render"]
        self.assertTrue(any("is proven by no check in oracle" in problem for problem in sb.validate(data, folder)))
        data["tiers"] = ["live"]
        self.assertTrue(any("is proven by no check in oracle" in problem for problem in sb.validate(data, folder)))
        self.assertEqual([problem for problem in sb.validate(data, folder) if "reference" in problem], [])


# --------------------------------------------------------------------------------------------------------------- discovery

class Discovery(Temp):
    def test_scenarios_are_sorted_by_stage_order_with_improve_stages_last_then_by_name(self):
        for stage, name in (("document", "b"), ("improve@spec", "x"), ("validate-existing", "beta"), ("intake", "y"),
                            ("validate-existing", "alpha"), ("step-plan", "zeta"), ("improve@intake", "a"), ("document", "a")):
            scenario(self.cases, stage, name, LIGHT, {})
        found = sb.discover(self.cases)
        self.assertEqual([sc.id for sc in found],
                         ["intake/y", "step-plan/zeta", "validate-existing/alpha", "validate-existing/beta", "document/a",
                          "document/b", "improve@intake/a", "improve@spec/x"])
        order = [stage_spec.STAGES.index(sc.stage) for sc in found if not sc.stage.startswith("improve@")]
        self.assertEqual(order, sorted(order))
        first = found[2]
        self.assertEqual((first.stage, first.name, first.dir, first.tiers, first.tags),
                         ("validate-existing", "alpha", self.cases / "validate-existing" / "alpha", ("render",), ()))
        self.assertEqual(first.data["fixture"], "node-base")
        self.assertEqual(len({sc: 1 for sc in found}), len(found), "a scenario can be a dictionary key")

    def test_tiers_and_tags_come_from_the_scenario(self):
        scenario(self.cases, "validate-existing", "all", GOOD, GOOD_FILES)
        scenario(self.cases, "validate-existing", "two", {**LIGHT, "tiers": ["live", "render"], "tags": ["control"],
                                                           "oracle": [{"proves": "P1", "outcome": ["done"]}]}, {})
        found = {sc.name: sc for sc in sb.discover(self.cases)}
        self.assertEqual(found["all"].tiers, ("verify", "render", "live"))
        self.assertEqual(found["all"].tags, ("catch", "prep-fix"))
        self.assertEqual(found["two"].tiers, ("render", "live"))

    def test_nothing_to_discover_is_an_empty_list(self):
        self.assertEqual(sb.discover(self.cases), [])
        self.assertEqual(sb.discover(self.temp / "no-such-folder"), [])

    def test_every_problem_of_every_scenario_is_listed_in_one_error(self):
        scenario(self.cases, "validate-existing", "fine", LIGHT, {})
        scenario(self.cases, "validate-existing", "no-about", {k: v for k, v in LIGHT.items() if k != "about"}, {})
        scenario(self.cases, "step-plan", "bad-id", {**LIGHT, "planted": [{"id": "Q1", "what": "w"}], "render": []}, {})
        lay(self.cases / "test" / "broken", {"scenario.json": "{not json"})
        lay(self.cases / "test" / "empty", {"notes.txt": "x"})
        lay(self.cases / "nonsense" / "s", {"scenario.json": json.dumps(LIGHT)})
        lay(self.cases / "document" / "elsewhere", {"scenario.json": json.dumps({**LIGHT, "stage": "test"})})
        with self.assertRaises(sb.ScenarioError) as raised:
            sb.discover(self.cases)
        message, problems = str(raised.exception), raised.exception.problems
        self.assertIsInstance(raised.exception, ValueError)
        for wanted in ("validate-existing/no-about: about is required", "step-plan/bad-id: planted[0]: id 'Q1'",
                       "test/broken: scenario.json is not valid JSON", "test/empty: scenario.json is missing",
                       "nonsense: not a stage folder", "document/elsewhere: stage 'test' differs from its folder 'document'"):
            self.assertIn(wanted, message)
        self.assertEqual(len(problems), 6)
        self.assertNotIn("validate-existing/fine", message)

    def test_load_takes_the_stage_and_the_name(self):
        scenario(self.cases, "validate-existing", "fine", LIGHT, {})
        scenario(self.cases, "validate-existing", "no-about", {k: v for k, v in LIGHT.items() if k != "about"}, {})
        sc = sb.load("validate-existing/fine", self.cases)
        self.assertEqual((sc.id, sc.stage, sc.name), ("validate-existing/fine", "validate-existing", "fine"))
        for bad, why in (("validate-existing/missing", "no such scenario"), ("validate-existing", "<stage>/<name>"),
                         ("../cases/x", "<stage>/<name>"), ("a/b/c", "<stage>/<name>"),
                         ("validate-existing/no-about", "about is required")):
            with self.subTest(bad), self.assertRaisesRegex(sb.ScenarioError, why):
                sb.load(bad, self.cases)

    def test_the_shipped_scenarios_load(self):
        found = sb.discover()  # SCENARIOS_DIR: every one valid, or discover raises
        self.assertEqual(len({sc.id for sc in found}), len(found))
        # They are the ones the guide and the plan name; test/shiploop-e2e-stages.test.py verifies and renders them.
        self.assertLessEqual({"validate-existing/all-match", "validate-existing/broken-works-small-fix",
                              "validate-existing/wrong-check"}, {sc.id for sc in found})


# ------------------------------------------------------------------------------------------------------------------ trees

class Trees(Temp):
    def folder_for(self, files: dict, data: dict | None = None, stage: str = "validate-existing") -> sb.Scenario:
        name = f"t{len(list((self.cases / stage).glob('*'))) if (self.cases / stage).is_dir() else 0}"
        scenario(self.cases, stage, name, data or LIGHT, files)
        return sb.load(f"{stage}/{name}", self.cases)

    def test_the_seed_tree_is_the_fixture_then_repo_then_worktree(self):
        sc = self.folder_for({"repo/src/strings.js": "from repo\n", "repo/README.md": "repo readme\n",
                              "repo/only-repo.txt": "r\n", "repo/clash.txt": "from repo\n",
                              "worktree/clash.txt": "from worktree\n", "worktree/only-worktree.txt": "w\n",
                              "worktree/src/strings.js": "from worktree\n", "repo/__pycache__/x.pyc": "c"}, stage="implement")
        fixture_before = snapshot(HARNESS / "fixtures" / "node-base")
        into = sb.compose_seed_tree(sc, self.temp / "seed")
        self.assertEqual(into, self.temp / "seed")
        self.assertEqual((into / "src" / "strings.js").read_text(), "from worktree\n", "worktree over repo over the fixture")
        self.assertEqual((into / "clash.txt").read_text(), "from worktree\n")
        self.assertEqual((into / "README.md").read_text(), "repo readme\n", "repo over the fixture")
        self.assertEqual((into / "only-repo.txt").read_text(), "r\n")
        self.assertEqual((into / "only-worktree.txt").read_text(), "w\n")
        self.assertEqual((into / "src" / "paginate.js").read_bytes(),
                         (HARNESS / "fixtures" / "node-base" / "src" / "paginate.js").read_bytes(), "the rest is the fixture")
        self.assertFalse((into / "__pycache__").exists())
        self.assertEqual(snapshot(HARNESS / "fixtures" / "node-base"), fixture_before, "the fixture is never written")
        self.assertFalse((into / ".git").exists(), "file composition only: no Git")

    def test_a_scenario_without_overlays_composes_the_fixture_alone(self):
        sc = self.folder_for({})
        into = sb.compose_seed_tree(sc, self.temp / "seed")
        self.assertEqual(snapshot(into), snapshot(HARNESS / "fixtures" / "node-base"))

    def test_a_file_replaces_a_folder_and_a_folder_replaces_a_file(self):
        sc = self.folder_for({"repo/test": "now a file\n", "worktree/README.md/inside.txt": "now a folder\n"}, stage="implement")
        into = sb.compose_seed_tree(sc, self.temp / "seed")
        self.assertEqual((into / "test").read_text(), "now a file\n")
        self.assertEqual((into / "README.md" / "inside.txt").read_text(), "now a folder\n")

    def test_the_reference_outputs_are_listed_good_first(self):
        sc = self.folder_for({"reference/good/result.json": "{}", "reference/bad-b/result.json": "{}",
                              "reference/bad-a/result.json": "{}", "reference/notes.txt": "x"})
        self.assertEqual(sb.reference_names(sc), ["good", "bad-a", "bad-b"])
        self.assertEqual(sb.reference_names(self.folder_for({})), [])

    def test_a_reference_bundle_is_the_seed_tree_with_the_references_tree_laid_over_it(self):
        scenario(self.cases, "validate-existing", "ref", GOOD, {
            **GOOD_FILES, "repo/src/strings.js": "// BROKEN\n",
            "reference/good/tree/src/new.js": "module.exports = 1;\n",
            "reference/good/deleted.txt": "src/users.js\ntest/users.test.js\n\n"})
        sc = sb.load("validate-existing/ref", self.cases)
        bundle, meta = sb.reference_bundle(sc, "good", self.temp / "tmp")
        self.assertEqual(meta, {})
        self.assertEqual(bundle.result, {"outcome": "done", "summary": "Repaired."})
        self.assertTrue(bundle.issued)
        self.assertIsNone(bundle.packet)
        self.assertEqual(bundle.scenario_dir, sc.dir)
        self.assertEqual((bundle.seed_tree / "src" / "strings.js").read_text(), "// BROKEN\n", "the seed tree is untouched")
        self.assertTrue((bundle.seed_tree / "src" / "users.js").is_file())
        self.assertEqual((bundle.tree / "src" / "strings.js").read_text(), "// REPAIRED\nmodule.exports = {};\n")
        self.assertEqual((bundle.tree / "src" / "new.js").read_text(), "module.exports = 1;\n")
        self.assertFalse((bundle.tree / "src" / "users.js").exists(), "deleted.txt removes a file")
        self.assertFalse((bundle.tree / "test" / "users.test.js").exists())
        self.assertTrue((bundle.tree / "src" / "paginate.js").is_file(), "the rest of the tree stays")
        self.assertNotEqual(bundle.tree, bundle.seed_tree)
        # A second call for the same reference starts again from the seed tree.
        again, _ = sb.reference_bundle(sc, "good", self.temp / "tmp")
        self.assertEqual(snapshot(again.tree), snapshot(bundle.tree))

    def test_a_bad_reference_brings_its_meta(self):
        sc = self.folder_for(GOOD_FILES, GOOD)
        bundle, meta = sb.reference_bundle(sc, "bad-unrepaired", self.temp / "tmp")
        self.assertEqual(meta, {"fails": ["P1"], "why": "reports the fault, repairs nothing"})
        self.assertEqual(bundle.result, {"outcome": "send-back"})
        self.assertEqual(snapshot(bundle.tree), snapshot(bundle.seed_tree), "a bad output may leave the tree alone")

    def test_a_deleted_path_the_tree_does_not_hold_is_refused(self):
        sc = self.folder_for({**GOOD_FILES, "reference/good/deleted.txt": "src/no-such-file.js\n"}, GOOD)
        with self.assertRaisesRegex(sb.ScenarioError, "names 'src/no-such-file.js', which the tree does not hold"):
            sb.reference_bundle(sc, "good", self.temp / "tmp")
        with self.assertRaisesRegex(sb.ScenarioError, "no reference output 'bad-none'"):
            sb.reference_bundle(sc, "bad-none", self.temp / "tmp")

    def test_the_oracle_passes_the_good_output_and_fails_each_bad_one_on_the_id_it_plants(self):
        scenario(self.cases, "validate-existing", "verify", GOOD, {**GOOD_FILES, "repo/src/strings.js": "// BROKEN\n"})
        sc = sb.load("validate-existing/verify", self.cases)
        planted, controls = [row["id"] for row in GOOD["planted"]], [row["id"] for row in GOOD["controls"]]
        found = {}
        for name in sb.reference_names(sc):
            bundle, meta = sb.reference_bundle(sc, name, self.temp / "tmp")
            found[name] = (stage_oracle.verdict(planted, controls, stage_oracle.run_checks(sc.data["oracle"], bundle)), meta)
        self.assertTrue(found["good"][0]["pass"], found["good"][0])
        for name, (verdict, meta) in found.items():
            if name != "good":
                self.assertFalse(verdict["pass"], name)
                failed = [ident for ident, ok in {**verdict["caught"], **verdict["held"]}.items() if ok is False]
                self.assertEqual(failed, meta["fails"], name)


# --------------------------------------------------------------------------------------------------------------- building

def records(*expectations) -> dict:
    return {"step-plan": {"expectations": list(expectations)}}


class Builds(unittest.TestCase):
    """Real runs, built once for the class (about a second each)."""

    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory(prefix="stage-build-run-")
        cls.addClassCleanup(temp.cleanup)
        cls.temp = Path(temp.name).resolve()  # build returns resolved paths (macOS: /var/folders is /private/var/folders)
        # A private HOME and no Git configuration, as test/git_fixture.py does for a test case.
        home = cls.temp / "home"
        (home / ".config").mkdir(parents=True)
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
        isolated = mock.patch.dict(os.environ, environment, clear=True)
        isolated.start()
        cls.addClassCleanup(isolated.stop)
        cls.home = home
        cls.safepath = os.environ.get("PYTHONSAFEPATH")
        cls.cases = cls.temp / "cases"
        base = {"about": "x", "fixture": "node-base", "request_from": "node-fix-bug", "tiers": ["render"],
                "planted": [{"id": "P1", "what": "w"}], "render": [{"proves": "P1", "packet_contains": "x"}]}
        scenario(cls.cases, "validate-existing", "broken", base, {}, seed_records=records(E1, E2))
        scenario(cls.cases, "validate-existing", "repaired", base, {"repo/src/strings.js": "// GOOD\nmodule.exports = {};\n"},
                 seed_records=records(E1, E2))
        scenario(cls.cases, "document", "after-implement", base,
                 {"worktree/src/added.js": "module.exports = 2;\n", "notes/earlier.md": "Left by an earlier stage.\n"},
                 seed_records=records(E2))
        scenario(cls.cases, "carry-forward", "step-committed", base, {"worktree/src/added.js": "module.exports = 2;\n"},
                 seed_records=records(E2), options={"delegation": "ask-agent"})
        scenario(cls.cases, "improve@spec", "later", base, {})
        scenario(cls.cases, "release", "later", base, {})
        cls.box = cls.temp / "box"
        cls.box.mkdir()
        cls.watched = {"cases": snapshot(cls.cases), "fixtures": snapshot(HARNESS / "fixtures"), "home": snapshot(home)}
        cls.digest = boundary.fingerprint(HARNESS, None)
        cls.built = {}
        for sid in ("validate-existing/broken", "validate-existing/repaired", "document/after-implement"):
            cls.built[sid] = sb.render(sb.load(sid, cls.cases), cls.box / sid.replace("/", "-"))
        cls.carried = sb.build(sb.load("carry-forward/step-committed", cls.cases), cls.box / "carry-forward")

    def out(self, sid: str) -> Path:
        return self.box / sid.replace("/", "-")

    def test_a_build_through_a_symlinked_folder_spells_each_path_one_way(self):
        # ShipLoop records the execution checkout resolved; the run folder came from `out` as given. macOS's /var/folders
        # is such a link, and so is any symlinked output folder.
        real = self.temp / "linked-real"
        real.mkdir()
        link = self.temp / "linked"
        link.symlink_to(real, target_is_directory=True)
        built = sb.build(sb.load("validate-existing/broken", self.cases), link / "run")
        seed = real / "run" / ".shiploop-runs" / "seed"
        self.assertEqual((built.run_dir, built.worktree), (seed / "run", seed / "worktree"))

    def test_a_planted_failing_expectation_reaches_the_packet(self):
        bundle = self.built["validate-existing/broken"]
        self.assertTrue(bundle.issued)
        self.assertFalse(bundle.settled)
        self.assertEqual(bundle.current_stage, "validate-existing")
        self.assertIsNone(bundle.result)
        self.assertRegex(bundle.packet_head, r"ShipLoop navigator \| validate-existing \|")
        # The checks ran on entry (the engine's effect, which the harness's own seed skips): the packet names the expectation, its
        # statement and the mismatch, and leaves the one that matches alone.
        self.assertRegex(bundle.packet, r"E1 works\s+PLANTED-E1: src/strings\.js holds GOOD.*-> DOES NOT MATCH, exit 1")
        self.assertRegex(bundle.packet, r"E2 works\s+src/paginate\.js exists.*-> MATCHES")
        self.assertNotRegex(bundle.packet, r"E2 works.*DOES NOT MATCH")
        checks = [{"proves": "P1", "packet_contains": r"E1 works.*-> DOES NOT MATCH"},
                  {"proves": "P1", "packet_head_contains": r"\| validate-existing \|"},
                  {"proves": "P1", "packet_issued": True}, {"proves": "P1", "current_stage": "validate-existing"},
                  {"proves": "P1", "settled_by_script": False}, {"packet_not_contains": r"E2 works.*DOES NOT MATCH"}]
        verdict = stage_oracle.verdict(["P1"], [], stage_oracle.run_checks(checks, bundle))
        self.assertTrue(verdict["pass"], verdict)

    def test_the_bundle_carries_the_run_and_its_trees(self):
        bundle = self.built["validate-existing/broken"]
        self.assertTrue(bundle.run_dir.is_dir())
        self.assertEqual(bundle.run_dir, self.out("validate-existing/broken") / ".shiploop-runs" / "seed" / "run")
        self.assertEqual(bundle.tree, self.out("validate-existing/broken") / ".shiploop-runs" / "seed" / "worktree")
        self.assertEqual(bundle.scenario_dir, self.cases / "validate-existing" / "broken")
        self.assertTrue((bundle.run_dir / "packets").is_dir())
        self.assertEqual(snapshot(bundle.tree), snapshot(bundle.seed_tree), "nothing has changed the checkout since the seed")
        self.assertTrue((bundle.tree / "src" / "strings.js").is_file(), "the fixture is in the execution checkout")
        self.assertTrue((bundle.tree / "docs" / "shiploop" / "spec.md").is_file(), "with the neutral knowledge home")
        self.assertEqual(git(bundle.tree, "log", "--format=%s").strip(), "seed: baseline")
        work = self.out("validate-existing/broken") / "work"
        self.assertTrue((work / "src" / "strings.js").is_file(), "the product repository holds the baseline")
        self.assertTrue((bundle.run_dir / "lint" / "items" / "W1.md").is_file(), "the item base was recorded through the effects")

    def test_the_default_delegation_is_inline_and_the_work_item_is_the_cases(self):
        state = store.read_record(self.built["validate-existing/broken"].run_dir / "state.md")
        case = sb.step_cases()["node-fix-bug"]
        self.assertEqual(state["delegation"], "inline")
        self.assertEqual(state["work_items"][0]["id"], case["work_item"]["id"])
        self.assertEqual(state["work_items"][0]["title"], case["work_item"]["title"])

    def test_every_expectation_matching_settles_the_stage_by_script_and_issues_no_packet(self):
        bundle = self.built["validate-existing/repaired"]
        self.assertTrue(bundle.settled)
        self.assertFalse(bundle.issued)
        self.assertIsNone(bundle.packet)
        self.assertEqual(bundle.current_stage, "implement", "the run is already past the stage")
        self.assertRegex(bundle.packet_head, r"ShipLoop navigator \| implement \|")
        self.assertEqual((bundle.tree / "src" / "strings.js").read_text(), "// GOOD\nmodule.exports = {};\n",
                         "repo/ was laid before the baseline commit")
        self.assertEqual(git(bundle.tree, "log", "--format=%s").strip(), "seed: baseline")
        verdict = stage_oracle.verdict(["P1"], [], stage_oracle.run_checks(
            [{"proves": "P1", "settled_by_script": True}, {"proves": "P1", "packet_issued": False},
             {"proves": "P1", "current_stage": "implement"}], bundle))
        self.assertTrue(verdict["pass"], verdict)
        rows = [row for row in store.read_record(bundle.run_dir / "state.md")["history"]
                if row["stage"] == "validate-existing"]
        self.assertEqual([row["outcome"] for row in rows], ["done"])
        self.assertFalse((bundle.run_dir / "packets" / (rows[0]["action"] + ".md")).exists(), "no packet was issued")

    def test_the_worktree_overlay_laid_before_implement_leaves_the_document_stage_a_change(self):
        bundle = self.built["document/after-implement"]
        self.assertTrue(bundle.issued)
        self.assertEqual(bundle.current_stage, "document")
        self.assertRegex(bundle.packet_head, r"ShipLoop navigator \| document \|")
        self.assertEqual((bundle.tree / "src" / "added.js").read_text(), "module.exports = 2;\n")
        self.assertIn("?? src/added.js", git(bundle.tree, "status", "--short"), "left uncommitted, as implement leaves it")
        self.assertIn("Changed since the item base (script-derived): src/added.js", bundle.packet)
        self.assertTrue((bundle.run_dir / "iterations" / "W1.json").is_file(), "the step has the iteration record its commit needs")
        # The seed walked every stage before document through the seam; nothing was left for `next` to repair.
        stages = [row["stage"] for row in
                  store.read_record(bundle.run_dir / "state.md")["history"]]
        for stage in ("step-plan", "test-spec", "validate-existing", "implement", "test"):
            self.assertIn(stage, stages)
        self.assertNotIn("document", stages)
        self.assertEqual((bundle.notes / "earlier.md").read_text(), "Left by an earlier stage.\n", "notes/ is laid into RUN/notes")
        checks = [{"proves": "P1", "file": "src/added.js", "exists": True}, {"proves": "P1", "packet_contains": "src/added.js"}]
        self.assertTrue(stage_oracle.verdict(["P1"], [], stage_oracle.run_checks(checks, bundle))["pass"])

    def test_a_seed_past_document_has_the_steps_commit_and_the_scenarios_delegation(self):
        built = self.carried
        self.assertIsInstance(built, sb.Built)
        self.assertEqual((built.stage, built.current_stage, built.issued, built.settled),
                         ("carry-forward", "carry-forward", True, False))
        self.assertEqual(built.seeded["delegation"], "ask-agent")
        self.assertEqual(built.seeded["item_bases"], ["W1"])
        self.assertIn("feat(W1/S1)", git(built.worktree, "log", "--format=%s"), "the document stage's review was imported")
        self.assertEqual(git(built.worktree, "status", "--short", "src"), "", "and the overlay committed with it")
        self.assertEqual(built.cli, sb.DEFAULT_CLI)
        self.assertEqual(built.run_dir, self.box / "carry-forward" / ".shiploop-runs" / "seed" / "run")
        self.assertEqual(built.worktree, self.box / "carry-forward" / ".shiploop-runs" / "seed" / "worktree")
        self.assertEqual([row["stage"] for row in built.history_added if row["stage"] == "document"], ["document"])
        self.assertTrue(all(set(row) == {"stage", "outcome", "action"} for row in built.history_added))

    def test_a_build_writes_only_below_its_out_folder(self):
        self.assertEqual(sorted(path.name for path in self.box.iterdir()),
                         ["carry-forward", "document-after-implement", "validate-existing-broken", "validate-existing-repaired"])
        for name, folder in (("cases", self.cases), ("fixtures", HARNESS / "fixtures"), ("home", self.home)):
            self.assertEqual(snapshot(folder), self.watched[name], f"{name} was written by a build")
        self.assertEqual(sorted(path.name for path in self.cases.iterdir()),
                         ["carry-forward", "document", "improve@spec", "release", "validate-existing"])

    def test_a_build_does_not_reuse_a_folder_that_holds_a_run(self):
        sc = sb.load("validate-existing/broken", self.cases)
        with self.assertRaisesRegex(FileExistsError, "already holds a run"):
            sb.build(sc, self.out("validate-existing/broken"))

    def test_a_build_leaves_the_evaluator_digest_where_it_was(self):
        self.assertEqual(boundary.fingerprint(HARNESS, None), self.digest)

    def test_the_harness_seed_is_the_harnesss_own_again_after_a_build(self):
        self.assertNotEqual(run.SEED_SCRIPT, sb.SEAM_SEED_SCRIPT)
        self.assertIn("lint.capture_base", run.SEED_SCRIPT, "run.SEED_SCRIPT is the harness's, not edited")
        self.assertNotIn(sb.WORKTREE_ENV, os.environ)
        for index in range(1, 6):  # the same argv contract
            self.assertIn(f"sys.argv[{index}]", sb.SEAM_SEED_SCRIPT)
            self.assertIn(f"sys.argv[{index}]", run.SEED_SCRIPT)

    def test_the_harness_seed_is_restored_when_the_build_raises(self):
        sc = sb.load("validate-existing/broken", self.cases)
        original, progress = run.SEED_SCRIPT, os.environ.get("SHIPLOOP_PROGRESS")
        seen = {}

        def failing(*args, **kwargs):
            seen.update(script=run.SEED_SCRIPT, overlay=os.environ.get(sb.WORKTREE_ENV), progress=os.environ.get("SHIPLOOP_PROGRESS"))
            raise RuntimeError("the seed failed")

        with mock.patch.object(run, "seed_run", failing), self.assertRaisesRegex(RuntimeError, "the seed failed"):
            sb.build(sc, self.temp / "raises")
        self.assertIs(seen["script"], sb.SEAM_SEED_SCRIPT, "the call seeds through the seam")
        self.assertEqual(seen["progress"], "off")
        self.assertIsNone(seen["overlay"], "this scenario has no worktree/")
        self.assertIs(run.SEED_SCRIPT, original)
        self.assertEqual(os.environ.get("SHIPLOOP_PROGRESS"), progress)
        self.assertNotIn(sb.WORKTREE_ENV, os.environ)
        # The real seed_run failing (no ShipLoop at the CLI path) raises its own SystemExit; the global is restored as well.
        with self.assertRaises(SystemExit):
            sb.build(sc, self.temp / "raises-too", cli=self.temp / "no-such-cli" / "shiploop")
        self.assertIs(run.SEED_SCRIPT, original)
        # And a scenario with a worktree/ hands the folder to the seed.
        sc = sb.load("document/after-implement", self.cases)
        with mock.patch.object(run, "seed_run", failing), self.assertRaises(RuntimeError):
            sb.build(sc, self.temp / "raises-three")
        self.assertEqual(seen["overlay"], str(sc.dir / "worktree"))
        self.assertNotIn(sb.WORKTREE_ENV, os.environ)

    def test_the_seam_substitution_is_exclusive_between_threads(self):
        # Without a lock the second thread saves the first one's substitute as its "original" and puts it back last.
        original, progress = run.SEED_SCRIPT, os.environ.get("SHIPLOOP_PROGRESS")
        inside, begun = [], threading.Barrier(4)

        def seed(number: int):
            begun.wait()
            with sb.seam_seed(Path(f"/overlay/{number}")):
                time.sleep(0.05)  # long enough for another thread to have run, if it could
                inside.append((run.SEED_SCRIPT is sb.SEAM_SEED_SCRIPT, os.environ.get(sb.WORKTREE_ENV) == f"/overlay/{number}"))

        threads = [threading.Thread(target=seed, args=(number,)) for number in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        self.assertEqual(inside, [(True, True)] * 4, "each block saw its own substitution")
        self.assertIs(run.SEED_SCRIPT, original)
        self.assertEqual(os.environ.get("SHIPLOOP_PROGRESS"), progress)
        self.assertNotIn(sb.WORKTREE_ENV, os.environ)
        self.assertEqual(os.environ.get("PYTHONSAFEPATH"), self.safepath)

    def test_the_substitution_may_nest_in_one_thread(self):
        original = run.SEED_SCRIPT
        with sb.seam_seed(), sb.seam_seed(Path("/overlay/inner")):
            self.assertEqual(os.environ[sb.WORKTREE_ENV], "/overlay/inner")
        self.assertIs(run.SEED_SCRIPT, original)
        self.assertNotIn(sb.WORKTREE_ENV, os.environ)

    def test_the_seed_does_not_import_from_the_working_directory(self):
        with sb.seam_seed():
            self.assertEqual(os.environ["PYTHONSAFEPATH"], "1")
        self.assertEqual(os.environ.get("PYTHONSAFEPATH"), self.safepath)
        # And a build started from a folder that holds a module named like a standard-library one is not hurt by it.
        hostile = lay(self.temp / "hostile", {"json.py": "raise RuntimeError('EVIL json imported from the working directory')\n"})
        here = os.getcwd()
        os.chdir(hostile)
        try:
            bundle = sb.render(sb.load("validate-existing/broken", self.cases), self.temp / "from-hostile")
        finally:
            os.chdir(here)
        self.assertTrue(bundle.issued)
        self.assertEqual(bundle.current_stage, "validate-existing")

    def test_a_render_whose_packet_file_is_missing_says_so_instead_of_reading_the_head(self):
        sc = sb.load("validate-existing/broken", self.cases)
        # A `next` that printed a head and wrote no packet file (only stage_build's own `subprocess` is replaced).
        fake = types.SimpleNamespace(DEVNULL=subprocess.DEVNULL, run=lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout="ShipLoop navigator | validate-existing | head only", stderr=""))
        with mock.patch.object(sb, "subprocess", fake), self.assertRaisesRegex(RuntimeError, "issued no packet file at .*packets"):
            sb.render(sc, self.temp / "no-packet")

    def test_an_improve_stage_and_an_outer_stage_load_but_do_not_build_yet(self):
        for sid, wanted in (("improve@spec/later", "improve@ scenarios arrive with wave 2"),
                            ("release/later", "outer-stage scenarios arrive with wave 3")):
            sc = sb.load(sid, self.cases)
            for function in (sb.build, sb.render):
                with self.subTest(sid, function=function.__name__):
                    out = self.temp / "not-built" / sid.replace("/", "-") / function.__name__
                    with self.assertRaisesRegex(NotImplementedError, wanted):
                        function(sc, out)
                    self.assertFalse(out.exists(), "nothing was written")
        self.assertEqual(sb.load("improve@spec/later", self.cases).stage, "improve@spec")

    def test_a_scenario_that_names_no_request_cannot_be_built(self):
        cases = self.temp / "verify-cases"
        scenario(cases, "validate-existing", "verify-only", {key: value for key, value in GOOD.items() if key != "request_from"},
                 GOOD_FILES, tiers=["verify"])
        sc = sb.load("validate-existing/verify-only", cases)
        with self.assertRaisesRegex(sb.ScenarioError, "request_from is required to build"):
            sb.build(sc, self.temp / "no-request")


# ---------------------------------------------------------------------------------------------------------------- boundary

class Boundary(unittest.TestCase):
    def test_the_builder_is_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        builder = HARNESS / "stage_suite" / "stage_build.py"
        self.assertTrue(builder.is_file())
        evaluator, graded = set(boundary.evaluator_files(HARNESS)), set(boundary.oracle_files(HARNESS))
        self.assertNotIn(builder, evaluator)
        self.assertNotIn(builder, graded)
        self.assertFalse(any(path.parent.name in ("stage_suite", "stage_cases") for path in evaluator | graded))
        snapshot_files = boundary.qualification_snapshot(HARNESS)["files"]
        self.assertFalse([name for name in snapshot_files if "/stage_suite/" in name or "/stage_cases/" in name])
        self.assertFalse([name for name in snapshot_files if name.startswith("test/shiploop-e2e-stage")])

    def test_no_stage_file_is_in_the_top_level_of_the_harness(self):
        self.assertEqual(sorted(path.name for path in HARNESS.iterdir() if path.is_file() and path.name.startswith("stage")), [])

    def test_adding_or_changing_the_builder_leaves_the_digest_where_it_was(self):
        with tempfile.TemporaryDirectory(prefix="stage-build-boundary-") as temp:
            harness = lay(Path(temp), {"run.py": "x = 1\n", "checks/c.py": "y = 2\n", "SPEC.md": "s\n"})
            before = boundary.fingerprint(harness, None)
            lay(harness, {"stage_suite/stage_build.py": "z = 3\n", "stage_cases/validate-existing/s/scenario.json": "{}\n"})
            self.assertEqual(boundary.fingerprint(harness, None), before)
            lay(harness, {"stage_suite/stage_build.py": "z = 4\n"})
            self.assertEqual(boundary.fingerprint(harness, None), before)

    def test_the_candidate_may_not_change_the_builder_or_its_test(self):
        for path in ("test/shiploop_e2e/stage_suite/stage_build.py", "test/shiploop-e2e-stage-build.test.py"):
            with self.subTest(path=path):
                self.assertFalse(boundary.candidate_path(path))

    def test_the_builder_uses_the_engines_check_validation_and_the_harnesss_seed_without_copying_them(self):
        text = (HARNESS / "stage_suite" / "stage_build.py").read_text()
        self.assertIn("stage_oracle.validate_checks(", text)
        self.assertIn("run.seed_run(", text)
        for copied in ("def validate_checks", "class Bundle", "def run_checks"):
            self.assertNotIn(copied, text)


if __name__ == "__main__":
    unittest.main()
