#!/usr/bin/env python3
"""Hermetic tests for Gym UI proof, scope, receipt, and Aura parser boundaries."""
from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "test" / "shiploop_e2e" / "checks" / "gym_ui.py"
BROWSER = ROOT / "test" / "shiploop_e2e" / "checks" / "gym_ui_browser.cjs"
spec = importlib.util.spec_from_file_location("gym_ui_checker", CHECK)
ui = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ui)

HOST = "example.lightning.force.com"
USER_ID = "005000000000001"
SELF_ID = "a0B000000000001"
COACHED_ID = "a0B000000000002"
BASIC_ID = "a0B000000000003"
VISIT_ID = "a0C000000000001"
VISIT_BASIC_ID = "a0C000000000002"


def _call(index, method, *, state="SUCCESS", member_id=None, status=None, plan=None,
          result_member_id=None, result_status=None, result_plan=None,
          result_count=None, visit_id=None):
    call = {
        "request_number": index,
        "method": method,
        "request_id": "action-%s;a" % index,
        "response_id": "action-%s;a" % index,
        "response_state": state,
        "params_verified": True,
    }
    if member_id is not None or method == "adminSave":
        call["member_id"] = member_id
    if status is not None:
        call["status_value"] = status
    if plan is not None:
        call["plan_value"] = plan
    if result_member_id is not None:
        call["result_member_id"] = result_member_id
    if result_status is not None:
        call["result_status"] = result_status
    if result_plan is not None:
        call["result_plan"] = result_plan
    if result_count is not None:
        call["result_visit_count"] = result_count
    if visit_id is not None:
        call["visit_id"] = visit_id
    return call


