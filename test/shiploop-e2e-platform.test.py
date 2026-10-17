#!/usr/bin/env python3
"""No-model, no-platform checks for the E2E harness's `platform` hooks (test/shiploop_e2e/run.py).

A case may carry a `platform` object (preflight, before, cleanup, home_links); the harness runs the commands it names and knows
nothing about any platform. Here the commands are one tiny Python script written below, the hosts are fake `grok` and `claude`
executables, and no real platform, org or model is ever reached. They say nothing about a live platform.

  preflight  before any model call, with the host's environment: non-zero aborts
  before     once, on a fresh run only
  home_links symlinks of existing names in the real HOME into a throwaway HOME (Grok, Codex), recorded
  cleanup    after grading, always: success, failure, crash, KeyboardInterrupt; a failure is printed loudly
  model_bin  a guarded stand-in command written to <output>/platform/bin and put first on the host's PATH (real HOME inside),
             pinned first again in the throwaway HOME's shell startup files (path_helper) and checked per shell
  coverage   the guard's own log against the sf commands in the transcript: a run the guard never saw, or that went around the
             wrapper by a path, is an invalid trial
  keep       --keep-platform: a finished delivery is left in the platform, any other ending cleans as always, except a run that
             did not finish whose platform works (keep_checks pass, valid trial, no stop): kept, recorded NOT a pass, resumable
  resume_note a sentence for the prompt of a resumed run whose platform was reset (resume_note_kept: it was kept)
  check_timeout the ceiling of the case's own checks (60..3600 s, default 180), for that case only
  scrub      one function through which every stored or printed command output goes
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import environment  # noqa: E402
import hosts  # noqa: E402
import listeners  # noqa: E402
import run  # noqa: E402

TOKEN = "FAKE-TOKEN-DO-NOT-LOG"
SESSION = "00D5g000004AbCd!AQEAQFakeSessionTokenValue0123456789abcdefghijklmnop"

# The one platform command: records what it saw, one JSON line per call, and fails on demand (PLAT_FAIL=<verb>) with output
# that carries a credential, to show the harness never keeps it.
PLAT = f"""
import json, os, sys, time
verb = sys.argv[1]
home = os.environ["HOME"]
here = os.environ["E2E_PLATFORM_DIR"]
with open(os.environ["PLAT_LOG"], "a") as log:
    log.write(json.dumps({{"verb": verb, "home": home, "cwd": os.getcwd(), "platform_dir": here,
                          "checks": os.environ.get("E2E_CHECKS"), "path_head": os.environ.get("PATH", "").split(os.pathsep)[0],
                          "model_started": os.path.exists(os.environ["PLAT_MODEL_MARK"]),
                          "links": sorted(n for n in os.listdir(home) if os.path.islink(os.path.join(home, n)))}}) + "\\n")
if verb == "before":
    os.makedirs(here, exist_ok=True)
    with open(os.path.join(here, "before.json"), "w") as handle:
        json.dump({{"snapshot": True}}, handle)
if os.environ.get("PLAT_FAIL") == verb:
    print('boom {{"accessToken": "{TOKEN}"}} and {SESSION}')
    sys.exit(3)
print("ok " + verb)
"""

# The model_bin command: a stand-in for a CLI the model would run. It records what it saw (the real HOME, the baked variables).
# The sf wrapper of a coverage test: what checks/sf_guard.py logs for an allowed call (a decision line, then an end line).
GUARD_TOOL = """
import json, os, sys, time
log = os.path.join(os.environ["E2E_PLATFORM_DIR"], "sf-calls.jsonl")
call = "%08x" % (time.time_ns() & 0xffffffff)
with open(log, "a") as handle:
    handle.write(json.dumps({"ts": time.time(), "call": call, "org": "de", "prefix": "P", "argv": sys.argv[1:],
                             "decision": "allowed", "reason": "test"}) + "\\n")
    handle.write(json.dumps({"ts": time.time(), "call": call, "end": True, "exit": 0, "stderr_head": "", "interrupted": False}) + "\\n")
print("guard ok")
"""

TOOL = """
import json, os, sys
with open(os.environ["PLAT_LOG"], "a") as log:
    log.write(json.dumps({"verb": "tool", "argv": sys.argv[1:], "home": os.environ.get("HOME"),
                          "checks": os.environ.get("E2E_CHECKS"), "platform_dir": os.environ.get("E2E_PLATFORM_DIR"),
                          "bin_dir": os.environ.get("E2E_MODEL_BIN_DIR")}) + "\\n")
print("tool ok")
"""

PRODUCT = f"""
sys.path.insert(0, {str(ROOT / 'skills/shiploop/scripts')!r})
import shiploop_store as store
def product():
    Path("hello.py").write_text('print("Hello, world!")\\n')
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "done", "planning_review": "stage"}})
    Path(".shiploop/report.html").write_text("<html></html>")
    import subprocess
    Path(".gitignore").write_text(".shiploop/\\n")
    ident = ["-c", "user.name=Fake", "-c", "user.email=fake@example.invalid"]
    if not Path(".git").exists():
        subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "product"], check=True)
"""

# FAKE_MODE: done (product + done run), stuck (ends with ShipLoop active), blocked (ends with ShipLoop blocked), fail (exits 1 with
# no work), hang (never ends: the harness's --timeout does), stop (asks the harness to end the run, then never ends). Every start
# leaves PLAT_MODEL_MARK, so a platform command can say whether the model had started when it ran. A model that "shows" a
# credential puts it in its event stream, as a tool result would. FAKE_COMMANDS (a JSON list) is what its shell tool "ran".
FAKE_GROK = f"""#!{sys.executable}
import json, os, subprocess, sys, time
from pathlib import Path
{PRODUCT}
argv = sys.argv[1:]
home = Path(os.environ["HOME"])
registry = home / ".grok" / "fake-plugins.txt"
if argv[:2] == ["plugin", "install"]:
    registry.write_text(f"  skill-craft-1: skill-craft [local: {{Path(argv[2]).resolve()}}]\\n")
    print("Installed 1 plugin(s)")
    sys.exit(0)
if argv[:2] == ["plugin", "list"]:
    print(registry.read_text() if registry.exists() else "")
    sys.exit(0)
os.chdir(argv[argv.index("--cwd") + 1])
Path(os.environ["PLAT_MODEL_MARK"]).write_text("started")
Path(os.environ["PLAT_LOG"] + ".model").write_text(json.dumps({{"home": str(home), "links": sorted(
    n for n in os.listdir(home) if os.path.islink(os.path.join(home, n))), "path_head": os.environ["PATH"].split(os.pathsep)[0]}}))
print(json.dumps({{"type": "available_commands", "tools": [], "commands": ["shiploop", "improve"]}}))
print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": "python3 /x/skills/shiploop/scripts/shiploop next"}}}}))
for command in json.loads(os.environ.get("FAKE_COMMANDS", '["sf org display --json"]')):
    print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": command}}}}))
for _ in range(int(os.environ.get("FAKE_SF_CALLS", "0"))):  # the model reaching the guard: the first PATH folder holds the wrapper
    subprocess.run([os.environ["PATH"].split(os.pathsep)[0] + "/sf", "org", "list"], check=True, capture_output=True)
print(json.dumps({{"type": "text", "data": '{{"accessToken": "{TOKEN}"}}'}}))
mode = os.environ.get("FAKE_MODE")
if mode == "fail":
    sys.exit(1)
if mode == "done":
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)
    product()
elif mode in ("stuck", "blocked"):
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active" if mode == "stuck" else "blocked", "stage": "test-refine", "revision": 25}})
elif mode in ("hang", "stop"):
    if mode == "stop":
        Path("../stop").write_text("stop")  # the stop file sits beside the work folder, in the run's output folder
    time.sleep(60)
print(json.dumps({{"type": "end", "stopReason": "cancelled", "sessionId": "sess-1", "num_turns": 4, "total_cost_usd": 0.01}}))
"""

FAKE_CLAUDE = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
{PRODUCT}
argv = sys.argv[1:]
Path(os.environ["PLAT_MODEL_MARK"]).write_text("started")
Path(os.environ["PLAT_LOG"] + ".model").write_text(json.dumps({{"home": os.environ["HOME"], "path_head": os.environ["PATH"].split(os.pathsep)[0]}}))
plugin = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
print(json.dumps({{"type": "system", "subtype": "init", "model": "fake-model", "claude_code_version": "0.0.1-fake",
                  "slash_commands": ["skill-craft:shiploop"],
                  "plugins": [{{"name": "skill-craft", "path": plugin}}] if plugin else []}}), flush=True)
if os.environ.get("FAKE_MODE") == "done":
    product()
print(json.dumps({{"type": "result", "subtype": "success", "num_turns": 3, "total_cost_usd": 0.0, "result": "done"}}))
"""


class PlatformCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.fakes = {}
        for name, body in (("grok", FAKE_GROK), ("claude", FAKE_CLAUDE)):
            path = self.tmp / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
            self.fakes[name] = path
        (self.tmp / "plat.py").write_text(PLAT)
        (self.tmp / "tool.py").write_text(TOOL)
        (self.tmp / "guard_tool.py").write_text(GUARD_TOOL)
        self.plugin = self.tmp / "build" / "plugins" / "skill-craft"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "9.9.9"}))
        cli = self.plugin / "skills" / "shiploop" / "scripts" / "shiploop"
        cli.parent.mkdir(parents=True)
        cli.write_text("")
        self.baselines = self.tmp / "baselines.jsonl"
        self.plat_log = self.tmp / "plat.log"
        # The "real" HOME: it holds .sfdx (a name the case links) and no .sf, and is never the owner's.
        self.real_home = self.tmp / "real-home"
        (self.real_home / ".sfdx").mkdir(parents=True)
        (self.real_home / ".sfdx" / "alias.json").write_text("{}")
        auth = self.tmp / "auth.json"
        auth.write_text("{}")
        saved, hosts.GROK_AUTH = hosts.GROK_AUTH, auth
        self.addCleanup(setattr, hosts, "GROK_AUTH", saved)
        patched = mock.patch.dict(os.environ, {"HOME": str(self.real_home), "PLAT_LOG": str(self.plat_log),
                                               "PLAT_MODEL_MARK": str(self.tmp / "model-started")})
        patched.start()
        self.addCleanup(patched.stop)
        for var in ("PLAT_FAIL", "FAKE_MODE", "FAKE_SF_CALLS", "FAKE_COMMANDS"):
            self.addCleanup(os.environ.pop, var, None)
        for patch in (mock.patch.object(listeners, "observe", return_value=[]),
                      mock.patch.object(environment, "autodetect_browser", return_value=None)):
            patch.start()
            self.addCleanup(patch.stop)

    # ---- the case under test: hello's shape, a check that always passes, and a platform made of plat.py
    def command(self, verb: str) -> str:
        return f"{shlex.quote(sys.executable)} {shlex.quote(str(self.tmp / 'plat.py'))} {verb}"

    def platform(self, **override) -> dict:
        spec = {"kind": "test", "preflight": self.command("preflight"), "before": self.command("before"),
                "cleanup": self.command("cleanup"), "home_links": [".sfdx", ".sf"], "source": "this test"}
        spec.update(override)
        return {key: value for key, value in spec.items() if value is not None}

    def model_bin(self) -> dict:
        """A guarded command named `mytool` (it runs tool.py) and the preflight that proves it works from the host's PATH."""
        return {"mytool": f"{shlex.quote(sys.executable)} {shlex.quote(str(self.tmp / 'tool.py'))}"}

    def use_case(self, platform: dict | None, name: str = "plat") -> str:
        case = {"style": "smoke", "prompt": "Create hello.py.", "checks": ["true"], "checks_source": "this test"}
        if platform is not None:
            case["platform"] = platform
        path = self.tmp / "cases.json"
        path.write_text(json.dumps({name: case}))
        patched = mock.patch.object(run, "CASES", path)
        patched.start()
        self.addCleanup(patched.stop)
        return name

    def invoke(self, host: str, mode: str, *extra: str, name: str = "plat", tag: str = "a") -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = mode
        out = self.tmp / f"out-{host}-{tag}"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(out), "--case", name,
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def resume(self, host: str, out: Path, mode: str, *extra: str, ci: str = "success") -> tuple[dict, str]:
        os.environ["FAKE_MODE"] = mode
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
                    "shiploop_version": None, "unreleased": [], "ci": ci}
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", host, f"--{host}-bin", str(self.fakes[host]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--max-resumes", "0", *extra])
        return json.loads((out / "result.json").read_text()), printed.getvalue()

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.plat_log.read_text().splitlines()] if self.plat_log.exists() else []

    def verbs(self) -> list[str]:
        return [call["verb"] for call in self.calls()]

    def model_started(self) -> bool:
        return (self.tmp / "model-started").exists()

    def credential_files(self, folder: Path) -> list[str]:
        """Every file under the run folder, apart from the model's own profile, that holds the token."""
        found = []
        for path in sorted(folder.rglob("*")):
            if "home" in path.relative_to(folder).parts[:1] or not path.is_file() or path.is_symlink():
                continue
            if TOKEN.encode() in path.read_bytes() or SESSION.encode() in path.read_bytes():
                found.append(str(path.relative_to(folder)))
        return found


class ScrubTest(unittest.TestCase):
    def test_the_value_of_each_credential_key_is_replaced_in_every_shape_it_arrives_in(self):
        for key in run.SECRET_KEYS:
            for text in (f'{{"{key}": "{TOKEN}"}}', f'{{"{key}":"{TOKEN}","x":1}}', f'\\"{key}\\": \\"{TOKEN}\\"',
                         f"{key}: {TOKEN}", f"{key}={TOKEN}", f"'{key}': '{TOKEN}'"):
                with self.subTest(key=key, text=text):
                    clean = run.scrub(text)
                    self.assertNotIn(TOKEN, clean)
                    self.assertIn(run.REDACTED, clean)
                    self.assertIn(key, clean)

    def test_a_session_token_is_replaced_wherever_it_appears(self):
        clean = run.scrub(f"Access Token   {SESSION}\nbearer {SESSION}.")
        self.assertNotIn("AQEAQ", clean)
        self.assertEqual(clean.count(run.REDACTED), 2)

    def test_text_without_a_credential_is_returned_unchanged_and_scrubbing_is_idempotent(self):
        plain = '{"status": 0, "result": {"records": [{"Name": "SLChessEngine"}], "totalSize": 1}}\n  › Warning: update available'
        self.assertEqual(run.scrub(plain), plain)
        once = run.scrub(f'{{"accessToken": "{TOKEN}", "refreshToken": "{SESSION}"}}')
        self.assertEqual(run.scrub(once), once)
        self.assertEqual(run.scrub(None), "")

    def test_only_the_value_goes_and_the_text_around_it_stays(self):
        self.assertEqual(run.scrub(f'{{"alias": "de", "accessToken": "{TOKEN}", "apiVersion": "68.0"}}'),
                         '{"alias": "de", "accessToken": "[redacted]", "apiVersion": "68.0"}')

    def test_scrub_files_rewrites_a_record_that_holds_one_and_leaves_the_rest_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            (folder / "events.jsonl").write_text(json.dumps({"data": f'{{"accessToken": "{TOKEN}"}}'}) + "\n")
            clean = folder / "clean.txt"
            clean.write_bytes(b"caf\xc3\xa9 \xff\xfe not text\n")
            (folder / "sub").mkdir()
            (folder / "sub" / "kept.txt").write_text(TOKEN)
            self.assertEqual(run.scrub_files(folder), ["events.jsonl"])
            self.assertNotIn(TOKEN, (folder / "events.jsonl").read_text())
            json.loads((folder / "events.jsonl").read_text())  # still one valid line
            self.assertEqual(clean.read_bytes(), b"caf\xc3\xa9 \xff\xfe not text\n")
            self.assertEqual((folder / "sub" / "kept.txt").read_text(), TOKEN)  # only the folder's own files


