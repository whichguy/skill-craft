#!/usr/bin/env python3
"""A guarded `sf` for the model's PATH: the Salesforce policy behind the harness's `platform.model_bin`.

The harness writes an executable `sf` into <output>/platform/bin and puts that directory first on the model's PATH. The script
runs this file with the real HOME (so the real CLI can reach its login in the macOS keychain, which a throwaway HOME hides):

    sf_guard.py --org de --prefix SLChess [--deny-all] [--] <the model's argv...>

Policy (default deny; the isolated HOME is hygiene, not a boundary, so this is what keeps the model to the one org):

  * DENIED, no call to the real sf, exit 2 and a one-line reason on stderr: anything that shows or changes credentials or the CLI's
    own configuration (`org display|login|logout|create|delete`, `auth`, `login`, `logout`, `config`, `alias`, `plugins`, `update`,
    `org open`, `sfdxAuthUrl`, `--sfdx-url-file`), data writes (`data delete|create|update|upsert|import|export|bulk`), `project
    delete`, any deploy with `--post-destructive-changes`, `--pre-destructive-changes`, `--metadata-dir` or a manifest holding
    `<members>*</members>`, `--flags-dir` on any command (the CLI reads flag values from that directory after this check, so the
    call could not be judged), a bare `--`, and every command not in ALLOW (the refusal lists what is allowed).
  * PINNED: a command that talks to an org must carry `--target-org <org>` (or `-o <org>`), every occurrence equal to the case's
    org; a missing or different one is refused, so no command falls back to the default org.
  * SCOPED: `project deploy start|validate` may carry only the components the owner approved: Apex classes named <prefix>* and LWC
    bundles named <lwcPrefix>* (SLChess -> slChess). Every `--source-dir` tree, `--metadata` entry and
    `--manifest` is checked (with none of them, the `packageDirectories` of sfdx-project.json in the working directory); anything
    else, a path that leaves the working directory, or an unreadable manifest is refused with what to change.
  * LOCAL commands (`--version`, `--help`, `help`, `project generate`, `lightning generate`, `apex generate`, `template generate`,
    `org list`) pass unchanged. `--help` or `-h` after an allowed command, or a group of allowed commands, passes too, without
    `--target-org`: the CLI prints help and runs nothing. A denied command stays denied with `--help`.
  * `--deny-all` makes this a stand-in that denies everything (the harness uses it to cover `sfdx`, which would bypass the policy).

Every call appends a DECISION line to $E2E_PLATFORM_DIR/sf-calls.jsonl before anything runs (call id, timestamp, scrubbed argv,
decision and reason), and an allowed call appends an END line when the real sf has finished (the same call id, `"end": true`, the
exit code, the first 200 characters of scrubbed stderr, `interrupted`). The calls are the lines without an `end` key. A call that
cannot be logged is denied. SIGTERM and SIGHUP while the real sf runs are forwarded to it, logged as `interrupted` and exit 143.
stdout is never logged. The real sf's output is captured, so it reaches the model when the command ends, not as it runs; its exit
code passes through unchanged apart from the scrub: a value of accessToken/refreshToken/clientSecret/sfdxAuthUrl and any string
shaped like a session token become `[redacted]`.

The real sf is the first `sf` on PATH outside the wrapper's own directory ($E2E_MODEL_BIN_DIR and $E2E_PLATFORM_DIR/bin), so the
wrapper never calls itself; in hermetic tests that `sf` is test/shiploop_e2e/fake_sf.py.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
SECRET_FIELD_RE = re.compile(r"""(?P<head>(?:%s)(?:\\*["'])?\s*[:=]\s*(?:\\*["'])?)(?P<value>[^\s"'\\,}]+)""" % "|".join(SECRET_KEYS))
SESSION_RE = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
AUTH_URL_RE = re.compile(r"force://[^\s\"']+")
WILDCARD_RE = re.compile(r"<members>\s*\*\s*</members>")
LOG_NAME = "sf-calls.jsonl"
ARG_LIMIT = 300  # characters of one argument kept in the log
KILL_GRACE = 5.0  # seconds a signalled sf gets to exit before it is killed
SCOPE_SHOWN = 5  # out-of-scope files a refusal names
SCOPE_WALK = 50000  # entries one deploy may make the guard look at before it is refused as too large

# (command words) -> exact match unless listed in PREFIX_OK. Org-talking commands are PINNED; the rest are LOCAL.
PINNED = {
    ("project", "deploy", "start"), ("project", "deploy", "validate"), ("project", "deploy", "report"),
    ("project", "deploy", "quick"), ("project", "deploy", "cancel"), ("project", "deploy", "resume"),
    ("project", "retrieve", "start"), ("project", "retrieve", "preview"),
    ("apex", "run"), ("apex", "run", "test"), ("apex", "get", "test"), ("apex", "get", "log"), ("apex", "list", "log"),
    ("data", "query"), ("data", "get", "record"),
    ("sobject", "list"), ("sobject", "describe"),
    ("org", "list", "metadata"), ("org", "list", "metadata-types"),
}
LOCAL = {("version",), ("help",), ("project", "generate"), ("lightning", "generate"), ("apex", "generate"), ("template", "generate"),
         ("org", "list")}
PREFIX_OK = {("help",), ("project", "generate"), ("lightning", "generate"), ("apex", "generate"),
             ("template", "generate")}  # these take sub-words (`project generate manifest`)
HELP_ONLY = {("--version",), ("-v",), ("--help",), ("-h",)}  # the one flag-first form that passes: nothing else follows it
HELP_FLAGS = ("--help", "-h")

DENY_REASONS = [  # (command prefix, why) for a clear message; anything else not in ALLOW is "not in the allow list"
    (("org", "display"), "shows the org's access token"),
    (("org", "open"), "prints a login URL that carries a session id"),
    (("org", "login"), "signs in"), (("org", "logout"), "signs out"), (("org", "create"), "creates an org"),
    (("org", "delete"), "deletes an org"), (("auth",), "changes authorization"), (("login",), "signs in"),
    (("logout",), "signs out"), (("config",), "reads or changes the CLI's configuration"), (("alias",), "reads or changes aliases"),
    (("data", "delete"), "deletes data"), (("data", "create"), "writes data"), (("data", "update"), "writes data"),
    (("data", "upsert"), "writes data"), (("data", "import"), "writes data"), (("data", "export"), "reads bulk data"),
    (("data", "bulk"), "writes data"), (("project", "delete"), "deletes metadata in the org"),
    (("plugins",), "changes the CLI"), (("update",), "changes the CLI"),
]

DEPLOY_TYPES = ("ApexClass", "LightningComponentBundle")
# The flags of `project deploy start|validate` that take a value (long name -> short char), and the ones oclif lets repeat AND read
# the bare words after them as more values (`-d a b` is two directories). Needed to tell a path from the value of another flag.
DEPLOY_OPTIONS = {
    "--api-version": "-a", "--manifest": "-x", "--metadata": "-m", "--metadata-dir": None, "--source-dir": "-d",
    "--target-org": "-o", "--tests": "-t", "--test-level": "-l", "--wait": "-w", "--pre-destructive-changes": None,
    "--post-destructive-changes": None, "--coverage-formatters": None, "--results-dir": None, "--flags-dir": None,
}
DEPLOY_SHORT = {short: name for name, short in DEPLOY_OPTIONS.items() if short}
DEPLOY_GREEDY = ("--source-dir", "--metadata", "--tests", "--coverage-formatters")


# ---------------------------------------------------------------------------------------------------------------- scrub

def scrub(text) -> str:
    text = text if isinstance(text, str) else ("" if text is None else str(text))
    text = SECRET_FIELD_RE.sub(lambda m: m.group("head") + "[redacted]", text)
    text = AUTH_URL_RE.sub("[redacted]", text)
    return SESSION_RE.sub("[redacted]", text)


# ---------------------------------------------------------------------------------------------------------------- policy

def command_words(argv: list[str]) -> tuple[tuple[str, ...], list[str]]:
    """The leading non-flag tokens (an oclif `a:b:c` token counts as three words) and the rest."""
    words: list[str] = []
    i = 0
    while i < len(argv) and not argv[i].startswith("-"):
        words.extend(part for part in argv[i].split(":") if part)
        i += 1
    return tuple(words), argv[i:]


def flag_values(argv: list[str], long_name: str, short: str | None = None) -> list[str]:
    """Every value given to a flag, in the `--flag v`, `--flag=v`, `-f v`, `-f=v` and `-fv` spellings ('' where a value is missing)."""
    found = []
    for i, token in enumerate(argv):
        name, eq, inline = token.partition("=")
        if name == long_name:
            found.append(inline if eq else (argv[i + 1] if i + 1 < len(argv) else ""))
        elif short and token.startswith("-") and not token.startswith("--") and token[:2] == short:
            rest = token[2:]
            if rest:
                found.append(rest[1:] if rest.startswith("=") else rest)
            else:
                found.append(argv[i + 1] if i + 1 < len(argv) else "")
    return found


def has_flag(argv: list[str], long_name: str) -> bool:
    return any(token == long_name or token.startswith(long_name + "=") for token in argv)


def allowed_commands() -> str:
    return ", ".join(sorted(" ".join(words) + (" ..." if words in PREFIX_OK else "") for words in PINNED | LOCAL))


def decide(argv: list[str], org: str, prefix: str = "", cwd: str | None = None) -> tuple[bool, str]:
    """(allowed, reason) for the model's argv. `prefix` and `cwd` scope a deploy (see deploy_scope_problems)."""
    if not argv:
        return True, "no arguments (the CLI's own help)"
    if "--" in argv:
        return False, "a bare `--` argument terminator is not accepted"
    lowered = [token.lower() for token in argv]
    if any("sfdxauthurl" in token or "sfdx-url" in token for token in lowered):
        return False, "auth URLs are credentials; none are accepted"
    if has_flag(argv, "--flags-dir"):
        return False, "--flags-dir is denied: the CLI would read flag values from files after this check; pass the flags on the command line"
    if len(argv) == 1 and (argv[0],) in HELP_ONLY:
        return True, "local flag"
    if argv[0].startswith("-"):
        return False, "flags before the command are not accepted"
    words, rest = command_words(argv)
    for denied, why in DENY_REASONS:
        if words[:len(denied)] == denied:
            return False, f"`{' '.join(denied)}` is denied: it {why}"
    known = PINNED | LOCAL
    match = next((w for w in sorted(known, key=len, reverse=True)
                  if words == w or (w in PREFIX_OK and words[:len(w)] == w)), None)
    helping = any(token in HELP_FLAGS for token in rest)
    if match is None:
        if helping and words and any(w[:len(words)] == words for w in known):
            return True, "help for a group of allowed commands"
        return False, f"`{' '.join(words) or argv[0]}` is not in the allow list (default deny); allowed: {allowed_commands()}"
    if helping:
        return True, "help"
    given = flag_values(rest, "--target-org", "-o")
    wrong = [value for value in given if value != org]
    if wrong:
        return False, f"--target-org must be {org!r} on every command (got {wrong[0]!r})"
    if match in PINNED and not given:
        return False, f"`{' '.join(match)}` must carry --target-org {org} (no default-org fallback)"
    if match == ("org", "list") and has_flag(rest, "--clean"):
        return False, "`org list --clean` edits the CLI's stored orgs"
    if match in PREFIX_OK and match != ("help",):
        wrong = [value for value in flag_values(rest, "--from-org") if value != org]
        if wrong:
            return False, f"--from-org must be {org!r} (got {wrong[0]!r})"
    if match[:2] == ("project", "deploy"):
        for flag in ("--post-destructive-changes", "--pre-destructive-changes", "--metadata-dir"):
            if has_flag(rest, flag):
                return False, f"deploy {flag} is denied (destructive or unreviewable package)"
        if match[2] in ("start", "validate"):
            problems = deploy_scope_problems(rest, cwd or os.getcwd(), prefix)
            if problems:
                scope = f" (approved: Apex classes named {prefix}*, LWC bundles named {lwc_prefix(prefix)}*)" if prefix else ""
                return False, f"deploy is outside the approved scope{scope}: " + "; ".join(problems)
    return True, "allowed"


