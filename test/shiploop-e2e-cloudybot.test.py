"""Hermetic unit tests for the opt-in `cloudybot` Salesforce E2E case, guard, and lifecycle hooks."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
E2E = ROOT / "test" / "shiploop_e2e"
CHECKS = E2E / "checks"
if str(E2E) not in sys.path:
    sys.path.insert(0, str(E2E))

import run  # noqa: E402


FAKE_SF_CODE = textwrap.dedent(r"""
    import json
    import os
    from pathlib import Path
    import sys

    state_file = Path(os.environ["CLOUDYBOT_FAKE_SF_STATE"])
    state = json.loads(state_file.read_text(encoding="utf-8"))
    calls_log = Path(os.environ["CLOUDYBOT_FAKE_SF_CALLS"])
    argv = sys.argv[1:]
    with calls_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"argv": argv, "sf_target_org": os.environ.get("SF_TARGET_ORG")}) + "\n")

    def save_state():
        state_file.write_text(json.dumps(state), encoding="utf-8")

    if argv == ["--version"]:
        print("@salesforce/cli/2.154.4 darwin-arm64 node-v25.9.0")
        raise SystemExit(0)

    if argv[:2] == ["org", "list"] and (len(argv) == 2 or argv[2] == "--json"):
        print(json.dumps({
            "status": 0,
            "result": {
                "nonScratchOrgs": [{
                    "alias": state.get("alias", "de"),
                    "username": state.get("username", "user@example.com"),
                    "connectedStatus": state.get("connectedStatus", "Connected"),
                }]
            }
        }))
        raise SystemExit(0)

    if argv[:3] == ["org", "list", "metadata"]:
        mtype = argv[argv.index("--metadata-type") + 1]
        if mtype in state.get("unsupported_types", []):
            print(json.dumps({"status": 1, "message": f"INVALID_TYPE: {mtype} not supported"}))
            raise SystemExit(1)
        items = [{"fullName": n} for n in state.get("metadata", {}).get(mtype, [])]
        print(json.dumps({"status": 0, "result": items}))
        raise SystemExit(0)

    if argv[:2] == ["data", "query"]:
        soql = argv[argv.index("--query") + 1]
        if "FROM ApexClass" in soql and "Body" in soql:
            recs = [{"Name": n, "Body": b} for n, b in state.get("apex_bodies", {}).items()]
            print(json.dumps({"status": 0, "result": {"records": recs}}))
            raise SystemExit(0)
        if "FROM ApexClass" in soql:
            recs = [{"Name": n, "LastModifiedDate": d} for n, d in state.get("dates", {}).get("ApexClass", {}).items()]
            print(json.dumps({"status": 0, "result": {"records": recs}}))
            raise SystemExit(0)
        if "FROM LightningComponentBundle" in soql:
            recs = [{"DeveloperName": n, "LastModifiedDate": d} for n, d in state.get("dates", {}).get("LightningComponentBundle", {}).items()]
            print(json.dumps({"status": 0, "result": {"records": recs}}))
            raise SystemExit(0)
        if "FROM PermissionSetAssignment" in soql:
            recs = []
            for r in state.get("assignments", []):
                rec = {"Id": r["Id"], "PermissionSet": {"Name": r.get("PermissionSetName")}}
                if r.get("PermissionSetGroupName"):
                    rec["PermissionSet"] = {"Name": None}
                    rec["PermissionSetGroup"] = {"DeveloperName": r["PermissionSetGroupName"]}
                recs.append(rec)
            print(json.dumps({"status": 0, "result": {"records": recs}}))
            raise SystemExit(0)
        if "FROM PermissionSetTabSetting" in soql:
            print(json.dumps({"status": 0, "result": {"records": state.get("tab_visibility", [])}}))
            raise SystemExit(0)
        print(json.dumps({"status": 0, "result": {"records": []}}))
        raise SystemExit(0)

    if argv[:3] == ["data", "delete", "record"]:
        rid = argv[argv.index("--record-id") + 1]
        state["assignments"] = [r for r in state.get("assignments", []) if r["Id"] != rid]
        save_state()
        print(json.dumps({"status": 0, "result": {"id": rid, "success": True}}))
        raise SystemExit(0)

    if argv[:3] == ["project", "deploy", "start"]:
        if "--post-destructive-changes" in argv:
            import xml.etree.ElementTree as ET
            dest = Path(argv[argv.index("--post-destructive-changes") + 1])
            tree = ET.fromstring(dest.read_text(encoding="utf-8"))
            ns = "{http://soap.sforce.com/2006/04/metadata}"
            for tel in tree.findall(f"{ns}types"):
                kind = tel.find(f"{ns}name").text
                members = {m.text for m in tel.findall(f"{ns}members")}
                cur = state.get("metadata", {}).get(kind, [])
                state.setdefault("metadata", {})[kind] = [x for x in cur if x not in members]
                if kind in state.get("dates", {}):
                    for m in members:
                        state["dates"][kind].pop(m, None)
            save_state()
        tok = state.get("leak_token")
        if tok:
            sys.stderr.write(f"debug session={tok}\n")
        print(json.dumps({"status": 0, "result": {"success": True}}))
        raise SystemExit(0)

    if argv[:3] == ["apex", "run", "test"]:
        print(state.get("tap_output", "1..0\n"))
        raise SystemExit(int(state.get("tap_exit", 0)))

    print(json.dumps({"status": 0, "result": {}}))
