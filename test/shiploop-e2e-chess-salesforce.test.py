#!/usr/bin/env python3
"""The `chess-salesforce` case's checks (test/shiploop_e2e/checks/chess_salesforce.py), run against the fake `sf`.

No test here touches a real org: each puts test/shiploop_e2e/fake_sf.py on PATH as an executable named `sf` in a shim directory
and builds PATH from that directory plus /usr/bin:/bin only, so no other `sf` can be found (a test proves it). The fake refuses
every call whose --target-org is not `de`, so a check that fell back on the default org would fail loudly.

The oracle's expected answers are not trusted: a small independent move generator (REFERENCE, below) re-derives every perft count, each
game's final status and every literal answer, so a mistyped FEN or count in the check fails here instead of failing a run.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
        self.assertRegex(debug[0], r"^\d\d:\d\d:\d\d\.\d \(\d+\)\|USER_DEBUG\|\[\d+\]\|DEBUG\|RESULT\|probe\|1$")
        self.assertTrue(any("|CODE_UNIT_STARTED|" in line for line in log))
        self.assertEqual(cs.RESULT_LINE.findall(result["logs"]), [("probe", "1")])  # the echo line also says RESULT|probe|

    def test_a_type_can_be_made_to_fail_like_an_edition_without_the_object(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        self.assertEqual(self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ExternalString", "--target-org", "de")[0], 1)
        self.assertEqual(self.sf("data", "query", "--use-tooling-api", "-q", "SELECT DeveloperName FROM FlexiPage", "--target-org", "de")[0], 0)


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
        xml = cs.destructive_xml(["SLChessEngine", "SLChessEngineTest"], ["slChessBoard"])
        self.assertIn("<members>SLChessEngine</members>", xml)
        self.assertIn("<members>slChessBoard</members>", xml)
        self.assertNotIn("*", xml)
        self.assertNotIn("<types>", cs.empty_package_xml())

    def test_the_destructive_manifest_lists_components_before_the_classes_they_import(self) -> None:
        xml = cs.destructive_xml(["SLChessProbe", "SLChessProbeTest"], ["slChessProbe"])
        self.assertLess(xml.index("<name>LightningComponentBundle</name>"), xml.index("<name>ApexClass</name>"))
        self.assertEqual(xml.count("<types>"), 2)


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

    def test_a_type_the_org_cannot_query_is_skipped_and_said(self) -> None:
        self.edit(query_errors={"ExternalString": "sObject type 'ExternalString' is not supported."})
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("not queryable here: ExternalString", self.out(proc))

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

    def test_snapshot_refuses_an_org_holding_a_prefixed_item_of_another_type(self) -> None:
        self.add(FlexiPage=["SLChessHome"])
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FlexiPage SLChessHome", self.out(proc))
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
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"])

    def test_removes_only_new_prefixed_items_and_verifies(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(sorted(r["name"] for r in record["removed"]),
                         ["SLChessController", "SLChessEngine", "SLChessEngineTest", "slChessBoard"])

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

    def test_an_extra_item_of_a_type_cleanup_cannot_remove_fails_the_run_and_is_never_deleted(self) -> None:
        self.deployed_like_a_model()
        self.add(FlexiPage=["SLChessHome"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not removable by this cleanup: remove by hand: FlexiPage SLChessHome", self.out(proc))
        state = self.state()
        self.assertIn("SLChessHome", state["types"]["FlexiPage"])
        self.assertNotIn("SLChessEngine", state["apex_classes"])  # what it can remove, it still removed
        (call,) = self.deploys(destructive=True)
        self.assertNotIn("SLChessHome", json.dumps(call["destructive"]))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["extra"]), (False, {"FlexiPage": ["SLChessHome"]}))

    def test_an_item_of_every_recorded_type_is_reported_under_its_own_type(self) -> None:
        self.snapshot()
        extras = {spec[0]: "SLChessLeft%d" % i for i, spec in enumerate(cs.WATCHED)}
        self.add(**{kind: [name] for kind, name in extras.items()})
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        for kind, name in extras.items():
            self.assertIn("not removable by this cleanup: remove by hand: %s %s" % (kind, name), proc.stdout)
        self.assertEqual(self.deploys(), [])  # nothing prefixed in Apex or components, and the rest is never removed

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
        self.assertEqual(call["destructive"], {"ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"],
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
        self.assertEqual(call["destructive"]["ApexClass"], ["SLChessEngine"])

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
              "    @AuraEnabled public static String applyMove(String fen, String move) { return SLChessEngine.applyMove(fen, move); }\n}\n")
BOARD_JS = ("import { LightningElement } from 'lwc';\n"
            "import legalMoves from '@salesforce/apex/SLChessController.legalMoves';\n"
            "import applyMove from '@salesforce/apex/SLChessController.applyMove';\n"
            "export default class SlChessBoard extends LightningElement {}\n")
BOARD_HTML = '<template><template for:each={squares} for:item="square"><div key={square.id}>{square.label}</div></template></template>'


def make_project(tmp: Path, classes=("SLChessEngine", "SLChessController", "SLChessEngineTest"), bundle="slChessBoard", extra=(),
                 controller=CONTROLLER, js=BOARD_JS, html=BOARD_HTML) -> Path:
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

    def test_other_metadata_fails(self) -> None:
        for extra in ("objects/Thing__c/Thing__c.object-meta.xml", "flows/F.flow-meta.xml", "permissionsets/P.permissionset-meta.xml"):
            proc = self.run_project(self.make(extra=(extra,)))
            self.assertEqual(proc.returncode, 1, extra)
            self.assertIn("other metadata", self.out(proc))

    def failing(self, message: str, **kwargs) -> None:
        proc = self.run_project(self.make(**kwargs))
        self.assertEqual(proc.returncode, 1, self.out(proc))
        self.assertIn(message, self.out(proc))

    def test_a_project_without_the_controller_fails_and_names_it(self) -> None:
        self.failing("SLChessController.cls", classes=("SLChessEngine", "SLChessEngineTest"))

    def test_a_controller_without_an_aura_enabled_method_fails(self) -> None:
        self.failing("has no @AuraEnabled method", controller=CONTROLLER.replace("@AuraEnabled ", ""))

    def test_a_controller_missing_one_of_the_two_methods_fails_and_names_it(self) -> None:
        self.failing("declares no static method applyMove", controller=CONTROLLER.replace("applyMove(String", "apply(String"))
        self.failing("declares no static method legalMoves", controller=CONTROLLER.replace("legalMoves(String", "moves(String"))

    def test_a_component_that_never_imports_the_controller_fails(self) -> None:
        self.failing("does not import @salesforce/apex/SLChessController",
                     js="import { LightningElement } from 'lwc';\nexport default class X extends LightningElement {}\n")
        self.failing("does not import @salesforce/apex/SLChessController", js=BOARD_JS.replace("SLChessController", "SLChessEngine"))

    def test_a_component_template_that_renders_no_list_fails(self) -> None:
        self.failing("no for:each or iterator", html="<template><div>board</div></template>")

    def test_an_iterator_template_passes(self) -> None:
        proc = self.run_project(self.make(html="<template><template iterator:sq={squares}><div key={sq.value.id}></div></template></template>"))
        self.assertEqual(proc.returncode, 0, self.out(proc))


class TestDeployedAndTests(FakeOrg):
    def deploy_all(self, tests=("SLChessEngineTest", "SLChessMovesTest")) -> None:
        self.add(apex=["SLChessEngine", "SLChessController", *tests], lwc=["slChessBoard"])

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
                                     "SLChessController.legalMoves", "SLChessController.applyMove"})

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
        expected = {marker: value for _n, _s, marks in cs.rule_cases() for marker, value in marks if marker != "illegal"}
        self.assertEqual(sorted(answers), sorted(expected))  # a new marker needs a reference answer here
        self.assertEqual(answers, expected)

    def test_the_two_square_push_sets_the_en_passant_square_whether_or_not_a_capture_is_possible(self) -> None:
        self.assertEqual(ref_apply(cs.START, "e2e4").split(" ")[3], "e3")  # no black pawn can capture on e3
        self.assertEqual(ref_apply("4k3/8/8/8/8/8/P7/4K3 w - - 0 1", "a2a4").split(" ")[3], "a3")


class TestSelftest(FakeOrg):
    def run_selftest(self, probe="2", **env) -> subprocess.CompletedProcess:
        canned = self.tmp / "probe.json"
        canned.write_text(json.dumps({"probe": probe}))
        env.setdefault("FAKE_SF_APEX", str(canned))
        return self.run_check("selftest", "--org", "de", "--prefix", "SLChess", env=env)

    def test_rehearsal_deploys_tests_runs_anonymous_apex_and_removes_the_probe(self) -> None:
        proc = self.run_selftest()
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("preflight", "snapshot", "deploy", "deployed", "tests", "apex-run", "cleanup"):
            self.assertIn("PASS %s:" % step, proc.stdout)
        self.assertTrue(proc.stdout.startswith("selftest proves, in order: preflight"), proc.stdout[:80])
        self.assertIn("PASS apex-run: RESULT|probe| expected=2 got=2", proc.stdout)
        (run,) = [c for c in self.calls() if "--file" in c["argv"]]
        self.assertEqual((run["apex_markers"], run["argv"][run["argv"].index("--target-org") + 1]), (["probe"], "de"))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        (add,) = self.deploys(destructive=False)
        self.assertEqual(add["argv"][add["argv"].index("--target-org") + 1], "de")
        (rm,) = self.deploys(destructive=True)
        self.assertEqual(rm["destructive"], {"ApexClass": ["SLChessProbe", "SLChessProbeTest"], "LightningComponentBundle": ["slChessProbe"]})

    def test_a_probe_that_answers_anything_but_two_fails_the_rehearsal_and_still_cleans_up(self) -> None:
        proc = self.run_selftest(probe="3")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run: RESULT|probe| expected=2 got=3", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))

    def test_the_apex_run_step_reports_the_same_errors_rules_does(self) -> None:
        proc = self.run_selftest(probe={"compileProblem": "Variable does not exist: SLChessProbe"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run: RESULT|probe| expected=2 got=compile error: Variable does not exist: SLChessProbe", proc.stdout)
        proc = self.run_selftest(FAKE_SF_APEX=str(self.tmp / "none.json"), FAKE_SF_FAIL="apex")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL apex-run:", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)

    def test_the_probe_is_an_aura_enabled_class_and_a_component_that_imports_it(self) -> None:
        klass, test, bundle = cs.write_probe(self.tmp / "probe-project", "SLChess")
        classes = self.tmp / "probe-project" / "force-app" / "main" / "default"
        self.assertEqual((klass, test, bundle), ("SLChessProbe", "SLChessProbeTest", "slChessProbe"))
        self.assertIn("@AuraEnabled(cacheable=true) public static Integer two()", (classes / "classes" / "SLChessProbe.cls").read_text())
        self.assertIn("import two from '@salesforce/apex/SLChessProbe.two';", (classes / "lwc" / "slChessProbe" / "slChessProbe.js").read_text())
        self.assertIn("SLChessProbe.two()", (classes / "classes" / "SLChessProbeTest.cls").read_text())

    def test_a_failing_probe_test_still_cleans_up(self) -> None:
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 1, "failing": 1}))
        proc = self.run_selftest(FAKE_SF_TESTS=str(results))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL tests:", proc.stdout)
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

    def test_the_test_count_the_prompt_asks_for_is_the_one_the_check_requires(self) -> None:
        asked = int(re.search(r"at least (\d+) Apex test methods", self.prompt).group(1))
        required = int(re.search(r"--min-tests (\d+)", next(c for c in self.case["checks"] if " tests " in c)).group(1))
        self.assertEqual(asked, required)

    def test_the_prompt_does_not_mention_the_platform_machinery(self) -> None:
        for word in ("wrapper", "guard", "sf_guard", "model_bin", "harness", "PATH"):
            self.assertNotIn(word, self.prompt)

    def test_the_checks_are_the_same_subcommands_as_before(self) -> None:
        self.assertEqual([c.split()[2] for c in self.case["checks"]], ["project", "deployed", "tests", "rules"])

    def test_the_resume_note_tells_a_resumed_model_its_deployment_is_gone(self) -> None:
        note = self.case["platform"]["resume_note"]
        self.assertIsInstance(note, str)
        for part in ("reset to its baseline", "removed", "Deploy again from your source", "run tests in the org"):
            self.assertIn(part, note)
        self.assertNotIn("guard", note.lower())


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
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"])
        outputs.append(self.run_check("project", "--org", "de", cwd=project, env=env))
        outputs.append(self.run_check("deployed", "--org", "de", env=env))
        outputs.append(self.run_check("tests", "--org", "de", "--min-tests", "8", env=env))
        outputs.append(self.run_check("rules", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned))))
        outputs.append(self.run_check("cleanup", "--org", "de", env=env))
        outputs.append(self.run_check("selftest", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned))))
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


if __name__ == "__main__":
    unittest.main()
