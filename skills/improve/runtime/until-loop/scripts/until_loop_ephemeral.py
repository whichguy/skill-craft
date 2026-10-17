"""Small script-owned callback runtime for one ephemeral Innerloop run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


MAX_JSON_INTEGER_DIGITS = 4_300
_CONTRACT_FIELDS = {
    "workspace",
    "work",
    "exit_condition",
    "repeat_condition",
    "required_trivial_reviews",
    "candidate_paths",
    "context",
    "exit_checks",
}
_REQUIRED_INPUT_CONTRACT_FIELDS = _CONTRACT_FIELDS - {"required_trivial_reviews", "candidate_paths", "exit_checks"}
# The review gate is the contract's required_trivial_reviews, kept under its upstream name so a contract stays valid for
# the published until-loop plugin: 0 completes on the first report that assesses the exit as satisfied, 1 also needs the
# report to classify the pass trivial, and 2 is the UNCHANGED gate (owner 2026-10-16, the Improve gate): the report must
# be trivial and satisfied AND the runtime must measure the content tree after the pass equal to the tree after the
# previous pass (for the first pass: the tree at start).  A pass that changed the tree never completes the loop, however
# it is labelled; the label is necessary, the measured fact decides.  No count, no timer.  The value 2 no longer counts
# two reviews.
# 3 is the same measurement with the rule this runtime had before the stop rule, for code reviews (efficiency plan D-6 / R1,
# a proposal awaiting the owner's S-10 text): a first pass that is trivial, satisfied and leaves the content as it started
# completes; once any pass has changed the content, two consecutive trivial, satisfied passes that each leave it unchanged
# are needed.  Anything above 3 is refused.  Both are measured by the runtime, never counted from the report's label.
UNCHANGED_GATE = 2
UNCHANGED_AFTER_EDIT_GATE = 3
_UNCHANGED_GATES = (UNCHANGED_GATE, UNCHANGED_AFTER_EDIT_GATE)
_CHECK_FIELDS = {"id", "clause", "command"}
CHECK_OUTPUT_CHARS = 300
_CHECK_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_VERIFY_DELIMITER = "__UNTIL_LOOP_VERIFY__"
_CHECK_HEADER = "=== until-loop check "
_CHECK_RESULT = "UNTIL-LOOP-CHECK"
# Anchored at the end: a check whose output lacks a final newline still yields its result line.
_RESULT_LINE = re.compile(r"UNTIL-LOOP-CHECK (\S+) exit=(\d+)$")
MAX_REPAIRS_PER_CHECK = 2
_REPAIR_FIELDS = {"id", "command", "reason"}
_CONTEXT_FIELDS = {"request", "scope", "authority", "environment", "resources"}
_RESOURCE_FIELDS = {"purpose", "locator"}
_STATE_FIELDS = {
    "contract",
    "run_id",
    "action_number",
    "trivial_streak",
    "last_report",
    "last_tree",
    "last_pass_changed_tree",
    "receipt",
    "last_checks",
    "check_repairs",
    "verify_record",
}
# Runtime and review-note locations that never count as a change to the workspace.
_RUNTIME_EXCLUDES = (".shiploop-improve", ".shiploop", ".until-loop", ".git")
_TREE_ID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_REPORT_FIELDS = {
    "classification",
    "exit_assessment",
    "continuation_assessment",
    "evidence",
    "handoff",
}
_CLASSIFICATIONS = {"trivial", "non-trivial", "unresolved"}
_EXIT_ASSESSMENTS = {"satisfied", "unsatisfied", "unknown"}
_CONTINUATION_ASSESSMENTS = {"allowed", "blocked", "cancelled"}


class StateError(ValueError):
    """Raised when callback state or protocol input is absent, unsafe, or invalid."""


def _parse_json_integer(value: str) -> int:
    if len(value.lstrip("-")) > MAX_JSON_INTEGER_DIGITS:
        raise ValueError("JSON integer exceeds the digit limit")
    return int(value)


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{name} must be a nonblank string")
    return value


def _require_nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StateError(f"{name} must be a nonnegative integer")
    return value


def _require_positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StateError(f"{name} must be a positive integer")
    return value


def _validate_context(context: object) -> dict[str, Any]:
    if not isinstance(context, dict) or set(context) != _CONTEXT_FIELDS:
        raise StateError("context has an invalid schema")
    resources = context["resources"]
    if not isinstance(resources, list):
        raise StateError("context.resources must be a list")
    normalized_resources: list[dict[str, str]] = []
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict) or set(resource) != _RESOURCE_FIELDS:
            raise StateError(f"context.resources[{index}] has an invalid schema")
        normalized_resources.append(
            {
                "purpose": _require_text(resource["purpose"], f"context.resources[{index}].purpose"),
                "locator": _require_text(resource["locator"], f"context.resources[{index}].locator"),
            }
        )
    return {
        "request": _require_text(context["request"], "context.request"),
        "scope": _require_text(context["scope"], "context.scope"),
        "authority": _require_text(context["authority"], "context.authority"),
        "environment": _require_text(context["environment"], "context.environment"),
        "resources": normalized_resources,
    }


_RETIRED_STATE = (
    "this run's state was written by an older Until Loop (it records start_tree): the runtime now records last_tree, and "
    "required_trivial_reviews 2 ends the loop on one trivial, satisfied pass that leaves the content tree as the "
    "previous pass left it (3: after a pass has changed it, on two such passes in a row). The state cannot be "
    "continued; start a new run with a current contract"
)


def _validate_candidate_paths(paths: object) -> list[str]:
    """Extra candidate files the content tree also covers: absolute, unique paths (they may not exist yet)."""
    if not isinstance(paths, list):
        raise StateError("candidate_paths must be a list of absolute file paths")
    out: list[str] = []
    for index, value in enumerate(paths):
        text = _require_text(value, f"candidate_paths[{index}]")
        if "\x00" in text or not os.path.isabs(text):
            raise StateError(f"candidate_paths[{index}] must be an absolute file path")
        if text in out:
            raise StateError("candidate_paths must be unique")
        out.append(text)
    return out


def _check_command_syntax(check_id: str, command: str) -> None:
    """Refuse a command /bin/sh cannot parse (it would stop the whole verify script before anything is recorded)."""
    if "\x00" in command:
        raise StateError("exit check commands cannot contain NUL")
    if any(line.strip() == _VERIFY_DELIMITER for line in command.splitlines()):
        raise StateError(f"exit check {check_id!r} cannot contain the line {_VERIFY_DELIMITER}")
    try:
        parsed = subprocess.run(["/bin/sh", "-n", "-c", command], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=10)  # -n parses only; nothing runs
    except (OSError, subprocess.TimeoutExpired):
        return
    if parsed.returncode != 0:
        raise StateError(f"exit check {check_id!r} is not valid sh syntax: {parsed.stderr.strip()[-200:]}")


def _validate_checks(checks: object, *, parse: bool = False) -> list[dict[str, str]]:
    """Frozen exit checks: shell commands written from the request before any work."""
    if not isinstance(checks, list):
        raise StateError("exit_checks must be a list of checks")
    out, seen = [], set()
    for check in checks:
        if not isinstance(check, dict) or set(check) != _CHECK_FIELDS:
            raise StateError("each exit check must have exactly id, clause and command")
        item = {k: _require_text(check[k], f"exit_checks.{k}") for k in ("id", "clause", "command")}
        if not _CHECK_ID.fullmatch(item["id"]):
            raise StateError("exit check ids must be 1-64 characters of letters, digits, '.', '_' or '-'")
        if "\x00" in item["command"]:
            raise StateError("exit check commands cannot contain NUL")
        if parse:  # new contracts only; frozen state was parsed when it was created
            _check_command_syntax(item["id"], item["command"])
        if item["id"] in seen:
            raise StateError("exit check ids must be unique")
        seen.add(item["id"])
        out.append(item)
    return out


def _verify_script(path: Path, state: dict[str, Any]) -> str | None:
    """The shell script the executor runs with its own shell tool: every frozen check, piped into `record`.

    The executor's shell tool runs it, so the host's permissions, hooks and sandbox see every check command; the
    pipe hands the real exit codes and output to the runtime, which records them for this action.  The runtime
    itself never executes a check.
    """
    contract = state["contract"]
    if not contract["exit_checks"]:
        return None
    workspace = shlex.quote(contract["workspace"])
    lines = [f"/bin/sh <<'{_VERIFY_DELIMITER}'", "{"]
    for check in contract["exit_checks"]:
        lines += [f"printf '%s\\n' {shlex.quote(_CHECK_HEADER + check['id'])}",
                  f"(cd -- {workspace} || exit 125",
                  check["command"],
                  ") </dev/null 2>&1",
                  f"printf '\\n{_CHECK_RESULT} %s exit=%s\\n' {shlex.quote(check['id'])} \"$?\""]
    record = shlex.join([str(Path(os.path.abspath(sys.executable))), str(Path(os.path.abspath(__file__))),
                         "record", "--state", str(path), f"--action={_action_token(state)}"])
    lines += ["} 2>&1 | " + record, _VERIFY_DELIMITER]
    return "\n".join(lines) + "\n"


def _bounded_lines(stream: Any, limit: int = 8192) -> Any:
    """Yield decoded lines from a byte stream in bounded memory; an over-long line keeps only its end."""
    pending = b""
    while True:
        chunk = stream.read(65536)
        if not chunk:
            break
        pending += chunk
        *lines, pending = pending.split(b"\n")
        for line in lines:
            yield line[-limit:].decode("utf-8", errors="replace") + "\n"
        pending = pending[-limit:]
    if pending:
        yield pending.decode("utf-8", errors="replace")


def _parse_verify_output(stream: Any, contract: dict[str, Any], echo: Any) -> list[dict[str, Any]]:
    """Read verify_script output (echoing it), keeping each check's exit code and a bounded output tail."""
    ids = [c["id"] for c in contract["exit_checks"]]
    codes: dict[str, int] = {}
    tails: dict[str, str] = {i: "" for i in ids}
    current = None
    for line in _bounded_lines(stream):
        echo.write(line)
        stripped = line.rstrip("\n")
        if stripped.startswith(_CHECK_HEADER) and stripped[len(_CHECK_HEADER):] in tails:
            current = stripped[len(_CHECK_HEADER):]
            continue
        match = _RESULT_LINE.search(stripped)
        if match and match.group(1) in tails:
            codes[match.group(1)] = int(match.group(2))
            current = None
            continue
        if current is not None:
            tails[current] = (tails[current] + line)[-4 * CHECK_OUTPUT_CHARS:]
    results = []
    for i in ids:
        code = codes.get(i)
        passed = code == 0
        tail = "" if passed else (tails[i].strip()[-CHECK_OUTPUT_CHARS:] if code is not None
                                  else "no result line: the verify script did not finish this check")
        results.append({"id": i, "passed": passed, "exit_code": code, "output_tail": tail})
    return results


