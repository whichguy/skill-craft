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
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts  # noqa: E402
import metrics  # noqa: E402
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
    """Host.cli_version: the first stdout line of `<cli> --version`, None on any failure, and never a Claude probe."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_grok_and_codex_answer_with_the_first_stdout_line_of_version(self):
        grok = script(self.tmp / "grok", "#!/bin/sh\necho 'grok 1.0.50 (c58f321264ba)'\necho 'a second line'\n")
        # codex warns on stderr when CODEX_HOME does not exist; only stdout is the build
        codex = script(self.tmp / "codex", "#!/bin/sh\necho 'WARNING: CODEX_HOME does not exist' >&2\necho 'codex-cli 0.162.0'\n")
        self.assertEqual(hosts.GrokHost(str(grok)).cli_version({}), "grok 1.0.50 (c58f321264ba)")
        self.assertEqual(hosts.CodexHost(str(codex)).cli_version({}), "codex-cli 0.162.0")

    def test_a_probe_that_fails_prints_nothing_or_is_not_there_is_none(self):
        failing = script(self.tmp / "fails", "#!/bin/sh\necho 'grok 9'\nexit 1\n")
        silent = script(self.tmp / "silent", "#!/bin/sh\nexit 0\n")
        for binary in (failing, silent, self.tmp / "missing"):
            with self.subTest(binary=binary.name):
                self.assertIsNone(hosts.GrokHost(str(binary)).cli_version({}))
                self.assertIsNone(hosts.CodexHost(str(binary)).cli_version({}))

    def test_a_probe_that_hangs_is_ended_by_the_timeout_and_is_none(self):
        hangs = script(self.tmp / "hangs", "#!/bin/sh\nexec sleep 30\n")
        with mock.patch.object(hosts, "VERSION_TIMEOUT_SECONDS", 1):
            self.assertIsNone(hosts.GrokHost(str(hangs)).cli_version({}))

    def test_claude_is_never_probed_its_build_is_in_its_init_event(self):
        marker = self.tmp / "called"
        binary = script(self.tmp / "claude", f"#!/bin/sh\ntouch {marker}\necho '2.1.295 (Claude Code)'\n")
        self.assertIsNone(hosts.ClaudeHost(str(binary)).cli_version({}))
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
        (root / "stray.pyc").write_bytes(b"\3")
        outside = self.tmp / "outside.txt"
        outside.write_text("not part of the plugin")
        (root / "link").symlink_to(outside)
        self.assertEqual(run.tree_digest(root), before)
        outside.write_text("changed behind the link")
        self.assertEqual(run.tree_digest(root), before)

    def test_a_folder_that_is_not_there_has_no_digest(self):
        self.assertIsNone(run.tree_digest(self.tmp / "nowhere"))

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

    def test_local_head_is_read_from_a_marketplace_run_too(self):
        # a checkout run records versions.local_head; a marketplace run records it under versions.released
        row = run.baseline_row({"versions": {"source": "marketplace", "released": {"local_head": "7aff70aa"}}, "metrics": {}},
                               None, None)
        self.assertEqual(row["local_head"], "7aff70aa")

    def test_unreported_sessions_is_still_not_a_baseline_key(self):
        row = run.baseline_row({"metrics": {"unreported_sessions": 3}}, None, None)
        self.assertNotIn("unreported_sessions", row)


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
        self.assertIsNone(json.loads((Path(result["output"]) / "invocation.json").read_text())["host_build"])
        self.assertFalse(Path(f"{wrapper}.probes").exists(), "Claude was probed")

    def test_a_build_that_cannot_be_read_is_null_and_the_run_still_finishes(self):
        for host in ("grok", "codex"):
            with self.subTest(host=host):
                code, result, _ = self.run_as(host)  # the shared fakes exit non-zero on --version
                self.assertEqual(code, 0, result)
                self.assertIn("host_build", result)
                self.assertIsNone(result["host_build"])
                self.assertIsNone(self.last_row()["host_build"])

    def test_the_version_is_probed_once_per_launch_not_once_per_session_or_at_the_end(self):
        wrapper = self.versioned("grok", "grok 1.0.50 (c58f321264ba)")
        code, result, _ = self.run_as("grok", "resume", "--max-resumes", "2", binary=wrapper)
        self.assertEqual(code, 0, result)
        self.assertGreater(len(result["process"]["sessions"]), 1)
        self.assertEqual(len(Path(f"{wrapper}.probes").read_text().split()), 1)

    def test_a_resume_launch_writes_the_build_it_ran_on_its_own_record(self):
        code, stopped, _ = self.run_as("grok", "stuck", "--max-resumes", "0", binary=self.versioned("grok", "grok 1.0.50 (aaa)"))
        out = Path(stopped["output"])
        os.environ["FAKE_MODE"] = "done"
        newer = self.versioned("grok", "grok 1.0.51 (bbb)")
        # the same-host resume reads the catalog: a canned release, so nothing reaches git or the network
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False,
                    "catalog_version": "9.9.9", "shiploop_version": None, "unreleased": [], "ci": "success"}
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", "grok", "--grok-bin", str(newer), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.baselines), "--max-resumes", "0"])
        records = sorted(out.glob("invocation-resume-grok-*.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text())["host_build"], "grok 1.0.51 (bbb)")
        self.assertEqual(json.loads((out / "invocation.json").read_text())["host_build"], "grok 1.0.50 (aaa)")

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
        self.assertIsNone(regrade()["host_build"])

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

    def test_the_span_is_the_streams_first_and_last_stamp_and_an_unclosed_planning_window_is_null(self):
        code, result, _ = self.run_as("claude")
        stamps = [json.loads(line)["t"] for line in (Path(result["output"]) / "timeline.jsonl").read_text().splitlines()]
        self.assertEqual(result["span"], {"started": min(stamps), "ended": max(stamps)})
        row = self.last_row()
        self.assertEqual((row["started"], row["ended"]), (min(stamps), max(stamps)))
        self.assertIn("planning_seconds", result["metrics"])
        self.assertIsNone(result["metrics"]["planning_seconds"])  # no accepted test-spec: unknown, never 0
        self.assertIsNone(row["planning_seconds"])

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
        self.assertIn("turns 301 -> ", printed)
        self.assertNotIn("turns 503 -> ", printed)

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
                       "A baseline row has no overlap field", "as a lower bound", "a discipline and not a guarantee"):
            self.assertIn(phrase, readme)

    def test_the_readme_says_which_rows_a_run_is_compared_with_and_names_the_transitional_break(self):
        readme = self.text("README.md")
        for phrase in ("One rule picks the rows a run is compared with (`run.matching_rows`",
                       "is still written (a blocked run is a record) and is never the row another run is compared with",
                       "`baseline nothing compared: this run did not reach done (engine blocked)`",
                       "unknown is not excluded", "two prompts are two cells and one prompt in two folders is one",
                       "the 23 rows committed before the field existed keep comparing",
                       "The one transitional break is therefore the Grok `none` runs",
                       "a `sample:` line states facts and no verdict", "is `unknown`, not guessed"):
            self.assertIn(phrase, readme)

    def test_the_spec_carries_the_rules_this_group_serves(self):
        spec = self.text("SPEC.md")
        for phrase in ("**A comparison names its sample**", "**A baseline row is a finished run's**",
                       "Amended 2026-10-09", "never probed afterwards", "`plugin_sha256`", "`prompt_sha256`",
                       "Transitional break, named",
                       "**Runs compared on wall time or per-call cost run one after the other**"):
            self.assertIn(phrase, spec)


if __name__ == "__main__":
    unittest.main()
