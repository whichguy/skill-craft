#!/usr/bin/env python3
"""Checks and platform hooks for the `battleship-salesforce` E2E case: a single-player Battleship game in Apex with an LWC board,
deployed to a Salesforce Developer Edition org, granted to the logged-in user by a permission set, and removed again afterwards.

The Salesforce plumbing is chess_salesforce.py's, used as a library (loaded by path, so `python3 -I` works): the `sf` calls and
their scrub, the queries, the prefix rules, preflight, snapshot, the comparison with the snapshot, the destructive deploy, the
`deployed` and `tests` checks and the anonymous Apex runner. What is Battleship's lives here: the project and permission-set
checks, `access`, the `rules` oracle, and a cleanup that also removes the run's permission set and its assignments.

Subcommands (all exit 0 on success, 1 otherwise, and print scrubbed one-line reasons):
  preflight  org connected and holding no metadata with the case prefix (chess_salesforce.do_preflight; PermissionSet is watched)
  snapshot   record the org in $E2E_PLATFORM_DIR/before.json (chess_salesforce.do_snapshot)
  cleanup    remove exactly what this run created, in dependency order: first every PermissionSetAssignment of a new
             <prefix>* permission set (`sf data delete record`, one Id at a time), then those permission sets (one destructive
             deploy), then the new <prefix>* items of the other removable types (a second destructive deploy, chess's order); then
             verify the org against the snapshot exactly as the chess case does

preflight and snapshot also take --existing fresh|update (default: $E2E_PLATFORM_EXISTING, which `run.py --platform-existing` sets;
else fresh). `update` is for a run that deploys over work an earlier run kept (the release slice, run.py --seed-at release-plan):
the <prefix>* items already in the org are the baseline instead of a refusal, the snapshot also records the assignments of the
baseline <prefix>* permission sets, and the cleanup (which reads the mode from the snapshot) removes only what the run added beyond
that baseline: new items as always, plus the assignments the run added to a baseline permission set. A baseline <prefix>* class or
bundle the run deployed over is reported as updated in place, not as modified: its earlier version cannot be restored and replacing
it was the run's job. Everything else still has to equal the snapshot.
  project    the Salesforce DX project in the current directory has the files the request names (classes, component, tab, app and
             permission set, all prefixed), the permission set grants what the request says, and nothing else is there
  deployed   the org holds the engine, the controller, a test class, the component, the tab, the app and the permission set
  tests      run the SLBattle*Test classes in the org; all must pass, at least --min-tests of them
  access     read-only: the permission set is in the org, makes the tab visible (PermissionSetTabSetting) and is assigned to the
             user the CLI is logged in as (PermissionSetAssignment)
  rules      independent oracle: harness-owned anonymous Apex plays two whole games (one shot at each of the 100 cells) through
             SLBattleController, plays one seed again, and fires invalid shots at SLBattleEngine; the verdicts are computed here in
             Python from the standard fleet (sizes 5, 4, 3, 3, 2 and their names) and the geometry of the hits, never from the
             candidate's own answers; the last line sums up and names the failed markers
  selftest   rehearsal (real org: main session only): deploy a probe class, test, component, tab, app, app page and permission set,
             test it, assign the permission set, check `access`, run anonymous Apex and remove it all again. `selftest --reference
             [DIR]` deploys the known-good reference project instead and grades it with project, deployed, tests, access and rules;
             with `--keep` (needs `--platform-dir`) it stays in the org to be played and the by-hand cleanup command is printed

Safety: the chess case's rules (chess_salesforce.py docstring) hold here too; every call names `--target-org`, `sf org display` is
never called, output is scrubbed. The cleanup's two extra steps act only on permission sets named with the exact prefix that are
absent from before.json, and only on assignments of those permission sets.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _library():
    """chess_salesforce.py, loaded by path: the checks run as `python3 -I`, which puts no script folder on sys.path."""
    spec = importlib.util.spec_from_file_location("chess_salesforce_library", HERE / "chess_salesforce.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sfc = _library()
SfError, say, tail, scrub, lwc_prefix = sfc.SfError, sfc.say, sfc.tail, sfc.scrub, sfc.lwc_prefix

PREFIX = "SLBattle"
# The standard fleet the request names: the independent oracle of `rules` (never the candidate's own answers).
FLEET = {"carrier": 5, "battleship": 4, "cruiser": 3, "submarine": 3, "destroyer": 2}
GRID = 10
SHIP_CELLS = sum(FLEET.values())  # 17
RESULTS = ("miss", "hit", "sunk")
SEED_A, SEED_B = 7, 20261017  # two seeds the grader plays; the request asks that they give different fleets
# The removal order of this case: the permission set names the app, the tab and the classes, so it goes before them (chess's
# REMOVABLE order after it). Each step is its own call: the assignments, then the permission sets, then the rest.
REMOVABLE = ("PermissionSet",) + sfc.REMOVABLE
# Besides Apex classes and the component the request allows exactly these, each named with the case prefix: folder -> file suffix.
SCOPED_META = {"tabs": ".tab-meta.xml", "applications": ".app-meta.xml", "permissionsets": ".permissionset-meta.xml"}
# PermissionSetTabSetting.Visibility of a tab the permission set makes visible. DefaultOn is the API's value for metadata
# `<visibility>Visible</visibility>` (DefaultOff is Available) as far as the documentation says; not yet seen on the real org, so the
# check also accepts the metadata spelling and prints what it saw.
VISIBLE_TAB = ("DefaultOn", "Visible")
ID_RE = re.compile(r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")


def expected_names(prefix: str) -> dict[str, list[str]]:
    """What the request names, and `deployed` looks for by default."""
    return {"classes": [prefix + "Engine", prefix + "Controller"], "lwc": [lwc_prefix(prefix) + "Board"],
            "tabs": [prefix + "_Board"], "apps": [prefix], "permsets": [prefix + "_Access"]}


def soql_text(value: str) -> str:
    """A SOQL string literal's content: backslash and quote escaped."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


# ------------------------------------------------------------------------------------------------------------- project

