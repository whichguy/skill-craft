#!/usr/bin/env python3
"""G-RENDER of the efficiency plan: `packets.py --offline --text-dir` (fixed text at a stated run-directory and CLI path
length) and `render_diff.py` (every added or removed line, its size, its allowlist entry, the head table).

The renders here are the checkout's own offline walk (no model).  The comparison tests use small synthetic render
directories so each rule fails on exactly one input: a planted extra line, an allowlisted line, an offset that does not
pay, a head over its table value, renders made with other options, a malformed allowlist.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import packets  # noqa: E402
import render_diff  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

CASE = json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text())["node-fix-bug"]


def run(main, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main([str(a) for a in argv])
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 2
            if isinstance(exc.code, str):
                err.write(exc.code)
    return code, out.getvalue(), err.getvalue()


# --- padded paths ----------------------------------------------------------------------------------------------------

class PaddedPathTests(unittest.TestCase):
    def test_every_length_from_the_base_plus_two_is_exact_including_the_gaps_a_component_cannot_fill(self):
        for length in list(range(len("/base") + 2, len("/base") + 130)) + [len("/base") + 43, len("/base") + 42]:
            with self.subTest(length=length):
                path = packets.padded_path("/base", length)
                self.assertEqual(len(path), length)
                self.assertTrue(path.startswith("/base/"))
                self.assertNotIn("//", path)
                self.assertTrue(all(0 < len(part) <= 40 for part in path[len("/base/"):].split("/")))

    def test_the_base_itself_is_the_path_when_it_already_has_the_length(self):
        self.assertEqual(packets.padded_path("/base", 5), "/base")

    def test_a_length_one_more_than_the_base_or_less_than_it_cannot_be_made(self):
        for length in (len("/base") + 1, 3):
            with self.subTest(length=length), self.assertRaises(SystemExit):
                packets.padded_path("/base", length)


# --- the text render -------------------------------------------------------------------------------------------------

def render_to(directory: Path, *flags: str, delegation: str = "inline") -> dict:
    code, out, err = run(packets.main, ["--offline", "node-fix-bug", "--delegation", delegation, "--text-dir", directory, *flags])
    if code != 0:
        raise AssertionError(f"packets.py exited {code}: {err or out}")
    return json.loads((directory / "manifest.json").read_text())


def read_all(directory: Path) -> dict[str, str]:
    return {path.name: path.read_text() for path in sorted(directory.glob("*.txt"))}


class TextRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_default = tempfile.gettempdir()
        cls.temp = tempfile.TemporaryDirectory()
        base = Path(cls.temp.name)
        cls.dirs = {name: base / name for name in ("a83", "b83", "a163", "ask83", "bare")}
        cls.manifests = {
            "a83": render_to(cls.dirs["a83"], "--run-dir-length", "83", "--cli-path-length", "96"),
            "b83": render_to(cls.dirs["b83"], "--run-dir-length", "83", "--cli-path-length", "96"),
            "a163": render_to(cls.dirs["a163"], "--run-dir-length", "163", "--cli-path-length", "96"),
            "ask83": render_to(cls.dirs["ask83"], "--run-dir-length", "83", "--cli-path-length", "96", delegation="ask-agent"),
            "bare": render_to(cls.dirs["bare"]),
        }
        cls.text = {name: read_all(directory) for name, directory in cls.dirs.items()}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_each_packet_is_written_printed_and_whole_with_a_manifest_that_states_the_sizes_and_the_options(self):
        manifest = self.manifests["a83"]
        self.assertEqual((manifest["case"], manifest["delegation"], manifest["run_dir_length"], manifest["cli_path_length"]),
                         ("node-fix-bug", "inline", 83, 96))
        self.assertEqual(manifest["text_format"], packets.TEXT_FORMAT)
        self.assertEqual(manifest["print_limit"], navigator.PRINT_LIMIT)
        self.assertGreaterEqual(len(manifest["packets"]), 10)
        names = {row["key"] for row in manifest["packets"]}
        self.assertEqual(set(self.text["a83"]), {f"{key}.{form}.txt" for key in names for form in ("printed", "whole")})
        for row in manifest["packets"]:
            with self.subTest(packet=row["key"]):
                printed = self.text["a83"][row["key"] + ".printed.txt"]
                whole = self.text["a83"][row["key"] + ".whole.txt"]
                self.assertEqual((len(printed), len(whole)), (row["printed"], row["whole"]))
                self.assertEqual(row["head"], len(whole) > navigator.PRINT_LIMIT)
                # Every print ends with the end line (a whole print is the file plus it), so a cut one lacks it.
                self.assertTrue(printed.endswith("\n" + navigator.HEAD_END + "\n"))
                self.assertEqual(printed == whole + navigator.HEAD_END + "\n", not row["head"])
        self.assertTrue(any(row["head"] for row in manifest["packets"]))
        self.assertEqual(set(manifest["source"]), {"commit", "dirty"})

    def test_the_run_directory_has_exactly_the_stated_length_wherever_a_packet_prints_it(self):
        for name, length in (("a83", 83), ("b83", 83), ("a163", 163), ("ask83", 83)):
            seen = 0
            for file, text in self.text[name].items():
                for found in re.findall(r"--run-dir=(\S+)", text):
                    seen += 1
                    self.assertEqual(len(found), length, (name, file, found))
                for found in re.findall(r"WORKTREE = (\S+)", text):
                    seen += 1
                    self.assertEqual(len(found), length - len("/run"), (name, file, found))
            self.assertGreater(seen, 30, name)

    def test_the_cli_path_has_exactly_the_stated_length_and_the_default_prints_the_bare_name(self):
        for name in ("a83", "a163", "ask83"):
            paths = [m for text in self.text[name].values() for m in re.findall(r"python3 (\S+) (?:complete|next|pause)\b", text)]
            self.assertGreater(len(paths), 20, name)
            self.assertEqual({len(path) for path in paths}, {96}, name)
            self.assertEqual({path for path in paths}, {next(iter(set(paths)))}, name)
        head = self.text["a83"]["01-step-plan.printed.txt"]
        self.assertGreaterEqual(len(re.findall(r"python3 \S+ (?:complete|next|pause)\b", head)), 3)
        bare = [m for text in self.text["bare"].values() for m in re.findall(r"python3 (\S+) (?:complete|next|pause)\b", text)]
        self.assertEqual(set(bare), {"shiploop"})
        self.assertIsNone(self.manifests["bare"]["cli_path_length"])

    def test_the_red_check_script_and_the_callbacks_name_the_same_cli_under_one_install_root(self):
        test_packet = self.text["a83"]["08-test.whole.txt"]
        red = re.search(r"red-check: (\S+) (\S+) red-check", test_packet)
        callback = re.search(r"python3 (\S+) complete", test_packet)
        self.assertEqual(red.group(1), "/usr/bin/python3")
        self.assertEqual(red.group(2), callback.group(1))

    def test_two_renders_of_one_tree_are_the_same_text(self):
        self.assertEqual(self.text["a83"], self.text["b83"])
        self.assertEqual(self.manifests["a83"], self.manifests["b83"])

    def test_the_text_does_not_depend_on_the_temporary_directory(self):
        with tempfile.TemporaryDirectory(prefix="t") as other, mock.patch.object(tempfile, "tempdir", other):
            self.assertNotEqual(tempfile.gettempdir(), self.temp_default)
            elsewhere = Path(other) / "render"
            render_to(elsewhere, "--run-dir-length", "83", "--cli-path-length", "96")
            self.assertEqual(read_all(elsewhere), self.text["a83"])

    def test_nothing_of_this_machine_or_checkout_is_in_the_text(self):
        for name, files in self.text.items():
            blob = "\n".join(files.values())
            for leak in (str(ROOT), "shiploop-step-packets-", *([sys.executable] if sys.executable != packets.CANONICAL_PYTHON else [])):
                self.assertNotIn(leak, blob, (name, leak))
            self.assertIsNone(re.search(re.escape(tempfile.gettempdir()) + r"/(sl-|shiploop-step-packets-)", blob), name)

    def test_ids_are_derived_from_a_counter_and_the_real_generator_is_back_afterwards(self):
        real = uuid.uuid4
        first = packets.offline_renders(CASE, run_dir_length=83, cli_path_length=96)
        self.assertIs(uuid.uuid4, real)
        self.assertNotEqual(real().hex, real().hex)
        ids = re.findall(r"nav-[0-9a-f]{32}", first["01-step-plan"]["whole"])
        self.assertGreaterEqual(len(set(ids)), 4)
        self.assertEqual(first["01-step-plan"]["whole"], self.text["a83"]["01-step-plan.whole.txt"])

    def test_the_longer_run_directory_makes_longer_packets_and_a_packet_may_flip_between_whole_and_head(self):
        short, long = ({row["key"]: row for row in self.manifests[name]["packets"]} for name in ("a83", "a163"))
        self.assertTrue(all(long[key]["whole"] > short[key]["whole"] for key in short))
        # validate-existing is a whole print at 83 and passes the print limit at 163 (the plan's head-to-whole flip, read the other way).
        self.assertFalse(short["05-validate-existing"]["head"])
        self.assertTrue(long["05-validate-existing"]["head"])

    def test_the_natural_run_directory_is_this_machines_temporary_directory_and_the_sizes_are_still_fixed(self):
        manifest = self.manifests["bare"]
        self.assertEqual(manifest["run_dir_length"], len(tempfile.gettempdir()) + len("/shiploop-step-packets-") + 8 + len("/run"))
        again = Path(self.temp.name) / "bare-again"
        render_to(again)
        self.assertEqual(read_all(again), self.text["bare"])

    def test_the_ask_agent_route_prints_its_delegation_prefix_in_the_whole_text_only_and_is_its_own_manifest(self):
        self.assertEqual(self.manifests["ask83"]["delegation"], "ask-agent")
        self.assertNotEqual(self.text["ask83"]["01-step-plan.whole.txt"], self.text["a83"]["01-step-plan.whole.txt"])

    def test_the_default_walk_is_what_it_was(self):
        """offline_packets keeps this machine's paths and random ids: the other suites rely on its sizes and pins."""
        texts = packets.offline_packets(CASE)
        self.assertEqual(list(texts), [row["key"] for row in self.manifests["a83"]["packets"]])
        self.assertIn("shiploop-step-packets-", texts["01-step-plan"])
        printed = packets.offline_packets(CASE, printed=True)
        self.assertTrue(printed["01-step-plan"].rstrip("\n").endswith(navigator.HEAD_END))
        self.assertFalse(printed["03-test-spec"].rstrip("\n").endswith(navigator.HEAD_END))

    def test_the_options_are_refused_where_they_mean_nothing(self):
        directory = Path(self.temp.name) / "refused"
        for argv in (["--offline", "node-fix-bug", "--run-dir-length", "83"],
                     ["--offline", "node-fix-bug", "--cli-path-length", "96"],
                     ["--text-dir", directory],
                     ["--offline", "node-fix-bug", "--text-dir", directory, "--json"],
                     ["--offline", "node-fix-bug", "--text-dir", directory, "--run-dir-length", "10"],
                     ["--offline", "node-fix-bug", "--text-dir", directory, "--cli-path-length", "30"]):
            with self.subTest(argv=[str(a) for a in argv]):
                code, _, err = run(packets.main, argv)
                self.assertEqual(code, 2)
                self.assertFalse(directory.exists())

    def test_a_directory_that_already_holds_a_render_is_not_written_over(self):
        code, _, err = run(packets.main, ["--offline", "node-fix-bug", "--text-dir", self.dirs["a83"]])
        self.assertNotEqual(code, 0)
        self.assertEqual(read_all(self.dirs["a83"]), self.text["a83"])

    def test_a_run_directory_that_cannot_be_reached_from_the_temporary_directory_is_refused_with_the_remedy(self):
        with tempfile.TemporaryDirectory() as other:
            code, _, err = run(packets.main, ["--offline", "node-fix-bug", "--text-dir", Path(other) / "x", "--run-dir-length", "24"])
        self.assertNotEqual(code, 0)
        self.assertIn("TMPDIR", err)


