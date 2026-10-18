#!/usr/bin/env python3
"""The `battleship-salesforce` case's checks (test/shiploop_e2e/checks/battleship_salesforce.py), run against the fake `sf`.

No test here touches a real org: each puts test/shiploop_e2e/fake_sf.py on PATH as an executable named `sf` in a shim directory and
builds PATH from that directory plus /usr/bin:/bin only, so no other `sf` can be found. The fake refuses every call whose
--target-org is not `de`.

The grader is not trusted either way:
  * MIRROR is a Python copy of the reference engine (test/shiploop_e2e/fixtures/battleship-salesforce-reference), and broken
    variants of it (a fixed fleet, a bent or overlapping ship, an early game over ...). APEX SUBSET translates the few Apex constructs
    the grader's anonymous scripts use to Python and runs each script against an engine, so a script that computes something other
    than what `rules` grades fails here, and the canned answers the fake returns are what a real engine would print.
  * The oracle (grade, fleet_problem) must pass the correct engine on every marker and fail each broken one on the marker that names
    its fault.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
CHECKS = E2E / "checks" / "battleship_salesforce.py"
FAKE = E2E / "fake_sf.py"
REFERENCE = E2E / "fixtures" / "battleship-salesforce-reference"
ENGINE_CLS = REFERENCE / "force-app" / "main" / "default" / "classes" / "SLBattleEngine.cls"
TOKEN = "FAKE-TOKEN-DO-NOT-LOG"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bs = load("battleship_salesforce", CHECKS)
fk = load("fake_sf", FAKE)
sys.path.insert(0, str(E2E))
import run  # noqa: E402

sys.path.remove(str(E2E))

BASE_APEX = list(fk.BASELINE_APEX)
BASE_LWC = list(fk.BASELINE_LWC)
BASE_TYPES = {kind: list(names) for kind, names in fk.BASELINE_TYPES.items()}
REF_CLASSES = ["SLBattleController", "SLBattleEngine", "SLBattleEngineTest", "SLBattleGameTest"]


# --------------------------------------------------------------------------------------------------------------- MIRROR
# The reference engine (SLBattleEngine.cls), line for line in Python: a Park-Miller generator, the fleet in order, one shot at a time.
# `bug` names a broken variant; the oracle must fail each on its own marker.

MODULUS, MULTIPLIER = 2147483647, 48271
NAMES = ["carrier", "battleship", "cruiser", "submarine", "destroyer"]
SIZES = [5, 4, 3, 3, 2]


class InvalidShotException(Exception):
    pass


class Generator:
    def __init__(self, seed):
        self.state = abs(seed or 0) % (MODULUS - 1) + 1

    def below(self, bound: int) -> int:
        self.state = self.state * MULTIPLIER % MODULUS
        return self.state % bound


def place(seed) -> list[dict]:
    random, taken, ships = Generator(seed), set(), []
    for name, size in zip(NAMES, SIZES):
        while True:
            across = random.below(2) == 0
            row = random.below(10 if across else 10 - size + 1)
            col = random.below(10 - size + 1 if across else 10)
            cells = [row * 10 + col + k if across else (row + k) * 10 + col for k in range(size)]
            if not taken & set(cells):
                break
        taken |= set(cells)
        ships.append({"name": name, "size": size, "cells": cells, "hits": 0})
    return ships


def engine(bug: str = "") -> SimpleNamespace:
    """SLBattleEngine and SLBattleController for the APEX SUBSET (the controller delegates, like the reference's)."""
    calls = {"n": 0}

    def fleet(seed):
        if bug == "fixed":
            seed = 1  # ignores the seed
        if bug == "drift":
            calls["n"] += 1
            seed = seed + calls["n"]  # state left by an earlier call changes the fleet
        ships = place(seed)
        if bug == "overlap":  # the cruiser laid over the carrier's first cells
            ships[2]["cells"] = list(ships[0]["cells"][:3])
        if bug == "bent":  # a destroyer laid on a diagonal, clear of the others
            others = {cell for s in ships[:4] for cell in s["cells"]}
            free = next(c for c in range(89) if c % 10 < 9 and c not in others and c + 11 not in others)
            ships[4]["cells"] = [free, free + 11]
        if bug == "short-fleet":  # a consistent fleet of 5, 4, 3, 2, 2: not the standard one
            ships[3]["cells"] = ships[3]["cells"][:2]
            ships[3]["size"] = 2
        if bug == "names":
            for ship in ships:
                ship["name"] = ship["name"].capitalize()
        return ships

    def new_game(seed):
        ships = fleet(seed)
        return json.dumps({"ships": ships, "fired": [], "shots": 0, "shipsLeft": len(ships), "gameOver": False, "lastShot": None})

    def fire(game, row, col):
        if row is None or col is None or not (0 <= row < 10 and 0 <= col < 10):
            if bug == "accepts-outside":
                return game
            raise InvalidShotException("outside")
        state = json.loads(game)
        cell = row * 10 + col
        if cell in state["fired"] and bug != "accepts-repeat":
            raise InvalidShotException("again")
        if state["gameOver"] and bug == "after-over-throws":
            raise InvalidShotException("over")
        state["fired"].append(cell)
        outcome, name, size, afloat = "miss", None, None, 0
        for ship in state["ships"]:
            if cell in ship["cells"]:
                ship["hits"] += 1
                if ship["hits"] == len(ship["cells"]):
                    outcome, name, size = "sunk", ship["name"], len(ship["cells"])
                else:
                    outcome = "hit"
            if ship["hits"] < len(ship["cells"]):
                afloat += 1
        if bug == "hit-on-sink" and outcome == "sunk":
            outcome, name, size = "hit", None, None
        if bug == "ship-on-hit" and outcome == "hit":
            name = "carrier"
        state["shots"] += 0 if bug == "no-count" else 1
        state["shipsLeft"] = afloat
        state["gameOver"] = afloat <= (1 if bug == "early-over" else 0)
        state["lastShot"] = {"row": row, "col": col, "result": outcome, "ship": name, "size": size}
        return json.dumps(state)

    battle = SimpleNamespace(newGame=new_game, fire=fire, InvalidShotException=InvalidShotException)
    return SimpleNamespace(SLBattleEngine=battle, SLBattleController=SimpleNamespace(newGame=new_game, fire=fire))


# ------------------------------------------------------------------------------------------------------------ APEX SUBSET
# Runs the anonymous Apex the check sends, in Python, against an engine. It understands exactly what those scripts use, one statement
# per line: declarations, assignment, a counted loop, try/catch, break, System.debug, the JSON and Math calls, casts to
# Map<String, Object> and List<Object> literals. Anything else raises, so a new construct in a script is added here on purpose.

class TypeException(Exception):
    pass


def apex_text(value) -> str:
    if value is None:
        return "null"
    if value is True or value is False:
        return "true" if value else "false"
    return str(value)


class AStr(str):
    def __add__(self, other):
        return AStr(str(self) + apex_text(other))

    def __radd__(self, other):
        return AStr(apex_text(other) + str(self))


class AList(list):
    def add(self, item) -> None:
        self.append(item)

    def size(self) -> int:
        return len(self)


def cast_map(value):
    if value is None or isinstance(value, dict):
        return value
    raise TypeException("Invalid conversion to Map<String, Object>")


def apex_to_python(script: str) -> str:
    def expr(text: str) -> str:
        lits = []
        text = re.sub(r"'(?:[^'\\]|\\.)*'", lambda m: lits.append("AStr(%s)" % m.group(0)) or "\0%d\0" % (len(lits) - 1), text)
        text = re.sub(r"\(Map<String, Object>\) (.*)", r"cast_map(\1)", text)
        text = text.replace("new List<Object>()", "AList()")
        text = re.sub(r"new List<Object>\{(.*)\}", r"AList([\1])", text)
        text = text.replace("JSON.deserializeUntyped(", "json_untyped(").replace("JSON.serialize(", "json_serialize(")
        text = text.replace("Math.mod(", "apex_mod(")
        text = re.sub(r"(\w+)\.getTypeName\(\)", r"type_name(\1)", text)
        text = re.sub(r"(\w+)\.getMessage\(\)", r"message(\1)", text)
        text = text.replace(" / ", " // ")
        text = re.sub(r"\bnull\b", "None", re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", text)))
        return re.sub(r"\0(\d+)\0", lambda m: lits[int(m.group(1))], text)

    out, depth = [], 0
    for line in (raw.strip() for raw in script.splitlines()):
        if not line:
            continue
        if match := re.fullmatch(r"(?:String|Integer|Boolean|List<Object>|Map<String, Object>) (\w+) = (.*);", line):
            code = "%s = %s" % (match[1], expr(match[2]))
        elif match := re.fullmatch(r"(\w+) = (.*);", line):
            code = "%s = %s" % (match[1], expr(match[2]))
        elif match := re.fullmatch(r"for \(Integer (\w+) = (\d+); \1 < (\d+); \1\+\+\) \{", line):
            code = "for %s in range(%s, %s):" % (match[1], match[2], match[3])
        elif line == "try {":
            code = "try:"
        elif match := re.fullmatch(r"\} catch \(([\w.]+) (\w+)\) \{", line):
            code = "except %s as %s:" % (match[1], match[2])
        elif match := re.fullmatch(r"System\.debug\((.*)\);", line):
            code = "debug(%s)" % expr(match[1])
        elif line == "break;":
            code = "break"
        elif match := re.fullmatch(r"(\w[\w.]*\(.*\));", line):
            code = expr(match[1])
        elif line == "}":
            depth -= 1
            continue
        else:
            raise ValueError("APEX SUBSET cannot translate: " + line)
        depth -= line.startswith("}")
        out.append("    " * depth + code)
        depth += line.endswith("{")
    return "\n".join(out)


def run_script(script: str, apex: SimpleNamespace) -> dict[str, str]:
    """The value of each RESULT marker the script prints (the first print of a marker wins, as in the check's log parsing)."""
    seen: dict[str, str] = {}

    def debug(text) -> None:
        match = re.fullmatch(r"RESULT\|([^|]+)\|(.*)", str(text), re.DOTALL)
        if match:
            seen.setdefault(match[1], match[2])

    exec(apex_to_python(script), {
        "AStr": AStr, "AList": AList, "debug": debug, "cast_map": cast_map, "json_untyped": json.loads,
        "json_serialize": lambda value: json.dumps(value, separators=(",", ":")), "apex_mod": lambda a, b: a % b if a >= 0 else -((-a) % b),
        "type_name": lambda e: type(e).__name__, "message": lambda e: str(e),
        "SLBattleEngine": apex.SLBattleEngine, "SLBattleController": apex.SLBattleController})
    return seen


def outputs_for(apex: SimpleNamespace) -> dict[str, tuple[str, dict[str, str]]]:
    """What each scenario prints against one engine: {scenario: ("", {marker: value})}, the shape bs.grade reads."""
    return {name: ("", run_script(script, apex)) for name, script in bs.scenarios()}


def canned_for(apex: SimpleNamespace) -> dict[str, str]:
    """The fake's FAKE_SF_APEX answers for every marker of every scenario."""
    return {marker: value for _err, seen in outputs_for(apex).values() for marker, value in seen.items()}


def failed_markers(bug: str) -> set[str]:
    return {marker for marker, ok, _detail in bs.grade(outputs_for(engine(bug))) if not ok}


# --------------------------------------------------------------------------------------------------------------- the org

class FakeOrg(unittest.TestCase):
    """A temp dir holding the shim, the fake's state and log, a throwaway HOME and the platform dir."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="battleship-sf-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        sf = self.shim / "sf"
        sf.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, FAKE))
        sf.chmod(sf.stat().st_mode | stat.S_IXUSR)
        self.state_path = self.tmp / "state.json"
        self.log_path = self.tmp / "calls.jsonl"
        self.platform = self.tmp / "platform"
        self.work = self.tmp / "cwd"
        self.work.mkdir()
        (self.tmp / "home").mkdir()
        (self.tmp / "tmpdir").mkdir()
        self.set_state(dict(fk.default_state(), alias="de"))
        self.env = {"PATH": "%s:/usr/bin:/bin" % self.shim, "HOME": str(self.tmp / "home"), "FAKE_SF_STATE": str(self.state_path),
                    "FAKE_SF_LOG": str(self.log_path), "FAKE_SF_ORGS": "de", "E2E_PLATFORM_DIR": str(self.platform),
                    "TMPDIR": str(self.tmp / "tmpdir")}
        self.assertEqual(shutil.which("sf", path=self.env["PATH"]), str(self.shim / "sf"))

    def state(self) -> dict:
        return json.loads(self.state_path.read_text())

    def set_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state))

    def edit(self, **changes) -> None:
        state = self.state()
        state.update(changes)
        self.set_state(state)

    def add(self, apex=(), lwc=(), **types) -> None:
        state = self.state()
        state["apex_classes"] += list(apex)
        state["lwc"] += list(lwc)
        for kind, names in types.items():
            state["types"][kind] += list(names)
        self.set_state(state)

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text().splitlines()] if self.log_path.exists() else []

    def run_check(self, *args: str, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(CHECKS), *args], capture_output=True, text=True,
                              env=dict(self.env, **(env or {})), cwd=str(cwd or self.work), timeout=120)

    def out(self, proc: subprocess.CompletedProcess) -> str:
        return proc.stdout + proc.stderr

    def sf(self, *argv: str, env: dict | None = None, cwd: Path | None = None) -> tuple[int, dict]:
        proc = subprocess.run(["sf", *argv, "--json"], capture_output=True, text=True, env=dict(self.env, **(env or {})),
                              cwd=str(cwd or self.work))
        return proc.returncode, json.loads(proc.stdout)

    def project(self, name: str = "model-project") -> Path:
        project = self.tmp / name
        shutil.rmtree(project, ignore_errors=True)
        shutil.copytree(REFERENCE, project)
        return project

    def deploy_reference(self) -> Path:
        project = self.project()
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["status"]), (0, 0), doc)
        return project

    def assign(self, name: str = "SLBattle_Access") -> dict:
        code, doc = self.sf("org", "assign", "permset", "--name", name, "--target-org", "de")
        self.assertEqual(code, 0, doc)
        return doc

    def snapshot(self) -> None:
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def canned(self, apex: SimpleNamespace | None = None, **override) -> str:
        path = self.tmp / "apex.json"
        values = canned_for(apex or engine())
        values.update(override)
        path.write_text(json.dumps(dict(values, probe="2")))
        return str(path)

    def baseline_again(self) -> None:
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        self.assertEqual({kind: sorted(names) for kind, names in state["types"].items()},
                         {kind: sorted(names) for kind, names in BASE_TYPES.items()})
        self.assertEqual((state["assignments"], state["tab_settings"]), ([], []))


# ----------------------------------------------------------------------------------------------------------------- tests

class TestMirrorOfTheReference(unittest.TestCase):
    """The Python copy of the reference engine, and what the reference's own Apex tests assume of it."""

    def test_the_mirror_uses_the_reference_s_generator_names_and_sizes(self) -> None:
        source = ENGINE_CLS.read_text()
        for literal in ("2147483647L", "48271L", "'carrier', 'battleship', 'cruiser', 'submarine', 'destroyer'", "5, 4, 3, 3, 2",
                        "Math.mod(Math.abs(start), MODULUS - 1) + 1", "Math.mod(seedState * MULTIPLIER, MODULUS)",
                        "random.below(2) == 0", "random.below(across ? GRID : GRID - shipSize + 1)",
                        "random.below(across ? GRID - shipSize + 1 : GRID)"):
            self.assertIn(literal, source)

    def test_every_seed_gives_the_standard_fleet_straight_inside_and_apart(self) -> None:
        for seed in range(1, 201):
            ships = place(seed)
            self.assertEqual([(s["name"], len(s["cells"])) for s in ships], list(zip(NAMES, SIZES)))
            cells = [cell for s in ships for cell in s["cells"]]
            self.assertEqual(len(cells), len(set(cells)), seed)
            for s in ships:
                step = s["cells"][1] - s["cells"][0]
                self.assertIn(step, (1, 10))
                self.assertEqual(s["cells"], [s["cells"][0] + k * step for k in range(len(s["cells"]))])
                if step == 1:
                    self.assertEqual({c // 10 for c in s["cells"]}, {s["cells"][0] // 10})
                self.assertTrue(all(0 <= c < 100 for c in s["cells"]))

    def test_the_seeds_the_reference_test_and_the_grader_compare_give_different_fleets(self) -> None:
        self.assertEqual(place(42), place(42))
        self.assertNotEqual(place(1), place(2))  # SLBattleEngineTest.theSameSeedGivesTheSameFleetAndAnotherSeedAnotherOne
        self.assertNotEqual(place(bs.SEED_A), place(bs.SEED_B))
        self.assertEqual(place(-7), place(7))  # |seed|

    def test_the_mirror_scores_every_marker_of_the_grader(self) -> None:
        verdicts = bs.grade(outputs_for(engine()))
        self.assertEqual([marker for marker, _ok, _detail in verdicts], bs.markers())
        self.assertEqual([marker for marker, ok, detail in verdicts if not ok], [], verdicts)
        self.assertEqual(len(verdicts), 19)


class TestOracle(unittest.TestCase):
    """bs.grade against broken engines: each fails on the marker that names its fault, and only there where it can be told apart."""

    def test_each_broken_engine_fails_on_its_own_marker(self) -> None:
        expected = {
            "fixed": {"seed.different"},
            "drift": {"seed.same"},
            "overlap": {"game_a.hits", "game_a.fleet", "game_b.hits", "game_b.fleet"},
            "bent": {"game_a.fleet", "game_b.fleet"},
            "short-fleet": {"game_a.hits", "game_a.sunk", "game_b.hits", "game_b.sunk"},
            "names": {"game_a.sunk", "game_b.sunk"},
            "hit-on-sink": {"game_a.sunk", "game_a.gameover", "game_a.counts", "game_a.fleet",
                            "game_b.sunk", "game_b.gameover", "game_b.counts", "game_b.fleet"},
            "ship-on-hit": {"game_a.results", "game_b.results"},
            "no-count": {"game_a.counts", "game_b.counts"},
            "early-over": {"game_a.gameover", "game_b.gameover"},
            "accepts-repeat": {"invalid.repeat"},
            "accepts-outside": {"invalid.row", "invalid.col"},
        }
        for bug, markers in expected.items():
            with self.subTest(bug=bug):
                found = failed_markers(bug)
                self.assertTrue(markers <= found, (bug, sorted(markers - found)))
                self.assertFalse(found & {"game_a.start", "game_b.start"}, (bug, sorted(found)))
        # Where the fault cannot hide: the fixed fleet passes everything a single game can show, the bent ship everything but `fleet`.
        self.assertEqual(failed_markers("fixed"), {"seed.different"})
        self.assertEqual(failed_markers("bent"), {"game_a.fleet", "game_b.fleet"})
        self.assertEqual(failed_markers("drift"), {"seed.same"})

    def test_an_engine_that_refuses_shots_after_the_game_is_over_loses_the_whole_game(self) -> None:
        found = failed_markers("after-over-throws")
        for game in ("game_a", "game_b"):
            for mark in bs.GAME_MARKS[1:]:
                self.assertIn("%s.%s" % (game, mark), found)
        verdict = dict((m, d) for m, _ok, d in bs.grade(outputs_for(engine("after-over-throws"))))
        self.assertIn("threw InvalidShotException", verdict["game_a.results"])

    def test_the_fleet_oracle_is_the_geometry_not_the_candidate_s_word(self) -> None:
        def shot(cell, result, ship=None, size=None):
            return {"cell": cell, "result": result, "ship": ship, "size": size}

        def board(*sinks):
            """Every cell a miss except the given ships: (name, cells in row-major order) each sunk at its last cell."""
            result = {(r, c): shot((r, c), "miss") for r in range(10) for c in range(10)}
            for name, cells in sinks:
                for cell in cells[:-1]:
                    result[cell] = shot(cell, "hit")
                result[cells[-1]] = shot(cells[-1], "sunk", name, len(cells))
            return [result[(r, c)] for r in range(10) for c in range(10)]

        good = board(("carrier", [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]), ("battleship", [(2, 0), (3, 0), (4, 0), (5, 0)]),
                     ("cruiser", [(9, 7), (9, 8), (9, 9)]), ("submarine", [(5, 5), (6, 5), (7, 5)]), ("destroyer", [(2, 8), (2, 9)]))
        self.assertEqual(bs.fleet_problem(good), "")
        # Two ships touching end to end in one row are still told apart by where each sank.
        touching = board(("carrier", [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]), ("destroyer", [(0, 5), (0, 6)]))
        self.assertEqual(bs.fleet_problem(touching), "")
        bent = board(("destroyer", [(4, 4), (5, 5)]))
        self.assertIn("no straight run", bs.fleet_problem(bent))
        wrapped = board(("cruiser", [(3, 8), (3, 9), (4, 0)]))  # a row-major run that wraps to the next row is not straight
        self.assertIn("no straight run", bs.fleet_problem(wrapped))
        stray = board(("destroyer", [(2, 8), (2, 9)]))
        stray[55] = shot((5, 5), "hit")  # a hit no sunk ship accounts for
        self.assertIn("not 1 straight ships", bs.fleet_problem(stray))
        lied = board(("destroyer", [(2, 8), (2, 9)]))
        lied[29]["size"] = 3  # says 3 where only 2 cells were hit
        self.assertIn("no straight run", bs.fleet_problem(lied))

    def test_garbage_and_errors_fail_every_marker_without_raising(self) -> None:
        outputs = {name: ("", {}) for name, _script in bs.scenarios()}
        verdicts = bs.grade(outputs)
        self.assertEqual([ok for _m, ok, _d in verdicts], [False] * 19)
        for text in ("not json", "[]", '[["start"]]', "{}", "[[" + "1," * 5 + "1]]", '[["start",0,5,false,true],"x"]'):
            verdicts = bs.grade_game("game_a", text, "")
            first = 1 if text.startswith('[["start",0') else 0  # a good start passes on its own
            for marker, ok, detail in verdicts[first:]:
                self.assertFalse(ok, (text, marker))
                self.assertTrue(detail)
        cut = json.dumps([["start", 0, 5, False, True]] + [["miss", None, None, False, i + 1, 5, i // 10, i % 10] for i in range(40)])
        verdict = dict((m, d) for m, ok, d in bs.grade_game("game_a", cut, ""))
        self.assertIn("40 shots came back, not 100", verdict["game_a.hits"])
        self.assertTrue(all(not ok for _m, ok, _d in bs.grade_game("game_a", None, "Apex error: boom")))

    def test_the_scripts_are_one_anonymous_apex_run_per_scenario_and_read_only_the_keys_the_prompt_names(self) -> None:
        names = [name for name, _script in bs.scenarios()]
        self.assertEqual(names, ["game_a", "game_b", "repeat", "invalid"])
        prompt = json.loads((E2E / "cases.json").read_text())["battleship-salesforce"]["prompt"]
        for name, script in bs.scenarios():
            for key in set(re.findall(r"\.get\('(\w+)'\)", script)):
                self.assertTrue("`%s`" % key in prompt or '"%s"' % key in prompt, (name, key))
            if name != "invalid":
                self.assertIn("for (Integer i = 0; i < 100; i++) {", script)
                self.assertIn("SLBattleController.fire(g, r, c)", script)
                self.assertNotIn("SLBattleEngine", script)  # whole games go through the controller, as the prompt says
            else:
                self.assertNotIn("SLBattleController", script)
                for marker, row, col in bs.INVALID:
                    self.assertIn("SLBattleEngine.fire(g, %d, %d);" % (row, col), script)
        self.assertIn("String warm = SLBattleController.newGame(%d);" % bs.SEED_A, dict(bs.scenarios())["repeat"])


class TestFakeModelsPermissionSets(FakeOrg):
    """What the case adds to the fake: a deployed permission set, its tab settings, assignments and the destructive order."""

    def test_a_deployed_permission_set_its_tab_setting_and_an_assignment_can_be_read_back(self) -> None:
        self.deploy_reference()
        state = self.state()
        self.assertIn("SLBattle_Access", state["types"]["PermissionSet"])
        self.assertEqual(state["permset_refs"]["SLBattle_Access"], {"CustomApplication": ["SLBattle"], "CustomTab": ["SLBattle_Board"],
                                                                     "ApexClass": ["SLBattleController", "SLBattleEngine"]})
        code, doc = self.sf("data", "query", "-q", "SELECT Id, Name FROM PermissionSet WHERE Name = 'SLBattle_Access'", "--target-org", "de")
        (ps,) = doc["result"]["records"]
        code, doc = self.sf("data", "query", "-q", "SELECT Name, Visibility FROM PermissionSetTabSetting WHERE ParentId = '%s'" % ps["Id"],
                            "--target-org", "de")
        self.assertEqual([(r["Name"], r["Visibility"]) for r in doc["result"]["records"]], [("SLBattle_Board", "DefaultOn")])
        assigned = self.assign()
        self.assertEqual(assigned["result"]["successes"], [{"name": fk.USERNAME, "value": "SLBattle_Access"}])
        code, doc = self.sf("data", "query", "-q", "SELECT Id, AssigneeId FROM PermissionSetAssignment WHERE PermissionSetId = '%s'" % ps["Id"],
                            "--target-org", "de")
        self.assertEqual([r["AssigneeId"] for r in doc["result"]["records"]], [state["users"][0]["Id"]])
        code, again = self.sf("data", "query", "-q", "SELECT Id, Name FROM PermissionSet WHERE Name = 'SLBattle_Access'", "--target-org", "de")
        self.assertEqual(again["result"]["records"][0]["Id"], ps["Id"])  # Ids are stable from one query to the next
        self.assertEqual(self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Id FROM PermissionSetAssignment", "--target-org", "de")[1]["name"],
                         "INVALID_TYPE")
        code, doc = self.sf("data", "delete", "record", "--sobject", "PermissionSetAssignment", "--record-id",
                            self.state()["assignments"][0]["Id"], "--target-org", "de")
        self.assertEqual((code, self.state()["assignments"]), (0, []))

    def test_a_destructive_deploy_refuses_an_assigned_permission_set_and_what_a_remaining_one_names(self) -> None:
        self.deploy_reference()
        self.assign()
        manifest = self.tmp / "manifest"
        manifest.mkdir()
        (manifest / "package.xml").write_text(bs.sfc.empty_package_xml())

        def destroy(members: dict, order: tuple) -> tuple[int, dict]:
            (manifest / "destructiveChanges.xml").write_text(bs.sfc.destructive_xml(members, order))
            return self.sf("project", "deploy", "start", "--manifest", str(manifest / "package.xml"), "--post-destructive-changes",
                           str(manifest / "destructiveChanges.xml"), "--target-org", "de")

        everything = {"PermissionSet": ["SLBattle_Access"], "CustomApplication": ["SLBattle"], "CustomTab": ["SLBattle_Board"],
                      "LightningComponentBundle": ["slBattleBoard"], "ApexClass": REF_CLASSES}
        code, doc = destroy(everything, bs.REMOVABLE)
        self.assertEqual(code, 1)
        self.assertIn("assigned to one or more users", json.dumps(doc))
        code, doc = destroy({kind: names for kind, names in everything.items() if kind != "PermissionSet"}, bs.sfc.REMOVABLE)
        self.assertEqual(code, 1)
        self.assertIn("referenced by PermissionSet SLBattle_Access", json.dumps(doc))
        self.assertIn("SLBattle_Access", self.state()["types"]["PermissionSet"])  # all or nothing: nothing went
        self.assertIn("SLBattleEngine", self.state()["apex_classes"])


class TestProject(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="battleship-sf-project-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "p"
        shutil.copytree(REFERENCE, self.root)
        self.base = self.root / "force-app" / "main" / "default"

    def failing(self, part: str) -> None:
        ok, message = bs.do_project("SLBattle", self.root)
        self.assertFalse(ok, message)
        self.assertIn(part, message)

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.base / rel
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_the_reference_passes(self) -> None:
        ok, message = bs.do_project("SLBattle", REFERENCE)
        self.assertTrue(ok, message)
        self.assertIn("tab, app and permission set", message)

    def test_each_missing_class_method_or_exception_fails(self) -> None:
        cases = (("classes/SLBattleEngine.cls", "class InvalidShotException extends Exception", "class Other extends Exception",
                  "defines no InvalidShotException"),
                 ("classes/SLBattleEngine.cls", "public static String fire(", "public String shoot(", "SLBattleEngine.cls declares no static method fire"),
                 ("classes/SLBattleController.cls", "public static String newGame(", "public String start(",
                  "SLBattleController.cls declares no static method newGame"),
                 ("classes/SLBattleController.cls", "@AuraEnabled", "", "has no @AuraEnabled method"))
        for rel, old, new, part in cases:
            with self.subTest(part=part):
                self.setUp()
                self.edit(rel, old, new)
                self.failing(part)

    def test_missing_files_fail_by_name(self) -> None:
        for rel, part in (("classes/SLBattleEngine.cls", "no force-app/**/classes/SLBattleEngine.cls"),
                          ("classes/SLBattleController.cls", "no force-app/**/classes/SLBattleController.cls"),
                          ("lwc/slBattleBoard", "no force-app/**/lwc/slBattleBoard/"),
                          ("tabs/SLBattle_Board.tab-meta.xml", "no force-app/**/tabs/SLBattle_Board.tab-meta.xml"),
                          ("applications/SLBattle.app-meta.xml", "no force-app/**/applications/SLBattle.app-meta.xml"),
                          ("permissionsets/SLBattle_Access.permissionset-meta.xml",
                           "no force-app/**/permissionsets/SLBattle_Access.permissionset-meta.xml")):
            with self.subTest(rel=rel):
                self.setUp()
                target = self.base / rel
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                self.failing(part)
        self.setUp()
        (self.root / "sfdx-project.json").unlink()
        self.failing("sfdx-project.json missing")

    def test_the_board_must_call_the_controller_render_a_grid_and_offer_a_new_game(self) -> None:
        for rel, old, new, part in (
                ("lwc/slBattleBoard/slBattleBoard.js", "@salesforce/apex/SLBattleController.fire", "@salesforce/apex/SLBattleEngine.fire",
                 None),
                ("lwc/slBattleBoard/slBattleBoard.html", "for:each=", "data-each=", None),
                ("lwc/slBattleBoard/slBattleBoard.html", ">New game<", ">Restart<", "no New game control"),
                ("lwc/slBattleBoard/slBattleBoard.js-meta.xml", "<target>lightning__Tab</target>", "<target>lightning__AppPage</target>",
                 "does not expose the lightning__Tab target"),
                ("tabs/SLBattle_Board.tab-meta.xml", "<lwcComponent>slBattleBoard</lwcComponent>", "<lwcComponent>other</lwcComponent>",
                 "shows lwcComponent other"),
                ("applications/SLBattle.app-meta.xml", "<tabs>SLBattle_Board</tabs>", "<tabs>standard-home</tabs>", "lists no <tabs> entry")):
            with self.subTest(rel=rel, old=old):
                self.setUp()
                self.edit(rel, old, new)
                if rel.endswith(".js"):  # newGame still imports the controller: it takes both imports going to fail it
                    self.edit(rel, "@salesforce/apex/SLBattleController.newGame", "@salesforce/apex/SLBattleEngine.newGame")
                    part = "does not import @salesforce/apex/SLBattleController"
                elif part is None:
                    part = "has no for:each or iterator"
                self.failing(part)

    def test_the_permission_set_must_grant_the_app_the_visible_tab_and_both_classes(self) -> None:
        rel = "permissionsets/SLBattle_Access.permissionset-meta.xml"
        for old, new, part in (("<visible>true</visible>", "<visible>false</visible>", "does not make the app SLBattle visible"),
                               ("<visibility>Visible</visibility>", "<visibility>Available</visibility>",
                                "does not make the tab SLBattle_Board Visible"),
                               ("<apexClass>SLBattleEngine</apexClass>", "<apexClass>SLBattleOther</apexClass>", "does not enable class SLBattleEngine"),
                               ("<apexClass>SLBattleController</apexClass>\n        <enabled>true</enabled>",
                                "<apexClass>SLBattleController</apexClass>\n        <enabled>false</enabled>", "does not enable class SLBattleController"),
                               ("<PermissionSet xmlns", "<PermissionSet <broken xmlns", "is not valid XML")):
            with self.subTest(part=part):
                self.setUp()
                self.edit(rel, old, new)
                self.failing(part)

    def test_no_other_metadata_and_every_name_prefixed(self) -> None:
        for rel, part in (("flexipages/SLBattle_Home.flexipage-meta.xml", "other metadata main/default/flexipages/SLBattle_Home.flexipage-meta.xml"),
                          ("permissionsets/Admin_Extra.permissionset-meta.xml",
                           "other metadata main/default/permissionsets/Admin_Extra.permissionset-meta.xml"),
                          ("objects/SLBattle_Game__c/SLBattle_Game__c.object-meta.xml", "other metadata main/default/objects/"),
                          ("profiles/Admin.profile-meta.xml", "other metadata main/default/profiles/Admin.profile-meta.xml"),
                          ("classes/Helper.cls", "class Helper.cls does not start with SLBattle")):
            with self.subTest(rel=rel):
                self.setUp()
                path = self.base / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<x/>")
                self.failing(part)


class TestDeployedAndTests(FakeOrg):
    def test_deployed_finds_every_named_component_and_the_permission_set(self) -> None:
        self.deploy_reference()
        proc = self.run_check("deployed", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("permission set SLBattle_Access", proc.stdout)
        self.assertIn("tab SLBattle_Board", proc.stdout)

    def test_a_missing_permission_set_or_tab_fails_by_name(self) -> None:
        self.deploy_reference()
        state = self.state()
        state["types"]["PermissionSet"].remove("SLBattle_Access")
        state["types"]["CustomTab"].remove("SLBattle_Board")
        self.set_state(state)
        proc = self.run_check("deployed", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PermissionSet SLBattle_Access not found", proc.stdout)
        self.assertIn("CustomTab SLBattle_Board not found", proc.stdout)

    def test_tests_runs_each_test_class_and_needs_the_count(self) -> None:
        self.deploy_reference()
        proc = self.run_check("tests", "--org", "de", "--prefix", "SLBattle", "--min-tests", "8")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        ran = [c["argv"][c["argv"].index("--class-names") + 1] for c in self.calls() if c["argv"][:3] == ["apex", "run", "test"]]
        self.assertEqual(ran, ["SLBattleEngineTest", "SLBattleGameTest"])
        few = self.tmp / "few.json"
        few.write_text(json.dumps({"outcome": "Passed", "testsRan": 3, "failing": 0}))
        proc = self.run_check("tests", "--org", "de", "--prefix", "SLBattle", "--min-tests", "8", env={"FAKE_SF_TESTS": str(few)})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("6 ran, 0 failing, need at least 8", proc.stdout)


class TestAccess(FakeOrg):
    ACCESS = ("access", "--org", "de", "--prefix", "SLBattle")

    def test_the_deployed_and_assigned_permission_set_passes(self) -> None:
        self.deploy_reference()
        self.assign()
        before = len(self.calls())
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("PASS access: permission set SLBattle_Access, tab SLBattle_Board, assignment", proc.stdout)
        commands = {" ".join(c["argv"][:2]) for c in self.calls()[before:]}
        self.assertEqual(commands, {"data query", "org list"})  # read-only
        self.assertNotIn(fk.USERNAME, proc.stdout)  # the user is an identifier: never printed

    def test_without_the_assignment_it_fails(self) -> None:
        self.deploy_reference()
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL permission set SLBattle_Access is assigned to the user org 'de' is logged in as (0 assignments", proc.stdout)

    def test_an_assignment_to_another_user_is_not_the_logged_in_user_s(self) -> None:
        self.deploy_reference()
        state = self.state()
        other = {"Id": fk.record_id("User", "other@example.invalid"), "Username": "other@example.invalid"}
        state["users"].append(other)
        state["assignments"].append({"Id": fk.record_id("PermissionSetAssignment", "x"), "AssigneeId": other["Id"],
                                     "PermissionSetId": fk.record_id("PermissionSet", "SLBattle_Access")})
        self.set_state(state)
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("(1 assignments of it in all)", proc.stdout)

    def test_a_tab_that_is_only_available_fails_and_says_what_it_saw(self) -> None:
        project = self.project()
        rel = project / "force-app" / "main" / "default" / "permissionsets" / "SLBattle_Access.permissionset-meta.xml"
        rel.write_text(rel.read_text().replace("<visibility>Visible</visibility>", "<visibility>Available</visibility>"))
        self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assign()
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL permission set SLBattle_Access makes tab SLBattle_Board visible (tab settings seen: SLBattle_Board=DefaultOff)",
                      proc.stdout)

    def test_a_missing_permission_set_fails_first(self) -> None:
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL permission set SLBattle_Access is not (exactly once) in org 'de'", proc.stdout)

    def test_an_org_list_without_the_user_fails_instead_of_guessing(self) -> None:
        self.deploy_reference()
        self.assign()
        self.edit(users=[])
        proc = self.run_check(*self.ACCESS)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("was not found exactly once (0 rows)", proc.stdout)


class TestRules(FakeOrg):
    RULES = ("rules", "--org", "de")

    def test_the_reference_engine_passes_every_marker_through_the_fake(self) -> None:
        proc = self.run_check(*self.RULES, env={"FAKE_SF_APEX": self.canned()})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(proc.stdout.strip().splitlines()[-1], "rules: 19 of 19 markers passed; failed: none")
        files = [c for c in self.calls() if c["argv"][:2] == ["apex", "run"]]
        self.assertEqual([c["apex_markers"] for c in files], [["game_a"], ["game_b"], ["repeat"],
                                                              ["invalid.repeat", "invalid.row", "invalid.col"]])
        self.assertEqual(list((self.tmp / "tmpdir").iterdir()), [])  # the scripts' folder is removed

    def test_a_broken_engine_fails_with_the_marker_named_last(self) -> None:
        proc = self.run_check(*self.RULES, env={"FAKE_SF_APEX": self.canned(engine("bent"))})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.strip().splitlines()[-1], "rules: 17 of 19 markers passed; failed: game_a.fleet,game_b.fleet")
        self.assertIn("FAIL game_a.fleet: destroyer sank at", proc.stdout)

    def test_an_aura_exception_in_a_whole_game_fails_that_game_and_keeps_the_raw_log(self) -> None:
        canned = self.canned(game_a={"error": "System.LimitException: Can only throw this exception type from VisualForce or Aura context"})
        proc = self.run_check(*self.RULES, env={"FAKE_SF_APEX": canned})
        self.assertEqual(proc.returncode, 1)
        last = proc.stdout.strip().splitlines()[-1]
        self.assertIn("failed: game_a.start,game_a.results", last)
        self.assertIn("seed.same,seed.different", last)  # game_a is the reference for both seed markers
        self.assertIn("Can only throw this exception type", proc.stdout)
        self.assertIn("case game_a", (self.platform / "rules-raw.txt").read_text())

    def test_a_compile_error_or_a_failing_cli_fails_every_marker(self) -> None:
        for env, part in (({"FAKE_SF_APEX": self.canned(game_a={"compileProblem": "Invalid type: SLBattleController"},
                                                        game_b={"compileProblem": "Invalid type: SLBattleController"},
                                                        repeat={"compileProblem": "Invalid type: SLBattleController"},
                                                        **{"invalid.repeat": {"compileProblem": "Invalid type: SLBattleEngine"}})},
                           "compile error"),
                          ({"FAKE_SF_FAIL": "apex"}, "apex run failed on request")):
            with self.subTest(part=part):
                proc = self.run_check(*self.RULES, env=env)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stdout.strip().splitlines()[-1].split(";")[0], "rules: 0 of 19 markers passed")
                self.assertIn(part, proc.stdout)
                self.assertNotIn("Traceback", self.out(proc))

    def test_output_that_is_not_a_game_fails_without_a_traceback(self) -> None:
        proc = self.run_check(*self.RULES, env={"FAKE_SF_APEX": self.canned(game_a="{not json", game_b="[]")})
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("Traceback", self.out(proc))
        self.assertIn("FAIL game_a.start: the game output is not JSON", proc.stdout)


class TestPreflightAndSnapshot(FakeOrg):
    def test_a_clean_org_passes_and_a_prefixed_permission_set_is_refused(self) -> None:
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.add(PermissionSet=["SLBattle_Access"])
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PermissionSet SLBattle_Access", proc.stdout)

    def test_the_snapshot_records_the_permission_sets(self) -> None:
        self.snapshot()
        before = json.loads((self.platform / "before.json").read_text())
        self.assertEqual(before["other_types"]["PermissionSet"], BASE_TYPES["PermissionSet"])
        self.assertEqual(before["prefix"], "SLBattle")


class TestCleanup(FakeOrg):
    CLEAN = ("cleanup", "--org", "de", "--prefix", "SLBattle")

    def deployed_and_assigned(self) -> None:
        self.snapshot()
        self.deploy_reference()
        self.assign()

    def test_the_assignment_then_the_permission_set_then_the_rest_and_the_org_is_its_baseline_again(self) -> None:
        self.deployed_and_assigned()
        start = len(self.calls())
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.baseline_again()
        steps = []
        for call in self.calls()[start:]:
            if call["argv"][:3] == ["data", "delete", "record"]:
                steps.append(("delete", call["argv"][call["argv"].index("--sobject") + 1]))
            elif "destructive" in call:
                steps.append(("destroy", tuple(call["type_order"])))
        self.assertEqual(steps, [("delete", "PermissionSetAssignment"), ("destroy", ("PermissionSet",)),
                                 ("destroy", ("CustomApplication", "CustomTab", "LightningComponentBundle", "ApexClass"))])
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(record["unassigned"], [{"permission_set": "SLBattle_Access", "assignments": 1}])
        self.assertEqual(sorted(r["name"] for r in record["removed"]),
                         sorted(["SLBattle_Access", "SLBattle", "SLBattle_Board", "slBattleBoard", *REF_CLASSES]))
        self.assertIn("unassigned 1", proc.stdout)
        self.assertIn("in this order: the assignments of a new permission set, then PermissionSet, CustomApplication", proc.stdout)

    def test_an_assignment_that_cannot_be_removed_leaves_the_permission_set_and_fails_loudly(self) -> None:
        for env in ({"FAKE_SF_FAIL": "delete"}, {"FAKE_SF_NOOP_DELETE": "1"}):
            with self.subTest(env=env):
                self.set_state(dict(fk.default_state(), alias="de"))
                shutil.rmtree(self.platform, ignore_errors=True)
                self.deployed_and_assigned()
                proc = self.run_check(*self.CLEAN, env=env)
                self.assertEqual(proc.returncode, 1)
                self.assertIn("assigned to one or more users", proc.stdout)
                self.assertIn("extra PermissionSet SLBattle_Access", proc.stdout)
                self.assertIn("CLEANUP FAILED", proc.stderr)
                self.assertFalse(json.loads((self.platform / "cleanup.json").read_text())["verified"])
                # The rest stays too: the fake refuses to remove what the permission set that stayed names.
                self.assertIn("SLBattleEngine", self.state()["apex_classes"])

    def test_without_a_snapshot_nothing_is_deleted_or_unassigned(self) -> None:
        self.deploy_reference()
        self.assign()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no usable", proc.stdout)
        self.assertEqual([c for c in self.calls() if c["argv"][:3] == ["data", "delete", "record"] or "destructive" in c], [])
        self.assertEqual(len(self.state()["assignments"]), 1)

    def test_only_new_exactly_prefixed_permission_sets_lose_their_assignments(self) -> None:
        self.snapshot()
        state = self.state()
        user = state["users"][0]["Id"]
        for name in ("baseChessAccess", "slbattle_lookalike"):  # a baseline one and a look-alike a model could make
            state["assignments"].append({"Id": fk.record_id("PermissionSetAssignment", name), "PermissionSetId": fk.record_id("PermissionSet", name),
                                         "AssigneeId": user})
        state["types"]["PermissionSet"].append("slbattle_lookalike")
        self.set_state(state)
        self.deploy_reference()
        self.assign()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)  # the look-alike is new and not removable: remove by hand
        self.assertIn("new since the snapshot without the exact prefix, so left alone", proc.stdout)
        self.assertIn("PermissionSet slbattle_lookalike", proc.stdout)
        self.assertNotIn("extra PermissionSet slbattle_lookalike", proc.stdout)
        left = {row["PermissionSetId"] for row in self.state()["assignments"]}
        self.assertEqual(left, {fk.record_id("PermissionSet", "baseChessAccess"), fk.record_id("PermissionSet", "slbattle_lookalike")})
        self.assertNotIn("SLBattle_Access", self.state()["types"]["PermissionSet"])
        refused = json.loads((self.platform / "cleanup.json").read_text())["refused"]
        self.assertIn({"type": "PermissionSet", "name": "slbattle_lookalike", "reason": "does not start with the exact prefix SLBattle"}, refused)

    def test_a_permission_set_the_platform_made_on_its_own_fails_the_cleanup_but_is_named_as_not_the_run_s(self) -> None:
        """2026-10-17: during the chess reference rehearsal the org made a permission set of its own (no prefix) between the snapshot
        and the verification. The cleanup still fails closed (the org differs from its snapshot), and says the item was left alone."""
        self.deployed_and_assigned()
        self.add(PermissionSet=["sfdc_platformmade_example"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("org differs from the before snapshot: new since the snapshot without the exact prefix, so left alone", proc.stdout)
        self.assertIn("PermissionSet sfdc_platformmade_example", proc.stdout)
        self.assertNotIn("SLBattle_Access", self.state()["types"]["PermissionSet"])  # the run's own work is gone all the same
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual(record["extra"], {"PermissionSet": ["sfdc_platformmade_example"]})  # the record keeps every extra item

    def test_a_cleanup_with_nothing_to_remove_verifies_and_calls_nothing_destructive(self) -> None:
        self.snapshot()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("unassigned 0; removed nothing", proc.stdout)
        self.assertEqual([c for c in self.calls() if c["argv"][:3] == ["data", "delete", "record"] or "destructive" in c], [])


class TestSelftest(FakeOrg):
    def test_the_probe_rehearses_every_real_cli_step_and_leaves_the_baseline(self) -> None:
        proc = self.run_check("selftest", "--org", "de", env={"FAKE_SF_APEX": self.canned()})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("preflight", "snapshot", "deploy", "deployed", "tests", "assign", "access", "apex-run", "cleanup"):
            self.assertRegex(proc.stdout, r"(?m)^PASS %s(?: \(\d+ s[^)]*\))?: " % step)
        self.assertIn("permission set SLBattle_Probe", proc.stdout)
        self.baseline_again()
        assigned = [c for c in self.calls() if c["argv"][:3] == ["org", "assign", "permset"]]
        self.assertEqual([c["argv"][c["argv"].index("--name") + 1] for c in assigned], ["SLBattle_Probe"])

    def test_the_reference_passes_every_check_and_is_removed(self) -> None:
        proc = self.run_check("selftest", "--org", "de", "--reference", env={"FAKE_SF_APEX": self.canned()})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("fixture", "rules", "access", "cleanup"):
            self.assertRegex(proc.stdout, r"(?m)^PASS %s(?: \(\d+ s[^)]*\))?: " % step)
        self.assertIn("rules: 19 of 19 markers passed", proc.stdout)
        self.baseline_again()

    def test_keep_leaves_the_game_to_play_and_prints_the_cleanup(self) -> None:
        keep = self.tmp / "kept"
        proc = self.run_check("selftest", "--org", "de", "--reference", "--keep", "--platform-dir", str(keep),
                              env={"FAKE_SF_APEX": self.canned()})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("KEPT:", proc.stdout)
        self.assertIn("/lightning/n/SLBattle_Board", proc.stdout)
        self.assertIn("SLBattle_Access", self.state()["types"]["PermissionSet"])
        command = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(command.startswith("python3 %s cleanup --org de --prefix SLBattle --platform-dir " % CHECKS), command)
        proc = self.run_check("cleanup", "--org", "de", "--prefix", "SLBattle", "--platform-dir", str(keep))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.baseline_again()

    def test_a_reference_that_fails_its_tests_does_not_pass_and_is_still_removed(self) -> None:
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 10, "failing": 1}))
        proc = self.run_check("selftest", "--org", "de", "--reference", env={"FAKE_SF_APEX": self.canned(), "FAKE_SF_TESTS": str(results)})
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, r"(?m)^FAIL tests")
        self.assertIn("PASS cleanup:", proc.stdout)
        self.baseline_again()


class TestUpdateMode(FakeOrg):
    """`--existing update` (run.py --platform-existing update): a run that deploys over work an earlier run kept. What is in the org
    at the snapshot is the baseline; the cleanup removes only what the run adds beyond it, and the app that was kept stays."""

    CLEAN = ("cleanup", "--org", "de", "--prefix", "SLBattle")
    UPDATE = ("--org", "de", "--prefix", "SLBattle", "--existing", "update")
    KEPT = ["SLBattle", "SLBattle_Board", "slBattleBoard", "SLBattle_Access", *REF_CLASSES]

    def kept_app(self, assigned: bool = True) -> None:
        """An earlier run's kept app: the reference deployed (and assigned), with the dates of an earlier day."""
        self.deploy_reference()
        if assigned:
            self.assign()
        state = self.state()
        state["dates"] = {kind: {n: d for n, d in names.items() if not n.startswith(("SLBattle", "slBattle"))}
                          for kind, names in state["dates"].items()}
        self.set_state(state)

    def snapshot_update(self) -> subprocess.CompletedProcess:
        proc = self.run_check("snapshot", *self.UPDATE)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        return proc

    def before(self) -> dict:
        return json.loads((self.platform / "before.json").read_text())

    def extra_class(self) -> Path:
        """A project that also holds one class the baseline does not."""
        project = self.project("rerun")
        classes = project / "force-app" / "main" / "default" / "classes"
        (classes / "SLBattleExtra.cls").write_text("public class SLBattleExtra {}\n")
        (classes / "SLBattleExtra.cls-meta.xml").write_text((classes / "SLBattleEngine.cls-meta.xml").read_text())
        return project

    def redeploy(self, project: Path) -> None:
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["status"]), (0, 0), doc)

    def test_preflight_refuses_a_kept_app_by_default_and_accepts_it_in_update_mode(self) -> None:
        self.kept_app()
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("is not clean", proc.stdout)
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle", "--existing", "update")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("update mode:", proc.stdout)
        self.assertIn("PermissionSet SLBattle_Access", proc.stdout)
        # The mode also comes from the environment the harness sets, and a clean org passes in update mode as well.
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle", env={"E2E_PLATFORM_EXISTING": "update"})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.set_state(dict(fk.default_state(), alias="de"))
        proc = self.run_check("preflight", "--org", "de", "--prefix", "SLBattle", "--existing", "update")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("no SLBattle*/slBattle* item", proc.stdout)

    def test_the_snapshot_refuses_a_kept_app_by_default_and_records_it_as_the_baseline_in_update_mode(self) -> None:
        self.kept_app()
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to snapshot a dirty org", proc.stdout)
        self.assertFalse((self.platform / "before.json").exists())
        proc = self.snapshot_update()
        before = self.before()
        self.assertEqual(before["existing"], "update")
        self.assertEqual(sorted(before["baseline_prefixed"]),
                         sorted(["ApexClass " + n for n in REF_CLASSES] + ["LightningComponentBundle slBattleBoard", "CustomTab SLBattle_Board",
                                                                         "CustomApplication SLBattle", "PermissionSet SLBattle_Access"]))
        self.assertEqual(list(before["permset_assignments"]), ["SLBattle_Access"])
        self.assertEqual(len(before["permset_assignments"]["SLBattle_Access"]), 1)
        self.assertIn("update mode: 8 prefixed item(s) are the baseline", proc.stdout)
        self.assertIn("baseline permission sets SLBattle_Access with 1 assignment(s)", proc.stdout)

    def test_a_fresh_snapshot_keeps_the_file_it_has_always_had(self) -> None:
        self.snapshot()
        before = self.before()
        self.assertNotIn("existing", before)
        self.assertNotIn("permset_assignments", before)
        self.assertNotIn("baseline_prefixed", before)

    def test_the_cleanup_keeps_the_kept_app_removes_what_the_run_added_and_reports_what_it_deployed_over(self) -> None:
        self.kept_app(assigned=False)
        self.snapshot_update()
        self.assertEqual(self.before()["permset_assignments"], {"SLBattle_Access": []})
        project = self.extra_class()
        self.redeploy(project)  # the release stage: the baseline classes again, and one the baseline lacks
        self.assign()  # and the permission set assigned to the logged-in user
        self.assertIn("SLBattleExtra", self.state()["apex_classes"])
        self.assertEqual(len(self.state()["assignments"]), 1)
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        state = self.state()
        self.assertNotIn("SLBattleExtra", state["apex_classes"])  # only what the run added went
        self.assertEqual(sorted(n for n in state["apex_classes"] if n.startswith("SLBattle")), sorted(REF_CLASSES))
        self.assertIn("slBattleBoard", state["lwc"])
        self.assertIn("SLBattle_Access", state["types"]["PermissionSet"])
        self.assertIn("SLBattle", state["types"]["CustomApplication"])
        self.assertEqual(state["assignments"], [])  # the assignment the run added to a baseline permission set went too
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(record["existing"], "update")
        self.assertEqual([r["name"] for r in record["removed"]], ["SLBattleExtra"])
        self.assertEqual(record["unassigned"], [{"permission_set": "SLBattle_Access", "assignments": 1, "baseline_permission_set": True}])
        self.assertEqual(sorted(record["updated"]), ["ApexClass", "LightningComponentBundle"])
        self.assertEqual(record["modified"], {})
        self.assertEqual(len(record["baseline_kept"]), 8)
        self.assertIn("update mode: 8 baseline item(s) kept; deployed over in place (not restorable):", proc.stdout)

    def test_a_baseline_assignment_stays_and_a_cleanup_with_nothing_added_removes_nothing(self) -> None:
        self.kept_app(assigned=True)
        self.snapshot_update()
        start = len(self.calls())
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual([c for c in self.calls()[start:] if c["argv"][:3] == ["data", "delete", "record"] or "destructive" in c], [])
        self.assertEqual(len(self.state()["assignments"]), 1)
        self.assertEqual(json.loads((self.platform / "cleanup.json").read_text())["removed"], [])

    def test_the_default_cleanup_of_the_same_org_would_have_removed_the_kept_app(self) -> None:
        """What update mode protects: a fresh snapshot of an org without the app, then the app deployed, is all removed."""
        self.snapshot()
        self.deploy_reference()
        self.assign()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.baseline_again()

    def test_a_baseline_item_the_run_removed_or_a_non_prefixed_one_it_changed_still_fails_the_cleanup(self) -> None:
        self.kept_app()
        self.snapshot_update()
        state = self.state()
        state["apex_classes"].remove("SLBattleGameTest")  # the run deleted a baseline class
        state.setdefault("dates", {}).setdefault("ApexClass", {})["DeveloperEditionUtils"] = fk.DEPLOY_DATE  # and changed one it does not own
        self.set_state(state)
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing since the snapshot: ApexClass SLBattleGameTest", proc.stdout)
        self.assertIn("modified since the snapshot: ApexClass DeveloperEditionUtils", proc.stdout)
        self.assertNotIn("SLBattleEngine (", proc.stdout)

    def test_an_assignment_the_run_added_to_a_baseline_permission_set_that_cannot_be_removed_fails_loudly(self) -> None:
        self.kept_app(assigned=False)
        self.snapshot_update()
        self.assign()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_NOOP_DELETE": "1"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("PermissionSetAssignment", proc.stdout)
        self.assertEqual(len(self.state()["assignments"]), 1)

    def test_an_update_snapshot_without_its_baseline_assignments_is_not_usable_and_nothing_is_deleted(self) -> None:
        self.kept_app(assigned=False)
        self.snapshot_update()
        before = self.before()
        del before["permset_assignments"]
        (self.platform / "before.json").write_text(json.dumps(before))
        self.redeploy(self.extra_class())
        self.assign()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no usable", proc.stdout)
        self.assertEqual([c for c in self.calls() if c["argv"][:3] == ["data", "delete", "record"] or "destructive" in c], [])
        self.assertIn("SLBattleExtra", self.state()["apex_classes"])

    def test_the_mode_is_the_snapshots_not_the_environment_s_when_the_cleanup_runs(self) -> None:
        self.kept_app(assigned=False)
        self.snapshot_update()
        self.redeploy(self.extra_class())
        proc = self.run_check(*self.CLEAN, env={"E2E_PLATFORM_EXISTING": "fresh"})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("SLBattle_Access", self.state()["types"]["PermissionSet"])  # the baseline stayed whatever the environment said

    def test_the_case_lists_the_mode_its_commands_support(self) -> None:
        case = json.loads((E2E / "cases.json").read_text())["battleship-salesforce"]
        self.assertEqual(case["platform"]["existing"], ["update"])
        self.assertEqual(run.validate_platform("battleship-salesforce", case["platform"])["existing"], ["update"])
        for command in ("preflight", "before", "cleanup"):
            self.assertIn("battleship_salesforce.py", case["platform"][command])


class TestModelThroughTheGuard(FakeOrg):
    """What a model does, through the case's own `sf` wrapper (sf_guard.py --permission-sets): deploy, assign, and nothing else."""

    def setUp(self) -> None:
        super().setUp()
        case = json.loads((E2E / "cases.json").read_text())["battleship-salesforce"]
        command = case["platform"]["model_bin"]["sf"].replace("python3", sys.executable, 1)
        self.wrapper = run.write_model_bin({"sf": command}, self.platform, self.tmp / "home")["sf"]
        self.guarded = dict(self.env, E2E_CHECKS=str(E2E / "checks"))

    def model(self, *argv: str, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run([self.wrapper, *argv], capture_output=True, text=True, env=self.guarded, cwd=str(cwd))

    def test_the_prompt_s_deploy_and_assignment_pass_and_access_follows(self) -> None:
        self.snapshot()
        project = self.project()
        done = self.model("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", "--json", cwd=project)
        self.assertEqual(done.returncode, 0, done.stderr)
        done = self.model("org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", "de", "--json", cwd=project)
        self.assertEqual(done.returncode, 0, done.stderr)
        proc = self.run_check("access", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        denied = self.model("org", "assign", "permset", "--name", "Admin_Extra", "--target-org", "de", cwd=project)
        self.assertEqual(denied.returncode, 2)
        self.assertIn("must start with SLBattle", denied.stderr)
        proc = self.run_check("cleanup", "--org", "de", "--prefix", "SLBattle")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.baseline_again()


class TestCaseDefinition(unittest.TestCase):
    """The prompt states what the checks grade; the case carries the platform block the harness needs (cases.json)."""

    def setUp(self) -> None:
        self.cases = json.loads((E2E / "cases.json").read_text())
        self.case = self.cases["battleship-salesforce"]
        self.prompt = self.case["prompt"]

    def test_the_prompt_states_every_convention_the_checks_grade(self) -> None:
        for sentence in (
                "a Salesforce DX project in the current directory", "Developer Edition org with alias `de`",
                "Use `--target-org de` on every `sf` command that talks to the org;", "never run `sf org display`",
                "Name every Apex class `SLBattle...`", "the component `slBattleBoard`",
                "`tabs/SLBattle_Board.tab-meta.xml` that is a Lightning component tab (`<lwcComponent>slBattleBoard</lwcComponent>`",
                "a Lightning app `applications/SLBattle.app-meta.xml` (standard navigation, containing that tab)",
                "a permission set `permissionsets/SLBattle_Access.permissionset-meta.xml`", "`<visibility>Visible</visibility>`",
                "`sf org assign permset --name SLBattle_Access --target-org de`",
                "Create no other metadata (no custom objects, fields, other permission sets, static resources, triggers, profiles, labels, "
                "flows or app pages)", "the current directory itself, not a subfolder",
                "`carrier` (5 cells), `battleship` (4), `cruiser` (3), `submarine` (3) and `destroyer` (2)",
                "every ship lies straight along one row or one column, entirely inside the grid, and no two ships share a cell",
                "`newGame(Integer seed)`", "the same seed always gives the same fleet, in any transaction and however many games came before",
                "two different seeds give different fleets", "`fire(String game, Integer row, Integer col)`",
                "`shots`", "`shipsLeft`", "`gameOver`", "`lastShot`", "`SLBattleEngine.InvalidShotException`",
                "a public exception class you define inside `SLBattleEngine`",
                "After the game is over, a shot at a cell not yet fired at is still accepted: it is a `miss` and `gameOver` stays `true`",
                "`SLBattleController` has `@AuraEnabled public static` methods", "The grader calls `SLBattleController` only with valid shots",
                "fires at a cell when a person clicks it", "has a New game button",
                "`newGame` with a seed, then `fire` once at each of the 100 cells, each game in one anonymous Apex run",
                "at least 8 Apex test methods", "one test class at a time", "inside one transaction",
                "Do not stop until the tests pass in the org."):
            self.assertIn(sentence, self.prompt)
        self.assertIn('{"row": r, "col": c, "result": "miss" | "hit" | "sunk", "ship": name, "size": cells}', self.prompt)

    def test_the_prompt_names_the_standard_fleet_the_oracle_grades(self) -> None:
        for name, size in bs.FLEET.items():
            self.assertIn("`%s` (%d" % (name, size), self.prompt)
        self.assertEqual(sum(bs.FLEET.values()), bs.SHIP_CELLS)

    def test_the_prompt_allows_exactly_the_metadata_the_checks_guard_and_cleanup_handle(self) -> None:
        for folder in bs.SCOPED_META:
            self.assertIn("`%s/SLBattle" % folder, self.prompt)
        self.assertEqual(bs.REMOVABLE[0], "PermissionSet")
        self.assertEqual(bs.expected_names("SLBattle"), {"classes": ["SLBattleEngine", "SLBattleController"], "lwc": ["slBattleBoard"],
                                                         "tabs": ["SLBattle_Board"], "apps": ["SLBattle"], "permsets": ["SLBattle_Access"]})

    def test_the_test_count_the_prompt_asks_for_is_the_one_the_check_requires(self) -> None:
        asked = int(re.search(r"at least (\d+) Apex test methods", self.prompt).group(1))
        required = int(re.search(r"--min-tests (\d+)", next(c for c in self.case["checks"] if " tests " in c)).group(1))
        self.assertEqual((asked, required, bs.CASE_MIN_TESTS), (8, 8, 8))

    def test_the_checks_are_the_five_subcommands_and_exist(self) -> None:
        self.assertEqual([c.split()[2] for c in self.case["checks"]], ["project", "deployed", "tests", "access", "rules"])
        source = CHECKS.read_text()
        for sub in ("project", "deployed", "tests", "access", "rules"):
            self.assertIn('"%s":' % sub, source)

    def test_the_platform_block_is_the_chess_case_s_with_the_battleship_prefix_and_the_permission_sets(self) -> None:
        platform, chess = self.case["platform"], self.cases["chess-salesforce"]["platform"]
        self.assertIs(run.validate_platform("battleship-salesforce", platform), platform)
        run.refuse_unmatched_keep_checks("battleship-salesforce", platform, self.case["checks"])
        self.assertEqual((platform["kind"], platform["org"], platform["prefix"]), ("salesforce", "de", "SLBattle"))
        for key, verb in (("preflight", "preflight"), ("before", "snapshot"), ("cleanup", "cleanup")):
            self.assertRegex(platform[key], r'^python3 "\$E2E_CHECKS/battleship_salesforce\.py" %s +--org de --prefix SLBattle$' % verb)
        self.assertEqual(platform["keep_checks"], ["deployed", "tests", "rules"])
        self.assertEqual(platform["host_allow"], chess["host_allow"])
        self.assertEqual(platform["check_timeout"], chess["check_timeout"])
        self.assertEqual(platform["model_bin"]["sf"], 'python3 "$E2E_CHECKS/sf_guard.py" --org de --prefix SLBattle --permission-sets --')
        for key in ("resume_note", "resume_note_kept"):
            self.assertNotIn("guard", platform[key].lower())
        self.assertIn("assign the permission set again", platform["resume_note"])
        self.assertIn("2026-10-17", platform["source"])
        self.assertIn("developing a battleship game", platform["source"])
        self.assertEqual(self.case["budget"]["seeded_minutes"], 90)
        self.assertEqual(self.case["style"], "hosted-platform")
        self.assertEqual(bs.check_ceiling(), platform["check_timeout"])

    def test_the_prompt_does_not_mention_the_platform_machinery_or_the_reference(self) -> None:
        for word in ("wrapper", "guard", "sf_guard", "model_bin", "harness", "PATH", "reference", "SEED", str(bs.SEED_B)):
            self.assertNotIn(word, self.prompt)


class TestNoCredentialsAnywhere(FakeOrg):
    def test_the_token_never_reaches_any_output_or_file_and_every_call_names_the_org(self) -> None:
        env = {"FAKE_SF_WARN": "1", "FAKE_SF_APEX": self.canned()}
        outputs = [self.run_check("preflight", "--org", "de", env=env), self.run_check("snapshot", "--org", "de", env=env)]
        project = self.deploy_reference()
        self.assign()
        outputs.append(self.run_check("project", "--org", "de", cwd=project, env=env))
        for args in (("deployed",), ("tests", "--min-tests", "8"), ("access",), ("rules",), ("cleanup",), ("selftest",), ("selftest", "--reference")):
            outputs.append(self.run_check(args[0], "--org", "de", *args[1:], env=env))
        self.assertEqual([p.returncode for p in outputs], [0] * len(outputs), [self.out(p) for p in outputs])
        for proc in outputs:
            self.assertNotIn(TOKEN, self.out(proc))
        for path in self.tmp.rglob("*"):
            if path.is_file() and path != self.shim / "sf":
                self.assertNotIn(TOKEN, path.read_text(errors="replace"), str(path))
        calls = self.calls()
        self.assertEqual([c for c in calls if c["argv"][:2] == ["org", "display"] or c["refused"]], [])
        for call in calls:
            if call["argv"] in (["--version"],) or call["argv"][:2] == ["org", "list"]:
                continue
            self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de", call["argv"])
            self.assertIn("--json", call["argv"])


if __name__ == "__main__":
    unittest.main()
