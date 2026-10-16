#!/usr/bin/env python3
"""Checks and platform hooks for the `chess-salesforce` E2E case: a chess engine in Apex plus an LWC, deployed to a Salesforce
Developer Edition org and removed again afterwards.

Subcommands (all exit 0 on success, 1 otherwise, and print scrubbed one-line reasons):
  preflight  org connected and holding no metadata with the case prefix (any type in WATCHED); writes nothing
  snapshot   record the org in $E2E_PLATFORM_DIR/before.json: every ApexClass and LightningComponentBundle name with its
             LastModifiedDate, the names of each type in WATCHED, and the CLI version
  cleanup    remove exactly the prefixed ApexClass and LightningComponentBundle items this run created (absent from before.json),
             then verify the org against the snapshot: the name sets of every recorded type and the dates of the baseline items
  project    the Salesforce DX project in the current directory has the files the request names, and they do what it asks
  deployed   the org holds the engine, controller, a test class and the component
  tests      run the SLChess*Test classes in the org; all must pass, at least --min-tests of them
  rules      independent oracle: harness-owned anonymous Apex compares the engine and the controller with published perft counts,
             literal start-position answers and the mate/stalemate cases; the last line sums up and names the failed markers
  selftest   rehearsal: deploy a probe class and component, test it, run anonymous Apex against it and remove it again (real org:
             main session only)

Safety (the owner's rules for this case):
  * Every `sf` call resolves `sf` from PATH (so a test can substitute a fake) and names `--target-org <alias>` explicitly,
    except `sf org list` and `sf --version`, which have no target.
  * `sf org display` is never called; no credential is read, stored, passed to a model or printed. Anything that comes back
    from `sf` and is printed or written passes through scrub() first.
  * cleanup deletes only ApexClass names that start with the exact, case-sensitive prefix and LightningComponentBundle names
    that start with the prefix in component spelling (SLChess -> slChess), and only when they are absent from before.json. It never
    uses a wildcard, and exits 0 only after queries show every recorded name set equal to the snapshot and no baseline Apex class
    or bundle modified. Items of any other recorded type that differ are reported to remove by hand and fail the cleanup.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
    return [r[field] for r in records(org, soql, tooling)]


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


# Metadata a run could leave in the org besides Apex classes and bundles, which cleanup does not remove: (type, name field, Tooling
# API, extra WHERE). Each query was measured on the real Developer Edition org. The snapshot records every type's names, cleanup
# compares them by set (the org's baseline holds tabs, pages and applications of its own), and preflight refuses a prefixed one.
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
OWN_TYPES = ("ApexClass", "LightningComponentBundle")  # the two types cleanup removes from


def watched_names(org: str, spec: tuple, like_prefix: str | None = None) -> list[str]:
    kind, field, tooling, base = spec
    where = [c for c in (base, "%s LIKE '%s%%'" % (field, like_prefix) if like_prefix else "") if c]
    return sorted(query(org, "SELECT %s FROM %s%s" % (field, kind, " WHERE " + " AND ".join(where) if where else ""), field, tooling))


def with_prefix(found: dict[str, list[str]], prefix: str) -> list[str]:
    """`Type name` for every name that carries the case prefix exactly: the Apex spelling for ApexClass, the component spelling for
    LightningComponentBundle, either for the other types (a tab or page may follow either convention)."""
    spelling = {"ApexClass": (prefix,), "LightningComponentBundle": (lwc_prefix(prefix),)}
    return ["%s %s" % (kind, n) for kind, names in found.items() for n in names if n.startswith(spelling.get(kind, (prefix, lwc_prefix(prefix))))]


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


def do_preflight(org: str, prefix: str) -> tuple[bool, str]:
    status = org_status(org)
    if status is None:
        return False, "org alias %r is not in `sf org list`" % org
    if status != "Connected":
        return False, "org alias %r is not connected (connectedStatus=%s)" % (org, status)
    apex, lwc = prefixed(org, prefix)
    found, skipped = {"ApexClass": apex, "LightningComponentBundle": lwc}, []
    for spec in WATCHED:
        try:
            found[spec[0]] = watched_names(org, spec, prefix)
        except SfError:
            skipped.append(spec[0])  # an edition without that object: nothing there to be dirty
    dirty = with_prefix(found, prefix)
    if dirty:
        return False, "org %r is not clean: found %s before the run; nothing was deployed" % (org, ", ".join(dirty))
    return True, "org %r connected; no %s*/%s* item in %d metadata types%s" % (
        org, prefix, lwc_prefix(prefix), len(found), "; not queryable here: " + ", ".join(skipped) if skipped else "")


# ------------------------------------------------------------------------------------------------------------ snapshot

def read_org(org: str) -> dict:
    """The org as the snapshot records it: names of ApexClass, LightningComponentBundle and every WATCHED type, the LastModifiedDate of
    each Apex class and bundle, and the WATCHED types whose query failed (an edition without the object). A failed Apex class or
    bundle query raises: without those two the run cannot be told apart from the baseline."""
    dates = {"ApexClass": {r["Name"]: r.get("LastModifiedDate") for r in records(org, "SELECT Name, LastModifiedDate FROM ApexClass")},
             "LightningComponentBundle": {r["DeveloperName"]: r.get("LastModifiedDate") for r in records(
                 org, "SELECT DeveloperName, LastModifiedDate FROM LightningComponentBundle")}}
    names, unavailable = {kind: sorted(by_name) for kind, by_name in dates.items()}, {}
    for spec in WATCHED:
        try:
            names[spec[0]] = watched_names(org, spec)
        except SfError as exc:
            unavailable[spec[0]] = tail(str(exc), 200)
    return {"names": names, "dates": dates, "unavailable": unavailable}


def do_snapshot(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    check_prefix(prefix)
    seen = read_org(org)
    clash = with_prefix(seen["names"], prefix)
    if clash:
        return False, "org %r already holds prefixed metadata (%s); refusing to snapshot a dirty org" % (org, ", ".join(clash))
    names = seen["names"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "before.json").write_text(json.dumps({
        "org": org, "prefix": prefix, "apex_classes": names["ApexClass"], "lightning_component_bundles": names["LightningComponentBundle"],
        "last_modified": seen["dates"], "other_types": {kind: found for kind, found in names.items() if kind not in OWN_TYPES},
        "unavailable": seen["unavailable"], "counts": {kind: len(found) for kind, found in names.items()},
        "tool_versions": {"sf": sf_version()}}, indent=2) + "\n")
    return True, "snapshot of org %r: %s%s -> %s" % (
        org, ", ".join("%d %s" % (len(found), kind) for kind, found in names.items()),
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


def destructive_xml(apex: list[str], lwc: list[str]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<Package xmlns="%s">' % META_NS]
    # Components first: a bundle that imports an Apex class depends on it, and one destructive deploy removes both.
    for kind, names in (("LightningComponentBundle", lwc), ("ApexClass", apex)):
        if names:
            parts.append("    <types>")
            parts += ["        <members>%s</members>" % n for n in names]
            parts += ["        <name>%s</name>" % kind, "    </types>"]
    parts += ["    <version>%s</version>" % API_VERSION, "</Package>", ""]
    return "\n".join(parts)


def empty_package_xml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n<Package xmlns="%s">\n    <version>%s</version>\n</Package>\n' % (META_NS, API_VERSION)


def do_cleanup(org: str, prefix: str, directory: Path) -> tuple[bool, str]:
    check_prefix(prefix)
    record = {"removed": [], "refused": [], "verified": False}
    out = directory / "cleanup.json"

    def finish(ok: bool, message: str, **extra) -> tuple[bool, str]:
        record.update(extra, verified=ok)
        directory.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(scrub(record), indent=2) + "\n")
        return ok, message

    try:
        before = json.loads((directory / "before.json").read_text())
        before_apex, before_lwc = set(before["apex_classes"]), set(before["lightning_component_bundles"])
        if not all(isinstance(before[key], dict) for key in ("last_modified", "other_types", "unavailable")):
            raise TypeError("before.json is not a snapshot of this version")
    except (OSError, ValueError, KeyError, TypeError):
        return finish(False, "no usable %s: refusing to delete anything because the run's new metadata cannot be told apart"
                      % (directory / "before.json"), error="missing before.json")
    found_apex, found_lwc = loose(org, prefix)
    apex_rm, apex_no = plan_removal(found_apex, before_apex, prefix)
    lwc_rm, lwc_no = plan_removal(found_lwc, before_lwc, lwc_prefix(prefix))
    record["refused"] = [{"type": "ApexClass", "name": n, "reason": r} for n, r in apex_no] + \
                        [{"type": "LightningComponentBundle", "name": n, "reason": r} for n, r in lwc_no]
    deploy_note = ""
    if apex_rm or lwc_rm:
        work = Path(tempfile.mkdtemp(prefix="chess-sf-cleanup-"))
        try:
            (work / "force-app").mkdir()
            (work / "manifest").mkdir()
            (work / "sfdx-project.json").write_text(json.dumps(
                {"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": API_VERSION}))
            (work / "manifest" / "package.xml").write_text(empty_package_xml())
            (work / "manifest" / "destructiveChanges.xml").write_text(destructive_xml(apex_rm, lwc_rm))
            doc = sf(["project", "deploy", "start", "--manifest", str(work / "manifest" / "package.xml"),
                      "--post-destructive-changes", str(work / "manifest" / "destructiveChanges.xml"), "--wait", "10"],
                     org, timeout=900, cwd=str(work))
            if doc.get("status") != 0:
                deploy_note = "destructive deploy failed: %s" % tail(str(doc.get("message") or doc.get("name") or doc))
            else:
                record["removed"] = [{"type": "ApexClass", "name": n} for n in apex_rm] + \
                                    [{"type": "LightningComponentBundle", "name": n} for n in lwc_rm]
        except SfError as exc:
            deploy_note = str(exc)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    try:
        now = read_org(org)
    except SfError as exc:
        return finish(False, "%s; could not verify afterwards: %s" % (deploy_note or "deploy ran", exc), error=str(exc))
    diff = compare(before, now)
    record.update({key: diff[key] for key in ("extra", "missing", "modified", "unverified", "covered", "not_covered")})
    if any(diff[key] for key in ("extra", "missing", "modified", "unverified")):
        return finish(False, "%sorg differs from the before snapshot: %s" % (deploy_note + "; " if deploy_note else "", describe(diff)))
    removed = [r["name"] for r in record["removed"]]
    return finish(True, "cleanup verified: org %r matches the before snapshot by name on %s; LastModifiedDate unchanged on %d baseline "
                  "ApexClass and LightningComponentBundle items%s; removed %s" % (
                      org, ", ".join("%s %d" % (kind, n) for kind, n in diff["covered"].items()), diff["dates_checked"],
                      "; not covered (query failed at the snapshot): " + ", ".join(diff["not_covered"]) if diff["not_covered"] else "",
                      ", ".join(removed) or "nothing"))


def compare(before: dict, now: dict) -> dict:
    """The org now against the snapshot. extra, missing and modified are {type: [...]}; unverified is a recorded type that cannot be
    queried now (fail closed); not_covered are the types the snapshot could not query (skipped); covered is {type: count}."""
    diff = {"extra": {}, "missing": {}, "modified": {}, "unverified": {}, "covered": {}, "not_covered": dict(before["unavailable"]),
            "dates_checked": 0}
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
                    diff["modified"].setdefault(kind, []).append("%s (%s -> %s)" % (name, date, current[name]))
    return diff


def describe(diff: dict) -> str:
    parts = []
    for kind, names in diff["extra"].items():
        if kind in OWN_TYPES:
            parts.append("extra %s %s" % (kind, ", ".join(names)))
        else:
            parts.append("not removable by this cleanup: remove by hand: %s %s" % (kind, ", ".join(names)))
    parts += ["missing since the snapshot: %s %s" % (kind, ", ".join(names)) for kind, names in diff["missing"].items()]
    parts += ["modified since the snapshot: %s %s" % (kind, ", ".join(names)) for kind, names in diff["modified"].items()]
    parts += ["could not verify %s (query failed: %s)" % (kind, why) for kind, why in diff["unverified"].items()]
    return "; ".join(parts)


# ------------------------------------------------------------------------------------------------------------- project

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
        problems += ["%sController.cls declares no static method %s" % (prefix, m) for m in ("legalMoves", "applyMove")
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
        for meta in app.rglob("*-meta.xml"):
            parts = meta.relative_to(app).parts
            if "classes" not in parts and "lwc" not in parts:
                problems.append("other metadata %s (the request allows only Apex classes and the component)" % "/".join(parts))
    if problems:
        return False, "; ".join(problems)
    return True, "project ok: %d Apex classes, %d lwc bundles" % (len(classes), len(bundles))


# ------------------------------------------------------------------------------------------------------------ deployed

def test_class_names(org: str, prefix: str) -> list[str]:
    check_prefix(prefix)
    names = apex_names(org, " WHERE Name LIKE '%s%%Test'" % prefix)
    return sorted(n for n in names if n.startswith(prefix) and n.endswith("Test"))


def do_deployed(org: str, prefix: str, classes: list[str], lwc: list[str], min_test_classes: int) -> tuple[bool, str]:
    check_prefix(prefix)
    apex = set(apex_names(org, " WHERE Name LIKE '%s%%'" % prefix))
    bundles = set(lwc_names(org, " WHERE DeveloperName LIKE '%s%%'" % lwc_prefix(prefix)))
    tests = test_class_names(org, prefix)
    problems = ["ApexClass %s not found in org %r" % (n, org) for n in classes if n not in apex]
    problems += ["LightningComponentBundle %s not found in org %r" % (n, org) for n in lwc if n not in bundles]
    if len(tests) < min_test_classes:
        problems.append("%d %s*Test classes in the org, need %d" % (len(tests), prefix, min_test_classes))
    if problems:
        return False, "; ".join(problems)
    return True, "deployed: %s; %s; test classes: %s" % (", ".join(classes) or "-", ", ".join(lwc) or "-", ", ".join(tests) or "-")


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
        for marker, value in RESULT_LINE.findall(result.get("logs") or ""):
            seen.setdefault(marker, value.strip())
    return err, seen, result.get("logs") or ""


def do_rules(org: str, raw_dir: Path | None = None) -> tuple[bool, list[str]]:
    lines, failed, total, raw = [], [], 0, ""
    work = Path(tempfile.mkdtemp(prefix="chess-sf-rules-"))
    try:
        for name, script, marks in rule_cases():
            err, seen, logs = run_apex(org, work, name, script)
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

def write_probe(root: Path, prefix: str) -> tuple[str, str, str]:
    """A trivial class, its test and a component that imports the class, all carrying the case prefix. Returns their names."""
    base = root / "force-app" / "main" / "default"
    klass, test, bundle = prefix + "Probe", prefix + "ProbeTest", lwc_prefix(prefix) + "Probe"
    (base / "classes").mkdir(parents=True)
    meta = '<?xml version="1.0" encoding="UTF-8"?>\n<ApexClass xmlns="%s"><apiVersion>%s</apiVersion><status>Active</status></ApexClass>\n'
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
        '<?xml version="1.0" encoding="UTF-8"?>\n<LightningComponentBundle xmlns="%s"><apiVersion>%s</apiVersion>'
        "<isExposed>false</isExposed></LightningComponentBundle>\n" % (META_NS, API_VERSION))
    (root / "sfdx-project.json").write_text(json.dumps(
        {"packageDirectories": [{"path": "force-app", "default": True}], "sourceApiVersion": API_VERSION}))
    return klass, test, bundle


def do_selftest(org: str, prefix: str) -> bool:
    work = Path(tempfile.mkdtemp(prefix="chess-sf-selftest-"))
    snap = work / "platform"
    snapped, all_ok = False, True

    def step(name: str, ok: bool, message: str) -> bool:
        say("%s %s: %s" % ("PASS" if ok else "FAIL", name, message))
        return ok

    try:
        say("selftest proves, in order: preflight (the org is reachable and holds nothing with the prefix), snapshot (its baseline is "
            "recorded), deploy (a class with an @AuraEnabled method and a component that imports it deploy together), deployed (both "
            "are found by query), tests (`apex run test` runs the probe test in the org), apex-run (anonymous Apex calls the class and "
            "its RESULT line is parsed from result.logs exactly as `rules` does), cleanup (both are removed and the org equals its "
            "baseline on every recorded type)")
        ok, msg = do_preflight(org, prefix)
        if not step("preflight", ok, msg):
            return False
        ok, msg = do_snapshot(org, prefix, snap)
        snapped = ok
        if not step("snapshot", ok, msg):
            return False
        project = work / "project"
        klass, test, bundle = write_probe(project, prefix)
        doc = sf(["project", "deploy", "start", "--source-dir", "force-app", "--wait", "10"], org, timeout=900, cwd=str(project))
        result = doc.get("result") or {}
        if not step("deploy", doc.get("status") == 0 and result.get("success") is not False,
                    "status=%s %s" % (result.get("status"), tail(str(doc.get("message") or "")) if doc.get("status") != 0 else "")):
            return False
        ok, msg = do_deployed(org, prefix, [klass, test], [bundle], 1)
        all_ok &= step("deployed", ok, msg)
        ok, lines = do_tests(org, prefix, 1)
        all_ok &= step("tests", ok, "; ".join(lines))
        err, seen, _log = run_apex(org, work, "probe", "System.debug('RESULT|probe|' + %s.two());\n" % klass)
        got = seen.get("probe")
        all_ok &= step("apex-run", not err and got == "2",
                       "RESULT|probe| expected=2 got=%s" % (got if got is not None else (err or "no RESULT line")))
        return all_ok
    except SfError as exc:
        step("selftest", False, str(exc))
        return False
    finally:
        cleanup_failed = False
        if snapped:
            try:
                ok, msg = do_cleanup(org, prefix, snap)
            except BaseException as exc:  # cleanup must report, even when interrupted
                ok, msg = False, "cleanup raised %s" % type(exc).__name__
            step("cleanup", ok, msg)
            if not ok:
                cleanup_failed = True
                say("MANUAL CLEANUP NEEDED: remove %s*/%s* from org %r (destructive deploy of exactly those names)." % (prefix, lwc_prefix(prefix), org))
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
            p.add_argument("--classes")
            p.add_argument("--lwc")
            p.add_argument("--min-test-classes", type=int, default=1)
        if name == "tests":
            p.add_argument("--min-tests", type=int, default=1)
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
            classes = csv(args.classes) if args.classes is not None else [args.prefix + "Engine", args.prefix + "Controller"]
            bundles = csv(args.lwc) if args.lwc is not None else [lwc_prefix(args.prefix) + "Board"]
            ok, msg = do_deployed(args.org, args.prefix, classes, bundles, args.min_test_classes)
        elif args.cmd == "tests":
            ok, lines = do_tests(args.org, args.prefix, args.min_tests)
            msg = "\n".join(lines)
        elif args.cmd == "rules":
            raw_dir = args.platform_dir or os.environ.get("E2E_PLATFORM_DIR")
            ok, lines = do_rules(args.org, Path(raw_dir) if raw_dir else None)
            msg = "\n".join(lines)
        else:
            return 0 if do_selftest(args.org, args.prefix) else 1
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
