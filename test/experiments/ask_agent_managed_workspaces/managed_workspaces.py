#!/usr/bin/env python3
"""Test-only fixture and public-evidence verifier for managed Ask Agent workspaces.

This program never starts a model CLI, reads credentials, edits global settings,
or removes a worktree.  A live parent session performs native delegation; this
program records the disposable fixture and mechanically grades its public trace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Mapping

SCHEMA = "ask-agent-managed-workspaces.v2"
EVENT_SCHEMA = "ask-agent-managed-workspaces.events.v2"
OUTCOMES_SCHEMA = "ask-agent-managed-workspaces.helper-outcomes.v2"
ACCEPTANCE_SCHEMA = "ask-agent-managed-workspaces.acceptance.v2"
HOSTS = ("grok", "claude", "codex", "cursor", "opencode")

ROLES = ("code", "report")
DELIVERY_MODES = {"patch", "commits", "report-only"}
TASK_RESULTS = {"success", "failed", "cancelled", "blocked", "unknown"}
RETURN_KINDS = {"automatic_notification", "native_join", "after_exit_resume", "unknown"}
LAUNCH_STATES = {"accepted", "started", "running"}
TERMINAL_STATES = {"completed", "failed", "cancelled", "blocked", "unknown"}
EXPECTED_ARTIFACTS = {
    "code": ("reports/handoff-index.md", "reports/validation.md"),
    "report": ("reports/handoff-index.md", "reports/snapshot-audit.md"),
}
TRACE_LAYER_KEYS = (
    "native_launch",
    "parent_continuation",
    "native_return",
    "operation_cwd_root_binding",
    "delivery_acceptance",
    "reports_cleanup",
)
ATTEMPT_ID_RE = re.compile(r"[0-9a-f]{32}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")


class ContractError(ValueError):
    pass


def canonical(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def digest_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_digest(root: Path) -> str:
    """Digest names, file bytes, and symlink targets of the frozen package."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8", "surrogateescape")
        if path.is_symlink():
            payload = b"L\0" + os.readlink(path).encode("utf-8", "surrogateescape")
        elif path.is_file():
            payload = b"F\0" + bytes.fromhex(digest_path(path))
        elif path.is_dir():
            payload = b"D"
        else:
            continue
        digest.update(relative + b"\0" + payload + b"\0")
    return digest.hexdigest()


def write_new(path: Path, value: Any) -> None:
    path = canonical(path)
    if not path.parent.is_dir():
        raise ContractError(f"missing output parent: {path.parent}")
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError as exc:
        raise ContractError(f"refusing to overwrite evidence: {path}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON object required: {path}")
    return value


