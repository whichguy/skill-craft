#!/usr/bin/env python3
"""Hermetic safety/verdict checks for the opt-in gym adapter; never calls a real org."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "test/shiploop_e2e/checks/gym_membership_salesforce.py"
spec = importlib.util.spec_from_file_location("gym_acceptance", PATH)
gym = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gym)
P = "SLGym"
IDENTITY = {"Id": gym.EXPECTED_ORG_ID, "OrganizationType": "Developer Edition", "IsSandbox": False}


def baseline():
    names = {kind: [] for kind in gym.sfc.SPEC}
    names.update(ApexClass=["OtherClass"], LightningComponentBundle=["otherBundle"],
                 CustomObject=["KeepObject"], PermissionSet=["OtherAccess"])
    dates = {"ApexClass": {"OtherClass": "before"}, "LightningComponentBundle": {"otherBundle": "before"}}
    org = {"names": names, "dates": dates, "unavailable": {}}
    before = {"org": "de", "prefix": P, "apex_classes": names["ApexClass"],
              "lightning_component_bundles": names["LightningComponentBundle"],
              "last_modified": dates, "other_types": {k: v for k, v in names.items() if k not in gym.sfc.OWN_TYPES},
              "unavailable": {}, "gym": {"schema": "shiploop-gym-snapshot/1", "identity": IDENTITY,
              "object_api_names": [], "fields": [["Account", "KeepField"]]}}
    return copy.deepcopy(before), copy.deepcopy(org)


class IdentityTest(unittest.TestCase):
    def test_generated_entities_do_not_fail_deployment(self):
        entities = [P + suffix for suffix in ("Member__c", "Member__Share", "Member__ChangeEvent",
                                               "Visit__c", "Visit__ChangeEvent")]
        with mock.patch.object(gym, "identity", return_value=IDENTITY), \
                mock.patch.object(gym.sfc, "records", return_value=[{"QualifiedApiName": n} for n in entities]), \
                mock.patch.object(gym.bs, "do_deployed", return_value=(True, "deployed")):
            self.assertTrue(gym.do_deployed("de", P)[0])

    def test_only_the_authorized_live_identity_is_accepted(self):
        with mock.patch.object(gym.sfc, "records", return_value=[IDENTITY]) as query:
            self.assertEqual(gym.identity("de"), IDENTITY)
        self.assertFalse(query.call_args.kwargs["tooling"])

    def test_alias_retarget_or_wrong_edition_refuses(self):
        for values in (dict(IDENTITY, Id="00D000000000000AAA"), dict(IDENTITY, OrganizationType="Enterprise Edition"), {}):
            with self.subTest(values=values), mock.patch.object(gym.sfc, "records", return_value=[values]):
                with self.assertRaises(gym.sfc.SfError):
                    gym.identity("de")

    def test_field_inventory_is_complete_or_refuses(self):
        with mock.patch.object(gym.sfc, "records", side_effect=gym.sfc.SfError("truncated")):
            with self.assertRaises(gym.sfc.SfError):
                gym.field_inventory("de")

    def test_qualified_names_are_not_guessed_from_developer_names(self):
        with mock.patch.object(gym.sfc, "records", return_value=[{"QualifiedApiName": P + "Member__c"}]) as query:
            self.assertEqual(gym.object_names("de", P), [P + "Member__c"])
        self.assertIn("QualifiedApiName", query.call_args.args[1])
        self.assertFalse(query.call_args.kwargs["tooling"])


class ValidationTest(unittest.TestCase):
    def doc(self):
        return {"status": 0, "result": {"success": True, "details": {"runTestResult": {
            "successes": [{"name": P + "OracleTest", "methodName": "ownsMember"},
                          {"name": P + "OracleTest", "methodName": "blocksAdmin"}], "failures": []}}}}

    def grade(self, doc):
        return gym.validation_verdict(doc, {"ownsMember", "blocksAdmin"}, P + "OracleTest")[0]

    def test_named_successes_pass(self):
        self.assertTrue(self.grade(self.doc()))

    def test_success_exit_without_test_evidence_stays_unknown(self):
        self.assertFalse(self.grade({"status": 0, "result": {"success": True}}))
        self.assertFalse(gym.validation_verdict(self.doc(), set(), P + "OracleTest")[0])

    def test_missing_or_wrong_class_method_cannot_pass(self):
        for field, value in (("name", "OtherTest"), ("methodName", "invented")):
            doc = self.doc()
            doc["result"]["details"]["runTestResult"]["successes"][0][field] = value
            self.assertFalse(self.grade(doc))

    def test_failures_override_success(self):
        doc = self.doc()
        doc["result"]["details"]["runTestResult"]["failures"] = [{"message": "assertion failed"}]
        self.assertFalse(self.grade(doc))

    def test_compile_or_deploy_failure_cannot_pass(self):
        doc = self.doc()
        doc["status"] = 1
        self.assertFalse(self.grade(doc))
        doc = self.doc()
        doc["result"]["success"] = False
        self.assertFalse(self.grade(doc))

    def test_rules_cannot_deploy_an_oracle_during_builder_work(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(gym, "identity"), \
                mock.patch.dict("os.environ", {"E2E_CHECK_PHASE": "builder"}), mock.patch.object(gym.sfc, "sf") as call:
            ok, message = gym.do_rules("de", P, Path(directory))
        self.assertFalse(ok)
        self.assertIn("UNKNOWN", message)
        call.assert_not_called()

    def test_oracle_fixture_declares_only_verification_code(self):
        fixture = gym.ORACLE
        source = (fixture / "force-app/main/default/classes/SLGymOracleTest.cls").read_text()
        self.assertEqual(len(list(fixture.rglob("*.cls"))), 1)
        self.assertIn("@IsTest", source)
        self.assertNotIn("SeeAllData", source)
        for method in ("foreignMemberAccessIsRefusedWithoutAVisit", "statusIsCheckedBeforeSameDayDeduplication",
                       "cancelledSelfCannotResumeEvenForAdmin"):
            self.assertIn(method, source)


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.before, self.base = baseline()
        self.write()

    def write(self):
        (self.directory / "before.json").write_text(json.dumps(self.before))

    def receipt(self):
        return json.loads((self.directory / "cleanup.json").read_text())

    def test_missing_snapshot_refuses_all_deletion(self):
        (self.directory / "before.json").unlink()
        with mock.patch.object(gym.sfc, "destructive_deploy") as delete:
            self.assertFalse(gym.do_cleanup("de", P, self.directory)[0])
        delete.assert_not_called()

    def test_snapshot_scope_and_identity_must_match_before_deletion(self):
        for mutate in (lambda b: b.update(prefix="Other"), lambda b: b.update(existing="update"),
                       lambda b: b["gym"].update(object_api_names=[P + "Member__c"]),
                       lambda b: b["other_types"]["CustomObject"].append(P + "Member"),
                       lambda b: b["gym"].pop("fields")):
            self.before, _ = baseline()
            mutate(self.before)
            self.write()
            with mock.patch.object(gym, "identity", return_value=IDENTITY), \
                    mock.patch.object(gym.sfc, "destructive_deploy") as delete:
                self.assertFalse(gym.do_cleanup("de", P, self.directory)[0])
            delete.assert_not_called()

    def test_live_alias_change_refuses_without_inventory_or_delete(self):
        with mock.patch.object(gym, "identity", return_value=dict(IDENTITY, Id="different")), \
                mock.patch.object(gym.sfc, "read_org") as read, mock.patch.object(gym.sfc, "destructive_deploy") as delete:
            self.assertFalse(gym.do_cleanup("de", P, self.directory)[0])
        read.assert_not_called()
        delete.assert_not_called()

    def perform(self, *, fields=None, final=None, schema=None):
        current = copy.deepcopy(self.base)
        current["names"]["ApexClass"] += [P + "Controller"]
        current["dates"]["ApexClass"][P + "Controller"] = "new"
        current["names"]["LightningComponentBundle"] += ["slGymApp"]
        current["dates"]["LightningComponentBundle"]["slGymApp"] = "new"
        for kind, name in (("PermissionSet", P + "_Access"), ("CustomApplication", P),
                           ("CustomTab", P + "_Members"), ("CustomObject", P + "Member"), ("CustomObject", P + "Visit")):
            current["names"][kind].append(name)
        final = copy.deepcopy(final if final is not None else self.base)
        with mock.patch.object(gym, "identity", return_value=IDENTITY), \
                mock.patch.object(gym.sfc, "read_org", side_effect=[current, final]), \
                mock.patch.object(gym, "object_names", side_effect=[
                    schema if schema is not None else [P + "Member__c", P + "Visit__c"], []]), \
                mock.patch.object(gym, "field_inventory", return_value=fields if fields is not None else self.before["gym"]["fields"]), \
                mock.patch.object(gym.sfc, "query", return_value=["a00000000000001AAA"]), \
                mock.patch.object(gym.bs, "unassign", return_value=1) as unassign, \
                mock.patch.object(gym.sfc, "destructive_deploy", return_value="") as deploy:
            ok, message = gym.do_cleanup("de", P, self.directory)
        return ok, message, deploy, unassign

    def test_removal_is_owned_ordered_and_schema_only_is_purged(self):
        ok, _, deploy, unassign = self.perform()
        self.assertTrue(ok)
        calls = deploy.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0].args[1], {"PermissionSet": [P + "_Access"]})
        self.assertEqual(calls[1].args[1]["ApexClass"], [P + "Controller"])
        self.assertEqual(calls[2].args[1], {"CustomObject": [P + "Visit__c", P + "Member__c"]})
        self.assertEqual([c.kwargs["purge"] for c in calls], [False, False, True])
        self.assertEqual(unassign.call_args.args[:2], ("de", P + "_Access"))
        self.assertTrue(self.receipt()["verified"])
        self.assertEqual(self.receipt()["records_before"][P + "Member__c"]["count"], 1)

    def test_field_addition_on_baseline_object_is_not_a_clean_reset(self):
        fields = self.before["gym"]["fields"] + [["Account", "UnexpectedField"]]
        ok, _, _, _ = self.perform(fields=fields)
        self.assertFalse(ok)
        self.assertEqual(self.receipt()["fields"]["extra"], [["Account", "UnexpectedField"]])

    def test_baseline_metadata_modification_cannot_be_overridden(self):
        final = copy.deepcopy(self.base)
        final["dates"]["ApexClass"]["OtherClass"] = "changed"
        self.assertFalse(self.perform(final=final)[0])

    def test_foreign_new_metadata_is_preserved_and_not_deleted(self):
        final = copy.deepcopy(self.base)
        final["names"]["CustomApplication"].append("OtherNewApp")
        ok, _, deploy, _ = self.perform(final=final)
        self.assertTrue(ok)
        self.assertNotIn("OtherNewApp", str(deploy.call_args_list))
        self.assertEqual(self.receipt()["foreign_extra"], {"CustomApplication": ["OtherNewApp"]})

    def test_unsupported_owned_schema_fails_and_is_never_purged(self):
        ok, _, deploy, _ = self.perform(schema=[P + "Member__c", P + "Secret__mdt"])
        self.assertFalse(ok)
        self.assertNotIn(P + "Secret__mdt", str(deploy.call_args_list))

    def test_generated_entities_are_removed_with_their_base_objects(self):
        entities = [P + suffix for suffix in ("Member__c", "Member__Share", "Member__ChangeEvent",
                                               "Visit__c", "Visit__ChangeEvent")]
        ok, _, deploy, _ = self.perform(schema=entities)
        self.assertTrue(ok)
        self.assertEqual(self.receipt()["refused"], [])
        self.assertNotIn("__Share", str(deploy.call_args_list))
        self.assertNotIn("__ChangeEvent", str(deploy.call_args_list))


class CatalogTest(unittest.TestCase):
    def test_opt_in_case_invokes_subject_and_requires_browser_and_cleanup(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/cases.json").read_text())
        case = cases["gym-membership-salesforce"]
        self.assertIn("Use ShipLoop", case["prompt"])
        self.assertEqual(case["needs"], ["browser"])
        self.assertIn("--custom-objects", case["platform"]["model_bin"]["sf"])
        self.assertNotIn("existing", case["platform"])
        self.assertIn("cleanup", case["platform"])
        self.assertEqual(len(case["checks"]), 6)


if __name__ == "__main__":
    unittest.main()