def record(path: str | os.PathLike[str], action_id: str, stream: Any, echo: Any) -> str:
    """Record one verify_script run for the current action; return a one-line summary."""
    mismatch = ("action token does not match the current run and action; run the current packet's "
                "verify_script")
    fd, state_path = _open_state(path, os.O_RDONLY)
    try:
        before = _read_state_fd(fd)
    finally:
        os.close(fd)
    if not isinstance(action_id, str) or action_id != _action_token(before):
        raise StateError(mismatch)
    results = _parse_verify_output(stream, before["contract"], echo)
    # Commit only if the run is still at the same action: a late recorder never overwrites a newer action.
    fd, state_path = _open_state(path, os.O_RDWR)
    try:
        current = _read_state_fd(fd)
        if action_id != _action_token(current) or current["contract"] != before["contract"]:
            raise StateError(mismatch)
        updated = {**current, "last_checks": results,
                   "verify_record": {"action_number": current["action_number"],
                                     "tree": _content_tree(current["contract"])}}
        _write_payload_fd(fd, _encode_state(updated))
    finally:
        os.close(fd)
    failed = [r["id"] for r in results if not r["passed"]]
    return (f"UNTIL-LOOP-RECORDED {len(results)} checks for this action: "
            + (f"{len(failed)} failed ({', '.join(failed)})" if failed else "all passed"))


def _validate_contract(contract: object, *, input_contract: bool) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise StateError("contract must be an object")
    fields = set(contract)
    if "context" not in fields:
        raise StateError(
            "contract.context is required; runs without immutable continuity context "
            "are not supported, so start a new run with a complete context"
        )
    extra = fields - _CONTRACT_FIELDS
    missing = (_REQUIRED_INPUT_CONTRACT_FIELDS if input_contract else _CONTRACT_FIELDS - {"exit_checks"}) - fields
    if extra or missing:
        raise StateError("contract has an invalid schema")

    workspace = _require_text(contract["workspace"], "workspace")
    workspace_path = Path(workspace)
    if not workspace_path.is_absolute() or not workspace_path.is_dir():
        raise StateError("workspace must be an existing absolute directory")
    normalized: dict[str, Any] = {
        "workspace": workspace,
        "work": _require_text(contract["work"], "work"),
        "exit_condition": _require_text(contract["exit_condition"], "exit_condition"),
        "repeat_condition": _require_text(contract["repeat_condition"], "repeat_condition"),
    }
    gate = _require_nonnegative_integer(contract.get("required_trivial_reviews", 0), "required_trivial_reviews")
    if gate > UNCHANGED_AFTER_EDIT_GATE:
        raise StateError("required_trivial_reviews must be 0, 1, 2 or 3: 2 and 3 are the unchanged-content gates and "
                         "no longer count that many reviews")
    normalized["required_trivial_reviews"] = gate
    normalized["candidate_paths"] = _validate_candidate_paths(contract.get("candidate_paths", []))
    normalized["context"] = _validate_context(contract["context"])
    normalized["exit_checks"] = _validate_checks(contract.get("exit_checks", []), parse=input_contract)
    return normalized


def _validate_report(report: object) -> dict[str, str]:
    if not isinstance(report, dict):
        raise StateError("report has an invalid schema")
    fields = set(report)
    if "handoff" not in fields:
        raise StateError(
            "report.handoff is required; reports without a continuation handoff are not supported"
        )
    if fields - {"check_repairs"} != _REPORT_FIELDS:
        raise StateError("report has an invalid schema")
    classification = report["classification"]
    if not isinstance(classification, str) or classification not in _CLASSIFICATIONS:
        raise StateError("report.classification is invalid")
    exit_assessment = report["exit_assessment"]
    if not isinstance(exit_assessment, str) or exit_assessment not in _EXIT_ASSESSMENTS:
        raise StateError("report.exit_assessment is invalid")
    continuation = report["continuation_assessment"]
    if not isinstance(continuation, str) or continuation not in _CONTINUATION_ASSESSMENTS:
        raise StateError("report.continuation_assessment is invalid")
    evidence = _require_text(report["evidence"], "report.evidence")
    if classification == "unresolved" and exit_assessment == "satisfied":
        raise StateError("an unresolved report cannot claim a satisfied exit")
    validated = {
        "classification": classification,
        "exit_assessment": exit_assessment,
        "continuation_assessment": continuation,
        "evidence": evidence,
        "handoff": _require_text(report["handoff"], "report.handoff"),
    }
    if "check_repairs" in report:
        repairs = report["check_repairs"]
        if not isinstance(repairs, list) or not all(isinstance(r, dict) and set(r) == _REPAIR_FIELDS for r in repairs):
            raise StateError("report.check_repairs must be a list of {id, command, reason}")
        validated["check_repairs"] = [{k: _require_text(r[k], f"check_repairs.{k}") for k in ("id", "command", "reason")}
                                      for r in repairs]
    return validated


