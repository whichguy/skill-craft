#!/usr/bin/env python3
"""A stand-in for the Salesforce `sf` CLI, for hermetic tests. It never talks to a network or an org.

A test builds a shim directory holding an executable named `sf` that runs this file, puts that directory first on PATH, and
points the fake at its state with environment variables:

  FAKE_SF_STATE   JSON file holding the fake org (created on first use). Keys:
                    alias            org alias shown by `sf org list` (default: the first FAKE_SF_ORGS entry)
                    connectedStatus  default "Connected"
                    apex_classes     ApexClass Names (default: 4 baseline names)
                    lwc              LightningComponentBundle DeveloperNames (default: 13 baseline names)
  FAKE_SF_LOG     file; one JSON line is appended per call: {"argv", "target_org", "refused", ...}. A destructive deploy
                  also logs {"destructive": {"ApexClass": [...], "LightningComponentBundle": [...]}, "manifest_types": N}.
  FAKE_SF_ORGS    comma list of --target-org values the fake accepts (default "fake-org"). Any other value, or a missing
                  --target-org on a command that needs one, is refused with exit 1 and a JSON error: this proves no check
                  ever relies on the default org or names a different org.
  FAKE_SF_WARN    "1": print a ` ›   Warning: ...` line before the JSON, like the real CLI, so tests prove the parser skips it.
  FAKE_SF_TESTS   JSON file {"outcome": "Passed", "testsRan": 10, "failing": 0} for `sf apex run test` (default 10 passing).
  FAKE_SF_APEX    JSON file mapping a RESULT name to its canned value for `sf apex run --file`. The fake scans the script for
                  the literal markers `RESULT|<name>|` (the check embeds `System.debug('RESULT|<name>|' + ...)`) and answers
                  one USER_DEBUG line per marker, in order of first appearance. A value is a scalar, or an object
                  {"error": "<exceptionMessage>"} (success=false, compiled=true) or {"compileProblem": "<text>"}.
                  A marker with no canned value answers `MISSING`.
  FAKE_SF_FAIL    comma list of operations that fail with exit 1: any of query, deploy, destructive, test, apex.
  FAKE_SF_NOOP_DESTRUCTIVE   "1": a destructive deploy reports success but removes nothing (to test the verify step).

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
KINDS = {"ApexClass": ("apex_classes", "Name", "01p"), "LightningComponentBundle": ("lwc", "DeveloperName", "0Rb")}


def default_state() -> dict:
    return {
        "alias": (os.environ.get("FAKE_SF_ORGS") or "fake-org").split(",")[0].strip(),
        "connectedStatus": "Connected",
        "apex_classes": ["AccountTriage", "LeadScorer", "OrderService", "OrderServiceTest"],
        "lwc": ["baseCard%02d" % i for i in range(1, 14)],
    }


def load_state() -> tuple[dict, Path]:
    path = Path(os.environ.get("FAKE_SF_STATE") or "fake_sf_state.json")
    if path.exists():
        return json.loads(path.read_text()), path
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


def run_query(state: dict, soql: str) -> int:
    match = re.fullmatch(
        r"\s*SELECT\s+(?P<fields>.+?)\s+FROM\s+(?P<obj>\w+)(?:\s+WHERE\s+(?P<where>.+?))?(?:\s+ORDER\s+BY\s+(?P<order>\w+))?\s*",
        soql, re.IGNORECASE | re.DOTALL)
    if not match or match.group("obj") not in KINDS:
        return fail("fake sf cannot parse this query: %s" % soql, "MALFORMED_QUERY")
    key, field, prefix = KINDS[match.group("obj")]
    names = list(state.get(key, []))
    if match.group("where"):
        for cond in re.split(r"\s+AND\s+", match.group("where"), flags=re.IGNORECASE):
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
    records = []
    for index, name in enumerate(names, 1):
        record = {}
        for f in fields:
            if f == "Id":
                record["Id"] = "%s%012dAAA" % (prefix, index)
            elif f.lower() == field.lower():
                record[field] = name
            else:
                return fail("fake sf does not know field %s on %s" % (f, match.group("obj")), "INVALID_FIELD")
        records.append(record)
    return emit({"status": 0, "result": {"records": records, "totalSize": len(records), "done": True}, "warnings": []})


def add_unique(state: dict, key: str, name: str) -> bool:
    if name not in state[key]:
        state[key].append(name)
        return True
    return False


def run_deploy(state: dict, path: Path, flags: dict, entry: dict) -> int:
    destructive = first(flags, "--post-destructive-changes", "--pre-destructive-changes")
    if destructive:
        if "destructive" in fail_ops():
            return fail("fake sf: destructive deploy failed on request", "DeployFailed")
        manifest = first(flags, "--manifest", "-x")
        members: dict[str, list[str]] = {"ApexClass": [], "LightningComponentBundle": []}
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
            elif names:
                return fail("fake sf: unsupported destructive type %s" % kind)
        entry["destructive"] = members
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
                key = KINDS[kind][0]
                state[key] = [n for n in state[key] if n not in names]
            save_state(state, path)
        count = sum(len(v) for v in members.values())
        return emit({"status": 0, "result": {"success": True, "status": "Succeeded", "numberComponentsDeployed": count,
                                             "numberComponentErrors": 0}})
    if "deploy" in fail_ops():
        return fail("fake sf: deploy failed on request", "DeployFailed")
    dirs = flags.get("--source-dir", []) + flags.get("-d", [])
    if not dirs:
        return fail("fake sf: deploy needs --source-dir or --post-destructive-changes")
    deployed = 0
    for directory in dirs:
        root = Path(directory)
        if not root.exists():
            return fail("fake sf: no such source dir %s" % directory, "InvalidSourceDir")
        for cls in sorted(root.rglob("*.cls")):
            deployed += add_unique(state, "apex_classes", cls.stem)
        candidates = [p for p in root.rglob("*") if p.is_dir() and p.parent.name == "lwc"]
        if root.parent.name == "lwc":
            candidates.append(root)
        for bundle in sorted(candidates):
            deployed += add_unique(state, "lwc", bundle.name)
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
    lines = ["64.0 APEX_CODE,DEBUG;APEX_PROFILING,INFO", "Execute Anonymous: (fake)", "12:00:00.0 (1000)|EXECUTION_STARTED"]
    for index, name in enumerate(names, 1):
        value = canned.get(name, "MISSING")
        if isinstance(value, dict):
            if "compileProblem" in value:
                return emit({"status": 0, "result": {"success": False, "compiled": False, "compileProblem": value["compileProblem"],
                                                     "exceptionMessage": "", "exceptionStackTrace": "", "logs": ""}})
            if "error" in value:
                return emit({"status": 0, "result": {"success": False, "compiled": True, "compileProblem": "",
                                                     "exceptionMessage": value["error"], "exceptionStackTrace": "AnonymousBlock: line 1",
                                                     "logs": "\n".join(lines)}})
        lines.append("12:00:00.0 (%d)|USER_DEBUG|[%d]|DEBUG|RESULT|%s|%s" % (2000 + index, index + 2, name, value))
    lines.append("12:00:00.0 (9000)|EXECUTION_FINISHED")
    return emit({"status": 0, "result": {"success": True, "compiled": True, "compileProblem": "", "exceptionMessage": "",
                                         "exceptionStackTrace": "", "logs": "\n".join(lines) + "\n"}})


def main(argv: list[str]) -> int:
    words, flags = parse(argv)
    target = first(flags, "--target-org", "-o")
    entry = {"argv": argv, "target_org": target, "cwd": os.getcwd(), "refused": False}
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
            code = emit({"status": 0, "result": {"nonScratchOrgs": [{
                "alias": state["alias"], "username": "fake@example.invalid", "instanceUrl": "https://fake.my.salesforce.com",
                "connectedStatus": state["connectedStatus"], "isDefaultUsername": True}], "other": [], "scratchOrgs": [],
                "sandboxes": [], "devHubs": []}, "warnings": []})
        elif command == "org display":
            code = emit({"status": 0, "result": {"accessToken": TOKEN, "alias": target, "apiVersion": "68.0", "clientId": "x",
                                                 "connectedStatus": state["connectedStatus"], "id": "00D000000000000AAA",
                                                 "instanceUrl": "https://fake.my.salesforce.com", "username": "fake@example.invalid"}})
        elif command == "data query":
            soql = first(flags, "-q", "--query") or ""
            if "--use-tooling-api" not in flags:
                code = fail("fake sf: ApexClass and LightningComponentBundle need --use-tooling-api", "INVALID_TYPE")
            elif "query" in fail_ops():
                code = fail("fake sf: query failed on request", "QueryFailed")
            else:
                code = run_query(state, soql)
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
