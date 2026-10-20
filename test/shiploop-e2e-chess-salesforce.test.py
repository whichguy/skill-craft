#!/usr/bin/env python3
"""The `chess-salesforce` case's checks (test/shiploop_e2e/checks/chess_salesforce.py), run against the fake `sf`.

No test here touches a real org: each puts test/shiploop_e2e/fake_sf.py on PATH as an executable named `sf` in a shim directory
and builds PATH from that directory plus /usr/bin:/bin only, so no other `sf` can be found (a test proves it). The fake refuses
every call whose --target-org is not `de`, so a check that fell back on the default org would fail loudly.

The oracle's expected answers are not trusted: a small independent move generator (REFERENCE, below) re-derives every perft count, each
game's plies and statuses and every literal answer, so a mistyped FEN, count or move in the check fails here instead of failing a run.
The Apex scripts are not trusted either: APEX SUBSET translates the few Apex constructs they use to Python and runs each script against
the REFERENCE, so a script that computes something other than the answer the check expects fails here too.
"""

from __future__ import annotations

import html
import importlib.util
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
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
CHECKS = E2E / "checks" / "chess_salesforce.py"
FAKE = E2E / "fake_sf.py"
TOKEN = "FAKE-TOKEN-DO-NOT-LOG"

spec = importlib.util.spec_from_file_location("chess_salesforce", CHECKS)
cs = importlib.util.module_from_spec(spec)
sys.modules["chess_salesforce"] = cs
spec.loader.exec_module(cs)
spec = importlib.util.spec_from_file_location("fake_sf", FAKE)
fk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fk)

BASE_APEX = list(fk.BASELINE_APEX)
BASE_LWC = list(fk.BASELINE_LWC)
BASE_TYPES = {kind: list(names) for kind, names in fk.BASELINE_TYPES.items()}


# ------------------------------------------------------------------------------------------------------------ REFERENCE
# An independent chess move generator, written for this suite only (pure Python, no packages): pseudo-legal moves, castling, en
# passant, promotion, legality by king safety. It shares no code or data with the check, so the two agree only when both are right.

KNIGHT = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
KING = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
RAYS = {"B": KING[1::2], "R": KING[0::2], "Q": KING}


def ref_sq(text: str) -> tuple[int, int]:
    return "abcdefgh".index(text[0]), int(text[1]) - 1


def ref_name(square: tuple[int, int]) -> str:
    return "abcdefgh"[square[0]] + str(square[1] + 1)


def ref_parse(fen: str):
    placement, side, castling, ep, half, full = fen.split(" ")
    board = {}
    for rank, row in enumerate(placement.split("/")):
        file = 0
        for ch in row:
            if ch.isdigit():
                file += int(ch)
            else:
                board[(file, 7 - rank)] = ch
                file += 1
    return board, side == "w", "" if castling == "-" else castling, None if ep == "-" else ref_sq(ep), int(half), int(full)


def ref_fen(board, white, castling, ep, half, full) -> str:
    rows = []
    for rank in range(7, -1, -1):
        row, gap = "", 0
        for file in range(8):
            piece = board.get((file, rank))
            row, gap = (row + (str(gap) if gap else "") + piece, 0) if piece else (row, gap + 1)
        rows.append(row + (str(gap) if gap else ""))
    return "%s %s %s %s %d %d" % ("/".join(rows), "w" if white else "b", castling or "-", ref_name(ep) if ep else "-", half, full)


def ref_attacked(board, target, by_white: bool) -> bool:
    tf, tr = target
    own = (lambda piece: piece) if by_white else (lambda piece: piece.lower())
    if any(board.get((tf + df, tr - 1 if by_white else tr + 1)) == own("P") for df in (-1, 1)):
        return True
    if any(board.get((tf + df, tr + dr)) == own(kind) for kind, offsets in (("N", KNIGHT), ("K", KING)) for df, dr in offsets):
        return True
    for kinds, rays in (("BQ", RAYS["B"]), ("RQ", RAYS["R"])):
        for df, dr in rays:
            f, r = tf + df, tr + dr
            while 0 <= f < 8 and 0 <= r < 8 and (f, r) not in board:
                f, r = f + df, r + dr
            if (f, r) in board and board[(f, r)] in [own(k) for k in kinds]:
                return True
    return False


def ref_make(board, frm, to, promo, ep):
    after = dict(board)
    piece = after.pop(frm)
    if piece.upper() == "P" and to == ep and to not in board:
        after.pop((to[0], frm[1]))
    if piece.upper() == "K" and abs(to[0] - frm[0]) == 2:
        rook_from, rook_to = (7, 5) if to[0] == 6 else (0, 3)
        after[(rook_to, frm[1])] = after.pop((rook_from, frm[1]))
    after[to] = (promo.upper() if piece.isupper() else promo) if promo else piece
    return after


def ref_pseudo(board, white: bool, castling: str, ep):
    for frm, piece in list(board.items()):
        if piece.isupper() != white:
            continue
        kind, (f, r) = piece.upper(), frm
        if kind == "P":
            step, home, last = (1, 1, 7) if white else (-1, 6, 0)
            tos = [(f, r + step)] if (f, r + step) not in board else []
            if tos and r == home and (f, r + 2 * step) not in board:
                tos.append((f, r + 2 * step))
            tos += [t for t in ((f - 1, r + step), (f + 1, r + step)) if t == ep or (t in board and board[t].isupper() != white)]
            for to in tos:
                for promo in ("q", "r", "b", "n") if to[1] == last else (None,):
                    yield frm, to, promo
            continue
        if kind in "NK":
            tos = [(f + df, r + dr) for df, dr in (KNIGHT if kind == "N" else KING)]
        else:
            tos = []
            for df, dr in RAYS[kind]:
                t = (f + df, r + dr)
                while 0 <= t[0] < 8 and 0 <= t[1] < 8:
                    tos.append(t)
                    if t in board:
                        break
                    t = (t[0] + df, t[1] + dr)
        for to in tos:
            if 0 <= to[0] < 8 and 0 <= to[1] < 8 and (to not in board or board[to].isupper() != white):
                yield frm, to, None
        if kind == "K" and frm == (4, 0 if white else 7) and not ref_attacked(board, frm, not white):
            for flag, rook, between, passes, dest in (("K", 7, (5, 6), (5, 6), 6), ("Q", 0, (1, 2, 3), (3, 2), 2)):
                if (flag if white else flag.lower()) in castling and board.get((rook, r)) == ("R" if white else "r") \
                        and all((b, r) not in board for b in between) and not any(ref_attacked(board, (p, r), not white) for p in passes):
                    yield frm, (dest, r), None


def ref_legal(fen: str) -> list[str]:
    board, white, castling, ep, _half, _full = ref_parse(fen)
    out = []
    for frm, to, promo in ref_pseudo(board, white, castling, ep):
        after = ref_make(board, frm, to, promo, ep)
        if not ref_attacked(after, next(sq for sq, piece in after.items() if piece == ("K" if white else "k")), not white):
            out.append(ref_name(frm) + ref_name(to) + (promo or ""))
    return sorted(out)


def ref_apply(fen: str, move: str) -> str:
    board, white, castling, ep, half, full = ref_parse(fen)
    assert move in ref_legal(fen), "%s is not legal in %s" % (move, fen)
    frm, to, promo = ref_sq(move[:2]), ref_sq(move[2:4]), move[4:] or None
    for square, flags in (((4, 0), "KQ"), ((4, 7), "kq"), ((7, 0), "K"), ((0, 0), "Q"), ((7, 7), "k"), ((0, 7), "q")):
        if square in (frm, to):
            castling = "".join(c for c in castling if c not in flags)
    pawn = board[frm].upper() == "P"
    double = (frm[0], (frm[1] + to[1]) // 2) if pawn and abs(to[1] - frm[1]) == 2 else None  # set after every double push, capturable or not
    return ref_fen(ref_make(board, frm, to, promo, ep), not white, castling, double, 0 if pawn or to in board else half + 1,
                   full + (0 if white else 1))


def ref_status(fen: str) -> str:
    board, white, *_ = ref_parse(fen)
    in_check = ref_attacked(board, next(sq for sq, piece in board.items() if piece == ("K" if white else "k")), not white)
    if ref_legal(fen):
        return "check" if in_check else "ongoing"
    return "checkmate" if in_check else "stalemate"


def ref_perft(fen: str, depth: int) -> int:
    moves = ref_legal(fen)
    return len(moves) if depth == 1 else sum(ref_perft(ref_apply(fen, m), depth - 1) for m in moves)


def ref_play(moves: list[str]) -> str:
    fen = cs.START
    for move in moves:
        fen = ref_apply(fen, move)
    return fen


# ------------------------------------------------------------------------------------------------------------ APEX SUBSET
# Runs the anonymous Apex the check sends, in Python, against the REFERENCE. It understands exactly what those scripts use, one
# statement per line: declarations, `+=`, for-each and counted loops, if/else, try/catch, break, System.debug and calls on the engine
# and the controller. Anything else raises, so a new construct in a script is added here on purpose.

class AStr(str):
    """An Apex String: `+` joins by converting to text, split() returns a list."""
    def __add__(self, other):
        return AStr(str(self) + str(other))

    def __radd__(self, other):
        return AStr(str(other) + str(self))

    def split(self, sep=None, maxsplit=-1):
        return AList(AStr(part) for part in str.split(self, sep))


class AList(list):
    def size(self):
        return len(self)

    def contains(self, item):
        return item in self


class IllegalMoveException(Exception):
    pass


def apex_to_python(script: str) -> str:
    def expr(text: str) -> str:
        lits = []  # string literals are set aside so no rewrite touches their text
        text = re.sub(r"'(?:[^'\\]|\\.)*'", lambda m: lits.append("AStr(%s)" % m.group(0)) or "\0%d\0" % (len(lits) - 1), text)
        text = re.sub(r"new List<String>\{([^}]*)\}", r"AList([\1])", text)
        text = text.replace("String.join(", "join(").replace("&&", " and ").replace("||", " or ")
        text = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", re.sub(r"!(?!=)", " not ", text)))
        return re.sub(r"\0(\d+)\0", lambda m: lits[int(m.group(1))], text)

    out, depth = [], 0
    for line in (raw.strip() for raw in script.splitlines()):
        if match := re.fullmatch(r"(?:String|Integer|Boolean|List<String>) (\w+) = (.*);|(\w+) (\+?=) (.*);", line):
            name, op, rhs = (match[1], "=", match[2]) if match[1] else (match[3], match[4], match[5])
            code = "%s %s %s" % (name, op, expr(rhs))
        elif match := re.fullmatch(r"for \(\w+ (\w+) : (.*)\) \{", line):
            code = "for %s in %s:" % (match[1], expr(match[2]))
        elif match := re.fullmatch(r"for \(Integer (\w+) = (\d+); \1 < (.*); \1\+\+\) \{", line):
            code = "for %s in range(%s, %s):" % (match[1], match[2], expr(match[3]))
        elif match := re.fullmatch(r"if \((.*)\) \{", line):
            code = "if %s:" % expr(match[1])
        elif match := re.fullmatch(r"\} catch \(([\w.]+) (\w+)\) \{", line):
            code = "except %s as %s:" % (match[1], match[2])
        elif match := re.fullmatch(r"System\.debug\((.*)\);", line):
            code = "debug(%s)" % expr(match[1])
        elif match := re.fullmatch(r"(.*);", line):
            code = "break" if line == "break;" else expr(match[1])
        elif line in ("try {", "} else {"):
            code = "try:" if line == "try {" else "else:"
        elif line != "}":
            raise ValueError("APEX SUBSET cannot translate: " + line)
        else:
            depth -= 1
            continue
        depth -= line.startswith("}")
        out.append("    " * depth + code)
        depth += line.endswith("{")
    return "\n".join(out)


def run_apex_script(script: str, **classes) -> dict[str, str]:
    """The value of each RESULT marker the script prints (the first print of a marker wins, as in the check's log parsing)."""
    seen = {}

    def debug(text) -> None:
        match = re.fullmatch(r"RESULT\|([^|]+)\|(.*)", str(text), re.DOTALL)
        if match:
            seen.setdefault(match[1], match[2])

    exec(apex_to_python(script), {"AStr": AStr, "AList": AList, "debug": debug, "join": lambda items, sep: AStr(str(sep).join(items)),
                                  **classes})
    return seen


def reference_engine() -> SimpleNamespace:
    """What SLChessEngine and SLChessController answer, from the REFERENCE; an illegal move raises like the engine does."""
    def apply(fen: str, move: str) -> AStr:
        if move not in ref_legal(fen):
            raise IllegalMoveException(move)
        return AStr(ref_apply(fen, move))

    return SimpleNamespace(startFen=lambda: AStr(cs.START), legalMoves=lambda fen: AList(AStr(m) for m in ref_legal(fen)), applyMove=apply,
                           status=lambda fen: AStr(ref_status(fen)), IllegalMoveException=IllegalMoveException)


def step_line(name: str, ok: bool = True) -> str:
    """A regex for one line of a rehearsal: deployed, tests and rules carry their seconds between the step name and the colon."""
    return r"(?m)^%s %s(?: \(\d+ s[^)]*\))?: " % ("PASS" if ok else "FAIL", name)


class FakeOrg(unittest.TestCase):
    """A temp dir holding the shim, the fake's state and log, a throwaway HOME and the platform dir."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="chess-sf-test-")).resolve()
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
        self.set_state(dict(fk.default_state(), alias="de"))
        self.env = {
            "PATH": "%s:/usr/bin:/bin" % self.shim, "HOME": str(self.tmp / "home"), "FAKE_SF_STATE": str(self.state_path),
            "FAKE_SF_LOG": str(self.log_path), "FAKE_SF_ORGS": "de", "E2E_PLATFORM_DIR": str(self.platform),
            "TMPDIR": str(self.tmp / "tmpdir"),
        }
        (self.tmp / "tmpdir").mkdir()
        # The only `sf` any check can resolve is the shim: the real CLI's directory is not on this PATH.
        self.assertEqual(shutil.which("sf", path=self.env["PATH"]), str(self.shim / "sf"))

    # state of the fake org
    def state(self) -> dict:
        return json.loads(self.state_path.read_text())

    def set_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state))

    def add(self, apex=(), lwc=(), **types) -> None:
        """Put names in the fake org: Apex classes, bundles and, by keyword, any other type (FlexiPage=["SLChessHome"])."""
        state = self.state()
        state["apex_classes"] += list(apex)
        state["lwc"] += list(lwc)
        for kind, names in types.items():
            state["types"][kind] += list(names)
        self.set_state(state)

    def edit(self, **changes) -> None:
        """Set top-level keys of the fake org's state (org_buckets, query_errors, ...)."""
        state = self.state()
        state.update(changes)
        self.set_state(state)

    def set_date(self, kind: str, name: str, date: str) -> None:
        state = self.state()
        state["dates"].setdefault(kind, {})[name] = date
        self.set_state(state)

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text().splitlines()] if self.log_path.exists() else []

    def deploys(self, destructive: bool | None = None) -> list[dict]:
        out = [c for c in self.calls() if c["argv"][:3] == ["project", "deploy", "start"]]
        if destructive is not None:
            out = [c for c in out if ("destructive" in c) == destructive]
        return out

    def destroyed(self, call: dict) -> dict:
        """The members a destructive deploy named, by type, without the types it did not name."""
        return {kind: names for kind, names in call["destructive"].items() if names}

    def run_check(self, *args: str, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(CHECKS), *args], capture_output=True, text=True,
                              env=dict(self.env, **(env or {})), cwd=str(cwd or self.work), timeout=120)

    def out(self, proc: subprocess.CompletedProcess) -> str:
        return proc.stdout + proc.stderr

    def sf(self, *argv: str, env: dict | None = None, cwd: Path | None = None) -> tuple[int, dict]:
        """A model-style call to the fake through the shim; returns the exit code and the parsed JSON."""
        proc = subprocess.run(["sf", *argv, "--json"], capture_output=True, text=True, env=dict(self.env, **(env or {})),
                              cwd=str(cwd or self.work))
        return proc.returncode, json.loads(proc.stdout)

    def deploy_classes(self, *names: str) -> None:
        project = self.tmp / "model-project"
        shutil.rmtree(project, ignore_errors=True)
        (project / "force-app" / "main" / "default" / "classes").mkdir(parents=True)
        for name in names:
            (project / "force-app" / "main" / "default" / "classes" / (name + ".cls")).write_text("public class %s {}" % name)
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["status"]), (0, 0), doc)

    def snapshot(self) -> None:
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def before(self) -> dict:
        return json.loads((self.platform / "before.json").read_text())


