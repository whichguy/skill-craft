#!/usr/bin/env python3
"""Hermetic tests of the guarded `sf` the harness puts on the model's PATH (platform.model_bin; checks/sf_guard.py).

The wrapper under test is the one run.write_model_bin writes, the "real" sf behind it is test/shiploop_e2e/fake_sf.py (or a tiny
stub), and no real org, real `sf` or model is ever reached. What these prove, one test per rule:

  deny    a command that shows credentials, changes the CLI or the org destructively, or is unknown never reaches sf (exit 2)
  pin     an org-talking command must name the case's org on every --target-org / -o; none or another is refused
  pass    the build's own commands (deploy --source-dir, apex run test --synchronous, data query, --version, org list) reach sf
  log     one JSON line per call in $E2E_PLATFORM_DIR/sf-calls.jsonl, no stdout, no credential
  scrub   a token in sf's output never reaches the model; the exit code and everything else pass through
  wrapper no recursion, the real HOME, the baked E2E_* variables
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e" / "checks"))
import run  # noqa: E402
import sf_guard  # noqa: E402

CHECKS = ROOT / "test" / "shiploop_e2e" / "checks"
FAKE_SF = ROOT / "test" / "shiploop_e2e" / "fake_sf.py"
ORG = "fake-org"
TOKEN = "FAKE-TOKEN-DO-NOT-LOG"
SESSION = "00D5g000004AbCd!AQEAQFakeSessionTokenValue0123456789abcdefghijklmnop"
GUARD = f"{shlex.quote(sys.executable)} \"$E2E_CHECKS/sf_guard.py\" --org {ORG} --prefix SLChess --"

# A stand-in `sf` that prints what it was given and a credential, then exits with a code the test chose.
STUB = f"""#!{sys.executable}
import json, os, sys
print(json.dumps({{"argv": sys.argv[1:], "home": os.environ.get("HOME"), "e2e": sorted(k for k in os.environ if k.startswith("E2E_")),
                  "accessToken": "{TOKEN}", "note": "{SESSION}"}}))
print("stderr says refreshToken={TOKEN} and {SESSION}", file=sys.stderr)
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""


class GuardCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.real_home = self.tmp / "real-home"
        self.real_home.mkdir()
        self.work = self.tmp / "work"
        self.work.mkdir()
        self.platform_dir = self.tmp / "out" / "platform"
        self.platform_dir.mkdir(parents=True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        self.use_sf(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(FAKE_SF))} \"$@\"\n")
        self.wrappers = run.write_model_bin({"sf": GUARD, "sfdx": GUARD.replace("--prefix SLChess --", "--prefix SLChess --deny-all --")},
                                            self.platform_dir, self.real_home)
        self.state = self.tmp / "state.json"
        self.fake_log = self.tmp / "fake.log"

    def use_sf(self, body: str) -> None:
        path = self.shim / "sf"
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def env(self, **extra) -> dict:
        base = {"PATH": os.pathsep.join([str(self.platform_dir / "bin"), str(self.shim), "/usr/bin", "/bin"]),
                "HOME": str(self.tmp / "throwaway-home"), "FAKE_SF_STATE": str(self.state), "FAKE_SF_LOG": str(self.fake_log),
                "FAKE_SF_ORGS": ORG}
        base.update(extra)
        return base

    def sf(self, *argv: str, name: str = "sf", env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([str(self.platform_dir / "bin" / name), *argv], cwd=self.work, env=env or self.env(),
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def reached(self) -> list[dict]:
        return [json.loads(line) for line in self.fake_log.read_text().splitlines()] if self.fake_log.exists() else []

    def calls(self) -> list[dict]:
        path = self.platform_dir / sf_guard.LOG_NAME
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_denied(self, *argv: str, reason: str = "", name: str = "sf") -> None:
        before_reached, before_calls = len(self.reached()), len(self.calls())
        done = self.sf(*argv, name=name)
        self.assertEqual(done.returncode, 2, (argv, done.stdout, done.stderr))
        self.assertIn("sf_guard: denied", done.stderr)
        self.assertIn(reason, done.stderr, argv)
        self.assertEqual(done.stdout, "")
        self.assertEqual(len(self.reached()), before_reached, f"{argv} reached sf")
        calls = self.calls()
        self.assertEqual(len(calls), before_calls + 1)
        self.assertEqual(calls[-1]["decision"], "denied")
        self.assertEqual(calls[-1]["argv"], list(argv))

    def assert_reaches_sf(self, *argv: str) -> subprocess.CompletedProcess:
        before_reached = len(self.reached())
        done = self.sf(*argv)
        self.assertNotIn("sf_guard:", done.stderr, (argv, done.stderr))
        self.assertEqual(len(self.reached()), before_reached + 1, (argv, done.stdout, done.stderr))
        self.assertEqual(self.calls()[-1]["decision"], "allowed")
        return done


class DenyTest(GuardCase):
    def test_commands_that_show_credentials_are_denied_without_reaching_sf(self):
        self.assert_denied("org", "display", "--target-org", ORG, "--json", reason="access token")
        self.assert_denied("org:display", "--target-org", ORG, "--json", reason="access token")
        self.assert_denied("org", "display", "user", "-o", ORG, reason="access token")
        self.assert_denied("org", "open", "--url-only", "--target-org", ORG, reason="session id")
        self.assert_denied("org", "login", "web", "--alias", "x", reason="signs in")
        self.assert_denied("org", "logout", "--target-org", ORG, "--no-prompt", reason="signs out")
        self.assert_denied("auth", "list", reason="authorization")
        self.assert_denied("login", reason="signs in")
        self.assert_denied("logout", reason="signs out")

    def test_commands_that_change_the_cli_or_the_org_are_denied(self):
        self.assert_denied("org", "create", "scratch", "-f", "x.json", reason="creates an org")
        self.assert_denied("org", "delete", "scratch", "--target-org", ORG, reason="deletes an org")
        self.assert_denied("config", "set", "target-org=other", reason="configuration")
        self.assert_denied("config", "unset", "target-org", reason="configuration")
        self.assert_denied("alias", "set", "de=other@example.com", reason="aliases")
        self.assert_denied("alias", "unset", "de", reason="aliases")
        self.assert_denied("plugins", "install", "x", reason="changes the CLI")
        self.assert_denied("update", reason="changes the CLI")
        self.assert_denied("project", "delete", "source", "--target-org", ORG, reason="deletes metadata")

    def test_data_writes_are_denied(self):
        for verb in ("delete", "create", "update", "upsert", "import", "export", "bulk"):
            self.assert_denied("data", verb, "record", "--target-org", ORG, "--json", reason=f"`data {verb}`")

    def test_a_destructive_or_wildcard_deploy_is_denied(self):
        for flag in ("--post-destructive-changes", "--pre-destructive-changes"):
            self.assert_denied("project", "deploy", "start", "--manifest", "package.xml", flag, "destructiveChanges.xml",
                               "--target-org", ORG, "--json", reason=flag)
            self.assert_denied("project", "deploy", "start", f"{flag}=d.xml", "--target-org", ORG, reason=flag)
        self.assert_denied("project", "deploy", "start", "--metadata-dir", "mdapi", "--target-org", ORG, reason="--metadata-dir")
        (self.work / "package.xml").write_text("<Package><types><members>*</members><name>ApexClass</name></types></Package>")
        self.assert_denied("project", "deploy", "start", "--manifest", "package.xml", "--target-org", ORG, reason="wildcard")
        self.assert_denied("project", "deploy", "start", "-x", "package.xml", "-o", ORG, reason="wildcard")
        (self.work / "spaced.xml").write_text("<Package><types><members>\n  *  \n</members></types></Package>")
        self.assert_denied("project", "deploy", "validate", "--manifest=spaced.xml", "--target-org", ORG, reason="wildcard")

    def test_an_auth_url_in_any_argument_is_denied(self):
        self.assert_denied("data", "query", "-q", "select Id from ApexClass", "--target-org", ORG, "--sfdx-url-file", "u.txt",
                           reason="auth URLs")
        done = self.sf("data", "query", "--sfdxAuthUrl=force://x@y", "--target-org", ORG)
        self.assertEqual(done.returncode, 2)
        self.assertIn("auth URLs", done.stderr)
        self.assertEqual(self.reached(), [])
        self.assertEqual(self.calls()[-1]["argv"][2], "--sfdxAuthUrl=[redacted]")  # the log keeps no auth URL either

    def test_an_unknown_command_is_denied_by_default(self):
        self.assert_denied("force", "source", "deploy", "--target-org", ORG, reason="allow list")
        self.assert_denied("org", "list", "auth", reason="allow list")
        self.assert_denied("apex", "tail", "log", "--target-org", ORG, reason="allow list")
        self.assert_denied("lightning", "dev", "component", "--target-org", ORG, reason="allow list")
        self.assert_denied("data", "resume", "--target-org", ORG, reason="allow list")
        self.assert_denied("totally-unknown", reason="allow list")

    def test_flags_before_the_command_and_a_bare_double_dash_are_denied(self):
        self.assert_denied("--json", "org", "list", reason="before the command")
        self.assert_denied("data", "query", "--", "--target-org", ORG, reason="`--`")
        self.assert_denied("org", "list", "--clean", reason="--clean")

    def test_sfdx_is_denied_whatever_it_is_given(self):
        self.assert_denied("force:org:display", "--targetusername", ORG, name="sfdx", reason="not available in this run")
        self.assert_denied("--version", name="sfdx", reason="not available in this run")


class PinTest(GuardCase):
    def test_a_command_that_talks_to_an_org_must_name_the_case_s_org(self):
        for argv in (("data", "query", "-q", "SELECT Name FROM ApexClass", "--use-tooling-api", "--json"),
                     ("project", "deploy", "start", "--source-dir", "force-app"),
                     ("project", "deploy", "start"),
                     ("project", "deploy", "validate"), ("project", "deploy", "report"), ("project", "deploy", "quick"),
                     ("project", "deploy", "cancel"), ("project", "deploy", "resume"),
                     ("project", "retrieve", "start"), ("project", "retrieve", "preview"),
                     ("apex", "run", "--file", "x.apex"), ("apex", "run", "test", "--synchronous"),
                     ("apex", "get", "test"), ("apex", "get", "log"), ("apex", "list", "log"),
                     ("data", "get", "record"), ("sobject", "list"), ("sobject", "describe"),
                     ("org", "list", "metadata"), ("org", "list", "metadata-types")):
            self.assert_denied(*argv, reason="must carry --target-org")
        self.assertEqual(self.reached(), [])

    def test_another_org_or_a_mixed_pair_is_refused_in_every_spelling(self):
        for flags in (["--target-org", "other"], ["-o", "other"], ["--target-org=other"], ["-oother"], ["-o=other"],
                      ["--target-org", ORG, "-o", "other"], ["--target-org", ""], ["--target-org"]):
            self.assert_denied("data", "query", "-q", "SELECT Name FROM ApexClass", *flags, "--json", reason="--target-org must be")

    def test_the_right_org_passes_in_every_spelling(self):
        for flags in (["--target-org", ORG], ["-o", ORG], ["--target-org", ORG, "-o", ORG]):
            done = self.assert_reaches_sf("data", "query", "--use-tooling-api", "-q", "SELECT COUNT() FROM ApexClass", *flags, "--json")
            self.assertEqual(json.loads(done.stdout)["status"], 0, done.stdout)
        self.assertEqual({entry["target_org"] for entry in self.reached()}, {ORG})
        # Spellings the fake does not parse: the policy alone decides (the real CLI reads all of them).
        for flags in ([f"--target-org={ORG}"], [f"-o{ORG}"], [f"-o={ORG}"]):
            allowed, reason = sf_guard.decide(["data", "query", "-q", "SELECT Name FROM ApexClass", *flags], ORG)
            self.assertTrue(allowed, (flags, reason))

    def test_a_command_never_falls_back_to_the_default_org(self):
        # The fake is the second wall: it also refuses a missing --target-org. The guard stops the call first.
        done = self.sf("data", "query", "-q", "SELECT Name FROM ApexClass", "--json")
        self.assertEqual(done.returncode, 2)
        self.assertEqual(self.reached(), [])

    def test_from_org_of_a_generated_manifest_is_pinned_too(self):
        self.assert_denied("project", "generate", "manifest", "--from-org", "other", reason="--from-org")
        self.assert_reaches_sf("project", "generate", "manifest", "--from-org", ORG)


class PassTest(GuardCase):
    def test_the_build_s_own_commands_reach_sf_and_change_the_fake_org(self):
        classes = self.work / "force-app" / "main" / "default" / "classes"
        classes.mkdir(parents=True)
        (classes / "SLChessEngine.cls").write_text("public class SLChessEngine {}")
        (classes / "SLChessEngineTest.cls").write_text("@IsTest private class SLChessEngineTest {}")
        (self.work / "force-app" / "main" / "default" / "lwc" / "slChessBoard").mkdir(parents=True)
        deployed = self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json")
        self.assertEqual(json.loads(deployed.stdout)["result"]["status"], "Succeeded")
        state = json.loads(self.state.read_text())
        self.assertIn("SLChessEngine", state["apex_classes"])
        self.assertIn("slChessBoard", state["lwc"])
        tested = self.assert_reaches_sf("apex", "run", "test", "--class-names", "SLChessEngineTest", "--synchronous",
                                        "--result-format", "json", "--target-org", ORG, "--json")
        self.assertEqual(json.loads(tested.stdout)["result"]["summary"]["outcome"], "Passed")
        anonymous = self.work / "x.apex"
        anonymous.write_text("System.debug('RESULT|a|1');")
        self.assert_reaches_sf("apex", "run", "--file", str(anonymous), "--target-org", ORG, "--json")
        # The prompt's own spelling: no --source-dir, the colon form of the command.
        self.assert_reaches_sf("project:deploy:start", "--target-org", ORG, "--json")

    def test_a_manifest_without_a_wildcard_passes(self):
        (self.work / "package.xml").write_text("<Package><types><members>SLChessEngine</members><name>ApexClass</name></types></Package>")
        self.assert_reaches_sf("project", "deploy", "start", "--manifest", "package.xml", "--target-org", ORG, "--json")

    def test_local_commands_pass_without_an_org(self):
        self.assert_reaches_sf("--version")
        self.assert_reaches_sf("--help")
        self.assert_reaches_sf("help", "project", "deploy", "start")
        self.assert_reaches_sf("project", "generate", "--name", "x")
        self.assert_reaches_sf("lightning", "generate", "component", "--name", "slChessBoard", "--type", "lwc")
        done = self.assert_reaches_sf("org", "list", "--json")
        self.assertEqual(json.loads(done.stdout)["result"]["nonScratchOrgs"][0]["connectedStatus"], "Connected")

    def test_stdout_is_the_real_sf_s_byte_for_byte_warning_line_included(self):
        argv = ["data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--json"]
        env = self.env(FAKE_SF_WARN="1")
        direct = subprocess.run([str(self.shim / "sf"), *argv], env=env, capture_output=True, text=True, cwd=self.work)
        through = self.sf(*argv, env=env)
        self.assertEqual(through.returncode, direct.returncode)
        self.assertEqual(through.stdout, direct.stdout)
        self.assertTrue(through.stdout.startswith(" ›   Warning"))

    def test_sf_s_failure_exit_code_and_message_pass_through(self):
        done = self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--json",
                       env=self.env(FAKE_SF_FAIL="query"))
        self.assertEqual(done.returncode, 1)
        self.assertIn("query failed on request", done.stdout)
        entry = self.calls()[-1]
        self.assertEqual((entry["decision"], entry["exit"]), ("allowed", 1))


class LogAndScrubTest(GuardCase):
    def test_one_line_per_call_with_the_decision_and_no_credential(self):
        self.sf("org", "display", "--target-org", ORG, "--json")
        self.sf("org", "list", "--json")
        self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--json")
        self.sf("data", "query", "-q", "SELECT Name FROM ApexClass", "--json")
        entries = self.calls()
        self.assertEqual([e["decision"] for e in entries], ["denied", "allowed", "allowed", "denied"])
        self.assertEqual([e.get("exit") for e in entries], [None, 0, 0, None])
        for entry in entries:
            self.assertEqual(entry["org"], ORG)
            self.assertTrue(entry["ts"] and entry["reason"])
        self.assertNotIn("stdout", json.dumps(entries))
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        self.assertEqual(len(raw.splitlines()), 4)
        self.assertNotIn(TOKEN, raw)
        self.assertNotIn("FAKE-TOKEN", raw)

    def test_a_token_shaped_argument_is_scrubbed_in_the_log(self):
        self.sf("data", "query", "-q", f"SELECT Name FROM ApexClass -- {SESSION}", "--target-org", ORG)
        self.sf("org", "display", f"accessToken={TOKEN}")
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        self.assertNotIn(SESSION, raw)
        self.assertNotIn(TOKEN, raw)
        self.assertIn("[redacted]", raw)

    def test_a_token_in_sf_s_output_never_reaches_the_model_and_the_exit_code_does(self):
        self.use_sf(STUB)
        done = self.sf("data", "query", "-q", "x", "--target-org", ORG, env=self.env(STUB_EXIT="7"))
        self.assertEqual(done.returncode, 7)
        for stream in (done.stdout, done.stderr):
            self.assertNotIn(TOKEN, stream)
            self.assertNotIn(SESSION, stream)
            self.assertIn("[redacted]", stream)
        self.assertEqual(json.loads(done.stdout)["argv"], ["data", "query", "-q", "x", "--target-org", ORG])
        entry = self.calls()[-1]
        self.assertEqual(entry["exit"], 7)
        self.assertLessEqual(len(entry["stderr_head"]), 200)
        self.assertNotIn(TOKEN, json.dumps(entry))
        self.assertNotIn(SESSION, json.dumps(entry))

    def test_the_fake_s_org_display_token_would_be_scrubbed_if_the_command_were_ever_allowed(self):
        self.assertEqual(sf_guard.scrub(json.dumps({"accessToken": TOKEN, "id": "00D000000000000AAA"})),
                         json.dumps({"accessToken": "[redacted]", "id": "00D000000000000AAA"}))
        self.assertEqual(sf_guard.scrub(f"x {SESSION} y"), "x [redacted] y")
        self.assertEqual(sf_guard.scrub("sfdxAuthUrl: force://abc@def.my.salesforce.com"), "sfdxAuthUrl: [redacted]")

    def test_without_a_place_to_log_nothing_runs(self):
        env = {key: value for key, value in self.env().items() if not key.startswith("E2E_")}
        done = subprocess.run([sys.executable, str(CHECKS / "sf_guard.py"), "--org", ORG, "--prefix", "SLChess", "--",
                               "data", "query", "-q", "x", "--target-org", ORG], env=env, capture_output=True, text=True, cwd=self.work)
        self.assertEqual(done.returncode, 2)
        self.assertIn("could not be logged", done.stderr)
        self.assertEqual(self.reached(), [])


class WrapperTest(GuardCase):
    def test_the_wrapper_is_executable_and_bakes_the_real_home_and_the_harness_variables_as_literals(self):
        path = Path(self.wrappers["sf"])
        self.assertEqual(path, self.platform_dir / "bin" / "sf")
        self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
        text = path.read_text()
        self.assertTrue(text.startswith("#!/bin/sh\n"))
        self.assertIn(f"HOME={shlex.quote(str(self.real_home))}", text)
        self.assertIn(f"E2E_CHECKS={shlex.quote(str(CHECKS))}", text)
        self.assertIn(f"E2E_PLATFORM_DIR={shlex.quote(str(self.platform_dir))}", text)
        self.assertTrue(text.rstrip().endswith('"$@"'))

    def test_the_real_sf_runs_with_the_real_home_not_the_model_s(self):
        self.use_sf(STUB)
        done = self.sf("--version")
        seen = json.loads(done.stdout)
        self.assertEqual(seen["home"], str(self.real_home))
        self.assertNotEqual(seen["home"], self.env()["HOME"])

    def test_the_wrapper_does_not_call_itself(self):
        self.assert_reaches_sf("org", "list", "--json")
        self.assertEqual(len(self.reached()), 1)
        self.assertEqual(len(self.calls()), 1)

    def test_with_no_real_sf_after_the_wrapper_the_call_fails_cleanly_and_does_not_loop(self):
        env = self.env(PATH=os.pathsep.join([str(self.platform_dir / "bin"), "/usr/bin", "/bin"]))
        done = self.sf("org", "list", "--json", env=env)
        self.assertEqual(done.returncode, 127)
        self.assertIn("no real `sf`", done.stderr)

    def test_a_relative_path_entry_is_never_searched_for_sf(self):
        planted = self.work / "sf"
        planted.write_text("#!/bin/sh\necho planted\n")
        planted.chmod(0o755)
        env = self.env(PATH=os.pathsep.join([str(self.platform_dir / "bin"), ".", "", "/usr/bin", "/bin"]))
        done = self.sf("org", "list", "--json", env=env)
        self.assertEqual(done.returncode, 127)
        self.assertNotIn("planted", done.stdout)

    def test_the_fixed_flags_come_first_and_the_model_s_flags_are_its_own(self):
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "--", "data", "query", "--org", "x"]),
                         ("de", "P", False, ["data", "query", "--org", "x"]))
        self.assertEqual(sf_guard.parse_fixed(["--prefix", "P", "--org", "de", "--deny-all", "--", "--"]),
                         ("de", "P", True, ["--"]))
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "org", "list"]), ("de", "P", False, ["org", "list"]))


if __name__ == "__main__":
    unittest.main()
