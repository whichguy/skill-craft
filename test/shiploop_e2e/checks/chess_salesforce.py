#!/usr/bin/env python3
"""Checks and platform hooks for the `chess-salesforce` E2E case: a chess engine in Apex plus an LWC, deployed to a Salesforce
Developer Edition org and removed again afterwards.

Subcommands (all exit 0 on success, 1 otherwise, and print scrubbed one-line reasons):
  preflight  org connected and holding no metadata with the case prefix (any type in WATCHED); writes nothing
  snapshot   record the org in $E2E_PLATFORM_DIR/before.json: every ApexClass and LightningComponentBundle name with its
             LastModifiedDate, the names of each type in WATCHED, and the CLI version
  cleanup    remove exactly the prefixed items of the five REMOVABLE types this run created (absent from before.json) in one
             destructive deploy, then verify the org against the snapshot: the name sets of every recorded type and the dates of
             the baseline items. A new item under another case's prefix, or with no prefix relationship to this one at all (another
             case's kept work, an unrelated platform permission set), is reported as left alone, not a failure; a new item that is
             this case's own, including one this cleanup cannot remove (a PermissionSet, which the request forbids and so only a
             model, never this harness, could have made), still fails the cleanup and, for a PermissionSet, is named with the exact
             `sf data delete record` commands to remove it by hand
  project    the Salesforce DX project in the current directory has the files the request names (Apex classes, the component, a
             tab, an app and optionally an app page, all prefixed), and they do what it asks
  deployed   the org holds the engine, controller, a test class, the component, the tab and the app
  tests      run the SLChess*Test classes in the org; all must pass, at least --min-tests of them
  rules      independent oracle: harness-owned anonymous Apex compares the engine and the controller with published perft counts,
             literal start-position answers and the mate/stalemate cases, then plays two complete games through the controller
             (legalMoves, applyMove, status per ply); the last line sums up and names the failed markers
  selftest   rehearsal: deploy a probe class, component, tab, app and app page, test it, run anonymous Apex against it and remove
             it again (real org: main session only). `selftest --reference [DIR]` deploys the known-good reference project
             instead, grades it with project, deployed, tests and rules, and removes it; with `--keep` it stays in the org for
             the owner to open and the by-hand cleanup command is printed. `--keep` needs `--platform-dir`, a folder that outlives
             the run (the cleanup later needs the snapshot in it), and the printed command names this file, so run a `--keep`
             from the checkout that stays (the canonical one after the merge). deployed, tests and rules print their seconds
             against the case's check ceiling (cases.json, platform.check_timeout)

Safety (the owner's rules for this case):
  * Every `sf` call resolves `sf` from PATH (so a test can substitute a fake) and names `--target-org <alias>` explicitly,
    except `sf org list` and `sf --version`, which have no target.
  * `sf org display` is never called; no credential is read, stored, passed to a model or printed. Anything that comes back
    from `sf` and is printed or written passes through scrub() first.
  * cleanup deletes only ApexClass, CustomTab, CustomApplication and FlexiPage names that start with the exact, case-sensitive
    prefix and LightningComponentBundle names that start with the prefix in component spelling (SLChess -> slChess), and only when
    they are absent from before.json. It never uses a wildcard, and exits 0 only after queries show every recorded name set equal
    to the snapshot (barring another case's own prefix or an item with no relationship to this one at all, left alone and only
    noted) and no baseline Apex class or bundle modified. An item of this case's own prefix that is of any other recorded type is
    reported to remove by hand (exact commands for a PermissionSet) and fails the cleanup.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOKEN_RE = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
SECRET_FIELD_RE = re.compile(r'("(?:%s)"\s*:\s*)"(?:[^"\\]|\\.)*"' % "|".join(SECRET_KEYS))
AUTH_URL_RE = re.compile(r"force://[^\s\"']+")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
API_VERSION = "60.0"
META_NS = "http://soap.sforce.com/2006/04/metadata"


# ---------------------------------------------------------------------------------------------------------------- scrub

def scrub(value):
    """Replace secret values (by key name or by shape) with [redacted], in text or in parsed JSON."""
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


# ------------------------------------------------------------------------------------------------------------- sf calls

class SfError(Exception):
    pass


def parse_json(text: str):
    """The first JSON object that starts a line; the real CLI prints update warnings before the JSON."""
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


def run_sf(cmd: list[str], timeout: int, cwd: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise SfError("sf is not on PATH")
    except subprocess.TimeoutExpired:
        raise SfError("sf %s timed out after %ds" % (" ".join(cmd[1:4]), timeout))


def sf(args: list[str], org: str | None, timeout: int = 300, cwd: str | None = None) -> dict:
    """Run `sf <args> [--target-org org] --json` and return the parsed document (any status). The raw output is never kept."""
    cmd = ["sf", *args]
    if org is not None:
        cmd += ["--target-org", org]
    cmd += ["--json"]
    proc = run_sf(cmd, timeout, cwd)
    doc = parse_json(proc.stdout)
    if doc is None:
        raise SfError("sf %s printed no JSON (exit %d): %s" % (" ".join(args[:3]), proc.returncode,
                                                                tail(proc.stdout + " " + proc.stderr)))
    return doc


def sf_version() -> str:
    """The first line of `sf --version`, scrubbed; the installed CLI changes between sessions, so a snapshot records which one ran."""
    try:
        proc = run_sf(["sf", "--version"], 60)
    except SfError:
        return "unavailable"
    lines = scrub(proc.stdout).strip().splitlines()
    return lines[0].strip()[:200] if proc.returncode == 0 and lines else "unavailable"


def need_ok(doc: dict, what: str) -> dict:
    if doc.get("status") != 0:
        raise SfError("%s failed: %s" % (what, tail(str(doc.get("message") or doc.get("name") or doc))))
    return doc


def records(org: str, soql: str, tooling: bool = True) -> list[dict]:
    doc = need_ok(sf(["data", "query", *(["--use-tooling-api"] if tooling else []), "-q", soql], org), "query %r" % soql)
    result = doc.get("result") or {}
    if result.get("done") is False or result.get("totalSize") != len(result.get("records") or []):
        raise SfError("query %r came back truncated; refusing to act on a partial list" % soql)
    return result["records"]


def query(org: str, soql: str, field: str, tooling: bool = True) -> list[str]:
    """The ``field`` of every record that has one. A record without it cannot be ours: the real org holds a CustomTab whose
    DeveloperName is null (first seen by the 2026-10-16 rehearsal), and the fake never produced one."""
    return [r[field] for r in records(org, soql, tooling) if r.get(field)]


def renamed(script: str, default: str, prefix: str) -> str:
    """An oracle's anonymous Apex for a run whose items carry `prefix` in place of the case's `default` (run.py
    --platform-prefix): every class the oracle names begins with the default, so that spelling is renamed and nothing else."""
    return script if prefix == default else script.replace(default, prefix)


def lwc_prefix(prefix: str) -> str:
    """The component spelling of the Apex prefix: lower-case the leading capitals but the last one (SLChess -> slChess)."""
    run = re.match(r"[A-Z]+", prefix)
    if not run:
        return prefix
    caps = run.group(0)
    keep = 1 if 1 < len(caps) < len(prefix) else 0
    return caps[:len(caps) - keep].lower() + prefix[len(caps) - keep:]


def check_prefix(prefix: str) -> None:
    if not NAME_RE.match(prefix):
        raise SfError("prefix %r is not a plain identifier" % prefix)


def apex_names(org: str, where: str = "") -> list[str]:
    return query(org, "SELECT Name FROM ApexClass%s" % where, "Name")


def lwc_names(org: str, where: str = "") -> list[str]:
    return query(org, "SELECT DeveloperName FROM LightningComponentBundle%s" % where, "DeveloperName")


def prefixed(org: str, prefix: str) -> tuple[list[str], list[str]]:
    """Prefixed ApexClass and LightningComponentBundle names now in the org. SOQL LIKE ignores case, so the exact, case-sensitive
    prefix is enforced here as well; look-alikes with another case are returned by `loose` in cleanup instead."""
    check_prefix(prefix)
    apex = [n for n in apex_names(org, " WHERE Name LIKE '%s%%'" % prefix) if n.startswith(prefix)]
    lwc = [n for n in lwc_names(org, " WHERE DeveloperName LIKE '%s%%'" % lwc_prefix(prefix)) if n.startswith(lwc_prefix(prefix))]
    return sorted(apex), sorted(lwc)


def loose(org: str, prefix: str) -> tuple[list[str], list[str]]:
    """Case-insensitive matches, for cleanup to refuse the ones that do not carry the exact prefix."""
    return (sorted(apex_names(org, " WHERE Name LIKE '%s%%'" % prefix)),
            sorted(lwc_names(org, " WHERE DeveloperName LIKE '%s%%'" % lwc_prefix(prefix))))


# Metadata a run could leave in the org besides Apex classes and bundles: (type, name field, Tooling API, extra WHERE). Each query
# was measured on the real Developer Edition org. The snapshot records every type's names, cleanup compares them by set (the org's
# baseline holds tabs, pages and applications of its own), and preflight refuses a prefixed one. Of these only CustomTab,
# CustomApplication and FlexiPage are removable (the request allows them); a leftover of any other type is detected, never removed.
WATCHED = [
    ("ApexTrigger", "Name", True, ""),
    ("ApexPage", "Name", True, ""),
    ("ApexComponent", "Name", True, ""),
    ("AuraDefinitionBundle", "DeveloperName", True, ""),
    ("StaticResource", "Name", False, ""),
    ("FlexiPage", "DeveloperName", True, ""),
    ("CustomTab", "DeveloperName", True, ""),
    ("CustomApplication", "DeveloperName", True, ""),
    ("CustomObject", "DeveloperName", True, ""),
    ("PermissionSet", "Name", False, "IsOwnedByProfile = false"),
    ("ExternalString", "Name", True, ""),
]
SPEC = {spec[0]: spec for spec in WATCHED}
OWN_TYPES = ("ApexClass", "LightningComponentBundle")  # queried with their LastModifiedDate; cleanup also removes from them
# The types cleanup removes from, in the order of the destructive manifest: what refers to something comes before it (an app lists
# tabs, a tab shows the component or a page, the page and the component use the Apex class), and one deploy handles them together.
REMOVABLE = ("CustomApplication", "CustomTab", "FlexiPage", "LightningComponentBundle", "ApexClass")
UNSUPPORTED_RE = re.compile(r"not supported|INVALID_TYPE")  # the CLI's answer for an object the edition does not have
NOT_QUERYABLE = "type was not queryable at the snapshot"


def cleanup_scope(prefix: str, *, removable: tuple[str, ...] = REMOVABLE,
                  unassigns: tuple[str, ...] = (), assignment_baseline: bool = False) -> dict[str, object]:
    """Describe the declared cleanup policy; this is not evidence that its namespace is actually exclusive."""
    removable_types = set(removable)
    scope: dict[str, object] = {
        "kind": "declared-cleanup-policy",
        "policy": "shared-org-tracked",
        "removes": list(removable),
        "unassigns": list(unassigns),
        "compares_only": sorted(({spec[0] for spec in WATCHED} | set(OWN_TYPES)) - removable_types),
        "ownership_assumption": {
            "kind": "reserved_namespace",
            "prefix": prefix,
            "case_sensitive": True,
            "removal_requires_absent_from_before_json": True,
            "removal_prefix_by_type": {kind: removal_prefix(kind, prefix) for kind in removable},
        },
        "not_observed": [
            "arbitrary_apex_dml_business_records",
            "fields_on_baseline_objects_or_metadata_contents",
            "metadata_outside_watched_types",
            "jobs",
            "late_finishing_deployments",
        ],
    }
    if assignment_baseline:
        scope["assignment_baseline"] = {
            "source": "before.json.permset_assignments",
            "identity": "PermissionSetAssignment.Id",
            "baseline_ids_preserved": True,
            "new_ids_removed": True,
        }
    return scope


def watched_names(org: str, spec: tuple, like_prefix: str | None = None) -> list[str]:
    kind, field, tooling, base = spec
    where = [c for c in (base, "%s LIKE '%s%%'" % (field, like_prefix) if like_prefix else "") if c]
    return sorted(query(org, "SELECT %s FROM %s%s" % (field, kind, " WHERE " + " AND ".join(where) if where else ""), field, tooling))


def queryable_names(org: str, spec: tuple, like_prefix: str | None = None) -> tuple[list[str] | None, str]:
    """(names, "") for one WATCHED type, or (None, why) when the edition has no such object. Any other failure (timeout, no JSON,
    truncation, auth) raises: a transient error must not pass as "nothing there"."""
    try:
        return watched_names(org, spec, like_prefix), ""
    except SfError as exc:
        if UNSUPPORTED_RE.search(str(exc)):
            return None, tail(str(exc), 200)
        raise


def name_spelling(kind: str, prefix: str) -> tuple[str, ...]:
    """The case-prefix spelling(s) that count as this case's own for one metadata kind: the Apex spelling for ApexClass, the
    component spelling for LightningComponentBundle, either spelling for any other type (a tab or page may follow either
    convention)."""
    if kind == "ApexClass":
        return (prefix,)
    if kind == "LightningComponentBundle":
        return (lwc_prefix(prefix),)
    return (prefix, lwc_prefix(prefix))


def with_prefix(found: dict[str, list[str]], prefix: str) -> list[str]:
    """`Type name` for every name that carries the case prefix exactly (see `name_spelling`)."""
    return ["%s %s" % (kind, n) for kind, names in found.items() for n in names if n.startswith(name_spelling(kind, prefix))]


def looks_like_ours(kind: str, name: str, prefix: str) -> bool:
    """Whether `name` (of kind `kind`) is related to this case's own prefix at all, case-insensitively: a look-alike that only
    differs by case (slchess, SLCHESS_Home, slChess_Board) is still this case's own, and still unsafe to auto-remove; only a name
    with no such relationship to the prefix in either spelling is another case's own work, or the platform's."""
    return any(name.lower().startswith(spelling.lower()) for spelling in name_spelling(kind, prefix))


def classify_extra(extra: dict[str, list[str]], prefix: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Split one comparison's extra items (new since the snapshot) into (ours, foreign) by `looks_like_ours`. This cleanup's job is
    this case's own prefix: a foreign item (another case's kept work, or an item with no prefix relationship to this one at all,
    such as a platform-wide permission set) is reported as an informational note and never fails the cleanup; an item that is ours,
    even a look-alike this cleanup refuses to touch, still does."""
    ours: dict[str, list[str]] = {}
    foreign: dict[str, list[str]] = {}
    for kind, names in extra.items():
        mine = [n for n in names if looks_like_ours(kind, n, prefix)]
        other = [n for n in names if n not in mine]
        if mine:
            ours[kind] = mine
        if other:
            foreign[kind] = other
    return ours, foreign


