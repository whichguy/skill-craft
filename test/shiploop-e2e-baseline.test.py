#!/usr/bin/env python3
"""No-model checks for what a baseline row says about the run it records (batch 1011, group G3).

Part 1, run identity: the plugin tree digest, the prompt digest with the run's own folder masked, the host build, the span
and the planning window as optional fields of a baseline row and of result.json, null where unknown.  Part 2, one
matching rule behind the live "baseline vs" line.  Part 3, the read-only ``--baseline-report``.

Hosts are fakes (the shared ones of test/shiploop-e2e.test.py); the saved runs of 2026-10-03 to 2026-10-08 are reduced to
compact extracts under test/fixtures/baseline-spread/ and are never read from the machine's own run folder.  Nothing here
touches the machine's process table, ports or ~/.claude.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import metrics  # noqa: E402
import progress  # noqa: E402
import run  # noqa: E402

FIXTURES = ROOT / "test" / "fixtures" / "baseline-spread"


def main_tests():
    """The shared fake hosts and printed-report case of test/shiploop-e2e.test.py, loaded once."""
    name = "shiploop_e2e_main_tests"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "test" / "shiploop-e2e.test.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def script(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class CliVersionTest(unittest.TestCase):
    """Host.cli_version: (the first stdout line of `<cli> --version`, None) or (None, why), and never a Claude probe."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_grok_and_codex_answer_with_the_first_stdout_line_of_version(self):
        grok = script(self.tmp / "grok", "#!/bin/sh\necho 'grok 1.0.50 (c58f321264ba)'\necho 'a second line'\n")
        # codex warns on stderr when CODEX_HOME does not exist; only stdout is the build
        codex = script(self.tmp / "codex", "#!/bin/sh\necho 'WARNING: CODEX_HOME does not exist' >&2\necho 'codex-cli 0.162.0'\n")
        self.assertEqual(hosts.GrokHost(str(grok)).cli_version({}), ("grok 1.0.50 (c58f321264ba)", None))
        self.assertEqual(hosts.CodexHost(str(codex)).cli_version({}), ("codex-cli 0.162.0", None))

    def test_a_probe_that_fails_says_which_way(self):
        failing = script(self.tmp / "fails", "#!/bin/sh\necho 'grok 9'\nexit 1\n")
        silent = script(self.tmp / "silent", "#!/bin/sh\nexit 0\n")
        for binary, why in ((failing, "probe failed: non-zero exit 1"), (silent, "probe failed: silent"),
                            (self.tmp / "missing", "probe failed: not found")):
            with self.subTest(binary=binary.name):
                self.assertEqual(hosts.GrokHost(str(binary)).cli_version({}), (None, why))
                self.assertEqual(hosts.CodexHost(str(binary)).cli_version({}), (None, why))

    def test_a_probe_that_hangs_is_ended_by_the_timeout_and_is_none(self):
        # It would print a version if it were left to finish: only the timeout makes it unknown.
        hangs = script(self.tmp / "hangs", f"#!{sys.executable}\nimport time\ntime.sleep(30)\nprint('grok late')\n")
        started = time.time()
        with mock.patch.object(hosts, "VERSION_TIMEOUT_SECONDS", 1):
            build, why = hosts.GrokHost(str(hangs)).cli_version({})
        self.assertEqual(build, None)
        self.assertTrue(why.startswith("probe failed: hung"), why)
        self.assertLess(time.time() - started, 10)

    def test_the_probe_runs_in_the_launchs_own_environment_with_stdin_closed_and_a_ceiling(self):
        # `grok --version` creates ~/.grok under whatever HOME it runs in: the probe must run in the run's isolated one.
        echo = script(self.tmp / "grok", '#!/bin/sh\necho "grok home=$HOME codex=$CODEX_HOME"\n')
        env = {"HOME": "/isolated/home", "CODEX_HOME": "/isolated/home/.codex"}
        self.assertEqual(hosts.GrokHost(str(echo)).cli_version(env)[0], "grok home=/isolated/home codex=/isolated/home/.codex")
        done = mock.Mock(returncode=0, stdout="grok 1\n", stderr="")
        with mock.patch.object(hosts.subprocess, "run", return_value=done) as called:
            hosts.GrokHost("grok").cli_version(env)
        self.assertEqual(called.call_args.args[0], ["grok", "--version"])
        self.assertEqual(called.call_args.kwargs["env"], env)
        self.assertEqual(called.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(called.call_args.kwargs["timeout"], hosts.VERSION_TIMEOUT_SECONDS)

    def test_claude_is_never_probed_its_build_is_in_its_init_event(self):
        marker = self.tmp / "called"
        binary = script(self.tmp / "claude", f"#!/bin/sh\ntouch {marker}\necho '2.1.295 (Claude Code)'\n")
        build, why = hosts.ClaudeHost(str(binary)).cli_version({})
        self.assertIsNone(build)
        self.assertIn("init event", why)
        self.assertFalse(marker.exists())


class TreeDigestTest(unittest.TestCase):
    """run.tree_digest: the bytes a host loads, not the paths they sit at nor the bytecode they compile to."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def tree(self, name: str, files: dict[str, str]) -> Path:
        root = self.tmp / name
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        return root

    FILES = {"a.txt": "alpha\n", "skills/x/SKILL.md": "---\nversion: 1.0.0\n---\n", "skills/x/scripts/run": "echo hi\n"}

    def test_equal_bytes_at_different_paths_and_times_are_one_build(self):
        first, second = self.tree("one", self.FILES), self.tree("deep/er/two", self.FILES)
        os.utime(second / "a.txt", (1, 1))
        self.assertEqual(run.tree_digest(first), run.tree_digest(second))
        self.assertRegex(run.tree_digest(first), r"^[0-9a-f]{12}$")

    def test_the_digest_is_pinned_so_a_saved_report_stays_reproducible(self):
        self.assertEqual(run.tree_digest(self.tree("pinned", {"a.txt": "x", "d/b.txt": "y"})), "96788439bf74")

    def test_one_changed_byte_or_one_renamed_file_is_another_build(self):
        base = run.tree_digest(self.tree("base", self.FILES))
        self.assertNotEqual(base, run.tree_digest(self.tree("byte", {**self.FILES, "a.txt": "alphb\n"})))
        renamed = {("b.txt" if k == "a.txt" else k): v for k, v in self.FILES.items()}
        self.assertNotEqual(base, run.tree_digest(self.tree("renamed", renamed)))

    def test_bytecode_and_symlinks_do_not_change_the_digest(self):
        root = self.tree("code", self.FILES)
        before = run.tree_digest(root)
        (root / "skills" / "x" / "scripts" / "__pycache__").mkdir()
        (root / "skills" / "x" / "scripts" / "__pycache__" / "m.cpython-314.pyc").write_bytes(b"\0\1\2")
        (root / "skills" / "x" / "scripts" / "__pycache__" / "notes.txt").write_text("not bytecode, still inside __pycache__")
        (root / "stray.pyc").write_bytes(b"\3")
        outside = self.tmp / "outside.txt"
        outside.write_text("not part of the plugin")
        (root / "link").symlink_to(outside)
        self.assertEqual(run.tree_digest(root), before)
        outside.write_text("changed behind the link")
        self.assertEqual(run.tree_digest(root), before)

    def test_a_folder_that_is_not_there_has_no_digest(self):
        self.assertIsNone(run.tree_digest(self.tmp / "nowhere"))

    def unreadable(self, path: Path) -> None:
        path.chmod(0)
        self.addCleanup(path.chmod, 0o755 if path.is_dir() else 0o644)

    def test_an_unreadable_file_gives_no_digest_with_the_reason_and_never_raises(self):
        root = self.tree("locked", self.FILES)
        self.unreadable(root / "skills" / "x" / "scripts" / "run")
        if os.access(root / "skills" / "x" / "scripts" / "run", os.R_OK):
            self.skipTest("the user can read a mode 000 file (root)")
        digest, why = run.tree_digest_checked(root)
        self.assertIsNone(digest)
        self.assertIn("scripts/run", why)
        self.assertIsNone(run.tree_digest(root))

    def test_an_unreadable_folder_is_not_skipped_into_a_digest_of_fewer_files(self):
        # The old walk skipped it silently: the same bytes digested differently depending on one file mode.
        root = self.tree("locked-dir", self.FILES)
        whole = run.tree_digest(root)
        self.unreadable(root / "skills" / "x")
        if os.access(root / "skills" / "x", os.R_OK):
            self.skipTest("the user can list a mode 000 folder (root)")
        digest, why = run.tree_digest_checked(root)
        self.assertIsNone(digest, "a digest of the files that could be read is not the plugin's digest")
        self.assertIn("skills/x", why)
        self.assertNotEqual(whole, digest)

    def test_a_plugin_that_cannot_be_digested_says_why_in_its_versions(self):
        plugin = self.tree("plugin-locked", {".claude-plugin/plugin.json": json.dumps({"version": "1.2.3"}), **self.FILES})
        self.unreadable(plugin / "a.txt")
        if os.access(plugin / "a.txt", os.R_OK):
            self.skipTest("the user can read a mode 000 file (root)")
        versions = run.installed_versions(plugin)
        self.assertIsNone(versions["plugin_sha256"])
        self.assertIn("a.txt", versions["plugin_sha256_unmeasured"])
        self.assertEqual(versions["plugin_version"], "1.2.3")  # the rest of the record is still made
        clean = run.installed_versions(self.tree("plugin-whole", {".claude-plugin/plugin.json": "{}", **self.FILES}))
        self.assertNotIn("plugin_sha256_unmeasured", clean)

    def test_a_missing_folder_has_its_reason_too(self):
        digest, why = run.tree_digest_checked(self.tmp / "nowhere")
        self.assertEqual((digest, why), (None, "the plugin folder does not exist"))

    def test_installed_versions_carries_the_digest_of_the_plugin_it_names(self):
        plugin = self.tree("plugin", {".claude-plugin/plugin.json": json.dumps({"version": "1.2.3"}), **self.FILES})
        versions = run.installed_versions(plugin)
        self.assertEqual(versions["plugin_version"], "1.2.3")
        self.assertEqual(versions["plugin_sha256"], run.tree_digest(plugin))
        self.assertIsNone(run.installed_versions(self.tmp / "missing-plugin")["plugin_sha256"])

    def test_one_version_string_on_two_trees_is_two_builds_and_one_tree_under_two_heads_is_one(self):
        # v1220 and v1230 of 2026-10-06/07 both said plugin 1.22.0; the trees differed (scripts). r1 Battleship (587cd90d) and
        # r1 Checkers (5e209285) were built from different heads and carried byte-identical trees.
        manifest = {".claude-plugin/plugin.json": json.dumps({"version": "1.22.0"})}
        one = self.tree("v1", {**manifest, "skills/shiploop/scripts/nav.py": "a = 1\n"})
        two = self.tree("v2", {**manifest, "skills/shiploop/scripts/nav.py": "a = 2\n"})
        self.assertEqual(run.installed_versions(one)["plugin_version"], run.installed_versions(two)["plugin_version"])
        self.assertNotEqual(run.installed_versions(one)["plugin_sha256"], run.installed_versions(two)["plugin_sha256"])
        copy = self.tree("v1-copy", {**manifest, "skills/shiploop/scripts/nav.py": "a = 1\n"})
        self.assertEqual(run.installed_versions(one)["plugin_sha256"], run.installed_versions(copy)["plugin_sha256"])


class PromptDigestTest(unittest.TestCase):
    """run.masked_prompt_digest: the prompt with the run's own output folder replaced, so one prompt is one hash."""

    def test_a_prompt_naming_the_run_folder_hashes_alike_in_another_folder(self):
        prompt = "Build it. Use --improve-skill {out}/build/plugins/skill-craft/skills/improve/SKILL.md first.\n"
        a = run.masked_prompt_digest(prompt.format(out="/x/run-a"), Path("/x/run-a"))
        b = run.masked_prompt_digest(prompt.format(out="/x/run-b"), Path("/x/run-b"))
        self.assertEqual(a, b)
        self.assertRegex(a, r"^[0-9a-f]{12}$")
        changed = run.masked_prompt_digest(prompt.format(out="/x/run-a").replace("Build", "Make"), Path("/x/run-a"))
        self.assertNotEqual(a, changed)

    def test_a_prompt_with_no_path_is_the_plain_hash_of_its_text_without_the_trailing_newline(self):
        text = "Make a command-line tool that says hello."
        expected = hashlib.sha256(text.encode()).hexdigest()[:12]
        self.assertEqual(run.masked_prompt_digest(text + "\n", Path("/x/run-a")), expected)
        self.assertEqual(run.masked_prompt_digest(text, Path("/x/run-a")), expected)

    def sha(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:12]

    def test_the_requested_spelling_of_the_folder_is_masked_as_well_as_the_resolved_one(self):
        # --output /tmp/x resolves to /private/tmp/x on macOS, and a prompt may name either; both are the run's folder
        resolved, requested = Path("/private/tmp/x"), Path("/tmp/x")
        by_resolved = run.masked_prompt_digest("Read /private/tmp/x/build/SKILL.md", resolved, requested)
        by_requested = run.masked_prompt_digest("Read /tmp/x/build/SKILL.md", resolved, requested)
        self.assertEqual(by_resolved, by_requested)
        self.assertEqual(by_resolved, self.sha("Read <output>/build/SKILL.md"))
        # without the requested spelling the resolved folder's /private-less form is still recognised
        self.assertEqual(run.masked_prompt_digest("Read /tmp/x/build/SKILL.md", resolved), self.sha("Read <output>/build/SKILL.md"))

    def test_the_home_relative_spelling_is_masked(self):
        out = Path.home() / "e2e-runs" / "x"
        got = run.masked_prompt_digest("Read ~/e2e-runs/x/build/SKILL.md", out)
        self.assertEqual(got, self.sha("Read <output>/build/SKILL.md"))

    def test_a_longer_folder_sharing_the_prefix_is_not_corrupted_and_a_sentence_end_is_masked(self):
        out = Path("/a/run1")
        got = run.masked_prompt_digest("Use /a/run1 and not /a/run10/x or /a/run1.bak, then /a/run1.", out)
        self.assertEqual(got, self.sha("Use <output> and not /a/run10/x or /a/run1.bak, then <output>."))
        # the same characters inside a longer path are not the folder
        self.assertEqual(run.masked_prompt_digest("see /other/a/run1/x", out), self.sha("see /other/a/run1/x"))

    def test_the_five_recorded_grok_prompts_are_five_raw_hashes_and_one_masked_hash(self):
        # prompt.txt of the Grok `none` runs of 2026-10-06, 10-07 and 10-08 (r1, r2, r3): each embeds its own folder.
        raw, masked = set(), set()
        for folder in sorted((FIXTURES / "prompts").iterdir()):
            text = (folder / "prompt.txt").read_text()
            recorded = json.loads((folder / "output.json").read_text())["output"]
            self.assertIn(recorded, text)
            raw.add(hashlib.sha256(text.strip().encode()).hexdigest()[:8])
            masked.add(run.masked_prompt_digest(text, Path(recorded)))
        self.assertEqual((len(raw), len(masked)), (5, 1))
        self.assertTrue(masked.pop().startswith("5ea67bf3"))


class SpanAndPlanningTest(unittest.TestCase):
    """metrics.collect reports the run's span from its stream stamps; the planning window yields one scalar."""

    def collect(self, stamps: list[float] | None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "end", "stopReason": "end_turn", "num_turns": 1}) + "\n")
            if stamps is not None:
                (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)))
            return metrics.collect(out, None)

    def test_the_span_is_the_first_and_last_stamp_and_null_without_a_timeline(self):
        self.assertEqual(self.collect([1791481009.116, 1791481500.0, 1791481838.24])["span"],
                         {"started": 1791481009.116, "ended": 1791481838.24})
        self.assertEqual(self.collect(None)["span"], {"started": None, "ended": None})

    def test_the_one_span_reader_counts_finite_stamps_only_and_refuses_a_backwards_stream(self):
        # Integration of batch 1011: G3's metrics.span and G4's environment.span were two readers of one timeline. The one
        # left keeps G4's defences: NaN and infinity are not times, and a stream whose first stamp is after its last has no span.
        nothing = {"started": None, "ended": None}
        self.assertEqual(metrics.span({0: 100.0, 1: float("nan"), 2: 200.0, 3: float("inf")}), {"started": 100.0, "ended": 200.0})
        self.assertEqual(metrics.span({0: 300.0, 1: 200.0, 2: 100.0}), nothing, "a backwards stream is no span")
        self.assertEqual(metrics.span({0: float("nan")}), nothing)
        self.assertEqual(self.collect([1800.0, 1500.0, 1200.0])["span"], nothing)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timeline.jsonl"
            path.write_text('{"line": 0, "t": 1500}\n{"line": 1, "t": NaN}\n{"line": 2, "t": 1600.5}\n{"line": 3, "t": 19')
            self.assertEqual(metrics.span(path), {"started": 1500.0, "ended": 1600.5}, "a path is read; a half-written line skipped")
            folder = Path(tmp) / "a-directory.jsonl"
            folder.mkdir()
            self.assertEqual(metrics.span(folder), nothing, "what cannot be read has no span, and nothing raises")
            self.assertEqual(metrics.span(Path(tmp) / "missing.jsonl"), nothing)

    def test_one_interval_rule_serves_the_report_and_the_environment_record(self):
        rule = metrics.spans_overlap
        self.assertTrue(rule((0.0, 10.0), (5.0, 20.0)))
        self.assertFalse(rule((0.0, 10.0), (10.0, 20.0)), "touching spans do not overlap")
        self.assertTrue(rule((15.0, 15.0), (10.0, 20.0)), "an instant inside the other span does")
        self.assertFalse(rule((10.0, 10.0), (10.0, 20.0)), "an instant at the other's start does not")
        self.assertFalse(rule((None, 10.0), (0.0, 20.0)), "an unknown end is no overlap (the report counts it as unknown)")
        import environment
        self.assertFalse(hasattr(environment, "span"), "one span reader: metrics.span")
        asked = []

        def recording(a, b):
            asked.append((tuple(a), tuple(b)))
            return rule(a, b)

        with mock.patch.object(metrics, "spans_overlap", side_effect=recording):
            self.assertEqual(run.span_overlaps([(0.0, 10.0), (5.0, 20.0)]), [1, 1])
            self.assertTrue(asked, "the report counts overlap through metrics.spans_overlap")
            asked.clear()
            with tempfile.TemporaryDirectory() as tmp:
                for name, (a, b) in (("me", (1000.0, 2000.0)), ("other", (1500.0, 2500.0))):
                    (Path(tmp) / name).mkdir()
                    (Path(tmp) / name / "timeline.jsonl").write_text(
                        json.dumps({"line": 0, "t": a}) + "\n" + json.dumps({"line": 1, "t": b}) + "\n")
                record = environment.overlap(Path(tmp) / "me")
            self.assertEqual(asked, [((1000.0, 2000.0), (1500.0, 2500.0))], "and so does environment.overlap")
            self.assertEqual([(e["folder"], e["overlapped_seconds"]) for e in record["runs"]], [("other", 500.0)])

    def test_planning_seconds_is_the_closed_window_and_never_an_open_one_or_a_zero(self):
        closed = {"window": {"closed": True, "through": "test-spec", "seconds": 336.0}}
        self.assertEqual(metrics.planning_seconds(closed), 336.0)
        open_window = {"window": {"closed": False, "through": "spec", "seconds": 120.0}}
        self.assertIsNone(metrics.planning_seconds(open_window))
        self.assertIsNone(metrics.planning_seconds({"window": {"closed": True, "seconds": None}}))
        for nothing in (None, {}, {"window": None}):
            self.assertIsNone(metrics.planning_seconds(nothing))