class SchemaTest(unittest.TestCase):
    def test_a_malformed_platform_is_refused_with_every_problem_named(self):
        for bad, words in (({"cleanup": ""}, "cleanup"), ({"before": "x"}, "before without cleanup"),
                           ({"preflight": 3}, "preflight"), ({"home_links": [".sf/x"]}, "home_links"),
                           ({"home_links": [".."]}, "home_links"), ({"home_links": ".sf"}, "home_links"), ("text", "object"),
                           ({"model_bin": ["sf"]}, "model_bin"), ({"model_bin": {"a/b": "x"}}, "model_bin"),
                           ({"model_bin": {"sf": ""}}, "model_bin"), ({"model_bin": {"sf": 3}}, "model_bin"),
                           ({"model_bin": {"": "x"}}, "model_bin")):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", bad)
            self.assertIn(words, str(raised.exception))

    def test_a_check_timeout_is_a_whole_number_of_seconds_from_a_minute_to_an_hour(self):
        for bad in (59, 0, -1, 3601, 86400, "900", 900.5, 900.0, True, None, [900]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", {"cleanup": "c", "check_timeout": bad})
            self.assertIn("check_timeout must be an integer number of seconds from 60 to 3600", str(raised.exception))
        for good in (60, 180, 900, 3600):
            with self.subTest(good=good):
                spec = {"cleanup": "c", "check_timeout": good}
                self.assertIs(run.validate_platform("c", spec), spec)
        self.assertEqual(run.validate_platform("c", {"cleanup": "c"}), {"cleanup": "c"}, "a case without one is as it was")

    def test_a_well_formed_platform_is_returned_as_given(self):
        spec = {"kind": "k", "preflight": "p", "before": "b", "cleanup": "c", "home_links": [".sf"], "org": "x",
                "model_bin": {"sf": "guard --org x"}}
        self.assertIs(run.validate_platform("c", spec), spec)

    def test_keep_checks_and_the_kept_resume_note_are_validated_at_load(self):
        for bad in ([], "deployed", ["deployed", "deployed"], ["two words"], [""], [3], ["deployed", None], None, {"a": 1}):
            with self.subTest(keep_checks=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", {"cleanup": "c", "keep_checks": bad})
            self.assertIn("keep_checks must be a non-empty list of distinct words", str(raised.exception))
        for bad in ("", "  ", 3, ["x"], None):
            with self.subTest(resume_note_kept=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", {"cleanup": "c", "resume_note_kept": bad})
            self.assertIn("resume_note_kept must be a non-empty string", str(raised.exception))
        spec = {"cleanup": "c", "keep_checks": ["deployed", "tests"], "resume_note_kept": "still there"}
        self.assertIs(run.validate_platform("c", spec), spec)

    def test_a_keep_word_must_name_exactly_one_of_the_cases_checks_before_any_model_starts(self):
        checks = ['python3 "$E2E_CHECKS/x.py" project --org de', 'python3 "$E2E_CHECKS/x.py" deployed --org de',
                  'python3 "$E2E_CHECKS/x.py" tests --org de --min-tests 8']
        run.refuse_unmatched_keep_checks("c", {"keep_checks": ["deployed", "tests"]}, checks)
        run.refuse_unmatched_keep_checks("c", {"cleanup": "c"}, checks)
        run.refuse_unmatched_keep_checks("c", None, checks)
        for words, why in ((["rules"], "'rules' names 0"), (["deployed", "--org"], "'--org' names 3"), (["min"], "'min' names 0")):
            with self.subTest(words=words), self.assertRaises(SystemExit) as raised:
                run.refuse_unmatched_keep_checks("c", {"keep_checks": words}, checks)
            self.assertIn(why, str(raised.exception))
            self.assertIn("'c'", str(raised.exception))
        # a word is matched whole, so `--min-tests` names the one command that holds it and `min` names none
        run.refuse_unmatched_keep_checks("c", {"keep_checks": ["--min-tests"]}, checks)


class CommandTest(PlatformCase):
    def test_a_command_reports_its_exit_and_a_scrubbed_tail_of_its_output(self):
        done = run.run_platform_command("echo " + shlex.quote('{"accessToken": "' + TOKEN + '"}') + "; echo second; exit 4",
                                        self.tmp, dict(os.environ))
        self.assertEqual((done["returncode"], done["ok"]), (4, False))
        self.assertNotIn(TOKEN, done["output"])
        self.assertIn("second", done["output"])
        long = run.run_platform_command("python3 -c 'print(\"x\" * 5000)'", self.tmp, dict(os.environ))
        self.assertLessEqual(len(long["output"]), run.PLATFORM_TAIL)

    def test_a_command_that_never_ends_is_killed_at_its_ceiling_with_its_children(self):
        began = time.time()
        done = run.run_platform_command("sleep 60 & sleep 60", self.tmp, dict(os.environ), timeout=1)
        self.assertLess(time.time() - began, 20)
        self.assertEqual((done["returncode"], done["ok"]), (None, False))
        self.assertIn("timeout after 1s", done["output"])

    def test_one_ctrl_c_is_waited_out_and_a_second_abandons_the_command(self):
        class Interrupted:
            def __init__(self, interrupts):
                self.pid, self.returncode, self.interrupts = 0, 0, interrupts

            def communicate(self, timeout=None):
                if self.interrupts:
                    self.interrupts -= 1
                    raise KeyboardInterrupt
                return "finished\n", None

        for interrupts, ok in ((1, True), (2, False)):
            with self.subTest(interrupts=interrupts), contextlib.redirect_stdout(io.StringIO()) as printed, \
                    mock.patch.object(run.subprocess, "Popen", return_value=Interrupted(interrupts)):
                done = run.run_platform_command("cleanup", self.tmp, {})
            self.assertEqual(done["ok"], ok, done)
            self.assertIn("waiting for the platform command", printed.getvalue())
            if not ok:
                self.assertIn("abandoned", done["output"])


class HomeLinkTest(PlatformCase):
    def test_only_names_that_exist_are_linked_and_each_name_is_recorded(self):
        throwaway = self.tmp / "throwaway"
        throwaway.mkdir()
        records = run.link_homes([".sfdx", ".sf"], {"HOME": str(throwaway)})
        self.assertEqual(records, [{"name": ".sfdx", "linked": True, "target": str(self.real_home / ".sfdx")},
                                   {"name": ".sf", "linked": False, "reason": "absent from the real HOME"}])
        self.assertEqual(os.readlink(throwaway / ".sfdx"), str(self.real_home / ".sfdx"))
        self.assertFalse(os.path.lexists(throwaway / ".sf"))

    def test_the_contents_of_a_linked_folder_are_never_read(self):
        secret = self.real_home / ".sf"
        secret.mkdir()
        (secret / "key").write_text("x")
        secret.chmod(0)
        self.addCleanup(secret.chmod, stat.S_IRWXU)
        throwaway = self.tmp / "throwaway"
        throwaway.mkdir()
        self.assertTrue(run.link_homes([".sf"], {"HOME": str(throwaway)})[0]["linked"])

    def test_linking_twice_is_the_same_and_a_name_already_there_is_not_replaced(self):
        throwaway = self.tmp / "throwaway"
        throwaway.mkdir()
        first = run.link_homes([".sfdx"], {"HOME": str(throwaway)})
        self.assertEqual(run.link_homes([".sfdx"], {"HOME": str(throwaway)}), first)
        (throwaway / ".sf").mkdir()
        (self.real_home / ".sf").mkdir()
        record = run.link_homes([".sf"], {"HOME": str(throwaway)})[0]
        self.assertFalse(record["linked"])
        self.assertFalse((throwaway / ".sf").is_symlink())

    def test_a_host_on_the_real_home_needs_no_links(self):
        records = run.link_homes([".sfdx", ".sf"], {"HOME": str(self.real_home)})
        self.assertEqual([r["linked"] for r in records], [False, False])
        self.assertEqual({r["reason"] for r in records}, {"the host runs in the real HOME"})
        self.assertFalse(any(path.is_symlink() for path in self.real_home.iterdir()))


class RunTest(PlatformCase):
    def test_a_good_run_orders_preflight_before_model_and_cleanup_and_records_all_of_it(self):
        self.use_case(self.platform())
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])
        preflight, before, cleanup = self.calls()
        self.assertFalse(preflight["model_started"])
        self.assertFalse(before["model_started"])
        self.assertTrue(cleanup["model_started"], "cleanup runs after the model, not before")
        out = Path(result["output"])
        # The host's environment for preflight (the throwaway HOME, where the link must already be); the harness's for the rest.
        self.assertEqual(Path(preflight["home"]), out / "home")
        self.assertEqual(preflight["links"], [".sfdx"])
        self.assertEqual(Path(before["home"]), self.real_home)
        self.assertEqual(Path(cleanup["home"]), self.real_home)
        for call in (preflight, before, cleanup):
            self.assertEqual(Path(call["platform_dir"]), out / "platform")
            self.assertEqual(Path(call["checks"]), Path(run.HERE) / "checks")
            self.assertEqual(Path(call["cwd"]).resolve(), out.resolve())
        # What the model could reach, recorded, and what it actually saw.
        self.assertEqual(json.loads(Path(str(self.plat_log) + ".model").read_text())["links"], [".sfdx"])
        links = [{"name": ".sfdx", "linked": True, "target": str(self.real_home / ".sfdx")},
                 {"name": ".sf", "linked": False, "reason": "absent from the real HOME"}]
        block = result["platform"]
        self.assertEqual(block["home_links"], links)
        self.assertEqual(result["environment"]["platform_home_links"], links)
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["home_links"], links)
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["spec"], self.platform())
        self.assertTrue(block["preflight"]["ok"] and block["before"]["ok"] and block["cleanup"]["ok"])
        self.assertTrue((out / "platform" / "before.json").is_file())
        self.assertTrue(result["pass"])
        self.assertIn("  platform  PASS  cleanup ran; home links .sfdx", printed)
        self.assertTrue(os.path.islink(out / "home" / ".sfdx"))

    def test_a_failing_preflight_aborts_before_the_model_and_runs_no_other_hook(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "preflight"
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.invoke("grok", "done")
        self.assertEqual(self.verbs(), ["preflight"])
        self.assertFalse(self.model_started())
        message = str(refused.exception)
        self.assertIn("preflight refused", message)
        self.assertIn("boom", message)
        out = self.tmp / "out-grok-a"
        stub = json.loads((out / "result.json").read_text())
        self.assertFalse(stub["pass"])
        self.assertTrue(stub["platform"]["refused"])
        self.assertEqual(self.credential_files(out), [])
        self.assertNotIn(TOKEN, message)
        self.assertNotIn(SESSION, message)

    def test_a_failing_before_aborts_before_the_model_and_there_is_nothing_to_clean(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "before"
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.invoke("grok", "done")
        self.assertEqual(self.verbs(), ["preflight", "before"])
        self.assertFalse(self.model_started())
        self.assertIn("before command failed", str(refused.exception))
        self.assertEqual(self.credential_files(self.tmp / "out-grok-a"), [])

    def test_cleanup_runs_after_a_run_whose_model_failed(self):
        self.use_case(self.platform())
        code, result, _ = self.invoke("grok", "fail")
        self.assertEqual(code, 1)
        self.assertFalse(result["process"]["pass"])
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])
        self.assertTrue(result["platform"]["cleanup"]["ok"])

    def test_cleanup_runs_after_a_run_whose_checks_fail(self):
        self.use_case(self.platform())
        code, result, _ = self.invoke("grok", "stuck")
        self.assertEqual(code, 1)
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])

    def test_cleanup_runs_when_the_harness_itself_raises_after_the_model_started(self):
        self.use_case(self.platform())
        for tag, exception in (("boom", RuntimeError("boom")), ("ctrl-c", KeyboardInterrupt())):
            with self.subTest(exception=type(exception).__name__):
                self.plat_log.unlink(missing_ok=True)
                with mock.patch.object(run, "summarize_events", side_effect=exception), \
                        contextlib.redirect_stdout(io.StringIO()), self.assertRaises(type(exception)):
                    self.invoke("grok", "done", tag=tag)
                self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])
                recorded = json.loads((self.tmp / f"out-grok-{tag}" / "platform" / "cleanup-record.json").read_text())
                self.assertTrue(recorded["ran"] and recorded["ok"])

    def test_cleanup_runs_when_the_harness_exits_after_the_model_started(self):
        self.use_case(self.platform())
        with mock.patch.object(run, "summarize_events", side_effect=SystemExit("stop")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            self.invoke("grok", "done")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])

    def test_a_failed_cleanup_is_loud_recorded_scrubbed_and_fails_the_run(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"], "the product is right, but the platform was left dirty")
        cleanup = result["platform"]["cleanup"]
        self.assertEqual((cleanup["ran"], cleanup["ok"], cleanup["returncode"]), (True, False, 3))
        self.assertIn("PLATFORM CLEANUP FAILED", printed)
        out = Path(result["output"])
        # The exact command to rerun, with the folders it needs.
        self.assertIn(f"E2E_PLATFORM_DIR={shlex.quote(str(out / 'platform'))}", printed)
        self.assertIn(self.command("cleanup"), printed)
        self.assertIn(run.REDACTED, cleanup["output"])
        self.assertNotIn(TOKEN, printed)
        self.assertNotIn(SESSION, printed)
        self.assertEqual(self.credential_files(out), [])
        self.assertIn("platform", (out / "mismatch.md").read_text())

    def test_the_model_s_credential_in_its_event_stream_and_the_checks_is_not_kept(self):
        self.use_case(self.platform())
        # The check prints the credential but does not contain it, so only its output could leak it.
        half = len(TOKEN) // 2
        printing = 'python3 -c "print(\'{\\"accessToken\\": \\"%s\' + \'%s\\"}\')"' % (TOKEN[:half], TOKEN[half:])
        cases = json.loads(run.CASES.read_text())
        cases["plat"]["checks"] = [printing]
        run.CASES.write_text(json.dumps(cases))
        code, result, printed = self.invoke("grok", "done")
        out = Path(result["output"])
        self.assertEqual(self.credential_files(out), [])
        self.assertNotIn(TOKEN, printed)
        self.assertIn(run.REDACTED, (out / "events.jsonl").read_text())
        self.assertIn(run.REDACTED, result["checks"][0]["output"])

    def test_a_claude_host_on_the_real_home_links_nothing_and_says_so(self):
        self.use_case(self.platform())
        code, result, _ = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        preflight = self.calls()[0]
        self.assertEqual(Path(preflight["home"]), self.real_home)
        self.assertEqual(preflight["links"], [])
        self.assertEqual({link["reason"] for link in result["platform"]["home_links"]}, {"the host runs in the real HOME"})
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])

    def test_a_case_without_a_platform_is_unchanged(self):
        self.use_case(None)
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(self.verbs(), [])
        self.assertNotIn("platform", result)
        self.assertNotIn("platform_home_links", result["environment"])
        self.assertNotIn("platform", json.loads((Path(result["output"]) / "invocation.json").read_text()))
        self.assertNotIn("platform", printed)
        self.assertFalse((Path(result["output"]) / "platform").exists())

    def test_a_custom_prompt_never_has_a_platform(self):
        self.use_case(self.platform())
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "out-custom"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out), "--prompt", "x",
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(self.verbs(), [])


class ModelBinTest(PlatformCase):
    """platform.model_bin: a wrapper per name in <output>/platform/bin, first on the host's PATH (and on the preflight's), run with the
    real HOME and the baked E2E_* variables. Only the cases that name it get any of this."""

    def with_bin(self, **override) -> dict:
        probe = self.model_bin()
        spec = self.platform(model_bin=probe, home_links=None, **override)
        spec["preflight"] = f"mytool probe && {self.command('preflight')}"
        return spec

    def tool_calls(self) -> list[dict]:
        return [call for call in self.calls() if call["verb"] == "tool"]

    def test_the_wrapper_is_written_first_on_the_hosts_path_and_the_preflight_runs_through_it(self):
        self.use_case(self.with_bin())
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        out = Path(result["output"])
        wrapper = out / "platform" / "bin" / "mytool"
        self.assertTrue(wrapper.is_file() and os.access(wrapper, os.X_OK))
        text = wrapper.read_text()
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        self.assertIn(f"HOME={shlex.quote(str(self.real_home))}", text)
        self.assertTrue(text.rstrip().endswith('"$@"'))
        # The preflight (the host's environment) found the wrapper first on its PATH and ran it, with the real HOME.
        tool, preflight, before, cleanup = self.calls()
        self.assertEqual((tool["verb"], preflight["verb"]), ("tool", "preflight"))
        self.assertEqual(tool["argv"], ["probe"])
        self.assertEqual(Path(tool["home"]), self.real_home)
        self.assertEqual(Path(preflight["home"]), out / "home", "the platform command itself still ran in the host's HOME")
        self.assertEqual(Path(preflight["path_head"]), out / "platform" / "bin")
        # The model's launch has it too; the harness's own before and cleanup do not (they must reach the real CLI).
        self.assertEqual(Path(json.loads(Path(str(self.plat_log) + ".model").read_text())["path_head"]), out / "platform" / "bin")
        self.assertNotEqual(Path(before["path_head"]), out / "platform" / "bin")
        self.assertNotEqual(Path(cleanup["path_head"]), out / "platform" / "bin")
        # Recorded: names and the wrapper path only.
        recorded = {"mytool": str(wrapper)}
        self.assertEqual(result["platform"]["model_bin"], recorded)
        self.assertEqual(result["environment"]["platform_model_bin"], recorded)
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["model_bin"], recorded)
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["spec"]["model_bin"], self.model_bin())
        self.assertIn("guarded commands mytool", printed)
        self.assertTrue(result["pass"])
        self.assertEqual(self.credential_files(out), [])

    def test_the_wrapper_needs_nothing_from_the_model_s_environment(self):
        self.use_case(self.with_bin())
        _, result, _ = self.invoke("grok", "done")
        out = Path(result["output"])
        before = len(self.tool_calls())
        env = {"PATH": "/usr/bin:/bin", "PLAT_LOG": str(self.plat_log), "HOME": str(out / "home")}  # no E2E_* and a throwaway HOME
        done = subprocess.run([str(out / "platform" / "bin" / "mytool"), "a", "b c"], env=env, capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "tool ok"), done.stderr)
        call = self.tool_calls()[before]
        self.assertEqual(call["argv"], ["a", "b c"])
        self.assertEqual(Path(call["home"]), self.real_home)
        self.assertEqual(Path(call["checks"]), Path(run.HERE) / "checks")
        self.assertEqual(Path(call["platform_dir"]), out / "platform")
        self.assertEqual(Path(call["bin_dir"]), out / "platform" / "bin")

    def test_a_claude_host_gets_the_same_path_and_the_wrapper(self):
        self.use_case(self.with_bin())
        code, result, _ = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        out = Path(result["output"])
        self.assertEqual(Path(json.loads(Path(str(self.plat_log) + ".model").read_text())["path_head"]), out / "platform" / "bin")
        self.assertEqual(self.tool_calls()[0]["argv"], ["probe"])

    def test_a_failing_wrapper_refuses_the_run_before_the_model_starts(self):
        spec = self.with_bin()
        spec["model_bin"] = {"mytool": "false"}
        self.use_case(spec)
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.invoke("grok", "done")
        self.assertIn("preflight refused", str(refused.exception))
        self.assertFalse(self.model_started())
        self.assertEqual(self.verbs(), [])

    def test_preflight_only_runs_the_preflight_through_the_wrapper(self):
        self.use_case(self.with_bin())
        out = self.tmp / "pf"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})):
            code = run.main(["--preflight-only", "--case", "plat", "--output", str(out), "--host", "grok",
                             "--grok-bin", str(self.fakes["grok"])])
        self.assertEqual(code, 0, printed.getvalue())
        self.assertEqual(self.verbs(), ["tool", "preflight"])
        self.assertTrue((out / "grok" / "platform" / "bin" / "mytool").is_file())
        self.assertEqual(Path(self.calls()[1]["path_head"]), out / "grok" / "platform" / "bin")
        self.assertIn("mytool", json.loads((out / "grok" / "preflight.json").read_text())["platform"]["model_bin"])
        self.assertEqual(json.loads((out / "grok" / "preflight.json").read_text())["platform"]["model_bin_resolution"],
                         {"ok": True, "problems": []})

    def test_a_resume_writes_the_wrapper_again_and_a_regrade_restates_it(self):
        self.use_case(self.with_bin())
        code, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        (out / "platform" / "bin" / "mytool").unlink()
        result, _ = self.resume("grok", out, "done")
        self.assertTrue((out / "platform" / "bin" / "mytool").is_file(), "the resumed model runs behind the wrapper too")
        self.assertEqual(Path(json.loads(Path(str(self.plat_log) + ".model").read_text())["path_head"]), out / "platform" / "bin")
        calls = self.calls()
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(regraded["platform"]["model_bin"], result["platform"]["model_bin"])
        self.assertEqual(self.calls(), calls)

    def test_a_platform_without_model_bin_is_unchanged(self):
        self.use_case(self.platform())
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        out = Path(result["output"])
        self.assertNotIn("model_bin", result["platform"])
        self.assertNotIn("platform_model_bin", result["environment"])
        self.assertNotIn("model_bin", json.loads((out / "invocation.json").read_text())["platform"])
        self.assertFalse((out / "platform" / "bin").exists())
        self.assertNotIn("guarded commands", printed)
        for call in self.calls():
            self.assertNotEqual(Path(call["path_head"]), out / "platform" / "bin")
        self.assertNotEqual(Path(json.loads(Path(str(self.plat_log) + ".model").read_text())["path_head"]), out / "platform" / "bin")


