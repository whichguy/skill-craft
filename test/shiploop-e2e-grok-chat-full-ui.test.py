#!/usr/bin/env python3
"""Offline calibration for the independent Grok chat UI driver."""
from __future__ import annotations

import contextlib
import hashlib
from html.parser import HTMLParser
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "test" / "shiploop_e2e" / "checks" / "grok_chat_full_ui.py"
BROWSER = ROOT / "test" / "shiploop_e2e" / "checks" / "grok_chat_full_ui_browser.cjs"
FIXTURES = ROOT / "test" / "fixtures" / "grok-chat-full-ui" / "dom"
spec = importlib.util.spec_from_file_location("grok_chat_full_ui", DRIVER)
assert spec is not None and spec.loader is not None
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


SOURCE_HEAD = "a" * 40
METADATA_SHA256 = "b" * 64
EXPECTED_HOST = "orgfarm-test.develop.lightning.force.com"


def positive_observation(*, duplicate_create: bool = True) -> dict:
    calls = []

    def add(method: str, *, status: str | None = None, operation: str | None = None,
            action_id: str | None = None,
            correlated: bool = False) -> None:
        request_id = f"req-{len(calls) + 1};a"
        call = {
            "method": method,
            "request_id": request_id,
            "response_id": request_id,
            "response_state": "SUCCESS",
            "params_valid": True,
            "http_ok": True,
            "json_string_decoded_once": True,
            "ui_correlated": correlated,
        }
        if status is not None:
            call["result_status"] = status
        if operation is not None:
            call["result_operation"] = operation
        if action_id is not None:
            call["action_id"] = action_id
        calls.append(call)

    for method in ("getSetup", "saveSetup", "testConnection", "getSetup", "newConversation",
                   "seedItems", "getConversation"):
        add(method)
    for _ in range(5):
        add("sendMessage", correlated=True)
    add("confirmAction", status="applied", operation="create", action_id="create-a", correlated=True)
    if duplicate_create:
        add("confirmAction", status="rejected", operation="create", action_id="create-a", correlated=True)
    add("confirmAction", status="applied", operation="update", action_id="update-a", correlated=True)
    add("confirmAction", status="stale", operation="update", action_id="stale-a", correlated=True)
    add("cancelAction", status="cancelled", action_id="cancel-a", correlated=True)

    return {
        "schema": "shiploop-grok-chat-full-ui-observation/1",
        "mode": "run",
        "phase": "builder",
        "status": "passed",
        "source_head": SOURCE_HEAD,
        "candidate_metadata_sha256": METADATA_SHA256,
        "route_host": EXPECTED_HOST,
        "route_path": "/lightning/n/SLGrokChat_Chat",
        "browser_version": "Chrome 157.0.0.0",
        "ui_attempted_first": True,
        "auth_required": True,
        "auth_used": True,
        "controller_calls": calls,
        "setup_missing_without_chat_attempt": True,
        "setup_business_unchanged": True,
        "config_readback_match": True,
        "connection_ok": True,
        "recheck_ready": True,
        "read_tool_proof": {
            "find_items": True,
            "read_item": True,
            "result_matches_nonce": True,
            "assistant_used_result": True,
            "conversation_persisted": True,
            "prompt_excluded_nonce": True,
            "unsafe_markup_is_text": True,
        },
        "create_proposal_exact": True,
        "create_preconfirm_absent": True,
        "create_one_write": True,
        "update_proposal_exact": True,
        "update_preconfirm_unchanged": True,
        "update_one_write": True,
        "cancel_proposal_exact": True,
        "cancelled_absent": True,
        "stale_proposal_exact": True,
        "stale_rejected": True,
        "stale_external_value_preserved": True,
        "duplicate_safe": True,
        "reload_history_persisted": True,
        "new_conversation": True,
        "desktop_layout_ok": True,
        "narrow_layout_ok": True,
        "keyboard_ok": True,
        "safe_text_ok": True,
        "business_write_count": 2,
        "extra_write_count": 0,
        "action_ids": {"create": "create-a", "update": "update-a",
                       "cancel": "cancel-a", "stale": "stale-a"},
        "duplicate_attempted": True,
        "duplicate_delivery_count": 2 if duplicate_create else 1,
        "screenshots": 5,
    }