class BaselineRowIdentityTest(unittest.TestCase):
    """run.baseline_row stays a pure function of the result dict: the identity fields are copied, null where absent."""

    NEW = ("plugin_sha256", "prompt_sha256", "host_build", "local_head", "started", "ended", "planning_seconds")

    def test_a_result_without_the_new_keys_gives_null_never_zero_or_empty(self):
        row = run.baseline_row({"case": "hello", "metrics": {}}, None, None)
        for key in self.NEW:
            self.assertIn(key, row)
            self.assertIsNone(row[key], key)

    def test_the_fields_are_copied_from_the_result(self):
        result = {"case": "hello", "host": "claude", "prompt_sha256": "5ea67bf3a1c2", "host_build": "2.1.294",
                  "span": {"started": 100.5, "ended": 900.25},
                  "versions": {"source": "checkout", "plugin_sha256": "3a7515d2efd3", "local_head": "587cd90d"},
                  "metrics": {"planning_seconds": 336.0}}
        row = run.baseline_row(result, None, None)
        self.assertEqual({key: row[key] for key in self.NEW},
                         {"plugin_sha256": "3a7515d2efd3", "prompt_sha256": "5ea67bf3a1c2", "host_build": "2.1.294",
                          "local_head": "587cd90d", "started": 100.5, "ended": 900.25, "planning_seconds": 336.0})

    def test_a_null_field_carries_the_reason_the_result_gave_or_says_the_result_predates_it(self):
        row = run.baseline_row({"case": "hello", "host_build": None, "prompt_sha256": "aaaaaaaaaaaa",
                                "identity_unmeasured": {"host_build": "probe failed: hung (still running after 20 s)"},
                                "metrics": {}}, None, None)
        self.assertEqual(row["identity_unmeasured"]["host_build"], "probe failed: hung (still running after 20 s)")
        self.assertIn("predates", row["identity_unmeasured"]["plugin_sha256"])  # no reason given: the result is old
        self.assertNotIn("prompt_sha256", row["identity_unmeasured"])  # known fields have no entry
        full = run.baseline_row({"identity_unmeasured": {}, "prompt_sha256": "a", "host_build": "b",
                                 "span": {"started": 1.0, "ended": 2.0},
                                 "versions": {"plugin_sha256": "c", "local_head": "d"}, "metrics": {"planning_seconds": 3.0}},
                                None, None)
        self.assertEqual(full["identity_unmeasured"], {})  # measured and empty

    def test_local_head_is_read_from_a_marketplace_run_too(self):
        # a checkout run records versions.local_head; a marketplace run records it under versions.released
        row = run.baseline_row({"versions": {"source": "marketplace", "released": {"local_head": "7aff70aa"}}, "metrics": {}},
                               None, None)
        self.assertEqual(row["local_head"], "7aff70aa")

    def test_unreported_sessions_is_still_not_a_baseline_key(self):
        row = run.baseline_row({"metrics": {"unreported_sessions": 3}}, None, None)
        self.assertNotIn("unreported_sessions", row)

    def test_the_row_carries_only_what_eligibility_and_comparison_read_and_no_record_of_the_ending(self):
        # Batch 1011 integration: group G4's blocked detail and outcome class are records in result.json; the row is a basis
        # for comparison (row_reached_done reads termination.engine_status), so they stay out of it, live and regraded.
        live = {"process_status": "exited", "returncode": 0, "engine_status": "blocked", "engine_stage": "system-test",
                "engine_unaccepted_stage": None, "engine_status_reason": "access: no browser",
                "engine_blocked_by": "access", "engine_awaiting_kind": "present", "engine_awaiting_no_default": True}
        regraded = {"process_status": "exited", "engine_status": "active", "regraded": True, "engine_status_at_regrade": "done",
                    "engine_stage_at_regrade": "done", "engine_status_reason_at_regrade": None,
                    "engine_blocked_by_at_regrade": None, "engine_awaiting_kind_at_regrade": None,
                    "engine_awaiting_no_default_at_regrade": None}
        for termination in (live, regraded):
            result = {"case": "hello", "termination": termination, "outcome_class": "BLOCKED", "outcome_basis": "x",
                      "environment": {"observed": True}, "metrics": {}}
            row = run.baseline_row(result, None, None)
            with self.subTest(regraded=termination is regraded):
                self.assertFalse({"outcome_class", "outcome_basis", "environment", "quality"} & set(row))
                self.assertFalse([key for key in row["termination"] if key.startswith(("engine_blocked_by", "engine_awaiting"))],
                                 row["termination"])
                self.assertFalse([key for key in row["termination"] if key.endswith("_at_regrade")
                                  and key != "engine_status_at_regrade"], row["termination"])
                for key in ("process_status", "engine_status"):
                    self.assertEqual(row["termination"][key], termination[key])
                self.assertEqual(result["termination"], termination, "result.json keeps every key")
                self.assertIn("identity_unmeasured", row)
                self.assertTrue(set(self.NEW) <= set(row))
        self.assertEqual(run.baseline_row({"termination": regraded, "metrics": {}}, None, None)["termination"]
                         ["engine_status_at_regrade"], "done")
        self.assertFalse(run.row_reached_done(run.baseline_row({"termination": live, "metrics": {}}, None, None)))