def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def grants(path: Path) -> dict[str, list[dict[str, str]]] | None:
    """The child values of each grant element of a permission set file ({"tabSettings": [{"tab": ..., "visibility": ...}], ...});
    None when the file is not XML."""
    try:
        root = ET.fromstring(path.read_bytes())
    except (OSError, ET.ParseError):
        return None
    found: dict[str, list[dict[str, str]]] = {}
    for element in root:
        found.setdefault(local(element.tag), []).append({local(child.tag): (child.text or "").strip() for child in element})
    return found


def permission_set_problems(app: Path, prefix: str) -> list[str]:
    """The permission set the request names, and what it must grant: the app (visible), the tab (Visible), the two classes."""
    name = prefix + "_Access"
    files = [p for p in sorted(app.glob("**/permissionsets/*.permissionset-meta.xml")) if p.name == name + ".permissionset-meta.xml"]
    if not files:
        return ["no force-app/**/permissionsets/%s.permissionset-meta.xml" % name]
    found = grants(files[0])
    if found is None:
        return ["permission set %s is not valid XML" % files[0].name]
    problems = []
    if not any(g.get("application") == prefix and g.get("visible") == "true" for g in found.get("applicationVisibilities", [])):
        problems.append("permission set %s does not make the app %s visible (<applicationVisibilities> <visible>true</visible>)" % (name, prefix))
    if not any(g.get("tab") == prefix + "_Board" and g.get("visibility") == "Visible" for g in found.get("tabSettings", [])):
        problems.append("permission set %s does not make the tab %s_Board Visible (<tabSettings>)" % (name, prefix))
    for klass in (prefix + "Engine", prefix + "Controller"):
        if not any(g.get("apexClass") == klass and g.get("enabled") == "true" for g in found.get("classAccesses", [])):
            problems.append("permission set %s does not enable class %s (<classAccesses>)" % (name, klass))
    return problems


def do_project(prefix: str, root: Path = Path(".")) -> tuple[bool, str]:
    problems = []
    try:
        json.loads((root / "sfdx-project.json").read_text())
    except (OSError, ValueError):
        problems.append("sfdx-project.json missing or not JSON")
    app = root / "force-app"
    classes = sorted(app.glob("**/classes/*.cls")) if app.is_dir() else []
    bundles = sorted(p for p in app.glob("**/lwc/*") if p.is_dir()) if app.is_dir() else []
    problems += ["class %s does not start with %s" % (c.name, prefix) for c in classes if not c.name.startswith(prefix)]
    for role, methods in (("Engine", ("newGame", "fire")), ("Controller", ("newGame", "fire"))):
        found = [c for c in classes if c.name == "%s%s.cls" % (prefix, role)]
        if not found:
            problems.append("no force-app/**/classes/%s%s.cls" % (prefix, role))
            continue
        source = found[0].read_text(errors="replace")
        problems += ["%s%s.cls declares no static method %s" % (prefix, role, m) for m in methods
                     if not re.search(r"\bstatic\b[^;{(]*?\b%s\s*\(" % m, source, re.IGNORECASE)]
        if role == "Engine" and not re.search(r"\bclass\s+InvalidShotException\s+extends\s+Exception\b", source, re.IGNORECASE):
            problems.append("%sEngine.cls defines no InvalidShotException (a class extending Exception)" % prefix)
        if role == "Controller" and not re.search(r"@AuraEnabled\b", source, re.IGNORECASE):
            problems.append("%sController.cls has no @AuraEnabled method" % prefix)
    board = lwc_prefix(prefix) + "Board"
    boards = [b for b in bundles if b.name == board]
    if not boards:
        problems.append("no force-app/**/lwc/%s/" % board)
    else:
        for ext in (".js", ".html"):
            if not list(boards[0].glob("*" + ext)):
                problems.append("lwc/%s has no %s file" % (board, ext))
        script = "\n".join(f.read_text(errors="replace") for f in sorted(boards[0].glob("*.js")))
        markup = "\n".join(f.read_text(errors="replace") for f in sorted(boards[0].glob("*.html")))
        if not re.search(r"""from\s+['"]@salesforce/apex/%sController\.\w+['"]""" % re.escape(prefix), script):
            problems.append("lwc/%s js does not import @salesforce/apex/%sController.<method>" % (board, prefix))
        if "for:each" not in markup and "iterator" not in markup:
            problems.append("lwc/%s html has no for:each or iterator, so it cannot render a grid of cells" % board)
        if not re.search(r"new\s+game", markup + script, re.IGNORECASE):
            problems.append("lwc/%s has no New game control (no `New game` text in its html or js)" % board)
    problems += ["lwc bundle %s does not start with %s" % (b.name, lwc_prefix(prefix)) for b in bundles
                 if not b.name.startswith(lwc_prefix(prefix))]
    if app.is_dir():
        problems += sfc.ui_problems(app, prefix, board, boards)
        problems += permission_set_problems(app, prefix)
        for meta in app.rglob("*-meta.xml"):
            parts = meta.relative_to(app).parts
            allowed = "classes" in parts or "lwc" in parts or (
                len(parts) > 1 and parts[-2] in SCOPED_META and parts[-1].startswith(prefix) and parts[-1].endswith(SCOPED_META[parts[-2]]))
            if not allowed:
                problems.append("other metadata %s (the request allows only Apex classes, the component and the %s* tab, app and "
                                "permission set)" % ("/".join(parts), prefix))
    if problems:
        return False, "; ".join(problems)
    return True, "project ok: %d Apex classes, %d lwc bundles, tab, app and permission set" % (len(classes), len(bundles))


# ------------------------------------------------------------------------------------------------------------ deployed

def do_deployed(org: str, prefix: str, want: dict[str, list[str]], min_test_classes: int = 1) -> tuple[bool, str]:
    """chess_salesforce.do_deployed (classes, bundles, tab, app, test classes) plus the permission set."""
    ok, message = sfc.do_deployed(org, prefix, want["classes"], want["lwc"], min_test_classes, want["tabs"], want["apps"], [])
    held = {n for n in sfc.watched_names(org, sfc.SPEC["PermissionSet"], prefix) if n.startswith(prefix)}
    problems = ([] if ok else [message]) + ["PermissionSet %s not found in org %r" % (n, org) for n in want["permsets"] if n not in held]
    if problems:
        return False, "; ".join(problems)
    return True, "%s; permission set %s" % (message, ", ".join(want["permsets"]) or "-")


# -------------------------------------------------------------------------------------------------------------- access