def foreign_note(foreign: dict[str, list[str]]) -> str:
    """One line naming extra items that carry no relationship to this case's prefix at all: informational only, never a cleanup
    failure (`classify_extra`)."""
    items = ["%s %s" % (kind, n) for kind, names in sorted(foreign.items()) for n in names]
    return "not this case's: left alone: %s" % ", ".join(items)


def platform_dir(override: str | None = None) -> Path:
    return Path(override or os.environ.get("E2E_PLATFORM_DIR") or "platform")


# ----------------------------------------------------------------------------------------------------------- preflight

def org_status(org: str) -> str | None:
    doc = need_ok(sf(["org", "list"], None), "org list")
    groups = doc.get("result") or {}
    for key, entries in groups.items():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("alias") == org:
                    return str(entry.get("connectedStatus"))
    return None


# How a run treats prefixed metadata that is already in the org. "fresh" (the default): none may be there, the run starts from an
# org without it and the cleanup restores that. "update": a run that deploys over an earlier run's kept work (the release slice,
# `run.py --platform-existing update`): what is there at the snapshot is the baseline, so the cleanup removes only what the run
# adds beyond it. The harness hands the mode to a case's commands as $E2E_PLATFORM_EXISTING.
EXISTING_MODES = ("fresh", "update")


def do_preflight(org: str, prefix: str, existing: str = "fresh") -> tuple[bool, str]:
    status = org_status(org)
    if status is None:
        return False, "org alias %r is not in `sf org list`" % org
    if status != "Connected":
        return False, "org alias %r is not connected (connectedStatus=%s)" % (org, status)
    apex, lwc = prefixed(org, prefix)
    found, skipped = {"ApexClass": apex, "LightningComponentBundle": lwc}, []
    for spec in WATCHED:
        names, _why = queryable_names(org, spec, prefix)
        if names is None:
            skipped.append(spec[0])  # an edition without that object: nothing there to be dirty
        else:
            found[spec[0]] = names
    dirty = with_prefix(found, prefix)
    if dirty and existing == "update":
        return True, "org %r connected; update mode: %d %s*/%s* item(s) already there are the baseline, kept by the cleanup: %s" % (
            org, len(dirty), prefix, lwc_prefix(prefix), ", ".join(dirty))
    if dirty:
        return False, "org %r is not clean: found %s before the run; nothing was deployed" % (org, ", ".join(dirty))
    return True, "org %r connected; no %s*/%s* item in %d metadata types%s" % (
        org, prefix, lwc_prefix(prefix), len(found), "; not queryable here: " + ", ".join(skipped) if skipped else "")


