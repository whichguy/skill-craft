#!/usr/bin/env python3
"""The stage suite's check engine (test/shiploop_e2e/stage_suite/stage_oracle.py; docs/plans/shiploop-stage-suite.md), no model.

Every check kind runs on synthetic bundles built in temporary folders, once to a pass and once to a failure. The rest pins
the engine's design points:

- ``validate_checks`` names each malformed shape (not a list, not an object, no kind or several, a wrong value type, an
  unknown key, an unknown ``proves``, a regular expression that does not compile, a path that leaves the tree, a bad
  assertion combination) and accepts the good ones.
- A path that leaves the tree (``..``, absolute, a symlink out) is a failed check and nothing outside is read, in the tree and
  in the seed tree; a symlink met while walking a folder is compared by its target and never followed.
- ``file`` and ``changed_only`` compare bytes, the executable bit and link targets against the seed tree and ignore compiled
  files and caches; the last component of a ``file`` path is a link as it is (a dangling one is there, a file replaced by a
  link to the same bytes is changed); the file comparison has no cache; a glob matches a name with a newline and a path written
  with ``./`` or ``//``.
- A ``command`` runs in a scratch copy (the tree is never touched; a symlink that leaves the copy is left out, so nothing can be
  written through it), stdin closed, a reduced environment, a scratch HOME and TMPDIR; a timeout kills its whole process group
  and fails the check whatever exit was asked for; so does a flood of output, which is also never read whole; "nonzero" is not
  satisfied by a shell that could not run the command; the scratch folder is gone afterwards.
- A ``stand_in`` that kills is shown on a candidate on which the command passes: a command that already fails there kills nothing.
- ``[*]``, ``any``, a missing key and the "at least one value" rule behave as the shared contract says.
- ``verdict`` separates caught, missed, not exercised, an unproved failure, and an id that two checks prove of which one fails.
- The engine, the stage cases and the stage suite's other files are outside the evaluator digest and the qualification
  snapshot, as the probes are (test/shiploop-e2e-sdlc-probes.test.py).
"""
from __future__ import annotations

import os
import shlex
import shutil
import sys
import tempfile
import time
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
import stage_oracle as oracle  # noqa: E402
from stage_oracle import Bundle, run_check, run_checks, validate_checks, verdict  # noqa: E402

IDS = ["P1", "P2", "C1"]


def py(code: str) -> str:
    """A shell command that runs `code` with this interpreter."""
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