def org_username(org: str) -> str | None:
    """The user name `sf org list` shows for the alias: the user the CLI is logged in as (never printed)."""
    doc = sfc.need_ok(sfc.sf(["org", "list"], None), "org list")
    for entries in (doc.get("result") or {}).values():
        for entry in entries if isinstance(entries, list) else ():
            if isinstance(entry, dict) and entry.get("alias") == org and entry.get("username"):
                return str(entry["username"])
    return None


def permission_set_id(org: str, name: str) -> str | None:
    rows = [r for r in sfc.records(org, "SELECT Id, Name FROM PermissionSet WHERE Name = '%s'" % soql_text(name), tooling=False)
            if r.get("Name") == name and ID_RE.match(str(r.get("Id") or ""))]
    return rows[0]["Id"] if len(rows) == 1 else None


def do_access(org: str, permset: str, tab: str) -> tuple[bool, list[str]]:
    """Read-only. The three things that make the board open for the logged-in user: the permission set exists, it makes the tab
    visible, and it is assigned to that user. The chess case granted nothing, and its run 2 left the tab hidden (F9, as reported on
    2026-10-17): a new custom tab is hidden until a permission set or profile grants it."""
    lines, ok = [], True

    def mark(good: bool, text: str) -> None:
        nonlocal ok
        ok = ok and good
        lines.append("%s %s" % ("PASS" if good else "FAIL", text))

    ps = permission_set_id(org, permset)
    mark(ps is not None, "permission set %s %s in org %r" % (permset, "is" if ps else "is not (exactly once)", org))
    if ps is None:
        lines.append("FAIL access: the permission set is missing, so the tab and the assignment cannot be checked")
        return False, lines
    settings = sfc.records(org, "SELECT Name, Visibility FROM PermissionSetTabSetting WHERE ParentId = '%s'" % ps, tooling=False)
    seen = ", ".join("%s=%s" % (r.get("Name"), r.get("Visibility")) for r in settings) or "none"
    mark(any(r.get("Name") == tab and r.get("Visibility") in VISIBLE_TAB for r in settings),
         "permission set %s makes tab %s visible (tab settings seen: %s)" % (permset, tab, tail(seen, 300)))
    username = org_username(org)
    users = sfc.records(org, "SELECT Id FROM User WHERE Username = '%s'" % soql_text(username), tooling=False) if username else []
    if len(users) != 1:
        mark(False, "the user org %r is logged in as was not found exactly once (%d rows)" % (org, len(users)))
    else:
        user = str(users[0].get("Id") or "")
        assigned = sfc.records(org, "SELECT Id, AssigneeId FROM PermissionSetAssignment WHERE PermissionSetId = '%s'" % ps, tooling=False)
        mark(any(str(r.get("AssigneeId") or "")[:15] == user[:15] for r in assigned),
             "permission set %s is assigned to the user org %r is logged in as (%d assignments of it in all)" % (permset, org, len(assigned)))
    lines.append("%s access: permission set %s, tab %s, assignment" % ("PASS" if ok else "FAIL", permset, tab))
    return ok, lines


# --------------------------------------------------------------------------------------------------------------- rules

def game_script(name: str, seed: int, warmup: bool = False) -> str:
    """One anonymous Apex that plays a whole game through SLBattleController: newGame(seed), then one shot at each of the 100 cells
    in row-major order. It records, per shot, what the game JSON says (result, ship, size, gameOver, shots, shipsLeft, row, col) and
    prints them all as one JSON array; the verdicts are computed in Python (grade_game). A shot that throws ends the game with an
    `error` entry (an AuraHandledException cannot be caught here, F7.4 of the chess case, so the grader fires only valid shots).
    `warmup` makes one newGame(seed) call first, so a fleet that depends on state left by an earlier call shows up."""
    return "\n".join([
        "List<Object> trail = new List<Object>();",
        *(["String warm = SLBattleController.newGame(%d);" % seed] if warmup else []),
        "String g = SLBattleController.newGame(%d);" % seed,
        "Map<String, Object> st = (Map<String, Object>) JSON.deserializeUntyped(g);",
        "trail.add(new List<Object>{'start', st.get('shots'), st.get('shipsLeft'), st.get('gameOver'), st.get('lastShot') == null});",
        "for (Integer i = 0; i < 100; i++) {",
        "    Integer r = i / 10;",
        "    Integer c = Math.mod(i, 10);",
        "    try {",
        "        g = SLBattleController.fire(g, r, c);",
        "        st = (Map<String, Object>) JSON.deserializeUntyped(g);",
        "        Map<String, Object> ls = (Map<String, Object>) st.get('lastShot');",
        "        trail.add(new List<Object>{ls.get('result'), ls.get('ship'), ls.get('size'), st.get('gameOver'), st.get('shots'), "
        "st.get('shipsLeft'), ls.get('row'), ls.get('col')});",
        "    } catch (Exception e) {",
        "        trail.add(new List<Object>{'error', e.getTypeName() + ': ' + e.getMessage()});",
        "        break;",
        "    }",
        "}",
        "System.debug('RESULT|%s|' + JSON.serialize(trail));" % name, ""])


INVALID = (("invalid.repeat", 0, 0), ("invalid.row", 10, 0), ("invalid.col", 0, -1))


def invalid_script() -> str:
    """One anonymous Apex: after a valid shot at (0, 0), the same cell again, row 10 and column -1 must each throw
    SLBattleEngine.InvalidShotException (any other exception is named in the result)."""
    lines = ["String g = SLBattleEngine.newGame(%d);" % SEED_A, "g = SLBattleEngine.fire(g, 0, 0);"]
    for index, (marker, row, col) in enumerate(INVALID):
        lines += ["String o%d = 'accepted';" % index, "try {", "    SLBattleEngine.fire(g, %d, %d);" % (row, col),
                  "} catch (SLBattleEngine.InvalidShotException e%d) {" % index, "    o%d = 'threw';" % index,
                  "} catch (Exception x%d) {" % index, "    o%d = 'threw ' + x%d.getTypeName();" % (index, index), "}"]
    lines += ["System.debug('RESULT|%s|' + o%d);" % (marker, index) for index, (marker, _r, _c) in enumerate(INVALID)]
    return "\n".join(lines) + "\n"