class ResumeTest(PlatformCase):
    def test_a_resume_does_not_snapshot_again_and_cleans_again_at_its_end(self):
        self.use_case(self.platform())
        code, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        self.assertEqual(code, 1)
        out = Path(first["output"])
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])
        (out / "platform" / "before.json").write_text('{"snapshot": "the first run\'s"}')
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "preflight", "cleanup"],
                         "preflight and cleanup again; no second before")
        self.assertEqual(json.loads((out / "platform" / "before.json").read_text()), {"snapshot": "the first run's"})
        block = result["platform"]
        self.assertTrue(block["before"]["ok"], "the first invocation's snapshot record is restated")
        self.assertTrue(block["cleanup"]["ok"])
        self.assertEqual(len(block["earlier_cleanups"]), 1)
        self.assertTrue(result["pass"], result)

    def test_a_resume_on_an_unclean_platform_is_refused_without_replacing_the_result(self):
        self.use_case(self.platform())
        self.invoke("grok", "stuck", "--max-resumes", "0")
        out = self.tmp / "out-grok-a"
        kept = (out / "result.json").read_text()
        os.environ["PLAT_FAIL"] = "preflight"
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", out, "done")
        self.assertEqual((out / "result.json").read_text(), kept)
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "preflight"], "no cleanup: no model ran")


class RegradeTest(PlatformCase):
    def test_a_regrade_of_a_cleaned_run_starts_nothing_and_restates_the_checks_made_while_deployed(self):
        self.use_case(self.platform())
        self.invoke("grok", "done")
        out = self.tmp / "out-grok-a"
        before = json.loads((out / "result.json").read_text())
        calls = self.calls()
        cases = json.loads(run.CASES.read_text())
        cases["plat"]["checks"] = ["false"]  # asking the platform now would find nothing there
        run.CASES.write_text(json.dumps(cases))
        result, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.calls(), calls, "no preflight, before or cleanup for a run already cleaned")
        self.assertEqual(result["checks"], before["checks"])
        self.assertTrue(result["pass"], result)
        self.assertIn("checks_restated", result["platform"])

    def test_a_regrade_of_a_run_whose_cleanup_failed_cleans_it(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        self.invoke("grok", "done")
        out = self.tmp / "out-grok-a"
        del os.environ["PLAT_FAIL"]
        result, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "cleanup"])
        self.assertTrue(result["platform"]["cleanup"]["ok"])
        self.assertTrue(result["pass"], result)


class PreflightOnlyTest(PlatformCase):
    def preflight_only(self, *extra: str) -> tuple[int, Path, str]:
        out = self.tmp / "pf"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})):
            code = run.main(["--preflight-only", "--case", "plat", "--output", str(out), *extra])
        return code, out, printed.getvalue()

    def test_preflight_only_runs_the_case_s_platform_preflight_and_nothing_else(self):
        self.use_case(self.platform())
        code, out, printed = self.preflight_only("--host", "grok", "--grok-bin", str(self.fakes["grok"]))
        self.assertEqual(code, 0, printed)
        self.assertEqual(self.verbs(), ["preflight"])
        self.assertEqual(self.calls()[0]["links"], [".sfdx"])
        record = json.loads((out / "grok" / "preflight.json").read_text())
        self.assertTrue(record["platform"]["preflight"]["ok"])
        self.assertIn("platform preflight (grok): OK", printed)
        self.assertFalse(self.model_started())

    def test_a_failing_platform_preflight_refuses_preflight_only(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "preflight"
        code, out, printed = self.preflight_only("--host", "claude", "--claude-bin", str(self.fakes["claude"]))
        self.assertEqual(code, 1)
        self.assertIn("platform preflight (claude): REFUSED", printed)
        self.assertNotIn(TOKEN, printed)
        self.assertNotIn(SESSION, printed)
        self.assertEqual(self.credential_files(out), [])

    def test_a_case_without_a_platform_preflights_as_before(self):
        self.use_case(None)
        code, out, printed = self.preflight_only("--host", "claude", "--claude-bin", str(self.fakes["claude"]))
        self.assertEqual(code, 0, printed)
        self.assertNotIn("platform", json.loads((out / "claude" / "preflight.json").read_text()))
        self.assertNotIn("platform preflight", printed)


class ShellTest(PlatformCase):
    """The shells the model may start (a login shell runs macOS path_helper, which puts /opt/homebrew/bin ahead of the PATH the host
    was launched with) must find the wrapper first. Only `command -v` is ever run against a name: nothing here executes a wrapper."""

    def folders(self) -> tuple[Path, Path, Path]:
        """(home, bin, decoy): a throwaway home, a wrapper folder holding `e2etool` and a decoy folder holding another one."""
        home, bin_dir, decoy = self.tmp / "throwaway", self.tmp / "wrappers", self.tmp / "decoy"
        for folder in (home, bin_dir, decoy):
            folder.mkdir()
        for folder in (bin_dir, decoy):
            tool = folder / "e2etool"
            tool.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(self.tmp / 'executed'))}\n")
            tool.chmod(0o755)
        return home, bin_dir, decoy

    def env(self, home: Path, *folders: Path) -> dict:
        return {"HOME": str(home), "PATH": os.pathsep.join([*map(str, folders), "/usr/bin", "/bin"])}

    def installed(self) -> list[tuple[str, str]]:
        return [shell for shell in run.RESOLUTION_SHELLS if os.access(shell[0], os.X_OK)]

    def simulate_path_helper(self, home: Path, decoy: Path) -> None:
        """What /etc/zprofile and /etc/profile do before the user's own startup files: a folder put ahead of the host's PATH."""
        for name in (".zprofile", ".bash_profile", ".profile"):
            (home / name).write_text(f'export PATH={shlex.quote(str(decoy))}":$PATH"\n')


class PinTest(ShellTest):
    def test_the_five_startup_files_get_the_path_line_in_a_throwaway_home_and_none_in_the_real_one(self):
        home, bin_dir, _ = self.folders()
        written = run.pin_shell_path(home, bin_dir, self.real_home)
        self.assertEqual(written, [".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile"])
        for name in written:
            text = (home / name).read_text()
            self.assertIn(run.PIN_MARK, text)
            self.assertIn(f"PATH={shlex.quote(str(bin_dir))}\":$PATH\"\nexport PATH\n", text)
        self.assertEqual(sorted(path.name for path in self.real_home.iterdir()), [".sfdx"], "the real home gained nothing")

    def test_a_second_call_changes_nothing_and_a_file_that_exists_keeps_its_content(self):
        home, bin_dir, _ = self.folders()
        (home / ".zprofile").write_text("export KEEP=1")  # no trailing newline
        first = run.pin_shell_path(home, bin_dir, self.real_home)
        snapshot = {name: (home / name).read_bytes() for name in first}
        self.assertTrue(snapshot[".zprofile"].startswith(b"export KEEP=1\n" + run.PIN_MARK.encode()))
        self.assertEqual(run.pin_shell_path(home, bin_dir, self.real_home), first)
        self.assertEqual({name: (home / name).read_bytes() for name in first}, snapshot)
        self.assertEqual(snapshot[".zprofile"].count(run.PIN_MARK.encode()), 1)

    def test_the_real_home_is_never_written_whatever_way_it_is_spelled(self):
        home, bin_dir, _ = self.folders()
        link = self.tmp / "real-home-link"
        link.symlink_to(self.real_home)
        before = sorted(path.name for path in self.real_home.iterdir())
        for spelling in (self.real_home, link, self.real_home / ".sfdx" / "..", self.real_home / ".." / "real-home"):
            with self.subTest(spelling=str(spelling)):
                self.assertEqual(run.pin_shell_path(spelling, bin_dir, self.real_home), [])
        self.assertEqual(sorted(path.name for path in self.real_home.iterdir()), before)

    def test_a_startup_file_that_is_a_link_to_the_real_home_is_not_written_through(self):
        home, bin_dir, _ = self.folders()
        real_rc = self.real_home / ".zshrc"
        real_rc.write_text("# the owner's own\n")
        (home / ".zshrc").symlink_to(real_rc)
        written = run.pin_shell_path(home, bin_dir, self.real_home)
        self.assertNotIn(".zshrc", written)
        self.assertEqual(real_rc.read_text(), "# the owner's own\n")
        self.assertIn(".zprofile", written)


class ResolutionTest(ShellTest):
    def test_a_decoy_ahead_of_the_wrapper_is_a_problem_in_every_shell_and_the_right_order_is_none(self):
        home, bin_dir, decoy = self.folders()
        shells = self.installed()
        self.assertTrue(shells, "/bin/sh exists on any machine this runs on")
        wrong = run.shell_resolution_problems(["e2etool"], bin_dir, self.env(home, decoy, bin_dir))
        self.assertEqual(len(wrong), len(shells), wrong)
        for (shell, flag), problem in zip(shells, wrong):
            self.assertIn(f"`{shell} {flag}`", problem)
            self.assertIn(str(decoy / "e2etool"), problem)
            self.assertIn(str(bin_dir / "e2etool"), problem)
        self.assertEqual(run.shell_resolution_problems(["e2etool"], bin_dir, self.env(home, bin_dir, decoy)), [])
        self.assertFalse((self.tmp / "executed").exists(), "command -v never runs the command")

    def test_one_problem_per_name_and_a_name_that_is_nowhere_resolves_to_nothing(self):
        home, bin_dir, _ = self.folders()
        problems = run.shell_resolution_problems(["e2etool", "absent"], bin_dir, self.env(home, bin_dir))
        self.assertEqual(len(problems), len(self.installed()))
        self.assertTrue(all("`absent` resolves to nothing" in problem for problem in problems))

    def test_a_shell_that_is_not_installed_is_skipped_and_one_that_hangs_is_a_problem(self):
        home, bin_dir, _ = self.folders()
        env = self.env(home, bin_dir)
        with mock.patch.object(run, "RESOLUTION_SHELLS", (("/bin/no-such-shell", "-c"), ("/bin/sh", "-c"))):
            self.assertEqual(run.shell_resolution_problems(["e2etool"], bin_dir, env), [])
            with mock.patch.object(run.subprocess, "run", side_effect=subprocess.TimeoutExpired("sh", 1)):
                problems = run.shell_resolution_problems(["e2etool"], bin_dir, env)
        self.assertEqual(len(problems), 1)
        self.assertIn("did not answer", problems[0])

    def test_a_login_shell_that_reorders_the_path_is_found_out_and_the_pin_puts_the_wrapper_back(self):
        home, bin_dir, decoy = self.folders()
        login = [shell for shell in self.installed() if "l" in shell[1]]
        if not login:
            self.skipTest("no login shell installed")
        self.simulate_path_helper(home, decoy)
        env = self.env(home, bin_dir)
        unpinned = run.shell_resolution_problems(["e2etool"], bin_dir, env)
        self.assertEqual(len(unpinned), len(login), unpinned)
        for problem in unpinned:
            self.assertIn(str(decoy / "e2etool"), problem)
            self.assertTrue(any(f"`{shell} {flag}`" in problem for shell, flag in login), problem)
        run.pin_shell_path(home, bin_dir, self.real_home)
        self.assertEqual(run.shell_resolution_problems(["e2etool"], bin_dir, env), [])
        self.assertFalse((self.tmp / "executed").exists())


class OwnShellTest(ShellTest):
    """H-7: a login `sh` and the host's own $SHELL are shells the model may start too."""

    def own_shell(self) -> Path:
        shell = self.tmp / "ownsh"
        shell.write_text('#!/bin/sh\nexec /bin/sh "$@"\n')
        shell.chmod(0o755)
        return shell

    def test_a_login_sh_is_among_the_shells_checked(self):
        self.assertIn(("/bin/sh", "-lc"), run.RESOLUTION_SHELLS)
        self.assertIn(("/bin/sh", "-lc"), run.resolution_shells({}))

    def test_the_hosts_own_shell_is_checked_login_and_interactive_when_it_is_none_of_the_listed_ones(self):
        shell = self.own_shell()
        self.assertEqual(run.resolution_shells({"SHELL": str(shell)})[len(run.RESOLUTION_SHELLS):],
                         [(str(shell), "-lc"), (str(shell), "-ilc")])
        for env in ({}, {"SHELL": ""}, {"SHELL": "/bin/zsh"}, {"SHELL": "/bin/bash"}, {"SHELL": str(self.tmp / "no-such-shell")},
                    {"SHELL": str(self.tmp)}):  # absent, empty, already listed, not there, not executable
            with self.subTest(env=env):
                self.assertEqual(run.resolution_shells(env), list(run.RESOLUTION_SHELLS))

    def test_a_wrapper_that_the_hosts_own_shell_does_not_find_first_is_a_problem(self):
        home, bin_dir, decoy = self.folders()
        shell = self.own_shell()
        env = dict(self.env(home, decoy, bin_dir), SHELL=str(shell))
        problems = run.shell_resolution_problems(["e2etool"], bin_dir, env)
        for flag in ("-lc", "-ilc"):
            self.assertTrue(any(f"`{shell} {flag}`" in problem for problem in problems), (flag, problems))
        self.assertEqual(run.shell_resolution_problems(["e2etool"], bin_dir, dict(self.env(home, bin_dir, decoy), SHELL=str(shell))), [])
        self.assertFalse((self.tmp / "executed").exists(), "command -v never runs the command")


class ShellPreflightTest(ShellTest):
    def host(self, name: str = "grok") -> tuple[dict, Path]:
        out = self.tmp / f"pf-{name}"
        out.mkdir()
        return dict(os.environ, HOME=str(out / "home")), out

    def test_a_resolution_problem_fails_the_preflight_and_the_cases_own_command_is_not_run(self):
        env, out = self.host()
        (out / "home").mkdir()
        spec = self.platform(model_bin=self.model_bin(), home_links=None)
        with mock.patch.object(run, "shell_resolution_problems", return_value=["`mytool` resolves to /x/mytool under `/bin/zsh -lc`"]):
            state = run.platform_preflight(spec, env, out)
        self.assertEqual(self.calls(), [], "the case's preflight command was not run")
        self.assertEqual((state["preflight"]["ok"], state["preflight"]["returncode"], state["preflight"]["command"]),
                         (False, 1, "model_bin shell resolution"))
        self.assertIn("resolves to /x/mytool", state["preflight"]["output"])
        self.assertEqual(state["model_bin_resolution"], {"ok": False, "problems": ["`mytool` resolves to /x/mytool under `/bin/zsh -lc`"]})
        self.assertEqual(state["shell_path_pinned"], [".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile"])
        self.assertNotIn("guard_log_preflight", state)
        self.assertFalse((out / "platform" / run.PREFLIGHT_RANGES).exists(), "no preflight ran, so there is no range to record")

    def test_a_good_resolution_is_recorded_and_the_cases_command_runs_behind_it(self):
        env, out = self.host()
        (out / "home").mkdir()
        state = run.platform_preflight(self.platform(model_bin=self.model_bin(), home_links=None), env, out)
        self.assertEqual(state["model_bin_resolution"], {"ok": True, "problems": []})
        self.assertTrue(state["preflight"]["ok"])
        self.assertNotIn("guard_log_preflight", state, "the range is the preflight's own file, not a field of each invocation's record")
        self.assertEqual((out / "platform" / run.PREFLIGHT_RANGES).read_text(), "[0, 0]\n", "no wrapper call: no guard-log line")
        self.assertEqual(run.preflight_ranges(out), [(0, 0)])
        self.assertEqual(self.verbs(), ["preflight"])

    def test_a_case_without_a_model_bin_pins_nothing_and_checks_nothing(self):
        env, out = self.host()
        (out / "home").mkdir()
        with mock.patch.object(run, "shell_resolution_problems", side_effect=AssertionError("checked")):
            state = run.platform_preflight(self.platform(), env, out)
        for key in ("shell_path_pinned", "model_bin_resolution", "guard_log_preflight", "model_bin"):
            self.assertNotIn(key, state)
        self.assertFalse((out / "platform" / run.PREFLIGHT_RANGES).exists(), "no wrapper, no range")
        self.assertEqual(os.listdir(out / "home"), [".sfdx"])

    def with_bin(self) -> dict:
        spec = self.platform(model_bin=self.model_bin(), home_links=None)
        spec["preflight"] = f"mytool probe && {self.command('preflight')}"
        return spec

    def test_a_run_records_the_pin_and_the_resolution_and_pins_only_the_throwaway_home(self):
        self.use_case(self.with_bin())
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        out = Path(result["output"])
        pinned = [".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile"]
        self.assertEqual(result["platform"]["shell_path_pinned"], pinned)
        self.assertEqual(result["platform"]["model_bin_resolution"], {"ok": True, "problems": []})
        self.assertEqual(json.loads((out / "invocation.json").read_text())["platform"]["shell_path_pinned"], pinned)
        for name in pinned:
            self.assertIn(str(out / "platform" / "bin"), (out / "home" / name).read_text())
        self.assertEqual(sorted(path.name for path in self.real_home.iterdir()), [".sfdx"])

    def test_a_resume_pins_again_and_the_resumed_host_launches_behind_the_wrapper(self):
        self.use_case(self.with_bin())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        for name in first["platform"]["shell_path_pinned"]:
            (out / "home" / name).unlink()
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(result["platform"]["shell_path_pinned"], first["platform"]["shell_path_pinned"])
        self.assertTrue((out / "home" / ".zprofile").is_file(), "the pin was written again for the resumed launch")
        self.assertEqual(Path(json.loads(Path(str(self.plat_log) + ".model").read_text())["path_head"]), out / "platform" / "bin")

    def test_a_regrade_restates_the_pin_and_the_resolution_without_checking_again(self):
        self.use_case(self.with_bin())
        _, first, _ = self.invoke("grok", "done")
        with mock.patch.object(run, "shell_resolution_problems", side_effect=AssertionError("checked")):
            regraded, _ = self.resume("grok", Path(first["output"]), "done", "--grade-only")
        for key in ("shell_path_pinned", "model_bin_resolution"):
            self.assertEqual(regraded["platform"][key], first["platform"][key])

    def test_a_resume_whose_shells_no_longer_find_the_wrapper_is_refused_and_leaves_the_result_alone(self):
        self.use_case(self.with_bin())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        kept = (out / "result.json").read_text()
        calls = self.calls()
        self.plat_log.with_name("plat.log.model").unlink()
        problem = "`mytool` resolves to /x/mytool under `/bin/zsh -lc`, not to the wrapper"
        with mock.patch.object(run, "shell_resolution_problems", return_value=[problem]), \
                self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", out, "done")
        self.assertIn("preflight refused", str(refused.exception))
        self.assertIn(problem, str(refused.exception))
        self.assertEqual((out / "result.json").read_text(), kept)
        self.assertEqual(self.calls(), calls, "neither the probe, the preflight nor a cleanup ran")
        self.assertFalse(self.plat_log.with_name("plat.log.model").exists(), "no model started")

    def refusing_real_home(self) -> None:
        """A Claude host runs in the real home: nothing is pinned there, and a login shell whose startup files put a decoy ahead of
        the wrapper must refuse the run rather than let the model reach the real command."""
        decoy = self.tmp / "decoy"
        decoy.mkdir()
        tool = decoy / "mytool"
        tool.write_text("#!/bin/sh\n")
        tool.chmod(0o755)
        self.simulate_path_helper(self.real_home, decoy)
        if not [shell for shell in self.installed() if "l" in shell[1]]:
            self.skipTest("no login shell installed")

    def test_a_host_on_the_real_home_whose_login_shell_reorders_the_path_is_refused_before_any_model(self):
        self.use_case(self.with_bin())
        self.refusing_real_home()
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.invoke("claude", "done")
        message = str(refused.exception)
        self.assertIn("preflight refused", message)
        self.assertIn("not to the wrapper", message)
        self.assertFalse(self.model_started())
        self.assertEqual(self.verbs(), [], "neither the probe nor the case's preflight ran")
        stub = json.loads((self.tmp / "out-claude-a" / "result.json").read_text())
        self.assertFalse(stub["pass"])
        self.assertEqual(stub["platform"]["shell_path_pinned"], [], "nothing was written into the real home")
        self.assertFalse(stub["platform"]["model_bin_resolution"]["ok"])
        self.assertEqual(sorted(path.name for path in self.real_home.iterdir()), [".bash_profile", ".profile", ".sfdx", ".zprofile"])

    def test_preflight_only_refuses_the_same_run_and_names_the_shells(self):
        self.use_case(self.with_bin())
        self.refusing_real_home()
        out = self.tmp / "pf"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})):
            code = run.main(["--preflight-only", "--case", "plat", "--output", str(out), "--host", "claude",
                             "--claude-bin", str(self.fakes["claude"])])
        self.assertEqual(code, 1)
        self.assertIn("platform preflight (claude): REFUSED", printed.getvalue())
        self.assertIn("-lc", printed.getvalue())
        record = json.loads((out / "claude" / "preflight.json").read_text())["platform"]
        self.assertFalse(record["model_bin_resolution"]["ok"])
        self.assertEqual(self.verbs(), [])


