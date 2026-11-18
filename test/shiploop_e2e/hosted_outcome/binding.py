"""Operator inputs for the named hosted discovery case."""
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

CASE = "grok-chat-outcome"
HERE = Path(__file__).resolve().parents[1]
ENV_KEYS = {"HOME", "USER", "LOGNAME", "PATH", "TMPDIR", "TERM", "LANG", "LC_ALL",
            "CODEX_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME",
            "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT", "GIT_CEILING_DIRECTORIES", "NO_COLOR", "SF_USE_GENERIC_UNIX_KEYCHAIN"}
LEGACY_TOOLS = ("grok-chat-ui", "grok-chat-oracle", "grok-chat-quality")
SYSTEM_DIRS = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")
TRACKED_METADATA = ("ApexClass", "LightningComponentBundle", "CustomObject", "CustomApplication", "CustomTab",
                    "FlexiPage", "PermissionSet", "ApexTrigger", "ApexPage", "ApexComponent",
                    "AuraDefinitionBundle", "StaticResource", "CustomLabels")
DIGEST = r"[0-9a-f]{64}"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode() + b"\n"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _number(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("binding JSON requires finite numbers")
    return number


def decoded(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_float=_number, parse_constant=_number)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def fields(item, names):
    require(isinstance(item, dict) and set(item) == set(names.split()), "unexpected or missing binding/receipt fields")


def match(pattern, item):
    return isinstance(item, str) and re.fullmatch(pattern, item, re.ASCII) is not None


def absolute(value):
    require(isinstance(value, (str, Path)), "expected a canonical absolute path")
    path = Path(value)
    require(path.is_absolute() and str(path) == str(value) and path.resolve() == path
            and not any(ord(char) < 32 for char in str(path)), "expected a canonical absolute path")
    return path


def sf_id(value, prefix):
    if not match(prefix + r"[A-Za-z0-9]{15}", value):
        return False
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    return value[15:] == "".join(alphabet[sum(1 << j for j, char in enumerate(value[i:i + 5])
                                            if char.isupper())] for i in (0, 5, 10))


def recent(checked_at, age, now):
    return type(checked_at) in (int, float) and now - age <= checked_at <= now


def load(path, *, now=None, fresh=True):
    """Read and validate one binding and each referenced receipt once."""
    now = time.time() if now is None else now
    path = absolute(path)
    raw = path.read_bytes()
    data = decoded(raw)
    fields(data, "case run_kind product_cwd target namespace legacy_prefixes provider synthetic_label "
                 "sf_bin tool_dirs prompt_sha256 source_readiness_sha256 receipts")
    require(data["case"] == CASE and data["run_kind"] == "create", "binding must name the hosted create case")
    work = absolute(data["product_cwd"])
    require(work.name == "work" and work.parent != HERE.parents[1] and HERE.parents[1] not in work.parents, "product must be the external runner work path")
    target = data["target"]
    fields(target, "org_id user_id selector username")
    require(sf_id(target["org_id"], "00D") and sf_id(target["user_id"], "005")
            and match(r"[A-Za-z0-9][A-Za-z0-9._@+-]{0,159}", target["selector"])
            and match(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+", target["username"]), "invalid canonical Salesforce target")
    require(match(r"[A-Z][A-Za-z0-9]{3,19}", data["namespace"])
            and isinstance(data["legacy_prefixes"], list)
            and all(match(r"[A-Z][A-Za-z0-9]{3,19}", p) for p in data["legacy_prefixes"]), "invalid metadata namespace")
    require(match(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,63}", data["synthetic_label"]), "invalid synthetic scope label")
    provider = data["provider"]
    fields(provider, "reference endpoint model")
    require(match(r"[A-Za-z][A-Za-z0-9_]{0,79}", provider["reference"])
            and match(r"grok-[A-Za-z0-9._-]{1,70}", provider["model"])
            and match(r"https://[A-Za-z0-9./_-]+", provider["endpoint"])
            and urlsplit(provider["endpoint"]).netloc == "api.x.ai", "expected nonsecret xAI binding")
    require(absolute(data["sf_bin"]).is_file() and os.access(data["sf_bin"], os.X_OK), "missing executable sf")
    require(isinstance(data["tool_dirs"], list) and all(absolute(item).is_dir() for item in data["tool_dirs"]),
            "invalid tool search path")
    require(not any(os.access(Path(folder) / tool, os.X_OK) for tool in LEGACY_TOOLS
                    for folder in (*data["tool_dirs"], *SYSTEM_DIRS)), "historical helper present on builder PATH")
    source = HERE / "scenarios" / CASE
    require(data["prompt_sha256"] == sha((source / "BUILDER_PROMPT.md").read_bytes())
            and data["source_readiness_sha256"] == sha((source / "READINESS.json").read_bytes()),
            "binding prompt or source readiness digest differs")
    require(work.parent not in path.parents, "binding must be outside runner output")
    fields(data["receipts"], "authority retirement observer")
    identity = sha(encoded({key: value for key, value in data.items() if key != "receipts"}))
    timestamps = {}
    for kind, ref in data["receipts"].items():
        fields(ref, "path sha256")
        receipt_path = absolute(ref["path"])
        require(work.parent not in receipt_path.parents, "operator evidence must be outside runner output")
        receipt_raw = receipt_path.read_bytes()
        require(sha(receipt_raw) == ref["sha256"], f"{kind} receipt digest differs")
        receipt = decoded(receipt_raw)
        require(isinstance(receipt, dict) and receipt.get("kind") == kind
                and receipt.get("identity_sha256") == identity and receipt.get("status") == "VERIFIED",
                f"{kind} receipt does not verify this binding")
        age = 86400 if kind == "retirement" else 28800
        require(not fresh or recent(receipt.get("checked_at"), age, now), f"{kind} receipt is stale")
        timestamps[kind] = (receipt.get("checked_at"), age)
    return data, sha(raw), timestamps


def approval(path, key, intent_raw, context, *, payload_members=None):
    """Validate exactly the review envelope both forwarding and cleanup consume."""
    require(match(DIGEST, key) and sha(intent_raw) == key, "deployment intent digest differs")
    require(path.is_file() and not path.is_symlink(), "deployment approval must be a regular file")
    raw = path.read_bytes()
    decision = decoded(raw)
    fields(decision, "intent_sha256 approved binding_sha256 force_app_sha256 project_sha256 members review_evidence")
    intent = decoded(intent_raw)
    require(decision["approved"] is True and decision["intent_sha256"] == key
            and intent["target"] == context["target"]
            and decision["binding_sha256"] == intent["binding_sha256"] == context["binding_sha256"],
            "deployment approval binding differs")
    require(all(match(DIGEST, intent[name]) and decision[name] == intent[name]
                for name in ("force_app_sha256", "project_sha256")), "deployment approval source differs")
    members = decision["members"]
    require(isinstance(members, dict) and members and set(members) <= {*TRACKED_METADATA, "CustomField"},
            "approved metadata members required")
    namespace = context["namespace"].casefold()
    legacy = ("slgrok", *(name.casefold() for name in context.get("legacy_prefixes", ())))
    for kind, names in members.items():
        require(isinstance(names, list) and names
                and all(match(r"[A-Za-z][A-Za-z0-9_.]{0,159}", name)
                        and name.casefold().startswith(namespace) and not name.casefold().startswith(legacy)
                        for name in names) and len(names) == len(set(names)), "approved metadata member out of scope")
        if kind == "CustomField":
            require(all(name.count(".") == 1 and name.split(".")[0] in members.get("CustomObject", ())
                        for name in names), "approved CustomField requires its reviewed CustomObject")
    if payload_members is not None:
        require({kind: set(names) for kind, names in members.items()} == payload_members,
                "approved metadata member map must exactly match the deployment payload")
    ref = decision["review_evidence"]
    fields(ref, "path sha256")
    evidence = absolute(ref["path"])
    require(evidence != path and evidence != path.with_suffix(".intent")
            and not evidence.is_relative_to(Path(context["output"])) and evidence.is_file()
            and match(DIGEST, ref["sha256"]), "invalid operator review evidence reference")
    evidence_raw = evidence.read_bytes()
    require(evidence_raw and sha(evidence_raw) == ref["sha256"], "operator review evidence digest differs")
    return members, sha(raw)


@contextlib.contextmanager
def build_lock(state, *, close=False, exclusive=False):
    """Keep forwards in the build phase and prevent tests from racing deployments."""
    with (state / "build.lock").open("ab") as lock:
        try:
            fcntl.flock(lock, (fcntl.LOCK_EX if close or exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("hosted build phase transition or CLI call in progress") from None
        yield


def no_launch_without_reset(context):
    """A read-only reset may be re-observed only before any launch or baseline freeze."""
    state = Path(context["state_dir"])
    output = Path(context["output"])
    return (not os.path.lexists(output)
            and not any(os.path.lexists(state / name) for name in
                        ("reset.json", "operator-baseline.json", "launching.json", "launch.json", "runner.log",
                         "resources.jsonl", "bin", "app-access.json", "observe-request.json", "observations.json"))
            and not any(state.glob("*.intent")) and not any(state.glob("*.submitted"))
            and not any(state.glob("*.returned"))
            and not any(state.glob("operator-cleanup-*/*-destructive-submitted.json")))


def opening(prompt, data):
    target, provider = data["target"], data["provider"]
    return (prompt + "\nResolved environment and authority\n"
            f"Start ShipLoop from {data['product_cwd']}. Use guarded sf with --target-org {target['selector']} "
            f"(org {target['org_id']}, user {target['username']} / {target['user_id']}). "
            "From the active DX project root, request deployment of the full force-app package with "
            f"`sf project deploy start --source-dir force-app --target-org {target['selector']} --json`. "
            "Retry that command after the operator approves the inspected source. "
            f"Scope app source, deployment and access to the {data['namespace']} prefix and "
            f"synthetic records labeled {data['synthetic_label']}. Use xAI Named Credential "
            f"{provider['reference']}, endpoint {provider['endpoint']}, model {provider['model']}. "
            "The operator handles app access and anonymous Apex. From the deployed DX workspace, run one "
            "approved and deployed Apex test class at a time with "
            f"`sf apex run test --class-names <class> --synchronous --target-org {target['selector']} --json`. "
            "Obtain explicit human approval for each exact proposed "
            "business create or update before applying it. Leave credentials, users, unrelated records "
            "and metadata alone. Use only owned jobs and avoid indefinite schedules.\n")


def guard_path(data, env, state, startup_files, python_pin_dir, probe):
    """Use a fresh guarded PATH and the stock real-HOME CLI auth pattern."""
    real_home = Path.home()
    clean = {key: value for key, value in env.items() if key in ENV_KEYS}
    home = Path(clean["HOME"])
    folder = state / "bin"
    folder.mkdir()
    tools = [*data["tool_dirs"], *SYSTEM_DIRS]
    for name in ("sf", "sfdx"):
        args = [sys.executable, str(HERE / "checks/sf_guard.py"), "--org", data["target"]["selector"],
                "--prefix", data["namespace"], "--custom-objects", "--permission-sets", "--name", name]
        if name == "sfdx":
            args.append("--deny-all")
        fixed = {"HOME": str(real_home), "PATH": os.pathsep.join(tools), "HOSTED_SF_GATE": str(state),
                 "E2E_PLATFORM_DIR": str(state), "HOSTED_SF_BIN": data["sf_bin"]}
        wrapper = folder / name
        wrapper.write_text("#!/bin/sh\nexec /usr/bin/env -i "
                           + shlex.join([*(f"{k}={v}" for k, v in fixed.items()), *args, "--"]) + ' "$@"\n')
        wrapper.chmod(0o700)
    python_bin = str(home / python_pin_dir)
    clean["PATH"] = os.pathsep.join([str(folder), python_bin, *tools])
    # Replace the inherited PATH after system login initialization as well.
    for name in startup_files:
        startup = home / name
        require(not startup.is_symlink(), "unexpected symlink in hosted shell profile")
        with startup.open("a") as handle:
            handle.write(f"\nexport PATH={shlex.quote(clean['PATH'])}\n")
    problems = probe(("sf", "sfdx"), folder, clean)
    require(not problems, "guarded sf/sfdx shell resolution failed")
    return clean