def scenarios() -> list[tuple[str, str]]:
    """(name, script): one anonymous Apex run each."""
    return [("game_a", game_script("game_a", SEED_A)), ("game_b", game_script("game_b", SEED_B)),
            ("repeat", game_script("repeat", SEED_A, warmup=True)), ("invalid", invalid_script())]


GAME_MARKS = ("start", "results", "hits", "sunk", "gameover", "counts", "fleet")


def markers() -> list[str]:
    """Every marker `rules` grades, in order."""
    return (["%s.%s" % (game, mark) for game in ("game_a", "game_b") for mark in GAME_MARKS]
            + ["seed.same", "seed.different"] + [marker for marker, _r, _c in INVALID])


def number(value) -> int | None:
    """A JSON number with an integer value (3 or 3.0), else None; true and false are not numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        return None
    return int(value)


def decode_game(text: str | None) -> tuple[list[dict] | None, dict | None, str]:
    """(shots, start, why): the game a game script printed. `shots` lists one dict per shot (cell, result, ship, size, over, shots,
    left, row, col) up to the first error; `why` is "" for a complete game of 100 shots, else what is wrong."""
    try:
        rows = json.loads(text) if text is not None else None
    except ValueError:
        return None, None, "the game output is not JSON: %s" % tail(str(text), 120)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list) or rows[0][:1] != ["start"] or len(rows[0]) != 5:
        return None, None, "the game output does not start with the new game's state: %s" % tail(json.dumps(rows), 120)
    start = dict(zip(("shots", "left", "over", "no_last"), rows[0][1:]))
    shots, why = [], ""
    for index, row in enumerate(rows[1:]):
        if isinstance(row, list) and row[:1] == ["error"]:
            why = "shot %d at (%d, %d) threw %s" % (index + 1, index // GRID, index % GRID, tail(str(row[1] if len(row) > 1 else ""), 200))
            break
        if not isinstance(row, list) or len(row) != 8:
            why = "shot %d came back in an unknown shape: %s" % (index + 1, tail(json.dumps(row), 120))
            break
        shots.append(dict(zip(("result", "ship", "size", "over", "shots", "left", "row", "col"), row), cell=(index // GRID, index % GRID)))
    if not why and len(shots) != GRID * GRID:
        why = "%d shots came back, not %d" % (len(shots), GRID * GRID)
    return shots, start, why


def fleet_problem(shots: list[dict]) -> str:
    """Whether the hit cells are the standard fleet laid straight inside the grid without sharing a cell: every sinking shot ends
    a straight run of its ship's size, left along its row or up its column (row-major order fires that cell last), whose other
    cells were plain hits, and one choice of runs covers every hit cell exactly once. "" when it holds."""
    result = {s["cell"]: s["result"] for s in shots}
    hits = {cell for cell, r in result.items() if r in ("hit", "sunk")}
    choices = []
    for s in (s for s in shots if s["result"] == "sunk"):
        size = number(s["size"])
        if size is None or not 1 <= size <= GRID:
            return "the sinking shot at %s reports size %r" % (s["cell"], s["size"])
        row, col = s["cell"]
        runs = []
        for dr, dc in ((0, 1), (1, 0)):
            cells = [(row - dr * k, col - dc * k) for k in range(size)]
            if all(0 <= r < GRID and 0 <= c < GRID for r, c in cells) and all(result[cell] == "hit" for cell in cells[1:]):
                runs.append(frozenset(cells))
        if not runs:
            return "%s sank at %s, but no straight run of %d hit cells ends there" % (s["ship"], s["cell"], size)
        choices.append(runs)

    def cover(index: int, used: frozenset) -> bool:
        if index == len(choices):
            return used == hits
        return any(not (run & used) and cover(index + 1, used | run) for run in choices[index])

    if not cover(0, frozenset()):
        return "the %d hit cells are not %d straight ships that each end where they sank and share no cell" % (len(hits), len(choices))
    return ""


def grade_game(name: str, text: str | None, err: str) -> list[tuple[str, bool, str]]:
    """(marker, passed, detail) for each of GAME_MARKS of one whole game."""
    marks = ["%s.%s" % (name, mark) for mark in GAME_MARKS]
    if err:
        return [(mark, False, err) for mark in marks]
    shots, start, why = decode_game(text)
    if shots is None:
        return [(mark, False, why) for mark in marks]
    out = []
    want_start = {"shots": 0, "left": len(FLEET), "over": False, "no_last": True}
    got_start = {"shots": number(start["shots"]), "left": number(start["left"]), "over": start["over"], "no_last": start["no_last"]}
    out.append((marks[0], got_start == want_start, "new game: shots=%s shipsLeft=%s gameOver=%s lastShot null=%s" % (
        start["shots"], start["left"], start["over"], start["no_last"])))
    if why:
        return out + [(mark, False, why) for mark in marks[1:]]
    bad = next((s for s in shots if s["result"] not in RESULTS
                or (number(s["row"]), number(s["col"])) != s["cell"]
                or (s["result"] != "sunk" and (s["ship"] is not None or s["size"] is not None))), None)
    out.append((marks[1], bad is None, "every shot is miss, hit or sunk at the cell fired, with ship and size only on a sink" if bad is None
                else "shot at %s: result=%r row=%r col=%r ship=%r size=%r" % (bad["cell"], bad["result"], bad["row"], bad["col"],
                                                                              bad["ship"], bad["size"])))
    hit_count = sum(s["result"] in ("hit", "sunk") for s in shots)
    out.append((marks[2], hit_count == SHIP_CELLS, "%d of 100 shots hit (the fleet has %d cells)" % (hit_count, SHIP_CELLS)))
    sunk = [(s["ship"], number(s["size"])) for s in shots if s["result"] == "sunk"]
    names = [ship for ship, _size in sunk]
    good = (len(sunk) == len(FLEET) and Counter(size for _ship, size in sunk) == Counter(FLEET.values())
            and len(set(map(str, names))) == len(names) and all(FLEET.get(ship) == size for ship, size in sunk))
    out.append((marks[3], good, "sunk: %s (the standard fleet: %s)" % (
        ", ".join("%s %s" % pair for pair in sunk) or "none", ", ".join("%s %d" % pair for pair in FLEET.items()))))
    sinks, wrong = 0, None
    for s in shots:
        sinks += s["result"] == "sunk"
        if s["over"] is not (sinks >= len(FLEET)) and wrong is None:
            wrong = s
    out.append((marks[4], wrong is None and sinks == len(FLEET),
                "gameOver is false before the fifth sink and true from it on" if wrong is None and sinks == len(FLEET) else
                "%d sinks; at %s gameOver=%r" % (sinks, wrong["cell"] if wrong else "-", wrong["over"] if wrong else None)))
    sinks, wrong = 0, None
    for index, s in enumerate(shots):
        sinks += s["result"] == "sunk"
        if (number(s["shots"]), number(s["left"])) != (index + 1, len(FLEET) - sinks) and wrong is None:
            wrong = (s, index + 1, len(FLEET) - sinks)
    out.append((marks[5], wrong is None, "shots counts every shot and shipsLeft every ship not yet sunk" if wrong is None else
                "at %s shots=%r shipsLeft=%r, expected %d and %d" % (wrong[0]["cell"], wrong[0]["shots"], wrong[0]["left"], wrong[1], wrong[2])))
    problem = fleet_problem(shots)
    out.append((marks[6], not problem, problem or "the hits are 5 straight ships inside the grid that share no cell"))
    return out


def sequence(text: str | None, err: str) -> tuple[list | None, str]:
    """(result, ship, size) per shot of a whole game, or (None, why)."""
    if err:
        return None, err
    shots, _start, why = decode_game(text)
    if shots is None or why:
        return None, why
    return [(s["result"], s["ship"], number(s["size"])) for s in shots], ""


def grade(outputs: dict[str, tuple[str, dict[str, str]]]) -> list[tuple[str, bool, str]]:
    """Every marker's verdict from what each scenario printed: {scenario: (error text, {marker: value})}."""
    verdicts = []
    for game in ("game_a", "game_b"):
        err, seen = outputs[game]
        verdicts += grade_game(game, seen.get(game), err or ("" if game in seen else "no RESULT line in the debug log"))
    seqs = {}
    for game in ("game_a", "game_b", "repeat"):
        err, seen = outputs[game]
        seqs[game] = sequence(seen.get(game), err or ("" if game in seen else "no RESULT line in the debug log"))
    (a, why_a), (b, why_b), (again, why_again) = seqs["game_a"], seqs["game_b"], seqs["repeat"]
    verdicts.append(("seed.same", a is not None and a == again,
                     "the same seed in another transaction, after one newGame call, gave %s" % (
                         "the same fleet" if a is not None and a == again else why_a or why_again or "a different fleet")))
    verdicts.append(("seed.different", a is not None and b is not None and a != b,
                     "seeds %d and %d gave %s" % (SEED_A, SEED_B, why_a or why_b or (
                         "different fleets" if a != b else "the same fleet"))))
    err, seen = outputs["invalid"]
    for marker, row, col in INVALID:
        got = seen.get(marker)
        verdicts.append((marker, not err and got == "threw", "SLBattleEngine.fire(%d, %d) %s" % (
            row, col, err or ("threw InvalidShotException" if got == "threw" else "gave %s" % (got or "no RESULT line")))))
    return verdicts


