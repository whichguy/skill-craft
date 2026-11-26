#!/usr/bin/env python3
"""Guarded `sf` wrapper for the `cloudybot` E2E case (`platform.model_bin`).

Usage:
  cloudybot_sf_guard.py --org <alias> --prefix <Prefix> [--deny-all --name <cmd>] -- <argv...>

Logs every invocation to `$E2E_PLATFORM_DIR/sf-calls.jsonl`, scrubs secrets,
pins `--target-org <org>` and `SF_TARGET_ORG=<org>`, and restricts deploys to
components prefixed with `<prefix>` (or `<lwcPrefix>` for LWC/Aura bundles).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.parse
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
SECRET_FIELD_RE = re.compile(
    r"""(?P<head>(?:%s)(?:\\*["'])?\s*[:=]\s*(?:\\*["'])?)(?P<value>[^\s"'\\,}]+)"""
    % "|".join(SECRET_KEYS)
)
SESSION_RE = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
AUTH_URL_RE = re.compile(r"force://[^\s\"']+")
WILDCARD_RE = re.compile(r"<members>\s*\*\s*</members>")
DECLARATION_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)

LOG_NAME = "sf-calls.jsonl"
ARG_LIMIT = 300
REASON_LIMIT = 2000
SCOPE_WALK = 50000
SCOPE_SHOWN = 5
MANIFEST_LIMIT = 1_000_000
MIN_DEPLOY_WAIT = 5
KILL_GRACE = 5.0
SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)

LOCAL_COMMANDS = {
    ("version",),
    ("help",),
    ("project", "generate"),
    ("lightning", "generate"),
    ("apex", "generate"),
    ("template", "generate"),
    ("org", "list"),
}
PREFIX_LOCAL = {
    ("help",),
    ("project", "generate"),
    ("lightning", "generate"),
    ("apex", "generate"),
    ("template", "generate"),
}
PINNED_COMMANDS = {
    ("org", "list", "metadata"),
    ("org", "list", "metadata-types"),
    ("org", "list", "limits"),
    ("limits", "api", "display"),
    ("sobject", "list"),
    ("sobject", "describe"),
    ("data", "query"),
    ("data", "get", "record"),
    ("project", "deploy", "start"),
    ("project", "deploy", "validate"),
    ("project", "deploy", "report"),
    ("project", "retrieve", "start"),
    ("project", "retrieve", "preview"),
    ("apex", "run"),
    ("apex", "run", "test"),
    ("apex", "get", "test"),
    ("apex", "get", "log"),
    ("apex", "list", "log"),
    ("org", "assign", "permset"),
}
SECRET_REST_OBJECTS = (
    "NamedCredential",
    "ExternalCredential",
    "NamedPrincipal",
    "ExternalAuthIdentityProvider",
    "AuthProvider",
    "ConnectedApplication",
    "OauthToken",
    "TwoFactorInfo",
    "SessionPermSetActivation",
)
SECRET_REST_OBJECT_RE = re.compile(r"\b(?:" + "|".join(SECRET_REST_OBJECTS) + r")\b", re.IGNORECASE)
ALLOWED_DATA_REST_RE = re.compile(
    r"^/services/data(?:"
    r"|/v\d+\.\d+(?:"
    r"|/limits"
    r"|/sobjects(?:/[A-Za-z][A-Za-z0-9_]*/describe)?"
    r"|/tooling(?:"
    r"|/sobjects(?:/[A-Za-z][A-Za-z0-9_]*/describe|/ApexLog/[A-Za-z0-9]{15,18}/Body)?"
    r"|/query(?:/[A-Za-z0-9_-]+)?"
    r")"
    r")"
    r")$"
)
APEXREST_RE = re.compile(r"^/services/apexrest/([A-Za-z0-9_.-]+)(?:/.*)?$")
HELP_ONLY = {("--version",), ("-v",), ("--help",), ("-h",)}
HELP_FLAGS = ("--help", "-h")

DENY_REASONS = [
    (("org", "display"), "shows the org's access token"),
    (("org", "open"), "prints a login URL carrying a session id"),
    (("org", "login"), "changes org authentication"),
    (("org", "logout"), "signs out"),
    (("org", "create"), "creates an org"),
    (("org", "delete"), "deletes an org"),
    (("auth",), "changes authorization"),
    (("login",), "signs in"),
    (("logout",), "signs out"),
    (("config",), "reads or changes CLI configuration"),
    (("alias",), "reads or changes aliases"),
    (("plugins",), "modifies CLI plugins"),
    (("update",), "updates CLI"),
    (("project", "delete"), "deletes metadata in the org"),
    (("project", "deploy", "quick"), "uses global deploy cache without pinning target org"),
    (("project", "deploy", "cancel"), "uses global deploy cache without pinning target org"),
    (("project", "deploy", "resume"), "uses global deploy cache without pinning target org"),
    (("data", "delete"), "deletes records"),
    (("data", "create"), "writes records"),
    (("data", "update"), "writes records"),
    (("data", "upsert"), "writes records"),
    (("data", "import"), "writes records"),
    (("data", "export"), "exports bulk records"),
    (("data", "bulk"), "writes bulk records"),
]


def camel_prefix(prefix: str) -> str:
    match = re.match(r"^([A-Z]+)(?=[A-Z][a-z])|^([A-Z]+)$", prefix)
    if match:
        head = match.group(1) or match.group(2)
        return head.lower() + prefix[len(head):]
    return prefix[:1].lower() + prefix[1:]


def scrub(text: str) -> str:
    text = SECRET_FIELD_RE.sub(r'\g<head>[redacted]', text)
    text = AUTH_URL_RE.sub("[redacted]", text)
    return SESSION_RE.sub("[redacted]", text)


def log_path() -> Path | None:
    pdir = os.environ.get("E2E_PLATFORM_DIR")
    return Path(pdir) / LOG_NAME if pdir else None


def append_log(record: dict) -> bool:
    path = log_path()
    if path is None:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def split_tokens(argv: list[str]) -> tuple[list[str], list[str]]:
    """Return (leading_command_words, flags_and_rest) stopping at first flag."""
    words: list[str] = []
    for idx, tok in enumerate(argv):
        if tok == "--" or tok.startswith("-"):
            return words, argv[idx:]
        words.append(tok)
    return words, []


def extract_flag_values(argv: list[str], names: tuple[str, ...]) -> list[str]:
    vals: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        matched = False
        for name in names:
            if tok == name:
                if i + 1 < len(argv):
                    vals.append(argv[i + 1])
                i += 2
                matched = True
                break
            if tok.startswith(name + "="):
                vals.append(tok.split("=", 1)[1])
                i += 1
                matched = True
                break
        if not matched:
            i += 1
    return vals


def has_any_flag(argv: list[str], flags: tuple[str, ...]) -> str | None:
    for tok in argv:
        for flag in flags:
            if tok == flag or tok.startswith(flag + "="):
                return flag
    return None


def component_allowed(rel: Path, prefix: str, lwc_prefix: str) -> bool:
    parts = rel.parts
    if not parts:
        return False
    # Ignore gitkeep / hidden metadata placeholders
    if rel.name == ".gitkeep" or rel.name.startswith("."):
        return True
    # Locate the metadata type directory (e.g. main/default/<type>/... or direct <type>/...)
    type_dirs = {
        "lwc", "aura", "objects", "customMetadata", "classes", "triggers",
        "tabs", "applications", "flexipages", "permissionsets", "permissionsetgroups",
        "groups", "sharingRules", "platformEventSubscriberConfigs", "namedCredentials",
        "externalCredentials", "flows", "staticresources", "labels",
        "customPermissions", "remoteSiteSettings", "cspTrustedSites",
        "corsWhitelistOrigins", "quickActions", "layouts",
    }
    idx = None
    for i, part in enumerate(parts):
        if part in type_dirs:
            idx = i
            break
    if idx is None:
        # Unknown folder inside source tree: require stem to carry prefix
        return parts[-1].startswith(prefix) or parts[-1].startswith(lwc_prefix)

    kind = parts[idx]
    rest = parts[idx + 1:]
    if not rest:
        return True
    if kind in ("lwc", "aura"):
        bundle = rest[0]
        if bundle.startswith("."):
            return True
        return bundle.startswith(lwc_prefix)
    if kind == "objects":
        obj_name = rest[0]
        return obj_name.startswith(prefix)
    if kind == "customMetadata":
        return rest[0].startswith(prefix)
    return rest[0].startswith(prefix)


def check_source_dir(directory: Path, root: Path, prefix: str, lwc_prefix: str) -> str | None:
    try:
        resolved = directory.resolve()
        if resolved != root and root not in resolved.parents:
            return f"source path {directory} escapes project directory"
    except OSError as exc:
        return f"cannot resolve source path {directory}: {exc}"
    if not resolved.exists():
        return f"source path does not exist: {directory}"
    files = [resolved] if resolved.is_file() else []
    if resolved.is_dir():
        count = 0
        for p in resolved.rglob("*"):
            count += 1
            if count > SCOPE_WALK:
                return f"source tree exceeds {SCOPE_WALK} entries"
            if p.is_file():
                files.append(p)
    bad: list[str] = []
    for f in files:
        try:
            rel = f.resolve().relative_to(root)
        except ValueError:
            bad.append(str(f))
            continue
        if not component_allowed(rel, prefix, lwc_prefix):
            bad.append(rel.as_posix())
            if len(bad) >= SCOPE_SHOWN:
                break
    if bad:
        return "deploy includes unprefixed components outside " + prefix + ": " + ", ".join(bad)
    return None


def member_allowed(kind: str, member: str, prefix: str, lwc_prefix: str) -> bool:
    if not member or "*" in member:
        return False
    if kind in ("LightningComponentBundle", "AuraDefinitionBundle"):
        return member.startswith(lwc_prefix)
    if "." in member and kind in (
        "CustomField", "ListView", "ValidationRule", "WebLink", "CompactLayout",
        "FieldSet", "RecordType", "BusinessProcess", "CustomMetadata",
        "SharingCriteriaRule", "SharingOwnerRule",
    ):
        head = member.split(".", 1)[0]
        return head.startswith(prefix)
    return member.startswith(prefix)


def check_manifest(manifest_path: Path, root: Path, prefix: str, lwc_prefix: str) -> str | None:
    try:
        resolved = manifest_path.resolve()
        if resolved != root and root not in resolved.parents:
            return f"manifest path {manifest_path} escapes project directory"
        data = resolved.read_bytes()
    except OSError as exc:
        return f"cannot read manifest {manifest_path}: {exc}"
    if len(data) > MANIFEST_LIMIT:
        return f"manifest exceeds {MANIFEST_LIMIT} bytes"
    text = data.decode("utf-8", errors="replace")
    if DECLARATION_RE.search(text):
        return "manifest contains forbidden DOCTYPE/ENTITY declaration"
    if WILDCARD_RE.search(text):
        return "manifest contains forbidden wildcard <members>*</members>"
    try:
        tree = ET.fromstring(text)
    except ET.ParseError as exc:
        return f"invalid manifest XML: {exc}"
    ns = ""
    if tree.tag.startswith("{"):
        ns = tree.tag[: tree.tag.index("}") + 1]
    bad: list[str] = []
    for types_el in tree.findall(f"{ns}types"):
        name_el = types_el.find(f"{ns}name")
        kind = name_el.text.strip() if name_el is not None and name_el.text else ""
        for mem_el in types_el.findall(f"{ns}members"):
            mem = (mem_el.text or "").strip()
            if not member_allowed(kind, mem, prefix, lwc_prefix):
                bad.append(f"{kind}:{mem}")
                if len(bad) >= SCOPE_SHOWN:
                    break
        if len(bad) >= SCOPE_SHOWN:
            break
    if bad:
        return f"manifest names unprefixed members outside {prefix}: {', '.join(bad)}"
    return None


def check_deploy_scope(argv: list[str], prefix: str, lwc_prefix: str) -> str | None:
    if has_any_flag(argv, ("--async",)):
        return "deploy must run synchronously (--async is forbidden)"
    wait_vals = extract_flag_values(argv, ("--wait", "-w"))
    for w in wait_vals:
        if not re.fullmatch(r"\d+", w) or int(w) < MIN_DEPLOY_WAIT:
            return f"--wait must be an integer >= {MIN_DEPLOY_WAIT} minutes"
    root = Path.cwd().resolve()
    manifests = extract_flag_values(argv, ("--manifest", "-x"))
    metadata_entries = extract_flag_values(argv, ("--metadata", "-m"))
    source_dirs = extract_flag_values(argv, ("--source-dir", "-d"))
    for mpath in manifests:
        err = check_manifest(Path(mpath), root, prefix, lwc_prefix)
        if err:
            return err
    for entry in metadata_entries:
        # e.g. ApexClass:CloudyBotFoo or LightningComponentBundle:cloudyBotChat
        if ":" in entry:
            kind, mem = entry.split(":", 1)
            if not member_allowed(kind, mem, prefix, lwc_prefix):
                return f"--metadata {entry!r} is outside prefix {prefix}"
        else:
            if not (entry.startswith(prefix) or entry.startswith(lwc_prefix)):
                return f"--metadata {entry!r} must name prefixed type:member under {prefix}"
    if source_dirs:
        for sdir in source_dirs:
            err = check_source_dir(Path(sdir), root, prefix, lwc_prefix)
            if err:
                return err
    elif not manifests and not metadata_entries:
        proj = root / "sfdx-project.json"
        if not proj.is_file():
            return "default deploy requires sfdx-project.json in current working directory"
        try:
            cfg = json.loads(proj.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return f"cannot parse sfdx-project.json: {exc}"
        dirs = [d.get("path") for d in (cfg.get("packageDirectories") or []) if isinstance(d, dict) and d.get("path")]
        if not dirs:
            return "sfdx-project.json has no packageDirectories"
        for d in dirs:
            err = check_source_dir(root / d, root, prefix, lwc_prefix)
            if err:
                return err
    return None


def check_api_request_rest(rest_argv: list[str], prefix: str, lwc_prefix: str) -> str | None:
    forbidden_flags = ("--file", "-f", "--stream-to-file", "-S", "--include", "-i")
    bad_rest_flag = has_any_flag(rest_argv, forbidden_flags)
    if bad_rest_flag:
        return f"`api request rest` forbids {bad_rest_flag}"

    value_flags = ("--target-org", "-o", "--method", "-X", "--header", "-H", "--body", "-b", "--api-version")
    bool_flags = ("--json",)
    urls: list[str] = []
    methods: list[str] = []
    headers: list[str] = []
    bodies: list[str] = []

    i = 0
    while i < len(rest_argv):
        tok = rest_argv[i]
        if tok in bool_flags:
            i += 1
            continue
        matched_val = False
        for vf in value_flags:
            if tok == vf:
                if i + 1 >= len(rest_argv):
                    return f"`api request rest` flag {vf} requires a value"
                val = rest_argv[i + 1]
                i += 2
                matched_val = True
            elif tok.startswith(vf + "="):
                val = tok.split("=", 1)[1]
                i += 1
                matched_val = True
            else:
                continue
            if vf in ("--method", "-X"):
                methods.append(val)
            elif vf in ("--header", "-H"):
                headers.append(val)
            elif vf in ("--body", "-b"):
                bodies.append(val)
            break
        if matched_val:
            continue
        if tok.startswith("-"):
            return f"unsupported flag {tok} for `api request rest`"
        urls.append(tok)
        i += 1

    if not urls:
        return "`api request rest` requires a relative Salesforce API endpoint"
    if len(urls) > 1:
        return "`api request rest` accepts exactly one endpoint argument"

    for hdr in headers:
        hname = hdr.split(":", 1)[0].strip().lower()
        if hname in ("authorization", "cookie", "proxy-authorization", "x-sfdc-session"):
            return f"`api request rest` forbids custom {hname} header"

    norm_methods = {m.strip().upper() for m in methods if m.strip()}
    if len(norm_methods) > 1:
        return "conflicting --method values for `api request rest`"
    method = next(iter(norm_methods), "GET")

    root = Path.cwd().resolve()
    for body in bodies:
        if body == "-":
            return "`api request rest` forbids reading --body from stdin ('-')"
        if body.startswith("@"):
            bpath = Path(body[1:])
            try:
                resolved = bpath.resolve()
                if resolved != root and root not in resolved.parents:
                    return f"`api request rest` --body file {bpath} escapes project directory"
            except OSError as exc:
                return f"cannot resolve `api request rest` --body file {bpath}: {exc}"

    raw_url = urls[0].strip()
    if not raw_url or "://" in raw_url or raw_url.startswith("//") or re.search(r"[\s\x00-\x1f\x7f\\@#]", raw_url):
        return f"`api request rest` requires a relative org path (got {raw_url!r})"

    norm_url = "/" + raw_url.lstrip("/")
    path_part, _, query_part = norm_url.partition("?")
    if re.search(r"%(?:2e|2f|5c|00)", path_part, re.IGNORECASE):
        return f"`api request rest` forbids percent-encoded path traversal in {raw_url!r}"
    decoded_path = urllib.parse.unquote(path_part)
    if "\\" in decoded_path or "\x00" in decoded_path or ".." in decoded_path.split("/"):
        return f"`api request rest` forbids path traversal in {raw_url!r}"
    clean_path = re.sub(r"/+", "/", decoded_path).rstrip("/") or "/"

    apex_match = APEXREST_RE.fullmatch(clean_path)
    if apex_match:
        seg = apex_match.group(1)
        if not (seg.startswith(prefix) or seg.startswith(lwc_prefix)):
            return f"apexrest endpoint {clean_path!r} is outside prefix {prefix}"
        if method not in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"):
            return f"HTTP method {method} is not allowed for `api request rest`"
        if method in ("GET", "HEAD") and bodies:
            return f"`api request rest` {method} forbids --body"
        return None

    if not ALLOWED_DATA_REST_RE.fullmatch(clean_path):
        return (
            f"REST endpoint {clean_path!r} is not in the allow list "
            f"(allowed: GET /services/data[/vX.Y/(limits|sobjects|tooling/...)], or /services/apexrest/{prefix}/*)"
        )
    if method not in ("GET", "HEAD"):
        return f"REST endpoint {clean_path!r} allows GET/HEAD only (got {method})"
    if bodies:
        return f"`api request rest` {method} forbids --body"
    decoded_query = urllib.parse.unquote_plus(query_part)
    secret_hit = SECRET_REST_OBJECT_RE.search(decoded_path) or SECRET_REST_OBJECT_RE.search(decoded_query)
    if secret_hit:
        return f"`api request rest` forbids reading credential/session object `{secret_hit.group(0)}`"
    return None


def decide(argv: list[str], org: str, prefix: str, deny_all: bool, cmd_name: str) -> tuple[bool, str]:
    if deny_all:
        return False, f"{cmd_name} is disabled during guarded CloudyBot runs"
    if not argv:
        return True, "help"
    if tuple(argv) in HELP_ONLY:
        return True, "help"
    if "--" in argv:
        return False, "bare '--' is forbidden"
    bad_flag = has_any_flag(
        argv,
        (
            "--post-destructive-changes",
            "--pre-destructive-changes",
            "--metadata-dir",
            "--flags-dir",
            "--sfdx-url-file",
            "-u",
            "--u",
            "--targetusername",
            "--fromorg",
            "--from-org",
        ),
    )
    if bad_flag:
        return False, f"flag {bad_flag} is forbidden"

    words, rest = split_tokens(argv)
    if not words:
        return False, "flags without a command are not allowed"
    cmd = tuple(words)

    for denied_prefix, why in DENY_REASONS:
        if cmd[: len(denied_prefix)] == denied_prefix:
            return False, f"`{' '.join(denied_prefix)}` {why}"

    is_help = any(flag in argv for flag in HELP_FLAGS)

    # Local commands
    if cmd in LOCAL_COMMANDS or any(cmd[: len(p)] == p for p in PREFIX_LOCAL):
        return True, "local command"

    is_api_rest = cmd[:3] == ("api", "request", "rest")
    if not is_api_rest and cmd not in PINNED_COMMANDS:
        return False, f"`{' '.join(cmd)}` is not in the allow list"

    if is_help:
        return True, "help for allowed command"

    # Pinned org check
    target_vals = extract_flag_values(argv, ("--target-org", "-o"))
    if not target_vals:
        return False, f"missing `--target-org {org}`"
    if any(v != org for v in target_vals):
        return False, f"target org must be `{org}` (got {target_vals!r})"

    lwc_prefix = camel_prefix(prefix)
    if is_api_rest:
        rest_err = check_api_request_rest(argv[3:], prefix, lwc_prefix)
        if rest_err:
            return False, rest_err
        return True, "allowed"

    if cmd == ("project", "deploy", "report"):
        if has_any_flag(argv, ("--use-most-recent", "-r")):
            return False, "`project deploy report` forbids --use-most-recent / -r"
        if not extract_flag_values(argv, ("--job-id", "-i")):
            return False, "`project deploy report` requires --job-id"

    if cmd in (("project", "deploy", "start"), ("project", "deploy", "validate")):
        err = check_deploy_scope(argv, prefix, lwc_prefix)
        if err:
            return False, err

    if cmd == ("org", "assign", "permset"):
        if has_any_flag(argv, ("--on-behalf-of", "-b")):
            return False, "`org assign permset` forbids --on-behalf-of"
        names = extract_flag_values(argv, ("--name", "-n"))
        if not names:
            return False, "`org assign permset` requires --name"
        for n in names:
            if not re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9_]*", n):
                return False, f"permission set {n!r} must start with {prefix!r}"

    return True, "allowed"


def find_real_sf() -> str | None:
    excluded = set()
    for var in ("E2E_MODEL_BIN_DIR",):
        if os.environ.get(var):
            excluded.add(Path(os.environ[var]).resolve())
    if os.environ.get("E2E_PLATFORM_DIR"):
        excluded.add((Path(os.environ["E2E_PLATFORM_DIR"]) / "bin").resolve())
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            d = Path(entry).resolve()
        except OSError:
            continue
        if d in excluded:
            continue
        candidate = d / "sf"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def main() -> int:
    argv_raw = sys.argv[1:]
    if "--" in argv_raw:
        sep = argv_raw.index("--")
        guard_args = argv_raw[:sep]
        model_argv = argv_raw[sep + 1 :]
    else:
        guard_args = argv_raw
        model_argv = []

    org = ""
    prefix = ""
    deny_all = False
    cmd_name = "sf"
    i = 0
    while i < len(guard_args):
        tok = guard_args[i]
        if tok == "--org" and i + 1 < len(guard_args):
            org = guard_args[i + 1]
            i += 2
        elif tok == "--prefix" and i + 1 < len(guard_args):
            prefix = guard_args[i + 1]
            i += 2
        elif tok == "--deny-all":
            deny_all = True
            i += 1
        elif tok == "--name" and i + 1 < len(guard_args):
            cmd_name = guard_args[i + 1]
            i += 2
        else:
            sys.stderr.write(f"sf_guard: unknown guard flag {tok}\n")
            return 2

    if not org or not prefix:
        sys.stderr.write("sf_guard: --org and --prefix are required\n")
        return 2

    call_id = uuid.uuid4().hex[:12]
    allowed, reason = decide(model_argv, org, prefix, deny_all, cmd_name)

    entry = {
        "id": call_id,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "argv": [scrub(a)[:ARG_LIMIT] for a in model_argv],
        "decision": "allow" if allowed else "deny",
        "reason": scrub(reason)[:REASON_LIMIT],
    }
    if cmd_name != "sf":
        entry["name"] = cmd_name

    if not append_log(entry):
        sys.stderr.write(f"{cmd_name}: denied by this run's guard: failed to write guard log\n")
        return 2

    if not allowed:
        sys.stderr.write(f"{cmd_name}: denied by this run's guard: {scrub(reason)}\n")
        if not deny_all:
            sys.stderr.write(
                f"Allowed: org `{org}`, prefix `{prefix}` (LWC `{camel_prefix(prefix)}`), "
                "commands: org list/metadata/limits, sobject, data query, api request rest (scoped), "
                "project deploy start/validate/report, apex run/run test/get test/log, org assign permset.\n"
            )
        return 2

    real_sf = find_real_sf()
    if not real_sf:
        sys.stderr.write("sf: real sf executable not found on PATH\n")
        return 127

    child_env = dict(os.environ)
    for var in ("SFDX_DEFAULTUSERNAME", "SF_TARGET_DEV_HUB", "SFDX_DEFAULTDEVHUBUSERNAME"):
        child_env.pop(var, None)
    child_env["SF_TARGET_ORG"] = org

    proc = subprocess.Popen(
        [real_sf, *model_argv],
        env=child_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    interrupted = False

    def forward(signum, _frame):
        nonlocal interrupted
        interrupted = True
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass

    prev = {}
    for sig in SIGNALS:
        prev[sig] = signal.signal(sig, forward)
    try:
        stdout, stderr = proc.communicate()
    except KeyboardInterrupt:
        interrupted = True
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
    finally:
        for sig, handler in prev.items():
            signal.signal(sig, handler)

    if stdout:
        sys.stdout.write(scrub(stdout))
    if stderr:
        sys.stderr.write(scrub(stderr))

    append_log(
        {
            "id": call_id,
            "end": True,
            "returncode": 143 if interrupted else proc.returncode,
            "stderr_head": scrub(stderr or "")[:200],
            "interrupted": interrupted,
        }
    )
    return 143 if interrupted else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