class IdentityThroughMainTest(main_tests().PrintedCase):
    """The identity fields as run.main writes them: result.json, the launch records and the baseline row."""

    def versioned(self, host: str, line: str) -> Path:
        """The shared fake of `host` that also answers `--version`, and logs each probe to <fake>.probes."""
        wrapper = self.tmp / f"{host}-versioned"
        script(wrapper, f'#!/bin/sh\nif [ "$1" = "--version" ]; then echo x >> "{wrapper}.probes"; echo "{line}"; exit 0; fi\n'
                        f'exec "{self.fakes[host]}" "$@"\n')
        return wrapper

    def run_as(self, host: str, mode: str = "done", *extra: str, binary: Path | None = None) -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{mode}-{len(list(self.tmp.glob('out-*')))}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", host, f"--{host}-bin", str(binary or self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_grok_and_codex_builds_come_from_version_at_launch_and_sit_on_the_launch_record_and_the_row(self):
        for host, line in (("grok", "grok 1.0.50 (c58f321264ba)"), ("codex", "codex-cli 0.162.0")):
            with self.subTest(host=host):
                code, result, _ = self.run_as(host, binary=self.versioned(host, line))
                self.assertEqual(code, 0, result)
                out = Path(result["output"])
                self.assertEqual(result["host_build"], line)
                self.assertEqual(json.loads((out / "invocation.json").read_text())["host_build"], line)
                self.assertEqual(self.last_row()["host_build"], line)

    def test_claude_build_is_its_init_event_and_its_launch_record_probes_nothing(self):
        wrapper = self.versioned("claude", "2.1.295 (Claude Code)")
        code, result, _ = self.run_as("claude", binary=wrapper)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["host_build"], "0.0.1-fake")  # the fake's init event, not a --version line
        self.assertEqual(self.last_row()["host_build"], "0.0.1-fake")
        launch = json.loads((Path(result["output"]) / "invocation.json").read_text())
        self.assertIsNone(launch["host_build"])
        self.assertEqual(launch["identity_unmeasured"]["host_build"], "Claude: read from the init event after the run")
        self.assertNotIn("host_build", result["identity_unmeasured"])  # the result has it, from the init event
        self.assertFalse(Path(f"{wrapper}.probes").exists(), "Claude was probed")

    def test_a_build_that_cannot_be_read_is_null_with_its_reason_and_the_run_still_finishes(self):
        for host in ("grok", "codex"):
            with self.subTest(host=host):
                code, result, _ = self.run_as(host)  # the shared fakes exit non-zero on --version
                self.assertEqual(code, 0, result)
                self.assertIn("host_build", result)
                self.assertIsNone(result["host_build"])
                self.assertIsNone(self.last_row()["host_build"])
                reason = result["identity_unmeasured"]["host_build"]
                self.assertTrue(reason.startswith("probe failed: non-zero exit"), reason)
                self.assertEqual(self.last_row()["identity_unmeasured"]["host_build"], reason)
                launch = json.loads((Path(result["output"]) / "invocation.json").read_text())
                self.assertEqual((launch["host_build"], launch["identity_unmeasured"]["host_build"]), (None, reason))

    def test_the_probe_runs_in_the_isolated_home_of_the_launch_not_the_users(self):
        # `grok --version` creates ~/.grok: a probe under the user's real HOME would write into their profile
        wrapper = self.versioned("grok", "grok home=$HOME")
        code, result, _ = self.run_as("grok", binary=wrapper)
        self.assertEqual(result["host_build"], f"grok home={Path(result['output']) / 'home'}")

    def test_the_version_is_probed_once_per_launch_not_once_per_session_or_at_the_end(self):
        wrapper = self.versioned("grok", "grok 1.0.50 (c58f321264ba)")
        code, result, _ = self.run_as("grok", "resume", "--max-resumes", "2", binary=wrapper)
        self.assertEqual(code, 0, result)
        self.assertGreater(len(result["process"]["sessions"]), 1)
        self.assertEqual(len(Path(f"{wrapper}.probes").read_text().split()), 1)

    CATALOG = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
               "shiploop_version": None, "unreleased": [], "ci": "success"}

    def resume_on(self, host: str, out: Path, line: str, *extra: str) -> dict:
        os.environ["FAKE_MODE"] = "done"
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "released_versions", return_value=self.CATALOG):
            run.main(["--host", host, f"--{host}-bin", str(self.versioned(host, line)), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--max-resumes", "0", *extra])
        return json.loads((out / "result.json").read_text())

    def test_a_resume_launch_records_its_own_build_and_the_result_keeps_the_first_launchs(self):
        code, stopped, _ = self.run_as("grok", "stuck", "--max-resumes", "0", binary=self.versioned("grok", "grok 1.0.50 (aaa)"))
        out = Path(stopped["output"])
        result = self.resume_on("grok", out, "grok 1.0.51 (bbb)")
        records = sorted(out.glob("invocation-resume-grok-*.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text())["host_build"], "grok 1.0.51 (bbb)")
        self.assertEqual(json.loads((out / "invocation.json").read_text())["host_build"], "grok 1.0.50 (aaa)")
        self.assertEqual(result["host_build"], "grok 1.0.50 (aaa)")  # one meaning: the first launch's

    def test_a_run_resumed_whose_first_launch_predates_the_field_does_not_get_todays_build(self):
        code, stopped, _ = self.run_as("grok", "stuck", "--max-resumes", "0")
        out = Path(stopped["output"])
        first = json.loads((out / "invocation.json").read_text())
        first.pop("host_build", None)
        first.pop("identity_unmeasured", None)
        (out / "invocation.json").write_text(json.dumps(first))  # a launch made before the probe existed
        result = self.resume_on("grok", out, "grok 1.0.51 (bbb)")
        self.assertIsNone(result["host_build"])
        self.assertEqual(result["identity_unmeasured"]["host_build"], "first launch predates the field")
        record = json.loads(next(out.glob("invocation-resume-grok-*.json")).read_text())
        self.assertEqual(record["host_build"], "grok 1.0.51 (bbb)")  # the resume launch itself was probed

    def test_the_environment_record_reads_each_launchs_build_and_reason_as_its_launch_record_wrote_them(self):
        # Batch 1011 integration: one host_build contract. G3 writes host_build and identity_unmeasured.host_build on each launch
        # record; G4's environment.environments[] reads each launch through runrecord.host_build and carries the same two keys,
        # with G3's reasons (it derived reasons of its own before).
        import runrecord
        code, stopped, _ = self.run_as("grok", "stuck", "--max-resumes", "0", binary=self.versioned("grok", "grok 1.0.50 (aaa)"))
        out = Path(stopped["output"])
        result = self.resume_on("grok", out, "")  # the resume's probe prints nothing
        records = [record for _name, record in runrecord.launches(out)]
        entries = result["environment"]["environments"]
        self.assertEqual([(e["host_build"], e["identity_unmeasured"]) for e in entries],
                         [("grok 1.0.50 (aaa)", {}), (None, {"host_build": "probe failed: silent"})])
        self.assertEqual([(r["host_build"], r["identity_unmeasured"].get("host_build")) for r in records],
                         [("grok 1.0.50 (aaa)", None), (None, "probe failed: silent")])
        self.assertFalse(any("host_build_reason" in e for e in entries), "one set of key names")
        code, claude, _ = self.run_as("claude")
        entry = claude["environment"]["environments"][0]
        self.assertEqual((entry["host_build"], entry["identity_unmeasured"]),
                         (None, {"host_build": "Claude: read from the init event after the run"}))
        self.assertEqual(runrecord.host_build({"host": "grok"}), (None, "launch predates the field"))
        self.assertEqual(runrecord.host_build({"host": "claude"}), (None, "Claude: read from the init event after the run"))
        self.assertEqual(runrecord.host_build({"host": "grok", "host_build": None}), (None, "no reason recorded"))

    def test_a_run_resumed_on_another_host_names_no_single_build(self):
        code, stopped, _ = self.run_as("grok", "stuck", "--max-resumes", "0", binary=self.versioned("grok", "grok 1.0.50 (aaa)"))
        out = Path(stopped["output"])
        # A finish on another host is refused unless it is said to be deliberate (group G4's resume rule).
        result = self.resume_on("codex", out, "codex-cli 0.162.0", "--allow-host-change")
        self.assertIsNone(result["host_build"])
        self.assertEqual(result["identity_unmeasured"]["host_build"], "resumed on another host: see the launch records")
        self.assertEqual(json.loads(next(out.glob("invocation-resume-codex-*.json")).read_text())["host_build"], "codex-cli 0.162.0")

    def test_a_regrade_restates_the_recorded_build_and_never_asks_the_cli(self):
        code, first, _ = self.run_as("grok", binary=self.versioned("grok", "grok 1.0.50 (c58f321264ba)"))
        out = Path(first["output"])

        def regrade() -> dict:
            with contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.object(hosts.GrokHost, "cli_version", side_effect=AssertionError("a regrade probed the CLI")):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
            return json.loads((out / "result.json").read_text())

        self.assertEqual(regrade()["host_build"], "grok 1.0.50 (c58f321264ba)")
        # a run recorded before the field existed: today's build is never stamped on it
        for name in ("result.json", "invocation.json"):
            record = json.loads((out / name).read_text())
            record.pop("host_build", None)
            (out / name).write_text(json.dumps(record))
        old_run = regrade()
        self.assertIsNone(old_run["host_build"])
        self.assertEqual(old_run["identity_unmeasured"]["host_build"], "launch predates the field")

    def test_the_plugin_tree_digest_is_taken_at_launch_and_a_regrade_keeps_it(self):
        code, result, _ = self.run_as("claude")
        digest = run.tree_digest(self.plugin)
        self.assertEqual(result["versions"]["plugin_sha256"], digest)
        self.assertEqual(self.last_row()["plugin_sha256"], digest)
        self.assertEqual(json.loads((Path(result["output"]) / "invocation.json").read_text())["versions"]["plugin_sha256"], digest)
        (self.plugin / "skills" / "shiploop" / "scripts" / "shiploop").write_text("changed after the run\n")
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--resume-run", result["output"], "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        regraded = json.loads((Path(result["output"]) / "result.json").read_text())
        self.assertEqual(regraded["versions"]["plugin_sha256"], digest, "a regrade restates what the run recorded")

    def test_one_prompt_in_two_output_folders_is_one_prompt_hash(self):
        _, one, _ = self.run_as("claude", "done", "--prompt", "make hello", "--check", "true")
        _, two, _ = self.run_as("claude", "done", "--prompt", "make hello", "--check", "true")
        self.assertNotEqual(one["output"], two["output"])
        self.assertEqual(one["prompt_sha256"], two["prompt_sha256"])
        self.assertEqual(one["prompt_sha256"], run.masked_prompt_digest("make hello", Path(one["output"])))
        _, other, _ = self.run_as("claude", "done", "--prompt", "make goodbye", "--check", "true")
        self.assertNotEqual(one["prompt_sha256"], other["prompt_sha256"])
        self.assertEqual(self.last_row()["prompt_sha256"], other["prompt_sha256"])

    def test_a_prompt_naming_its_own_output_folder_is_masked_through_main_in_either_spelling(self):
        # The harness resolves --output; a prompt written by a person or a script names the folder as it asked for it.
        real = self.tmp / "real"
        real.mkdir()
        link = self.tmp / "link"
        link.symlink_to(real)
        digests = []
        for name, spelled in (("one", link / "one"), ("two", real / "two")):
            prompt = f"Make hello. Read {spelled}/build/SKILL.md first."
            os.environ["FAKE_MODE"] = "done"
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(["--host", "claude", "--claude-bin", str(self.fakes["claude"]), "--output", str(spelled),
                          "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--prompt", prompt,
                          "--check", "true"])
            result = json.loads((real / name / "result.json").read_text())
            digests.append(result["prompt_sha256"])
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(digests[0], hashlib.sha256(b"Make hello. Read <output>/build/SKILL.md first.").hexdigest()[:12])

    def test_the_span_is_the_streams_first_and_last_stamp_and_an_unclosed_planning_window_is_null(self):
        code, result, _ = self.run_as("claude")
        stamps = [json.loads(line)["t"] for line in (Path(result["output"]) / "timeline.jsonl").read_text().splitlines()]
        self.assertEqual(result["span"], {"started": min(stamps), "ended": max(stamps)})
        row = self.last_row()
        self.assertEqual((row["started"], row["ended"]), (min(stamps), max(stamps)))
        self.assertIn("planning_seconds", result["metrics"])
        self.assertIsNone(result["metrics"]["planning_seconds"])  # no accepted test-spec: unknown, never 0
        self.assertIsNone(row["planning_seconds"])
        self.assertIn("no stage has been accepted", result["identity_unmeasured"]["planning_seconds"])
        self.assertEqual(row["identity_unmeasured"], result["identity_unmeasured"])

    def test_a_closed_planning_window_reaches_the_result_and_the_row_through_main(self):
        real = metrics.collect

        def with_a_window(out, run_dir=None, **kw):  # kw: the ToolLog run._main hands in for the fidelity block (G1)
            found = real(out, run_dir, **kw)
            found["planning"]["window"].update(closed=True, through="test-spec", seconds=336.0, host_seconds=340.0,
                                               before_engine_seconds=4.0)
            found["planning"]["unmeasured"] = {}
            return found

        with mock.patch.object(metrics, "collect", side_effect=with_a_window):
            code, result, _ = self.run_as("claude")
        self.assertEqual(result["metrics"]["planning_seconds"], 336.0)
        self.assertEqual(self.last_row()["planning_seconds"], 336.0)
        self.assertNotIn("planning_seconds", result["identity_unmeasured"])

    def test_local_head_is_in_the_row_for_a_checkout_run(self):
        code, result, _ = self.run_as("claude")
        self.assertRegex(result["versions"]["local_head"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.last_row()["local_head"], result["versions"]["local_head"])


DRIVER = {"case": "battleship", "source": "checkout", "host": "claude", "model": "m", "effort": None,
          "planning_review": "stage"}


def row(**fields) -> dict:
    return {**DRIVER, "date": "2026-10-08T10:00:00+0000", "shiploop_version": "0.56.0", "turns": 100,
            "verdicts": {"shiploop": True}, "termination": {"engine_status": "done"}, **fields}


def _source(function) -> str:
    import inspect
    return inspect.getsource(function)


class MatchingRowsTest(unittest.TestCase):
    """One matching rule (run.matching_rows) behind scan_baseline and previous_row; a row that did not reach done is a
    record and not a basis, and the prompt key applies only where both sides carry one (always for case 'custom')."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "baselines.jsonl"

    def write(self, *rows: dict) -> Path:
        self.path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return self.path

    def match(self, *rows: dict, case="battleship", prompt=None, mode="stage"):
        self.write(*rows)
        return run.matching_rows(self.path, case, "checkout", "claude", "m", None, mode, prompt)

    def test_a_row_that_did_not_reach_done_is_never_the_row_a_run_is_compared_with(self):
        done = row(turns=301)
        blocked = row(turns=503, verdicts={"shiploop": False}, termination={"engine_status": "blocked"})
        self.write(done, blocked)
        found, seen = run.scan_baseline(self.path, "battleship", "checkout", "claude", "m", None, "stage")
        self.assertEqual((found["turns"], seen), (301, 2))  # the blocked row is past the done one and is still skipped
        self.assertEqual(run.previous_row(self.path, "battleship", "checkout", "claude", "m", None)["turns"], 301)
        rows, seen, skipped = self.match(done, blocked)
        self.assertEqual(([r["turns"] for r in rows], seen, dict(skipped)), ([301], 2, {"did not reach done": 1}))
        self.assertEqual(run.scan_baseline(self.write(blocked), "battleship", "checkout", "claude", "m", None, "stage"),
                         (None, 1))

    def test_either_signal_that_the_run_did_not_finish_excludes_a_row_and_a_row_with_neither_is_kept(self):
        self.assertEqual(len(self.match(row(verdicts={"shiploop": False}, termination=None))[0]), 0)
        self.assertEqual(len(self.match(row(verdicts=None, termination={"engine_status": "blocked"}))[0]), 0)
        for status in ("halted", "paused", "unknown", "active"):
            self.assertEqual(len(self.match(row(termination={"engine_status": status}))[0]), 0, status)
        # unknown is not refused: a row written before verdicts and termination existed, or by a test, stays a baseline
        bare = {k: v for k, v in row().items() if k not in ("verdicts", "termination")}
        self.assertEqual(len(self.match(bare)[0]), 1)
        # a finished run whose product failed a check is a complete run: its cost is a complete run's cost
        self.assertEqual(len(self.match(row(**{"pass": False}))[0]), 1)

    def test_a_named_case_compares_rows_with_no_prompt_hash_and_splits_on_two_different_hashes(self):
        old, same, other = row(turns=1), row(turns=2, prompt_sha256="aaaaaaaaaaaa"), row(turns=3, prompt_sha256="bbbbbbbbbbbb")
        kept = [r["turns"] for r in self.match(old, same, other, prompt="aaaaaaaaaaaa")[0]]
        self.assertEqual(kept, [1, 2])  # the old row has no hash: the existing 'baseline vs' line survives for it
        self.assertEqual([r["turns"] for r in self.match(old, same, other, prompt=None)[0]], [1, 2, 3])
        rows, _, skipped = self.match(old, same, other, prompt="aaaaaaaaaaaa")
        self.assertEqual(dict(skipped), {"another prompt": 1})

    def test_the_custom_case_compares_only_rows_that_carry_the_same_prompt_hash(self):
        custom = {"case": "custom"}
        old = row(**custom, turns=1)  # a committed Grok 'none' row, written before the field existed
        same = row(**custom, turns=2, prompt_sha256="5ea67bf3a1c2")
        other = row(**custom, turns=3, prompt_sha256="0123456789ab")
        rows, seen, skipped = self.match(old, same, other, case="custom", prompt="5ea67bf3a1c2")
        self.assertEqual(([r["turns"] for r in rows], seen), ([2], 3))
        self.assertEqual(dict(skipped), {"another prompt": 2})
        # a caller that cannot name its prompt matches nothing for 'custom': two unknown prompts are not known to be one
        self.assertEqual(self.match(old, same, case="custom", prompt=None)[0], [])

    def test_the_other_rules_are_unchanged_the_driver_the_mode_and_the_source(self):
        rows, seen, skipped = self.match(row(turns=1), row(turns=2, host="grok"), row(turns=3, planning_review="none"),
                                         row(turns=4, source="marketplace"), row(turns=5, case="checkers"))
        self.assertEqual(([r["turns"] for r in rows], seen), ([1], 3))
        self.assertEqual(dict(skipped), {"another host, model or effort": 1, "another planning_review mode": 1})

    def test_a_missing_file_has_no_rows(self):
        self.assertEqual(run.matching_rows(self.path.with_name("nowhere.jsonl"), "x", "checkout")[:2], ([], 0))

    def test_scan_baseline_and_previous_row_have_no_filter_of_their_own(self):
        source = _source(run.scan_baseline) + _source(run.previous_row)
        self.assertIn("matching_rows(", source)
        self.assertNotIn("json.loads", source)  # no second reading of the file, so no second key


class ComparisonThroughMainTest(main_tests().PrintedCase):
    """The live 'baseline vs' line as run.main prints it: which row it draws on, the facts under it, and what a run that
    did not reach done prints."""

    def finish_blocked(self) -> Path:
        """The shared fake of the host, then a ShipLoop state that blocked itself: the host exits 0, the engine is blocked."""
        wrapper = self.tmp / "grok-blocks"
        script(wrapper, f"""#!/bin/sh
"{self.fakes['grok']}" "$@"
rc=$?
{sys.executable} - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
store.write_record(Path(".shiploop/state.md"), {{"status": "blocked", "stage": "system-test", "planning_review": "stage",
                                                "status_reason": "waiting for a person"}})
Path(".shiploop/report.html").unlink()
PY
exit $rc
""")
        return wrapper

    def once(self, mode="done", *extra, binary: Path | None = None, host="grok") -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{len(list(self.tmp.glob('out-*')))}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", host, f"--{host}-bin", str(binary or self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def edit_rows(self, **changes_by_index: dict) -> None:
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        for index, changes in changes_by_index.items():
            rows[int(index.removeprefix("r"))].update(changes)
        self.baselines.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def test_a_run_that_did_not_reach_done_still_writes_its_row_and_compares_with_nothing(self):
        self.once()
        self.edit_rows(r0={"turns": 301})
        code, result, printed = self.once(binary=self.finish_blocked())
        self.assertEqual(result["termination"]["engine_status"], "blocked", result["termination"])
        self.assertIn("  baseline  nothing compared: this run did not reach done (engine blocked)", printed)
        self.assertNotIn("baseline  vs", printed)
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual(len(rows), 2)  # a record, not a basis: the row is written
        self.assertEqual((rows[1]["verdicts"]["shiploop"], rows[1]["termination"]["engine_status"]), (False, "blocked"))

    def test_a_blocked_row_is_skipped_and_the_run_is_compared_with_the_done_row_before_it(self):
        self.once()
        self.once(binary=self.finish_blocked())
        self.edit_rows(r0={"turns": 301}, r1={"turns": 503})
        code, result, printed = self.once()
        self.assertIn("turns 301 (lower bound) -> ", printed)  # a Grok figure: marked
        self.assertNotIn("503", printed.split("  baseline")[1].split("\n")[0])

    def test_with_only_a_blocked_row_before_it_nothing_is_compared_and_the_report_says_why(self):
        self.once(binary=self.finish_blocked())
        code, result, printed = self.once()
        self.assertEqual(code, 0, result)
        self.assertIn("  baseline  nothing compared: 1 earlier row(s) for hello, none comparable with this run "
                      "(1 did not reach done)", printed)

    def test_two_custom_prompts_are_two_cells_and_one_prompt_in_two_folders_is_one_cell(self):
        args = ("--prompt", "make hello", "--check", "true")
        self.once("done", *args, host="claude")
        _, one_again, printed = self.once("done", *args, host="claude")
        self.assertIn("baseline  vs", printed)  # the same prompt in another folder is the same cell
        _, other, printed = self.once("done", "--prompt", "make goodbye", "--check", "true", host="claude")
        self.assertIn("  baseline  nothing compared: 2 earlier row(s) for custom, none comparable with this run "
                      "(2 another prompt)", printed)
        # a row written before the field existed compares with no custom run
        self.edit_rows(r0={"prompt_sha256": None}, r1={"prompt_sha256": None}, r2={"prompt_sha256": None})
        _, _, printed = self.once("done", *args, host="claude")
        self.assertIn("none comparable with this run (3 another prompt)", printed)

    def test_a_named_case_keeps_comparing_with_a_row_that_has_no_prompt_hash(self):
        self.once()
        self.edit_rows(r0={"prompt_sha256": None})
        code, result, printed = self.once()
        self.assertIn("baseline  vs", printed)
        self.edit_rows(r0={"prompt_sha256": "0123456789ab"}, r1={"prompt_sha256": "0123456789ab"})
        _, _, printed = self.once()  # both carry a hash and it differs from this run's: another cell
        self.assertIn("(2 another prompt)", printed)

    def line(self, printed: str, prefix: str) -> str:
        return next(ln for ln in printed.splitlines() if ln.startswith(prefix))

    def test_a_grok_comparison_marks_both_sides_as_lower_bounds(self):
        # the line that printed r1 Grok's '503 -> 301': both figures cover only the sessions that reported
        self.once()
        _, _, printed = self.once()
        line = self.line(printed, "  baseline  vs")
        self.assertIn("turns 4 (lower bound) -> 4 (lower bound), cost $0.01 (lower bound) -> $0.01 (lower bound)", line)

    def test_an_old_grok_row_without_the_marker_is_still_marked_by_its_host(self):
        self.once()
        self.edit_rows(r0={"unmeasured": []})  # a row from before 073fd4dd lists no unreported_sessions
        _, _, printed = self.once()
        self.assertIn("turns 4 (lower bound) -> 4 (lower bound)", self.line(printed, "  baseline  vs"))

    def test_a_claude_comparison_that_ended_whole_marks_nothing(self):
        self.once("done", host="claude")
        _, _, printed = self.once("done", host="claude")
        self.assertNotIn("lower bound", self.line(printed, "  baseline  vs"))

    def test_a_row_that_lists_the_session_count_unmeasured_is_marked_whatever_its_host(self):
        self.once("done", host="claude")
        self.edit_rows(r0={"unmeasured": ["unreported_sessions"]})
        _, _, printed = self.once("done", host="claude")
        line = self.line(printed, "  baseline  vs")
        self.assertRegex(line, r"turns \d+ \(lower bound\) -> \d+, cost \$[\d.]+ \(lower bound\) -> \$[\d.]+,")

    def test_the_facts_under_the_line_name_the_tree_the_host_build_and_the_cell(self):
        self.once("done", host="claude")
        _, _, printed = self.once("done", host="claude")
        line = next(ln for ln in printed.splitlines() if ln.startswith("            sample: "))
        digest = run.tree_digest(self.plugin)
        self.assertIn(f"plugin tree same ({digest}); Claude Code build 0.0.1-fake (same); "
                      "1 earlier row(s) in this cell on 1 recorded build(s)", line)
        self.edit_rows(r0={"plugin_sha256": None}, r1={"plugin_sha256": "aaaaaaaaaaaa", "host_build": "2.1.292"})
        _, _, printed = self.once("done", host="claude")
        line = next(ln for ln in printed.splitlines() if ln.startswith("            sample: "))
        self.assertIn(f"plugin tree different (aaaaaaaaaaaa -> {digest}); Claude Code build 2.1.292 -> 0.0.1-fake; "
                      "2 earlier row(s) in this cell on 1 recorded build(s), 1 with no recorded tree", line)

    def test_a_fact_one_side_does_not_record_is_unknown_and_makes_no_claim(self):
        self.once()
        self.edit_rows(r0={"plugin_sha256": None, "host_build": None})
        _, _, printed = self.once()
        line = next(ln for ln in printed.splitlines() if ln.startswith("            sample: "))
        self.assertIn("plugin tree unknown (the earlier row records none)", line)
        self.assertIn("grok build unknown (this run records none)", line)  # the shared fake's --version fails: this run has none
        for word in ("within", "above", "below", "regression", "faster", "slower"):
            self.assertNotIn(word, line)


class GrokSessionStartTest(unittest.TestCase):
    """A Grok event stream carries no session-start marker, so a session that never reported cannot be counted from it.

    ``available_commands`` is Grok's announcement of its tool and command list and it is repeated inside one session:
    r1-battleship-grok-none (2026-10-08) holds 314 of them for 2 `end` events (301 model calls), 2 at the head of the first
    launch and 8 at the head of the resume. Counting each as a start printed "lower bound: 312 session(s) never
    reported" for a cost that equals the two end events' totals. The count is unknown and the lower-bound marking stays,
    because a killed Grok session cannot be told from a long one by the stream alone; the harness's own launch rows can.
    What the stream does prove: model calls after the last `end` (or with no `end`) belong to a session that never
    reported, so at least one did. A stream is Grok's by its host (a launch record) or its `usage` events, not by a field
    of one event."""

    ACCEPTED = [("A1", "intake", "done", 105.0)]

    def stream(self) -> list[dict]:
        return [json.loads(line) for line in (FIXTURES / "grok-r1-session-shape.jsonl").read_text().splitlines()]

    def collect(self, stream: list[dict], host: str | None = None) -> dict:
        if host is None:
            return main_tests().collect_stream(stream, self.ACCEPTED)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = main_tests().write_stream_run(out, stream, self.ACCEPTED)
            (out / "invocation.json").write_text(json.dumps({"case": "custom", "host": host}))
            return metrics.collect(out, run_dir)

    def test_the_recorded_shape_has_many_announcements_for_two_ended_sessions(self):
        kinds = [event["type"] for event in self.stream()]
        self.assertEqual((kinds.count("available_commands"), kinds.count("usage"), kinds.count("end")), (314, 301, 2))

    def test_the_announcements_are_not_counted_as_starts_the_count_is_unknown_with_its_reason(self):
        m = self.collect(self.stream())
        self.assertIsNone(m["unreported_sessions"], "314 announcements are not 314 sessions")
        self.assertIn("available_commands", m["unmeasured"]["unreported_sessions"])
        self.assertEqual(len(m["sessions"]), 2)
        self.assertAlmostEqual(m["cost_usd"], 8.7455, places=4)  # the two end events' totals, as the row recorded

    def test_the_lower_bound_marking_stays_and_names_no_invented_count(self):
        m = self.collect(self.stream())
        self.assertTrue(metrics.lower_bound(m))
        self.assertEqual(metrics.cost_text(m), "$8.7455 (lower bound: this host's events do not show whether a session "
                                               "never reported)")
        self.assertTrue(metrics.turns_text(m).endswith("(lower bound)"))
        self.assertNotIn("312", metrics.summary_lines(m)[0])
        self.assertIn("(lower bound", metrics.summary_lines(m)[0])

    def test_a_grok_stream_that_names_its_session_is_no_more_countable(self):
        # The old reading told Grok's announcements from Codex's by a `sessionId` field; a Grok build that adds one must
        # not bring back "312 session(s) never reported".
        named = [dict(event, sessionId="s1") if event["type"] == "available_commands" else event for event in self.stream()]
        m = self.collect(named)
        self.assertIsNone(m["unreported_sessions"])
        self.assertTrue(metrics.lower_bound(m))

    def test_model_calls_after_the_last_end_prove_a_session_never_reported(self):
        whole = self.collect(self.stream())
        self.assertEqual(whole["unreported_sessions_at_least"], 0)
        events = self.stream()
        last_end = max(i for i, event in enumerate(events) if event["type"] == "end")
        cut = events[:last_end]  # the resume's own `end` never came: it was killed
        m = self.collect(cut)
        self.assertEqual(m["unreported_sessions_at_least"], 1)
        self.assertIsNone(m["unreported_sessions"])
        self.assertIn("at least 1 session(s) never reported", metrics.cost_text(m))
        self.assertTrue(metrics.turns_text(m).endswith("(lower bound)"))
        none_ended = [event for event in events if event["type"] != "end"]
        self.assertEqual(self.collect(none_ended)["unreported_sessions_at_least"], 1)  # r2, r3 and v1210: usage, no `end`

    def test_the_host_of_the_run_decides_when_the_stream_has_no_model_call_yet(self):
        # a Grok launch killed before its first model call: announcements only, but the launch record names Grok
        announcements = [{"type": "available_commands", "commands": [], "tools": []}] * 5
        self.assertIsNone(self.collect(announcements, host="grok")["unreported_sessions"])
        # with no record and no model call there is no telling hosts apart: a bare announcement opens a session
        self.assertEqual(self.collect(announcements[:1])["unreported_sessions"], 1)

    def test_a_stream_that_mixes_grok_and_claude_events_is_unknown_too(self):
        # r2-battleship-grok-none: Grok started it and was killed with its harness; Claude finished it.
        grok = self.stream()[:40]  # a launch that never ended, with model calls
        claude = [{"type": "system", "subtype": "init", "claude_code_version": "2.1.294"},
                  {"type": "result", "subtype": "success", "num_turns": 5, "total_cost_usd": 1.0}]
        m = self.collect(grok + claude)
        self.assertIsNone(m["unreported_sessions"])
        self.assertEqual(m["unreported_sessions_at_least"], 1)
        self.assertTrue(metrics.lower_bound(m))

    def test_a_host_that_marks_each_session_start_keeps_an_exact_count(self):
        init = {"type": "system", "subtype": "init", "model": "m"}
        result = {"type": "result", "subtype": "success", "num_turns": 5, "total_cost_usd": 1.85}
        codex_open = {"type": "available_commands", "commands": [], "sessionId": "t1"}  # the Codex translator names its session
        end = {"type": "end", "stopReason": "end_turn", "num_turns": 5, "total_cost_usd": None}
        self.assertEqual(self.collect([init, init, result])["unreported_sessions"], 1)
        self.assertEqual(self.collect([codex_open, codex_open, end])["unreported_sessions"], 1)
        self.assertEqual(self.collect([init, result])["unreported_sessions"], 0)
        self.assertFalse(metrics.lower_bound(self.collect([init, result])))
        self.assertIsNone(self.collect([init, result])["unreported_sessions_at_least"])

    def test_the_lower_bound_predicate_reads_a_count_a_reason_or_nothing(self):
        for found, want in (({"unreported_sessions": 0}, False), ({"unreported_sessions": 3}, True),
                            ({"unreported_sessions": None, "unmeasured": {"unreported_sessions": "why"}}, True),
                            ({"unreported_sessions": None}, None), ({}, None)):
            with self.subTest(found=found):
                self.assertIs(metrics.lower_bound(found), want)

    def test_the_count_is_still_not_a_baseline_key_and_a_grok_row_names_it_unmeasured(self):
        m = self.collect(self.stream())
        result = {"case": "battleship", "host": "grok", "metrics": {"unmeasured": m["unmeasured"], "turns": m["turns"],
                                                                      "cost_usd": m["cost_usd"],
                                                                      "unreported_sessions": m["unreported_sessions"]}}
        row = run.baseline_row(result, None, None)
        self.assertNotIn("unreported_sessions", row)
        self.assertIn("unreported_sessions", row["unmeasured"])


class GrokSessionStartThroughMainTest(main_tests().PrintedCase):
    """What run.main records and prints for a Grok run now that the session count is unknown, not invented."""

    def test_a_grok_run_prints_the_marking_without_a_count_and_the_row_names_the_count_unmeasured(self):
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertIsNone(result["metrics"]["unreported_sessions"])
        note = "(lower bound: this host's events do not show whether a session never reported)"
        process = next(line for line in printed.splitlines() if line.startswith("  process"))
        self.assertIn(f"cost=$0.01 {note}", process)
        self.assertIn(f"cost $0.01 {note}", next(line for line in printed.splitlines() if line.startswith("  metrics   turns")))
        row = self.last_row()
        self.assertNotIn("unreported_sessions", row)
        self.assertIn("unreported_sessions", row["unmeasured"])

    def test_a_claude_run_that_ended_whole_prints_no_marking(self):
        code, result, printed = self.invoke_printed("claude", "done")
        self.assertEqual(result["metrics"]["unreported_sessions"], 0)
        self.assertNotIn("lower bound", printed)


class BaselineReportCase(unittest.TestCase):
    """Runs `run.py --baseline-report` over the compact extracts of the saved 2026-10-05 to 2026-10-08 runs."""

    RUNS = FIXTURES / "runs"
    ROWS = FIXTURES / "rows.jsonl"  # the committed baselines.jsonl rows these runs wrote (7 of the 14 runs)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def report(self, *extra: str, rows: Path | None = None, runs: Path | None = None) -> dict:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--baseline-report", "--baseline", str(rows or self.ROWS), "--runs", str(runs or self.RUNS),
                             "--json", *extra])
        self.assertEqual(code, 0)
        return json.loads(printed.getvalue())

    def text(self, *extra: str, rows: Path | None = None, runs: Path | None = None) -> str:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--baseline-report", "--baseline", str(rows or self.ROWS), "--runs", str(runs or self.RUNS), *extra])
        self.assertEqual(code, 0)
        return printed.getvalue()

    @staticmethod
    def by_name(report: dict) -> dict:
        return {Path(record["output"]).name: record for record in report["records"]}

    @staticmethod
    def cell(report: dict, **want) -> dict:
        found = [c for c in report["cells"] if all(c["cell"].get(k) == v for k, v in want.items())]
        assert len(found) == 1, (want, [c["cell"] for c in report["cells"]])
        return found[0]


class BaselineReportClassTest(BaselineReportCase):
    """What the report counts and what it names and leaves out, by what the run folders themselves record."""

    def test_every_attempt_is_in_the_report_once_whether_the_file_or_a_folder_or_both_know_it(self):
        report = self.report()
        self.assertEqual(len(report["records"]), 19)
        sources = [r["record"] for r in report["records"]]
        self.assertEqual((sources.count("file+folder"), sources.count("folder"), sources.count("file")), (11, 8, 0))
        # a file row whose folder is gone stays, as a file-only record
        lonely = self.tmp / "rows.jsonl"
        lonely.write_text(self.ROWS.read_text() + json.dumps({"case": "hello", "source": "marketplace", "host": "claude",
                                                              "model": "m", "effort": None, "output": "/gone/hello",
                                                              "verdicts": {"shiploop": True}, "turns": 5}) + "\n")
        again = self.report(rows=lonely)
        self.assertEqual(len(again["records"]), 20)
        self.assertEqual(self.by_name(again)["hello"]["record"], "file")

    def test_a_regrade_is_not_a_resume_and_a_real_resume_a_mixed_host_run_and_a_blocked_run_are_named(self):
        records = self.by_name(self.report())
        classes = {name: record["class"] for name, record in records.items()}
        self.assertEqual({name for name, c in classes.items() if c == "counted"},
                         {"v1220-battleship-sonnet", "v1230-battleship-sonnet", "r1-battleship-sonnet", "r2-battleship-sonnet",
                          "r3-battleship-sonnet", "r1-checkers-sonnet", "r2-checkers-sonnet", "r3-checkers-sonnet",
                          "v1220-battleship-grok-medium-none", "v1161-hello", "v1180-hello-sonnet", "v1190-hello-sonnet",
                          "v1190-hello-sonnet-2", "v1200-hello-sonnet"})
        self.assertEqual(classes["r2-battleship-grok-none"], "mixed host")
        self.assertEqual(classes["r3-battleship-grok-none"], "resumed")
        self.assertEqual(classes["r1-battleship-grok-none"], "did not reach done")
        self.assertEqual(classes["v1230-battleship-grok-none"], "did not reach done")
        self.assertEqual(classes["v1210-battleship-grok-medium"], "no result.json")
        # the three regraded finished runs that "resumed_run is set" would have dropped are counted
        for name in ("v1230-battleship-sonnet", "r1-battleship-sonnet", "r1-checkers-sonnet"):
            self.assertEqual(records[name]["class"], "counted", name)
        self.assertEqual(records["r2-battleship-grok-none"]["hosts_used"], ["grok", "claude"])

    def test_the_reason_is_a_sentence_a_person_can_read(self):
        records = self.by_name(self.report())
        self.assertIn("grok and claude", records["r2-battleship-grok-none"]["why"])
        self.assertIn("engine blocked", records["v1230-battleship-grok-none"]["why"])
        self.assertIn("resumed", records["r3-battleship-grok-none"]["why"])
        self.assertIsNone(records["r3-battleship-sonnet"]["why"])

    def test_a_process_nobody_observed_is_not_counted(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        record = json.loads((copy / "r3-battleship-sonnet" / "result.json").read_text())
        record["process"] = {"status": "not observed", "returncode": None, "sessions": [], "pass": None, "regraded": True}
        record["termination"]["process_status"] = run.NOT_OBSERVED
        (copy / "r3-battleship-sonnet" / "result.json").write_text(json.dumps(record))
        (copy / "r3-battleship-sonnet" / "invocation.json").write_text(
            json.dumps({**json.loads((copy / "r3-battleship-sonnet" / "invocation.json").read_text())}))
        found = self.by_name(self.report(runs=copy))["r3-battleship-sonnet"]
        self.assertEqual(found["class"], "process not observed")

    def test_a_seeded_run_is_named_and_not_counted(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        record = json.loads((copy / "r2-battleship-sonnet" / "result.json").read_text())
        record["seeded"] = {"stage": "step-plan"}
        (copy / "r2-battleship-sonnet" / "result.json").write_text(json.dumps(record))
        self.assertEqual(self.by_name(self.report(runs=copy))["r2-battleship-sonnet"]["class"], "seeded")

    def test_a_result_that_cannot_be_read_does_not_stop_the_report(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        (copy / "r2-battleship-sonnet" / "result.json").write_text("{not json")
        found = self.by_name(self.report(runs=copy))["r2-battleship-sonnet"]
        self.assertEqual(found["class"], "no result.json")
        self.assertIn("unreadable", found["why"])


class BaselineReportCellTest(BaselineReportCase):
    """The cells: attempts, builds and the n, min, median and max of cost, turns, minutes and planning minutes, from the
    committed extracts. The figures are the ones the loop's journal cites, recomputed from the saved folders."""

    BATTLESHIP = dict(case="battleship", source="checkout", host="claude", effort=None, planning_review="stage")

    def test_battleship_on_sonnet_is_one_cell_of_five_runs_on_five_builds(self):
        cell = self.cell(self.report(), **self.BATTLESHIP)
        self.assertEqual(cell["attempts"], {"seen": 5, "counted": 5, "passed": 5, "did_not_reach_done": 0, "mixed_host": 0,
                                            "resumed": 0, "seeded": 0, "ended_by_harness": 0, "process_not_observed": 0,
                                            "no_driver_recorded": 0, "no_result": 0})
        self.assertEqual(sum(cell["builds"]["plugin_sha256"].values()), 5)
        self.assertEqual((len(cell["builds"]["plugin_sha256"]), cell["builds"]["unrecorded"]), (5, 0))
        measures = cell["measures"]
        self.assertEqual({k: measures["cost_usd"][k] for k in ("n", "min", "median", "max")},
                         {"n": 5, "min": 5.6749, "median": 5.8146, "max": 9.6543})
        self.assertEqual({k: measures["turns"][k] for k in ("n", "min", "median", "max")},
                         {"n": 5, "min": 197, "median": 207, "max": 294})
        self.assertEqual({k: measures["minutes"][k] for k in ("n", "min", "median", "max")},
                         {"n": 5, "min": 12.6, "median": 13.8, "max": 20.0})

    def test_the_planning_window_of_a_regraded_run_counts_and_the_file_row_that_lacks_it_loses_to_the_folder(self):
        report = self.report()
        planning = self.cell(report, **self.BATTLESHIP)["measures"]["planning_minutes"]
        # v1220 predates the planning block; v1230's regraded metrics.json holds a closed 388 s window its file row lacks
        self.assertEqual({k: planning[k] for k in ("n", "not_measured", "min", "median", "max")},
                         {"n": 4, "not_measured": 1, "min": 4.85, "median": 5.56, "max": 6.47})
        v1230 = self.by_name(report)["v1230-battleship-sonnet"]
        self.assertEqual(v1230["planning_seconds"], 388.0)
        self.assertIn("planning_seconds", v1230["recomputed"])
        self.assertIsNone(self.by_name(report)["v1220-battleship-sonnet"]["planning_seconds"])

    def test_checkers_on_sonnet_is_one_cell_of_three_and_two_of_its_rows_exist_only_in_a_folder(self):
        report = self.report()
        cell = self.cell(report, case="checkers", host="claude")
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["counted"]), (3, 3))
        self.assertEqual({k: cell["measures"]["cost_usd"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 5.1613, "median": 6.6509, "max": 8.5146})
        self.assertEqual({k: cell["measures"]["turns"][k] for k in ("min", "median", "max")}, {"min": 185, "median": 232, "max": 293})
        self.assertEqual({k: cell["measures"]["planning_minutes"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 5.67, "median": 6.12, "max": 7.02})
        by = self.by_name(report)
        self.assertEqual([by[n]["record"] for n in ("r1-checkers-sonnet", "r2-checkers-sonnet", "r3-checkers-sonnet")],
                         ["file+folder", "folder", "file+folder"])  # r2 wrote its row in a worktree that never committed it

    def test_the_file_row_wins_where_it_has_a_value_and_the_folder_fills_only_what_the_row_lacks(self):
        rows = [json.loads(line) for line in self.ROWS.read_text().splitlines()]
        for row in rows:
            if row["output"].endswith("/v1230-battleship-sonnet"):
                row["cost_usd"], row["planning_seconds"] = 99.0, 1.0
        edited = self.tmp / "rows.jsonl"
        edited.write_text("".join(json.dumps(r) + "\n" for r in rows))
        found = self.by_name(self.report(rows=edited))["v1230-battleship-sonnet"]
        self.assertEqual((found["cost_usd"], found["planning_seconds"]), (99.0, 1.0))
        self.assertNotIn("planning_seconds", found["recomputed"])

    def test_the_grok_cell_counts_every_attempt_and_marks_what_the_harness_calls_a_lower_bound(self):
        report = self.report()
        cell = self.cell(report, case="custom", host="grok")
        self.assertEqual(cell["attempts"], {"seen": 5, "counted": 1, "passed": 1, "did_not_reach_done": 2, "mixed_host": 1,
                                            "resumed": 1, "seeded": 0, "ended_by_harness": 0, "process_not_observed": 0,
                                            "no_driver_recorded": 0, "no_result": 0})
        self.assertEqual(cell["cell"]["prompt_sha256"][:8], "5ea67bf3")  # five raw prompts, one masked prompt
        cost = cell["measures"]["cost_usd"]
        self.assertEqual((cost["n"], cost["min"], cost["lower_bound_rows"], cost["lower_bound_unknown_rows"]), (1, 12.5014, 1, 0))
        self.assertEqual(cell["measures"]["turns"]["lower_bound_rows"], 1)
        self.assertNotIn("lower_bound_rows", cell["measures"]["minutes"])
        self.assertIs(self.by_name(report)["v1220-battleship-grok-medium-none"]["lower_bound"], True)
        self.assertIs(self.by_name(report)["r3-battleship-sonnet"]["lower_bound"], False)
        self.assertEqual(cell["outputs"]["mixed host"], ["r2-battleship-grok-none"])

    def test_a_run_with_no_result_is_an_attempt_in_its_own_cell(self):
        cell = self.cell(self.report(), case="battleship", source="marketplace", host="grok")
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["no_result"], cell["attempts"]["counted"]), (1, 1, 0))
        self.assertIsNone(cell["measures"]["cost_usd"]["min"])

    def test_the_same_plugin_bytes_are_one_build_and_one_version_string_on_two_trees_are_two(self):
        by = self.by_name(self.report())
        self.assertEqual(by["r1-battleship-sonnet"]["plugin_sha256"], by["r1-checkers-sonnet"]["plugin_sha256"])
        self.assertNotEqual(by["v1220-battleship-sonnet"]["plugin_sha256"], by["v1230-battleship-sonnet"]["plugin_sha256"])
        self.assertEqual((by["v1220-battleship-sonnet"]["plugin_version"], by["v1230-battleship-sonnet"]["plugin_version"]),
                         ("1.22.0", "1.22.0"))
        for name in ("r1-battleship-sonnet", "v1220-battleship-sonnet"):
            self.assertIn("plugin_sha256", by[name]["recomputed"])  # the old run did not record it: the report derived it

    def test_a_plugin_dir_outside_the_runs_own_folder_is_not_digested_after_the_fact(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "plugin.json").write_text("whatever is there today")
        record = json.loads((copy / "r2-battleship-sonnet" / "invocation.json").read_text())
        record["plugin_dir"] = str(elsewhere)
        (copy / "r2-battleship-sonnet" / "invocation.json").write_text(json.dumps(record))
        found = self.by_name(self.report(runs=copy))["r2-battleship-sonnet"]
        self.assertIsNone(found["plugin_sha256"])
        self.assertNotIn("plugin_sha256", found["recomputed"])

    def test_host_builds_come_from_the_runs_own_records_and_the_report_never_asks_a_cli(self):
        with mock.patch.object(hosts.Host, "cli_version", side_effect=AssertionError("the report probed a CLI")), \
                mock.patch.object(hosts.GrokHost, "cli_version", side_effect=AssertionError("the report probed Grok")), \
                mock.patch.object(hosts, "probe_version", side_effect=AssertionError("the report probed a CLI")):
            by = self.by_name(self.report())
        self.assertEqual(by["r3-battleship-sonnet"]["host_build"], "2.1.294")
        self.assertEqual(by["v1230-battleship-sonnet"]["host_build"], "2.1.292")
        self.assertEqual(by["v1220-battleship-sonnet"]["host_build"], "2.1.291")  # only in the run's init event
        self.assertIn("host_build", by["v1220-battleship-sonnet"]["recomputed"])
        self.assertIsNone(by["r1-battleship-grok-none"]["host_build"])  # launched before the field: null, not today's build
        cell = self.cell(self.report(), **self.BATTLESHIP)
        self.assertEqual(cell["host_builds"], {"2.1.291": 1, "2.1.292": 1, "2.1.294": 3, "unrecorded": 0})

    def test_overlap_is_a_lower_bound_over_the_recorded_runs_and_a_row_with_no_span_is_unknown(self):
        cell = self.cell(self.report(), **self.BATTLESHIP)
        self.assertEqual(cell["overlap"], {"rows": 5, "overlapped_by_span": 4, "not_seen_overlapping": 1, "unknown": 0})  # v1220 ran alone
        self.assertEqual(self.cell(self.report(), case="checkers", host="claude")["overlap"],
                         {"rows": 3, "overlapped_by_span": 3, "not_seen_overlapping": 0, "unknown": 0})
        spanless = self.tmp / "rows.jsonl"
        spanless.write_text(json.dumps({"case": "battleship", "source": "checkout", "host": "claude",
                                        "model": "claude-sonnet-5-5", "effort": None, "planning_review": "stage",
                                        "prompt_sha256": self.cell(self.report(), **self.BATTLESHIP)["cell"]["prompt_sha256"],
                                        "verdicts": {"shiploop": True}, "termination": {"engine_status": "done"},
                                        "turns": 150, "cost_usd": 4.0, "output": "/gone/older", "pass": True}) + "\n")
        wider = self.cell(self.report(rows=spanless), **self.BATTLESHIP)
        self.assertEqual(wider["overlap"], {"rows": 6, "overlapped_by_span": 4, "not_seen_overlapping": 1, "unknown": 1})
        self.assertEqual(wider["attempts"]["counted"], 6)
        self.assertIsNone(self.by_name(self.report(rows=spanless))["older"]["overlaps"])

    def test_the_spans_are_the_streams_first_and_last_stamp(self):
        record = self.by_name(self.report())["r3-battleship-sonnet"]
        self.assertEqual(record["minutes"], 12.6)
        self.assertLess(record["started"], record["ended"])


class BaselineReportOverlapTest(BaselineReportCase):
    """Overlap from recorded spans: strict intersection, both ways, nothing excluded."""

    def spans(self, *spans) -> dict:
        rows = [{"case": "hello", "source": "marketplace", "host": "claude", "model": "m", "effort": None,
                 "planning_review": "stage", "prompt_sha256": "aaaaaaaaaaaa", "verdicts": {"shiploop": True},
                 "termination": {"engine_status": "done"}, "pass": True, "turns": 10, "cost_usd": 1.0,
                 "output": f"/gone/r{n}", "started": a, "ended": b} for n, (a, b) in enumerate(spans)]
        path = self.tmp / "rows.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in rows))
        empty = self.tmp / "no-runs"
        empty.mkdir(exist_ok=True)
        return self.report(rows=path, runs=empty)

    def test_touching_intervals_do_not_overlap_and_crossing_ones_do_both_ways(self):
        report = self.spans((0.0, 10.0), (10.0, 20.0), (15.0, 30.0))
        self.assertEqual([r["overlaps"] for r in report["records"]], [0, 1, 1])
        self.assertEqual(report["cells"][0]["overlap"], {"rows": 3, "overlapped_by_span": 2, "not_seen_overlapping": 1, "unknown": 0})

    def test_a_run_inside_another_overlaps_it_and_the_minutes_come_from_the_span(self):
        report = self.spans((0.0, 600.0), (100.0, 200.0))
        self.assertEqual([r["overlaps"] for r in report["records"]], [1, 1])
        self.assertEqual([r["minutes"] for r in report["records"]], [10.0, 1.7])


class LiveLineAndReportTest(BaselineReportCase):
    """The live 'baseline vs' line reads one file; the report unions the file with the folders. One rule, two inputs."""

    def test_the_live_rule_sees_the_file_rows_and_the_report_sees_the_folders_the_file_lacks(self):
        battleship = self.cell(self.report(), case="battleship", host="claude")
        live, seen, _ = run.matching_rows(self.ROWS, "battleship", "checkout", "claude", "claude-sonnet-5-5", None, "stage",
                                          battleship["cell"]["prompt_sha256"])
        self.assertEqual((len(live), seen), (3, 3))  # v1220, v1230, r3: the rows the worktrees' files hold
        self.assertEqual(battleship["attempts"]["counted"], 5)  # r1 and r2 exist only as folders
        # the report's counted rows that a file holds are exactly the rows the live rule offers
        offered = {row["output"] for row in live}
        counted_in_file = {r["output"] for r in self.report()["records"]
                           if r["class"] == "counted" and r["record"] == "file+folder" and r["case"] == "battleship"}
        self.assertEqual(offered, counted_in_file)

    def test_the_two_committed_custom_rows_match_no_live_run_but_the_report_counts_the_done_one(self):
        # The transitional break named in SPEC: a row written before prompt_sha256 existed matches no custom run. The
        # report recovers the prompt from the folder's prompt.txt, so it still counts the finished Grok run.
        prompt = self.cell(self.report(), case="custom")["cell"]["prompt_sha256"]
        live, seen, skipped = run.matching_rows(self.ROWS, "custom", "checkout", "grok", "grok-4.7", "medium", "none", prompt)
        self.assertEqual((live, seen, dict(skipped)), ([], 2, {"another prompt": 2}))
        self.assertEqual(self.cell(self.report(), case="custom")["attempts"]["counted"], 1)
        # a custom row that carries the hash is a basis, and the blocked one is skipped for it
        rows = [json.loads(line) for line in self.ROWS.read_text().splitlines()]
        for row in rows:
            if row["case"] == "custom":
                row["prompt_sha256"] = prompt
        stamped = self.tmp / "rows.jsonl"
        stamped.write_text("".join(json.dumps(r) + "\n" for r in rows))
        live, seen, skipped = run.matching_rows(stamped, "custom", "checkout", "grok", "grok-4.7", "medium", "none", prompt)
        self.assertEqual(([Path(r["output"]).name for r in live], dict(skipped)),
                         (["v1220-battleship-grok-medium-none"], {"did not reach done": 1}))


class RowMatchesTest(unittest.TestCase):
    """run.row_matches: the one predicate behind matching_rows and the report; None when a row is a basis, else why not."""

    def test_the_source_is_compared_by_its_name_and_not_by_the_note_a_resume_adds(self):
        resumed = row(source="marketplace (resumed on its original install)")
        self.assertIsNone(run.row_matches(resumed, "battleship", "marketplace", "claude", "m", None, "stage", None))
        self.assertEqual(run.row_matches(row(), "battleship", "marketplace", "claude", "m", None, "stage", None),
                         "another case or source")

    def test_each_reason_has_its_own_words(self):
        key = ("battleship", "checkout", "claude", "m", None, "stage", None)
        self.assertIsNone(run.row_matches(row(), *key))
        self.assertEqual(run.row_matches(row(host="grok"), *key), "another host, model or effort")
        self.assertEqual(run.row_matches(row(planning_review="none"), *key), "another planning_review mode")
        self.assertEqual(run.row_matches(row(prompt_sha256="aaaaaaaaaaaa"), *key[:6], "bbbbbbbbbbbb"), "another prompt")
        self.assertEqual(run.row_matches(row(verdicts={"shiploop": False}), *key), "did not reach done")
        self.assertEqual(run.row_matches(row(case="checkers"), *key), "another case or source")

    def test_matching_rows_is_this_predicate_and_nothing_else(self):
        self.assertIn("row_matches(", _source(run.matching_rows))
        self.assertNotIn("_prompt_differs(", _source(run.matching_rows))


class BaselineReportRuleTest(BaselineReportCase):
    """The report and the live line decide with one predicate; where the report differs on purpose, the difference is
    listed in `recomputed`."""

    def copy_runs(self) -> Path:
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        return copy

    def test_runs_before_1_22_read_stage_by_the_same_rule_as_a_row(self):
        report = self.report()
        by = self.by_name(report)
        for name in ("v1161-hello", "v1180-hello-sonnet", "v1190-hello-sonnet", "v1190-hello-sonnet-2", "v1200-hello-sonnet"):
            self.assertEqual(by[name]["planning_review"], "stage", name)
        self.assertEqual(self.cell(report, case="hello", source="marketplace")["cell"]["planning_review"], "stage")
        self.assertFalse([r for r in report["records"] if r["planning_review"] == "not recorded" and r["plugin_version"]
                          and tuple(int(x) for x in r["plugin_version"].split(".")) < (1, 22, 0)])

    def test_the_live_rule_offers_one_hello_row_and_the_report_counts_four_with_the_difference_listed(self):
        report = self.report()
        cell = self.cell(report, case="hello", source="marketplace")
        live, seen, skipped = run.matching_rows(self.ROWS, "hello", "marketplace", "claude", "claude-sonnet-5-5", None, "stage",
                                                cell["cell"]["prompt_sha256"])
        self.assertEqual([Path(r["output"]).name for r in live], ["v1200-hello-sonnet"])
        self.assertEqual(dict(skipped), {"another host, model or effort": 3})
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["counted"]), (4, 4))
        by = self.by_name(report)
        for name in ("v1161-hello", "v1190-hello-sonnet", "v1190-hello-sonnet-2"):  # rows written before the driver fields
            self.assertTrue({"host", "model"} <= set(by[name]["recomputed"]), (name, by[name]["recomputed"]))
            self.assertNotIn("effort", by[name]["recomputed"])  # null in the row and in the folder: nothing supplied
        self.assertNotIn("host", by["v1200-hello-sonnet"]["recomputed"])  # its row names a driver

    def test_every_member_of_a_cell_is_a_row_the_live_predicate_accepts_for_the_cells_key(self):
        report = self.report()
        for cell in report["cells"]:
            c = cell["cell"]
            for record in report["records"]:
                if record["class"] != "counted" or Path(record["output"]).name not in cell["outputs"].get("counted", []):
                    continue
                member = {k: record[k] for k in ("case", "source", "host", "model", "effort", "planning_review",
                                                 "prompt_sha256")}
                member["verdicts"] = {"shiploop": True}
                if c["host"] is None and c["model"] is None:
                    continue
                self.assertIn(run.row_matches(member, c["case"], c["source"], c["host"], c["model"], c["effort"],
                                              c["planning_review"], c["prompt_sha256"]), (None,), (c, record["output"]))

    def file_rows(self, *specs) -> Path:
        base = {"case": "csv", "source": "checkout", "host": "claude", "model": "m", "effort": None,
                "planning_review": "stage", "verdicts": {"shiploop": True}, "termination": {"engine_status": "done"},
                "pass": True, "turns": 10, "cost_usd": 1.0}
        path = self.tmp / "rows.jsonl"
        path.write_text("".join(json.dumps({**base, "output": f"/gone/{name}", **({"prompt_sha256": h} if h else {})}) + "\n"
                                for name, h in specs))
        empty = self.tmp / "no-runs"
        empty.mkdir(exist_ok=True)
        return path

    def test_a_named_cases_row_with_no_prompt_hash_sits_in_the_only_cell_or_alone_when_there_are_two(self):
        empty = self.tmp / "no-runs"
        one = self.report(rows=self.file_rows(("a", "aaaaaaaaaaaa"), ("b", None)), runs=empty)
        self.assertEqual([(c["cell"]["prompt_sha256"], c["attempts"]["counted"]) for c in one["cells"]], [("aaaaaaaaaaaa", 2)])
        two = self.report(rows=self.file_rows(("a", "aaaaaaaaaaaa"), ("b", None), ("c", "cccccccccccc")), runs=empty)
        self.assertEqual([(c["cell"]["prompt_sha256"], c["outputs"]["counted"]) for c in two["cells"]],
                         [(None, ["b"]), ("aaaaaaaaaaaa", ["a"]), ("cccccccccccc", ["c"])])
        # the live rule would offer b to a run of either prompt: that is why the report cannot place it
        live = run.matching_rows(self.tmp / "rows.jsonl", "csv", "checkout", "claude", "m", None, "stage", "cccccccccccc")[0]
        self.assertEqual(sorted(Path(r["output"]).name for r in live), ["b", "c"])

    def test_a_custom_cases_row_with_no_hash_is_never_in_a_cell_with_a_hash(self):
        rows = self.tmp / "rows.jsonl"
        base = {"case": "custom", "source": "checkout", "host": "grok", "model": "m", "effort": "medium",
                "planning_review": "none", "verdicts": {"shiploop": True}, "termination": {"engine_status": "done"},
                "pass": True, "turns": 10, "cost_usd": 1.0}
        rows.write_text(json.dumps({**base, "output": "/gone/a", "prompt_sha256": "aaaaaaaaaaaa"}) + "\n"
                        + json.dumps({**base, "output": "/gone/b"}) + "\n")
        empty = self.tmp / "no-runs"
        empty.mkdir()
        report = self.report(rows=rows, runs=empty)
        self.assertEqual([(c["cell"]["prompt_sha256"], c["outputs"]["counted"]) for c in report["cells"]],
                         [(None, ["b"]), ("aaaaaaaaaaaa", ["a"])])

    def test_a_row_whose_folder_is_gone_and_whose_prompt_is_unrecorded_joins_its_drivers_cell(self):
        # the reviewer's repro: --runs given only the later date folders, so v1220 is known by its committed row alone
        copy = self.copy_runs()
        shutil.rmtree(copy / "v1220-battleship-sonnet")
        report = self.report(runs=copy)
        cell = self.cell(report, case="battleship", source="checkout", host="claude")
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["counted"]), (5, 5))
        self.assertEqual(cell["cell"]["prompt_sha256"], "d0c0cbe71344")
        self.assertEqual(self.by_name(report)["v1220-battleship-sonnet"]["record"], "file")
        self.assertEqual(len([c for c in report["cells"] if c["cell"]["case"] == "battleship"
                              and c["cell"]["source"] == "checkout" and c["cell"]["host"] == "claude"]), 1)

    def test_a_run_the_harness_ended_is_not_counted_though_its_engine_reached_done(self):
        copy = self.copy_runs()
        for name, change in (("r2-battleship-sonnet", lambda r: r["process"].update(status="timeout")),
                             ("r2-checkers-sonnet", lambda r: r["process"].update(status="stopped")),
                             ("r3-checkers-sonnet", lambda r: r["termination"].update(engine_status="active"))):
            record = json.loads((copy / name / "result.json").read_text())
            change(record)
            (copy / name / "result.json").write_text(json.dumps(record))
        by = self.by_name(self.report(runs=copy))
        for name in ("r2-battleship-sonnet", "r2-checkers-sonnet", "r3-checkers-sonnet"):
            self.assertEqual(by[name]["class"], "ended by the harness", name)
        self.assertIn("wrote no row", by["r2-battleship-sonnet"]["why"])
        self.assertEqual(self.cell(self.report(runs=copy), case="battleship", host="claude")["attempts"]["ended_by_harness"], 1)

    def test_a_file_only_grok_row_is_a_lower_bound(self):
        rows = self.tmp / "rows.jsonl"
        rows.write_text(json.dumps({"case": "battleship", "source": "checkout", "host": "grok", "model": "m", "effort": "medium",
                                    "planning_review": "none", "verdicts": {"shiploop": True}, "pass": True, "turns": 301,
                                    "cost_usd": 8.7455, "output": "/gone/grok", "prompt_sha256": "aaaaaaaaaaaa"}) + "\n"
                        + json.dumps({"case": "battleship", "source": "checkout", "host": "claude", "model": "m",
                                      "effort": None, "planning_review": "stage", "verdicts": {"shiploop": True}, "pass": True,
                                      "turns": 100, "cost_usd": 3.0, "output": "/gone/claude"}) + "\n")
        empty = self.tmp / "no-runs"
        empty.mkdir()
        report = self.report(rows=rows, runs=empty)
        by = self.by_name(report)
        self.assertIs(by["grok"]["lower_bound"], True)
        self.assertIsNone(by["claude"]["lower_bound"])  # a Claude row carries no count: unknown, not marked
        cell = self.cell(report, host="grok")
        self.assertEqual((cell["measures"]["cost_usd"]["lower_bound_rows"], cell["measures"]["cost_usd"]["lower_bound_unknown_rows"]), (1, 0))
        self.assertEqual(self.cell(report, host="claude")["measures"]["cost_usd"]["lower_bound_unknown_rows"], 1)


