#!/usr/bin/env python3
"""Scenario-specific Salesforce checks; the app is implemented only by ShipLoop."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gym_sf_library", HERE / "battleship_salesforce.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)
sfc = bs.sfc
PREFIX = "SLGym"
# This opt-in case names the owner's authorized shared Developer Edition target.
EXPECTED_ORG_ID = "00Daj000018BzO3EAK"
MEMBER_FIELDS = {
    "LoginUserId__c": "Text", "FullName__c": "Text", "Email__c": "Email",
    "Goal__c": "Text", "Plan__c": "Picklist", "Status__c": "Picklist",
}
VISIT_FIELDS = {"Member__c": "MasterDetail", "CheckedInAt__c": "DateTime", "Coaching__c": "TextArea"}
ORACLE = HERE.parent / "fixtures" / "gym-membership-salesforce-oracle"
REMOVABLE = bs.REMOVABLE + ("CustomObject",)
DERIVED_SUFFIXES = frozenset({"Share", "ChangeEvent", "History", "Feed"})


def identity(org: str) -> dict:
    rows = sfc.records(org, "SELECT Id, OrganizationType, IsSandbox FROM Organization", tooling=False)
    if len(rows) != 1 or rows[0].get("Id") != EXPECTED_ORG_ID or rows[0].get("OrganizationType") != "Developer Edition":
        raise sfc.SfError("live org identity/type does not match this case's authorized shared Developer Edition")
    return {key: rows[0][key] for key in ("Id", "OrganizationType", "IsSandbox")}


def derived_entity(name: str, prefix: str) -> bool:
    stem, separator, suffix = name.rpartition("__")
    return bool(separator and stem.startswith(prefix) and "__" not in stem and suffix in DERIVED_SUFFIXES)


def object_names(org: str, prefix: str, *, include_derived: bool = False) -> list[str]:
    sfc.check_prefix(prefix)
    rows = sfc.records(org, "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName LIKE '%s%%'" % prefix,
                       tooling=False)
    return sorted(row["QualifiedApiName"] for row in rows
                  if include_derived or not derived_entity(row["QualifiedApiName"], prefix))


def field_inventory(org: str) -> list[list[str]]:
    return sorted([[str(row["TableEnumOrId"]), str(row["DeveloperName"])]
                   for row in sfc.records(org, "SELECT TableEnumOrId, DeveloperName FROM CustomField")])


def do_preflight(org: str, prefix: str) -> tuple[bool, str]:
    identity(org)
    ok, message = sfc.do_preflight(org, prefix)
    held = object_names(org, prefix, include_derived=True)
    if held:
        return False, "fresh-only case: existing prefix-owned schema: " + ", ".join(held)
    return ok, message


def do_snapshot(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    current = identity(org)
    ok, message = do_preflight(org, prefix)
    if not ok:
        return ok, message
    fields = field_inventory(org)
    ok, message = sfc.do_snapshot(org, prefix, directory)
    if ok:
        path = directory / "before.json"
        before = json.loads(path.read_text())
        before["gym"] = {"schema": "shiploop-gym-snapshot/1", "identity": current,
                         "object_api_names": object_names(org, prefix), "fields": fields}
        path.write_text(json.dumps(before, indent=2) + "\n")
    return ok, message


def xml(path: Path) -> dict[str, list]:
    root = ET.parse(path).getroot()
    def node(element):
        children = list(element)
        if not children:
            return (element.text or "").strip()
        values = {}
        for child in children:
            values.setdefault(child.tag.rsplit("}", 1)[-1], []).append(node(child))
        return values
    return node(root)


def one(value: dict, key: str, default=""):
    items = value.get(key, [])
    return items[0] if len(items) == 1 else default


def object_specs(prefix: str) -> dict[str, dict]:
    return {prefix + "Member__c": MEMBER_FIELDS, prefix + "Visit__c": VISIT_FIELDS}


def permission_fields(prefix: str) -> set[str]:
    return {prefix + "Member__c." + name for name in MEMBER_FIELDS} | {
        prefix + "Visit__c.CheckedInAt__c", prefix + "Visit__c.Coaching__c"}


def do_project(prefix: str, root: Path = Path(".")) -> tuple[bool, str]:
    sfc.check_prefix(prefix)
    problems = []
    try:
        config = json.loads((root / "sfdx-project.json").read_text())
        if str(config.get("sourceApiVersion")) != "60.0":
            problems.append("sourceApiVersion must be 60.0")
        app = root / "force-app/main/default"
        specs = object_specs(prefix)
        for obj, fields in specs.items():
            directory = app / "objects" / obj
            meta = xml(directory / (obj + ".object-meta.xml"))
            wanted_sharing = "Private" if obj.endswith("Member__c") else "ControlledByParent"
            if one(meta, "sharingModel") != wanted_sharing or one(one(meta, "nameField", {}), "type") != "AutoNumber":
                problems.append(obj + " sharing/nameField mismatch")
            files = {p.name.removesuffix(".field-meta.xml"): p for p in (directory / "fields").glob("*.field-meta.xml")}
            if set(files) != set(fields):
                problems.append(obj + " field set mismatch")
            for name, kind in fields.items():
                if name not in files:
                    continue
                field = xml(files[name])
                if one(field, "fullName") != name or one(field, "type") != kind:
                    problems.append(obj + "." + name + " name/type mismatch")
                if one(field, "required") == "true":
                    problems.append(obj + "." + name + " must not set required=true")
                if kind == "MasterDetail" and one(field, "referenceTo") != prefix + "Member__c":
                    problems.append("visit master-detail must reference only owned member")
                if name == "LoginUserId__c" and (one(field, "unique") != "true" or one(field, "length") != "18"):
                    problems.append("LoginUserId must be unique Text18")
                if name in ("FullName__c", "Goal__c") and one(field, "length") != "80":
                    problems.append(name + " must be Text80")
                if kind == "Picklist":
                    value_set = one(field, "valueSet", {})
                    values = one(value_set, "valueSetDefinition", {})
                    actual = {one(v, "fullName") for v in values.get("value", [])}
                    expected = {"Basic", "Coached"} if name == "Plan__c" else {"Active", "Frozen", "Cancelled"}
                    if actual != expected or one(value_set, "restricted") != "true":
                        problems.append(name + " picklist mismatch")
        allowed_objects = set(specs)
        if {p.name for p in (app / "objects").iterdir() if p.is_dir()} != allowed_objects:
            problems.append("only the two declared owned custom objects are allowed")
        controller = app / "classes" / (prefix + "Controller.cls")
        source = controller.read_text()
        if "@AuraEnabled" not in source:
            problems.append("controller has no AuraEnabled methods")
        if (app / "classes" / (prefix + "OracleTest.cls")).exists():
            problems.append("independent OracleTest is not product code")
        component = sfc.lwc_prefix(prefix) + "App"
        bundle = app / "lwc" / component
        for suffix in (".js", ".html", ".js-meta.xml"):
            if not (bundle / (component + suffix)).is_file():
                problems.append("missing LWC " + component + suffix)
        if "lightning__Tab" not in (bundle / (component + ".js-meta.xml")).read_text():
            problems.append("LWC must expose lightning__Tab")
        tab = xml(app / "tabs" / (prefix + "_Members.tab-meta.xml"))
        if one(tab, "lwcComponent") != component:
            problems.append("tab must display declared LWC")
        app_meta = xml(app / "applications" / (prefix + ".app-meta.xml"))
        if prefix + "_Members" not in app_meta.get("tabs", []):
            problems.append("app must contain member tab")
        permissions = xml(app / "permissionsets" / (prefix + "_Access.permissionset-meta.xml"))
        if permissions.get("userPermissions"):
            problems.append("permission set must not grant userPermissions")
        field_grants = {one(v, "field"): v for v in permissions.get("fieldPermissions", [])}
        if set(field_grants) != permission_fields(prefix) or any(
                one(v, "readable") != "true" or one(v, "editable") != "true" for v in field_grants.values()):
            problems.append("permission set FLS mismatch; omit required master-detail")
        object_grants = {one(v, "object"): v for v in permissions.get("objectPermissions", [])}
        if set(object_grants) != allowed_objects or any(
                any(one(v, name) != "true" for name in ("allowCreate", "allowEdit", "allowRead")) or
                any(one(v, name) != "false" for name in ("allowDelete", "modifyAllRecords", "viewAllRecords"))
                for v in object_grants.values()):
            problems.append("permission set object CRUD scope mismatch")
        # Enforce source paths through the same opt-in guard as the model's deploy.
        guard_spec = importlib.util.spec_from_file_location("gym_guard_library", HERE / "sf_guard.py")
        guard = importlib.util.module_from_spec(guard_spec)
        guard_spec.loader.exec_module(guard)
        problems += guard.deploy_scope_problems(["--source-dir", str(root / "force-app")], str(root),
                                               prefix, permission_sets=True, custom_objects=True)
        allowed_flat = {"tabs": {prefix + "_Members.tab-meta.xml"},
                        "applications": {prefix + ".app-meta.xml"},
                        "permissionsets": {prefix + "_Access.permissionset-meta.xml"}}
        for folder, names in allowed_flat.items():
            if {p.name for p in (app / folder).iterdir() if p.is_file()} != names:
                problems.append(folder + " contains undeclared metadata")
    except (OSError, ValueError, ET.ParseError, TypeError, AttributeError) as exc:
        problems.append("project contract unreadable: " + sfc.tail(str(exc), 200))
    return not problems, "; ".join(problems) if problems else "project schema/app/access contract satisfied"


def do_deployed(org: str, prefix: str) -> tuple[bool, str]:
    identity(org)
    want = {"classes": [prefix + "Controller"], "lwc": [sfc.lwc_prefix(prefix) + "App"],
            "tabs": [prefix + "_Members"], "apps": [prefix], "permsets": [prefix + "_Access"]}
    ok, message = bs.do_deployed(org, prefix, want)
    names = object_names(org, prefix)
    expected = set(object_specs(prefix))
    return ok and set(names) == expected, message + "; owned objects=" + ", ".join(names)


def do_access(org: str, prefix: str) -> tuple[bool, list[str]]:
    identity(org)
    ok, lines = bs.do_access(org, prefix + "_Access", prefix + "_Members")
    ps = bs.permission_set_id(org, prefix + "_Access")
    if not ps:
        return False, lines
    rows = sfc.records(org, "SELECT SobjectType, PermissionsRead, PermissionsCreate, PermissionsEdit, PermissionsDelete, "
                       "PermissionsViewAllRecords, PermissionsModifyAllRecords FROM ObjectPermissions WHERE ParentId = '%s'" % ps,
                       tooling=False)
    held = {row["SobjectType"]: row for row in rows}
    scope = set(held) == set(object_specs(prefix)) and all(
        all(row.get(key) is True for key in ("PermissionsRead", "PermissionsCreate", "PermissionsEdit")) and
        all(row.get(key) is False for key in ("PermissionsDelete", "PermissionsViewAllRecords", "PermissionsModifyAllRecords"))
        for row in held.values())
    rows = sfc.records(org, "SELECT Field, PermissionsRead, PermissionsEdit FROM FieldPermissions WHERE ParentId = '%s'" % ps,
                       tooling=False)
    fls = {row["Field"]: row for row in rows}
    fields_ok = set(fls) == permission_fields(prefix) and all(
        row.get("PermissionsRead") is True and row.get("PermissionsEdit") is True for row in fls.values())
    lines += [("PASS" if scope else "FAIL") + " declared object CRUD only",
              ("PASS" if fields_ok else "FAIL") + " declared nonrequired field FLS only"]
    return ok and scope and fields_ok, lines


def do_cleanup(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    record = {"schema": "shiploop-gym-cleanup/1", "verified": False, "removed": [], "refused": [],
              "unassigned": [], "records_before": {}, "scope": sfc.cleanup_scope(
                  prefix, removable=REMOVABLE, unassigns=("PermissionSetAssignment",))}
    record["scope"]["observes"] = ["live_org_identity", "owned_qualified_object_names",
                                   "whole_org_custom_field_names", "owned_record_ids_before_purge"]
    record["scope"]["not_observed"] = ["arbitrary_apex_dml_outside_owned_objects", "baseline_field_or_metadata_contents",
                                       "metadata_outside_watched_types", "jobs", "late_finishing_deployments"]

    def finish(ok, message):
        record["verified"] = ok
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "cleanup.json").write_text(json.dumps(sfc.scrub(record), indent=2) + "\n")
        return ok, message

    try:
        before = json.loads((directory / "before.json").read_text())
        gym = before["gym"]
        if (before["org"] != org or before["prefix"] != prefix or before.get("existing") == "update"
                or gym.get("schema") != "shiploop-gym-snapshot/1" or gym.get("object_api_names") != []
                or not isinstance(gym.get("fields"), list)
                or not all(isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) for x in pair)
                           for pair in gym["fields"])
                or not all(isinstance(before[key], dict) for key in ("last_modified", "other_types", "unavailable"))
                or not all(isinstance(before[key], list) for key in ("apex_classes", "lightning_component_bundles"))):
            return finish(False, "unusable/mismatched fresh snapshot; no deletion attempted")
        if identity(org) != gym["identity"]:
            return finish(False, "live org identity changed; no deletion attempted")
        recorded = {kind: sfc.recorded_names(before, kind) for kind in REMOVABLE}
        if any(names is None or any(sfc.looks_like_ours(kind, name, prefix) for name in names)
               for kind, names in recorded.items()):
            return finish(False, "snapshot contains pre-existing or uncovered owned metadata; no deletion attempted")
        now = sfc.read_org(org)
        plan = {}
        for kind in bs.REMOVABLE:
            old = sfc.recorded_names(before, kind)
            if old is None:
                return finish(False, "baseline does not cover " + kind + "; no deletion attempted")
            found = now["names"].get(kind, [])
            owned, refused = sfc.plan_removal(found, set(old), sfc.removal_prefix(kind, prefix))
            # Foreign items were never a deletion candidate.
            plan[kind] = owned
            record["refused"] += [{"type": kind, "name": name, "reason": reason} for name, reason in refused
                                 if sfc.looks_like_ours(kind, name, prefix)]
        schema_found = object_names(org, prefix, include_derived=True)
        owned_objects = [name for name in schema_found if name.startswith(prefix) and name.endswith("__c")
                         and "__" not in name[:-3]]
        record["derived_entities"] = sorted(name for name in schema_found if derived_entity(name, prefix))
        unsupported = sorted(set(schema_found) - set(owned_objects) - set(record["derived_entities"]))
        record["refused"] += [{"type": "CustomObject", "name": name, "reason": "not an exactly owned __c object"}
                             for name in unsupported]
        for name in owned_objects:
            try:
                ids = sfc.query(org, "SELECT Id FROM " + name, "Id", tooling=False)
                record["records_before"][name] = {"ids": ids, "count": len(ids)}
            except sfc.SfError:
                record["records_before"][name] = {"count": None, "reason": "record enumeration unavailable"}
        notes = []
        for name in plan["PermissionSet"]:
            record["unassigned"].append({"permission_set": name, "count": bs.unassign(org, name, notes)})
        groups = [({"PermissionSet": plan["PermissionSet"]}, False),
                  ({kind: plan[kind] for kind in sfc.REMOVABLE}, False),
                  ({"CustomObject": sorted(owned_objects, key=lambda n: (n.endswith("Member__c"), n))}, True)]
        for members, purge in groups:
            if not any(members.values()):
                continue
            note = sfc.destructive_deploy(org, members, tuple(members), purge=purge)
            if note:
                notes.append(note)
            else:
                record["removed"] += [{"type": kind, "name": name, "purged": purge}
                                      for kind, names in members.items() for name in names]
        final = sfc.read_org(org)
        diff = sfc.compare(before, final)
        own_extra, foreign_extra = sfc.classify_extra(diff["extra"], prefix)
        field_now = field_inventory(org)
        field_before = {tuple(pair) for pair in gym["fields"]}
        field_after = {tuple(pair) for pair in field_now}
        fields_diff = {"extra": sorted(field_after - field_before), "missing": sorted(field_before - field_after)}
        remaining = object_names(org, prefix, include_derived=True)
        record.update({"comparison": diff, "foreign_extra": foreign_extra, "fields": fields_diff,
                       "remaining_object_api_names": remaining, "notes": notes})
        ok = not (notes or record["refused"] or own_extra or remaining or any(fields_diff.values())
                  or any(diff[key] for key in ("missing", "modified", "unverified")))
        return finish(ok, ("cleanup verified" if ok else "cleanup FAILED") +
                      ": tracked new artifacts/schema/records; baseline covered names, field names and Apex/LWC dates compared")
    except (OSError, ValueError, KeyError, TypeError, sfc.SfError) as exc:
        return finish(False, "cleanup not verified: " + sfc.tail(str(exc), 300))


def validation_verdict(doc: dict, expected_methods: set[str], oracle_class: str) -> tuple[bool, str]:
    result = doc.get("result") or {}
    run = (result.get("details") or {}).get("runTestResult") or {}
    successes = run.get("successes") or []
    actual = {row.get("methodName") for row in successes if row.get("name") == oracle_class}
    failures = run.get("failures") or []
    ok = bool(expected_methods) and expected_methods <= actual and not failures and doc.get("status") == 0 and result.get("success") is True
    return ok, ("PASS" if ok else "FAIL/UNKNOWN") + " independent oracle: %d/%d named methods, %d failures" % (
        len(actual & expected_methods), len(expected_methods), len(failures))


def do_rules(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    import hashlib
    import re
    import uuid

    identity(org)
    phase = os.environ.get("E2E_CHECK_PHASE")
    if phase not in {"final", "product_at_stop"}:
        return False, "UNKNOWN: independent role oracle runs only after the subject stops"
    artifact = directory / "gym-rules" / phase / uuid.uuid4().hex
    artifact.mkdir(parents=True, mode=0o700)
    class_name = prefix + "OracleTest"
    source = (ORACLE / "force-app/main/default/classes/SLGymOracleTest.cls").read_text().replace("SLGym", prefix)
    methods = set(re.findall(r"@isTest\s+static\s+void\s+(\w+)\s*\(", source, re.IGNORECASE))
    if len(methods) < 8:
        return False, "UNKNOWN: independent oracle fixture has fewer than eight declared methods"
    with tempfile.TemporaryDirectory(prefix="gym-oracle-") as temporary:
        work = Path(temporary)
        classes = work / "force-app/main/default/classes"
        classes.mkdir(parents=True)
        (work / "sfdx-project.json").write_text((ORACLE / "sfdx-project.json").read_text())
        (classes / (class_name + ".cls")).write_text(source)
        shutil.copyfile(ORACLE / "force-app/main/default/classes/SLGymOracleTest.cls-meta.xml",
                        classes / (class_name + ".cls-meta.xml"))
        doc = sfc.sf(["project", "deploy", "validate", "--source-dir", str(work / "force-app"),
                      "--test-level", "RunSpecifiedTests", "--tests", class_name, "--wait", "10"], org,
                     timeout=900, cwd=str(work))
    ok, message = validation_verdict(doc, methods, class_name)
    persisted = sfc.apex_names(org, " WHERE Name = '%s'" % class_name)
    if persisted:
        ok, message = False, message + "; unexpected persisted oracle class"
    (artifact / "validation.json").write_text(json.dumps(sfc.scrub(doc), indent=2) + "\n")
    receipt = {"schema": "shiploop-gym-oracle/1", "phase": phase, "org_id": EXPECTED_ORG_ID, "prefix": prefix,
               "oracle_sha256": hashlib.sha256(source.encode()).hexdigest(), "expected_methods": sorted(methods),
               "check_only": True, "persisted_oracle": bool(persisted), "ok": ok}
    (artifact / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return ok, message + "; receipt=" + str((artifact / "receipt.json").relative_to(directory))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "snapshot", "cleanup", "project", "deployed", "access", "tests", "rules"))
    parser.add_argument("--org", default="de")
    parser.add_argument("--prefix", default=PREFIX)
    parser.add_argument("--min-tests", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        if os.environ.get("E2E_PLATFORM_EXISTING", "fresh") != "fresh":
            raise sfc.SfError("gym case supports fresh state only")
        sfc.check_prefix(args.prefix)
        directory = sfc.platform_dir()
        if args.action == "project":
            ok, message = do_project(args.prefix)
        elif args.action == "preflight":
            ok, message = do_preflight(args.org, args.prefix)
        elif args.action == "snapshot":
            ok, message = do_snapshot(args.org, args.prefix, directory)
        elif args.action == "cleanup":
            ok, message = do_cleanup(args.org, args.prefix, directory)
        elif args.action == "deployed":
            ok, message = do_deployed(args.org, args.prefix)
        elif args.action == "access":
            ok, message = do_access(args.org, args.prefix)
        elif args.action == "tests":
            identity(args.org)
            ok, message = sfc.do_tests(args.org, args.prefix, args.min_tests)
        elif args.action == "rules":
            ok, message = do_rules(args.org, args.prefix, directory)
        else:
            raise sfc.SfError("unsupported gym checker action")
        for line in message if isinstance(message, list) else [message]:
            sfc.say(line)
        return 0 if ok else 1
    except (sfc.SfError, OSError, ValueError, KeyError, TypeError) as exc:
        sfc.say("FAIL/UNKNOWN: " + sfc.tail(str(exc), 300), stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