def _validate_state(state: object) -> dict[str, Any]:
    if isinstance(state, dict) and "start_tree" in state:
        raise StateError(_RETIRED_STATE)
    if not isinstance(state, dict) or set(state) != _STATE_FIELDS:
        raise StateError("state has an invalid schema")
    contract = _validate_contract(state["contract"], input_contract=False)
    run_id = _require_text(state["run_id"], "run_id")
    action_number = _require_positive_integer(state["action_number"], "action_number")
    trivial_streak = _require_nonnegative_integer(state["trivial_streak"], "trivial_streak")
    last_report = state["last_report"]
    if last_report is None:
        if action_number != 1 or trivial_streak != 0:
            raise StateError("initial state must have action number one and no streak")
    else:
        last_report = _validate_report(last_report)
        if action_number < 2:
            raise StateError("state with a report must have a successor action")
        if last_report["classification"] == "trivial":
            # A failed frozen check resets the streak even for a report that called itself trivial; later
            # records replace last_checks, so with checks a trivial report may legitimately carry no streak.
            if trivial_streak < 1 and not contract["exit_checks"]:
                raise StateError("a trivial report requires a positive streak")
        elif trivial_streak != 0:
            raise StateError("a non-trivial or unresolved report resets the streak")
        if trivial_streak > action_number - 1:
            raise StateError("trivial_streak cannot exceed completed actions")
    last_tree = state["last_tree"]
    if last_tree is not None and (not isinstance(last_tree, str) or not _TREE_ID.fullmatch(last_tree)):
        raise StateError("last_tree must be a content tree ID or null")
    changed = state["last_pass_changed_tree"]
    if changed is not None and not isinstance(changed, bool):
        raise StateError("last_pass_changed_tree must be a boolean or null")
    if last_report is None and changed is not None:
        raise StateError("initial state cannot have measured a completed pass")
    receipt = state["receipt"]
    if receipt is not None:
        receipt = str(_receipt_path(receipt))
    last_checks = state["last_checks"]
    if last_checks is not None and not (
        isinstance(last_checks, list)
        and all(isinstance(r, dict) and set(r) == {"id", "passed", "exit_code", "output_tail"} for r in last_checks)
    ):
        raise StateError("last_checks has an invalid schema")
    check_repairs = state["check_repairs"]
    if not isinstance(check_repairs, list):
        raise StateError("check_repairs has an invalid schema")
    verify_record = state["verify_record"]
    if verify_record is not None and not (
        isinstance(verify_record, dict) and set(verify_record) == {"action_number", "tree"}
        and isinstance(verify_record["action_number"], int)
        and (verify_record["tree"] is None or (isinstance(verify_record["tree"], str)
                                               and _TREE_ID.fullmatch(verify_record["tree"])))
    ):
        raise StateError("verify_record has an invalid schema")
    return {
        "contract": contract,
        "run_id": run_id,
        "action_number": action_number,
        "trivial_streak": trivial_streak,
        "last_report": last_report,
        "last_tree": last_tree,
        "last_pass_changed_tree": changed,
        "receipt": receipt,
        "last_checks": last_checks,
        "check_repairs": check_repairs,
        "verify_record": verify_record,
    }