class BaselineReportWalkTest(BaselineReportCase):
    """Which folders are run folders, and what happens to an input that is not there."""

    def test_a_run_folder_is_found_at_any_depth_and_the_walk_stops_at_it(self):
        deep = self.tmp / "deep"
        (deep / "a" / "b" / "c").mkdir(parents=True)
        shutil.copytree(self.RUNS / "r3-battleship-sonnet", deep / "a" / "b" / "c" / "r3-battleship-sonnet")
        shutil.copytree(self.RUNS / "r3-checkers-sonnet", deep / "r3-checkers-sonnet")
        # a look-alike inside a run folder is part of the run's product, not a run
        inner = deep / "r3-checkers-sonnet" / "work" / "docs"
        inner.mkdir(parents=True)
        (inner / "invocation.json").write_text(json.dumps({"case": "hello", "host": "claude"}))
        # a folder of another harness (the audit's trial folders) is not a run folder
        audit = deep / "gas" / "battleship-create"
        audit.mkdir(parents=True)
        (audit / "result.json").write_text(json.dumps({"schema_version": 1, "trial_id": "x", "step_id": "y"}))
        names = sorted(Path(r["output"]).name for r in self.report(runs=deep, rows=self.tmp / "none.jsonl")["records"])
        self.assertEqual(names, ["r3-battleship-sonnet", "r3-checkers-sonnet"])

    def test_the_records_do_not_depend_on_how_runs_is_spelled(self):
        whole = self.report()
        children = sorted(p for p in self.RUNS.iterdir() if p.is_dir())
        by_child = self.report(runs=children[0])
        for extra in (children[1:],):
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                run.main(["--baseline-report", "--baseline", str(self.ROWS), "--runs", *map(str, reversed(children)),
                          "--json"])
            again = json.loads(printed.getvalue())
        relative = os.path.relpath(self.RUNS, Path.cwd())
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main(["--baseline-report", "--baseline", str(self.ROWS), "--runs", relative + "/", "--json"])
        spelled = json.loads(printed.getvalue())
        for other in (again, spelled):
            self.assertEqual(other["records"], whole["records"])
            self.assertEqual(other["cells"], whole["cells"])
        self.assertNotEqual(by_child["records"], whole["records"])  # one folder is one folder

    def test_a_missing_input_is_named_in_the_report_and_the_exit_stays_zero(self):
        gone = self.tmp / "nowhere"
        report = self.report(rows=gone, runs=gone)
        notes = " ".join(report["notes"])
        self.assertIn(f"the baseline file {gone} does not exist", notes)
        self.assertIn(f"the --runs directory {gone} does not exist", notes)
        empty = self.tmp / "empty"
        empty.mkdir()
        self.assertIn(f"no run folder was found under {empty}", " ".join(self.report(rows=self.ROWS, runs=empty)["notes"]))
        self.assertIn("does not exist", self.text(rows=gone, runs=gone))
        self.assertEqual(self.report(rows=gone, runs=gone)["records"], [])


