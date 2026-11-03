"""Prove the small set of direct-run Improve files owned by one selected run."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import time
from pathlib import Path

ROOT_NAME = ".shiploop-improve"
_SCHEMA = "shiploop-improve-root-observation-v1"
_ID = re.compile(r"^[A-Za-z0-9_-]{8,160}$")
_HASH = re.compile(r"^[0-9a-f]{40,64}$")
_PASS = re.compile(r"pass-([1-9][0-9]*)\.json$")
_REVIEW = re.compile(r"review-([1-9][0-9]*)\.md$")
_MARKER = "ShipLoop standalone Improve binding: "


class AttributionError(ValueError):
    """The observed runtime paths cannot be proved to belong to this run."""


def _git(work: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-C", str(work), *args], capture_output=True, env=env, timeout=30)


def capture_baseline(work: Path) -> dict:
    """Record the prelaunch absence and identity of this workspace's runtime root."""
    result = {"schema": _SCHEMA, "root": ROOT_NAME, "observed_at_ns": None,
              "workspace": None, "workspace_dev": None, "workspace_ino": None,
              "root_absent": False, "git_observed": None, "git_mode": None,
              "git_toplevel": None, "git_head": None}
    try:
        original = work.lstat()
        workspace = work.resolve(strict=True)
        if stat.S_ISLNK(original.st_mode) or not stat.S_ISDIR(original.st_mode):
            return result
        identity = workspace.lstat()
        result.update(workspace=str(workspace), workspace_dev=identity.st_dev, workspace_ino=identity.st_ino)
        try:
            (workspace / ROOT_NAME).lstat()
        except FileNotFoundError:
            result["root_absent"] = True
        except OSError:
            return result
        result["observed_at_ns"] = time.time_ns()
        top = _git(workspace, "rev-parse", "--show-toplevel")
        if top.returncode == 0:
            result.update(git_observed=True, git_mode="git")
            result["git_toplevel"] = str(Path(top.stdout.decode("utf-8", "replace").strip()).resolve())
            head = _git(workspace, "rev-parse", "--verify", "HEAD")
            if head.returncode == 0:
                result["git_head"] = head.stdout.decode("ascii", "replace").strip()
        else:
            markers = []
            for directory in (workspace, *workspace.parents):
                try:
                    (directory / ".git").lstat()
                except FileNotFoundError:
                    continue
                except OSError:
                    return result
                markers.append(directory)
            if not markers:
                # A fresh E2E work directory is not a Git repository until its builder initializes it.
                result.update(git_observed=False, git_mode="non-git")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        pass
    return result


