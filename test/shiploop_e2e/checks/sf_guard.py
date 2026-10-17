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
    `<members>*</members>` or a DOCTYPE/ENTITY declaration (the CLI's XML parser and this check's could read it differently), a
    deploy that does not wait (`--async`, or a `--wait` below 5 minutes or not written as plain digits: the deploy can keep running
    in the org after the command returned), `--flags-dir` on any command (the CLI reads flag values from that directory after this
    check, so the call could not be judged), the old spellings of the org flags (`-u`, `--u`, `--targetusername`, `--fromorg`: they
    select an org without being read as `--target-org` / `--from-org`), a bare `--`, and every command not in ALLOW (the refusal
    lists what is allowed). `project deploy quick|cancel|resume` are not in ALLOW: they take the org from the CLI's global deploy cache (~/.sf/deploy-cache.json,
    shared with the owner's own deploys), so `--target-org` does not pin them. `project deploy report` is allowed only with
    `--job-id` and never with `--use-most-recent` / `-r`, for the same reason; it is pinned only for a job id that is not in that
    cache, because a cached id reports on the org of the deploy that left it, whatever `--target-org` says (read-only).
  * PINNED: a command that talks to an org must carry `--target-org <org>` (or `-o <org>`), every occurrence equal to the case's
    org; a missing or different one is refused, so no command falls back to the default org. The real sf is also run with
    `SF_TARGET_ORG=<org>` and every other default-org variable (`SFDX_DEFAULTUSERNAME`, `SF_TARGET_DEV_HUB` ...) removed from its
    environment, so a pin the guard read but the CLI did not (a flag spelling the guard misjudged) falls back to the case's org.
  * SCOPED: `project deploy start|validate` may carry only the components the owner approved: ApexClass, CustomTab,
    CustomApplication and FlexiPage named <prefix>* (an underscore suffix is fine: SLChess_Board) and LightningComponentBundle named
    <lwcPrefix>* (SLChess -> slChess). Every `--source-dir` tree, `--metadata` entry and `--manifest` is checked (with none of them,
    the `packageDirectories` of the sfdx-project.json at or above the working directory); anything else, a path that leaves the
    project, or an unreadable manifest is refused with what to change. The tab, app and app page name check is on the file name, the
    --metadata entry and the manifest member only, never on the file's content. A file named exactly `.gitkeep` (git's placeholder
    for an empty folder; it names no component) and an empty folder are not judged.
  * LOCAL commands (`--version`, `--help`, `help`, `project generate`, `lightning generate`, `apex generate`, `template generate`,
    `org list`) pass unchanged. `--help` or `-h` after an allowed command, or a group of allowed commands, passes too, without
    `--target-org`: the CLI prints help and runs nothing. A denied command stays denied with `--help`.
  * `--deny-all` makes this a stand-in that denies everything (the harness uses it to cover `sfdx`, which would bypass the policy).

Every call appends a DECISION line to $E2E_PLATFORM_DIR/sf-calls.jsonl before anything runs (call id, timestamp, scrubbed argv,
decision and reason), and an allowed call appends an END line when the real sf has finished (the same call id, `"end": true`, the
exit code, the first 200 characters of scrubbed stderr, `interrupted`). The calls are the lines without an `end` key. A call that
cannot be logged is denied; so is a call the guard could not judge (an exception in the policy). SIGTERM, SIGHUP and SIGINT while the
real sf runs are forwarded to it, logged as `interrupted` and exit 143. stdout is never logged. The real sf's output is captured,
so it reaches the model when the command ends, not as it runs; its exit code passes through unchanged apart from the scrub: a
value of accessToken/refreshToken/clientSecret/sfdxAuthUrl and any string shaped like a session token become `[redacted]`.

The real sf is the first `sf` on PATH outside the wrapper's own directory ($E2E_MODEL_BIN_DIR and $E2E_PLATFORM_DIR/bin), so the
wrapper never calls itself; in hermetic tests that `sf` is test/shiploop_e2e/fake_sf.py.