def do_rules(org: str, raw_dir: Path | None = None) -> tuple[bool, list[str]]:
    outputs, raw = {}, ""
    work = Path(tempfile.mkdtemp(prefix="battleship-sf-rules-"))
    try:
        for name, script in scenarios():
            err, seen, logs = sfc.run_apex(org, work, name, script)
            outputs[name] = (err, seen)
            if (err or not seen) and not raw:
                raw = "case %s: %s\n%s" % (name, err or "no RESULT line", scrub(logs)[:1024])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    verdicts = grade(outputs)
    failed = [marker for marker, ok, _detail in verdicts if not ok]
    lines = ["%s %s: %s" % ("PASS" if ok else "FAIL", marker, tail(detail, 300)) for marker, ok, detail in verdicts]
    # The harness keeps the last 2000 characters of a check's output, so the verdict and the failed markers come last.
    lines.append("rules: %d of %d markers passed; failed: %s" % (len(verdicts) - len(failed), len(verdicts), ",".join(failed) or "none"))
    if raw and raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "rules-raw.txt").write_text(raw)
    return not failed, lines


# ------------------------------------------------------------------------------------------------------------- cleanup

def do_snapshot(org: str, prefix: str, directory: Path, existing: str = "fresh") -> tuple[bool, str]:
    """chess_salesforce.do_snapshot; in update mode also the Ids of the assignments the baseline <prefix>* permission sets already
    have, which the cleanup must not remove."""
    ok, message = sfc.do_snapshot(org, prefix, directory, existing)
    if not ok or existing != "update":
        return ok, message
    path = directory / "before.json"
    before = json.loads(path.read_text())
    names = [n for n in sfc.recorded_names(before, "PermissionSet") or [] if n.startswith(prefix)]
    before["permset_assignments"] = {name: assignment_ids(org, name) for name in sorted(names)}
    path.write_text(json.dumps(before, indent=2) + "\n")
    held = sum(len(ids) for ids in before["permset_assignments"].values())
    return True, "%s; baseline permission sets %s with %d assignment(s)" % (message, ", ".join(sorted(names)) or "-", held)


def unassign(org: str, name: str, notes: list[str], keep=()) -> int:
    """Delete every assignment of one permission set except the Ids in ``keep``; returns how many went. A failure is a note."""
    removed = 0
    for rid in assignment_ids(org, name):
        if rid in keep:
            continue
        doc = sfc.sf(["data", "delete", "record", "--sobject", "PermissionSetAssignment", "--record-id", rid], org)
        if doc.get("status") == 0:
            removed += 1
        else:
            notes.append("could not remove an assignment of %s: %s" % (name, tail(str(doc.get("message") or doc.get("name") or doc), 200)))
    return removed


def assignment_ids(org: str, permset: str) -> list[str]:
    """The Ids of every PermissionSetAssignment of one permission set (named exactly), whoever it is assigned to."""
    ps = permission_set_id(org, permset)
    if ps is None:
        return []
    rows = sfc.records(org, "SELECT Id FROM PermissionSetAssignment WHERE PermissionSetId = '%s'" % ps, tooling=False)
    return [str(r["Id"]) for r in rows if ID_RE.match(str(r.get("Id") or ""))]


