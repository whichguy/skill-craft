#!/usr/bin/env python3
"""Smoke checks for the Grok chat case, not an independent chat/security oracle.

The catalog reuses the gym adapter's fresh-prefix lifecycle unchanged. A
missing model credential must not gate building or testing the setup UI.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gym = load("grok_chat_lifecycle", "gym_membership_salesforce.py")
guard = load("grok_chat_guard", "sf_guard.py")
sfc = gym.sfc
PREFIX = "SLGrokChat"
OBJECT_SUFFIXES = ("Action", "Config", "Item", "Message", "Thread")


def do_project(prefix: str, root: Path = Path(".")) -> tuple[bool, str]:
    """Check the declared source/metadata contract without inferring behavior."""
    sfc.check_prefix(prefix)
    problems = []
    app = root / "force-app/main/default"
    try:
        config = json.loads((root / "sfdx-project.json").read_text())
        if not isinstance(config, dict) or not config.get("packageDirectories"):
            problems.append("sfdx-project.json must declare packageDirectories")
        problems += guard.deploy_scope_problems(
            ["--source-dir", str((root / "force-app").resolve())], str(root.resolve()),
            prefix, permission_sets=True, custom_objects=True)
        source = (app / "classes" / (prefix + "Controller.cls")).read_text()
        if "@AuraEnabled" not in source:
            problems.append("controller has no AuraEnabled entry point")
        component = sfc.lwc_prefix(prefix) + "App"
        bundle = app / "lwc" / component
        for suffix in (".js", ".html", ".js-meta.xml"):
            if not (bundle / (component + suffix)).is_file():
                problems.append("missing LWC " + component + suffix)
        if "lightning__Tab" not in (bundle / (component + ".js-meta.xml")).read_text():
            problems.append("LWC must expose lightning__Tab")
        tab = gym.xml(app / "tabs" / (prefix + "_Chat.tab-meta.xml"))
        if gym.one(tab, "lwcComponent") != component:
            problems.append("chat tab must display the declared LWC")
        application = gym.xml(app / "applications" / (prefix + ".app-meta.xml"))
        if prefix + "_Chat" not in application.get("tabs", []):
            problems.append("app must contain the chat tab")
        objects = {p.name for p in (app / "objects").iterdir() if p.is_dir()}
        allowed = {prefix + suffix + "__c" for suffix in OBJECT_SUFFIXES}
        if objects - allowed:
            problems.append("only the declared owned custom objects are allowed")
        item = prefix + "Item__c"
        if item not in objects:
            problems.append("missing synthetic work-item object")
        field_names = set()
        for name in sorted(objects):
            directory = app / "objects" / name
            meta = gym.xml(directory / (name + ".object-meta.xml"))
            fields = {p.name.removesuffix(".field-meta.xml"): gym.xml(p)
                      for p in (directory / "fields").glob("*.field-meta.xml")}
            field_names.update(name + "." + field for field in fields)
            if meta.get("customSettingsType"):
                problems.append("custom settings are outside the declared object scope")
            parents = [f for f in fields.values() if gym.one(f, "type") == "MasterDetail"]
            sharing = "ControlledByParent" if parents else "Private"
            if gym.one(meta, "sharingModel") != sharing:
                problems.append(name + " must use " + sharing + " sharing")
            if any((gym.one(f, "referenceTo") != prefix + "Thread__c" or name == prefix + "Thread__c"
                    or prefix + "Thread__c" not in objects) for f in fields.values()
                   if gym.one(f, "type") in ("Lookup", "MasterDetail")):
                problems.append(name + " relationship must reference the owned Thread parent")
            if name == item:
                if gym.one(gym.one(meta, "nameField", {}), "type") != "Text":
                    problems.append("work-item Name must be Text")
                status = fields.get("Status__c", {})
                values = gym.one(status, "valueSet", {})
                declared = gym.one(values, "valueSetDefinition", {})
                if (gym.one(status, "type") != "Picklist" or gym.one(values, "restricted") != "true"
                        or {gym.one(v, "fullName") for v in declared.get("value", [])} != {"Open", "Done"}):
                    problems.append("work-item Status must be a restricted Open/Done picklist")
                if gym.one(fields.get("Notes__c", {}), "type") not in ("Text", "TextArea", "LongTextArea"):
                    problems.append("work-item Notes must be text")
        permissions = gym.xml(app / "permissionsets" / (prefix + "_Access.permissionset-meta.xml"))
        if permissions.get("userPermissions") or permissions.get("externalCredentialPrincipalAccesses"):
            problems.append("app permission set must not provision system or credential access")
        grants = permissions.get("objectPermissions", [])
        required_grants = objects - {prefix + "Config__c"}
        for name in required_grants:
            matching = [g for g in grants if gym.one(g, "object") == name]
            if len(matching) != 1 or any(gym.one(matching[0], f) != "true"
                                         for f in ("allowRead", "allowCreate", "allowEdit")):
                problems.append(name + " requires one read/create/edit grant")
        for grant in grants:
            if gym.one(grant, "object") == prefix + "Config__c" and any(
                    gym.one(grant, f) == "true" for f in ("allowCreate", "allowEdit")):
                problems.append("app access must not grant configuration writes")
            if gym.one(grant, "object") not in objects or any(
                    gym.one(grant, field) == "true" for field in
                    ("allowDelete", "modifyAllRecords", "viewAllRecords", "viewAllFields")):
                problems.append("object grant exceeds owned read/create/edit scope")
        fields = permissions.get("fieldPermissions", [])
        for name in (item + ".Status__c", item + ".Notes__c"):
            matching = [g for g in fields if gym.one(g, "field") == name]
            if len(matching) != 1 or any(gym.one(matching[0], f) != "true" for f in ("readable", "editable")):
                problems.append(name + " requires one readable/editable field grant")
        for grant in fields:
            field = gym.one(grant, "field")
            if field not in field_names:
                problems.append("field grant is outside delivered schema")
            if field.startswith(prefix + "Config__c.") and gym.one(grant, "editable") == "true":
                problems.append("app access must not grant configuration field writes")
        for grant in permissions.get("classAccesses", []):
            if not (app / "classes" / (gym.one(grant, "apexClass") + ".cls")).is_file():
                problems.append("class grant is outside delivered classes")
        for folder, expected in {
            "permissionsets": {prefix + "_Access.permissionset-meta.xml"},
            "tabs": {prefix + "_Chat.tab-meta.xml"},
            "applications": {prefix + ".app-meta.xml"},
        }.items():
            if {p.name for p in (app / folder).iterdir() if p.is_file()} != expected:
                problems.append(folder + " contains undeclared metadata")
        if (app / "flexipages").is_dir() and any((app / "flexipages").iterdir()):
            problems.append("the request does not declare FlexiPage metadata")
    except (OSError, ValueError, ET.ParseError, TypeError, AttributeError) as exc:
        problems.append("project contract unreadable: " + sfc.tail(str(exc), 200))
    return not problems, "; ".join(problems) if problems else (
        "project smoke contract satisfied; runtime setup, tool use, approval and UI behavior remain unverified")


def do_deployed(org: str, prefix: str) -> tuple[bool, str]:
    gym.identity(org)
    ok, message = sfc.do_deployed(org, prefix, [prefix + "Controller"],
                                 [sfc.lwc_prefix(prefix) + "App"], 1,
                                 [prefix + "_Chat"], [prefix])
    objects = set(gym.object_names(org, prefix))
    allowed = {prefix + suffix + "__c" for suffix in OBJECT_SUFFIXES}
    if objects - allowed:
        return False, message + "; undeclared deployed owned objects: " + ", ".join(sorted(objects - allowed))
    if prefix + "Item__c" not in objects:
        return False, message + "; synthetic work-item object is not deployed"
    if not sfc.permission_set_id(org, prefix + "_Access"):
        return False, message + "; app access permission set is not deployed"
    return ok, message + "; inventory only, not runtime authorization or UI evidence"


def do_acceptance() -> tuple[bool, str]:
    # Smoke-only PASS would enter baselines.jsonl and could satisfy a release gate.
    # Keep this explicit gap until real independent behavior checks replace it.
    return False, ("UNKNOWN: independent setup, live tool use, confirmation/authorization, "
                   "UI and code/comment review are not calibrated for this exploratory case; "
                   "project/deployed/Apex smoke success is not full E2E acceptance")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("project", "deployed", "tests", "acceptance"))
    parser.add_argument("--org", default="de")
    parser.add_argument("--prefix", default=PREFIX)
    parser.add_argument("--min-tests", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        sfc.check_prefix(args.prefix)
        if args.action == "project":
            ok, message = do_project(args.prefix)
        elif args.action == "deployed":
            ok, message = do_deployed(args.org, args.prefix)
        elif args.action == "acceptance":
            ok, message = do_acceptance()
        elif args.action == "tests":
            gym.identity(args.org)
            ok, message = sfc.do_tests(args.org, args.prefix, args.min_tests)
        for line in message if isinstance(message, list) else [message]:
            sfc.say(line)
        return 0 if ok else 1
    except (sfc.SfError, OSError, ValueError, KeyError, TypeError) as exc:
        sfc.say("FAIL/UNKNOWN: " + sfc.tail(str(exc), 300), stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
