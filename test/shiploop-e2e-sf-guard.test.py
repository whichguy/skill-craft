#!/usr/bin/env python3
"""Hermetic tests of the guarded `sf` the harness puts on the model's PATH (platform.model_bin; checks/sf_guard.py).

The wrapper under test is the one run.write_model_bin writes, the "real" sf behind it is test/shiploop_e2e/fake_sf.py (or a tiny
stub), and no real org, real `sf` or model is ever reached. What these prove, one test per rule:

  deny    a command that shows credentials, changes the CLI or the org destructively, or is unknown never reaches sf (exit 2);
          --flags-dir is denied on every command (the CLI reads flag values from it after the policy ran)
  pin     an org-talking command must name the case's org on every --target-org / -o; none or another is refused, whatever boolean
          short flag is fused in front of -o, and the old spellings (-u, --u, --targetusername, --fromorg) are refused; the real sf runs
          with SF_TARGET_ORG set to the case's org and no other default-org variable; `project deploy quick|cancel|resume` (they
          take the org from the CLI's global deploy cache) are not allowed, and `deploy report` needs a --job-id and no --use-most-recent
  scope   a deploy may carry only ApexClass, CustomTab, CustomApplication and FlexiPage named SLChess* and LightningComponentBundle
          named slChess*: every --source-dir tree, --metadata entry and --manifest (or the package directories of the
          sfdx-project.json at or above the working dir) is checked, with paths kept inside the project, however a flag is spelled
          (-rd, a value that starts with `-`, `link/../x`, a class file named like another type's meta file), and `-t` is the tests
          flag there, not a boolean; a manifest with a DOCTYPE or ENTITY declaration is refused; a deploy that would not wait
          (--async, --wait under 5 or not plain digits) is refused; a file named exactly `.gitkeep` (git's placeholder for an
          empty folder) is not judged, every other name is
  permset with --permission-sets (the battleship case) a deploy may also carry PermissionSet named SLBattle*, and `org assign permset`
          passes only with every --name/-n prefixed, the org pinned and no --on-behalf-of, a bare word or an unknown flag; without the
          flag (the chess case) both stay refused
  pass    the build's own commands (deploy --source-dir, apex run test --synchronous, data query, --version, org list), --help
          anywhere on an allowed command, and the local generate families reach sf
  log     a decision line before the call and an end line after it (same call id) in $E2E_PLATFORM_DIR/sf-calls.jsonl, no stdout, no
          credential; a call that cannot be logged, or that the guard cannot judge, is denied with a line; SIGTERM/SIGHUP/SIGINT are
          forwarded, logged as interrupted and exit 143
  scrub   a token in sf's output never reaches the model; the exit code and everything else pass through
  wrapper no recursion, the real HOME, the baked E2E_* variables, the real sf's environment (SF_TARGET_ORG = the case's org)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import signal
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
                  "sf_env": {{k: v for k, v in os.environ.items() if k.startswith(("SF_", "SFDX_"))}},
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
        self.write_wrappers()
        self.state = self.tmp / "state.json"
        self.fake_log = self.tmp / "fake.log"

    def write_wrappers(self, bins: dict | None = None, path: str | None = None) -> None:
        # Wrappers bind the operator's PATH when written; the model cannot select a different CLI at invocation.
        bins = bins or {"sf": GUARD,
                        **{name: GUARD.replace("--prefix SLChess --", f"--prefix SLChess --deny-all --name {name} --")
                           for name in ("sfdx", "osascript", "open")}}
        operator_path = path if path is not None else os.pathsep.join([
            str(self.platform_dir / "bin"), str(self.shim), "/usr/bin", "/bin"])
        with mock.patch.dict(os.environ, {"PATH": operator_path}):
            self.wrappers = run.write_model_bin(bins, self.platform_dir, self.real_home)

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

    def log_lines(self) -> list[dict]:
        path = self.platform_dir / sf_guard.LOG_NAME
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def calls(self) -> list[dict]:
        """The decision lines: one per call, whether or not it ran."""
        return [entry for entry in self.log_lines() if "end" not in entry]

    def ends(self) -> list[dict]:
        """The end lines: one per call that reached the real sf."""
        return [entry for entry in self.log_lines() if entry.get("end")]

    def assert_denied(self, *argv: str, reason: str = "", name: str = "sf") -> None:
        before_reached, before_calls = len(self.reached()), len(self.calls())
        done = self.sf(*argv, name=name)
        self.assertEqual(done.returncode, 2, (argv, done.stdout, done.stderr))
        self.assertIn(f"{name}: denied by this run's guard: ", done.stderr)
        self.assertIn(reason, done.stderr, argv)
        self.assertIn(f"{name}: this run allows only `sf`, only on org {ORG!r}", done.stderr)  # the scope, after every denial
        self.assertNotIn("sf_guard", done.stderr)  # no message names the guard's file
        self.assertNotIn(str(CHECKS), done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertEqual(len(self.reached()), before_reached, f"{argv} reached sf")
        calls = self.calls()
        self.assertEqual(len(calls), before_calls + 1)
        self.assertEqual(calls[-1]["decision"], "denied")
        self.assertEqual(calls[-1]["argv"], list(argv))

    def assert_reaches_sf(self, *argv: str) -> subprocess.CompletedProcess:
        before_reached = len(self.reached())
        done = self.sf(*argv)
        self.assertNotIn("denied by this run's guard", done.stderr, (argv, done.stderr))
        self.assertEqual(len(self.reached()), before_reached + 1, (argv, done.stdout, done.stderr))
        self.assertEqual(self.calls()[-1]["decision"], "allowed")
        self.assertEqual(self.ends()[-1]["call"], self.calls()[-1]["call"])
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

    def test_host_automation_is_denied_logged_by_name_and_not_counted_as_an_sf_call(self):
        self.assert_denied("-e", 'tell application "Browser" to open location "https://example.test"', name="osascript",
                           reason="`osascript` is not available in this run")
        self.assert_denied("https://example.test", name="open", reason="`open` is not available in this run")
        self.assertEqual([entry.get("name") for entry in self.calls()], ["osascript", "open"])
        out = self.platform_dir.parent
        (out / "events.jsonl").write_text("")
        self.assertEqual(run.guard_coverage(out)["guard_calls"], 0)  # stand-in lines are not the model's sf calls
        self.assert_denied("org", "display", "--target-org", ORG, reason="access token")
        self.assertEqual(run.guard_coverage(out)["guard_calls"], 1)
        self.assertNotIn("name", self.calls()[-1])

    def test_the_salesforce_case_stands_in_for_sfdx_and_host_automation(self):
        case = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())["chess-salesforce"]
        bins = case["platform"]["model_bin"]
        self.assertEqual(set(bins), {"sf", "sfdx", "osascript", "open"})
        for name in ("sfdx", "osascript", "open"):
            self.assertIn(f"--deny-all --name {name} --", bins[name])
        self.assertNotIn("--deny-all", bins["sf"])


class ScopeLineTest(GuardCase):
    """The guard tells the model what the run allows, so the model need not read the guard's source."""

    def test_help_prints_the_run_s_scope_after_the_cli_s_own_help(self):
        for argv in (("--help",), ("project", "deploy", "start", "--help"), ("help",)):
            done = self.sf(*argv)
            self.assertEqual(self.calls()[-1]["decision"], "allowed", argv)  # reached the CLI (the fake's exit code passes through)
            scope = done.stderr.strip().splitlines()[-1]
            self.assertTrue(scope.startswith(f"sf: this run allows only `sf`, only on org {ORG!r}"), (argv, scope))
            self.assertIn("deploys: ApexClass, CustomTab, CustomApplication, FlexiPage named SLChess*", scope)
            self.assertIn("commands: ", scope)
            self.assertNotIn("sf_guard", done.stderr)
        done = self.sf("org", "list", "--json")  # not a help call: the CLI's output only
        self.assertNotIn("this run allows", done.stderr)

    def test_a_denial_that_lists_the_allowed_commands_does_not_list_them_twice(self):
        done = self.sf("totally-unknown")
        self.assertEqual(done.stderr.count("apex run test"), 1, done.stderr)
        done = self.sf("org", "display", "--target-org", ORG)
        self.assertEqual(done.stderr.count("apex run test"), 1, done.stderr)


class PinTest(GuardCase):
    def test_a_command_that_talks_to_an_org_must_name_the_case_s_org(self):
        for argv in (("data", "query", "-q", "SELECT Name FROM ApexClass", "--use-tooling-api", "--json"),
                     ("project", "deploy", "start", "--source-dir", "force-app"),
                     ("project", "deploy", "start"),
                     ("project", "deploy", "validate"), ("project", "deploy", "report"),
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

    def test_deploy_quick_cancel_and_resume_are_not_allowed_whatever_they_carry(self):
        # They take the org from the CLI's global deploy cache (~/.sf/deploy-cache.json, which also holds the owner's own deploys), so
        # a right --target-org does not pin them: not in the allow list at all.
        job = "0Af000000000000AAA"
        for verb in ("quick", "cancel", "resume"):
            for flags in ([], ["--target-org", ORG], ["-o", ORG, "--job-id", job], ["-o", ORG, "--use-most-recent"], ["-o", ORG, "-r"],
                          ["-i", job, "-o", ORG, "--wait", "10"], ["--help"]):
                self.assert_denied("project", "deploy", verb, *flags, reason="not in the allow list")
            self.assert_denied(f"project:deploy:{verb}", "--target-org", ORG, reason="not in the allow list")
        done = self.sf("project", "deploy", "quick", "--target-org", ORG)
        allowed = done.stderr.split("allowed:")[1]
        self.assertIn("project deploy start", allowed)
        self.assertIn("project deploy report", allowed)
        for verb in ("quick", "cancel", "resume"):
            self.assertNotIn(f"project deploy {verb}", allowed)
        self.assertEqual(self.reached(), [])

    def test_deploy_report_needs_a_job_id_and_is_never_the_most_recent(self):
        job = "0Af000000000000AAA"
        report = ("project", "deploy", "report")
        for flags in (["--job-id", job], ["-i", job], [f"--job-id={job}"], [f"-i{job}"], [f"-i={job}"], ["--job-id", job, "--wait", "10"]):
            allowed, reason = sf_guard.decide([*report, *flags, "--target-org", ORG], ORG)
            self.assertTrue(allowed, (flags, reason))
        # The cached deploy of any org: --use-most-recent, -r alone, -r fused in front of another flag, with or without a job id.
        for flags in (["--use-most-recent", "--target-org", ORG], ["--target-org", ORG, "--use-most-recent"], ["-o", ORG, "--use-most-recent=true"],
                      ["-r", "--target-org", ORG], ["--target-org", ORG, "-r"], ["-ro", ORG], ["-ri", job, "-o", ORG],
                      ["--job-id", job, "-r", "-o", ORG], ["-i", job, "--use-most-recent", "-o", ORG], ["-rr", "-o", ORG]):
            self.assert_denied(*report, *flags, reason="--use-most-recent")
        # No job id: the CLI would report the newest cached deploy.
        for flags in (["--target-org", ORG], ["-o", ORG, "--wait", "10"], ["-o", ORG, "--job-id"], ["-o", ORG, "--job-id", ""]):
            self.assert_denied(*report, *flags, reason="must carry --job-id")
        self.assert_reaches_sf(*report, "--job-id", job, "--target-org", ORG, "--json")
        self.assertEqual(len(self.reached()), 1)

    def test_the_old_spellings_of_the_org_flags_are_denied_on_every_command(self):
        # -u and --targetusername still select the org on many commands and --fromorg is --from-org's old name; the guard reads none of
        # them. The CLI errors when --target-org is given twice, so the attack pairs one with a pin the CLI swallows as another flag's
        # value (`--loglevel --target-org=de`).
        decoy = ["--loglevel", f"--target-org={ORG}"]
        commands = (("apex", "run", "--file", "x.apex"), ("apex", "run", "test", "--synchronous"), ("apex", "get", "test"), ("apex", "get", "log"),
                    ("apex", "list", "log"), ("data", "query", "-q", "SELECT Name FROM ApexClass"), ("data", "get", "record"),
                    ("sobject", "describe"), ("sobject", "list"), ("org", "list", "metadata"), ("org", "list", "metadata-types"),
                    ("project", "retrieve", "start"), ("project", "deploy", "start"), ("org", "list"), ("project", "generate", "manifest"))
        for command in commands:
            # `--u` is the alias `u` written as a long flag (oclif looks a long flag up among the aliases too); `-ku` is -k (a boolean of
            # `org list metadata-types`) in front of -u.
            for flags in (["-u", "other"], ["-uother"], ["-u=other"], ["--targetusername", "other"], ["--targetusername=other"],
                          ["-u", ORG], ["--targetusername", ORG], ["--fromorg", "other"], ["--fromorg=other"], ["--fromorg", ORG],
                          ["-tu", "other"], ["-cyu", "other"], ["--u", "other"], ["--u=other"], ["--u", ORG], ["--u=" + ORG],
                          ["-ku", "other"], ["-ku", ORG]):
                for tail in ([], decoy, ["--target-org", ORG]):
                    allowed, reason = sf_guard.decide([*command, *flags, *tail], ORG, prefix="SLChess", cwd=str(self.work))
                    self.assertFalse(allowed, (command, flags, tail))
                    self.assertIn("old spellings", reason)
        # Through the wrapper: refused before the real sf is reached, and the log keeps the call.
        self.assert_denied("project", "generate", "manifest", "--fromorg", "other", reason="old spellings")
        self.assert_denied("apex", "run", "test", "-u", "other", *decoy, reason="old spellings")
        self.assert_denied("data", "query", "-q", "SELECT Name FROM ApexClass", "--targetusername", "other", *decoy, reason="old spellings")
        self.assert_denied("apex", "run", "--file", "evil.apex", "--u", "other", *decoy, reason="old spellings")
        self.assert_denied("data", "query", "-q", "SELECT Name FROM ApexClass", "--u=other", *decoy, reason="old spellings")
        self.assert_denied("org", "list", "metadata-types", "-ku", "other", *decoy, reason="old spellings")
        self.assertEqual(self.reached(), [])
        # Flags that only start like them are not confused with them (`--u` is matched whole, never as a prefix).
        for flags in (["--use-tooling-api"], ["--user-x"], ["--u-x", "y"], ["--from-org", ORG], ["-q", "SELECT Name FROM ApexClass"]):
            allowed, reason = sf_guard.decide(["project", "generate", "manifest", *flags], ORG)
            self.assertTrue(allowed, (flags, reason))

    def test_a_boolean_short_flag_fused_in_front_of_the_org_flag_is_read_on_every_command(self):
        # `data query -to other` is -t (--use-tooling-api) and then -o other. Unread, it leaves the decoy pin the only one the guard sees.
        decoy = ["--loglevel", f"--target-org={ORG}"]
        read = ("data", "query", "-q", "SELECT Name FROM ApexClass")
        cases = ((read, "-to"), (read, "-bo"), (read, "-tbo"), (("apex", "run", "test"), "-yo"), (("apex", "run", "test"), "-co"),
                 (("apex", "run", "test"), "-vo"), (("apex", "run", "test"), "-cvyo"), (("project", "retrieve", "start"), "-co"),
                 (("project", "retrieve", "start"), "-zo"), (("sobject", "describe"), "-to"), (("data", "get", "record"), "-to"),
                 (("apex", "get", "log"), "-co"), (("apex", "get", "test"), "-co"), (("project", "deploy", "start"), "-co"),
                 (("org", "list", "metadata-types"), "-ko"), (("org", "list", "metadata-types"), "-kto"))
        for command, fused in cases:
            with self.subTest(command=command[:2], fused=fused):
                allowed, reason = sf_guard.decide([*command, fused, "other", *decoy], ORG, prefix="SLChess", cwd=str(self.work))
                self.assertFalse(allowed)
                self.assertIn("--target-org must be", reason)
                allowed, reason = sf_guard.decide([*command, fused, "other"], ORG, prefix="SLChess", cwd=str(self.work))
                self.assertFalse(allowed)
                self.assertIn("--target-org must be", reason)  # named as the wrong org, not as a missing one
                if command[:2] != ("project", "deploy"):
                    allowed, reason = sf_guard.decide([*command, fused, ORG], ORG, prefix="SLChess", cwd=str(self.work))
                    self.assertTrue(allowed, reason)
        self.assert_denied(*read, "-to", "other", *decoy, "--json", reason="--target-org must be")
        self.assert_denied("org", "list", "metadata-types", "-ko", "other", *decoy, reason="--target-org must be")
        self.assertEqual(self.reached(), [])


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
        # The prompt's own spelling: no --source-dir (the scope is the project's package directories), the colon form of the command.
        (self.work / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}]}))
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
        self.assertEqual(self.calls()[-1]["decision"], "allowed")
        self.assertEqual(self.ends()[-1]["exit"], 1)