def do_cleanup(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    sfc.check_prefix(prefix)
    record = {"removed": [], "unassigned": [], "refused": [], "verified": False}
    out = directory / "cleanup.json"

    def finish(ok: bool, message: str, **extra) -> tuple[bool, str]:
        record.update(extra, verified=ok)
        directory.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scrub(record), indent=2) + "\n")
        return ok, message

    try:
        before = json.loads((directory / "before.json").read_text())
        if not (all(isinstance(before[key], dict) for key in ("last_modified", "other_types", "unavailable"))
                and all(isinstance(before[key], list) for key in ("apex_classes", "lightning_component_bundles"))):
            raise TypeError("before.json is not a snapshot of this version")
        # An update snapshot is only usable with the baseline assignments it was to record: without them the assignments the run
        # added cannot be told from the ones that were there, and nothing is unassigned.
        if before.get("existing") == "update" and not (isinstance(before.get("permset_assignments"), dict) and all(
                isinstance(ids, list) for ids in before["permset_assignments"].values())):
            raise TypeError("an update snapshot without its baseline assignments")
    except (OSError, ValueError, KeyError, TypeError):
        return finish(False, "no usable %s: refusing to delete anything because the run's new metadata cannot be told apart"
                      % (directory / "before.json"), error="missing before.json")
    update = before.get("existing") == "update"
    apex_found, lwc_found = sfc.loose(org, prefix)
    found = {"ApexClass": apex_found, "LightningComponentBundle": lwc_found}
    for kind in REMOVABLE:
        if kind not in found:
            found[kind] = sfc.queryable_names(org, sfc.SPEC[kind], sfc.removal_prefix(kind, prefix))[0] or []
    plan = {}
    for kind in REMOVABLE:
        recorded = sfc.recorded_names(before, kind)
        if recorded is None:
            plan[kind], refused = [], [(n, sfc.NOT_QUERYABLE) for n in sorted(set(found[kind]))]
        else:
            plan[kind], refused = sfc.plan_removal(found[kind], set(recorded), sfc.removal_prefix(kind, prefix))
        record["refused"] += [{"type": kind, "name": n, "reason": why} for n, why in refused]
    notes = []
    # 1. The assignments: a permission set that is assigned to a user cannot be deleted.
    for name in plan["PermissionSet"]:
        try:
            record["unassigned"].append({"permission_set": name, "assignments": unassign(org, name, notes)})
        except SfError as exc:
            notes.append("assignments of %s: %s" % (name, exc))
    # Update mode: a baseline permission set stays, so only the assignments the run added to it go.
    baseline_assignments = before["permset_assignments"] if update else {}
    for name, was in sorted(baseline_assignments.items()):
        if not name.startswith(sfc.removal_prefix("PermissionSet", prefix)):
            continue
        try:
            record["unassigned"].append({"permission_set": name, "assignments": unassign(org, name, notes, keep=set(was)),
                                         "baseline_permission_set": True})
        except SfError as exc:
            notes.append("assignments of %s: %s" % (name, exc))
    # 2. The permission sets, which name the app, the tab and the classes; 3. everything else, in the chess case's order.
    for kinds in (("PermissionSet",), sfc.REMOVABLE):
        members = {kind: plan[kind] for kind in kinds}
        if any(members.values()):
            note = sfc.destructive_deploy(org, members, kinds)
            if note:
                notes.append(note)
            else:
                record["removed"] += [{"type": kind, "name": n} for kind in kinds for n in members[kind]]
    try:
        now = sfc.read_org(org)
    except SfError as exc:
        return finish(False, "%s; could not verify afterwards: %s" % ("; ".join(notes) or "cleanup ran", exc), error=str(exc))
    diff = sfc.compare(before, now, {kind: sfc.removal_prefix(kind, prefix) for kind in sfc.OWN_TYPES} if update else None)
    for r in record["refused"]:
        if r["reason"] == sfc.NOT_QUERYABLE:
            diff["extra"].setdefault(r["type"], []).append(r["name"])
    for name, was in sorted(baseline_assignments.items()):  # the baseline permission sets' assignments must be the baseline's again
        try:
            held = set(assignment_ids(org, name))
        except SfError as exc:
            diff["unverified"]["PermissionSetAssignment " + name] = str(exc)
            continue
        if held - set(was):
            diff["extra"].setdefault("PermissionSetAssignment", []).extend(sorted(held - set(was)))
        if set(was) - held:
            diff["missing"].setdefault("PermissionSetAssignment", []).extend(sorted(set(was) - held))
    record.update({key: diff[key] for key in ("extra", "missing", "modified", "unverified", "covered", "not_covered")})
    if update:
        record["existing"] = "update"
        record["updated"] = diff["updated"]
        record["baseline_kept"] = [{"type": r["type"], "name": r["name"]} for r in record["refused"] if r["reason"] == "was already in the before snapshot"]
    if notes:
        record["notes"] = notes
    if any(diff[key] for key in ("extra", "missing", "modified", "unverified")):
        # A new item without the exact prefix was never this cleanup's to remove (the platform makes some permission sets on its own,
        # 2026-10-17): it still fails the cleanup, but is named apart so it is not read as one the cleanup failed to delete.
        foreign, ours = [], {}
        for kind, names in diff["extra"].items():
            theirs = [n for n in names if kind in REMOVABLE and not n.startswith(sfc.removal_prefix(kind, prefix))]
            foreign += ["%s %s" % (kind, n) for n in theirs]
            if len(theirs) < len(names):
                ours[kind] = [n for n in names if n not in theirs]
        shown = dict(diff, extra=ours)  # the record keeps every extra item; only the message names the foreign ones apart
        parts = [part for part in (sfc.describe(shown, REMOVABLE), "new since the snapshot without the exact prefix, so left alone (the "
                                   "platform makes some on its own; remove by hand any that a person or the model made): " + ", ".join(foreign)
                                   if foreign else "") if part]
        return finish(False, "%sorg differs from the before snapshot: %s" % ("; ".join(notes) + "; " if notes else "", "; ".join(parts)))
    removed = ["%s %s" % (r["type"], r["name"]) for r in record["removed"]]
    unassigned = sum(r["assignments"] for r in record["unassigned"])
    kept = ("; update mode: %d baseline item(s) kept%s" % (len(record["baseline_kept"]), "; deployed over in place (not restorable): " + ", ".join(
        "%s %s" % (kind, n) for kind, names in diff["updated"].items() for n in names) if diff["updated"] else "")) if update else ""
    return finish(True, "cleanup verified: org %r matches the before snapshot by name on %s; LastModifiedDate unchanged on %d baseline "
                  "ApexClass and LightningComponentBundle items; removes when new and prefixed (%s*, %s* for bundles), in this order: "
                  "the assignments of a new permission set, then %s; only compares, never removes: %s%s; unassigned %d; removed %s" % (
                      org, ", ".join("%s %d" % (kind, n) for kind, n in diff["covered"].items()), diff["dates_checked"],
                      prefix, lwc_prefix(prefix), ", ".join(REMOVABLE),
                      ", ".join(kind for kind in diff["covered"] if kind not in REMOVABLE) or "-",
                      "; not covered (query failed at the snapshot): " + ", ".join(diff["not_covered"]) if diff["not_covered"] else "",
                      unassigned, ", ".join(removed) or "nothing") + kept)


