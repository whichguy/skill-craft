"""Versioned V7 apparatus identity, registration and runtime-context policy."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat

REGISTRATION = "shiploop-security-pilot/v3"
OBSERVATION = "shiploop-security-observation/v3"
ASSEMBLED = "shiploop-security-assembled/v1"
SOURCE_DIRS = ("analysis", "coordination", "corpus", "judgment", "preflight", "v7")
SOURCE_FILES = ("operator/runner.py", "materialization.json", "scope_evidence.py", "logger_failure.cjs")
CASES = {"already-secure", "authorization", "cosmetic", "integrated-secure",
         "integration-only", "later-added-work", "secret-exposure", "tenant-isolation"}
ROLES = {"subject": {"model": "gpt-6.1-sol", "effort": "medium"},
         "judge": {"model": "gpt-6-astra", "effort": "high"}}
POLICIES = {
    "git": "retained-native-context/v1",
    "history": "synthetic-calibration-only/v1",
    "probes": "v7-calibrated-probes/v1",
    "report": "private-masked-context/v1",
    "usage": "started-ledger-parent-replay/v1",
    "native": {"inner": "carry-forward-accepted-with-Improve", "outer": "product-acceptance-accepted"},
}
HEX = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    path = Path(path)
    if path != path.resolve() or not path.is_file():
        raise ValueError("missing or linked registration input")
    return json.loads(path.read_bytes())


def tree_rows(root, *, directories=False):
    """Regular sources only, with exact file modes; no transitive links."""
    root = Path(root)
    if root != root.resolve() or not root.is_dir():
        raise ValueError("source tree is absent or linked")
    rows = []
    for parent, subdirs, files in os.walk(root, followlinks=False):
        parent = Path(parent)
        for name in sorted(subdirs + files):
            path = parent / name
            rel = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                if directories:
                    rows.append((rel, stat.S_IMODE(mode), None))
                continue
            if not stat.S_ISREG(mode) or "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                raise ValueError("unsupported assembled source entry")
            rows.append((rel, stat.S_IMODE(mode), digest(path.read_bytes())))
    return sorted(rows)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()


def sources(root):
    root = Path(root)
    rows = []
    for name in SOURCE_DIRS:
        rows.extend((f"{name}/{rel}", mode, sha) for rel, mode, sha in tree_rows(root / name))
    for name in SOURCE_FILES:
        path = root / name
        if path != path.resolve() or not path.is_file():
            raise ValueError("missing or linked assembled source")
        rows.append((name, stat.S_IMODE(path.stat().st_mode), digest(path.read_bytes())))
    return [list(row) for row in sorted(rows)]


def verify_assembled(root, expected=None):
    path = root / "assembled.json"
    receipt = read(path)
    if (receipt.get("schema") != ASSEMBLED or receipt.get("sources") != sources(root)
            or receipt.get("source_sha256") != digest(canonical(receipt["sources"]))):
        raise ValueError("assembled V7 source inventory differs")
    observed = digest(path.read_bytes())
    if expected is not None and expected != observed:
        raise ValueError("assembled V7 identity differs from registration")
    return observed


def validate_protocol(registration):
    if (not isinstance(registration, dict) or registration.get("schema") != REGISTRATION
            or registration.get("observation_schema") != OBSERVATION
            or registration.get("policies") != POLICIES
            or registration.get("roles") != ROLES
            or registration.get("purpose") not in ("smoke", "comparison")
            or registration.get("comparative") is not (registration.get("purpose") == "comparison")):
        raise ValueError("V7 requires a fresh v3 registration with declared purpose and policies")


def validate_schedule(registration, schedule):
    samples = schedule["samples"]
    arms = registration["arms"]
    smoke = registration["purpose"] == "smoke"
    if (not samples or len(samples) != registration["sample_count"]
            or len(samples) > 128 or set(arms) != ({"A"} if smoke else {"A", "B"})
            or schedule.get("purpose") != registration["purpose"]):
        raise ValueError("invalid registered V7 schedule or arm count")
    ids, mask_ids, keys = set(), set(), set()
    for row in samples:
        sid, mid = row["sample_id"], row["masked_id"]
        key = (row["case"], row["arm"], row["trial"])
        if (not ID.fullmatch(sid) or not ID.fullmatch(mid) or sid == mid
                or sid in ids or mid in mask_ids or key in keys
                or row["case"] not in CASES or row["arm"] not in arms
                or type(row["trial"]) is not int or row["trial"] < 1):
            raise ValueError("invalid or repeated registered sample identity")
        ids.add(sid)
        mask_ids.add(mid)
        keys.add(key)
    if ids & mask_ids:
        raise ValueError("masked IDs overlap trial identities")
    cases = {row["case"] for row in samples}
    if smoke:
        if len(samples) != 1 or cases != {"secret-exposure"} or samples[0]["trial"] != 1:
            raise ValueError("smoke is one disposable secret-exposure inner sample")
    else:
        n = registration["trials_per_arm_case"]
        if type(n) is not int or not 1 <= n <= 64 or "cosmetic" not in cases or len(cases) < 2:
            raise ValueError("comparison requires cosmetic and risk strata")
        expected = {(case, arm, trial) for case in cases for arm in arms for trial in range(1, n + 1)}
        if keys != expected:
            raise ValueError("comparison schedule is not balanced")
    return samples


def git_binding(out, sample, registration_sha, start, terminal, export_sha, scope_binding):
    return {"registration_sha256": registration_sha, "trial_id": sample["sample_id"],
            "case_id": sample["case"], "scope_start_sha256": start,
            "scope_terminal_sha256": terminal, "export_sha256": export_sha,
            "lifecycle_binding_sha256": digest(canonical({
                "trial": str(Path(out).resolve()), "sample": sample, "registration_sha256": registration_sha,
            })), "native_worktree_sha256": digest(canonical(scope_binding))}


GRADE = "shiploop-security-grade/v1"


def grade_records(output, samples, cohort, observations=None):
    """Verify the retained grade/details, independently of the grading entry point."""
    output = Path(output)
    receipt = read(output / "grade-manifest.json")
    if observations is None:
        observations = output / "observations.json"
    observations = Path(observations)
    if observations != output / "observations.json":
        raise ValueError("observations must belong to the retained grade directory")
    rows = read(observations)
    ids = [sample["sample_id"] for sample in samples]
    expected = {"schema": GRADE, "registration_sha256": cohort["registration_sha256"],
                "cohort_sha256": digest((output / "cohort-evidence.json").read_bytes()),
                "observations_sha256": digest(observations.read_bytes()),
                "details_sha256": {sid: digest((output / (sid + ".json")).read_bytes()) for sid in ids}}
    if (receipt != expected or read(output / "cohort-evidence.json") != cohort
            or [row.get("sample_id") for row in rows] != ids):
        raise ValueError("retained grade identity or inventory differs")
    details = []
    for sample, row in zip(samples, rows):
        sid = sample["sample_id"]
        detail = read(output / (sid + ".json"))
        if (detail.get("observation") != row or row.get("observation_schema") != OBSERVATION
                or any(row.get(k) != v for k, v in sample.items())
                or row.get("registration_sha256") != cohort["registration_sha256"]
                or row.get("cohort_summary_sha256") != cohort["dispatch_summary_sha256"]
                or row.get("source_receipts") != cohort["slots"].get(sid)):
            raise ValueError("observation is stale, unbound or incompatible")
        if row.get("valid") is True:
            execution = detail.get("execution_context", {})
            stored = output / sid / "execution-inputs.json"
            if (not row.get("source_receipts") or execution.get("status") != "restored_and_verified"
                    or row.get("git_context_status") != "restored_and_verified"
                    or execution != read(stored) or row.get("execution_inputs_sha256") != digest(stored.read_bytes())):
                raise ValueError("valid observation lacks bound execution context")
            sealed = execution["pre_execution_export"]
            observed = {path: {"kind": "file", "mode": mode, "sha256": sha}
                        for path, mode, sha in tree_rows(output / sid / "input-export")}
            if observed != sealed or execution.get("source_receipts") != row["source_receipts"]:
                raise ValueError("retained grading input differs from the execution receipt")
        details.append(detail)
    return rows, details


def validate_launch(argv, binary, *, cwd, resumed=None):
    """Check effective explicit controls for the actual fresh/resume argv."""
    subject = ROLES["subject"]
    if not argv or argv[:3] != [binary, "exec", "--json"] or not isinstance(argv[-1], str):
        raise ValueError("actual host argv is not the registered Codex exec")
    if resumed is not None and argv[-3:-1] != ["resume", resumed]:
        raise ValueError("actual Codex continuation does not match its native thread")
    controls = argv[3:-3] if resumed is not None else argv[3:-1]
    reserved = ("--model", "--config", "--profile", "--cd")
    if "resume" in controls or any(arg.startswith(reserved) for arg in controls):
        raise ValueError("unexpected Codex resume or override control")
    required = {"-m": subject["model"], "-C": str(Path(cwd).resolve())}
    for key, value in required.items():
        if controls.count(key) != 1 or controls.index(key) + 1 >= len(controls) or controls[controls.index(key) + 1] != value:
            raise ValueError("actual Codex argv model or working directory differs")
    config = {}
    for i, arg in enumerate(controls):
        if arg == "-c":
            if i + 1 >= len(controls):
                raise ValueError("actual Codex argv has a truncated override")
            key, sep, value = controls[i + 1].partition("=")
            if not sep or key in config:
                raise ValueError("actual Codex argv has ambiguous config overrides")
            config[key] = value
    expected = {"model_reasoning_effort": subject["effort"],
                "agents.default_subagent_model": json.dumps(subject["model"]),
                "agents.default_subagent_reasoning_effort": subject["effort"]}
    if any(config.get(k) != v for k, v in expected.items()):
        raise ValueError("actual Codex argv model/effort controls differ")