def complete_observation(initial_status=None):
    calls = [
        _call(1, "getMyMembership"),
        _call(2, "listMembers"),
        _call(3, "saveMyMembership", result_member_id=SELF_ID,
              result_status=initial_status or "Active", result_plan="Basic"),
        _call(4, "setMyStatus", status="Frozen", result_member_id=SELF_ID,
              result_status="Frozen", result_plan="Basic"),
        _call(5, "saveMyMembership", result_member_id=SELF_ID,
              result_status="Frozen", result_plan="Coached"),
        _call(6, "setMyStatus", status="Active", result_member_id=SELF_ID,
              result_status="Active", result_plan="Coached"),
        _call(7, "getMyMembership"),
        _call(8, "adminSave", status="Active", plan="Coached",
              result_member_id=COACHED_ID, result_status="Active",
              result_plan="Coached", result_count=0),
        _call(9, "member360", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Active", result_plan="Coached", result_count=0),
        _call(10, "checkIn", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Active", result_plan="Coached", result_count=1, visit_id=VISIT_ID),
        _call(11, "checkIn", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Active", result_plan="Coached", result_count=1, visit_id=VISIT_ID),
        _call(12, "member360", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Active", result_plan="Coached", result_count=1),
        _call(13, "adminSave", member_id=COACHED_ID, status="Frozen", plan="Coached",
              result_member_id=COACHED_ID, result_status="Frozen", result_plan="Coached",
              result_count=1),
        _call(14, "checkIn", state="ERROR", member_id=COACHED_ID),
        _call(15, "member360", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Frozen", result_plan="Coached", result_count=1),
        _call(16, "adminSave", member_id=COACHED_ID, status="Cancelled", plan="Coached",
              result_member_id=COACHED_ID, result_status="Cancelled", result_plan="Coached",
              result_count=1),
        _call(17, "checkIn", state="ERROR", member_id=COACHED_ID),
        _call(18, "member360", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Cancelled", result_plan="Coached", result_count=1),
        _call(19, "adminSave", status="Active", plan="Basic",
              result_member_id=BASIC_ID, result_status="Active",
              result_plan="Basic", result_count=0),
        _call(20, "member360", member_id=BASIC_ID, result_member_id=BASIC_ID,
              result_status="Active", result_plan="Basic", result_count=0),
        _call(21, "checkIn", member_id=BASIC_ID, result_member_id=BASIC_ID,
              result_status="Active", result_plan="Basic", result_count=1,
              visit_id=VISIT_BASIC_ID),
        _call(22, "member360", member_id=COACHED_ID, result_member_id=COACHED_ID,
              result_status="Cancelled", result_plan="Coached", result_count=1),
        _call(23, "member360", member_id=BASIC_ID, result_member_id=BASIC_ID,
              result_status="Active", result_plan="Basic", result_count=1),
    ]
    if initial_status in {"Frozen", "Cancelled"}:
        calls.insert(6, _call(24, "adminSave", member_id=SELF_ID, status="Active",
                              plan="Basic", result_member_id=SELF_ID,
                              result_status="Active", result_plan="Basic"))
    return {
        "schema": "shiploop-gym-ui-browser/1",
        "route_host": HOST,
        "route_path": "/lightning/n/SLGym_Members",
        "browser_version": "Chromium 130.0",
        "journeys": {
            "self": {
                "member_id": SELF_ID,
                "initial_status": initial_status,
                "first_save_status": initial_status or "Active",
                "frozen_status": "Frozen",
                "frozen_edit_status": "Frozen",
                "resume_status": "Active",
                "reloaded_status": "Active",
                "frozen_profile_edit_verified": True,
            },
            "coached": {
                "member_id": COACHED_ID,
                "plan_verified": True,
                "initial_visit_count": 0,
                "first_visit_id": VISIT_ID,
                "repeat_visit_id": VISIT_ID,
                "first_visit_count": 1,
                "repeat_visit_count": 1,
                "coaching_contains_goal": True,
                "frozen_refused": True,
                "cancelled_refused": True,
                "visits_after_frozen_refusal": 1,
                "visits_after_cancelled_refusal": 1,
                "reloaded_status": "Cancelled",
                "reloaded_visit_count": 1,
            },
            "basic": {
                "member_id": BASIC_ID,
                "plan_verified": True,
                "visit_id": VISIT_BASIC_ID,
                "visit_count": 1,
                "coaching_contains_independent_training": True,
                "reloaded_status": "Active",
                "reloaded_visit_count": 1,
            },
        },
        "calls": calls,
    }


def mutation_only_observation(initial_status=None):
    observation = complete_observation(initial_status)
    observation["calls"] = [
        call for call in observation["calls"]
        if call["method"] not in {"getMyMembership", "listMembers", "member360"}
    ]
    return observation


def fake_shared():
    def query_result(records):
        return {"status": 0, "result": {
            "done": True, "totalSize": len(records), "records": records,
        }}

    class Shared:
        def __init__(self):
            self.synthetic = None

        def org_identity(self, org):
            return {"alias": org, "org_id": ui.EXPECTED_ORG_ID, "lightning_host": HOST}

        def sf_json(self, argv, timeout=60):
            if argv[:2] == ["org", "list"]:
                return {"status": 0, "result": {"nonScratchOrgs": [
                    {"alias": "de", "username": "gym-admin@example.invalid"},
                ]}}
            query = argv[3]
            if "FROM Organization" in query:
                return query_result([
                    {"Id": ui.EXPECTED_ORG_ID, "OrganizationType": "Developer Edition"},
                ])
            if "FROM User " in query:
                return query_result([
                    {"Id": USER_ID, "Profile": {"PermissionsModifyAllData": True}},
                ])
            if "WHERE LoginUserId__c =" in query:
                rows = []
                if self.synthetic is not None:
                    profile = self.synthetic["self_final"]
                    rows.append({
                        "Id": SELF_ID, "FullName__c": profile["fullName"],
                        "Email__c": profile["email"], "Goal__c": profile["goal"],
                        "Plan__c": profile["plan"], "Status__c": "Active",
                        "LoginUserId__c": USER_ID,
                    })
                return query_result(rows)
            if "Member__c WHERE Id IN" in query:
                assert self.synthetic is not None
                profiles = self.synthetic
                return query_result([
                    {
                        "Id": SELF_ID, "FullName__c": profiles["self_final"]["fullName"],
                        "Email__c": profiles["self_final"]["email"],
                        "Goal__c": profiles["self_final"]["goal"],
                        "Plan__c": profiles["self_final"]["plan"], "Status__c": "Active",
                        "LoginUserId__c": USER_ID,
                    },
                    {
                        "Id": COACHED_ID, "FullName__c": profiles["coached"]["fullName"],
                        "Email__c": profiles["coached"]["email"],
                        "Goal__c": profiles["coached"]["goal"],
                        "Plan__c": "Coached", "Status__c": "Cancelled",
                        "LoginUserId__c": None,
                    },
                    {
                        "Id": BASIC_ID, "FullName__c": profiles["basic"]["fullName"],
                        "Email__c": profiles["basic"]["email"],
                        "Goal__c": profiles["basic"]["goal"],
                        "Plan__c": "Basic", "Status__c": "Active",
                        "LoginUserId__c": None,
                    },
                ])
            if "Visit__c WHERE Member__c IN" in query:
                return query_result([
                    {"Id": VISIT_ID, "Member__c": COACHED_ID,
                     "Coaching__c": self.synthetic["coached"]["goal"] + " stored"},
                    {"Id": VISIT_BASIC_ID, "Member__c": BASIC_ID,
                     "Coaching__c": "Independent training"},
                ])
            raise AssertionError("unexpected mocked query")

        def candidate_fingerprint(self, root):
            return "source-head", "metadata-hash"

        def frontdoor_url(self, org):
            return "https://private.example/frontdoor?token=PRIVATE_FRONTDOOR"

        def command_path(self, name):
            return "/usr/bin/node"

        def runtime_env(self):
            return {}

    return Shared()


class GymUiProofTests(unittest.TestCase):
    def test_incomplete_or_truncated_soql_result_fails_closed(self):
        for result in (
            {"records": []},
            {"done": False, "totalSize": 0, "records": []},
            {"done": True, "totalSize": 2, "records": [{}]},
            {"done": True, "totalSize": True, "records": []},
        ):
            with self.subTest(result=result), self.assertRaises(ui.CheckFailure):
                ui._result_records({"result": result})

    def test_duplicate_aura_ids_are_scoped_to_http_request_number(self):
        observation = complete_observation()
        reused_id = observation["calls"][0]["request_id"]
        observation["calls"][1]["request_id"] = reused_id
        observation["calls"][1]["response_id"] = reused_id
        self.assertEqual(
            [], ui.validate_browser_observation(
                observation, expected_host=HOST, prefix="SLGym",
            ),
        )
        _, calls = ui._closed_browser_projection(observation)
        self.assertEqual(
            [(1, reused_id, reused_id), (2, reused_id, reused_id)],
            [(call["request_number"], call["request_id"], call["response_id"])
             for call in calls[:2]],
        )

        duplicate_pair = complete_observation()
        duplicate_pair["calls"][1]["request_number"] = duplicate_pair["calls"][0]["request_number"]
        duplicate_pair["calls"][1]["request_id"] = duplicate_pair["calls"][0]["request_id"]
        duplicate_pair["calls"][1]["response_id"] = duplicate_pair["calls"][0]["response_id"]
        self.assertIn(
            "controller-proof-invalid",
            ui.validate_browser_observation(duplicate_pair, expected_host=HOST, prefix="SLGym"),
        )

        for request_number in (0, True, "1"):
            invalid_number = complete_observation()
            invalid_number["calls"][0]["request_number"] = request_number
            with self.subTest(request_number=request_number):
                self.assertIn(
                    "controller-proof-missing",
                    ui.validate_browser_observation(
                        invalid_number, expected_host=HOST, prefix="SLGym",
                    ),
                )

    def test_accepts_complete_observation_for_active_and_builder_owned_cancelled_self(self):
        for initial in (None, "Active", "Frozen", "Cancelled"):
            with self.subTest(initial=initial):
                self.assertEqual(
                    [],
                    ui.validate_browser_observation(
                        complete_observation(initial), expected_host=HOST, prefix="SLGym",
                    ),
                )

    def test_cacheable_read_rpcs_are_optional_but_mutation_proof_is_required(self):
        observation = mutation_only_observation()
        self.assertEqual(
            [], ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )

        observation = complete_observation()
        observation["calls"] = [call for call in observation["calls"]
                                if call["method"] != "setMyStatus"]
        self.assertIn(
            "controller-proof-missing",
            ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )

    def test_wrong_persisted_soql_state_still_fails_without_read_rpcs(self):
        shared = fake_shared()
        synthetic = ui._synthetic_profiles("wrong-soql")
        shared.synthetic = synthetic
        original_query = shared.sf_json

        def mismatched_query(argv, timeout=60):
            document = original_query(argv, timeout=timeout)
            if "Member__c WHERE Id IN" in argv[3]:
                document["result"]["records"][0]["FullName__c"] = "Wrong stored value"
            return document

        shared.sf_json = mismatched_query
        with self.assertRaises(ui.CheckFailure) as failure:
            ui._validate_database(
                shared, "de", "SLGym", USER_ID, None, synthetic,
                mutation_only_observation(),
            )
        self.assertEqual("database-state-mismatch", failure.exception.reason)

    def test_rejects_empty_or_incomplete_controller_proof(self):
        observation = complete_observation()
        observation["calls"] = []
        self.assertIn(
            "controller-proof-missing",
            ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )
        observation = complete_observation()
        observation["calls"][0]["response_id"] = "different;a"
        self.assertIn(
            "controller-proof-missing",
            ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )

    def test_rejects_unknown_methods_private_fields_and_wrong_host(self):
        cases = []
        observation = complete_observation()
        observation["calls"][0]["method"] = "deleteMember"
        cases.append(observation)
        observation = complete_observation()
        observation["calls"][0]["email"] = "person@example.invalid"
        cases.append(observation)
        observation = complete_observation()
        observation["route_host"] = "other.lightning.force.com"
        cases.append(observation)
        for item in cases:
            with self.subTest(item=item):
                self.assertTrue(
                    ui.validate_browser_observation(item, expected_host=HOST, prefix="SLGym"),
                )

    def test_rejects_wrong_repeat_visit_or_wrong_refusal_count(self):
        observation = complete_observation()
        observation["journeys"]["coached"]["repeat_visit_id"] = VISIT_BASIC_ID
        self.assertIn(
            "journey-invalid",
            ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )
        observation = complete_observation()
        observation["journeys"]["coached"]["visits_after_cancelled_refusal"] = 2
        self.assertIn(
            "journey-invalid",
            ui.validate_browser_observation(observation, expected_host=HOST, prefix="SLGym"),
        )

    def test_receipt_writer_hashes_phase_artifact_and_keeps_it_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            platform = Path(temporary) / "platform"
            platform.mkdir()
            path = platform / "gym-ui" / "final" / "observation.json"
            path.parent.mkdir(parents=True)
            relative, digest = ui._write_receipt(
                path, platform, {"schema": "shiploop-gym-ui-observation/1", "status": "failed"},
            )
            self.assertEqual("gym-ui/final/observation.json", relative)
            self.assertEqual(64, len(digest))
            self.assertEqual(0o600, path.stat().st_mode & 0o777)

    def test_scope_requires_one_fixed_org_prefix_and_named_check(self):
        args, errors = ui.parse_scope(["--org", "de", "--prefix", "SLGym",
                                       "--final", "--check-name", "gym-ui"])
        self.assertEqual([], errors)
        self.assertTrue(args.final)
        self.assertIn("duplicate-scope-option",
                      ui.parse_scope(["--org", "de", "--org", "elsewhere",
                                      "--prefix", "SLGym"])[1])
        self.assertIn("scope-invalid",
                      ui.parse_scope(["--org", "de", "--prefix", "SLGym",
                                      "--check-name", "other"])[1])

    def test_harness_phase_owns_receipt_phase_even_when_final_flag_is_passed(self):
        with mock.patch.dict(os.environ, {"E2E_CHECK_PHASE": "builder"}):
            args, errors = ui.parse_scope(["--org", "de", "--prefix", "SLGym", "--final"])
            self.assertEqual([], errors)
            self.assertTrue(args.final)
            self.assertEqual("builder", ui.check_phase())
        with mock.patch.dict(os.environ, {"E2E_CHECK_PHASE": "final"}):
            self.assertEqual("final", ui.check_phase())

    def test_org_and_current_user_identity_gates_fail_closed(self):
        with self.assertRaises(ui.CheckFailure):
            ui._organization_preflight(
                SimpleNamespace(org_identity=lambda org: {
                    "alias": "de", "org_id": "00D000000000001",
                    "lightning_host": HOST,
                }),
                "de",
            )

        class NonAdmin:
            def sf_json(self, argv, timeout=60):
                if argv[:2] == ["org", "list"]:
                    return {"result": {"nonScratchOrgs": [
                        {"alias": "de", "username": "member@example.invalid"},
                    ]}}
                return {"result": {"done": True, "totalSize": 1, "records": [
                    {"Id": USER_ID, "Profile": {"PermissionsModifyAllData": False}},
                ]}}

        with self.assertRaises(ui.CheckFailure):
            ui._current_user(NonAdmin(), "de")

    def test_mocked_builder_run_records_sanitized_soql_and_screenshot_proof(self):
        shared = fake_shared()
        observation = complete_observation()

        def fake_browser(command, *, input, **kwargs):
            request = json.loads(input)
            self.assertEqual("https://private.example/frontdoor?token=PRIVATE_FRONTDOOR",
                             request["login_url"])
            self.assertIsNone(request["initial_self"])
            shared.synthetic = request["synthetic"]
            for filename in request["screenshots"].values():
                Path(filename).write_bytes(b"synthetic screenshot")
            return SimpleNamespace(returncode=0, stdout=json.dumps(observation), stderr="PRIVATE_STDERR")

        with tempfile.TemporaryDirectory() as temporary:
            platform = Path(temporary) / "run" / "platform"
            platform.mkdir(parents=True)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {
                "E2E_PLATFORM_DIR": str(platform), "E2E_CHECK_PHASE": "builder",
            }), mock.patch.object(ui.subprocess, "run", side_effect=fake_browser), \
                 mock.patch.object(ui.sys, "stdout", stdout), \
                 mock.patch.object(ui.sys, "stderr", stderr):
                self.assertEqual(0, ui.run_check("de", "SLGym", shared=shared))
            receipt_path = next(platform.rglob("observation.json"))
            receipt_text = receipt_path.read_text()
            receipt = json.loads(receipt_text)
            self.assertEqual("builder", receipt["phase"])
            self.assertEqual("builder", receipt_path.parent.parent.name)
            self.assertEqual("passed", receipt["status"])
            self.assertEqual(7, len(receipt["screenshots"]))
            self.assertTrue(all(len(value["sha256"]) == 64 for value in receipt["screenshots"].values()))
            self.assertNotIn("@example.invalid", receipt_text)
            self.assertNotIn("PRIVATE_FRONTDOOR", receipt_text)
            self.assertNotIn("PRIVATE_STDERR", receipt_text)
            self.assertNotIn("Gym Self", receipt_text)
            self.assertNotIn("email", json.dumps(receipt["controller_calls"]).lower())

    def test_missing_browser_proof_cannot_pass_or_retain_browser_errors(self):
        shared = fake_shared()

        def failed_browser(command, *, input, **kwargs):
            return SimpleNamespace(
                returncode=1,
                stdout=json.dumps({"status": "failed", "stage": "controller",
                                   "reason": "controller-proof-missing"}),
                stderr="PRIVATE_EMAIL person@example.invalid PRIVATE_FRONTDOOR",
            )

        with tempfile.TemporaryDirectory() as temporary:
            platform = Path(temporary) / "run" / "platform"
            platform.mkdir(parents=True)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(platform)}), \
                 mock.patch.object(ui.subprocess, "run", side_effect=failed_browser), \
                 mock.patch.object(ui.sys, "stdout", stdout), mock.patch.object(ui.sys, "stderr", stderr):
                self.assertEqual(1, ui.run_check("de", "SLGym", shared=shared))
            receipt_path = next(platform.rglob("observation.json"))
            receipt_text = receipt_path.read_text()
            self.assertEqual("failed", json.loads(receipt_text)["status"])
            self.assertNotIn("person@example.invalid", receipt_text + stdout.getvalue() + stderr.getvalue())
            self.assertNotIn("PRIVATE_FRONTDOOR", receipt_text + stdout.getvalue() + stderr.getvalue())
            self.assertNotIn("PRIVATE_EMAIL", receipt_text + stdout.getvalue() + stderr.getvalue())

    def test_missing_screenshot_prevents_a_valid_browser_projection_from_passing(self):
        shared = fake_shared()
        observation = complete_observation()

        def browser_without_screenshots(command, *, input, **kwargs):
            request = json.loads(input)
            shared.synthetic = request["synthetic"]
            return SimpleNamespace(returncode=0, stdout=json.dumps(observation), stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            platform = Path(temporary) / "run" / "platform"
            platform.mkdir(parents=True)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {"E2E_PLATFORM_DIR": str(platform)}), \
                 mock.patch.object(ui.subprocess, "run", side_effect=browser_without_screenshots), \
                 mock.patch.object(ui.sys, "stdout", stdout), \
                 mock.patch.object(ui.sys, "stderr", stderr):
                self.assertEqual(1, ui.run_check("de", "SLGym", shared=shared))
            receipt = json.loads(next(platform.rglob("observation.json")).read_text())
            self.assertEqual("failed", receipt["status"])
            self.assertEqual("screenshot-missing", receipt["failure"]["reason"])

    def test_node_aura_parser_correlates_only_allowlisted_actions_and_sanitizes_projection(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const memberId = 'a0B000000000001';
const request = {
  id: '44;a',
  descriptor: 'apex://SLGymController/ACTION$checkIn',
  params: { memberId },
};
const body = new URLSearchParams({ message: JSON.stringify({ actions: [request] }) }).toString();
const parsed = ui.parseAuraRequest(body, 'SLGymController');
assert.equal(parsed.length, 1);
assert.equal(parsed[0].id, request.id);
assert.equal(parsed[0].params.memberId, memberId);
assert.equal(ui.parseAuraRequest(JSON.stringify({ actions: [request] }),
  'SLGymController').length, 1);
assert.equal(ui.parseAuraRequest(JSON.stringify({ message: { actions: [request] } }),
  'SLGymController').length, 1);
const wrapped = {
  id: '45;a',
  descriptor: 'aura://ApexActionController/ACTION$execute',
  params: { classname: 'SLGymController', method: 'checkIn', params: { memberId } },
};
assert.equal(ui.parseAuraRequest(JSON.stringify({ actions: [wrapped] }),
  'SLGymController')[0].method, 'checkIn');
const duplicateMessage = new URLSearchParams();
duplicateMessage.append('message', JSON.stringify({ actions: [request] }));
duplicateMessage.append('message', JSON.stringify({ actions: [request] }));
assert.throws(() => ui.parseAuraRequest(duplicateMessage.toString(), 'SLGymController'));
assert.throws(() => ui.parseAuraRequest(JSON.stringify({
  actions: [request, { ...request }],
}), 'SLGymController'), error => error.reason === 'controller-id-invalid');
assert.throws(() => ui.parseAuraRequest(JSON.stringify({
  actions: [request, { ...request, descriptor: 'apex://OtherController/ACTION$checkIn' }],
}), 'SLGymController'), error => error.reason === 'controller-id-invalid');
assert.deepEqual(ui.parseAuraResponse(JSON.stringify({
  actions: [{ id: request.id, state: 'SUCCESS', returnValue: JSON.stringify({
    id: memberId, status: 'Active', plan: 'Basic', loginUserId: null,
    visitCount: 1, visitId: 'a0C000000000001', coaching: 'Independent training',
  }) }],
}), parsed).map(item => item.state), ['SUCCESS']);
assert.throws(() => ui.parseAuraRequest(new URLSearchParams({ message: JSON.stringify({
  actions: [{ ...request, descriptor: 'apex://SLGymController/ACTION$deleteMember' }],
}) }).toString(), 'SLGymController'));
assert.throws(() => ui.parseAuraResponse(JSON.stringify({
  actions: [{ id: 'wrong;a', state: 'SUCCESS', returnValue: '{}' }],
}), parsed));
assert.equal(ui.choiceControlMode('SELECT'), 'native-select');
assert.equal(ui.choiceControlMode('LIGHTNING-COMBOBOX'), 'lightning-combobox');
assert.equal(ui.shouldAssertCoachingText(null), false);
assert.equal(ui.shouldAssertCoachingText(''), false);
assert.equal(ui.shouldAssertCoachingText('   '), false);
assert.equal(ui.shouldAssertCoachingText('Independent training'), true);
assert.equal(ui.auraEndpointAllowed(
  'https://example.lightning.force.com/aura?r=1', 'example.lightning.force.com',
), true);
assert.equal(ui.auraEndpointAllowed(
  'http://example.lightning.force.com/aura', 'example.lightning.force.com',
), false);
assert.equal(ui.auraEndpointAllowed(
  'https://other.lightning.force.com/aura', 'example.lightning.force.com',
), false);
assert.equal(ui.auraEndpointAllowed(
  'https://example.lightning.force.com:8443/aura', 'example.lightning.force.com',
), false);
assert.equal(ui.normalizeHost('other.lightning.force.com'), 'other.lightning.force.com');
assert.equal(ui.normalizeHost('not-salesforce.example'), null);
const observer = new ui.GymAuraObserver({}, 'SLGymController', 'example.lightning.force.com');
observer.calls.push({
  sequence: 1, request_number: 1, method: 'saveMyMembership',
  request_id: '45;a', response_id: '45;a',
  response_state: 'SUCCESS', params_verified: true, proof_required: true,
  params: { fullName: 'SECRET NAME', email: 'SECRET EMAIL', goal: 'SECRET GOAL', plan: 'Basic' },
  value: { id: memberId, fullName: 'Gym Person', email: 'gym@example.invalid',
    goal: 'Strength', status: 'Active', plan: 'Basic', visitCount: 0 },
});
const projection = JSON.stringify(observer.projection());
assert(!projection.includes('SECRET'));
process.stdout.write('ok');
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_aura_parser_normalizes_no_arg_reads_but_requires_mutation_params(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const controller = 'SLGymController';
let nextId = 50;
function actionFor(method, kind, params, includeParams) {
  const id = `${nextId++};a`;
  if (kind === 'direct') {
    return {
      id,
      descriptor: `apex://${controller}/ACTION$${method}`,
      ...(includeParams ? { params } : {}),
    };
  }
  return {
    id,
    descriptor: 'aura://ApexActionController/ACTION$execute',
    params: {
      classname: controller,
      method,
      ...(includeParams ? { params } : {}),
    },
  };
}
function parse(action) {
  return ui.parseAuraRequest(JSON.stringify({ actions: [action] }), controller);
}
for (const method of ['getMyMembership', 'listMembers']) {
  for (const kind of ['direct', 'wrapped']) {
    for (const [label, params, includeParams] of [
      ['absent', undefined, false], ['null', null, true], ['empty', {}, true],
    ]) {
      const action = actionFor(method, kind, params, includeParams);
      assert.deepEqual(parse(action), [{ id: action.id, method, params: {} }],
        `${kind} ${method} ${label} params`);
    }
  }
}
for (const kind of ['direct', 'wrapped']) {
  for (const [label, params, includeParams] of [
    ['absent', undefined, false], ['null', null, true],
  ]) {
    const action = actionFor('saveMyMembership', kind, params, includeParams);
    assert.throws(() => parse(action), error => error.reason === 'controller-params-invalid',
      `${kind} mutation ${label} params`);
  }
}
process.stdout.write('ok');
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_aura_observer_pairs_duplicate_action_ids_by_http_request(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const controller = 'SLGymController';
const host = 'example.lightning.force.com';
const url = `https://${host}/aura`;
const actionId = '77;a';
const observer = new ui.GymAuraObserver({ waitForTimeout: async () => {} }, controller, host);
const profiles = [
  { fullName: 'Synthetic One', email: 'one@example.invalid', goal: 'Strength', plan: 'Basic' },
  { fullName: 'Synthetic Two', email: 'two@example.invalid', goal: 'Mobility', plan: 'Coached' },
  { fullName: 'Synthetic Unrelated', email: 'other@example.invalid', goal: 'Balance', plan: 'Basic' },
];
const dto = (index) => ({
  id: `a0B00000000000${index + 1}`,
  ...profiles[index], status: 'Active', loginUserId: null, visitCount: 0,
});
const action = profile => ({
  id: actionId,
  descriptor: `apex://${controller}/ACTION$saveMyMembership`,
  params: profile,
});
const request = body => ({
  url: () => url,
  method: () => 'POST',
  postData: () => JSON.stringify(body),
});
const firstRequest = request({ actions: [action(profiles[0])] });
const secondRequest = request({ actions: [action(profiles[1])] });
const unrelatedRequest = request({ actions: [{
  id: actionId,
  descriptor: 'apex://OtherController/ACTION$unrelated',
  params: {},
}] });
const response = (requestObject, value, responseUrl = url) => ({
  url: () => responseUrl,
  request: () => requestObject,
  status: () => 200,
  text: async () => JSON.stringify({ actions: [{
    id: actionId,
    state: 'SUCCESS',
    returnValue: JSON.stringify(value),
  }] }),
});

observer._request(firstRequest);
observer._request(secondRequest);
observer._request(unrelatedRequest);
(async () => {
  await observer._response(response(unrelatedRequest, dto(2)));
  assert.equal(observer.calls.length, 0,
    'an unrelated HTTP response with the same action ID must not satisfy either call');

  await assert.rejects(
    observer._response(response(secondRequest, dto(1), 'https://other.lightning.force.com/aura')),
    error => error.reason === 'controller-host-invalid',
  );
  assert.equal(observer.calls.length, 0,
    'a wrong-host response must not satisfy a request from the expected host');

  await observer._response(response(secondRequest, dto(1)));
  assert.equal(observer.calls.length, 1);
  assert.equal(observer.calls[0].params.email, profiles[1].email);
  assert.equal(observer.calls[0].value.id, dto(1).id);
  assert.equal(observer.calls[0].request_id, actionId);
  assert.equal(observer.calls[0].response_id, actionId);
  assert.equal(observer.calls.some(call => call.params.email === profiles[0].email), false,
    'the second request response must not satisfy the first request');

  await observer._response(response(firstRequest, dto(0)));
  assert.equal(observer.calls.length, 2);
  const firstCall = await observer.waitForCall(0, 'saveMyMembership',
    (params, value) => params.email === profiles[0].email && ui.normalizeDto(value).id === dto(0).id,
    'SUCCESS', 10);
  const secondCall = await observer.waitForCall(0, 'saveMyMembership',
    (params, value) => params.email === profiles[1].email && ui.normalizeDto(value).id === dto(1).id,
    'SUCCESS', 10);
  assert.equal(firstCall.request_id, actionId);
  assert.equal(firstCall.response_id, actionId);
  assert.equal(firstCall.request_number, 1);
  assert.equal(secondCall.request_id, actionId);
  assert.equal(secondCall.response_id, actionId);
  assert.equal(secondCall.request_number, 2);
  assert.deepEqual(observer.projection()
    .map(call => [call.request_number, call.request_id, call.response_id])
    .sort((left, right) => left[0] - right[0]), [
      [1, actionId, actionId], [2, actionId, actionId],
    ]);
  assert.equal(observer.failure, null, 'separate HTTP requests may reuse an Aura action ID');
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_real_apex_action_envelope_preserves_dto_validation_and_mutation_proof(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const dto = {
  id: 'a0B000000000001', fullName: 'Synthetic', email: 'member@example.invalid',
  goal: 'Strength', plan: 'Coached', status: 'Active', loginUserId: null, visitCount: 0,
};
// Actual read-only transport capture had these outer keys, with a JSON String inside.
const wrapped = value => ({ cacheable: false, returnValue: JSON.stringify(value) });
for (const value of [dto, JSON.stringify(dto), wrapped(dto), JSON.stringify(wrapped(dto)),
  { returnValue: JSON.stringify(dto) }]) {
  assert.equal(ui.normalizeDto(value).id, dto.id);
}
assert.deepEqual(ui.normalizeList(wrapped([dto])).map(item => item.id), [dto.id]);
assert.equal(ui.normalizeDto(wrapped(null)), null);
for (const value of [
  wrapped({ ...dto, visitCount: -1 }), wrapped({ ...dto, status: 'Unknown' }),
  { cacheable: false, returnValue: 'not JSON' },
  { ...dto, returnValue: JSON.stringify(dto), visitCount: -1 },
]) assert.throws(() => ui.normalizeDto(value));

const host = 'example.lightning.force.com';
const url = 'https://' + host + '/aura';
const observer = new ui.GymAuraObserver({ waitForTimeout: async () => {} }, 'SLGymController', host);
const action = { id: 'saved;a', descriptor: 'aura://ApexActionController/ACTION$execute',
  params: { classname: 'SLGymController', method: 'saveMyMembership',
    params: { fullName: dto.fullName, email: dto.email, goal: dto.goal, plan: dto.plan } } };
const requestObject = { url: () => url, method: () => 'POST',
  postData: () => JSON.stringify({ actions: [action] }) };
observer._request(requestObject);
(async () => {
  await observer._response({ url: () => url, request: () => requestObject, status: () => 200,
    text: async () => JSON.stringify({
    actions: [{ id: action.id, state: 'SUCCESS', returnValue: wrapped(dto) }],
  }) });
  const call = await observer.waitForCall(0, 'saveMyMembership',
    (params, value) => params.email === dto.email && ui.normalizeDto(value).id === dto.id,
    'SUCCESS', 10);
  assert.equal(call.params_verified, true);
  assert.equal(observer.projection()[0].result_member_id, dto.id);
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_optional_admin_create_null_360_and_incidental_calls_do_not_poison_proof(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const host = 'example.lightning.force.com';
const controller = 'SLGymController';
const omitted = { fullName: 'Synthetic', email: 'member@example.invalid', goal: 'Strength',
  plan: 'Coached', status: 'Active' };
assert.equal(ui.paramsAreValid('adminSave', omitted), true);
const create = { id: 'create;a', descriptor: 'apex://SLGymController/ACTION$adminSave', params: omitted };
const normalized = ui.parseAuraRequest(JSON.stringify({ actions: [create] }), controller)[0];
assert.equal(normalized.params.memberId, null);
const nullRead = { id: 'read;a', descriptor: 'apex://SLGymController/ACTION$member360',
  params: { memberId: null } };
assert.equal(ui.parseAuraRequest(JSON.stringify({ actions: [nullRead] }), controller)[0].params.memberId, null);

const observer = new ui.GymAuraObserver({ waitForTimeout: async () => {} }, controller, host);
const url = 'https://' + host + '/aura';
const request = (action) => ({ url: () => url, method: () => 'POST',
  postData: () => JSON.stringify({ actions: [action] }) });
const response = (requestObject, id, state, value) => ({ url: () => url,
  request: () => requestObject, status: () => 200,
  text: async () => JSON.stringify({ actions: [{ id, state,
    ...(value === undefined ? {} : { returnValue: JSON.stringify(value) }) }] }) });
(async () => {
  const readRequest = request(nullRead);
  observer._request(readRequest);
  await observer._response(response(readRequest, 'read;a', 'ERROR'));
  assert.equal(observer.failure, null);
  assert.deepEqual(observer.projection(), []);
  const unrelated = { id: 'update;a', descriptor: 'apex://SLGymController/ACTION$adminSave',
    params: { ...omitted, memberId: 'a0B000000000009' } };
  const unrelatedRequest = request(unrelated);
  observer._request(unrelatedRequest);
  await observer._response(response(unrelatedRequest, 'update;a', 'ERROR'));
  const createRequest = request(create);
  observer._request(createRequest);
  await observer._response(response(createRequest, 'create;a', 'SUCCESS', {
    id: 'a0B000000000001', fullName: 'Synthetic', email: 'member@example.invalid',
    goal: 'Strength', plan: 'Coached', status: 'Active', loginUserId: null, visitCount: 0,
  }));
  const call = await observer.waitForCall(0, 'adminSave', p => p.memberId === null, 'SUCCESS', 10);
  assert.equal(call.request_id, 'create;a');
  assert.deepEqual(observer.projection().map(item => item.request_id), ['create;a']);
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_waits_for_visible_controls_and_skips_unrelated_same_method_calls(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
(async () => {
  let visible = false;
  let waited = false;
  const locator = {
    first() { return this; },
    async waitFor(options) {
      assert.equal(options.state, 'visible');
      waited = true;
      await new Promise(resolve => setTimeout(resolve, 25));
      visible = true;
    },
    async count() { return visible ? 1 : 0; },
  };
  await ui.waitVisible(locator, { timeoutMs: 1000 });
  assert.equal(waited, true);
  assert.equal(visible, true);

  const observer = new ui.GymAuraObserver({ waitForTimeout: async () => {} },
    'SLGymController', 'example.lightning.force.com');
  observer.calls = [
    { sequence: 1, request_number: 1, method: 'adminSave',
      request_id: 'other;a', response_id: 'other;a',
      response_state: 'ERROR', params: { memberId: 'a0B000000000009' }, proof_required: false },
    { sequence: 2, request_number: 2, method: 'adminSave',
      request_id: 'wanted;a', response_id: 'wanted;a',
      response_state: 'SUCCESS', params: { memberId: null }, proof_required: false,
      value: { id: 'a0B000000000001', fullName: 'Synthetic',
        email: 'member@example.invalid', goal: 'Strength', plan: 'Coached',
        status: 'Active', loginUserId: null, visitCount: 0 } },
  ];
  const call = await observer.waitForCall(0, 'adminSave', p => p.memberId === null, 'SUCCESS', 10);
  assert.equal(call.request_id, 'wanted;a');
  assert.deepEqual(observer.projection().map(item => item.request_id), ['wanted;a']);
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_refusal_feedback_accepts_explanations_and_rejects_other_states(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
function pageFor(visibleTexts) {
  return {
    getByText(pattern) {
      const matches = visibleTexts.filter(text => pattern.test(text));
      return {
        first() { return this; },
        async waitFor({ state }) {
          assert.equal(state, 'visible');
          if (!matches.length) throw new Error('no visible match');
        },
        async count() { return matches.length; },
      };
    },
  };
}
(async () => {
  await ui.requireRefusal(pageFor(['Check-in refused']));
  await ui.requireRefusal(pageFor(['Check-in refused: membership is Frozen']));
  for (const visibleTexts of [['Check-in completed'], []]) {
    await assert.rejects(
      ui.requireRefusal(pageFor(visibleTexts)),
      error => error.stage === 'status-refusal' && error.reason === 'ui-state-invalid',
    );
  }
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_aura_batch_response_pairs_by_request_and_keeps_omitted_action_pending(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const host = 'example.lightning.force.com';
const url = `https://${host}/aura`;
const memberId = 'a0B000000000009';
const adminParams = {
  memberId, fullName: 'Batch Member', email: 'batch@example.invalid',
  goal: 'Strength', plan: 'Coached', status: 'Active',
};
const memberDto = {
  id: memberId, fullName: adminParams.fullName, email: adminParams.email,
  goal: adminParams.goal, plan: adminParams.plan, status: 'Active',
  loginUserId: null, visitCount: 0,
};
const actions = [
  { id: 'a;a', descriptor: 'apex://SLGymController/ACTION$adminSave', params: adminParams },
  { id: 'b;a', descriptor: 'apex://SLGymController/ACTION$checkIn', params: { memberId } },
];
const request = actionList => ({
  url: () => url,
  method: () => 'POST',
  postData: () => JSON.stringify({ actions: actionList }),
});
const response = (requestObject, responseActions) => ({
  url: () => url,
  request: () => requestObject,
  status: () => 200,
  text: async () => JSON.stringify({ actions: responseActions }),
});
const page = {
  async waitForTimeout(ms) {
    await new Promise(resolve => setTimeout(resolve, Math.min(ms, 5)));
  },
};
const observer = new ui.GymAuraObserver(page, 'SLGymController', host);
(async () => {
  const firstRequest = request(actions);
  observer._request(firstRequest);
  await observer._response(response(firstRequest, [
    { id: 'b;a', state: 'ERROR' },
    { id: 'a;a', state: 'SUCCESS', returnValue: JSON.stringify(memberDto) },
  ]));

  const adminCall = await observer.waitForCall(0, 'adminSave',
    (params, value) => params.memberId === memberId && params.email === adminParams.email
      && ui.normalizeDto(value).id === memberId,
    'SUCCESS', 50);
  const checkInCall = await observer.waitForCall(0, 'checkIn',
    params => params.memberId === memberId, 'ERROR', 50);
  assert.deepEqual(adminCall.params, adminParams);
  assert.equal(adminCall.request_id, 'a;a');
  assert.equal(adminCall.response_id, 'a;a');
  assert.equal(adminCall.response_state, 'SUCCESS');
  assert.equal(ui.normalizeDto(adminCall.value).status, 'Active');
  assert.equal(checkInCall.method, 'checkIn');
  assert.equal(checkInCall.request_id, 'b;a');
  assert.equal(checkInCall.response_id, 'b;a');
  assert.equal(checkInCall.response_state, 'ERROR');
  assert.equal(checkInCall.value, undefined);
  assert.equal(adminCall.request_number, checkInCall.request_number);
  assert.equal(Number.isInteger(adminCall.request_number) && adminCall.request_number > 0, true);
  assert.equal(adminCall.request_number, 1);
  assert.equal(observer.failure, null);

  const secondCursor = observer.cursor();
  const secondRequest = request(actions);
  observer._request(secondRequest);
  await observer._response(response(secondRequest, [
    { id: 'a;a', state: 'SUCCESS', returnValue: JSON.stringify(memberDto) },
  ]));
  const secondAdminCall = await observer.waitForCall(secondCursor, 'adminSave',
    (params, value) => params.memberId === memberId && ui.normalizeDto(value).id === memberId,
    'SUCCESS', 50);
  assert.equal(secondAdminCall.method, 'adminSave');
  assert.deepEqual(secondAdminCall.params, adminParams);
  assert.equal(secondAdminCall.request_number, 2);
  assert.equal(secondAdminCall.request_id, 'a;a');
  assert.equal(secondAdminCall.response_id, 'a;a');
  assert.equal(secondAdminCall.response_state, 'SUCCESS');
  assert.equal(ui.normalizeDto(secondAdminCall.value).id, memberId);
  assert.equal(observer.calls.some(call => call.request_number === 2 && call.request_id === 'b;a'), false);
  await assert.rejects(
    observer.waitForCall(secondCursor, 'checkIn',
      params => params.memberId === memberId, 'ERROR', 50),
    error => error.reason === 'controller-response-missing',
  );
  assert.equal(observer.failure, null);
  process.stdout.write('ok');
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)

    def test_node_self_reload_requires_rendered_saved_fields_and_status(self):
        script = r"""
const assert = require('node:assert/strict');
const ui = require(process.argv[1]);
const expected = { id: 'a0B000000000001', status: 'Active', fullName: 'Gym Person',
  email: 'gym@example.invalid', goal: 'Strength', plan: 'Coached' };
let fakeNow = 0;
function makePage(values) {
  const page = {
    loaded: false,
    async reload() { this.loaded = true; },
    async waitForTimeout(ms) { fakeNow += ms; },
    getByText(text) {
      return makeLocator(this, () => this.loaded && text === 'My status: Active');
    },
    getByRole(role, options) {
      const label = options.name;
      return makeLocator(this, () => this.loaded && (role === 'combobox' || role === 'textbox')
        && Object.hasOwn(values, label), {
        inputValue: async () => values[label],
        evaluate: async fn => fn({ tagName: label === 'My plan' ? 'SELECT' : 'INPUT' }),
        innerText: async () => '',
        getAttribute: async () => null,
      });
    },
    getByLabel(label) { return this.getByRole(label === 'My plan' ? 'combobox' : 'textbox', { name: label }); },
  };
  return page;
}
function makeLocator(page, visible, methods = {}) {
  return {
    first() { return this; },
    async waitFor() {
      if (!visible()) throw new Error('not visible');
    },
    async count() { return visible() ? 1 : 0; },
    ...methods,
  };
}
(async () => {
  const realNow = Date.now;
  fakeNow = 0;
  Date.now = () => fakeNow;
  const values = { 'My full name': expected.fullName, 'My email': expected.email,
    'My goal': expected.goal, 'My plan': expected.plan };
  try {
    await ui.readSelf(makePage(values), expected);
    const stale = { ...values, 'My full name': 'Stale name' };
    await assert.rejects(() => ui.readSelf(makePage(stale), expected),
      error => error.reason === 'ui-state-invalid');
    process.stdout.write('ok');
  } finally {
    Date.now = realNow;
  }
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
        result = subprocess.run(
            ["node", "-e", script, str(BROWSER)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ok", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