# The command ShipLoop's `workspace start` is run with on every ShipLoop run of the Salesforce case (run 1, shortened): the case prompt
# is an argument, and it names `sf` commands in prose, with the quote idiom of a prompt that holds an apostrophe.
WORKSPACE_START = (
    'SKILL_ROOT="/x/live1/home/.grok/installed-plugins/skill-craft-e56c8527/skills/shiploop"\n'
    'CLI="$SKILL_ROOT/scripts/shiploop"\n'
    'REPO="/x/live1/work"\n'
    'python3 "$CLI" workspace start --repo "$REPO" --delivery-contract --prompt=\'Deploy with `sf project deploy start --target-org de` '
    'and run the tests with `sf apex run test --target-org de`; never run `sf org display`. Cover fool\'"\'"\'s mate and stalemate. '
    'Do not stop until the tests pass.\'')
# A ShipLoop note written through a python heredoc (run 1): sf appears in prose inside the body, with an apostrophe in it.
NOTES_HEREDOC = (
    "python3 << 'PY'\nfrom pathlib import Path\nPath('notes/lifecycle.md').write_text(\"\"\"# Lifecycle\n"
    "- Operation: `sf project deploy start --target-org de`, then it's `sf org list` once.\n\"\"\")\nPY")


class ModelCommandTest(PlatformCase):
    """What the transcript shows the model ran, against what the guard logged."""

    def events(self, *events) -> Path:
        path = self.tmp / "events.jsonl"
        path.write_text("".join((event if isinstance(event, str) else json.dumps(event)) + "\n" for event in events))
        return path

    def commands(self, *commands: str) -> Path:
        return self.events(*({"rawInput": {"command": command}} for command in commands))

    def test_sf_is_found_in_a_command_whatever_the_host_calls_the_event(self):
        for label, event in (
                ("grok", {"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {"command": "sf org list --json"}}),
                ("claude", {"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "HOME=/Users/x sf apex run --file a.apex"}}]}}),
                ("codex", {"type": "tool_call", "toolName": "run_terminal_command",
                           "rawInput": {"command": "/bin/zsh -lc 'cd w && sfdx force:org:list'"}}),
                ("codex-list", {"type": "tool_call", "rawInput": {"cmd": ["bash", "-lc", "sf data query -q x"]}})):
            with self.subTest(label):
                found = run.model_sf_commands(self.events(event))
                self.assertEqual(len(found), 1, found)

    def test_the_forms_the_model_runs_sf_in_are_all_accepted(self):
        for command in ("sf org list", "cd w && sf project deploy start -o de", "HOME=/Users/x sf apex run", "sfdx force:org:list",
                        'python3 -c \'import subprocess; subprocess.run(["sf", "data", "query"])\'',
                        "subprocess.run(['sfdx', 'x'])", "/opt/homebrew/bin/sf org list", "/opt/homebrew/bin/sfdx", "echo x | sf --help",
                        'ORGS="$(sf org list --json)"', "ORGS=$(sf org list --json)", "echo `sf org list`", "sf",
                        "for c in A B; do sf apex run test --class-names $c; done", "if sf org list; then echo ok; fi",
                        "env -i FOO=1 sf org list", "timeout 60 sf org list", "time sf org list", "command sf org list",
                        "exec sf org list", "nohup sf org list &", "xargs sf org list", '"sf" org list', "$(command -v sf) org list",
                        'eval "sf org list"', "bash -c 'echo hi; sf org list'", "sf org list --json > out.json 2>err.txt",
                        "sf \\\n  org list", "git commit -m \"$(cat <<'EOF'\nfix\nEOF\n)\" && sf org list",
                        "cat <<EOF > notes.txt\nsf org list\nEOF\nsf org list"):
            with self.subTest(command=command):
                self.assertTrue(run.model_sf_commands(self.commands(command)), command)

    def test_a_command_that_only_mentions_sf_and_text_outside_a_command_are_not_counted(self):
        events = self.events(
            {"rawInput": {"command": "ls -la"}}, {"rawInput": {"command": "cat sf-calls.jsonl"}},
            {"rawInput": {"command": "python3 /x/transforms.py"}}, {"rawInput": {"command": "echo asf org"}},
            {"rawInput": {"command": "/opt/homebrew/bin/sfx --help"}},
            {"type": "text", "data": "I will run sf org list now"}, {"type": "user", "message": {"content": "use sf org list"}},
            {"rawInput": {"command": ["ls", 3]}}, "not json at all", "[1, 2, 3]", '{"half": ')
        self.assertEqual(run.model_sf_commands(events), [])
        self.assertEqual(run.model_sf_commands(self.tmp / "missing.jsonl"), [])

    def test_the_prompt_a_note_a_lookup_and_a_comment_name_sf_without_running_it(self):
        """Run 1: every ShipLoop run starts with `workspace start --prompt='<case prompt>'`, which names sf commands, and a note
        written through a heredoc does too. None of these starts sf (H-1), though each one holds the words `sf org list` or
        `sf project deploy start`."""
        for command in (WORKSPACE_START, NOTES_HEREDOC, 'command -v sf || echo "sf missing"', "which sf", "type -p sf",
                        "# sf version without org\nls", "echo sf org list", "grep -r 'sf org' .", "cat <<'EOF'\nsf org list\nEOF",
                        'cat <<< "sf org list"', "git commit -m 'sf deploy'", "cd sf && ls", "ls /opt/homebrew/bin/sf",
                        "echo $(date) sf org list", "printf '%s' \"sf org list\" | wc -c", "FOO=sf true", "export SF_ORG=de"):
            with self.subTest(command=command[:60]):
                self.assertEqual(run.sf_words(command), [])
        self.assertEqual(run.model_sf_commands(self.commands(WORKSPACE_START, NOTES_HEREDOC)), [])

    def test_a_real_call_beside_such_text_is_counted_once_and_by_the_word_that_ran_it(self):
        for command in (WORKSPACE_START + "\nsf org list --json", NOTES_HEREDOC + "\nHOME=/x sf org list",
                        "command -v sf && sf version", 'echo "sf missing"; /opt/homebrew/bin/sf version'):
            with self.subTest(command=command[-40:]):
                self.assertEqual(len(run.sf_words(command)), 1, run.sf_words(command))
        self.assertEqual(run.sf_words(NOTES_HEREDOC + "\nHOME=/x sf org list"), ["sf"])
        self.assertEqual(run.sf_words('echo "sf missing"; /opt/homebrew/bin/sf version'), ["/opt/homebrew/bin/sf"])
        # a python heredoc that calls sf through subprocess is a call, by the list form, with its path when it has one
        body = "python3 << 'PY'\nimport subprocess\nsubprocess.run([\"/opt/homebrew/bin/sf\", \"org\", \"list\"])\nPY"
        self.assertEqual(run.sf_words(body), ["/opt/homebrew/bin/sf"])

    def test_text_the_shell_scanner_cannot_close_does_not_hang_or_raise(self):
        for command in ("echo 'unclosed", 'echo "unclosed $(sf org list', "cat <<EOF\nnever closed", "a <<- 'X'\n\tbody\n\tX\nsf x", "`unclosed",
                        "$(", "\\", "<<", "<<<", "()", ";;|&"):
            with self.subTest(command=command[:30]):
                self.assertIsInstance(run.sf_words(command), list)
        self.assertEqual(run.sf_words("a <<- 'X'\n\tbody sf org list\n\tX\nsf x"), ["sf"], "the tab-indented terminator ends the body")

    def test_the_same_command_in_a_call_and_its_update_is_counted_once(self):
        call = {"type": "tool_call", "rawInput": {"command": "sf org list"}}
        found = run.model_sf_commands(self.events(call, dict(call, type="tool_call_update"), {"rawInput": {"command": "sfdx x"}}))
        self.assertEqual(found, ["sf org list", "sfdx x"])

    def test_a_command_that_starts_sf_by_a_path_outside_the_wrapper_goes_around_it(self):
        bin_dir = self.tmp / "run" / "platform" / "bin"
        for command, direct in (
                ("/opt/homebrew/bin/sf org list", True), ("HOME=/Users/x ~/.local/share/sf/client/bin/sf apex run", True),
                ("cd w && /usr/local/bin/sfdx force:org:list", True), ("./node_modules/.bin/sf org list", True),
                ("$HOME/.local/share/sf/client/bin/sf org list", True), ("'/opt/homebrew/bin/sf' org list", True),
                ("python3 -c 'import subprocess; subprocess.run([\"/opt/homebrew/bin/sf\", \"org\"])'", True),
                (f"{bin_dir}/sf org list", False), (f"{bin_dir}/../bin/sf org list", False), ("sf org list", False),
                ("$(command -v sf) org list", False), ("ls /opt/homebrew/bin/sf", False), ("command -v /opt/homebrew/bin/sf", False),
                ("bash -lc 'cd w && /opt/homebrew/bin/sf org list'", True)):
            with self.subTest(command=command):
                self.assertEqual(bool(run.direct_sf_commands(self.commands(command), bin_dir)), direct)

    def test_coverage_counts_calls_not_end_lines_and_not_any_invocations_preflight(self):
        out = self.tmp / "run"
        (out / "platform").mkdir(parents=True)
        log = [{"call": "p", "decision": "allowed"}, {"call": "p", "end": True, "exit": 0},  # the first invocation's preflight
               {"call": "a", "decision": "allowed"}, {"call": "a", "end": True, "exit": 0},
               {"call": "b", "decision": "denied"},
               {"call": "q", "decision": "allowed"}, {"call": "q", "end": True, "exit": 0},  # a resume's preflight
               {"call": "c", "decision": "allowed"}]  # c was cut off: no end line
        (out / "platform" / "sf-calls.jsonl").write_text("".join(json.dumps(line) + "\n" for line in log) + "not json\n")
        (out / "events.jsonl").write_text(json.dumps({"rawInput": {"command": "sf org list"}}) + "\n")
        self.assertEqual(run.guard_coverage(out, [(0, 2), (5, 7)]),
                         {"model_sf_commands": 1, "guard_calls": 3, "direct_sf_commands": 0, "bypassed": False})
        self.assertEqual(run.guard_coverage(out, [(0, 2)])["guard_calls"], 4, "a resume's preflight call, left in, would be counted")
        self.assertEqual(run.guard_log_lines(out), 9)

    def test_coverage_flags_a_bypass_only_when_commands_exist_and_the_guard_saw_none(self):
        out = self.tmp / "run"
        (out / "platform").mkdir(parents=True)
        (out / "platform" / "sf-calls.jsonl").write_text(json.dumps({"call": "p", "decision": "allowed"}) + "\n"
                                                           + json.dumps({"call": "p", "end": True}) + "\n")
        (out / "events.jsonl").write_text(json.dumps({"rawInput": {"command": "sf org list"}}) + "\n")
        self.assertEqual(run.guard_coverage(out, [(0, 2)]),
                         {"model_sf_commands": 1, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": True})
        self.assertFalse(run.guard_coverage(out, [])["bypassed"], "counted from the start the preflight's call is a guard call")
        (out / "events.jsonl").write_text(json.dumps({"rawInput": {"command": "ls"}}) + "\n")
        self.assertEqual(run.guard_coverage(out, [(0, 2)]),
                         {"model_sf_commands": 0, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": False})
        (out / "platform" / "sf-calls.jsonl").unlink()
        self.assertEqual(run.guard_coverage(out, []), {"model_sf_commands": 0, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": False})

    def test_a_direct_call_is_a_bypass_in_its_own_right_even_when_the_guard_saw_other_calls(self):
        out = self.tmp / "run"
        (out / "platform").mkdir(parents=True)
        (out / "platform" / "sf-calls.jsonl").write_text(json.dumps({"call": "a", "decision": "allowed"}) + "\n")
        (out / "events.jsonl").write_text(json.dumps({"rawInput": {"command": "sf org list"}}) + "\n"
                                          + json.dumps({"rawInput": {"command": "/opt/homebrew/bin/sf data query -q x"}}) + "\n"
                                          + json.dumps({"rawInput": {"command": f"{out}/platform/bin/sf org list"}}) + "\n")
        coverage = run.guard_coverage(out, [])
        self.assertEqual(coverage, {"model_sf_commands": 3, "guard_calls": 1, "direct_sf_commands": 1, "bypassed": True})
        self.assertEqual(len(run.bypass_lines(coverage)), 1)
        self.assertIn("by a path outside the wrapper", run.bypass_lines(coverage)[0])
        unseen = run.bypass_lines(dict(coverage, direct_sf_commands=0, guard_calls=0))
        self.assertEqual(len(unseen), 1)
        self.assertIn("saw no model call", unseen[0])
        self.assertEqual(run.bypass_lines(dict(coverage, direct_sf_commands=0)), [], "a guarded call and no direct one: nothing to say")

    def test_each_preflight_appends_the_range_of_log_lines_it_wrote_to_one_file(self):
        out = self.tmp / "run"
        (out / "platform").mkdir(parents=True)
        ranges = out / "platform" / run.PREFLIGHT_RANGES
        ranges.write_text("[0, 2]\n[4, 6]\n[\"x\", 1]\n[1]\n{\"a\": 1}\n7\nnot json\n\n[8, 9]\n")
        self.assertEqual(run.preflight_ranges(out), [(0, 2), (4, 6), (8, 9)], "a line that is not a pair of integers is skipped")
        self.assertEqual(run.preflight_ranges(self.tmp / "nowhere"), [])
        # the invocation records no longer carry it: a record that is written only after a gate cannot be what the count rests on
        (out / "invocation.json").write_text(json.dumps({"platform": {"guard_log_preflight": [20, 22]}}))
        self.assertEqual(run.preflight_ranges(out), [(0, 2), (4, 6), (8, 9)])


class CoverageRunTest(PlatformCase):
    """An sf wrapper in a run: the guard log against the (fake) model's transcript, which shows one `sf org display` command unless a
    test says what the model ran (FAKE_COMMANDS)."""

    def sf_case(self, **override) -> dict:
        spec = self.platform(model_bin={"sf": f"{shlex.quote(sys.executable)} {shlex.quote(str(self.tmp / 'guard_tool.py'))}"},
                             home_links=None, **override)
        spec["preflight"] = f"sf probe && {self.command('preflight')}"
        return spec

    def baseline_rows(self) -> list[dict]:
        return [json.loads(line) for line in self.baselines.read_text().splitlines()] if self.baselines.exists() else []

    def test_a_model_that_reached_the_guard_passes_and_the_run_says_what_the_guard_saw(self):
        self.use_case(self.sf_case())
        os.environ["FAKE_SF_CALLS"] = "2"
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        block = result["platform"]
        self.assertEqual(block["guard_log_preflight_ranges"], [[0, 2]], "the preflight's own probe: a decision and an end line")
        self.assertNotIn("guard_log_preflight", block, "the ranges are the preflights' own file; the result carries all of them")
        self.assertEqual(block["guard_coverage"], {"model_sf_commands": 1, "guard_calls": 2, "direct_sf_commands": 0, "bypassed": False})
        out = Path(result["output"])
        self.assertEqual((out / "platform" / run.PREFLIGHT_RANGES).read_text(), "[0, 2]\n")
        self.assertNotIn("guard_log_preflight", json.loads((out / "invocation.json").read_text())["platform"])
        self.assertIn("  platform  PASS  cleanup ran;", printed)
        self.assertIn("guard saw 2 model calls (transcript shows 1 sf-looking commands)", printed)
        self.assertNotIn("invalid trial", printed)
        self.assertEqual(len(self.baseline_rows()), 1, "a valid finished trial is a baseline row")

    def test_a_model_the_guard_never_saw_is_an_invalid_trial_that_fails_the_run_and_is_no_baseline_row(self):
        self.use_case(self.sf_case())
        code, result, printed = self.invoke("grok", "done")  # the fake model's transcript shows `sf org display` and never calls the wrapper
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"], "everything else about the run is right")
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 1, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": True})
        self.assertTrue(result["platform"]["cleanup"]["ok"])
        self.assertIn("  platform  FAIL  cleanup ran;", printed)
        self.assertIn("guard saw 0 model calls (transcript shows 1 sf-looking commands)", printed)
        self.assertIn("the guard saw no model call although the transcript shows 1 sf-looking commands", printed)
        self.assertIn("an invalid trial, not a ShipLoop verdict", printed)
        self.assertIn("guard", (Path(result["output"]) / "mismatch.md").read_text())
        # H-5: not a ShipLoop verdict, so not FAILED and not a row that later same-cell comparisons would read
        self.assertIsNone(result["outcome_class"])
        self.assertTrue(result["outcome_basis"].startswith("invalid trial: the guard saw no model call"), result["outcome_basis"])
        self.assertEqual(self.baseline_rows(), [])
        self.assertIn("baseline  nothing compared: an invalid trial", printed)

    def test_a_run_whose_prompt_and_notes_only_mention_sf_is_not_flagged(self):
        """H-1: the run ends before the model's first guarded call; the commands it did run are the case prompt and a note."""
        self.use_case(self.sf_case())
        os.environ["FAKE_COMMANDS"] = json.dumps([WORKSPACE_START, NOTES_HEREDOC, 'command -v sf || echo "sf missing"'])
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 0, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": False})
        self.assertTrue(result["pass"])
        self.assertNotIn("invalid trial", printed)
        self.assertEqual(result["outcome_class"], "PASS")
        self.assertEqual(len(self.baseline_rows()), 1)

    def test_a_model_that_runs_the_real_cli_by_a_path_after_a_guarded_call_is_an_invalid_trial(self):
        """H-3: the guard saw a call, and the model then went around the wrapper."""
        self.use_case(self.sf_case())
        os.environ["FAKE_SF_CALLS"] = "1"
        os.environ["FAKE_COMMANDS"] = json.dumps(["sf org list", "/opt/homebrew/bin/sf data query -q x"])
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 1)
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 2, "guard_calls": 1, "direct_sf_commands": 1, "bypassed": True})
        self.assertFalse(result["pass"])
        self.assertIn("1 by a path outside the wrapper", printed)
        self.assertIn("the model started sf by a path outside the wrapper in 1 sf-looking commands", printed)
        self.assertNotIn("saw no model call", printed)
        self.assertEqual(self.baseline_rows(), [])
        self.assertIn("by a path outside the wrapper", (Path(result["output"]) / "mismatch.md").read_text())

    def test_a_platform_whose_wrappers_are_not_sf_has_no_coverage(self):
        self.use_case(self.platform(model_bin=self.model_bin(), home_links=None, preflight=None))
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertNotIn("guard_coverage", result["platform"])
        self.assertEqual(result["platform"]["guard_log_preflight_ranges"], [[0, 0]])
        self.assertNotIn("guard saw", printed)

    def test_a_resume_s_own_preflight_calls_are_not_the_model_s(self):
        """H-2: each invocation's preflight calls the wrapper; only the model's calls count, on a resumed run too."""
        self.use_case(self.sf_case())
        os.environ["FAKE_SF_CALLS"] = "1"
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        self.assertEqual(first["platform"]["guard_coverage"]["guard_calls"], 1)
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(result["platform"]["guard_log_preflight_ranges"], [[0, 2], [4, 6]], "one range per invocation")
        self.assertEqual((out / "platform" / run.PREFLIGHT_RANGES).read_text(), "[0, 2]\n[4, 6]\n")
        # the first model call and the resumed model's call: the resume preflight's probe is not one
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 1, "guard_calls": 2, "direct_sf_commands": 0, "bypassed": False})
        self.assertTrue(result["pass"], result)

    def test_a_resume_refused_after_its_preflight_still_has_its_probe_out_of_the_model_s_calls(self):
        """R2-H-1: the version gate refuses a resume after its preflight called the wrapper and before any invocation record is
        written; the next resume must not count that probe as a model call and hide a model that never reached the guard."""
        self.use_case(self.sf_case())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")  # the fake model's transcript shows sf; it never calls the wrapper
        out = Path(first["output"])
        # The marketplace gate applies to a run that started on the marketplace install (a checkout run is exempt: ResumeGateTest).
        recorded = json.loads((out / "invocation.json").read_text())
        recorded["versions"]["source"] = "marketplace"
        (out / "invocation.json").write_text(json.dumps(recorded))
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", out, "done", ci="failure")
        self.assertIn("origin/main's CI failed", str(refused.exception))
        self.assertEqual(list(out.glob("invocation-resume-*.json")), [], "refused before the invocation record")
        self.assertEqual(run.preflight_ranges(out), [(0, 2), (2, 4)], "the refused resume's probe has its range all the same")
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(result["platform"]["guard_log_preflight_ranges"], [[0, 2], [2, 4], [4, 6]])
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 1, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": True})
        self.assertFalse(result["pass"])

    def test_a_preflight_that_fails_still_records_its_range(self):
        """R2-H-1: the range is recorded as the preflight ends, whether it passed or not."""
        self.use_case(self.sf_case())
        os.environ["PLAT_FAIL"] = "preflight"
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            self.invoke("grok", "done")
        self.assertEqual(run.preflight_ranges(self.tmp / "out-grok-a"), [(0, 2)])
        del os.environ["PLAT_FAIL"]

    def test_a_resumed_model_that_bypasses_the_guard_completely_is_found_out(self):
        self.use_case(self.sf_case())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        self.assertTrue(first["platform"]["guard_coverage"]["bypassed"])
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(result["platform"]["guard_coverage"],
                         {"model_sf_commands": 1, "guard_calls": 0, "direct_sf_commands": 0, "bypassed": True},
                         "the resume's own preflight probe must not read as a model call")
        self.assertFalse(result["pass"])

    def test_a_regrade_grades_the_bypass_again_from_what_is_on_disk(self):
        self.use_case(self.sf_case())
        _, first, _ = self.invoke("grok", "done")
        out = Path(first["output"])
        self.assertFalse(first["pass"])
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertTrue(regraded["platform"]["guard_coverage"]["bypassed"])
        self.assertFalse(regraded["pass"])
        # a run that recorded no preflight range is not judged
        (out / "platform" / run.PREFLIGHT_RANGES).unlink()
        old, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertNotIn("guard_coverage", old["platform"])
        self.assertTrue(old["pass"], old)


class KeepPlatformTest(PlatformCase):
    """--keep-platform: a finished delivery is left in the platform for a person to use; every other ending cleans as it always did."""

    CLEANED = ["preflight", "before", "cleanup"]
    KEPT = {"ran": False, "ok": True, "kept": True, "reason": "--keep-platform"}

    def argv(self, *extra: str, tag: str = "a", mode: str = "done", host: str = "grok") -> list[str]:
        os.environ["FAKE_MODE"] = mode
        return ["--host", host, f"--{host}-bin", str(self.fakes[host]), "--output", str(self.tmp / f"out-{host}-{tag}"), "--case", "plat",
                "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra]

    def go(self, *extra: str, tag: str = "a", mode: str = "done") -> tuple[int, str, Path]:
        """One run of the harness without invoke's read of result.json; (exit code, printed, output folder)."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(self.argv(*extra, tag=tag, mode=mode))
        return code, printed.getvalue(), self.tmp / f"out-grok-{tag}"

    def result(self, out: Path) -> dict:
        return json.loads((out / "result.json").read_text())

    def test_it_is_refused_where_there_is_no_platform_to_keep(self):
        self.use_case(None)
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            self.go("--keep-platform")
        self.assertIn("no platform", str(raised.exception))
        self.assertIn("'plat'", str(raised.exception))
        self.assertFalse((self.tmp / "out-grok-a").exists(), "refused before the output folder was made")
        self.assertFalse(self.model_started())
        # a custom prompt never has a platform
        self.use_case(self.platform())
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "out-custom"), "--prompt", "x",
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--keep-platform"])
        self.assertIn("'custom' has no platform", str(raised.exception))
        self.assertEqual(self.verbs(), [])

    def test_it_is_refused_for_a_suite_a_preflight_only_run_and_a_baseline_report(self):
        for flag in (("--suite", "focused"), ("--preflight-only",), ("--baseline-report",)):
            with self.subTest(flag=flag[0]), self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
                run.main([*flag, "--keep-platform"])
            self.assertIn("--keep-platform", str(raised.exception))
            self.assertIn(flag[0], str(raised.exception))

    def test_a_new_run_needs_a_durable_output_folder_and_a_resume_needs_none(self):
        """CASE3-2: the snapshot a later cleanup needs lives in <output>/platform, and the default output is under $TMPDIR, which macOS
        purges after days. The refusal comes before any folder is made; a resume reuses its run's folder (--output is ignored there)."""
        self.use_case(self.platform())
        sys_tmp = self.tmp / "sys-tmp"
        no_output = ["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--case", "plat", "--plugin-dir", str(self.plugin),
                     "--baseline", str(self.baselines)]
        with mock.patch.object(run.tempfile, "gettempdir", return_value=str(sys_tmp)):
            with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
                run.main([*no_output, "--keep-platform"])
            self.assertIn("--keep-platform needs --output", str(raised.exception))
            self.assertIn("$TMPDIR", str(raised.exception))
            self.assertFalse(sys_tmp.exists(), "refused before the output folder was made")
            self.assertEqual(self.verbs(), [])
            self.assertFalse(self.model_started())
            os.environ["FAKE_MODE"] = "done"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run.main(no_output), 0, "without the flag the default output is as it was")
            self.assertEqual(len(list((sys_tmp / "shiploop-e2e").glob("plat-*"))), 1)
        # a resume of a run that was started with a folder of its own keeps the platform without --output (the existing resume test)
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform", tag="resumed")
        result, _ = self.resume("grok", Path(first["output"]), "done", "--keep-platform")
        self.assertEqual(result["platform"]["cleanup"], self.KEPT)

    def test_a_resume_of_a_run_without_a_platform_is_refused_too(self):
        self.use_case(None)
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", Path(first["output"]), "done", "--keep-platform")
        self.assertIn("no platform", str(raised.exception))

    def test_a_finished_delivery_is_kept_and_the_block_says_what_remains_and_how_to_remove_it(self):
        self.use_case(self.platform())
        code, result, printed = self.invoke("grok", "done", "--keep-platform")
        self.assertEqual(code, 0, result)
        self.assertEqual(self.verbs(), ["preflight", "before"], "no cleanup ran")
        out = Path(result["output"])
        self.assertEqual(result["platform"]["cleanup"], self.KEPT)
        self.assertEqual(json.loads((out / "platform" / "cleanup-record.json").read_text()), self.KEPT)
        self.assertNotIn("keep_not_honoured", result["platform"])
        self.assertTrue(result["pass"])
        self.assertEqual(result["outcome_class"], "PASS")
        self.assertIs(json.loads((out / "invocation.json").read_text())["keep_platform"], True)
        command = run.manual_cleanup_command(out, self.platform())
        self.assertIn("  platform  PASS  platform KEPT (--keep-platform), no cleanup run; home links .sfdx", printed)
        self.assertEqual(printed.count("PLATFORM KEPT (--keep-platform)"), 1)
        self.assertEqual(printed.count(command), 2, "once at the start of the run, once in the kept block")
        self.assertIn("cleanup runs after grading unless --keep-platform keeps a finished delivery", printed)
        # unmissable: the last thing printed, after the report, and it states what stays and that only the person removes it
        block = printed[printed.index("=" * 78):]
        self.assertGreater(printed.index("PLATFORM KEPT"), printed.index("  quality   "))
        self.assertTrue(block.rstrip().endswith("=" * 78))
        self.assertIn("The cleanup did not run, so everything the run deployed stays until you remove it", block)
        self.assertIn("Nothing else removes it", block)
        self.assertIn(f"  {command}\n", block)
        self.assertIn(str(out / "platform"), block)
        # the printed command is the one that removes it, pasted into a shell
        done = subprocess.run(command, shell=True, capture_output=True, text=True)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, "ok cleanup"), done.stderr)
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])

    def test_a_kept_record_is_what_the_reader_of_result_json_sees_and_a_regrade_keeps_it(self):
        self.use_case(self.platform())
        _, result, _ = self.invoke("grok", "done", "--keep-platform")
        out = Path(result["output"])
        calls = self.calls()
        regraded, printed = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.calls(), calls, "a regrade neither cleans a kept platform nor asks it again")
        self.assertEqual(regraded["platform"]["cleanup"], self.KEPT)
        self.assertIn("checks_restated", regraded["platform"])
        self.assertTrue(regraded["pass"])
        again, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertEqual(self.calls(), calls)
        self.assertEqual(again["platform"]["cleanup"], self.KEPT)
        self.assertIn("--keep-platform changes nothing here: no cleanup was pending", printed)
        self.assertNotIn("NOT honoured", printed, "nothing was cleaned, so nothing is said to have been")
        self.assertNotIn("keep_not_honoured", again["platform"], "a kept platform and a not-honoured keep are not shown together")
        self.assertNotIn("PLATFORM KEPT (--keep-platform)", printed, "the block belongs to the run that kept it")

    def test_pass_does_not_depend_on_the_cleanup_when_the_platform_is_kept(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        code, result, printed = self.invoke("grok", "done", "--keep-platform")
        self.assertEqual(code, 0, result)
        self.assertTrue(result["pass"])
        self.assertNotIn("PLATFORM CLEANUP FAILED", printed)
        self.assertEqual(self.verbs(), ["preflight", "before"])
        # the same environment without the flag is the failed cleanup it always was
        code, result, printed = self.invoke("grok", "done", tag="b")
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"])
        self.assertIn("PLATFORM CLEANUP FAILED", printed)

    def test_the_default_run_is_unchanged(self):
        self.use_case(self.platform())
        code, result, printed = self.invoke("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertNotIn("kept", result["platform"]["cleanup"])
        self.assertNotIn("keep_not_honoured", result["platform"])
        self.assertIs(json.loads((Path(result["output"]) / "invocation.json").read_text())["keep_platform"], False)
        self.assertNotIn("KEPT", printed)
        self.assertNotIn("keep-platform", printed)
        self.assertIn("cleanup runs after grading, always", printed)

    def test_every_other_ending_still_cleans_and_says_the_keep_was_not_honoured(self):
        self.use_case(self.platform())
        cases = (("stuck", (), "ShipLoop is active, not done"), ("blocked", (), "ShipLoop is blocked, not done"),
                 ("fail", (), "ShipLoop is unknown, not done"), ("hang", ("--timeout", "2"), "the host timed out"),
                 ("stop", (), "the run was stopped (stopped by "))
        for mode, extra, why in cases:
            with self.subTest(mode=mode):
                self.plat_log.unlink(missing_ok=True)
                code, printed, out = self.go("--keep-platform", "--max-resumes", "0", *extra, mode=mode, tag=mode)
                result = self.result(out)
                self.assertEqual(self.verbs(), self.CLEANED)
                self.assertTrue(result["platform"]["cleanup"]["ran"] and result["platform"]["cleanup"]["ok"])
                self.assertNotIn("kept", result["platform"]["cleanup"])
                self.assertIn(why, result["platform"]["keep_not_honoured"])
                self.assertIn("--keep-platform NOT honoured (", printed)
                self.assertIn(why, printed)
                self.assertIn("so the platform was cleaned as usual", printed)
                self.assertNotIn("PLATFORM KEPT", printed)
                self.assertIs(json.loads((out / "invocation.json").read_text())["keep_platform"], True)

    def test_a_failed_case_check_cleans_even_when_everything_else_finished(self):
        self.use_case(self.platform())
        cases = json.loads(run.CASES.read_text())
        cases["plat"]["checks"] = ["false"]
        run.CASES.write_text(json.dumps(cases))
        code, printed, out = self.go("--keep-platform")
        self.assertEqual(code, 1)
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertIn("a case check failed (false)", self.result(out)["platform"]["keep_not_honoured"])
        self.assertNotIn("PLATFORM KEPT", printed)

    def test_an_invalid_trial_is_cleaned_not_kept(self):
        spec = self.platform(model_bin={"sf": f"{shlex.quote(sys.executable)} {shlex.quote(str(self.tmp / 'guard_tool.py'))}"},
                             home_links=None)
        spec["preflight"] = f"sf probe && {self.command('preflight')}"
        self.use_case(spec)
        code, printed, out = self.go("--keep-platform")  # the model's transcript shows sf and the guard never saw a call
        self.assertEqual(code, 1)
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertIn("an invalid trial: the guard did not govern the model's sf", self.result(out)["platform"]["keep_not_honoured"])

    def test_a_crash_a_ctrl_c_or_an_exit_still_cleans(self):
        self.use_case(self.platform())
        for tag, exception in (("boom", RuntimeError("boom")), ("ctrl-c", KeyboardInterrupt()), ("exit", SystemExit("stop"))):
            with self.subTest(exception=type(exception).__name__):
                self.plat_log.unlink(missing_ok=True)
                with mock.patch.object(run, "summarize_events", side_effect=exception), \
                        contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(type(exception)):
                    run.main(self.argv("--keep-platform", tag=tag))
                self.assertEqual(self.verbs(), self.CLEANED)
                recorded = json.loads((self.tmp / f"out-grok-{tag}" / "platform" / "cleanup-record.json").read_text())
                self.assertTrue(recorded["ran"] and recorded["ok"])
                self.assertNotIn("kept", recorded)
                self.assertNotIn("PLATFORM KEPT", printed.getvalue())

    def test_a_crash_after_the_decision_to_keep_still_says_how_to_remove_it(self):
        self.use_case(self.platform())
        out = self.tmp / "out-grok-late"
        with mock.patch.object(run, "review_export", side_effect=RuntimeError("late")), \
                contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(RuntimeError):
            run.main(self.argv("--keep-platform", tag="late"))
        self.assertEqual(self.verbs(), ["preflight", "before"], "the decision was made on a finished delivery: nothing cleans")
        self.assertEqual(printed.getvalue().count("PLATFORM KEPT (--keep-platform)"), 1)
        self.assertIn(run.manual_cleanup_command(out, self.platform()), printed.getvalue())
        self.assertEqual(json.loads((out / "platform" / "cleanup-record.json").read_text()), self.KEPT)

    def test_a_resumed_run_keeps_the_platform_only_when_the_resume_passes_the_flag_again(self):
        self.use_case(self.platform())
        for tag, again in (("plain", ()), ("again", ("--keep-platform",))):
            with self.subTest(resume=tag):
                self.plat_log.unlink(missing_ok=True)
                _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform", tag=tag)
                out = Path(first["output"])
                self.assertTrue(first["platform"]["cleanup"]["ran"], "the first segment was not finished: cleaned")
                self.assertIn("not done", first["platform"]["keep_not_honoured"])
                result, _ = self.resume("grok", out, "done", *again)
                (resume_file,) = out.glob("invocation-resume-grok-*.json")
                self.assertIs(json.loads(resume_file.read_text())["keep_platform"], bool(again))
                if again:
                    self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "preflight"])
                    self.assertEqual(result["platform"]["cleanup"], self.KEPT)
                    self.assertEqual(len(result["platform"]["earlier_cleanups"]), 1, "the first segment's cleanup stays on record")
                else:
                    self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "preflight", "cleanup"])
                    self.assertTrue(result["platform"]["cleanup"]["ran"])
                    self.assertNotIn("kept", result["platform"]["cleanup"])

    def test_the_command_that_continues_a_run_carries_the_flag(self):
        self.use_case(self.platform())
        out = self.tmp / "r"
        for given, expected in ((("--keep-platform",), True), ((), False)):
            args = run.parser().parse_args(["--host", "grok", "--model", "m", *given])
            self.assertEqual("--keep-platform" in shlex.split(run.resume_command(out, args)), expected)
        _, result, printed = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform", tag="line")
        resume_lines = [line for line in printed.splitlines() if line.startswith("resume:") or line.startswith("  resume ")]
        self.assertTrue(resume_lines and all("--keep-platform" in line for line in resume_lines), resume_lines)

    def test_the_kept_decision_is_a_pure_function_of_how_the_run_ended(self):
        stop = self.tmp / "stop"
        good = dict(shiploop={"pass": True}, engine={"status": "done"}, process={"status": "exited", "pass": True},
                    stop_seen=False, stop_file=stop, checks=[{"command": "c", "pass": True}], invalid=False)
        self.assertIsNone(run.keep_refusal(**good))
        for change, why in (
                ({"stop_seen": True}, "the run was stopped"), ({"process": {"status": "stopped", "pass": None}}, "the run was stopped"),
                ({"process": {"status": "timeout", "pass": False}}, "the host timed out"),
                ({"engine": {"status": "blocked"}}, "ShipLoop is blocked, not done"), ({"engine": {"status": "active"}}, "ShipLoop is active"),
                ({"engine": {}}, "ShipLoop is unknown"), ({"shiploop": {"pass": False, "status": "done"}}, "ShipLoop wrote no report"),
                ({"process": {"status": "failed", "returncode": 1, "pass": False}}, "the host ended failed rc=1"),
                ({"checks": [{"command": "a", "pass": True}, {"command": "b", "pass": False}]}, "a case check failed (b)"),
                ({"invalid": True}, "an invalid trial")):
            with self.subTest(why=why):
                self.assertIn(why, run.keep_refusal(**{**good, "stop_seen": False, **change}))
        stop.write_text("stop")
        self.assertIn("the run was stopped", run.keep_refusal(**good))
        stop.unlink()
        with mock.patch.object(run.TERMINATION, "is_set", return_value=True):
            self.assertIn("the run was stopped", run.keep_refusal(**good))
        self.assertIsNone(run.keep_refusal(**{**good, "process": {"status": "not observed", "pass": None}}), "a regrade observed no exit")
        failed = {"ran": True, "ok": False, "returncode": 3, "output": "boom"}
        self.assertEqual(run.keep_refusal(**good, earlier_cleanup=failed),
                         "an earlier cleanup of this run failed: run the printed command first")
        self.assertIn("earlier cleanup", run.keep_refusal(**good, earlier_cleanup={"ran": False, "ok": False, "reason": "no cleanup record"}))
        for record in (None, {}, {"ran": True, "ok": True}, self.KEPT, {"ran": False, "ok": True, "reason": "the case names no cleanup command"}):
            with self.subTest(earlier_cleanup=record):
                self.assertIsNone(run.keep_refusal(**good, earlier_cleanup=record))

    def late_crash(self, *extra: str, tag: str) -> Path:
        """A run that raises after the platform decision (the cleanup, or the keep) and before result.json is written."""
        with mock.patch.object(environment, "result_block", side_effect=RuntimeError("late")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run.main(self.argv(*extra, tag=tag))
        out = self.tmp / f"out-grok-{tag}"
        self.assertFalse((out / "result.json").exists(), "the run never reached its result")
        return out

    def test_a_regrade_of_a_run_that_never_wrote_result_json_reads_the_cleanup_record(self):
        """R2-H-2: --grade-only is the recovery for a run that never wrote its records; it must not treat the platform as uncleaned."""
        self.use_case(self.platform())
        out = self.late_crash("--keep-platform", tag="kept")
        self.assertEqual(self.verbs(), ["preflight", "before"], "kept before the crash")
        regraded, printed = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), ["preflight", "before"], "a kept platform is not cleaned by the regrade that follows a crash")
        self.assertEqual(regraded["platform"]["cleanup"], self.KEPT)
        self.assertTrue(regraded["pass"], regraded)
        self.assertNotIn("PLATFORM KEPT (--keep-platform)", printed, "the block belongs to the run that kept it")
        # a crash after a normal cleanup: cleaned once, not twice
        self.plat_log.unlink()
        out = self.late_crash(tag="cleaned")
        self.assertEqual(self.verbs(), self.CLEANED)
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED, "no second cleanup")
        self.assertTrue(regraded["platform"]["cleanup"]["ran"] and regraded["platform"]["cleanup"]["ok"])
        self.assertTrue(regraded["pass"], regraded)
        # a crash after a cleanup that failed: the regrade cleans again, as it does for a run that did write its result
        self.plat_log.unlink()
        os.environ["PLAT_FAIL"] = "cleanup"
        out = self.late_crash(tag="failed")
        del os.environ["PLAT_FAIL"]
        self.assertFalse(json.loads((out / "platform" / "cleanup-record.json").read_text())["ok"])
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED + ["cleanup"])
        self.assertTrue(regraded["platform"]["cleanup"]["ok"])

    def test_the_latest_cleanup_record_wins_over_the_one_in_an_older_result(self):
        """R2-H-2: a later invocation that crashed after a failed cleanup leaves result.json holding the earlier invocation's."""
        self.use_case(self.platform())
        _, first, _ = self.invoke("grok", "done")
        out = Path(first["output"])
        self.assertTrue(first["platform"]["cleanup"]["ok"])
        (out / "platform" / "cleanup-record.json").write_text(json.dumps({"ran": True, "ok": False, "returncode": 3, "output": "boom"}))
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED + ["cleanup"], "the failed cleanup is cleaned again")
        self.assertTrue(regraded["platform"]["cleanup"]["ok"])
        self.assertNotIn("checks_restated", regraded["platform"], "the platform was not clean when the regrade began")

    def test_keep_on_a_regrade_of_a_run_whose_cleanup_failed_is_refused_and_the_regrade_cleans(self):
        """R2-H-3: the failed run's leftovers must not become a kept, passing run with the failure record overwritten."""
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        _, first, _ = self.invoke("grok", "done")
        out = Path(first["output"])
        self.assertFalse(first["platform"]["cleanup"]["ok"])
        del os.environ["PLAT_FAIL"]
        regraded, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertEqual(self.verbs(), self.CLEANED + ["cleanup"], "cleaned, not kept")
        cleanup = regraded["platform"]["cleanup"]
        self.assertTrue(cleanup["ran"] and cleanup["ok"])
        self.assertNotIn("kept", cleanup)
        self.assertEqual(regraded["platform"]["keep_not_honoured"],
                         "an earlier cleanup of this run failed: run the printed command first")
        self.assertIn("--keep-platform NOT honoured (an earlier cleanup of this run failed: run the printed command first), "
                      "so the platform was cleaned as usual", printed)
        self.assertNotIn("PLATFORM KEPT", printed)
        self.assertNotIn("kept", json.loads((out / "platform" / "cleanup-record.json").read_text()))

    def test_a_regrade_with_no_cleanup_record_at_all_can_still_keep_a_finished_delivery(self):
        """R2-H-3: a harness killed after the delivery finished leaves no record; there is no failure to refuse on."""
        self.use_case(self.platform())
        _, first, _ = self.invoke("grok", "done")
        out = Path(first["output"])
        (out / "result.json").unlink()
        (out / "platform" / "cleanup-record.json").unlink()
        calls = self.calls()
        regraded, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertEqual(self.calls(), calls, "kept: the regrade cleaned nothing")
        self.assertEqual(regraded["platform"]["cleanup"], self.KEPT)
        self.assertNotIn("keep_not_honoured", regraded["platform"])
        self.assertEqual(printed.count("PLATFORM KEPT (--keep-platform)"), 1)

    def test_keep_where_no_cleanup_was_pending_says_it_changes_nothing_and_records_no_refusal(self):
        """R2-H-4: a regrade of a run that was already cleaned cleans nothing, so it does not say it cleaned and does not record a refusal."""
        self.use_case(self.platform())
        _, first, _ = self.invoke("grok", "done")
        out = Path(first["output"])
        calls = self.calls()
        regraded, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertEqual(self.calls(), calls)
        self.assertIn("--keep-platform changes nothing here: no cleanup was pending", printed)
        self.assertNotIn("NOT honoured", printed)
        self.assertNotIn("cleaned as usual", printed)
        self.assertNotIn("keep_not_honoured", regraded["platform"])
        self.assertTrue(regraded["platform"]["cleanup"]["ok"] and not regraded["platform"]["cleanup"].get("kept"))
        # the same where another harness holds the case: nothing is pending for this invocation either
        held = listeners.hold_case(out)
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        again, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertIn("changes nothing here", printed)
        self.assertNotIn("keep_not_honoured", again["platform"])

    def test_the_guard_keeps_only_what_is_pending_and_a_later_finish_cleans_nothing(self):
        out = self.tmp / "guard-out"
        out.mkdir()
        marker = self.tmp / "cleaned"
        spec = {"kind": "test", "cleanup": f"touch {shlex.quote(str(marker))}"}
        unarmed = run.PlatformGuard()
        self.assertIsNone(unarmed.keep("--keep-platform"))
        guard = run.PlatformGuard()
        guard.arm(spec, out)
        self.assertTrue(guard.armed())
        self.assertEqual(guard.keep("--keep-platform"), self.KEPT)
        self.assertFalse(guard.armed())
        self.assertIsNone(guard.keep("--keep-platform"), "kept once")
        self.assertEqual(guard.finish(), self.KEPT)
        self.assertFalse(marker.exists(), "finish after keep must not clean")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            guard.print_kept()
            guard.print_kept()
        self.assertEqual(printed.getvalue().count("PLATFORM KEPT"), 1)
        self.assertIn("in the test (", printed.getvalue())
        self.assertIn(run.manual_cleanup_command(out, spec), printed.getvalue())
        # a case that names no cleanup says so instead of printing a command
        bare = run.PlatformGuard()
        bare.arm({"kind": "test"}, out)
        bare.keep("--keep-platform")
        self.assertIn("the case names no cleanup command", bare.banner)


