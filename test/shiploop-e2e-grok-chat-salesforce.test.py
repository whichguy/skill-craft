#!/usr/bin/env python3
"""Hermetic source/inventory checks for the exploratory Grok chat case."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "test/shiploop_e2e/checks/grok_chat_salesforce.py"
spec = importlib.util.spec_from_file_location("grok_chat_salesforce_tested", ADAPTER)
grok = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grok)

PREFIX = "SLGrokChat"
ITEM = PREFIX + "Item__c"
THREAD = PREFIX + "Thread__c"
MESSAGE = PREFIX + "Message__c"
CONFIG = PREFIX + "Config__c"
LWC = "slGrokChatApp"
OPTIONAL = ("Action", "Config", "Message", "Thread")


def put(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def add_object(root: Path, name: str) -> Path:
    folder = f"force-app/main/default/objects/{name}"
    put(root, f"{folder}/{name}.object-meta.xml",
        "<CustomObject><nameField><type>Text</type></nameField><sharingModel>Private</sharingModel></CustomObject>")
    (root / folder / "fields").mkdir(parents=True, exist_ok=True)
    return root / folder


def add_field(root: Path, obj: str, name: str, kind: str, extra: str = "") -> Path:
    return put(root, f"force-app/main/default/objects/{obj}/fields/{name}.field-meta.xml",
               f"<CustomField><fullName>{name}</fullName><type>{kind}</type>{extra}</CustomField>")


def write_permission_set(root: Path, *, extra_objects=(), omit_objects=(), object_overrides=None,
                         field_overrides=None, credential_access=False, user_permission=False):
    object_overrides = object_overrides or {}
    field_overrides = field_overrides or {}
    object_dir = root / "force-app/main/default/objects"
    objects = {p.name for p in object_dir.iterdir() if p.is_dir()} | set(extra_objects)
    grants = []
    for name in sorted(objects - set(omit_objects)):
        values = {"allowRead": "true", "allowCreate": "false" if name == CONFIG else "true",
                  "allowEdit": "false" if name == CONFIG else "true", "allowDelete": "false",
                  "modifyAllRecords": "false", "viewAllRecords": "false", "viewAllFields": "false"}
        values.update(object_overrides.get(name, {}))
        fields = "".join(f"<{key}>{value}</{key}>" for key, value in values.items())
        grants.append(f"<objectPermissions><object>{name}</object>{fields}</objectPermissions>")
    field_grants = []
    for path in sorted(object_dir.glob("*/fields/*.field-meta.xml")):
        obj, field = path.parents[1].name, path.name.removesuffix(".field-meta.xml")
        if obj == CONFIG:
            editable = "false"
        else:
            editable = "true"
        values = {"readable": "true", "editable": editable}
        values.update(field_overrides.get(obj + "." + field, {}))
        fields = "".join(f"<{key}>{value}</{key}>" for key, value in values.items())
        field_grants.append(f"<fieldPermissions><field>{obj}.{field}</field>{fields}</fieldPermissions>")
    credentials = ("<externalCredentialPrincipalAccesses><externalCredentialPrincipalAccess>"
                   "<enabled>true</enabled><externalCredentialPrincipal>Grok-Principal</externalCredentialPrincipal>"
                   "</externalCredentialPrincipalAccess></externalCredentialPrincipalAccesses>"
                   if credential_access else "")
    users = ("<userPermissions><userPermission><enabled>true</enabled><name>AuthorApex</name>"
             "</userPermission></userPermissions>" if user_permission else "")
    return put(root, f"force-app/main/default/permissionsets/{PREFIX}_Access.permissionset-meta.xml",
               "<PermissionSet>" + "".join(grants) + "".join(field_grants) +
               f"<classAccesses><apexClass>{PREFIX}Controller</apexClass><enabled>true</enabled></classAccesses>"
               + credentials + users + "</PermissionSet>")


def minimal_project(root: Path, prefix: str = PREFIX) -> None:
    """Build only the adapter's declared source shape, not a functioning chat app."""
    put(root, "sfdx-project.json",
        json.dumps({"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": "60.0"}))
    app = "force-app/main/default"
    component = grok.gym.sfc.lwc_prefix(prefix) + "App"
    put(root, f"{app}/classes/{prefix}Controller.cls",
        f"public with sharing class {prefix}Controller {{ @AuraEnabled public static String ping() {{ return 'stub'; }} }}")
    put(root, f"{app}/lwc/{component}/{component}.js",
        "import { LightningElement } from 'lwc'; export default class Stub extends LightningElement {}")
    put(root, f"{app}/lwc/{component}/{component}.html", "<template><div>Setup</div></template>")
    put(root, f"{app}/lwc/{component}/{component}.js-meta.xml",
        "<LightningComponentBundle><targets><target>lightning__Tab</target></targets></LightningComponentBundle>")
    put(root, f"{app}/tabs/{prefix}_Chat.tab-meta.xml",
        f"<LightningComponentTab><lwcComponent>{component}</lwcComponent></LightningComponentTab>")
    put(root, f"{app}/applications/{prefix}.app-meta.xml",
        f"<CustomApplication><tabs>{prefix}_Chat</tabs></CustomApplication>")

    add_object(root, prefix + "Item__c")
    add_field(root, prefix + "Item__c", "Status__c", "Picklist", """
        <valueSet><restricted>true</restricted><valueSetDefinition>
          <value><fullName>Open</fullName></value><value><fullName>Done</fullName></value>
        </valueSetDefinition></valueSet>""")
    add_field(root, prefix + "Item__c", "Notes__c", "TextArea")
    write_permission_set(root)