Known limits (adversarial only; the harness's cleanup and its comparison with the recorded baseline are the backstop, not this file):
the guard is a lexical allow list over oclif's spellings, and each review round found new adversarial-only spellings of a flag (a
short flag fused in front of another, an alias written as a long flag, a number the CLI reads differently from Python); the org
comparison after cleanup is the backstop, and the follow-up is a canonical-form parser generated from the CLI's own command manifest;
a deploy can outlive its command: a host's tool timeout kills the local sf with SIGTERM but not the deploy running server side, and
even a wait of 5 minutes can end before a large deploy does. The case's cleanup does not poll for deploys in flight: its comparison
of the org with the recorded baseline after cleanup is the only backstop, and it does not see a deploy that lands after it, so after
any run that ended by timeout or stop the person running the case checks Setup > Deployment Status in the org (the guard cannot see
the org's deploy queue);
the deploy scope does not bound what else runs in the org, because `apex run --file` and `apex run test` execute arbitrary Apex there
(including the DML the `data` denials stop); sfdx-project.json is writable by the model, and its packageDirectories (the default
scope), registryCustomizations and replacements change what the CLI deploys; `project retrieve start` accepts `--output-dir`,
`--target-metadata-dir` and `--zip-file-name` anywhere on disk; and the policy judges the tree at one instant, so a background writer
can change it between this check and the CLI reading it.
"""
from __future__ import annotations

import json
import os
import re
import signal
import stat
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
DECLARATION_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)
LOG_NAME = "sf-calls.jsonl"
ARG_LIMIT = 300  # characters of one argument kept in the log
KILL_GRACE = 5.0  # seconds a signalled sf gets to exit before it is killed
SCOPE_SHOWN = 5  # out-of-scope files a refusal names
SCOPE_WALK = 50000  # entries one deploy may make the guard look at before it is refused as too large
PLACEHOLDER = ".gitkeep"  # the file name git users keep in an otherwise empty folder; it has no metadata suffix, so it is no component
MANIFEST_LIMIT = 1_000_000  # bytes of a manifest the guard reads
MIN_DEPLOY_WAIT = 5  # minutes: a deploy command with a shorter --wait is refused
SHOWN_LIMIT = 80  # characters of a model- or file-chosen name a refusal repeats
REASON_LIMIT = 2000  # characters of a reason kept in the log
SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)  # forwarded to the real sf while it runs

# (command words) -> exact match unless listed in PREFIX_OK. Org-talking commands are PINNED; the rest are LOCAL. `project deploy
# quick|cancel|resume` are left out on purpose: they take the org from the CLI's global deploy cache, which --target-org does not pin.
PINNED = {
    ("project", "deploy", "start"), ("project", "deploy", "validate"), ("project", "deploy", "report"),
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

# The metadata types the owner approved that live in one flat folder, and the file suffixes of each; their names start with the case
# prefix (SLChess_Board is fine). The component bundle (lwc/<lwcPrefix>*/...) is the fifth kind and has its own rule. Tab, app and app
# page files are judged on the file name (and the --metadata entry or manifest member) only, never on what the file says.
FLAT_TYPES = {
    "ApexClass": ("classes", (".cls", ".cls-meta.xml")),
    "CustomTab": ("tabs", (".tab-meta.xml",)),
    "CustomApplication": ("applications", (".app-meta.xml",)),
    "FlexiPage": ("flexipages", (".flexipage-meta.xml",)),
}
FLAT_FOLDERS = {folder: suffixes for folder, suffixes in FLAT_TYPES.values()}
BUNDLE_TYPE = "LightningComponentBundle"
LWC_CONFIG_FILES = ("jsconfig.json", ".eslintrc.json")  # the two files sf generates next to the bundles in lwc/
# The folders the CLI types a file by when ANY of them is above it (strictDirectoryName in source-deploy-retrieve's registry of the
# installed sf, measured 2026-10): a class file under one of them is deployed as that folder's type, whatever its own folder says.
STRICT_DIRS = frozenset("""ActionableEventOrchDefSettings ActionableEventTypeDefSettings IndustriesManufacturingSettings
    ObjectHierarchyRelationship accessControlPolicies aiAgentDefinitionVersions aiAuthoringBundles appTemplates
    appointmentAssignmentPolicies appointmentSchedulingPolicies aura botBlocks botTemplates bots contentTypes documents emailservices
    experiencePropertyTypeBundles experiences fieldRestrictionRules genAiFunctions genAiPlannerBundles integArtifactDefs
    integrationHub lightningTypes lwc mktDataSources objectTranslations objects restrictionRules siteDotComSites sites staticresources
    uiBundles uiWidgets waveTemplates""".split())
# The flags of `project deploy start|validate` that take a value (long name -> short char), and the ones oclif lets repeat AND read
# the bare words after them as more values (`-d a b` is two directories). Needed to tell a path from the value of another flag.
DEPLOY_OPTIONS = {
    "--api-version": "-a", "--manifest": "-x", "--metadata": "-m", "--metadata-dir": None, "--source-dir": "-d",
    "--target-org": "-o", "--tests": "-t", "--test-level": "-l", "--wait": "-w", "--pre-destructive-changes": None,
    "--post-destructive-changes": None, "--coverage-formatters": None, "--results-dir": None, "--flags-dir": None,
}
DEPLOY_SHORT = {short: name for name, short in DEPLOY_OPTIONS.items() if short}
DEPLOY_GREEDY = ("--source-dir", "--metadata", "--tests", "--coverage-formatters")
# The boolean short flags of `project deploy start|validate`: -c -g -r. oclif reads `-rd evil` as -r and then -d, so they are peeled
# off the front of a short-flag token before it is looked up. The deploy's scope and wait checks peel only these: `-t` there is
# --tests (a value flag), so peeling it would make the guard judge `-d <path>` where the CLI reads tests and deploys the default
# package directories.
DEPLOY_BOOLEAN_SHORTS = "cgr"
# The boolean short flags of the allowed commands, all together: -c -r -g (deploy start), -r (deploy report), -c -z (retrieve start),
# -y -c -v (apex run test), -c (apex get test|log), -b -t (data query), -t (data get record, sobject describe), -k (org list
# metadata-types). Used where an over-peeled letter fails closed or harmlessly: the org pin and the old spellings of the org flags (a
# pin that exists only for the guard falls back to the case's org, child_env), and the checks that deny a flag they find.
BOOLEAN_SHORTS = "bcgkrtvyz"
# The old spellings of --target-org (-u, --u, --targetusername) and --from-org (--fromorg) that the CLI still accepts on some commands.
# `--u` is the one-letter alias written as a long flag (oclif looks a long flag up among the aliases too); only `--u` and `--u=...` are
# it, so `--use-tooling-api` is not matched by a prefix test.
LEGACY_ORG_FLAGS = ("--targetusername", "--fromorg")
LEGACY_ORG_EXACT = ("--u",)
# The environment variables that set a default org or dev hub for the CLI (SF_TARGET_ORG, SFDX_DEFAULTUSERNAME ...).
DEFAULT_ORG_ENV_RE = re.compile(r"(?:SF|SFDX)_(?:DEFAULT\w*|TARGET_\w+)")


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


def peel(token: str, booleans: str) -> str:
    """A short-flag token without the boolean short flags fused in front of it (`-rd` -> `-d` when `r` is a boolean flag)."""
    while len(token) > 2 and token[0] == "-" and token[1] in booleans:
        token = "-" + token[2:]
    return token


def flag_values(argv: list[str], long_name: str, short: str | None = None, booleans: str = "") -> list[str]:
    """Every value given to a flag, in the `--flag v`, `--flag=v`, `-f v`, `-f=v` and `-fv` spellings ('' where a value is missing).
    `booleans` names the boolean short flags of the command, which may be fused in front of `-f` (`-co de`)."""
    found = []
    for i, token in enumerate(argv):
        token = peel(token, booleans)
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


def has_short(argv: list[str], letter: str) -> bool:
    """Whether a boolean short flag is given, alone or fused with other boolean short flags in front of another flag (`-r`, `-ro`)."""
    for token in argv:
        if token.startswith("-") and not token.startswith("--"):
            letters = token[1:]
            if letter in letters[:len(letters) - len(letters.lstrip(BOOLEAN_SHORTS))]:
                return True
    return False


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
    for token in argv:
        peeled = peel(token, BOOLEAN_SHORTS)  # `-tu other`: a boolean short flag in front of -u hides it
        if token.startswith(LEGACY_ORG_FLAGS) or peeled.startswith("-u") or token.partition("=")[0] in LEGACY_ORG_EXACT:
            return False, (f"{clip(token, 40)!r} is denied: -u, --u, --targetusername and --fromorg are old spellings of the org flags that "
                           f"this check does not read; use --target-org {org} (or --from-org {org})")
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
    deploying = match[:2] == ("project", "deploy")
    given = flag_values(rest, "--target-org", "-o", BOOLEAN_SHORTS)
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
    if deploying:
        for flag in ("--post-destructive-changes", "--pre-destructive-changes", "--metadata-dir"):
            if has_flag(rest, flag):
                return False, f"deploy {flag} is denied (destructive or unreviewable package)"
        if match[2] == "report":
            problem = report_problem(rest)
            if problem:
                return False, problem
        else:  # start, validate
            no_wait = deploy_no_wait(rest)
            if no_wait:
                return False, f"deploy {no_wait[0]} is denied: the deploy can keep running in the org after the command returns; {no_wait[1]}"
            problems = deploy_scope_problems(rest, cwd or os.getcwd(), prefix)
            if problems:
                scope = f" (approved: {approved_text(prefix, lwc_prefix(prefix))})" if prefix else ""
                return False, f"deploy is outside the approved scope{scope}: " + "; ".join(problems)
    return True, "allowed"


def deploy_no_wait(rest: list[str]) -> tuple[str, str] | None:
    """(the flag as written, what to do instead) for `--async` or a `--wait` under MIN_DEPLOY_WAIT minutes, the ways a deploy command
    returns while the deploy keeps running. The default wait (33 minutes) is fine, so leaving the flag out passes. The CLI reads the
    value with parseInt(value, 10), which takes `1e1` as 1 and `9abc` as 9, so only plain ASCII digits are accepted."""
    if has_flag(rest, "--async"):
        return "--async", "leave it out and wait for the deploy to finish"
    for value in flag_values(rest, "--wait", "-w", DEPLOY_BOOLEAN_SHORTS):
        if not re.fullmatch(r"[0-9]{1,6}", value) or int(value) < MIN_DEPLOY_WAIT:
            return (f"--wait {clip(value)}", f"use --wait {MIN_DEPLOY_WAIT} or a larger value (or leave it out) and wait for the deploy "
                                              "to finish")
    return None


def report_problem(rest: list[str]) -> str | None:
    """Why a `project deploy report` is refused, or None. The CLI reads the deploy to report on from its global cache when it is not
    named, so --use-most-recent (-r) is refused and a --job-id is required."""
    if has_flag(rest, "--use-most-recent") or has_short(rest, "r"):
        return ("deploy report --use-most-recent (-r) is denied: the CLI takes the newest deploy of any org from its global cache; "
                "name your deploy with --job-id")
    if not any(flag_values(rest, "--job-id", "-i", BOOLEAN_SHORTS)):
        return "deploy report must carry --job-id (the CLI would otherwise report the newest deploy of any org from its global cache)"
    return None


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


def type_prefixes(prefix: str, lwc: str) -> dict[str, str]:
    """The name every approved metadata type must start with."""
    return {**{kind: prefix for kind in FLAT_TYPES}, BUNDLE_TYPE: lwc}


def approved_text(prefix: str, lwc: str) -> str:
    return f"{', '.join(FLAT_TYPES)} named {prefix}*, {BUNDLE_TYPE} named {lwc}*"


def shown(text: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", "?", text)


def clip(text: str, limit: int = SHOWN_LIMIT) -> str:
    """`shown`, cut to `limit` characters: a name the model or a manifest chose can be of any length."""
    text = shown(text)
    return text if len(text) <= limit else text[:limit] + "..."


def inside(real: str, real_root: str) -> bool:
    return real == real_root or real.startswith(real_root.rstrip(os.sep) + os.sep)


def relative(path: str, root: str, real_root: str) -> str:
    rel = os.path.relpath(path, root)
    if rel == ".." or rel.startswith(".." + os.sep):  # reached through a differently spelled (symlinked) working directory
        rel = os.path.relpath(os.path.realpath(path), real_root)
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
                token = peel(token, DEPLOY_BOOLEAN_SHORTS)
                name = DEPLOY_SHORT.get(token[:2], token)
                attached = token[2:].removeprefix("=") if len(token) > 2 else None
            if name not in DEPLOY_OPTIONS:
                continue
            current = name
            if attached is None and i < len(rest):  # the next word is the value, even one that starts with `-` (as oclif reads it)
                attached, i = rest[i], i + 1
            if name in found and attached is not None:
                found[name].append(attached)
        elif current in found and current in DEPLOY_GREEDY:
            found[current].append(token)
    return found


def comma_parts(value: str) -> list[str]:
    """A --source-dir value read both ways: as one path, and (when it holds a comma) as a comma list."""
    return [value] + [part for part in value.split(",") if part] if "," in value else [value]


def project_root(real_cwd: str) -> str | None:
    """The nearest folder at or above the working directory that holds sfdx-project.json (where sf finds the project), or None."""
    current = real_cwd
    while True:
        if os.path.isfile(os.path.join(current, "sfdx-project.json")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def package_dirs(root: str) -> list[str] | None:
    try:
        paths = [entry["path"] for entry in json.loads(Path(root, "sfdx-project.json").read_text())["packageDirectories"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return paths if paths and all(isinstance(path, str) and path for path in paths) else None


def in_scope(parts: list[str], prefix: str, lwc: str) -> bool:
    """Whether a file at this path (relative to the project) is an approved file: a class, tab, app or app page file of the right
    suffix straight in its own folder (and no `-meta.xml` in front of that suffix), or a file of an approved bundle. The CLI types a
    file by ANY strict folder above it (lwc, aura, objects ...), not by its own parent, so a class file under one of those is judged
    by that folder."""
    name, dirs = parts[-1], parts[:-1]
    if any(folder in STRICT_DIRS and folder != "lwc" for folder in dirs):
        return False
    if "lwc" in dirs:  # every lwc folder on the path must lead straight into an approved bundle (or be the folder of the config files)
        return all(dirs[i + 1].startswith(lwc) if i + 1 < len(dirs) else name in LWC_CONFIG_FILES
                   for i, folder in enumerate(dirs) if folder == "lwc")
    suffixes = FLAT_FOLDERS.get(dirs[-1]) if dirs else None
    suffix = next((end for end in suffixes or () if name.endswith(end)), None)
    # The CLI finds `<name>.<type>-meta.xml` anywhere in a file name (unanchored), so `SLChess.permissionset-meta.xml.cls` is a
    # PermissionSet named SLChess: a stem that holds `-meta.xml` is not a plain class, tab, app or app page file.
    return suffix is not None and name.startswith(prefix) and "-meta.xml" not in name[:-len(suffix)]


def out_of_scope(path: str, root: str, real_root: str, prefix: str, lwc: str, limit: int) -> list[str]:
    """Up to `limit` paths (relative to the project) under `path`, a file or a directory tree walked through its symlinks, that the
    approved scope does not cover; a link that leads outside the project counts. Empty directories are fine, and so is a file named
    exactly `.gitkeep` (PLACEHOLDER)."""
    bad: list[str] = []
    stack: list[tuple[str, tuple[str, ...]]] = [(path, ())]
    looked = 0
    while stack and len(bad) < limit:
        current, above = stack.pop()
        if not os.path.lexists(current):  # a path that is not there (or one half of a comma list): the real sf says so
            continue
        looked += 1
        if looked > SCOPE_WALK:
            bad.append(f"more than {SCOPE_WALK} entries under {shown(relative(path, root, real_root))}")
            break
        real = os.path.realpath(current)
        rel = shown(relative(current, root, real_root))
        if not inside(real, real_root):
            bad.append(f"{rel} (leads outside the project directory)")
        elif os.path.isdir(current):
            if real in above:  # a symlink loop
                continue
            try:
                names = sorted(os.listdir(current), reverse=True)
            except OSError:
                bad.append(f"{rel} (cannot be read)")
                continue
            stack.extend((os.path.join(current, name), above + (real,)) for name in names)
        elif os.path.basename(current) == PLACEHOLDER:
            continue  # after the project boundary above: a link to somewhere else is still refused
        elif not in_scope(rel.split(os.sep), prefix, lwc):
            bad.append(rel)
    return bad


def metadata_problem(entry: str, prefix: str, lwc: str) -> str | None:
    """Why a --metadata entry is not an approved `Type:Name`, or None. A single trailing * is the CLI's own wildcard (ApexClass:SLChess*
    stays inside the prefix); a manifest keeps refusing any star."""
    kind, _, member = entry.strip().partition(":")
    wanted = type_prefixes(prefix, lwc).get(kind)
    if wanted is None or not re.fullmatch(re.escape(wanted) + r"\w*\*?", member):
        names = ", ".join(f"{name}:{start}<name>" for name, start in type_prefixes(prefix, lwc).items())
        return f"--metadata {clip(entry)!r} must be one of {names} (no other type; a * only at the very end)"
    return None


def manifest_problems(path: str, cwd: str, prefix: str, lwc: str) -> list[str]:
    """The problems of the manifest at `path`. It is read under both spellings of the path (as written, and with `link/..` folded
    away lexically) because the CLI may open either; the problems are the union."""
    joined = os.path.join(cwd, path)
    problems: list[str] = []
    for spelling in dict.fromkeys((joined, os.path.normpath(joined))):
        problems += manifest_file_problems(spelling, clip(path, 200), prefix, lwc)
    return list(dict.fromkeys(problems))[:SCOPE_SHOWN]


def manifest_file_problems(full: str, shown_path: str, prefix: str, lwc: str) -> list[str]:
    try:
        fd = os.open(full, os.O_RDONLY | os.O_NONBLOCK)  # never waits for the writer of a pipe
    except OSError:
        return [f"manifest {shown_path!r} cannot be read"]
    try:  # judged on the open file, so what is checked is what is read
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
        data = os.read(fd, MANIFEST_LIMIT + 1) if regular else b""
    except OSError:
        return [f"manifest {shown_path!r} cannot be read"]
    finally:
        os.close(fd)
    if not regular or len(data) > MANIFEST_LIMIT:
        return [f"manifest {shown_path!r} must be a regular file of at most {MANIFEST_LIMIT // 1_000_000} MB (not a pipe, device or folder)"]
    text = data.decode("utf-8", errors="replace")
    if WILDCARD_RE.search(text):
        return [f"manifest {shown_path!r} holds a wildcard member (<members>*</members>); list the {prefix}* components by name"]
    if DECLARATION_RE.search(text):  # entities declared twice: the first wins here, the CLI's parser takes the last
        return [f"manifest {shown_path!r} holds a DOCTYPE or ENTITY declaration; write the members out in a plain package.xml"]
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, LookupError, ValueError):  # LookupError: an encoding the parser does not know
        return [f"manifest {shown_path!r} is not valid XML"]
    wanted_by_type = type_prefixes(prefix, lwc)
    problems = []
    for types in (element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "types"):
        children = [(child.tag.rsplit("}", 1)[-1], (child.text or "").strip()) for child in types]
        kind = next((text for tag, text in children if tag == "name"), "")
        wanted = wanted_by_type.get(kind)
        if wanted is None:
            problems.append(f"manifest {shown_path!r} lists type {clip(kind)!r}; only {', '.join(wanted_by_type)} are approved")
            continue
        for tag, member in children:
            if tag == "members" and not re.fullmatch(re.escape(wanted) + r"\w*", member):
                problems.append(f"manifest {shown_path!r}: {kind} member {clip(member)!r} must start with {wanted} and hold no wildcard")
    return problems[:SCOPE_SHOWN]


def deploy_scope_problems(rest_argv: list[str], cwd: str, prefix: str) -> list[str]:
    """Why a `project deploy start|validate` with these flags would carry more than the approved scope, or [] when it would not.

    The scope is ApexClass, CustomTab, CustomApplication and FlexiPage named <prefix>* and LightningComponentBundle named
    <lwcPrefix>* (SLChess -> slChess; see lwc_prefix). Every --source-dir path (a comma list is read both ways), --metadata entry and
    --manifest is checked; with none of them the scope is the packageDirectories of the sfdx-project.json at or above `cwd` (the
    project root, where sf finds it; `cwd` itself when there is none). A source path is folded lexically (`link/../x` is `x`, as the
    CLI deploys it) and must stay inside the project root (symlinks included); every file under it must be `classes/<prefix>*.cls`,
    `classes/<prefix>*.cls-meta.xml`, `tabs/<prefix>*.tab-meta.xml`, `applications/<prefix>*.app-meta.xml`,
    `flexipages/<prefix>*.flexipage-meta.xml`, inside `lwc/<lwcPrefix>*/`, or `lwc/jsconfig.json` / `lwc/.eslintrc.json`; empty
    directories are fine, and so is a file named exactly `.gitkeep` (git's placeholder for an empty folder: it names no component).
    The tab, app and app page checks are on file names, --metadata entries and manifest members, not on content."""
    if not prefix:
        return ["the wrapper has no --prefix, so no deploy scope is defined"]
    lwc = lwc_prefix(prefix)
    given = deploy_inputs(rest_argv)
    real_cwd = os.path.realpath(cwd)
    found = project_root(real_cwd)
    root = cwd if found in (None, real_cwd) else found
    real_root = os.path.realpath(root)
    if any(given.values()):  # (the path as written, the folder it is relative to)
        paths = [(part, cwd) for value in given["--source-dir"] for part in comma_parts(value)]
    else:
        listed = package_dirs(root)
        if listed is None:
            return [f"no --source-dir, --metadata or --manifest was given and the packageDirectories of the sfdx-project.json at or above the "
                    f"working directory cannot be read; name what to deploy, for example --source-dir force-app/main/default/classes/{prefix}Engine.cls"]
        paths = [(path, root) for path in listed]
    problems: list[str] = []
    bad: list[str] = []
    for path, base in paths:
        full = os.path.normpath(os.path.join(base, path))
        if not inside(os.path.realpath(full), real_root):
            problems.append(f"source path {clip(path, 200)!r} is outside the project directory")
        elif len(bad) < SCOPE_SHOWN:
            bad += out_of_scope(full, root, real_root, prefix, lwc, SCOPE_SHOWN - len(bad))
    if bad:
        problems.append(f"not a class, tab, app or app page named {prefix}* or part of an LWC bundle named {lwc}*: {', '.join(bad)}"
                        " (deploy only those, for example --source-dir on the class file or the bundle folder; a file retrieved from the org"
                        " is not yours to deploy: delete it or narrow the path)")
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
                      "reason": scrub(reason)[:REASON_LIMIT]})


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


def child_env(org: str, environ: dict | None = None) -> dict:
    """The real sf's environment: the caller's, with every default-org variable removed and SF_TARGET_ORG set to the case's org. The
    CLI falls back to that variable when no --target-org reaches it, so a pin the guard read but the CLI did not selects the case's
    org, never the owner's default."""
    env = {key: value for key, value in (os.environ if environ is None else environ).items() if not DEFAULT_ORG_ENV_RE.fullmatch(key)}
    env["SF_TARGET_ORG"] = org
    return env


def run_real(real: str, argv: list[str], state: dict, env: dict | None = None) -> tuple[str, str, int]:
    """Run the real sf (with `env`, or the caller's environment) and capture its output; (stdout, stderr, exit code). A signal seen in
    `state` ends it: SIGTERM first, SIGKILL after KILL_GRACE seconds."""
    if state["interrupted"]:
        return "", "", 143
    proc = subprocess.Popen([real, *argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
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
        try:
            allowed, reason = decide(argv, org, prefix=prefix)
        except Exception as exc:  # a crash is a refusal with a decision line, never a traceback and an unlogged call
            allowed, reason = False, f"the guard could not judge this call ({type(exc).__name__})"
    if not allowed:
        logged = log_decision(call, argv, org, prefix, False, reason)
        print(f"sf_guard: denied: {reason[:REASON_LIMIT]}" + ("" if logged else " (and the call could not be logged)"), file=sys.stderr)
        return 2
    state: dict = {"proc": None, "interrupted": False, "at": 0.0}

    def interrupt(signum, frame):
        if not state["interrupted"]:
            state["interrupted"], state["at"] = True, time.monotonic()
        if state["proc"] is not None:
            state["proc"].send_signal(signal.SIGTERM)

    for number in SIGNALS:
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
        out, err, code = run_real(real, argv, state, child_env(org))
    except OSError as exc:
        log_end(call, 126, str(exc), False)
        print(f"sf_guard: the real `sf` could not be started: {scrub(str(exc))}", file=sys.stderr)
        return 126
    for number in SIGNALS:  # the child is gone: a later signal ends this process instead of being swallowed while the output is written
        signal.signal(number, signal.SIG_DFL)
    log_end(call, code, err, state["interrupted"])
    sys.stdout.write(scrub(out))
    sys.stdout.flush()
    sys.stderr.write(scrub(err))
    sys.stderr.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