class BaselineReportRobustnessTest(BaselineReportCase):
    """One bad record is one 'unreadable record' with the exception text; the report goes on and exits 0."""

    def test_malformed_records_become_unreadable_records_and_the_rest_are_unchanged(self):
        whole = self.report()
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)

        def edit(folder: str, name: str, change) -> None:
            path = copy / folder / name
            record = json.loads(path.read_text())
            change(record)
            path.write_text(json.dumps(record))

        edit("r1-battleship-sonnet", "invocation.json", lambda r: r.update(versions="oops"))
        edit("r1-checkers-sonnet", "result.json", lambda r: r.update(termination="blocked"))
        edit("r2-battleship-sonnet", "result.json", lambda r: r.update(process="exited"))
        edit("r2-checkers-sonnet", "result.json", lambda r: r.update(earlier_terminations=3))
        edit("r3-battleship-sonnet", "result.json", lambda r: r.update(output=5))
        rows = self.tmp / "rows.jsonl"
        lines = [json.loads(line) for line in self.ROWS.read_text().splitlines()]
        for row in lines:
            if row["output"].endswith("/r3-checkers-sonnet"):
                row["started"] = "yesterday"
        rows.write_text("".join(json.dumps(r) + "\n" for r in lines))
        report = self.report(rows=rows, runs=copy)
        by = self.by_name(report)
        bad = {"r1-battleship-sonnet", "r1-checkers-sonnet", "r2-battleship-sonnet", "r2-checkers-sonnet",
               "r3-battleship-sonnet", "r3-checkers-sonnet"}
        for name in bad:
            found = by.get(name) or by.get(str(5))
            self.assertIsNotNone(found, name)
        unreadable = [r for r in report["records"] if r["class"] == "unreadable record"]
        self.assertEqual(len(unreadable), 6, [(r["output"], r["class"]) for r in report["records"]])
        for record in unreadable:
            self.assertRegex(record["why"], r"\w+(Error|Exception): ")
        good = {Path(r["output"]).name: r for r in report["records"] if r["class"] != "unreadable record"}
        original = {Path(r["output"]).name: r for r in whole["records"]}
        for name, record in good.items():
            if name in original and name not in bad:
                self.assertEqual(record["class"], original[name]["class"], name)
        self.assertIn("unreadable record", self.text(rows=rows, runs=copy))

    def test_an_unreadable_plugin_file_is_a_null_digest_with_its_reason_and_the_report_exits_zero(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        locked = copy / "r3-battleship-sonnet" / "build" / "plugins" / "skill-craft" / "skills" / "shiploop" / "scripts" / "shiploop"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o644)
        if os.access(locked, os.R_OK):
            self.skipTest("the user can read a mode 000 file (root)")
        found = self.by_name(self.report(runs=copy))["r3-battleship-sonnet"]
        self.assertIsNone(found["plugin_sha256"])
        self.assertIn("unreadable", found["identity_unmeasured"]["plugin_sha256"])
        self.assertEqual(found["class"], "counted")