def lay(base: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_text(text)
    return base


def alive(pid: int) -> bool:
    try:  # a zombie is dead; only a reaper that is not there leaves one
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gone(pid: int, seconds: float = 5.0) -> bool:
    end = time.monotonic() + seconds
    while alive(pid):
        if time.monotonic() > end:
            return False
        time.sleep(0.05)
    return True


def snapshot(folder: Path) -> dict[str, str]:
    return {path.relative_to(folder).as_posix(): path.read_text() for path in sorted(folder.rglob("*")) if path.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="stage-oracle-test-")
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.tree = lay(self.dir / "tree", {"src/a.js": "const a = 1;\n", "README.md": "# demo\n", "docs/x.md": "x\n"})
        self.seed = lay(self.dir / "seed", {"src/a.js": "const a = 1;\n", "README.md": "# demo\n", "docs/x.md": "x\n"})
        self.outside = lay(self.dir / "outside", {"secret.txt": "TOP-SECRET-VALUE\n", "sub/deep.txt": "TOP-SECRET-DEEP\n"})

    def bundle(self, **kwargs) -> Bundle:
        return Bundle(**{"tree": self.tree, "seed_tree": self.seed, **kwargs})

    def run_one(self, check: dict, **kwargs) -> dict:
        return run_check(check, self.bundle(**kwargs))

    def passes(self, check: dict, **kwargs) -> dict:
        found = self.run_one(check, **kwargs)
        self.assertTrue(found["pass"], found)
        return found

    def fails(self, check: dict, fragment: str = "", **kwargs) -> dict:
        found = self.run_one(check, **kwargs)
        self.assertFalse(found["pass"], found)
        self.assertIn(fragment, found["detail"])
        return found


# ------------------------------------------------------------------------------------------------------ validate_checks

class Validation(unittest.TestCase):
    GOOD = [
        {"outcome": ["done", "send-back"]},
        {"field": "failed_expectations[*].route", "equals": "check"},
        {"field": "a.b", "matches": "x+", "any": True, "proves": "P1", "why": "prose"},
        {"field": "a", "exists": False}, {"field": "a[*]", "count": 0}, {"field": "[*].a", "none_equal": None},
        {"file": "src/paginate.js", "exists": True}, {"file": "a", "contains": "x.*y"}, {"file": "a", "not_contains": "x"},
        {"file": ".", "unchanged": True},
        {"changed_only": ["src/strings.js", "docs/**", "**/*.md", "a?.js"]}, {"changed_only": []},
        {"command": "node --test", "exit": 0}, {"command": "false", "exit": "nonzero", "timeout": 5},
        {"command": "x", "exit": 255, "timeout": 0.5},
        {"stand_in": "stand_ins/empty", "command": "node --test", "kills": True, "proves": "C1"},
        {"stand_in": "stand_ins/lenient", "command": "x", "kills": False, "timeout": 3},
        {"trace": "refusals_max", "value": 1},
        {"packet_contains": "E1"}, {"packet_not_contains": "E2"}, {"packet_head_contains": "^head"},
        {"packet_issued": False}, {"settled_by_script": True}, {"current_stage": "implement"},
    ]

    def test_every_kind_has_a_valid_spelling(self):
        for check in self.GOOD:
            with self.subTest(check=check):
                self.assertEqual(validate_checks([check], IDS), [])
        self.assertEqual(validate_checks([], IDS), [])
        spelled = {kind for check in self.GOOD for kind in oracle._kinds(check)}
        self.assertEqual(spelled, set(oracle.KINDS))  # no kind goes without a valid spelling here

    BAD = [
        ("a check is not an object", "x", "must be an object"),
        ("a check is a list", ["outcome"], "must be an object"),
        ("no kind", {"proves": "P1"}, "no check kind"),
        ("an empty check", {}, "no check kind"),
        ("two kinds", {"outcome": ["done"], "packet_issued": True}, "several check kinds"),
        ("a stand-in and a file", {"stand_in": "d", "command": "x", "kills": True, "file": "a", "exists": True},
         "several check kinds"),
        ("an unknown key", {"outcome": ["done"], "extra": 1}, "unknown key 'extra'"),
        ("a key of another kind", {"command": "x", "exit": 0, "kills": True}, "unknown key 'kills'"),
        ("proves outside the ids", {"outcome": ["done"], "proves": "P9"}, "not a planted or control id"),
        ("proves not a string", {"outcome": ["done"], "proves": 1}, "proves must be an id"),
        ("proves null", {"outcome": ["done"], "proves": None}, "proves must be an id"),
        ("why not a string", {"outcome": ["done"], "why": 3}, "why must be a string"),
        ("outcome not a list", {"outcome": "done"}, "non-empty list"),
        ("outcome empty", {"outcome": []}, "non-empty list"),
        ("outcome with a number", {"outcome": ["done", 1]}, "non-empty list"),
        ("field not a string", {"field": 3, "equals": 1}, "non-empty string"),
        ("field with a bad segment", {"field": "a.b c[1]", "equals": 1}, "not a key followed by [*]"),
        ("field with an empty segment", {"field": "a..b", "equals": 1}, "has no key"),
        ("field without an assertion", {"field": "a"}, "exactly one of"),
        ("field with two assertions", {"field": "a", "equals": 1, "exists": True}, "exactly one of"),
        ("field matches with a broken regex", {"field": "a", "matches": "("}, "not a regular expression"),
        ("field matches empty", {"field": "a", "matches": ""}, "non-empty regular expression"),
        ("field exists not a bool", {"field": "a", "exists": "yes"}, "exists must be true or false"),
        ("field count negative", {"field": "a", "count": -1}, "non-negative integer"),
        ("field count a bool", {"field": "a", "count": True}, "non-negative integer"),
        ("field count a float", {"field": "a", "count": 1.5}, "non-negative integer"),
        ("field any not a bool", {"field": "a", "equals": 1, "any": "yes"}, "any must be true or false"),
        ("field any with exists", {"field": "a", "exists": True, "any": True}, "any has no meaning"),
        ("field any with count", {"field": "a", "count": 1, "any": True}, "any has no meaning"),
        ("file path empty", {"file": "", "exists": True}, "non-empty string"),
        ("file path with ..", {"file": "../x", "exists": True}, "climbs out"),
        ("file path with .. inside", {"file": "a/../../x", "exists": True}, "climbs out"),
        ("file path absolute", {"file": "/etc/passwd", "exists": True}, "is absolute"),
        ("file path with a NUL", {"file": "a\0b", "exists": True}, "holds a NUL"),
        ("file without an assertion", {"file": "a"}, "exactly one of"),
        ("file with two assertions", {"file": "a", "exists": True, "unchanged": True}, "exactly one of"),
        ("file contains and not_contains", {"file": "a", "contains": "x", "not_contains": "y"}, "exactly one of"),
        ("file contains broken regex", {"file": "a", "contains": "[a-"}, "not a regular expression"),
        ("file not_contains broken regex", {"file": "a", "not_contains": "(?P<"}, "not a regular expression"),
        ("file unchanged not a bool", {"file": "a", "unchanged": "true"}, "unchanged must be true or false"),
        ("file exists a number", {"file": "a", "exists": 1}, "exists must be true or false"),
        ("changed_only not a list", {"changed_only": "src/**"}, "must be a list of globs"),
        ("changed_only with a number", {"changed_only": [1]}, "non-empty string"),
        ("changed_only glob with ..", {"changed_only": ["../x"]}, "climbs out"),
        ("changed_only glob absolute", {"changed_only": ["/tmp/**"]}, "is absolute"),
        ("changed_only glob with a bracket", {"changed_only": ["src/[ab].js"]}, "bracket or brace"),
        ("changed_only glob ending in a slash", {"changed_only": ["docs/"]}, "dir/**"),
        ("command empty", {"command": "", "exit": 0}, "non-empty string"),
        ("command not a string", {"command": ["ls"], "exit": 0}, "non-empty string"),
        ("command without exit", {"command": "x"}, "needs exit"),
        ("command exit a bool", {"command": "x", "exit": True}, "exit must be"),
        ("command exit out of range", {"command": "x", "exit": 256}, "exit must be"),
        ("command exit a string", {"command": "x", "exit": "0"}, "exit must be"),
        ("command timeout zero", {"command": "x", "exit": 0, "timeout": 0}, "positive number"),
        ("command timeout a bool", {"command": "x", "exit": 0, "timeout": True}, "positive number"),
        ("command timeout a string", {"command": "x", "exit": 0, "timeout": "5"}, "positive number"),
        ("command timeout not finite", {"command": "x", "exit": 0, "timeout": float("inf")}, "positive number"),
        ("command timeout nan", {"command": "x", "exit": 0, "timeout": float("nan")}, "positive number"),
        ("stand_in without a command", {"stand_in": "d", "kills": True}, "needs a command"),
        ("stand_in without kills", {"stand_in": "d", "command": "x"}, "kills"),
        ("stand_in kills not a bool", {"stand_in": "d", "command": "x", "kills": "yes"}, "kills"),
        ("stand_in path with ..", {"stand_in": "../d", "command": "x", "kills": True}, "climbs out"),
        ("stand_in path absolute", {"stand_in": "/d", "command": "x", "kills": True}, "is absolute"),
        ("stand_in with an exit", {"stand_in": "d", "command": "x", "kills": True, "exit": 0}, "unknown key 'exit'"),
        ("trace unknown", {"trace": "no_model_glue", "value": 0}, "must be one of"),
        ("trace without value", {"trace": "refusals_max"}, "needs a value"),
        ("trace value negative", {"trace": "refusals_max", "value": -1}, "non-negative integer"),
        ("trace value a bool", {"trace": "refusals_max", "value": False}, "non-negative integer"),
        ("packet_contains broken regex", {"packet_contains": "*x"}, "not a regular expression"),
        ("packet_not_contains not a string", {"packet_not_contains": 5}, "non-empty regular expression"),
        ("packet_head_contains empty", {"packet_head_contains": ""}, "non-empty regular expression"),
        ("packet_issued not a bool", {"packet_issued": "no"}, "must be true or false"),
        ("settled_by_script a number", {"settled_by_script": 1}, "must be true or false"),
        ("current_stage empty", {"current_stage": ""}, "stage name"),
    ]

    def test_each_malformed_shape_is_named(self):
        for label, check, fragment in self.BAD:
            with self.subTest(label):
                problems = validate_checks([check], IDS)
                self.assertTrue(problems, "accepted")
                self.assertTrue(any(fragment in problem for problem in problems), problems)
                self.assertTrue(problems[0].startswith("checks[0]: "), problems)

    def test_the_list_itself_must_be_a_list_and_each_problem_names_its_index(self):
        for value in (None, {"outcome": ["done"]}, "outcome", ("a",)):
            with self.subTest(value=value):
                self.assertIn("must be a list", validate_checks(value, IDS)[0])
        problems = validate_checks([{"outcome": ["done"]}, {"outcome": "x"}, {"packet_issued": True}, 7], IDS)
        self.assertEqual([problem.split(":")[0] for problem in problems], ["checks[1]", "checks[3]"])

    def test_ids_none_skips_only_the_proves_test(self):
        self.assertEqual(validate_checks([{"outcome": ["done"], "proves": "P9"}], None), [])
        self.assertTrue(validate_checks([{"outcome": ["done"], "proves": "P9"}], []))
        self.assertTrue(validate_checks([{"outcome": "x"}], None))

    def test_a_regex_is_checked_the_way_it_is_used(self):
        self.assertEqual(validate_checks([{"packet_contains": "^E1 .*$"}], IDS), [])  # anchors are fine under MULTILINE
        self.assertTrue(validate_checks([{"packet_contains": "(?P<n>a)(?P<n>b)"}], IDS))


# ------------------------------------------------------------------------------------------------- outcome, field, flags

class Results(Base):
    RESULT = {
        "outcome": "send-back", "summary": "PLANTED-E1 does not match", "n": 1, "flag": True, "nothing": None,
        "failed_expectations": [{"id": "E1", "route": "check", "actual": "x"}, {"id": "E2", "route": "check"}],
        "items": [{"tags": ["a", "b"]}, {"tags": ["c"]}, {}],
    }

    def check(self, check: dict, expect: bool, fragment: str = ""):
        found = self.run_one(check, result=self.RESULT)
        self.assertEqual(found["pass"], expect, found)
        self.assertIn(fragment, found["detail"])
        self.assertEqual(found["kind"], "field")

    def test_outcome(self):
        self.passes({"outcome": ["done", "send-back"]}, result=self.RESULT)
        self.fails({"outcome": ["done", "blocked"]}, "send-back is not one of", result=self.RESULT)
        self.fails({"outcome": ["done"]}, "no result")
        self.fails({"outcome": ["done"]}, "is not one of", result={"summary": "x"})
        self.fails({"outcome": ["1"]}, "is not one of", result={"outcome": 1})
        self.fails({"outcome": ["done"]}, "no result", result=["done"])

    def test_equals_needs_every_selected_value(self):
        self.check({"field": "failed_expectations[*].route", "equals": "check"}, True)
        self.check({"field": "failed_expectations[*].id", "equals": "E1"}, False, "1 of 2 values do not equal")
        self.check({"field": "failed_expectations[*].id", "equals": "E1", "any": True}, True)
        self.check({"field": "failed_expectations[*].id", "equals": "E9", "any": True}, False, "2 of 2")
        self.check({"field": "outcome", "equals": "send-back"}, True)
        self.check({"field": "outcome", "equals": "done"}, False)

    def test_a_missing_key_is_not_selected_never_an_error(self):
        self.check({"field": "nothing_here", "equals": 1}, False, "selects no value")
        self.check({"field": "failed_expectations[*].missing", "equals": 1}, False, "selects no value")
        self.check({"field": "outcome.deeper", "equals": 1}, False, "selects no value")  # a string has no key
        self.check({"field": "failed_expectations[*].actual", "equals": "x"}, True)  # one element lacks it: skipped
        self.check({"field": "outcome[*]", "count": 0}, True)  # [*] over a string selects nothing
        self.check({"field": "nothing_here", "matches": "x"}, False, "selects no value")
        self.check({"field": "nothing_here", "none_equal": 1}, False, "selects no value")

    def test_exists_and_count_may_select_nothing(self):
        self.check({"field": "nothing_here", "exists": False}, True)
        self.check({"field": "nothing_here", "exists": True}, False, "selects 0 values")
        self.check({"field": "outcome", "exists": True}, True)
        self.check({"field": "outcome", "exists": False}, False)
        self.check({"field": "nothing", "exists": True}, True)  # a key holding null is selected
        self.check({"field": "nothing_here", "count": 0}, True)
        self.check({"field": "failed_expectations", "count": 0}, False, "selects 1 values, not 0")
        self.check({"field": "failed_expectations[*]", "count": 2}, True)
        self.check({"field": "failed_expectations[*]", "count": 3}, False)
        self.check({"field": "items[*].tags[*]", "count": 3}, True)
        self.check({"field": "items[*].tags", "count": 2}, True)  # the element with no tags selects nothing

    def test_matches_searches_the_string_form_with_multiline(self):
        self.check({"field": "summary", "matches": "PLANTED-E1"}, True)
        self.check({"field": "summary", "matches": "^PLANTED"}, True)
        self.check({"field": "summary", "matches": "^does"}, False, "do not match")
        self.check({"field": "n", "matches": "^1$"}, True)  # a number is read as its JSON text
        self.check({"field": "flag", "matches": "^true$"}, True)
        self.check({"field": "nothing", "matches": "^null$"}, True)
        self.check({"field": "failed_expectations[*]", "matches": '"route": "check"', "any": True}, True)
        self.assertTrue(self.run_one({"field": "t", "matches": "^b$"}, result={"t": "a\nb\nc"})["pass"])

    def test_none_equal(self):
        self.check({"field": "failed_expectations[*].route", "none_equal": "steps"}, True)
        self.check({"field": "failed_expectations[*].route", "none_equal": "check"}, False, "2 of 2")
        self.check({"field": "failed_expectations[*].id", "none_equal": "E1"}, False, "1 of 2")
        self.check({"field": "failed_expectations[*].id", "none_equal": "E1", "any": True}, True)

    def test_equality_is_json_equality(self):
        self.check({"field": "flag", "equals": True}, True)
        self.check({"field": "flag", "equals": 1}, False)  # a boolean is not a number
        self.check({"field": "n", "equals": True}, False)
        self.check({"field": "n", "equals": 1.0}, True)
        self.check({"field": "nothing", "equals": None}, True)
        self.check({"field": "nothing", "equals": 0}, False)
        self.check({"field": "items[*].tags", "equals": ["a", "b"], "any": True}, True)
        found = self.run_one({"field": "items[2]", "equals": {}}, result=self.RESULT)  # indexes are not part of the grammar
        self.assertFalse(found["pass"])
        self.assertIn("not a key followed by", found["detail"])
        self.check({"field": "failed_expectations[*]", "equals": {"id": "E2", "route": "check"}, "any": True}, True)

    def test_a_result_that_is_not_an_object_fails_the_field(self):
        self.fails({"field": "outcome", "equals": "done"}, "no result")
        self.fails({"field": "outcome", "exists": False}, "no result")
        self.fails({"field": "outcome", "equals": "done"}, "no result", result=[1])

    def test_flags_and_stage(self):
        self.passes({"packet_issued": True}, issued=True)
        self.fails({"packet_issued": True}, "issued is False")
        self.passes({"packet_issued": False})
        self.fails({"packet_issued": False}, "issued is True", issued=True)
        self.passes({"settled_by_script": True}, settled=True)
        self.fails({"settled_by_script": True}, "settled is False")
        self.passes({"settled_by_script": False})
        self.fails({"settled_by_script": False}, "", settled=True)
        self.passes({"current_stage": "implement"}, current_stage="implement")
        self.fails({"current_stage": "implement"}, "not implement", current_stage="test")
        self.fails({"current_stage": "implement"}, "None, not implement")


# -------------------------------------------------------------------------------------------------------- packet, trace

class PacketAndTrace(Base):
    PACKET = "Stage: validate-existing\nE1 works PLANTED-E1 -> DOES NOT MATCH, exit 1\nE2 broken -> matches\n"

    def test_packet_contains_and_not_contains_search_with_multiline(self):
        self.passes({"packet_contains": "^E1 works .*DOES NOT MATCH"}, packet=self.PACKET)
        self.passes({"packet_contains": "^E2 broken"}, packet=self.PACKET)
        self.fails({"packet_contains": "^E3"}, "does not match", packet=self.PACKET)
        self.fails({"packet_contains": "validate-existing\\nE2"}, "does not match", packet=self.PACKET)
        self.passes({"packet_not_contains": "E2 broken .*DOES NOT MATCH"}, packet=self.PACKET)
        found = self.fails({"packet_not_contains": "^E1 works"}, "matches", packet=self.PACKET)
        self.assertIn("E1 works", found["detail"])

    def test_no_packet_fails_every_packet_check_even_a_not_contains(self):
        for check in ({"packet_contains": "x"}, {"packet_not_contains": "x"}, {"packet_head_contains": "x"}):
            with self.subTest(check=check):
                self.fails(check, "no packet", packet=None, packet_head=None)
        self.fails({"packet_contains": "x"}, "no packet", packet_head="x")
        self.passes({"packet_not_contains": "x"}, packet="")  # an empty packet is a packet

    def test_the_head_is_read_apart_from_the_packet(self):
        self.passes({"packet_head_contains": "^shiploop next"}, packet_head="shiploop next\nbody", packet="other")
        self.fails({"packet_head_contains": "body"}, "does not match", packet_head="head only", packet="body")
        self.fails({"packet_head_contains": "head"}, "no packet head", packet="head")

    ROWS = [
        {"kind": "command", "verb": "complete", "exit": 1},
        {"kind": "command", "verb": "next", "exit": 0},
        {"kind": "command", "verb": "check", "exit": 1},  # a check reports and never refuses
        {"kind": "command", "verb": "complete", "exit": 2, "held": True},  # held once for owner notes
        {"kind": "command", "verb": "complete", "exit": None},
        {"kind": "packet", "exit": 5},
        {"kind": "hook", "exit": 5},
        "junk", None, 7,
    ]

    def test_refusals_max_counts_the_engines_refusals(self):
        self.passes({"trace": "refusals_max", "value": 1}, trace=self.ROWS)
        self.passes({"trace": "refusals_max", "value": 3}, trace=self.ROWS)
        found = self.fails({"trace": "refusals_max", "value": 0}, "1 refusals, at most 0", trace=self.ROWS)
        self.assertEqual(found["kind"], "trace")
        self.passes({"trace": "refusals_max", "value": 0}, trace=[])
        two = self.ROWS + [{"kind": "command", "verb": "complete", "exit": 3}]
        self.fails({"trace": "refusals_max", "value": 1}, "2 refusals", trace=two)

    def test_a_trace_that_was_not_read_fails_and_is_not_zero_refusals(self):
        self.fails({"trace": "refusals_max", "value": 5}, "no trace")
        self.fails({"trace": "refusals_max", "value": 5}, "no trace", trace="rows")


# ---------------------------------------------------------------------------------------------------- file, changed_only

class Files(Base):
    def test_exists(self):
        self.passes({"file": "src/a.js", "exists": True})
        self.passes({"file": "src", "exists": True})  # a folder is there too
        self.passes({"file": "src/b.js", "exists": False})
        self.fails({"file": "src/b.js", "exists": True}, "is not there")
        self.fails({"file": "src/a.js", "exists": False}, "is there")
        self.passes({"file": "./src//a.js", "exists": True})

    def test_contains_and_not_contains_search_with_multiline(self):
        lay(self.tree, {"src/p.js": "line one\nexport function paginate(a) {}\nPLANTED\n"})
        self.passes({"file": "src/p.js", "contains": "^export function paginate"})
        self.passes({"file": "src/p.js", "contains": "^PLANTED$"})
        self.fails({"file": "src/p.js", "contains": "^paginate"}, "does not match")
        self.passes({"file": "src/p.js", "not_contains": "formatPage"})
        found = self.fails({"file": "src/p.js", "not_contains": "PLANT\\w+"}, "matches")
        self.assertIn("PLANTED", found["detail"])

    def test_a_missing_file_or_a_folder_fails_contains_and_not_contains_alike(self):
        self.fails({"file": "src/none.js", "contains": "x"}, "is not a file")
        self.fails({"file": "src/none.js", "not_contains": "x"}, "is not a file")
        self.fails({"file": "src", "not_contains": "x"}, "(a folder)")

    def test_a_file_that_is_not_text_is_still_searched(self):
        (self.tree / "blob.bin").write_bytes(b"\xff\xfe\x00MARK\xff")
        self.passes({"file": "blob.bin", "contains": "MARK"})

    def test_unchanged_compares_bytes_with_the_seed_tree(self):
        self.passes({"file": "src/a.js", "unchanged": True})
        self.fails({"file": "src/a.js", "unchanged": False}, "is unchanged")
        (self.tree / "src/a.js").write_text("const a = 2;\n")
        self.fails({"file": "src/a.js", "unchanged": True}, "is changed")
        self.passes({"file": "src/a.js", "unchanged": False})
        (self.tree / "src/a.js").write_text("const a = 1;\n")
        self.passes({"file": "src/a.js", "unchanged": True})
        (self.tree / "src/a.js").write_bytes(b"const a = 1;\r\n")  # the same text but not the same bytes
        self.fails({"file": "src/a.js", "unchanged": True}, "is changed")

    def test_unchanged_sees_a_file_added_or_removed(self):
        (self.tree / "src/new.js").write_text("n\n")
        self.fails({"file": "src/new.js", "unchanged": True}, "src/new.js")
        (self.tree / "README.md").unlink()
        self.fails({"file": "README.md", "unchanged": True}, "is changed")
        self.passes({"file": "src/never.js", "unchanged": True})  # absent from both

    def test_unchanged_on_a_folder_is_every_file_below_it(self):
        self.passes({"file": "src", "unchanged": True})
        self.passes({"file": ".", "unchanged": True})
        lay(self.tree, {"src/deep/more.js": "m\n"})
        found = self.fails({"file": "src", "unchanged": True}, "src/deep/more.js")
        self.assertIn("is changed", found["detail"])
        self.fails({"file": ".", "unchanged": True}, "src/deep/more.js")
        self.passes({"file": "docs", "unchanged": True})
        self.passes({"file": "src", "unchanged": False})

    def test_compiled_files_and_caches_are_not_a_change(self):
        lay(self.tree, {"src/__pycache__/a.cpython-313.pyc": "x", "src/mod.pyc": "y", "pkg/__pycache__/z.txt": "z"})
        self.passes({"file": "src", "unchanged": True})
        self.passes({"file": ".", "unchanged": True})
        self.passes({"changed_only": []})

    def test_the_top_level_git_folder_is_not_a_change_but_a_nested_one_is(self):
        lay(self.tree, {".git/HEAD": "ref\n"})
        self.passes({"changed_only": []})
        self.passes({"file": ".", "unchanged": True})
        lay(self.tree, {"vendor/.git/HEAD": "ref\n"})
        self.fails({"changed_only": []}, "vendor/.git/HEAD")

    def test_changed_only_names_added_changed_and_removed_files(self):
        self.passes({"changed_only": []})
        (self.tree / "src/a.js").write_text("changed\n")
        found = self.fails({"changed_only": ["docs/**"]}, "src/a.js")
        self.assertIn("1 of 1 changed", found["detail"])
        self.passes({"changed_only": ["src/a.js"]})
        (self.tree / "src/b.js").write_text("new\n")
        self.fails({"changed_only": ["src/a.js"]}, "src/b.js")
        (self.tree / "docs/x.md").unlink()
        found = self.fails({"changed_only": ["src/a.js", "src/b.js"]}, "docs/x.md")
        self.assertIn("1 of 3", found["detail"])
        self.passes({"changed_only": ["src/*.js", "docs/**"]})

    def test_changed_only_globs(self):
        lay(self.tree, {"src/deep/er/x.js": "x\n", "top.js": "t\n", "docs/a/b.md": "b\n"})
        self.passes({"changed_only": ["src/**", "top.js", "docs/**"]})
        self.fails({"changed_only": ["src/*", "top.js", "docs/**"]}, "src/deep/er/x.js")  # * stays inside one name
        self.passes({"changed_only": ["**/*.js", "docs/**"]})
        self.passes({"changed_only": ["**", ]})
        self.fails({"changed_only": ["src/**", "*.md"]}, "top.js")
        self.fails({"changed_only": ["src/**", "top.j?x", "docs/**"]}, "top.js")
        self.passes({"changed_only": ["src/**", "top.j?", "docs/**"]})
        self.fails({"changed_only": ["src/deep", "top.js", "docs/**"]}, "src/deep/er/x.js")  # a folder name is not a prefix
        self.passes({"changed_only": ["./src/**", "./top.js", "docs/**"]})
        self.fails({"changed_only": ["src.js/**", "top.js", "docs/**"]}, "src/deep/er/x.js")  # the dot is literal, not a wildcard

    def test_a_missing_tree_or_seed_tree_fails(self):
        self.fails({"file": "src/a.js", "exists": True}, "no tree", tree=None)
        self.fails({"file": "src/a.js", "unchanged": True}, "no seed tree", seed_tree=None)
        self.passes({"file": "src/a.js", "exists": True}, seed_tree=None)
        self.fails({"changed_only": []}, "no seed tree", seed_tree=None)
        self.fails({"changed_only": []}, "no tree", tree=None)
        self.fails({"file": "x", "exists": False}, "is not a folder", tree=self.dir / "nothing")
        self.fails({"file": "a", "exists": False}, "is not a folder", tree=self.tree / "src/a.js")

    def test_the_checks_leave_both_trees_as_they_were(self):
        before = (snapshot(self.tree), snapshot(self.seed))
        run_checks([{"file": "src/a.js", "unchanged": True}, {"changed_only": []}, {"file": "src", "contains": "x"},
                    {"command": "rm -rf src; echo > README.md", "exit": 0}], self.bundle())
        self.assertEqual((snapshot(self.tree), snapshot(self.seed)), before)


class LastComponent(Base):
    """A ``file`` path is looked at as it is in its last component: a symlink is an entry, not the file it points to."""

    def test_a_file_replaced_by_a_symlink_to_the_same_bytes_is_a_change(self):
        (self.tree / "src/a.js").unlink()
        (self.tree / "src/real.js").write_text("const a = 1;\n")
        (self.tree / "src/a.js").symlink_to("real.js")
        self.fails({"file": "src/a.js", "unchanged": True}, "is changed")
        self.fails({"file": "src", "unchanged": True}, "src/a.js")
        self.fails({"changed_only": ["src/real.js"]}, "src/a.js")
        self.passes({"file": "src/a.js", "contains": "const a"})  # the content is still read through an inside link

    def test_two_links_with_the_same_target_are_unchanged_and_a_retargeted_one_is_not(self):
        for tree in (self.tree, self.seed):
            (tree / "ln").symlink_to("src/a.js")
        self.passes({"file": "ln", "unchanged": True})
        (self.tree / "ln").unlink()
        (self.tree / "ln").symlink_to("README.md")
        self.fails({"file": "ln", "unchanged": True}, "is changed")

    def test_a_dangling_link_is_there(self):
        (self.tree / "dang").symlink_to("nowhere")
        self.passes({"file": "dang", "exists": True})
        self.fails({"file": "dang", "exists": False}, "is there")
        self.fails({"file": "dang", "unchanged": True}, "is changed")
        self.passes({"file": "gone", "exists": False})

    def test_a_link_to_a_folder_is_an_entry_and_the_folder_below_it_is_still_reached(self):
        (self.tree / "alias").symlink_to("src")
        self.passes({"file": "alias", "exists": True})
        self.fails({"file": "alias", "unchanged": True}, "is changed")
        self.passes({"file": "alias/a.js", "exists": True})

    def test_the_executable_bit_is_part_of_a_file(self):
        for tree in (self.tree, self.seed):
            lay(tree, {"run.sh": "echo\n"})
        self.passes({"file": "run.sh", "unchanged": True})
        os.chmod(self.tree / "run.sh", 0o755)
        self.fails({"file": "run.sh", "unchanged": True}, "is changed")
        self.fails({"file": ".", "unchanged": True}, "run.sh")
        self.fails({"changed_only": ["docs/**"]}, "run.sh")
        self.passes({"changed_only": ["run.sh"]})
        os.chmod(self.tree / "run.sh", 0o644)
        os.chmod(self.seed / "run.sh", 0o755)  # losing the bit is a change too
        self.fails({"changed_only": []}, "run.sh")

    def test_a_file_of_the_same_size_and_mtime_is_compared_on_every_call(self):
        # filecmp keeps a cache keyed on (path, size, mtime): a changed file that keeps both would be called unchanged.
        for tree in (self.tree, self.seed):
            (tree / "s1").write_text("AAAA")
        stamp = os.stat(self.seed / "s1").st_mtime_ns
        os.utime(self.tree / "s1", ns=(stamp, stamp))
        self.passes({"file": "s1", "unchanged": True})
        (self.tree / "s1").write_text("BBBB")
        os.utime(self.tree / "s1", ns=(stamp, stamp))
        self.fails({"file": "s1", "unchanged": True}, "is changed")
        self.fails({"changed_only": []}, "s1")

    def test_a_glob_matches_a_name_with_a_newline_and_a_path_written_with_dots_and_slashes(self):
        lay(self.tree, {"docs/a\nb.md": "changed\n"})
        self.passes({"changed_only": ["docs/**"]})
        self.passes({"changed_only": ["docs/*"]})
        self.passes({"changed_only": ["**/*.md"]})
        (self.tree / "src/a.js").write_text("changed\n")
        self.passes({"changed_only": ["docs/**", "src/./a.js"]})
        self.passes({"changed_only": ["docs//**", "src//a.js"]})
        self.passes({"changed_only": ["./docs/**", "./src/./a.js"]})
        self.fails({"changed_only": ["docs/**", "src/b.js"]}, "src/a.js")


# ------------------------------------------------------------------------------------------------------- path escapes

class Escapes(Base):
    def test_a_path_that_leaves_the_tree_fails_and_the_value_outside_is_never_in_the_detail(self):
        absolute = str(self.outside / "secret.txt")
        for path in ("../outside/secret.txt", "src/../../outside/secret.txt", absolute, "/" + absolute.lstrip("/"),
                     "src/../../outside/sub"):
            for check in ({"contains": "SECRET"}, {"not_contains": "NOPE"}, {"exists": True}, {"exists": False},
                          {"unchanged": True}):
                with self.subTest(path=path, check=check):
                    found = self.run_one({"file": path, **check})
                    self.assertFalse(found["pass"], found)
                    self.assertIn("invalid check", found["detail"])
                    self.assertNotIn("TOP-SECRET", found["detail"])

    def test_the_runtime_refuses_what_the_validator_would_have_stopped(self):
        tree = oracle._root(self.tree, "tree")
        with self.assertRaises(oracle.Fail):
            oracle._inside(tree, "../outside/secret.txt")
        with self.assertRaises(oracle.Fail):
            oracle._inside(tree, "a/../../outside")
        self.assertEqual(oracle._inside(tree, "src/a.js"), os.path.join(tree, "src/a.js"))

    def test_a_symlink_out_of_the_tree_is_never_read_or_probed(self):
        (self.tree / "link.txt").symlink_to(self.outside / "secret.txt")
        (self.tree / "linkdir").symlink_to(self.outside)
        for path, check in (("link.txt", {"contains": "SECRET"}), ("link.txt", {"not_contains": "NOPE"}),
                            ("link.txt", {"exists": True}), ("link.txt", {"exists": False}),
                            ("linkdir/secret.txt", {"contains": "SECRET"}), ("linkdir/sub/deep.txt", {"exists": True}),
                            ("linkdir", {"unchanged": True}), ("linkdir/secret.txt", {"unchanged": False})):
            with self.subTest(path=path, check=check):
                found = self.fails({"file": path, **check}, "outside the tree")
                self.assertNotIn("TOP-SECRET", found["detail"])

    def test_a_symlink_inside_the_tree_is_followed(self):
        (self.tree / "alias.js").symlink_to(self.tree / "src/a.js")
        self.passes({"file": "alias.js", "contains": "const a"})
        (self.tree / "folder-alias").symlink_to(self.tree / "src")
        self.passes({"file": "folder-alias/a.js", "exists": True})

    def test_a_symlink_out_of_the_seed_tree_fails_an_unchanged(self):
        (self.seed / "link.txt").symlink_to(self.outside / "secret.txt")
        (self.tree / "link.txt").write_text("plain\n")
        self.fails({"file": "link.txt", "unchanged": True}, "outside the tree")

    def test_a_symlink_met_in_a_folder_walk_is_compared_by_its_target_and_not_followed(self):
        for tree in (self.tree, self.seed):
            (tree / "out.txt").symlink_to(self.outside / "secret.txt")
            (tree / "outdir").symlink_to(self.outside)
            (tree / "dangling").symlink_to(self.dir / "does-not-exist")
        self.passes({"changed_only": []})
        self.passes({"file": ".", "unchanged": True})
        (self.outside / "secret.txt").write_text("CHANGED-OUTSIDE\n")  # a read through the link would see this
        (self.outside / "sub/deep.txt").write_text("CHANGED-DEEP\n")
        self.passes({"changed_only": []})
        (self.tree / "out.txt").unlink()
        (self.tree / "out.txt").symlink_to(self.outside / "sub/deep.txt")  # retargeted: that is a change
        found = self.fails({"changed_only": ["docs/**"]}, "out.txt")
        self.assertNotIn("CHANGED", found["detail"])
        self.passes({"changed_only": ["out.txt"]})

    def test_a_link_replaced_by_a_file_is_a_change(self):
        (self.seed / "x").symlink_to("a.js")
        (self.tree / "x").write_text("a.js")
        self.fails({"changed_only": []}, "x")


# --------------------------------------------------------------------------------------------------------------- command

class Commands(Base):
    def setUp(self):
        super().setUp()
        self.scratch_home = self.dir / "scratch-home"
        self.scratch_home.mkdir()
        patch = mock.patch.object(tempfile, "tempdir", str(self.scratch_home))
        patch.start()
        self.addCleanup(patch.stop)

    def scratch_left(self) -> list[str]:
        return sorted(path.name for path in self.scratch_home.iterdir())

    def test_exit_status(self):
        self.passes({"command": "true", "exit": 0})
        found = self.fails({"command": py("print('boom'); raise SystemExit(3)"), "exit": 0}, "exit 3")
        self.assertIn("boom", found["detail"])
        self.assertIn("exit 0 was asked for", found["detail"])
        self.passes({"command": "exit 3", "exit": 3})
        self.fails({"command": "exit 3", "exit": 4}, "exit 3")
        self.passes({"command": "exit 1", "exit": "nonzero"})
        self.passes({"command": "exit 255", "exit": "nonzero"})
        self.fails({"command": "true", "exit": "nonzero"}, "exit 0, a nonzero status")
        self.passes({"command": "kill -KILL $$", "exit": "nonzero"})  # killed by a signal: it failed

    def test_a_shell_that_could_not_run_the_command_is_not_a_failing_test(self):
        found = self.fails({"command": "definitely-not-a-command-xyz", "exit": "nonzero"}, "could not run")
        self.assertIn("exit 127", found["detail"])
        self.fails({"command": "definitely-not-a-command-xyz", "exit": 0}, "exit 127")
        self.passes({"command": "definitely-not-a-command-xyz", "exit": 127})  # asked for by number

    def test_it_runs_in_a_copy_and_the_tree_is_never_touched(self):
        before = snapshot(self.tree)
        self.passes({"command": "echo edited > src/a.js; rm README.md; echo new > added.txt; mkdir made", "exit": 0})
        self.assertEqual(snapshot(self.tree), before)
        self.assertFalse((self.tree / "added.txt").exists())
        self.passes({"command": f"test \"$(pwd -P)\" != {shlex.quote(os.path.realpath(self.tree))} && test -f src/a.js", "exit": 0})
        self.passes({"command": "grep -q 'const a' src/a.js", "exit": 0})

    def test_the_copy_drops_caches_compiled_files_and_git(self):
        lay(self.tree, {".git/HEAD": "ref\n", "src/__pycache__/x.pyc": "x", "m.pyc": "y", "keep/.git/HEAD": "ref\n"})
        self.passes({"command": "test ! -e .git && test ! -e src/__pycache__ && test ! -e m.pyc && test -f keep/.git/HEAD", "exit": 0})

    def test_the_copy_keeps_a_symlink_that_stays_inside_as_a_link(self):
        (self.tree / "inner").symlink_to("src")
        (self.tree / "src/up").symlink_to("../README.md")
        (self.tree / "dangling").symlink_to("nowhere")
        self.passes({"command": "test -L inner && test \"$(readlink inner)\" = src && test -f inner/a.js && test -L src/up "
                                "&& grep -q demo src/up && test -L dangling", "exit": 0})

    def test_a_symlink_that_leaves_the_copy_is_left_out_so_a_command_cannot_write_through_it(self):
        (self.tree / "link").symlink_to(self.outside)  # an absolute link out
        (self.tree / "src/climb").symlink_to("../../outside")  # a relative one that climbs out of the copy
        (self.tree / "back").symlink_to(self.tree / "src")  # an absolute link into the candidate tree itself
        (self.tree / "file-link").symlink_to(self.outside / "secret.txt")
        self.passes({"command": "test ! -e link && test ! -L link && test ! -L src/climb && test ! -L back && test ! -L file-link",
                     "exit": 0})
        self.passes({"command": "echo pwned > link/hit; echo pwned > back/hit; echo pwned > file-link; true", "exit": 0})
        self.assertFalse((self.outside / "hit").exists())
        self.assertFalse((self.tree / "src/hit").exists())
        self.assertEqual((self.outside / "secret.txt").read_text(), "TOP-SECRET-VALUE\n")

    def test_stdin_is_closed_whatever_the_harness_has_on_its_own(self):
        # An open pipe nobody writes to: a command that inherited it would block on a read until its timeout.
        reader, writer = os.pipe()
        kept = os.dup(0)
        os.dup2(reader, 0)
        try:
            self.passes({"command": py("import sys; sys.exit(0 if sys.stdin.read() == '' else 1)"), "exit": 0, "timeout": 5})
        finally:
            os.dup2(kept, 0)
            for descriptor in (kept, reader, writer):
                os.close(descriptor)

    def test_the_environment_is_cut_to_five_variables_and_home_and_tmpdir_are_scratch(self):
        # Names the child sets for itself, not inherited: the shell's, and macOS CoreFoundation's, which every process gets
        # at start even under `env -i`.
        probe = ("import os, sys\n"
                 "keys = set(os.environ) - {'PWD', 'OLDPWD', 'SHLVL', '_', '__CF_USER_TEXT_ENCODING'}\n"
                 "ok = keys == {'PATH', 'HOME', 'TMPDIR', 'LC_ALL', 'SHIPLOOP_PROGRESS'}\n"
                 "ok = ok and os.path.isdir(os.environ['TMPDIR']) and os.environ['TMPDIR'] != " + repr(str(self.scratch_home)) + "\n"
                 "ok = ok and not os.path.realpath(os.getcwd()).startswith(os.path.realpath(os.environ['TMPDIR']))\n"
                 "ok = ok and os.environ['LC_ALL'] == 'C' and os.environ['SHIPLOOP_PROGRESS'] == 'off'\n"
                 "ok = ok and os.environ['PATH'] == " + repr(os.environ.get("PATH") or os.defpath) + "\n"
                 "ok = ok and os.path.isdir(os.environ['HOME']) and os.environ['HOME'] != " + repr(os.environ.get("HOME", "")) + "\n"
                 "ok = ok and not os.path.realpath(os.getcwd()).startswith(os.path.realpath(os.environ['HOME']))\n"
                 "sys.exit(0 if ok else 1)\n")
        with mock.patch.dict(os.environ, {"SECRET_TOKEN": "s3cret", "GIT_DIR": "/nowhere", "TMPDIR": str(self.scratch_home)}):
            found = self.passes({"command": py(probe), "exit": 0})
        self.assertNotIn("s3cret", found["detail"])
        self.assertEqual(self.scratch_left(), [])

    def test_a_timeout_kills_the_command_fails_the_check_whatever_exit_was_asked_for(self):
        for wanted in (0, "nonzero", 137):
            with self.subTest(exit=wanted):
                began = time.monotonic()
                found = self.fails({"command": "sleep 30", "exit": wanted, "timeout": 0.5}, "timed out")
                self.assertLess(time.monotonic() - began, 15)
                self.assertEqual(found["kind"], "command")
        self.assertEqual(self.scratch_left(), [])

    def test_a_timeout_kills_the_whole_process_group(self):
        pidfile = self.dir / "child.pid"
        command = f"sleep 60 & echo $! > {shlex.quote(str(pidfile))}; sleep 60"
        self.fails({"command": command, "exit": 0, "timeout": 1}, "timed out")
        pid = int(pidfile.read_text())
        self.assertTrue(gone(pid), "the background child survived the timeout")

    def test_a_command_that_ends_does_not_leave_what_it_started(self):
        pidfile = self.dir / "left.pid"
        self.passes({"command": f"sleep 60 & echo $! > {shlex.quote(str(pidfile))}", "exit": 0, "timeout": 20})
        self.assertTrue(gone(int(pidfile.read_text())), "a background child outlived its command")

    def test_the_tail_of_the_output_is_kept_and_the_head_dropped(self):
        found = self.fails({"command": py("print('HEADMARK' + 'x' * 6000 + 'TAILMARK'); raise SystemExit(2)"), "exit": 0}, "TAILMARK")
        self.assertNotIn("HEADMARK", found["detail"])
        self.assertLess(len(found["detail"]), 2500)

    def test_stderr_is_kept_with_stdout(self):
        self.fails({"command": "echo to-stderr 1>&2; exit 9", "exit": 0}, "to-stderr")

    def test_a_command_that_floods_its_output_is_stopped_and_fails_whatever_exit_was_asked_for(self):
        with mock.patch.object(oracle, "OUTPUT_LIMIT", 1 << 20):
            for wanted in (0, "nonzero", 137):
                with self.subTest(exit=wanted):
                    began = time.monotonic()
                    found = self.fails({"command": "yes FLOODMARK", "exit": wanted, "timeout": 60}, "more than 1 MB of output")
                    self.assertLess(time.monotonic() - began, 20)
                    self.assertIn("FLOODMARK", found["detail"])  # the end of the output is kept
                    self.assertLess(len(found["detail"]), 2500)
            # a command that writes a lot and ends at once is a flood too, (also with the exit it reports asked for)
            self.fails({"command": "head -c 3000000 /dev/zero", "exit": 0}, "more than 1 MB of output")
            self.fails({"command": "head -c 3000000 /dev/zero; exit 3", "exit": 3}, "more than 1 MB of output")
        self.assertEqual(self.scratch_left(), [])

    def test_a_flood_kills_the_whole_process_group(self):
        pidfile = self.dir / "flood.pid"
        with mock.patch.object(oracle, "OUTPUT_LIMIT", 1 << 20):
            self.fails({"command": f"sleep 60 & echo $! > {shlex.quote(str(pidfile))}; yes", "exit": 0, "timeout": 60},
                       "more than 1 MB")
        self.assertTrue(gone(int(pidfile.read_text())), "the background child survived the flood")

    def test_only_the_end_of_a_large_output_is_ever_read(self):
        # The log is read from the end: a read of the whole file would hand `read` an unbounded size.
        reads = []
        real = oracle.tempfile.TemporaryFile

        class Spy:
            def __init__(self):
                self.inner = real()

            def __enter__(self):
                self.inner.__enter__()
                return self

            def __exit__(self, *args):
                return self.inner.__exit__(*args)

            def read(self, size=-1):
                reads.append(size)
                return self.inner.read(size)

            def __getattr__(self, name):
                return getattr(self.inner, name)

        with mock.patch.object(oracle.tempfile, "TemporaryFile", Spy):
            self.fails({"command": py("print('x' * 400000); raise SystemExit(2)"), "exit": 0}, "exit 2")
        self.assertEqual(reads, [oracle.TAIL])

    def test_a_command_under_the_limit_is_not_a_flood(self):
        with mock.patch.object(oracle, "OUTPUT_LIMIT", 1 << 20):
            self.passes({"command": "head -c 500000 /dev/zero", "exit": 0})

    def test_the_output_has_no_name_for_the_command_to_find(self):
        self.passes({"command": "test \"$(ls ..)\" = \"$(printf 'home\\ntmp\\ntree')\" && test ! -e ../output.log", "exit": 0})

    def test_tmpdir_is_a_scratch_folder_that_goes_with_the_scratch(self):
        self.passes({"command": "test -d \"$TMPDIR\" && echo x > \"$TMPDIR/f\" && mktemp > /dev/null", "exit": 0})
        self.assertEqual(self.scratch_left(), [])

    def test_the_scratch_folder_is_gone_even_after_a_failure_and_a_read_only_folder(self):
        self.passes({"command": "mkdir ro && echo x > ro/f && chmod 500 ro", "exit": 0})
        self.fails({"command": "mkdir -p deep/er && echo x > deep/er/f && chmod 500 deep/er deep && exit 4", "exit": 0}, "exit 4")
        self.assertEqual(self.scratch_left(), [])

    def test_a_tree_that_cannot_be_copied_is_a_failed_check_and_leaves_no_scratch(self):
        with mock.patch.object(oracle.shutil, "copytree", side_effect=OSError(28, "No space left on device")):
            found = self.fails({"command": "true", "exit": 0}, "could not be evaluated")
        self.assertIn("No space left", found["detail"])
        self.assertEqual(self.scratch_left(), [])

    def test_a_missing_tree_fails(self):
        self.fails({"command": "true", "exit": 0}, "no tree", tree=None)
        self.fails({"command": "true", "exit": 0}, "is not a folder", tree=self.dir / "nothing")


class StandIns(Base):
    def setUp(self):
        super().setUp()
        lay(self.tree, {"calc.py": "def add(a, b):\n    return a + b\n",
                        "sharp.py": "from calc import add\nassert add(1, 2) == 3 and add(2, 2) == 4\n",
                        "lenient.py": "from calc import add\nassert add(0, 0) == 0\n"})
        self.scenario = lay(self.dir / "scenario", {"stand_ins/zero/calc.py": "def add(a, b):\n    return 0\n",
                                                    "stand_ins/empty/readme.txt": "nothing weaker\n"})

    def stand(self, **kwargs):
        return {"stand_in": "stand_ins/zero", "kills": True, **kwargs}

    def test_a_sharp_command_kills_the_weaker_implementation(self):
        found = self.passes(self.stand(command=f"{shlex.quote(sys.executable)} -B sharp.py"), scenario_dir=self.scenario)
        self.assertEqual(found["kind"], "stand_in")
        self.assertIn("was killed", found["detail"])
        self.assertIn("AssertionError", found["detail"])

    def test_a_command_that_already_fails_on_the_candidate_kills_nothing(self):
        lay(self.tree, {"calc.py": "def add(a, b):\n    return a - b\n"})  # the candidate is wrong itself
        found = self.fails(self.stand(command=f"{shlex.quote(sys.executable)} -B sharp.py"), "fails on the candidate itself",
                           scenario_dir=self.scenario)
        self.assertIn("AssertionError", found["detail"])
        broken = self.fails(self.stand(command="exit 1"), "fails on the candidate itself", scenario_dir=self.scenario)
        self.assertIn("exit 1", broken["detail"])
        # kills: false asks only that the command pass on the stand-in
        self.passes(self.stand(command="grep -q 'return 0' calc.py || true", kills=False), scenario_dir=self.scenario)

    def test_a_command_is_run_on_the_candidate_before_the_stand_in(self):
        marker = self.dir / "runs.log"
        command = f"echo \"$(grep -c 'return 0' calc.py)\" >> {shlex.quote(str(marker))}; test \"$(grep -c 'return 0' calc.py)\" = 0"
        self.passes(self.stand(command=command), scenario_dir=self.scenario)
        self.assertEqual(marker.read_text().split(), ["0", "1"])  # the candidate first, then the overlaid copy

    def test_a_lenient_command_lets_it_survive_and_the_check_fails(self):
        found = self.fails(self.stand(command=f"{shlex.quote(sys.executable)} -B lenient.py"), "survived",
                           scenario_dir=self.scenario)
        self.assertIn("exit 0", found["detail"])
        self.passes(self.stand(command=f"{shlex.quote(sys.executable)} -B lenient.py", kills=False), scenario_dir=self.scenario)
        self.fails(self.stand(command=f"{shlex.quote(sys.executable)} -B sharp.py", kills=False), "was killed",
                   scenario_dir=self.scenario)

    def test_the_overlay_goes_over_a_copy_and_never_into_the_tree_or_the_scenario(self):
        before = (snapshot(self.tree), snapshot(self.scenario))
        self.passes(self.stand(command=f"{shlex.quote(sys.executable)} -B sharp.py"), scenario_dir=self.scenario)
        self.assertEqual((snapshot(self.tree), snapshot(self.scenario)), before)
        self.passes(self.stand(command="grep -q 'return 0' calc.py", kills=False), scenario_dir=self.scenario)
        self.passes({"command": "grep -q 'a + b' calc.py", "exit": 0}, scenario_dir=self.scenario)

    def test_a_command_that_never_ran_or_timed_out_kills_nothing(self):
        self.fails(self.stand(command="no-such-command-xyz"), "said nothing", scenario_dir=self.scenario)
        self.fails(self.stand(command="no-such-command-xyz", kills=False), "said nothing", scenario_dir=self.scenario)
        self.fails(self.stand(command="sleep 30", timeout=0.5), "timed out", scenario_dir=self.scenario)

    def test_the_overlay_is_a_folder_of_the_scenario(self):
        self.fails(self.stand(command="true"), "no scenario folder")
        self.fails(self.stand(command="true", stand_in="stand_ins/missing"), "is not a folder", scenario_dir=self.scenario)
        self.fails(self.stand(command="true", stand_in="stand_ins/zero/calc.py"), "is not a folder", scenario_dir=self.scenario)
        found = self.run_one(self.stand(command="true", stand_in="../tree"), scenario_dir=self.scenario)
        self.assertFalse(found["pass"])
        self.assertIn("climbs out", found["detail"])

    def test_an_overlay_that_is_a_symlink_out_of_the_scenario_is_not_used(self):
        (self.scenario / "stand_ins/escape").symlink_to(self.outside)
        found = self.fails(self.stand(command="true", stand_in="stand_ins/escape"), "outside the tree", scenario_dir=self.scenario)
        self.assertNotIn("TOP-SECRET", found["detail"])

    def test_the_overlay_replaces_a_symlink_of_the_copy_and_never_writes_through_it(self):
        victim = lay(self.tree, {"victim-target.txt": "ORIGINAL\n"}) / "victim-target.txt"
        (self.tree / "victim.txt").symlink_to("victim-target.txt")
        lay(self.scenario, {"stand_ins/zero/victim.txt": "WEAK\n"})
        self.passes(self.stand(command="grep -q WEAK victim.txt && grep -q ORIGINAL victim-target.txt", kills=False),
                    scenario_dir=self.scenario)
        self.assertEqual(victim.read_text(), "ORIGINAL\n")
        self.assertTrue((self.tree / "victim.txt").is_symlink())

    def test_the_overlay_refuses_to_write_below_a_symlinked_folder_of_the_copy(self):
        (self.tree / "linked").symlink_to("src")  # a link that stays inside the copy is kept, so the overlay meets it
        lay(self.scenario, {"stand_ins/zero/linked/planted.txt": "WEAK\n"})
        self.fails(self.stand(command="true"), "write through the symlink", scenario_dir=self.scenario)
        self.assertFalse((self.tree / "src/planted.txt").exists())

    def test_an_overlay_can_replace_a_folder_with_a_file_and_a_file_with_a_folder(self):
        lay(self.tree, {"was_file": "f\n", "was_dir/inside.txt": "i\n"})
        lay(self.scenario, {"stand_ins/zero/was_file/now.txt": "n\n"})
        (self.scenario / "stand_ins/zero/was_dir").write_text("now a file\n")
        self.passes(self.stand(command="test -f was_file/now.txt && test -f was_dir", kills=False), scenario_dir=self.scenario)


# ---------------------------------------------------------------------------------------------------- run_check, verdict

class Robustness(Base):
    def test_a_check_that_cannot_be_evaluated_fails_with_the_reason_and_never_raises(self):
        for check in (None, "outcome", 3, ["outcome"], {}, {"outcome": "done"}, {"file": "../x", "exists": True},
                      {"packet_contains": "("}, {"field": "a", "equals": 1, "exists": True}, {"nope": 1}):
            with self.subTest(check=check):
                found = run_check(check, Bundle())
                self.assertEqual(found["pass"], False)
                self.assertEqual(found["kind"], "invalid")
                self.assertTrue(found["detail"].startswith("invalid check: "), found)
                self.assertEqual(set(found), {"proves", "kind", "pass", "detail"})

    def test_proves_is_kept_from_a_malformed_check_so_that_it_fails_the_id_it_names(self):
        found = run_check({"outcome": "done", "proves": "P1"}, Bundle())
        self.assertEqual((found["proves"], found["pass"]), ("P1", False))
        self.assertIsNone(run_check({"outcome": "done", "proves": 5}, Bundle())["proves"])
        self.assertIsNone(run_check("x", Bundle())["proves"])
        good = run_check({"outcome": ["done"], "proves": "P1"}, Bundle(result={"outcome": "done"}))
        self.assertEqual((good["proves"], good["kind"], good["pass"]), ("P1", "outcome", True))

    def test_a_runner_that_raises_is_a_failed_check(self):
        with mock.patch.dict(oracle.RUNNERS, {"outcome": mock.Mock(side_effect=ZeroDivisionError("boom"))}):
            found = run_check({"outcome": ["done"]}, Bundle(result={"outcome": "done"}))
        self.assertFalse(found["pass"])
        self.assertIn("ZeroDivisionError: boom", found["detail"])
        self.assertEqual(found["kind"], "outcome")

    def test_a_bundle_of_the_wrong_shape_fails_the_check_and_not_the_harness(self):
        self.assertFalse(run_check({"packet_contains": "x"}, Bundle(packet=b"x"))["pass"])
        self.assertFalse(run_check({"file": "a", "exists": True}, Bundle(tree=3))["pass"])
        self.assertFalse(run_check({"trace": "refusals_max", "value": 1}, Bundle(trace=3))["pass"])

    def test_run_checks_keeps_the_order_and_one_result_per_check(self):
        checks = [{"outcome": ["done"]}, {"outcome": ["blocked"]}, {"packet_issued": False, "proves": "C1"}, 4]
        results = run_checks(checks, Bundle(result={"outcome": "done"}))
        self.assertEqual([row["pass"] for row in results], [True, False, True, False])
        self.assertEqual([row["kind"] for row in results], ["outcome", "outcome", "packet_issued", "invalid"])
        self.assertEqual(run_checks([], Bundle()), [])

    def test_run_checks_given_something_that_is_not_a_list_is_one_failed_check(self):
        for value in (None, {"outcome": ["done"]}, "x"):
            with self.subTest(value=value):
                [row] = run_checks(value, Bundle())
                self.assertFalse(row["pass"])
                self.assertIn("must be a list", row["detail"])

    def test_the_same_bundle_gives_the_same_results(self):
        checks = [{"file": "src/a.js", "unchanged": True}, {"changed_only": ["docs/**"]},
                  {"command": py("print(1)"), "exit": 0}, {"field": "a", "exists": False}]
        bundle = self.bundle(result={"a": 1})
        self.assertEqual(run_checks(checks, bundle), run_checks(checks, bundle))

    def test_a_bundle_names_the_places_a_run_keeps_its_records(self):
        bundle = Bundle(tree=Path("/t"), run_dir=Path("/r"))
        self.assertEqual((bundle.knowledge, bundle.notes, bundle.records),
                         (Path("/t/docs/shiploop"), Path("/r/notes"), Path("/r")))
        empty = Bundle()
        self.assertEqual((empty.knowledge, empty.notes, empty.records), (None, None, None))
        self.assertEqual((empty.result, empty.trace, empty.packet, empty.issued, empty.settled), (None, None, None, False, False))


def row(proves, passed, kind="outcome", detail="d"):
    return {"proves": proves, "kind": kind, "pass": passed, "detail": detail}


class Verdict(unittest.TestCase):
    def test_caught_held_and_a_pass(self):
        found = verdict(["P1", "P2"], ["C1"], [row("P1", True), row("P2", True), row("C1", True), row(None, True)])
        self.assertEqual(found["caught"], {"P1": True, "P2": True})
        self.assertEqual(found["held"], {"C1": True})
        self.assertEqual(found["unproved_failures"], [])
        self.assertTrue(found["pass"])

    def test_a_missed_planted_condition_fails_the_sample(self):
        found = verdict(["P1", "P2"], ["C1"], [row("P1", True), row("P2", False), row("C1", True)])
        self.assertEqual(found["caught"], {"P1": True, "P2": False})
        self.assertFalse(found["pass"])

    def test_a_broken_control_fails_the_sample(self):
        found = verdict(["P1"], ["C1", "C2"], [row("P1", True), row("C1", False), row("C2", True)])
        self.assertEqual(found["held"], {"C1": False, "C2": True})
        self.assertFalse(found["pass"])

    def test_an_id_no_check_names_is_not_exercised_and_is_never_a_pass(self):
        found = verdict(["P1", "P2"], ["C1"], [row("P1", True)])
        self.assertEqual(found["caught"], {"P1": True, "P2": None})
        self.assertEqual(found["held"], {"C1": None})
        self.assertIsNone(found["caught"]["P2"])
        self.assertTrue(found["pass"])  # the exercised id holds and nothing failed: a tier may run a part of the checks
        self.assertEqual(verdict(["P1"], [], [row("P1", False)])["caught"], {"P1": False})

    def test_a_failing_check_that_proves_nothing_fails_the_sample_and_is_listed(self):
        found = verdict(["P1"], ["C1"], [row("P1", True), row("C1", True), row(None, False, "file", "src/x.js is changed")])
        self.assertEqual(found["caught"], {"P1": True})
        self.assertEqual(found["held"], {"C1": True})
        self.assertEqual(found["unproved_failures"], ["file: src/x.js is changed"])
        self.assertFalse(found["pass"])

    def test_a_failing_check_that_names_an_unknown_id_is_an_unproved_failure(self):
        found = verdict(["P1"], [], [row("P1", True), row("P9", False, "command", "exit 1")])
        self.assertEqual(found["unproved_failures"], ["command: exit 1"])
        self.assertFalse(found["pass"])
        self.assertTrue(verdict(["P1"], [], [row("P1", True), row("P9", True)])["pass"])

    def test_an_id_two_checks_prove_is_caught_only_when_both_pass(self):
        both = verdict(["P1"], [], [row("P1", True), row("P1", True, "command")])
        self.assertEqual(both["caught"], {"P1": True})
        one_fails = verdict(["P1"], [], [row("P1", True), row("P1", False, "command", "exit 1")])
        self.assertEqual(one_fails["caught"], {"P1": False})
        self.assertEqual(one_fails["unproved_failures"], [])  # it is attributed to P1, not unproved
        self.assertFalse(one_fails["pass"])
        first_fails = verdict(["P1"], [], [row("P1", False), row("P1", True)])
        self.assertEqual(first_fails["caught"], {"P1": False})

    def test_a_check_that_proves_one_id_does_not_prove_another(self):
        found = verdict(["P1", "P2"], [], [row("P1", True), row("P2", False)])
        self.assertEqual(found["caught"], {"P1": True, "P2": False})

    def test_nothing_run_is_not_a_pass(self):
        for results in ([], None):
            with self.subTest(results=results):
                found = verdict(["P1"], ["C1"], results)
                self.assertEqual((found["caught"], found["held"], found["checks"]), ({"P1": None}, {"C1": None}, 0))
                self.assertFalse(found["pass"])
        self.assertFalse(verdict([], [], [])["pass"])
        self.assertTrue(verdict([], [], [row(None, True)])["pass"])  # only unproved checks (a render scenario of flags)

    def test_a_pass_value_that_is_not_true_is_a_failure(self):
        found = verdict(["P1"], [], [{"proves": "P1", "kind": "x", "pass": "yes", "detail": ""}])
        self.assertEqual(found["caught"], {"P1": False})
        self.assertFalse(found["pass"])

    def test_a_malformed_result_row_is_an_unproved_failure(self):
        found = verdict(["P1"], [], [row("P1", True), "junk", {"proves": ["P1"], "kind": "k", "pass": False, "detail": "weird"}])
        self.assertEqual(len(found["unproved_failures"]), 2)
        self.assertFalse(found["pass"])

    def test_no_ids_at_all(self):
        self.assertEqual(verdict(None, None, [row(None, True)])["caught"], {})
        self.assertFalse(verdict(None, None, [row(None, False)])["pass"])

    def test_run_checks_feeds_verdict(self):
        tree = lay(Path(tempfile.mkdtemp(prefix="stage-oracle-verdict-")), {"a.txt": "kept\n"})
        self.addCleanup(shutil.rmtree, tree, True)
        seed = lay(Path(tempfile.mkdtemp(prefix="stage-oracle-verdict-")), {"a.txt": "kept\n"})
        self.addCleanup(shutil.rmtree, seed, True)
        bundle = Bundle(result={"outcome": "send-back", "failed_expectations": [{"route": "check"}]}, tree=tree, seed_tree=seed)
        checks = [{"outcome": ["send-back"], "proves": "P1"}, {"field": "failed_expectations[*].route", "equals": "check", "proves": "P1"},
                  {"file": "a.txt", "unchanged": True, "proves": "C1"}, {"changed_only": ["b.txt"]}]
        found = verdict(["P1", "P2"], ["C1"], run_checks(checks, bundle))
        self.assertEqual((found["caught"], found["held"], found["pass"]), ({"P1": True, "P2": None}, {"C1": True}, True))
        (tree / "a.txt").write_text("touched\n")
        found = verdict(["P1", "P2"], ["C1"], run_checks(checks, bundle))
        self.assertEqual(found["held"], {"C1": False})
        self.assertEqual(len(found["unproved_failures"]), 1)  # changed_only ["b.txt"] fails too
        self.assertFalse(found["pass"])


# ------------------------------------------------------------------------------------------------------------ boundary

class Boundary(unittest.TestCase):
    def test_the_stage_suite_and_its_cases_are_outside_the_evaluator_digest_and_the_qualification_snapshot(self):
        suite, cases = HARNESS / "stage_suite", HARNESS / "stage_cases"
        self.assertTrue((suite / "stage_oracle.py").is_file())
        mine = {path for folder in (suite, cases) if folder.is_dir() for path in folder.rglob("*")}
        self.assertIn(suite / "stage_oracle.py", mine)
        evaluator, graded = set(boundary.evaluator_files(HARNESS)), set(boundary.oracle_files(HARNESS))
        self.assertFalse(mine & evaluator)
        self.assertFalse(mine & graded)
        self.assertNotIn(suite / "stage_oracle.py", evaluator)
        self.assertFalse(any(path.parent.name in ("stage_suite", "stage_cases") for path in evaluator))
        snapshot_files = boundary.qualification_snapshot(HARNESS)["files"]
        self.assertFalse([name for name in snapshot_files if "/stage_suite/" in name or "/stage_cases/" in name])
        self.assertFalse([name for name in snapshot_files if name.startswith("test/shiploop-e2e-stage")])

    def test_nothing_of_the_suite_is_in_the_top_level_of_the_harness(self):
        self.assertEqual(sorted(path.name for path in HARNESS.iterdir() if path.is_file() and path.name.startswith("stage")), [])

    def test_adding_or_changing_a_stage_file_leaves_the_digest_where_it_was(self):
        with tempfile.TemporaryDirectory(prefix="stage-oracle-boundary-") as temp:
            harness = lay(Path(temp), {"run.py": "x = 1\n", "checks/c.py": "y = 2\n", "SPEC.md": "s\n"})
            before = boundary.fingerprint(harness, None)
            lay(harness, {"stage_suite/stage_oracle.py": "z = 3\n", "stage_cases/v/s/scenario.json": "{}\n",
                          "stage_suite/__pycache__/m.pyc": "c"})
            self.assertEqual(boundary.fingerprint(harness, None), before)
            lay(harness, {"stage_suite/stage_oracle.py": "z = 4\n", "stage_cases/v/s/scenario.json": "{\"a\": 1}\n"})
            self.assertEqual(boundary.fingerprint(harness, None), before)
            lay(harness, {"run.py": "x = 2\n"})
            self.assertNotEqual(boundary.fingerprint(harness, None)["evaluator"], before["evaluator"])

    def test_the_candidate_may_not_change_the_suite_or_its_tests(self):
        for path in ("test/shiploop_e2e/stage_suite/stage_oracle.py", "test/shiploop_e2e/stage_cases/x/scenario.json",
                     "test/shiploop-e2e-stage-oracle.test.py"):
            with self.subTest(path=path):
                self.assertFalse(boundary.candidate_path(path))

    def test_the_engine_reads_no_harness_module(self):
        text = (HARNESS / "stage_suite" / "stage_oracle.py").read_text()
        for name in ("run", "hosts", "boundary", "slice", "metrics"):
            self.assertNotRegex(text, rf"^\s*(import|from) {name}\b")


if __name__ == "__main__":
    unittest.main()
