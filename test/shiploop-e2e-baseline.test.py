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


class GrokSessionStartTest(unittest.TestCase):
    """A Grok event stream carries no session-start marker, so a session that never reported cannot be counted from it.

    ``available_commands`` is Grok's announcement of its tool and command list and it is repeated inside one session:
    r1-battleship-grok-none (2026-10-08) holds 314 of them for 2 `end` events (301 model calls), 2 at the head of the
    first launch and 8 at the head of the resume. Counting each as a start printed "lower bound: 312 session(s) never
    reported" for a cost that equals the two end events' totals. The count is unknown, and the lower-bound marking stays,
    because a killed Grok session cannot be told from a long one by the stream alone; the harness's own launch rows can."""

    ACCEPTED = [("A1", "intake", "done", 105.0)]

    def stream(self) -> list[dict]:
        return [json.loads(line) for line in (FIXTURES / "grok-r1-session-shape.jsonl").read_text().splitlines()]

    def collect(self, stream: list[dict]) -> dict:
        return main_tests().collect_stream(stream, self.ACCEPTED)

    def test_the_recorded_shape_has_many_announcements_for_two_ended_sessions(self):
        kinds = [event["type"] for event in self.stream()]
        self.assertEqual((kinds.count("available_commands"), kinds.count("end")), (314, 2))

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

    def test_a_stream_that_mixes_grok_and_claude_events_is_unknown_too(self):
        # r2-battleship-grok-none: Grok started it and was killed with its harness; Claude finished it.
        grok = [e for e in self.stream()[:6]]  # a launch that never ended
        claude = [{"type": "system", "subtype": "init", "claude_code_version": "2.1.294"},
                  {"type": "result", "subtype": "success", "num_turns": 5, "total_cost_usd": 1.0}]
        m = self.collect(grok + claude)
        self.assertIsNone(m["unreported_sessions"])
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
        self.assertEqual(len(report["records"]), 14)
        sources = [r["record"] for r in report["records"]]
        self.assertEqual((sources.count("file+folder"), sources.count("folder"), sources.count("file")), (7, 7, 0))
        # a file row whose folder is gone stays, as a file-only record
        lonely = self.tmp / "rows.jsonl"
        lonely.write_text(self.ROWS.read_text() + json.dumps({"case": "hello", "source": "marketplace", "host": "claude",
                                                              "model": "m", "effort": None, "output": "/gone/hello",
                                                              "verdicts": {"shiploop": True}, "turns": 5}) + "\n")
        again = self.report(rows=lonely)
        self.assertEqual(len(again["records"]), 15)
        self.assertEqual(self.by_name(again)["hello"]["record"], "file")

    def test_a_regrade_is_not_a_resume_and_a_real_resume_a_mixed_host_run_and_a_blocked_run_are_named(self):
        records = self.by_name(self.report())
        classes = {name: record["class"] for name, record in records.items()}
        self.assertEqual({name for name, c in classes.items() if c == "counted"},
                         {"v1220-battleship-sonnet", "v1230-battleship-sonnet", "r1-battleship-sonnet", "r2-battleship-sonnet",
                          "r3-battleship-sonnet", "r1-checkers-sonnet", "r2-checkers-sonnet", "r3-checkers-sonnet",
                          "v1220-battleship-grok-medium-none"})
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

    def test_the_report_writes_nothing(self):
        def snapshot(root: Path) -> dict:
            return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}
        before = snapshot(FIXTURES)
        self.report()
        self.text()
        self.assertEqual(snapshot(FIXTURES), before)