def add_optional_objects(root: Path, prefix: str = PREFIX) -> None:
    thread, message = prefix + "Thread__c", prefix + "Message__c"
    add_object(root, thread)
    add_object(root, message)
    add_field(root, message, "Thread__c", "Lookup", f"<referenceTo>{thread}</referenceTo>")
    write_permission_set(root)


class HermeticTest(unittest.TestCase):
    def setUp(self):
        # Accidental org operations fail here instead of reaching a local Salesforce CLI.
        self.cli = mock.patch.object(grok.sfc, "sf", side_effect=AssertionError("real Salesforce CLI is forbidden"))
        self.sf = self.cli.start()
        self.addCleanup(self.cli.stop)

    def evaluate_source(self, mutate=None, *, prefix: str = PREFIX):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            minimal_project(root, prefix)
            if mutate:
                mutate(root, prefix)
            return grok.do_project(prefix, root)


class SourceContractTest(HermeticTest):
    def test_minimal_source_passes_as_smoke_only(self):
        ok, message = self.evaluate_source()
        self.assertTrue(ok, message)
        self.assertIn("unverified", message.lower())
        self.assertNotRegex(message.lower(), r"runtime[^.]{0,30}(?:verified|passed|working)")

    def test_optional_message_to_thread_relationship_and_read_only_config_are_in_scope(self):
        def add_valid_internal_schema(root, prefix):
            add_optional_objects(root, prefix)
            config = prefix + "Config__c"
            add_object(root, config)
            add_field(root, config, "Model__c", "Text")
            write_permission_set(root)
        ok, message = self.evaluate_source(add_valid_internal_schema)
        self.assertTrue(ok, message)

    def test_missing_or_miswired_tab_component_and_required_item_fail(self):
        mutations = (
            ("tab", lambda r, p: (r / f"force-app/main/default/tabs/{p}_Chat.tab-meta.xml").unlink()),
            ("tab binding", lambda r, p: put(r, f"force-app/main/default/tabs/{p}_Chat.tab-meta.xml",
                                             "<LightningComponentTab><lwcComponent>unrelatedApp</lwcComponent></LightningComponentTab>")),
            ("component", lambda r, p: (r / f"force-app/main/default/lwc/{grok.gym.sfc.lwc_prefix(p)}App/"
                                             f"{grok.gym.sfc.lwc_prefix(p)}App.html").unlink()),
            ("item object", lambda r, p: shutil.rmtree(r / f"force-app/main/default/objects/{p}Item__c")),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                self.assertFalse(self.evaluate_source(mutate)[0])

    def test_foreign_metadata_relationship_and_custom_settings_fail(self):
        cases = (
            ("foreign object", lambda r, p: add_object(r, "Account")),
            ("custom metadata", lambda r, p: put(
                r, f"force-app/main/default/objects/{p}Policy__mdt/{p}Policy__mdt.object-meta.xml",
                "<CustomObject><sharingModel>Private</sharingModel></CustomObject>")),
            ("Named Credential", lambda r, p: put(
                r, f"force-app/main/default/namedCredentials/{p}_Grok.namedCredential-meta.xml",
                "<NamedCredential><label>Grok</label></NamedCredential>")),
            ("foreign relationship", lambda r, p: add_field(
                r, p + "Item__c", "Foreign__c", "Lookup", "<referenceTo>Account</referenceTo>")),
            ("custom settings", lambda r, p: put(
                r, f"force-app/main/default/objects/{p}Item__c/{p}Item__c.object-meta.xml",
                "<CustomObject><customSettingsType>List</customSettingsType><nameField><type>Text</type></nameField>"
                "<sharingModel>Private</sharingModel></CustomObject>")),
            ("thread self reference", lambda r, p: (
                add_object(r, p + "Thread__c"),
                add_field(r, p + "Thread__c", "ParentThread__c", "Lookup", f"<referenceTo>{p}Thread__c</referenceTo>"),
                write_permission_set(r))),
        )
        for label, mutate in cases:
            with self.subTest(label=label):
                self.assertFalse(self.evaluate_source(mutate)[0])

    def test_picklist_and_required_object_or_field_grants_are_checked(self):
        def bad_picklist(root, prefix):
            path = root / f"force-app/main/default/objects/{prefix}Item__c/fields/Status__c.field-meta.xml"
            path.write_text("<CustomField><fullName>Status__c</fullName><type>Picklist</type>"
                            "<valueSet><restricted>false</restricted><valueSetDefinition>"
                            "<value><fullName>Open</fullName></value><value><fullName>Closed</fullName></value>"
                            "</valueSetDefinition></valueSet></CustomField>")
        def missing_item_grant(root, _prefix):
            write_permission_set(root, omit_objects=(ITEM,))
        def missing_notes_grant(root, _prefix):
            path = root / f"force-app/main/default/permissionsets/{PREFIX}_Access.permissionset-meta.xml"
            path.write_text(path.read_text().replace(
                f"<fieldPermissions><field>{ITEM}.Notes__c</field><readable>true</readable><editable>true</editable></fieldPermissions>", ""))
        for label, mutate in (("bad picklist", bad_picklist), ("missing CRUD grant", missing_item_grant),
                              ("missing FLS grant", missing_notes_grant)):
            with self.subTest(label=label):
                self.assertFalse(self.evaluate_source(mutate)[0])

    def test_broad_permissions_and_config_writes_fail(self):
        broad = ("allowDelete", "modifyAllRecords", "viewAllRecords", "viewAllFields")
        for flag in broad:
            with self.subTest(flag=flag):
                def mutate(root, _prefix, flag=flag):
                    write_permission_set(root, object_overrides={ITEM: {flag: "true"}})
                self.assertFalse(self.evaluate_source(mutate)[0])

        def config_create(root, prefix):
            add_object(root, prefix + "Config__c")
            add_field(root, prefix + "Config__c", "Model__c", "Text")
            write_permission_set(root, object_overrides={prefix + "Config__c": {"allowCreate": "true"}})
        def config_field_edit(root, prefix):
            add_object(root, prefix + "Config__c")
            add_field(root, prefix + "Config__c", "Model__c", "Text")
            write_permission_set(root, field_overrides={prefix + "Config__c.Model__c": {"editable": "true"}})
        for label, mutate in (("credential principal", lambda r, _p: write_permission_set(r, credential_access=True)),
                              ("system permission", lambda r, _p: write_permission_set(r, user_permission=True)),
                              ("Config create", config_create), ("Config field edit", config_field_edit)):
            with self.subTest(label=label):
                self.assertFalse(self.evaluate_source(mutate)[0])


class AdapterDispatchTest(HermeticTest):
    def invoke(self, *argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = grok.main(list(argv))
        return status, output.getvalue()

    def test_prefix_override_and_subject_test_count_are_forwarded(self):
        with mock.patch.object(grok, "do_project", return_value=(True, "smoke only")) as project:
            status, _ = self.invoke("project", "--prefix", "SLAlt")
        self.assertEqual(status, 0)
        project.assert_called_once_with("SLAlt")

        with mock.patch.object(grok.gym, "identity") as identity, \
                mock.patch.object(grok.sfc, "do_tests", return_value=(True, ["PASS: 12 tests"])) as tests:
            status, _ = self.invoke("tests", "--org", "fake-org", "--prefix", "SLAlt", "--min-tests", "12")
        self.assertEqual(status, 0)
        identity.assert_called_once_with("fake-org")
        tests.assert_called_once_with("fake-org", "SLAlt", 12)
        self.sf.assert_not_called()

    def test_wrong_org_identity_fails_before_deployed_inventory(self):
        with mock.patch.object(grok.gym, "identity", side_effect=grok.sfc.SfError("org identity mismatch")), \
                mock.patch.object(grok.sfc, "do_deployed") as inventory, \
                mock.patch.object(grok.gym, "object_names") as objects, \
                mock.patch.object(grok.sfc, "permission_set_id") as permissions:
            status, output = self.invoke("deployed", "--org", "retargeted")
        self.assertEqual(status, 1)
        self.assertIn("org identity mismatch", output)
        inventory.assert_not_called()
        objects.assert_not_called()
        permissions.assert_not_called()
        self.sf.assert_not_called()

    def test_deployed_requires_metadata_objects_permission_and_rejects_extra_objects(self):
        def evaluate(*, metadata=(True, "metadata present"), objects=(ITEM,), permission="0PS123"):
            with mock.patch.object(grok.gym, "identity", return_value={"Id": "fake"}) as identity, \
                    mock.patch.object(grok.sfc, "do_deployed", return_value=metadata) as dispatch, \
                    mock.patch.object(grok.gym, "object_names", return_value=list(objects)), \
                    mock.patch.object(grok.sfc, "permission_set_id", return_value=permission):
                result = grok.do_deployed("fake-org", PREFIX)
            identity.assert_called_once_with("fake-org")
            dispatch.assert_called_once_with("fake-org", PREFIX, [PREFIX + "Controller"], [LWC],
                                             1, [PREFIX + "_Chat"], [PREFIX])
            return result
        self.assertFalse(evaluate(metadata=(False, "chat tab is missing"))[0])
        self.assertFalse(evaluate(objects=())[0])
        self.assertFalse(evaluate(permission=None)[0])
        extra = evaluate(objects=(ITEM, PREFIX + "Audit__c"))
        self.assertFalse(extra[0])
        self.assertIn("undeclared", extra[1])
        self.sf.assert_not_called()

    def test_acceptance_stays_unknown_without_org_or_model_calls_in_all_phases(self):
        for phase in ("builder", "final", "product_at_stop"):
            with self.subTest(phase=phase), mock.patch.dict(os.environ, {"E2E_CHECK_PHASE": phase}), \
                    mock.patch.object(grok.gym, "identity") as identity, \
                    mock.patch.object(grok.sfc, "do_tests") as tests:
                status, output = self.invoke("acceptance", "--org", "de", "--prefix", PREFIX)
                self.assertNotEqual(status, 0)
                self.assertIn("UNKNOWN", output)
                identity.assert_not_called()
                tests.assert_not_called()
                self.sf.assert_not_called()

    def test_declared_checker_actions_are_valid_cli_actions(self):
        for action in ("project", "deployed", "tests", "acceptance"):
            with self.subTest(action=action), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    grok.main([action, "--help"])
                self.assertEqual(raised.exception.code, 0)
        self.sf.assert_not_called()


class CatalogIntegrationTest(HermeticTest):
    def test_lifecycle_commands_and_guard_scope_are_explicit(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/cases.json").read_text())
        case = cases["grok-chat-salesforce"]
        platform = case["platform"]
        self.assertEqual(platform["prefix"], PREFIX)
        for key, action in (("preflight", "preflight"), ("before", "snapshot"), ("cleanup", "cleanup")):
            parts = shlex.split(platform[key])
            self.assertEqual(parts[:2], ["python3", "$E2E_CHECKS/gym_membership_salesforce.py"])
            self.assertEqual(parts[2:], [action, "--org", "de", "--prefix", PREFIX])

        sf_command = platform["model_bin"]["sf"]
        self.assertEqual(sf_command, 'python3 "$E2E_CHECKS/sf_guard.py" --org de --prefix SLGrokChat --permission-sets --custom-objects --')
        self.assertNotRegex(sf_command.lower(), r"credential|named-credential")
        for name in ("sfdx", "osascript", "open"):
            self.assertIn("--deny-all", platform["model_bin"][name])
        self.assertEqual(platform.get("existing", "fresh"), "fresh")

    def test_case_check_commands_and_suite_membership(self):
        cases = json.loads((ROOT / "test/shiploop_e2e/cases.json").read_text())
        case = cases["grok-chat-salesforce"]
        actions = []
        for command in case["checks"]:
            parts = shlex.split(command)
            self.assertEqual(parts[:2], ["python3", "$E2E_CHECKS/grok_chat_salesforce.py"])
            actions.append(parts[2])
            self.assertIn("--org", parts)
            self.assertIn("--prefix", parts)
            self.assertIn(PREFIX, parts)
        self.assertEqual(actions, ["project", "deployed", "tests", "acceptance"])
        self.assertEqual(case["needs"], ["browser"])
        suites = json.loads((ROOT / "test/shiploop_e2e/suites.json").read_text())
        for name, suite in suites.items():
            if isinstance(suite, dict):
                self.assertNotIn("grok-chat-salesforce", suite.get("cases", []) + suite.get("gate", []), name)


if __name__ == "__main__":
    unittest.main()

