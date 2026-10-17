#!/usr/bin/env python3
"""A stand-in for the Salesforce `sf` CLI, for hermetic tests. It never talks to a network or an org.

A test builds a shim directory holding an executable named `sf` that runs this file, puts that directory first on PATH, and
points the fake at its state with environment variables:

  FAKE_SF_STATE   JSON file holding the fake org (created on first use). Keys:
                    alias            org alias shown by `sf org list` (default: the first FAKE_SF_ORGS entry)
                    connectedStatus  default "Connected"
                    org_buckets      the `sf org list` buckets that hold the org (default ["other", "nonScratchOrgs"]: the real CLI
                                     puts a Developer Edition org under `other` and also lists it under `nonScratchOrgs`)
                    apex_classes     ApexClass Names (default: the 4 names of the real Developer Edition baseline)
                    lwc              LightningComponentBundle DeveloperNames (default: its 13 baseline names)
                    types            {metadata type: names} for the other queryable types (default: the baseline counts of the same
                                     org: 12 CustomTab, 16 FlexiPage, 37 CustomApplication, 1 CustomObject, 1 PermissionSet)
                    dates            {type: {name: LastModifiedDate}}; a name without an entry has BASE_DATE, a deploy sets DEPLOY_DATE
                    query_errors     {type: message}: a query on that type fails. A message that says "not supported" is answered
                                     like an edition without the object (INVALID_TYPE); any other text, like a timeout, comes back as
                                     a plain QueryFailed error
  FAKE_SF_LOG     file; one JSON line is appended per call: {"argv", "target_org", "refused", ...}. A destructive deploy
                  also logs {"destructive": {"CustomApplication": [...], "CustomTab": [...], "FlexiPage": [...],
                  "LightningComponentBundle": [...], "ApexClass": [...]}, "type_order": [...], "manifest_types": N}: the members of
                  each of those five types (an empty list for a type the manifest does not name) and the types in the order the
                  destructive manifest listed them.
  FAKE_SF_ORGS    comma list of --target-org values the fake accepts (default "fake-org"). Any other value, or a missing
                  --target-org on a command that needs one, is refused with exit 1 and a JSON error: this proves no check
                  ever relies on the default org or names a different org.
  FAKE_SF_WARN    "1": print a ` ›   Warning: ...` line before the JSON, like the real CLI, so tests prove the parser skips it.
  FAKE_SF_TESTS   JSON file {"outcome": "Passed", "testsRan": 10, "failing": 0} for `sf apex run test` (default 10 passing).
  FAKE_SF_APEX    JSON file mapping a RESULT name to its canned value for `sf apex run --file`. The fake scans the script for
                  the literal markers `RESULT|<name>|` (the check embeds `System.debug('RESULT|<name>|' + ...)`) and answers
                  one USER_DEBUG line per marker, in order of first appearance. A value is a scalar, or an object
                  {"error": "<exceptionMessage>"} (success=false, compiled=true), {"compileProblem": "<text>"} (compiled=false) or
                  {"failure": "<message>"} (the CLI itself fails, as the real one did for "Compilation failed at Line 2 ...").
                  The log has the shape the real CLI returns in `result.logs`: a version line, one `Execute Anonymous:` line per
                  source line, then EXECUTION_STARTED, CODE_UNIT_STARTED, the USER_DEBUG lines and the closing events.
                  A marker with no canned value answers `MISSING`. A whole-game script has one marker (`game_opera`), so one
                  canned value (`ok`, or the text of the first thing that went wrong) stands for the game.
  FAKE_SF_FAIL    comma list of operations that fail with exit 1: any of query, deploy, destructive, test, apex.
  FAKE_SF_DEPLOY_PROBLEM  "Type|Name|problem": a deploy is rejected with that component failure, as the real CLI reports it (status 1,
                  result.details.componentFailures); nothing is deployed.
  FAKE_SF_NOOP_DESTRUCTIVE   "1": a destructive deploy reports success but removes nothing (to test the verify step).

A deploy of a source directory creates what it holds: Apex classes, Lightning web component bundles, and the tabs, applications
and flexipages (`tabs/<Name>.tab-meta.xml`, `applications/<Name>.app-meta.xml`, `flexipages/<Name>.flexipage-meta.xml`). A
destructive deploy removes the named members of those five types.

Queries mirror the real CLI: the Tooling API types need --use-tooling-api, StaticResource and PermissionSet (IsOwnedByProfile = false)
must be queried without it, and every type answers its name field and LastModifiedDate. `sf --version` prints one plain line.

The accessToken in `sf org display --json` is always FAKE-TOKEN-DO-NOT-LOG: tests assert it never reaches any recorded output.
Wildcard destructive changes (<members>*</members>) are refused, so a test fails loudly if a harness ever issues one.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TOKEN = "FAKE-TOKEN-DO-NOT-LOG"
WARNING = " ›   Warning: @salesforce/cli update available from 2.150.6 to 2.151.7."
VALUE_FLAGS = {
    "--target-org", "-o", "--source-dir", "-d", "--manifest", "-x", "--post-destructive-changes",
    "--pre-destructive-changes", "--class-names", "-n", "--result-format", "-r", "--file", "-f", "--query", "-q",
    "--wait", "-w", "--test-level", "-l", "--tests", "-t", "--api-version", "--metadata", "-m", "--output-dir",
}
VERSION = "@salesforce/cli/2.150.6 darwin-arm64 node-v22.14.0"
BASE_DATE = "2026-09-01T09:00:00.000+0000"
DEPLOY_DATE = "2026-10-16T12:00:00.000+0000"
# The measured baseline of the owner's Developer Edition org (docs/e2e-salesforce-chess-evidence/baseline-*.txt).
BASELINE_APEX = ["DeveloperEditionUtils", "DeveloperEditionUtilsTest", "PostInstallScript", "PostInstallScriptTest"]
BASELINE_LWC = ["backgammon", "battleship", "bgRace", "checkers", "chess", "getStartedAgentforce", "getStartedDataCloud",
                "getStartedMuleSoft", "getStartedSfdx", "sharedStyles", "ticTacToe", "utils", "welcome"]
BASELINE_TYPES = {
    "ApexTrigger": [], "ApexPage": [], "ApexComponent": [], "AuraDefinitionBundle": [], "StaticResource": [],
    "FlexiPage": ["baseFlexiPage%02d" % i for i in range(1, 17)],
    "CustomTab": ["baseTab%02d" % i for i in range(1, 13)],
    "CustomApplication": ["baseApp%02d" % i for i in range(1, 38)],
    "CustomObject": ["BaseGame"],
    "PermissionSet": ["baseChessAccess"],
    "ExternalString": [],
}
# object -> (where its names live in the state, name field, id prefix). ApexClass and LightningComponentBundle keep their own keys.
KINDS = {"ApexClass": ("apex_classes", "Name", "01p"), "LightningComponentBundle": ("lwc", "DeveloperName", "0Rb"),
         **{kind: (None, "Name" if kind in ("ApexTrigger", "ApexPage", "ApexComponent", "StaticResource", "PermissionSet", "ExternalString")
                   else "DeveloperName", "0Xx") for kind in BASELINE_TYPES}}
DEPLOYABLE = ("CustomApplication", "CustomTab", "FlexiPage", "LightningComponentBundle", "ApexClass")  # what a deploy may create or remove
SOURCE_SUFFIX = {"CustomTab": ".tab-meta.xml", "CustomApplication": ".app-meta.xml", "FlexiPage": ".flexipage-meta.xml"}  # in tabs/, applications/, flexipages/
STANDARD_API = {"StaticResource", "PermissionSet"}  # every other object here is queried with --use-tooling-api


def default_state() -> dict:
    return {
        "alias": (os.environ.get("FAKE_SF_ORGS") or "fake-org").split(",")[0].strip(),
        "connectedStatus": "Connected",
        "org_buckets": ["other", "nonScratchOrgs"],
        "apex_classes": list(BASELINE_APEX),
        "lwc": list(BASELINE_LWC),
        "types": {kind: list(names) for kind, names in BASELINE_TYPES.items()},
        "dates": {},
        "query_errors": {},
    }


def names_of(state: dict, kind: str) -> list[str]:
    key = KINDS[kind][0]
    return state[key] if key else state.setdefault("types", {}).setdefault(kind, [])


def load_state() -> tuple[dict, Path]:
    path = Path(os.environ.get("FAKE_SF_STATE") or "fake_sf_state.json")
    if path.exists():
        return {**default_state(), **json.loads(path.read_text())}, path
    state = default_state()
    path.write_text(json.dumps(state, indent=2))
    return state, path


def save_state(state: dict, path: Path) -> None:
    path.write_text(json.dumps(state, indent=2))


def log(entry: dict) -> None:
    target = os.environ.get("FAKE_SF_LOG")
    if target:
        with open(target, "a") as handle:
            handle.write(json.dumps(entry) + "\n")


def emit(payload: dict, code: int = 0) -> int:
    if os.environ.get("FAKE_SF_WARN") == "1":
        print(WARNING)
    print(json.dumps(payload))
    return code


def fail(message: str, name: str = "FakeSfError") -> int:
    return emit({"status": 1, "name": name, "message": message, "exitCode": 1, "warnings": []}, 1)


def parse(argv: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    words: list[str] = []
    flags: dict[str, list[str]] = {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("-") and len(token) > 1:
            name, eq, inline = token.partition("=")
            if eq:
                flags.setdefault(name, []).append(inline)
            elif name in VALUE_FLAGS and i + 1 < len(argv):
                flags.setdefault(name, []).append(argv[i + 1])
                i += 1
            else:
                flags.setdefault(name, []).append("")
        else:
            words.append(token)
        i += 1
    return words, flags


def first(flags: dict, *names: str) -> str | None:
    for name in names:
        if flags.get(name):
            return flags[name][0]
    return None


def like(value: str, pattern: str) -> bool:
    # SOQL LIKE is case-insensitive, % and _ are the wildcards.
    regex = "".join(".*" if c == "%" else "." if c == "_" else re.escape(c) for c in pattern)
    return re.fullmatch(regex, value, re.IGNORECASE | re.DOTALL) is not None


def run_query(state: dict, soql: str, tooling: bool) -> int:
    match = re.fullmatch(
        r"\s*SELECT\s+(?P<fields>.+?)\s+FROM\s+(?P<obj>\w+)(?:\s+WHERE\s+(?P<where>.+?))?(?:\s+ORDER\s+BY\s+(?P<order>\w+))?\s*",
        soql, re.IGNORECASE | re.DOTALL)
    if not match or match.group("obj") not in KINDS:
        return fail("fake sf cannot parse this query: %s" % soql, "MALFORMED_QUERY")
    obj = match.group("obj")
    _key, field, prefix = KINDS[obj]
    if tooling == (obj in STANDARD_API):
        return fail("sObject type '%s' is not supported%s." % (obj, " by the Tooling API" if tooling else " without --use-tooling-api"),
                    "INVALID_TYPE")
    if obj in state.get("query_errors", {}):
        message = state["query_errors"][obj]
        return fail(message, "INVALID_TYPE" if "not supported" in message else "QueryFailed")
    names = list(names_of(state, obj))
    if match.group("where"):
        for cond in re.split(r"\s+AND\s+", match.group("where"), flags=re.IGNORECASE):
            if obj == "PermissionSet" and re.fullmatch(r"\s*IsOwnedByProfile\s*=\s*false\s*", cond, re.IGNORECASE):
                continue  # the state lists only the permission sets that no profile owns
            cm = re.fullmatch(r"\s*(\w+)\s+(LIKE|=)\s+'((?:[^'\\]|\\.)*)'\s*", cond, re.IGNORECASE)
            if not cm or cm.group(1).lower() != field.lower():
                return fail("fake sf supports WHERE %s LIKE|= '...' only: %s" % (field, soql), "MALFORMED_QUERY")
            pattern = cm.group(3)
            if cm.group(2).upper() == "LIKE":
                names = [n for n in names if like(n, pattern)]
            else:
                names = [n for n in names if n.lower() == pattern.lower()]
    if match.group("order"):
        names = sorted(names)
    fields = [f.strip() for f in match.group("fields").split(",")]
    if [f.upper() for f in fields] == ["COUNT()"]:
        return emit({"status": 0, "result": {"records": [], "totalSize": len(names), "done": True}, "warnings": []})
    dates = state.get("dates", {}).get(obj, {})
    records = []
    for index, name in enumerate(names, 1):
        record = {}
        for f in fields:
            if f == "Id":
                record["Id"] = "%s%012dAAA" % (prefix, index)
            elif f.lower() == field.lower():
                record[field] = name
            elif f == "LastModifiedDate":
                record[f] = dates.get(name, BASE_DATE)
            else:
                return fail("fake sf does not know field %s on %s" % (f, obj), "INVALID_FIELD")
        records.append(record)
    return emit({"status": 0, "result": {"records": records, "totalSize": len(records), "done": True}, "warnings": []})


def touch(state: dict, kind: str, name: str) -> None:
    """A deploy of a component: it exists afterwards and was modified just now."""
    if name not in names_of(state, kind):
        names_of(state, kind).append(name)
    state.setdefault("dates", {}).setdefault(kind, {})[name] = DEPLOY_DATE


def run_deploy(state: dict, path: Path, flags: dict, entry: dict) -> int:
    destructive = first(flags, "--post-destructive-changes", "--pre-destructive-changes")
    if destructive:
        if "destructive" in fail_ops():
            return fail("fake sf: destructive deploy failed on request", "DeployFailed")
        manifest = first(flags, "--manifest", "-x")
        members: dict[str, list[str]] = {kind: [] for kind in DEPLOYABLE}
        order: list[str] = []
        try:
            tree = ET.parse(destructive)
        except (OSError, ET.ParseError) as exc:
            return fail("fake sf cannot read destructive changes %s: %s" % (destructive, exc))
        for types in tree.getroot().iter():
            if not types.tag.endswith("types"):
                continue
            kind = next((c.text.strip() for c in types if c.tag.endswith("name") and c.text), "")
            names = [c.text.strip() for c in types if c.tag.endswith("members") and c.text]
            if kind in members:
                members[kind].extend(names)
                order.append(kind)
            elif names:
                return fail("fake sf: unsupported destructive type %s" % kind)
        entry["destructive"] = members
        entry["type_order"] = order
        entry["manifest_types"] = 0
        if manifest:
            try:
                entry["manifest_types"] = sum(1 for e in ET.parse(manifest).getroot().iter() if e.tag.endswith("types"))
            except (OSError, ET.ParseError):
                entry["manifest_types"] = -1
        if any(m == "*" for names in members.values() for m in names):
            return fail("fake sf: wildcard destructive change refused", "WildcardRefused")
        if os.environ.get("FAKE_SF_NOOP_DESTRUCTIVE") != "1":
            for kind, names in members.items():
                current = names_of(state, kind)
                current[:] = [n for n in current if n not in names]
                for n in names:
                    state.get("dates", {}).get(kind, {}).pop(n, None)
            save_state(state, path)
        count = sum(len(v) for v in members.values())
        return emit({"status": 0, "result": {"success": True, "status": "Succeeded", "numberComponentsDeployed": count,
                                             "numberComponentErrors": 0}})
    if "deploy" in fail_ops():
        return fail("fake sf: deploy failed on request", "DeployFailed")
    problem = os.environ.get("FAKE_SF_DEPLOY_PROBLEM", "")  # "Type|Name|problem": the real CLI's shape for a rejected component
    if problem:
        kind, name, why = (problem.split("|", 2) + ["", ""])[:3]
        return emit({"status": 1, "result": {"status": "Failed", "success": False, "numberComponentErrors": 1,
                                             "details": {"componentFailures": [{"componentType": kind, "fullName": name, "problem": why}]}}}, 1)
    dirs = flags.get("--source-dir", []) + flags.get("-d", [])
    if not dirs:
        return fail("fake sf: deploy needs --source-dir or --post-destructive-changes")
    deployed = 0
    for directory in dirs:
        root = Path(directory)
        if not root.exists():
            return fail("fake sf: no such source dir %s" % directory, "InvalidSourceDir")
        for cls in sorted(root.rglob("*.cls")):
            touch(state, "ApexClass", cls.stem)
            deployed += 1
        candidates = [p for p in root.rglob("*") if p.is_dir() and p.parent.name == "lwc"]
        if root.parent.name == "lwc":
            candidates.append(root)
        for bundle in sorted(candidates):
            touch(state, "LightningComponentBundle", bundle.name)
            deployed += 1
        for kind, suffix in SOURCE_SUFFIX.items():
            for item in sorted(root.rglob("*" + suffix)):
                touch(state, kind, item.name[:-len(suffix)])
                deployed += 1
    save_state(state, path)
    return emit({"status": 0, "result": {"success": True, "status": "Succeeded", "numberComponentsDeployed": deployed,
                                         "numberComponentErrors": 0}})


def fail_ops() -> set[str]:
    return {p.strip() for p in os.environ.get("FAKE_SF_FAIL", "").split(",") if p.strip()}


def run_tests(state: dict, flags: dict) -> int:
    if "test" in fail_ops():
        return fail("fake sf: test run failed on request", "TestRunFailed")
    names = [n for n in (first(flags, "--class-names", "-n") or "").split(",") if n]
    if not names or "--synchronous" not in flags:
        return fail("fake sf: apex run test needs --class-names and --synchronous")
    missing = [n for n in names if n not in state["apex_classes"]]
    if missing:
        return fail("fake sf: no such test class in the org: %s" % ",".join(missing), "InvalidTestClass")
    spec = {"outcome": "Passed", "testsRan": 10, "failing": 0}
    if os.environ.get("FAKE_SF_TESTS"):
        spec.update(json.loads(Path(os.environ["FAKE_SF_TESTS"]).read_text()))
    ran, failing = int(spec["testsRan"]), int(spec.get("failing", 0))
    skipped = int(spec.get("skipped", 0))
    outcome = spec.get("outcome") or ("Passed" if failing == 0 else "Failed")
    tests = [{"ApexClass": {"Name": names[i % len(names)]}, "MethodName": "fakeTest%d" % (i + 1),
              "Outcome": "Fail" if i < failing else "Pass", "Message": "fake failure" if i < failing else None}
             for i in range(ran)]
    summary = {"outcome": outcome, "testsRan": ran, "passing": max(ran - failing - skipped, 0), "failing": failing,
               "skipped": skipped}
    return emit({"status": 0, "result": {"summary": summary, "tests": tests}})


def run_apex(flags: dict, entry: dict) -> int:
    if "apex" in fail_ops():
        return fail("fake sf: apex run failed on request", "ApexRunFailed")
    script = first(flags, "--file", "-f")
    if not script:
        return fail("fake sf: apex run needs --file")
    try:
        source = Path(script).read_text()
    except OSError as exc:
        return fail("fake sf: cannot read %s: %s" % (script, exc))
    names: list[str] = []
    for name in re.findall(r"RESULT\|([^|'\"\s]+)\|", source):
        if name not in names:
            names.append(name)
    entry["apex_markers"] = names
    canned: dict = {}
    if os.environ.get("FAKE_SF_APEX"):
        canned = json.loads(Path(os.environ["FAKE_SF_APEX"]).read_text())
    # The real log echoes the source after "Execute Anonymous:"; those lines mention RESULT| too and are not USER_DEBUG output.
    lines = ["64.0 APEX_CODE,DEBUG;APEX_PROFILING,INFO"] + ["Execute Anonymous: %s" % row for row in source.splitlines()]
    lines += ["12:00:00.0 (1000)|EXECUTION_STARTED", "12:00:00.0 (1100)|CODE_UNIT_STARTED|[EXTERNAL]|execute_anonymous_apex"]
    for index, name in enumerate(names, 1):
        value = canned.get(name, "MISSING")
        if isinstance(value, dict):
            if "failure" in value:
                return fail(value["failure"], "ApexCompileError")
            if "compileProblem" in value:
                return emit({"status": 0, "result": {"success": False, "compiled": False, "compileProblem": value["compileProblem"],
                                                     "exceptionMessage": "", "exceptionStackTrace": "", "line": 2, "column": 22,
                                                     "logs": ""}})
            if "error" in value:
                return emit({"status": 0, "result": {"success": False, "compiled": True, "compileProblem": "",
                                                     "exceptionMessage": value["error"], "exceptionStackTrace": "AnonymousBlock: line 1",
                                                     "line": 1, "column": 1, "logs": "\n".join(lines) + "\n"}})
        lines.append("12:00:00.0 (%d)|USER_DEBUG|[%d]|DEBUG|%s" % (2000 + index, index + 2, ("RESULT|%s|%s" % (name, value)).replace("|", "&#124;")))  # the real CLI escapes the pipes
    lines += ["12:00:00.0 (8000)|CODE_UNIT_FINISHED|execute_anonymous_apex", "12:00:00.0 (9000)|EXECUTION_FINISHED"]
    return emit({"status": 0, "result": {"success": True, "compiled": True, "compileProblem": "", "exceptionMessage": "",
                                         "exceptionStackTrace": "", "line": -1, "column": -1, "logs": "\n".join(lines) + "\n"}})


def main(argv: list[str]) -> int:
    words, flags = parse(argv)
    target = first(flags, "--target-org", "-o")
    entry = {"argv": argv, "target_org": target, "cwd": os.getcwd(), "refused": False}
    if argv in (["--version"], ["-v"]):  # one plain line, no --json and no org, like the real CLI
        log(entry)
        print(VERSION)
        return 0
    state, path = load_state()
    command = " ".join(words[:3]) if words[:2] == ["apex", "run"] and words[2:3] == ["test"] else " ".join(words[:2])
    if command != "org list":
        accepted = {o.strip() for o in os.environ.get("FAKE_SF_ORGS", "fake-org").split(",") if o.strip()}
        if target is None or target not in accepted:
            entry["refused"] = True
            log(entry)
            return fail("fake sf refuses --target-org %r (accepted: %s)" % (target, ",".join(sorted(accepted))), "NoOrgFound")
    if "--json" not in flags:
        entry["refused"] = True
        log(entry)
        return fail("fake sf: every call must pass --json")
    try:
        if command == "org list":
            listed = {"alias": state["alias"], "username": "fake@example.invalid", "instanceUrl": "https://fake.my.salesforce.com",
                      "connectedStatus": state["connectedStatus"], "isDefaultUsername": True}
            buckets = {"nonScratchOrgs": [], "other": [], "scratchOrgs": [], "sandboxes": [], "devHubs": []}
            for bucket in state["org_buckets"]:
                buckets[bucket] = [listed]
            code = emit({"status": 0, "result": buckets, "warnings": []})
        elif command == "org display":
            code = emit({"status": 0, "result": {"accessToken": TOKEN, "alias": target, "apiVersion": "68.0", "clientId": "x",
                                                 "connectedStatus": state["connectedStatus"], "id": "00D000000000000AAA",
                                                 "instanceUrl": "https://fake.my.salesforce.com", "username": "fake@example.invalid"}})
        elif command == "data query":
            soql = first(flags, "-q", "--query") or ""
            if "query" in fail_ops():
                code = fail("fake sf: query failed on request", "QueryFailed")
            else:
                code = run_query(state, soql, "--use-tooling-api" in flags)
        elif command == "project deploy":
            code = run_deploy(state, path, flags, entry) if words[2:3] == ["start"] else fail("fake sf: unsupported: %s" % " ".join(words))
        elif command == "apex run test":
            code = run_tests(state, flags)
        elif command == "apex run":
            code = run_apex(flags, entry)
        else:
            code = fail("fake sf: unsupported command: %s" % " ".join(words))
    finally:
        log(entry)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