class BaselineReportCellTest(BaselineReportCase):
    """The cells: attempts, builds and the n, min, median and max of cost, turns, minutes and planning minutes, from the
    committed extracts. The figures are the ones the loop's journal cites, recomputed from the saved folders."""

    BATTLESHIP = dict(case="battleship", source="checkout", host="claude", effort=None, planning_review="stage")

    def test_battleship_on_sonnet_is_one_cell_of_five_runs_on_five_builds(self):
        cell = self.cell(self.report(), **self.BATTLESHIP)
        self.assertEqual(cell["attempts"], {"seen": 5, "counted": 5, "passed": 5, "did_not_reach_done": 0, "mixed_host": 0,
                                            "resumed": 0, "seeded": 0, "process_not_observed": 0, "no_driver_recorded": 0,
                                            "no_result": 0})
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
                                            "resumed": 1, "seeded": 0, "process_not_observed": 0, "no_driver_recorded": 0,
                                            "no_result": 0})
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
        self.assertEqual(by["v1220-battleship-sonnet"]["plugin_version"], by["v1230-battleship-sonnet"]["plugin_version"])
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
        self.assertEqual(cell["overlap"], {"rows": 5, "overlapped_at_least": 4, "not_seen_overlapping": 1, "unknown": 0})  # v1220 ran alone
        self.assertEqual(self.cell(self.report(), case="checkers", host="claude")["overlap"],
                         {"rows": 3, "overlapped_at_least": 3, "not_seen_overlapping": 0, "unknown": 0})
        spanless = self.tmp / "rows.jsonl"
        spanless.write_text(json.dumps({"case": "battleship", "source": "checkout", "host": "claude",
                                        "model": "claude-sonnet-5-5", "effort": None, "planning_review": "stage",
                                        "prompt_sha256": self.cell(self.report(), **self.BATTLESHIP)["cell"]["prompt_sha256"],
                                        "verdicts": {"shiploop": True}, "termination": {"engine_status": "done"},
                                        "turns": 150, "cost_usd": 4.0, "output": "/gone/older", "pass": True}) + "\n")
        wider = self.cell(self.report(rows=spanless), **self.BATTLESHIP)
        self.assertEqual(wider["overlap"], {"rows": 6, "overlapped_at_least": 4, "not_seen_overlapping": 1, "unknown": 1})
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
        self.assertEqual(report["cells"][0]["overlap"], {"rows": 3, "overlapped_at_least": 2, "not_seen_overlapping": 1, "unknown": 0})

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
                                 "recomputed", "overlaps"]))
        cell = report["cells"][0]
        self.assertEqual(sorted(cell), ["attempts", "builds", "cell", "host_builds", "measures", "outputs", "overlap"])
        self.assertEqual(sorted(cell["cell"]), ["case", "effort", "host", "model", "planning_review", "prompt_sha256", "source"])
        self.assertEqual(sorted(cell["measures"]), ["cost_usd", "minutes", "planning_minutes", "turns"])
        self.assertEqual(sorted(cell["measures"]["cost_usd"]),
                         ["lower_bound_rows", "lower_bound_unknown_rows", "max", "median", "min", "n", "not_measured"])

    def test_the_text_report_states_facts_and_makes_no_claim_about_any_run(self):
        text = self.text()
        self.assertIn("cell battleship | checkout | claude | claude-sonnet-5-5 | effort - | planning_review stage | prompt ", text)
        self.assertIn("attempts   seen 5, counted 5, passed 5", text)
        self.assertIn("cost_usd   n=5 min 5.6749 median 5.8146 max 9.6543", text)
        self.assertIn("(lower bound in 1 of 1 rows)", text)
        self.assertIn("at least 4 of 5 rows overlapped another recorded run; 1 not seen to", text)
        for word in ("within", "above the", "below the", "regression", "outside the range"):
            self.assertNotIn(word, text)
        self.assertIn("a range across builds is not a noise estimate", text)

    def test_the_inputs_are_recorded_as_given_so_the_command_can_be_run_again(self):
        report = self.report()
        self.assertEqual(report["inputs"], {"baseline": str(self.ROWS), "runs": [str(self.RUNS)]})


RUNS_JSON = ROOT / "docs" / "experiments" / "baseline-spread-20261009" / "runs.json"