class GrokChatFullUiValidatorTests(unittest.TestCase):
    def validate(self, value: dict) -> list[str]:
        return ui.validate_observation(
            value,
            mode="run",
            phase="builder",
            expected_host=EXPECTED_HOST,
            source_head=SOURCE_HEAD,
            metadata_sha256=METADATA_SHA256,
        )

    def test_accepts_server_deduplicated_double_click_and_disabled_duplicate(self):
        self.assertEqual([], self.validate(positive_observation(duplicate_create=True)))
        self.assertEqual([], self.validate(positive_observation(duplicate_create=False)))

    def test_rejects_missing_or_wrong_host_and_stale_source(self):
        for host in (None, "wrong.lightning.force.com"):
            value = positive_observation()
            value["route_host"] = host
            self.assertIn("host-mismatch", self.validate(value))
        value = positive_observation()
        value["candidate_metadata_sha256"] = "c" * 64
        self.assertIn("source-stale", self.validate(value))

    def test_rejects_prose_without_real_read_tools(self):
        value = positive_observation()
        value["read_tool_proof"]["read_item"] = False
        self.assertIn("fake-prose-without-tool", self.validate(value))

    def test_rejects_missing_write_and_extra_write(self):
        value = positive_observation()
        value["create_one_write"] = False
        self.assertIn("write-missing", self.validate(value))
        value = positive_observation()
        value["extra_write_count"] = 1
        self.assertIn("extra-write", self.validate(value))
        value = positive_observation()
        value["setup_business_unchanged"] = False
        self.assertIn("extra-write", self.validate(value))

    def test_rejects_mismatched_request_response_action_ids(self):
        value = positive_observation()
        value["controller_calls"][0]["response_id"] = "other;a"
        self.assertIn("controller-response-id-mismatch", self.validate(value))

    def test_observe_is_exploration_only_without_deployment_binding(self):
        value = {
            "schema": "shiploop-grok-chat-full-ui-observation/1", "mode": "observe",
            "phase": "builder", "status": "observed", "evidence_scope": "ui-exploration",
            "acceptance_bound": False, "source_deployment_bound": False,
            "source_head": SOURCE_HEAD, "candidate_metadata_sha256": METADATA_SHA256,
            "deployment": None, "route_host": EXPECTED_HOST,
            "route_path": "/lightning/n/SLGrokChat_Chat", "browser_version": "Chrome 157",
            "ui_attempted_first": True, "auth_required": False, "auth_used": False,
            "observed_setup_status": "missing", "screenshots": 1,
            "controller_calls": [{"method": "getSetup", "request_id": "req-1;a",
                "response_id": "req-1;a", "response_state": "SUCCESS", "params_valid": True,
                "http_ok": True, "json_string_decoded_once": True}],
        }
        self.assertEqual([], ui.validate_observation(value, mode="observe", phase="builder",
            expected_host=EXPECTED_HOST, source_head=SOURCE_HEAD, metadata_sha256=METADATA_SHA256))
        value["acceptance_bound"] = True
        self.assertIn("browser-result-invalid", ui.validate_observation(value, mode="observe",
            phase="builder", expected_host=EXPECTED_HOST, source_head=SOURCE_HEAD,
            metadata_sha256=METADATA_SHA256))

    def test_cli_scope_is_fixed_and_modes_are_bounded(self):
        args, errors = ui.parse_options(["--mode", "run"])
        self.assertEqual([], errors)
        self.assertEqual("run", args.mode)
        for argv in (
            ["--mode", "run", "--org", "other"],
            ["--mode", "run", "--url", "https://example.invalid"],
            ["--mode", "run", "--sql", "SELECT Id FROM Account"],
            ["--mode", "run", "--phase", "final"],
            ["--mode", "run", "--mode", "observe"],
        ):
            with self.subTest(argv=argv):
                _, rejected = ui.parse_options(argv)
                self.assertTrue(rejected)

    def test_product_at_stop_phase_refuses_before_platform_or_org_access(self):
        with mock.patch.dict(os.environ, {"E2E_CHECK_PHASE": "product_at_stop"}):
            with mock.patch.object(ui, "load_shared_ui", side_effect=AssertionError("must not resolve Salesforce")):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(1, ui.run_check("run"))

    def test_candidate_hash_includes_ignored_deployable_files_and_rejects_symlinks(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git is required")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run([git, "init", "-q", str(root)], check=True)
            subprocess.run([git, "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run([git, "-C", str(root), "config", "user.name", "Offline Test"], check=True)
            force = root / "force-app" / "main" / "default" / "classes"
            force.mkdir(parents=True)
            (root / ".gitignore").write_text("force-app/main/default/classes/ignored.js\n")
            (force / "SLGrokChatController.cls").write_text("public class SLGrokChatController {}\n")
            subprocess.run([git, "-C", str(root), "add", ".gitignore", "force-app/main/default/classes/SLGrokChatController.cls"], check=True)
            subprocess.run([git, "-C", str(root), "commit", "-qm", "fixture"], check=True)
            _, before = ui._candidate_identity(root)
            (force / "ignored.js").write_text("// deployable and ignored\n")
            _, after = ui._candidate_identity(root)
            self.assertNotEqual(before, after)
            (force / "link.js").symlink_to(force / "ignored.js")
            with self.assertRaises(ui.CheckFailure):
                ui._candidate_identity(root)

    def test_fresh_snapshot_is_required_and_matches_live_org_identity(self):
        live_identity = {"Id": ui.EXPECTED_ORG_ID, "OrganizationType": "Developer Edition", "IsSandbox": False}
        with tempfile.TemporaryDirectory() as temp:
            platform = Path(temp)
            snapshot = {"org": "de", "prefix": "SLGrokChat", "existing": None,
                        "gym": {"schema": "shiploop-gym-snapshot/1", "object_api_names": [],
                                "fields": [], "identity": live_identity}}
            (platform / "before.json").write_text(json.dumps(snapshot))
            with mock.patch.object(ui, "_query", return_value=[live_identity]):
                self.assertRegex(ui._validate_before_snapshot(platform, None), r"^[a-f0-9]{64}$")
            snapshot["org"] = "other"
            (platform / "before.json").write_text(json.dumps(snapshot))
            with mock.patch.object(ui, "_query", side_effect=AssertionError("must reject before org query")):
                with self.assertRaises(ui.CheckFailure):
                    ui._validate_before_snapshot(platform, None)
            snapshot["org"] = "de"
            snapshot["existing"] = "update"
            (platform / "before.json").write_text(json.dumps(snapshot))
            with mock.patch.object(ui, "_query", side_effect=AssertionError("must reject before org query")):
                with self.assertRaises(ui.CheckFailure):
                    ui._validate_before_snapshot(platform, None)

    def test_setup_write_is_rejected_before_the_explicit_seed_step(self):
        for setup_wrote in (False, True):
            with self.subTest(setup_wrote=setup_wrote), tempfile.TemporaryDirectory() as folder:
                platform = Path(folder).resolve()
                shared = mock.Mock()
                shared.org_identity.return_value = {"org_id": ui.EXPECTED_ORG_ID,
                                                    "lightning_host": EXPECTED_HOST}
                steps = []

                def browser_step(worker, request, **kwargs):
                    steps.append(request["step"])
                    if request["step"] == "attempt":
                        return {"ui_attempted_first": True, "auth_required": False}
                    return {}  # An empty explicit seed response deliberately stops the positive control.

                after = [{"Id": "a01000000000001AAA", "Name": "Unexpected setup item"}] if setup_wrote else []
                patches = {
                    "load_shared_ui": {"return_value": shared},
                    "_current_user": {"return_value": ("005000000000001AAA", True)},
                    "_candidate_identity": {"return_value": (SOURCE_HEAD, METADATA_SHA256)},
                    "_latest_successful_deploy": {"return_value": {"exit": 0, "interrupted": False}},
                    "_source_is_fresh": {"return_value": True},
                    "_validate_before_snapshot": {"return_value": "baseline"},
                    "_items": {"side_effect": [[], after]},
                    "_start_browser": {"return_value": mock.Mock()},
                    "_run_browser": {"side_effect": browser_step},
                    "_reset_config": {"return_value": 0},
                    "_verify_config": {"return_value": True},
                }
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(platform),
                                                                    "E2E_CHECK_PHASE": "builder"}))
                    for name, behavior in patches.items():
                        stack.enter_context(mock.patch.object(ui, name, **behavior))
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                    self.assertEqual(1, ui.run_check("run"))
                receipt = json.loads(next(platform.rglob("observation.json")).read_text())
                self.assertEqual("extra-write" if setup_wrote else "seed-invalid", receipt["failure"]["reason_code"])
                self.assertEqual(["attempt", "setup"] if setup_wrote else ["attempt", "setup", "seed"], steps)

    def test_config_reset_refuses_rows_not_created_by_this_test_user(self):
        class Shared:
            deletes = 0

            def sf_json(self, argv):
                self.deletes += 1
                return {}

        shared = Shared()
        with mock.patch.object(ui, "_config_rows", return_value=[
            {"Id": "a" * 18, "CreatedById": "b" * 18,
             "NamedCredential__c": ui.NAMED_CREDENTIAL, "Model__c": ui.MODEL},
        ]):
            with self.assertRaises(ui.CheckFailure):
                ui._reset_config(shared, "c" * 18)
        self.assertEqual(0, shared.deletes)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the Aura parser calibration")
    def test_aura_parser_binds_exact_request_response_and_decodes_once(self):
        program = r'''const h=require(process.argv[1]);
const request=JSON.stringify({actions:[{id:'req-1;a',descriptor:'apex://SLGrokChatController/ACTION$getSetup',params:{}}]});
const payload={status:'missing',canConfigure:true,namedCredential:null,model:null,code:null};
const response=value=>JSON.stringify({actions:[{id:'req-1;a',state:'SUCCESS',returnValue:value}]});
const actions=h.parseAuraRequest(request,'SLGrokChatController');
const pair=h.pairAuraActions(actions,response(JSON.stringify(payload)))[0];
let mismatch='';
try { h.pairAuraActions(actions,JSON.stringify({actions:[{id:'wrong;a',state:'SUCCESS',returnValue:JSON.stringify(payload)}]})); }
catch(e) { mismatch=e.reason; }
let twice='';
try { h.pairAuraActions(actions,response(JSON.stringify(JSON.stringify(payload)))); }
catch(e) { twice=e.reason; }
process.stdout.write(JSON.stringify({request_id:pair.request_id,response_id:pair.response_id,
  decoded_once:pair.json_string_decoded_once,status:pair.result.status,mismatch,twice}));'''
        observed = subprocess.run(
            [shutil.which("node"), "-e", program, str(BROWSER)],
            capture_output=True, text=True, check=True, timeout=90,
        )
        result = json.loads(observed.stdout)
        self.assertEqual(result["request_id"], result["response_id"])
        self.assertTrue(result["decoded_once"])
        self.assertEqual("missing", result["status"])
        self.assertEqual("controller-response-id-mismatch", result["mismatch"])
        self.assertEqual("controller-response-invalid", result["twice"])

    def test_dom_fixture_declares_accessible_controls_and_missing_send_is_detected(self):
        class ContractParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.labels = {}
                self.ids = set()
                self.buttons = []
                self.regions = set()
                self.active_label = None
                self.active_button = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get("id"):
                    self.ids.add(attrs["id"])
                if tag == "label":
                    self.active_label = (attrs.get("for"), [])
                if tag == "button":
                    self.active_button = []
                if attrs.get("role") == "region" and attrs.get("aria-label"):
                    self.regions.add(attrs["aria-label"])

            def handle_data(self, data):
                if self.active_label is not None:
                    self.active_label[1].append(data)
                if self.active_button is not None:
                    self.active_button.append(data)

            def handle_endtag(self, tag):
                if tag == "label" and self.active_label is not None:
                    key, words = self.active_label
                    self.labels[key] = "".join(words).strip()
                    self.active_label = None
                if tag == "button" and self.active_button is not None:
                    self.buttons.append("".join(self.active_button).strip())
                    self.active_button = None

        def observed(path):
            parser = ContractParser()
            parser.feed(path.read_text())
            controls = {label: key in parser.ids for key, label in parser.labels.items()}
            return controls, set(parser.buttons), parser.regions

        complete, complete_buttons, complete_regions = observed(FIXTURES / "complete.html")
        missing, missing_buttons, _ = observed(FIXTURES / "missing-send.html")
        self.assertTrue(all(complete.get(label) for label in ("Named credential", "Model", "Message")))
        self.assertTrue({"Save setup", "Test connection", "Recheck setup", "Setup", "New conversation",
                         "Send", "Confirm", "Cancel", "Seed demo items"}.issubset(complete_buttons))
        self.assertTrue({"Setup status", "Conversation", "Chat status", "Proposed change",
                         "Action status"}.issubset(complete_regions))
        self.assertNotIn("Send", missing_buttons)


class GrokChatDeploymentBindingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "project"
        self.platform = self.root.parent / "platform"
        self.apex = self.root / "force-app/main/default/classes/SLGrokChatController.cls"
        self.lwc = self.root / "force-app/main/default/lwc/slGrokChatApp/slGrokChatApp.js"
        self.apex.parent.mkdir(parents=True)
        self.lwc.parent.mkdir(parents=True)
        self.apex.write_bytes(b"apex\n")
        self.lwc.write_bytes(b"lwc\n")
        (self.root / "sfdx-project.json").write_text('{"packageDirectories":[{"path":"force-app"}]}')

    def deploy(self, *flags, bind=True, command=("project", "deploy", "start"),
               run_real=None, expected_code=0):
        guard = ui.sf_guard
        env = {"E2E_PLATFORM_DIR": str(self.platform)}
        if bind:
            env["E2E_BIND_DEPLOY_SOURCE"] = "1"
        argv = ["--org", ui.EXPECTED_ORG, "--prefix", ui.PREFIX, "--", *command,
                "--target-org", ui.EXPECTED_ORG, *flags]
        with mock.patch.object(guard.os, "environ", env), \
             mock.patch.object(guard.os, "getcwd", return_value=str(self.root)), \
             mock.patch.object(guard.signal, "signal"), \
             mock.patch.object(guard, "find_real_sf", return_value="/unused/sf"), \
             mock.patch.object(guard, "run_real", side_effect=run_real, return_value=("", "", 0)) as real:
            self.assertEqual(expected_code, guard.main(argv))
            real.assert_called_once()
        return ui._latest_successful_deploy(self.platform)

    def candidate_digest(self, head=SOURCE_HEAD):
        with mock.patch.object(ui.subprocess, "run", return_value=mock.Mock(stdout=head + "\n")):
            return ui._candidate_identity(self.root)[1]

    def test_missing_binding_does_not_use_success_or_timestamps(self):
        deploy = self.deploy("--source-dir", "force-app", bind=False)
        self.assertEqual(0, deploy["exit"])
        self.assertNotIn("source_binding", deploy)
        self.assertFalse(ui._source_is_fresh(self.root, deploy, self.candidate_digest()))

    def test_successful_full_package_matches_exact_source_after_head_change(self):
        before = self.candidate_digest()
        deploy = self.deploy("-d", str(self.root / "force-app"), "--wait", "10", "--json")
        expected = hashlib.sha256(
            b"force-app/main/default/classes/SLGrokChatController.cls\0apex\n\0"
            b"force-app/main/default/lwc/slGrokChatApp/slGrokChatApp.js\0lwc\n\0"
        ).hexdigest()
        self.assertEqual(expected, before)
        self.assertIs(deploy["interrupted"], False)
        self.assertEqual({"root": str(self.root), "before_sha256": expected, "after_sha256": expected,
                          "full_package": True, "unchanged": True}, deploy["source_binding"])
        self.assertTrue(ui._source_is_fresh(self.root, deploy, self.candidate_digest("c" * 40)))

    def test_newer_partial_deploy_supersedes_full_binding(self):
        full = self.deploy("--source-dir", "force-app")
        partial = self.deploy("--source-dir", str(self.apex), command=("project:deploy:start",))
        self.assertIn("source_binding", full)
        self.assertNotEqual(full["call_id"], partial["call_id"])
        self.assertNotIn("source_binding", partial)
        self.assertFalse(ui._source_is_fresh(self.root, partial, self.candidate_digest()))

    def test_binding_from_another_root_does_not_count(self):
        deploy = self.deploy("--source-dir", "force-app")
        other_root = self.root.with_name("other-project")
        shutil.copytree(self.root, other_root)
        self.assertFalse(ui._source_is_fresh(other_root, deploy, self.candidate_digest()))

    def test_changed_lwc_fails_binding_even_with_old_mtime(self):
        deploy = self.deploy("--source-dir", "force-app")
        self.lwc.write_bytes(b"edited LWC\n")
        os.utime(self.lwc, (1, 1))
        self.assertFalse(ui._source_is_fresh(self.root, deploy, self.candidate_digest()))

    def test_source_mutation_during_cli_call_marks_binding_changed(self):
        before = self.candidate_digest()

        def mutate(*args):
            self.lwc.write_bytes(b"changed during deploy\n")
            return "", "", 0

        deploy = self.deploy("--source-dir", "force-app", run_real=mutate)
        after = self.candidate_digest()
        self.assertEqual(before, deploy["source_binding"]["before_sha256"])
        self.assertEqual(after, deploy["source_binding"]["after_sha256"])
        self.assertNotEqual(before, after)
        self.assertIs(deploy["source_binding"]["unchanged"], False)
        self.assertFalse(ui._source_is_fresh(self.root, deploy, after))

    def test_alternate_selectors_and_dry_run_never_attest(self):
        manifest = self.root / "package.xml"
        manifest.write_text("<Package><types><members>SLGrokChatController</members>"
                            "<name>ApexClass</name></types></Package>")
        for extra in (("--metadata", "ApexClass:SLGrokChatController"),
                      ("--manifest", str(manifest)),
                      ("-d", str(self.apex)), (str(self.apex),), ("--dry-run",), ("-c",)):
            with self.subTest(extra=extra):
                deploy = self.deploy("--source-dir", "force-app", *extra)
                self.assertNotIn("source_binding", deploy)

    def test_explicit_source_outside_a_project_never_attests(self):
        (self.root / "sfdx-project.json").unlink()
        deploy = self.deploy("--source-dir", "force-app")
        self.assertNotIn("source_binding", deploy)

    def test_symlinked_package_never_attests(self):
        package = self.root / "force-app"
        original = package.rename(self.root / "real-app")
        package.symlink_to(original, target_is_directory=True)
        deploy = self.deploy("--source-dir", "force-app")
        self.assertNotIn("source_binding", deploy)

    def test_source_exclusions_before_or_during_deploy_never_attest(self):
        ignore = self.root / ".forceignore"
        ignore.write_text("# comments alone do not exclude source\n")
        self.assertIn("source_binding", self.deploy("--source-dir", "force-app"))
        ignore.write_text("force-app/main/default/lwc/**\n")
        self.assertNotIn("source_binding", self.deploy("--source-dir", "force-app"))
        ignore.unlink()

        def exclude_during_deploy(*args):
            ignore.write_text("force-app/**\n")
            return "", "", 0

        self.assertNotIn("source_binding", self.deploy("--source-dir", "force-app", run_real=exclude_during_deploy))

    def test_unsuccessful_or_interrupted_call_never_attests(self):
        failed = self.deploy("--source-dir", "force-app", expected_code=1, run_real=lambda *args: ("", "", 1))
        self.assertNotIn("source_binding", failed)

        def interrupt(real, argv, state, env):
            state["interrupted"] = True
            return "", "", 143

        interrupted = self.deploy("--source-dir", "force-app", expected_code=143, run_real=interrupt)
        self.assertIs(interrupted["interrupted"], True)
        self.assertNotIn("source_binding", interrupted)


if __name__ == "__main__":
    unittest.main()
