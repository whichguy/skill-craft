#!/usr/bin/env python3
"""No-model, no-platform checks for the E2E harness's `platform` hooks (test/shiploop_e2e/run.py).

A case may carry a `platform` object (preflight, before, cleanup, home_links); the harness runs the commands it names and knows
nothing about any platform. Here the commands are one tiny Python script written below, the hosts are fake `grok` and `claude`
executables, and no real platform, org or model is ever reached. They say nothing about a live platform.

  preflight  before any model call, with the host's environment: non-zero aborts
  before     once, on a fresh run only
  home_links symlinks of existing names in the real HOME into a throwaway HOME (Grok, Codex), recorded
  cleanup    after grading, always: success, failure, crash, KeyboardInterrupt; a failure is printed loudly
  model_bin  a guarded stand-in command written to <output>/platform/bin and put first on the host's PATH (real HOME inside)
  scrub      one function through which every stored or printed command output goes
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
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

# FAKE_MODE: done (product + done run), stuck (ends with ShipLoop active), fail (exits 1 with no work). Every start leaves
# PLAT_MODEL_MARK, so a platform command can say whether the model had started when it ran. A model that "shows" a credential
# puts it in its event stream, as a tool result would.
FAKE_GROK = f"""#!{sys.executable}
import json, os, sys
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
print(json.dumps({{"type": "tool_call", "toolName": "run_terminal_command", "rawInput": {{"command": "sf org display --json"}}}}))
print(json.dumps({{"type": "text", "data": '{{"accessToken": "{TOKEN}"}}'}}))
mode = os.environ.get("FAKE_MODE")
if mode == "fail":
    sys.exit(1)
if mode == "done":
    import shutil
    shutil.rmtree(".shiploop", ignore_errors=True)
    product()
elif mode == "stuck":
    Path(".shiploop").mkdir(exist_ok=True)
    store.write_record(Path(".shiploop/state.md"), {{"status": "active", "stage": "test-refine", "revision": 25}})
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
        for var in ("PLAT_FAIL", "FAKE_MODE"):
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

    def resume(self, host: str, out: Path, mode: str, *extra: str) -> tuple[dict, str]:
        os.environ["FAKE_MODE"] = mode
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": "9.9.9",
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
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

    def test_a_well_formed_platform_is_returned_as_given(self):
        spec = {"kind": "k", "preflight": "p", "before": "b", "cleanup": "c", "home_links": [".sf"], "org": "x",
                "model_bin": {"sf": "guard --org x"}}
        self.assertIs(run.validate_platform("c", spec), spec)


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


if __name__ == "__main__":
    unittest.main()