# ------------------------------------------------------------------------------------------------------------ selftest

REFERENCE = HERE.parent / "fixtures" / "battleship-salesforce-reference"
CASES = HERE.parent / "cases.json"
CASE = "battleship-salesforce"
CASE_MIN_TESTS = 8  # the --min-tests of the case's `tests` check; a test holds the two together


def check_ceiling() -> int | None:
    """The seconds the harness gives each of this case's checks (cases.json, platform.check_timeout); None when it cannot be read."""
    try:
        return int(json.loads(CASES.read_text())[CASE]["platform"]["check_timeout"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def probe_permission_set(names: dict[str, str]) -> str:
    """The probe's permission set: the probe app visible, the probe tab Visible, the probe class enabled."""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<PermissionSet xmlns="%s">\n'
            "    <applicationVisibilities>\n        <application>%s</application>\n        <visible>true</visible>\n"
            "    </applicationVisibilities>\n    <classAccesses>\n        <apexClass>%s</apexClass>\n        <enabled>true</enabled>\n"
            "    </classAccesses>\n    <hasActivationRequired>false</hasActivationRequired>\n    <label>%s</label>\n"
            "    <tabSettings>\n        <tab>%s</tab>\n        <visibility>Visible</visibility>\n    </tabSettings>\n</PermissionSet>\n"
            % (sfc.META_NS, names["app"], names["class"], names["permset"], names["tab"]))


def write_probe(root: Path, prefix: str) -> dict[str, str]:
    """chess_salesforce.write_probe (class, test, component, tab, app, app page) plus a permission set granting them."""
    names = dict(sfc.write_probe(root, prefix), permset=prefix + "_Probe")
    folder = root / "force-app" / "main" / "default" / "permissionsets"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (names["permset"] + ".permissionset-meta.xml")).write_text(probe_permission_set(names))
    return names


def assign(org: str, permset: str) -> tuple[bool, str]:
    """What the request tells the model to run after its deploy: assign the permission set to the logged-in user."""
    doc = sfc.sf(["org", "assign", "permset", "--name", permset], org, timeout=300)
    result = doc.get("result") or {}
    failures = result.get("failures") or []
    ok = doc.get("status") == 0 and not failures
    return ok, "status=%s successes=%d failures=%s" % (doc.get("status"), len(result.get("successes") or []),
                                                        tail(json.dumps(failures), 300) if failures else "none")