# ------------------------------------------------------------------------------------------------------------ snapshot

def read_org(org: str) -> dict:
    """The org as the snapshot records it: names of ApexClass, LightningComponentBundle and every WATCHED type, the LastModifiedDate of
    each Apex class and bundle, and the WATCHED types the edition does not have. Any other failed query raises: without every
    answer the run cannot be told apart from the baseline."""
    dates = {"ApexClass": {r["Name"]: r.get("LastModifiedDate") for r in records(org, "SELECT Name, LastModifiedDate FROM ApexClass")},
             "LightningComponentBundle": {r["DeveloperName"]: r.get("LastModifiedDate") for r in records(
                 org, "SELECT DeveloperName, LastModifiedDate FROM LightningComponentBundle")}}
    names, unavailable = {kind: sorted(by_name) for kind, by_name in dates.items()}, {}
    for spec in WATCHED:
        found, why = queryable_names(org, spec)
        if found is None:
            unavailable[spec[0]] = why
        else:
            names[spec[0]] = found
    return {"names": names, "dates": dates, "unavailable": unavailable}


def do_snapshot(org: str, prefix: str, directory: Path, existing: str = "fresh") -> tuple[bool, str]:
    check_prefix(prefix)
    seen = read_org(org)
    clash = with_prefix(seen["names"], prefix)
    if clash and existing != "update":
        return False, "org %r already holds prefixed metadata (%s); refusing to snapshot a dirty org" % (org, ", ".join(clash))
    names = seen["names"]
    directory.mkdir(parents=True, exist_ok=True)
    # The mode is recorded only for "update": a fresh snapshot keeps the file it has always had, and the cleanup reads the mode
    # from the snapshot it compares with, so a snapshot and its cleanup cannot disagree about what the baseline is.
    update = {"existing": "update", "baseline_prefixed": clash} if existing == "update" else {}
    (directory / "before.json").write_text(json.dumps({
        "org": org, "prefix": prefix, "apex_classes": names["ApexClass"], "lightning_component_bundles": names["LightningComponentBundle"],
        "last_modified": seen["dates"], "other_types": {kind: found for kind, found in names.items() if kind not in OWN_TYPES},
        "unavailable": seen["unavailable"], "counts": {kind: len(found) for kind, found in names.items()},
        "tool_versions": {"sf": sf_version()}, **update}, indent=2) + "\n")
    return True, "snapshot of org %r%s: %s%s -> %s" % (
        org, " (update mode: %d prefixed item(s) are the baseline)" % len(clash) if update else "",
        ", ".join("%d %s" % (len(found), kind) for kind, found in names.items()),
        "; unavailable: " + ", ".join(seen["unavailable"]) if seen["unavailable"] else "", directory / "before.json")


# ------------------------------------------------------------------------------------------------------------- cleanup

