#!/usr/bin/env python3
"""The `chess-salesforce` case's checks (test/shiploop_e2e/checks/chess_salesforce.py), run against the fake `sf`.

No test here touches a real org: each puts test/shiploop_e2e/fake_sf.py on PATH as an executable named `sf` in a shim directory
and builds PATH from that directory plus /usr/bin:/bin only, so no other `sf` can be found (a test proves it). The fake refuses
every call whose --target-org is not `de`, so a check that fell back on the default org would fail loudly.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
CHECKS = E2E / "checks" / "chess_salesforce.py"
FAKE = E2E / "fake_sf.py"
TOKEN = "FAKE-TOKEN-DO-NOT-LOG"

spec = importlib.util.spec_from_file_location("chess_salesforce", CHECKS)
cs = importlib.util.module_from_spec(spec)
sys.modules["chess_salesforce"] = cs
spec.loader.exec_module(cs)

BASE_APEX = ["AccountTriage", "LeadScorer", "OrderService", "OrderServiceTest"]
BASE_LWC = ["baseCard%02d" % i for i in range(1, 14)]


class FakeOrg(unittest.TestCase):
    """A temp dir holding the shim, the fake's state and log, a throwaway HOME and the platform dir."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="chess-sf-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.shim = self.tmp / "shim"
        self.shim.mkdir()
        sf = self.shim / "sf"
        sf.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, FAKE))
        sf.chmod(sf.stat().st_mode | stat.S_IXUSR)
        self.state_path = self.tmp / "state.json"
        self.log_path = self.tmp / "calls.jsonl"
        self.platform = self.tmp / "platform"
        self.work = self.tmp / "cwd"
        self.work.mkdir()
        (self.tmp / "home").mkdir()
        self.set_state({"alias": "de", "connectedStatus": "Connected", "apex_classes": list(BASE_APEX), "lwc": list(BASE_LWC)})
        self.env = {
            "PATH": "%s:/usr/bin:/bin" % self.shim, "HOME": str(self.tmp / "home"), "FAKE_SF_STATE": str(self.state_path),
            "FAKE_SF_LOG": str(self.log_path), "FAKE_SF_ORGS": "de", "E2E_PLATFORM_DIR": str(self.platform),
            "TMPDIR": str(self.tmp / "tmpdir"),
        }
        (self.tmp / "tmpdir").mkdir()
        # The only `sf` any check can resolve is the shim: the real CLI's directory is not on this PATH.
        self.assertEqual(shutil.which("sf", path=self.env["PATH"]), str(self.shim / "sf"))

    # state of the fake org
    def state(self) -> dict:
        return json.loads(self.state_path.read_text())

    def set_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state))

    def add(self, apex=(), lwc=()) -> None:
        state = self.state()
        state["apex_classes"] += list(apex)
        state["lwc"] += list(lwc)
        self.set_state(state)

    def calls(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text().splitlines()] if self.log_path.exists() else []

    def deploys(self, destructive: bool | None = None) -> list[dict]:
        out = [c for c in self.calls() if c["argv"][:3] == ["project", "deploy", "start"]]
        if destructive is not None:
            out = [c for c in out if ("destructive" in c) == destructive]
        return out

    def run_check(self, *args: str, env: dict | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(CHECKS), *args], capture_output=True, text=True,
                              env=dict(self.env, **(env or {})), cwd=str(cwd or self.work), timeout=120)

    def out(self, proc: subprocess.CompletedProcess) -> str:
        return proc.stdout + proc.stderr

    def snapshot(self) -> None:
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def before(self) -> dict:
        return json.loads((self.platform / "before.json").read_text())