class KeepUnfinishedTest(PlatformCase):
    """--keep-platform for a run that did not finish (owner 2026-10-17): ShipLoop not done, or the host timed out, with a platform
    that works (every `keep_checks` word of the case's own checks passes) and a valid trial. It is kept and recorded NOT a pass; a
    person's stop, an invalid trial and a failing keep check clean as always. A resume of such a run is not refused by the case's
    preflight (which refuses a platform that is not clean) and is told its work is still there. Here the keep word is the command
    `true`, which the test case's one check is."""

    CLEANED = KeepPlatformTest.CLEANED
    KEPT = KeepPlatformTest.KEPT
    KEPT_UNFINISHED = {"ran": False, "ok": True, "kept": True, "kept_unfinished": True,
                       "reason": "--keep-platform (ShipLoop did not finish: NOT a pass)"}
    NOTE = "The platform was reset when the last session ended: deploy again what you still need."
    NOTE_KEPT = "Your last session's work was kept: what you deployed is still in the platform."
    argv, go, result = KeepPlatformTest.argv, KeepPlatformTest.go, KeepPlatformTest.result

    def spec(self, **override) -> dict:
        return self.platform(**{"keep_checks": ["true"], "resume_note": self.NOTE, "resume_note_kept": self.NOTE_KEPT, **override})

    def test_a_host_that_timed_out_with_a_working_platform_is_kept_and_recorded_not_a_pass(self):
        self.use_case(self.spec())
        code, printed, out = self.go("--keep-platform", "--timeout", "2", "--max-resumes", "0", mode="hang")
        result = self.result(out)
        self.assertEqual(result["process"]["status"], "timeout")
        self.assertEqual(code, 1)
        self.assertFalse(result["pass"], "a kept unfinished platform is never a pass")
        self.assertEqual(self.verbs(), ["preflight", "before"], "no cleanup ran")
        self.assertEqual(result["platform"]["cleanup"], self.KEPT_UNFINISHED)
        self.assertIs(result["platform"]["kept_unfinished"], True)
        self.assertNotIn("keep_not_honoured", result["platform"])
        self.assertEqual(json.loads((out / "platform" / "cleanup-record.json").read_text()), self.KEPT_UNFINISHED)
        self.assertIn("  platform  KEPT  platform KEPT (--keep-platform), ShipLoop did not finish: NOT a pass; home links", printed)
        self.assertNotIn("NOT honoured", printed)
        self.assertFalse(self.baselines.exists(), "an unfinished run is no baseline")
        # the last thing printed says what stays, that it is not a pass, and the one command that removes it
        block = printed[printed.rindex("=" * 78, 0, printed.index("PLATFORM KEPT (--keep-platform): what")):]
        self.assertEqual(printed.count("PLATFORM KEPT (--keep-platform): what"), 1)
        self.assertTrue(block.rstrip().endswith("=" * 78))
        self.assertIn("ShipLoop did not finish, so this is NOT a pass", block)
        self.assertIn("(true)", block)
        self.assertIn("Resuming this run continues with it in place", block)
        self.assertIn(f"  {run.manual_cleanup_command(out, self.spec())}\n", block)
        self.assertIn("cleanup runs after grading unless --keep-platform keeps a finished delivery, or an unfinished one whose "
                      "keep checks (true) pass", printed)

    def test_a_shiploop_that_stopped_before_done_is_kept_the_same_way(self):
        self.use_case(self.spec())
        for mode in ("stuck", "blocked", "fail"):
            with self.subTest(mode=mode):
                self.plat_log.unlink(missing_ok=True)
                code, printed, out = self.go("--keep-platform", "--max-resumes", "0", mode=mode, tag=mode)
                result = self.result(out)
                self.assertEqual(self.verbs(), ["preflight", "before"])
                self.assertEqual(result["platform"]["cleanup"], self.KEPT_UNFINISHED)
                self.assertFalse(result["pass"])
                self.assertEqual(code, 1)
                self.assertIn("ShipLoop did not finish: NOT a pass", printed)

    def test_a_failing_case_check_that_is_not_a_keep_check_does_not_stop_the_keep(self):
        """The chess case's `project` check needs a commit: an unfinished run fails it and its working app is still kept."""
        self.use_case(self.spec())
        cases = json.loads(run.CASES.read_text())
        cases["plat"]["checks"] = ["true", "false"]
        run.CASES.write_text(json.dumps(cases))
        _, printed, out = self.go("--keep-platform", "--max-resumes", "0", mode="stuck")
        self.assertEqual(self.result(out)["platform"]["cleanup"], self.KEPT_UNFINISHED)
        self.assertEqual(self.verbs(), ["preflight", "before"])

    def test_a_failing_keep_check_cleans_and_says_why(self):
        self.use_case(self.spec(keep_checks=["false"]))
        cases = json.loads(run.CASES.read_text())
        cases["plat"]["checks"] = ["true", "false"]
        run.CASES.write_text(json.dumps(cases))
        for mode, extra, why in (("stuck", (), "ShipLoop is active, not done"), ("hang", ("--timeout", "2"), "the host timed out")):
            with self.subTest(mode=mode):
                self.plat_log.unlink(missing_ok=True)
                _, printed, out = self.go("--keep-platform", "--max-resumes", "0", *extra, mode=mode, tag=mode)
                found = self.result(out)["platform"]
                self.assertEqual(self.verbs(), self.CLEANED)
                self.assertTrue(found["cleanup"]["ran"] and found["cleanup"]["ok"])
                self.assertNotIn("kept", found["cleanup"])
                self.assertNotIn("kept_unfinished", found)
                self.assertIn(why, found["keep_not_honoured"])
                self.assertIn("not kept as an unfinished run either: the keep check(s) false did not pass", found["keep_not_honoured"])
                self.assertIn("--keep-platform NOT honoured (", printed)
                self.assertNotIn("PLATFORM KEPT", printed)

    def test_a_person_s_stop_and_an_invalid_trial_clean_even_when_the_platform_works(self):
        self.use_case(self.spec())
        _, printed, out = self.go("--keep-platform", "--max-resumes", "0", mode="stop", tag="stop")
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertIn("the run was stopped (stopped by ", self.result(out)["platform"]["keep_not_honoured"])
        self.assertNotIn("PLATFORM KEPT", printed)
        # an invalid trial: the transcript shows sf and the guard never saw a call
        self.plat_log.unlink()
        spec = self.spec(model_bin={"sf": f"{shlex.quote(sys.executable)} {shlex.quote(str(self.tmp / 'guard_tool.py'))}"}, home_links=None)
        spec["preflight"] = f"sf probe && {self.command('preflight')}"
        self.use_case(spec)
        _, printed, out = self.go("--keep-platform", "--max-resumes", "0", mode="stuck", tag="invalid")
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertEqual(self.result(out)["platform"]["keep_not_honoured"], "an invalid trial: the guard did not govern the model's sf")
        self.assertNotIn("PLATFORM KEPT", printed)

    def test_a_signal_or_a_crash_still_cleans_an_unfinished_run(self):
        self.use_case(self.spec())
        for tag, exception in (("ctrl-c", KeyboardInterrupt()), ("boom", RuntimeError("boom"))):
            with self.subTest(exception=type(exception).__name__):
                self.plat_log.unlink(missing_ok=True)
                with mock.patch.object(run, "summarize_events", side_effect=exception), \
                        contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(type(exception)):
                    run.main(self.argv("--keep-platform", "--max-resumes", "0", tag=tag, mode="stuck"))
                self.assertEqual(self.verbs(), self.CLEANED)
                self.assertNotIn("PLATFORM KEPT", printed.getvalue())

    def test_a_finished_delivery_of_a_case_with_keep_checks_is_kept_as_a_finished_one(self):
        self.use_case(self.spec())
        code, printed, out = self.go("--keep-platform")
        result = self.result(out)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["platform"]["cleanup"], self.KEPT)
        self.assertNotIn("kept_unfinished", result["platform"])
        self.assertTrue(result["pass"])
        self.assertIn("platform KEPT (--keep-platform), no cleanup run", printed)
        self.assertNotIn("NOT a pass", printed)

    def test_without_the_flag_an_unfinished_run_is_cleaned_as_always(self):
        self.use_case(self.spec())
        _, printed, out = self.go("--max-resumes", "0", mode="stuck")
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertNotIn("kept", self.result(out)["platform"]["cleanup"])
        self.assertNotIn("KEPT", printed)
        self.assertNotIn("keep checks", printed)

    def test_a_resume_of_a_kept_unfinished_run_skips_the_case_preflight_and_is_told_the_work_is_still_there(self):
        self.use_case(self.spec())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform")
        out = Path(first["output"])
        self.assertEqual(first["platform"]["cleanup"], self.KEPT_UNFINISHED)
        self.assertEqual(self.verbs(), ["preflight", "before"])
        os.environ["PLAT_FAIL"] = "preflight"  # the platform now holds the run's own items: the case's preflight would refuse it
        result, printed = self.resume("grok", out, "done", "--keep-platform")
        self.assertEqual(self.verbs(), ["preflight", "before"], "the case's preflight did not run again, and nothing was cleaned")
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["platform"]["cleanup"], self.KEPT, "this segment finished: a finished delivery is kept as one")
        self.assertEqual(result["platform"]["earlier_cleanups"], [self.KEPT_UNFINISHED])
        skipped = result["platform"]["preflight"]
        self.assertTrue(skipped["ok"] and skipped["skipped"] and skipped["returncode"] is None and skipped["command"], skipped)
        self.assertEqual(result["platform"]["home_links"][0]["name"], ".sfdx", "the links and the wrappers are still made")
        self.assertIn("the case's own preflight is skipped", printed)
        (resume_file,) = out.glob("invocation-resume-grok-*.json")
        self.assertTrue(json.loads(resume_file.read_text())["platform"]["preflight"]["skipped"])
        prompt = sorted(out.glob("resume-grok-*.txt"))[-1].read_text()
        self.assertTrue(prompt.endswith(self.NOTE_KEPT), prompt[-200:])
        self.assertNotIn(self.NOTE, prompt, "it was not reset, so the reset note would be false")

    def test_a_resume_after_a_cleaned_ending_still_runs_the_case_preflight(self):
        self.use_case(self.spec())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")  # no --keep-platform: cleaned
        out = Path(first["output"])
        self.assertEqual(self.verbs(), self.CLEANED)
        os.environ["PLAT_FAIL"] = "preflight"
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", out, "done", "--keep-platform")
        self.assertIn("platform preflight refused the run before any model started", str(refused.exception))
        self.assertEqual(self.verbs(), self.CLEANED + ["preflight"], "the case's preflight ran and refused")

    def test_a_resume_without_the_flag_skips_the_preflight_but_cleans_at_its_end(self):
        self.use_case(self.spec())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform")
        out = Path(first["output"])
        os.environ["PLAT_FAIL"] = "preflight"
        result, _ = self.resume("grok", out, "done")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"])
        self.assertTrue(result["platform"]["cleanup"]["ran"] and result["platform"]["cleanup"]["ok"])
        self.assertTrue(sorted(out.glob("resume-grok-*.txt"))[-1].read_text().endswith(self.NOTE_KEPT))

    def test_a_segment_killed_hard_after_a_kept_one_leaves_a_pending_record_so_the_preflight_runs_again(self):
        """A task kill leaves no signal handler to clean or keep: the pending record says nothing is known, the next resume's case
        preflight judges the platform (a dirty one is refused, and the printed removal command is the way out)."""
        self.use_case(self.spec())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform")
        out = Path(first["output"])
        self.assertEqual(first["platform"]["cleanup"], self.KEPT_UNFINISHED)
        with mock.patch.object(run.PlatformGuard, "finish", return_value=None), \
                mock.patch.object(run, "summarize_events", side_effect=RuntimeError("killed")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            self.resume("grok", out, "stuck", "--keep-platform")  # killed after arming, before the keep decision
        self.assertEqual(json.loads((out / "platform" / "cleanup-record.json").read_text()), run.PENDING_CLEANUP)
        os.environ["PLAT_FAIL"] = "preflight"
        with self.assertRaises(SystemExit) as refused, contextlib.redirect_stdout(io.StringIO()):
            self.resume("grok", out, "done", "--keep-platform")
        self.assertIn("platform preflight refused", str(refused.exception))

    def test_a_regrade_of_a_kept_unfinished_run_neither_cleans_it_nor_calls_it_a_pass(self):
        self.use_case(self.spec())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", "--keep-platform")
        out = Path(first["output"])
        calls = self.calls()
        regraded, printed = self.resume("grok", out, "stuck", "--grade-only", "--keep-platform")
        self.assertEqual(self.calls(), calls, "nothing was cleaned and nothing was asked of the platform's commands")
        self.assertEqual(regraded["platform"]["cleanup"], self.KEPT_UNFINISHED)
        self.assertIs(regraded["platform"]["kept_unfinished"], True)
        self.assertFalse(regraded["pass"])
        self.assertIn("--keep-platform changes nothing here", printed)

    def test_the_note_for_a_resumed_model_depends_on_what_the_earlier_segment_did(self):
        spec = {"resume_note": self.NOTE, "resume_note_kept": self.NOTE_KEPT}
        kept, cleaned = {"cleanup": self.KEPT_UNFINISHED}, {"cleanup": {"ran": True, "ok": True}}
        self.assertEqual(run.resume_platform_note(spec, kept, regrade=False), self.NOTE_KEPT)
        self.assertEqual(run.resume_platform_note(spec, cleaned, regrade=False), self.NOTE)
        self.assertIsNone(run.resume_platform_note(spec, kept, regrade=True))
        self.assertIsNone(run.resume_platform_note({"resume_note": self.NOTE}, kept, regrade=False),
                          "a case with no kept note says nothing rather than the reset note, which would be false")
        self.assertIsNone(run.resume_platform_note(spec, {"cleanup": self.KEPT}, regrade=False), "a finished keep is not resumed")
        self.assertIsNone(run.resume_platform_note(spec, {}, regrade=False))

    def test_the_keep_decision_is_a_pure_function_of_how_the_run_ended(self):
        stop = self.tmp / "stop"
        good = dict(shiploop={"pass": True}, engine={"status": "done"}, process={"status": "exited", "pass": True},
                    stop_seen=False, stop_file=stop, checks=[{"command": "c deployed", "pass": True}], invalid=False)
        unfinished = {**good, "engine": {"status": "active"}, "shiploop": {"pass": False}}
        timeout = {**good, "process": {"status": "timeout", "pass": False}}
        words = ("deployed",)
        self.assertEqual(run.keep_decision(**good, keep_checks=words), (run.KEPT_FINISHED, None))
        self.assertEqual(run.keep_decision(**good), (run.KEPT_FINISHED, None), "a case with no keep_checks keeps a finished delivery")
        for ended in (unfinished, timeout, {**unfinished, "engine": {"status": "blocked"}}, {**unfinished, "engine": {}},
                      {**unfinished, "process": {"status": "failed", "returncode": 1, "pass": False}}):
            with self.subTest(ended=ended["engine"], process=ended["process"]["status"]):
                self.assertEqual(run.keep_decision(**ended, keep_checks=words), (run.KEPT_UNFINISHED, None))
                self.assertEqual(run.keep_decision(**ended), (None, run.keep_refusal(**ended)), "no keep_checks: cleaned as before")
        # ShipLoop done and the host not timed out is a finished delivery only: a failed check, no report or a failed host is a failed
        # delivery, cleaned even though the keep checks pass
        for change in ({"checks": [{"command": "c project", "pass": False}, {"command": "c deployed", "pass": True}]},
                       {"shiploop": {"pass": False, "status": "done"}},
                       {"process": {"status": "failed", "returncode": 1, "pass": False}}):
            with self.subTest(finished_but=list(change)):
                kind, why = run.keep_decision(**{**good, **change}, keep_checks=words)
                self.assertEqual((kind, why), (None, run.keep_refusal(**{**good, **change})))
        # a case check that is not a keep check may fail; a keep check that fails or never ran may not
        failing = [{"command": "c project", "pass": False}, {"command": "c deployed", "pass": True}]
        self.assertEqual(run.keep_decision(**{**timeout, "checks": failing}, keep_checks=words), (run.KEPT_UNFINISHED, None))
        for checks in ([{"command": "c deployed", "pass": False}], [{"command": "c project", "pass": True}], []):
            kind, why = run.keep_decision(**{**timeout, "checks": checks}, keep_checks=words)
            self.assertIsNone(kind)
            self.assertEqual(why, "the host timed out; not kept as an unfinished run either: the keep check(s) deployed did not pass")
        self.assertIsNone(run.keep_decision(**{**timeout, "checks": [{"command": "c deployed2", "pass": True}]}, keep_checks=words)[0],
                          "a keep word is a whole word of the command")
        # nothing forbidden by keep_blocker is ever kept, whatever the checks say
        for change, why in (({"stop_seen": True}, "the run was stopped"), ({"process": {"status": "stopped", "pass": None}}, "the run was stopped"),
                            ({"invalid": True}, "an invalid trial")):
            with self.subTest(blocker=why):
                self.assertIn(why, run.keep_decision(**{**timeout, **change}, keep_checks=words)[1])
                self.assertIsNone(run.keep_decision(**{**timeout, **change}, keep_checks=words)[0])
        stop.write_text("stop")
        self.assertIn("the run was stopped", run.keep_decision(**timeout, keep_checks=words)[1])
        stop.unlink()
        with mock.patch.object(run.TERMINATION, "is_set", return_value=True):
            self.assertIn("the run was stopped", run.keep_decision(**timeout, keep_checks=words)[1])
        failed = {"ran": True, "ok": False, "returncode": 3, "output": "boom"}
        self.assertEqual(run.keep_decision(**timeout, keep_checks=words, earlier_cleanup=failed),
                         (None, "an earlier cleanup of this run failed: run the printed command first"))
        for record in (None, run.PENDING_CLEANUP, self.KEPT_UNFINISHED):
            with self.subTest(earlier_cleanup=record):
                self.assertEqual(run.keep_decision(**timeout, keep_checks=words, earlier_cleanup=record)[0], run.KEPT_UNFINISHED)

    def test_the_readme_states_the_rule_and_what_a_kept_app_does_to_the_next_run(self):
        text = (ROOT / "test" / "shiploop_e2e" / "README.md").read_text()
        section = text[text.index("#### Keeping what a run made"):text.index("### Launching long runs")]
        for part in ("keep_checks", "kept_unfinished", "NOT a pass", "resume_note_kept", "chess_salesforce.py preflight",
                     "refuse the next run", "kept after a person's stop"):
            self.assertIn(part, section)


class ManualCleanupTest(PlatformCase):
    def spec(self) -> dict:
        return {"cleanup": 'echo "[$E2E_CHECKS][$E2E_PLATFORM_DIR]"; echo "it'"'"'s $HOME"'}

    def test_the_printed_command_works_pasted_into_a_clean_shell(self):
        out = self.tmp / "my run"
        text = run.manual_cleanup_command(out, self.spec())
        done = subprocess.run(text, shell=True, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": "/h"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(), [f"[{run.HERE / 'checks'}][{out / 'platform'}]", "it's /h"])

    def test_the_old_prefix_assignment_form_would_have_expanded_the_variables_empty(self):
        out = self.tmp / "r"
        old = (f"E2E_PLATFORM_DIR={shlex.quote(str(out / 'platform'))} E2E_CHECKS={shlex.quote(str(run.HERE / 'checks'))} "
               f"{self.spec()['cleanup']}")
        done = subprocess.run(old, shell=True, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(done.stdout.splitlines()[0], "[][]", "why the printed form is `env ... sh -c`")

    def test_the_failure_banner_and_the_start_of_the_run_print_that_command(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        code, result, printed = self.invoke("grok", "done")
        out = Path(result["output"])
        text = run.manual_cleanup_command(out, self.platform())
        self.assertEqual(printed.count(text), 2, "once at the start of the run, once in the failure banner")
        self.assertIn(f"  {text}\n", printed)


class GuardHostTest(PlatformCase):
    def sleeper(self) -> subprocess.Popen:
        proc = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(proc.wait)
        self.addCleanup(listeners.end_group, proc.pid)
        return proc

    def state(self) -> str:
        return ("import subprocess, sys; print(subprocess.run(['ps', '-o', 'stat=', '-p', sys.argv[1]], capture_output=True, "
                "text=True).stdout.strip() or 'gone')")

    def test_the_cleanup_waits_until_this_threads_host_is_gone_and_leaves_a_sibling_s_alone(self):
        mine, sibling = self.sleeper(), self.sleeper()
        script = self.tmp / "state.py"
        script.write_text(self.state())
        seen = self.tmp / "seen.txt"
        cleanup = f"{shlex.quote(sys.executable)} {shlex.quote(str(script))} {mine.pid} > {shlex.quote(str(seen))}"
        groups = {mine.pid, sibling.pid}
        owners = {mine.pid: threading.get_ident(), sibling.pid: threading.get_ident() + 1}
        out = self.tmp / "guard-out"
        out.mkdir()
        with mock.patch.object(run, "LIVE_HOST_GROUPS", groups), mock.patch.object(run, "HOST_THREAD", owners):
            guard = run.PlatformGuard()
            guard.arm({"cleanup": cleanup}, out)
            record = guard.finish()
        self.assertTrue(record["ok"], record)
        state = seen.read_text().strip()
        self.assertTrue(state.startswith(("Z", "gone")), f"the host was still {state!r} when the cleanup ran")
        self.assertIsNone(sibling.poll(), "another case's host in a suite is not ended")
        self.assertEqual(listeners.unreaped(sibling.pid), "running")

    def slow_host(self, seconds: float):
        """Patches that make one registered leader of this thread look `running` for ``seconds`` and then exited, and ending it a no-op."""
        ready = time.time() + seconds
        owners = {4242: threading.get_ident()}
        return ready, (mock.patch.object(run, "LIVE_HOST_GROUPS", {4242}), mock.patch.object(run, "HOST_THREAD", owners),
                       mock.patch.object(listeners, "end_group", return_value=True),
                       mock.patch.object(listeners, "unreaped", side_effect=lambda pid: "running" if time.time() < ready else "exited"))

    def test_the_cleanup_does_not_start_while_the_host_is_still_running(self):
        ready, patches = self.slow_host(0.6)
        script = self.tmp / "stamp.py"
        script.write_text("import time; print(time.time())")
        stamp = self.tmp / "stamp.txt"
        out = self.tmp / "guard-out"
        out.mkdir()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            guard = run.PlatformGuard()
            guard.arm({"cleanup": f"{shlex.quote(sys.executable)} {shlex.quote(str(script))} > {shlex.quote(str(stamp))}"}, out)
            self.assertTrue(guard.finish()["ok"])
        self.assertGreaterEqual(float(stamp.read_text()), ready, "the cleanup began before the host was gone")

    def test_a_host_that_does_not_die_does_not_stop_the_cleanup(self):
        _, patches = self.slow_host(3600)
        out = self.tmp / "guard-out"
        out.mkdir()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(run, "HOST_END_WAIT", 0.3))
            for patch in patches:
                stack.enter_context(patch)
            guard = run.PlatformGuard()
            guard.arm({"cleanup": "true"}, out)
            began = time.monotonic()
            record = guard.finish()
            waited = time.monotonic() - began
        self.assertTrue(record["ran"] and record["ok"], "the platform is cleaned although the host would not go")
        self.assertGreaterEqual(waited, 0.3)
        self.assertLess(waited, 10)

    def test_an_unarmed_guard_ends_no_host(self):
        proc = self.sleeper()
        with mock.patch.object(run, "LIVE_HOST_GROUPS", {proc.pid}), \
                mock.patch.object(run, "HOST_THREAD", {proc.pid: threading.get_ident()}):
            self.assertIsNone(run.PlatformGuard().finish())
        self.assertIsNone(proc.poll())

    def test_ending_every_host_is_still_the_default(self):
        proc = self.sleeper()
        with mock.patch.object(run, "LIVE_HOST_GROUPS", {proc.pid}):
            run.end_live_hosts()
        proc.wait(timeout=10)
        self.assertEqual(proc.returncode, -9)


class HostRegistryTest(PlatformCase):
    def test_a_launched_host_is_registered_with_its_thread_and_forgotten_once_reaped(self):
        out = self.tmp / "launched"
        (out / "work").mkdir(parents=True)
        result: dict = {}
        with mock.patch.object(run, "LIVE_HOST_GROUPS", set()), mock.patch.object(run, "HOST_THREAD", {}):
            thread = threading.Thread(target=lambda: result.update(run.launch(
                [sys.executable, "-c", "import time; time.sleep(20)"], out / "work", out, dict(os.environ), 60, watch=False)))
            thread.start()
            try:
                for _ in range(100):
                    if run.LIVE_HOST_GROUPS:
                        break
                    time.sleep(0.05)
                (leader,) = run.LIVE_HOST_GROUPS
                self.assertEqual(run.HOST_THREAD, {leader: thread.ident})
                run.end_live_hosts(thread=thread.ident + 1)
                self.assertEqual(listeners.unreaped(leader), "running", "another thread's scope does not reach this host")
                run.end_live_hosts(thread=thread.ident, wait=10)
                thread.join(15)
                self.assertFalse(thread.is_alive())
                self.assertEqual((run.LIVE_HOST_GROUPS, run.HOST_THREAD), (set(), {}))
            finally:
                run.end_live_hosts()  # a failed assertion above leaves no host behind
                thread.join(15)
        self.assertEqual(result["status"], "failed")


class RegradeLockTest(PlatformCase):
    def test_a_regrade_does_not_clean_a_run_another_harness_holds_and_says_why(self):
        self.use_case(self.platform())
        os.environ["PLAT_FAIL"] = "cleanup"
        self.invoke("grok", "done")
        out = self.tmp / "out-grok-a"
        del os.environ["PLAT_FAIL"]
        held = listeners.hold_case(out)  # the trial's own harness
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        result, printed = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup"], "no second cleanup")
        self.assertIn("is held by another harness", printed)
        self.assertIn("no cleanup is run now", printed)
        self.assertIn(run.manual_cleanup_command(out, self.platform()), printed)
        self.assertFalse(result["platform"]["cleanup"]["ok"])
        self.assertFalse(result["pass"])
        held.close()
        result, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), ["preflight", "before", "cleanup", "cleanup"], "once the trial's harness is gone it is cleaned")
        self.assertTrue(result["platform"]["cleanup"]["ok"])


class HardKillTest(PlatformCase):
    """R3-H-1: a harness killed hard (a task limit, SIGKILL) after the model may have deployed, before its own cleanup. Simulated by
    an invocation whose finish() never runs and whose result is never built; the pending record it armed is all it leaves."""

    CLEANED = ["preflight", "before", "cleanup"]
    KEPT = {"ran": False, "ok": True, "kept": True, "reason": "--keep-platform"}
    NOTE = "The platform was reset when the last session ended: deploy again what you still need."

    def killed(self, call) -> None:
        with mock.patch.object(run.PlatformGuard, "finish", return_value=None), \
                mock.patch.object(environment, "result_block", side_effect=RuntimeError("killed")), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            call()

    def record(self, out: Path) -> dict:
        return json.loads((out / "platform" / "cleanup-record.json").read_text())

    def test_a_resumed_segment_killed_before_its_cleanup_is_not_read_as_cleaned_by_the_regrade(self):
        self.use_case(self.platform())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertTrue(self.record(out)["ok"], "segment 1 ended with an ok cleanup record")
        segment_one = (out / "result.json").read_text()
        self.killed(lambda: self.resume("grok", out, "done"))
        self.assertEqual(self.verbs(), self.CLEANED + ["preflight"], "segment 2 began and never cleaned")
        self.assertEqual((out / "result.json").read_text(), segment_one, "no result of segment 2: result.json is still segment 1's")
        self.assertEqual(self.record(out), run.PENDING_CLEANUP, "segment 1's ok record no longer stands for the run")
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED + ["preflight", "cleanup"], "the regrade cleans what segment 2 may have deployed")
        self.assertTrue(regraded["platform"]["cleanup"]["ran"] and regraded["platform"]["cleanup"]["ok"])
        self.assertNotIn("checks_restated", regraded["platform"], "the platform was deployed when the regrade began: its checks are asked")
        self.assertTrue(self.record(out)["ran"] and self.record(out)["ok"])
        self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED + ["preflight", "cleanup"], "cleaned once: the next regrade has nothing to clean")

    def test_a_killed_first_segment_is_cleaned_by_the_regrade_too(self):
        self.use_case(self.platform())
        self.killed(lambda: self.invoke("grok", "stuck", "--max-resumes", "0"))
        out = self.tmp / "out-grok-a"
        self.assertEqual(self.record(out), run.PENDING_CLEANUP)
        self.assertFalse((out / "result.json").exists())
        regraded, _ = self.resume("grok", out, "done", "--grade-only")
        self.assertEqual(self.verbs(), self.CLEANED)
        self.assertTrue(regraded["platform"]["cleanup"]["ok"])

    def test_the_resume_after_such_a_kill_is_still_told_the_platform_was_reset(self):
        """The note reads segment 1's cleanup in result.json, which wins over a record that says only 'pending'."""
        self.use_case(self.platform(resume_note=self.NOTE))
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        self.killed(lambda: self.resume("grok", out, "stuck"))
        self.assertEqual(self.record(out), run.PENDING_CLEANUP)
        self.resume("grok", out, "done")
        latest = sorted(out.glob("resume-grok-*.txt"))[-1]
        self.assertTrue(latest.read_text().endswith(self.NOTE), latest.read_text()[-200:])

    def test_a_pending_record_is_no_failed_cleanup_so_a_killed_harness_can_still_keep_a_finished_delivery(self):
        """R2-H-3: only a cleanup that was attempted and failed refuses the keep; a harness killed after the delivery finished may keep."""
        self.use_case(self.platform())
        self.killed(lambda: self.invoke("grok", "done"))
        out = self.tmp / "out-grok-a"
        self.assertEqual(self.record(out), run.PENDING_CLEANUP)
        regraded, printed = self.resume("grok", out, "done", "--grade-only", "--keep-platform")
        self.assertEqual(self.verbs(), ["preflight", "before"], "kept: the regrade cleaned nothing")
        self.assertEqual(regraded["platform"]["cleanup"], self.KEPT)
        self.assertNotIn("keep_not_honoured", regraded["platform"])
        self.assertEqual(printed.count("PLATFORM KEPT (--keep-platform)"), 1)
        self.assertEqual(self.record(out), self.KEPT)
        failed = {"ran": True, "ok": False, "returncode": 3, "output": "boom"}
        self.assertIn("earlier cleanup", run.keep_refusal(**self.finished(), earlier_cleanup=failed))
        self.assertIsNone(run.keep_refusal(**self.finished(), earlier_cleanup=run.PENDING_CLEANUP))

    def finished(self) -> dict:
        return dict(shiploop={"pass": True}, engine={"status": "done"}, process={"status": "exited", "pass": True},
                    stop_seen=False, stop_file=self.tmp / "no-stop", checks=[{"command": "c", "pass": True}], invalid=False)

    def test_arming_writes_the_pending_record_and_keeping_or_finishing_replaces_it(self):
        spec = {"kind": "test", "cleanup": "true"}
        out = self.tmp / "armed"
        (out / "platform").mkdir(parents=True)
        (out / "platform" / "cleanup-record.json").write_text(json.dumps({"ran": True, "ok": True}))
        guard = run.PlatformGuard()
        guard.arm(spec, out)
        self.assertEqual(self.record(out), run.PENDING_CLEANUP, "an earlier invocation's ok record is replaced")
        self.assertFalse(run.PENDING_CLEANUP["ok"] or run.PENDING_CLEANUP["ran"])
        self.assertTrue(guard.finish()["ok"])
        self.assertTrue(self.record(out)["ran"] and self.record(out)["ok"] and "pending" not in self.record(out))
        kept = run.PlatformGuard()
        kept.arm(spec, out)
        self.assertEqual(self.record(out), run.PENDING_CLEANUP)
        kept.keep("--keep-platform")
        self.assertEqual(self.record(out), self.KEPT)
        # a case with no cleanup command writes no record at arming or at its end: nothing is there to be pending
        bare_out = self.tmp / "bare"
        bare_out.mkdir()
        bare = run.PlatformGuard()
        bare.arm({"kind": "test"}, bare_out)
        bare.finish()
        self.assertFalse((bare_out / "platform").exists())
        # a record that cannot be written never raises: the cleanup still runs
        blocked = self.tmp / "blocked"
        blocked.mkdir()
        (blocked / "platform").write_text("a file where the folder should be")
        guard = run.PlatformGuard()
        guard.arm(spec, blocked)
        self.assertTrue(guard.finish()["ok"])