class BaselineReportReasonTest(BaselineReportCase):
    """A null identity field in the report says why, merged from the row, the result and the folder."""

    def test_old_grok_runs_say_their_launch_predates_the_field_and_known_fields_have_no_entry(self):
        by = self.by_name(self.report())
        grok = by["r1-battleship-grok-none"]
        self.assertIsNone(grok["host_build"])
        self.assertEqual(grok["identity_unmeasured"]["host_build"], "launch predates the field")
        self.assertNotIn("plugin_sha256", grok["identity_unmeasured"])
        self.assertEqual(by["r3-battleship-sonnet"]["identity_unmeasured"], {})  # measured and empty
        self.assertTrue(by["v1220-battleship-sonnet"]["identity_unmeasured"]["planning_seconds"])

    def test_the_host_build_of_a_run_is_its_first_launchs_and_never_a_later_one(self):
        copy = self.tmp / "runs"
        shutil.copytree(self.RUNS, copy)
        resume = next((copy / "r3-battleship-grok-none").glob("invocation-resume-grok-*.json"))
        record = json.loads(resume.read_text())
        record["host_build"] = "grok 9.9.9 (later)"
        resume.write_text(json.dumps(record))
        self.assertIsNone(self.by_name(self.report(runs=copy))["r3-battleship-grok-none"]["host_build"])
        first = copy / "r3-battleship-grok-none" / "invocation.json"
        record = json.loads(first.read_text())
        record["host_build"] = "grok 1.0.50 (first)"
        first.write_text(json.dumps(record))
        self.assertEqual(self.by_name(self.report(runs=copy))["r3-battleship-grok-none"]["host_build"], "grok 1.0.50 (first)")