def do_selftest(org: str, prefix: str, reference: Path | None = None, keep: bool = False, platform: Path | None = None) -> bool:
    if keep and platform is None:
        raise ValueError("keep needs a platform folder that outlives the run")
    work = Path(tempfile.mkdtemp(prefix="battleship-sf-selftest-"))
    snap = platform if keep else work / "platform"
    snapped, deployed, all_ok, ceiling = False, False, True, check_ceiling()

    def step(name: str, ok: bool, message: str, seconds: float | None = None) -> bool:
        took = "" if seconds is None else " (%d s%s)" % (round(seconds), " of the case's %d s check ceiling" % ceiling if ceiling else "")
        say("%s %s%s: %s" % ("PASS" if ok else "FAIL", name, took, message))
        return ok

    try:
        say("selftest proves, in order: %spreflight, snapshot, deploy (%s together), deployed, tests, assign (`org assign permset` "
            "gives the permission set to the logged-in user), access (the permission set makes the tab visible and is assigned, read "
            "back by query), %s, %s" % (
                "fixture (the reference project passes `project`, offline), " if reference else "",
                "the reference project's classes, component, tab, app and permission set" if reference else
                "a class with an @AuraEnabled method, its test, a component, a tab, an app, an app page and a permission set",
                "rules (the graded oracle, two whole games included, runs against it)" if reference else
                "apex-run (anonymous Apex calls the class and its RESULT line is parsed from result.logs exactly as `rules` does)",
                "kept (nothing is removed; the by-hand cleanup command is printed)" if keep else
                "cleanup (the assignment, then the permission set, then the rest are removed and the org equals its baseline)"))
        project = work / "project"
        if reference is not None:
            if not reference.is_dir():
                step("fixture", False, "the reference project %s does not exist" % reference)
                return False
            shutil.copytree(reference, project, ignore=shutil.ignore_patterns(".sf", ".sfdx", ".git", "node_modules"))
            ok, msg = do_project(prefix, project)
            if not step("fixture", ok, msg if ok else "the reference project %s is incomplete: %s" % (reference, msg)):
                return False
        ok, msg = sfc.do_preflight(org, prefix)
        if not step("preflight", ok, msg):
            return False
        ok, msg = sfc.do_snapshot(org, prefix, snap)
        snapped = ok
        if not step("snapshot", ok, msg):
            return False
        if reference is None:
            names = write_probe(project, prefix)
            want = {"classes": [names["class"], names["test"]], "lwc": [names["bundle"]], "tabs": [names["tab"]],
                    "apps": [names["app"]], "permsets": [names["permset"]]}
            permset, tab = names["permset"], names["tab"]
        else:
            want = expected_names(prefix)
            permset, tab = want["permsets"][0], want["tabs"][0]
        doc = sfc.sf(["project", "deploy", "start", "--source-dir", "force-app", "--wait", "10"], org, timeout=900, cwd=str(project))
        result = doc.get("result") or {}
        failures = "; ".join("%s %s: %s" % (f.get("componentType"), f.get("fullName"), tail(str(f.get("problem") or ""), 200))
                             for f in ((result.get("details") or {}).get("componentFailures") or [])[:5])
        deployed = step("deploy", doc.get("status") == 0 and result.get("success") is not False,
                        "status=%s %s" % (result.get("status"), failures or (tail(str(doc.get("message") or "")) if doc.get("status") != 0 else "")))
        if not deployed:
            return False
        (ok, msg), took = sfc.timed(do_deployed, org, prefix, want, 1)
        all_ok &= step("deployed", ok, msg, took)
        (ok, lines), took = sfc.timed(sfc.do_tests, org, prefix, CASE_MIN_TESTS if reference else 1)
        all_ok &= step("tests", ok, "; ".join(lines), took)
        ok, msg = assign(org, permset)
        all_ok &= step("assign", ok, msg)
        (ok, lines), took = sfc.timed(do_access, org, permset, tab)
        all_ok &= step("access", ok, "; ".join(lines), took)
        if reference is None:
            err, seen, _log = sfc.run_apex(org, work, "probe", sfc.probe_script(names["class"]))
            got = seen.get("probe")
            all_ok &= step("apex-run", not err and got == "2",
                           "RESULT|probe| expected=2 got=%s" % (got if got is not None else (err or "no RESULT line")))
        else:
            (ok, lines), took = sfc.timed(do_rules, org, platform)
            all_ok &= step("rules", ok, lines[-1], took)
            for line in lines[:-1]:
                say("    " + line)
        return all_ok
    except SfError as exc:
        step("selftest", False, str(exc))
        return False
    finally:
        cleanup_failed = False
        if snapped and keep and deployed:
            kept = snap.resolve()
            say("KEPT: nothing was removed from org %r; the %s app stays there to play (App Launcher: %s, or /lightning/n/%s_Board). "
                "The snapshot that cleanup needs is in %s. Remove everything by hand when you are done:\npython3 %s cleanup --org %s "
                "--prefix %s --platform-dir %s" % (org, prefix, prefix, prefix, kept, Path(__file__).resolve(), org, prefix, kept))
        elif snapped:
            try:
                ok, msg = do_cleanup(org, prefix, snap)
            except BaseException as exc:  # cleanup must report, even when interrupted
                ok, msg = False, "cleanup raised %s" % type(exc).__name__
            step("cleanup", ok, msg)
            if not ok:
                cleanup_failed = True
                say("MANUAL CLEANUP NEEDED: remove the assignments of the %s* permission sets, then the %s* and %s* items (%s) from "
                    "org %r (destructive deploys of exactly those names)." % (prefix, prefix, lwc_prefix(prefix), ", ".join(REMOVABLE), org))
        shutil.rmtree(work, ignore_errors=True)
        if cleanup_failed:
            raise SystemExit(1)


# -------------------------------------------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="battleship_salesforce.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("preflight", "snapshot", "cleanup", "project", "deployed", "tests", "access", "rules", "selftest"):
        p = sub.add_parser(name)
        p.add_argument("--org", required=name not in ("project",))
        p.add_argument("--prefix", default=PREFIX)
        p.add_argument("--platform-dir")
        if name in ("preflight", "snapshot"):
            p.add_argument("--existing", choices=sfc.EXISTING_MODES, default=os.environ.get("E2E_PLATFORM_EXISTING") or "fresh")
        if name == "deployed":
            for option in ("classes", "lwc", "tabs", "apps", "permsets"):
                p.add_argument("--" + option)
            p.add_argument("--min-test-classes", type=int, default=1)
        if name == "tests":
            p.add_argument("--min-tests", type=int, default=1)
        if name == "access":
            p.add_argument("--permission-set")
            p.add_argument("--tab")
        if name == "selftest":
            p.add_argument("--reference", nargs="?", const=str(REFERENCE))
            p.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "preflight":
            ok, msg = sfc.do_preflight(args.org, args.prefix, args.existing)
        elif args.cmd == "snapshot":
            ok, msg = do_snapshot(args.org, args.prefix, sfc.platform_dir(args.platform_dir), args.existing)
        elif args.cmd == "cleanup":
            ok, msg = do_cleanup(args.org, args.prefix, sfc.platform_dir(args.platform_dir))
            if not ok:
                say("CLEANUP FAILED. Remove the run's %s* permission set assignments and %s*/%s* metadata from org %r by hand, or rerun: "
                    "python3 battleship_salesforce.py cleanup --org %s --prefix %s" % (args.prefix, args.prefix, lwc_prefix(args.prefix),
                                                                                      args.org, args.org, args.prefix), sys.stderr)
        elif args.cmd == "project":
            ok, msg = do_project(args.prefix)
        elif args.cmd == "deployed":
            want = {option: sfc.csv(getattr(args, option)) if getattr(args, option) is not None else default
                    for option, default in expected_names(args.prefix).items()}
            ok, msg = do_deployed(args.org, args.prefix, want, args.min_test_classes)
        elif args.cmd == "tests":
            ok, lines = sfc.do_tests(args.org, args.prefix, args.min_tests)
            msg = "\n".join(lines)
        elif args.cmd == "access":
            names = expected_names(args.prefix)
            ok, lines = do_access(args.org, args.permission_set or names["permsets"][0], args.tab or names["tabs"][0])
            msg = "\n".join(lines)
        elif args.cmd == "rules":
            raw_dir = args.platform_dir or os.environ.get("E2E_PLATFORM_DIR")
            ok, lines = do_rules(args.org, Path(raw_dir) if raw_dir else None)
            msg = "\n".join(lines)
        else:
            if args.keep and not args.reference:
                parser.error("--keep needs --reference")
            if args.keep and not args.platform_dir:
                parser.error("--keep needs --platform-dir (a durable folder; the snapshot cleanup needs later must not live in $TMPDIR)")
            return 0 if do_selftest(args.org, args.prefix, Path(args.reference) if args.reference else None, args.keep,
                                    Path(args.platform_dir) if args.platform_dir else None) else 1
    except SfError as exc:
        say("FAIL %s: %s" % (args.cmd, exc))
        return 1
    say(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
