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
CONVERSATION_ID = "a01000000000001AAA"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def positive_observation(*, duplicate_create: bool = True, split_steps: tuple = ()) -> dict:
    calls = []
    turns = []
    action_ids = {"create": "create-a", "update": "update-a", "cancel": "cancel-a", "stale": "stale-a"}

    def add(method: str, *, status: str | None = None, operation: str | None = None,
            action_id: str | None = None, correlated: bool = False, **fields) -> int:
        sequence = len(calls) + 1
        request_id = f"req-{sequence};a"
        call = {
            "method": method,
            "request_sequence": sequence,
            "request_id": request_id,
            "response_id": request_id,
            "response_state": "SUCCESS",
            "params_valid": True,
            "http_ok": True,
            "json_string_decoded_once": True,
            "ui_correlated": correlated,
            **fields,
        }
        if method in ui.TURN_METHODS | {"testConnection"}:
            call.update(request_started_at=sequence * 10, response_completed_at=sequence * 10 + 5,
                        server_request_id=f"server-{sequence}")
        if status is not None:
            call["result_status"] = status
        if operation is not None:
            call["result_operation"] = operation
        if action_id is not None:
            call.update(action_id=action_id, request_action_id=action_id, card_action_id=action_id)
        calls.append(call)
        return sequence

    for method in ("getSetup", "saveSetup"):
        add(method)
    add("testConnection", status="ok", correlated=True)
    for method in ("getSetup", "newConversation", "seedItems", "getConversation"):
        add(method)
    methods = ["testConnection"]
    conversation = {"request_conversation_id": CONVERSATION_ID, "result_conversation_id": CONVERSATION_ID}
    for index, step in enumerate(ui.TURN_STEPS):
        begin = None
        execution_fields = {"message_sha256": sha(step)}
        if step in split_steps:
            token = sha(f"pending-{index}")
            begin = add("beginMessage", status="working", correlated=True, **conversation,
                        message_sha256=sha(step), client_request_id_sha256=sha(f"client-{index}"),
                        issued_turn_token_sha256=token)
            method = "executePendingMessage"
            execution_fields = {"submitted_turn_token_sha256": token}
        else:
            method = "sendMessage"
        if method not in methods:
            methods.append(method)
        execution = add(method, status="ready", correlated=True, **conversation, **execution_fields)
        action = step.removesuffix("-proposal")
        action_id = action_ids.get(action)
        turns.append({
            "step": step, "conversation_id": CONVERSATION_ID, "begin_request_sequence": begin,
            "execution_request_sequence": execution, "proposal_action_id": action_id,
            "before_message_count": 2 * index, "final_message_count": 2 * index + 2,
            "before_history_sha256": sha(f"history-{index}"), "final_history_sha256": sha(f"history-{index+1}"),
            "rendered_history_matched": True,
        })
        if action == "cancel":
            add("cancelAction", status="cancelled", action_id=action_id, correlated=True)
        elif action_id:
            add("confirmAction", status="stale" if action == "stale" else "applied",
                operation="create" if action == "create" else "update", action_id=action_id, correlated=True)
            if action == "create" and duplicate_create:
                add("confirmAction", status="rejected", operation="create", action_id=action_id, correlated=True)

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
        "conversation_id": CONVERSATION_ID,
        "chat_turns": turns,
        "live_callout_methods": methods,
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
        "action_ids": action_ids,
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

    def test_name_fallback_uses_normalized_database_names_and_selected_id(self):
        selected_id = "a02000000000001AAA"
        other_id = "a02000000000002AAA"
        name = "Shared item name"
        selected = {"Id": selected_id, "Name": "Shared\u200b  item name"}
        self.assertTrue(ui._unique_visible_item_name([selected], selected_id, name))
        for duplicate in ("Shared  item name", "Shared\titem\u00a0name", "\ufeffShared i\u00adtem name\u3000"):
            with self.subTest(duplicate=duplicate):
                rows = [selected, {"Id": other_id, "Name": duplicate}]
                self.assertFalse(ui._unique_visible_item_name(rows, selected_id, name))
        self.assertFalse(ui._unique_visible_item_name([{"Id": other_id, "Name": name}], selected_id, name))
        self.assertTrue(ui._unique_visible_item_name(
            [selected, {"Id": other_id, "Name": "Shared\u0085item name"}], selected_id, name))
        self.assertFalse(ui._unique_visible_item_name(
            [selected] + [{"Id": f"other-{i}", "Name": f"Item {i}"} for i in range(500)], selected_id, name))

    def test_accepts_five_split_turns_and_distinct_direct_and_split_interactions(self):
        for steps in (ui.TURN_STEPS, ("create-proposal", "stale-proposal")):
            with self.subTest(steps=steps):
                value = positive_observation(split_steps=steps)
                self.assertEqual([], self.validate(value))
                self.assertIn("executePendingMessage", value["live_callout_methods"])
                self.assertNotIn("beginMessage", value["live_callout_methods"])
            with self.subTest(steps=steps, after_confirmation_bookkeeping=True):
                value = positive_observation(split_steps=steps)
                first_after_update = ui.TURN_STEPS.index("cancel-proposal")
                for index, turn in enumerate(value["chat_turns"][first_after_update:], first_after_update):
                    turn["before_message_count"] += 1
                    turn["final_message_count"] += 1
                    turn["before_history_sha256"] = sha(f"reconciled-history-{index}")
                    turn["final_history_sha256"] = sha(f"reconciled-history-{index + 1}")
                self.assertEqual([], self.validate(value))

    def test_missing_malformed_or_reused_native_request_identity_is_incomplete(self):
        for value in (None, "", "TID:unexpected-prefix", "a" * 85, "bad\nvalue", "server-3"):
            with self.subTest(value=value):
                observation = positive_observation()
                call = next(row for row in observation["controller_calls"] if row["method"] == "sendMessage")
                call["server_request_id"] = value
                self.assertIn("controller-proof-missing", self.validate(observation))

    def test_rejects_an_extra_connection_even_when_uncorrelated(self):
        for correlated in (False, True):
            with self.subTest(correlated=correlated):
                value = positive_observation()
                calls = value["controller_calls"]
                connection = next(call for call in calls if call["method"] == "testConnection")
                calls.append({**connection, "request_sequence": len(calls) + 1,
                              "request_id": "extra;a", "response_id": "extra;a", "ui_correlated": correlated})
                self.assertIn("controller-proof-missing", self.validate(value))

    def test_split_projection_rejects_invalid_or_unmatched_proof(self):
        for variant in ("wrong-conversation", "wrong-token", "wrong-id", "reused-client", "early-execute",
                        "reused-token", "replayed-history", "no-render", "extra-execute", "wrong-card",
                        "wrong-live-method", "duplicate-sequence", "wrong-proposal"):
            with self.subTest(variant=variant):
                value = positive_observation(split_steps=ui.TURN_STEPS)
                calls = {call["request_sequence"]: call for call in value["controller_calls"]}
                turn, next_turn = value["chat_turns"][:2]
                begin = calls[turn["begin_request_sequence"]]
                execute = calls[turn["execution_request_sequence"]]
                if variant == "wrong-conversation":
                    execute["result_conversation_id"] = "a01000000000002AAA"
                elif variant == "wrong-token":
                    execute["submitted_turn_token_sha256"] = "c" * 64
                elif variant == "wrong-id":
                    execute["response_id"] = "wrong;a"
                elif variant == "early-execute":
                    execute["request_started_at"] = begin["request_started_at"]
                elif variant == "reused-client":
                    calls[next_turn["begin_request_sequence"]]["client_request_id_sha256"] = begin["client_request_id_sha256"]
                elif variant == "reused-token":
                    calls[next_turn["begin_request_sequence"]]["issued_turn_token_sha256"] = begin["issued_turn_token_sha256"]
                    calls[next_turn["execution_request_sequence"]]["submitted_turn_token_sha256"] = begin["issued_turn_token_sha256"]
                elif variant == "replayed-history":
                    next_turn["final_history_sha256"] = turn["final_history_sha256"]
                elif variant == "no-render":
                    turn["rendered_history_matched"] = False
                elif variant == "extra-execute":
                    value["controller_calls"].append({**execute, "request_sequence": max(calls) + 1})
                elif variant == "wrong-card":
                    next(call for call in calls.values() if call["method"] == "confirmAction")["card_action_id"] = "other"
                elif variant == "wrong-live-method":
                    value["live_callout_methods"] = ["testConnection", "sendMessage"]
                elif variant == "duplicate-sequence":
                    execute["request_sequence"] = begin["request_sequence"]
                elif variant == "wrong-proposal":
                    next_turn["proposal_action_id"] = "other"
                self.assertIn("controller-proof-missing", self.validate(value))

    def test_closed_projection_keeps_token_digests_and_drops_raw_capabilities(self):
        value = positive_observation(split_steps=ui.TURN_STEPS)
        begin = next(call for call in value["controller_calls"] if call["method"] == "beginMessage")
        begin.update(turnToken="synthetic-raw-capability", params={"turnToken": "synthetic-raw-capability"})
        turn = {**value["chat_turns"][0], "pending": {"token": "synthetic-raw-capability"}}
        calls = ui._safe_controller_projection([value])
        proof = ui._safe_chat_turn_projection({"chat_turn": turn})
        self.assertEqual(begin["issued_turn_token_sha256"], calls[begin["request_sequence"] - 1]["issued_turn_token_sha256"])
        self.assertEqual(turn["final_history_sha256"], proof["final_history_sha256"])
        self.assertNotIn("synthetic-raw-capability", json.dumps([calls, proof]))

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

    def test_app_host_binding_requires_the_declared_tab_and_exposed_bundle(self):
        ns = 'xmlns="http://soap.sforce.com/2006/04/metadata"'
        tab = f"<CustomTab {ns}><lwcComponent>slGrokChatApp</lwcComponent></CustomTab>"
        bundle = (f"<LightningComponentBundle {ns}><isExposed>true</isExposed>"
                  "<targets><target>lightning__Tab</target></targets></LightningComponentBundle>")
        cases = {
            "declared binding": (tab, bundle),
            "missing tab": (None, bundle),
            "different component": (tab.replace("slGrokChatApp", "slGrokChatOther"), bundle),
            "conflicting component": (tab.replace("</CustomTab>", "<lwcComponent>other</lwcComponent></CustomTab>"),
                                      bundle),
            "not exposed": (tab, bundle.replace("true", "false")),
            "wrong target": (tab, bundle.replace("lightning__Tab", "lightning__AppPage")),
            "malformed metadata": (tab, "<LightningComponentBundle>"),
        }
        for name, (tab_xml, bundle_xml) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                base = root / "force-app" / "main" / "default"
                for relative, content in (("tabs/SLGrokChat_Chat.tab-meta.xml", tab_xml),
                                          ("lwc/slGrokChatApp/slGrokChatApp.js-meta.xml", bundle_xml)):
                    if content is not None:
                        path = base / relative
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(content)
                if name == "declared binding":
                    ui._validate_app_tab(root)
                else:
                    with self.assertRaises(ui.CheckFailure) as error:
                        ui._validate_app_tab(root)
                    self.assertEqual(("source", "source-invalid"), (error.exception.stage, error.exception.reason))

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
                    "_validate_app_tab": {"return_value": None},
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

    def test_controller_projection_updates_pending_observations_without_hiding_conflicts(self):
        terminal = {**positive_observation()["controller_calls"][0], "request_sequence": 1}
        pending = {**terminal, "response_id": None, "response_state": "PENDING",
                   "http_ok": False, "json_string_decoded_once": False}
        results = [{"controller_calls": [pending]}, {"controller_calls": [terminal]}]
        observed = ui._safe_controller_projection(results)
        self.assertEqual(1, len(observed))
        self.assertTrue(ui._valid_call(observed[0]))
        self.assertEqual(1, observed[0]["request_sequence"])
        # Aura IDs may restart after reload; the observer's sequence keeps requests distinct.
        distinct = ui._safe_controller_projection([
            {"controller_calls": [terminal, {**terminal, "request_sequence": 2}]},
        ])
        self.assertEqual(2, len(distinct))
        # Each row below would pass individually. Their disagreement must remain
        # non-passing even if the first valid row is repeated later.
        other = {**terminal, "result_status": "ready"}
        self.assertTrue(ui._valid_call(other))
        conflict = ui._safe_controller_projection([
            {"controller_calls": [{**terminal, "result_status": "missing"}]},
            {"controller_calls": [other]},
            {"controller_calls": [other]},
        ])
        self.assertEqual(1, len(conflict))
        self.assertEqual("CONFLICT", conflict[0]["response_state"])
        self.assertFalse(ui._valid_call(conflict[0]))

    def test_pending_sequence_cannot_change_request_identity_when_completed(self):
        terminal = {**positive_observation()["controller_calls"][0], "request_sequence": 1}
        pending = {**terminal, "response_id": None, "response_state": "PENDING",
                   "http_ok": False, "json_string_decoded_once": False}
        for changed in (
            {**terminal, "request_id": "other;a", "response_id": "other;a"},
            {**terminal, "method": "saveSetup"},
        ):
            with self.subTest(changed=changed):
                self.assertTrue(ui._valid_call(changed))
                projected = ui._safe_controller_projection([
                    {"controller_calls": [pending]}, {"controller_calls": [changed]},
                ])
                self.assertEqual(1, len(projected))
                self.assertEqual("CONFLICT", projected[0]["response_state"])
                self.assertFalse(ui._valid_call(projected[0]))

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
    def test_server_identity_projection_excludes_headers_and_refuses_ambiguity(self):
        program = r'''const h=require(process.argv[1]);
const result={valid:h.serverRequestId({'x-sfdc-request-id':'1113000000b27bd678',
  'x-request-id':'1113000000b27bd678','set-cookie':'synthetic-secret'}),errors:[]};
for(const headers of [{},{'x-request-id':'only-generic-id'},
  {'x-sfdc-request-id':'known','x-request-id':'different'},
  {'x-sfdc-request-id':'TID:unexpected'}, {'x-sfdc-request-id':'x'.repeat(85)}]) {
  try { h.serverRequestId(headers); result.errors.push(null); }
  catch(e) { result.errors.push(e.reason); }
}
process.stdout.write(JSON.stringify(result));'''
        observed = subprocess.run([shutil.which("node"), "-e", program, str(BROWSER)],
                                  capture_output=True, text=True, check=True, timeout=30)
        self.assertNotIn("synthetic-secret", observed.stdout)
        self.assertEqual({"valid": "1113000000b27bd678", "errors": ["controller-proof-missing"] * 5},
                         json.loads(observed.stdout))

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

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the live-envelope regression")
    def test_lwc_transport_envelope_and_supporting_rpc_do_not_hide_required_proof(self):
        program = r'''const h=require(process.argv[1]);
const payload={status:'missing',canConfigure:true,namedCredential:null,model:null,code:null};
const wrapped={id:'req-1;a',descriptor:'aura://ApexActionController/ACTION$execute',
  params:{classname:'SLGrokChatController',method:'getSetup',params:{}}};
const supporting={id:'req-2;a',descriptor:'aura://ApexActionController/ACTION$execute',
  params:{classname:'SLGrokChatController',method:'listConversations',params:{beforeId:null}}};
const request=actions=>h.parseAuraRequest(JSON.stringify({actions}),'SLGrokChatController');
const response=value=>JSON.stringify({actions:[
  {id:'req-1;a',state:'SUCCESS',returnValue:value},
  {id:'req-2;a',state:'SUCCESS',returnValue:{returnValue:'[]',cacheable:false}},
]});
const attempts={};
for(const [name,actions,value] of [
  ['live_lwc',[wrapped,supporting],{returnValue:JSON.stringify(payload),cacheable:false}],
  ['ambiguous_id',[wrapped,{...supporting,id:wrapped.id}],{returnValue:JSON.stringify(payload),cacheable:false}],
  ['direct_masquerade',[{id:'req-1;a',descriptor:'apex://SLGrokChatController/ACTION$getSetup',params:{}}],
    {returnValue:JSON.stringify(payload),cacheable:false}],
  ['double_encoded',[wrapped],{returnValue:JSON.stringify(JSON.stringify(payload)),cacheable:false}],
  ['object_return',[wrapped],{returnValue:payload,cacheable:false}],
  ['invalid_envelope',[wrapped],{returnValue:JSON.stringify(payload),cacheable:'false'}],
]) {
  try { const parsed=request(actions); const paired=h.pairAuraActions(parsed,response(value));
    attempts[name]={status:paired[0].result.status,paired:paired.length,decoded:paired[0].json_string_decoded_once}; }
  catch(e) { attempts[name]={reason:e.reason}; }
}
try { attempts.supporting_only={count:request([supporting]).length}; }
catch(e) { attempts.supporting_only={reason:e.reason}; }
process.stdout.write(JSON.stringify(attempts));'''
        observed = subprocess.run([shutil.which("node"), "-e", program, str(BROWSER)],
                                  capture_output=True, text=True, check=True, timeout=90)
        result = json.loads(observed.stdout)
        self.assertEqual({"status": "missing", "paired": 1, "decoded": True}, result["live_lwc"])
        self.assertEqual({"count": 0}, result["supporting_only"])
        self.assertEqual({"reason": "controller-action-invalid"}, result["ambiguous_id"])
        for name in ("direct_masquerade", "double_encoded", "object_return", "invalid_envelope"):
            self.assertEqual({"reason": "controller-response-invalid"}, result[name], name)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the pre-setup request regression")
    def test_supporting_send_attempts_fail_setup_without_becoming_required_proof(self):
        program = r'''const h=require(process.argv[1]);
const host='fixture.lightning.force.com';
const request=(method,wrapped)=>({
  url:()=>`https://${host}/aura`,method:()=>'POST',
  postData:()=>JSON.stringify({actions:[wrapped
    ? {id:'req-1;a',descriptor:'aura://ApexActionController/ACTION$execute',
       params:{classname:'SLGrokChatController',method,params:{conversationId:'a01000000000001AAA'}}}
    : {id:'req-1;a',descriptor:`apex://SLGrokChatController/ACTION$${method}`,
       params:{conversationId:'a01000000000001AAA'}}]})
});
const result={};
for(const method of ['listConversations','beginMessage','executePendingMessage']) {
  result[method]=[];
  for(const wrapped of [true,false]) {
    const observer=new h.ApexObserver({},host);
    observer.onRequest(request(method,wrapped));
    let reason=null;
    try { h.assertNoChatBeforeSetup(observer,0); } catch(e) { reason=e.reason; }
    result[method].push({reason,required:observer.projection().length,failure:!!observer.failure});
  }
}
process.stdout.write(JSON.stringify(result));'''
        observed = subprocess.run([shutil.which("node"), "-e", program, str(BROWSER)],
                                  capture_output=True, text=True, check=True, timeout=90)
        result = json.loads(observed.stdout)
        self.assertEqual([{"reason": None, "required": 0, "failure": False}] * 2,
                         result["listConversations"])
        for name in ("beginMessage", "executePendingMessage"):
            self.assertEqual([{"reason": "chat-attempted-before-setup", "required": 0,
                               "failure": False}] * 2, result[name])

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the Send chain regression")
    def test_aura_observer_and_turn_matching_reject_false_correlation(self):
        program = r'''const h = require(process.argv[1]);
const host = 'fixture.lightning.force.com';
const conversationId = 'a01000000000001AAA';
const message = 'Read this exact nonce-backed item.';
const token = 'synthetic-capability';
const clientRequestId = 'ui-request-1';
const prior = [{role:'user',content:'Earlier question'},{role:'assistant',content:'Earlier answer'}];
const user = {role:'user',content:message};
const answer = {role:'assistant',content:'New answer'};
const history = (messages, extra = {}) => ({
  conversationId, messages, actions: [], toolCalls: [], status:'ready', ...extra
});
const before = h.normalizeResult('getConversation', JSON.stringify(history(prior)));
const results = {};
async function scenario(kind) {
  const observer = new h.ApexObserver({}, host, {trackSplit:true});
  let index = 0;
  async function rpc(method, params, payload, options = {}) {
    const id = `req-${++index};a`;
    const timing = {startTime: 1000 + index * 100, responseEnd: 20};
    if (options.early) timing.startTime -= 90;
    const request = {
      url: () => `https://${host}/aura`, method: () => 'POST', timing: () => timing,
      postData: () => JSON.stringify({actions:[{id, descriptor:'aura://ApexActionController/ACTION$execute',
        params:{classname:'SLGrokChatController',method,params}}]})
    };
    observer.onRequest(request);
    if (observer.failure) throw observer.failure;
    await observer.onResponse({
      url:request.url, request:() => request, status:() => 200, finished:async () => null,
      allHeaders:async () => ({'x-sfdc-request-id':`fixture-${index}`}),
      text:async () => JSON.stringify({actions:[{id:options.id || id,state:'SUCCESS',
        returnValue:{returnValue:JSON.stringify(payload),cacheable:false}}]})
    });
  }
  const terminal = history([...prior,user,answer]);
  const direct = {conversationId,message};
  if (kind === 'direct' || kind === 'mixed') await rpc('sendMessage', direct, terminal);
  if (kind !== 'direct') {
    const begin = {...direct, clientRequestId};
    if (kind === 'unexpected-param') begin.extra = true;
    const pending = history([...prior,user], {status:'working',
      pending:{token,requestId:kind === 'wrong-client-echo' ? 'wrong-request' : clientRequestId}});
    await rpc('beginMessage', begin, pending);
    const execId = kind === 'wrong-conversation' ? 'a01000000000002AAA' : conversationId;
    const execute = {conversationId:execId,turnToken:kind === 'wrong-token' ? 'wrong-capability' : token};
    const reply = kind === 'replay' ? history(prior) : {...terminal,conversationId:execId};
    if (kind === 'wrong-response-conversation') reply.conversationId = 'a01000000000003AAA';
    await rpc('executePendingMessage', execute, reply, {
      id:kind === 'wrong-response-id' ? 'wrong;a' : null,early:kind === 'early-execute',
    });
    if (kind === 'extra-execute') await rpc('executePendingMessage', execute, terminal);
  }
  const turn = h.matchTurn(observer.records, before, conversationId, message);
  return {method:turn.call.method, methods:observer.projection().map(call => call.method),
    added:turn.added.messages.map(row => row.role), rawTokenRetained:JSON.stringify(observer.projection()).includes(token)};
}
(async () => {
  for (const kind of ['direct','split','mixed','wrong-conversation','wrong-response-conversation','wrong-token',
    'wrong-response-id','wrong-client-echo','replay','early-execute','extra-execute','unexpected-param']) {
    try { results[kind] = await scenario(kind); }
    catch (error) { results[kind] = {reason:error.reason || error.message}; }
  }
  process.stdout.write(JSON.stringify(results));
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });'''
        observed = subprocess.run([shutil.which("node"), "-e", program, str(BROWSER)],
                                  capture_output=True, text=True, check=True, timeout=90)
        result = json.loads(observed.stdout)
        for case, methods in (("direct", ["sendMessage"]), ("split", ["beginMessage", "executePendingMessage"])):
            self.assertEqual({"method": methods[-1], "methods": methods,
                              "added": ["user", "assistant"], "rawTokenRetained": False}, result[case])
        self.assertEqual({"reason": "controller-response-id-mismatch"}, result["wrong-response-id"])
        self.assertEqual({"reason": "controller-response-invalid"}, result["wrong-response-conversation"])
        self.assertEqual({"reason": "controller-action-invalid"}, result["unexpected-param"])
        for case in ("mixed", "wrong-conversation", "wrong-token", "wrong-client-echo",
                     "replay", "early-execute", "extra-execute"):
            self.assertEqual({"reason": "controller-proof-missing"}, result[case], case)

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