""")


class CloudyBotCatalogTests(unittest.TestCase):
    def test_case_loads_validates_and_renames_prefix_cleanly(self):
        cases = run.catalog()
        self.assertIn("cloudybot", cases)
        name, prompt, checks, follows = run.load_case(type("Args", (), {"prompt": None, "case": "cloudybot", "check": None})())
        self.assertEqual(name, "cloudybot")
        self.assertIsNone(follows)
        self.assertEqual(len(checks), 3)
        self.assertIn("CloudyBot", prompt)
        self.assertIn("cloudyBot", prompt)
        for clause in (
            "Config Mode",
            "aiplatform.ModelsAPI",
            "Send to background task",
            "steer",
            "New update ready",
            "backpressure",
            "systemPromptAppend",
            "Public Group",
            "USER_MODE",
            "sf_soql_query",
            "sessionId",
            "Bedrock",
            "Gemini",
            "Claude",
            "@InvocableMethod",
            "WaitingOnBot",
            "SKILL.md",
            "marketplace.json",
            "PullRequest",
            "statusNote",
            "Worked for",
            "Grok",
            "GovCloud",
            "Test Connection",
            "default URL",
            "Admin-Only",
            "Admin-Locked",
            "Kill Switch",
            "Response Format",
            "Visual",
        ):
            self.assertIn(clause, prompt)

        spec = run.case_platform("cloudybot")
        self.assertIsNotNone(spec)
        run.refuse_unmatched_keep_checks("cloudybot", spec, checks)

        renamed = run.with_prefix(cases["cloudybot"], "NimbusBot")
        self.assertIn("NimbusBot", renamed["prompt"])
        self.assertIn("nimbusBot", renamed["prompt"])
        self.assertNotIn("CloudyBot", json.dumps(renamed))
        self.assertNotIn("cloudyBot", json.dumps(renamed))
        self.assertNotIn("cloudybot", renamed["prompt"])

        terms = json.loads((E2E / "probe_terms.json").read_text(encoding="utf-8"))
        self.assertIn("cloudybot", terms["terms"])
        suites = json.loads((E2E / "suites.json").read_text(encoding="utf-8"))
        self.assertIn("hosted-platform", suites["breadth"]["not_covered"])


class CloudyBotGuardAndCheckerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.bin_dir = self.root / "real_bin"
        self.bin_dir.mkdir()
        self.pdir = self.root / "platform"
        self.pdir.mkdir()
        self.proj = self.root / "proj"
        self.proj.mkdir()

        self.state_file = self.root / "sf_state.json"
        self.calls_log = self.root / "sf_calls.jsonl"
        self.state_file.write_text(
            json.dumps({
                "alias": "de",
                "username": "owner@example.com",
                "connectedStatus": "Connected",
                "metadata": {
                    "ApexClass": ["ExistingOtherClass"],
                    "LightningComponentBundle": ["existingOtherLwc"],
                    "CustomTab": [],
                    "CustomApplication": [],
                    "PermissionSet": [],
                    "PermissionSetGroup": [],
                    "CustomPermission": [],
                    "CustomObject": [],
                    "CustomMetadata": [],
                    "Group": [],
                    "ApexTrigger": [],
                    "FlexiPage": [],
                    "Flow": [],
                    "PlatformEventSubscriberConfig": [],
                    "NamedCredential": [],
                    "ExternalCredential": [],
                    "RemoteSiteSetting": [],
                    "CspTrustedSite": [],
                    "StaticResource": [],
                },
                "dates": {
                    "ApexClass": {"ExistingOtherClass": "2026-11-01T00:00:00.000+0000"},
                    "LightningComponentBundle": {"existingOtherLwc": "2026-11-01T00:00:00.000+0000"},
                },
                "assignments": [],
                "tab_visibility": [],
                "apex_bodies": {},
                "tap_output": "1..0\n",
            }),
            encoding="utf-8",
        )

        fake_sf = self.bin_dir / "sf"
        fake_sf.write_text(f"#!{sys.executable}\n" + FAKE_SF_CODE, encoding="utf-8")
        fake_sf.chmod(0o755)

        self.env = {
            **os.environ,
            "PATH": f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "E2E_PLATFORM_DIR": str(self.pdir),
            "CLOUDYBOT_FAKE_SF_STATE": str(self.state_file),
            "CLOUDYBOT_FAKE_SF_CALLS": str(self.calls_log),
        }

    def write_dx_project(self, extra_files: dict[str, str] | None = None):
        (self.proj / "sfdx-project.json").write_text(
            json.dumps({"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": "68.0"}),
            encoding="utf-8",
        )
        (self.proj / ".gitignore").write_text(".sf/\n.sfdx/\n", encoding="utf-8")
        base = self.proj / "force-app" / "main" / "default"
        files = {
            "classes/CloudyBotDriver.cls": "public with sharing class CloudyBotDriver {}\n",
            "classes/CloudyBotDriver.cls-meta.xml": "<ApexClass/>",
            "classes/CloudyBotDriverTest.cls": "@isTest\nprivate class CloudyBotDriverTest { @isTest static void t1() {} }\n",
            "classes/CloudyBotDriverTest.cls-meta.xml": "<ApexClass/>",
            "objects/CloudyBot_Task__c/CloudyBot_Task__c.object-meta.xml": "<CustomObject/>",
            "objects/CloudyBot_Task__c/fields/Status__c.field-meta.xml": "<CustomField/>",
            "lwc/cloudyBotConsole/cloudyBotConsole.js": "export default class CloudyBotConsole {}",
            "lwc/cloudyBotConsole/cloudyBotConsole.js-meta.xml": "<LightningComponentBundle><isExposed>true</isExposed></LightningComponentBundle>",
            "tabs/CloudyBot_Console.tab-meta.xml": "<CustomTab><lwcComponent>cloudyBotConsole</lwcComponent></CustomTab>",
            "applications/CloudyBot.app-meta.xml": "<CustomApplication><tabs>CloudyBot_Console</tabs></CustomApplication>",
            "permissionsets/CloudyBot_User.permissionset-meta.xml": "<PermissionSet/>",
        }
        if extra_files:
            files.update(extra_files)
        for rel, body in files.items():
            target = base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

    def run_guard(self, *argv: str, deny_all: bool = False, name: str | None = None):
        cmd = [sys.executable, str(CHECKS / "cloudybot_sf_guard.py"), "--org", "de", "--prefix", "CloudyBot"]
        if deny_all:
            cmd.append("--deny-all")
        if name:
            cmd += ["--name", name]
        cmd += ["--", *argv]
        return subprocess.run(cmd, cwd=self.proj, env=self.env, capture_output=True, text=True)

    def run_checker(self, *args: str, env_override: dict[str, str] | None = None):
        env = {**self.env, **(env_override or {})}
        cmd = [sys.executable, str(CHECKS / "cloudybot_salesforce.py"), *args]
        return subprocess.run(cmd, cwd=self.proj, env=env, capture_output=True, text=True)

    def test_guard_allows_scoped_commands_denies_unsafe_ones_and_scrubs_tokens(self):
        self.write_dx_project()
        state = json.loads(self.state_file.read_text())
        state["leak_token"] = "00Daj000018BzO3EAK!AQEAQSecretSessionToken123456"
        self.state_file.write_text(json.dumps(state))

        self.assertEqual(self.run_guard("--version").returncode, 0)
        self.assertEqual(self.run_guard("org", "list").returncode, 0)
        self.assertEqual(self.run_guard("data", "query", "--target-org", "de", "--query", "SELECT Id FROM Account").returncode, 0)
        self.assertEqual(self.run_guard("org", "assign", "permset", "--target-org", "de", "--name", "CloudyBot_User").returncode, 0)

        dep = self.run_guard("project", "deploy", "start", "--target-org", "de", "--wait", "10")
        self.assertEqual(dep.returncode, 0, dep.stderr)
        self.assertNotIn("AQEAQSecretSessionToken", dep.stderr)
        self.assertIn("[redacted]", dep.stderr)

        # Denials
        for bad in (
            ("org", "display", "--target-org", "de"),
            ("org", "open", "--target-org", "de"),
            ("data", "query", "--query", "SELECT Id FROM Account"),
            ("data", "query", "--target-org", "other", "--query", "SELECT Id FROM Account"),
            ("org", "assign", "permset", "--target-org", "de", "--name", "OtherPerm"),
            ("project", "deploy", "start", "--target-org", "de", "--post-destructive-changes", "d.xml"),
            ("project", "deploy", "start", "--target-org", "de", "--wait", "2"),
        ):
            res = self.run_guard(*bad)
            self.assertEqual(res.returncode, 2, bad)
            self.assertIn("denied", res.stderr)

        self.assertEqual(self.run_guard("org", "list", deny_all=True, name="sfdx").returncode, 2)

        # Prefixed Public Groups, Permission Set Groups, Custom Permissions, and Sharing Rules deploy cleanly
        self.write_dx_project({
            "groups/CloudyBot_RevOps.group-meta.xml": "<Group/>",
            "permissionsetgroups/CloudyBot_Operators.permissionsetgroup-meta.xml": "<PermissionSetGroup/>",
            "customPermissions/CloudyBot_Admin.customPermission-meta.xml": "<CustomPermission/>",
            "sharingRules/CloudyBot_Bot__c.sharingRules-meta.xml": "<SharingRules/>",
        })
        self.assertEqual(self.run_guard("project", "deploy", "start", "--target-org", "de", "--wait", "10").returncode, 0)

        # Unprefixed files in force-app (including groups / permissionsetgroups) are refused by deploy scope
        for extra in (
            {"classes/RogueHelper.cls": "public class RogueHelper {}"},
            {"groups/RogueGroup.group-meta.xml": "<Group/>"},
            {"permissionsetgroups/RogueGroup.permissionsetgroup-meta.xml": "<PermissionSetGroup/>"},
        ):
            self.write_dx_project(extra)
            bad_dep = self.run_guard("project", "deploy", "start", "--target-org", "de", "--wait", "10")
            self.assertEqual(bad_dep.returncode, 2, extra)
            self.assertIn("Rogue", bad_dep.stderr)

        # Guard log matches run.guard_coverage expectations
        events = self.root / "events.jsonl"
        events.write_text(json.dumps({"type": "tool_call", "toolName": "bash", "rawInput": {"command": "sf org list"}}) + "\n")
        fake_out = self.root / "out"
        (fake_out / "platform" / "bin").mkdir(parents=True)
        shutil.copyfile(self.pdir / "sf-calls.jsonl", fake_out / "platform" / "sf-calls.jsonl")
        shutil.copyfile(events, fake_out / "events.jsonl")
        cov = run.guard_coverage(fake_out)
        self.assertGreater(cov["guard_calls"], 0)
        self.assertFalse(cov["bypassed"])

    def test_project_preflight_snapshot_cleanup_deployed_and_tests_lifecycle(self):
        self.write_dx_project()
        # 1. project check
        ok_proj = self.run_checker("project", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(ok_proj.returncode, 0, ok_proj.stdout)

        (self.proj / ".gitignore").write_text(".sf/\n", encoding="utf-8")
        bad_proj = self.run_checker("project", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(bad_proj.returncode, 1)
        self.assertIn(".sfdx/", bad_proj.stdout)

        # 2. preflight + snapshot on clean org
        pre = self.run_checker("preflight", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(pre.returncode, 0, pre.stdout)
        snap = self.run_checker("snapshot", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(snap.returncode, 0, snap.stdout)
        self.assertTrue((self.pdir / "before.json").is_file())

        # 3. Simulate deployment of CloudyBot artifacts + unrelated foreign item
        state = json.loads(self.state_file.read_text())
        state["metadata"]["ApexClass"].extend(["CloudyBotDriver", "CloudyBotDriverTest", "ForeignAppHelper"])
        state["metadata"]["LightningComponentBundle"].append("cloudyBotConsole")
        state["metadata"]["CustomTab"].append("CloudyBot_Console")
        state["metadata"]["CustomApplication"].append("CloudyBot")
        state["metadata"]["PermissionSet"].append("CloudyBot_User")
        state["metadata"]["PermissionSetGroup"].append("CloudyBot_Operators")
        state["metadata"]["CustomPermission"].append("CloudyBot_Admin")
        state["metadata"]["CustomObject"].append("CloudyBot_Task__c")
        state["metadata"]["Group"].extend(["CloudyBot_RevOps", "ForeignPublicGroup"])
        state["metadata"]["RemoteSiteSetting"].append("CloudyBot_GitHub")
        state["metadata"]["CspTrustedSite"].append("CloudyBot_Api")
        state["metadata"]["StaticResource"].append("CloudyBot_Assets")
        state["dates"]["ApexClass"]["CloudyBotDriver"] = "2026-11-25T00:00:00Z"
        state["assignments"].append({"Id": "0Pa000000000001AAA", "PermissionSetName": "CloudyBot_User"})
        state["assignments"].append({"Id": "0Pa000000000002AAA", "PermissionSetGroupName": "CloudyBot_Operators"})
        state["tab_visibility"].append({"Name": "CloudyBot_Console", "Visibility": "DefaultOn", "Parent": {"Name": "CloudyBot_User"}})
        state["apex_bodies"] = {
            "CloudyBotDriver": "public class CloudyBotDriver {}",
            "CloudyBotDriverTest": "@isTest private class CloudyBotDriverTest {}",
        }
        state["tap_output"] = "\n".join(["1..10"] + [f"ok {i} CloudyBotDriverTest.t{i}" for i in range(1, 11)]) + "\n"
        self.state_file.write_text(json.dumps(state))

        # Preflight fails in fresh mode, passes in update mode
        self.assertEqual(self.run_checker("preflight", "--org", "de", "--prefix", "CloudyBot").returncode, 1)
        self.assertEqual(
            self.run_checker("preflight", "--org", "de", "--prefix", "CloudyBot", env_override={"E2E_PLATFORM_EXISTING": "update"}).returncode,
            0,
        )

        # deployed & tests pass
        dep_chk = self.run_checker("deployed", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(dep_chk.returncode, 0, dep_chk.stdout)
        tst_chk = self.run_checker("tests", "--org", "de", "--prefix", "CloudyBot", "--min-tests", "10")
        self.assertEqual(tst_chk.returncode, 0, tst_chk.stdout)

        # Fails if too few tests or SKIP/not ok
        state["tap_output"] = "1..2\nok 1 A.t1\nok 2 A.t2 # SKIP\n"
        self.state_file.write_text(json.dumps(state))
        self.assertEqual(self.run_checker("tests", "--org", "de", "--prefix", "CloudyBot", "--min-tests", "2").returncode, 1)

        # 4. cleanup removes CloudyBot* + assignment, leaves ExistingOtherClass & ForeignAppHelper intact
        clean = self.run_checker("cleanup", "--org", "de", "--prefix", "CloudyBot")
        self.assertEqual(clean.returncode, 0, clean.stdout)
        after = json.loads(self.state_file.read_text())
        self.assertEqual(after["assignments"], [])
        self.assertIn("ExistingOtherClass", after["metadata"]["ApexClass"])
        self.assertIn("ForeignAppHelper", after["metadata"]["ApexClass"])
        self.assertIn("ForeignPublicGroup", after["metadata"]["Group"])
        self.assertNotIn("CloudyBotDriver", after["metadata"]["ApexClass"])
        self.assertNotIn("CloudyBot_Task__c", after["metadata"]["CustomObject"])
        self.assertNotIn("CloudyBot_RevOps", after["metadata"]["Group"])
        self.assertNotIn("CloudyBot_Operators", after["metadata"]["PermissionSetGroup"])
        self.assertNotIn("CloudyBot_Admin", after["metadata"]["CustomPermission"])
        self.assertNotIn("CloudyBot_GitHub", after["metadata"]["RemoteSiteSetting"])
        self.assertNotIn("CloudyBot_Api", after["metadata"]["CspTrustedSite"])
        self.assertNotIn("CloudyBot_Assets", after["metadata"]["StaticResource"])


if __name__ == "__main__":
    unittest.main()