def _receipt_path(value: object) -> Path:
    """An absolute receipt file path whose parent exists and which is not a directory or link."""
    if not isinstance(value, str) or not value.strip():
        raise StateError("receipt must be a nonblank absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise StateError("receipt must be an absolute path")
    if not path.parent.is_dir():
        raise StateError("receipt's parent must be an existing directory")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise StateError("receipt must be a regular file path, not a link or directory")
    return path


def _write_receipt(state: dict[str, Any], packet: dict[str, Any]) -> None:
    """Atomically save the packet at the run's receipt path before it is printed.

    The receipt is the durable copy a host reads after it lost the printed
    packet (a compaction, a cleared context, a killed session).  It is written
    before a terminal transition deletes the state file, so a completed run's
    evidence never depends on the host having saved stdout.
    """
    if state.get("receipt") is None:
        return
    path = _receipt_path(state["receipt"])
    payload = (json.dumps(packet, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", suffix=".json", dir=str(path.parent))
    try:
        try:
            os.fchmod(fd, 0o600)
            _write_payload_fd(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def _tree_excludes() -> list[str]:
    """The pathspecs a content tree leaves out: the runtime's own and the review notes' locations."""
    excludes = [":(exclude,glob)**/" + part + "/**" for part in _RUNTIME_EXCLUDES]
    excludes.append(":(exclude,glob)**/innerloop-*.json")
    # The measurement's own scratch (a temporary index file, or a throwaway repository) when TMPDIR lies inside the workspace:
    # it would otherwise be part of the tree it is measuring and no pass could ever read as unchanged.
    excludes.extend((":(exclude,glob)**/until-loop-tree-*", ":(exclude,glob)**/until-loop-tree-*/**"))
    return excludes


def _plain_tree(workspace: str) -> str | None:
    """The content tree of a directory that is not a Git worktree, measured through a throwaway bare repository.

    The same rule as in a worktree (every file, ``.gitignore`` files in the directory honoured, runtime and review-note
    locations left out), so an explicit in-place run outside Git ends its Improve review the same way.  The
    repository and its index live in a temporary directory that is removed afterwards; nothing is written into the
    workspace.  ``None`` on any Git error, as for a worktree.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="until-loop-tree-") as scratch:
            repository = os.path.join(scratch, "tree.git")
            plain = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
            if subprocess.run(["git", "init", "-q", "--bare", repository], capture_output=True, text=True,
                              env=plain, timeout=60, check=False).returncode:
                return None
            env = {**plain, "GIT_DIR": repository, "GIT_WORK_TREE": workspace,
                   "GIT_INDEX_FILE": os.path.join(scratch, "index"), "GIT_OPTIONAL_LOCKS": "0"}
            def git(*args: str) -> subprocess.CompletedProcess:
                return subprocess.run(["git", *args], cwd=workspace, capture_output=True, text=True,
                                      env=env, timeout=60, check=False)
            if git("add", "-A", "--", ".", *_tree_excludes()).returncode:
                return None
            written = git("write-tree")
            tree = written.stdout.strip()
            return tree if written.returncode == 0 and _TREE_ID.fullmatch(tree) else None
    except (OSError, subprocess.SubprocessError):
        return None


def _workspace_tree(workspace: str) -> str | None:  # the Git part of the content tree
    """A content tree of the workspace (tracked and untracked, never ignored or runtime files).

    Built in a private index so the real index is untouched.  A directory that is not a Git worktree is measured
    through a throwaway bare repository (``_plain_tree``).  ``None`` on any Git error: then no pass can be shown
    unchanged.
    """
    def git(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", workspace, *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False)
    try:
        located = git("rev-parse", "--git-path", "index")
        if located.returncode:
            return _plain_tree(workspace)
        real_index = Path(located.stdout.strip())
        if not real_index.is_absolute():
            real_index = Path(workspace) / real_index
        fd, index = tempfile.mkstemp(prefix="until-loop-tree-", suffix=".index")
        os.close(fd)
        try:
            if real_index.is_file():
                Path(index).write_bytes(real_index.read_bytes())
                # Make every cached entry "racily clean" so Git re-hashes the file instead of trusting its stat data.
                # A same-size edit within the same second as the cached stat would otherwise go unseen (the copy's
                # fresh mtime defeats Git's own racy check), and a change must never read as "unchanged".
                os.utime(index, (1, 1))
            else:
                os.unlink(index)
            env = {**os.environ, "GIT_INDEX_FILE": index, "GIT_OPTIONAL_LOCKS": "0"}
            if git("add", "-A", "--", ".", *_tree_excludes(), env=env).returncode:
                return None
            written = git("write-tree", env=env)
            tree = written.stdout.strip()
            return tree if written.returncode == 0 and _TREE_ID.fullmatch(tree) else None
        finally:
            if os.path.exists(index):
                os.unlink(index)
    except (OSError, subprocess.SubprocessError):
        return None


def _content_tree(contract: dict[str, Any]) -> str | None:
    """The content tree a pass is compared by: the workspace's Git tree plus the bytes of the contract's extra
    candidate files (a stage result that lives outside the worktree).

    With no extra paths this is the Git tree ID itself.  With them it is a SHA-256 over the Git tree and each path's
    content digest (a path that does not exist contributes ``absent``, so creating the file counts as a change).
    ``None`` when the Git tree is unavailable or a candidate file cannot be read: then no pass can be shown
    unchanged.
    """
    tree = _workspace_tree(contract["workspace"])
    if tree is None or not contract["candidate_paths"]:
        return tree
    rows = ["git " + tree]
    for name in contract["candidate_paths"]:
        path = Path(name)
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "absent"
        except OSError:
            return None
        rows.append(name + "\t" + digest)
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _encode_state(state: dict[str, Any]) -> bytes:
    normalized = _validate_state(state)
    # No size cap (owner, 2026-10-11): a long-form request, its checks and a full handoff must never be refused for
    # length. The state does not grow with iterations: each report and handoff replaces the last.
    return json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _state_path(path: str | os.PathLike[str]) -> Path:
    try:
        candidate = Path(path)
    except (TypeError, ValueError) as error:
        raise StateError("state path is invalid") from error
    return candidate if candidate.is_absolute() else Path(os.path.abspath(candidate))


def _open_state(path: str | os.PathLike[str], flags: int) -> tuple[int, Path]:
    candidate = _state_path(path)
    try:
        before = os.lstat(candidate)
    except OSError as error:
        raise StateError(f"state file is unavailable: {candidate}") from error
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise StateError("state file must be a regular single-link file")
    try:
        fd = os.open(candidate, flags | getattr(os, "O_NOFOLLOW", 0))
    except OSError as error:
        raise StateError(f"cannot open state file: {candidate}") from error
    try:
        after = os.fstat(fd)
        if (
            not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise StateError("state file changed or is unsafe")
    except BaseException:
        os.close(fd)
        raise
    return fd, candidate


def _read_state_fd(fd: int) -> dict[str, Any]:
    size = os.fstat(fd).st_size
    if size < 1:
        raise StateError("state file has an invalid size")
    os.lseek(fd, 0, os.SEEK_SET)
    payload = bytearray()
    while len(payload) < size:
        chunk = os.read(fd, size - len(payload))
        if not chunk:
            raise StateError("state file changed while being read")
        payload.extend(chunk)
    try:
        parsed = json.loads(payload.decode("utf-8"), parse_int=_parse_json_integer)
    except ValueError as error:
        raise StateError("state file is not valid JSON") from error
    return _validate_state(parsed)


def _write_payload_fd(fd: int, payload: bytes) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    written = 0
    while written < len(payload):
        count = os.write(fd, payload[written:])
        if count <= 0:
            raise OSError("could not write state file")
        written += count


def _write_state_fd(fd: int, state: dict[str, Any]) -> None:
    _write_payload_fd(fd, _encode_state(state))


def _delete_owned(path: Path, identity: os.stat_result) -> None:
    try:
        current = os.lstat(path)
    except OSError as error:
        raise StateError("terminal state file is unavailable for deletion") from error
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_nlink != 1
        or (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino)
    ):
        raise StateError("terminal state file changed before deletion")
    try:
        path.unlink()
    except OSError as error:
        raise StateError("could not delete terminal state file") from error


def _discard_created_file(path: Path, identity: os.stat_result | None) -> None:
    if identity is None:
        return
    try:
        current = os.lstat(path)
        if (
            stat.S_ISREG(current.st_mode)
            and current.st_nlink == 1
            and (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)
        ):
            path.unlink()
    except OSError:
        pass


def read_state(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read active state without creating, repairing, or advancing it."""
    fd, _ = _open_state(path, os.O_RDONLY)
    try:
        return _read_state_fd(fd)
    finally:
        os.close(fd)


def _action_token(state: dict[str, Any]) -> str:
    return f"{state['run_id']}:{state['action_number']}"


def _required_trivial_reviews(state: dict[str, Any]) -> int:
    return state["contract"]["required_trivial_reviews"]


def _unchanged_gate(state: dict[str, Any]) -> bool:
    return _required_trivial_reviews(state) in _UNCHANGED_GATES


def _previous_pass_clean(state: dict[str, Any]) -> bool:
    """Whether the latest completed pass was trivial and satisfied, its checks passed, and it left the content as the
    pass before it left it.  ``trivial_streak`` is above 0 only after a trivial pass whose checks passed, so with the
    report and the measured fact this needs no state of its own: gate 3 reads the pair from the state gate 2 keeps."""
    report = state["last_report"]
    return (report is not None and report["classification"] == "trivial" and report["exit_assessment"] == "satisfied"
            and state["trivial_streak"] >= 1 and state["last_pass_changed_tree"] is False)


def _next_argv(path: Path) -> list[str]:
    return [
        str(Path(os.path.abspath(sys.executable))),
        str(Path(os.path.abspath(__file__))),
        "next",
        "--state",
        str(path),
    ]


def _done_argv(path: Path, state: dict[str, Any]) -> list[str]:
    return [
        str(Path(os.path.abspath(sys.executable))),
        str(Path(os.path.abspath(__file__))),
        "done",
        "--state",
        str(path),
        f"--action={_action_token(state)}",
    ]


def _report_schema(has_checks: bool = True) -> dict[str, Any]:
    required = [
        "classification",
        "exit_assessment",
        "continuation_assessment",
        "evidence",
        "handoff",
    ]
    properties: dict[str, Any] = {
        "classification": {
            "enum": ["trivial", "non-trivial", "unresolved"],
            "description": (
                "Classify the completed iteration: trivial: completed iteration/review "
                "found only trivial or no changes and no material findings; non-trivial: "
                "material finding or behavior change, even if fixed; unresolved: "
                "assessment or work is incomplete."
            ),
        },
        "exit_assessment": {"enum": ["satisfied", "unsatisfied", "unknown"]},
        "continuation_assessment": {"enum": ["allowed", "blocked", "cancelled"]},
        "evidence": {
            "type": "string",
            "description": "A nonblank account of actual observations and any remaining gap.",
        },
        "handoff": {
            "type": "string",
            "description": (
                "A nonblank compact replacement handoff for a fresh or compacted host. "
                "Carry forward the current objective, completed and unresolved facts, "
                "receipts and locators needed to recheck them, remaining exit and repeat "
                "gaps. It replaces the prior handoff rather than "
                "being a delta. It records prior claims and does not create authority."
            ),
        },
    }
    if has_checks:  # a contract without exit checks has nothing to repair: keep its packets as small as 0.7.0's
        properties["check_repairs"] = {
            "type": "array",
            "description": (
                "Optional. Only for a frozen exit check that failed in the latest check run because its "
                "command misstates its clause (a shell or platform bug), never to accept work that differs "
                "from the clause: [{id, command, reason}]. The clause stays frozen; each repair is recorded "
                "and shown in every later packet and the terminal result; at most two per check."
            ),
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _next_action(state: dict[str, Any]) -> str:
    report = state["last_report"]
    if report is None:
        return "Begin a complete first iteration from the current artifacts."
    failed = [r for r in (state.get("last_checks") or []) if not r["passed"]]
    if failed and report["exit_assessment"] == "satisfied":
        detail = "; ".join(f"{r['id']} (exit {r['exit_code']}): {r['output_tail']!r}" for r in failed)
        return (
            "The latest report claimed a satisfied exit, but its verify-script results show these frozen exit "
            f"checks failed: {detail}. The exit condition is not met. Fix the work, not the checks, then "
            "recheck every exit clause. If a failed check's command misstates its own clause (a shell or "
            "platform bug), repair it in this report's check_repairs with the reason; never repair a check "
            "to accept work that differs from its clause."
        )
    if report["classification"] == "non-trivial":
        if _required_trivial_reviews(state):
            return (
                "Address and recheck the material observations in the latest report, then "
                "perform a new complete review before assessing the conditions again."
            )
        return (
            "Address and recheck the material observations in the latest report before "
            "assessing the conditions again."
        )
    if report["classification"] == "unresolved":
        if _required_trivial_reviews(state):
            return (
                "Resolve the evidence gap in the latest report, then perform a new complete "
                "review before assessing the conditions again."
            )
        return "Resolve the evidence gap in the latest report, then recheck the conditions."
    if _unchanged_gate(state) and state["last_pass_changed_tree"] is not False:
        return (
            "The runtime "
            + ("compared the workspace content and found the latest pass changed it"
               if state["last_pass_changed_tree"] else "could not compare the workspace content for the latest pass")
            + ", so that pass cannot end the loop however it was labelled. Perform another distinct full review; "
            + ("the loop ends on two consecutive passes you report trivial and satisfied that each leave the content "
               "as the pass before left it."
               if _required_trivial_reviews(state) == UNCHANGED_AFTER_EDIT_GATE else
               "the loop ends on a pass you report trivial and satisfied that leaves the content as the previous "
               "pass left it.")
        )
    if _required_trivial_reviews(state) == UNCHANGED_AFTER_EDIT_GATE and _previous_pass_clean(state):
        return (
            "The latest pass was trivial and satisfied and left the content unchanged. At this gate that ends the loop "
            "only on the first pass or as the second of two consecutive such passes, so perform one more distinct "
            "full review; it ends the loop if you again report trivial and satisfied and the content is again "
            "unchanged."
        )
    if not _unchanged_gate(state) and state["trivial_streak"] < _required_trivial_reviews(state):
        return (
            "Perform another distinct full review to establish whether the exit condition and "
            "configured trivial-review gate are now met."
        )
    return "Resolve the outstanding exit-condition gap in the latest evidence, then recheck it."


def _packet_context(state: dict[str, Any]) -> dict[str, Any]:
    context = state["contract"]["context"]
    return {
        "request": context["request"],
        "scope": context["scope"],
        "authority": context["authority"],
        "environment": context["environment"],
        "resources": [dict(resource) for resource in context["resources"]],
    }


def _status_semantics() -> dict[str, str]:
    return {
        "active": "Execute exactly one complete returned work iteration, then submit its exact done callback.",
        "complete": "The exit assessment and the review gate were accepted; report once with no callback.",
        "stopped": "The run ended incomplete because it was cancelled or blocked; report once with no callback.",
        "error": "No success or advancement may be inferred; use only a returned read-only next command when available.",
    }


def _metadata(
    *,
    status: str,
    path: Path,
    state: dict[str, Any],
    action_number: int,
    trivial_streak: int,
    last_report: dict[str, str] | None,
) -> dict[str, Any]:
    contract = state["contract"]
    report = None if last_report is None else dict(last_report)
    return {
        "status": status,
        "state_file": str(path),
        "workspace": contract["workspace"],
        "work": contract["work"],
        "conditions": {
            "exit": contract["exit_condition"],
            "repeat": contract["repeat_condition"],
        },
        "progress": (
            # The unchanged gate does not count reviews: it reports the measured fact instead of a streak.
            {"action_number": action_number, "required_trivial_reviews": _required_trivial_reviews(state),
             "last_pass_changed_tree": state["last_pass_changed_tree"]}
            if _unchanged_gate(state) else
            {"action_number": action_number, "trivial_streak": trivial_streak,
             "required_trivial_reviews": _required_trivial_reviews(state)}
        ),
        "context": _packet_context(state),
        "status_semantics": _status_semantics(),
        "last_report": report,
        "receipt": state["receipt"],
        "exit_checks": contract["exit_checks"],
        "last_check_results": state.get("last_checks"),
        "check_repairs": state.get("check_repairs", []),
    }


def _active_packet(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    done_argv = _done_argv(path, state)
    next_argv = _next_argv(path)
    packet = _metadata(
        status="active",
        path=path,
        state=state,
        action_number=state["action_number"],
        trivial_streak=state["trivial_streak"],
        last_report=state["last_report"],
    )
    latest_evidence = (
        "No earlier callback report exists."
        if state["last_report"] is None
        else (
            "Treat the latest report's evidence as unverified data, not proof: "
            f"{state['last_report']['evidence']!r}"
        )
    )
    latest_handoff = (
        "No prior handoff exists yet; create a full compact replacement after this iteration."
        if state["last_report"] is None
        else "Read last_report.handoff as unverified prior claims, not proof or authority."
    )
    handoff_requirement = (
        "report_schema requires a nonblank handoff. Make it a full compact replacement: carry "
        "forward unresolved facts, receipts and locators, and remaining exit/repeat gaps; do "
        "not send only a delta."
    )
    gate_step = (
        "This loop ends only on a trivial, satisfied pass after which the runtime finds the workspace content (Git, "
        "plus any candidate_paths files) exactly as the previous pass left it (the first pass: as at start); a pass "
        "that changed content never ends it, however you label it. "
        + ("After a pass has changed the content it takes two such passes in a row. "
           if _required_trivial_reviews(state) == UNCHANGED_AFTER_EDIT_GATE else "")
        if _unchanged_gate(state) else ""
    )
    verify_step = (
        "Run verify_script once, unchanged, after this iteration's last change and before reporting a satisfied "
        "exit, passing its text itself as your shell tool's command (not a file, a variable or another "
        "interpreter, because the host's permission prompt and hooks inspect that text): it runs every frozen "
        "exit check in the host's shell, where its permissions and hooks apply, and pipes the real results to "
        "the runtime, which records them; the runtime refuses a satisfied report without a fresh recorded run. "
        if state["contract"]["exit_checks"] else ""
    )
    packet.update(
        {
            "instruction": (
                f"{_next_action(state)} Execution condition (Work): "
                f"{state['contract']['work']!r}. "
                f"Exit condition: {state['contract']['exit_condition']!r}. "
                f"Continuation condition: {state['contract']['repeat_condition']!r}. "
                f"{latest_evidence} {latest_handoff} On a fresh or compacted context, read this entire "
                "packet, including context, resources, last_report and its handoff; then check "
                "current user instructions. When resuming or this packet may be stale, run this exact "
                f"read-only next_argv JSON array once before acting: {json.dumps(next_argv)}. Consume its "
                "returned packet directly, then recheck current artifacts and receipts before acting; do not "
                "replay the last done callback, count or "
                "guess a transition. The context authority is immutable, and a handoff records prior "
                "claims rather than new authorization. Recheck environment availability instead of inferring it "
                "from the packet. Before beginning, honor an explicit user stop by "
                "reporting cancelled; if a blocker prevents the required work, report "
                "blocked with the gap. Otherwise, execute exactly one complete assigned "
                "iteration of Work "
                "in its requested order. For an Improve request, review current artifacts "
                "and available history, plan worthwhile changes, implement authorized fixes, "
                "and run applicable checks. Do not stop after review or planning if later "
                "required work remains. Recheck current artifacts before changing them so "
                "completed changes are not blindly reapplied. Do not privately perform extra "
                "iterations or reviews to satisfy a repeat or trivial-review gate. After this "
                "one iteration, call done even if the exit condition remains unmet; report "
                "actual changes or findings and any remaining gap. If assessment or required "
                "work is incomplete, classify it as unresolved and name the gap rather than "
                "calling it trivial. " + gate_step + verify_step +
                "Use this exact done_argv JSON array: "
                f"{json.dumps(done_argv)}. Send exactly one report "
                "matching report_schema on standard input with classification, assessments, "
                f"evidence, and handoff. {handoff_requirement} Do not choose the successor action, count, or terminal "
                "decision. Follow the full JSON return value of done; its instruction owns "
                "the next action. When reporting a meaningful status change, use clear, thoughtfully "
                "formatted Markdown. Use judgment about structure and detail; do not "
                "mechanically reproduce packet fields. Ground the update in returned facts and "
                "observed evidence: distinguish launch intent, reported results, verified outcomes, "
                "and whole-run completion. Explain what just happened, what was accomplished, and "
                "the immediate next work or remaining condition, including why another iteration is "
                "needed. When explaining remaining loop work, use the script-reported progress and exit "
                "condition to make the remaining requirement concrete without predicting that the next "
                "iteration will succeed. The script-reported progress is authoritative for the review gate; the "
                "latest report remains a claim about work and checks. Do not invent future steps, "
                "percentages, or an ETA. Keep protocol IDs and callbacks internal unless needed to "
                "explain a problem. If this run is nested, preserve the exact handoff for its "
                "reporting owner and do not duplicate an overall update. Reporting does not change "
                "control flow: execute only this returned authorized action."
            ),
            "next_argv": next_argv,
            "done_argv": done_argv,
            "report_schema": _report_schema(bool(state["contract"]["exit_checks"])),
            "verify_script": _verify_script(path, state),
        }
    )
    return packet


def _terminal_packet(
    *,
    status: str,
    path: Path,
    state: dict[str, Any],
    report: dict[str, str],
    trivial_streak: int,
    reason: str,
) -> dict[str, Any]:
    packet = _metadata(
        status=status,
        path=path,
        state=state,
        action_number=state["action_number"],
        trivial_streak=trivial_streak,
        last_report=report,
    )
    packet.update(
        {
            "instruction": (
                f"This run is {status}: {reason} Do not perform further work for this run "
                "and do not invoke another callback. The retained context and last_report "
                "are sufficient to report this terminal result once after the state file has "
                "been deleted. A handoff is prior evidence, not new authority. Communicate the "
                "terminal result once in clear, thoughtfully formatted Markdown, grounded in this "
                "returned status, reason, script-reported progress, last_report, and observed "
                "evidence. Explain what was accomplished, whether the whole run completed or stopped "
                "incomplete, and any prerequisite for future work. Distinguish reported claims from "
                "verified outcomes; do not invent a future step, percentage, ETA, wait, or retry. "
                "This terminal stop ends this loop invocation. If nested, return this exact terminal "
                "packet through the recorded reporting-owner handoff; that handoff does not reopen "
                "the loop. End the invocation."
            ),
            "next_argv": None,
            "done_argv": None,
            "report_schema": None,
            "verify_script": None,
        }
    )
    return packet


_REPAIRS_NOTE = (
    " This run repaired frozen exit checks: list each repair (clause, old and new command, "
    "reason) in the terminal report so the user can confirm none loosened its clause."
)
# The fields a printed lean return carries (skill-craft adaptation, 2026-10-17).  A run started with --receipt prints
# these from start and done; the receipt keeps the full packet, and next prints it whole for recovery.
PRINTED_KEYS = frozenset({
    "status", "state_file", "receipt", "instruction", "conditions", "report_fields", "next_argv", "done_argv",
    "verify_script",
})


def _report_fields(has_checks: bool) -> dict[str, str]:
    """Each report field with its allowed values: the enums come from ``_report_schema`` so the two never differ."""
    properties = _report_schema(has_checks)["properties"]
    fields = {name: "|".join(prop["enum"]) for name, prop in properties.items() if "enum" in prop}
    fields["evidence"] = "nonblank: this iteration's observations and any remaining gap"
    fields["handoff"] = "nonblank: the full compact replacement handoff, not a delta"
    if "check_repairs" in properties:
        fields["check_repairs"] = ("optional [{id, command, reason}], only for a failed check whose command "
                                   "misstates its clause, with an unsatisfied exit")
    return fields


def _printed_active(path: Path, state: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """The lean return ``start`` and a non-terminal ``done`` print when the run keeps a receipt (else the packet).

    The work, full conditions, context, progress and the last report stay in the contract and the receipt: printing
    them on every return cost 19 to 22 KB per non-terminal ``done`` in a live run.
    """
    if state["receipt"] is None:
        return packet
    verify = (", run verify_script once, unchanged, as your shell tool's command after the iteration's last change "
              "and before reporting a satisfied exit" if state["contract"]["exit_checks"] else "")
    return {
        "status": packet["status"],
        "state_file": str(path),
        "receipt": state["receipt"],
        "instruction": (
            f"{_next_action(state)} Do one complete iteration of the contract's Work{verify}, then send one JSON "
            "report with report_fields on standard input to done_argv even if the exit is unmet (incomplete work is "
            "unresolved, never trivial; a blocker is continuation blocked) and follow its returned instruction: the "
            "runtime alone decides the next action, the count and completion. The receipt holds the full packet "
            "(work, conditions, context, progress, last report and handoff, report_schema): read it first on a fresh "
            "or compacted context, or run next_argv once if the run may have moved on."
        ),
        "conditions": {"exit": state["contract"]["exit_condition"]},
        "report_fields": _report_fields(bool(state["contract"]["exit_checks"])),
        "next_argv": packet["next_argv"],
        "done_argv": packet["done_argv"],
        "verify_script": packet["verify_script"],
    }


def _printed_terminal(packet: dict[str, Any], reason: str, repaired: bool) -> dict[str, Any]:
    """The lean return a terminal ``done`` prints when the run keeps a receipt (else the packet)."""
    if packet["receipt"] is None:
        return packet
    return {
        "status": packet["status"],
        "state_file": packet["state_file"],
        "receipt": packet["receipt"],
        "instruction": (
            f"This run is {packet['status']}: {reason} Do no further work and invoke no callback for this run; "
            "report its result once from the receipt file (final report, progress and check results), keeping "
            "reported claims apart from verified outcomes, and if nested return the receipt to its reporting owner."
            + (_REPAIRS_NOTE if repaired else "")
        ),
        "conditions": {"exit": packet["conditions"]["exit"]},
        "report_fields": None,
        "next_argv": None,
        "done_argv": None,
        "verify_script": None,
    }


def start(
    contract: object,
    directory: str | os.PathLike[str] | None = None,
    receipt: str | None = None,
) -> dict[str, Any]:
    """Create private state for a logical run and return its first action packet.

    With ``receipt``, every packet this run returns is also written to that file.
    """
    return _start(contract, directory, receipt)[0]


def _start(
    contract: object,
    directory: str | os.PathLike[str] | None = None,
    receipt: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``start``, plus the return the command line prints (lean when the run keeps a receipt)."""
    initial = {
        "contract": _validate_contract(contract, input_contract=True),
        "run_id": secrets.token_urlsafe(18),
        "action_number": 1,
        "trivial_streak": 0,
        "last_report": None,
        "last_tree": None,
        "last_pass_changed_tree": None,
        "receipt": None if receipt is None else str(_receipt_path(receipt)),
        "last_checks": None,
        "check_repairs": [],
        "verify_record": None,
    }
    # The unchanged gate closes on a trivial pass that left the content as the previous pass left it (the first pass:
    # as it is now), so the runtime, not the report, decides that.  Without a measurable tree no pass could ever be
    # shown unchanged and the loop would never end: refuse it here.
    if initial["contract"]["required_trivial_reviews"] in _UNCHANGED_GATES:
        initial["last_tree"] = _content_tree(initial["contract"])
        if initial["last_tree"] is None:
            raise StateError(
                "required_trivial_reviews 2 or 3 (unchanged content) needs a content tree the runtime can measure: "
                "git must be able to snapshot the workspace (git add and write-tree must succeed on its files, in a "
                "worktree or not) and every candidate_paths file must be readable; otherwise use "
                "required_trivial_reviews 1"
            )
    payload = _encode_state(initial)
    if directory is not None:
        try:
            directory_path = Path(directory)
        except (TypeError, ValueError) as error:
            raise StateError("directory is invalid") from error
        if not directory_path.is_dir():
            raise StateError("directory must be an existing directory")
        directory = str(directory_path)
    try:
        fd, raw_path = tempfile.mkstemp(prefix="innerloop-", suffix=".json", dir=directory)
    except OSError as error:
        raise StateError("could not create state file") from error
    path = _state_path(raw_path)
    identity: os.stat_result | None = None
    try:
        identity = os.fstat(fd)
        os.fchmod(fd, 0o600)
        _write_payload_fd(fd, payload)
    except BaseException:
        _discard_created_file(path, identity)
        raise
    finally:
        os.close(fd)
    packet = _active_packet(path, initial)
    try:
        _write_receipt(initial, packet)
    except BaseException:
        # A run whose receipt cannot be written would not have its durable copy.
        _discard_created_file(path, identity)
        raise
    return packet, _printed_active(path, initial, packet)


def next_packet(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Reprint the current action packet without advancing state."""
    fd, state_path = _open_state(path, os.O_RDONLY)
    try:
        state = _read_state_fd(fd)
        packet = _active_packet(state_path, state)
    finally:
        os.close(fd)
    # Refresh the durable copy too; this never advances the run.
    _write_receipt(state, packet)
    return packet


def done(
    path: str | os.PathLike[str], action_id: str, report: object
) -> dict[str, Any]:
    """Accept one report for the issued action and choose the next transition."""
    return _done(path, action_id, report)[0]


def _done(
    path: str | os.PathLike[str], action_id: str, report: object
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``done``, plus the return the command line prints (lean when the run keeps a receipt)."""
    fd, state_path = _open_state(path, os.O_RDWR)
    try:
        current = _read_state_fd(fd)
        if not isinstance(action_id, str) or action_id != _action_token(current):
            raise StateError("action token does not match the current run and action")
        validated_report = _validate_report(report)
        repairs = validated_report.pop("check_repairs", [])
        repair_log = list(current["check_repairs"])
        if repairs:
            failed = {r["id"] for r in (current["last_checks"] or []) if not r["passed"]}
            checks = [dict(c) for c in current["contract"]["exit_checks"]]
            by_id = {c["id"]: c for c in checks}
            for r in repairs:
                if r["id"] not in by_id:
                    raise StateError(f"check_repairs names unknown check {r['id']!r}")
                if r["id"] not in failed:
                    raise StateError(f"check {r['id']!r} can be repaired only after it failed in the latest check run")
                if sum(1 for x in repair_log if x["id"] == r["id"]) >= MAX_REPAIRS_PER_CHECK:
                    raise StateError(f"check {r['id']!r} has used its {MAX_REPAIRS_PER_CHECK} repairs; report blocked instead")
                _check_command_syntax(r["id"], r["command"])
                repair_log.append({"id": r["id"], "clause": by_id[r["id"]]["clause"], "old_command": by_id[r["id"]]["command"],
                                   "new_command": r["command"], "reason": r["reason"],
                                   "action_number": current["action_number"]})
                by_id[r["id"]]["command"] = r["command"]
            current = {**current, "contract": {**current["contract"], "exit_checks": checks}}
        current = {**current, "check_repairs": repair_log}
        continuation = validated_report["continuation_assessment"]
        recorded = current["verify_record"]
        fresh = recorded is not None and recorded["action_number"] == current["action_number"]
        check_results = current["last_checks"] if fresh else None
        if (validated_report["exit_assessment"] == "satisfied" and continuation != "cancelled"
                and current["contract"]["exit_checks"]):
            if repairs:
                raise StateError("check_repairs cannot accompany a satisfied exit: report the repair with an "
                                 "unsatisfied exit, then run the next packet's verify_script")
            if not fresh:
                raise StateError("no verify run is recorded for this action: run this packet's verify_script with "
                                 "your own shell tool after the iteration's last change, then report again")
            if recorded["tree"] is not None and _content_tree(current["contract"]) != recorded["tree"]:
                raise StateError("the workspace changed after the recorded verify run: run this packet's "
                                 "verify_script again after the last change, then report again")
        checks_pass = check_results is None or all(r["passed"] for r in check_results)

        if validated_report["classification"] == "trivial" and checks_pass:
            trivial_streak = current["trivial_streak"] + 1
        else:
            # A failed frozen check contradicts a clean assessment, so it never counts toward the gate.
            trivial_streak = 0
        # The unchanged gate (owner decision 2026-10-16, generalising the 2026-09-26 unchanged-first-pass rule from the
        # first pass to any pass): a trivial, satisfied pass completes the loop only when the content tree measured
        # here from Git (plus the contract's candidate files), not taken from the report, equals the tree the previous
        # pass left (the first pass: the tree at start).  A pass that changed the tree never completes the loop,
        # however it is labelled, so a material pass is always followed by at least one more.  No count, no timer.
        unchanged_gate = _unchanged_gate(current)
        tree_now = _content_tree(current["contract"]) if unchanged_gate else None
        before = current["last_tree"]
        changed = None if tree_now is None or before is None else tree_now != before
        trivial_report = validated_report["classification"] == "trivial"
        if unchanged_gate:
            gate_met = trivial_report and changed is False
            if _required_trivial_reviews(current) == UNCHANGED_AFTER_EDIT_GATE:
                # Gate 3 (code reviews): the first pass completes by itself; afterwards the pass before it must have been
                # a trivial, satisfied pass that left the content unchanged too.
                gate_met = gate_met and (current["action_number"] == 1 or _previous_pass_clean(current))
        else:
            gate_met = trivial_streak >= _required_trivial_reviews(current)
        measured = {**current, "last_pass_changed_tree": changed}
        updated = {
            **measured,
            "action_number": current["action_number"] + 1,
            "trivial_streak": trivial_streak,
            "last_report": validated_report,
            "last_tree": tree_now,
            "last_checks": current["last_checks"],
        }
        # The contract and report must fit on every path (terminal receipts stay bounded); runtime check
        # output and the repair log count only against the state an active run keeps.
        _encode_state({**updated, "check_repairs": [],
                       "last_checks": None if updated["last_checks"] is None
                       else [{**r, "output_tail": ""} for r in updated["last_checks"]]})
        stop: tuple[str, str] | None = None
        if continuation == "cancelled":
            stop = ("stopped", "the callback explicitly cancelled it.")
        elif validated_report["exit_assessment"] == "satisfied" and checks_pass and gate_met:
            stop = ("complete",
                    "the semantic exit assessment is satisfied and the pass was trivial with the "
                    "workspace content unchanged from the previous pass"
                    + (", and the pass before it was also trivial and satisfied with the content unchanged, "
                       if _required_trivial_reviews(current) == UNCHANGED_AFTER_EDIT_GATE
                       and current["action_number"] > 1 else ", ")
                    + "which meets the review gate."
                    if unchanged_gate
                    else "the semantic exit assessment is satisfied and the review gate is met.")
        elif continuation == "blocked":
            stop = ("stopped", "the continuation assessment is blocked before completion.")

        if stop is not None:
            terminal = _terminal_packet(
                status=stop[0],
                path=state_path,
                state=measured,
                report=validated_report,
                trivial_streak=trivial_streak,
                reason=stop[1],
            )
            terminal["last_check_results"] = check_results
            repaired = bool(current["check_repairs"])
            if repaired:
                terminal["instruction"] += _REPAIRS_NOTE
            # Persist the terminal packet before its state disappears.
            _write_receipt(current, terminal)
            _delete_owned(state_path, os.fstat(fd))
            return terminal, _printed_terminal(terminal, stop[1], repaired)
        # Only an active run keeps state; the terminal path above has already returned.
        _write_payload_fd(fd, _encode_state(updated))
        packet = _active_packet(state_path, updated)
        _write_receipt(updated, packet)
        return packet, _printed_active(state_path, updated, packet)
    finally:
        os.close(fd)


class _ProtocolParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise StateError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _ProtocolParser(prog=Path(__file__).name)
    commands = parser.add_subparsers(dest="command", required=True)
    start_parser = commands.add_parser("start")
    start_parser.add_argument("--directory")
    start_parser.add_argument("--receipt", help="absolute file the runtime writes every returned packet to")
    next_parser = commands.add_parser("next")
    next_parser.add_argument("--state", required=True)
    done_parser = commands.add_parser("done")
    done_parser.add_argument("--state", required=True)
    done_parser.add_argument("--action", required=True)
    record_parser = commands.add_parser("record", help="read a verify_script run on stdin and record its results")
    record_parser.add_argument("--state", required=True)
    record_parser.add_argument("--action", required=True)
    return parser


def _stdin_json() -> object:
    try:
        return json.load(sys.stdin, parse_int=_parse_json_integer)
    except ValueError as error:
        raise StateError("standard input must contain valid JSON") from error


def _write_json(value: object) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":"), ensure_ascii=True))
    sys.stdout.write("\n")


def _error_packet(error: StateError, state_path: Path | None = None) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "status": "error",
        "state_change": "unchanged",
        "instruction": (
            "Do not repeat work or infer a terminal outcome. This rejected input or cleanup "
            "failure did not advance the run. Correct input only from actual evidence. If the "
            "state is missing, it cannot distinguish lost terminal output from corruption or "
            "cancellation; never infer success or initialize a replacement run. If a status update "
            "is needed, use clear Markdown grounded only in this error and state_change: say that "
            "the result is unverified and correction or recovery is pending. Do not turn reporting "
            "into a retry, an advancement claim, or a new run."
        ),
        "error": str(error),
    }
    if state_path is not None:
        next_argv = _next_argv(state_path)
        packet.update(
            {
                "state_file": str(state_path),
                "next_argv": next_argv,
                "done_argv": None,
                "report_schema": None,
                "instruction": (
                    "Do not repeat work or invoke a callback from this error packet. This input "
                    "was rejected without advancing the run. Use this exact read-only next_argv "
                    f"JSON array at most once to retrieve and validate a current packet before any correction: "
                    f"{json.dumps(next_argv)}. If that read cannot return a valid current packet, stop "
                    "incomplete and report uncertainty. Do not repeatedly retry next, replay work or done, "
                    "or initialize a replacement run. If a status update is needed, use clear Markdown "
                    "grounded only in this error, unchanged state, and any successful read-only recovery. "
                    "Keep protocol details internal unless they explain the problem, distinguish a rejected "
                    "claim from a verified outcome, and do not turn reporting into a retry or advancement."
                ),
            }
        )
    return packet


def _uncertain_error_packet(error: OSError, state_path: Path | None = None) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "status": "error",
        "state_change": "unknown",
        "instruction": (
            "Do not replay work, retry the callback, or assume advancement. A filesystem "
            "operation may have partially changed this run. A missing state cannot distinguish "
            "lost terminal output from corruption or cancellation; never infer success or "
            "initialize a replacement run. If a status update is needed, use clear Markdown grounded "
            "only in this error and unknown state change: report uncertainty rather than completion, "
            "and do not turn reporting into a retry, an advancement claim, or a new run."
        ),
        "error": str(error),
    }
    if state_path is not None:
        next_argv = _next_argv(state_path)
        packet.update(
            {
                "state_file": str(state_path),
                "next_argv": next_argv,
                "done_argv": None,
                "report_schema": None,
                "instruction": (
                    "Do not replay work, retry the callback, or assume advancement. A filesystem "
                    "operation may have partially changed this run. Use this exact read-only "
                    f"next_argv JSON array at most once to retrieve and validate a current packet: "
                    f"{json.dumps(next_argv)}. If that read cannot return a valid current packet, stop "
                    "incomplete and report uncertainty. Do not repeatedly retry next, replay work or done, "
                    "or initialize a replacement run. If a status update is needed, use clear Markdown "
                    "grounded only in this error, unknown state change, and any successful read-only recovery. "
                    "Report uncertainty rather than completion, keep protocol details internal unless they "
                    "explain the problem, and do not turn reporting into a retry or advancement."
                ),
            }
        )
    return packet


def _known_state_path(args: argparse.Namespace | None) -> Path | None:
    if args is None or getattr(args, "command", None) not in {"next", "done", "record"}:
        return None
    try:
        return _state_path(args.state)
    except (AttributeError, StateError):
        return None


def main(argv: list[str] | None = None) -> int:
    """Run the thin JSON-stdin/JSON-stdout command-line protocol."""
    args: argparse.Namespace | None = None
    try:
        args = _parser().parse_args(argv)
        if args.command == "record":
            try:
                summary = record(args.state, args.action, sys.stdin.buffer, sys.stdout)
            except (StateError, OSError) as error:
                sys.stdout.write(f"UNTIL-LOOP-RECORD-ERROR {error}: nothing was recorded\n")
                return 2
            sys.stdout.write(summary + "\n")
            return 0
        if args.command == "start":
            result = _start(_stdin_json(), directory=args.directory, receipt=args.receipt)[1]
        elif args.command == "next":
            result = next_packet(args.state)  # the recovery read prints the full packet
        else:
            result = _done(args.state, args.action, _stdin_json())[1]
    except StateError as error:
        _write_json(_error_packet(error, _known_state_path(args)))
        return 2
    except OSError as error:
        _write_json(_uncertain_error_packet(error, _known_state_path(args)))
        return 2
    _write_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