# ---------------------------------------------------------------------------------------------------------------- deploy scope

def lwc_prefix(prefix: str) -> str:
    """The component spelling of the Apex prefix: lower-case the leading capitals but the last one (SLChess -> slChess). The same
    rule as chess_salesforce.lwc_prefix, kept here so the guard stays a stand-alone script (a test holds the two together)."""
    run = re.match(r"[A-Z]+", prefix)
    if not run:
        return prefix
    caps = run.group(0)
    keep = 1 if 1 < len(caps) < len(prefix) else 0
    return caps[:len(caps) - keep].lower() + prefix[len(caps) - keep:]


def shown(text: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "?", text)


def inside(real: str, real_cwd: str) -> bool:
    return real == real_cwd or real.startswith(real_cwd.rstrip(os.sep) + os.sep)


def relative(path: str, cwd: str, real_cwd: str) -> str:
    rel = os.path.relpath(path, cwd)
    if rel == ".." or rel.startswith(".." + os.sep):  # reached through a differently spelled (symlinked) working directory
        rel = os.path.relpath(os.path.realpath(path), real_cwd)
    return rel


def deploy_inputs(rest: list[str]) -> dict[str, list[str]]:
    """The values of --source-dir, --metadata and --manifest the way the CLI reads them: every spelling of the flag, and the bare
    words after a repeatable flag, up to the next flag that takes a value (a boolean flag such as --json does not end the run)."""
    found: dict[str, list[str]] = {"--source-dir": [], "--metadata": [], "--manifest": []}
    current, i = None, 0
    while i < len(rest):
        token = rest[i]
        i += 1
        if token.startswith("-") and token != "-":
            if token.startswith("--"):
                name, eq, inline = token.partition("=")
                attached = inline if eq else None
            else:
                name = DEPLOY_SHORT.get(token[:2], token)
                attached = token[2:].removeprefix("=") if len(token) > 2 else None
            if name not in DEPLOY_OPTIONS:
                continue
            current = name
            if attached is None and i < len(rest) and not rest[i].startswith("-"):
                attached, i = rest[i], i + 1
            if name in found and attached is not None:
                found[name].append(attached)
        elif current in found and current in DEPLOY_GREEDY:
            found[current].append(token)
    return found


