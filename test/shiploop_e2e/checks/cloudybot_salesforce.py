#!/usr/bin/env python3
"""Platform lifecycle hooks and verification checks for the `cloudybot` E2E case.

Subcommands:
  preflight  Verify org is connected and clean of `<prefix>*` metadata (unless E2E_PLATFORM_EXISTING=update).
  snapshot   Record baseline metadata & permset assignments to `$E2E_PLATFORM_DIR/before.json`.
  cleanup    Remove strictly new `<prefix>*` metadata & assignments added since `before.json`, then verify.
  project    Offline DX structure, `.gitignore`, and prefix checks in current working directory.
  deployed   Verify deployed CloudyBot metadata & consumer-entry tab visibility in the org.
  tests      Run all deployed `@isTest` classes under `<prefix>*` via TAP and enforce `--min-tests`.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

API_VERSION = "68.0"
META_NS = "http://soap.sforce.com/2006/04/metadata"
TOKEN_RE = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
SECRET_FIELD_RE = re.compile(r'("(?:%s)"\s*:\s*)"(?:[^"\\]|\\.)*"' % "|".join(SECRET_KEYS))
AUTH_URL_RE = re.compile(r"force://[^\s\"']+")
UNSUPPORTED_RE = re.compile(r"not supported|INVALID_TYPE|invalid type", re.IGNORECASE)
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# Order matters for destructiveChanges.xml: dependents before targets.
DESTRUCTIVE_ORDER = (
    "CustomApplication",
    "CustomTab",
    "FlexiPage",
    "LightningComponentBundle",
    "Flow",
    "PlatformEventSubscriberConfig",
    "ApexTrigger",
    "ApexClass",
    "PermissionSetGroup",
    "PermissionSet",
    "CustomPermission",
    "CustomMetadata",
    "CustomObject",
    "Group",
    "NamedCredential",
    "ExternalCredential",
    "RemoteSiteSetting",
    "CspTrustedSite",
    "StaticResource",
)


def camel_prefix(prefix: str) -> str:
    match = re.match(r"^([A-Z]+)(?=[A-Z][a-z])|^([A-Z]+)$", prefix)
    if match:
        head = match.group(1) or match.group(2)
        return head.lower() + prefix[len(head):]
    return prefix[:1].lower() + prefix[1:]


def scrub(value):
    if isinstance(value, str):
        value = SECRET_FIELD_RE.sub(r'\1"[redacted]"', value)
        value = AUTH_URL_RE.sub("[redacted]", value)
        return TOKEN_RE.sub("[redacted]", value)
    if isinstance(value, dict):
        return {k: ("[redacted]" if k in SECRET_KEYS else scrub(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def say(text: str = "", stream=None) -> None:
    print(scrub(text), file=stream or sys.stdout)


def tail(text: str, limit: int = 600) -> str:
    text = " ".join(scrub(text or "").split())
    return text if len(text) <= limit else "..." + text[-limit:]


class SfError(Exception):
    pass


def parse_json(text: str):
    decoder = json.JSONDecoder()
    pos = 0
    while True:
        i = text.find("{", pos)
        if i < 0:
            return None
        if i == 0 or text[i - 1] == "\n":
            try:
                obj, _ = decoder.raw_decode(text, i)
            except ValueError:
                obj = None
            if isinstance(obj, dict):
                return obj
        pos = i + 1


def run_sf(cmd: list[str], timeout: int = 300, cwd: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise SfError("sf is not on PATH")
    except subprocess.TimeoutExpired:
        raise SfError("sf %s timed out after %ds" % (" ".join(cmd[1:4]), timeout))


def sf(args: list[str], org: str | None, timeout: int = 300, cwd: str | None = None) -> dict:
    cmd = ["sf", *args]
    if org is not None:
        cmd += ["--target-org", org]
    cmd += ["--json"]
    proc = run_sf(cmd, timeout=timeout, cwd=cwd)
    doc = parse_json(proc.stdout)
    if doc is None:
        raise SfError(
            "sf %s printed no JSON (exit %d): %s"
            % (" ".join(args[:3]), proc.returncode, tail(proc.stdout + " " + proc.stderr))
        )
    return doc


def need_ok(doc: dict, action: str) -> dict:
    if doc.get("status") != 0:
        msg = doc.get("message") or doc.get("name") or tail(json.dumps(doc))
        raise SfError(f"{action} failed: {msg}")
    return doc


def sf_version() -> str:
    try:
        proc = run_sf(["sf", "--version"], timeout=60)
        return scrub((proc.stdout or proc.stderr or "").splitlines()[0] if (proc.stdout or proc.stderr) else "unknown")
    except (SfError, IndexError):
        return "unknown"


def org_entry(org: str) -> dict | None:
    doc = need_ok(sf(["org", "list"], None, timeout=120), "org list")
    groups = doc.get("result") or {}
    for entries in groups.values():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("alias") == org:
                    return entry
    return None


def list_metadata(org: str, meta_type: str) -> tuple[list[str] | None, str]:
    try:
        doc = sf(["org", "list", "metadata", "--metadata-type", meta_type], org, timeout=180)
    except SfError as exc:
        if UNSUPPORTED_RE.search(str(exc)):
            return None, tail(str(exc), 200)
        raise
    if doc.get("status") != 0:
        msg = str(doc.get("message") or "")
        if UNSUPPORTED_RE.search(msg):
            return None, tail(msg, 200)
        raise SfError(f"org list metadata {meta_type} failed: {msg}")
    res = doc.get("result")
    if res is None:
        return [], ""
    if isinstance(res, dict):
        res = [res]
    names = sorted({str(item["fullName"]) for item in res if isinstance(item, dict) and item.get("fullName")})
    return names, ""


def tooling_or_data_query(org: str, soql: str, tooling: bool = True) -> list[dict]:
    args = ["data", "query", "--query", soql]
    if tooling:
        args.append("--use-tooling-api")
    doc = need_ok(sf(args, org, timeout=180), f"query ({'tooling' if tooling else 'data'})")
    return list(((doc.get("result") or {}).get("records")) or [])


def name_prefixes(kind: str, prefix: str) -> tuple[str, ...]:
    lwc = camel_prefix(prefix)
    if kind in ("ApexClass", "ApexTrigger", "CustomObject", "PermissionSet", "PermissionSetGroup",
                "CustomPermission", "CustomMetadata", "Group", "PlatformEventSubscriberConfig",
                "NamedCredential", "ExternalCredential", "RemoteSiteSetting", "CspTrustedSite",
                "StaticResource", "Flow"):
        return (prefix,)
    if kind == "LightningComponentBundle":
        return (lwc,)
    return (prefix, lwc)


def matches_prefix(kind: str, full_name: str, prefix: str) -> bool:
    return any(full_name.startswith(p) for p in name_prefixes(kind, prefix))


def read_org_metadata(org: str, prefix: str) -> tuple[dict[str, list[str]], dict[str, str], dict[str, dict[str, str]]]:
    metadata: dict[str, list[str]] = {}
    unavailable: dict[str, str] = {}
    for kind in DESTRUCTIVE_ORDER:
        names, why = list_metadata(org, kind)
        if names is None:
            unavailable[kind] = why
        else:
            metadata[kind] = names

    baseline_dates: dict[str, dict[str, str]] = {"ApexClass": {}, "LightningComponentBundle": {}}
    lwc = camel_prefix(prefix)
    for rec in tooling_or_data_query(
        org, f"SELECT Name, LastModifiedDate FROM ApexClass WHERE Name LIKE '{prefix}%'", tooling=True
    ):
        if rec.get("Name"):
            baseline_dates["ApexClass"][str(rec["Name"])] = str(rec.get("LastModifiedDate") or "")
    for rec in tooling_or_data_query(
        org,
        f"SELECT DeveloperName, LastModifiedDate FROM LightningComponentBundle WHERE DeveloperName LIKE '{lwc}%'",
        tooling=True,
    ):
        if rec.get("DeveloperName"):
            baseline_dates["LightningComponentBundle"][str(rec["DeveloperName"])] = str(
                rec.get("LastModifiedDate") or ""
            )
    return metadata, unavailable, baseline_dates


def current_permset_assignments(org: str, username: str, prefix: str) -> list[dict]:
    if not username:
        return []
    safe_user = username.replace("'", "\\'")
    soql = (
        "SELECT Id, PermissionSet.Name, PermissionSetGroup.DeveloperName FROM PermissionSetAssignment "
        f"WHERE Assignee.Username = '{safe_user}' "
        f"AND (PermissionSet.Name LIKE '{prefix}%' OR PermissionSetGroup.DeveloperName LIKE '{prefix}%')"
    )
    rows = tooling_or_data_query(org, soql, tooling=False)
    out = []
    for row in rows:
        ps = row.get("PermissionSet") or {}
        psg = row.get("PermissionSetGroup") or {}
        name = ps.get("Name") or psg.get("DeveloperName")
        if row.get("Id") and name:
            out.append({"Id": str(row["Id"]), "PermissionSetName": str(name)})
    return sorted(out, key=lambda r: r["Id"])


def check_prefix(prefix: str) -> None:
    if not NAME_RE.fullmatch(prefix):
        raise SystemExit(f"invalid prefix {prefix!r}")


def platform_dir(override: str | None = None) -> Path:
    return Path(override or os.environ.get("E2E_PLATFORM_DIR") or "platform")


# --------------------------------------------------------------------------------------------- subcommands

def cmd_preflight(args) -> int:
    check_prefix(args.prefix)
    entry = org_entry(args.org)
    if entry is None:
        say(f"FAIL: org alias {args.org!r} is not in `sf org list`")
        return 1
    if str(entry.get("connectedStatus")) != "Connected":
        say(f"FAIL: org {args.org!r} is not connected (connectedStatus={entry.get('connectedStatus')})")
        return 1

    existing_mode = os.environ.get("E2E_PLATFORM_EXISTING", "fresh")
    metadata, _unavail, _dates = read_org_metadata(args.org, args.prefix)
    hits = [
        f"{kind} {name}"
        for kind, names in metadata.items()
        for name in names
        if matches_prefix(kind, name, args.prefix)
    ]
    if hits and existing_mode != "update":
        say(f"FAIL: org {args.org!r} already contains prefixed metadata: {', '.join(hits[:10])}")
        return 1
    if hits and existing_mode == "update":
        say(f"PASS: org {args.org!r} connected (update mode; {len(hits)} baseline {args.prefix}* item(s) kept)")
        return 0
    say(f"PASS: org {args.org!r} connected and clean of {args.prefix}* / {camel_prefix(args.prefix)}* metadata")
    return 0


def cmd_snapshot(args) -> int:
    check_prefix(args.prefix)
    entry = org_entry(args.org)
    if entry is None or str(entry.get("connectedStatus")) != "Connected":
        say(f"FAIL: org {args.org!r} is not connected")
        return 1
    pdir = platform_dir(args.platform_dir)
    pdir.mkdir(parents=True, exist_ok=True)
    metadata, unavailable, baseline_dates = read_org_metadata(args.org, args.prefix)
    username = str(entry.get("username") or "")
    assignments = current_permset_assignments(args.org, username, args.prefix)
    snap = {
        "org": args.org,
        "username": username,
        "prefix": args.prefix,
        "lwc_prefix": camel_prefix(args.prefix),
        "existing": os.environ.get("E2E_PLATFORM_EXISTING", "fresh"),
        "sf_version": sf_version(),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metadata": metadata,
        "unavailable": unavailable,
        "baseline_dates": baseline_dates,
        "permset_assignments": assignments,
    }
    (pdir / "before.json").write_text(json.dumps(scrub(snap), indent=2) + "\n", encoding="utf-8")
    say(f"PASS: snapshot saved to {pdir / 'before.json'}")
    return 0


def destructive_xml(members: dict[str, list[str]]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<Package xmlns="{META_NS}">']
    for kind in DESTRUCTIVE_ORDER:
        names = members.get(kind) or []
        if not names:
            continue
        lines.append("    <types>")
        for n in names:
            lines.append(f"        <members>{html.escape(n)}</members>")
        lines.append(f"        <name>{kind}</name>")
        lines.append("    </types>")
    lines.append(f"    <version>{API_VERSION}</version>")
    lines.append("</Package>")
    return "\n".join(lines) + "\n"


def empty_package_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Package xmlns="{META_NS}">\n'
        f"    <version>{API_VERSION}</version>\n"
        "</Package>\n"
    )


def cmd_cleanup(args) -> int:
    check_prefix(args.prefix)
    pdir = platform_dir(args.platform_dir)
    before_path = pdir / "before.json"
    if not before_path.is_file():
        say(f"FAIL: missing snapshot {before_path}; refusing cleanup")
        return 1
    try:
        before = json.loads(before_path.read_text(encoding="utf-8"))
        before_meta = before["metadata"]
        before_dates = before["baseline_dates"]
        before_assign_ids = {row["Id"] for row in before.get("permset_assignments", [])}
        username = str(before.get("username") or "")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        say(f"FAIL: unreadable snapshot {before_path}: {exc}")
        return 1

    # 1. Remove any newly created PermissionSetAssignments for prefixed permission sets first.
    cur_assign = current_permset_assignments(args.org, username, args.prefix)
    for row in cur_assign:
        if row["Id"] not in before_assign_ids:
            need_ok(
                sf(["data", "delete", "record", "--sobject", "PermissionSetAssignment", "--record-id", row["Id"]], args.org),
                f"delete PermissionSetAssignment {row['Id']}",
            )

    # 2. Identify strictly new prefixed metadata items absent from before.json.
    now_meta, _unavail, _now_dates = read_org_metadata(args.org, args.prefix)
    plan: dict[str, list[str]] = {}
    for kind in DESTRUCTIVE_ORDER:
        if kind not in now_meta or kind not in before_meta:
            continue
        old_set = set(before_meta[kind])
        new_prefixed = [n for n in sorted(now_meta[kind]) if n not in old_set and matches_prefix(kind, n, args.prefix)]
        if new_prefixed:
            plan[kind] = new_prefixed

    if any(plan.values()):
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            pkg = tdir / "package.xml"
            dest = tdir / "destructiveChanges.xml"
            pkg.write_text(empty_package_xml(), encoding="utf-8")
            dest.write_text(destructive_xml(plan), encoding="utf-8")
            need_ok(
                sf(
                    [
                        "project",
                        "deploy",
                        "start",
                        "--manifest",
                        str(pkg),
                        "--post-destructive-changes",
                        str(dest),
                        "--ignore-warnings",
                        "--wait",
                        "10",
                    ],
                    args.org,
                    timeout=600,
                ),
                "destructive cleanup deploy",
            )

    # 3. Verify org matches snapshot for this prefix and baseline dates did not change.
    after_meta, _unavail2, after_dates = read_org_metadata(args.org, args.prefix)
    leftover: list[str] = []
    foreign_notes: list[str] = []
    for kind in DESTRUCTIVE_ORDER:
        if kind not in after_meta or kind not in before_meta:
            continue
        extras = sorted(set(after_meta[kind]) - set(before_meta[kind]))
        for name in extras:
            if any(name.lower().startswith(p.lower()) for p in name_prefixes(kind, args.prefix)):
                leftover.append(f"{kind} {name}")
            else:
                foreign_notes.append(f"{kind} {name}")

    modified_base: list[str] = []
    for kind in ("ApexClass", "LightningComponentBundle"):
        for name, dt in before_dates.get(kind, {}).items():
            if after_dates.get(kind, {}).get(name) != dt:
                modified_base.append(f"{kind} {name}")

    if foreign_notes:
        say(f"NOTE: unrelated metadata left untouched: {', '.join(foreign_notes[:10])}")
    if leftover or modified_base:
        problems = []
        if leftover:
            problems.append("leftover prefixed metadata: " + ", ".join(leftover))
        if modified_base:
            problems.append("modified baseline items: " + ", ".join(modified_base))
        say("FAIL: " + "; ".join(problems))
        return 1

    removed_count = sum(len(v) for v in plan.values())
    say(f"PASS: cleanup verified for {args.prefix}* ({removed_count} new metadata item(s) removed)")
    return 0


def cmd_project(args) -> int:
    check_prefix(args.prefix)
    lwc_prefix = camel_prefix(args.prefix)
    root = Path.cwd().resolve()
    problems: list[str] = []

    proj_file = root / "sfdx-project.json"
    pkg_dirs: list[str] = []
    if not proj_file.is_file():
        problems.append("missing sfdx-project.json")
    else:
        try:
            cfg = json.loads(proj_file.read_text(encoding="utf-8"))
            pkg_dirs = [d["path"] for d in (cfg.get("packageDirectories") or []) if isinstance(d, dict) and d.get("path")]
            if not pkg_dirs:
                problems.append("sfdx-project.json defines no packageDirectories")
        except (OSError, ValueError) as exc:
            problems.append(f"invalid sfdx-project.json: {exc}")

    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        problems.append("missing .gitignore")
    else:
        gi_text = gitignore.read_text(encoding="utf-8", errors="replace")
        for pat in (".sf/", ".sfdx/"):
            if pat not in gi_text:
                problems.append(f".gitignore missing {pat}")

    apex_classes: list[Path] = []
    apex_tests: list[Path] = []
    exposed_lwcs: list[str] = []
    tabs: list[str] = []
    apps: list[str] = []
    permsets: list[str] = []
    unprefixed: list[str] = []

    for d in pkg_dirs:
        base = (root / d).resolve()
        if not base.is_dir():
            problems.append(f"package directory {d} missing")
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.name == ".gitkeep" or f.name.startswith("."):
                continue
            rel = f.relative_to(base)
            parts = rel.parts
            # Support standard main/default/<folder>/... or <folder>/...
            folder = parts[2] if len(parts) >= 3 and parts[0] == "main" and parts[1] == "default" else parts[0]
            tail_parts = parts[3:] if len(parts) >= 3 and parts[0] == "main" and parts[1] == "default" else parts[1:]
            if not tail_parts:
                continue

            if folder in ("lwc", "aura"):
                bundle = tail_parts[0]
                if not bundle.startswith(lwc_prefix):
                    unprefixed.append(rel.as_posix())
                elif folder == "lwc" and f.name == f"{bundle}.js-meta.xml":
                    xml_text = f.read_text(encoding="utf-8", errors="replace")
                    if "<isExposed>true</isExposed>" in xml_text:
                        exposed_lwcs.append(bundle)
            elif folder == "objects":
                if not tail_parts[0].startswith(args.prefix):
                    unprefixed.append(rel.as_posix())
            elif folder == "customMetadata":
                if not tail_parts[0].startswith(args.prefix):
                    unprefixed.append(rel.as_posix())
            else:
                fname = tail_parts[0]
                if not fname.startswith(args.prefix):
                    unprefixed.append(rel.as_posix())
                elif folder == "classes" and f.name.endswith(".cls"):
                    apex_classes.append(f)
                    if re.search(r"@isTest\b", f.read_text(encoding="utf-8", errors="replace"), re.IGNORECASE):
                        apex_tests.append(f)
                elif folder == "tabs" and f.name.endswith(".tab-meta.xml"):
                    tabs.append(f.name.removesuffix(".tab-meta.xml"))
                elif folder == "applications" and f.name.endswith(".app-meta.xml"):
                    apps.append(f.name.removesuffix(".app-meta.xml"))
                elif folder == "permissionsets" and f.name.endswith(".permissionset-meta.xml"):
                    permsets.append(f.name.removesuffix(".permissionset-meta.xml"))

    if unprefixed:
        problems.append(f"unprefixed source file(s): {', '.join(unprefixed[:5])}")
    if not apex_classes:
        problems.append(f"no prefixed Apex classes ({args.prefix}*.cls)")
    if not apex_tests:
        problems.append(f"no prefixed Apex @isTest class ({args.prefix}*.cls)")
    if not exposed_lwcs:
        problems.append(f"no exposed LWC bundle ({lwc_prefix}* with <isExposed>true</isExposed>)")
    if not tabs:
        problems.append(f"no prefixed CustomTab ({args.prefix}*.tab-meta.xml)")
    if not apps:
        problems.append(f"no prefixed CustomApplication ({args.prefix}*.app-meta.xml)")
    if not permsets:
        problems.append(f"no prefixed PermissionSet ({args.prefix}*.permissionset-meta.xml)")

    if problems:
        say("FAIL: " + "; ".join(problems))
        return 1
    say(
        f"PASS: DX project valid ({len(apex_classes)} Apex classes, {len(apex_tests)} test classes, "
        f"{len(exposed_lwcs)} exposed LWC, {len(tabs)} tab, {len(apps)} app, {len(permsets)} permset)"
    )
    return 0


def cmd_deployed(args) -> int:
    check_prefix(args.prefix)
    entry = org_entry(args.org)
    if entry is None or str(entry.get("connectedStatus")) != "Connected":
        say(f"FAIL: org {args.org!r} is not connected")
        return 1
    username = str(entry.get("username") or "")
    metadata, _unavail, _dates = read_org_metadata(args.org, args.prefix)

    required = ("ApexClass", "LightningComponentBundle", "CustomTab", "CustomApplication", "PermissionSet")
    missing = []
    found_counts = {}
    for kind in required:
        hits = [n for n in metadata.get(kind, []) if matches_prefix(kind, n, args.prefix)]
        found_counts[kind] = len(hits)
        if not hits:
            missing.append(kind)

    tabs = [n for n in metadata.get("CustomTab", []) if matches_prefix("CustomTab", n, args.prefix)]
    if tabs and username:
        safe_user = username.replace("'", "\\'")
        tab_list = ", ".join("'" + t.replace("'", "\\'") + "'" for t in tabs)
        vis_soql = (
            "SELECT Name, Visibility, Parent.Name FROM PermissionSetTabSetting "
            f"WHERE Name IN ({tab_list}) AND Visibility IN ('DefaultOn', 'DefaultOff') "
            "AND ParentId IN (SELECT PermissionSetId FROM PermissionSetAssignment "
            f"WHERE Assignee.Username = '{safe_user}')"
        )
        vis_rows = tooling_or_data_query(args.org, vis_soql, tooling=False)
        if not vis_rows:
            missing.append("visible PermissionSetTabSetting for user on " + ", ".join(tabs))

    if missing:
        say(f"FAIL: missing deployed artifacts in {args.org}: {', '.join(missing)}")
        return 1
    summary = ", ".join(f"{k}={v}" for k, v in found_counts.items())
    say(f"PASS: deployed metadata and tab visibility verified in {args.org} ({summary})")
    return 0


def parse_tap(output: str) -> tuple[int, list[str], list[str]]:
    """Return (passed_count, failed_lines, skipped_lines)."""
    passed = 0
    failed: list[str] = []
    skipped: list[str] = []
    for raw in output.splitlines():
        line = raw.strip()
        if re.match(r"^ok\s+\d+\b", line):
            if "# SKIP" in line.upper() or "# TODO" in line.upper():
                skipped.append(line)
            else:
                passed += 1
        elif re.match(r"^not ok\s+\d+\b", line):
            failed.append(line)
    return passed, failed, skipped


def cmd_tests(args) -> int:
    check_prefix(args.prefix)
    recs = tooling_or_data_query(
        args.org, f"SELECT Name, Body FROM ApexClass WHERE Name LIKE '{args.prefix}%'", tooling=True
    )
    test_classes = sorted(
        str(r["Name"])
        for r in recs
        if r.get("Name") and re.search(r"@isTest\b", str(r.get("Body") or ""), re.IGNORECASE)
    )
    if not test_classes:
        say(f"FAIL: no deployed @isTest Apex classes found under {args.prefix}*")
        return 1

    cmd = [
        "sf",
        "apex",
        "run",
        "test",
        "--target-org",
        args.org,
        "--result-format",
        "tap",
        "--wait",
        "10",
        "--code-coverage",
    ]
    for cls in test_classes:
        cmd += ["--class-names", cls]

    proc = run_sf(cmd, timeout=600)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    passed, failed, skipped = parse_tap(combined)

    if proc.returncode != 0 or failed or skipped or passed < args.min_tests:
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"exit {proc.returncode}")
        if failed:
            reasons.append(f"{len(failed)} failed ({failed[0]})")
        if skipped:
            reasons.append(f"{len(skipped)} skipped")
        if passed < args.min_tests:
            reasons.append(f"only {passed} passed (< {args.min_tests})")
        say(f"FAIL: Apex tests across {len(test_classes)} class(es): {'; '.join(reasons)}")
        if tail(combined):
            say(tail(combined, 400))
        return 1

    say(f"PASS: {passed} Apex test(s) passed across {len(test_classes)} class(es): {', '.join(test_classes)}")
    return 0


DISPATCH = {
    "preflight": cmd_preflight,
    "snapshot": cmd_snapshot,
    "cleanup": cmd_cleanup,
    "project": cmd_project,
    "deployed": cmd_deployed,
    "tests": cmd_tests,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="subcommand", required=True)
    for name in ("preflight", "snapshot", "cleanup", "project", "deployed"):
        sp = sub.add_parser(name)
        sp.add_argument("--org", required=True)
        sp.add_argument("--prefix", required=True)
        sp.add_argument("--platform-dir")
    tp = sub.add_parser("tests")
    tp.add_argument("--org", required=True)
    tp.add_argument("--prefix", required=True)
    tp.add_argument("--min-tests", type=int, default=10)
    tp.add_argument("--platform-dir")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return DISPATCH[args.subcommand](args)
    except SfError as exc:
        say(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