class TestShim(FakeOrg):
    def test_the_only_sf_on_the_path_is_the_fake(self) -> None:
        found = shutil.which("sf", path=self.env["PATH"])
        self.assertEqual(found, str(self.shim / "sf"))
        self.assertIn("fake_sf.py", Path(found).read_text())

    def test_the_fake_refuses_the_default_org_and_other_aliases(self) -> None:
        for extra in ([], ["--target-org", "prod"]):
            proc = subprocess.run(["sf", "data", "query", "--use-tooling-api", "-q", "SELECT COUNT() FROM ApexClass", "--json", *extra],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(json.loads(proc.stdout)["status"], 1)
        self.assertTrue(all(c["refused"] for c in self.calls()))


class TestFakeMirrorsTheRealCli(FakeOrg):
    """The checks are only as good as the fake: it answers the way the real CLI was measured to (COMMON facts of the fix batch and
    docs/e2e-salesforce-chess-evidence)."""

    def test_the_default_org_is_the_measured_baseline(self) -> None:
        state = self.state()
        self.assertEqual(state["apex_classes"], ["DeveloperEditionUtils", "DeveloperEditionUtilsTest", "PostInstallScript", "PostInstallScriptTest"])
        self.assertEqual((len(state["lwc"]), "chess" in state["lwc"]), (13, True))  # a baseline bundle is named `chess`
        self.assertEqual({kind: len(names) for kind, names in state["types"].items() if names},
                         {"FlexiPage": 16, "CustomTab": 12, "CustomApplication": 37, "CustomObject": 1, "PermissionSet": 1})

    def test_org_list_puts_the_org_under_other_and_also_under_nonscratch_like_the_real_cli(self) -> None:
        code, doc = self.sf("org", "list")
        buckets = {bucket: [entry["alias"] for entry in entries] for bucket, entries in doc["result"].items()}
        self.assertEqual((code, buckets["other"], buckets["nonScratchOrgs"]), (0, ["de"], ["de"]))
        self.assertEqual([buckets[b] for b in ("scratchOrgs", "sandboxes", "devHubs")], [[], [], []])
        self.edit(org_buckets=["other"])
        self.assertEqual(self.sf("org", "list")[1]["result"]["nonScratchOrgs"], [])

    def test_version_is_one_plain_line_without_json_or_an_org(self) -> None:
        proc = subprocess.run(["sf", "--version"], capture_output=True, text=True, env=self.env)
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, fk.VERSION))
        self.assertRegex(proc.stdout, r"^@salesforce/cli/\d+\.\d+\.\d+ \S+ node-v\S+\n$")
        self.assertEqual(self.calls()[-1]["argv"], ["--version"])

    def test_each_type_is_queried_the_way_it_was_measured_to_work(self) -> None:
        for kind, tooling in (("ApexClass", True), ("FlexiPage", True), ("CustomTab", True), ("StaticResource", False), ("PermissionSet", False)):
            right, wrong = ("--use-tooling-api",), ()
            if not tooling:
                right, wrong = wrong, right
            code, doc = self.sf("data", "query", *right, "-q", "SELECT Id FROM " + kind, "--target-org", "de")
            self.assertEqual((kind, code, doc["status"]), (kind, 0, 0), doc)
            code, doc = self.sf("data", "query", *wrong, "-q", "SELECT Id FROM " + kind, "--target-org", "de")
            self.assertEqual((kind, code, doc["name"]), (kind, 1, "INVALID_TYPE"))

    def test_last_modified_dates_are_answered_and_a_deploy_moves_only_what_it_deploys(self) -> None:
        def dates() -> dict:
            _code, doc = self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name, LastModifiedDate FROM ApexClass", "--target-org", "de")
            return {r["Name"]: r["LastModifiedDate"] for r in doc["result"]["records"]}

        self.assertEqual(dates(), {name: fk.BASE_DATE for name in BASE_APEX})
        self.deploy_classes("PostInstallScript", "SLChessEngine")
        self.assertEqual(dates()["PostInstallScript"], fk.DEPLOY_DATE)
        self.assertEqual(dates()["SLChessEngine"], fk.DEPLOY_DATE)
        self.assertEqual(dates()["DeveloperEditionUtils"], fk.BASE_DATE)

    def test_a_permission_set_query_keeps_only_those_no_profile_owns(self) -> None:
        code, doc = self.sf("data", "query", "-q", "SELECT Name FROM PermissionSet WHERE IsOwnedByProfile = false", "--target-org", "de")
        self.assertEqual((code, [r["Name"] for r in doc["result"]["records"]]), (0, BASE_TYPES["PermissionSet"]))

    def test_apex_run_returns_the_documented_log_shape_and_the_source_echo_is_not_a_result(self) -> None:
        script = self.tmp / "a.apex"
        script.write_text("Integer x = 1;\nSystem.debug('RESULT|probe|' + x);\n")
        canned = self.tmp / "canned.json"
        canned.write_text(json.dumps({"probe": "1"}))
        _code, doc = self.sf("apex", "run", "--file", str(script), "--target-org", "de", env={"FAKE_SF_APEX": str(canned)})
        result = doc["result"]
        self.assertEqual((result["success"], result["compiled"], result["line"], result["column"]), (True, True, -1, -1))
        log = result["logs"].splitlines()
        self.assertRegex(log[0], r"^\d+\.\d APEX_CODE,")
        self.assertIn("Execute Anonymous: System.debug('RESULT|probe|' + x);", log)
        debug = [line for line in log if "|USER_DEBUG|" in line]
        self.assertEqual(len(debug), 1)
        self.assertRegex(debug[0], r"^\d\d:\d\d:\d\d\.\d \(\d+\)\|USER_DEBUG\|\[\d+\]\|DEBUG\|RESULT&#124;probe&#124;1$")  # the real CLI escapes pipes
        self.assertTrue(any("|CODE_UNIT_STARTED|" in line for line in log))
        self.assertEqual(cs.RESULT_LINE.findall(html.unescape(result["logs"])), [("probe", "1")])  # the echo line also says RESULT|probe|

    def test_a_type_can_be_made_to_fail_like_an_edition_without_the_object(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        self.assertEqual(self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ExternalString", "--target-org", "de")[0], 1)
        self.assertEqual(self.sf("data", "query", "--use-tooling-api", "-q", "SELECT DeveloperName FROM FlexiPage", "--target-org", "de")[0], 0)

    def test_only_a_not_supported_message_looks_like_a_missing_object_any_other_failure_is_plain(self) -> None:
        self.edit(query_errors={"FlexiPage": "Request timed out, please retry", "ExternalString": "sObject type 'ExternalString' is not supported."})
        names = {}
        for kind, field in (("FlexiPage", "DeveloperName"), ("ExternalString", "Name")):
            code, doc = self.sf("data", "query", "--use-tooling-api", "-q", "SELECT %s FROM %s" % (field, kind), "--target-org", "de")
            names[kind] = (code, doc["name"])
        self.assertEqual(names, {"FlexiPage": (1, "QueryFailed"), "ExternalString": (1, "INVALID_TYPE")})

    def test_a_deploy_creates_the_tab_app_and_page_it_holds_and_a_destructive_deploy_removes_them(self) -> None:
        project = self.tmp / "ui-project"
        base = project / "force-app" / "main" / "default"
        for folder, name in (("tabs", "SLChess_Board.tab-meta.xml"), ("applications", "SLChess.app-meta.xml"),
                             ("flexipages", "SLChess_Home.flexipage-meta.xml")):
            (base / folder).mkdir(parents=True)
            (base / folder / name).write_text("<x/>")
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["result"]["numberComponentsDeployed"]), (0, 3))
        state = self.state()
        self.assertEqual((state["types"]["CustomTab"][-1], state["types"]["CustomApplication"][-1], state["types"]["FlexiPage"][-1]),
                         ("SLChess_Board", "SLChess", "SLChess_Home"))
        manifest = self.tmp / "manifest"
        manifest.mkdir()
        (manifest / "package.xml").write_text(cs.empty_package_xml())
        (manifest / "destructiveChanges.xml").write_text(cs.destructive_xml(
            {"CustomApplication": ["SLChess"], "CustomTab": ["SLChess_Board"], "FlexiPage": ["SLChess_Home"]}))
        code, _doc = self.sf("project", "deploy", "start", "--manifest", str(manifest / "package.xml"),
                             "--post-destructive-changes", str(manifest / "destructiveChanges.xml"), "--target-org", "de")
        self.assertEqual(code, 0)
        self.assertEqual(self.state()["types"], BASE_TYPES)
        (call,) = self.deploys(destructive=True)
        self.assertEqual(call["type_order"], ["CustomApplication", "CustomTab", "FlexiPage"])


class TestParsing(unittest.TestCase):
    def test_parse_json_skips_leading_warning_text(self) -> None:
        text = ' \u203a   Warning: update {x} available.\n{"status": 0, "result": {"a": 1}}\n'
        self.assertEqual(cs.parse_json(text), {"status": 0, "result": {"a": 1}})
        self.assertIsNone(cs.parse_json("no json here"))
        self.assertEqual(cs.parse_json('{"status": 0}'), {"status": 0})

    def test_scrub_replaces_secret_keys_and_token_shapes(self) -> None:
        token = "00D5g0000012345AAA!AQEAQabcdefghijklmnopqrstuvwxyz0123456789"
        self.assertNotIn(token, cs.scrub("header " + token + " trailer"))
        self.assertEqual(cs.scrub("x " + token), "x [redacted]")
        doc = {"result": {"accessToken": TOKEN, "list": [{"refreshToken": "r", "clientSecret": "c", "sfdxAuthUrl": "force://a:b@c", "ok": 1}]}}
        scrubbed = cs.scrub(doc)
        self.assertEqual(scrubbed["result"]["accessToken"], "[redacted]")
        self.assertEqual(scrubbed["result"]["list"][0], {"refreshToken": "[redacted]", "clientSecret": "[redacted]",
                                                         "sfdxAuthUrl": "[redacted]", "ok": 1})
        raw = json.dumps(doc)
        self.assertNotIn(TOKEN, cs.scrub(raw))
        self.assertNotIn("force://a:b@c", cs.scrub("url force://a:b@c done"))
        self.assertEqual(cs.scrub("plain text"), "plain text")

    def test_the_component_prefix_is_the_camel_case_spelling_of_the_apex_prefix(self) -> None:
        self.assertEqual([cs.lwc_prefix(p) for p in ("SLChess", "Chess", "SL", "chess")], ["slChess", "chess", "sl", "chess"])

    def test_plan_removal_refuses_look_alikes_and_snapshot_members(self) -> None:
        remove, refused = cs.plan_removal(["SLChessEngine", "slchessEvil", "AccountTriage", "SLChessKeep", "SLChess Bad", "SLChessA-b"],
                                          {"SLChessKeep"}, "SLChess")
        self.assertEqual(remove, ["SLChessEngine"])
        self.assertEqual({n for n, _ in refused}, {"slchessEvil", "AccountTriage", "SLChessKeep", "SLChess Bad", "SLChessA-b"})
        self.assertEqual(cs.plan_removal(["slChessBoard", "SLChessBoard"], set(), "slChess")[0], ["slChessBoard"])

    def test_destructive_xml_lists_exactly_the_members_and_no_wildcard(self) -> None:
        xml = cs.destructive_xml({"ApexClass": ["SLChessEngine", "SLChessEngineTest"], "LightningComponentBundle": ["slChessBoard"]})
        self.assertIn("<members>SLChessEngine</members>", xml)
        self.assertIn("<members>slChessBoard</members>", xml)
        self.assertNotIn("*", xml)
        self.assertNotIn("<types>", cs.empty_package_xml())

    def test_the_destructive_manifest_lists_what_refers_to_something_before_it(self) -> None:
        xml = cs.destructive_xml({"ApexClass": ["SLChessProbe", "SLChessProbeTest"], "LightningComponentBundle": ["slChessProbe"],
                                  "CustomTab": ["SLChess_Probe"], "CustomApplication": ["SLChess_Probe"], "FlexiPage": ["SLChess_Probe"]})
        order = ["CustomApplication", "CustomTab", "FlexiPage", "LightningComponentBundle", "ApexClass"]
        self.assertEqual(sorted(order, key=lambda kind: xml.index("<name>%s</name>" % kind)), order)  # an app lists tabs, a tab shows the component
        self.assertEqual(xml.count("<types>"), 5)
        self.assertEqual(cs.destructive_xml({"ApexClass": ["SLChessProbe"], "CustomTab": []}).count("<types>"), 1)  # a type with no members is not named
        self.assertEqual(cs.REMOVABLE, tuple(order))