class ResumeNoteTest(PlatformCase):
    NOTE = "The platform was reset when the last session ended: deploy again what you still need."

    def test_the_note_is_a_non_empty_string_or_the_case_is_refused(self):
        for bad in ("", "  ", 3, ["x"], None):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", {"cleanup": "c", "resume_note": bad})
            self.assertIn("resume_note", str(raised.exception))
        self.assertEqual(run.validate_platform("c", {"cleanup": "c", "resume_note": self.NOTE})["resume_note"], self.NOTE)

    def test_the_prompt_without_a_note_is_what_it_always_was(self):
        cli = Path("/p/cli")
        self.assertEqual(run.resume_prompt("/r/run", cli), run.resume_prompt("/r/run", cli, None))
        self.assertEqual(run.resume_prompt("/r/run", cli), run.resume_prompt("/r/run", cli, ""))
        self.assertTrue(run.resume_prompt("/r/run", cli).endswith("Never end the turn while a ShipLoop command is still running."))
        for run_dir in ("/r/run", None):
            self.assertEqual(run.resume_prompt(run_dir, cli, self.NOTE), run.resume_prompt(run_dir, cli) + " " + self.NOTE)

    def resumed_prompt(self, out: Path) -> str:
        return next(out.glob("resume-grok-*.txt")).read_text().replace(str(out), "<out>")

    def test_a_resumed_run_whose_platform_was_reset_is_told_so_and_a_case_without_a_note_is_not(self):
        texts = {}
        for tag, platform in (("note", self.platform(resume_note=self.NOTE)), ("plain", self.platform())):
            self.use_case(platform)
            _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0", tag=tag)
            out = Path(first["output"])
            self.assertTrue(first["platform"]["cleanup"]["ran"])
            self.resume("grok", out, "done")
            texts[tag] = self.resumed_prompt(out)
        self.assertEqual(texts["note"], texts["plain"] + " " + self.NOTE)
        self.assertNotIn("reset", texts["plain"])

    def test_no_note_when_the_earlier_segment_did_not_clean_or_when_nothing_starts(self):
        self.use_case(self.platform(resume_note=self.NOTE))
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        record = json.loads((out / "result.json").read_text())
        record["platform"]["cleanup"]["ran"] = False
        (out / "result.json").write_text(json.dumps(record))
        self.resume("grok", out, "done")
        self.assertNotIn(self.NOTE, self.resumed_prompt(out))
        spec = {"resume_note": self.NOTE}
        self.assertIsNone(run.resume_platform_note(spec, {"cleanup": {"ran": True}}, regrade=True))
        self.assertIsNone(run.resume_platform_note({}, {"cleanup": {"ran": True}}, regrade=False))
        self.assertIsNone(run.resume_platform_note(None, {"cleanup": {"ran": True}}, regrade=False))
        self.assertIsNone(run.resume_platform_note(spec, {}, regrade=False))
        self.assertEqual(run.resume_platform_note(spec, {"cleanup": {"ran": True}}, regrade=False), self.NOTE)