def package_dirs(cwd: str) -> list[str] | None:
    try:
        paths = [entry["path"] for entry in json.loads(Path(cwd, "sfdx-project.json").read_text())["packageDirectories"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return paths if paths and all(isinstance(path, str) and path for path in paths) else None


def in_scope(parts: list[str], prefix: str, lwc: str) -> bool:
    """Whether a file at this path (relative to the working directory) is an approved Apex class file or part of an approved bundle."""
    name = parts[-1]
    parent = parts[-2] if len(parts) > 1 else ""
    if parent == "classes" and name.startswith(prefix) and name.endswith((".cls", ".cls-meta.xml")):
        return True
    if parent == "lwc" and name in ("jsconfig.json", ".eslintrc.json"):
        return True
    return any(parts[i - 1] == "lwc" and parts[i].startswith(lwc) for i in range(1, len(parts) - 1))


def out_of_scope(path: str, cwd: str, real_cwd: str, prefix: str, lwc: str, limit: int) -> list[str]:
    """Up to `limit` paths (relative to the working directory) under `path`, a file or a directory tree walked through its symlinks,
    that the approved scope does not cover; a link that leads outside the working directory counts. Empty directories are fine."""
    bad: list[str] = []
    stack: list[tuple[str, tuple[str, ...]]] = [(path, ())]
    looked = 0
    while stack and len(bad) < limit:
        current, above = stack.pop()
        if not os.path.lexists(current):  # a path that is not there (or one half of a comma list): the real sf says so
            continue
        looked += 1
        if looked > SCOPE_WALK:
            bad.append(f"more than {SCOPE_WALK} entries under {shown(relative(path, cwd, real_cwd))}")
            break
        real = os.path.realpath(current)
        rel = shown(relative(current, cwd, real_cwd))
        if not inside(real, real_cwd):
            bad.append(f"{rel} (leads outside the working directory)")
        elif os.path.isdir(current):
            if real in above:  # a symlink loop
                continue
            try:
                names = sorted(os.listdir(current), reverse=True)
            except OSError:
                bad.append(f"{rel} (cannot be read)")
                continue
            stack.extend((os.path.join(current, name), above + (real,)) for name in names)
        elif not in_scope(rel.split(os.sep), prefix, lwc):
            bad.append(rel)
    return bad


def metadata_problem(entry: str, prefix: str, lwc: str) -> str | None:
    kind, _, member = entry.strip().partition(":")
    wanted = {"ApexClass": prefix, "LightningComponentBundle": lwc}.get(kind)
    if wanted is None or not re.fullmatch(re.escape(wanted) + r"\w*", member):
        return f"--metadata {shown(entry)!r} must be ApexClass:{prefix}<name> or LightningComponentBundle:{lwc}<name> (no other type, no wildcard)"
    return None


def manifest_problems(path: str, cwd: str, prefix: str, lwc: str) -> list[str]:
    shown_path = shown(path)
    try:
        data = Path(cwd, path).read_bytes()
    except OSError:
        return [f"manifest {shown_path!r} cannot be read"]
    if WILDCARD_RE.search(data.decode("utf-8", errors="replace")):
        return [f"manifest {shown_path!r} holds a wildcard member (<members>*</members>); list the {prefix}* components by name"]
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return [f"manifest {shown_path!r} is not valid XML"]
    problems = []
    for types in (element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "types"):
        children = [(child.tag.rsplit("}", 1)[-1], (child.text or "").strip()) for child in types]
        kind = next((text for tag, text in children if tag == "name"), "")
        wanted = {"ApexClass": prefix, "LightningComponentBundle": lwc}.get(kind)
        if wanted is None:
            problems.append(f"manifest {shown_path!r} lists type {shown(kind)!r}; only ApexClass and LightningComponentBundle are approved")
            continue
        for tag, member in children:
            if tag == "members" and not re.fullmatch(re.escape(wanted) + r"\w*", member):
                problems.append(f"manifest {shown_path!r}: {kind} member {shown(member)!r} must start with {wanted} and hold no wildcard")
    return problems[:SCOPE_SHOWN]


def deploy_scope_problems(rest_argv: list[str], cwd: str, prefix: str) -> list[str]:
    """Why a `project deploy start|validate` with these flags would carry more than the approved scope, or [] when it would not.

    The scope is Apex classes named <prefix>* and LWC bundles named <lwcPrefix>* (SLChess -> slChess; see lwc_prefix). Every
    --source-dir path (a comma list is read both ways), --metadata entry and --manifest is checked; with none of them the scope is
    the packageDirectories of sfdx-project.json in `cwd`. A source path must stay inside `cwd` (symlinks included); every file under
    it must be `classes/<prefix>*.cls`, `classes/<prefix>*.cls-meta.xml`, inside `lwc/<lwcPrefix>*/`, or `lwc/jsconfig.json` /
    `lwc/.eslintrc.json`; empty directories are fine."""
    if not prefix:
        return ["the wrapper has no --prefix, so no deploy scope is defined"]
    lwc = lwc_prefix(prefix)
    given = deploy_inputs(rest_argv)
    problems: list[str] = []
    paths = [part for value in given["--source-dir"] for part in ([value] + [p for p in value.split(",") if p] if "," in value else [value])]
    if not any(given.values()):
        paths = package_dirs(cwd)
        if paths is None:
            return [f"no --source-dir, --metadata or --manifest was given and the packageDirectories of sfdx-project.json in the working "
                    f"directory cannot be read; name what to deploy, for example --source-dir force-app/main/default/classes/{prefix}Engine.cls"]
    real_cwd = os.path.realpath(cwd)
    bad: list[str] = []
    for path in paths:
        full = os.path.join(cwd, path)
        if not inside(os.path.realpath(full), real_cwd):
            problems.append(f"source path {shown(path)!r} is outside the working directory")
        elif len(bad) < SCOPE_SHOWN:
            bad += out_of_scope(full, cwd, real_cwd, prefix, lwc, SCOPE_SHOWN - len(bad))
    if bad:
        problems.append(f"not an Apex class named {prefix}* or part of an LWC bundle named {lwc}*: {', '.join(bad)}"
                        " (deploy only those, for example --source-dir on the class file or the bundle folder)")
    for value in given["--metadata"]:
        for entry in value.split(","):
            problem = metadata_problem(entry, prefix, lwc)
            if problem:
                problems.append(problem)
    for manifest in given["--manifest"]:
        problems += manifest_problems(manifest, cwd, prefix, lwc)
    return problems


# ---------------------------------------------------------------------------------------------------------------- run

def find_real_sf(name: str = "sf") -> str | None:
    skip = set()
    for directory in (os.environ.get("E2E_MODEL_BIN_DIR"), os.path.join(os.environ.get("E2E_PLATFORM_DIR") or "", "bin")):
        if directory:
            skip.add(os.path.realpath(directory))
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory or not os.path.isabs(directory) or os.path.realpath(directory) in skip:
            continue
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK) and os.path.realpath(os.path.dirname(candidate)) not in skip:
            return candidate
    return None


def write_log(entry: dict) -> bool:
    """Append one JSON line to the call log, in one write so calls running side by side do not interleave their lines."""
    directory = os.environ.get("E2E_PLATFORM_DIR")
    if not directory:
        return False
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        fd = os.open(os.path.join(directory, LOG_NAME), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(entry) + "\n").encode())
        finally:
            os.close(fd)
    except OSError:
        return False
    return True