# --- render_diff -------------------------------------------------------------------------------------------------------

ALPHA = "alpha line one\nalpha line two\nalpha line three\n"
BETA = "beta line one\nbeta line two\n"


def make_render(directory: Path, packet_texts: dict[str, tuple[str, str]], **manifest) -> Path:
    directory.mkdir(parents=True)
    rows = []
    for key, (printed, whole) in packet_texts.items():
        (directory / f"{key}.printed.txt").write_text(printed)
        (directory / f"{key}.whole.txt").write_text(whole)
        rows.append({"key": key, "stage": key.split("-", 1)[1], "kind": "producer", "whole": len(whole), "printed": len(printed),
                     "head": printed != whole})
    (directory / "manifest.json").write_text(json.dumps({
        "tool": "test", "text_format": 1, "case": "demo", "delegation": "inline", "run_dir_length": 83, "cli_path_length": 96,
        "install_root_length": 63, "python": "/usr/bin/python3", "print_limit": 16000, "host_cut": 20000,
        "source": {"commit": "0123456789abcdef", "dirty": False}, "packets": rows, **manifest}))
    return directory


def line_size(text: str) -> int:
    return len(text) + 1


class RenderDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.changes = self.base / "changes.json"
        self.table = self.base / "table.json"
        self.write_changes({})
        self.write_table({"demo": {"inline/83/96": {"alpha": 200, "beta": 200, "alpha-improve": 200}}})

    def tearDown(self):
        self.temp.cleanup()

    def write_changes(self, units: dict) -> None:
        self.changes.write_text(json.dumps({"_doc": "x", "U1": [], "U2": [], **units}))

    def write_table(self, table: dict) -> None:
        self.table.write_text(json.dumps(table))

    def renders(self, old: dict, new: dict, **new_manifest) -> tuple[Path, Path]:
        return (make_render(self.base / "old", old), make_render(self.base / "new", new, **new_manifest))

    def diff(self, old: Path, new: Path, *flags: str, unit: str = "U1"):
        return run(render_diff.main, [old, new, "--unit", unit, "--changes", self.changes, "--head-table", self.table, *flags])

    SAME = {"01-alpha": (ALPHA, ALPHA), "02-beta": (BETA, BETA)}

    def test_identical_renders_pass(self):
        old, new = self.renders(self.SAME, self.SAME)
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 0, out)
        self.assertIn("All 2 stages pass.", out)

    def test_a_planted_extra_line_fails_names_the_line_and_its_size_and_says_it_is_not_allowlisted(self):
        extra = "PLANTED: a line nobody allowed"
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + extra + "\n", ALPHA + extra + "\n")})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn(extra, out)
        self.assertIn(f"+ {line_size(extra):>5}  [PW] {extra}", out)
        self.assertIn("NOT ALLOWLISTED", out)

    def test_a_line_added_to_the_packet_file_only_is_judged_too(self):
        extra = "PLANTED: only the packet file has it"
        old, new = self.renders({"01-alpha": (ALPHA, ALPHA + "tail\n")}, {"01-alpha": (ALPHA, ALPHA + "tail\n" + extra + "\n")})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn(f"[W] {extra}", out)

    def test_an_approved_entry_allows_the_line_and_the_output_names_the_decision(self):
        extra = "ALLOWED: the new line of the unit"
        self.write_changes({"U1": [{"prefix": "ALLOWED: the new line", "approval": "plan row SP-2, owner 2026-10-17"}]})
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + extra + "\n", ALPHA + extra + "\n")})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 0, out)
        self.assertIn("approval: plan row SP-2, owner 2026-10-17", out)

    def test_an_offset_entry_passes_when_the_removed_lines_it_names_pay_for_the_added_ones(self):
        self.write_changes({"U1": [{"prefix": "NEW: shorter", "offset": ["OLD: a much longer line"]}]})
        old_text = ALPHA + "OLD: a much longer line that goes away\n"
        new_text = ALPHA + "NEW: shorter\n"
        old, new = self.renders({"01-alpha": (old_text, old_text)}, {"01-alpha": (new_text, new_text)})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 0, out)
        self.assertIn("offset: OLD: a much longer line", out)
        self.assertIn("-    ", out)

    def test_an_offset_that_pays_less_than_the_entry_adds_fails_and_says_by_how_much(self):
        self.write_changes({"U1": [{"prefix": "NEW: a longer line", "offset": ["OLD: short"]}]})
        old_text, new_text = ALPHA + "OLD: short\n", ALPHA + "NEW: a longer line than the old\n"
        old, new = self.renders({"01-alpha": (old_text, old_text)}, {"01-alpha": (new_text, new_text)})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn(f"adds {line_size('NEW: a longer line than the old')} characters but the removed lines it names pay "
                      f"{line_size('OLD: short')}", out)

    def test_an_offset_that_names_a_line_nobody_removed_fails(self):
        self.write_changes({"U1": [{"prefix": "NEW: a line", "offset": ["OLD: not removed at all"]}]})
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + "NEW: a line\n", ALPHA + "NEW: a line\n")})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn("names no unused removed line", out)

    def test_one_removed_line_pays_for_one_entry_only(self):
        self.write_changes({"U1": [{"prefix": "NEW: first", "offset": ["OLD: the one line"]},
                                   {"prefix": "NEW: second", "offset": ["OLD: the one line"]}]})
        old_text = ALPHA + "OLD: the one line is long enough to pay for both of them\n"
        new_text = ALPHA + "NEW: first\nNEW: second\n"
        old, new = self.renders({"01-alpha": (old_text, old_text)}, {"01-alpha": (new_text, new_text)})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("<- U1 offset"), 2)
        self.assertIn("names no unused removed line", out)

    def test_an_entry_of_another_unit_does_not_allow_the_line_unless_that_unit_is_named_too(self):
        extra = "ALLOWED: for the other unit"
        self.write_changes({"U2": [{"prefix": "ALLOWED: for the other", "approval": "decision"}]})
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + extra + "\n", ALPHA + extra + "\n")})
        self.assertEqual(self.diff(old, new, unit="U1")[0], 1)
        code, _, _ = run(render_diff.main, [old, new, "--unit", "U1", "--unit", "U2", "--changes", self.changes,
                                            "--head-table", self.table])
        self.assertEqual(code, 0)

    def test_stage_and_route_filters_narrow_an_entry(self):
        extra = "ALLOWED: only in some stages"
        both = {"01-alpha": (ALPHA + extra + "\n", ALPHA + extra + "\n"), "02-alpha-improve": (BETA + extra + "\n", BETA + extra + "\n")}
        base = {"01-alpha": (ALPHA, ALPHA), "02-alpha-improve": (BETA, BETA)}
        for entry, expected in (({"stages": ["alpha"]}, 1), ({"stages": ["*-improve"]}, 1), ({"stages": ["alpha", "*-improve"]}, 0),
                                ({"routes": ["ask-agent"]}, 1), ({"routes": ["inline"]}, 0)):
            with self.subTest(entry=entry):
                shutil_rmtree(self.base / "old"), shutil_rmtree(self.base / "new")
                self.write_changes({"U1": [{"prefix": "ALLOWED: only in", "approval": "decision", **entry}]})
                old, new = self.renders(base, both)
                self.assertEqual(self.diff(old, new)[0], expected)

    def test_a_line_that_only_moved_is_not_a_change_and_is_counted_as_moved(self):
        reordered = "alpha line three\nalpha line one\nalpha line two\n"
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (reordered, reordered)})
        code, out, _ = self.diff(old, new, "--json")
        self.assertEqual(code, 0, out)
        stage = json.loads(out)["stages"][0]
        self.assertEqual(stage["lines"], [])
        self.assertGreaterEqual(stage["moved_lines"]["printed"], 1)

    def test_a_line_added_twice_counts_twice(self):
        extra = "ALLOWED: twice"
        self.write_changes({"U1": [{"prefix": "ALLOWED: twice", "approval": "decision"}]})
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + (extra + "\n") * 2, ALPHA + (extra + "\n") * 2)})
        code, out, _ = self.diff(old, new, "--json")
        self.assertEqual(code, 0, out)
        (added,) = [l for l in json.loads(out)["stages"][0]["lines"] if l["op"] == "+"]
        self.assertEqual((added["count"], added["size"]), (2, 2 * line_size(extra)))

    def test_blank_lines_are_not_listed_but_count_in_the_sizes_and_the_head_table(self):
        self.write_table({"demo": {"inline/83/96": {"alpha": len(ALPHA), "beta": 200}}})
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + "\n\n", ALPHA + "\n\n")})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn(f"printed {len(ALPHA) + 2} passes the table value {len(ALPHA)}", out)
        self.assertNotIn("NOT ALLOWLISTED", out)

    def test_the_head_table_value_is_a_ceiling_a_stage_at_it_passes_and_over_it_fails(self):
        for table, expected in ((len(ALPHA), 0), (len(ALPHA) - 1, 1)):
            with self.subTest(table=table):
                self.write_table({"demo": {"inline/83/96": {"alpha": table, "beta": 200}}})
                shutil_rmtree(self.base / "old"), shutil_rmtree(self.base / "new")
                old, new = self.renders(self.SAME, self.SAME)
                self.assertEqual(self.diff(old, new)[0], expected)

    def test_a_stage_or_a_render_key_the_table_does_not_hold_fails_unless_the_check_is_skipped_by_name(self):
        for table in ({"demo": {"inline/83/96": {"beta": 200}}}, {"demo": {"inline/163/96": {"alpha": 200, "beta": 200}}}, {}):
            with self.subTest(table=table):
                self.write_table(table)
                shutil_rmtree(self.base / "old"), shutil_rmtree(self.base / "new")
                old, new = self.renders(self.SAME, self.SAME)
                code, out, _ = self.diff(old, new)
                self.assertEqual(code, 1)
                self.assertIn("no ", out)
                code, out, _ = self.diff(old, new, "--no-head-table")
                self.assertEqual(code, 0, out)
                self.assertIn("NOT checked (--no-head-table)", out)

    def test_renders_made_with_other_options_are_refused_not_compared(self):
        for override in ({"delegation": "ask-agent"}, {"run_dir_length": 163}, {"cli_path_length": None}, {"case": "other"},
                         {"install_root_length": 40}, {"text_format": 2}):
            with self.subTest(override=override):
                shutil_rmtree(self.base / "old"), shutil_rmtree(self.base / "new")
                old, new = self.renders(self.SAME, self.SAME, **override)
                code, _, err = self.diff(old, new)
                self.assertEqual(code, 2)
                self.assertIn(next(iter(override)), err)

    def test_a_directory_that_is_not_a_render_or_whose_files_disagree_with_its_manifest_is_refused(self):
        old, new = self.renders(self.SAME, self.SAME)
        (new / "01-alpha.printed.txt").write_text(ALPHA + "changed behind the manifest\n")
        code, _, err = self.diff(old, new)
        self.assertEqual((code, "disagree" in err), (2, True))
        code, _, err = self.diff(old, self.base)
        self.assertEqual(code, 2)

    def test_a_malformed_allowlist_is_refused(self):
        old, new = self.renders(self.SAME, self.SAME)
        bad = [{"U1": [{"prefix": "ALLOWED: long enough"}]},
               {"U1": [{"prefix": "ALLOWED: long enough", "offset": ["x"], "approval": "y"}]},
               {"U1": [{"prefix": "short", "approval": "y"}]},
               {"U1": [{"prefix": "ALLOWED: long enough", "approval": "y", "extra": 1}]},
               {"U1": [{"prefix": "ALLOWED: long enough", "approval": "  "}]},
               {"U1": [{"prefix": "ALLOWED: long enough", "offset": []}]},
               {"U1": {"prefix": "ALLOWED: long enough"}}]
        for units in bad:
            with self.subTest(units=units):
                self.write_changes(units)
                self.assertEqual(self.diff(old, new)[0], 2)
        self.write_changes({})
        self.assertEqual(self.diff(old, new, unit="U99")[0], 2)

    def test_a_packet_only_the_new_render_has_must_be_allowlisted_line_by_line_and_a_removed_packet_is_not_a_failure(self):
        old, new = self.renders({"01-alpha": (ALPHA, ALPHA)}, {"01-alpha": (ALPHA, ALPHA), "02-beta": (BETA, BETA)})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 1)
        self.assertIn("## beta: new packet", out)
        shutil_rmtree(self.base / "old"), shutil_rmtree(self.base / "new")
        old, new = self.renders(self.SAME, {"01-alpha": (ALPHA, ALPHA)})
        code, out, _ = self.diff(old, new)
        self.assertEqual(code, 0, out)
        self.assertIn("packet no longer rendered", out)

    def test_the_json_result_carries_the_verdicts(self):
        extra = "PLANTED: json"
        old, new = self.renders(self.SAME, {**self.SAME, "01-alpha": (ALPHA + extra + "\n", ALPHA + extra + "\n")})
        code, out, _ = self.diff(old, new, "--json")
        result = json.loads(out)
        self.assertEqual((code, result["ok"], result["table_key"], result["units"]), (1, False, "inline/83/96", ["U1"]))
        stage = next(s for s in result["stages"] if s["stage"] == "alpha")
        self.assertEqual([(l["op"], l["text"], l["ok"], sorted(l["forms"])) for l in stage["lines"]],
                         [("+", extra, False, ["printed", "whole"])])

    def test_emit_table_prints_the_printed_sizes_and_write_merges_them_without_losing_other_cases(self):
        render = make_render(self.base / "r", {"01-alpha": (ALPHA, ALPHA + "x\n"), "02-beta": (BETA, BETA)})
        code, out, _ = run(render_diff.main, ["--emit-table", render])
        self.assertEqual(json.loads(out), {"demo": {"inline/83/96": {"alpha": len(ALPHA), "beta": len(BETA)}}})
        self.write_table({"_doc": "keep me", "other": {"inline/83/96": {"x": 1}}, "demo": {"ask-agent/83/96": {"alpha": 5}}})
        code, out, _ = run(render_diff.main, ["--emit-table", render, "--head-table", self.table, "--write"])
        merged = json.loads(self.table.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(merged["_doc"], "keep me")
        self.assertEqual(merged["other"], {"inline/83/96": {"x": 1}})
        self.assertEqual(merged["demo"]["ask-agent/83/96"], {"alpha": 5})
        self.assertEqual(merged["demo"]["inline/83/96"], {"alpha": len(ALPHA), "beta": len(BETA)})

    def test_a_missing_unit_or_directory_is_a_usage_error(self):
        old, new = self.renders(self.SAME, self.SAME)
        self.assertEqual(run(render_diff.main, [old, new])[0], 2)
        self.assertEqual(run(render_diff.main, [old])[0], 2)


def shutil_rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)