def _read(path: Path) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or before.st_nlink != 1:
        raise AttributionError(f"not a regular single-link file: {path.name}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise AttributionError(f"file changed while opening: {path.name}")
        raw = stream.read()
    after = path.lstat()
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise AttributionError(f"file changed while reading: {path.name}")
    return raw


def _json(path: Path) -> tuple[dict, bytes]:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    raw = _read(path)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeDecodeError, ValueError) as exc:
        raise AttributionError(f"malformed JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise AttributionError(f"JSON is not an object: {path.name}")
    return value, raw


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "stage"


def _workspace(work: Path, baseline: object) -> Path:
    if not isinstance(baseline, dict):
        raise AttributionError("prelaunch root observation is missing")
    original = work.lstat()
    root = work.resolve(strict=True)
    current = root.lstat()
    if stat.S_ISLNK(original.st_mode) or not stat.S_ISDIR(original.st_mode):
        raise AttributionError("selected workspace is linked or not a directory")
    mode = baseline.get("git_mode")
    git_identity_ok = ((mode == "git" and baseline.get("git_observed") is True
                        and baseline.get("git_toplevel") == str(root))
                       or (mode == "non-git" and baseline.get("git_observed") is False
                           and baseline.get("git_toplevel") is None and baseline.get("git_head") is None))
    if (baseline.get("schema") != _SCHEMA or baseline.get("root") != ROOT_NAME
            or baseline.get("root_absent") is not True or not git_identity_ok
            or type(baseline.get("observed_at_ns")) is not int or baseline["observed_at_ns"] <= 0
            or baseline.get("workspace") != str(root) or baseline.get("workspace_dev") != current.st_dev
            or baseline.get("workspace_ino") != current.st_ino):
        raise AttributionError("prelaunch root absence or workspace identity is unproved")
    return root


def _status_paths(lines: list[str]) -> tuple[set[str], bool]:
    untracked, contaminated = set(), False
    for line in lines:
        if len(line) < 4:
            continue
        path = line[3:]
        if path == ROOT_NAME or path.startswith(ROOT_NAME + "/"):
            if line.startswith("?? "):
                untracked.add(path)
            else:
                contaminated = True
    return untracked, contaminated


def _git_is_clean_for_runtime(work: Path, baseline: dict, contaminated: bool) -> None:
    if contaminated:
        raise AttributionError("tracked or staged Improve runtime paths are present")
    indexed = _git(work, "ls-files", "-z", "--", ROOT_NAME)
    if indexed.returncode or indexed.stdout:
        raise AttributionError("Improve runtime paths are tracked")
    current = _git(work, "rev-parse", "--verify", "HEAD")
    if current.returncode:
        raise AttributionError("current HEAD is unavailable")
    top = _git(work, "rev-parse", "--show-toplevel")
    if top.returncode or Path(top.stdout.decode("utf-8", "replace").strip()).resolve() != work:
        raise AttributionError("selected workspace is no longer the Git root")
    tree = _git(work, "ls-tree", "-r", "--name-only", "-z", "HEAD", "--", ROOT_NAME)
    history = _git(work, "log", "--all", "--format=", "--name-only", "-z", "--", ROOT_NAME)
    if tree.returncode or tree.stdout or history.returncode or history.stdout:
        raise AttributionError("Improve runtime paths occur in tracked history")
    start = baseline.get("git_head")
    if start is not None and (not isinstance(start, str) or not _HASH.fullmatch(start)):
        raise AttributionError("prelaunch Git identity is malformed")
    if start:
        prior = _git(work, "ls-tree", "-r", "--name-only", "-z", start, "--", ROOT_NAME)
        if prior.returncode or prior.stdout:
            raise AttributionError("prelaunch Git tree already contains Improve runtime paths")


def _bindings(state: dict, work: Path) -> list[dict]:
    run_id = state.get("run_id")
    history, results = state.get("history"), state.get("improve_results")
    if not isinstance(run_id, str) or not _ID.fullmatch(run_id) or not isinstance(history, list) or not isinstance(results, dict):
        raise AttributionError("selected run identity, history or Improve results are missing")
    stages = {}
    for row in history:
        if not isinstance(row, dict) or not isinstance(row.get("action"), str) or row["action"] in stages:
            raise AttributionError("selected run history is malformed or ambiguous")
        stages[row["action"]] = row.get("stage")
    found = []
    for action, record in results.items():
        if not isinstance(record, dict):
            raise AttributionError("selected run has a malformed Improve import")
        if not any(key in record for key in ("binding_id", "runtime_phase", "improve_action")):
            continue  # inherited seed record, not a direct child import
        stage = stages.get(action)
        if (record.get("runtime_phase") != "complete" or record.get("action_id") != action
                or record.get("binding_id") != f"{run_id}/{action}" or not isinstance(stage, str)
                or not stage or record.get("stage") != stage or not isinstance(record.get("improve_action"), str)
                or not _ID.fullmatch(record["improve_action"])):
            raise AttributionError(f"Improve import for {action!r} is incomplete or foreign")
        workspace = record.get("workspace")
        if not isinstance(workspace, str) or Path(workspace).resolve(strict=True) != work:
            raise AttributionError(f"Improve import for {action!r} belongs to another workspace")
        found.append({"action": action, "stage": stage, "binding_id": f"{run_id}/{action}", "record": record})
    if not found:
        raise AttributionError("selected run has no complete imported Improve result")
    return found


def _reference(work: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise AttributionError("Improve receipt has a non-local evidence path")
    relative = Path(value)
    if ".." in relative.parts:
        raise AttributionError("Improve evidence traverses outside the workspace")
    return work / relative


def _child_files(work: Path, child: Path, binding: dict) -> set[str]:
    record, action, stage = binding["record"], binding["action"], binding["stage"]
    if child.name != f"{_slug(stage)}-{action[-8:]}" or not _ID.fullmatch(action):
        raise AttributionError("Improve child directory does not match the selected action")
    start, _ = _json(child / "start.json")
    context = start.get("context")
    request = context.get("request") if isinstance(context, dict) else None
    marker = _MARKER + binding["binding_id"]
    if (start.get("workspace") != str(work) or not isinstance(request, str)
            or request.splitlines().count(marker) != 1):
        raise AttributionError("Improve start packet is not uniquely bound to the selected action")

    packet_path = child / "packet.json"
    packet, packet_raw = _json(packet_path)
    terminal_context = packet.get("context")
    terminal_request = terminal_context.get("request") if isinstance(terminal_context, dict) else None
    if (packet.get("status") != "complete" or packet.get("receipt") != str(packet_path)
            or packet.get("workspace") != str(work) or terminal_context != context
            or not isinstance(terminal_request, str) or terminal_request.splitlines().count(marker) != 1):
        raise AttributionError("Improve terminal receipt is incomplete or foreign")
    state_file = packet.get("state_file")
    if not isinstance(state_file, str) or not Path(state_file).is_absolute():
        raise AttributionError("Improve terminal state path is malformed")
    try:
        Path(state_file).lstat()
    except FileNotFoundError:
        pass
    else:
        raise AttributionError("Improve terminal state is still present")
    progress, report = packet.get("progress"), packet.get("last_report")
    if (not isinstance(progress, dict) or type(progress.get("action_number")) is not int
            or progress["action_number"] < 1 or not isinstance(report, dict)
            or report.get("classification") != "trivial" or report.get("exit_assessment") != "satisfied"
            or report.get("continuation_assessment") == "cancelled"):
        raise AttributionError("Improve terminal receipt does not prove a completed review")
    identities = record.get("identities")
    if (not isinstance(identities, dict)
            or identities.get("terminal_packet_sha256") != hashlib.sha256(packet_raw).hexdigest()):
        raise AttributionError("selected run does not bind the terminal receipt")

    reviews = child / "reviews"
    receipt = record.get("receipt")
    review_refs = receipt.get("review_refs") if isinstance(receipt, dict) else None
    check_refs = receipt.get("check_refs") if isinstance(receipt, dict) else None
    if (not isinstance(review_refs, list) or len(review_refs) not in (1, 2)
            or not isinstance(check_refs, list) or not check_refs):
        raise AttributionError("selected run has an incomplete evidence receipt")
    pass_files = {}
    for path in reviews.iterdir():
        match = _PASS.fullmatch(path.name)
        if match:
            pass_files[int(match.group(1))] = path
    numbers = sorted(pass_files)
    if not numbers or numbers != list(range(1, numbers[-1] + 1)) or numbers[-1] != progress["action_number"]:
        raise AttributionError("Improve pass records are absent, discontinuous or do not match the receipt")

    allowed = {child / name for name in ("opening.md", "start.json", "handoff.md", "parent-return.md", "packet.json")}
    if (child / "commit-message.md").exists() or (child / "commit-message.md").is_symlink():
        allowed.add(child / "commit-message.md")
    allowed.add(reviews / "checks.md")
    for number, path in sorted(pass_files.items()):
        facts, _ = _json(path)
        if (type(facts.get("pass")) is not int or facts["pass"] != number
                or not isinstance(facts.get("tree"), str) or not _HASH.fullmatch(facts["tree"])
                or not isinstance(facts.get("changed"), bool) or "commit" not in facts
                or facts["commit"] is not None and not isinstance(facts["commit"], str)):
            raise AttributionError(f"Improve pass {number} record is malformed")
        tree = _git(work, "cat-file", "-e", facts["tree"] + "^{tree}")
        if tree.returncode:
            raise AttributionError(f"Improve pass {number} tree cannot be resolved")
        if facts["commit"] is not None:
            commit = facts["commit"]
            if not re.fullmatch(r"[0-9a-f]{7,64}", commit) or _git(work, "rev-parse", "--verify", commit + "^{commit}").returncode:
                raise AttributionError(f"Improve pass {number} commit cannot be resolved")
        report_path, review_path = reviews / f"report-{number}.json", reviews / f"review-{number}.md"
        _json(report_path)
        _read(review_path)
        allowed.update((path, report_path, review_path))
        result_path = reviews / f"result-{number}.json"
        if result_path.exists() or result_path.is_symlink():
            _read(result_path)
            allowed.add(result_path)

    refs = {}
    for group in (review_refs, check_refs):
        for value in group:
            path = _reference(work, value)
            refs[str(value)] = path
    review_numbers = []
    for value in review_refs:
        path = refs[value]
        match = _REVIEW.fullmatch(path.name)
        if path.parent != reviews or match is None or int(match.group(1)) not in pass_files:
            raise AttributionError("Improve receipt references a foreign review")
        review_numbers.append(int(match.group(1)))
    if review_numbers != numbers[-len(review_numbers):]:
        raise AttributionError("Improve receipt reviews do not match the final recorded passes")
    for value in check_refs:
        path = refs[value]
        if path.is_relative_to(work / ROOT_NAME):
            if path != reviews / "checks.md":
                raise AttributionError("Improve receipt references an unrecognized runtime check file")
        elif not path.is_relative_to(work):
            raise AttributionError("Improve receipt check escapes the workspace")

    expected_refs = set(refs)
    digests = identities.get("evidence_sha256")
    evidence = record.get("evidence")
    archived = {row.get("source"): row.get("sha256") for row in evidence if isinstance(row, dict)} if isinstance(evidence, list) else {}
    if not isinstance(digests, dict) or set(digests) != expected_refs or set(archived) != expected_refs:
        raise AttributionError("selected run has incomplete evidence digests")
    for value, path in refs.items():
        if path.is_relative_to(work / ROOT_NAME):
            if path not in allowed or hashlib.sha256(_read(path)).hexdigest() != digests.get(value):
                raise AttributionError("selected run evidence differs from its runtime receipt")
        if digests.get(value) != archived.get(value) or not isinstance(digests.get(value), str):
            raise AttributionError("selected run evidence archive is malformed")

    resources = context.get("resources") if isinstance(context, dict) else None
    if isinstance(resources, list) and any(
            isinstance(row, dict) and row.get("purpose") == "native owner record (parent coordination data)"
            and row.get("locator") == str(child / "host-owner.md") for row in resources):
        allowed.add(child / "host-owner.md")
    result = set()
    for path in allowed:
        _read(path)
        result.add(path.relative_to(work).as_posix())
    return result


def _scan(root: Path, expected_children: set[str]) -> set[str]:
    files, directories = set(), set()
    for here, names, filenames in os.walk(root, followlinks=False):
        relative = Path(here).relative_to(root)
        for name in names:
            path = Path(here) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise AttributionError("Improve runtime contains a symlink or special directory")
            directories.add(path.relative_to(root).as_posix())
        for name in filenames:
            path = Path(here) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise AttributionError("Improve runtime contains a symlink or special file")
            files.add(path.relative_to(root.parent).as_posix())
        if relative == Path(".") and set(names) != expected_children:
            raise AttributionError("Improve runtime has an unbound child directory")
        if relative.parts and len(relative.parts) == 1 and set(names) != {"reviews"}:
            raise AttributionError("Improve child has an unbound directory")
        if relative.parts and len(relative.parts) == 2 and names:
            raise AttributionError("Improve reviews contain an unbound directory")
    expected_dirs = {name for child in expected_children for name in (child, f"{child}/reviews")}
    if directories != expected_dirs:
        raise AttributionError("Improve runtime has an unbound or missing directory")
    return files


def owned_untracked_paths(work: Path, run_dir: Path | None, state: dict, baseline: object,
                          status_lines: list[str]) -> tuple[set[str], str | None]:
    """Return exact run-owned untracked paths, or leave all runtime dirt as product dirt."""
    candidates, contaminated = _status_paths(status_lines)
    if not candidates:
        if contaminated:
            return set(), "tracked or staged Improve runtime paths are present"
        try:
            (work / ROOT_NAME).lstat()
        except FileNotFoundError:
            return set(), None
        except OSError as exc:
            return set(), " ".join(str(exc).split())[:240] or type(exc).__name__
    try:
        workspace = _workspace(work, baseline)
        if run_dir is None or not run_dir.is_absolute():
            raise AttributionError("selected run directory is missing")
        run_info = run_dir.lstat()
        if stat.S_ISLNK(run_info.st_mode) or not stat.S_ISDIR(run_info.st_mode):
            raise AttributionError("selected run directory is linked or not a directory")
        run_dir = run_dir.resolve(strict=True)
        state_info = (run_dir / "state.md").lstat()
        if stat.S_ISLNK(state_info.st_mode) or not stat.S_ISREG(state_info.st_mode):
            raise AttributionError("selected run state is missing or linked")
        for wrapper in (run_dir.parent / "workspace.md", run_dir.parent / "return-receipt.md"):
            try:
                wrapper.lstat()
            except FileNotFoundError:
                continue
            raise AttributionError("selected run uses a workspace wrapper, not direct mode")
        repo = state.get("repo")
        if not isinstance(repo, str) or Path(repo).resolve(strict=True) != workspace:
            raise AttributionError("selected run belongs to another workspace")
        _git_is_clean_for_runtime(workspace, baseline, contaminated)
        root = workspace / ROOT_NAME
        info = root.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise AttributionError("Improve runtime root is not a real directory")
        bindings = _bindings(state, workspace)
        expected = {_slug(row["stage"]) + "-" + row["action"][-8:] for row in bindings}
        if len(expected) != len(bindings):
            raise AttributionError("selected Improve actions collide on one child directory")
        for binding in bindings:
            child = root / (_slug(binding["stage"]) + "-" + binding["action"][-8:])
            # Scan every start marker, not only the expected child's start file.
            starts = []
            for candidate in root.glob("*/start.json"):
                start, _ = _json(candidate)
                context = start.get("context")
                request = context.get("request") if isinstance(context, dict) else None
                if isinstance(request, str) and request.splitlines().count(_MARKER + binding["binding_id"]):
                    starts.append(candidate)
            if len(starts) != 1 or starts[0].parent != child:
                raise AttributionError("selected Improve binding is absent or ambiguous")
        recognized = set()
        for binding in bindings:
            recognized.update(_child_files(workspace, root / (_slug(binding["stage"]) + "-" + binding["action"][-8:]), binding))
        if _scan(root, expected) != recognized:
            raise AttributionError("Improve runtime contains an unrecognized artifact")
        if candidates != recognized:
            raise AttributionError("untracked Improve runtime paths do not match the recognized artifact set")
        return recognized & candidates, None
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        reason = " ".join(str(exc).split())[:240] or type(exc).__name__
        return set(), reason