class ResumeAfterCrashTest(ResumeNoteTest):
    """H-4: a run that ended by Ctrl-C or a crash ran its cleanup but never wrote result.json; the resumed model is told all the same."""

    def test_a_resume_after_a_ctrl_c_or_a_crash_is_told_the_platform_was_reset(self):
        self.use_case(self.platform(resume_note=self.NOTE))
        for tag, exception in (("ctrl-c", KeyboardInterrupt()), ("crash", RuntimeError("boom"))):
            with self.subTest(exception=type(exception).__name__):
                with mock.patch.object(run, "summarize_events", side_effect=exception), \
                        contextlib.redirect_stdout(io.StringIO()), self.assertRaises(type(exception)):
                    self.invoke("grok", "stuck", "--max-resumes", "0", tag=tag)
                out = self.tmp / f"out-grok-{tag}"
                self.assertFalse((out / "result.json").exists(), "the run never reached its result")
                self.assertTrue(json.loads((out / "platform" / "cleanup-record.json").read_text())["ran"])
                self.resume("grok", out, "done")
                self.assertIn(self.NOTE, self.resumed_prompt(out))

    def test_a_resume_after_a_crash_before_the_model_started_is_not_told(self):
        """No cleanup record, no reset: a platform that was never touched needs no note."""
        self.use_case(self.platform(resume_note=self.NOTE))
        self.invoke("grok", "stuck", "--max-resumes", "0")
        out = self.tmp / "out-grok-a"
        (out / "result.json").unlink()
        (out / "platform" / "cleanup-record.json").unlink()
        self.resume("grok", out, "done")
        self.assertNotIn(self.NOTE, self.resumed_prompt(out))
        self.assertIsNone(run.earlier_cleanup_record(out / "platform"), "no record there, and none inside platform/platform")
        (out / "platform" / "cleanup-record.json").write_text("[1]")
        self.assertIsNone(run.earlier_cleanup_record(out), "a record that is not an object is no record")