class BaselineReportShapeTest(BaselineReportCase):
    """The keys Run Review reads, and the words the report does not use."""

    def test_the_json_keys_are_pinned(self):
        report = self.report()
        self.assertEqual(sorted(report), ["cells", "inputs", "notes", "records"])
        self.assertEqual(sorted(report["records"][0]),
                         sorted(["output", "record", "case", "source", "host", "model", "effort", "planning_review",
                                 "prompt_sha256", "plugin_version", "plugin_sha256", "host_build", "local_head", "started",
                                 "ended", "minutes", "planning_seconds", "planning_minutes", "cost_usd", "turns",
                                 "lower_bound", "pass", "engine_status", "process_status", "hosts_used", "class", "why",
                                 "recomputed", "identity_unmeasured", "overlaps"]))
        cell = report["cells"][0]
        self.assertEqual(sorted(cell), ["attempts", "builds", "cell", "host_builds", "measures", "outputs", "overlap"])
        self.assertEqual(sorted(cell["cell"]), ["case", "effort", "host", "model", "planning_review", "prompt_sha256", "source"])
        self.assertEqual(sorted(cell["measures"]), ["cost_usd", "minutes", "planning_minutes", "turns"])
        self.assertEqual(sorted(cell["measures"]["cost_usd"]),
                         ["lower_bound_rows", "lower_bound_unknown_rows", "max", "median", "min", "n", "not_measured"])
        self.assertEqual(sorted(cell["measures"]["minutes"]),
                         ["max", "median", "min", "n", "not_measured", "not_seen_overlapping", "overlapped_by_span"])
        self.assertEqual(sorted(cell["overlap"]), ["not_seen_overlapping", "overlapped_by_span", "rows", "unknown"])

    def test_the_text_report_states_facts_and_makes_no_claim_about_any_run(self):
        text = self.text()
        self.assertIn("cell battleship | checkout | claude | claude-sonnet-5-5 | effort - | planning_review stage | prompt ", text)
        self.assertIn("attempts   seen 5, counted 5, passed 5", text)
        self.assertIn("cost_usd   n=5 min 5.6749 median 5.8146 max 9.6543", text)
        self.assertIn("(lower bound in 1 of 1 rows)", text)
        self.assertIn("4 of 5 rows overlapped another recorded span; 1 not seen to", text)
        self.assertIn("minutes    n=5 min 12.6 median 13.8 max 20.0 (4 of 5 overlapped)", text)
        for word in ("within", "above the", "below the", "regression", "outside the range"):
            self.assertNotIn(word, text)
        self.assertIn("a range across builds is not a noise estimate", text)

    def test_the_inputs_are_recorded_as_given_so_the_command_can_be_run_again(self):
        report = self.report()
        self.assertEqual(report["inputs"], {"baseline": str(self.ROWS), "runs": [str(self.RUNS)]})


RUNS_JSON = ROOT / "docs" / "experiments" / "baseline-spread-20261009" / "runs.json"


