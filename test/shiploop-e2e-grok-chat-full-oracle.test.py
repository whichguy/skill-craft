#!/usr/bin/env python3
"""Hermetic contract and safety tests for the full Grok chat check-only Apex oracle."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "test/shiploop_e2e/checks/grok_chat_full_salesforce.py"
spec = importlib.util.spec_from_file_location("grok_chat_full_salesforce_tested", ADAPTER)
grok = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grok)

PREFIX = grok.PREFIX
ORG_IDENTITY = {
    "Id": grok.EXPECTED_ORG_ID,
    "OrganizationType": "Developer Edition",
    "IsSandbox": False,
}


def put(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def controller_source(prefix: str = PREFIX) -> str:
    lines = [f"public with sharing class {prefix}Controller {{"]
    for name, params in grok.INTERFACE.items():
        arguments = ", ".join(params)
        lines.append(f"    @AuraEnabled public static String {name}({arguments}) {{ return '{{}}'; }}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def add_object(root: Path, name: str, *, name_type: str = "Text") -> Path:
    folder = f"force-app/main/default/objects/{name}"
    put(
        root,
        f"{folder}/{name}.object-meta.xml",
        f"<CustomObject><nameField><type>{name_type}</type></nameField><sharingModel>Private</sharingModel></CustomObject>",
    )
    (root / folder / "fields").mkdir(parents=True, exist_ok=True)
    return root / folder


def add_field(root: Path, obj: str, name: str, kind: str, extra: str = "") -> Path:
    return put(
        root,
        f"force-app/main/default/objects/{obj}/fields/{name}.field-meta.xml",
        f"<CustomField><fullName>{name}</fullName><type>{kind}</type>{extra}</CustomField>",
    )


def minimal_project(root: Path, *, prefix: str = PREFIX) -> None:
    put(root, "sfdx-project.json", json.dumps({
        "packageDirectories": [{"path": "force-app", "default": True}],
        "sourceApiVersion": "60.0",
    }))
    put(root, f"force-app/main/default/classes/{prefix}Controller.cls", controller_source(prefix))
    item = prefix + "Item__c"
    config = prefix + "Config__c"
    add_object(root, item)
    add_field(
        root,
        item,
        "Status__c",
        "Picklist",
        '<valueSet><restricted>true</restricted><valueSetDefinition>'
        '<value><fullName>Open</fullName></value><value><fullName>Done</fullName></value>'
        '</valueSetDefinition></valueSet>',
    )
    add_field(root, item, "Notes__c", "TextArea")
    add_object(root, config)
    add_field(root, config, "NamedCredential__c", "Text")
    add_field(root, config, "Model__c", "Text")


def validation_doc(methods=None):
    methods = sorted(methods or grok.REQUIRED_METHODS)
    successes = [{"name": grok.ORACLE_CLASS, "methodName": name} for name in methods]
    count = len(successes)
    return {
        "status": 0,
        "result": {
            "success": True,
            "details": {
                "runTestResult": {
                    "numTestsRun": count,
                    "numFailures": 0,
                    "successes": successes,
                    "failures": [],
                }
            },
        },
    }


class HermeticTest(unittest.TestCase):
    def setUp(self):
        self.no_cli = mock.patch.object(
            grok.sfc, "sf", side_effect=AssertionError("real Salesforce CLI is forbidden in hermetic tests")
        )
        self.no_cli.start()
        self.addCleanup(self.no_cli.stop)

    def evaluate(self, mutate=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            minimal_project(root)
            if mutate:
                mutate(root)
            return grok.do_project(root=root)


class SourceContractTest(HermeticTest):
    def test_minimal_source_satisfies_public_json_string_interface_and_fields(self):
        ok, message = self.evaluate()
        self.assertTrue(ok, message)
        self.assertIn("controller_sha256=", message)
        self.assertIn("candidate_sha256=", message)

    def test_declared_parameters_are_exact_and_no_authority_flag_is_accepted(self):
        def add_authority_argument(root):
            path = root / "force-app/main/default/classes/SLGrokChatController.cls"
            path.write_text(
                path.read_text().replace(
                    "saveSetup(String namedCredential, String model)",
                    "saveSetup(String namedCredential, String model, Boolean isAdmin)",
                ),
                encoding="utf-8",
            )
        self.assertFalse(self.evaluate(add_authority_argument)[0])

    def test_comment_text_cannot_supply_a_missing_public_method(self):
        def comment_out_method(root):
            path = root / "force-app/main/default/classes/SLGrokChatController.cls"
            source = path.read_text()
            source = source.replace(
                "    @AuraEnabled public static String getSetup() { return '{}'; }\n",
                "    // @AuraEnabled public static String getSetup() { return '{}'; }\n",
            )
            path.write_text(source, encoding="utf-8")
        ok, message = self.evaluate(comment_out_method)
        self.assertFalse(ok)
        self.assertIn("getSetup", message)

    def test_contract_checks_do_not_require_comment_keywords(self):
        ok, message = self.evaluate()
        self.assertTrue(ok, message)

    def test_required_config_and_item_fields_and_types_are_enforced(self):
        mutations = (
            ("missing config field", lambda r: (r / f"force-app/main/default/objects/{PREFIX}Config__c/fields/Model__c.field-meta.xml").unlink()),
            ("wrong model type", lambda r: add_field(r, PREFIX + "Config__c", "Model__c", "Checkbox")),
            ("missing notes", lambda r: (r / f"force-app/main/default/objects/{PREFIX}Item__c/fields/Notes__c.field-meta.xml").unlink()),
            ("wrong status values", lambda r: add_field(
                r, PREFIX + "Item__c", "Status__c", "Picklist",
                '<valueSet><restricted>false</restricted><valueSetDefinition>'
                '<value><fullName>Open</fullName></value><value><fullName>Working</fullName></value>'
                '</valueSetDefinition></valueSet>')),
            ("auto number name", lambda r: add_object(r, PREFIX + "Item__c", name_type="AutoNumber")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                self.assertFalse(self.evaluate(mutate)[0])

    def test_only_force_app_is_a_deployable_package_root(self):
        def add_second_package(root):
            project = json.loads((root / "sfdx-project.json").read_text())
            project["packageDirectories"].append({"path": "extra", "default": False})
            (root / "sfdx-project.json").write_text(json.dumps(project))
        ok, message = self.evaluate(add_second_package)
        self.assertFalse(ok)
        self.assertIn("only the force-app package directory", message)

    def test_product_cannot_include_reserved_oracle_class_or_fault_rule(self):
        def class_collision(root):
            put(root, f"force-app/main/default/classes/{PREFIX}OracleTest.cls",
                "private class " + PREFIX + "OracleTest {}")

        def rule_collision(root):
            put(root,
                f"force-app/main/default/objects/{PREFIX}Item__c/validationRules/"
                f"{PREFIX}OracleDmlFault.validationRule-meta.xml",
                "<ValidationRule/>")

        self.assertFalse(self.evaluate(class_collision)[0])
        self.assertFalse(self.evaluate(rule_collision)[0])

    def test_comment_only_reserved_class_name_is_not_treated_as_app_code(self):
        ok, message = self.evaluate(lambda r: put(
            r, f"force-app/main/default/classes/{PREFIX}Other.cls",
            "/* private class " + PREFIX + "OracleTest {} */ public class " + PREFIX + "Other {}",
        ))
        self.assertTrue(ok, message)


class FixtureContractTest(HermeticTest):
    def test_named_required_apex_methods_are_present(self):
        source = grok.ORACLE_CLASS_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(grok.oracle_method_names(source), set(grok.REQUIRED_METHODS))
        self.assertEqual(len(grok.REQUIRED_METHODS), 25)
        self.assertEqual(grok.fixture_problems(), [])

    def test_fixture_contains_only_check_only_class_and_dml_fault_rule(self):
        class_files = list(grok.ORACLE.glob("force-app/**/classes/*.cls"))
        rule_files = list(grok.ORACLE.glob("force-app/**/validationRules/*.validationRule-meta.xml"))
        self.assertEqual(class_files, [grok.ORACLE_CLASS_SOURCE])
        self.assertEqual(rule_files, [grok.ORACLE_RULE_SOURCE])
        actual_files = {path for path in (grok.ORACLE / "force-app").rglob("*") if path.is_file()}
        self.assertEqual(actual_files, {
            grok.ORACLE_CLASS_SOURCE,
            grok.ORACLE_CLASS_META,
            grok.ORACLE_RULE_SOURCE,
        })
        self.assertIn('BEGINS(Name, "E2E-OracleDmlFailure-")',
                      grok.ORACLE_RULE_SOURCE.read_text(encoding="utf-8"))
        self.assertFalse((grok.ORACLE / "force-app/main/default/classes/SLGrokChatController.cls").exists())

    def test_compiler_regressions_keep_long_text_out_of_soql_filters_and_json_type_unshadowed(self):
        source = grok.ORACLE_CLASS_SOURCE.read_text(encoding="utf-8")
        self.assertIn("asMap(String jsonText)", source)
        self.assertIn("System.JSON.deserializeUntyped(jsonText)", source)
        self.assertNotIn("JSON.deserializeUntyped(json)", source)
        masked = grok._mask_apex(source)
        queries = re.findall(r"\[\s*SELECT\b(.*?)\]", masked, re.IGNORECASE | re.DOTALL)
        self.assertTrue(queries)
        for query in queries:
            where = re.search(r"\bWHERE\b(.*)", query, re.IGNORECASE | re.DOTALL)
            if where:
                self.assertNotRegex(where.group(1), r"\bNotes__c\b")


class ValidationVerdictTest(HermeticTest):
    def test_all_named_methods_and_explicit_zero_counts_pass(self):
        ok, message = grok.validation_verdict(validation_doc(), set(grok.REQUIRED_METHODS))
        self.assertTrue(ok, message)
        self.assertIn("25/25 named methods", message)

    def test_missing_or_wrong_method_cannot_pass(self):
        for mutation in (
            lambda doc: doc["result"]["details"]["runTestResult"]["successes"].pop(),
            lambda doc: doc["result"]["details"]["runTestResult"]["successes"][0].update(name="OtherTest"),
            lambda doc: doc["result"]["details"]["runTestResult"]["successes"][0].update(methodName="invented"),
        ):
            with self.subTest(mutation=mutation):
                doc = validation_doc()
                mutation(doc)
                self.assertFalse(grok.validation_verdict(doc, set(grok.REQUIRED_METHODS))[0])

    def test_missing_counts_arrays_or_run_result_stay_unknown(self):
        cases = []
        missing_run = validation_doc()
        missing_run["result"]["details"].pop("runTestResult")
        cases.append(missing_run)
        missing_tests = validation_doc()
        missing_tests["result"]["details"]["runTestResult"].pop("numTestsRun")
        cases.append(missing_tests)
        missing_failures = validation_doc()
        missing_failures["result"]["details"]["runTestResult"].pop("numFailures")
        cases.append(missing_failures)
        missing_successes = validation_doc()
        missing_successes["result"]["details"]["runTestResult"].pop("successes")
        cases.append(missing_successes)
        missing_failures_array = validation_doc()
        missing_failures_array["result"]["details"]["runTestResult"].pop("failures")
        cases.append(missing_failures_array)
        wrong_count = validation_doc()
        wrong_count["result"]["details"]["runTestResult"]["numTestsRun"] -= 1
        cases.append(wrong_count)
        for doc in cases:
            with self.subTest(doc=doc):
                self.assertFalse(grok.validation_verdict(doc, set(grok.REQUIRED_METHODS))[0])

    def test_nonzero_failures_or_wrong_envelope_cannot_pass(self):
        mutations = []
        failed_method = validation_doc()
        run = failed_method["result"]["details"]["runTestResult"]
        run["numFailures"] = 1
        run["failures"] = [{"name": grok.ORACLE_CLASS, "methodName": "failed"}]
        run["numTestsRun"] += 1
        mutations.append(failed_method)
        failed_exit = validation_doc()
        failed_exit["status"] = 1
        mutations.append(failed_exit)
        failed_result = validation_doc()
        failed_result["result"]["success"] = False
        mutations.append(failed_result)
        for doc in mutations:
            with self.subTest(doc=doc):
                self.assertFalse(grok.validation_verdict(doc, set(grok.REQUIRED_METHODS))[0])


class RulesAdapterTest(HermeticTest):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "candidate"
        self.output = Path(self.tmp.name) / "platform"
        self.root.mkdir()
        self.output.mkdir()
        minimal_project(self.root)
        self.apex_sources = grok.prefix_apex_sha256(self.root)
        self.controller_sha = self.apex_sources[grok.CONTROLLER]

    def call_rules(self, **patches):
        identity = patches.pop("identity", ORG_IDENTITY)
        reserved = patches.pop("reserved", {"class": False, "rule": False})
        remote = patches.pop("remote", self.apex_sources)
        doc = patches.pop("doc", validation_doc())
        deploy_effect = patches.pop("deploy_effect", None)
        with mock.patch.dict("os.environ", {"E2E_CHECK_PHASE": "final"}), \
                mock.patch.object(grok.gym, "identity", side_effect=identity if isinstance(identity, list) else None,
                                  return_value=None if isinstance(identity, list) else identity) as ident, \
                mock.patch.object(grok, "reserved_components",
                                  side_effect=reserved if isinstance(reserved, list) else None,
                                  return_value=None if isinstance(reserved, list) else reserved) as components, \
                mock.patch.object(grok, "deployed_prefix_apex_sha256",
                                  side_effect=remote if isinstance(remote, list) else None,
                                  return_value=None if isinstance(remote, list) else remote) as deployed, \
                mock.patch.object(grok.sfc, "sf", return_value=doc, side_effect=deploy_effect) as deploy:
            ok, message = grok.do_rules(self.output, self.root)
        return ok, message, ident, components, deployed, deploy

    def test_phase_refuses_unknown_and_product_at_stop_before_any_org_call(self):
        for phase in ("", "unknown", "product_at_stop"):
            with self.subTest(phase=phase), mock.patch.dict("os.environ", {"E2E_CHECK_PHASE": phase}), \
                    mock.patch.object(grok.gym, "identity") as identity, \
                    mock.patch.object(grok.sfc, "sf") as deploy:
                ok, message = grok.do_rules(self.output, self.root)
            self.assertFalse(ok)
            self.assertIn("UNKNOWN", message)
            identity.assert_not_called()
            deploy.assert_not_called()

    def test_only_builder_and_final_phases_are_accepted(self):
        for phase in ("builder", "final"):
            with self.subTest(phase=phase), mock.patch.dict("os.environ", {"E2E_CHECK_PHASE": phase}), \
                    mock.patch.object(grok.gym, "identity", return_value=ORG_IDENTITY), \
                    mock.patch.object(grok, "reserved_components", return_value={"class": False, "rule": False}), \
                    mock.patch.object(grok, "deployed_prefix_apex_sha256", return_value=self.apex_sources), \
                    mock.patch.object(grok.sfc, "sf", return_value=validation_doc()) as deploy:
                ok, message = grok.do_rules(self.output, self.root)
            self.assertTrue(ok, message)
            deploy.assert_called_once()

    def test_org_mismatch_and_preexisting_reserved_names_refuse_before_validation(self):
        wrong_org = dict(ORG_IDENTITY, Id="00D000000000000AAA")
        cases = (
            ({"identity": wrong_org}, "identity/type mismatch"),
            ({"reserved": {"class": True, "rule": False}}, "collision"),
            ({"reserved": {"class": False, "rule": True}}, "collision"),
        )
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                ok, message, _, _, _, deploy = self.call_rules(**kwargs)
                self.assertFalse(ok)
                self.assertIn(expected, message)
                deploy.assert_not_called()

    def test_deployed_controller_must_match_candidate_before_validation(self):
        ok, message, _, _, _, deploy = self.call_rules(remote={grok.CONTROLLER: "not-the-candidate"})
        self.assertFalse(ok)
        self.assertIn("does not exactly match the candidate", message)
        deploy.assert_not_called()

    def test_every_prefix_helper_body_and_the_exact_class_set_are_bound(self):
        helper = put(
            self.root,
            f"force-app/main/default/classes/{PREFIX}Service.cls",
            f"public with sharing class {PREFIX}Service {{ public static String helper() {{ return 'source'; }} }}",
        )
        candidate = grok.prefix_apex_sha256(self.root)
        self.assertIn(PREFIX + "Service", candidate)
        for remote in (
            {grok.CONTROLLER: candidate[grok.CONTROLLER]},
            dict(candidate, **{PREFIX + "Service": "stale-helper-body"}),
        ):
            with self.subTest(remote=remote):
                ok, message, _, _, _, deploy = self.call_rules(remote=remote)
                self.assertFalse(ok)
                self.assertIn("deployed prefix Apex source does not exactly match", message)
                deploy.assert_not_called()
        helper.unlink()

    def test_check_only_command_is_pinned_bounded_and_scope_limited(self):
        submitted = {}

        def inspect_validation_input(args, org, **kwargs):
            source_dir = Path(args[args.index("--source-dir") + 1])
            # Observe the actual submitted tree while it exists; the adapter
            # deliberately removes its temporary source when validation returns.
            submitted["classes"] = [p.relative_to(source_dir).as_posix()
                                    for p in source_dir.rglob("*.cls")]
            submitted["rules"] = [p.relative_to(source_dir).as_posix()
                                  for p in source_dir.rglob("*.validationRule-meta.xml")]
            return validation_doc()

        ok, message, _, _, _, deploy = self.call_rules(deploy_effect=inspect_validation_input)
        self.assertTrue(ok, message)
        args = deploy.call_args.args[0]
        self.assertEqual(args[:3], ["project", "deploy", "validate"])
        self.assertIn("--test-level", args)
        self.assertEqual(args[args.index("--test-level") + 1], "RunSpecifiedTests")
        self.assertEqual(args[args.index("--tests") + 1], grok.ORACLE_CLASS)
        self.assertEqual(args[args.index("--wait") + 1], "10")
        self.assertEqual(deploy.call_args.args[1], "de")
        self.assertEqual(deploy.call_args.kwargs["timeout"], 900)
        source_dir = Path(args[args.index("--source-dir") + 1])
        self.assertEqual(
            submitted["classes"],
            ["main/default/classes/" + grok.ORACLE_CLASS + ".cls"],
        )
        self.assertEqual(
            submitted["rules"],
            ["main/default/objects/" + grok.ITEM_OBJECT + "/validationRules/" +
             grok.ORACLE_RULE + ".validationRule-meta.xml"],
        )
        self.assertFalse(source_dir.exists(), "temporary validation source must be cleaned")

    def test_incomplete_validation_result_never_passes(self):
        incomplete = {
            "status": 0,
            "result": {"success": True, "details": {"runTestResult": {"successes": [], "failures": []}}},
        }
        ok, message, _, _, _, _ = self.call_rules(doc=incomplete)
        self.assertFalse(ok)
        self.assertIn("FAIL/UNKNOWN", message)

    def test_post_validation_target_or_source_mismatch_fails(self):
        wrong_identity = [ORG_IDENTITY, dict(ORG_IDENTITY, Id="00D000000000000AAA")]
        ok, message, _, _, _, _ = self.call_rules(identity=wrong_identity)
        self.assertFalse(ok)
        self.assertIn("identity changed", message)

        ok, message, _, _, _, _ = self.call_rules(remote=[self.apex_sources, {grok.CONTROLLER: "changed-controller"}])
        self.assertFalse(ok)
        self.assertIn("no longer matches candidate source", message)

    def test_persisted_oracle_class_or_rule_fails_and_is_recorded(self):
        cases = (
            [{"class": False, "rule": False}, {"class": True, "rule": False}],
            [{"class": False, "rule": False}, {"class": False, "rule": True}],
        )
        for reserved in cases:
            with self.subTest(reserved=reserved):
                ok, message, _, _, _, _ = self.call_rules(reserved=reserved)
                self.assertFalse(ok)
                self.assertIn("persisted", message)
                receipts = list((self.output / "grok-chat-full-oracle").rglob("receipt.json"))
                self.assertTrue(receipts)
                receipt = json.loads(receipts[-1].read_text())
                self.assertFalse(receipt["complete"])
                self.assertTrue(receipt["check_only"])
                self.assertTrue(any(receipt["reserved_after"].values()))
                shutil.rmtree(self.output / "grok-chat-full-oracle")

    def test_cli_does_not_allow_org_or_prefix_override(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                grok.main(["rules", "--org", "other"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