def run(cwd: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if result.returncode:
        raise ContractError(f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def git_snapshot(checkout: Path) -> dict[str, Any]:
    checkout = canonical(checkout)
    root = canonical(run(checkout, "rev-parse", "--show-toplevel").decode().strip())
    index_path = canonical(run(checkout, "rev-parse", "--git-path", "index").decode().strip())
    tracked = [item.decode("utf-8", "surrogateescape") for item in run(checkout, "ls-files", "-z").split(b"\0") if item]
    untracked = [item.decode("utf-8", "surrogateescape") for item in run(checkout, "ls-files", "-z", "--others", "--exclude-standard").split(b"\0") if item]
    files: dict[str, dict[str, Any]] = {}
    for rel in sorted(set(tracked + untracked)):
        path = checkout / rel
        files[rel] = {"exists": path.is_file(), "sha256": digest_path(path) if path.is_file() else None}
    return {
        "checkout": str(checkout), "git_root": str(root),
        "branch": run(checkout, "branch", "--show-current").decode().strip() or "(detached)",
        "head": run(checkout, "rev-parse", "HEAD").decode().strip(),
        "raw_index_sha256": digest_path(index_path),
        "status_porcelain_sha256": hashlib.sha256(run(checkout, "status", "--porcelain=v1", "-z", "--untracked-files=all")).hexdigest(),
        "staged_diff_sha256": hashlib.sha256(run(checkout, "diff", "--cached", "--binary", "--no-ext-diff")).hexdigest(),
        "unstaged_diff_sha256": hashlib.sha256(run(checkout, "diff", "--binary", "--no-ext-diff")).hexdigest(),
        "tracked": tracked, "untracked": untracked, "files": files,
        # Pricing is the one permitted caller integration.  Preserve both other
        # dirty layers and every nonpricing index record independently of it.
        "nonpricing_git": {
            "staged_sha256": hashlib.sha256(run(checkout, "diff", "--cached", "--binary", "--no-ext-diff", "--", ".", ":(exclude)pricing.json")).hexdigest(),
            "unstaged_sha256": hashlib.sha256(run(checkout, "diff", "--binary", "--no-ext-diff", "--", ".", ":(exclude)pricing.json")).hexdigest(),
            "index_sha256": hashlib.sha256(b"\0".join(item for item in run(checkout, "ls-files", "-s", "-z").split(b"\0") if b"\tpricing.json" not in item)).hexdigest(),
        },
    }


def copy_package(source: Path, target: Path) -> None:
    if not (source / "SKILL.md").is_file():
        raise ContractError(f"skill root lacks SKILL.md: {source}")
    shutil.copytree(source, target, symlinks=True)


def returned_inspection_args(receipt: str | Path, role: str) -> list[str]:
    """One test-only command contract for the live prompt and real-helper tests."""
    if role not in ROLES:
        raise ContractError(f"unknown worker role: {role}")
    args = ["inspect", "--receipt", str(receipt), "--phase", "returned",
            "--delivery-mode", "patch" if role == "code" else "report-only"]
    for artifact in EXPECTED_ARTIFACTS[role]:
        args.extend(["--artifact", artifact])
    return args


def parent_prompt(run_dir: Path, host: str, worker_delay_seconds: int = 0) -> str:
    package = run_dir / "package" / "ask-agent"
    caller = run_dir / "caller"
    inspections = {
        role: shlex.join(["python3", str(package / "scripts" / "ask_agent_workspace.py"),
                          *returned_inspection_args("REPLACE_WITH_WORKER_RECEIPT", role)])
        for role in ROLES
    }
    delay = (f"For this timing control only, each worker must run one native shell command in its assigned worktree that sleeps {worker_delay_seconds} seconds before doing its assignment. Pass that instruction directly in both native launch prompts. The parent must not sleep or poll files; it continues with the arithmetic via a native shell tool while workers are delayed. This delay is experiment instrumentation, never Ask Agent runtime machinery.\n" if worker_delay_seconds else "")
    return f'''Use the Ask Agent skill at {package / "SKILL.md"} for this live native-delegation experiment. Before dispatch, read the current {host} route in Host capabilities plus its Git integration, workspace-operation, and native-lifecycle references. This is an opt-in test fixture, not Ask Agent runtime implementation.

Caller checkout: {caller}
Frozen package root: {package}
Operator baseline: {run_dir / "operator" / "source-baseline.json"}
Operator evidence root: {run_dir / "operator"}

Use the packaged workspace helper to prepare two fresh, separate worker worktrees from the actual dirty caller checkout. Give each worker its own helper receipt. Launch both as fresh, general-purpose native background workers through the current host route; do not shell-launch a model, do not use a shared checkout, and do not use --no-subagents. Use native worker cwd if this host exposes it (the Grok Build CLI must bind its native cwd); otherwise state that limited mode in the final receipt. Before any task operation, each worker must run the packaged helper's check-context command with its receipt from the assigned operation directory, retain its actual process cwd and Git-root output, and stop on failure. A git -C target is not an operation-directory check. Put each complete worker assignment directly in its native launch prompt.

Editing worker: change only pricing.json in its prepared worktree by adding discount_rate: 0.10. Delivery mode is patch: do not commit inherited or contributed files. Preserve the inherited staged/unstaged/untracked sentinels and raw index. Validate JSON. Run the packaged helper inspect command with --phase returned --delivery-mode patch and the two report artifacts before returning. Write reports/handoff-index.md and reports/validation.md describing actual cwd, Git root, helper receipt, inherited sentinel findings, contribution relative to inherited state, validation, and parent integration recommendation.

Report worker: inspect its separate prepared workspace. Delivery mode is report-only: do not edit fixture inputs or commit. Write only reports/handoff-index.md and reports/snapshot-audit.md, then run the packaged helper inspect command with --phase returned --delivery-mode report-only and the two report artifacts before returning. Report actual cwd/root, helper receipt, and each sentinel finding.

After writing the reports, use these exact inspection command templates from the assigned worktree. Replace REPLACE_WITH_WORKER_RECEIPT with that worker's actual absolute receipt path, preserving shell quoting. Do not substitute --report for --artifact.

Editing worker:
```sh
{inspections["code"]}
```
Report worker:
```sh
{inspections["report"]}
```

{delay}
After confirmed native launches and before collection, calculate 18 * 12.50 + 85 - 10 using a native shell tool and report that useful parent result. Then collect actual native returns. Inspect worker contribution relative to its inherited baseline. Integrate only the editing worker's pricing.json discount_rate: 0.10 into the caller; do not alter caller reports, other dirty files, or raw index layers. Revalidate JSON and sentinel preservation. Create operator acceptance evidence that cites actual native launch/return locators, archive/retain worker reports through the packaged helper, and close only after acceptance. Keep retained results outside removable worktrees. Final output distinguishes worker completion, integration, preservation, collection gaps, and cleanup.

Host requested: {host}. If a required native background capability, auth, helper, or cwd binding is unavailable, report BLOCKED/UNOBSERVED rather than simulating it. OpenCode qualification uses its persistent TUI with the documented background-subagent flag; a one-shot process exit is not evidence of automatic Task return.'''


def prepare(args: argparse.Namespace) -> int:
    if not 0 <= args.worker_delay_seconds <= 120:
        raise ContractError("worker delay must be between 0 and 120 seconds")
    run_dir = canonical(args.run)
    if run_dir.exists():
        raise ContractError(f"--run must be a new owned directory: {run_dir}")
    skill_root = canonical(args.skill_root) if args.skill_root else canonical(Path(__file__).parents[3] / "skills" / "ask-agent")
    helper = skill_root / "scripts" / "ask_agent_workspace.py"
    if not helper.is_file():
        raise ContractError(f"managed-workspace helper is required before freezing: {helper}")
    run_dir.mkdir(parents=True)
    operator, primary, caller = run_dir / "operator", run_dir / "primary", run_dir / "caller"
    operator.mkdir()
    copy_package(skill_root, run_dir / "package" / "ask-agent")
    run(run_dir, "init", "-b", "main", str(primary))
    run(primary, "config", "user.name", "Ask Agent managed-workspace fixture")
    run(primary, "config", "user.email", "ask-agent-fixture@example.invalid")
    (primary / "pricing.json").write_text('{"currency":"USD","base_price":100}\n', encoding="utf-8")
    (primary / "dual.txt").write_text("base\n", encoding="utf-8")
    (primary / "deleted.txt").write_text("delete me\n", encoding="utf-8")
    (primary / "unstaged.txt").write_text("original\n", encoding="utf-8")
    run(primary, "add", "pricing.json", "dual.txt", "deleted.txt", "unstaged.txt")
    run(primary, "commit", "-m", "fixture baseline")
    run(primary, "worktree", "add", "-b", "feature", str(caller))
    (caller / "feature.txt").write_text("caller ahead of main\n", encoding="utf-8")
    run(caller, "add", "feature.txt")
    run(caller, "commit", "-m", "caller feature")
    (caller / "dual.txt").write_text("staged layer\n", encoding="utf-8"); run(caller, "add", "dual.txt")
    (caller / "dual.txt").write_text("staged layer\nunstaged layer\n", encoding="utf-8")
    (caller / "staged-add.txt").write_text("staged addition\n", encoding="utf-8"); run(caller, "add", "staged-add.txt")
    (caller / "deleted.txt").unlink()
    (caller / "unstaged.txt").write_text("changed but unstaged\n", encoding="utf-8")
    (caller / "notes.txt").write_text("untracked input\n", encoding="utf-8")
    baseline = git_snapshot(caller)
    baseline["permitted_caller_change"] = "pricing.json: add discount_rate 0.10 only"
    write_new(operator / "source-baseline.json", baseline)
    prompt = parent_prompt(run_dir, args.host, args.worker_delay_seconds)
    prompt_record = {"schema": SCHEMA, "host": args.host, "prompt": prompt,
                     "sha256": hashlib.sha256(prompt.encode()).hexdigest(), "transport": "operator-only external parent input"}
    write_new(operator / "parent-prompt.json", prompt_record)
    manifest = {"schema": SCHEMA, "host": args.host, "run": str(run_dir), "primary": str(primary), "caller": str(caller), "source_head": baseline["head"], "fixture_code_delivery_mode": "patch",
                "package": str(run_dir / "package" / "ask-agent"), "baseline": str(operator / "source-baseline.json"),
                "prompt": str(operator / "parent-prompt.json"), "skill_sha256": digest_path(run_dir / "package" / "ask-agent" / "SKILL.md"),
                "package_tree_sha256": package_digest(run_dir / "package" / "ask-agent"),
                "workspace_helper": str(run_dir / "package" / "ask-agent" / "scripts" / "ask_agent_workspace.py")}
    write_new(operator / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_within(path: Path, root: Path) -> bool:
    path = canonical(path)
    root = canonical(root)
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _existing_file(value: Any, *, label: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ContractError(f"{label} must be a nonempty absolute path")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        raise ContractError(f"{label} must be an absolute path")
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"cannot resolve {label}: {exc}") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise ContractError(f"{label} must be a regular non-symlink file: {resolved}")
    return resolved


def _existing_directory(value: Any, *, label: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ContractError(f"{label} must be a nonempty absolute path")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() or candidate.is_symlink():
        raise ContractError(f"{label} must be a non-symlink absolute directory")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"cannot resolve {label}: {exc}") from exc
    if not resolved.is_dir():
        raise ContractError(f"{label} must be a directory: {resolved}")
    return resolved


def _sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _required_text(value: Any, *, label: str) -> str:
    if not _nonempty(value):
        raise ContractError(f"{label} must be a nonempty string")
    return str(value)


def _load_receipt_evidence(value: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Load a real helper receipt and bind it to this fixture's caller.

    Receipt content proves helper preparation only.  Native worker identity and
    host return state are deliberately kept in the public v2 event trace.
    """
    receipt_path = _existing_file(value, label="helper receipt")
    receipt = load_json(receipt_path)
    required = {"schema", "version", "status", "attempt_id", "store", "source", "worktree", "branch", "baseline", "baseline_sha256"}
    if set(receipt) != required or receipt.get("schema") != "ask-agent.workspace.receipt.v1" or receipt.get("version") != 1 or receipt.get("status") != "prepared":
        raise ContractError(f"unsupported helper receipt: {receipt_path}")
    attempt_id = _required_text(receipt.get("attempt_id"), label="receipt attempt_id")
    if ATTEMPT_ID_RE.fullmatch(attempt_id) is None:
        raise ContractError("helper receipt has an invalid attempt identity")
    store = _existing_directory(receipt.get("store"), label="receipt store")
    attempt = canonical(store / "attempts" / attempt_id)
    if receipt_path.parent != attempt or receipt_path.name != "receipt.json" or not attempt.is_dir():
        raise ContractError("helper receipt is outside its declared attempt directory")
    worktree = canonical(_required_text(receipt.get("worktree"), label="receipt worktree"))
    if worktree != attempt / "worktree":
        raise ContractError("helper receipt worktree is not the owned attempt worktree")
    source = receipt.get("source")
    if not isinstance(source, dict) or set(source) != {"root", "common_dir", "head"}:
        raise ContractError("helper receipt lacks source binding")
    expected_caller = canonical(_required_text(manifest.get("caller"), label="manifest caller"))
    if canonical(_required_text(source.get("root"), label="receipt source root")) != expected_caller:
        raise ContractError("helper receipt source root does not bind to this fixture caller")
    if GIT_SHA_RE.fullmatch(_required_text(source.get("head"), label="receipt source head")) is None:
        raise ContractError("helper receipt source head is not a full Git SHA")
    common_raw = _required_text(source.get("common_dir"), label="receipt source common_dir")
    common_candidate = Path(common_raw)
    if not common_candidate.is_absolute():
        common_candidate = expected_caller / common_candidate
    common = _existing_directory(common_candidate, label="receipt source common_dir")
    expected_common_raw = run(expected_caller, "rev-parse", "--git-common-dir").decode().strip()
    expected_common = Path(expected_common_raw)
    if not expected_common.is_absolute():
        expected_common = expected_caller / expected_common
    if common != _existing_directory(expected_common, label="caller Git common dir"):
        raise ContractError("helper receipt source common directory no longer matches the caller")
    expected_source_head = manifest.get("source_head")
    if expected_source_head is not None and source["head"] != expected_source_head:
        raise ContractError("helper receipt source HEAD does not match the immutable fixture baseline")
    baseline_path = _existing_file(receipt.get("baseline"), label="receipt baseline")
    if baseline_path != attempt / "baseline.json" or not _sha256(str(receipt.get("baseline_sha256", ""))):
        raise ContractError("helper receipt baseline path or digest is invalid")
    if digest_path(baseline_path) != receipt["baseline_sha256"]:
        raise ContractError("helper receipt baseline digest does not match durable baseline")
    baseline = load_json(baseline_path)
    if baseline.get("schema") != "ask-agent.workspace.baseline.v1" or baseline.get("version") != 1 or baseline.get("attempt_id") != attempt_id:
        raise ContractError("helper receipt baseline has an unsupported identity")
    baseline_source = baseline.get("source")
    if not isinstance(baseline_source, dict) or baseline_source.get("root") != source["root"] or baseline_source.get("common_dir") != source["common_dir"] or baseline_source.get("head") != source["head"]:
        raise ContractError("helper receipt baseline source does not match receipt source")
    baseline_files = _existing_directory(baseline.get("baseline_files"), label="receipt baseline file store")
    if baseline_files != attempt / "baseline-files" or not _sha256(str(baseline.get("worker_state_fingerprint", ""))):
        raise ContractError("helper receipt baseline evidence is incomplete")
    return {
        "path": receipt_path,
        "data": receipt,
        "attempt_id": attempt_id,
        "attempt": attempt,
        "worktree": worktree,
        "source": expected_caller,
        "baseline": baseline_path,
    }


def _expected_mode(role: str, mode: Any) -> bool:
    return (role == "code" and mode in {"patch", "commits"}) or (role == "report" and mode == "report-only")


def _artifact_rows(value: Any, *, label: str) -> dict[str, dict[str, str]]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    rows: dict[str, dict[str, str]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise ContractError(f"{label} item must be an object")
        relative = item.get("path", item.get("source"))
        archive = item.get("archive", item.get("archived"))
        digest = item.get("sha256")
        if not _nonempty(relative) or Path(str(relative)).is_absolute() or ".." in Path(str(relative)).parts:
            raise ContractError(f"{label} has an unsafe artifact path")
        if not _nonempty(archive) or not _nonempty(digest) or not _sha256(str(digest)):
            raise ContractError(f"{label} has an incomplete artifact row")
        if str(relative) in rows:
            raise ContractError(f"{label} repeats artifact path: {relative}")
        rows[str(relative)] = {"archive": str(archive), "sha256": str(digest)}
    return rows


def _load_inspection_evidence(value: Any, receipt: Mapping[str, Any], role: str, mode: str) -> dict[str, Any]:
    inspection_path = _existing_file(value, label="inspection evidence")
    inspections = Path(receipt["attempt"]) / "inspections"
    if not _is_within(inspection_path, inspections):
        raise ContractError("inspection evidence is outside the helper attempt inspections directory")
    inspection = load_json(inspection_path)
    if inspection.get("schema") != "ask-agent.workspace.inspection.v1" or inspection.get("phase") != "returned":
        raise ContractError("inspection evidence is not a returned helper inspection")
    if canonical(_required_text(inspection.get("receipt"), label="inspection receipt")) != receipt["path"]:
        raise ContractError("inspection evidence belongs to a different helper receipt")
    artifacts = inspection.get("artifacts")
    if not isinstance(artifacts, list) or set(artifacts) != set(EXPECTED_ARTIFACTS[role]):
        raise ContractError("inspection evidence does not declare the exact required report artifacts")
    contribution = inspection.get("contribution_paths")
    if not isinstance(contribution, list) or not all(_nonempty(path) for path in contribution):
        raise ContractError("inspection evidence has invalid contribution paths")
    if role == "report" and contribution:
        raise ContractError("report-only inspection contains a contribution")
    if role == "code" and set(contribution) != {"pricing.json"}:
        raise ContractError("code inspection must contain only pricing.json")
    return {"path": inspection_path, "data": inspection}


def _load_delivery_evidence(item: Mapping[str, Any], receipt: Mapping[str, Any], inspection: Mapping[str, Any], role: str, mode: str) -> dict[str, Any]:
    """Bind normalized delivery claims to the helper's immutable mode proof."""
    delivery = item.get("delivery")
    if not isinstance(delivery, dict) or delivery.get("mode") != mode:
        raise ContractError("helper outcome lacks delivery evidence for its declared mode")
    evidence_path = _existing_file(item.get("delivery_evidence"), label="delivery evidence")
    delivery_root = Path(receipt["attempt"]) / "delivery-evidence"
    if not _is_within(evidence_path, delivery_root):
        raise ContractError("delivery evidence is outside the helper attempt delivery-evidence directory")
    evidence = load_json(evidence_path)
    if evidence.get("schema") != "ask-agent.workspace.delivery.v1" or evidence.get("version") != 1:
        raise ContractError("delivery evidence has an unsupported schema")
    if canonical(_required_text(evidence.get("receipt"), label="delivery receipt")) != receipt["path"]:
        raise ContractError("delivery evidence belongs to a different helper receipt")
    if evidence.get("fingerprint") != inspection["data"].get("fingerprint") or evidence.get("mode") != mode:
        raise ContractError("delivery evidence does not bind the returned inspection/mode")
    for key, value in delivery.items():
        if evidence.get(key) != value:
            raise ContractError(f"delivery evidence does not match normalized {key}")
    if delivery.get("base") != receipt["data"]["source"]["head"]:
        raise ContractError("delivery evidence base does not match prepared source HEAD")
    if mode == "patch":
        patch = _existing_file(delivery.get("contribution_patch"), label="patch delivery evidence")
        if not _is_within(patch, Path(receipt["attempt"]) / "inspections"):
            raise ContractError("patch delivery evidence is outside the helper attempt inspections directory")
        if canonical(_required_text(inspection["data"].get("contribution_patch"), label="inspection contribution patch")) != patch:
            raise ContractError("patch delivery evidence does not match the inspection contribution patch")
        if set(delivery.get("contribution_paths", [])) != {"pricing.json"}:
            raise ContractError("patch delivery evidence does not name only pricing.json")
    elif mode == "commits":
        commits = delivery.get("commits")
        if not isinstance(commits, list) or not commits or not all(_nonempty(commit) and GIT_SHA_RE.fullmatch(str(commit)) for commit in commits):
            raise ContractError("commit delivery evidence lacks full commit identifiers")
        if set(delivery.get("commit_paths", [])) != {"pricing.json"} or delivery.get("residual_paths") != []:
            raise ContractError("commit delivery evidence does not prove the exact code contribution")
    elif mode == "report-only":
        if delivery.get("contribution_paths") != [] or set(delivery.get("artifacts", [])) != set(EXPECTED_ARTIFACTS[role]):
            raise ContractError("report-only delivery evidence does not prove an artifact-only return")
    return {"path": evidence_path, "data": evidence, "delivery": delivery}


def _load_close_evidence(value: Any, receipt: Mapping[str, Any], role: str) -> dict[str, Any]:
    close_path = _existing_file(value, label="close evidence")
    attempt = Path(receipt["attempt"])
    if close_path != attempt / "close.json":
        raise ContractError("close evidence is not the helper attempt close outcome")
    close = load_json(close_path)
    if close.get("schema") != "ask-agent.workspace.close.v1" or close.get("status") != "closed" or close.get("removed") is not True:
        raise ContractError("close evidence is not a completed helper close outcome")
    if canonical(_required_text(close.get("receipt"), label="close receipt")) != receipt["path"]:
        raise ContractError("close evidence belongs to a different helper receipt")
    if canonical(_required_text(close.get("worktree"), label="close worktree")) != receipt["worktree"]:
        raise ContractError("close evidence worktree does not match its helper receipt")
    rows = _artifact_rows(close.get("archived_artifacts"), label="close archived artifacts")
    if set(rows) != set(EXPECTED_ARTIFACTS[role]):
        raise ContractError("close evidence does not archive the exact required report artifacts")
    results_root = attempt / "results"
    for relative, artifact in rows.items():
        archive = _existing_file(artifact["archive"], label="archived report")
        if archive != results_root / relative:
            raise ContractError("archived report path escapes the helper durable results directory")
        if digest_path(archive) != artifact["sha256"]:
            raise ContractError("archived report digest does not match close evidence")
    return {"path": close_path, "data": close, "artifacts": rows}


def _load_helper_acceptance(value: Any, operator: Path, inspection: Mapping[str, Any], role: str) -> Path:
    acceptance_path = _existing_file(value, label="helper acceptance")
    if not _is_within(acceptance_path, operator):
        raise ContractError("helper acceptance must remain under operator evidence")
    acceptance = load_json(acceptance_path)
    if acceptance.get("schema") != "ask-agent.acceptance.v1" or acceptance.get("workers_stopped") is not True:
        raise ContractError("helper acceptance lacks a stopped-worker attestation")
    if acceptance.get("inspection_fingerprint") != inspection["data"].get("fingerprint"):
        raise ContractError("helper acceptance does not bind the returned inspection fingerprint")
    expected_decision = "integrated" if role == "code" else "report-consumed"
    if acceptance.get("decision") != expected_decision:
        raise ContractError("helper acceptance decision does not match worker role")
    artifacts = acceptance.get("artifacts")
    if not isinstance(artifacts, list) or {item.get("path") for item in artifacts if isinstance(item, dict)} != set(EXPECTED_ARTIFACTS[role]):
        raise ContractError("helper acceptance does not name the exact required report artifacts")
    return acceptance_path


def _validate_retained_attempt(receipt: Mapping[str, Any]) -> None:
    """A failed/cancelled task must retain a real, still-registered workspace."""
    attempt = Path(receipt["attempt"])
    if (attempt / "close.json").exists():
        raise ContractError("retained failed worker already has a close outcome")
    worktree = _existing_directory(receipt["worktree"], label="retained worker worktree")
    root = canonical(run(worktree, "rev-parse", "--show-toplevel").decode().strip())
    if root != receipt["worktree"]:
        raise ContractError("retained worker Git root does not match helper receipt")
    rows = run(receipt["source"], "worktree", "list", "--porcelain").decode("utf-8", "replace").splitlines()
    registered: set[Path] = set()
    for row in rows:
        if row.startswith("worktree "):
            registered.add(canonical(row.partition(" ")[2]))
    if receipt["worktree"] not in registered:
        raise ContractError("retained worker worktree is no longer Git-registered")


def _outcome_validation(manifest: Mapping[str, Any], operator: Path) -> dict[str, Any]:
    """Validate v2 outcome records against helper-generated durable files."""
    path = operator / "helper-outcomes.json"
    errors: list[str] = []
    attempts: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        payload = load_json(path)
        if payload.get("schema") != OUTCOMES_SCHEMA or not isinstance(payload.get("workers"), list):
            raise ContractError(f"helper outcomes must use {OUTCOMES_SCHEMA}")
        for number, item in enumerate(payload["workers"]):
            label = f"helper outcomes worker {number}"
            if not isinstance(item, dict):
                raise ContractError(f"{label} must be an object")
            worker_id = _required_text(item.get("worker_id"), label=f"{label} worker_id")
            attempt_id = _required_text(item.get("attempt_id"), label=f"{label} attempt_id")
            role = _required_text(item.get("role"), label=f"{label} role")
            mode = _required_text(item.get("delivery_mode"), label=f"{label} delivery_mode")
            state = _required_text(item.get("state"), label=f"{label} state")
            if role not in ROLES or not _expected_mode(role, mode):
                raise ContractError(f"{label} has an unsupported role/delivery-mode pair")
            key = (worker_id, attempt_id)
            if key in attempts:
                raise ContractError(f"{label} repeats worker/attempt identity")
            receipt = _load_receipt_evidence(item.get("helper_receipt"), manifest)
            if receipt["attempt_id"] != attempt_id:
                raise ContractError(f"{label} attempt_id does not match helper receipt")
            observed_root = canonical(_required_text(item.get("observed_git_root"), label=f"{label} observed_git_root"))
            if observed_root != receipt["worktree"]:
                raise ContractError(f"{label} observed Git root does not match helper receipt worktree")
            record: dict[str, Any] = {"item": item, "worker_id": worker_id, "attempt_id": attempt_id, "role": role, "mode": mode, "state": state, "receipt": receipt}
            if state == "closed":
                inspection = _load_inspection_evidence(item.get("inspection"), receipt, role, mode)
                delivery = _load_delivery_evidence(item, receipt, inspection, role, mode)
                close = _load_close_evidence(item.get("close"), receipt, role)
                claimed = _artifact_rows(item.get("artifacts"), label=f"{label} artifacts")
                if claimed != close["artifacts"]:
                    raise ContractError(f"{label} artifacts do not match helper close outcome")
                record.update({"inspection": inspection, "delivery": delivery, "close": close})
            elif state == "retained":
                _validate_retained_attempt(receipt)
            else:
                raise ContractError(f"{label} state must be closed or retained")
            attempts[key] = record
    except ContractError as exc:
        errors.append(str(exc))
    return {"pass": not errors, "errors": errors, "attempts": attempts, "evidence": str(path) if path.is_file() else None}


def _acceptance_validation(
    operator: Path,
    attempts: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    path = operator / "acceptance.json"
    errors: list[str] = []
    accepted: dict[tuple[str, str], dict[str, Any]] = {}
    integration: dict[str, Any] | None = None
    try:
        payload = load_json(path)
        if payload.get("schema") != ACCEPTANCE_SCHEMA or not isinstance(payload.get("accepted"), list):
            raise ContractError(f"acceptance must use {ACCEPTANCE_SCHEMA}")
        for number, item in enumerate(payload["accepted"]):
            label = f"acceptance item {number}"
            if not isinstance(item, dict):
                raise ContractError(f"{label} must be an object")
            worker_id = _required_text(item.get("worker_id"), label=f"{label} worker_id")
            attempt_id = _required_text(item.get("attempt_id"), label=f"{label} attempt_id")
            key = (worker_id, attempt_id)
            if key in accepted or key not in attempts:
                raise ContractError(f"{label} has an unknown or duplicate worker/attempt")
            record = attempts[key]
            if item.get("role") != record["role"] or item.get("delivery_mode") != record["mode"]:
                raise ContractError(f"{label} does not match the helper outcome identity")
            if canonical(_required_text(item.get("helper_receipt"), label=f"{label} helper_receipt")) != record["receipt"]["path"]:
                raise ContractError(f"{label} helper receipt does not match the helper outcome")
            _required_text(item.get("native_launch_reference"), label=f"{label} native_launch_reference")
            _required_text(item.get("native_return_reference"), label=f"{label} native_return_reference")
            if "inspection" not in record:
                raise ContractError(f"{label} cannot accept a retained attempt")
            helper_acceptance = _load_helper_acceptance(item.get("helper_acceptance"), operator, record["inspection"], record["role"])
            accepted[key] = {"item": item, "helper_acceptance": helper_acceptance}
        integration_value = payload.get("integration")
        if not isinstance(integration_value, dict):
            raise ContractError("acceptance must contain integration evidence")
        integration = integration_value
        code = [record for key, record in attempts.items() if record["role"] == "code" and key in accepted]
        if len(code) == 1:
            record = code[0]
            if integration.get("delivery_mode") != record["mode"]:
                raise ContractError("integration delivery mode does not match accepted code worker")
            if record["mode"] == "patch":
                _required_text(integration.get("patch_evidence"), label="integration patch_evidence")
            elif record["mode"] == "commits":
                commits = integration.get("commit_shas")
                if not isinstance(commits, list) or not commits or not all(_nonempty(commit) and len(str(commit)) == 40 for commit in commits):
                    raise ContractError("commit integration lacks full commit identifiers")
    except ContractError as exc:
        errors.append(str(exc))
    return {"pass": not errors, "errors": errors, "accepted": accepted, "integration": integration, "evidence": str(path) if path.is_file() else None}


def _event_identity(
    event: Mapping[str, Any],
    attempts: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    label: str,
) -> tuple[tuple[str, str], Mapping[str, Any]]:
    worker_id = _required_text(event.get("worker_id"), label=f"{label} worker_id")
    attempt_id = _required_text(event.get("attempt_id"), label=f"{label} attempt_id")
    key = (worker_id, attempt_id)
    if key not in attempts:
        raise ContractError(f"{label} does not bind a helper outcome worker/attempt")
    record = attempts[key]
    if event.get("role") != record["role"] or event.get("delivery_mode") != record["mode"]:
        raise ContractError(f"{label} role or delivery mode does not match helper outcome")
    if canonical(_required_text(event.get("helper_receipt"), label=f"{label} helper_receipt")) != record["receipt"]["path"]:
        raise ContractError(f"{label} helper receipt does not match helper outcome")
    return key, record


def _native_event(event: Mapping[str, Any], *, label: str, launch: bool, host: str, parent_session: str) -> Mapping[str, Any]:
    native = event.get("native")
    if not isinstance(native, dict):
        raise ContractError(f"{label} lacks native evidence")
    if native.get("host") != host or not _nonempty(native.get("tool")) or not _nonempty(native.get("session_id")) or not _nonempty(native.get("task_id")) or not _nonempty(native.get("locator")):
        raise ContractError(f"{label} has incomplete native evidence")
    if launch and native.get("session_id") != parent_session:
        raise ContractError(f"{label} launch is not in the recorded parent session")
    state = native.get("terminal_state")
    if launch and state not in LAUNCH_STATES:
        raise ContractError(f"{label} launch is not a confirmed active native task")
    if not launch and state not in TERMINAL_STATES:
        raise ContractError(f"{label} return has an invalid native terminal state")
    binding = native.get("cwd_binding")
    if not isinstance(binding, dict) or not _nonempty(binding.get("mode")) or not isinstance(binding.get("observed"), bool):
        raise ContractError(f"{label} lacks explicit native cwd-binding evidence")
    return native


def _layer_verdict(
    errors: list[str],
    *,
    unobserved: bool = False,
    **details: Any,
) -> dict[str, Any]:
    """Return a small serializable verdict without changing the strict trace gate."""
    status = "UNOBSERVED" if unobserved else "FAIL" if errors else "PASS"
    return {"pass": status == "PASS", "status": status, "errors": list(errors), **details}


def _unobserved_trace_layers(reason: str) -> dict[str, dict[str, Any]]:
    return {
        name: _layer_verdict([reason], unobserved=True)
        for name in TRACE_LAYER_KEYS
    }


def _record_trace_error(
    errors: list[str],
    layer_errors: dict[str, list[str]],
    layer: str,
    message: str,
) -> None:
    errors.append(message)
    layer_errors[layer].append(message)


def _trace_v2_validation(
    manifest: Mapping[str, Any],
    operator: Path,
    trace_path: Path,
    outcomes: Mapping[str, Any],
    acceptance: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate v2 public trace ordering and bind every claim to durable evidence."""
    errors: list[str] = []
    layer_errors: dict[str, list[str]] = {name: [] for name in TRACE_LAYER_KEYS}
    details: dict[str, Any] = {"evidence": str(trace_path) if trace_path.is_file() else None}
    if not trace_path.is_file():
        reason = "public native event trace is missing"
        return {"pass": False, "status": "UNOBSERVED", "errors": [reason], "layers": _unobserved_trace_layers(reason), **details}
    try:
        payload = load_json(trace_path)
    except ContractError as exc:
        reason = str(exc)
        return {"pass": False, "status": "UNOBSERVED", "errors": [reason], "layers": _unobserved_trace_layers(reason), **details}
    if payload.get("schema") != EVENT_SCHEMA or not isinstance(payload.get("events"), list):
        reason = f"public event trace must use {EVENT_SCHEMA}"
        return {"pass": False, "status": "UNOBSERVED", "errors": [reason], "layers": _unobserved_trace_layers(reason), **details}
    parent = payload.get("parent")
    if not isinstance(parent, dict) or parent.get("host") != manifest.get("host") or not _nonempty(parent.get("session_id")) or not _nonempty(parent.get("locator")):
        reason = "v2 trace lacks parent host/session/locator evidence"
        return {"pass": False, "status": "UNOBSERVED", "errors": [reason], "layers": _unobserved_trace_layers(reason), **details}
    # Keep whatever independently validated identities are available.  A later
    # delivery defect must not erase a real native launch/return from the trace.
    attempts = outcomes.get("attempts", {})
    accepted = acceptance.get("accepted", {})
    events = payload["events"]
    launches: dict[tuple[str, str], tuple[int, Mapping[str, Any], Mapping[str, Any]]] = {}
    returns: dict[tuple[str, str], tuple[int, Mapping[str, Any], Mapping[str, Any]]] = {}
    operations: dict[tuple[str, str], list[int]] = {}
    accept_events: dict[tuple[str, str], int] = {}
    cleanup_events: dict[tuple[str, str], int] = {}
    parent_work: list[int] = []
    task_ids: dict[str, tuple[str, str]] = {}
    first_by_role: dict[str, tuple[int, tuple[str, str]]] = {}
    for index, event in enumerate(events):
        label = f"event {index}"
        event_layer = "native_launch"
        try:
            if not isinstance(event, dict) or not _nonempty(event.get("kind")):
                raise ContractError(f"{label} must be an object with a kind")
            kind = event["kind"]
            # Parent prose is diagnosed independently; a completed Task lifecycle
            # need not imply that its parent subsequently produced a final reply.
            if kind == "parent_final":
                continue
            if kind == "parent_work":
                event_layer = "parent_continuation"
                event_parent = event.get("parent")
                if not isinstance(event_parent, dict) or event_parent.get("session_id") != parent["session_id"] or not _nonempty(event_parent.get("locator")) or not _nonempty(event.get("description")):
                    raise ContractError(f"{label} lacks real parent work/session/locator evidence")
                parent_work.append(index)
                continue
            if kind not in {"native_launch", "operation", "native_return", "parent_acceptance", "cleanup"}:
                raise ContractError(f"{label} has unsupported kind {kind}")
            event_layer = {
                "native_launch": "native_launch",
                "operation": "operation_cwd_root_binding",
                "native_return": "native_return",
                "parent_acceptance": "delivery_acceptance",
                "cleanup": "reports_cleanup",
            }[kind]
            key, record = _event_identity(event, attempts, label=label)
            if kind == "native_launch":
                if key in launches:
                    raise ContractError(f"{label} repeats native launch for a worker/attempt")
                native = _native_event(event, label=label, launch=True, host=str(manifest["host"]), parent_session=str(parent["session_id"]))
                task_id = str(native["task_id"])
                if task_id in task_ids:
                    raise ContractError(f"{label} reuses native task id from another fresh attempt")
                task_ids[task_id] = key
                launches[key] = (index, event, native)
                first_by_role.setdefault(str(record["role"]), (index, key))
            elif kind == "operation":
                operation = event.get("operation")
                if not isinstance(operation, dict) or not _nonempty(operation.get("cwd")) or not _nonempty(operation.get("git_root")) or not _nonempty(operation.get("locator")):
                    raise ContractError(f"{label} lacks actual operation cwd/root/locator evidence")
                root = canonical(str(operation["git_root"]))
                cwd = canonical(str(operation["cwd"]))
                if root != record["receipt"]["worktree"] or not _is_within(cwd, root):
                    raise ContractError(f"{label} operation root/cwd does not bind to the helper receipt worktree")
                operations.setdefault(key, []).append(index)
            elif kind == "native_return":
                if key in returns:
                    raise ContractError(f"{label} repeats native return for a worker/attempt")
                native = _native_event(event, label=label, launch=False, host=str(manifest["host"]), parent_session=str(parent["session_id"]))
                if key not in launches:
                    raise ContractError(f"{label} returns before its native launch")
                if native.get("task_id") != launches[key][2].get("task_id"):
                    raise ContractError(f"{label} native task id does not match its launch")
                result = event.get("task_result")
                if not isinstance(result, dict) or result.get("status") not in TASK_RESULTS:
                    raise ContractError(f"{label} lacks explicit task-result status")
                if result["status"] == "cancelled" and native.get("terminal_state") != "cancelled":
                    raise ContractError(f"{label} declares cancellation without confirmed native cancellation")
                if result["status"] == "success":
                    if native.get("terminal_state") != "completed":
                        raise ContractError(f"{label} declares success without completed native terminal state")
                    if native.get("return_kind") not in {"automatic_notification", "native_join"}:
                        raise ContractError(f"{label} declares success without automatic notification or native join")
                    if native.get("session_id") != parent["session_id"]:
                        raise ContractError(f"{label} successful native return is not in the original parent session")
                elif native.get("return_kind") not in RETURN_KINDS:
                    raise ContractError(f"{label} has unsupported native return route")
                returns[key] = (index, event, native)
            elif kind == "parent_acceptance":
                if key in accept_events or key not in accepted:
                    raise ContractError(f"{label} is missing or repeats accepted worker evidence")
                if not _nonempty(event.get("locator")):
                    raise ContractError(f"{label} lacks an acceptance locator")
                helper_acceptance = _existing_file(event.get("helper_acceptance"), label=f"{label} helper acceptance")
                if helper_acceptance != accepted[key]["helper_acceptance"]:
                    raise ContractError(f"{label} helper acceptance does not match acceptance evidence")
                accept_events[key] = index
            elif kind == "cleanup":
                if key in cleanup_events:
                    raise ContractError(f"{label} repeats cleanup for a worker/attempt")
                if not _nonempty(event.get("locator")):
                    raise ContractError(f"{label} lacks a cleanup locator")
                close = _existing_file(event.get("close"), label=f"{label} close evidence")
                if "close" not in record or close != record["close"]["path"]:
                    raise ContractError(f"{label} close evidence does not match helper outcome")
                cleanup_events[key] = index
        except ContractError as exc:
            _record_trace_error(errors, layer_errors, event_layer, str(exc))
    all_attempts = set(attempts)
    if set(launches) != all_attempts:
        _record_trace_error(errors, layer_errors, "native_launch", "every helper outcome attempt must have exactly one native launch")
    if set(returns) != set(launches):
        _record_trace_error(errors, layer_errors, "native_return", "every launched worker attempt must have exactly one native return")
    worker_ids = [key[0] for key in attempts]
    if len(worker_ids) != len(set(worker_ids)):
        _record_trace_error(errors, layer_errors, "native_launch", "fresh worker attempts reuse a native worker identity")
    roots = [record["receipt"]["worktree"] for record in attempts.values()]
    if len(roots) != len(set(roots)):
        _record_trace_error(errors, layer_errors, "operation_cwd_root_binding", "fresh worker attempts share a helper worktree")
    unobserved_failed_operations: list[str] = []
    for key, (launch_index, _, _) in launches.items():
        returned = returns.get(key)
        observed_operations = operations.get(key, [])
        if returned is None:
            _record_trace_error(errors, layer_errors, "native_return", f"worker/attempt {key[0]}/{key[1]} lacks a native return")
            continue
        successful = returned[1].get("task_result", {}).get("status") == "success"
        if successful and not observed_operations:
            _record_trace_error(errors, layer_errors, "operation_cwd_root_binding", f"successful worker/attempt {key[0]}/{key[1]} lacks actual operation root/cwd evidence")
        elif not successful and not observed_operations:
            unobserved_failed_operations.append(f"{key[0]}:{key[1]}")
        if observed_operations and not all(launch_index < item < returned[0] for item in observed_operations):
            _record_trace_error(errors, layer_errors, "operation_cwd_root_binding", f"worker/attempt {key[0]}/{key[1]} lacks launch-to-operation-to-return chronology")
    if set(first_by_role) != set(ROLES):
        _record_trace_error(errors, layer_errors, "native_launch", "two initial fresh worker roles were not launched")
    elif parent_work:
        both_initial_launches = max(item[0] for item in first_by_role.values())
        first_return = min((item[0] for item in returns.values()), default=len(events))
        if not any(both_initial_launches < item < first_return for item in parent_work):
            _record_trace_error(errors, layer_errors, "parent_continuation", "real parent work was not recorded after both initial launches and before either return")
    else:
        _record_trace_error(errors, layer_errors, "parent_continuation", "no real parent work was recorded")
    successes: dict[str, tuple[str, str]] = {}
    for role in ROLES:
        role_attempts = sorted((key for key, record in attempts.items() if record["role"] == role), key=lambda key: launches.get(key, (len(events),))[0])
        success_keys = [key for key in role_attempts if key in returns and returns[key][1].get("task_result", {}).get("status") == "success"]
        if len(success_keys) != 1:
            _record_trace_error(errors, layer_errors, "native_return", f"role {role} must have exactly one successful task result")
            continue
        success = success_keys[0]
        successes[role] = success
        success_index = returns[success][0]
        for key in role_attempts:
            if key == success:
                continue
            if key not in returns or returns[key][1].get("task_result", {}).get("status") == "success":
                _record_trace_error(errors, layer_errors, "native_return", f"role {role} retry history is ambiguous")
                continue
            if returns[key][0] >= success_index or launches[success][0] <= returns[key][0] or attempts[key].get("state") != "retained":
                _record_trace_error(errors, layer_errors, "native_return", f"role {role} failed/cancelled retry history was not retained before fresh success")
        record = attempts.get(success)
        if record is not None and record.get("state") != "closed":
            _record_trace_error(errors, layer_errors, "delivery_acceptance", f"successful {role} worker did not produce a closed helper outcome")
    successful_keys = set(successes.values())
    if set(accepted) != successful_keys:
        _record_trace_error(errors, layer_errors, "delivery_acceptance", "acceptance does not bind exactly the successful worker attempts")
    if set(accept_events) != successful_keys:
        _record_trace_error(errors, layer_errors, "delivery_acceptance", "parent acceptance events do not bind exactly the successful worker attempts")
    if set(cleanup_events) != successful_keys:
        _record_trace_error(errors, layer_errors, "reports_cleanup", "cleanup events do not bind exactly the successful worker attempts")
    for key in successful_keys:
        if key in returns and key in accept_events and key in cleanup_events:
            if not (returns[key][0] < accept_events[key] < cleanup_events[key]):
                _record_trace_error(errors, layer_errors, "reports_cleanup", f"worker/attempt {key[0]}/{key[1]} cleanup occurred before completed acceptance")
    if manifest.get("host") == "grok":
        grok_launches = [native for _, _, native in launches.values()]
        if not grok_launches or not all(native.get("cwd_binding", {}).get("observed") is True for native in grok_launches):
            _record_trace_error(errors, layer_errors, "native_launch", "Grok Build requires observed native cwd binding at launch")
    if not outcomes.get("pass"):
        layer_errors["delivery_acceptance"].extend(
            f"helper outcomes: {error}" for error in outcomes.get("errors", [])
        )
    if not acceptance.get("pass"):
        layer_errors["delivery_acceptance"].extend(
            f"acceptance: {error}" for error in acceptance.get("errors", [])
        )
    layers = {
        "native_launch": _layer_verdict(layer_errors["native_launch"], launches=sorted(f"{key[0]}:{key[1]}" for key in launches)),
        "parent_continuation": _layer_verdict(layer_errors["parent_continuation"], parent_work_count=len(parent_work)),
        "native_return": _layer_verdict(layer_errors["native_return"], returns=sorted(f"{key[0]}:{key[1]}" for key in returns)),
        "operation_cwd_root_binding": _layer_verdict(
            layer_errors["operation_cwd_root_binding"],
            unobserved=bool(unobserved_failed_operations) and not operations,
            operation_count=sum(len(items) for items in operations.values()),
            unobserved_failed_operations=sorted(unobserved_failed_operations),
        ),
        "delivery_acceptance": _layer_verdict(layer_errors["delivery_acceptance"], successes={role: f"{key[0]}:{key[1]}" for role, key in successes.items()}),
        "reports_cleanup": _layer_verdict(layer_errors["reports_cleanup"], cleanup_attempts=sorted(f"{key[0]}:{key[1]}" for key in cleanup_events)),
    }
    details.update({
        "launches": sorted(f"{key[0]}:{key[1]}" for key in launches),
        "returns": sorted(f"{key[0]}:{key[1]}" for key in returns),
        "successes": {role: f"{key[0]}:{key[1]}" for role, key in successes.items()},
        "return_kinds": sorted({str(native.get("return_kind")) for _, _, native in returns.values()}),
        "parent_work_count": len(parent_work),
        "unobserved_failed_operations": sorted(unobserved_failed_operations),
        "layers": layers,
        "errors": errors,
    })
    return {"pass": not errors and outcomes.get("pass") and acceptance.get("pass"), "status": "OBSERVED" if not errors and outcomes.get("pass") and acceptance.get("pass") else "UNOBSERVED", **details}


def _parent_final_validation(manifest: Mapping[str, Any], trace_path: Path) -> dict[str, Any]:
    """Diagnose parent response separately from the two-worker lifecycle gate."""
    try:
        payload = load_json(trace_path)
    except ContractError as exc:
        return _layer_verdict([str(exc)], unobserved=True)
    events, parent = payload.get("events"), payload.get("parent")
    if (payload.get("schema") != EVENT_SCHEMA or not isinstance(events, list)
            or not isinstance(parent, dict) or parent.get("host") != manifest.get("host")
            or not _nonempty(parent.get("session_id")) or not _nonempty(parent.get("locator"))):
        return _layer_verdict(["parent final response lacks a v2 parent trace"], unobserved=True)
    finals = [(index, event) for index, event in enumerate(events)
              if isinstance(event, dict) and event.get("kind") == "parent_final"]
    if not finals:
        return _layer_verdict(["parent final response was not observed"], unobserved=True)
    errors = []
    if len(finals) != 1:
        errors.append("parent final response must have exactly one observed event")
    index, event = finals[0]
    origin = event.get("parent")
    if (not isinstance(origin, dict) or origin.get("session_id") != parent["session_id"]
            or not _nonempty(origin.get("locator"))):
        errors.append("parent final response lacks the original parent session and locator")
    if event.get("status") != "completed" or not _nonempty(event.get("summary")):
        errors.append("parent final response is not an observed completed reply")
    if any(isinstance(later, dict) and later.get("kind") in
           {"native_launch", "native_return", "parent_acceptance", "cleanup"}
           for later in events[index + 1:]):
        errors.append("parent final response preceded remaining worker lifecycle events")
    return _layer_verdict(errors, evidence=str(trace_path))


def _public_outcomes(validation: Mapping[str, Any]) -> dict[str, Any]:
    """Keep internal Path/tuple indexes out of the durable JSON verdict."""
    attempts = validation.get("attempts", {})
    public_attempts: list[dict[str, Any]] = []
    if isinstance(attempts, Mapping):
        for record in attempts.values():
            if not isinstance(record, Mapping):
                continue
            receipt = record.get("receipt", {})
            public_attempts.append({
                "worker_id": record.get("worker_id"),
                "attempt_id": record.get("attempt_id"),
                "role": record.get("role"),
                "delivery_mode": record.get("mode"),
                "state": record.get("state"),
                "helper_receipt": str(receipt.get("path")) if isinstance(receipt, Mapping) else None,
                "worktree": str(receipt.get("worktree")) if isinstance(receipt, Mapping) else None,
                "archive_paths": sorted(record.get("close", {}).get("artifacts", {})) if isinstance(record.get("close"), Mapping) else [],
            })
    return {
        "pass": bool(validation.get("pass")),
        "errors": list(validation.get("errors", [])),
        "evidence": validation.get("evidence"),
        "attempts": sorted(public_attempts, key=lambda item: (str(item["role"]), str(item["attempt_id"]))),
    }


def _public_acceptance(validation: Mapping[str, Any]) -> dict[str, Any]:
    accepted = validation.get("accepted", {})
    public_accepted: list[dict[str, Any]] = []
    if isinstance(accepted, Mapping):
        for key, value in accepted.items():
            if not isinstance(value, Mapping):
                continue
            item = value.get("item", {})
            if isinstance(item, Mapping):
                public_accepted.append({
                    "worker_id": item.get("worker_id"),
                    "attempt_id": item.get("attempt_id"),
                    "role": item.get("role"),
                    "delivery_mode": item.get("delivery_mode"),
                    "helper_acceptance": str(value.get("helper_acceptance")),
                })
    return {
        "pass": bool(validation.get("pass")),
        "errors": list(validation.get("errors", [])),
        "evidence": validation.get("evidence"),
        "accepted": sorted(public_accepted, key=lambda item: (str(item["role"]), str(item["attempt_id"]))),
        "integration": validation.get("integration"),
    }


def _failed_check_errors(
    checks: Mapping[str, Any],
    key: str,
) -> list[str]:
    value = checks.get(key)
    if not isinstance(value, Mapping) or value.get("pass") is True:
        return []
    raw_errors = value.get("errors")
    if isinstance(raw_errors, list) and raw_errors:
        return [f"{key}: {error}" for error in raw_errors if _nonempty(error)]
    return [f"{key} did not pass"]


def _trace_layer(
    trace: Mapping[str, Any],
    key: str,
) -> dict[str, Any]:
    layers = trace.get("layers")
    value = layers.get(key) if isinstance(layers, Mapping) else None
    if not isinstance(value, Mapping):
        return _layer_verdict([f"native trace does not expose {key}"], unobserved=True)
    errors = value.get("errors")
    copied = {
        name: item
        for name, item in value.items()
        if name not in {"pass", "status", "errors"}
    }
    status = value.get("status")
    if status == "UNOBSERVED":
        return _layer_verdict(
            [str(error) for error in errors] if isinstance(errors, list) else [],
            unobserved=True,
            **copied,
        )
    return _layer_verdict(
        [str(error) for error in errors] if isinstance(errors, list) else [],
        **copied,
    )


def _merge_layer_errors(
    layer: Mapping[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    existing = layer.get("errors")
    merged = [str(error) for error in existing] if isinstance(existing, list) else []
    for error in errors:
        if error not in merged:
            merged.append(error)
    copied = {
        name: item
        for name, item in layer.items()
        if name not in {"pass", "status", "errors"}
    }
    return _layer_verdict(
        merged,
        unobserved=layer.get("status") == "UNOBSERVED" and not errors,
        **copied,
    )


def _lifecycle_layer_verdicts(checks: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Expose independent lifecycle outcomes while retaining the v2 overall gate."""
    native_trace = checks.get("native_trace")
    trace = native_trace if isinstance(native_trace, Mapping) else {}
    layers = {
        key: _trace_layer(trace, key)
        for key in (
            "native_launch",
            "parent_continuation",
            "native_return",
            "operation_cwd_root_binding",
        )
    }
    caller_errors: list[str] = []
    for key in (
        "caller_nonpricing_preserved",
        "caller_nonpricing_index_and_layers_preserved",
        "caller_identity_and_paths_preserved",
        "raw_caller_index_preserved",
    ):
        caller_errors.extend(_failed_check_errors(checks, key))
    layers["caller_preservation"] = _layer_verdict(caller_errors)
    delivery = _trace_layer(trace, "delivery_acceptance")
    delivery_errors: list[str] = []
    for key in (
        "helper_receipts_and_outcomes",
        "managed_fixture_delivery_mode",
        "acceptance",
        "pricing_only_integration",
    ):
        delivery_errors.extend(_failed_check_errors(checks, key))
    layers["delivery_acceptance"] = _merge_layer_errors(delivery, delivery_errors)
    reports = _trace_layer(trace, "reports_cleanup")
    layers["reports_cleanup"] = _merge_layer_errors(
        reports,
        _failed_check_errors(checks, "retained_reports"),
    )
    return layers


MANIFEST_KEYS = frozenset({
    "schema", "host", "run", "primary", "caller", "source_head", "fixture_code_delivery_mode",
    "package", "baseline", "prompt", "skill_sha256", "package_tree_sha256", "workspace_helper",
})


def load_manifest(path: Path) -> dict[str, Any]:
    """Read the fixture manifest `prepare` writes; any other schema is refused."""
    manifest = load_json(path)
    if manifest.get("schema") != SCHEMA:
        raise ContractError(f"fixture manifest must use {SCHEMA}; found {manifest.get('schema')!r}: {path}")
    missing = sorted(MANIFEST_KEYS - set(manifest))
    if missing:
        raise ContractError(f"fixture manifest lacks {', '.join(missing)}: {path}")
    return manifest


def verify(args: argparse.Namespace) -> int:
    run_dir = canonical(args.run); operator = run_dir / "operator"
    manifest = load_manifest(operator / "manifest.json"); baseline = load_json(operator / "source-baseline.json")
    caller = canonical(manifest["caller"]); current = git_snapshot(caller)
    checks: dict[str, Any] = {"schema": SCHEMA, "run": str(run_dir), "host": manifest["host"], "checks": {}, "status": "PARTIAL"}
    expected = baseline["files"]
    sentinel_failures = []
    for rel, entry in expected.items():
        if rel == "pricing.json":
            continue
        now = current["files"].get(rel)
        if now != entry:
            sentinel_failures.append(rel)
    checks["checks"]["caller_nonpricing_preserved"] = {"pass": not sentinel_failures, "changed": sentinel_failures}
    nonpricing_changed = {
        key: {"expected": baseline["nonpricing_git"][key], "actual": current["nonpricing_git"][key]}
        for key in baseline["nonpricing_git"] if baseline["nonpricing_git"][key] != current["nonpricing_git"][key]
    }
    checks["checks"]["caller_nonpricing_index_and_layers_preserved"] = {"pass": not nonpricing_changed, "changed": nonpricing_changed}
    unexpected_paths = sorted((set(current["files"]) - {"pricing.json"}) ^ (set(baseline["files"]) - {"pricing.json"}))
    checks["checks"]["caller_identity_and_paths_preserved"] = {
        "pass": current["branch"] == baseline["branch"] and current["head"] == baseline["head"] and not unexpected_paths,
        "branch": {"expected": baseline["branch"], "actual": current["branch"]},
        "head": {"expected": baseline["head"], "actual": current["head"]}, "unexpected_or_missing_nonpricing_paths": unexpected_paths,
    }
    checks["checks"]["raw_caller_index_preserved"] = {"pass": current["raw_index_sha256"] == baseline["raw_index_sha256"],
        "expected": baseline["raw_index_sha256"], "actual": current["raw_index_sha256"]}
    try:
        price = json.loads((caller / "pricing.json").read_text(encoding="utf-8"))
        pricing_ok = price == {"currency": "USD", "base_price": 100, "discount_rate": 0.10}
    except (OSError, json.JSONDecodeError):
        pricing_ok = False
    checks["checks"]["pricing_only_integration"] = {"pass": pricing_ok}
    outcomes = _outcome_validation(manifest, operator)
    checks["checks"]["helper_receipts_and_outcomes"] = _public_outcomes(outcomes)
    code_modes = sorted({record.get("mode") for record in outcomes["attempts"].values() if record.get("role") == "code"})
    checks["checks"]["managed_fixture_delivery_mode"] = {
        "pass": code_modes == [manifest["fixture_code_delivery_mode"]],
        "expected": manifest["fixture_code_delivery_mode"],
        "observed": code_modes,
        "note": "The dirty managed fixture qualifies patch delivery; clean commit-delivery proof is covered by the helper suite.",
    }
    acceptance = _acceptance_validation(operator, outcomes["attempts"])
    checks["checks"]["acceptance"] = _public_acceptance(acceptance)
    trace_path = canonical(args.events) if args.events else operator / "public-native-events.json"
    if trace_path.parent != operator:
        raise ContractError(f"normalized event evidence must remain under operator evidence: {trace_path}")
    checks["checks"]["native_trace"] = _trace_v2_validation(manifest, operator, trace_path, outcomes, acceptance)
    checks["checks"]["parent_final_response"] = _parent_final_validation(manifest, trace_path)
    archive_files: list[str] = []
    for record in outcomes["attempts"].values():
        if "close" in record:
            archive_files.extend(sorted(record["close"]["artifacts"]))
    checks["checks"]["retained_reports"] = {
        "pass": outcomes["pass"] and len(archive_files) == 4,
        "files": archive_files,
        "evidence": outcomes["evidence"],
    }
    frozen_package = canonical(manifest["package"])
    package_ok = frozen_package.is_dir() and package_digest(frozen_package) == manifest["package_tree_sha256"] and canonical(manifest["workspace_helper"]).is_file()
    checks["checks"]["frozen_package_integrity"] = {"pass": package_ok, "expected_tree_sha256": manifest["package_tree_sha256"],
        "actual_tree_sha256": package_digest(frozen_package) if frozen_package.is_dir() else None, "helper": manifest["workspace_helper"]}
    checks["checks"]["lifecycle_layers"] = _lifecycle_layer_verdicts(checks["checks"])
    hard = all(checks["checks"][key]["pass"] for key in ("caller_nonpricing_preserved", "caller_nonpricing_index_and_layers_preserved", "caller_identity_and_paths_preserved", "raw_caller_index_preserved", "pricing_only_integration", "retained_reports", "helper_receipts_and_outcomes", "managed_fixture_delivery_mode", "acceptance", "frozen_package_integrity"))
    trace_ok = checks["checks"]["native_trace"]["status"] == "OBSERVED"
    checks["status"] = "COMPLETE" if hard and trace_ok else "PARTIAL" if hard else "FAILED"
    output = canonical(args.output) if args.output else operator / "verification-summary.json"
    if output.parent != operator:
        raise ContractError(f"verification output must remain under operator evidence: {output}")
    if output.exists():
        raise ContractError(f"verification evidence already exists: {output}")
    write_new(output, checks)
    print(json.dumps(checks, indent=2, sort_keys=True))
    return 0 if checks["status"] == "COMPLETE" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Test-only Ask Agent managed-workspace fixture; never launches a model.")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="create a disposable dirty caller fixture and frozen parent prompt")
    prep.add_argument("--run", required=True); prep.add_argument("--host", required=True, choices=HOSTS); prep.add_argument("--skill-root")
    prep.add_argument("--worker-delay-seconds", type=int, default=0, help="optional bounded worker delay to make parent overlap observable")
    prep.set_defaults(func=prepare)
    verify_parser = sub.add_parser("verify", help="grade retained public evidence and actual caller state")
    verify_parser.add_argument("--run", required=True)
    verify_parser.add_argument("--events", help="operator-local normalized event JSON; default is public-native-events.json")
    verify_parser.add_argument("--output", help="new operator-local JSON verdict path; default is verification-summary.json")
    verify_parser.set_defaults(func=verify)
    args = parser.parse_args()
    try:
        return args.func(args)
    except ContractError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "CONTRACT_ERROR", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