class CheckTimeoutTest(PlatformCase):
    """H3-1: platform.check_timeout is the ceiling of the case's own checks in that case's run, and nowhere else."""

    def timeouts(self, platform: dict | None, *extra: str, mode: str = "done") -> list:
        self.use_case(platform)
        with mock.patch.object(run, "run_checks", wraps=run.run_checks) as spy:
            code, result, _ = self.invoke("grok", mode, *extra, tag=f"t{len(list(self.tmp.glob('out-grok-*')))}")
        self.assertEqual(code, 0, result)
        return [call.kwargs["timeout"] for call in spy.call_args_list]

    def test_a_case_with_one_has_its_checks_run_with_it(self):
        self.assertEqual(self.timeouts(self.platform(check_timeout=900)), [900])
        self.assertEqual(self.timeouts(self.platform(check_timeout=60)), [60])

    def test_a_platform_without_one_and_a_case_without_a_platform_keep_the_default(self):
        self.assertEqual(run.CHECK_TIMEOUT, 180)
        self.assertEqual(self.timeouts(self.platform()), [180])
        self.assertEqual(self.timeouts(None), [180])

    def test_the_default_of_run_checks_is_the_constant_and_a_check_that_ends_in_time_passes(self):
        self.assertEqual(inspect.signature(run.run_checks).parameters["timeout"].default, run.CHECK_TIMEOUT)
        self.assertEqual(run.PRODUCT_AT_STOP_TIMEOUT, 180, "the product-at-stop ceiling is its own and does not follow the case")
        (self.tmp / "w").mkdir()
        self.assertTrue(run.run_checks(self.tmp / "w", ["true"], timeout=run.CHECK_TIMEOUT)[0]["pass"])

    def test_a_regrade_runs_the_checks_it_asks_again_with_the_case_s_ceiling(self):
        self.use_case(self.platform(check_timeout=900))
        _, first, _ = self.invoke("grok", "done", "--keep-platform")
        out = Path(first["output"])
        (out / "result.json").unlink()  # nothing to restate: the checks are asked of the platform again
        with mock.patch.object(run, "run_checks", wraps=run.run_checks) as spy:
            self.resume("grok", out, "done", "--grade-only")
        self.assertEqual([call.kwargs["timeout"] for call in spy.call_args_list], [900])


class UnchangedCaseTest(PlatformCase):
    def test_a_case_without_a_platform_gains_nothing_from_any_of_this(self):
        self.use_case(None)
        _, result, printed = self.invoke("grok", "stuck", "--max-resumes", "0")
        out = Path(result["output"])
        resumed, _ = self.resume("grok", out, "done")
        prompt = next(out.glob("resume-grok-*.txt")).read_text()
        self.assertTrue(prompt.endswith("Never end the turn while a ShipLoop command is still running."))
        self.assertEqual(prompt.count("reset"), 0)
        for done in (result, resumed):
            self.assertNotIn("platform", done)
            self.assertNotIn("guard", json.dumps(done["environment"]))
        for name in ("platform", ".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile"):
            self.assertFalse((out / name).exists() or (out / "home" / name).exists(), name)
        self.assertNotIn("guard saw", printed)
        self.assertEqual(self.verbs(), [])


class HostAllowTest(unittest.TestCase):
    """platform.host_allow: the permission rules a case asks the host to pre-approve. Found 2026-10-17: Grok's auto mode blocked a
    real `sf project deploy start --target-org de` three times ("not requested by the user") once a session restart left it only
    the generic resume prompt; the run ended blocked."""

    RULES = ("Bash(sf *)", "Bash(cd *)")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def argv(self, host: str, **extra) -> list[str]:
        return hosts.host(host, host).argv(prompt="p", prompt_file=self.tmp / "p.txt", cwd=self.tmp, model="m", effort="medium",
                                           permission_mode="auto", max_turns=5, **extra)

    def test_grok_gets_one_allow_flag_per_rule_in_order(self):
        argv = self.argv("grok", allow=self.RULES)
        flags = [argv[i + 1] for i, token in enumerate(argv) if token == "--allow"]
        self.assertEqual(flags, list(self.RULES))
        self.assertEqual(argv.count("--allow"), 2)

    def test_a_launch_without_rules_is_what_it_always_was(self):
        for host in ("grok", "claude", "codex"):
            with self.subTest(host=host):
                self.assertEqual(self.argv(host), self.argv(host, allow=()))
                self.assertNotIn("--allow", self.argv(host))
                self.assertNotIn("--allowedTools", self.argv(host))

    def test_claude_gets_one_allowed_tools_list(self):
        argv = self.argv("claude", allow=self.RULES)
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Bash(sf *),Bash(cd *)")

    def test_codex_runs_with_approval_never_so_there_is_nothing_to_pre_approve(self):
        self.assertEqual(self.argv("codex", allow=self.RULES)[:-1], self.argv("codex")[:-1])

    def test_the_case_object_accepts_a_list_of_rules_and_refuses_anything_else(self):
        self.assertEqual(run.validate_platform("c", {"cleanup": "c", "host_allow": list(self.RULES)})["host_allow"], list(self.RULES))
        for bad in ("Bash(sf *)", [""], ["Bash(sf *)", 3], [None], {"a": 1}):
            with self.subTest(bad=bad), self.assertRaises(SystemExit) as raised:
                run.validate_platform("c", {"cleanup": "c", "host_allow": bad})
            self.assertIn("host_allow", str(raised.exception))

    def test_the_chess_salesforce_case_allows_the_guarded_sf_and_the_cd_that_precedes_it(self):
        rules = run.case_platform("chess-salesforce")["host_allow"]
        self.assertIn("Bash(sf *)", rules)
        self.assertIn("Bash(cd *)", rules)


class ResumeGateTest(PlatformCase):
    """A resume of a run started on --source checkout is not put through the marketplace gate. Found 2026-10-17: the gate refused
    the resume of live run 2 because its local HEAD was, by design, ahead of origin/main ("publish them first")."""

    AHEAD = {"origin_main": "a" * 40, "local_head": "b" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
             "shiploop_version": None, "unreleased": [], "ci": "success"}

    def resume_ahead(self, out: Path) -> str:
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(run, "released_versions", return_value=self.AHEAD):
            run.main(["--host", "grok", f"--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), "--max-resumes", "0"])
        return printed.getvalue()

    def first_run(self) -> Path:
        self.use_case(self.platform())
        _, first, _ = self.invoke("grok", "stuck", "--max-resumes", "0")
        return Path(first["output"])

    def test_a_checkout_run_resumes_although_its_local_head_is_ahead_of_origin_main(self):
        out = self.first_run()
        recorded = json.loads((out / "invocation.json").read_text())
        self.assertEqual(recorded["versions"]["source"], "checkout")
        self.resume_ahead(out)  # must not raise
        self.assertTrue((out / "result.json").is_file())

    def test_a_marketplace_run_is_still_gated(self):
        out = self.first_run()
        recorded = json.loads((out / "invocation.json").read_text())
        recorded["versions"]["source"] = "marketplace"
        (out / "invocation.json").write_text(json.dumps(recorded))
        with self.assertRaisesRegex(SystemExit, "version gate: .*publish them first"):
            self.resume_ahead(out)


if __name__ == "__main__":
    unittest.main()