class TestShim(FakeOrg):
    def test_the_only_sf_on_the_path_is_the_fake(self) -> None:
        found = shutil.which("sf", path=self.env["PATH"])
        self.assertEqual(found, str(self.shim / "sf"))
        self.assertIn("fake_sf.py", Path(found).read_text())

    def test_the_fake_refuses_the_default_org_and_other_aliases(self) -> None:
        for extra in ([], ["--target-org", "prod"]):
            proc = subprocess.run(["sf", "data", "query", "--use-tooling-api", "-q", "SELECT COUNT() FROM ApexClass", "--json", *extra],
                                  capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(json.loads(proc.stdout)["status"], 1)
        self.assertTrue(all(c["refused"] for c in self.calls()))


class TestParsing(unittest.TestCase):
    def test_parse_json_skips_leading_warning_text(self) -> None:
        text = ' \u203a   Warning: update {x} available.\n{"status": 0, "result": {"a": 1}}\n'
        self.assertEqual(cs.parse_json(text), {"status": 0, "result": {"a": 1}})
        self.assertIsNone(cs.parse_json("no json here"))
        self.assertEqual(cs.parse_json('{"status": 0}'), {"status": 0})

    def test_scrub_replaces_secret_keys_and_token_shapes(self) -> None:
        token = "00D5g0000012345AAA!AQEAQabcdefghijklmnopqrstuvwxyz0123456789"
        self.assertNotIn(token, cs.scrub("header " + token + " trailer"))
        self.assertEqual(cs.scrub("x " + token), "x [redacted]")
        doc = {"result": {"accessToken": TOKEN, "list": [{"refreshToken": "r", "clientSecret": "c", "sfdxAuthUrl": "force://a:b@c", "ok": 1}]}}
        scrubbed = cs.scrub(doc)
        self.assertEqual(scrubbed["result"]["accessToken"], "[redacted]")
        self.assertEqual(scrubbed["result"]["list"][0], {"refreshToken": "[redacted]", "clientSecret": "[redacted]",
                                                         "sfdxAuthUrl": "[redacted]", "ok": 1})
        raw = json.dumps(doc)
        self.assertNotIn(TOKEN, cs.scrub(raw))
        self.assertNotIn("force://a:b@c", cs.scrub("url force://a:b@c done"))
        self.assertEqual(cs.scrub("plain text"), "plain text")

    def test_the_component_prefix_is_the_camel_case_spelling_of_the_apex_prefix(self) -> None:
        self.assertEqual([cs.lwc_prefix(p) for p in ("SLChess", "Chess", "SL", "chess")], ["slChess", "chess", "sl", "chess"])

    def test_plan_removal_refuses_look_alikes_and_snapshot_members(self) -> None:
        remove, refused = cs.plan_removal(["SLChessEngine", "slchessEvil", "AccountTriage", "SLChessKeep", "SLChess Bad", "SLChessA-b"],
                                          {"SLChessKeep"}, "SLChess")
        self.assertEqual(remove, ["SLChessEngine"])
        self.assertEqual({n for n, _ in refused}, {"slchessEvil", "AccountTriage", "SLChessKeep", "SLChess Bad", "SLChessA-b"})
        self.assertEqual(cs.plan_removal(["slChessBoard", "SLChessBoard"], set(), "slChess")[0], ["slChessBoard"])

    def test_destructive_xml_lists_exactly_the_members_and_no_wildcard(self) -> None:
        xml = cs.destructive_xml(["SLChessEngine", "SLChessEngineTest"], ["slChessBoard"])
        self.assertIn("<members>SLChessEngine</members>", xml)
        self.assertIn("<members>slChessBoard</members>", xml)
        self.assertNotIn("*", xml)
        self.assertNotIn("<types>", cs.empty_package_xml())


class TestPreflight(FakeOrg):
    def args(self, org: str = "de") -> tuple[str, ...]:
        return ("preflight", "--org", org, "--prefix", "SLChess")

    def test_clean_org_passes_and_writes_nothing(self) -> None:
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertFalse(self.platform.exists())
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertEqual(self.state()["apex_classes"], BASE_APEX)

    def test_the_warning_line_before_the_json_is_skipped(self) -> None:
        proc = self.run_check(*self.args(), env={"FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def test_prefixed_apex_class_fails(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessEngine", self.out(proc))
        self.assertIn("not clean", self.out(proc))

    def test_prefixed_component_fails(self) -> None:
        self.add(lwc=["slChessBoard"])
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("slChessBoard", self.out(proc))

    def test_a_look_alike_with_another_case_is_not_the_prefix(self) -> None:
        self.add(apex=["slchessOld", "SLCHESSOld"], lwc=["SLChessBoard"])
        self.assertEqual(self.run_check(*self.args()).returncode, 0)

    def test_alias_not_connected_fails(self) -> None:
        state = self.state()
        state["connectedStatus"] = "RefreshTokenAuthError"
        self.set_state(state)
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not connected", self.out(proc))
        self.assertEqual([c["argv"][:2] for c in self.calls()], [["org", "list"]])

    def test_unknown_alias_fails_without_querying(self) -> None:
        state = self.state()
        state["alias"] = "someone-else"
        self.set_state(state)
        proc = self.run_check(*self.args())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not in `sf org list`", self.out(proc))

    def test_an_org_the_fake_does_not_accept_fails(self) -> None:
        state = self.state()
        state["alias"] = "other"
        self.set_state(state)
        proc = self.run_check(*self.args("other"))
        self.assertEqual(proc.returncode, 1)


class TestSnapshot(FakeOrg):
    def test_snapshot_records_the_whole_org_sorted(self) -> None:
        self.add(apex=["ZedUtil"], lwc=["aaaFirst"])
        self.snapshot()
        before = self.before()
        self.assertEqual(before["apex_classes"], sorted(BASE_APEX + ["ZedUtil"]))
        self.assertEqual(before["lightning_component_bundles"], sorted(BASE_LWC + ["aaaFirst"]))
        self.assertEqual(before["counts"], {"ApexClass": 5, "LightningComponentBundle": 14})
        self.assertEqual((before["org"], before["prefix"]), ("de", "SLChess"))

    def test_the_platform_dir_defaults_to_platform_in_the_cwd(self) -> None:
        env = dict(self.env)
        del env["E2E_PLATFORM_DIR"]
        proc = subprocess.run([sys.executable, "-I", str(CHECKS), "snapshot", "--org", "de"], capture_output=True, text=True,
                              env=env, cwd=str(self.work))
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertTrue((self.work / "platform" / "before.json").is_file())

    def test_snapshot_refuses_a_dirty_org_and_writes_nothing(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check("snapshot", "--org", "de", "--prefix", "SLChess")
        self.assertEqual(proc.returncode, 1)
        self.assertFalse((self.platform / "before.json").exists())


class TestCleanup(FakeOrg):
    CLEAN = ("cleanup", "--org", "de", "--prefix", "SLChess")

    def deployed_like_a_model(self) -> None:
        self.snapshot()
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"])

    def test_removes_only_new_prefixed_items_and_verifies(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertTrue(record["verified"])
        self.assertEqual(sorted(r["name"] for r in record["removed"]),
                         ["SLChessController", "SLChessEngine", "SLChessEngineTest", "slChessBoard"])

    def test_the_destructive_deploy_names_exactly_those_members_with_an_empty_package(self) -> None:
        self.deployed_like_a_model()
        self.assertEqual(self.run_check(*self.CLEAN).returncode, 0)
        (call,) = self.deploys(destructive=True)
        self.assertEqual(call["destructive"], {"ApexClass": ["SLChessController", "SLChessEngine", "SLChessEngineTest"],
                                               "LightningComponentBundle": ["slChessBoard"]})
        self.assertEqual(call["manifest_types"], 0)
        self.assertIn("--post-destructive-changes", call["argv"])
        self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de")
        self.assertNotIn("*", json.dumps(call["destructive"]))

    def test_an_item_that_was_in_before_json_is_kept(self) -> None:
        self.snapshot()
        before = self.before()
        before["apex_classes"] = sorted(before["apex_classes"] + ["SLChessKeep"])
        (self.platform / "before.json").write_text(json.dumps(before))
        self.add(apex=["SLChessKeep", "SLChessEngine"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("SLChessKeep", self.state()["apex_classes"])
        self.assertNotIn("SLChessEngine", self.state()["apex_classes"])
        (call,) = self.deploys(destructive=True)
        self.assertEqual(call["destructive"]["ApexClass"], ["SLChessEngine"])

    def test_a_look_alike_name_is_refused_not_deleted_and_the_run_fails_verification(self) -> None:
        self.deployed_like_a_model()
        self.add(apex=["slchessSneaky"], lwc=["SLChessUpper"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        state = self.state()
        self.assertIn("slchessSneaky", state["apex_classes"])
        self.assertIn("SLChessUpper", state["lwc"])
        (call,) = self.deploys(destructive=True)
        self.assertNotIn("slchessSneaky", json.dumps(call["destructive"]))
        self.assertNotIn("SLChessUpper", json.dumps(call["destructive"]))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertFalse(record["verified"])
        self.assertEqual({r["name"] for r in record["refused"]}, {"slchessSneaky", "SLChessUpper"})
        self.assertIn("CLEANUP FAILED", proc.stderr)

    def test_nothing_else_is_ever_removed(self) -> None:
        self.deployed_like_a_model()
        self.run_check(*self.CLEAN)
        state = self.state()
        self.assertTrue(set(BASE_APEX) <= set(state["apex_classes"]))
        self.assertTrue(set(BASE_LWC) <= set(state["lwc"]))

    def test_idempotent_nothing_to_remove_is_success_without_a_deploy(self) -> None:
        self.deployed_like_a_model()
        self.assertEqual(self.run_check(*self.CLEAN).returncode, 0)
        deploys_before = len(self.deploys())
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(len(self.deploys()), deploys_before)
        self.assertEqual(json.loads((self.platform / "cleanup.json").read_text())["removed"], [])

    def test_a_clean_org_with_a_snapshot_is_success(self) -> None:
        self.snapshot()
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(self.deploys(), [])

    def test_without_before_json_nothing_is_deleted(self) -> None:
        self.add(apex=["SLChessEngine"])
        proc = self.run_check(*self.CLEAN)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])
        self.assertIn("SLChessEngine", self.state()["apex_classes"])

    def test_a_deploy_that_removes_nothing_is_not_verified(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_NOOP_DESTRUCTIVE": "1"})
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads((self.platform / "cleanup.json").read_text())["verified"])
        self.assertIn("SLChessEngine", self.out(proc))

    def test_a_failed_destructive_deploy_fails_and_says_so(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_FAIL": "destructive"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("destructive deploy failed", self.out(proc))
        record = json.loads((self.platform / "cleanup.json").read_text())
        self.assertEqual((record["verified"], record["removed"]), (False, []))

    def test_a_failed_query_fails_closed(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_FAIL": "query"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])

    def test_the_warning_line_does_not_break_cleanup(self) -> None:
        self.deployed_like_a_model()
        proc = self.run_check(*self.CLEAN, env={"FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))


def make_project(tmp: Path, classes=("SLChessEngine", "SLChessController", "SLChessEngineTest"), bundle="slChessBoard", extra=()) -> Path:
    project = tmp / "proj"
    shutil.rmtree(project, ignore_errors=True)
    base = project / "force-app" / "main" / "default"
    (base / "classes").mkdir(parents=True)
    for name in classes:
        (base / "classes" / (name + ".cls")).write_text("public class %s {}" % name)
        (base / "classes" / (name + ".cls-meta.xml")).write_text("<ApexClass/>")
    (base / "lwc" / bundle).mkdir(parents=True)
    (base / "lwc" / bundle / (bundle + ".js")).write_text("export default class X {}")
    (base / "lwc" / bundle / (bundle + ".html")).write_text("<template></template>")
    (base / "lwc" / ".eslintrc.json").write_text("{}")
    (base / "lwc" / "jsconfig.json").write_text("{}")
    (project / "sfdx-project.json").write_text(json.dumps({"packageDirectories": [{"path": "force-app"}]}))
    for rel in extra:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("<x/>")
    return project


class TestProject(FakeOrg):
    def make(self, **kwargs) -> Path:
        return make_project(self.tmp, **kwargs)

    def run_project(self, project: Path) -> subprocess.CompletedProcess:
        return self.run_check("project", "--org", "de", cwd=project)

    def test_a_complete_project_passes(self) -> None:
        proc = self.run_project(self.make())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertEqual(self.calls(), [])  # no sf call at all

    def test_missing_engine_fails(self) -> None:
        proc = self.run_project(self.make(classes=("SLChessController",)))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessEngine.cls", self.out(proc))

    def test_no_sfdx_project_json_fails(self) -> None:
        project = self.make()
        (project / "sfdx-project.json").unlink()
        self.assertEqual(self.run_project(project).returncode, 1)

    def test_component_without_html_fails(self) -> None:
        project = self.make()
        next(project.rglob("slChessBoard.html")).unlink()
        proc = self.run_project(project)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(".html", self.out(proc))

    def test_wrong_component_name_fails(self) -> None:
        self.assertEqual(self.run_project(self.make(bundle="chessBoard")).returncode, 1)

    def test_a_class_without_the_prefix_fails(self) -> None:
        self.assertEqual(self.run_project(self.make(classes=("SLChessEngine", "Helper"))).returncode, 1)

    def test_other_metadata_fails(self) -> None:
        for extra in ("objects/Thing__c/Thing__c.object-meta.xml", "flows/F.flow-meta.xml", "permissionsets/P.permissionset-meta.xml"):
            proc = self.run_project(self.make(extra=(extra,)))
            self.assertEqual(proc.returncode, 1, extra)
            self.assertIn("other metadata", self.out(proc))


class TestDeployedAndTests(FakeOrg):
    def deploy_all(self, tests=("SLChessEngineTest", "SLChessMovesTest")) -> None:
        self.add(apex=["SLChessEngine", "SLChessController", *tests], lwc=["slChessBoard"])

    def run_deployed(self, *extra: str) -> subprocess.CompletedProcess:
        return self.run_check("deployed", "--org", "de", "--prefix", "SLChess", *extra)

    def test_deployed_passes_when_everything_is_there(self) -> None:
        self.deploy_all()
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 0, self.out(proc))

    def test_deployed_names_what_is_missing(self) -> None:
        self.add(apex=["SLChessEngine", "SLChessEngineTest"])
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SLChessController", self.out(proc))
        self.assertIn("slChessBoard", self.out(proc))

    def test_deployed_needs_a_test_class(self) -> None:
        self.deploy_all(tests=())
        proc = self.run_deployed()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Test classes", self.out(proc))

    def test_a_look_alike_test_class_does_not_count(self) -> None:
        self.deploy_all(tests=("slchessEngineTest", "SLChessEngineTests"))
        self.assertEqual(self.run_deployed().returncode, 1)

    def test_tests_pass_with_enough_methods_one_call_per_class(self) -> None:
        self.deploy_all()
        proc = self.run_check("tests", "--org", "de", "--prefix", "SLChess", "--min-tests", "8")
        self.assertEqual(proc.returncode, 0, self.out(proc))
        runs = [c["argv"] for c in self.calls() if c["argv"][:3] == ["apex", "run", "test"]]
        self.assertEqual(sorted(a[a.index("--class-names") + 1] for a in runs), ["SLChessEngineTest", "SLChessMovesTest"])
        self.assertTrue(all("--synchronous" in a and a[a.index("--target-org") + 1] == "de" for a in runs))

    def test_threshold_counts_total_tests_that_ran(self) -> None:
        self.deploy_all()
        counts = self.tmp / "tests.json"
        counts.write_text(json.dumps({"testsRan": 3}))
        low = self.run_check("tests", "--org", "de", "--min-tests", "8", env={"FAKE_SF_TESTS": str(counts)})
        self.assertEqual(low.returncode, 1)
        self.assertIn("need at least 8", self.out(low))
        enough = self.run_check("tests", "--org", "de", "--min-tests", "6", env={"FAKE_SF_TESTS": str(counts)})
        self.assertEqual(enough.returncode, 0, self.out(enough))

    def test_a_failing_test_fails(self) -> None:
        self.deploy_all()
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 10, "failing": 1}))
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(results)})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL", self.out(proc))

    def test_outcome_must_be_passed_even_with_zero_failing(self) -> None:
        self.deploy_all()
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Skipped", "testsRan": 10, "failing": 0}))
        self.assertEqual(self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(results)}).returncode, 1)

    def test_no_test_class_fails(self) -> None:
        self.deploy_all(tests=())
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([c for c in self.calls() if c["argv"][:3] == ["apex", "run", "test"]], [])

    def test_a_failed_test_run_command_fails(self) -> None:
        self.deploy_all()
        proc = self.run_check("tests", "--org", "de", "--min-tests", "1", env={"FAKE_SF_TESTS": str(self.tmp / "none.json"), "FAKE_SF_FAIL": "test"})
        self.assertEqual(proc.returncode, 1)


class TestRules(FakeOrg):
    def canned(self, **override) -> Path:
        values = {marker: expected for _name, _script, marks in cs.rule_cases() for marker, expected in marks}
        values.update(override)
        path = self.tmp / "apex.json"
        path.write_text(json.dumps(values))
        return path

    def run_rules(self, canned: Path) -> subprocess.CompletedProcess:
        return self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(canned)})

    def test_the_oracle_table_is_the_published_one(self) -> None:
        table = {name: (one, two) for name, _fen, one, two in cs.PERFT}
        self.assertEqual(table, {"start": (20, 400), "kiwipete": (48, None), "pos3": (14, 191), "pos4": (6, 264),
                                 "pos5": (44, 1486), "castle": (26, None)})

    def test_matching_logs_pass_and_every_position_prints_a_line(self) -> None:
        proc = self.run_rules(self.canned())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        self.assertIn("PASS start.p1 expected=20 got=20", proc.stdout)
        self.assertIn("PASS pos5.p2 expected=1486 got=1486", proc.stdout)
        self.assertIn("PASS foolsmate expected=checkmate got=checkmate", proc.stdout)
        self.assertNotIn("FAIL", proc.stdout)

    def test_each_position_is_its_own_anonymous_apex_call_with_a_harness_owned_file(self) -> None:
        proc = self.run_rules(self.canned())
        self.assertEqual(proc.returncode, 0, self.out(proc))
        runs = [c for c in self.calls() if c["argv"][:2] == ["apex", "run"]]
        self.assertEqual(len(runs), len(cs.rule_cases()))
        for call in runs:
            file = Path(call["argv"][call["argv"].index("--file") + 1])
            self.assertTrue(str(file).startswith(str(self.tmp / "tmpdir")), file)
            self.assertFalse(file.exists(), "the temp script is removed afterwards")
            self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de")
        markers = [m for c in runs for m in c["apex_markers"]]
        self.assertEqual(markers, [marker for _n, _s, marks in cs.rule_cases() for marker, _e in marks])

    def test_the_scripts_call_only_the_interface_in_the_prompt(self) -> None:
        for _name, script, _marks in cs.rule_cases():
            for call in __import__("re").findall(r"SLChess\w*\.\w+", script):
                self.assertIn(call, {"SLChessEngine.legalMoves", "SLChessEngine.applyMove", "SLChessEngine.status",
                                     "SLChessEngine.startFen", "SLChessEngine.IllegalMoveException"})

    def test_a_wrong_count_fails_and_shows_expected_and_got(self) -> None:
        proc = self.run_rules(self.canned(**{"start.p2": "399"}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL start.p2 expected=400 got=399", proc.stdout)
        self.assertIn("PASS start.p1 expected=20 got=20", proc.stdout)

    def test_a_wrong_status_or_missing_result_fails(self) -> None:
        proc = self.run_rules(self.canned(scholarsmate="check"))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL scholarsmate expected=checkmate got=check", proc.stdout)
        canned = json.loads(self.canned().read_text())
        del canned["epfield"]
        (self.tmp / "apex2.json").write_text(json.dumps(canned))
        again = self.run_rules(self.tmp / "apex2.json")
        self.assertEqual(again.returncode, 1)
        self.assertIn("FAIL epfield expected=e3 got=MISSING", again.stdout)

    def test_an_engine_over_the_cpu_limit_fails_with_the_apex_error_shown(self) -> None:
        proc = self.run_rules(self.canned(**{"kiwipete.p1": {"error": "System.LimitException: Maximum CPU time exceeded"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL kiwipete.p1", proc.stdout)
        self.assertIn("Maximum CPU time exceeded", proc.stdout)

    def test_a_compile_error_fails_with_the_problem_shown(self) -> None:
        proc = self.run_rules(self.canned(**{"start.p1": {"compileProblem": "Variable does not exist: SLChessEngine"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("compile error: Variable does not exist", proc.stdout)

    def test_an_apex_command_failure_fails(self) -> None:
        proc = self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(self.canned()), "FAKE_SF_FAIL": "apex"})
        self.assertEqual(proc.returncode, 1)

    def test_the_warning_line_does_not_break_rules(self) -> None:
        proc = self.run_check("rules", "--org", "de", env={"FAKE_SF_APEX": str(self.canned()), "FAKE_SF_WARN": "1"})
        self.assertEqual(proc.returncode, 0, self.out(proc))


class TestSelftest(FakeOrg):
    def run_selftest(self, **env) -> subprocess.CompletedProcess:
        return self.run_check("selftest", "--org", "de", "--prefix", "SLChess", env=env)

    def test_rehearsal_deploys_tests_and_removes_the_probe(self) -> None:
        proc = self.run_selftest()
        self.assertEqual(proc.returncode, 0, self.out(proc))
        for step in ("preflight", "snapshot", "deploy", "deployed", "tests", "cleanup"):
            self.assertIn("PASS %s:" % step, proc.stdout)
        state = self.state()
        self.assertEqual((sorted(state["apex_classes"]), sorted(state["lwc"])), (sorted(BASE_APEX), sorted(BASE_LWC)))
        (add,) = self.deploys(destructive=False)
        self.assertEqual(add["argv"][add["argv"].index("--target-org") + 1], "de")
        (rm,) = self.deploys(destructive=True)
        self.assertEqual(rm["destructive"], {"ApexClass": ["SLChessProbe", "SLChessProbeTest"], "LightningComponentBundle": ["slChessProbe"]})

    def test_a_failing_probe_test_still_cleans_up(self) -> None:
        results = self.tmp / "tests.json"
        results.write_text(json.dumps({"outcome": "Failed", "testsRan": 1, "failing": 1}))
        proc = self.run_selftest(FAKE_SF_TESTS=str(results))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL tests:", proc.stdout)
        self.assertIn("PASS cleanup:", proc.stdout)
        self.assertEqual(sorted(self.state()["apex_classes"]), sorted(BASE_APEX))

    def test_a_failed_deploy_still_attempts_cleanup(self) -> None:
        proc = self.run_selftest(FAKE_SF_FAIL="deploy")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("FAIL deploy:", proc.stdout)
        self.assertEqual(len(self.deploys(destructive=False)), 1)  # the one add attempt, which failed
        self.assertIn("PASS cleanup:", proc.stdout)  # snapshot was taken, so cleanup ran and verified an unchanged org

    def test_a_cleanup_that_cannot_verify_is_loud(self) -> None:
        proc = self.run_selftest(FAKE_SF_NOOP_DESTRUCTIVE="1")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("MANUAL CLEANUP NEEDED", proc.stdout)

    def test_a_dirty_org_stops_before_any_deploy(self) -> None:
        self.add(apex=["SLChessLeftover"])
        proc = self.run_selftest()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.deploys(), [])
        self.assertIn("SLChessLeftover", self.state()["apex_classes"])


class TestNoCredentialsAnywhere(FakeOrg):
    def test_the_token_never_reaches_any_output_or_file_and_org_display_is_never_called(self) -> None:
        outputs = []
        env = {"FAKE_SF_WARN": "1"}
        canned = self.tmp / "apex.json"
        canned.write_text(json.dumps({m: e for _n, _s, marks in cs.rule_cases() for m, e in marks}))
        project = make_project(self.tmp)
        steps = [
            ("preflight", "--org", "de"), ("snapshot", "--org", "de"),
        ]
        for step in steps:
            outputs.append(self.run_check(*step, env=env))
        self.add(apex=["SLChessEngine", "SLChessController", "SLChessEngineTest"], lwc=["slChessBoard"])
        outputs.append(self.run_check("project", "--org", "de", cwd=project, env=env))
        outputs.append(self.run_check("deployed", "--org", "de", env=env))
        outputs.append(self.run_check("tests", "--org", "de", "--min-tests", "8", env=env))
        outputs.append(self.run_check("rules", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned))))
        outputs.append(self.run_check("cleanup", "--org", "de", env=env))
        outputs.append(self.run_check("selftest", "--org", "de", env=env))
        failing = self.run_check("rules", "--org", "de", env=dict(env, FAKE_SF_APEX=str(canned), FAKE_SF_FAIL="apex"))
        outputs.append(failing)
        self.assertEqual([p.returncode for p in outputs[:-1]], [0] * (len(outputs) - 1), [self.out(p) for p in outputs])
        for proc in outputs:
            self.assertNotIn(TOKEN, proc.stdout)
            self.assertNotIn(TOKEN, proc.stderr)
        for path in self.tmp.rglob("*"):
            if path.is_file() and path != self.shim / "sf":
                self.assertNotIn(TOKEN, path.read_text(errors="replace"), str(path))
        calls = self.calls()
        self.assertGreater(len(calls), 20)
        self.assertEqual([c for c in calls if c["argv"][:2] == ["org", "display"]], [])
        self.assertEqual([c for c in calls if c["refused"]], [])
        for call in calls:
            if call["argv"][:2] != ["org", "list"]:
                self.assertEqual(call["argv"][call["argv"].index("--target-org") + 1], "de", call["argv"])
            self.assertIn("--json", call["argv"])

    def test_a_credential_in_an_error_message_is_scrubbed_from_what_a_check_prints(self) -> None:
        # The fake never emits a real-shaped token; prove the printing path scrubs one anyway.
        token = "00D5g0000012345AAA!AQEAQabcdefghijklmnopqrstuvwxyz0123456789"
        proc = subprocess.run([sys.executable, "-I", "-c",
                               "import importlib.util,sys\n"
                               "s=importlib.util.spec_from_file_location('c', %r); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                               "m.say('boom %s accessToken\": \"abc\"')\n" % (str(CHECKS), token)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn(token, proc.stdout)
        self.assertIn("[redacted]", proc.stdout)


if __name__ == "__main__":
    unittest.main()