class LogAndScrubTest(GuardCase):
    def test_one_line_per_call_with_the_decision_and_no_credential(self):
        self.sf("org", "display", "--target-org", ORG, "--json")
        self.sf("org", "list", "--json")
        self.sf("data", "query", "--use-tooling-api", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--json")
        self.sf("data", "query", "-q", "SELECT Name FROM ApexClass", "--json")
        entries = self.calls()
        self.assertEqual([e["decision"] for e in entries], ["denied", "allowed", "allowed", "denied"])
        self.assertEqual([e["exit"] for e in self.ends()], [0, 0])
        for entry in entries:
            self.assertEqual(entry["org"], ORG)
            self.assertTrue(entry["ts"] and entry["reason"] and entry["call"])
        self.assertNotIn("stdout", json.dumps(self.log_lines()))
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        self.assertEqual(len(raw.splitlines()), 6)  # a decision line per call, an end line for each of the two that ran
        self.assertNotIn(TOKEN, raw)
        self.assertNotIn("FAKE-TOKEN", raw)

    def test_a_token_shaped_argument_is_scrubbed_in_the_log(self):
        self.sf("data", "query", "-q", f"SELECT Name FROM ApexClass -- {SESSION}", "--target-org", ORG)
        self.sf("org", "display", f"accessToken={TOKEN}")
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        self.assertNotIn(SESSION, raw)
        self.assertNotIn(TOKEN, raw)
        self.assertIn("[redacted]", raw)

    def test_a_token_that_the_reason_repeats_is_scrubbed_in_the_log_too(self):
        done = self.sf("data", "query", "-q", "x", "--target-org", SESSION)
        self.assertEqual(done.returncode, 2)
        self.assertIn("--target-org must be", done.stderr)
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        self.assertNotIn(SESSION, raw)
        self.assertIn("--target-org must be", self.calls()[-1]["reason"])

    def test_a_token_in_sf_s_output_never_reaches_the_model_and_the_exit_code_does(self):
        self.use_sf(STUB)
        done = self.sf("data", "query", "-q", "x", "--target-org", ORG, env=self.env(STUB_EXIT="7"))
        self.assertEqual(done.returncode, 7)
        for stream in (done.stdout, done.stderr):
            self.assertNotIn(TOKEN, stream)
            self.assertNotIn(SESSION, stream)
            self.assertIn("[redacted]", stream)
        self.assertEqual(json.loads(done.stdout)["argv"], ["data", "query", "-q", "x", "--target-org", ORG])
        entry = self.ends()[-1]
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

    def test_the_real_sf_runs_with_the_case_org_as_its_default_and_no_other_default_org_variable(self):
        # A pin the guard read but the CLI did not falls back to the environment's default org: the case's, never the owner's.
        self.use_sf(STUB)
        seen = json.loads(self.sf("org", "list", "--json").stdout)["sf_env"]
        self.assertEqual(seen, {"SF_TARGET_ORG": ORG})
        env = self.env(SF_TARGET_ORG="other", SFDX_DEFAULTUSERNAME="other", SFDX_DEFAULTDEVHUBUSERNAME="hub", SF_TARGET_DEV_HUB="hub",
                       SF_DEFAULT_X="x", SF_ORG_API_VERSION="64.0")
        seen = json.loads(self.sf("data", "query", "-q", "x", "--target-org", ORG, env=env).stdout)["sf_env"]
        self.assertEqual(seen, {"SF_TARGET_ORG": ORG, "SF_ORG_API_VERSION": "64.0"})  # another SF_ variable is the caller's own
        self.assertEqual(sf_guard.child_env("de", {"PATH": "/bin", "SF_TARGET_ORG": "x", "SFDX_DEFAULTUSERNAME": "y", "SF_TARGET_DEV_HUB": "z"}),
                         {"PATH": "/bin", "SF_TARGET_ORG": "de"})

    def test_the_wrapper_does_not_call_itself(self):
        self.assert_reaches_sf("org", "list", "--json")
        self.assertEqual(len(self.reached()), 1)
        self.assertEqual(len(self.calls()), 1)

    def test_with_no_real_sf_after_the_wrapper_the_call_fails_cleanly_and_does_not_loop(self):
        env = self.env(PATH=os.pathsep.join([str(self.platform_dir / "bin"), "/usr/bin", "/bin"]))
        self.write_wrappers(path=env["PATH"])
        done = self.sf("org", "list", "--json", env=env)
        self.assertEqual(done.returncode, 127)
        self.assertIn("no real `sf`", done.stderr)

    def test_a_relative_path_entry_is_never_searched_for_sf(self):
        planted = self.work / "sf"
        planted.write_text("#!/bin/sh\necho planted\n")
        planted.chmod(0o755)
        env = self.env(PATH=os.pathsep.join([str(self.platform_dir / "bin"), ".", "", "/usr/bin", "/bin"]))
        self.write_wrappers(path=env["PATH"])
        done = self.sf("org", "list", "--json", env=env)
        self.assertEqual(done.returncode, 127)
        self.assertNotIn("planted", done.stdout)

    def test_the_fixed_flags_come_first_and_the_model_s_flags_are_its_own(self):
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "--", "data", "query", "--org", "x"]),
                         ("de", "P", False, "sf", ["data", "query", "--org", "x"], False))
        self.assertEqual(sf_guard.parse_fixed(["--prefix", "P", "--org", "de", "--deny-all", "--name", "open", "--", "--"]),
                         ("de", "P", True, "open", ["--"], False))
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "org", "list"]),
                         ("de", "P", False, "sf", ["org", "list"], False))