def plan_removal(found: list[str], before: set[str], prefix: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Split `found` into names safe to remove and (name, reason) refusals. A name is removable only if it starts with the exact,
    case-sensitive prefix, is a plain identifier, and is absent from the before snapshot."""
    remove, refused = [], []
    for name in sorted(set(found)):
        if not NAME_RE.match(name) or not name.startswith(prefix):
            refused.append((name, "does not start with the exact prefix %s" % prefix))
        elif name in before:
            refused.append((name, "was already in the before snapshot"))
        else:
            remove.append(name)
    return remove, refused


def destructive_xml(members: dict[str, list[str]], order: tuple[str, ...] = REMOVABLE) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<Package xmlns="%s">' % META_NS]
    # REMOVABLE order: what refers to something is listed before it, and one destructive deploy removes them all.
    for kind in order:
        if members.get(kind):
            parts.append("    <types>")
            parts += ["        <members>%s</members>" % n for n in members[kind]]
            parts += ["        <name>%s</name>" % kind, "    </types>"]
    parts += ["    <version>%s</version>" % API_VERSION, "</Package>", ""]
    return "\n".join(parts)


def empty_package_xml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<Package xmlns="%s">\n    <version>%s</version>\n</Package>\n' % (META_NS, API_VERSION)


def recorded_names(before: dict, kind: str) -> list[str] | None:
    """The names of one type in the snapshot; None when the snapshot could not query that type."""
    if kind == "ApexClass":
        return before["apex_classes"]
    if kind == "LightningComponentBundle":
        return before["lightning_component_bundles"]
    return before["other_types"].get(kind)


def removal_prefix(kind: str, prefix: str) -> str:
    """The exact spelling cleanup removes: the component spelling for bundles, the Apex spelling for every other type."""
    return lwc_prefix(prefix) if kind == "LightningComponentBundle" else prefix


def do_cleanup(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    check_prefix(prefix)
    record = {"scope": cleanup_scope(prefix), "removed": [], "refused": [], "verified": False}
    out = directory / "cleanup.json"

    def finish(ok: bool, message: str, **extra) -> tuple[bool, str]:
        record.update(extra, verified=ok)
        directory.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scrub(record), indent=2) + "\n")
        return ok, message

    try:
        before = json.loads((directory / "before.json").read_text())
        if not (all(isinstance(before[key], dict) for key in ("last_modified", "other_types", "unavailable"))
                and all(isinstance(before[key], list) for key in ("apex_classes", "lightning_component_bundles"))):
            raise TypeError("before.json is not a snapshot of this version")
    except (OSError, ValueError, KeyError, TypeError):
        return finish(False, "no usable %s: refusing to delete anything because the run's new metadata cannot be told apart"
                      % (directory / "before.json"), error="missing before.json")
    apex_found, lwc_found = loose(org, prefix)
    found = {"ApexClass": apex_found, "LightningComponentBundle": lwc_found}
    for kind in REMOVABLE:
        if kind not in found:  # an edition without the object has nothing to remove; the verification below speaks for the rest
            found[kind] = queryable_names(org, SPEC[kind], removal_prefix(kind, prefix))[0] or []
    plan = {}
    for kind in REMOVABLE:
        recorded = recorded_names(before, kind)
        if recorded is None:  # the snapshot could not query this type, so nothing in it can be told apart from the baseline
            plan[kind], refused = [], [(n, NOT_QUERYABLE) for n in sorted(set(found[kind]))]
        else:
            plan[kind], refused = plan_removal(found[kind], set(recorded), removal_prefix(kind, prefix))
        record["refused"] += [{"type": kind, "name": n, "reason": why} for n, why in refused]
    deploy_note = ""
    if any(plan.values()):
        deploy_note = destructive_deploy(org, plan)
        if not deploy_note:
            record["removed"] = [{"type": kind, "name": n} for kind in REMOVABLE for n in plan[kind]]
    try:
        now = read_org(org)
    except SfError as exc:
        return finish(False, "%s; could not verify afterwards: %s" % (deploy_note or "deploy ran", exc), error=str(exc))
    diff = compare(before, now)
    for r in record["refused"]:  # compare() skips a type the snapshot could not query, but a prefixed item of it is still left over
        if r["reason"] == NOT_QUERYABLE:
            diff["extra"].setdefault(r["type"], []).append(r["name"])
    record.update({key: diff[key] for key in ("extra", "missing", "modified", "unverified", "covered", "not_covered")})
    # The cleanup's job is this case's own prefix: an extra item under another case's prefix, or with no prefix relationship to
    # this one at all (a platform-wide permission set, for example), is reported as an informational note and never fails it; an
    # extra item that is ours, even one this cleanup refuses to touch, still does.
    own_extra, foreign_extra = classify_extra(diff["extra"], prefix)
    note = "; " + foreign_note(foreign_extra) if foreign_extra else ""
    if any(diff[key] for key in ("missing", "modified", "unverified")) or own_extra:
        shown = dict(diff, extra=own_extra)
        return finish(False, "%sorg differs from the before snapshot: %s%s" % (
            deploy_note + "; " if deploy_note else "", describe(shown, REMOVABLE, org), note))
    removed = ["%s %s" % (r["type"], r["name"]) for r in record["removed"]]
    return finish(True, "cleanup verified: org %r matches the before snapshot by name on %s; LastModifiedDate unchanged on %d baseline "
                  "ApexClass and LightningComponentBundle items; removes when new and prefixed (%s*, %s* for bundles): %s; only compares, "
                  "never removes: %s%s; removed %s%s" % (
                      org, ", ".join("%s %d" % (kind, n) for kind, n in diff["covered"].items()), diff["dates_checked"],
                      prefix, lwc_prefix(prefix), ", ".join(REMOVABLE),
                      ", ".join(kind for kind in diff["covered"] if kind not in REMOVABLE) or "-",
                      "; not covered (query failed at the snapshot): " + ", ".join(diff["not_covered"]) if diff["not_covered"] else "",
                      ", ".join(removed) or "nothing", note))


def destructive_deploy(org: str, members: dict[str, list[str]], order: tuple[str, ...] = REMOVABLE, *, purge: bool = False) -> str:
    """One destructive deploy of exactly these named members (listed in `order`) from a throwaway project: "" when it succeeded, else
    why it failed (the verification after it decides the cleanup). `purge=True` appends the CLI's purge-on-delete option; by default the
    command is unchanged."""
    work = Path(tempfile.mkdtemp(prefix="sf-cleanup-"))
    try:
        (work / "force-app").mkdir()
        (work / "manifest").mkdir()
        (work / "sfdx-project.json").write_text(json.dumps(
            {"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": API_VERSION}))
        (work / "manifest" / "package.xml").write_text(empty_package_xml())
        (work / "manifest" / "destructiveChanges.xml").write_text(destructive_xml(members, order))
        args = ["project", "deploy", "start", "--manifest", str(work / "manifest" / "package.xml"),
                "--post-destructive-changes", str(work / "manifest" / "destructiveChanges.xml"), "--wait", "10"]
        if purge:
            args.append("--purge-on-delete")
        doc = sf(args, org, timeout=900, cwd=str(work))
        if doc.get("status") != 0:
            failures = "; ".join("%s %s: %s" % (f.get("componentType"), f.get("fullName"), tail(str(f.get("problem") or ""), 200))
                                 for f in (((doc.get("result") or {}).get("details") or {}).get("componentFailures") or [])[:5])
            return "destructive deploy failed: %s" % (failures or tail(str(doc.get("message") or doc.get("name") or doc)))
        return ""
    except SfError as exc:
        return str(exc)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def permission_set_id(org: str, name: str) -> str | None:
    """The Id of the PermissionSet named exactly `name`, when it is found exactly once."""
    rows = [r for r in records(org, "SELECT Id, Name FROM PermissionSet WHERE Name = '%s'" % name.replace("\\", "\\\\").replace("'", "\\'"),
                               tooling=False) if r.get("Name") == name and r.get("Id")]
    return str(rows[0]["Id"]) if len(rows) == 1 else None


def permission_set_assignment_ids(org: str, permset_id: str) -> list[str]:
    """The Ids of every PermissionSetAssignment of one permission set Id, whoever it is assigned to."""
    return [str(r["Id"]) for r in records(org, "SELECT Id FROM PermissionSetAssignment WHERE PermissionSetId = '%s'" % permset_id,
                                          tooling=False) if r.get("Id")]


def by_hand_plan(org: str, name: str) -> str:
    """One line for one prefixed PermissionSet this cleanup does not remove itself: this case's own request forbids a permission
    set, so only a model that disregarded it, never this harness, could have made one (F9 of the live 2026-10-19 run). The exact
    `sf data delete record` commands that remove its assignments and then it are printed, with the live Ids looked up so they can
    be run exactly as given; this mirrors the module's own destructive-removal pattern (battleship_salesforce.unassign), just
    through a plain data delete of the set itself rather than a destructive deploy, since a data delete needs no local manifest."""
    base = "not removable by this cleanup: remove by hand: PermissionSet %s" % name
    note = "only a model could have made it, never this harness"
    try:
        ps_id = permission_set_id(org, name)
        if ps_id is None:
            return "%s (%s; its Id could not be looked up to print exact commands)" % (base, note)
        assign_ids = permission_set_assignment_ids(org, ps_id)
    except SfError as exc:
        return "%s (%s; could not look up its Id or assignments: %s)" % (base, note, exc)
    commands = ["sf data delete record --sobject PermissionSetAssignment --record-id %s --target-org %s" % (aid, org) for aid in assign_ids]
    commands.append("sf data delete record --sobject PermissionSet --record-id %s --target-org %s" % (ps_id, org))
    return "%s (%s): %s" % (base, note, "; ".join(commands))


def compare(before: dict, now: dict, updated: dict[str, str] | None = None) -> dict:
    """The org now against the snapshot. extra, missing and modified are {type: [...]}; unverified is a recorded type that cannot be
    queried now (fail closed); not_covered are the types the snapshot could not query (skipped); covered is {type: count}.

    ``updated`` ({type: exact name prefix}, update mode only) names baseline items a run is expected to deploy over: a changed
    LastModifiedDate on one of those is reported under ``updated`` and not under ``modified``, because a cleanup cannot restore the
    earlier version and the run's job was to replace it. Every other changed date is ``modified`` as always."""
    diff = {"extra": {}, "missing": {}, "modified": {}, "updated": {}, "unverified": {}, "covered": {},
            "not_covered": dict(before["unavailable"]), "dates_checked": 0}
    recorded = {"ApexClass": before["apex_classes"], "LightningComponentBundle": before["lightning_component_bundles"],
                **before["other_types"]}
    for kind, was in recorded.items():
        if kind in now["unavailable"]:
            diff["unverified"][kind] = now["unavailable"][kind]
            continue
        found = now["names"][kind]
        diff["covered"][kind] = len(found)
        for key, names in (("extra", sorted(set(found) - set(was))), ("missing", sorted(set(was) - set(found)))):
            if names:
                diff[key][kind] = names
    for kind, dates in before["last_modified"].items():
        current = now["dates"].get(kind, {})
        for name, date in sorted(dates.items()):
            if name in current:
                diff["dates_checked"] += 1
                if current[name] != date:
                    expected = (updated or {}).get(kind)
                    bucket = "updated" if expected and name.startswith(expected) else "modified"
                    diff[bucket].setdefault(kind, []).append("%s (%s -> %s)" % (name, date, current[name]))
    return diff


def describe(diff: dict, removable: tuple[str, ...] = REMOVABLE, org: str | None = None) -> str:
    parts = []
    for kind, names in diff["extra"].items():
        if kind in removable:
            parts.append("extra %s %s" % (kind, ", ".join(names)))
        elif kind == "PermissionSet" and org is not None:
            parts += [by_hand_plan(org, name) for name in names]
        else:
            parts.append("not removable by this cleanup: remove by hand: %s %s" % (kind, ", ".join(names)))
    parts += ["missing since the snapshot: %s %s" % (kind, ", ".join(names)) for kind, names in diff["missing"].items()]
    parts += ["modified since the snapshot: %s %s" % (kind, ", ".join(names)) for kind, names in diff["modified"].items()]
    parts += ["could not verify %s (query failed: %s)" % (kind, why) for kind, why in diff["unverified"].items()]
    return "; ".join(parts)


# ------------------------------------------------------------------------------------------------------------- project

# Besides Apex classes and the component the request allows exactly these, each named with the case prefix: folder -> file suffix.
SCOPED_META = {"tabs": ".tab-meta.xml", "applications": ".app-meta.xml", "flexipages": ".flexipage-meta.xml"}


def tag_values(text: str, tag: str) -> list[str]:
    return re.findall(r"<%s>\s*([^<\s]+)\s*</%s>" % (tag, tag), text)


def scoped(app: Path, folder: str, prefix: str) -> dict[str, Path]:
    """name -> file of the prefixed metadata in one allowed folder (tabs, applications or flexipages)."""
    suffix = SCOPED_META[folder]
    return {p.name[:-len(suffix)]: p for p in sorted(app.glob("**/%s/*%s" % (folder, suffix))) if p.name.startswith(prefix)}


def ui_problems(app: Path, prefix: str, board: str, boards: list[Path]) -> list[str]:
    """The tab, the app and the optional app page the request asks for, and the component meta file they depend on."""
    tabs, apps, pages = (scoped(app, folder, prefix) for folder in ("tabs", "applications", "flexipages"))
    problems = []
    if "%s_Board" % prefix not in tabs:
        problems.append("no force-app/**/tabs/%s_Board.tab-meta.xml" % prefix)
    if prefix not in apps:
        problems.append("no force-app/**/applications/%s.app-meta.xml" % prefix)
    for file in tabs.values():
        text = file.read_text(errors="replace")
        component, page = tag_values(text, "lwcComponent"), tag_values(text, "flexiPage")
        if component and component[0] != board:
            problems.append("tab %s shows lwcComponent %s, not %s" % (file.name, component[0], board))
        elif not component and not (page and page[0] in pages):
            problems.append("tab %s has no <lwcComponent>%s</lwcComponent> (or a <flexiPage> naming a %s* FlexiPage in this project)"
                            % (file.name, board, prefix))
    for file in apps.values():
        if not set(tag_values(file.read_text(errors="replace"), "tabs")) & set(tabs):
            problems.append("app %s lists no <tabs> entry naming one of this project's %s* tabs" % (file.name, prefix))
    if boards:
        files = sorted(boards[0].glob("*.js-meta.xml"))
        meta = "\n".join(f.read_text(errors="replace") for f in files)
        if not files:
            problems.append("lwc/%s has no .js-meta.xml file" % board)
        elif "lightning__Tab" not in meta:
            problems.append("lwc/%s js-meta.xml does not expose the lightning__Tab target" % board)
        elif pages and "lightning__AppPage" not in meta:
            problems.append("lwc/%s js-meta.xml does not expose lightning__AppPage, which the FlexiPage needs" % board)
    return problems


def do_project(prefix: str, root: Path = Path(".")) -> tuple[bool, str]:
    problems = []
    manifest = root / "sfdx-project.json"
    try:
        json.loads(manifest.read_text())
    except (OSError, ValueError):
        problems.append("sfdx-project.json missing or not JSON")
    app = root / "force-app"
    classes = sorted(app.glob("**/classes/*.cls")) if app.is_dir() else []
    bundles = sorted(p for p in app.glob("**/lwc/*") if p.is_dir()) if app.is_dir() else []
    if not any(c.name == "%sEngine.cls" % prefix for c in classes):
        problems.append("no force-app/**/classes/%sEngine.cls" % prefix)
    problems += ["class %s does not start with %s" % (c.name, prefix) for c in classes if not c.name.startswith(prefix)]
    controller = [c for c in classes if c.name == "%sController.cls" % prefix]
    if not controller:
        problems.append("no force-app/**/classes/%sController.cls" % prefix)
    else:
        source = controller[0].read_text(errors="replace")
        if not re.search(r"@AuraEnabled\b", source, re.IGNORECASE):
            problems.append("%sController.cls has no @AuraEnabled method" % prefix)
        problems += ["%sController.cls declares no static method %s" % (prefix, m) for m in ("legalMoves", "applyMove", "status")
                     if not re.search(r"\bstatic\b[^;{(]*?\b%s\s*\(" % m, source, re.IGNORECASE)]
    board = lwc_prefix(prefix) + "Board"
    boards = [b for b in bundles if b.name == board]
    if not boards:
        problems.append("no force-app/**/lwc/%s/" % board)
    else:
        for ext in (".js", ".html"):
            if not list(boards[0].glob("*" + ext)):
                problems.append("lwc/%s has no %s file" % (board, ext))
        script = "\n".join(f.read_text(errors="replace") for f in sorted(boards[0].glob("*.js")))
        if not re.search(r"""from\s+['"]@salesforce/apex/%sController\.\w+['"]""" % re.escape(prefix), script):
            problems.append("lwc/%s js does not import @salesforce/apex/%sController.<method>" % (board, prefix))
        markup = "\n".join(f.read_text(errors="replace") for f in sorted(boards[0].glob("*.html")))
        if "for:each" not in markup and "iterator" not in markup:
            problems.append("lwc/%s html has no for:each or iterator, so it cannot render a board of squares" % board)
    problems += ["lwc bundle %s does not start with %s" % (b.name, lwc_prefix(prefix)) for b in bundles
                 if not b.name.startswith(lwc_prefix(prefix))]
    if app.is_dir():
        problems += ui_problems(app, prefix, board, boards)
        for meta in app.rglob("*-meta.xml"):
            parts = meta.relative_to(app).parts
            allowed = "classes" in parts or "lwc" in parts or (  # their own checks name the files
                len(parts) > 1 and parts[-2] in SCOPED_META and parts[-1].startswith(prefix) and parts[-1].endswith(SCOPED_META[parts[-2]]))
            if not allowed:
                problems.append("other metadata %s (the request allows only Apex classes, the component and the %s* tab, app and app page)"
                                % ("/".join(parts), prefix))
    if problems:
        return False, "; ".join(problems)
    return True, "project ok: %d Apex classes, %d lwc bundles, tab, app%s" % (
        len(classes), len(bundles), " and app page" if scoped(app, "flexipages", prefix) else "")


# ------------------------------------------------------------------------------------------------------------ deployed

def test_class_names(org: str, prefix: str) -> list[str]:
    check_prefix(prefix)
    names = apex_names(org, " WHERE Name LIKE '%s%%Test'" % prefix)
    return sorted(n for n in names if n.startswith(prefix) and n.endswith("Test"))


def do_deployed(org: str, prefix: str, classes: list[str], lwc: list[str], min_test_classes: int,
                tabs: list[str] = (), apps: list[str] = (), pages: list[str] = ()) -> tuple[bool, str]:
    check_prefix(prefix)
    apex = set(apex_names(org, " WHERE Name LIKE '%s%%'" % prefix))
    bundles = set(lwc_names(org, " WHERE DeveloperName LIKE '%s%%'" % lwc_prefix(prefix)))
    ui = {kind: {n for n in watched_names(org, SPEC[kind], prefix) if n.startswith(prefix)}
          for kind in ("CustomTab", "CustomApplication", "FlexiPage")}  # prefixed names only: the org's own are never listed
    tests = test_class_names(org, prefix)
    problems = ["ApexClass %s not found in org %r" % (n, org) for n in classes if n not in apex]
    problems += ["LightningComponentBundle %s not found in org %r" % (n, org) for n in lwc if n not in bundles]
    for kind, wanted in (("CustomTab", tabs), ("CustomApplication", apps), ("FlexiPage", pages)):
        problems += ["%s %s not found in org %r" % (kind, n, org) for n in wanted if n not in ui[kind]]
    if len(tests) < min_test_classes:
        problems.append("%d %s*Test classes in the org, need %d" % (len(tests), prefix, min_test_classes))
    if problems:
        return False, "; ".join(problems)
    return True, "deployed: %s; %s; tab %s; app %s%s; test classes: %s" % (
        ", ".join(classes) or "-", ", ".join(lwc) or "-", ", ".join(tabs) or "-", ", ".join(apps) or "-",
        "; app page " + ", ".join(pages) if pages else "", ", ".join(tests) or "-")


def expected_names(prefix: str) -> dict[str, list[str]]:
    """What the request names, and `deployed` looks for by default."""
    return {"classes": [prefix + "Engine", prefix + "Controller"], "lwc": [lwc_prefix(prefix) + "Board"],
            "tabs": [prefix + "_Board"], "apps": [prefix], "pages": []}


# --------------------------------------------------------------------------------------------------------------- tests

def do_tests(org: str, prefix: str, min_tests: int) -> tuple[bool, list[str]]:
    classes = test_class_names(org, prefix)
    if not classes:
        return False, ["no %s*Test class in org %r" % (prefix, org)]
    lines, ran, failing, ok = [], 0, 0, True
    # `sf apex run test --synchronous` takes test methods of a single Apex class only (plugin-apex runtestcommon.md,
    # syncClassErr), so each class is its own call and the totals are summed here.
    for cls in classes:
        doc = sf(["apex", "run", "test", "--class-names", cls, "--synchronous", "--result-format", "json"], org, timeout=900)
        summary = (doc.get("result") or {}).get("summary")
        if not isinstance(summary, dict):
            lines.append("FAIL %s: no test summary (%s)" % (cls, tail(str(doc.get("message") or doc.get("name") or doc))))
            ok = False
            continue
        cran, cfail = int(summary.get("testsRan") or 0), int(summary.get("failing") or 0)
        passed = summary.get("outcome") == "Passed" and cfail == 0
        ran, failing, ok = ran + cran, failing + cfail, ok and passed
        lines.append("%s %s: outcome=%s testsRan=%d failing=%d" % ("PASS" if passed else "FAIL", cls, summary.get("outcome"), cran, cfail))
    if ran < min_tests:
        ok = False
    lines.append("%s tests: %d ran, %d failing, need at least %d" % ("PASS" if ok else "FAIL", ran, failing, min_tests))
    return ok, lines


# --------------------------------------------------------------------------------------------------------------- rules

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
PERFT = [  # name, fen, perft(1), perft(2) or None; published chess-programming perft counts
    ("start", START, 20, 400),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 48, None),
    ("pos3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 14, 191),
    ("pos4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 6, 264),
    ("pos5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 44, 1486),
    ("castle", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", 26, None),
]
CASTLE_FEN = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
STALEMATE_FEN = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
CHECK_FEN = "4k3/8/8/8/8/8/8/4RK2 b - - 0 1"  # a lone rook on the open e-file checks the black king, which can step aside
PROMO_FEN = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
# Literal answers the prompt states or implies, derived with an independent move generator (the hermetic suite re-derives them).
START_MOVES = "a2a3,a2a4,b1a3,b1c3,b2b3,b2b4,c2c3,c2c4,d2d3,d2d4,e2e3,e2e4,f2f3,f2f4,g1f3,g1h3,g2g3,g2g4,h2h3,h2h4"
AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
AFTER_E4_E5 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
PROMO_MOVES = "a7a8b,a7a8n,a7a8q,a7a8r,e1d1,e1d2,e1e2,e1f1,e1f2"


def perft_script(name: str, fen: str, with_two: bool) -> str:
    lines = ["String fen = '%s';" % fen,
             "List<String> moves = SLChessEngine.legalMoves(fen);",
             "System.debug('RESULT|%s.p1|' + moves.size());" % name]
    if with_two:
        lines += ["Integer total = 0;",
                  "for (String m : moves) {",
                  "    total += SLChessEngine.legalMoves(SLChessEngine.applyMove(fen, m)).size();",
                  "}",
                  "System.debug('RESULT|%s.p2|' + total);" % name]
    return "\n".join(lines) + "\n"


def play_script(name: str, moves: list[str]) -> str:
    return ("String fen = SLChessEngine.startFen();\n"
            "for (String m : new List<String>{%s}) {\n    fen = SLChessEngine.applyMove(fen, m);\n}\n"
            "System.debug('RESULT|%s|' + SLChessEngine.status(fen));\n") % (", ".join("'%s'" % m for m in moves), name)


# Complete games played ply by ply through the controller, the way the board component does: name, UCI plies, the status after a ply
# when it is not `ongoing`, and (after this ply, a move that is illegal in that position). The hermetic suite re-derives every
# ply, status and refusal with its own move generator.
OPERA = ("e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 "
         "d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8").split()  # Morphy against the Duke of Brunswick and Count Isouard, 1858
SECOND = ("e2e4 a7a6 e4e5 d7d5 e5d6 d8d7 f1a6 b7b6 a6c8 a8a3 c8d7 b8d7 b1a3 h7h5 d6c7 g7g6 c7c8r").split()  # en passant, then a rook promotion mates
GAMES = [
    ("game_opera", OPERA, {21: "check", 29: "check", 31: "check", 33: "checkmate"}, (21, "h7h6")),
    ("game_second", SECOND, {11: "check", 17: "checkmate"}, (11, "h7h5")),
]


def game_script(name: str, moves: list[str], special: dict[int, str], refusal: tuple[int, str]) -> str:
    """One anonymous Apex that plays a whole game through SLChessController: each ply must be among legalMoves, applyMove advances
    the position and status matches. After one ply an illegal move must be refused by the engine (IllegalMoveException). The controller is
    only ever called with legal moves: an AuraHandledException (what a board's controller idiomatically throws) cannot be thrown or caught in
    anonymous Apex, where it becomes an uncatchable System.LimitException (seen on the real org, 2026-10-16). The RESULT value is `ok` or
    the first thing that went wrong."""
    after, bad = refusal
    quote = lambda items: ", ".join("'%s'" % item for item in items)
    return "\n".join([
        "List<String> moves = new List<String>{%s};" % quote(moves),
        "List<String> expected = new List<String>{%s};" % quote(special.get(i, "ongoing") for i in range(1, len(moves) + 1)),
        "String fen = SLChessEngine.startFen();",
        "String outcome = 'ok';",
        "for (Integer i = 0; i < moves.size(); i++) {",
        "    String move = moves[i];",
        "    if (!SLChessController.legalMoves(fen).contains(move)) {",
        "        outcome = 'ply ' + (i + 1) + ' ' + move + ' is not in legalMoves';",
        "        break;",
        "    }",
        "    fen = SLChessController.applyMove(fen, move);",
        "    String shown = SLChessController.status(fen);",
        "    if (shown != expected[i]) {",
        "        outcome = 'ply ' + (i + 1) + ' ' + move + ' leaves status ' + shown + ', expected ' + expected[i];",
        "        break;",
        "    }",
        "    if (i == %d) {" % (after - 1),
        "        Boolean engineThrew = false;",
        "        try {",
        "            SLChessEngine.applyMove(fen, '%s');" % bad,
        "        } catch (SLChessEngine.IllegalMoveException e1) {",
        "            engineThrew = true;",
        "        }",
        "        if (!engineThrew) {",
        "            outcome = 'after ply %d SLChessEngine.applyMove accepted the illegal move %s';" % (after, bad),
        "            break;",
        "        }",
        "    }",
        "}",
        "if (outcome == 'ok' && SLChessController.legalMoves(fen).size() != 0) {",
        "    outcome = 'the last position still has ' + SLChessController.legalMoves(fen).size() + ' legal moves';",
        "}",
        "System.debug('RESULT|%s|' + outcome);" % name, ""])


# (script, [(marker, expected)])
def rule_cases() -> list[tuple[str, str, list[tuple[str, str]]]]:
    cases = []
    for name, fen, one, two in PERFT:
        marks = [("%s.p1" % name, str(one))] + ([("%s.p2" % name, str(two))] if two else [])
        cases.append((name, perft_script(name, fen, two is not None), marks))
    cases.append(("foolsmate", play_script("foolsmate", ["f2f3", "e7e5", "g2g4", "d8h4"]), [("foolsmate", "checkmate")]))
    cases.append(("scholarsmate", play_script("scholarsmate", ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]),
                  [("scholarsmate", "checkmate")]))
    cases.append(("stalemate", "String fen = '%s';\n"
                  "System.debug('RESULT|stalemate.status|' + SLChessEngine.status(fen));\n"
                  "System.debug('RESULT|stalemate.moves|' + SLChessEngine.legalMoves(fen).size());\n" % STALEMATE_FEN,
                  [("stalemate.status", "stalemate"), ("stalemate.moves", "0")]))
    cases.append(("illegal", "String outcome = 'nothrow';\n"
                  "try {\n    SLChessEngine.applyMove(SLChessEngine.startFen(), 'e2e5');\n"
                  "} catch (SLChessEngine.IllegalMoveException e) {\n    outcome = 'threw';\n}\n"
                  "System.debug('RESULT|illegal|' + outcome);\n", [("illegal", "threw")]))
    cases.append(("enpassant", "String fen = SLChessEngine.applyMove(SLChessEngine.startFen(), 'e2e4');\n"
                  "System.debug('RESULT|epfield|' + fen.split(' ')[3]);\n", [("epfield", "e3")]))
    cases.append(("castling", "String fen = SLChessEngine.applyMove('%s', 'e1g1');\n"
                  "System.debug('RESULT|castle.board|' + fen.split(' ')[0]);\n" % CASTLE_FEN,
                  [("castle.board", "r3k2r/8/8/8/8/8/8/R4RK1")]))
    cases.append(("startfen", "System.debug('RESULT|startfen|' + SLChessEngine.startFen());\n"
                  "System.debug('RESULT|startmoves|' + String.join(SLChessEngine.legalMoves(SLChessEngine.startFen()), ','));\n",
                  [("startfen", START), ("startmoves", START_MOVES)]))
    cases.append(("pawnpush", "String fen = SLChessEngine.applyMove(SLChessEngine.startFen(), 'e2e4');\n"
                  "System.debug('RESULT|e2e4|' + fen);\n"
                  "System.debug('RESULT|e7e5|' + SLChessEngine.applyMove(fen, 'e7e5'));\n", [("e2e4", AFTER_E4), ("e7e5", AFTER_E4_E5)]))
    cases.append(("status", "System.debug('RESULT|status.start|' + SLChessEngine.status(SLChessEngine.startFen()));\n"
                  "System.debug('RESULT|status.check|' + SLChessEngine.status('%s'));\n" % CHECK_FEN,
                  [("status.start", "ongoing"), ("status.check", "check")]))
    cases.append(("promotion", "System.debug('RESULT|promo.moves|' + String.join(SLChessEngine.legalMoves('%s'), ','));\n" % PROMO_FEN,
                  [("promo.moves", PROMO_MOVES)]))
    cases.append(("controller", "System.debug('RESULT|controller.moves|' + SLChessController.legalMoves(SLChessEngine.startFen()).size());\n"
                  "System.debug('RESULT|controller.apply|' + SLChessController.applyMove(SLChessEngine.startFen(), 'e2e4'));\n",
                  [("controller.moves", "20"), ("controller.apply", AFTER_E4)]))
    for name, moves, special, refusal in GAMES:
        cases.append((name, game_script(name, moves, special, refusal), [(name, "ok")]))
    return cases


RESULT_LINE = re.compile(r"\|USER_DEBUG\|\[\d+\]\|DEBUG\|RESULT\|([^|\s]+)\|(.*)$", re.MULTILINE)


def run_apex(org: str, work: Path, name: str, script: str) -> tuple[str, dict[str, str], str]:
    """Run one anonymous Apex script from a harness-owned file. Returns the error text ("" on success), the value of each RESULT
    marker in the debug log (`result.logs`), and the raw log."""
    path = work / ("%s.apex" % name)
    path.write_text(script)
    err, result = "", {}
    try:
        doc = sf(["apex", "run", "--file", str(path)], org, timeout=420)
        result = doc.get("result") or {}
        if "compiled" not in result and doc.get("status") != 0:
            err = tail(str(doc.get("message") or doc.get("name") or doc))
    except SfError as exc:
        err = str(exc)
    if not err and result.get("compiled") is False:
        err = "compile error: " + tail(str(result.get("compileProblem")))
    elif not err and not result.get("success"):
        err = "Apex error: " + tail(str(result.get("exceptionMessage")))
    seen = {}
    if not err:
        # The real CLI HTML-escapes the debug text (RESULT&#124;probe&#124;1): found by the 2026-10-16 rehearsal, the fake had written plain pipes.
        for marker, value in RESULT_LINE.findall(html.unescape(result.get("logs") or "")):
            seen.setdefault(marker, value.strip())
    return err, seen, result.get("logs") or ""


def do_rules(org: str, raw_dir: Path | None = None, prefix: str = "SLChess") -> tuple[bool, list[str]]:
    lines, failed, total, raw = [], [], 0, ""
    work = Path(tempfile.mkdtemp(prefix="chess-sf-rules-"))
    try:
        for name, script, marks in rule_cases():
            err, seen, logs = run_apex(org, work, name, renamed(script, "SLChess", prefix))
            bad = False
            for marker, expected in marks:
                got = seen.get(marker)
                good = got is not None and got == expected and not err
                total += 1
                if not good:
                    failed.append(marker)
                    bad = True
                detail = got if got is not None else (err or "no RESULT line in the debug log")
                lines.append("%s %s expected=%s got=%s" % ("PASS" if good else "FAIL", marker, expected, tail(str(detail), 300)))
            if bad and not raw:
                raw = "case %s: %s\n%s" % (name, err or "no Apex error", scrub(logs)[:1024])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # The harness keeps the last 2000 characters of a check's output, so the verdict and the failed markers come last.
    lines.append("rules: %d of %d markers passed; failed: %s" % (total - len(failed), total, ",".join(failed) or "none"))
    if raw and raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "rules-raw.txt").write_text(raw)
    return not failed, lines


# ------------------------------------------------------------------------------------------------------------ selftest

REFERENCE = Path(__file__).resolve().parents[1] / "fixtures" / "chess-salesforce-reference"
CASES = Path(__file__).resolve().parents[1] / "cases.json"
CASE_MIN_TESTS = 8  # the --min-tests of the case's `tests` check; a test holds the two together


def check_ceiling() -> int | None:
    """The seconds the harness gives each of this case's checks (cases.json, platform.check_timeout); None when it cannot be read."""
    try:
        return int(json.loads(CASES.read_text())["chess-salesforce"]["platform"]["check_timeout"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def timed(call, *args):
    """(call(*args), seconds it took)."""
    started = time.monotonic()
    return call(*args), time.monotonic() - started


def probe_script(klass: str) -> str:
    return "System.debug('RESULT|probe|' + %s.two());\n" % klass


def write_probe(root: Path, prefix: str) -> dict[str, str]:
    """A class and its test, a component that imports the class and is exposed on a tab and an app page, a tab showing the component,
    an app holding the tab and an app page holding the component, all carrying the case prefix. Returns their names by role."""
    base = root / "force-app" / "main" / "default"
    names = {"class": prefix + "Probe", "test": prefix + "ProbeTest", "bundle": lwc_prefix(prefix) + "Probe",
             "tab": prefix + "_Probe", "app": prefix + "_Probe", "page": prefix + "_Probe"}
    klass, test, bundle = names["class"], names["test"], names["bundle"]
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    for folder in ("classes", "tabs", "applications", "flexipages"):
        (base / folder).mkdir(parents=True)
    meta = head + '<ApexClass xmlns="%s"><apiVersion>%s</apiVersion><status>Active</status></ApexClass>\n'
    (base / "classes" / (klass + ".cls")).write_text(
        "public class %s {\n    @AuraEnabled(cacheable=true) public static Integer two() { return 2; }\n}\n" % klass)
    (base / "classes" / (klass + ".cls-meta.xml")).write_text(meta % (META_NS, API_VERSION))
    (base / "classes" / (test + ".cls")).write_text(
        "@IsTest\nprivate class %s {\n    @IsTest static void probe() { System.assertEquals(2, %s.two()); }\n}\n" % (test, klass))
    (base / "classes" / (test + ".cls-meta.xml")).write_text(meta % (META_NS, API_VERSION))
    (base / "lwc" / bundle).mkdir(parents=True)
    (base / "lwc" / bundle / (bundle + ".html")).write_text("<template><div>probe</div></template>\n")
    (base / "lwc" / bundle / (bundle + ".js")).write_text(
        "import { LightningElement } from 'lwc';\nimport two from '@salesforce/apex/%s.two';\n"
        "export default class %s extends LightningElement {\n    answer = two;\n}\n" % (klass, bundle[:1].upper() + bundle[1:]))
    (base / "lwc" / bundle / (bundle + ".js-meta.xml")).write_text(
        head + '<LightningComponentBundle xmlns="%s">\n    <apiVersion>%s</apiVersion>\n    <isExposed>true</isExposed>\n'
        "    <targets>\n        <target>lightning__Tab</target>\n        <target>lightning__AppPage</target>\n    </targets>\n"
        "</LightningComponentBundle>\n" % (META_NS, API_VERSION))
    (base / "tabs" / (names["tab"] + ".tab-meta.xml")).write_text(
        head + '<CustomTab xmlns="%s">\n    <label>%s probe</label>\n    <lwcComponent>%s</lwcComponent>\n'
        "    <motif>Custom57: Grid</motif>\n</CustomTab>\n" % (META_NS, prefix, bundle))
    (base / "applications" / (names["app"] + ".app-meta.xml")).write_text(
        head + '<CustomApplication xmlns="%s">\n    <formFactors>Large</formFactors>\n    <isNavAutoTempTabsDisabled>false</isNavAutoTempTabsDisabled>\n'
        "    <isNavPersonalizationDisabled>false</isNavPersonalizationDisabled>\n    <label>%s probe</label>\n"
        "    <navType>Standard</navType>\n    <tabs>%s</tabs>\n    <uiType>Lightning</uiType>\n</CustomApplication>\n"
        % (META_NS, prefix, names["tab"]))
    (base / "flexipages" / (names["page"] + ".flexipage-meta.xml")).write_text(
        head + '<FlexiPage xmlns="%s">\n    <flexiPageRegions>\n        <itemInstances>\n            <componentInstance>\n'
        "                <componentName>c:%s</componentName>\n                <identifier>c_%s</identifier>\n"
        "            </componentInstance>\n        </itemInstances>\n        <name>main</name>\n"
        "        <type>Region</type>\n    </flexiPageRegions>\n    <masterLabel>%s probe</masterLabel>\n    <template>\n"
        "        <name>flexipage:defaultAppHomeTemplate</name>\n    </template>\n    <type>AppPage</type>\n</FlexiPage>\n"
        % (META_NS, bundle, bundle, prefix))
    (root / "sfdx-project.json").write_text(json.dumps(
        {"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": API_VERSION}))
    return names


def do_selftest(org: str, prefix: str, reference: Path | None = None, keep: bool = False, platform: Path | None = None) -> bool:
    if keep and platform is None:
        raise ValueError("keep needs a platform folder that outlives the run")
    work = Path(tempfile.mkdtemp(prefix="chess-sf-selftest-"))
    snap = platform if keep else work / "platform"
    snapped, deployed, all_ok, ceiling = False, False, True, check_ceiling()

    def step(name: str, ok: bool, message: str, seconds: float | None = None) -> bool:
        took = "" if seconds is None else " (%d s%s)" % (round(seconds), " of the case's %d s check ceiling" % ceiling if ceiling else "")
        say("%s %s%s: %s" % ("PASS" if ok else "FAIL", name, took, message))
        return ok

    try:
        say("selftest proves, in order: %spreflight (the org is reachable and holds nothing with the prefix), snapshot (its baseline is "
            "recorded), deploy (%s deploy together), deployed (all are found by query), tests (`apex run test` runs the test class in "
            "the org), %s, %s" % (
                "fixture (the reference project passes `project`, offline), " if reference else "",
                "the reference project's class, component, tab and app" if reference else
                "a class with an @AuraEnabled method, a component that imports it, a tab, an app and an app page",
                "rules (the graded oracle, including two whole games, runs against it)" if reference else
                "apex-run (anonymous Apex calls the class and its RESULT line is parsed from result.logs exactly as `rules` does)",
                "kept (nothing is removed; the by-hand cleanup command is printed)" if keep else
                "cleanup (everything is removed and the org equals its baseline on every recorded type)"))
        project = work / "project"
        if reference is not None:
            if not reference.is_dir():
                step("fixture", False, "the reference project %s does not exist" % reference)
                return False
            shutil.copytree(reference, project, ignore=shutil.ignore_patterns(".sf", ".sfdx", ".git", "node_modules"))
            ok, msg = do_project(prefix, project)
            if not step("fixture", ok, msg if ok else "the reference project %s is incomplete: %s" % (reference, msg)):
                return False
        ok, msg = do_preflight(org, prefix)
        if not step("preflight", ok, msg):
            return False
        ok, msg = do_snapshot(org, prefix, snap)
        snapped = ok
        if not step("snapshot", ok, msg):
            return False
        if reference is None:
            names = write_probe(project, prefix)
            want = {"classes": [names["class"], names["test"]], "lwc": [names["bundle"]], "tabs": [names["tab"]],
                    "apps": [names["app"]], "pages": [names["page"]]}
        else:
            want = expected_names(prefix)
        doc = sf(["project", "deploy", "start", "--source-dir", "force-app", "--wait", "10"], org, timeout=900, cwd=str(project))
        result = doc.get("result") or {}
        failures = "; ".join("%s %s: %s" % (f.get("componentType"), f.get("fullName"), tail(str(f.get("problem") or ""), 200))
                             for f in ((result.get("details") or {}).get("componentFailures") or [])[:5])
        deployed = step("deploy", doc.get("status") == 0 and result.get("success") is not False,
                        "status=%s %s" % (result.get("status"), failures or (tail(str(doc.get("message") or "")) if doc.get("status") != 0 else "")))
        if not deployed:
            return False
        (ok, msg), took = timed(do_deployed, org, prefix, want["classes"], want["lwc"], 1, want["tabs"], want["apps"], want["pages"])
        all_ok &= step("deployed", ok, msg, took)
        (ok, lines), took = timed(do_tests, org, prefix, CASE_MIN_TESTS if reference else 1)
        all_ok &= step("tests", ok, "; ".join(lines), took)
        if reference is None:
            err, seen, _log = run_apex(org, work, "probe", probe_script(names["class"]))
            got = seen.get("probe")
            all_ok &= step("apex-run", not err and got == "2",
                           "RESULT|probe| expected=2 got=%s" % (got if got is not None else (err or "no RESULT line")))
        else:
            (ok, lines), took = timed(do_rules, org, platform)
            all_ok &= step("rules", ok, lines[-1], took)
            for line in lines[:-1]:
                say("    " + line)
        return all_ok
    except SfError as exc:
        step("selftest", False, str(exc))
        return False
    finally:
        cleanup_failed = False
        if snapped and keep and deployed:
            kept = snap.resolve()  # the command is run later, from any directory
            say("KEPT: nothing was removed from org %r; the %s* app stays there to open (App Launcher: %s, or /lightning/n/%s_Board). "
                "The snapshot that cleanup needs is in %s. Remove everything by hand when you are done:\npython3 %s cleanup --org %s "
                "--prefix %s --platform-dir %s" % (org, prefix, prefix, prefix, kept, Path(__file__).resolve(), org, prefix, kept))
        elif snapped:
            try:
                ok, msg = do_cleanup(org, prefix, snap)
            except BaseException as exc:  # cleanup must report, even when interrupted
                ok, msg = False, "cleanup raised %s" % type(exc).__name__
            step("cleanup", ok, msg)
            if not ok:
                cleanup_failed = True
                say("MANUAL CLEANUP NEEDED: remove the %s* and %s* items (%s) from org %r (destructive deploy of exactly those names)."
                    % (prefix, lwc_prefix(prefix), ", ".join(REMOVABLE), org))
        shutil.rmtree(work, ignore_errors=True)
        if cleanup_failed:
            raise SystemExit(1)


# -------------------------------------------------------------------------------------------------------------- main

def csv(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="chess_salesforce.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("preflight", "snapshot", "cleanup", "project", "deployed", "tests", "rules", "selftest"):
        p = sub.add_parser(name)
        p.add_argument("--org", required=name not in ("project",))
        p.add_argument("--prefix", default="SLChess")
        p.add_argument("--platform-dir")
        if name == "deployed":
            for option in ("classes", "lwc", "tabs", "apps", "pages"):
                p.add_argument("--" + option)
            p.add_argument("--min-test-classes", type=int, default=1)
        if name == "tests":
            p.add_argument("--min-tests", type=int, default=1)
        if name == "selftest":
            p.add_argument("--reference", nargs="?", const=str(REFERENCE))
            p.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "preflight":
            ok, msg = do_preflight(args.org, args.prefix)
        elif args.cmd == "snapshot":
            ok, msg = do_snapshot(args.org, args.prefix, platform_dir(args.platform_dir))
        elif args.cmd == "cleanup":
            ok, msg = do_cleanup(args.org, args.prefix, platform_dir(args.platform_dir))
            if not ok:
                say("CLEANUP FAILED. Remove the run's %s*/%s* metadata from org %r by hand, or rerun: "
                    "python3 chess_salesforce.py cleanup --org %s --prefix %s" % (args.prefix, lwc_prefix(args.prefix), args.org,
                                                                                 args.org, args.prefix), sys.stderr)
        elif args.cmd == "project":
            ok, msg = do_project(args.prefix)
        elif args.cmd == "deployed":
            want = {option: csv(getattr(args, option)) if getattr(args, option) is not None else default
                    for option, default in expected_names(args.prefix).items()}
            ok, msg = do_deployed(args.org, args.prefix, want["classes"], want["lwc"], args.min_test_classes,
                                  want["tabs"], want["apps"], want["pages"])
        elif args.cmd == "tests":
            ok, lines = do_tests(args.org, args.prefix, args.min_tests)
            msg = "\n".join(lines)
        elif args.cmd == "rules":
            raw_dir = args.platform_dir or os.environ.get("E2E_PLATFORM_DIR")
            ok, lines = do_rules(args.org, Path(raw_dir) if raw_dir else None, args.prefix)
            msg = "\n".join(lines)
        else:
            if args.keep and not args.reference:
                parser.error("--keep needs --reference")
            if args.keep and not args.platform_dir:
                parser.error("--keep needs --platform-dir (a durable folder; the snapshot cleanup needs later must not live in $TMPDIR)")
            return 0 if do_selftest(args.org, args.prefix, Path(args.reference) if args.reference else None, args.keep,
                                    Path(args.platform_dir) if args.platform_dir else None) else 1
    except SfError as exc:
        say("FAIL %s: %s" % (args.cmd, exc))
        return 1
    say(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