# --- the shipped files and real renders -------------------------------------------------------------------------------

class ShippedFilesTests(unittest.TestCase):
    def test_the_allowlist_has_one_list_per_unit_so_units_edit_different_lines(self):
        data = json.loads(render_diff.CHANGES.read_text())
        units = [key for key in data if not key.startswith("_")]
        self.assertEqual(units, [f"U{n}" for n in range(1, 36)])
        self.assertTrue(all(isinstance(data[key], list) for key in units))
        self.assertIn("_doc", data)
        for number, line in enumerate(render_diff.CHANGES.read_text().splitlines()[2:-1], 3):
            self.assertRegex(line, r'^  "U\d+": \[.*\],?$', f"line {number}: one key per line so that units do not conflict")
        self.assertEqual(render_diff.load_entries(render_diff.CHANGES, ["U1", "U35"]), [])

    def test_the_head_table_holds_every_stage_of_the_case_at_the_four_keys_the_plan_names(self):
        table = render_diff.load_table(render_diff.HEAD_TABLE)
        self.assertIn("_doc", table)
        keys = {"inline/83/96", "inline/163/96", "ask-agent/83/96", "ask-agent/163/96"}
        self.assertEqual(set(table["node-fix-bug"]), keys)
        stages = None
        for key, values in table["node-fix-bug"].items():
            stages = stages or set(values)
            self.assertEqual(set(values), stages, key)
            self.assertTrue(all(isinstance(v, int) and 1000 < v < 40_000 for v in values.values()), key)
        self.assertIn("step-plan", stages)
        self.assertIn("carry-forward-improve", stages)

    def test_two_real_renders_of_this_tree_compare_clean_and_a_planted_line_in_a_real_head_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / "old", Path(temp) / "new"
            for directory in (old, new):
                render_to(directory, "--run-dir-length", "83", "--cli-path-length", "96")
            code, out, _ = run(render_diff.main, [old, new, "--unit", "U1", "--no-head-table"])
            self.assertEqual(code, 0, out)
            for form in ("printed", "whole"):
                path = new / f"01-step-plan.{form}.txt"
                text = path.read_text()
                path.write_text(text.replace("\n", "\nPLANTED: a real head gets one more line\n", 1))
            manifest = json.loads((new / "manifest.json").read_text())
            for row in manifest["packets"]:
                if row["key"] == "01-step-plan":
                    row["printed"] = len((new / "01-step-plan.printed.txt").read_text())
                    row["whole"] = len((new / "01-step-plan.whole.txt").read_text())
            (new / "manifest.json").write_text(json.dumps(manifest))
            code, out, _ = run(render_diff.main, [old, new, "--unit", "U1", "--no-head-table"])
            self.assertEqual(code, 1)
            self.assertIn("PLANTED: a real head gets one more line", out)


if __name__ == "__main__":
    unittest.main()