class FlagsDirTest(GuardCase):
    def test_flags_dir_is_denied_on_every_command_in_both_spellings(self):
        # The CLI reads flag values from these files after the policy ran, so a destructive or other-org flag could ride in them.
        for argv in (("project", "deploy", "start", "--flags-dir", "fd", "--target-org", ORG),
                     ("project", "deploy", "start", "--flags-dir=fd", "--target-org", ORG, "--json"),
                     ("org", "list", "--flags-dir", "fd"), ("org", "list", "--flags-dir=fd", "--json"),
                     ("project", "generate", "--name", "x", "--flags-dir", "fd"),
                     ("project", "generate", "--flags-dir=fd", "--name", "x"),
                     ("data", "query", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--flags-dir", "fd"),
                     ("project", "deploy", "start", "--flags-dir", "fd", "--help")):
            self.assert_denied(*argv, reason="--flags-dir")
        self.assertEqual(self.reached(), [])

    def test_a_flag_that_only_starts_like_it_is_not_confused_with_it(self):
        allowed, reason = sf_guard.decide(["data", "query", "-q", "SELECT Name FROM ApexClass", "--target-org", ORG, "--flags-directory-x"], ORG)
        self.assertTrue(allowed, reason)


class ScopeTest(GuardCase):
    """A deploy may carry only ApexClass, CustomTab, CustomApplication and FlexiPage named SLChess* and LightningComponentBundle named slChess*."""
    D = "force-app/main/default/"
    GENERATED = ("applications", "aura", "classes", "contentassets", "flexipages", "layouts", "lwc", "objects", "permissionsets",
                 "staticresources", "tabs", "triggers")
    GOOD = {
        "classes/SLChessEngine.cls": "public class SLChessEngine {}",
        "classes/SLChessEngine.cls-meta.xml": "<ApexClass/>",
        "classes/SLChessEngineTest.cls": "@IsTest private class SLChessEngineTest {}",
        "lwc/slChessBoard/slChessBoard.html": "<template></template>",
        "lwc/slChessBoard/slChessBoard.js": "export default class SlChessBoard {}",
        "lwc/slChessBoard/slChessBoard.js-meta.xml": "<LightningComponentBundle/>",
        "lwc/slChessBoard/__tests__/board.test.js": "",
        "lwc/jsconfig.json": "{}",
        "lwc/.eslintrc.json": "{}",
        "tabs/SLChess_Board.tab-meta.xml": "<CustomTab/>",
        "applications/SLChess_Chess.app-meta.xml": "<CustomApplication/>",
        "flexipages/SLChess_Board.flexipage-meta.xml": "<FlexiPage/>",
    }

    def layout(self, files: dict | None = None, base: Path | None = None) -> Path:
        """The tree `sf project generate` makes (every folder empty) plus these files, given relative to force-app/main/default."""
        base = base or self.work
        for name in self.GENERATED:
            (base / (self.D + name)).mkdir(parents=True, exist_ok=True)
        (base / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}]}))
        for rel, text in (files or {}).items():
            path = base / (self.D + rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return base

    def verdict(self, *flags: str, base: Path | None = None, command=("project", "deploy", "start"), custom_objects: bool = False,
                permission_sets: bool = False) -> tuple[bool, str]:
        return sf_guard.decide([*command, *flags, "--target-org", ORG, "--json"], ORG, prefix="SLChess", cwd=str((base or self.work)),
                               custom_objects=custom_objects, permission_sets=permission_sets)

    def assert_scope_ok(self, *flags: str, base: Path | None = None, command=("project", "deploy", "start"), custom_objects: bool = False,
                        permission_sets: bool = False) -> None:
        allowed, reason = self.verdict(*flags, base=base, command=command, custom_objects=custom_objects, permission_sets=permission_sets)
        self.assertTrue(allowed, (flags, reason))

    def assert_scope_denied(self, *flags: str, reason: str, base: Path | None = None, command=("project", "deploy", "start"),
                            custom_objects: bool = False, permission_sets: bool = False) -> str:
        allowed, why = self.verdict(*flags, base=base, command=command, custom_objects=custom_objects, permission_sets=permission_sets)
        self.assertFalse(allowed, flags)
        self.assertIn("approved scope", why)
        self.assertIn(reason, why, flags)
        self.assertNotIn("\n", why)
        return why

    def test_the_generated_layout_with_only_empty_directories_passes_in_every_spelling(self):
        self.layout()
        for flags in (["--source-dir", "force-app"], ["-d", "force-app"], ["--source-dir=force-app"], ["-dforce-app"], ["-d=force-app"],
                      ["--source-dir", "./force-app/"], ["--source-dir", str(self.work / "force-app")], []):
            self.assert_scope_ok(*flags)
        self.assert_scope_ok("-d", "force-app", command=("project", "deploy", "validate"))

    def test_a_gitkeep_placeholder_is_not_a_component_and_only_that_exact_name_is_forgiven(self):
        """The live Salesforce run's default-scope deploy was refused for force-app/main/default/.gitkeep, the placeholder git
        keeps in a folder with no other file. It has no metadata suffix, so the CLI deploys nothing for it: the exact name `.gitkeep` is
        skipped in the scope walk, wherever it sits, and every other name is judged as before."""
        base = self.layout(base=self.work / "keep")
        only = base / "force-app" / "main" / "default" / ".gitkeep"
        only.write_text("")
        for flags in ([], ["--source-dir", "force-app"], ["-d", "force-app/main/default"], ["-d", self.D + ".gitkeep"]):
            self.assert_scope_ok(*flags, base=base)
            self.assert_scope_ok(*flags, base=base, command=("project", "deploy", "validate"))
        for folder in self.GENERATED:  # one in every generated folder, an lwc and an objects folder included
            (base / (self.D + folder) / ".gitkeep").write_text("")
        self.assert_scope_ok(base=base)
        # The approved files beside the placeholders still pass; a refused file beside one is still named, and the placeholder is not.
        full = self.layout(self.GOOD | {"classes/.gitkeep": ""}, base=self.work / "full")
        self.assert_scope_ok(base=full)
        (full / (self.D + "classes") / "Other.cls").write_text("x")
        why = self.assert_scope_denied(reason="classes/Other.cls", base=full)
        self.assertNotIn(".gitkeep", why)
        # Anything that only looks like it is judged as before.
        for number, (what, rel) in enumerate({"another dot file": ".gitignore", "a suffixed name": ".gitkeep.bak", "a prefixed name": "x.gitkeep",
                                              "a different case": ".GITKEEP", "a name without the dot": "gitkeep",
                                              "a class-shaped name": "classes/.gitkeep.cls",
                                              "a meta-shaped name": "classes/.gitkeep.cls-meta.xml"}.items()):
            with self.subTest(what):
                case = self.layout({rel: "x"}, base=self.work / f"keep-{number}")
                self.assert_scope_denied(reason=sf_guard.shown(rel), base=case)
        # The skip comes after the project boundary: a link named .gitkeep that leads outside the project is still refused.
        outside = self.tmp / "outside"
        outside.write_text("x")
        linked = self.layout(base=self.work / "linked")
        (linked / (self.D + "classes") / ".gitkeep").symlink_to(outside)
        self.assert_scope_denied(reason="leads outside the project directory", base=linked)
        # Through the wrapper: a deploy of a tree that holds only a placeholder reaches the (fake) org.
        wrapped = self.layout(base=self.work)
        (wrapped / (self.D + ".gitkeep")).write_text("")
        deployed = self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json")
        self.assertEqual(json.loads(deployed.stdout)["result"]["status"], "Succeeded")

    def test_the_approved_classes_and_bundles_pass_as_a_tree_a_folder_or_a_single_file(self):
        self.layout(self.GOOD)
        classes, lwc = self.D + "classes", self.D + "lwc"
        for flags in (["--source-dir", "force-app"], [],
                      ["--source-dir", classes], ["--source-dir", lwc], ["--source-dir", lwc + "/slChessBoard"],
                      ["--source-dir", classes + "/SLChessEngine.cls"], ["-d", classes + "/SLChessEngine.cls-meta.xml"],
                      ["-d", classes + "/SLChessEngine.cls", "-d", lwc + "/slChessBoard"],
                      ["--source-dir", classes + "/SLChessEngine.cls", "--source-dir", lwc + "/slChessBoard"],
                      ["--source-dir", f"{classes}/SLChessEngine.cls,{lwc}/slChessBoard"],
                      ["--source-dir", classes + "/SLChessEngine.cls", lwc + "/slChessBoard"]):
            self.assert_scope_ok(*flags)
            self.assert_scope_ok(*flags, command=("project", "deploy", "validate"))
        # Through the wrapper: the deploy reaches the (fake) org and the classes and bundle land there.
        deployed = self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json")
        self.assertEqual(json.loads(deployed.stdout)["result"]["status"], "Succeeded")
        state = json.loads(self.state.read_text())
        self.assertIn("SLChessEngine", state["apex_classes"])
        self.assertIn("slChessBoard", state["lwc"])

    def test_the_component_prefix_is_the_one_the_checks_use(self):
        import chess_salesforce  # the cleanup and the deployed check name the same bundles
        for prefix in ("SLChess", "Chess", "ABC", "SLChessEngine", "A", "abc", "X1", "AB1"):
            self.assertEqual(sf_guard.lwc_prefix(prefix), chess_salesforce.lwc_prefix(prefix), prefix)
        self.assertEqual(sf_guard.lwc_prefix("SLChess"), "slChess")

    def test_a_flag_value_is_not_mistaken_for_a_source_path(self):
        # `--manifest manifest/package.xml` follows `--source-dir`: it is the manifest's value, not another directory (a file the scope refuses).
        self.layout(self.GOOD)
        (self.work / "manifest").mkdir()
        (self.work / "manifest" / "package.xml").write_text("<Package><types><members>SLChessEngine</members><name>ApexClass</name></types></Package>")
        self.assert_scope_ok("--source-dir", "force-app", "--manifest", "manifest/package.xml")
        # The values of the other flags ARE bad paths here (each folder holds a trigger), so reading one of them as a source path is caught.
        for name in ("10", "NoTestRun", "64.0", "Foo"):
            (self.work / name).mkdir()
            (self.work / name / "T.trigger").write_text("x")
        self.assert_scope_ok("--source-dir", "force-app", "--wait", "10", "-l", "NoTestRun")
        self.assert_scope_ok("--source-dir", "force-app", "-w", "10", "--test-level=NoTestRun", "--api-version", "64.0", "-t", "Foo")
        self.assert_scope_ok("-d", "force-app", "-w10", "-lNoTestRun", "-a64.0", "--tests", "Foo", "--json")
        self.assert_scope_denied("--source-dir", "force-app", "10", reason="10/T.trigger")  # a bare word after --source-dir IS a path

    def test_metadata_entries_of_the_approved_names_pass(self):
        self.layout()
        for flags in (["--metadata", "ApexClass:SLChessEngine"], ["-m", "LightningComponentBundle:slChessBoard"],
                      ["-m", "ApexClass:SLChessEngine", "-m", "LightningComponentBundle:slChessBoard"],
                      ["--metadata=ApexClass:SLChessEngineTest"], ["-mApexClass:SLChess"],
                      ["--metadata", "ApexClass:SLChessEngine", "LightningComponentBundle:slChessBoard"],
                      ["--metadata", "ApexClass:SLChessEngine,LightningComponentBundle:slChessBoard"],
                      ["--metadata", "CustomTab:SLChess_Board"], ["-m", "CustomApplication:SLChess_Chess"], ["-m", "FlexiPage:SLChess_Board"],
                      ["--metadata=CustomTab:SLChess"], ["-mFlexiPage:SLChess_Board"],
                      ["-m", "CustomTab:SLChess_Board", "-m", "CustomApplication:SLChess_Chess", "-m", "FlexiPage:SLChess_Board"],
                      ["--metadata", "CustomTab:SLChess_Board", "CustomApplication:SLChess_Chess", "FlexiPage:SLChess_Board"],
                      ["--metadata", "ApexClass:SLChessEngine,CustomTab:SLChess_Board,LightningComponentBundle:slChessBoard"]):
            self.assert_scope_ok(*flags)
        self.assert_reaches_sf("project", "deploy", "start", "--metadata", "ApexClass:SLChessEngine", "--target-org", ORG, "--json")
        self.assert_reaches_sf("project", "deploy", "start", "--metadata", "CustomTab:SLChess_Board", "--target-org", ORG, "--json")

    def test_a_single_trailing_star_in_a_metadata_entry_stays_inside_the_prefix(self):
        self.layout()
        for entry in ("ApexClass:SLChess*", "CustomTab:SLChess*", "CustomTab:SLChess_*", "CustomApplication:SLChess*", "FlexiPage:SLChess_B*",
                      "LightningComponentBundle:slChess*"):
            self.assert_scope_ok("--metadata", entry)
        for entry in ("ApexClass:*", "ApexClass:SLChess**", "ApexClass:SL*", "ApexClass:SLChess*x", "ApexClass:SLChess*Engine",
                      "CustomTab:*", "CustomTab:SLChess**", "FlexiPage:*Chess", "LightningComponentBundle:slChess**", "CustomTab:Chess*"):
            with self.subTest(entry):
                self.assert_scope_denied("--metadata", entry, reason="--metadata")

    def test_a_manifest_of_the_approved_names_passes_with_or_without_the_real_header(self):
        self.layout()
        header = '<?xml version="1.0" encoding="UTF-8"?>\n<Package xmlns="http://soap.sforce.com/2006/04/metadata">'
        (self.work / "real.xml").write_text(header + "<types><members>SLChessEngine</members><members>SLChessEngineTest</members>"
                                            "<name>ApexClass</name></types><types><members>slChessBoard</members>"
                                            "<name>LightningComponentBundle</name></types><version>64.0</version></Package>")
        (self.work / "bare.xml").write_text("<Package><types><members>SLChessEngine</members><name>ApexClass</name></types></Package>")
        (self.work / "ui.xml").write_text(header + "<types><members>SLChess_Board</members><members>SLChess</members><name>CustomTab</name></types>"
                                          "<types><members>SLChess_Chess</members><name>CustomApplication</name></types>"
                                          "<types><members>SLChess_Board</members><name>FlexiPage</name></types><version>64.0</version></Package>")
        (self.work / "pretty.xml").write_text(header + "\n    <types>\n        <members>SLChessEngine</members>\n"
                                              "        <members>SLChessEngineTest</members>\n        <name>ApexClass</name>\n    </types>\n"
                                              "    <types>\n        <members>SLChess_Board</members>\n        <name>CustomTab</name>\n    </types>\n"
                                              "    <version>64.0</version>\n</Package>\n")
        self.assert_scope_ok("--manifest", "real.xml")
        self.assert_scope_ok("-x", "bare.xml", command=("project", "deploy", "validate"))
        self.assert_scope_ok("--manifest=real.xml")
        for name in ("ui.xml", "pretty.xml"):
            self.assert_scope_ok("--manifest", name)
            self.assert_scope_ok("-x", name, command=("project", "deploy", "validate"))
        self.assert_reaches_sf("project", "deploy", "start", "--manifest", "real.xml", "--target-org", ORG, "--json")
        self.assert_reaches_sf("project", "deploy", "start", "--manifest", "ui.xml", "--target-org", ORG, "--json")

    def test_a_tree_holding_anything_else_is_refused_and_the_files_are_named(self):
        cases = {
            "a baseline class": "classes/DeveloperEditionUtils.cls",
            "a baseline class's meta file": "classes/DeveloperEditionUtils.cls-meta.xml",
            "a class not matching the prefix by case": "classes/slchessOther.cls",
            "an approved name with another suffix": "classes/SLChessEngine.cls.bak",
            "a trigger": "triggers/SLChessTrigger.trigger",
            "a trigger's meta file": "triggers/SLChessTrigger.trigger-meta.xml",
            "a static resource": "staticresources/SLChess.resource-meta.xml",
            "a prefixed static resource": "staticresources/SLChess_a.resource",
            "a tab without the prefix": "tabs/Chess_Board.tab-meta.xml",
            "a tab with the component prefix": "tabs/slChess_Other.tab-meta.xml",
            "a tab in the wrong folder": "classes/SLChess_Board.tab-meta.xml",
            "a tab with another suffix": "tabs/SLChess_Board.tab-meta.xml.bak",
            "a tab with a flexipage's suffix": "tabs/SLChess_Board.flexipage-meta.xml",
            "a flexipage without the prefix": "flexipages/Home_Page.flexipage-meta.xml",
            "a flexipage in the wrong folder": "layouts/SLChess_Board.flexipage-meta.xml",
            "an app without the prefix": "applications/Chess.app-meta.xml",
            "an app with the component prefix": "applications/slChess_Other.app-meta.xml",
            "an app in the wrong folder": "flexipages/SLChess_Chess.app-meta.xml",
            "an object": "objects/SLChess__c/SLChess__c.object-meta.xml",
            "a permission set": "permissionsets/SLChess.permissionset-meta.xml",
            "a prefixed permission set": "permissionsets/SLChess_X.permissionset-meta.xml",
            "a profile": "profiles/Admin.profile-meta.xml",
            "a label file": "labels/CustomLabels.labels-meta.xml",
            "a baseline bundle": "lwc/chess/chess.js",
            "a bundle with the class prefix's capital": "lwc/SLChessOther/SLChessOther.js",
            "a loose file in lwc": "lwc/slChessLoose.js",
            "a class in a folder that is not classes": "layouts/SLChessEngine.cls",
            # The CLI types a file by ANY strict folder above it, not by its own parent folder.
            "a class inside a baseline bundle": "lwc/chess/classes/SLChessX.cls",
            "a class inside a static resource": "staticresources/Foo/classes/SLChessX.cls",
            "a class inside an aura bundle": "aura/Foo/classes/SLChessX.cls",
            "a class inside an object": "objects/Foo__c/classes/SLChessX.cls",
            "a tab inside an object": "objects/Foo__c/tabs/SLChess_X.tab-meta.xml",
            "a baseline bundle nested in an approved one": "lwc/slChessBoard/lwc/chess/chess.js",
            "a file with a newline in its name": "classes/Bad\nName.cls",
            # The CLI reads `<name>.<type>-meta.xml` anywhere in a file name, so these are deployed as other types named SLChess*.
            "a class file named like a permission set's meta file": "classes/SLChess.permissionset-meta.xml.cls",
            "a class file named like a profile's meta file": "classes/SLChess.profile-meta.xml.cls",
            "a class file named like a flow's meta file": "classes/SLChess.flow-meta.xml.cls",
            "a class meta file named like a layout's meta file": "classes/SLChess.layout-meta.xml.cls-meta.xml",
            "a tab file named like a profile's meta file": "tabs/SLChess_A.profile-meta.xml.tab-meta.xml",
            "an app file named like a flow's meta file": "applications/SLChess.flow-meta.xml.app-meta.xml",
            "a flexipage file named like a profile's meta file": "flexipages/SLChess.profile-meta.xml.flexipage-meta.xml",
            # Each rule of in_scope on its own: the suffix of an app, of a class, and the folder straight above the file.
            "an app with a bare xml suffix": "applications/SLChess_x.xml",
            "a class with a text suffix": "classes/SLChess.txt",
            "a class in a folder below classes": "classes/sub/SLChessX.cls",
            "a tab in a folder below tabs": "tabs/sub/SLChess_X.tab-meta.xml",
        }
        for number, (what, rel) in enumerate(cases.items()):
            with self.subTest(what):
                base = self.layout(self.GOOD | {rel: "x"}, base=self.work / f"case{number}")
                named = sf_guard.shown(rel)  # the refusal shows a control character as ?
                why = self.assert_scope_denied("--source-dir", "force-app", reason=named, base=base)
                self.assert_scope_denied(reason=named, base=base)  # the default scope (sfdx-project.json) is the same tree
                self.assert_scope_denied("-d", self.D + rel, reason=named, base=base, command=("project", "deploy", "validate"))
                self.assertIn("SLChess*", why)
                self.assertIn("slChess*", why)

    def test_a_refusal_names_at_most_five_files_and_does_not_walk_forever(self):
        base = self.layout({f"classes/Other{n}.cls": "x" for n in range(12)})
        why = self.assert_scope_denied("--source-dir", "force-app", reason="Other0.cls", base=base)
        self.assertEqual(why.count("Other"), 5)

    def test_a_path_that_leaves_the_working_directory_is_refused(self):
        self.layout(self.GOOD)
        outside = self.tmp / "outside"
        (outside / "classes").mkdir(parents=True)
        (outside / "classes" / "SLChessOutside.cls").write_text("x")
        (self.work / "link-out").symlink_to(outside)
        (self.work / "force-app" / "main" / "default" / "classes" / "SLChessLinked.cls").symlink_to(outside / "classes" / "SLChessOutside.cls")
        for flags in (["--source-dir", "../outside"], ["--source-dir", str(outside)], ["--source-dir", "force-app/../../outside"],
                      ["--source-dir", "link-out"], ["--source-dir", "link-out/classes/SLChessOutside.cls"],
                      ["--source-dir", f"force-app,{outside}"], ["--source-dir", "force-app", "../outside"]):
            self.assert_scope_denied(*flags, reason="outside the project directory")
        # A link inside the tree that leads out is named, and so is a directory link.
        self.assert_scope_denied("--source-dir", "force-app", reason="SLChessLinked.cls (leads outside the project directory)")
        (self.work / "force-app" / "main" / "default" / "classes" / "SLChessLinked.cls").unlink()
        (self.work / "force-app" / "main" / "default" / "lwc" / "slChessLinkedBundle").symlink_to(outside, target_is_directory=True)
        self.assert_scope_denied("--source-dir", "force-app", reason="slChessLinkedBundle (leads outside the project directory)")
        self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app/main/default/classes/SLChessEngine.cls", "--target-org", ORG, "--json")

    def test_a_path_that_is_not_there_is_judged_by_where_it_points_only(self):
        self.layout(self.GOOD)
        self.assert_scope_denied("--source-dir", "../no-such-dir", reason="outside the project directory")
        self.assert_scope_denied("--source-dir", str(self.tmp / "no-such-dir"), reason="outside the project directory")
        self.assert_scope_ok("--source-dir", "force-app/main/default/classes/SLChessNotWrittenYet.cls")  # the real sf reports it missing
        self.assert_scope_ok("--source-dir", "no-such-dir,force-app/main/default/classes/SLChessEngine.cls")

    def test_a_link_inside_the_project_cannot_hide_a_tree_under_an_approved_name(self):
        # lwc/slChessBoard -> objects: reached through the bundle name the files pass, but `force-app` also holds `objects` itself.
        base = self.layout({"objects/Foo__c/Foo__c.object-meta.xml": "<CustomObject/>"})
        (base / (self.D + "lwc") / "slChessBoard").symlink_to(base / (self.D + "objects"), target_is_directory=True)
        self.assert_scope_denied("--source-dir", "force-app", reason="objects/Foo__c/Foo__c.object-meta.xml", base=base)

    def test_a_symlink_loop_ends(self):
        base = self.layout(self.GOOD)
        (base / "force-app" / "loop").symlink_to(base / "force-app", target_is_directory=True)
        started = time.monotonic()
        self.assert_scope_ok("--source-dir", "force-app")
        self.assertLess(time.monotonic() - started, 5)

    def test_extra_paths_after_a_source_dir_are_read_as_more_directories(self):
        # The CLI reads `-d a b` as two directories, and a boolean flag between them does not end the list.
        self.layout(self.GOOD | {"objects/Foo__c/Foo__c.object-meta.xml": "<CustomObject/>", "triggers/T.trigger": "x"})
        good = self.D + "classes/SLChessEngine.cls"
        for flags in (["--source-dir", good, self.D + "objects"], ["-d", good, self.D + "triggers"],
                      ["--source-dir", good, "--json", self.D + "triggers"], ["--source-dir=" + good, self.D + "triggers"],
                      ["--source-dir", good, "--source-dir", self.D + "triggers"], ["--source-dir", f"{good},{self.D}triggers"]):
            self.assert_scope_denied(*flags, reason="T.trigger" if "triggers" in " ".join(flags) else "Foo__c.object-meta.xml")

    def test_metadata_outside_the_approved_names_is_refused(self):
        self.layout()
        for entry in ("CustomObject:Foo__c", "ApexClass", "ApexClass:", "ApexClass:*", "ApexClass:DeveloperEditionUtils",
                      "LightningComponentBundle:chess", "LightningComponentBundle:SLChessBoard", "ApexTrigger:SLChessTrigger",
                      "ApexTrigger:SLChessT", "ApexPage:SLChessP", "ApexComponent:SLChessC", "PermissionSet:SLChess", "PermissionSet:SLChess_X",
                      "StaticResource:SLChess_a", "Profile:Admin", "CustomLabels:SLChess", "CustomObject:SLChess__c",
                      "CustomTab:Chess_Board", "CustomTab:slChess_Board", "CustomApplication:Chess", "CustomApplication:slChess_Chess",
                      "FlexiPage:Home_Page", "FlexiPage:slChess_Board", "ApexClass:slChess_X",
                      "ApexClass:SLChessEngine,CustomObject:Foo__c", ""):
            with self.subTest(entry):
                self.assert_scope_denied("--metadata", entry, reason="--metadata")
        self.assert_scope_denied("-m", "ApexClass:SLChessEngine", "CustomObject:Foo__c", reason="CustomObject:Foo__c")
        self.assert_scope_denied("--metadata", "ApexClass:SLChessEngine", "--json", "ApexTrigger:T", reason="ApexTrigger:T")
        # Through the wrapper: refused before the real sf is reached.
        done = self.sf("project", "deploy", "start", "--metadata", "CustomObject:Foo__c", "--target-org", ORG, "--json")
        self.assertEqual(done.returncode, 2)
        self.assertIn("sf: denied by this run's guard: deploy is outside the approved scope", done.stderr)
        self.assertEqual(self.reached(), [])

    def test_a_manifest_outside_the_approved_names_is_refused(self):
        self.layout()
        manifests = {
            "another type": ("<Package><types><members>SLChessEngine</members><name>CustomObject</name></types></Package>", "CustomObject"),
            "a baseline member": ("<Package><types><members>DeveloperEditionUtils</members><name>ApexClass</name></types></Package>",
                                  "DeveloperEditionUtils"),
            "a second type with a baseline member": ("<Package><types><members>SLChessEngine</members><name>ApexClass</name></types>"
                                                     "<types><members>chess</members><name>LightningComponentBundle</name></types></Package>", "'chess'"),
            "a star in a member name": ("<Package><types><members>SLChess*</members><name>ApexClass</name></types></Package>", "SLChess*"),
            "a bare star": ("<Package><types><members>*</members><name>ApexClass</name></types></Package>", "wildcard"),
            "a spaced star": ("<Package><types><members> * </members><name>LightningComponentBundle</name></types></Package>", "wildcard"),
            "a type with no name": ("<Package><types><members>SLChessEngine</members></types></Package>", "lists type ''"),
            "not xml": ("this is not xml", "not valid XML"),
            "an encoding the parser does not know": ('<?xml version="1.0" encoding="bogus"?><Package/>', "not valid XML"),
            "a trigger": ("<Package><types><members>SLChessT</members><name>ApexTrigger</name></types></Package>", "ApexTrigger"),
            "a page": ("<Package><types><members>SLChessP</members><name>ApexPage</name></types></Package>", "ApexPage"),
            "a permission set": ("<Package><types><members>SLChess_X</members><name>PermissionSet</name></types></Package>", "PermissionSet"),
            "a static resource": ("<Package><types><members>SLChess_a</members><name>StaticResource</name></types></Package>", "StaticResource"),
            "a profile": ("<Package><types><members>Admin</members><name>Profile</name></types></Package>", "Profile"),
            "a tab without the prefix": ("<Package><types><members>Chess_Board</members><name>CustomTab</name></types></Package>", "'Chess_Board'"),
            "an app with the component prefix": ("<Package><types><members>slChess_Chess</members><name>CustomApplication</name></types></Package>",
                                                 "'slChess_Chess'"),
            "a star in a flexipage name": ("<Package><types><members>SLChess*</members><name>FlexiPage</name></types></Package>", "SLChess*"),
            "a star in a tab name": ("<Package><types><members>SLChess_*</members><name>CustomTab</name></types></Package>", "SLChess_*"),
            "a bad member after good ones, pretty-printed": (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Package xmlns=\"http://soap.sforce.com/2006/04/metadata\">\n    <types>\n"
                "        <members>SLChess_Board</members>\n        <members>Chess_Other</members>\n        <name>CustomTab</name>\n"
                "    </types>\n</Package>\n", "'Chess_Other'"),
        }
        for what, (text, reason) in manifests.items():
            with self.subTest(what):
                (self.work / "m.xml").write_text(text)
                self.assert_scope_denied("--manifest", "m.xml", reason=reason)
                self.assert_scope_denied("-x", "m.xml", reason=reason, command=("project", "deploy", "validate"))

    def test_a_manifest_with_a_doctype_or_entity_declaration_is_refused(self):
        # An entity declared twice is read with the first declaration by the XML parser here (SLChessA, which passes) and with the last
        # by the CLI's (a wildcard, which deploys every local class).
        self.layout()
        header = '<?xml version="1.0"?>'
        body = "<Package><types><members>&m;</members><name>ApexClass</name></types></Package>"
        manifests = {
            "an entity declared twice": f'{header}<!DOCTYPE Package [<!ENTITY m "SLChessA"><!ENTITY m "*">]>{body}',
            "an entity declared once": f'{header}<!DOCTYPE Package [<!ENTITY m "SLChessA">]>{body}',
            "a doctype without entities": f"{header}<!DOCTYPE Package><Package/>",
            "a lower-case doctype": f"{header}<!doctype Package><Package/>",
            "an entity outside a doctype": f'{header}<!ENTITY m "SLChessA">{body}',
        }
        for what, text in manifests.items():
            with self.subTest(what):
                (self.work / "m.xml").write_text(text)
                self.assert_scope_denied("--manifest", "m.xml", reason="DOCTYPE or ENTITY")
                self.assert_scope_denied("-x", "m.xml", reason="DOCTYPE or ENTITY", command=("project", "deploy", "validate"))
        # Without the declaration the same members are fine.
        (self.work / "m.xml").write_text(f"{header}<Package><types><members>SLChessA</members><name>ApexClass</name></types></Package>")
        self.assert_scope_ok("--manifest", "m.xml")
        # Through the wrapper the deploy never reaches the real sf.
        (self.work / "m.xml").write_text(manifests["an entity declared twice"])
        done = self.sf("project", "deploy", "start", "--manifest", "m.xml", "--target-org", ORG, "--json")
        self.assertEqual(done.returncode, 2)
        self.assertIn("DOCTYPE or ENTITY", done.stderr)
        self.assertEqual(self.reached(), [])

    def test_a_missing_or_unreadable_manifest_is_refused_not_passed_through(self):
        self.layout()
        self.assert_scope_denied("--manifest", "no-such.xml", reason="cannot be read")
        done = self.sf("project", "deploy", "start", "--manifest", "no-such.xml", "--target-org", ORG, "--json")
        self.assertEqual(done.returncode, 2)
        self.assertEqual(self.reached(), [])

    def test_with_no_scope_flag_the_package_directories_decide(self):
        base = self.layout(base=self.work / "plain")
        self.assert_scope_ok(base=base)
        (base / "force-app" / "main" / "default" / "triggers" / "T.trigger").write_text("x")
        self.assert_scope_denied(reason="T.trigger", base=base)
        # A second package directory counts, and so does one that leaves the project.
        other = self.layout(base=self.work / "two")
        (other / "extra" / "classes").mkdir(parents=True)
        (other / "extra" / "classes" / "Baseline.cls").write_text("x")
        (other / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app"}, {"path": "extra"}]}))
        self.assert_scope_denied(reason="extra/classes/Baseline.cls", base=other)
        (other / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "../outside"}]}))
        self.assert_scope_denied(reason="outside the project directory", base=other)

    def test_with_no_scope_flag_and_no_readable_project_file_the_deploy_is_refused(self):
        for number, text in enumerate((None, "not json", "{}", '{"packageDirectories": []}', '{"packageDirectories": [1]}',
                                       '{"packageDirectories": [{"path": ""}]}')):
            with self.subTest(text):
                base = self.work / f"noproject{number}"
                base.mkdir()
                if text is not None:
                    (base / "sfdx-project.json").write_text(text)
                self.assert_scope_denied(reason="sfdx-project.json", base=base)
        done = self.sf("project:deploy:start", "--target-org", ORG, "--json")  # self.work has no project file
        self.assertEqual(done.returncode, 2)
        self.assertIn("name what to deploy", done.stderr)
        self.assertEqual(self.reached(), [])

    def test_only_a_deploy_that_sends_source_is_scoped(self):
        # Nothing to judge for a report (it names a job) or a retrieve (it only reads the org).
        for command in (("project", "deploy", "report"), ("project", "retrieve", "start")):
            allowed, reason = sf_guard.decide([*command, "--job-id", "0Af000000000000AAA", "--target-org", ORG], ORG, prefix="SLChess",
                                              cwd=str(self.work))
            self.assertTrue(allowed, (command, reason))
        allowed, reason = sf_guard.decide(["project", "retrieve", "start", "--metadata", "CustomObject:Foo__c", "--target-org", ORG], ORG,
                                          prefix="SLChess", cwd=str(self.work))
        self.assertTrue(allowed, reason)

    def test_without_a_prefix_no_deploy_is_defined(self):
        self.layout(self.GOOD)
        self.assertEqual(sf_guard.deploy_scope_problems(["--source-dir", "force-app"], str(self.work), ""),
                         ["the wrapper has no --prefix, so no deploy scope is defined"])
        allowed, reason = sf_guard.decide(["project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG], ORG, cwd=str(self.work))
        self.assertFalse(allowed)
        self.assertIn("no --prefix", reason)

    def test_the_destructive_and_wildcard_denials_come_first_and_keep_their_wording(self):
        self.layout(self.GOOD)
        self.assert_denied("project", "deploy", "start", "--source-dir", "force-app", "--post-destructive-changes", "d.xml",
                           "--manifest", "m.xml", "--target-org", ORG, reason="--post-destructive-changes")
        self.assert_denied("project", "deploy", "validate", "--metadata-dir", "mdapi", "--target-org", ORG, reason="--metadata-dir")

    def test_a_prefixed_tab_app_and_app_page_pass_as_a_tree_a_folder_or_a_single_file(self):
        self.layout(self.GOOD | {"tabs/SLChess.tab-meta.xml": "<CustomTab/>"})
        tabs, apps, pages = self.D + "tabs", self.D + "applications", self.D + "flexipages"
        tab, app, page = tabs + "/SLChess_Board.tab-meta.xml", apps + "/SLChess_Chess.app-meta.xml", pages + "/SLChess_Board.flexipage-meta.xml"
        for flags in (["--source-dir", "force-app"], [], ["--source-dir", tabs], ["--source-dir", apps], ["--source-dir", pages],
                      ["-d", tab], ["-d", tabs + "/SLChess.tab-meta.xml"], ["-d", app], ["--source-dir", page],
                      ["-d", tab, "-d", app, "-d", page], ["--source-dir", f"{tab},{app}"], ["--source-dir", tab, app, page]):
            self.assert_scope_ok(*flags)
            self.assert_scope_ok(*flags, command=("project", "deploy", "validate"))
        # Through the wrapper the deploy reaches the (fake) org.
        self.assert_reaches_sf("project", "deploy", "start", "--source-dir", tab, "--source-dir", app, "--source-dir", page,
                               "--target-org", ORG, "--json")

    def test_the_refusals_list_the_five_approved_kinds(self):
        kinds = ("ApexClass", "CustomTab", "CustomApplication", "FlexiPage", "LightningComponentBundle")
        self.layout({"triggers/T.trigger": "x"})
        why = self.assert_scope_denied("--source-dir", "force-app", reason="approved: ")
        for kind in kinds:
            self.assertIn(kind, why)
        self.assertIn("named SLChess*", why)
        self.assertIn("named slChess*", why)
        why = self.assert_scope_denied("--metadata", "CustomObject:Foo__c", reason="--metadata")
        for entry in ("ApexClass:SLChess<name>", "CustomTab:SLChess<name>", "CustomApplication:SLChess<name>", "FlexiPage:SLChess<name>",
                      "LightningComponentBundle:slChess<name>"):
            self.assertIn(entry, why)
        (self.work / "m.xml").write_text("<Package><types><members>SLChessT</members><name>ApexTrigger</name></types></Package>")
        why = self.assert_scope_denied("--manifest", "m.xml", reason="ApexTrigger")
        for kind in kinds:
            self.assertIn(kind, why)

    def test_a_path_or_manifest_whose_name_starts_with_a_dash_is_still_the_flag_s_value(self):
        # oclif takes the next word as the value of a flag that needs one, whatever it starts with.
        base = self.layout(self.GOOD)
        (base / "-zevil" / "triggers").mkdir(parents=True)
        (base / "-zevil" / "triggers" / "T.trigger").write_text("x")
        (base / "-zm.xml").write_text("<Package><types><members>Evil</members><name>ApexClass</name></types></Package>")
        for flags, reason in ((["--source-dir", "-zevil"], "-zevil/triggers/T.trigger"), (["-d", "-zevil"], "-zevil/triggers/T.trigger"),
                              (["--source-dir", "force-app", "-d", "-zevil"], "-zevil/triggers/T.trigger"),
                              (["--manifest", "-zm.xml"], "'Evil'"), (["-x", "-zm.xml"], "'Evil'")):
            with self.subTest(flags):
                self.assert_scope_denied(*flags, reason=reason)
        self.assert_denied("project", "deploy", "start", "--source-dir", "-zevil", "--target-org", ORG, reason="approved scope")
        self.assertEqual(self.reached(), [])

    def test_a_boolean_short_flag_fused_in_front_of_a_scope_flag_does_not_hide_it(self):
        # `-rd evil` is -r (--ignore-errors) and then -d evil; the retry of a refused `-d force-app` must not slip through that way.
        base = self.layout(self.GOOD)
        (base / "evil" / "triggers").mkdir(parents=True)
        (base / "evil" / "triggers" / "T.trigger").write_text("x")
        (base / "evil.xml").write_text("<Package><types><members>SLChessT</members><name>ApexTrigger</name></types></Package>")
        for fused in ("-rd", "-cd", "-gd", "-crd", "-rgcd"):
            with self.subTest(fused):
                self.assert_scope_denied(fused, "evil", reason="evil/triggers/T.trigger")
                self.assert_scope_denied(fused + "evil", reason="evil/triggers/T.trigger")
                self.assert_scope_denied(fused + "=evil", reason="evil/triggers/T.trigger")
        for fused in ("-gm", "-rm", "-cm"):
            self.assert_scope_denied(fused, "ApexTrigger:SLChessT", reason="--metadata")
        for fused in ("-gx", "-cx", "-rx"):
            self.assert_scope_denied(fused, "evil.xml", reason="ApexTrigger")
        # A fused boolean in front of a harmless flag leaves the rest as it was.
        self.assert_scope_ok("-rd", "force-app", "-gw", "10")
        self.assert_denied("project", "deploy", "start", "-rd", "evil", "--target-org", ORG, reason="approved scope")

    def test_t_on_a_deploy_is_the_tests_flag_and_does_not_hide_the_scope_flag_after_it(self):
        # `-t` is --tests (a value flag, repeatable and greedy) on `project deploy start|validate`, so `-td <path>` is tests ['d', <path>]
        # and NO source flag: the CLI then deploys the packageDirectories, whatever <path> is. Peeling `t` as a boolean would make the
        # guard check only that narrow path.
        base = self.layout(self.GOOD | {"permissionsets/Evil.permissionset-meta.xml": "<PermissionSet/>"})
        (base / "m.xml").write_text("<Package><types><members>SLChessEngine</members><name>ApexClass</name></types></Package>")
        engine = self.D + "classes/SLChessEngine.cls"
        for command in (("project", "deploy", "start"), ("project", "deploy", "validate")):
            self.assert_scope_denied(reason="Evil.permissionset-meta.xml", command=command)  # the plain deploy of the whole tree
            for flags in (["-td", engine], ["-td" + engine], ["-tm", "ApexClass:SLChessEngine"], ["-tx", "m.xml"], ["-tm=ApexClass:SLChessEngine"],
                          ["-ctd", engine], ["-tgd", engine]):
                with self.subTest(command=command[2], flags=flags):
                    self.assert_scope_denied(*flags, reason="Evil.permissionset-meta.xml", command=command)
            # The tests flag with its own value, then a real source flag: judged by that flag.
            for flags in (["-t", "SLChessEngineTest", "-l", "RunSpecifiedTests", "-d", self.D + "classes"],
                          ["-ct", "SLChessEngineTest", "-d", self.D + "classes"], ["--tests", "SLChessEngineTest", "-d", engine]):
                with self.subTest(command=command[2], flags=flags, allowed=True):
                    self.assert_scope_ok(*flags, command=command)
            self.assert_scope_denied("-t", "SLChessEngineTest", "-l", "RunSpecifiedTests", "-d", "force-app", reason="Evil.permissionset-meta.xml",
                                     command=command)
        self.assert_denied("project", "deploy", "start", "-td", engine, "--target-org", ORG, reason="approved scope")
        self.assertEqual(self.reached(), [])

    def test_a_boolean_short_flag_fused_in_front_of_the_org_flag_is_still_the_org_pin(self):
        self.layout()
        for flags in (["-co", ORG], ["-go", ORG], ["-cro", ORG], ["-co" + ORG]):
            allowed, reason = sf_guard.decide(["project", "deploy", "start", *flags, "--source-dir", "force-app"], ORG, prefix="SLChess",
                                              cwd=str(self.work))
            self.assertTrue(allowed, (flags, reason))
        allowed, reason = sf_guard.decide(["project", "deploy", "start", "-co", "other", "--source-dir", "force-app"], ORG, prefix="SLChess",
                                          cwd=str(self.work))
        self.assertFalse(allowed)
        self.assertIn("--target-org must be", reason)  # named as the wrong org, not as a missing one

    def test_a_link_followed_by_a_dot_dot_hop_is_judged_where_the_cli_deploys_it(self):
        # `x/s/../../evil`: the kernel walks s's target (emptydir/a/b) and finds the empty emptydir/evil; the CLI folds the hops away
        # lexically and deploys <cwd>/evil. Both are judged.
        base = self.layout(self.GOOD)
        (base / "emptydir" / "a" / "b").mkdir(parents=True)
        (base / "emptydir" / "evil").mkdir()
        (base / "evil" / "triggers").mkdir(parents=True)
        (base / "evil" / "triggers" / "T.trigger").write_text("x")
        (base / "x").mkdir()
        (base / "x" / "s").symlink_to(base / "emptydir" / "a" / "b", target_is_directory=True)
        self.assert_scope_denied("--source-dir", "x/s/../../evil", reason="evil/triggers/T.trigger")
        self.assert_scope_denied("-d", "x/s/../../evil", reason="evil/triggers/T.trigger", command=("project", "deploy", "validate"))
        # The same twist for a manifest path, in both directions: one spelling clean and the other not.
        clean = "<Package><types><members>SLChessEngine</members><name>ApexClass</name></types></Package>"
        dirty = "<Package><types><members>SLChessT</members><name>ApexTrigger</name></types></Package>"
        (base / "m1.xml").write_text(dirty)
        (base / "emptydir" / "m1.xml").write_text(clean)
        (base / "m2.xml").write_text(clean)
        (base / "emptydir" / "m2.xml").write_text(dirty)
        self.assert_scope_denied("--manifest", "x/s/../../m1.xml", reason="ApexTrigger")
        self.assert_scope_denied("--manifest", "x/s/../../m2.xml", reason="ApexTrigger")
        (base / "emptydir" / "m1.xml").write_text(dirty)
        (base / "m1.xml").write_text(clean)
        self.assert_scope_denied("--manifest", "x/s/../../m1.xml", reason="ApexTrigger")
        (base / "emptydir" / "m1.xml").write_text(clean)
        self.assert_scope_ok("--manifest", "x/s/../../m1.xml")

    def test_a_sibling_folder_that_shares_the_working_directory_s_name_as_a_prefix_is_outside(self):
        self.layout(self.GOOD)
        sibling = self.tmp / "work-evil"
        (sibling / "classes").mkdir(parents=True)
        (sibling / "classes" / "SLChessEvil.cls").write_text("x")  # fine by name: only the containment check can refuse it
        for flags in (["--source-dir", "../work-evil"], ["--source-dir", str(sibling)], ["--source-dir", "../work-evil/classes/SLChessEvil.cls"]):
            self.assert_scope_denied(*flags, reason="outside the project directory")

    def test_a_tree_with_more_entries_than_the_walk_limit_is_refused(self):
        self.layout()  # about fifteen empty folders
        with mock.patch.object(sf_guard, "SCOPE_WALK", 3):
            self.assert_scope_denied("--source-dir", "force-app", reason="more than 3 entries under force-app")
        self.assert_scope_ok("--source-dir", "force-app")

    def test_a_folder_that_cannot_be_read_is_refused_by_name(self):
        if os.geteuid() == 0:
            self.skipTest("root reads any folder")
        base = self.layout(self.GOOD)
        locked = base / "force-app" / "main" / "default" / "locked"
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o755)
        self.assert_scope_denied("--source-dir", "force-app", reason="force-app/main/default/locked (cannot be read)")

    def test_an_absolute_path_through_a_differently_spelled_working_directory_is_named_relative_to_it(self):
        self.layout(self.GOOD | {"triggers/T.trigger": "x"})
        linked = self.tmp / "linked-work"
        linked.symlink_to(self.work, target_is_directory=True)
        for spelled in (self.work, linked):
            trigger = spelled / (self.D + "triggers/T.trigger")
            self.assert_scope_denied("--source-dir", str(trigger), reason="slChess*: force-app/main/default/triggers/T.trigger (", base=linked)
        self.assert_scope_denied("--source-dir", "force-app", reason="slChess*: force-app/main/default/triggers/T.trigger (", base=linked)
        self.assert_scope_ok("--source-dir", str(self.work / (self.D + "classes/SLChessEngine.cls")), base=linked)

    def test_a_name_the_model_or_a_manifest_chose_is_not_repeated_without_a_bound(self):
        self.layout()
        long = "SLChess" + "x" * 1_000_000 + "!"
        why = self.assert_scope_denied("--metadata", f"ApexClass:{long}", reason="--metadata")
        self.assertLess(len(why), 1500)
        for member, kind in ((long, "ApexClass"), ("ok", "T" * 1_000_000)):
            (self.work / "long.xml").write_text(f"<Package><types><members>{member}</members><name>{kind}</name></types></Package>")
            why = self.assert_scope_denied("--manifest", "long.xml", reason="manifest 'long.xml'")
            self.assertLess(len(why), 1500)
        # A member that a DOCTYPE entity would expand to a megabyte is refused on the declaration, before anything expands.
        levels = ['<!ENTITY a "' + "x" * 1000 + '">'] + [f'<!ENTITY {n} "' + f"&{m};" * 10 + '">' for m, n in zip("abc", "bcd")]
        (self.work / "bomb.xml").write_text(f"<?xml version=\"1.0\"?><!DOCTYPE Package [{''.join(levels)}]><Package><types>"
                                            "<members>&d;</members><name>ApexClass</name></types></Package>")
        why = self.assert_scope_denied("--manifest", "bomb.xml", reason="DOCTYPE or ENTITY")
        self.assertLess(len(why), 1500)
        # The log keeps at most 2000 characters of a reason whatever echoes into it.
        done = self.sf("data", "query", "-q", "x", "--target-org", "y" * 5000)
        self.assertEqual(done.returncode, 2)
        self.assertLessEqual(len(self.calls()[-1]["reason"]), 2000)
        self.assertLess(len(done.stderr), 2200 + len(sf_guard.scope_line("sf", ORG, "SLChess")) + 1)  # + the fixed scope line

    def test_a_manifest_that_is_not_a_regular_file_is_refused_without_being_read(self):
        # Each is judged in a child with a timeout: reading the pipe would wait for a writer that never comes.
        self.layout()
        os.mkfifo(self.work / "fifo.xml")
        (self.work / "adir.xml").mkdir()
        (self.work / "big.xml").write_text("<Package>" + " " * 1_000_000 + "</Package>")
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import sf_guard; "
                "print(sf_guard.manifest_problems(sys.argv[2], sys.argv[3], 'SLChess', 'slChess'))")
        for name in ("fifo.xml", "adir.xml", "big.xml", "/dev/null"):
            done = subprocess.run([sys.executable, "-c", code, str(CHECKS), name, str(self.work)], capture_output=True, text=True, timeout=30)
            self.assertIn("must be a regular file of at most 1 MB", done.stdout, (name, done.stdout, done.stderr))
        done = subprocess.run([str(self.platform_dir / "bin" / "sf"), "project", "deploy", "start", "--manifest", "fifo.xml", "--target-org", ORG],
                              cwd=self.work, env=self.env(), capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
        self.assertEqual(done.returncode, 2)
        self.assertIn("regular file", done.stderr)
        self.assertEqual(self.reached(), [])

    def test_a_deploy_from_a_folder_inside_the_project_is_judged_relative_to_the_project(self):
        base = self.layout(self.GOOD | {"triggers/T.trigger": "x", "lwc/chess/classes/SLChessEngine.cls": "x"}, base=self.work / "proj")
        default = base / "force-app" / "main" / "default"
        for where, flags in ((default / "classes", ["-d", "SLChessEngine.cls"]), (default / "classes", ["--source-dir", "."]),
                             (default / "classes", ["-d", "../lwc/slChessBoard"]), (default / "lwc" / "slChessBoard", ["-d", "."]),
                             (default / "lwc" / "slChessBoard", ["-d", "slChessBoard.js"]), (default / "tabs", ["-d", "SLChess_Board.tab-meta.xml"]),
                             (base / "force-app", ["-d", "main/default/classes"]), (default / "classes", ["--metadata", "ApexClass:SLChessEngine"])):
            with self.subTest(where=where.name, flags=flags):
                allowed, reason = sf_guard.decide(["project", "deploy", "start", *flags, "--target-org", ORG], ORG, prefix="SLChess", cwd=str(where))
                self.assertTrue(allowed, reason)
        for flags, reason in (([], "T.trigger"), (["-d", "../triggers"], "T.trigger"), (["-d", "../../../.."], "T.trigger"),
                              (["-d", "../../../../.."], "outside the project directory"),
                              (["-d", "../lwc/chess/classes/SLChessEngine.cls"], "chess/classes")):
            with self.subTest(flags=flags):
                self.assert_scope_denied(*flags, reason=reason, base=default / "classes")

    def test_a_deploy_that_does_not_wait_is_refused(self):
        # --async, and a --wait the CLI accepts (1 minute and more) that is too short for a deploy to finish: the command returns and
        # the deploy keeps running in the org, where the case's cleanup could overlap it.
        self.layout(self.GOOD)
        for command in (("project", "deploy", "start"), ("project", "deploy", "validate")):
            for flags in (["--async"], ["--wait", "0"], ["-w", "0"], ["--wait=0"], ["-w0"], ["-gw", "0"], ["--wait", "00"], ["--wait", "0.0"],
                          ["--async", "--wait", "10"], ["--wait", "10", "--async"], ["--wait", "-1"],
                          ["--wait", "1"], ["-w", "1"], ["--wait=4"], ["-w4"], ["-gw", "2"], ["--wait", "4.9"], ["--wait", "10", "--wait", "3"],
                          # The CLI reads the value with parseInt(value, 10): `1e1` is 1, `1_0` is 1, `4.9e1` is 4, `1x` is 1, `1,5` is 1,
                          # `9abc` is 9 minutes. Python's float() reads three of them as 10, 10, 49 and raises on the rest; only ASCII digits pass.
                          ["--wait", "1e1"], ["--wait", "1_0"], ["--wait", "4.9e1"], ["--wait", "1x"], ["--wait", "1,5"],
                          ["--wait", "9abc"], ["-w", "10x"], ["--wait=1e1"], ["--wait", "\uff11\uff10"], ["--wait", "+10"],
                          ["--wait", " 10"], ["--wait", "10\n"], ["--wait", ""], ["--wait="], ["--wait", "1000000"]):
                with self.subTest(command=command[2], flags=flags):
                    allowed, reason = sf_guard.decide([*command, *flags, "--source-dir", "force-app", "--target-org", ORG], ORG, prefix="SLChess",
                                                      cwd=str(self.work))
                    self.assertFalse(allowed)
                    self.assertIn("wait for the deploy to finish", reason)
            for flags in ([], ["--wait", "10"], ["-w", "33"], ["--wait=10"], ["-w10"], ["-gw", "10"], ["--wait", "5"], ["-w5"],
                          ["--wait", "010"], ["--wait", "999999"],
                          # `-t` is --tests here, a value flag: `-tw 1` is tests ['w', '1'] and no --wait, so the default wait applies.
                          ["-tw", "1"], ["-t", "SLChessEngineTest", "-l", "RunSpecifiedTests"]):
                with self.subTest(command=command[2], flags=flags, allowed=True):
                    allowed, reason = sf_guard.decide([*command, *flags, "--source-dir", "force-app", "--target-org", ORG], ORG, prefix="SLChess",
                                                      cwd=str(self.work))
                    self.assertTrue(allowed, reason)
        # A short wait is told to use a larger value; --async is told to leave the flag out.
        allowed, reason = sf_guard.decide(["project", "deploy", "start", "--wait", "1", "--source-dir", "force-app", "--target-org", ORG], ORG,
                                          prefix="SLChess", cwd=str(self.work))
        self.assertIn("--wait 1 is denied", reason)
        self.assertIn("use --wait 5 or a larger value", reason)
        allowed, reason = sf_guard.decide(["project", "deploy", "start", "--async", "--source-dir", "force-app", "--target-org", ORG], ORG,
                                          prefix="SLChess", cwd=str(self.work))
        self.assertIn("leave it out", reason)
        # A report is not a deploy that runs on: the flag is another matter there.
        allowed, reason = sf_guard.decide(["project", "deploy", "report", "--async", "--job-id", "0Af000000000000AAA", "--target-org", ORG], ORG,
                                          prefix="SLChess")
        self.assertTrue(allowed, reason)
        self.assert_denied("project", "deploy", "start", "--source-dir", "force-app", "--async", "--target-org", ORG, "--json",
                           reason="wait for the deploy to finish")
        self.assert_denied("project", "deploy", "start", "--source-dir", "force-app", "--wait", "1", "--target-org", ORG, "--json",
                           reason="use --wait 5 or a larger value")
        self.assertEqual(self.reached(), [])

    def test_custom_objects_are_default_deny_and_opt_in_for_every_source_path_form(self):
        files = {
            "objects/SLChessMember__c/SLChessMember__c.object-meta.xml": "<CustomObject/>",
            "objects/SLChessMember__c/fields/Goal__c.field-meta.xml": "<CustomField/>",
            "objects/SLChess_Second_Member__c/SLChess_Second_Member__c.object-meta.xml": "<CustomObject/>",
            "objects/SLChess_Second_Member__c/fields/Preferred_Name__c.field-meta.xml": "<CustomField/>",
        }
        base = self.layout(files)
        self.assert_scope_denied("--source-dir", "force-app", reason="SLChessMember__c.object-meta.xml", base=base)
        self.assert_scope_ok("--source-dir", "force-app", base=base, custom_objects=True)
        self.assert_scope_ok(base=base, custom_objects=True)  # the default packageDirectories path
        for path in (self.D + "objects", self.D + "objects/SLChessMember__c",
                     self.D + "objects/SLChessMember__c/SLChessMember__c.object-meta.xml",
                     self.D + "objects/SLChessMember__c/fields/Goal__c.field-meta.xml"):
            self.assert_scope_ok("--source-dir", path, base=base, custom_objects=True)
        self.assert_scope_ok("--source-dir", self.D + "objects/SLChessMember__c", base=base, custom_objects=True,
                             command=("project", "deploy", "validate"))
        self.assert_scope_denied("--source-dir", self.D + "objects/SLChess*__c", reason="wildcard syntax", base=base, custom_objects=True)
        self.assert_denied("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json",
                           reason="SLChessMember__c.object-meta.xml")
        custom_guard = (f"{shlex.quote(sys.executable)} {shlex.quote(str(CHECKS / 'sf_guard.py'))} --org {ORG} --prefix SLChess "
                        "--custom-objects --")
        self.write_wrappers({"sf": custom_guard})
        self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json")

    def test_custom_object_and_field_metadata_are_exact_owned_names(self):
        self.layout()
        for entry in ("CustomObject:SLChessMember__c", "CustomField:SLChessMember__c.Goal__c",
                      "CustomObject:SLChess_Second_Member__c", "CustomField:SLChess_Second_Member__c.Preferred_Name__c",
                      "ApexClass:SLChessEngine", "PermissionSet:SLChess_Access"):
            if entry.startswith("PermissionSet:"):
                self.assert_scope_denied("--metadata", entry, reason="--metadata", custom_objects=True)
                self.assert_scope_ok("--metadata", entry, custom_objects=True, permission_sets=True)
            else:
                self.assert_scope_ok("--metadata", entry, custom_objects=True)
        self.assert_scope_ok("--metadata", "PermissionSet:SLChess_Access", permission_sets=True)
        self.assert_scope_denied("--metadata", "CustomObject:SLChessMember__c", reason="--metadata")
        self.assert_scope_denied("--metadata", "CustomField:SLChessMember__c.Goal__c", reason="--metadata")
        invalid = (
            "CustomObject:Account", "CustomObject:Other__c", "CustomObject:SLChessMember__mdt", "CustomObject:SLChessMember__c*",
            "CustomObject:SLChessBad__Inner__c", "CustomObject:SLChessBad__c__c",
            r"CustomObject:SLChessMember__c\*", "CustomField:Other__c.Goal__c", "CustomField:SLChessMember__c.Name",
            "CustomField:SLChessMember__c.Goal__mdt", "CustomField:SLChessMember__c.Goal__c*",
            "CustomField:SLChessMember__c.Bad__Inner__c", "CustomField:SLChessMember__c.Bad__c__c",
            r"CustomField:SLChessMember__c.Goal__c\*", "CustomField:SLChessMember__c.Goal__c.More",
            "CustomField:SLChessMember__c", "CustomField:SLChessMember__c.*",
        )
        for entry in invalid:
            with self.subTest(entry=entry):
                self.assert_scope_denied("--metadata", entry, reason="--metadata", custom_objects=True)

    def test_custom_manifests_require_exact_owned_objects_and_dot_fields(self):
        self.layout()
        good = ("<Package><types><members>SLChessMember__c</members><members>SLChess_Second_Member__c</members>"
                "<name>CustomObject</name></types><types><members>SLChessMember__c.Goal__c</members>"
                "<members>SLChess_Second_Member__c.Preferred_Name__c</members><name>CustomField</name></types></Package>")
        (self.work / "custom.xml").write_text(good)
        self.assert_scope_ok("--manifest", "custom.xml", custom_objects=True)
        self.assert_scope_ok("-x", "custom.xml", custom_objects=True, command=("project", "deploy", "validate"))
        self.assert_scope_denied("--manifest", "custom.xml", reason="CustomObject")
        manifests = (
            ("CustomObject", "Account", "owned"),
            ("CustomObject", "SLChessMember__mdt", "owned"),
            ("CustomObject", "SLChessBad__Inner__c", "owned"),
            ("CustomObject", "SLChessBad__c__c", "owned"),
            ("CustomObject", "SLChessMember__c*", "exact"),
            ("CustomObject", r"SLChessMember__c\*", "exact"),
            ("CustomField", "Other__c.Goal__c", "owned"),
            ("CustomField", "SLChessMember__c.Bad__Inner__c", "__c.<Name>__c"),
            ("CustomField", "SLChessMember__c.Bad__c__c", "__c.<Name>__c"),
            ("CustomField", "SLChessMember__c.Name", "__c.<Name>__c"),
            ("CustomField", "SLChessMember__c.Goal__c*", "__c.<Name>__c"),
            ("CustomField", r"SLChessMember__c.Goal__c\*", "__c.<Name>__c"),
            ("CustomField", "SLChessMember__c.Goal__c.More", "__c.<Name>__c"),
        )
        for number, (kind, member, reason) in enumerate(manifests):
            with self.subTest(kind=kind, member=member):
                (self.work / f"bad-{number}.xml").write_text(
                    f"<Package><types><members>{member}</members><name>{kind}</name></types></Package>")
                self.assert_scope_denied("--manifest", f"bad-{number}.xml", reason=reason, custom_objects=True)

    def test_custom_object_source_rejects_foreign_types_children_and_nested_strict_paths(self):
        cases = (
            ("objects/Other__c/Other__c.object-meta.xml", "Other__c.object-meta.xml"),
            ("objects/Account/Account.object-meta.xml", "Account.object-meta.xml"),
            ("objects/SLChessEvent__mdt/SLChessEvent__mdt.object-meta.xml", "SLChessEvent__mdt.object-meta.xml"),
            ("objects/SLChessEvent__e/SLChessEvent__e.object-meta.xml", "SLChessEvent__e.object-meta.xml"),
            ("objects/SLChessEvent__x/SLChessEvent__x.object-meta.xml", "SLChessEvent__x.object-meta.xml"),
            ("objects/SLChessEvent__b/SLChessEvent__b.object-meta.xml", "SLChessEvent__b.object-meta.xml"),
            ("objects/SLChessMember__Share/SLChessMember__Share.object-meta.xml", "SLChessMember__Share.object-meta.xml"),
            ("objects/SLChessMember__History/SLChessMember__History.object-meta.xml", "SLChessMember__History.object-meta.xml"),
            ("objects/SLChessMember__c/Other__c.object-meta.xml", "Other__c.object-meta.xml"),
            ("objects/SLChessBad__Inner__c/SLChessBad__Inner__c.object-meta.xml", "SLChessBad__Inner__c.object-meta.xml"),
            ("objects/SLChessBad__c__c/SLChessBad__c__c.object-meta.xml", "SLChessBad__c__c.object-meta.xml"),
            ("objects/SLChessMember__c/fields/Name.field-meta.xml", "Name.field-meta.xml"),
            ("objects/SLChessMember__c/fields/Bad__Inner__c.field-meta.xml", "Bad__Inner__c.field-meta.xml"),
            ("objects/SLChessMember__c/fields/Bad__c__c.field-meta.xml", "Bad__c__c.field-meta.xml"),
            ("objects/Account/fields/Goal__c.field-meta.xml", "Goal__c.field-meta.xml"),
            ("objects/SLChessMember__c/validationRules/SLChessMember__c.validationRule-meta.xml",
             "SLChessMember__c.validationRule-meta.xml"),
            ("objects/SLChessMember__c/classes/SLChessEngine.cls", "SLChessEngine.cls"),
            ("objects/SLChessMember__c/lwc/slChessBoard/slChessBoard.js", "slChessBoard.js"),
            ("objects/SLChessMember__c/fields/nested/Goal__c.field-meta.xml", "Goal__c.field-meta.xml"),
            ("classes/objects/SLChessMember__c/SLChessMember__c.object-meta.xml", "SLChessMember__c.object-meta.xml"),
            ("triggers/objects/SLChessMember__c/SLChessMember__c.object-meta.xml", "SLChessMember__c.object-meta.xml"),
        )
        for number, (rel, shown) in enumerate(cases):
            with self.subTest(rel=rel):
                base = self.layout({rel: "x"}, base=self.work / f"invalid-schema-{number}")
                self.assert_scope_denied("--source-dir", "force-app", reason=shown, base=base, custom_objects=True)
        base = self.layout({"objects/SLChessMember__c/SLChessMember__c.object-meta.xml": "<CustomObject/>"},
                           base=self.work / "linked-schema")
        outside = self.tmp / "outside-schema.xml"
        outside.write_text("<CustomField/>")
        field = base / (self.D + "objects/SLChessMember__c/fields/Goal__c.field-meta.xml")
        field.parent.mkdir(parents=True, exist_ok=True)
        field.symlink_to(outside)
        self.assert_scope_denied("--source-dir", "force-app", reason="leads outside the project directory", base=base, custom_objects=True)

    def test_custom_objects_and_permission_sets_are_independent_opt_ins(self):
        self.layout()
        self.assert_scope_ok("--metadata", "CustomObject:SLChessMember__c", custom_objects=True)
        self.assert_scope_denied("--metadata", "PermissionSet:SLChess_Access", reason="--metadata", custom_objects=True)
        self.assert_scope_ok("--metadata", "PermissionSet:SLChess_Access", permission_sets=True)
        self.assert_scope_denied("--metadata", "CustomObject:SLChessMember__c", reason="--metadata", permission_sets=True)
        self.assert_scope_ok("--metadata", "CustomObject:SLChessMember__c", "--metadata", "PermissionSet:SLChess_Access",
                             custom_objects=True, permission_sets=True)
        fixed = ["--org", "de", "--prefix", "SLChess", "--permission-sets", "--custom-objects", "--", "project", "deploy"]
        self.assertEqual(sf_guard.parse_fixed_options(fixed), ("de", "SLChess", False, "sf", ["project", "deploy"], True, True))
        self.assertEqual(sf_guard.parse_fixed(fixed), ("de", "SLChess", False, "sf", ["project", "deploy"], True))
        after_separator = sf_guard.parse_fixed_options(["--org", "de", "--prefix", "SLChess", "--", "--custom-objects"])
        self.assertEqual(after_separator[4:], (["--custom-objects"], False, False))
        self.assertNotIn("CustomObject", sf_guard.scope_line("sf", ORG, "SLChess"))
        scope = sf_guard.scope_line("sf", ORG, "SLChess", custom_objects=True)
        self.assertIn("CustomObject", scope)
        self.assertIn("CustomField", scope)


class HelpAndGenerateTest(GuardCase):
    def test_help_after_an_allowed_command_passes_without_an_org(self):
        for argv in (("project", "deploy", "start", "--help"), ("project", "deploy", "validate", "-h"), ("data", "query", "-h"),
                     ("apex", "run", "test", "--help", "--json"), ("project", "retrieve", "start", "--help"),
                     ("project:deploy:start", "--help"), ("sobject", "describe", "-h"), ("org", "list", "metadata", "--help"),
                     ("help", "project", "deploy"), ("apex", "get", "log", "--help"), ("project", "generate", "--help")):
            self.assert_reaches_sf(*argv)

    def test_help_for_a_group_of_allowed_commands_passes(self):
        for argv in (("project", "--help"), ("project", "deploy", "--help"), ("apex", "-h"), ("data", "--help"), ("sobject", "--help"),
                     ("org", "list", "--help"), ("apex", "run", "-h"), ("template", "--help")):
            self.assert_reaches_sf(*argv)

    def test_help_never_makes_a_denied_command_allowed(self):
        for argv, reason in ((("org", "display", "--help"), "access token"), (("org", "display", "-h", "--target-org", ORG), "access token"),
                             (("org:display", "--help"), "access token"), (("org", "open", "-h"), "session id"),
                             (("config", "set", "--help"), "configuration"), (("config", "get", "-h"), "configuration"),
                             (("alias", "list", "--help"), "aliases"), (("auth", "-h"), "authorization"),
                             (("data", "delete", "record", "--help"), "deletes data"), (("project", "delete", "source", "-h"), "deletes metadata"),
                             (("plugins", "install", "--help"), "changes the CLI"), (("update", "-h"), "changes the CLI"),
                             (("force", "source", "deploy", "--help"), "allow list"), (("totally-unknown", "--help"), "allow list"),
                             (("org", "list", "auth", "--help"), "allow list"), (("data", "resume", "--help"), "allow list"),
                             (("--json", "project", "deploy", "start", "--help"), "before the command"),
                             (("project", "deploy", "start", "--help", "--flags-dir", "fd"), "--flags-dir"),
                             (("project", "deploy", "start", "--help", "--", "x"), "`--`")):
            self.assert_denied(*argv, reason=reason)
        self.assertEqual(self.reached(), [])

    def test_the_local_scaffolding_families_pass_in_both_spellings(self):
        for argv in (("apex", "generate", "class", "--name", "SLChessEngine"), ("apex:generate:class", "--name", "SLChessEngine"),
                     ("apex", "generate", "trigger", "--name", "SLChessTrigger"), ("apex:generate:trigger", "--name", "T"),
                     ("template", "generate", "flexipage", "--name", "x"), ("template:generate:project", "--name", "x"),
                     ("template", "generate", "digital-experience", "site", "--name", "x"),
                     ("lightning:generate:component", "--name", "slChessBoard", "--type", "lwc"),
                     ("project:generate", "--name", "x")):
            self.assert_reaches_sf(*argv)
        # They are local: a generate family still cannot name another org, and the neighbours stay out.
        self.assert_denied("apex", "generate", "class", "--from-org", "other", reason="--from-org")
        self.assert_denied("apex", "tail", "log", "--target-org", ORG, reason="allow list")
        self.assert_denied("template", "publish", reason="allow list")

    def test_a_default_deny_lists_what_is_allowed(self):
        self.assert_denied("force", "source", "deploy", reason="allowed: ")
        done = self.sf("totally-unknown")
        for command in ("project deploy start", "project retrieve start", "apex run test", "apex generate ...", "template generate ...",
                        "data query", "org list", "lightning generate ...", "sobject describe", "help ..."):
            self.assertIn(command, done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 2)  # the denial with the list, then the scope without it

    def test_denials_of_reading_say_so(self):
        self.assert_denied("config", "get", "target-org", reason="reads or changes the CLI's configuration")
        self.assert_denied("alias", "list", reason="reads or changes aliases")
        self.assert_denied("org", "display", "--target-org", ORG, reason="shows the org's access token")


class CallLineTest(GuardCase):
    def test_an_allowed_call_writes_a_decision_line_then_an_end_line_with_the_same_call_id(self):
        self.use_sf(STUB)
        self.sf("data", "query", "-q", "x", "--target-org", ORG, env=self.env(STUB_EXIT="3"))
        raw = (self.platform_dir / sf_guard.LOG_NAME).read_text()
        decision, end = [json.loads(line) for line in raw.splitlines()]
        self.assertRegex(decision["call"], r"^[0-9a-f]{8}$")
        self.assertEqual(sorted(decision), ["argv", "call", "decision", "org", "prefix", "reason", "ts"])
        self.assertEqual((decision["decision"], decision["org"], decision["prefix"]), ("allowed", ORG, "SLChess"))
        self.assertEqual(sorted(end), ["call", "end", "exit", "interrupted", "stderr_head", "ts"])
        self.assertEqual((end["call"], end["end"], end["exit"], end["interrupted"]), (decision["call"], True, 3, False))
        for token in (TOKEN, SESSION):
            self.assertNotIn(token, raw)
        self.assertIn("[redacted]", end["stderr_head"])

    def test_a_denied_call_writes_one_line_and_each_call_has_its_own_id(self):
        self.sf("org", "display", "--target-org", ORG)
        self.sf("org", "list", "--json")
        self.sf("org", "list", "--json")
        lines = self.log_lines()
        self.assertEqual([("end" in line, line.get("decision")) for line in lines],
                         [(False, "denied"), (False, "allowed"), (True, None), (False, "allowed"), (True, None)])
        self.assertEqual(len({line["call"] for line in lines if "end" not in line}), 3)
        self.assertEqual(lines[1]["call"], lines[2]["call"])
        self.assertEqual(lines[3]["call"], lines[4]["call"])
        self.assertNotEqual(lines[1]["call"], lines[3]["call"])

    def test_the_decision_is_on_disk_before_the_real_sf_runs(self):
        seen = self.tmp / "seen.jsonl"
        self.use_sf(f"""#!{sys.executable}
import os, pathlib
pathlib.Path(os.environ["SEEN"]).write_text(pathlib.Path(os.environ["E2E_PLATFORM_DIR"], "sf-calls.jsonl").read_text())
""")
        self.sf("org", "list", "--json", env=self.env(SEEN=str(seen)))
        lines = [json.loads(line) for line in seen.read_text().splitlines()]
        self.assertEqual([("end" in line, line["decision"] if "end" not in line else None) for line in lines], [(False, "allowed")])

    def test_a_call_that_cannot_be_logged_is_denied_and_never_runs(self):
        (self.platform_dir / sf_guard.LOG_NAME).mkdir()  # the log cannot be opened for appending
        for argv in (("org", "list", "--json"), ("data", "query", "-q", "x", "--target-org", ORG, "--json")):
            done = self.sf(*argv)
            self.assertEqual(done.returncode, 2, argv)
            self.assertTrue(done.stderr.startswith("sf: denied by this run's guard: the call could not be logged"), (argv, done.stderr))
            self.assertEqual(len(done.stderr.strip().splitlines()), 1)
            self.assertEqual(done.stdout, "")
        self.assertEqual(self.reached(), [])
        done = self.sf("org", "display", "--target-org", ORG)  # a denied call says it was not logged either
        self.assertEqual(done.returncode, 2)
        self.assertIn("(and the call could not be logged)", done.stderr)

    def test_no_real_sf_and_a_real_sf_that_will_not_start_are_logged_as_ended(self):
        env = self.env(PATH=os.pathsep.join([str(self.platform_dir / "bin"), "/usr/bin", "/bin"]))
        self.write_wrappers(path=env["PATH"])
        done = self.sf("org", "list", "--json", env=env)
        self.assertEqual(done.returncode, 127)
        self.assertEqual([(end["exit"], end["interrupted"]) for end in self.ends()], [(127, False)])
        self.write_wrappers()
        self.use_sf("#!/nonexistent/interpreter\n")
        done = self.sf("org", "list", "--json")
        self.assertEqual(done.returncode, 126)
        self.assertIn("could not be started", done.stderr)
        self.assertEqual([end["exit"] for end in self.ends()], [127, 126])
        self.assertEqual(self.ends()[-1]["call"], self.calls()[-1]["call"])


class CrashTest(GuardCase):
    """Every call writes a decision line, so one that the policy cannot judge is a logged refusal, not a traceback."""

    def test_a_manifest_in_an_encoding_the_parser_does_not_know_is_a_logged_refusal(self):
        (self.work / "bogus.xml").write_text('<?xml version="1.0" encoding="bogus"?><Package/>')
        self.assert_denied("project", "deploy", "start", "--manifest", "bogus.xml", "--target-org", ORG, reason="not valid XML")

    def test_a_policy_that_raises_is_a_logged_refusal_and_never_reaches_sf(self):
        (self.work / "sfdx-project.json").write_text("[" * 200000 + "]" * 200000)  # json.loads gives up with RecursionError
        done = self.sf("project", "deploy", "start", "--target-org", ORG, "--json")
        self.assertEqual(done.returncode, 2)
        self.assertIn("sf: denied by this run's guard: the guard could not judge this call (RecursionError)", done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual(done.stdout, "")
        self.assertEqual([(entry["decision"], entry["argv"][:3]) for entry in self.calls()], [("denied", ["project", "deploy", "start"])])
        self.assertIn("could not judge", self.calls()[-1]["reason"])
        self.assertEqual(self.reached(), [])


class InterruptTest(GuardCase):
    SLEEPER = '#!/bin/sh\necho $$ > "$STUB_PID"\nexec sleep 30\n'

    def start(self) -> tuple[subprocess.Popen, Path]:
        pid_file = self.tmp / "child.pid"
        self.use_sf(self.SLEEPER)
        proc = subprocess.Popen([str(self.platform_dir / "bin" / "sf"), "org", "list", "--json"], cwd=self.work, env=self.env(STUB_PID=str(pid_file)),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        deadline = time.monotonic() + 15
        while not pid_file.exists() or not pid_file.read_text().strip():  # the child is running, so the handlers are installed
            self.assertLess(time.monotonic(), deadline, "the stand-in sf never started")
            time.sleep(0.05)
        return proc, pid_file

    def test_sigterm_sighup_and_sigint_are_forwarded_logged_as_interrupted_and_exit_143(self):
        # SIGINT is what a host's tool timeout or Ctrl-C sends: without the handler the wrapper dies with a traceback and no end line,
        # and the real sf keeps deploying.
        for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            with self.subTest(signal=number.name):
                before = len(self.log_lines())
                proc, pid_file = self.start()
                child = int(pid_file.read_text())
                pid_file.unlink()
                proc.send_signal(number)
                proc.communicate(timeout=20)
                self.assertEqual(proc.returncode, 143)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child, 0)  # the real sf got the signal and is gone
                decision, end = self.log_lines()[before:]
                self.assertEqual(decision["decision"], "allowed")
                self.assertEqual((end["call"], end["end"], end["exit"], end["interrupted"]), (decision["call"], True, 143, True))

    def test_once_the_real_sf_has_finished_a_signal_ends_the_wrapper_instead_of_being_swallowed(self):
        # The stand-in prints more than a pipe holds and nobody reads it, so the wrapper is blocked writing it back when the signal comes.
        self.use_sf(f"#!{sys.executable}\nimport sys\nsys.stdout.write('x' * 2_000_000)\n")
        proc = subprocess.Popen([str(self.platform_dir / "bin" / "sf"), "org", "list", "--json"], cwd=self.work, env=self.env(),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        self.addCleanup(proc.stdout.close)
        self.addCleanup(proc.stderr.close)
        deadline = time.monotonic() + 15
        while not self.ends():  # the end line is written once the real sf is gone
            self.assertLess(time.monotonic(), deadline, "the stand-in sf never finished")
            time.sleep(0.05)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
        self.assertEqual(proc.returncode, -signal.SIGTERM)

    def test_a_real_sf_that_ignores_the_signal_is_killed_after_the_grace_period(self):
        stub = self.tmp / "stubborn"
        stub.write_text("#!/bin/sh\ntrap '' TERM\nwhile :; do sleep 1; done\n")
        stub.chmod(0o755)
        state = {"proc": None, "interrupted": False, "at": 0.0}
        timer = threading.Timer(0.5, lambda: state.update(interrupted=True, at=time.monotonic()))  # the handler's flag, without its SIGTERM
        timer.start()
        self.addCleanup(timer.cancel)
        result: dict = {}
        worker = threading.Thread(target=lambda: result.update(code=sf_guard.run_real(str(stub), [], state)[2]), daemon=True)
        with mock.patch.object(sf_guard, "KILL_GRACE", 0.5):
            worker.start()
            worker.join(15)
        try:
            self.assertFalse(worker.is_alive(), "the stubborn sf was never killed")
        finally:
            if state["proc"] is not None and state["proc"].poll() is None:
                state["proc"].kill()
        self.assertEqual(result["code"], 143)


PS_GUARD = f"{shlex.quote(sys.executable)} \"$E2E_CHECKS/sf_guard.py\" --org {ORG} --prefix SLBattle --permission-sets --"


class PermissionSetTest(GuardCase):
    """`--permission-sets` (the battleship-salesforce case): a deploy may also carry PermissionSet named <prefix>*, and
    `org assign permset` is allowed only when every --name/-n starts with the prefix, the org is pinned and nothing assigns to
    another user. Without the flag (the chess case) both stay refused, as before."""

    D = "force-app/main/default/"
    FILES = {
        "classes/SLBattleEngine.cls": "public class SLBattleEngine {}",
        "lwc/slBattleBoard/slBattleBoard.js": "export default class SlBattleBoard {}",
        "tabs/SLBattle_Board.tab-meta.xml": "<CustomTab/>",
        "applications/SLBattle.app-meta.xml": "<CustomApplication/>",
        "permissionsets/SLBattle_Access.permissionset-meta.xml": "<PermissionSet/>",
    }

    def setUp(self):
        super().setUp()
        self.write_wrappers({"sf": PS_GUARD})  # the case's own sf wrapper, flag included
        (self.work / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app", "default": True}]}))
        for rel, text in self.FILES.items():
            path = self.work / (self.D + rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def decide(self, *argv: str, permission_sets: bool = True) -> tuple[bool, str]:
        return sf_guard.decide(list(argv), ORG, prefix="SLBattle", cwd=str(self.work), permission_sets=permission_sets)

    def test_the_fixed_flag_is_read_with_the_others(self):
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "--permission-sets", "--", "org", "list"]),
                         ("de", "P", False, "sf", ["org", "list"], True))
        self.assertEqual(sf_guard.parse_fixed(["--org", "de", "--prefix", "P", "--", "org", "list"])[5], False)

    def test_a_prefixed_permission_set_deploys_with_the_flag_in_every_form(self):
        ps = self.D + "permissionsets/SLBattle_Access.permissionset-meta.xml"
        (self.work / "package.xml").write_text(
            "<Package><types><members>SLBattle_Access</members><name>PermissionSet</name></types>"
            "<types><members>SLBattleEngine</members><name>ApexClass</name></types></Package>")
        for flags in (["--source-dir", "force-app"], [], ["-d", self.D + "permissionsets"], ["--source-dir", ps],
                      ["--metadata", "PermissionSet:SLBattle_Access"], ["--manifest", "package.xml"]):
            allowed, reason = self.decide("project", "deploy", "start", *flags, "--target-org", ORG)
            self.assertTrue(allowed, (flags, reason))
        done = self.assert_reaches_sf("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, "--json")
        self.assertEqual(json.loads(done.stdout)["status"], 0, done.stdout)

    def test_without_the_flag_a_permission_set_deploy_and_the_assignment_stay_refused(self):
        allowed, reason = self.decide("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG, permission_sets=False)
        self.assertFalse(allowed)
        self.assertIn("SLBattle_Access.permissionset-meta.xml", reason)
        allowed, reason = self.decide("project", "deploy", "start", "--metadata", "PermissionSet:SLBattle_Access", "--target-org", ORG,
                                      permission_sets=False)
        self.assertFalse(allowed)
        self.assertIn("--metadata", reason)
        allowed, reason = self.decide("org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", ORG, permission_sets=False)
        self.assertFalse(allowed)
        self.assertIn("not in the allow list", reason)
        self.assertNotIn("org assign permset", sf_guard.allowed_commands())

    def test_a_permission_set_outside_the_prefix_is_refused_even_with_the_flag(self):
        (self.work / (self.D + "permissionsets/Admin_Extra.permissionset-meta.xml")).write_text("<PermissionSet/>")
        allowed, reason = self.decide("project", "deploy", "start", "--source-dir", "force-app", "--target-org", ORG)
        self.assertFalse(allowed)
        self.assertIn("Admin_Extra.permissionset-meta.xml", reason)
        self.assertIn("permission set", reason)
        for entry in ("PermissionSet:Admin_Extra", "PermissionSet:slBattle_Access", "PermissionSet:*"):
            allowed, reason = self.decide("project", "deploy", "start", "--metadata", entry, "--target-org", ORG)
            self.assertFalse(allowed, entry)
            self.assertIn("PermissionSet:SLBattle<name>", reason)

    def test_assigning_a_prefixed_permission_set_to_the_logged_in_user_passes_in_every_spelling(self):
        for flags in (["--name", "SLBattle_Access"], ["-n", "SLBattle_Access"], ["--name=SLBattle_Access"], ["-nSLBattle_Access"],
                      ["-n=SLBattle_Access"], ["--name", "SLBattle_Access", "--name", "SLBattle_Extra"]):
            for org in (["--target-org", ORG], ["-o", ORG], [f"--target-org={ORG}"]):
                allowed, reason = self.decide("org", "assign", "permset", *flags, *org, "--json")
                self.assertTrue(allowed, (flags, org, reason))
        allowed, reason = self.decide("org:assign:permset", "--name", "SLBattle_Access", "--target-org", ORG)
        self.assertTrue(allowed, reason)
        self.assert_reaches_sf("org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", ORG, "--json")
        self.assertEqual(self.reached()[-1]["argv"][:3], ["org", "assign", "permset"])
        self.assertIn("org assign permset", sf_guard.allowed_commands(permission_sets=True))
        help_call = self.sf("org", "assign", "permset", "--help")
        self.assertEqual(self.calls()[-1]["decision"], "allowed", help_call.stderr)

    def test_another_permission_set_name_is_refused(self):
        for flags in (["--name", "Admin_Extra"], ["-n", "slBattle_Access"], ["--name", "SLBattle_Access", "--name", "Other"],
                      ["--name=Other"], ["-nOther"], ["--name", "SLBattle_Access,Other"], ["--name", "SLBattle Access"]):
            allowed, reason = self.decide("org", "assign", "permset", *flags, "--target-org", ORG)
            self.assertFalse(allowed, flags)
            self.assertIn("must start with SLBattle", reason)
        self.assert_denied("org", "assign", "permset", "--name", "Admin_Extra", "--target-org", ORG, "--json", reason="must start with SLBattle")

    def test_assigning_on_behalf_of_another_user_is_refused(self):
        for flags in (["--on-behalf-of", "someone@example.invalid"], ["--on-behalf-of=someone@example.invalid"], ["-b", "someone"],
                      ["-bsomeone"]):
            allowed, reason = self.decide("org", "assign", "permset", "--name", "SLBattle_Access", *flags, "--target-org", ORG)
            self.assertFalse(allowed, flags)
            self.assertIn("--on-behalf-of", reason)
        self.assert_denied("org", "assign", "permset", "--name", "SLBattle_Access", "--on-behalf-of", "x@example.invalid",
                           "--target-org", ORG, reason="--on-behalf-of")

    def test_an_assignment_without_a_name_is_refused(self):
        for flags in ([], ["--name"], ["-n"], ["--name", ""], ["--name="]):
            allowed, reason = self.decide("org", "assign", "permset", "--target-org", ORG, *flags)
            self.assertFalse(allowed, flags)
            self.assertIn("must carry --name", reason)
        self.assert_denied("org", "assign", "permset", "--target-org", ORG, "--json", reason="must carry --name")

    def test_a_wrapper_without_a_prefix_assigns_nothing_and_a_name_is_plain_ascii(self):
        allowed, reason = sf_guard.decide(["org", "assign", "permset", "--name", "Anything", "--target-org", ORG], ORG, permission_sets=True)
        self.assertFalse(allowed)
        self.assertIn("no --prefix", reason)
        allowed, reason = self.decide("org", "assign", "permset", "--name", "SLBattle_Acc\u00e9s", "--target-org", ORG)
        self.assertFalse(allowed)
        self.assertIn("must start with SLBattle", reason)

    def test_an_assignment_must_be_pinned_and_takes_no_word_or_flag_the_guard_cannot_read(self):
        allowed, reason = self.decide("org", "assign", "permset", "--name", "SLBattle_Access")
        self.assertFalse(allowed)
        self.assertIn("must carry --target-org", reason)
        allowed, reason = self.decide("org", "assign", "permset", "--name", "SLBattle_Access", "--target-org", "other")
        self.assertFalse(allowed)
        self.assertIn("--target-org must be", reason)
        # oclif reads the bare words after a repeatable flag as more values: `--name A Other` would assign Other too.
        for flags in (["--name", "SLBattle_Access", "Other"], ["--name=SLBattle_Access", "Other"],
                      ["--loglevel", "--name=Other", "--name", "SLBattle_Access"], ["--name", "SLBattle_Access", "--verbose"]):
            allowed, reason = self.decide("org", "assign", "permset", *flags, "--target-org", ORG)
            self.assertFalse(allowed, flags)
            self.assertIn("not accepted on `org assign permset`", reason)
        self.assertEqual(self.reached(), [])

    def test_the_scope_line_names_the_permission_set_kind_and_the_assignment(self):
        line = sf_guard.scope_line("sf", ORG, "SLBattle", permission_sets=True)
        self.assertIn("PermissionSet named SLBattle*", line)
        self.assertIn("org assign permset", line)
        self.assertNotIn("PermissionSet", sf_guard.scope_line("sf", ORG, "SLChess"))
        done = self.sf("totally-unknown")
        self.assertIn("org assign permset", done.stderr)
        self.assertIn("PermissionSet named SLBattle*", done.stderr)

    def test_the_battleship_case_wrapper_carries_the_flag_and_the_chess_case_wrapper_does_not(self):
        cases = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text())
        battle = cases["battleship-salesforce"]["platform"]["model_bin"]
        self.assertEqual(set(battle), {"sf", "sfdx", "osascript", "open"})
        self.assertIn("--prefix SLBattle --permission-sets --", battle["sf"])
        for name in ("sfdx", "osascript", "open"):
            self.assertIn(f"--deny-all --name {name} --", battle[name])
        self.assertNotIn("--permission-sets", json.dumps(cases["chess-salesforce"]["platform"]["model_bin"]))


if __name__ == "__main__":
    unittest.main()
