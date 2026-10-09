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

    def test_the_spec_carries_the_rules_this_group_serves(self):
        spec = self.text("SPEC.md")
        for phrase in ("**A comparison names its sample**", "**A baseline row is a finished run's**",
                       "Amended 2026-10-09", "never probed afterwards", "`plugin_sha256`", "`prompt_sha256`",
                       "Transitional break, named",
                       "**Runs compared on wall time or per-call cost run one after the other**"):
            self.assertIn(phrase, spec)


if __name__ == "__main__":
    unittest.main()