class RecordedLoopRunsTest(unittest.TestCase):
    """The committed output of `run.py --baseline-report --baseline test/shiploop_e2e/baselines.jsonl --runs
    /Users/dadleet/e2e-runs --json` over the baseline file and the 22 saved run folders of 2026-10-03 to 2026-10-08. This
    pins that file and never the live baselines.jsonl or the machine's run folders: the owner committing the four rows that
    lived in other worktrees, or deleting a run folder, must not turn a test red. To regenerate: run the command again and
    review the diff."""

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

    def test_35_attempts_in_15_cells_each_of_the_22_folders_and_the_23_rows_once(self):
        records = self.report["records"]
        self.assertEqual((len(records), len(self.report["cells"])), (35, 15))
        kinds = [r["record"] for r in records]
        self.assertEqual((kinds.count("file+folder"), kinds.count("folder"), kinds.count("file")), (13, 12, 10))
        self.assertEqual(kinds.count("file+folder") + kinds.count("file"), 23)  # every committed row, once
        classes = {c: sum(1 for r in records if r["class"] == c) for c in {r["class"] for r in records}}
        self.assertEqual(classes, {"counted": 15, "no driver recorded": 9, "did not reach done": 4, "resumed": 3,
                                   "no result.json": 3, "mixed host": 1})

    def test_the_loop_rows_three_of_seven_are_in_the_committed_file(self):
        in_file = {"r1-checkers-sonnet", "r3-battleship-sonnet", "r3-checkers-sonnet"}
        folder_only = {"r1-battleship-sonnet", "r1-battleship-grok-none", "r2-battleship-sonnet", "r2-checkers-sonnet"}
        for name in in_file:
            self.assertEqual(self.by_name[name]["record"], "file+folder", name)
        for name in folder_only:
            self.assertEqual(self.by_name[name]["record"], "folder", name)

    def test_sonnet_battleship_is_five_runs_on_five_plugin_trees_and_three_host_builds(self):
        cell = self.cell(case="battleship", host="claude")
        self.assertEqual((cell["attempts"]["seen"], cell["attempts"]["counted"], cell["attempts"]["passed"]), (5, 5, 5))
        self.assertEqual(len(cell["builds"]["plugin_sha256"]), 5)
        self.assertEqual(cell["host_builds"], {"2.1.291": 1, "2.1.292": 1, "2.1.294": 3, "unrecorded": 0})
        stats = lambda name: {k: cell["measures"][name][k] for k in ("n", "min", "median", "max")}  # noqa: E731
        self.assertEqual(stats("cost_usd"), {"n": 5, "min": 5.6749, "median": 5.8146, "max": 9.6543})
        self.assertEqual(stats("turns"), {"n": 5, "min": 197, "median": 207, "max": 294})
        self.assertEqual(stats("minutes"), {"n": 5, "min": 12.6, "median": 13.8, "max": 20.0})
        self.assertEqual(stats("planning_minutes"), {"n": 4, "min": 4.85, "median": 5.56, "max": 6.47})
        self.assertEqual(cell["measures"]["planning_minutes"]["not_measured"], 1)  # v1220 predates the planning block
        self.assertEqual(cell["overlap"], {"rows": 5, "overlapped_at_least": 4, "not_seen_overlapping": 1, "unknown": 0})

    def test_the_two_runs_that_said_plugin_1_22_0_are_two_builds_and_three_heads_are_one(self):
        # The "Sonnet cost rise, decomposed" entry explained 238 turns / $6.54 against 294 / $9.65 between two builds.
        a, b = self.by_name["v1220-battleship-sonnet"], self.by_name["v1230-battleship-sonnet"]
        self.assertEqual((a["plugin_version"], b["plugin_version"]), ("1.22.0", "1.22.0"))
        self.assertNotEqual(a["plugin_sha256"], b["plugin_sha256"])
        self.assertNotEqual(a["local_head"], b["local_head"])
        self.assertNotEqual(a["host_build"], b["host_build"])
        trio = {self.by_name[n]["plugin_sha256"] for n in ("r1-battleship-sonnet", "r1-checkers-sonnet", "r1-battleship-grok-none")}
        self.assertEqual(len(trio), 1, "byte-identical trees under three different heads")
        self.assertNotEqual(self.by_name["r1-battleship-sonnet"]["local_head"], self.by_name["r1-checkers-sonnet"]["local_head"])

    def test_sonnet_checkers_is_three_runs(self):
        cell = self.cell(case="checkers", host="claude")
        self.assertEqual({k: cell["measures"]["cost_usd"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 5.1613, "median": 6.6509, "max": 8.5146})
        self.assertEqual({k: cell["measures"]["turns"][k] for k in ("n", "min", "median", "max")},
                         {"n": 3, "min": 185, "median": 232, "max": 293})
        self.assertEqual(cell["overlap"], {"rows": 3, "overlapped_at_least": 3, "not_seen_overlapping": 0, "unknown": 0})

    def test_the_grok_cell_names_its_five_attempts_and_one_masked_prompt(self):
        cell = self.cell(case="custom", host="grok")
        self.assertEqual(cell["attempts"], {"seen": 5, "counted": 1, "passed": 1, "did_not_reach_done": 2, "mixed_host": 1,
                                            "resumed": 1, "seeded": 0, "process_not_observed": 0, "no_driver_recorded": 0,
                                            "no_result": 0})
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