def log_decision(call: str, argv: list[str], org: str, prefix: str, allowed: bool, reason: str) -> bool:
    return write_log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "call": call, "org": org, "prefix": prefix,
                      "argv": [scrub(token)[:ARG_LIMIT] for token in argv], "decision": "allowed" if allowed else "denied",
                      "reason": scrub(reason)})


def log_end(call: str, code: int | None, stderr: str, interrupted: bool) -> bool:
    return write_log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "call": call, "end": True, "exit": code,
                      "stderr_head": scrub(stderr)[:200], "interrupted": interrupted})


def parse_fixed(args: list[str]) -> tuple[str, str, bool, list[str]]:
    """The wrapper's fixed flags (--org, --prefix, --deny-all, in any order), one optional `--` after them, then the model's argv."""
    org, prefix, deny_all, i = "", "", False, 0
    while i < len(args):
        if args[i] == "--org" and i + 1 < len(args):
            org, i = args[i + 1], i + 2
        elif args[i] == "--prefix" and i + 1 < len(args):
            prefix, i = args[i + 1], i + 2
        elif args[i] == "--deny-all":
            deny_all, i = True, i + 1
        else:
            break
    if i < len(args) and args[i] == "--":
        i += 1
    return org, prefix, deny_all, args[i:]


def run_real(real: str, argv: list[str], state: dict) -> tuple[str, str, int]:
    """Run the real sf with its output captured; (stdout, stderr, exit code). A signal seen in `state` ends it: SIGTERM first, SIGKILL
    after KILL_GRACE seconds."""
    if state["interrupted"]:
        return "", "", 143
    proc = subprocess.Popen([real, *argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    state["proc"] = proc
    if state["interrupted"]:  # the signal came between the check and the child's start
        proc.terminate()
    while True:
        try:
            out, err = proc.communicate(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            if state["interrupted"] and time.monotonic() - state["at"] > KILL_GRACE:
                proc.kill()
    code = proc.returncode if proc.returncode >= 0 else 128 - proc.returncode
    return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), 143 if state["interrupted"] else code


def main(args: list[str]) -> int:
    org, prefix, deny_all, argv = parse_fixed(args)
    if not org:
        print("sf_guard: denied: the wrapper was built without --org", file=sys.stderr)
        return 2
    call = os.urandom(4).hex()
    if deny_all:
        allowed, reason = False, "this command is not available in this run; use `sf` with --target-org " + org
    else:
        allowed, reason = decide(argv, org, prefix=prefix)
    if not allowed:
        logged = log_decision(call, argv, org, prefix, False, reason)
        print(f"sf_guard: denied: {reason}" + ("" if logged else " (and the call could not be logged)"), file=sys.stderr)
        return 2
    state: dict = {"proc": None, "interrupted": False, "at": 0.0}

    def interrupt(signum, frame):
        if not state["interrupted"]:
            state["interrupted"], state["at"] = True, time.monotonic()
        if state["proc"] is not None:
            state["proc"].send_signal(signal.SIGTERM)

    for number in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, interrupt)
    if not log_decision(call, argv, org, prefix, True, reason):
        print("sf_guard: denied: the call could not be logged (E2E_PLATFORM_DIR is unset or not writable)", file=sys.stderr)
        return 2
    real = find_real_sf()
    if real is None:
        log_end(call, 127, "no real sf on PATH", False)
        print("sf_guard: no real `sf` found on PATH outside the wrapper", file=sys.stderr)
        return 127
    try:
        out, err, code = run_real(real, argv, state)
    except OSError as exc:
        log_end(call, 126, str(exc), False)
        print(f"sf_guard: the real `sf` could not be started: {scrub(str(exc))}", file=sys.stderr)
        return 126
    log_end(call, code, err, state["interrupted"])
    sys.stdout.write(scrub(out))
    sys.stdout.flush()
    sys.stderr.write(scrub(err))
    sys.stderr.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