class RecordedLoopRunsTest(unittest.TestCase):
    """A RECORD, not a check of code: the committed output of `run.py --baseline-report --baseline
    test/shiploop_e2e/baselines.jsonl --runs /Users/dadleet/e2e-runs --json` over the baseline file and the 29 saved run
    folders of 2026-10-03 to 2026-10-08, read as a static file. These tests pin what that record says (the figures the
    journal cites) and that it is internally consistent; none of them runs the report. They never read the live
    baselines.jsonl or the machine's run folders, so the owner committing the four rows that lived in other worktrees, or
    deleting a run folder, turns nothing red. The report code is pinned by BaselineReport* over the compact extracts and by
    FixtureReportRegenerationTest, which regenerates a report from them through the shipped command. To regenerate this
    file: run the command again and review the diff."""

    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(RUNS_JSON.read_text())
        cls.by_name = {Path(r["output"]).name: r for r in cls.report["records"]}

    def cell(self, **want) -> dict:
        found = [c for c in self.report["cells"] if all(c["cell"].get(k) == v for k, v in want.items())]
        self.assertEqual(len(found), 1, (want, [c["cell"] for c in self.report["cells"]]))
        return found[0]

    def test_the_inputs_are_the_command_that_made_it(self):
        self.assertEqual(self.report["inputs"], {"baseline": "test/shiploop_e2e/baselines.jsonl", "runs": ["/Users/dadleet/e2e-runs"]})

    def test_39_attempts_in_17_cells_each_of_the_29_folders_and_the_23_rows_once(self):
        records = self.report["records"]
        self.assertEqual((len(records), len(self.report["cells"])), (39, 17))
        kinds = [r["record"] for r in records]
        self.assertEqual((kinds.count("file+folder"), kinds.count("folder"), kinds.count("file")), (13, 16, 10))
        self.assertEqual(kinds.count("file+folder") + kinds.count("file"), 23)  # every committed row, once
        self.assertEqual(kinds.count("file+folder") + kinds.count("folder"), 29)  # every run folder, once
        classes = {c: sum(1 for r in records if r["class"] == c) for c in {r["class"] for r in records}}
        self.assertEqual(classes, {"counted": 15, "no driver recorded": 9, "did not reach done": 4, "resumed": 7,
                                   "no result.json": 3, "mixed host": 1})

    def test_the_loop_rows_three_of_seven_are_in_the_committed_file(self):
        in_file = {"r1-checkers-sonnet", "r3-battleship-sonnet", "r3-checkers-sonnet"}
        folder_only = {"r1-battleship-sonnet", "r1-battleship-grok-none", "r2-battleship-sonnet", "r2-checkers-sonnet"}
        for name in in_file:
            self.assertEqual(self.by_name[name]["record"], "file+folder", name)
        for name in folder_only:
            self.assertEqual(self.by_name[name]["record"], "folder", name)

    def test_sonnet_battleship_is_five_runs_on_five_plugin_trees_and_three_host_builds(self):
        cell = self.cell(case="battleship", source="checkout", host="claude")
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["counted"], cell["attempts"]["passed"]), (5, 5, 5))
        self.assertEqual(len(cell["builds"]["plugin_sha256"]), 5)
        self.assertEqual(cell["host_builds"], {"2.1.291": 1, "2.1.292": 1, "2.1.294": 3, "unrecorded": 0})
        stats = lambda name: {k: cell["measures"][name][k] for k in ("n", "min", "median", "max")}  # noqa: E731
        self.assertEqual(stats("cost_usd"), {"n": 5, "min": 5.6749, "median": 5.8146, "max": 9.6543})
        self.assertEqual(stats("turns"), {"n": 5, "min": 197, "median": 207, "max": 294})
        self.assertEqual(stats("minutes"), {"n": 5, "min": 12.6, "median": 13.8, "max": 20.0})
        self.assertEqual(stats("planning_minutes"), {"n": 4, "min": 4.85, "median": 5.56, "max": 6.47})
        self.assertEqual(cell["measures"]["planning_minutes"]["not_measured"], 1)  # v1220 predates the planning block
        self.assertEqual(cell["overlap"], {"rows": 5, "overlapped_by_span": 4, "not_seen_overlapping": 1, "unknown": 0})

    def test_the_two_runs_that_said_plugin_1_22_0_are_two_builds_and_two_heads_that_built_one_tree_are_one_build(self):
        # The "Sonnet cost rise, decomposed" entry explained 238 turns / $6.54 against 294 / $9.65 between two builds.
        a, b = self.by_name["v1220-battleship-sonnet"], self.by_name["v1230-battleship-sonnet"]
        self.assertEqual((a["plugin_version"], b["plugin_version"]), ("1.22.0", "1.22.0"))
        self.assertNotEqual(a["plugin_sha256"], b["plugin_sha256"])
        self.assertNotEqual(a["local_head"], b["local_head"])
        self.assertNotEqual(a["host_build"], b["host_build"])
        trio = {self.by_name[n]["plugin_sha256"] for n in ("r1-battleship-sonnet", "r1-checkers-sonnet", "r1-battleship-grok-none")}
        self.assertEqual(len(trio), 1, "three runs from two heads (587cd90d, 5e209285): one byte-identical tree")
        self.assertNotEqual(self.by_name["r1-battleship-sonnet"]["local_head"], self.by_name["r1-checkers-sonnet"]["local_head"])

    def test_the_only_pair_of_runs_on_one_build_is_the_two_v1190_hello_runs_and_it_is_in_a_cell_of_four_trees(self):
        # "a cell has no two runs of one build" was said and is false: v1190-hello-sonnet and -2 share a plugin tree and a
        # Claude Code build, and differ by 60 turns and $1.96. They are the only such pair in the data.
        a, b = self.by_name["v1190-hello-sonnet"], self.by_name["v1190-hello-sonnet-2"]
        self.assertEqual((a["plugin_sha256"], a["host_build"]), (b["plugin_sha256"], b["host_build"]))
        self.assertEqual((a["plugin_sha256"], a["host_build"]), ("643ee0214c57", "2.1.289"))
        self.assertEqual(((a["turns"], a["cost_usd"], a["minutes"]), (b["turns"], b["cost_usd"], b["minutes"])),
                         ((194, 5.3678, 12.8), (254, 7.3252, 15.4)))
        cell = self.cell(case="hello", source="marketplace", host="claude")
        self.assertEqual((cell["attempts"]["counted"], len(cell["builds"]["plugin_sha256"])), (5, 4))
        same = [(x["output"], y["output"]) for i, x in enumerate(self.report["records"]) for y in self.report["records"][i + 1:]
                if x["class"] == y["class"] == "counted" and x["plugin_sha256"] and x["plugin_sha256"] == y["plugin_sha256"]
                and x["host_build"] == y["host_build"] and x["case"] == y["case"] and x["host"] == y["host"]]
        self.assertEqual(len(same), 1)  # the only pair
        # the second of the pair overlapped v1180-hello-sonnet for 722 s, so its minutes are not a clean second sample
        c = self.by_name["v1180-hello-sonnet"]
        self.assertAlmostEqual(min(b["ended"], c["ended"]) - max(b["started"], c["started"]), 722.0, delta=1.0)
        self.assertEqual((a["overlaps"], b["overlaps"]), (0, 1))

    def test_the_four_batch_sonnet_runs_are_real_resumes_and_are_counted_in_no_measure(self):
        for name in ("battleship", "battleship-scoring", "hello", "seat-reservations"):
            found = [r for r in self.report["records"] if "/batch-sonnet/" in r["output"] and r["output"].endswith("/" + name)]
            self.assertEqual(len(found), 1, name)
            self.assertEqual(found[0]["class"], "resumed", name)

    def test_the_audit_harness_trial_folders_are_not_in_the_report(self):
        self.assertFalse([r for r in self.report["records"] if "gas-battleship-audit" in r["output"]])

    def test_sonnet_checkers_is_three_runs(self):
        cell = self.cell(case="checkers", host="claude")
        self.assertEqual({k: cell["measures"]["cost_usd"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 5.1613, "median": 6.6509, "max": 8.5146})
        self.assertEqual({k: cell["measures"]["turns"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 185, "median": 232, "max": 293})
        self.assertEqual(cell["overlap"], {"rows": 3, "overlapped_by_span": 3, "not_seen_overlapping": 0, "unknown": 0})

    def test_the_grok_cell_names_its_five_attempts_and_one_masked_prompt(self):
        cell = self.cell(case="custom", host="grok")
        self.assertEqual(cell["attempts"], {"seen": 5, "counted": 1, "passed": 1, "did_not_reach_done": 2, "mixed_host": 1,
                                            "resumed": 1, "seeded": 0, "ended_by_harness": 0, "process_not_observed": 0,
                                            "no_driver_recorded": 0, "no_result": 0})
        self.assertEqual(cell["outputs"], {"counted": ["v1220-battleship-grok-medium-none"],
                                           "did not reach done": ["v1230-battleship-grok-none", "r1-battleship-grok-none"],
                                           "mixed host": ["r2-battleship-grok-none"], "resumed": ["r3-battleship-grok-none"]})
        hashes = {self.by_name[n]["prompt_sha256"] for names in cell["outputs"].values() for n in names}
        self.assertEqual(hashes, {cell["cell"]["prompt_sha256"]})  # five raw prompts, one masked prompt
        self.assertTrue(cell["cell"]["prompt_sha256"].startswith("5ea67bf3"))
        self.assertEqual(self.by_name["r2-battleship-grok-none"]["hosts_used"], ["grok", "claude"])

    def test_every_grok_cost_and_turns_figure_is_marked_a_lower_bound(self):
        grok = [r for r in self.report["records"] if r["host"] == "grok" and r["cost_usd"] is not None and r["record"] != "file"]
        self.assertGreaterEqual(len(grok), 4)
        for record in grok:
            self.assertIs(record["lower_bound"], True, record["output"])
        cell = self.cell(case="custom", host="grok")
        self.assertEqual((cell["measures"]["cost_usd"]["lower_bound_rows"], cell["measures"]["turns"]["lower_bound_rows"]), (1, 1))

    def test_the_session_count_is_not_in_the_report_and_no_run_is_placed_against_a_range(self):
        text = RUNS_JSON.read_text()
        for word in ("unreported_sessions", "within", "regression", "outside the range"):
            self.assertNotIn(word, text)

    def test_the_cell_figures_are_the_records_summarised_and_nothing_else(self):
        import statistics
        for cell in self.report["cells"]:
            counted = [r for r in self.report["records"] if r["class"] == "counted"
                       and all(r[k] == cell["cell"][k] for k in cell["cell"])]
            self.assertEqual(len(counted), cell["attempts"]["counted"])
            for name in ("cost_usd", "turns", "minutes", "planning_minutes"):
                values = [r[name] for r in counted if r[name] is not None]
                got = cell["measures"][name]
                self.assertEqual(got["n"], len(values), (cell["cell"], name))
                if values:
                    digits = {"cost_usd": 4, "turns": 0, "minutes": 1, "planning_minutes": 2}[name]
                    self.assertEqual(got["min"], round(min(values), digits))
                    self.assertEqual(got["max"], round(max(values), digits))
                    self.assertEqual(got["median"], round(statistics.median(values), digits))


class LowerBoundMarkingTest(main_tests().PrintedCase):
    """A figure the harness calls a lower bound stays marked wherever it is summarised: the follow-on line and progress.py,
    not only the process and metrics lines."""

    def prior(self, metrics_record: dict) -> Path:
        prior = self.tmp / "prior"
        work = prior / "work"
        work.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        (work / "prior.txt").write_text("kept\n")
        (prior / "result.json").write_text(json.dumps({"case": "hello", "pass": True, "metrics": metrics_record}))
        return prior

    def follow_on(self, prior: Path) -> str:
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "follow"),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--continue-from", str(prior),
                             "--prompt", "Add a feature.", "--check", "true"])
        self.assertEqual(code, 0)
        return next(ln for ln in printed.getvalue().splitlines() if ln.startswith("  follow-on of"))

    def test_the_follow_on_line_marks_a_grok_run_and_a_prior_that_was_a_lower_bound(self):
        prior = self.prior({"turns": 40, "cost_usd": 2.5, "unreported_sessions": None,
                            "unmeasured": {"unreported_sessions": "Grok marks no session start"}})
        line = self.follow_on(prior)
        self.assertIn("turns 4 (lower bound) vs 40 (lower bound), cost $0.01 (lower bound) vs $2.5 (lower bound)", line)

    def test_a_prior_that_ended_whole_is_not_marked_and_one_that_predates_the_field_is_not_guessed(self):
        whole = self.follow_on(self.prior({"turns": 40, "cost_usd": 2.5, "unreported_sessions": 0}))
        self.assertIn("vs 40, cost $0.01 (lower bound) vs $2.5", whole)
        shutil.rmtree(self.tmp / "prior")
        shutil.rmtree(self.tmp / "follow")
        old = self.follow_on(self.prior({"turns": 40, "cost_usd": 2.5}))
        self.assertIn("vs 40, cost $0.01 (lower bound) vs $2.5", old)

    def test_progress_marks_the_cost_of_a_grok_run_as_it_marks_its_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            events = [{"type": "available_commands", "commands": [], "tools": []},
                      {"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                      {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.5}]
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            text = progress.report(out)
            self.assertIn("turns 1 (lower bound)", text)
            self.assertIn("cost $1.50 (lower bound)", text)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            events = [{"type": "system", "subtype": "init"},
                      {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
                      {"type": "result", "subtype": "success", "num_turns": 1, "total_cost_usd": 1.5}]
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            text = progress.report(out)
            self.assertIn("cost $1.50 |", text)
            self.assertNotIn("lower bound", text)


class FixtureReportRegenerationTest(BaselineReportCase):
    """The executable pin: the shipped command over the compact extracts reproduces test/fixtures/baseline-spread/report.json,
    its own committed output. (The 29-folder runs.json is a record of the live machine; this is the check of the code.)
    To regenerate: from the repository root,
      python3 test/shiploop_e2e/run.py --baseline-report --baseline test/fixtures/baseline-spread/rows.jsonl \\
          --runs test/fixtures/baseline-spread/runs --json | sed "s#$(pwd -P)#<repo>#g" > test/fixtures/baseline-spread/report.json"""

    def test_the_command_reproduces_the_committed_report(self):
        got = json.loads(json.dumps(self.report()).replace(str(ROOT), "<repo>"))
        want = json.loads((FIXTURES / "report.json").read_text())
        got["inputs"] = want["inputs"] = None  # the paths as typed
        self.assertEqual(got, want)

    def test_the_report_writes_nothing_anywhere_and_changes_no_file_time(self):
        def snapshot(root: Path) -> dict:
            return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(root.rglob("*")) if p.is_file()}

        writes: list[str] = []
        real_open = open

        def spy_open(file, mode="r", *args, **kwargs):
            if isinstance(mode, str) and any(c in mode for c in "wax+"):
                writes.append(f"open {file}")
            return real_open(file, mode, *args, **kwargs)

        def refuse(name):
            def fail(self, *args, **kwargs):
                writes.append(f"{name} {self}")
                raise AssertionError(f"{name} {self}")
            return fail

        before = snapshot(FIXTURES)
        empty_cwd, empty_tmp = self.tmp / "cwd", self.tmp / "tmp"
        empty_cwd.mkdir()
        empty_tmp.mkdir()
        here = Path.cwd()
        try:
            os.chdir(empty_cwd)
            with mock.patch.dict(os.environ, {"TMPDIR": str(empty_tmp)}), mock.patch("builtins.open", spy_open), \
                    mock.patch.object(Path, "write_text", refuse("write_text")), \
                    mock.patch.object(Path, "write_bytes", refuse("write_bytes")), \
                    mock.patch.object(Path, "mkdir", refuse("mkdir")), mock.patch.object(Path, "touch", refuse("touch")), \
                    mock.patch.object(os, "replace", side_effect=AssertionError("replace")), \
                    mock.patch.object(os, "remove", side_effect=AssertionError("remove")), \
                    mock.patch.object(shutil, "rmtree", side_effect=AssertionError("rmtree")):
                self.report()
                self.text()
        finally:
            os.chdir(here)
        self.assertEqual(writes, [])
        self.assertEqual(snapshot(FIXTURES), before)
        self.assertEqual(list(empty_cwd.iterdir()) + list(empty_tmp.iterdir()), [])


class IdentityDocsTest(unittest.TestCase):
    """The README says what each identity field is and what is never done to it; the SPEC carries the rules."""

    def text(self, name: str) -> str:
        return " ".join((ROOT / "test" / "shiploop_e2e" / name).read_text().split())

    def test_the_readme_names_each_field_and_the_probe_rule(self):
        readme = self.text("README.md")
        for phrase in ("`plugin_sha256`", "`prompt_sha256`", "`host_build`", "`started`, `ended`", "`planning_seconds`",
                       "`local_head`", "probed once when a launch starts", "It is never probed again",
                       "stays null, because today's build stamped on it would be a made-up fact",
                       "A regrade restates the recorded digest and never computes one",
                       "the build of the run's first launch",
                       "A later launch records its own probe on its own record and the run's result keeps the first launch's",
                       "`identity_unmeasured`", "a bare null is never all there is",
                       "A baseline row has no overlap field", "a discipline and not a guarantee",
                       "it can include a resumed run's pause"):
            self.assertIn(phrase, readme)

    def test_the_readme_says_which_rows_a_run_is_compared_with_and_names_the_transitional_break(self):
        readme = self.text("README.md")
        for phrase in ("`run.row_matches`, behind `run.matching_rows`",
                       "is still written (a blocked run is a record) and is never the row another run is compared with",
                       "`baseline nothing compared: this run did not reach done (engine blocked)`",
                       "unknown is not excluded", "two prompts are two cells and one prompt in two folders is one",
                       "Of the 23 committed rows, 15 name no host, model or effort and were never a basis; 6",
                       "the transitional break is the two Grok `none` rows",
                       "is marked on the `baseline vs` line too", "a `sample:` line states facts and no verdict",
                       "is `unknown`, not guessed"):
            self.assertIn(phrase, readme)

    def test_the_readme_says_why_the_grok_session_count_is_unknown_and_what_will_count_it(self):
        readme = self.text("README.md")
        for phrase in ("For a stream with Grok in it it is `null`, named in `unmeasured`", "Grok's events mark no session start",
                       "314 of them for 2 `end` events", "A null count keeps the lower-bound marking",
                       "the test is the host, not a field of one event",
                       "at least one session never reported", "`metrics.lower_bound` is the one predicate",
                       "a launch whose lines hold no `end` event never reported"):
            self.assertIn(phrase, readme)

    def test_the_readme_documents_the_baseline_report(self):
        readme = self.text("README.md")
        for phrase in ("--baseline-report [--baseline FILE] [--runs DIR ...] [--json]",
                       "Read-only: it starts no host, probes no CLI and writes nothing, and always exits 0",
                       "an input that is missing, and a record that cannot be read, are named in the report",
                       "found at any depth under each `--runs` directory and the walk stops at it",
                       "The output does not depend on how `--runs` is spelled",
                       "the row wins wherever it has a value", "A regrade is not a resume",
                       "`unreadable record`", "`no result.json`", "`mixed host`", "`ended by the harness`",
                       "`process not observed`", "`did not reach done`", "`counted`",
                       "`lower_bound_rows`", "`lower_bound_unknown_rows`", "`overlapped_by_span`",
                       "so it is a count and not a bound", "(4 of 5 overlapped)",
                       "listed under the cell of the host their result names and are counted in no measure",
                       "The report places no run within or outside a range and sets no threshold",
                       "Whether a run is a basis is this report's own rule", "its class does not replace this rule",
                       "`--json` prints `{inputs, records, cells, notes}`",
                       "the tests pin that file, never the live `baselines.jsonl`"):
            self.assertIn(phrase, readme)

    def test_the_spec_carries_the_rules_this_group_serves(self):
        spec = self.text("SPEC.md")
        for phrase in ("**A comparison names its sample**", "**A baseline row is a finished run's**",
                       "Amended 2026-10-09", "never probed afterwards", "`plugin_sha256`", "`prompt_sha256`",
                       "Transitional break, named", "`identity_unmeasured`", "`host_build` is the build of the run's first launch",
                       "One predicate (`row_matches`, behind `matching_rows`)", "The report differs on purpose in two ways",
                       "listed in the report with their class and counted in no measure",
                       "A count of overlapping runs from recorded spans is a count and not a bound",
                       "probability exactly 2/(n+1)", "classed \"ended by the harness\"",
                       "**Runs compared on wall time or per-call cost run one after the other**"):
            self.assertIn(phrase, spec)
        for retired in ("kept out of every cell", "belongs to no host's cell", "That count is a lower bound"):
            self.assertNotIn(retired, spec)


if __name__ == "__main__":
    unittest.main()