class TestPreflight(FakeOrg):
    def args(self, org: str = "de") -> tuple[str, ...]:
        return ("preflight", "--org", org, "--prefix", "SLChess")

    def test_clean_org_passes_and_writes_nothing(self) -> None:
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertFalse(self.platform.exists())
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertEqual(self.state()["apex_classes"], BASE_APEX)

    def test_the_warning_line_before_the_json_is_skipped(self) -> None:
        proc = self.run_check(*self.args(), env={"FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def test_prefixed_apex_class_fails(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessEngine", self.out(proc))
        self.assertIn("not clean", self.out(proc))

    def test_prefixed_component_fails(self) -> None:
        self.add(lwc=["slChessBoard"])
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("slChessBoard", self.out(proc))

    def test_a_look_alike_with_another_case_is_not_the_prefix(self) -> None:
        self.add(apex=["slchessOld", "SLCHESSOld"], lwc=["SLChessBoard"], FlexiPage=["slchessOld"], CustomTab=["SLCHESS_Tab"])
        self.assertEqual(self.run_check(*self.args()).returncode, 0)

    def test_a_prefixed_item_of_any_other_type_fails_and_names_the_type_and_the_name(self) -> None:
        # Both spellings count for the types a model may name either way; the item is found by the type's own name field.
        found = {"ApexTrigger": "SLChessTrigger", "ApexPage": "SLChessPage", "ApexComponent": "SLChessComp", "AuraDefinitionBundle": "slChessAura",
                 "StaticResource": "SLChessPieces", "FlexiPage": "SLChessHome", "CustomTab": "slChess_Board", "CustomApplication": "SLChess_App",
                 "CustomObject": "SLChess_Game", "PermissionSet": "SLChessAccess", "ExternalString": "SLChess_Label"}
        self.assertEqual(set(found), {spec[0] for spec in cs.WATCHED})
        self.add(**{kind: [name] for kind, name in found.items()})
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        for kind, name in found.items():
            self.assertIn("%s %s" % (kind, name), self.out(proc))
        self.assertIn("not clean", self.out(proc))

    def test_the_tab_app_and_page_the_request_names_are_refused_when_already_in_the_org(self) -> None:
        for kind, name in (("CustomTab", "SLChess_Board"), ("CustomApplication", "SLChess"), ("FlexiPage", "SLChess_Board")):
            self.set_state(dict(fk.default_state(), alias="de"))
            self.add(**{kind: [name]})
            proc = self.run_check(*self.args())
            self.assertEqual(proc.returncode, 1, kind)
            self.assertIn("%s %s" % (kind, name), self.out(proc))

    def test_a_type_the_org_cannot_query_is_skipped_and_said(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("not queryable here: ExternalString", self.out(proc))

    def test_a_transient_failure_on_a_type_query_fails_the_preflight_instead_of_skipping_the_type(self) -> None:
        self.edit(query_errors={"FlexiPage": "Request timed out, please retry"})
        self.add(FlexiPage=["SLChessHome"])  # what a skipped type would have hidden
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("timed out", self.out(proc))
        self.assertNotIn("not queryable here", self.out(proc))

    def test_the_org_is_found_in_either_bucket_the_real_cli_may_use(self) -> None:
        for buckets, expected in ((["other"], 0), (["nonScratchOrgs"], 0), (["other", "nonScratchOrgs"], 0), ([], 1)):
            self.edit(org_buckets=buckets)
            self.assertEqual(self.run_check(*self.args()).returncode, expected, buckets)

    def test_alias_not_connected_fails(self) -> None:
        state = self.state()
        state["connectedStatus"] = "RefreshTokenAuthError"
        self.set_state(state)
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not connected", self.out(proc))
        self.assertEqual([c["argv"][:2] for c in self.calls()], [["org", "list"]])

    def test_unknown_alias_fails_without_querying(self) -> None:
        state = self.state()
        state["alias"] = "someone-else"
        self.set_state(state)
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not in `sf org list`", self.out(proc))

    def test_an_org_the_fake_does_not_accept_fails(self) -> None:
        state = self.state()
        state["alias"] = "other"
        self.set_state(state)
        proc = self.run_check(*self.args("other"))
        self.assertEqual(proc.returncode, 1)


class TestSnapshot(FakeOrg):
    def test_snapshot_records_the_whole_org_sorted(self) -> None:
        self.add(apex=["ZedUtil"], lwc=["aaaFirst"])
        self.snapshot()
        before = self.before()
        self.assertEqual(before["apex_classes"], sorted(BASE_APEX + ["ZedUtil"]))
        self.assertEqual(before["lightning_component_bundles"], sorted(BASE_LWC + ["aaaFirst"]))
        self.assertEqual(before["counts"], dict({"ApexClass": 5, "LightningComponentBundle": 14},
                                                **{kind: len(names) for kind, names in BASE_TYPES.items()}))
        self.assertEqual((before["org"], before["prefix"]), ("de", "SLChess"))

    def test_snapshot_records_every_watched_type_the_dates_and_the_cli_version(self) -> None:
        self.snapshot()
        before = self.before()
        # The eleven types the live org answers, each as a sorted name set (a baseline org already holds some of them).
        self.assertEqual(sorted(before["other_types"]), sorted(["ApexTrigger", "ApexPage", "ApexComponent", "AuraDefinitionBundle", "StaticResource",
                                                                 "FlexiPage", "CustomTab", "CustomApplication", "CustomObject", "PermissionSet",
                                                                 "ExternalString"]))
        self.assertEqual(before["other_types"], {kind: sorted(names) for kind, names in BASE_TYPES.items()})
        self.assertEqual(before["unavailable"], {})  # a type queried through the wrong API would have failed in the fake and landed here
        self.assertEqual(before["last_modified"], {"ApexClass": {n: fk.BASE_DATE for n in BASE_APEX},
                                                   "LightningComponentBundle": {n: fk.BASE_DATE for n in BASE_LWC}})
        self.assertEqual(before["tool_versions"], {"sf": fk.VERSION})
        queries = [c["argv"] for c in self.calls() if c["argv"][:2] == ["data", "query"]]
        permission = next(a for a in queries if "FROM PermissionSet" in a[a.index("-q") + 1])
        self.assertIn("IsOwnedByProfile = false", permission[permission.index("-q") + 1])
        self.assertNotIn("--use-tooling-api", permission)
        self.assertIn("--use-tooling-api", next(a for a in queries if "FROM FlexiPage" in a[a.index("-q") + 1]))
        self.assertEqual([c["argv"] for c in self.calls() if c["argv"][0] == "--version"], [["--version"]])

    def test_a_type_that_errors_is_recorded_unavailable_and_the_snapshot_still_works(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        self.snapshot()
        before = self.before()
        self.assertEqual(list(before["unavailable"]), ["ExternalString"])
        self.assertIn("not supported", before["unavailable"]["ExternalString"])
        self.assertNotIn("ExternalString", before["other_types"])
        self.assertNotIn("ExternalString", before["counts"])

    def test_a_transient_failure_on_a_type_query_fails_the_snapshot_instead_of_recording_the_type_unavailable(self) -> None:
        self.edit(query_errors={"FlexiPage": "Request timed out, please retry"})
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("timed out", self.out(proc))
        self.assertFalse((self.platform / "before.json").exists())

    def test_snapshot_refuses_an_org_holding_a_prefixed_item_of_another_type(self) -> None:
        self.add(FlexiPage=["SLChessHome"])
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FlexiPage SLChessHome", self.out(proc))
        self.assertFalse((self.platform / "before.json").exists())

    def test_snapshot_refuses_an_org_already_holding_the_requested_tab_or_app(self) -> None:
        for kind, name in (("CustomTab", "SLChess_Board"), ("CustomApplication", "SLChess")):
            self.set_state(dict(fk.default_state(), alias="de"))
            self.add(**{kind: [name]})
            proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
            self.assertEqual(proc.returncode, 1, kind)
            self.assertIn("%s %s" % (kind, name), self.out(proc))
            self.assertFalse((self.platform / "before.json").exists())

    def test_the_platform_dir_defaults_to_platform_in_the_cwd(self) -> None:
        env = dict(self.env)
        del env["E2E_PLATFORM_DIR"]
        proc = subprocess.run([sys.executable, "-I", str(CHECKS), "snapshot", "--org", "de"], capture_output=True, text=True,
                              env=env, cwd=str(self.work))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertTrue((self.work / "platform" / "before.json").is_file())

    def test_snapshot_refuses_a_dirty_org_and_writes_nothing(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 1)
        self.assertFalse((self.platform / "before.json").exists())


class TestCleanup(FakeOrg):
    CLEAN = ("cleanup", "--org", "de", "--prefix", "SLChess")

    def deployed_like_a_model(self) -> None:
        self.snapshot()
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"],
                 CustomTab=["SLChess_Board"], CustomApplication=["SLChess"])

    def test_removes_only_new_prefixed_items_and_verifies(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        self.assertEqual(state["types"], BASE_TYPES)
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(sorted(r["name"] for r in record["removed"]),
                         ["SLChess", "SLChessController", "SLChessEngine", "SLChessEngineTest", "SLChess_Board", "slChessBoard"])

    def test_the_tab_app_and_page_go_in_the_same_single_destructive_deploy_apps_first(self) -> None:
        self.deployed_like_a_model()
        self.add(FlexiPage=["SLChess_Home"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        (call,) = self.deploys(destructive=True)  # one transaction handles the references between them
        self.assertEqual(self.destroyed(call), {"CustomApplication": ["SLChess"], "CustomTab": ["SLChess_Board"], "FlexiPage": ["SLChess_Home"],
                                                "LightningComponentBundle": ["slChessBoard"],
                                                "ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"]})
        self.assertEqual(call["type_order"], ["CustomApplication", "CustomTab", "FlexiPage", "LightningComponentBundle", "ApexClass"])
        self.assertEqual(self.state()["types"], BASE_TYPES)  # the baseline tabs, apps and pages are all still there

    def test_a_prefixed_name_that_was_in_the_snapshot_is_kept_in_the_new_types_too(self) -> None:
        self.snapshot()
        before = self.before()
        before["other_types"]["CustomTab"] = sorted(before["other_types"]["CustomTab"] + ["SLChess_Keep"])
        (self.platform / "before.json").write_text(json.dumps(before))
        self.add(CustomTab=["SLChess_Keep", "SLChess_Board"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("SLChess_Keep", self.state()["types"]["CustomTab"])
        self.assertNotIn("SLChess_Board", self.state()["types"]["CustomTab"])
        (call,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(call), {"CustomTab": ["SLChess_Board"]})

    def test_tab_app_and_page_look_alikes_are_refused_not_deleted_and_fail_the_verification(self) -> None:
        self.snapshot()
        look_alikes = {"CustomTab": "slChess_Board", "CustomApplication": "slchess", "FlexiPage": "SLCHESS_Home"}
        self.add(CustomTab=["SLChess_Board", look_alikes["CustomTab"]], CustomApplication=[look_alikes["CustomApplication"]],
                 FlexiPage=[look_alikes["FlexiPage"]])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        (call,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(call), {"CustomTab": ["SLChess_Board"]})  # only the exact prefix goes
        for kind, name in look_alikes.items():
            self.assertIn(name, self.state()["types"][kind])
            self.assertIn("extra %s %s" % (kind, name), proc.stdout)
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual({(r["type"], r["name"]) for r in record["refused"]}, set(look_alikes.items()))

    def test_a_leftover_prefixed_tab_or_app_after_the_deploy_fails_the_verification_and_names_it(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_NOOP_DESTRUCTIVE": "1"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("extra CustomApplication SLChess", proc.stdout)
        self.assertIn("extra CustomTab SLChess_Board", proc.stdout)
        self.assertNotIn("remove by hand", proc.stdout)  # these two types are removable, so a leftover is a failed removal
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["extra"]["CustomTab"]), (False, ["SLChess_Board"]))

    def test_a_removable_type_the_snapshot_could_not_query_is_never_removed_from_and_its_leftover_fails_the_cleanup(self) -> None:
        self.edit(query_errors={"CustomTab": "sObject type 'CustomTab' is not supported."})
        self.snapshot()
        self.edit(query_errors={})
        self.add(CustomTab=["SLChess_Board"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1, self.out(proc))  # the tab is still in the org: an exit 0 would record a clean platform
        self.assertIn("extra CustomTab SLChess_Board", proc.stdout)
        self.assertIn("CLEANUP FAILED", proc.stderr)
        self.assertIn("SLChess_Board", self.state()["types"]["CustomTab"])  # nothing in a type the snapshot could not see is told apart from the baseline
        self.assertEqual(self.deploys(), [])
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual([(r["type"], r["name"], r["reason"]) for r in record["refused"]],
                         [("CustomTab", "SLChess_Board", "type was not queryable at the snapshot")])
        self.assertEqual((record["verified"], record["extra"], list(record["not_covered"])), (False, {"CustomTab": ["SLChess_Board"]}, ["CustomTab"]))

    def test_an_unqueryable_removable_type_with_nothing_prefixed_in_it_still_passes(self) -> None:
        self.edit(query_errors={"FlexiPage": "sObject type 'FlexiPage' is not supported."})
        self.snapshot()
        self.edit(query_errors={})
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("not covered (query failed at the snapshot): FlexiPage", proc.stdout)

    def test_a_transient_failure_while_looking_for_a_removable_type_stops_before_any_deploy(self) -> None:
        self.deployed_like_a_model()
        self.edit(query_errors={"FlexiPage": "Request timed out, please retry"})
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("timed out", self.out(proc))
        self.assertEqual(self.deploys(), [])
        self.assertIn("SLChessEngine", self.state()["apex_classes"])

    def test_the_verified_message_lists_exactly_the_types_and_counts_it_covered(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        covered = dict({"ApexClass": 4, "LightningComponentBundle": 13}, **{kind: len(names) for kind, names in BASE_TYPES.items()})
        self.assertEqual(json.loads((self.platform / "cleanup.json").read_text())["covered"], covered)
        for kind, count in covered.items():
            self.assertIn("%s %d" % (kind, count), proc.stdout)
        self.assertIn("LastModifiedDate unchanged on 17 baseline", proc.stdout)
        self.assertNotIn("not covered", proc.stdout)

    def test_the_verified_message_says_which_types_it_removes_and_which_it_only_compares(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        removes = "removes when new and prefixed (SLChess*, slChess* for bundles): CustomApplication, CustomTab, FlexiPage, LightningComponentBundle, ApexClass"
        self.assertIn(removes, proc.stdout)
        self.assertIn("only compares, never removes: ApexTrigger, ApexPage, ApexComponent, AuraDefinitionBundle, StaticResource, CustomObject, "
                      "PermissionSet, ExternalString", proc.stdout)
        self.assertIn("removed CustomApplication SLChess, CustomTab SLChess_Board, LightningComponentBundle slChessBoard, ApexClass SLChessController",
                      proc.stdout)

    def test_an_extra_item_of_a_type_cleanup_cannot_remove_fails_the_run_and_is_never_deleted(self) -> None:
        self.deployed_like_a_model()
        self.add(StaticResource=["SLChessPieces"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not removable by this cleanup: remove by hand: StaticResource SLChessPieces", self.out(proc))
        state = self.state()
        self.assertIn("SLChessPieces", state["types"]["StaticResource"])
        self.assertNotIn("SLChessEngine", state["apex_classes"])  # what it can remove, it still removed
        (call,) = self.deploys(destructive=True)
        self.assertNotIn("SLChessPieces", json.dumps(call["destructive"]))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["extra"]), (False, {"StaticResource": ["SLChessPieces"]}))

    def test_a_cleanup_whose_org_also_holds_another_cases_kept_items_succeeds_and_notes_them_as_left_alone(self) -> None:
        """Live run F9/F10 (2026-10-19): org `de` also held another case's kept app (prefix SLBattle) and an unrelated platform
        permission set (AccessDevOpsCenterNamedCredentials), and a correct chess cleanup reported failure for both. This cleanup's
        job is its own prefix: neither item is this case's to remove, so both are left alone and only noted, while this run's own
        deployment is still fully removed and verified."""
        self.deployed_like_a_model()
        self.add(apex=["SLBattleEngine"], lwc=["slBattleBoard"], CustomTab=["SLBattle_Board"], CustomApplication=["SLBattle"],
                 PermissionSet=["AccessDevOpsCenterNamedCredentials"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("not this case's: left alone", proc.stdout)
        for item in ("ApexClass SLBattleEngine", "LightningComponentBundle slBattleBoard", "CustomTab SLBattle_Board",
                     "CustomApplication SLBattle", "PermissionSet AccessDevOpsCenterNamedCredentials"):
            self.assertIn(item, proc.stdout)
        state = self.state()
        self.assertNotIn("SLChessEngine", state["apex_classes"])  # this case's own work is still removed
        self.assertIn("SLBattleEngine", state["apex_classes"])  # the other case's kept work is left exactly alone
        self.assertIn("slBattleBoard", state["lwc"])
        self.assertIn("SLBattle_Board", state["types"]["CustomTab"])
        self.assertIn("SLBattle", state["types"]["CustomApplication"])
        self.assertIn("AccessDevOpsCenterNamedCredentials", state["types"]["PermissionSet"])
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(record["extra"], {"ApexClass": ["SLBattleEngine"], "LightningComponentBundle": ["slBattleBoard"],
                                           "CustomTab": ["SLBattle_Board"], "CustomApplication": ["SLBattle"],
                                           "PermissionSet": ["AccessDevOpsCenterNamedCredentials"]})

    def test_an_extra_permission_set_under_the_case_s_own_prefix_cannot_be_removed_and_names_the_exact_commands_by_hand(self) -> None:
        """Live run F9/F10 (2026-10-19): a kept chess app left SLChess_Access, a permission set the request forbids the model from
        making (the chess-salesforce prompt creates no permission set), so only a model that disregarded the request, never this
        harness, could have made one. The cleanup must not silently delete something a model made against the request: it still
        fails, and names the exact `sf data delete record` commands (its live Id and its assignment's Id) to remove it by hand."""
        self.deployed_like_a_model()
        self.add(PermissionSet=["SLChess_Access"])
        state = self.state()
        user = state["users"][0]["Id"]
        ps_id = fk.record_id("PermissionSet", "SLChess_Access")
        assign_id = fk.record_id("PermissionSetAssignment", "SLChess_Access")
        state["assignments"].append({"Id": assign_id, "PermissionSetId": ps_id, "AssigneeId": user})
        self.set_state(state)
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        out = self.out(proc)
        self.assertIn("not removable by this cleanup: remove by hand: PermissionSet SLChess_Access", out)
        self.assertIn("only a model could have made it, never this harness", out)
        self.assertIn("sf data delete record --sobject PermissionSetAssignment --record-id %s --target-org de" % assign_id, out)
        self.assertIn("sf data delete record --sobject PermissionSet --record-id %s --target-org de" % ps_id, out)
        self.assertNotIn("not this case's", out)  # this case's own prefix, never informational
        self.assertIn("SLChess_Access", self.state()["types"]["PermissionSet"])  # never touched
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["extra"]), (False, {"PermissionSet": ["SLChess_Access"]}))

    def test_an_item_of_every_recorded_type_is_removed_if_the_request_allows_it_and_reported_under_its_own_type_if_not(self) -> None:
        self.snapshot()
        extras = {spec[0]: "SLChessLeft%d" % i for i, spec in enumerate(cs.WATCHED)}
        self.add(**{kind: [name] for kind, name in extras.items()})
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        for kind, name in extras.items():
            if kind in cs.REMOVABLE:
                self.assertNotIn(name, self.state()["types"][kind])
            else:
                self.assertIn("not removable by this cleanup: remove by hand: %s %s" % (kind, name), proc.stdout)
        (call,) = self.deploys(destructive=True)  # only the three types the request allows; the rest is never removed
        self.assertEqual(self.destroyed(call), {kind: [extras[kind]] for kind in ("CustomApplication", "CustomTab", "FlexiPage")})

    def test_a_baseline_item_that_disappeared_is_reported_missing(self) -> None:
        self.snapshot()
        state = self.state()
        state["types"]["CustomTab"].remove("baseTab01")
        self.set_state(state)
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing since the snapshot: CustomTab baseTab01", proc.stdout)

    def test_a_baseline_class_whose_date_changed_is_reported_modified(self) -> None:
        self.snapshot()
        self.set_date("ApexClass", "PostInstallScript", "2026-10-16T13:00:00.000+0000")
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("modified since the snapshot: ApexClass PostInstallScript (%s -> 2026-10-16T13:00:00.000+0000)" % fk.BASE_DATE, proc.stdout)
        self.assertEqual(json.loads((self.platform / "cleanup.json").read_text())["modified"],
                         {"ApexClass": ["PostInstallScript (%s -> 2026-10-16T13:00:00.000+0000)" % fk.BASE_DATE]})

    def test_a_baseline_bundle_whose_date_changed_is_reported_modified(self) -> None:
        self.snapshot()
        self.set_date("LightningComponentBundle", "chess", "2026-10-16T13:00:00.000+0000")
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("modified since the snapshot: LightningComponentBundle chess", proc.stdout)

    def test_a_model_that_redeploys_a_baseline_class_is_caught_by_its_date(self) -> None:
        self.snapshot()
        self.deploy_classes("DeveloperEditionUtils")  # same name and still 4 baseline names: only the date shows it
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("modified since the snapshot: ApexClass DeveloperEditionUtils", proc.stdout)
        self.assertEqual(self.deploys(destructive=True), [])  # a baseline item is never removed

    def test_a_type_the_snapshot_could_not_query_is_skipped_in_the_comparison_and_said(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        self.snapshot()
        self.edit(query_errors={})
        self.add(ExternalString=["SLChess_Label"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("not covered (query failed at the snapshot): ExternalString", proc.stdout)
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertNotIn("ExternalString", record["covered"])
        self.assertIn("ExternalString", record["not_covered"])

    def test_a_recorded_type_that_cannot_be_queried_afterwards_fails_closed(self) -> None:
        self.snapshot()
        self.edit(query_errors={"FlexiPage": "sObject type 'FlexiPage' is not supported."})
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("could not verify FlexiPage", proc.stdout)

    def test_a_snapshot_of_the_old_shape_is_refused_and_nothing_is_deleted(self) -> None:
        self.deployed_like_a_model()
        before = self.before()
        old = {key: before[key] for key in ("org", "prefix", "apex_classes", "lightning_component_bundles", "counts")}
        (self.platform / "before.json").write_text(json.dumps(old))
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no usable", self.out(proc))
        self.assertEqual(self.deploys(), [])

    def test_the_destructive_deploy_names_exactly_those_members_with_an_empty_package(self) -> None:
        self.deployed_like_a_model()
        self.assertEqual(self.run_check(*self.CLEAN).returncode, 0)
        (call,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(call), {"CustomApplication": ["SLChess"], "CustomTab": ["SLChess_Board"],
                                                "ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"],
                                                "LightningComponentBundle": ["slChessBoard"]})
        self.assertEqual(call["manifest_types"], 0)
        self.assertIn("--post-destructive-changes", call["argv"])
        self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de")
        self.assertNotIn("*", json.dumps(call["destructive"]))

    def test_an_item_that_was_in_before_json_is_kept(self) -> None:
        self.snapshot()
        before = self.before()
        before["apex_classes"] = sorted(before["apex_classes"] + ["SLChessKeep"])
        (self.platform / "before.json").write_text(json.dumps(before))
        self.add(apex=["SLChessKeep", "SLChessEngine"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("SLChessKeep", self.state()["apex_classes"])
        self.assertNotIn("SLChessEngine", self.state()["apex_classes"])
        (call,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(call), {"ApexClass": ["SLChessEngine"]})

    def test_a_look_alike_name_is_refused_not_deleted_and_the_run_fails_verification(self) -> None:
        self.deployed_like_a_model()
        self.add(apex=["slchessSneaky"], lwc=["SLChessUpper"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        state = self.state()
        self.assertIn("slchessSneaky", state["apex_classes"])
        self.assertIn("SLChessUpper", state["lwc"])
        (call,) = self.deploys(destructive=True)
        self.assertNotIn("slchessSneaky", json.dumps(call["destructive"]))
        self.assertNotIn("SLChessUpper", json.dumps(call["destructive"]))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertFalse(record["verified"])
        self.assertEqual({r["name"] for r in record["refused"]}, {"slchessSneaky", "SLChessUpper"})
        self.assertIn("CLEANUP FAILED", proc.stderr)

    def test_nothing_else_is_ever_removed(self) -> None:
        self.deployed_like_a_model()
        self.run_check(*self.CLEAN)
        state = self.state()
        self.assertTrue(set(BASE_APEX) <= set(state["apex_classes"]))
        self.assertTrue(set(BASE_LWC) <= set(state["lwc"]))

    def test_idempotent_nothing_to_remove_is_success_without_a_deploy(self) -> None:
        self.deployed_like_a_model()
        self.assertEqual(self.run_check(*self.CLEAN).returncode, 0)
        deploys_before = len(self.deploys())
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(len(self.deploys()), deploys_before)
        self.assertEqual(json.loads((self.platform / "cleanup.json").read_text())["removed"], [])

    def test_a_clean_org_with_a_snapshot_is_success(self) -> None:
        self.snapshot()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(self.deploys(), [])

    def test_without_before_json_nothing_is_deleted(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])
        self.assertIn("SLChessEngine", self.state()["apex_classes"])

    def test_a_deploy_that_removes_nothing_is_not_verified(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_NOOP_DESTRUCTIVE": "1"})
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads((self.platform / "cleanup.json").read_text())["verified"])
        self.assertIn("SLChessEngine", self.out(proc))

    def test_a_failed_destructive_deploy_fails_and_says_so(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_FAIL": "destructive"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("destructive deploy failed", self.out(proc))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["removed"]), (False, []))

    def test_a_failed_query_fails_closed(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_FAIL": "query"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])

    def test_the_warning_line_does_not_break_cleanup(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))


CONTROLLER = ("public with sharing class SLChessController {\n"
              "    @AuraEnabled public static List<String> legalMoves(String fen) { return SLChessEngine.legalMoves(fen); }\n"
              "    @AuraEnabled public static String applyMove(String fen, String move) { return SLChessEngine.applyMove(fen, move); }\n"
              "    @AuraEnabled public static String status(String fen) { return SLChessEngine.status(fen); }\n}\n")
BOARD_JS = ("import { LightningElement } from 'lwc';\n"
            "import legalMoves from '@salesforce/apex/SLChessController.legalMoves';\n"
            "import applyMove from '@salesforce/apex/SLChessController.applyMove';\n"
            "export default class SlChessBoard extends LightningElement {}\n")
BOARD_HTML = '<template><template for:each={squares} for:item="square"><div key={square.id}>{square.label}</div></template></template>'
XML = '<?xml version="1.0" encoding="UTF-8"?>\n'
BOARD_META = XML + ('<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>60.0</apiVersion>'
                    "<isExposed>true</isExposed><targets>%s</targets></LightningComponentBundle>\n")
TARGET_TAB = "<target>lightning__Tab</target>"
TARGET_PAGE = "<target>lightning__AppPage</target>"
TAB_XML = XML + '<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata"><label>Chess</label>%s<motif>Custom57: Grid</motif></CustomTab>\n'
TAB_BOARD = TAB_XML % "<lwcComponent>slChessBoard</lwcComponent>"
APP_XML = XML + ('<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata"><formFactors>Large</formFactors><label>Chess</label>'
                 "<navType>Standard</navType>%s<uiType>Lightning</uiType></CustomApplication>\n")
APP_BOARD = APP_XML % "<tabs>standard-home</tabs><tabs>SLChess_Board</tabs>"
PAGE_XML = XML + '<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata"><masterLabel>Chess</masterLabel><type>AppPage</type></FlexiPage>\n'


def make_project(tmp: Path, classes=("SLChessEngine", "SLChessController", "SLChessEngineTest"), bundle="slChessBoard", extra=(),
                 controller=CONTROLLER, js=BOARD_JS, html=BOARD_HTML, targets=TARGET_TAB, files=None) -> Path:
    """A project that passes `project`. `files` replaces or adds files under force-app/main/default (a value of None removes one):
    the tab, the app and the component meta file are among the defaults, so a test changes just the one it is about."""
    project = tmp / "proj"
    shutil.rmtree(project, ignore_errors=True)
    base = project / "force-app" / "main" / "default"
    (base / "classes").mkdir(parents=True)
    for name in classes:
        (base / "classes" / (name + ".cls")).write_text(controller if name == "SLChessController" else "public class %s {}" % name)
        (base / "classes" / (name + ".cls-meta.xml")).write_text("<ApexClass/>")
    (base / "lwc" / bundle).mkdir(parents=True)
    (base / "lwc" / bundle / (bundle + ".js")).write_text(js)
    (base / "lwc" / bundle / (bundle + ".html")).write_text(html)
    (base / "lwc" / ".eslintrc.json").write_text("{}")
    (base / "lwc" / "jsconfig.json").write_text("{}")
    (project / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app"}]}))
    defaults = {"lwc/%s/%s.js-meta.xml" % (bundle, bundle): BOARD_META % targets, "tabs/SLChess_Board.tab-meta.xml": TAB_BOARD,
                "applications/SLChess.app-meta.xml": APP_BOARD}
    for rel, text in {**defaults, **(files or {})}.items():
        target = base / rel
        if text is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    for rel in extra:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("<x/>")
    return project


class TestProject(FakeOrg):
    def make(self, **kwargs) -> Path:
        return make_project(self.tmp, **kwargs)

    def run_project(self, project: Path) -> subprocess.CompletedProcess:
        return self.run_check("project", "--org", "de", cwd=project)

    def test_a_complete_project_passes(self) -> None:
        proc = self.run_project(self.make())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("tab, app", proc.stdout)
        self.assertEqual(self.calls(), [])  # no sf call at all

    def test_missing_engine_fails(self) -> None:
        proc = self.run_project(self.make(classes=("SLChessController",)))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessEngine.cls", self.out(proc))

    def test_no_sfdx_project_json_fails(self) -> None:
        project = self.make()
        (project / "sfdx-project.json").unlink()
        self.assertEqual(self.run_project(project).returncode, 1)

    def test_component_without_html_fails(self) -> None:
        project = self.make()
        next(project.rglob("slChessBoard.html")).unlink()
        proc = self.run_project(project)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(".html", self.out(proc))

    def test_wrong_component_name_fails(self) -> None:
        self.assertEqual(self.run_project(self.make(bundle="chessBoard")).returncode, 1)

    def test_a_class_without_the_prefix_fails(self) -> None:
        self.assertEqual(self.run_project(self.make(classes=("SLChessEngine", "Helper"))).returncode, 1)

    def test_other_metadata_fails_even_when_it_carries_the_prefix(self) -> None:
        for extra in ("objects/Thing__c/Thing__c.object-meta.xml", "flows/F.flow-meta.xml", "permissionsets/P.permissionset-meta.xml",
                      "permissionsets/SLChess_P.permissionset-meta.xml", "objects/SLChess__c/SLChess__c.object-meta.xml",
                      "staticresources/SLChess_a.resource-meta.xml", "triggers/SLChessT.trigger-meta.xml",
                      "profiles/Admin.profile-meta.xml", "labels/CustomLabels.labels-meta.xml"):
            proc = self.run_project(self.make(extra=(extra,)))
            self.assertEqual(proc.returncode, 1, extra)
            self.assertIn("other metadata main/default/%s" % extra, self.out(proc))

    def failing(self, message: str, **kwargs) -> None:
        proc = self.run_project(self.make(**kwargs))
        self.assertEqual(proc.returncode, 1, self.out(proc))
        self.assertIn(message, self.out(proc))

    def test_a_project_without_the_controller_fails_and_names_it(self) -> None:
        self.failing("SLChessController.cls", classes=("SLChessEngine", "SLChessEngineTest"))

    def test_a_controller_without_an_aura_enabled_method_fails(self) -> None:
        self.failing("has no @AuraEnabled method", controller=CONTROLLER.replace("@AuraEnabled ", ""))

    def test_a_controller_missing_one_of_the_three_methods_fails_and_names_it(self) -> None:
        self.failing("declares no static method applyMove", controller=CONTROLLER.replace("applyMove(String", "apply(String"))
        self.failing("declares no static method legalMoves", controller=CONTROLLER.replace("legalMoves(String", "moves(String"))
        self.failing("declares no static method status", controller=CONTROLLER.replace("String status(", "String state("))

    def test_a_component_that_never_imports_the_controller_fails(self) -> None:
        self.failing("does not import @salesforce/apex/SLChessController",
                     js="import { LightningElement } from 'lwc';\nexport default class X extends LightningElement {}\n")
        self.failing("does not import @salesforce/apex/SLChessController", js=BOARD_JS.replace("SLChessController", "SLChessEngine"))

    def test_a_component_template_that_renders_no_list_fails(self) -> None:
        self.failing("no for:each or iterator", html="<template><div>board</div></template>")

    def test_an_iterator_template_passes(self) -> None:
        proc = self.run_project(self.make(html="<template><template iterator:sq={squares}><div key={sq.value.id}></div></template></template>"))
        self.assertEqual(proc.returncode, 0, self.out(proc))

    # the tab, the app and the optional app page
    def test_a_project_without_the_tab_or_the_app_fails_and_names_the_file(self) -> None:
        self.failing("no force-app/**/tabs/SLChess_Board.tab-meta.xml", files={"tabs/SLChess_Board.tab-meta.xml": None})
        self.failing("no force-app/**/applications/SLChess.app-meta.xml", files={"applications/SLChess.app-meta.xml": None})

    def test_a_tab_without_lwc_component_fails(self) -> None:
        self.failing("tab SLChess_Board.tab-meta.xml has no <lwcComponent>slChessBoard</lwcComponent>",
                     files={"tabs/SLChess_Board.tab-meta.xml": TAB_XML % ""})

    def test_a_tab_that_shows_another_component_fails(self) -> None:
        self.failing("tab SLChess_Board.tab-meta.xml shows lwcComponent chessBoard, not slChessBoard",
                     files={"tabs/SLChess_Board.tab-meta.xml": TAB_XML % "<lwcComponent>chessBoard</lwcComponent>"})

    def test_a_tab_may_show_a_prefixed_app_page_that_is_in_the_project(self) -> None:
        pages = {"tabs/SLChess_Board.tab-meta.xml": TAB_XML % "<flexiPage>SLChess_Home</flexiPage>",
                 "flexipages/SLChess_Home.flexipage-meta.xml": PAGE_XML}
        proc = self.run_project(self.make(files=pages, targets=TARGET_TAB + TARGET_PAGE))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("app page", proc.stdout)
        self.failing("has no <lwcComponent>", files=dict(pages, **{"flexipages/SLChess_Home.flexipage-meta.xml": None}), targets=TARGET_TAB + TARGET_PAGE)

    def test_an_app_that_lists_no_tab_of_the_project_fails(self) -> None:
        self.failing("app SLChess.app-meta.xml lists no <tabs> entry naming one of this project's SLChess* tabs",
                     files={"applications/SLChess.app-meta.xml": APP_XML % "<tabs>standard-home</tabs>"})
        self.failing("lists no <tabs> entry", files={"applications/SLChess.app-meta.xml": APP_XML % "<tabs>SLChess_Gone</tabs>"})

    def test_the_component_meta_must_expose_the_tab_target_and_the_page_target_when_there_is_a_page(self) -> None:
        self.failing("js-meta.xml does not expose the lightning__Tab target", targets=TARGET_PAGE)
        page = {"flexipages/SLChess_Home.flexipage-meta.xml": PAGE_XML}
        self.failing("does not expose lightning__AppPage", files=page, targets=TARGET_TAB)
        self.assertEqual(self.run_project(self.make(files=page, targets=TARGET_TAB + TARGET_PAGE)).returncode, 0)

    def test_a_component_without_a_meta_file_fails(self) -> None:
        self.failing("has no .js-meta.xml file", files={"lwc/slChessBoard/slChessBoard.js-meta.xml": None})

    def test_a_tab_app_or_page_without_the_prefix_or_in_the_wrong_folder_is_other_metadata(self) -> None:
        for rel in ("tabs/Board.tab-meta.xml", "applications/Chess.app-meta.xml", "flexipages/Home.flexipage-meta.xml",
                    "tabs/SLChess_X.app-meta.xml", "applications/SLChess_X.tab-meta.xml", "tabs/slChess_Other.tab-meta.xml"):
            self.failing("other metadata main/default/%s" % rel, extra=(rel,))

    def test_a_second_prefixed_tab_is_allowed_when_it_also_shows_the_component(self) -> None:
        proc = self.run_project(self.make(files={"tabs/SLChess_Two.tab-meta.xml": TAB_BOARD}))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.failing("tab SLChess_Two.tab-meta.xml has no <lwcComponent>", files={"tabs/SLChess_Two.tab-meta.xml": TAB_XML % ""})


class TestDeployedAndTests(FakeOrg):
    def deploy_all(self, tests=("SLChessEngineTest", "SLChessMovesTest")) -> None:
        self.add(apex=["SLChessEngine", "SLChessController", *tests], lwc=["slChessBoard"], CustomTab=["SLChess_Board"],
                 CustomApplication=["SLChess"])

    def run_deployed(self, *extra: str) -> subprocess.CompletedProcess:
        return self.run_check("deployed", "--org", "de", "--prefix", "SLChess", *extra)

    def test_deployed_passes_when_everything_is_there(self) -> None:
        self.deploy_all()
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def test_deployed_names_what_is_missing(self) -> None:
        self.add(apex=["SLChessEngine", "SLChessEngineTest"])
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessController", self.out(proc))
        self.assertIn("slChessBoard", self.out(proc))
        self.assertIn("CustomTab SLChess_Board not found", self.out(proc))
        self.assertIn("CustomApplication SLChess not found", self.out(proc))

    def test_deployed_needs_the_tab_and_the_app_each_on_its_own(self) -> None:
        for missing, message in (("CustomTab", "CustomTab SLChess_Board not found"), ("CustomApplication", "CustomApplication SLChess not found")):
            self.set_state(dict(fk.default_state(), alias="de"))
            self.deploy_all()
            state = self.state()
            state["types"][missing] = BASE_TYPES[missing]
            self.set_state(state)
            proc = self.run_deployed()
            self.assertEqual(proc.returncode, 1, missing)
            self.assertIn(message, self.out(proc))
            self.assertEqual(self.out(proc).count("not found"), 1)

    def test_a_tab_or_app_of_the_orgs_own_or_with_another_case_does_not_count(self) -> None:
        self.deploy_all()
        state = self.state()
        state["types"]["CustomTab"] = BASE_TYPES["CustomTab"] + ["slChess_Board"]
        state["types"]["CustomApplication"] = BASE_TYPES["CustomApplication"] + ["slchess"]
        self.set_state(state)
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("CustomTab SLChess_Board not found", self.out(proc))
        self.assertIn("CustomApplication SLChess not found", self.out(proc))

    def test_deployed_queries_only_prefixed_tabs_apps_and_pages(self) -> None:
        self.deploy_all()
        self.assertEqual(self.run_deployed().returncode, 0)
        queries = [c["argv"][c["argv"].index("-q") + 1] for c in self.calls() if c["argv"][:2] == ["data", "query"]]
        for kind in ("CustomTab", "CustomApplication", "FlexiPage"):
            self.assertIn("SELECT DeveloperName FROM %s WHERE DeveloperName LIKE 'SLChess%%'" % kind, queries)

    def test_the_app_page_is_required_only_when_it_is_named(self) -> None:
        self.deploy_all()
        self.assertEqual(self.run_deployed().returncode, 0)
        proc = self.run_deployed("--pages", "SLChess_Home")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FlexiPage SLChess_Home not found", self.out(proc))
        self.add(FlexiPage=["SLChess_Home"])
        self.assertEqual(self.run_deployed("--pages", "SLChess_Home").returncode, 0)
        self.assertIn("app page SLChess_Home", self.run_deployed("--pages", "SLChess_Home").stdout)

    def test_deployed_needs_a_test_class(self) -> None:
        self.deploy_all(tests=())
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Test classes", self.out(proc))

    def test_a_look_alike_test_class_does_not_count(self) -> None:
        self.deploy_all(tests=("slchessEngineTest", "SLChessEngineTests"))
        self.assertEqual(self.run_deployed().returncode, 1)

    def test_tests_pass_with_enough_methods_one_call_per_class(self) -> None:
        self.deploy_all()
        proc = self.run_check("tests", "--org", "de", "--prefix", "SLChess", "--min-tests", "8")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        runs = [c["argv"] for c in self.calls() if c["argv"][:3] == ["apex", "run", "test"]]
        self.assertEqual(sorted(a[a.index("--class-names") + 1] for a in runs), ["SLChessEngineTest", "SLChessMovesTest"])
        self.assertTrue(all("--synchronous" in a and a[a.index("--target-org") + 1] == "de" for a in runs))

    def test_threshold_counts_total_tests_that_ran(self) -> None:
        self.deploy_all()
        counts = self.tmp / "tests.json"
        counts.write_text(json.dumps({"testsRan": 3}))
        low = self.run_check("tests", "--org", "de", "--min-tests", "8", env={"FAKE_SF_TESTS": str(counts)})
        self.assertEqual(low.returncode, 1)
        self.assertIn("need at least 8", self.out(low))
        enough = self.run_check("tests", "--org", "de", "--min-tests", "6", env={"FAKE_SF_TESTS": str(counts)})
        self.assertEqual(enough.returncode, 0, self.out(enough))

    def test_a_failing_test_fails(self) -> None:
        self.deploy_all()
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 10, "failing": 1}))
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(results)})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL", self.out(proc))

    def test_outcome_must_be_passed_even_with_zero_failing(self) -> None:
        self.deploy_all()
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Skipped", "testsRan": 10, "failing": 0}))
        self.assertEqual(self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(results)}).returncode, 1)

    def test_no_test_class_fails(self) -> None:
        self.deploy_all(tests=())
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([c for c in self.calls() if c["argv"][:3] == ["apex", "run", "test"]], [])

    def test_a_failed_test_run_command_fails(self) -> None:
        self.deploy_all()
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(self.tmp / "none.json"), "FAKE_SF_FAIL": "test"})
        self.assertEqual(proc.returncode, 1)


class TestRules(FakeOrg):
    def canned(self, **override) -> Path:
        values = {marker: expected for _name, _script, marks in cs.rule_cases() for marker, expected in marks}
        values.update(override)
        path = self.tmp / "apex.json"
        path.write_text(json.dumps(values))
        return path

    def run_rules(self, canned: Path) -> subprocess.CompletedProcess:
        return self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(canned)})

    def test_the_oracle_table_is_the_published_one(self) -> None:
        table = {name: (one, two) for name, _fen, one, two in cs.PERFT}
        self.assertEqual(table, {"start": (20, 400), "kiwipete": (48, None), "pos3": (14, 191), "pos4": (6, 264),
                                 "pos5": (44, 1486), "castle": (26, None)})

    def test_matching_logs_pass_and_every_position_prints_a_line(self) -> None:
        proc = self.run_rules(self.canned())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("PASS start.p1 expected=20 got=20", proc.stdout)
        self.assertIn("PASS pos5.p2 expected=1486 got=1486", proc.stdout)
        self.assertIn("PASS foolsmate expected=checkmate got=checkmate", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_each_position_is_its_own_anonymous_apex_call_with_a_harness_owned_file(self) -> None:
        proc = self.run_rules(self.canned())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        runs = [c for c in self.calls() if c["argv"][:2] == ["apex", "run"]]
        self.assertEqual(len(runs), len(cs.rule_cases()))
        for call in runs:
            file = Path(call["argv"][call["argv"].index("--file") + 1])
            self.assertTrue(str(file).startswith(str(self.tmp / "tmpdir")), file)
            self.assertFalse(file.exists(), "the temp script is removed afterwards")
            self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de")
        markers = [m for c in runs for m in c["apex_markers"]]
        self.assertEqual(markers, [marker for _n, _s, marks in cs.rule_cases() for marker, _e in marks])

    def test_the_scripts_call_only_the_interface_in_the_prompt(self) -> None:
        for _name, script, _marks in cs.rule_cases():
            for call in re.findall(r"SLChess\w*\.\w+", script):
                self.assertIn(call, {"SLChessEngine.legalMoves", "SLChessEngine.applyMove", "SLChessEngine.status",
                                     "SLChessEngine.startFen", "SLChessEngine.IllegalMoveException",
                                     "SLChessController.legalMoves", "SLChessController.applyMove", "SLChessController.status"})

    def test_each_game_is_one_anonymous_apex_that_plays_every_ply_through_the_controller(self) -> None:
        scripts = {name: script for name, script, _marks in cs.rule_cases()}
        for name, moves, special, (after, bad) in cs.GAMES:
            script = scripts[name]
            self.assertEqual(re.findall(r"'([a-h][1-8][a-h][1-8][qrbn]?)'", re.search(r"moves = new List<String>\{([^}]*)\}", script)[1]), moves)
            for call in ("SLChessController.legalMoves(fen)", "SLChessController.applyMove(fen, move)", "SLChessController.status(fen)"):
                self.assertIn(call, script)
            self.assertEqual(script.count("RESULT|"), 1)  # one marker for the whole game
            self.assertIn("SLChessEngine.applyMove(fen, '%s')" % bad, script)  # the engine itself refuses the illegal move
            self.assertIn("catch (SLChessEngine.IllegalMoveException", script)
            self.assertEqual(len([line for line in script.splitlines() if line.startswith("for ")]), 1)

    def test_a_game_whose_last_status_is_wrong_fails_rules_and_shows_where(self) -> None:
        for name, wrong in (("game_opera", "ply 33 d1d8 leaves status check, expected checkmate"),
                            ("game_second", "ply 17 c7c8r is not in legalMoves")):
            proc = self.run_rules(self.canned(**{name: wrong}))
            self.assertEqual(proc.returncode, 1, name)
            self.assertIn("FAIL %s expected=ok got=%s" % (name, wrong), proc.stdout)
            self.assertEqual(proc.stdout.splitlines()[-1].split("failed: ")[1], name)  # and nothing else failed

    def test_a_game_that_is_not_played_to_the_end_never_passes_by_default(self) -> None:
        canned = json.loads(self.canned().read_text())
        del canned["game_second"]
        (self.tmp / "apex3.json").write_text(json.dumps(canned))
        proc = self.run_rules(self.tmp / "apex3.json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL game_second expected=ok got=MISSING", proc.stdout)

    def test_a_wrong_count_fails_and_shows_expected_and_got(self) -> None:
        proc = self.run_rules(self.canned(**{"start.p2": "399"}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL start.p2 expected=400 got=399", proc.stdout)
        self.assertIn("PASS start.p1 expected=20 got=20", proc.stdout)

    def test_a_wrong_status_or_missing_result_fails(self) -> None:
        proc = self.run_rules(self.canned(scholarsmate="check"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL scholarsmate expected=checkmate got=check", proc.stdout)
        canned = json.loads(self.canned().read_text())
        del canned["epfield"]
        (self.tmp / "apex2.json").write_text(json.dumps(canned))
        again = self.run_rules(self.tmp / "apex2.json")
        self.assertEqual(again.returncode, 1)
        self.assertIn("FAIL epfield expected=e3 got=MISSING", again.stdout)

    def test_an_engine_over_the_cpu_limit_fails_with_the_apex_error_shown(self) -> None:
        proc = self.run_rules(self.canned(**{"kiwipete.p1": {"error": "System.LimitException: Maximum CPU time exceeded"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL kiwipete.p1", proc.stdout)
        self.assertIn("Maximum CPU time exceeded", proc.stdout)

    def test_a_compile_error_fails_with_the_problem_shown(self) -> None:
        proc = self.run_rules(self.canned(**{"start.p1": {"compileProblem": "Variable does not exist: SLChessEngine"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("compile error: Variable does not exist", proc.stdout)

    def test_an_apex_command_failure_fails(self) -> None:
        proc = self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(self.canned()), "FAKE_SF_FAIL": "apex"})
        self.assertEqual(proc.returncode, 1)

    def test_the_warning_line_does_not_break_rules(self) -> None:
        proc = self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(self.canned()), "FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def test_the_literal_answers_the_oracle_adds_are_checked_one_marker_each(self) -> None:
        proc = self.run_rules(self.canned())
        for marker in ("startfen", "startmoves", "e2e4", "e7e5", "status.start", "status.check", "promo.moves",
                       "controller.moves", "controller.apply"):
            self.assertRegex(proc.stdout, r"PASS %s expected=\S" % marker.replace(".", r"\."))
        for marker, wrong in (("startmoves", cs.START_MOVES.replace("a2a3,", "")), ("e7e5", cs.AFTER_E4_E5.replace(" e6 ", " - ")),
                              ("status.check", "ongoing"), ("promo.moves", cs.PROMO_MOVES.replace("a7a8n,", "")),
                              ("controller.moves", "19"), ("controller.apply", cs.AFTER_E4.replace(" e3 ", " - "))):
            again = self.run_rules(self.canned(**{marker: wrong}))
            self.assertEqual(again.returncode, 1, marker)
            self.assertIn("FAIL %s expected=" % marker, again.stdout)

    def test_the_last_line_sums_up_and_names_every_failed_marker(self) -> None:
        total = sum(len(marks) for _n, _s, marks in cs.rule_cases())
        ok = self.run_rules(self.canned())
        self.assertEqual(ok.stdout.splitlines()[-1], "rules: %d of %d markers passed; failed: none" % (total, total))
        bad = self.run_rules(self.canned(**{"start.p2": "399", "e7e5": "x"}))
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(bad.stdout.splitlines()[-1], "rules: %d of %d markers passed; failed: start.p2,e7e5" % (total - 2, total))
        self.assertLess(len(bad.stdout.splitlines()[-1]), 200)  # the stored output keeps only the last 2000 characters

    def test_a_failure_keeps_the_first_kb_of_the_scrubbed_log_in_the_platform_dir(self) -> None:
        proc = self.run_rules(self.canned(**{"start.p1": '{"accessToken": "SECRET-VALUE-123"} ' + "x" * 3000}))
        self.assertEqual(proc.returncode, 1)
        text = (self.platform / "rules-raw.txt").read_text()
        header, log = text.split("\n", 1)
        self.assertEqual(header, "case start: no Apex error")
        self.assertEqual(len(log), 1024)  # the log is far longer; only its first KB is kept
        self.assertIn("USER_DEBUG", log)
        self.assertIn("APEX_CODE", log)
        self.assertNotIn("SECRET-VALUE-123", text)
        self.assertNotIn("SECRET-VALUE-123", proc.stdout)
        self.assertIn("[redacted]", text)

    def test_the_raw_log_is_the_first_failing_case_and_an_error_replaces_a_missing_log(self) -> None:
        proc = self.run_rules(self.canned(**{"kiwipete.p1": {"error": "System.LimitException: Maximum CPU time exceeded"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual((self.platform / "rules-raw.txt").read_text().splitlines()[0],
                         "case kiwipete: Apex error: System.LimitException: Maximum CPU time exceeded")

    def test_no_raw_log_is_written_when_everything_passes_or_the_platform_dir_is_not_set(self) -> None:
        self.assertEqual(self.run_rules(self.canned()).returncode, 0)
        self.assertFalse((self.platform / "rules-raw.txt").exists())
        proc = self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(self.canned(**{"start.p2": "1"})), "E2E_PLATFORM_DIR": ""})
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(self.platform.exists())
        self.assertEqual(list(self.work.iterdir()), [])

    def test_a_failure_the_cli_itself_reports_shows_its_message(self) -> None:
        message = "Compilation failed at Line 2 column 22: Variable does not exist: SLChessEngine"
        proc = self.run_rules(self.canned(**{"start.p1": {"failure": message}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL start.p1 expected=20 got=%s" % message, proc.stdout)


class TestOracleAgainstTheReference(unittest.TestCase):
    """Every expected answer in the check is re-derived by the reference generator above; nothing here is copied from the check."""

    def test_the_reference_generator_reproduces_published_counts_the_table_does_not_hold(self) -> None:
        self.assertEqual(ref_perft(cs.START, 3), 8902)
        self.assertEqual(ref_perft("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2), 2039)
        self.assertEqual(ref_perft("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3), 2812)

    def test_every_perft_row_equals_the_reference(self) -> None:
        for name, fen, one, two in cs.PERFT:
            self.assertEqual(ref_perft(fen, 1), one, "%s depth 1" % name)
            if two is not None:
                self.assertEqual(ref_perft(fen, 2), two, "%s depth 2" % name)
        self.assertEqual(cs.START, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(dict((n, f) for n, f, _a, _b in cs.PERFT)["castle"], cs.CASTLE_FEN)

    def test_the_games_and_positions_end_the_way_the_check_says(self) -> None:
        for name, script, marks in cs.rule_cases():
            if name in ("foolsmate", "scholarsmate"):
                moves = re.findall(r"'([a-h][1-8][a-h][1-8][qrbn]?)'", re.search(r"List<String>\{([^}]*)\}", script).group(1))
                self.assertEqual(ref_status(ref_play(moves)), marks[0][1], name)
        self.assertEqual((ref_status(cs.STALEMATE_FEN), ref_legal(cs.STALEMATE_FEN)), ("stalemate", []))
        self.assertNotIn("e2e5", ref_legal(cs.START))  # the move the illegal case expects to be refused

    def play_game(self, moves: list[str], special: dict[int, str], refusal: tuple[int, str]) -> list[str]:
        """What the reference finds wrong with a game as the check states it (an empty list: every ply legal, every status as stated,
        the illegal move refused where the check says, and nothing left to play at the end)."""
        problems, fen = [], cs.START
        for ply, move in enumerate(moves, 1):
            if move not in ref_legal(fen):
                return problems + ["ply %d %s is not legal in %s" % (ply, move, fen)]
            fen = ref_apply(fen, move)
            if ref_status(fen) != special.get(ply, "ongoing"):
                problems.append("ply %d %s leaves %s, the check says %s" % (ply, move, ref_status(fen), special.get(ply, "ongoing")))
            if ply == refusal[0] and refusal[1] in ref_legal(fen):
                problems.append("%s is legal after ply %d, the check expects a refusal" % (refusal[1], ply))
        if ref_legal(fen) or ref_status(fen) not in ("checkmate", "stalemate"):
            problems.append("the game does not end in checkmate or stalemate: %s" % ref_status(fen))
        return problems

    def test_every_ply_of_every_game_is_legal_ends_as_stated_and_the_refusal_is_a_refusal(self) -> None:
        self.assertEqual([name for name, *_rest in cs.GAMES], ["game_opera", "game_second"])
        for name, moves, special, refusal in cs.GAMES:
            self.assertEqual(self.play_game(moves, special, refusal), [], name)
            self.assertIn(refusal[0], range(1, len(moves)))  # in the middle, not after the last ply
            self.assertEqual(max(special), len(moves))  # the last ply is always stated

    def test_the_opera_game_is_the_one_the_brief_gives(self) -> None:
        self.assertEqual(len(cs.OPERA), 33)
        self.assertEqual(cs.OPERA[:4] + cs.OPERA[-1:], ["e2e4", "e7e5", "g1f3", "d7d6", "d1d8"])  # 1. e4 e5 2. Nf3 d6 ... 17. Rd8#
        statuses, fen = {}, cs.START
        for ply, move in enumerate(cs.OPERA, 1):
            fen = ref_apply(fen, move)
            if ref_status(fen) != "ongoing":
                statuses[ply] = ref_status(fen)
        self.assertEqual(statuses, {21: "check", 29: "check", 31: "check", 33: "checkmate"})
        self.assertIn("e1c1", cs.OPERA)  # the queenside castle
        self.assertEqual(statuses, cs.GAMES[0][2])

    def test_the_second_game_has_an_en_passant_capture_a_promotion_and_ends_in_checkmate(self) -> None:
        en_passant, promotions, fen = [], [], cs.START
        for ply, move in enumerate(cs.SECOND, 1):
            board, _white, _castling, ep, *_rest = ref_parse(fen)
            if board[ref_sq(move[:2])].upper() == "P" and ref_sq(move[2:4]) == ep and ref_sq(move[2:4]) not in board:
                en_passant.append(ply)
            if len(move) == 5:
                promotions.append(ply)
            fen = ref_apply(fen, move)
        self.assertEqual((en_passant, promotions), ([5], [17]))
        self.assertEqual((ref_status(fen), ref_legal(fen)), ("checkmate", []))
        self.assertEqual(cs.GAMES[1][2], {11: "check", 17: "checkmate"})

    def test_a_mistyped_game_is_found_here(self) -> None:
        name, moves, special, refusal = cs.GAMES[1]
        broken = moves[:6] + ["d7d6"] + moves[7:]  # black's own pawn is not where that move needs it
        self.assertTrue(self.play_game(broken, special, refusal)[0].startswith("ply 7 d7d6 is not legal"))
        self.assertIn("leaves checkmate, the check says ongoing", self.play_game(moves, {11: "check"}, refusal)[0])
        self.assertIn("ply 16 g7g6 leaves ongoing, the check says checkmate", self.play_game(moves, {**special, 16: "checkmate"}, refusal)[0])
        self.assertIn("is legal after ply 11", self.play_game(moves, special, (11, "b8d7"))[0])
        self.assertIn("does not end in checkmate or stalemate", self.play_game(moves[:-1], {11: "check"}, refusal)[0])

    def test_every_marker_has_a_reference_answer_and_it_is_the_one_the_check_expects(self) -> None:
        answers = {}
        for name, fen, _one, two in cs.PERFT:
            answers[name + ".p1"] = str(ref_perft(fen, 1))
            if two is not None:
                answers[name + ".p2"] = str(ref_perft(fen, 2))
        for name, script, _marks in cs.rule_cases():
            if name in ("foolsmate", "scholarsmate"):
                moves = re.findall(r"'([a-h][1-8][a-h][1-8][qrbn]?)'", re.search(r"List<String>\{([^}]*)\}", script).group(1))
                answers[name] = ref_status(ref_play(moves))
        after_e4 = ref_apply(cs.START, "e2e4")
        answers.update({
            "stalemate.status": ref_status(cs.STALEMATE_FEN), "stalemate.moves": str(len(ref_legal(cs.STALEMATE_FEN))),
            "epfield": after_e4.split(" ")[3], "castle.board": ref_apply(cs.CASTLE_FEN, "e1g1").split(" ")[0],
            "startfen": cs.START, "startmoves": ",".join(ref_legal(cs.START)), "e2e4": after_e4, "e7e5": ref_apply(after_e4, "e7e5"),
            "status.start": ref_status(cs.START), "status.check": ref_status(cs.CHECK_FEN), "promo.moves": ",".join(ref_legal(cs.PROMO_FEN)),
            "controller.moves": str(len(ref_legal(cs.START))), "controller.apply": after_e4,
        })
        for name, moves, special, refusal in cs.GAMES:
            answers[name] = "ok" if not self.play_game(moves, special, refusal) else "broken"
        expected = {marker: value for _n, _s, marks in cs.rule_cases() for marker, value in marks if marker != "illegal"}
        self.assertEqual(sorted(answers), sorted(expected))  # a new marker needs a reference answer here
        self.assertEqual(answers, expected)

    def test_the_two_square_push_sets_the_en_passant_square_whether_or_not_a_capture_is_possible(self) -> None:
        self.assertEqual(ref_apply(cs.START, "e2e4").split(" ")[3], "e3")  # no black pawn can capture on e3
        self.assertEqual(ref_apply("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "a2a4").split(" ")[3], "a3")


class TestScriptsAgainstTheReference(unittest.TestCase):
    """The Apex scripts themselves, run in Python (APEX SUBSET) against the REFERENCE: what each prints is what the check expects."""

    def run_case(self, name: str, engine=None, script: str | None = None) -> dict[str, str]:
        engine = engine or reference_engine()
        source = script or next(s for n, s, _marks in cs.rule_cases() if n == name)
        return run_apex_script(source, SLChessEngine=engine, SLChessController=engine)

    def test_every_rule_script_prints_the_values_the_check_expects(self) -> None:
        for name, script, marks in cs.rule_cases():
            seen = run_apex_script(script, SLChessEngine=reference_engine(), SLChessController=reference_engine())
            self.assertEqual({marker: seen.get(marker) for marker, _expected in marks}, dict(marks), name)

    def test_the_translator_is_strict_about_what_it_does_not_know(self) -> None:
        with self.assertRaises(ValueError):
            apex_to_python("while (true) {\n}\n")
        self.assertEqual(run_apex_script("Integer n = 0;\nfor (Integer i = 0; i < 3; i++) {\nn += i;\n}\nSystem.debug('RESULT|n|' + n);\n"), {"n": "3"})

    def test_a_script_that_computes_something_other_than_the_expected_answer_is_found(self) -> None:
        start = next(s for n, s, _marks in cs.rule_cases() if n == "start")
        self.assertEqual(self.run_case("start", script=start)["start.p2"], "400")
        self.assertEqual(self.run_case("start", script=start.replace("total +=", "total ="))["start.p2"], "20")  # a depth-2 count that forgets to sum
        castle = next(s for n, s, _marks in cs.rule_cases() if n == "castling")
        self.assertNotEqual(self.run_case("castling", script=castle.replace("e1g1", "e1c1"))["castle.board"], "r3k2r/8/8/8/8/8/8/R4RK1")

    def test_the_game_scripts_fail_with_a_message_when_the_engine_is_wrong(self) -> None:
        engine = reference_engine()
        late_status = SimpleNamespace(**dict(vars(engine), status=lambda fen: AStr("check" if ref_status(fen) == "checkmate" else ref_status(fen))))
        self.assertEqual(self.run_case("game_opera", late_status)["game_opera"], "ply 33 d1d8 leaves status check, expected checkmate")
        self.assertEqual(self.run_case("game_second", late_status)["game_second"], "ply 17 c7c8r leaves status check, expected checkmate")
        no_promotion = SimpleNamespace(**dict(vars(engine), legalMoves=lambda fen: AList(AStr(m) for m in ref_legal(fen) if not m.endswith("r"))))
        self.assertEqual(self.run_case("game_second", no_promotion)["game_second"], "ply 17 c7c8r is not in legalMoves")
        accepting = SimpleNamespace(**dict(vars(engine), applyMove=lambda fen, move: AStr(ref_apply(fen, move) if move in ref_legal(fen) else fen)))
        self.assertEqual(self.run_case("game_opera", accepting)["game_opera"], "after ply 21 SLChessEngine.applyMove accepted the illegal move h7h6")

    def test_the_game_scripts_never_ask_the_controller_to_throw(self) -> None:
        # An AuraHandledException cannot be thrown or caught in anonymous Apex (an uncatchable System.LimitException on the real org,
        # 2026-10-16), so a controller built the idiomatic way must still pass: whatever the controller does with an illegal move is not graded.
        engine = reference_engine()

        def run(controller) -> str:
            script = next(s for n, s, _marks in cs.rule_cases() if n == "game_second")
            return run_apex_script(script, SLChessEngine=engine, SLChessController=controller)["game_second"]

        def wrapping(fen: str, move: str) -> AStr:
            try:
                return engine.applyMove(fen, move)
            except IllegalMoveException as exc:
                raise RuntimeError("AuraHandledException: %s" % exc)

        swallowing = SimpleNamespace(**dict(vars(engine), applyMove=lambda fen, move: AStr(ref_apply(fen, move) if move in ref_legal(fen) else fen)))
        self.assertEqual(run(SimpleNamespace(**dict(vars(engine), applyMove=wrapping))), "ok")
        self.assertEqual(run(swallowing), "ok")
        for name, script, _marks in cs.rule_cases():
            if name.startswith("game_"):
                self.assertNotIn("controllerThrew", script)
                self.assertNotRegex(script, r"SLChessController\.applyMove\(fen, '(?!\s*\+)[a-h][1-8][a-h][1-8]'\)")

    def test_the_game_scripts_stop_at_the_first_problem_and_check_nothing_is_left_to_play(self) -> None:
        engine = reference_engine()
        more = SimpleNamespace(**dict(vars(engine), legalMoves=lambda fen: AList([AStr("a2a3")]) if ref_status(fen) == "checkmate" else engine.legalMoves(fen)))
        self.assertEqual(self.run_case("game_second", more)["game_second"], "the last position still has 1 legal moves")

    def test_the_selftest_probe_script_prints_what_the_probe_class_returns(self) -> None:
        for answer, expected in ((2, "2"), (3, "3")):
            seen = run_apex_script(cs.probe_script("SLChessProbe"), SLChessProbe=SimpleNamespace(two=lambda answer=answer: answer))
            self.assertEqual(seen, {"probe": expected})
        self.assertIn("RESULT|probe|", cs.probe_script("SLChessProbe"))


class TestSelftest(FakeOrg):
    def run_selftest(self, probe="2", **env) -> subprocess.CompletedProcess:
        canned = self.tmp / "probe.json"
        canned.write_text(json.dumps({"probe": probe}))
        env.setdefault("FAKE_SF_APEX", str(canned))
        return self.run_check("selftest", "--org", "de", "--prefix", "SLChess", env=env)

    def test_a_rejected_deploy_prints_the_component_failure_and_leaves_the_org_as_it_was(self) -> None:
        # The real org rejected the first probe app page ("a parent region enabling that mode doesn't exist") and the rehearsal printed an empty reason.
        proc = self.run_selftest(FAKE_SF_DEPLOY_PROBLEM="FlexiPage|SLChess_Probe|The 'main' region specifies mode 'REPLACE' but no parent region enables it")
        self.assertNotEqual(proc.returncode, 0, self.out(proc))
        self.assertRegex(proc.stdout, r"(?m)^FAIL deploy: status=Failed FlexiPage SLChess_Probe: The 'main' region specifies mode")
        self.assertRegex(proc.stdout, step_line("cleanup"))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))

    def test_rehearsal_deploys_tests_runs_anonymous_apex_and_removes_the_probe(self) -> None:
        proc = self.run_selftest()
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("preflight", "snapshot", "deploy", "deployed", "tests", "apex-run", "cleanup"):
            self.assertRegex(proc.stdout, step_line(step))
        self.assertTrue(proc.stdout.startswith("selftest proves, in order: preflight"), proc.stdout[:80])
        self.assertIn("PASS apex-run: RESULT|probe| expected=2 got=2", proc.stdout)
        for step in ("deployed", "tests"):
            self.assertRegex(proc.stdout, r"(?m)^PASS %s \(\d+ s of the case's \d+ s check ceiling\): " % step)
        self.assertIn("tab SLChess_Probe; app SLChess_Probe; app page SLChess_Probe", proc.stdout)
        (run,) = [c for c in self.calls() if "--file" in c["argv"]]
        self.assertEqual((run["apex_markers"], run["argv"][run["argv"].index("--target-org") + 1]), (["probe"], "de"))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        self.assertEqual(state["types"], BASE_TYPES)
        (add,) = self.deploys(destructive=False)  # one deploy holds the class, its test, the component, the tab, the app and the page
        self.assertEqual(add["argv"][add["argv"].index("--target-org") + 1], "de")
        (rm,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(rm), {"ApexClass": ["SLChessProbe", "SLChessProbeTest"], "LightningComponentBundle": ["slChessProbe"],
                                              "CustomTab": ["SLChess_Probe"], "CustomApplication": ["SLChess_Probe"], "FlexiPage": ["SLChess_Probe"]})

    def test_the_one_deploy_makes_the_tab_the_app_and_the_page_and_a_removal_that_does_nothing_is_reported(self) -> None:
        proc = self.run_selftest(FAKE_SF_NOOP_DESTRUCTIVE="1")  # the removal does nothing, so the org still shows what the deploy made
        self.assertEqual(proc.returncode, 1)
        state = self.state()
        self.assertEqual({kind: state["types"][kind][-1] for kind in ("CustomTab", "CustomApplication", "FlexiPage")},
                         {kind: "SLChess_Probe" for kind in ("CustomTab", "CustomApplication", "FlexiPage")})
        self.assertIn("extra CustomApplication SLChess_Probe", proc.stdout)
        self.assertIn("MANUAL CLEANUP NEEDED: remove the SLChess* and slChess* items (CustomApplication, CustomTab, FlexiPage, "
                      "LightningComponentBundle, ApexClass) from org 'de'", proc.stdout)

    def test_a_probe_that_answers_anything_but_two_fails_the_rehearsal_and_still_cleans_up(self) -> None:
        proc = self.run_selftest(probe="3")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run: RESULT|probe| expected=2 got=3", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))
        self.assertEqual(self.state()["types"], BASE_TYPES)

    def test_the_apex_run_step_reports_the_same_errors_rules_does(self) -> None:
        proc = self.run_selftest(probe={"compileProblem": "Variable does not exist: SLChessProbe"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run: RESULT|probe| expected=2 got=compile error: Variable does not exist: SLChessProbe", proc.stdout)
        proc = self.run_selftest(FAKE_SF_APEX=str(self.tmp / "none.json"), FAKE_SF_FAIL="apex")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run:", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)

    def test_the_probe_is_an_aura_enabled_class_and_a_component_that_imports_it(self) -> None:
        names = cs.write_probe(self.tmp / "probe-project", "SLChess")
        classes = self.tmp / "probe-project" / "force-app" / "main" / "default"
        self.assertEqual(names, {"class": "SLChessProbe", "test": "SLChessProbeTest", "bundle": "slChessProbe", "tab": "SLChess_Probe",
                                 "app": "SLChess_Probe", "page": "SLChess_Probe"})
        self.assertIn("@AuraEnabled(cacheable=true) public static Integer two()", (classes / "classes" / "SLChessProbe.cls").read_text())
        self.assertIn("import two from '@salesforce/apex/SLChessProbe.two';", (classes / "lwc" / "slChessProbe" / "slChessProbe.js").read_text())
        self.assertIn("SLChessProbe.two()", (classes / "classes" / "SLChessProbeTest.cls").read_text())

    def test_the_probe_tab_app_and_page_are_well_formed_metadata_in_the_shape_the_metadata_api_defines(self) -> None:
        cs.write_probe(self.tmp / "probe-project", "SLChess")
        base = self.tmp / "probe-project" / "force-app" / "main" / "default"
        ns = "{http://soap.sforce.com/2006/04/metadata}"

        def parse(rel: str) -> ET.Element:
            root = ET.parse(base / rel).getroot()
            self.assertTrue(root.tag.startswith(ns), rel)
            return root

        def text(root: ET.Element, *path: str) -> list[str]:
            return [e.text for e in root.findall("/".join(ns + p for p in path))]

        meta = parse("lwc/slChessProbe/slChessProbe.js-meta.xml")
        self.assertEqual((text(meta, "isExposed"), text(meta, "targets", "target")), (["true"], ["lightning__Tab", "lightning__AppPage"]))
        tab = parse("tabs/SLChess_Probe.tab-meta.xml")
        self.assertEqual((tab.tag, text(tab, "lwcComponent"), len(text(tab, "label")), len(text(tab, "motif"))), (ns + "CustomTab", ["slChessProbe"], 1, 1))
        app = parse("applications/SLChess_Probe.app-meta.xml")
        self.assertEqual((app.tag, text(app, "tabs"), text(app, "uiType"), text(app, "navType"), text(app, "formFactors"), len(text(app, "label"))),
                         (ns + "CustomApplication", ["SLChess_Probe"], ["Lightning"], ["Standard"], ["Large"], 1))
        page = parse("flexipages/SLChess_Probe.flexipage-meta.xml")
        self.assertEqual((page.tag, text(page, "type"), text(page, "template", "name"), text(page, "masterLabel")),
                         (ns + "FlexiPage", ["AppPage"], ["flexipage:defaultAppHomeTemplate"], ["SLChess probe"]))
        (region,) = page.findall(ns + "flexiPageRegions")
        self.assertEqual((text(region, "name"), text(region, "type"), text(region, "itemInstances", "componentInstance", "componentName")),
                         (["main"], ["Region"], ["c:slChessProbe"]))
        # every file the probe writes sits where `project` allows it, under the case prefix
        self.assertEqual(sorted(p.name for p in base.rglob("*-meta.xml")), sorted(
            ["SLChessProbe.cls-meta.xml", "SLChessProbeTest.cls-meta.xml", "slChessProbe.js-meta.xml", "SLChess_Probe.tab-meta.xml",
             "SLChess_Probe.app-meta.xml", "SLChess_Probe.flexipage-meta.xml"]))

    def test_a_failing_probe_test_still_cleans_up(self) -> None:
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 1, "failing": 1}))
        proc = self.run_selftest(FAKE_SF_TESTS=str(results))
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, step_line("tests", ok=False))
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))

    def test_a_failed_deploy_still_attempts_cleanup(self) -> None:
        proc = self.run_selftest(FAKE_SF_FAIL="deploy")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL deploy:", proc.stdout)
        self.assertEqual(len(self.deploys(destructive=False)), 1)  # the one add attempt, which failed
        self.assertIn("PASS cleanup:", proc.stdout)  # snapshot was taken, so cleanup ran and verified an unchanged org

    def test_a_cleanup_that_cannot_verify_is_loud(self) -> None:
        proc = self.run_selftest(FAKE_SF_NOOP_DESTRUCTIVE="1")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("MANUAL CLEANUP NEEDED", proc.stdout)

    def test_a_dirty_org_stops_before_any_deploy(self) -> None:
        self.add(apex=["SLChessLeftover"])
        proc = self.run_selftest()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])
        self.assertIn("SLChessLeftover", self.state()["apex_classes"])

    def test_keep_needs_the_reference(self) -> None:
        proc = self.run_check("selftest", "--org", "de", "--keep")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--keep needs --reference", proc.stderr)
        self.assertEqual(self.calls(), [])


class TestSelftestReference(FakeOrg):
    """`selftest --reference`: a known-good project is deployed, graded by the four checks the case runs and removed (or kept)."""

    def canned(self, **override) -> str:
        values = {marker: expected for _name, _script, marks in cs.rule_cases() for marker, expected in marks}
        values.update(override)
        path = self.tmp / "apex.json"
        path.write_text(json.dumps(values))
        return str(path)

    def run_reference(self, *extra: str, project: Path | None = None, **override) -> subprocess.CompletedProcess:
        env = {"FAKE_SF_APEX": self.canned(**override.pop("canned", {}))}
        env.update(override)
        project = project or make_project(self.tmp)
        return self.run_check("selftest", "--org", "de", "--reference", str(project), *extra, env=env)

    def test_the_whole_flow_runs_against_the_fake_and_the_org_is_back_at_its_baseline(self) -> None:
        project = make_project(self.tmp)
        before = sorted(str(p.relative_to(project)) for p in project.rglob("*"))
        proc = self.run_reference(project=project)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("fixture", "preflight", "snapshot", "deploy", "deployed", "tests", "rules", "cleanup"):
            self.assertRegex(proc.stdout, step_line(step))
        self.assertTrue(proc.stdout.startswith("selftest proves, in order: fixture"), proc.stdout[:60])
        self.assertIn("rules: %d of %d markers passed; failed: none" % (self.markers(), self.markers()), proc.stdout)
        self.assertIn("PASS game_opera expected=ok got=ok", proc.stdout)
        self.assertIn("PASS SLChessEngineTest: outcome=Passed testsRan=10 failing=0; PASS tests: 10 ran, 0 failing, need at least 8", proc.stdout)
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"]), state["types"]), (sorted(BASE_APEX), sorted(BASE_LWC), BASE_TYPES))
        (add,) = self.deploys(destructive=False)
        self.assertEqual(add["argv"][:3], ["project", "deploy", "start"])
        self.assertIn("force-app", add["argv"])
        self.assertNotEqual(Path(add["cwd"]).resolve(), project.resolve())  # deployed from a copy: sf may write beside the project
        self.assertEqual(sorted(str(p.relative_to(project)) for p in project.rglob("*")), before)  # the fixture is untouched
        (rm,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(rm), {"CustomApplication": ["SLChess"], "CustomTab": ["SLChess_Board"], "LightningComponentBundle": ["slChessBoard"],
                                              "ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"]})

    def markers(self) -> int:
        return sum(len(marks) for _n, _s, marks in cs.rule_cases())

    def test_deployed_tests_and_rules_print_their_seconds_against_the_cases_check_ceiling(self) -> None:
        proc = self.run_reference()
        self.assertEqual(proc.returncode, 0, self.out(proc))
        ceiling = json.loads((E2E / "cases.json").read_text())["chess-salesforce"]["platform"]["check_timeout"]
        for step in ("deployed", "tests", "rules"):
            self.assertRegex(proc.stdout, r"(?m)^PASS %s \(\d+ s of the case's %d s check ceiling\): " % (step, ceiling))
        for step in ("fixture", "preflight", "snapshot", "deploy", "cleanup"):  # the other steps are not checks the harness times
            self.assertRegex(proc.stdout, r"(?m)^PASS %s: " % step)
        failing = self.run_reference(canned={"start.p2": "399"})
        self.assertRegex(failing.stdout, r"(?m)^FAIL rules \(\d+ s of the case's %d s check ceiling\): " % ceiling)

    def test_a_ceiling_the_case_does_not_give_is_none_not_a_made_up_number(self) -> None:
        original = cs.CASES
        self.addCleanup(setattr, cs, "CASES", original)
        cs.CASES = self.tmp / "none.json"
        self.assertIsNone(cs.check_ceiling())
        cs.CASES.write_text(json.dumps({"chess-salesforce": {"platform": {}}}))
        self.assertIsNone(cs.check_ceiling())

    def test_the_four_graded_checks_run_with_the_cases_arguments(self) -> None:
        self.assertEqual(self.run_reference().returncode, 0)
        calls = [c["argv"] for c in self.calls()]
        queries = [a[a.index("-q") + 1] for a in calls if a[:2] == ["data", "query"]]
        self.assertIn("SELECT DeveloperName FROM CustomTab WHERE DeveloperName LIKE 'SLChess%'", queries)  # deployed, with the tab and the app
        tests = [a for a in calls if a[:3] == ["apex", "run", "test"]]
        self.assertEqual([a[a.index("--class-names") + 1] for a in tests], ["SLChessEngineTest"])
        self.assertEqual(len([a for a in calls if a[:2] == ["apex", "run"] and "--file" in a]), len(cs.rule_cases()))
        case = json.loads((E2E / "cases.json").read_text())["chess-salesforce"]
        self.assertEqual(cs.CASE_MIN_TESTS, int(re.search(r"--min-tests (\d+)", next(c for c in case["checks"] if " tests " in c))[1]))

    def test_a_reference_that_fails_the_tests_check_does_not_pass_and_is_still_removed(self) -> None:
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 10, "failing": 1}))
        proc = self.run_reference(FAKE_SF_TESTS=str(results))
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, step_line("tests", ok=False))
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(self.state()["types"], BASE_TYPES)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))

    def test_a_wrong_rules_answer_fails_names_the_marker_and_the_org_is_still_cleaned(self) -> None:
        proc = self.run_reference(canned={"game_second": "ply 9 a6c8 is not in legalMoves", "start.p2": "399"})
        self.assertEqual(proc.returncode, 1)
        self.assertRegex(proc.stdout, step_line("rules", ok=False) + "rules: %d of %d markers passed; failed: start.p2,game_second"
                         % (self.markers() - 2, self.markers()))
        self.assertIn("    FAIL start.p2 expected=400 got=399", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(self.state()["types"], BASE_TYPES)

    def test_a_failed_deploy_stops_the_checks_and_cleans(self) -> None:
        proc = self.run_reference(FAKE_SF_FAIL="deploy")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL deploy:", proc.stdout)
        self.assertNotIn("deployed:", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)

    def test_a_missing_reference_fails_with_a_clear_message_before_any_sf_call(self) -> None:
        proc = self.run_check("selftest", "--org", "de", "--reference", str(self.tmp / "no-such-reference"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL fixture: the reference project %s does not exist" % (self.tmp / "no-such-reference"), proc.stdout)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.platform.exists())

    def test_an_incomplete_reference_fails_and_names_what_is_missing_before_any_sf_call(self) -> None:
        for files, missing in (({"tabs/SLChess_Board.tab-meta.xml": None}, "no force-app/**/tabs/SLChess_Board.tab-meta.xml"),
                               ({"applications/SLChess.app-meta.xml": None}, "no force-app/**/applications/SLChess.app-meta.xml")):
            proc = self.run_check("selftest", "--org", "de", "--reference", str(make_project(self.tmp, files=files)))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("FAIL fixture: the reference project %s is incomplete: " % (self.tmp / "proj") , proc.stdout)
            self.assertIn(missing, proc.stdout)
        empty = self.tmp / "empty"
        empty.mkdir()
        proc = self.run_check("selftest", "--org", "de", "--reference", str(empty))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("incomplete: sfdx-project.json missing or not JSON", proc.stdout)
        self.assertEqual(self.calls(), [])

    def test_a_dirty_org_stops_the_reference_flow_before_any_deploy(self) -> None:
        self.add(CustomTab=["SLChess_Board"])
        proc = self.run_reference()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])
        self.assertIn("CustomTab SLChess_Board", proc.stdout)
        self.assertIn("SLChess_Board", self.state()["types"]["CustomTab"])  # not ours to remove: the snapshot never happened

    def test_keep_never_cleans_prints_the_command_and_exits_zero_when_the_checks_pass(self) -> None:
        proc = self.run_reference("--keep", "--platform-dir", str(self.tmp / "kept"))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(self.deploys(destructive=True), [])
        self.assertNotIn("cleanup:", proc.stdout.replace("cleanup --org", ""))
        state = self.state()
        self.assertTrue({"SLChessEngine", "SLChessController", "SLChessEngineTest"} <= set(state["apex_classes"]))
        self.assertIn("SLChess_Board", state["types"]["CustomTab"])
        self.assertIn("SLChess", state["types"]["CustomApplication"])
        self.assertIn("slChessBoard", state["lwc"])
        self.assertIn("KEPT: nothing was removed from org 'de'", proc.stdout)
        self.assertIn("/lightning/n/SLChess_Board", proc.stdout)
        command = [line for line in proc.stdout.splitlines() if line.startswith("python3 ")]
        self.assertEqual(len(command), 1)
        argv = shlex.split(command[0])
        self.assertEqual((argv[0], Path(argv[1]).name, argv[2:6]), ("python3", "chess_salesforce.py", ["cleanup", "--org", "de", "--prefix"]))
        self.assertEqual(Path(argv[1]).resolve(), CHECKS.resolve())
        # the command it prints removes the app and verifies the org against the snapshot that was kept
        by_hand = self.run_check(*argv[2:])
        self.assertEqual(by_hand.returncode, 0, self.out(by_hand))
        self.assertEqual(self.state()["types"], BASE_TYPES)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))

    def test_keep_with_a_failing_check_exits_one_and_still_keeps_and_prints_the_command(self) -> None:
        proc = self.run_reference("--keep", "--platform-dir", str(self.tmp / "kept"), canned={"start.p2": "399"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(destructive=True), [])
        self.assertRegex(proc.stdout, step_line("rules", ok=False))
        self.assertIn("cleanup --org de --prefix SLChess --platform-dir", proc.stdout)

    def test_keep_needs_a_platform_dir_so_the_snapshot_cleanup_needs_later_is_never_left_in_tmpdir(self) -> None:
        proc = self.run_reference("--keep")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--keep needs --platform-dir", proc.stderr)
        self.assertEqual(self.calls(), [])  # refused before any sf call
        self.assertEqual([p.name for p in (self.tmp / "tmpdir").iterdir()], [])

    def test_keep_after_a_failed_snapshot_has_nothing_to_keep_and_leaves_no_directory_behind(self) -> None:
        self.add(apex=["SLChessLeftover"])
        kept = self.tmp / "kept"
        proc = self.run_reference("--keep", "--platform-dir", str(kept))
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn("KEPT", proc.stdout)
        self.assertEqual([p.name for p in (self.tmp / "tmpdir").iterdir()], [])
        self.assertFalse(kept.exists())

    def test_a_relative_platform_dir_is_printed_as_an_absolute_path_so_the_command_works_from_anywhere(self) -> None:
        proc = self.run_reference("--keep", "--platform-dir", "kept-relative")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        command = [line for line in proc.stdout.splitlines() if line.startswith("python3 ")]
        self.assertEqual(shlex.split(command[0])[-1], str(self.work / "kept-relative"))
        elsewhere = self.run_check(*shlex.split(command[0])[2:], cwd=self.tmp)
        self.assertEqual(elsewhere.returncode, 0, self.out(elsewhere))
        self.assertEqual(self.state()["types"], BASE_TYPES)

    def test_keep_after_a_failed_deploy_says_nothing_is_kept_and_takes_the_cleanup_path(self) -> None:
        kept = self.tmp / "kept"
        proc = self.run_reference("--keep", "--platform-dir", str(kept), FAKE_SF_FAIL="deploy")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL deploy:", proc.stdout)
        self.assertNotIn("KEPT", proc.stdout)  # nothing was deployed, so no app stays "there to open"
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(self.state()["types"], BASE_TYPES)
        self.assertTrue(json.loads((kept / "cleanup.json").read_text())["verified"])

    def test_keep_uses_the_platform_dir_it_is_given_for_the_snapshot(self) -> None:
        kept = self.tmp / "kept"
        proc = self.run_reference("--keep", "--platform-dir", str(kept))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertTrue((kept / "before.json").is_file())
        self.assertIn("--platform-dir %s" % kept, proc.stdout)

    def test_a_failure_leaves_the_raw_log_where_the_platform_dir_points(self) -> None:
        kept = self.tmp / "kept"
        proc = self.run_reference("--keep", "--platform-dir", str(kept), canned={"start.p2": "399"})
        self.assertEqual(proc.returncode, 1)
        self.assertTrue((kept / "rules-raw.txt").is_file())

    def test_the_committed_reference_fixture_is_there_passes_project_and_runs_the_whole_flow(self) -> None:
        self.assertTrue(cs.REFERENCE.is_dir(), "the reference fixture %s is missing (worker K3 writes it)" % cs.REFERENCE)
        for needed in ("sfdx-project.json", "force-app", "README.md"):
            self.assertTrue((cs.REFERENCE / needed).exists(), "the reference fixture has no %s" % needed)
        ok, message = cs.do_project("SLChess", cs.REFERENCE)
        self.assertTrue(ok, message)
        proc = self.run_check("selftest", "--org", "de", "--reference", env={"FAKE_SF_APEX": self.canned()})
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("PASS fixture:", proc.stdout)
        self.assertEqual(self.state()["types"], BASE_TYPES)


class TestModelStyleDeploy(FakeOrg):
    """What a model does: `sf project deploy start --source-dir force-app` of its own project, with a tab, an app and maybe a page in
    it. The fake must record them in the org (a deploy that counts zero would let `deployed` and the cleanup be proven against nothing)."""
    PAGE = {"flexipages/SLChess_Home.flexipage-meta.xml": PAGE_XML}

    def model_deploys(self, **kwargs) -> dict:
        project = make_project(self.tmp, **kwargs)
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["status"]), (0, 0), doc)
        return doc["result"]

    def test_the_tab_and_app_a_model_deploys_are_in_the_org_and_counted(self) -> None:
        result = self.model_deploys()
        self.assertEqual(result["numberComponentsDeployed"], 6)  # three classes, the component, the tab and the app
        types = self.state()["types"]
        self.assertEqual((types["CustomTab"][-1], types["CustomApplication"][-1]), ("SLChess_Board", "SLChess"))
        self.assertEqual(types["FlexiPage"], BASE_TYPES["FlexiPage"])  # no page in the project, no page in the org

    def test_deployed_sees_the_tab_and_app_only_after_the_model_deployed_them(self) -> None:
        self.snapshot()
        before = self.run_check("deployed", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(before.returncode, 1)
        self.assertIn("CustomTab SLChess_Board not found", self.out(before))
        self.assertIn("CustomApplication SLChess not found", self.out(before))
        self.model_deploys()
        after = self.run_check("deployed", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(after.returncode, 0, self.out(after))
        self.assertIn("tab SLChess_Board; app SLChess", after.stdout)

    def test_the_app_page_a_model_deploys_is_seen_by_deployed_when_it_is_named(self) -> None:
        self.model_deploys(files=self.PAGE)
        self.assertIn("SLChess_Home", self.state()["types"]["FlexiPage"])
        proc = self.run_check("deployed", "--org", "de", "--prefix", "SLChess", "--pages", "SLChess_Home")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("app page SLChess_Home", proc.stdout)

    def test_cleanup_removes_the_tab_app_and_page_a_model_deployed_and_the_org_is_back_at_its_baseline(self) -> None:
        self.snapshot()
        self.model_deploys(files=self.PAGE)
        proc = self.run_check("cleanup", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        (call,) = self.deploys(destructive=True)
        self.assertEqual(self.destroyed(call), {"CustomApplication": ["SLChess"], "CustomTab": ["SLChess_Board"], "FlexiPage": ["SLChess_Home"],
                                                "LightningComponentBundle": ["slChessBoard"],
                                                "ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"]})
        state = self.state()
        self.assertEqual((state["types"], sorted(state["apex_classes"]), sorted(state["lwc"])), (BASE_TYPES, sorted(BASE_APEX), sorted(BASE_LWC)))
        self.assertEqual(self.run_check("deployed", "--org", "de", "--prefix", "SLChess").returncode, 1)  # and deployed no longer finds them

    def test_a_deploy_of_only_the_tab_folder_makes_only_the_tab(self) -> None:
        project = make_project(self.tmp)
        code, doc = self.sf("project", "deploy", "start", "--source-dir", "force-app/main/default/tabs", "--target-org", "de", cwd=project)
        self.assertEqual((code, doc["result"]["numberComponentsDeployed"]), (0, 1))
        types = self.state()["types"]
        self.assertEqual((types["CustomTab"][-1], types["CustomApplication"]), ("SLChess_Board", BASE_TYPES["CustomApplication"]))


class TestReferenceFixture(unittest.TestCase):
    """The committed reference project (the known-good answer the rehearsal grades): the CPU lines and the README's known limit."""
    CLASSES = cs.REFERENCE / "force-app" / "main" / "default" / "classes"

    def test_the_two_heaviest_enumerations_print_their_cpu_use_right_after_the_count(self) -> None:
        source = (self.CLASSES / "SLChessEngineTest.cls").read_text()
        for method, count in (("perftKiwipete", "System.assertEquals(2039, perft2(KIWIPETE));"),
                              ("perftPosition5", "System.assertEquals(1486, perft2(POSITION_5));")):
            body = re.search(r"static void %s\(\) \{\n(.*?)\n    \}\n" % method, source, re.DOTALL)[1]
            lines = [line.strip() for line in body.splitlines()]
            self.assertEqual(lines[lines.index(count) + 1], "System.debug('CPU ' + Limits.getCpuTime());", method)
        self.assertEqual(source.count("Limits.getCpuTime()"), 2)  # and nowhere else

    def test_the_readme_states_the_known_limit_that_a_host_with_file_access_could_read_it(self) -> None:
        readme = " ".join((cs.REFERENCE / "README.md").read_text().split())
        self.assertIn("Known limit: a host with file access could still read it", readme)
        self.assertIn("greps the run's commands for `chess-salesforce-reference`", readme)


class TestCaseDefinition(unittest.TestCase):
    """The prompt states what the checks grade, and the case carries the note a resumed model needs (cases.json, `chess-salesforce`)."""

    def setUp(self) -> None:
        self.case = json.loads((E2E / "cases.json").read_text())["chess-salesforce"]
        self.prompt = self.case["prompt"]

    def test_the_prompt_states_every_convention_the_checks_grade(self) -> None:
        for sentence in (
                "The en-passant target square is set after every two-square pawn push, whether or not a capture is possible",
                "the king's two-square move: `e1g1`, `e1c1`, `e8g8`, `e8c8`",
                "the current directory itself, not a subfolder", "`sfdx-project.json`", "`force-app/`",
                "`SLChessController` has `@AuraEnabled public static` methods `legalMoves(String fen)`, returning a `List<String>`",
                "`applyMove(String fen, String move)`, returning the new FEN as a `String`",
                "depth-2 legal-move enumeration", "inside one transaction"):
            self.assertIn(sentence, self.prompt)

    def test_the_prompt_asks_for_a_board_a_person_can_open_and_play(self) -> None:
        for sentence in (
                "`tabs/SLChess_Board.tab-meta.xml` that is a Lightning component tab (`<lwcComponent>slChessBoard</lwcComponent>`; the component's meta file "
                "exposes the `lightning__Tab` target)",
                "a Lightning app `applications/SLChess.app-meta.xml` (standard navigation, containing that tab)",
                "if you want one, a Lightning app page `flexipages/SLChess_<Name>.flexipage-meta.xml` (then the component's meta file also exposes `lightning__AppPage`)",
                "all named with the prefix `SLChess`", "Create no other metadata (no custom objects, fields, permission sets, static resources, triggers, "
                "profiles, labels or flows), and do not change profiles or permission sets",
                "a game two people can play by turns on one screen", "whose turn it is and the game status (check, checkmate, stalemate)",
                "refuses an illegal destination", "lets a pawn promote (queen is acceptable as the default)", "has a New game button",
                "`status(String fen)`, returning `ongoing`, `check`, `checkmate` or `stalemate` as a `String`, so that the grader can call them",
                "The grader calls `SLChessController` only with legal moves and calls `SLChessEngine.applyMove` directly for an illegal one",
                "so the controller may report an illegal move however suits the board (for example by throwing an `AuraHandledException`)",
                "graded by playing complete games, ply by ply, through `SLChessController` (`legalMoves`, `applyMove` and `status`)",
                "a whole game of about 35 plies played through `SLChessController`"):
            self.assertIn(sentence, self.prompt)

    def test_the_prompt_makes_the_exception_public_and_pins_only_the_commands_that_talk_to_the_org(self) -> None:
        self.assertIn("(a public exception class you define inside `SLChessEngine`)", self.prompt)
        self.assertIn("Use `--target-org de` on every `sf` command that talks to the org;", self.prompt)
        self.assertNotIn("on every `sf` command;", self.prompt)

    def test_the_prompt_allows_exactly_the_kinds_of_metadata_the_checks_and_the_cleanup_handle(self) -> None:
        allowed = {"tabs": "CustomTab", "applications": "CustomApplication", "flexipages": "FlexiPage"}
        self.assertEqual(sorted(cs.SCOPED_META), sorted(allowed))
        self.assertEqual(sorted(set(allowed.values()) | {"LightningComponentBundle", "ApexClass"}), sorted(cs.REMOVABLE))
        for folder in allowed:
            self.assertIn("`%s/SLChess" % folder, self.prompt)
        self.assertEqual(cs.expected_names("SLChess"), {"classes": ["SLChessEngine", "SLChessController"], "lwc": ["slChessBoard"],
                                                         "tabs": ["SLChess_Board"], "apps": ["SLChess"], "pages": []})

    def test_the_test_count_the_prompt_asks_for_is_the_one_the_check_requires(self) -> None:
        asked = int(re.search(r"at least (\d+) Apex test methods", self.prompt).group(1))
        required = int(re.search(r"--min-tests (\d+)", next(c for c in self.case["checks"] if " tests " in c)).group(1))
        self.assertEqual(asked, required)

    def test_the_case_gives_its_checks_longer_than_the_harness_default_and_the_rehearsal_reports_against_it(self) -> None:
        timeout = self.case["platform"]["check_timeout"]
        self.assertTrue(isinstance(timeout, int) and not isinstance(timeout, bool), timeout)
        self.assertTrue(60 <= timeout <= 3600, timeout)  # run.py accepts 60..3600 seconds
        self.assertGreater(timeout, 180)  # rules is 19 sequential `sf apex run` calls, two of them whole games: the default 180 is too tight
        self.assertEqual(cs.check_ceiling(), timeout)

    def test_the_prompt_does_not_mention_the_platform_machinery(self) -> None:
        for word in ("wrapper", "guard", "sf_guard", "model_bin", "harness", "PATH"):
            self.assertNotIn(word, self.prompt)

    def test_the_checks_are_the_same_subcommands_as_before(self) -> None:
        self.assertEqual([c.split()[2] for c in self.case["checks"]], ["project", "deployed", "tests", "rules"])
        self.assertNotIn("--tabs", self.case["checks"][1])  # the defaults are the names the prompt gives

    def test_the_resume_note_tells_a_resumed_model_its_deployment_is_gone(self) -> None:
        note = self.case["platform"]["resume_note"]
        self.assertIsInstance(note, str)
        for part in ("reset to its baseline", "removed", "Deploy again from your source", "run tests in the org"):
            self.assertIn(part, note)
        self.assertNotIn("guard", note.lower())

    def test_the_case_keeps_a_working_app_of_a_run_that_did_not_finish_by_its_org_checks_and_not_by_project(self) -> None:
        """Owner 2026-10-17: the app stays in the org to be played. Run 2 hit its session cap with `deployed`, `tests` and `rules`
        passing; `project` reads the work folder and needs a commit, which an unfinished run may not have made."""
        sys.path.insert(0, str(E2E))
        try:
            import run
        finally:
            sys.path.remove(str(E2E))
        platform = self.case["platform"]
        self.assertEqual(platform["keep_checks"], ["deployed", "tests", "rules"])
        self.assertIs(run.validate_platform("chess-salesforce", platform), platform)
        run.refuse_unmatched_keep_checks("chess-salesforce", platform, self.case["checks"])  # each word names exactly one check
        self.assertEqual(sum("project" in c.split() for c in self.case["checks"]), 1)
        self.assertNotIn("project", platform["keep_checks"])
        kept = platform["resume_note_kept"]
        self.assertIn("still in the org", kept)
        self.assertIn("check it before you deploy again", kept)
        self.assertNotIn("reset", kept)
        self.assertNotIn("guard", kept.lower())


class TestNoCredentialsAnywhere(FakeOrg):
    def test_the_token_never_reaches_any_output_or_file_and_org_display_is_never_called(self) -> None:
        outputs = []
        env = {"FAKE_SF_WARN": "1"}
        canned = self.tmp / "apex.json"
        canned.write_text(json.dumps(dict({m: e for _n, _s, marks in cs.rule_cases() for m, e in marks}, probe="2")))
        project = make_project(self.tmp)
        steps = [
            ("preflight", "--org", "de"), ("snapshot", "--org", "de"),
        ]
        for step in steps:
            outputs.append(self.run_check(*step, env=env))
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"], CustomTab=["SLChess_Board"],
                 CustomApplication=["SLChess"])
        outputs.append(self.run_check("project", "--org", "de", cwd=project, env=env))
        outputs.append(self.run_check("deployed", "--org", "de", env=env))
        outputs.append(self.run_check("tests", "--org", "de", "--min-tests", "8", env=env))
        outputs.append(self.run_check("rules", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned))))
        outputs.append(self.run_check("cleanup", "--org", "de", env=env))
        outputs.append(self.run_check("selftest", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned))))
        outputs.append(self.run_check("selftest", "--org", "de", "--reference", str(project), env=dict(env, FAKE_SF_APEX=str(canned))))
        failing = self.run_check("rules", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned), FAKE_SF_FAIL="apex"))
        outputs.append(failing)
        self.assertEqual([p.returncode for p in outputs[:-1]], [0] * (len(outputs) - 1), [self.out(p) for p in outputs])
        for proc in outputs:
            self.assertNotIn(TOKEN, proc.stdout)
            self.assertNotIn(TOKEN, proc.stderr)
        for path in self.tmp.rglob("*"):
            if path.is_file() and path != self.shim / "sf":
                self.assertNotIn(TOKEN, path.read_text(errors="replace"), str(path))
        calls = self.calls()
        self.assertGreater(len(calls), 20)
        self.assertEqual([c for c in calls if c["argv"][:2] == ["org", "display"]], [])
        self.assertEqual([c for c in calls if c["refused"]], [])
        for call in calls:
            if call["argv"] == ["--version"]:
                continue  # the one call with no org and no JSON: the CLI's own version line, recorded by every snapshot
            if call["argv"][:2] != ["org", "list"]:
                self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de", call["argv"])
            self.assertIn("--json", call["argv"])

    def test_a_credential_in_an_error_message_is_scrubbed_from_what_a_check_prints(self) -> None:
        # The fake never emits a real-shaped token; prove the printing path scrubs one anyway.
        token = "00D5g0000012345AAA!AQEAQabcdefghijklmnopqrstuvwxyz0123456789"
        proc = subprocess.run([sys.executable, "-I", "-c",
                               "import importlib.util,sys\n"
                               "s=importlib.util.spec_from_file_location('c', %r); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                               "m.say('boom %s accessToken\": \"abc\"')\n" % (str(CHECKS), token)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(token, proc.stdout)
        self.assertIn("[redacted]", proc.stdout)


class RealOrgQuirkTest(unittest.TestCase):
    """Shapes the real org returned that the fake did not (the 2026-10-16 rehearsal)."""

    def test_the_real_cli_escapes_the_pipes_of_a_debug_line_and_the_parser_still_finds_the_result(self) -> None:
        # Captured from `sf apex run --file` on the real org: USER_DEBUG text comes back as RESULT&#124;probe&#124;1.
        real = ("68.0 APEX_CODE,DEBUG;APEX_PROFILING,INFO\nExecute Anonymous: System.debug('RESULT|probe|1');\n"
                "17:40:58.23 (24461311)|USER_DEBUG|[1]|DEBUG|RESULT&#124;probe&#124;1\n17:40:58.23 (24461999)|CODE_UNIT_FINISHED|execute_anonymous_apex\n")
        original = cs.sf
        cs.sf = lambda args, org, **kw: {"status": 0, "result": {"success": True, "compiled": True, "logs": real}}
        try:
            err, seen, _log = cs.run_apex("de", Path(tempfile.mkdtemp()), "probe", "System.debug('RESULT|probe|1');")
        finally:
            cs.sf = original
        self.assertEqual((err, seen), ("", {"probe": "1"}))

    def test_a_record_with_a_null_name_is_skipped_instead_of_breaking_the_sort(self) -> None:
        # The real org has a CustomTab whose DeveloperName is null; sorted() over None raised a TypeError in the snapshot.
        rows = [{"DeveloperName": "Get_Started_SFDX"}, {"DeveloperName": None}, {"DeveloperName": ""}, {"DeveloperName": "Chess"}]
        original = cs.records
        cs.records = lambda org, soql, tooling=True: rows
        try:
            self.assertEqual(cs.query("de", "SELECT DeveloperName FROM CustomTab", "DeveloperName"), ["Get_Started_SFDX", "Chess"])
            self.assertEqual(cs.watched_names("de", ("CustomTab", "DeveloperName", True, "")), ["Chess", "Get_Started_SFDX"])
        finally:
            cs.records = original


if __name__ == "__main__":
    unittest.main()
