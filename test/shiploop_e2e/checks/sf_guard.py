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
    `<members>*</members>`, a bare `--`, and every command not in ALLOW.
  * PINNED: a command that talks to an org must carry `--target-org <org>` (or `-o <org>`), every occurrence equal to the case's
    org; a missing or different one is refused, so no command falls back to the default org.
  * LOCAL commands (`--version`, `--help`, `help`, `project generate`, `lightning generate`, `org list`) pass unchanged.
  * `--deny-all` makes this a stand-in that denies everything (the harness uses it to cover `sfdx`, which would bypass the policy).

Every call appends one JSON line to $E2E_PLATFORM_DIR/sf-calls.jsonl (timestamp, scrubbed argv, decision, reason and, for an allowed
call, the exit code and the first 200 characters of scrubbed stderr). stdout is never logged. The real sf's stdout, stderr and exit
code pass through unchanged apart from the scrub: a value of accessToken/refreshToken/clientSecret/sfdxAuthUrl and any string shaped
like a session token become `[redacted]`.

The real sf is the first `sf` on PATH outside the wrapper's own directory ($E2E_MODEL_BIN_DIR and $E2E_PLATFORM_DIR/bin), so the
wrapper never calls itself; in hermetic tests that `sf` is test/shiploop_e2e/fake_sf.py.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
SECRET_FIELD_RE = re.compile(r"""(?P<head>(?:%s)(?:\\*["'])?\s*[:=]\s*(?:\\*["'])?)(?P<value>[^\s"'\\,}]+)""" % "|".join(SECRET_KEYS))
SESSION_RE = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
AUTH_URL_RE = re.compile(r"force://[^\s\"']+")
WILDCARD_RE = re.compile(r"<members>\s*\*\s*</members>")
LOG_NAME = "sf-calls.jsonl"
ARG_LIMIT = 300  # characters of one argument kept in the log

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
LOCAL = {("version",), ("help",), ("project", "generate"), ("lightning", "generate"), ("org", "list")}
PREFIX_OK = {("help",), ("project", "generate"), ("lightning", "generate")}  # these take sub-words (`project generate manifest`)
HELP_ONLY = {("--version",), ("-v",), ("--help",), ("-h",)}  # the one flag-first form that passes: nothing else follows it

DENY_REASONS = [  # (command prefix, why) for a clear message; anything else not in ALLOW is "not in the allow list"
    (("org", "display"), "shows the org's access token"),
    (("org", "open"), "prints a login URL that carries a session id"),
    (("org", "login"), "signs in"), (("org", "logout"), "signs out"), (("org", "create"), "creates an org"),
    (("org", "delete"), "deletes an org"), (("auth",), "changes authorization"), (("login",), "signs in"),
    (("logout",), "signs out"), (("config",), "changes the CLI's configuration"), (("alias",), "changes aliases"),
    (("data", "delete"), "deletes data"), (("data", "create"), "writes data"), (("data", "update"), "writes data"),
    (("data", "upsert"), "writes data"), (("data", "import"), "writes data"), (("data", "export"), "reads bulk data"),
    (("data", "bulk"), "writes data"), (("project", "delete"), "deletes metadata in the org"),
    (("plugins",), "changes the CLI"), (("update",), "changes the CLI"),
]


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


def decide(argv: list[str], org: str) -> tuple[bool, str]:
    """(allowed, reason) for the model's argv."""
    if not argv:
        return True, "no arguments (the CLI's own help)"
    if "--" in argv:
        return False, "a bare `--` argument terminator is not accepted"
    lowered = [token.lower() for token in argv]
    if any("sfdxauthurl" in token or "sfdx-url" in token for token in lowered):
        return False, "auth URLs are credentials; none are accepted"
    if len(argv) == 1 and (argv[0],) in HELP_ONLY:
        return True, "local flag"
    if argv[0].startswith("-"):
        return False, "flags before the command are not accepted"
    words, rest = command_words(argv)
    for prefix, why in DENY_REASONS:
        if words[:len(prefix)] == prefix:
            return False, f"`{' '.join(prefix)}` is denied: it {why}"
    known = PINNED | LOCAL
    match = next((w for w in sorted(known, key=len, reverse=True)
                  if words == w or (w in PREFIX_OK and words[:len(w)] == w)), None)
    if match is None:
        return False, f"`{' '.join(words) or argv[0]}` is not in the allow list (default deny)"
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
        for manifest in flag_values(rest, "--manifest", "-x"):
            try:
                text = Path(manifest).read_text(errors="replace")
            except OSError:
                continue  # the real sf reports a missing file
            if WILDCARD_RE.search(text):
                return False, f"manifest {manifest!r} holds a wildcard member (<members>*</members>)"
    return True, "allowed"


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


def log_call(argv: list[str], org: str, prefix: str, allowed: bool, reason: str, code: int | None = None, stderr: str = "") -> bool:
    directory = os.environ.get("E2E_PLATFORM_DIR")
    if not directory:
        return False
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "org": org, "prefix": prefix,
             "argv": [scrub(token)[:ARG_LIMIT] for token in argv], "decision": "allowed" if allowed else "denied", "reason": reason}
    if allowed:
        entry["exit"] = code
        entry["stderr_head"] = scrub(stderr)[:200]
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        fd = os.open(os.path.join(directory, LOG_NAME), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        with os.fdopen(fd, "a") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        return False
    return True


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


def main(args: list[str]) -> int:
    org, prefix, deny_all, argv = parse_fixed(args)
    if not org:
        print("sf_guard: denied: the wrapper was built without --org", file=sys.stderr)
        return 2
    if deny_all:
        allowed, reason = False, "this command is not available in this run; use `sf` with --target-org " + org
    else:
        allowed, reason = decide(argv, org)
    if not allowed:
        logged = log_call(argv, org, prefix, False, reason)
        print(f"sf_guard: denied: {reason}" + ("" if logged else " (and the call could not be logged)"), file=sys.stderr)
        return 2
    real = find_real_sf()
    if real is None:
        log_call(argv, org, prefix, True, "allowed but no real sf on PATH", 127)
        print("sf_guard: no real `sf` found on PATH outside the wrapper", file=sys.stderr)
        return 127
    if not os.environ.get("E2E_PLATFORM_DIR"):
        print("sf_guard: denied: E2E_PLATFORM_DIR is not set, so the call could not be logged", file=sys.stderr)
        return 2
    proc = subprocess.run([real, *argv], capture_output=True)
    out = scrub(proc.stdout.decode("utf-8", errors="replace"))
    err_raw = proc.stderr.decode("utf-8", errors="replace")
    code = proc.returncode if proc.returncode >= 0 else 128 - proc.returncode
    log_call(argv, org, prefix, True, reason, code, err_raw)
    sys.stdout.write(out)
    sys.stdout.flush()
    sys.stderr.write(scrub(err_raw))
    sys.stderr.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
