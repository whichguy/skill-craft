#!/usr/bin/env python3
"""Build and verify an isolated ask-agent worktree experiment fixture."""

from __future__ import annotations

import argparse
from diagnostics import emit_diagnostics, evidence_reference, make_diagnostic, report_check_diagnostics

import base64
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKER_COUNTS = (3, 5)
DELIVERY_MODES = ("patch", "commits", "ephemeral")
DIRTY_PATHS = ("dual.txt", "added.txt", "deleted.txt", "notes.txt", ".gitignore")
EXPECTED_BASE_STATUS = {
    "added.txt": "A ",
    "deleted.txt": " D",
    "dual.txt": "MM",
    "notes.txt": "??",
}
PIPELINE_INPUTS = [-7, -1, 0, 1, 9, 100]
ORACLE_INPUTS = [-10**30, -999, -7, -1, 0, 1, 9, 100, 10**30]
IGNORE_DIRS = {"__pycache__"}
MARKER_RELATIVE_PATH = ".experiment-local/owner.txt"
MIN_PARALLEL_HOLD_OVERLAP_SECONDS = 0.1
VERIFICATION_SUMMARY_SCHEMA = "ask-agent-fixture-verification-summary/v1"
STATE_CHECK_KEYS = (
    "root_is_distinct_from_parent",
    "common_dir_matches_fixture",
    "head_matches_caller_snapshot",
    "index_entries_tree_and_staged_layer_match",
    "unstaged_dirty_input_diffs_match",
    "dirty_status_layers_match",
    "working_tree_matches_except_owned_step",
    "nonowner_source_files_unchanged",
    "owner_changed_from_baseline",
)
EPHEMERAL_STATE_CHECK_KEYS = (
    *STATE_CHECK_KEYS,
    "ephemeral_branch_unchanged",
    "ephemeral_no_commits",
)
COMMIT_STATE_CHECK_KEYS = (
    "root_is_distinct_from_parent",
    "common_dir_matches_fixture",
    "commit_baseline_binding",
    "commit_base_parent_matches_caller",
    "private_commit_tree_matches_snapshot",
    "worker_baseline_matches_caller_snapshot",
    "head_matches_commit_phase",
    "index_is_clean_at_head",
    "worker_has_no_uncommitted_residuals",
    "working_tree_matches_except_owned_step",
    "nonowner_source_files_unchanged",
    "owner_changed_from_baseline",
    "worker_history_is_linear_owner_only",
    "root_controls_preserved",
)


class FixtureError(RuntimeError):
    pass


def default_skill_root() -> Path:
    """Find skills/ask-agent relative to this checkout or the current Git repo."""
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "skills" / "ask-agent"
        if candidate.is_dir():
            return candidate
    try:
        repository = Path(git(Path.cwd(), "rev-parse", "--show-toplevel")).resolve()
        candidate = repository / "skills" / "ask-agent"
        if candidate.is_dir():
            return candidate
    except FixtureError:
        pass
    raise FixtureError("cannot find skills/ask-agent; pass --skill-root explicitly")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_exclusive(path: Path, payload: bytes) -> None:
    """Publish a complete file atomically without replacing existing evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise FixtureError(f"refusing to replace existing file: {path}") from exc
    except OSError as exc:
        raise FixtureError(f"cannot publish {path}: {exc}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_exclusive_text(path: Path, value: str) -> None:
    write_exclusive(path, value.encode("utf-8"))


def write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    write_exclusive_text(path, payload)


def run_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float = 20,
    text: bool = True,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    child_environment = os.environ.copy()
    child_environment["GIT_OPTIONAL_LOCKS"] = "0"
    if environment:
        child_environment.update(environment)
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            timeout=timeout,
            text=text,
            env=child_environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FixtureError(f"command failed to run: {args!r}: {exc}") from exc
    if check and result.returncode:
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        stderr = result.stderr if isinstance(result.stderr, str) else ""
        raise FixtureError(
            f"command exited {result.returncode}: {args!r}\n{stdout}\n{stderr}".strip()
        )
    return result


def git(
    root: Path,
    *args: str,
    check: bool = True,
    timeout: float = 20,
    environment: dict[str, str] | None = None,
) -> str:
    result = run_process(
        ["git", "-C", str(root), *args],
        check=check,
        timeout=timeout,
        environment=environment,
    )
    return result.stdout.strip()


def resolve_git_path(root: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def package_tree_sha256(root: Path) -> str:
    """Hash relative names and bytes, excluding Python cache artifacts."""
    root = root.resolve()
    digest = hashlib.sha256()
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORE_DIRS)
        current_path = Path(current)
        for name in sorted(filenames):
            path = current_path / name
            if path.suffix == ".pyc":
                continue
            relative = path.relative_to(root).as_posix().encode("utf-8")
            if path.is_symlink():
                marker = b"symlink:"
                content = os.readlink(path).encode("utf-8")
            else:
                marker = b"file:"
                content = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(marker)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    return digest.hexdigest()


def worktree_snapshot(root: Path, *, worker_mode: bool = False) -> dict[str, Any]:
    """Hash files and record directories, skipping Git metadata and Python caches."""
    root = root.resolve()
    files: dict[str, str] = {}
    directories: list[str] = []
    for current, names, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root).as_posix()
        if relative_dir == ".":
            relative_dir = ""

        retained: list[str] = []
        for name in sorted(names):
            relative = f"{relative_dir}/{name}".strip("/")
            if name == ".git" or name in IGNORE_DIRS:
                continue
            if worker_mode and relative == ".experiment-local":
                # The owner marker itself is separately verified. Descend so any
                # extra ignored evidence is still visible to the snapshot check.
                retained.append(name)
                continue
            retained.append(name)
            directories.append(relative)
        names[:] = retained

        for name in sorted(filenames):
            path = current_path / name
            relative = f"{relative_dir}/{name}".strip("/")
            if relative == ".git" or (worker_mode and relative == MARKER_RELATIVE_PATH):
                continue
            if path.is_symlink():
                files[relative] = "symlink:" + os.readlink(path)
            else:
                files[relative] = "sha256:" + sha256_file(path)
    return {"files": files, "directories": sorted(directories)}


def raw_index_sha256(index_path: Path) -> str:
    if not index_path.is_file():
        raise FixtureError(f"Git index is missing: {index_path}")
    return sha256_file(index_path)


def private_index_tree(root: Path, index_path: Path) -> str:
    """Compute the staged tree from a private index copy without locking the shared index."""
    temporary_root = Path(tempfile.gettempdir()).resolve()
    try:
        temporary_root.relative_to(root)
    except ValueError:
        pass
    else:
        raise FixtureError("system temporary directory is inside the Git worktree")

    try:
        with tempfile.TemporaryDirectory(prefix="ask-agent-index-tree-") as temporary_dir:
            private_index = Path(temporary_dir) / "index"
            shutil.copyfile(index_path, private_index)
            return git(
                root,
                "write-tree",
                environment={"GIT_INDEX_FILE": str(private_index.resolve())},
            )
    except OSError as exc:
        raise FixtureError(f"cannot compute index tree from a private index copy: {exc}") from exc


def status_entries(root: Path) -> dict[str, str]:
    output = run_process(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    entries: dict[str, str] = {}
    for line in output.splitlines():
        if len(line) < 4:
            raise FixtureError(f"unrecognized porcelain status line: {line!r}")
        entries[line[3:]] = line[:2]
    return entries


def diff_sha256(root: Path, *, cached: bool = False, path: str | None = None) -> str:
    args = ["diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv"]
    if cached:
        args.append("--cached")
    if path is not None:
        args.extend(["--", path])
    result = run_process(["git", "-C", str(root), *args], text=False)
    return sha256_bytes(result.stdout)


def capture_repo_state(root: Path, *, worker_mode: bool = False) -> dict[str, Any]:
    root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    common_dir = resolve_git_path(root, git(root, "rev-parse", "--git-common-dir"))
    index_path = resolve_git_path(root, git(root, "rev-parse", "--git-path", "index"))
    branch_result = run_process(
        ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    entries = git(root, "ls-files", "--stage", "--full-name").splitlines()
    head = git(root, "rev-parse", "HEAD")
    index_tree = private_index_tree(root, index_path)
    cached_diff = diff_sha256(root, cached=True)
    unstaged_diffs = {
        path: diff_sha256(root, path=path) for path in DIRTY_PATHS if path != "notes.txt"
    }
    status = status_entries(root)
    index_sha = raw_index_sha256(index_path)
    return {
        "root": str(root),
        "common_dir": str(common_dir),
        "index_path": str(index_path),
        "index_raw_sha256": index_sha,
        "branch": branch,
        "head": head,
        "index_entries": entries,
        "index_entries_sha256": sha256_bytes("\n".join(entries).encode("utf-8")),
        "index_tree": index_tree,
        "cached_diff_sha256": cached_diff,
        "unstaged_dirty_diffs": unstaged_diffs,
        "status": status,
        "working_tree": worktree_snapshot(root, worker_mode=worker_mode),
    }


def source_identity(source_skill: Path) -> dict[str, Any]:
    source_skill = source_skill.resolve()
    identity: dict[str, Any] = {
        "skill_path": str(source_skill),
        "repository": None,
        "revision": None,
        "skill_status": None,
    }
    try:
        repository = Path(git(source_skill, "rev-parse", "--show-toplevel")).resolve()
        revision = git(source_skill, "rev-parse", "HEAD")
        relative = source_skill.relative_to(repository).as_posix()
        status = git(repository, "status", "--porcelain=v1", "--", relative)
        identity.update(
            {
                "repository": str(repository),
                "revision": revision,
                "skill_status": status.splitlines(),
            }
        )
    except (FixtureError, ValueError):
        # Tests may supply a synthetic source tree without a Git repository.
        pass
    return identity


def formula(task_id: int, value: int) -> int:
    return (task_id + 1) * value + task_id * task_id


def generated_pipeline(worker_count: int) -> str:
    imports = "\n".join(
        f"from src.step_{task_id} import transform as transform_{task_id}"
        for task_id in range(1, worker_count + 1)
    )
    transforms = ", ".join(f"transform_{task_id}" for task_id in range(1, worker_count + 1))
    return f'''"""Apply every task transform in ascending task order."""

import json

{imports}

INPUTS = {PIPELINE_INPUTS!r}
TRANSFORMS = ({transforms},)


def transform_value(value):
    for transform in TRANSFORMS:
        value = transform(value)
    return value


def outputs():
    return [transform_value(value) for value in INPUTS]


if __name__ == "__main__":
    print(json.dumps(outputs()))
'''


def generated_checks(worker_count: int) -> str:
    return f'''"""Stdlib checks for the synthetic task fixture.

The baseline intentionally fails until workers replace their stubs.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

WORKER_COUNT = {worker_count}
INPUTS = {ORACLE_INPUTS!r}
PIPELINE_INPUTS = {PIPELINE_INPUTS!r}


def expected(task_id, value):
    return (task_id + 1) * value + task_id * task_id


def load_transform(task_id):
    path = Path(__file__).parent / "src" / f"step_{{task_id}}.py"
    spec = importlib.util.spec_from_file_location(f"fixture_step_{{task_id}}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transform


class FormulaCheck(unittest.TestCase):
    def __init__(self, task_id):
        super().__init__("runTest")
        self.task_id = task_id

    def runTest(self):
        transform = load_transform(self.task_id)
        for value in INPUTS:
            with self.subTest(task_id=self.task_id, value=value):
                result = transform(value)
                self.assertIs(type(result), int)
                self.assertEqual(result, expected(self.task_id, value))


class PipelineCheck(unittest.TestCase):
    def runTest(self):
        root = Path(__file__).parent
        result = subprocess.run(
            [sys.executable, str(root / "pipeline.py")],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        actual = json.loads(result.stdout)
        expected_values = []
        for original in PIPELINE_INPUTS:
            value = original
            for task_id in range(1, WORKER_COUNT + 1):
                value = expected(task_id, value)
            expected_values.append(value)
        self.assertEqual(actual, expected_values)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--worker", type=int)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.worker is not None and not 1 <= args.worker <= WORKER_COUNT:
        parser.error(f"--worker must be in 1..{{WORKER_COUNT}}")
    suite = unittest.TestSuite()
    worker_ids = range(1, WORKER_COUNT + 1) if args.all else [args.worker]
    for task_id in worker_ids:
        suite.addTest(FormulaCheck(task_id))
    if args.all:
        suite.addTest(PipelineCheck())
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
'''


def ignored_python_cache(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE_DIRS or name.endswith(".pyc")}


def create_fixture_source(root: Path, worker_count: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text(".experiment-local/\n__pycache__/\n", encoding="utf-8")
    (root / "dual.txt").write_text("head\n", encoding="utf-8")
    (root / "deleted.txt").write_text("initial file to delete\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    for task_id in range(1, worker_count + 1):
        (root / "src" / f"step_{task_id}.py").write_text(
            f'''def transform(x):
    raise NotImplementedError("task {task_id} must implement transform(x)")
''',
            encoding="utf-8",
        )
    (root / "pipeline.py").write_text(generated_pipeline(worker_count), encoding="utf-8")
    (root / "checks.py").write_text(generated_checks(worker_count), encoding="utf-8")


def fixture_paths(run_path: Path) -> dict[str, str]:
    return {
        "run": str(run_path),
        "primary": str(run_path / "primary"),
        "caller": str(run_path / "caller"),
        "package": str(run_path / "package" / "ask-agent"),
        "probes": str(run_path / "operator" / "probes"),
        "verification": str(run_path / "operator" / "verification.json"),
    }


def prepare_fixture(
    run_path: Path | str,
    workers: int,
    mode: str,
    hold_seconds: float = 0,
    *,
    source_skill: Path | str | None = None,
    seed_feedback_backlog: bool = False,
    seed_compact_ignore_controls: bool = False,
    delivery_mode: str = "patch",
) -> dict[str, Any]:
    if workers not in WORKER_COUNTS:
        raise FixtureError(f"workers must be one of {WORKER_COUNTS}")
    if mode not in {"parallel", "sequential"}:
        raise FixtureError("mode must be parallel or sequential")
    if delivery_mode not in DELIVERY_MODES:
        raise FixtureError(f"delivery-mode must be one of {DELIVERY_MODES}")
    if not math.isfinite(hold_seconds) or hold_seconds < 0:
        raise FixtureError("hold-seconds must be a finite nonnegative number")
    if type(seed_feedback_backlog) is not bool:
        raise FixtureError("seed-feedback-backlog must be a boolean")
    if type(seed_compact_ignore_controls) is not bool:
        raise FixtureError("seed-compact-ignore-controls must be a boolean")

    run_path = Path(run_path).expanduser().resolve()
    if run_path.exists() and any(run_path.iterdir()):
        raise FixtureError(f"run directory must be absent or empty: {run_path}")
    run_path.mkdir(parents=True, exist_ok=True)

    source_skill = Path(source_skill).expanduser().resolve() if source_skill else default_skill_root()
    if not source_skill.is_dir():
        raise FixtureError(f"ask-agent source skill directory is missing: {source_skill}")
    package_path = run_path / "package" / "ask-agent"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_skill, package_path, ignore=ignored_python_cache, symlinks=True)
    source_digest = package_tree_sha256(source_skill)
    package_digest = package_tree_sha256(package_path)
    if source_digest != package_digest:
        raise FixtureError("copied ask-agent package does not match source tree digest")

    primary = run_path / "primary"
    run_process(["git", "init", "-b", "main", str(primary)])
    git(primary, "config", "user.name", "Ask Agent Fixture")
    git(primary, "config", "user.email", "ask-agent-fixture@example.invalid")
    create_fixture_source(primary, workers)
    backlog_path = "tasks/in-progress/prompt-improvements-backlog.md"
    if seed_feedback_backlog:
        backlog = primary / backlog_path
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_bytes(
            b"# Prompt Improvement Backlog\n\n"
            b"Generated by feedback-collector plugin.\n\n"
        )
    initial_paths = [
        ".gitignore",
        "dual.txt",
        "deleted.txt",
        "pipeline.py",
        "checks.py",
        "src/__init__.py",
        *[f"src/step_{task_id}.py" for task_id in range(1, workers + 1)],
    ]
    if seed_feedback_backlog:
        initial_paths.append(backlog_path)
    git(primary, "add", *initial_paths)
    git(primary, "commit", "-m", "fixture baseline")
    primary_snapshot = capture_repo_state(primary)

    caller = run_path / "caller"
    git(primary, "worktree", "add", "-b", "experiment", str(caller), "main")
    run_id = uuid.uuid4().hex
    marker = f"run={run_id}\nbranch=experiment\n"
    (caller / "unique-ahead-marker.txt").write_text(marker, encoding="utf-8")
    git(caller, "add", "unique-ahead-marker.txt")
    git(caller, "commit", "-m", "unique caller marker")
    (caller / "dual.txt").write_text("staged\n", encoding="utf-8")
    git(caller, "add", "dual.txt")
    (caller / "dual.txt").write_text("unstaged\n", encoding="utf-8")
    (caller / "notes.txt").write_text("snapshot notes\n", encoding="utf-8")
    (caller / "added.txt").write_text("staged add\n", encoding="utf-8")
    git(caller, "add", "added.txt")
    (caller / "deleted.txt").unlink()
    if seed_compact_ignore_controls:
        gitignore = caller / ".gitignore"
        gitignore.write_text(
            gitignore.read_text(encoding="utf-8") + "/.claspignore\n/unrelated-ignored-input.txt\n",
            encoding="utf-8",
        )
        (caller / ".claspignore").write_text("dist/\n", encoding="utf-8")
        (caller / "unrelated-ignored-input.txt").write_text("omit from worker snapshot\n", encoding="utf-8")
    caller_snapshot = capture_repo_state(caller)
    expected_dirty_status = dict(EXPECTED_BASE_STATUS)
    if seed_compact_ignore_controls:
        expected_dirty_status[".gitignore"] = " M"
    if caller_snapshot["status"] != expected_dirty_status:
        raise FixtureError(
            f"fixture dirty layers were not created as expected: {caller_snapshot['status']!r}"
        )
    ahead = int(git(caller, "rev-list", "--count", "main..experiment"))
    if ahead != 1:
        raise FixtureError(f"caller branch should be exactly one commit ahead of main, got {ahead}")

    probes = run_path / "operator" / "probes"
    probes.mkdir(parents=True)
    assignments = []
    for task_id in range(1, workers + 1):
        assignments.append(
            {
                "worker_id": str(task_id),
                "task_index": task_id,
                "path": f"src/step_{task_id}.py",
                "assignment": (
                    f"Implement only src/step_{task_id}.py. Define transform(x) for every "
                    f"integer x as ({task_id}+1)*x+{task_id}*{task_id}. "
                    "Do not modify other files or dirty inputs."
                ),
                "marker_value": f"run={run_id};task={task_id}\n",
            }
        )

    source = source_identity(source_skill)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "mode": mode,
        "workers": workers,
        "seed_feedback_backlog": seed_feedback_backlog,
        "seed_compact_ignore_controls": seed_compact_ignore_controls,
        "worker_ids": [str(task_id) for task_id in range(1, workers + 1)],
        "hold_seconds": hold_seconds,
        "instrumentation_hold_excluded_from_timing_comparisons": True,
        "paths": fixture_paths(run_path),
        "source": {
            **source,
            "logical_card": "SKILL.md",
            "helper": "scripts/ask_agent_workspace.py",
            "package_tree_sha256": package_digest,
        },
        "caller_ahead_of_main_commits": ahead,
        "caller_marker": marker,
        "caller_snapshot": caller_snapshot,
        "primary_snapshot": primary_snapshot,
        "expected_dirty_status": expected_dirty_status,
        "dirty_inputs": [*DIRTY_PATHS[:-1], *([".gitignore"] if seed_compact_ignore_controls else [])],
        "compact_ignore_controls": {
            "ignored_root_control": ".claspignore" if seed_compact_ignore_controls else None,
            "ignored_unrelated_input": "unrelated-ignored-input.txt" if seed_compact_ignore_controls else None,
        },
        "task_assignments": assignments,
        "pipeline_inputs": PIPELINE_INPUTS,
        "oracle_inputs": ORACLE_INPUTS,
        "verification_notes": [
            "Worker ids and task indices are one-based.",
            "Each worker must use its own linked worktree and index.",
            "Child index bytes may differ because Git stores worktree-specific stat-cache data; entries, index tree, staged diff, and dirty input layers are compared.",
            "Raw index SHA differences are reported; entries, index tree, and staged diff determine semantic index preservation.",
            "The optional feedback backlog is seeded fixture content; it does not disable hooks or plugins.",
            "Probe hold intervals are instrumentation and excluded from model timing comparisons.",
            "Parallel runs with a positive hold require at least 0.1 seconds of overlap across every worker; sequential runs do not.",
            "Verification establishes fixture behavior and raw child events remain the controller's responsibility.",
        ],
    }
    # Keep historical patch manifests byte-compatible. A missing field means
    # patch for all previously prepared runs.
    if delivery_mode != "patch":
        manifest["delivery_mode"] = delivery_mode
    manifest_path = run_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(run_path: Path) -> dict[str, Any]:
    path = run_path / "manifest.json"
    if not path.is_file():
        raise FixtureError(f"manifest is missing: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"manifest is unreadable: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise FixtureError("unsupported manifest schema version")
    return manifest


def task_for(manifest: dict[str, Any], worker_id: str) -> dict[str, Any]:
    for task in manifest["task_assignments"]:
        if task["worker_id"] == worker_id:
            return task
    raise FixtureError(f"unknown worker id {worker_id!r}")


def marker_matches(marker_path: Path, expected: str) -> bool:
    try:
        return marker_path.is_file() and marker_path.read_text(encoding="utf-8") == expected
    except (OSError, UnicodeDecodeError):
        return False


def _compare_file_snapshot(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    allowed_file: str | None = None,
) -> tuple[bool, bool]:
    actual_files = actual["files"]
    expected_files = expected["files"]
    same_outside_allowed = True
    allowed_changed = False
    keys = set(actual_files) | set(expected_files)
    for key in keys:
        if key == allowed_file:
            if actual_files.get(key) != expected_files.get(key):
                allowed_changed = True
            elif key not in actual_files:
                same_outside_allowed = False
            continue
        if actual_files.get(key) != expected_files.get(key):
            same_outside_allowed = False
    if actual.get("directories") != expected.get("directories"):
        same_outside_allowed = False
    return same_outside_allowed, allowed_changed


def _setup_worker_branch(manifest: dict[str, Any], worker_id: str) -> str | None:
    """Read the prepared worker branch as the authoritative ephemeral identity."""
    setup_path = Path(manifest["paths"]["run"]) / "operator" / "setup-result.json"
    try:
        if setup_path.is_symlink() or not setup_path.is_file():
            return None
        setup = json.loads(setup_path.read_text(encoding="utf-8"))
        if (
            not isinstance(setup, dict)
            or setup.get("status") != "PREPARED"
            or setup.get("delivery_mode") != "ephemeral"
            or not isinstance(setup.get("workers"), list)
        ):
            return None
        matches = [
            worker for worker in setup["workers"]
            if isinstance(worker, dict) and worker.get("worker_id") == worker_id
        ]
        if len(matches) != 1:
            return None
        branch = matches[0].get("branch")
        return branch if isinstance(branch, str) and branch else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _start_probe_worker_branch(
    manifest: dict[str, Any], worker_id: str, root: str
) -> str | None:
    """Use a validated start probe only as a finish-phase fallback identity."""
    start_path = (
        Path(manifest["paths"]["probes"])
        / f"worker-{worker_id}-start.json"
    )
    try:
        if start_path.is_symlink() or not start_path.is_file():
            return None
        record = json.loads(start_path.read_text(encoding="utf-8"))
        branch = record.get("branch") if isinstance(record, dict) else None
        checks = record.get("checks") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("run_id") != manifest.get("run_id")
            or record.get("worker_id") != worker_id
            or record.get("phase") != "start"
            or record.get("root") != root
            or not isinstance(branch, str)
            or not branch
            or not isinstance(checks, dict)
            or not checks
            or any(value is not True for value in checks.values())
            or record.get("errors") != []
        ):
            return None
        return branch
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def state_checks(
    state: dict[str, Any],
    manifest: dict[str, Any],
    worker_id: str,
    phase: str,
    *,
    worker_baseline: dict[str, Any] | None = None,
    commit_base: str | None = None,
    snapshot: dict[str, Any] | None = None,
    binding_checks: dict[str, bool] | None = None,
    receipt_sha256: str | None = None,
    baseline_sha256: str | None = None,
    expected_worker_branch: str | None = None,
) -> tuple[dict[str, bool], dict[str, Any]]:
    if fixture_delivery_mode(manifest) == "commits":
        return _commit_state_checks(
            state,
            manifest,
            worker_id,
            phase,
            worker_baseline=worker_baseline,
            commit_base=commit_base,
            snapshot=snapshot,
            binding_checks=binding_checks,
            receipt_sha256=receipt_sha256,
            baseline_sha256=baseline_sha256,
        )

    baseline = manifest["caller_snapshot"]
    owner_path = task_for(manifest, worker_id)["path"]
    allow_owner = phase == "finish"
    expected_working_tree = _probe_baseline_working_tree(manifest)
    files_match, owner_changed = _compare_file_snapshot(
        state["working_tree"],
        expected_working_tree,
        allowed_file=owner_path if allow_owner else None,
    )

    source_files = state["working_tree"]["files"]
    expected_source_files = baseline["working_tree"]["files"]
    nonowner_source_unchanged = all(
        source_files.get(task["path"]) == expected_source_files.get(task["path"])
        for task in manifest["task_assignments"]
        if task["worker_id"] != worker_id
    )
    index_matches = (
        state["index_entries"] == baseline["index_entries"]
        and state["index_tree"] == baseline["index_tree"]
        and state["cached_diff_sha256"] == baseline["cached_diff_sha256"]
    )
    dirty_inputs = manifest.get("dirty_inputs", DIRTY_PATHS)
    dirty_diff_matches = all(
        state["unstaged_dirty_diffs"].get(path)
        == baseline["unstaged_dirty_diffs"].get(path)
        for path in dirty_inputs
        if path != "notes.txt"
    )
    expected_status = dict(manifest["expected_dirty_status"])
    if allow_owner and owner_changed:
        expected_status[owner_path] = " M"
    status_matches = state["status"] == expected_status
    expected_head = baseline["head"]
    checks = {
        "root_is_distinct_from_parent": state["root"]
        not in {manifest["paths"]["caller"], manifest["paths"]["primary"]},
        "common_dir_matches_fixture": state["common_dir"]
        == manifest["primary_snapshot"]["common_dir"],
        "head_matches_caller_snapshot": state["head"] == expected_head,
        "index_entries_tree_and_staged_layer_match": index_matches,
        "unstaged_dirty_input_diffs_match": dirty_diff_matches,
        "dirty_status_layers_match": status_matches,
        "working_tree_matches_except_owned_step": files_match,
        "nonowner_source_files_unchanged": nonowner_source_unchanged,
        "owner_changed_from_baseline": owner_changed if allow_owner else not owner_changed,
    }
    ephemeral_branch_expected = expected_worker_branch
    ephemeral_branch_source = "setup-argument" if expected_worker_branch is not None else None
    branch_baseline_available = True
    if fixture_delivery_mode(manifest) == "ephemeral":
        if ephemeral_branch_expected is None:
            ephemeral_branch_expected = _setup_worker_branch(manifest, worker_id)
            ephemeral_branch_source = "setup-result" if ephemeral_branch_expected else None
        if ephemeral_branch_expected is None and phase == "finish":
            ephemeral_branch_expected = _start_probe_worker_branch(
                manifest, worker_id, state.get("root", "")
            )
            ephemeral_branch_source = "validated-start-probe" if ephemeral_branch_expected else None
        branch_baseline_available = (
            isinstance(ephemeral_branch_expected, str) and bool(ephemeral_branch_expected)
        )
        checks["ephemeral_branch_unchanged"] = (
            branch_baseline_available
            and state.get("branch") == ephemeral_branch_expected
        )
        checks["ephemeral_no_commits"] = state["head"] == baseline["head"]
    if manifest.get("seed_compact_ignore_controls"):
        expected_root_control = baseline["working_tree"]["files"].get(".claspignore")
        checks["ignored_root_control_preserved"] = (
            isinstance(expected_root_control, str)
            and state["working_tree"]["files"].get(".claspignore") == expected_root_control
        )
        checks["unrelated_ignored_input_omitted"] = (
            "unrelated-ignored-input.txt" not in state["working_tree"]["files"]
        )
    details = {
        "expected_head": expected_head,
        "expected_status": expected_status,
        "actual_status": state["status"],
        "owner_path": owner_path,
        "owner_changed": owner_changed,
        "compact_ignore_controls": {
            "root_control_expected": expected_root_control if manifest.get("seed_compact_ignore_controls") else None,
            "root_control_actual": state["working_tree"]["files"].get(".claspignore"),
            "unrelated_ignored_input_present": "unrelated-ignored-input.txt" in state["working_tree"]["files"],
        },
    }
    if fixture_delivery_mode(manifest) == "ephemeral":
        details["ephemeral_branch"] = {
            "expected": ephemeral_branch_expected,
            "expected_source": ephemeral_branch_source,
            "actual": state.get("branch"),
            "baseline_available": branch_baseline_available,
        }
    return checks, details


def _commit_state_checks(
    state: dict[str, Any],
    manifest: dict[str, Any],
    worker_id: str,
    phase: str,
    *,
    worker_baseline: dict[str, Any] | None,
    commit_base: str | None,
    snapshot: dict[str, Any] | None,
    binding_checks: dict[str, bool] | None,
    receipt_sha256: str | None,
    baseline_sha256: str | None,
) -> tuple[dict[str, bool], dict[str, Any]]:
    caller_snapshot = manifest["caller_snapshot"]
    owner_path = task_for(manifest, worker_id)["path"]
    expected_tree = _probe_baseline_working_tree(manifest)
    files_match, owner_changed = _compare_file_snapshot(
        state["working_tree"],
        expected_tree,
        allowed_file=owner_path if phase == "finish" else None,
    )
    helper_binding_ok = bool(binding_checks) and all(
        value is True for value in binding_checks.values()
    )
    metadata_ok = (
        isinstance(worker_baseline, dict)
        and isinstance(snapshot, dict)
        and set(snapshot) == {"mode", "commit", "tree", "created", "source_dirty"}
        and snapshot.get("mode") == "private-commit"
        and type(snapshot.get("created")) is bool
        and snapshot.get("source_dirty") is True
        and isinstance(commit_base, str)
        and commit_base == snapshot.get("commit")
        and worker_baseline.get("head") == commit_base
        and worker_baseline.get("index_tree") == snapshot.get("tree")
        and worker_baseline.get("status") == {}
        and worker_baseline.get("working_tree") == expected_tree
    )

    try:
        caller_parent = git(state_root := Path(state["root"]), "show", "-s", "--format=%P", commit_base or "").split()
        snapshot_tree = git(state_root, "rev-parse", f"{commit_base}^{{tree}}")
        head_tree = git(state_root, "rev-parse", f"{state['head']}^{{tree}}")
        history = git(
            state_root,
            "rev-list",
            "--parents",
            "--topo-order",
            f"{commit_base}..{state['head']}",
        ).splitlines()
        changed_output = run_process(
            ["git", "-C", str(state_root), "diff", "--no-renames", "--name-only", "-z",
             commit_base or "", state["head"]],
            text=False,
        ).stdout
        changed_paths = [
            os.fsdecode(value) for value in changed_output.split(b"\0") if value
        ]
        if phase == "start":
            history_ok = state["head"] == commit_base and history == [] and changed_paths == []
        else:
            history_rows = [row.split() for row in history]
            history_ok = (
                len(history_rows) == 1
                and len(history_rows[0]) == 2
                and history_rows[0] == [state["head"], commit_base]
                and changed_paths == [owner_path]
            )
        commit_parent_ok = caller_parent == [caller_snapshot["head"]]
        commit_tree_ok = snapshot_tree == (snapshot or {}).get("tree")
        head_index_tree_ok = state["index_tree"] == head_tree
    except (FixtureError, OSError, KeyError, TypeError):
        caller_parent = []
        snapshot_tree = head_tree = None
        history = []
        changed_paths = []
        history_ok = commit_parent_ok = commit_tree_ok = head_index_tree_ok = False

    empty_diff = sha256_bytes(b"")
    baseline_entries = (
        _caller_index_entries_to_lines(worker_baseline.get("index_entries"))
        if isinstance(worker_baseline, dict) else None
    )
    baseline_index_digest_ok = (
        baseline_entries is not None
        and worker_baseline.get("index_entries_sha256")
        == sha256_bytes("\n".join(baseline_entries).encode("utf-8"))
    )
    baseline_index_at_start_ok = phase != "start" or (
        isinstance(worker_baseline, dict)
        and worker_baseline.get("index_entries") == state["index_entries"]
        and worker_baseline.get("index_entries_sha256") == state["index_entries_sha256"]
    )
    worker_baseline_ok = (
        isinstance(worker_baseline, dict)
        and worker_baseline.get("root") == state["root"]
        and worker_baseline.get("branch") == state["branch"]
        and worker_baseline.get("head") == commit_base
        and worker_baseline.get("common_dir") == state["common_dir"]
        and baseline_index_digest_ok
        and baseline_index_at_start_ok
        and worker_baseline.get("status") == {}
        and worker_baseline.get("index_tree") == (snapshot or {}).get("tree")
        and worker_baseline.get("cached_diff_sha256") == empty_diff
        and worker_baseline.get("working_tree") == expected_tree
    )
    clean_residual = (
        state["status"] == {}
        and state["cached_diff_sha256"] == empty_diff
        and head_index_tree_ok
        and diff_sha256(Path(state["root"])) == empty_diff
    )
    expected_files = expected_tree["files"]
    files = state["working_tree"]["files"]
    root_controls = (".gitignore", ".claspignore")
    controls_preserved = all(files.get(path) == expected_files.get(path) for path in root_controls)
    source_files = state["working_tree"]["files"]
    nonowner_source_unchanged = all(
        source_files.get(task["path"]) == expected_files.get(task["path"])
        for task in manifest["task_assignments"]
        if task["worker_id"] != worker_id
    )
    checks = {
        "root_is_distinct_from_parent": state["root"]
        not in {manifest["paths"]["caller"], manifest["paths"]["primary"]},
        "common_dir_matches_fixture": state["common_dir"]
        == manifest["primary_snapshot"]["common_dir"],
        "commit_baseline_binding": metadata_ok and helper_binding_ok,
        "commit_base_parent_matches_caller": commit_parent_ok,
        "private_commit_tree_matches_snapshot": commit_tree_ok,
        "worker_baseline_matches_caller_snapshot": worker_baseline_ok,
        "head_matches_commit_phase": (
            state["head"] == commit_base if phase == "start" else history_ok
        ),
        "index_is_clean_at_head": head_index_tree_ok and clean_residual,
        "worker_has_no_uncommitted_residuals": clean_residual,
        "working_tree_matches_except_owned_step": files_match,
        "nonowner_source_files_unchanged": nonowner_source_unchanged,
        "owner_changed_from_baseline": owner_changed if phase == "finish" else not owner_changed,
        "worker_history_is_linear_owner_only": history_ok,
        "root_controls_preserved": controls_preserved,
    }
    if manifest.get("seed_compact_ignore_controls"):
        checks["ignored_root_control_preserved"] = (
            isinstance(expected_files.get(".claspignore"), str)
            and files.get(".claspignore") == expected_files.get(".claspignore")
        )
        checks["unrelated_ignored_input_omitted"] = "unrelated-ignored-input.txt" not in files
    details = {
        "delivery_mode": "commits",
        "commit_base": commit_base,
        "snapshot": snapshot,
        "receipt_sha256": receipt_sha256,
        "baseline_sha256": baseline_sha256,
        "commit_delivery": {
            "commit_base": commit_base,
            "snapshot": snapshot,
            "receipt_sha256": receipt_sha256,
            "baseline_sha256": baseline_sha256,
        },
        "binding_checks": binding_checks or {},
        "worker_baseline_head": worker_baseline.get("head") if worker_baseline else None,
        "expected_status": {},
        "actual_status": state["status"],
        "expected_head": commit_base if phase == "start" else "one owner commit after commit_base",
        "actual_head": state["head"],
        "commit_parent": caller_parent,
        "snapshot_tree": snapshot_tree,
        "head_tree": head_tree,
        "history": history,
        "changed_paths_from_commit_base": changed_paths,
        "owner_path": owner_path,
        "owner_changed": owner_changed,
        "root_controls_preserved": controls_preserved,
    }
    return checks, details


def _probe_baseline_working_tree(manifest: dict[str, Any]) -> dict[str, Any]:
    expected = manifest["caller_snapshot"]["working_tree"]
    if manifest.get("seed_compact_ignore_controls"):
        expected = {**expected, "files": dict(expected["files"])}
        expected["files"].pop("unrelated-ignored-input.txt", None)
    return expected


def fixture_delivery_mode(manifest: dict[str, Any]) -> str:
    """Read the delivery mode while retaining support for legacy manifests."""
    value = manifest.get("delivery_mode", "patch")
    if value not in DELIVERY_MODES:
        raise FixtureError(f"unsupported delivery mode: {value!r}")
    return value


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def _helper_diff_sha256(root: Path, *, cached: bool = False) -> str:
    """Hash the helper's normalized patch bytes for source-capture binding."""
    args = [
        "git", "-C", str(root), "diff",
        "--binary", "--full-index", "--no-ext-diff", "--no-textconv", "--no-color",
        "--unified=3", "--inter-hunk-context=0", "--src-prefix=a/", "--dst-prefix=b/",
    ]
    if cached:
        args.append("--cached")
    return sha256_bytes(run_process(args, text=False).stdout)


def _helper_index_entries_to_lines(entries: Any) -> list[str] | None:
    if not isinstance(entries, list):
        return None
    lines: list[str] = []
    try:
        for item in sorted(entries, key=lambda row: row["path"]):
            path = item["path"]
            values = item["entries"]
            if not isinstance(path, str) or not isinstance(values, list):
                return None
            for value in values:
                lines.append(
                    f'{value["mode"]} {value["object"]} {value["stage"]}\t{path}'
                )
    except (KeyError, TypeError):
        return None
    return lines


def _caller_index_entries_to_lines(entries: Any) -> list[str] | None:
    """Validate the fixture snapshot's Git-formatted index records unchanged."""
    if not isinstance(entries, list):
        return None
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, str):
            return None
        header, separator, path = entry.partition("\t")
        fields = header.split(" ")
        if (
            not separator
            or not path
            or len(fields) != 3
            or not fields[0]
            or any(char not in "01234567" for char in fields[0])
            or len(fields[0]) != 6
            or len(fields[1]) not in {40, 64}
            or any(char not in "0123456789abcdef" for char in fields[1])
            or fields[2] not in {"0", "1", "2", "3"}
            or entry != f"{fields[0]} {fields[1]} {fields[2]}\t{path}"
        ):
            return None
        lines.append(entry)
    return lines


def _helper_files_to_snapshot(entries: Any) -> dict[str, str] | None:
    if not isinstance(entries, list):
        return None
    files: dict[str, str] = {}
    try:
        for entry in entries:
            path = entry["path"]
            kind = entry["type"]
            digest = entry["sha256"]
            if not isinstance(path, str) or not isinstance(digest, str) or path in files:
                return None
            if kind == "symlink":
                raw_target = base64.b64decode(entry["target_b64"], validate=True)
                if sha256_bytes(raw_target) != digest:
                    return None
                target = os.fsdecode(raw_target)
                files[path] = "symlink:" + target
            elif kind == "file":
                files[path] = "sha256:" + digest
            else:
                return None
    except (KeyError, TypeError, ValueError):
        return None
    return files


def _helper_source_capture_matches(
    source_capture: Any,
    caller_snapshot: dict[str, Any],
    expected_files: dict[str, Any],
    expected_unstaged_patch_sha256: str,
) -> bool:
    if not isinstance(source_capture, dict):
        return False
    expected_entries = _caller_index_entries_to_lines(caller_snapshot.get("index_entries"))
    actual_entries = _helper_index_entries_to_lines(source_capture.get("index_entries"))
    tracked = source_capture.get("tracked_files")
    untracked = source_capture.get("untracked")
    if not isinstance(tracked, list) or not isinstance(untracked, list):
        return False
    source_files = _helper_files_to_snapshot([*tracked, *untracked])
    if source_files is None:
        return False
    return (
        source_capture.get("head") == caller_snapshot.get("head")
        and source_capture.get("branch") == caller_snapshot.get("branch")
        and source_capture.get("common_dir") == caller_snapshot.get("common_dir")
        and source_capture.get("index_bytes_sha256") == caller_snapshot.get("index_raw_sha256")
        and actual_entries == expected_entries
        and source_capture.get("staged_patch_sha256") == caller_snapshot.get("cached_diff_sha256")
        and source_capture.get("unstaged_patch_sha256") == expected_unstaged_patch_sha256
        and source_files == expected_files
    )


def _helper_source_worker_state_matches_capture(
    helper_state: Any,
    source_capture: Any,
    expected_files: dict[str, Any],
    caller_head: str,
) -> bool:
    if not isinstance(helper_state, dict) or not isinstance(source_capture, dict):
        return False
    tracked = source_capture.get("tracked_files")
    untracked = source_capture.get("untracked")
    expected_entries = _helper_index_entries_to_lines(source_capture.get("index_entries"))
    actual_entries = _helper_index_entries_to_lines(helper_state.get("index_entries"))
    source_files = (
        _helper_files_to_snapshot([*tracked, *untracked])
        if isinstance(tracked, list) and isinstance(untracked, list) else None
    )
    helper_files = _helper_files_to_snapshot(helper_state.get("files"))
    return (
        source_files == expected_files
        and helper_files == expected_files
        and actual_entries == expected_entries
        and helper_state.get("head") == caller_head
        and helper_state.get("cached_patch_sha256") == source_capture.get("staged_patch_sha256")
        and helper_state.get("unstaged_patch_sha256") == source_capture.get("unstaged_patch_sha256")
    )


def _helper_worker_state_matches_capture(
    helper_state: Any,
    worker_baseline: Any,
    expected_tree: dict[str, Any],
) -> bool:
    if not isinstance(helper_state, dict) or not isinstance(worker_baseline, dict):
        return False
    helper_files = _helper_files_to_snapshot(helper_state.get("files"))
    helper_entries = _helper_index_entries_to_lines(helper_state.get("index_entries"))
    empty_diff = sha256_bytes(b"")
    return (
        helper_files == expected_tree.get("files")
        and helper_entries == worker_baseline.get("index_entries")
        and helper_state.get("head") == worker_baseline.get("head")
        and helper_state.get("branch") == worker_baseline.get("branch")
        and helper_state.get("cached_patch_sha256") == empty_diff
        and helper_state.get("unstaged_patch_sha256") == empty_diff
        and worker_baseline.get("working_tree") == expected_tree
    )


def _caller_matches_frozen_capture_after_integration(
    state: dict[str, Any], manifest: dict[str, Any]
) -> bool:
    """Allow exactly the assigned caller files after verified patch integration."""
    baseline = manifest["caller_snapshot"]
    allowed_paths = {task["path"] for task in manifest["task_assignments"]}
    actual_files = state["working_tree"]["files"]
    expected_files = baseline["working_tree"]["files"]
    changed_paths = {
        path for path in set(actual_files) | set(expected_files)
        if actual_files.get(path) != expected_files.get(path)
    }
    expected_status = dict(manifest["expected_dirty_status"])
    for path in allowed_paths:
        if actual_files.get(path) != expected_files.get(path):
            expected_status[path] = " M"
    return (
        changed_paths == allowed_paths
        and state["working_tree"]["directories"] == baseline["working_tree"]["directories"]
        and state["status"] == expected_status
        and all(
            state.get(key) == baseline.get(key)
            for key in (
                "root", "common_dir", "index_path", "branch", "head", "index_entries",
                "index_entries_sha256", "index_tree", "cached_diff_sha256",
            )
        )
        and all(
            state["unstaged_dirty_diffs"].get(path)
            == baseline["unstaged_dirty_diffs"].get(path)
            for path in DIRTY_PATHS if path != "notes.txt"
        )
    )


def _retained_preintegration_binding_matches(
    run_path: Path,
    worker_id: str,
    expected_delivery: dict[str, Any],
    expected_check_names: set[str],
) -> bool:
    for phase, details_key in (
        ("start", "initial_snapshot_details"),
        ("finish", "details"),
    ):
        path = run_path / "operator" / "probes" / f"worker-{worker_id}-{phase}.json"
        try:
            if path.is_symlink():
                return False
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        details = record.get(details_key) if isinstance(record, dict) else None
        binding_checks = details.get("binding_checks") if isinstance(details, dict) else None
        probe_checks = record.get("checks") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("worker_id") != worker_id
            or record.get("phase") != phase
            or record.get("status") != {}
            or record.get("errors") != []
            or not isinstance(probe_checks, dict)
            or not probe_checks
            or any(value is not True for value in probe_checks.values())
            or not isinstance(binding_checks, dict)
            or set(binding_checks) != expected_check_names
            or any(value is not True for value in binding_checks.values())
            or details.get("commit_delivery") != expected_delivery
        ):
            return False
    return True


def _load_commit_delivery_context(
    run_path: Path,
    manifest: dict[str, Any],
    worker_id: str,
    root: Path,
    *,
    after_integration: bool = False,
) -> dict[str, Any]:
    """Bind commit-mode probes to the frozen caller and helper receipt chain."""
    if fixture_delivery_mode(manifest) != "commits":
        return {}
    caller = Path(manifest["paths"]["caller"]).resolve()
    caller_snapshot = manifest["caller_snapshot"]
    expected_tree = _probe_baseline_working_tree(manifest)
    expected_files = expected_tree["files"]
    checks: dict[str, bool] = {}
    setup_path = run_path / "operator" / "setup-result.json"
    setup = json.loads(setup_path.read_text(encoding="utf-8"))
    if not isinstance(setup, dict):
        raise FixtureError("commit setup result is not an object")
    workers = setup.get("workers")
    selected = [
        item for item in workers if isinstance(item, dict) and item.get("worker_id") == worker_id
    ] if isinstance(workers, list) else []
    if len(selected) != 1:
        raise FixtureError(f"commit setup has no unique worker record for {worker_id}")
    worker = selected[0]
    worktree = Path(str(worker.get("worktree", ""))).resolve()
    receipt_path_value = Path(str(worker.get("receipt", "")))
    receipt_path = receipt_path_value.resolve()
    snapshot = worker.get("snapshot")
    commit_base = worker.get("commit_base")
    worker_baseline = worker.get("worker_baseline")
    checks["setup_worker_matches_root"] = (
        setup.get("status") == "PREPARED"
        and setup.get("source") == str(caller)
        and setup.get("source_head") == caller_snapshot["head"]
        and worktree == root.resolve()
        and worker.get("branch") == worker_baseline.get("branch")
        if isinstance(worker_baseline, dict) else False
    )
    checks["snapshot_shape_and_source_dirty"] = (
        isinstance(snapshot, dict)
        and set(snapshot) == {"mode", "commit", "tree", "created", "source_dirty"}
        and snapshot.get("mode") == "private-commit"
        and isinstance(snapshot.get("created"), bool)
        and snapshot.get("source_dirty") is True
        and isinstance(snapshot.get("commit"), str)
        and isinstance(snapshot.get("tree"), str)
    )
    checks["commit_base_matches_helper_snapshot"] = (
        isinstance(commit_base, str)
        and isinstance(snapshot, dict)
        and commit_base == snapshot.get("commit")
    )

    receipt: dict[str, Any] = {}
    baseline_data: dict[str, Any] = {}
    try:
        expected_store = (run_path / "workspace-store").resolve()
        if (
            receipt_path_value.is_symlink()
            or not receipt_path.is_file()
            or expected_store not in receipt_path.parents
        ):
            raise FixtureError("receipt path is missing or is a symlink")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise FixtureError("helper receipt is not an object")
        baseline_path_value = Path(str(receipt.get("baseline", "")))
        baseline_path = baseline_path_value.resolve()
        if (
            baseline_path_value.is_symlink()
            or not baseline_path.is_file()
            or expected_store not in baseline_path.parents
        ):
            raise FixtureError("helper baseline path is missing or is a symlink")
        baseline_bytes = baseline_path.read_bytes()
        baseline_data = json.loads(baseline_bytes.decode("utf-8"))
        if not isinstance(baseline_data, dict):
            raise FixtureError("helper baseline is not an object")
        baseline_hash = sha256_bytes(baseline_bytes)
        helper_baseline = baseline_data.get("worker_state")
        binding_path_value = Path(str(worker.get("compact_binding_path", "")))
        binding_path = binding_path_value.resolve()
        binding: dict[str, Any] = {}
        if (
            binding_path_value.is_symlink()
            or not binding_path.is_file()
            or binding_path.parent != (run_path / "operator" / "compact-bindings").resolve()
        ):
            raise FixtureError("commit binding path is missing, symlinked, or outside run evidence")
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        if not isinstance(binding, dict):
            raise FixtureError("commit binding is not an object")
        binding_without_digest = {key: value for key, value in binding.items() if key != "binding_sha256"}
        binding_digest = _canonical_json_sha256(binding_without_digest)
        binding_workspace = binding.get("workspace", {})
        binding_task = binding.get("task", {})
        checks["immutable_compact_binding_matches_setup"] = (
            binding.get("schema") == "ask-agent.task.binding.v1"
            and binding.get("status") == "READY_TO_LAUNCH"
            and binding.get("binding_sha256") == binding_digest
            and binding_digest == worker.get("compact_binding_sha256")
            and worker.get("compact_binding_path") == str(binding_path)
            and isinstance(binding_workspace, dict)
            and binding_workspace.get("route") == "worktree"
            and binding_workspace.get("source") == str(caller)
            and binding_workspace.get("root") == str(root.resolve())
            and binding_workspace.get("branch") == worker.get("branch")
            and binding_workspace.get("receipt") == str(receipt_path)
            and binding_workspace.get("baseline") == str(baseline_path)
            and binding_workspace.get("commit_base") == commit_base
            and binding_workspace.get("snapshot") == snapshot
            and isinstance(binding_task, dict)
            and binding_task.get("mode") == "edit"
            and binding_task.get("delivery_mode") == "commits"
            and binding_task.get("write_set") == [task_for(manifest, worker_id)["path"]]
        )
        prepared = worker.get("prepared_inspection")
        checks["receipt_and_baseline_hash_bound"] = (
            receipt.get("schema") == "ask-agent.workspace.receipt.v1"
            and receipt.get("status") == "prepared"
            and receipt.get("worktree") == str(root.resolve())
            and receipt.get("branch") == worker.get("branch")
            and Path(str(receipt.get("store", ""))).resolve() == expected_store
            and receipt.get("baseline_sha256") == baseline_hash
            and baseline_data.get("schema") == "ask-agent.workspace.baseline.v1"
            and baseline_data.get("attempt_id") == receipt.get("attempt_id")
            and prepared.get("baseline") == str(baseline_path)
            and prepared.get("receipt") == str(receipt_path)
            and prepared.get("fingerprint") == baseline_data.get("worker_state_fingerprint")
            and _canonical_json_sha256(helper_baseline)
            == baseline_data.get("worker_state_fingerprint")
        ) if isinstance(prepared, dict) else False
        receipt_source = receipt.get("source", {})
        baseline_source = baseline_data.get("source", {})
        checks["receipt_source_matches_frozen_caller"] = (
            isinstance(receipt_source, dict)
            and isinstance(baseline_source, dict)
            and Path(str(receipt_source.get("root", ""))).resolve() == caller
            and receipt_source.get("head") == caller_snapshot["head"]
            and Path(str(receipt_source.get("common_dir", ""))).resolve()
            == Path(caller_snapshot["common_dir"]).resolve()
            and Path(str(baseline_source.get("root", ""))).resolve() == caller
            and baseline_source.get("head") == caller_snapshot["head"]
            and baseline_source.get("branch") == caller_snapshot["branch"]
            and Path(str(baseline_source.get("common_dir", ""))).resolve()
            == Path(caller_snapshot["common_dir"]).resolve()
        )
        source_capture = baseline_data.get("source_capture")
        expected_source_diff = (
            source_capture.get("unstaged_patch_sha256")
            if after_integration and isinstance(source_capture, dict)
            else _helper_diff_sha256(caller)
        )
        checks["helper_source_capture_matches_frozen_caller"] = _helper_source_capture_matches(
            source_capture, caller_snapshot, expected_files, expected_source_diff
        )
        source_worker_state = baseline_data.get("source_worker_state")
        staged_artifact = baseline_data.get("source_staged_patch")
        unstaged_artifact = baseline_data.get("source_unstaged_patch")
        artifact_checks: dict[str, bool] = {}
        for name, artifact, capture_key in (
            ("staged", staged_artifact, "staged_patch_sha256"),
            ("unstaged", unstaged_artifact, "unstaged_patch_sha256"),
        ):
            artifact_ok = False
            if isinstance(artifact, dict) and isinstance(source_capture, dict):
                artifact_path_value = Path(str(artifact.get("path", "")))
                artifact_path = artifact_path_value.resolve()
                artifact_ok = (
                    not artifact_path_value.is_symlink()
                    and artifact_path.is_file()
                    and baseline_path.parent in artifact_path.parents
                    and sha256_file(artifact_path) == artifact.get("sha256")
                    and artifact.get("sha256") == source_capture.get(capture_key)
                )
            artifact_checks[name] = artifact_ok
        checks["source_patch_artifacts_match_capture"] = all(artifact_checks.values())
        checks["helper_pre_snapshot_state_bound"] = (
            baseline_data.get("snapshot") == snapshot
            and isinstance(source_worker_state, dict)
            and _canonical_json_sha256(source_worker_state)
            == baseline_data.get("source_worker_state_fingerprint")
            and _helper_source_worker_state_matches_capture(
                source_worker_state, source_capture, expected_files, caller_snapshot["head"]
            )
        )
        checks["helper_worker_baseline_matches_capture"] = (
            isinstance(worker_baseline, dict)
            and isinstance(helper_baseline, dict)
            and _helper_worker_state_matches_capture(
                helper_baseline, worker_baseline, expected_tree
            )
        )
        checks["snapshot_commit_parent_and_tree_match"] = False
        if isinstance(snapshot, dict) and isinstance(commit_base, str):
            normalized = git(root, "rev-parse", "--verify", f"{commit_base}^{{commit}}")
            parents = git(root, "show", "-s", "--format=%P", normalized).split()
            tree = git(root, "rev-parse", f"{normalized}^{{tree}}")
            checks["snapshot_commit_parent_and_tree_match"] = (
                normalized == commit_base
                and parents == [caller_snapshot["head"]]
                and tree == snapshot.get("tree")
                and snapshot.get("created") == (
                    tree != git(root, "rev-parse", f"{caller_snapshot['head']}^{{tree}}")
                )
                and isinstance(worker_baseline, dict)
                and worker_baseline.get("head") == commit_base
                and worker_baseline.get("index_tree") == tree
                and worker_baseline.get("status") == {}
                and worker_baseline.get("cached_diff_sha256") == sha256_bytes(b"")
                and worker_baseline.get("working_tree") == expected_tree
            )
        source_now = capture_repo_state(caller)
        if after_integration:
            checks["caller_still_matches_frozen_capture"] = (
                _caller_matches_frozen_capture_after_integration(source_now, manifest)
            )
            expected_delivery = {
                "commit_base": commit_base,
                "snapshot": snapshot,
                "receipt_sha256": sha256_file(receipt_path),
                "baseline_sha256": receipt["baseline_sha256"],
            }
            preintegration_check_names = set(checks)
            checks["preintegration_binding_evidence_matches_current_receipt"] = (
                _retained_preintegration_binding_matches(
                    run_path, worker_id, expected_delivery, preintegration_check_names
                )
            )
        else:
            checks["caller_still_matches_frozen_capture"] = all(
                source_now.get(key) == caller_snapshot.get(key)
                for key in (
                    "root", "common_dir", "index_path", "branch", "head", "index_entries",
                    "index_entries_sha256", "index_tree", "cached_diff_sha256",
                    "unstaged_dirty_diffs", "status", "working_tree",
                )
            )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, FixtureError, KeyError, TypeError, AttributeError) as exc:
        checks["immutable_compact_binding_matches_setup"] = False
        checks["receipt_and_baseline_hash_bound"] = False
        checks["receipt_source_matches_frozen_caller"] = False
        checks["helper_source_capture_matches_frozen_caller"] = False
        checks["helper_pre_snapshot_state_bound"] = False
        checks["source_patch_artifacts_match_capture"] = False
        checks["helper_worker_baseline_matches_capture"] = False
        checks["snapshot_commit_parent_and_tree_match"] = False
        checks["caller_still_matches_frozen_capture"] = False
        receipt["validation_error"] = f"{type(exc).__name__}: {exc}"
        baseline_hash = None

    if not all(checks.values()):
        raise FixtureError(f"commit setup binding failed for worker {worker_id}: {checks}")
    return {
        "worker_baseline": worker_baseline,
        "commit_base": commit_base,
        "snapshot": snapshot,
        "binding_checks": checks,
        "receipt_sha256": sha256_file(receipt_path),
        "baseline_sha256": receipt["baseline_sha256"],
        "receipt_path": str(receipt_path),
        "baseline_path": receipt["baseline"],
    }


def _commit_state_kwargs(context: dict[str, Any] | None) -> dict[str, Any]:
    if not context:
        return {}
    return {
        "worker_baseline": context.get("worker_baseline"),
        "commit_base": context.get("commit_base"),
        "snapshot": context.get("snapshot"),
        "binding_checks": context.get("binding_checks"),
        "receipt_sha256": context.get("receipt_sha256"),
        "baseline_sha256": context.get("baseline_sha256"),
    }


_ORACLE_PROGRAM = r'''
import contextlib
import importlib.util
import io
import json
import sys

path, task_text, values_text = sys.argv[1:4]
task_id = int(task_text)
values = json.loads(values_text)
cases = []
try:
    spec = importlib.util.spec_from_file_location("fixture_worker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load task module")
    module = importlib.util.module_from_spec(spec)
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
        spec.loader.exec_module(module)
        transform = module.transform
        for value in values:
            actual = transform(value)
            expected = (task_id + 1) * value + task_id * task_id
            display = actual
            if not isinstance(actual, (str, int, float, bool, type(None))):
                display = repr(actual)
            cases.append({
                "input": value,
                "expected": expected,
                "actual": display,
                "passed": type(actual) is int and actual == expected,
            })
    result = {"passed": bool(cases) and all(case["passed"] for case in cases), "cases": cases}
except BaseException as exc:
    result = {
        "passed": False,
        "error": type(exc).__name__ + ": " + str(exc),
        "cases": cases,
    }
print(json.dumps(result))
'''


def check_module_oracle(
    module_path: Path, task_id: int, *, timeout: float = 10
) -> dict[str, Any]:
    """Check task output in a bounded child process to isolate interpreter globals."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-I",
                "-c",
                _ORACLE_PROGRAM,
                str(module_path.resolve()),
                str(task_id),
                json.dumps(ORACLE_INPUTS),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "timed_out": True,
            "error": f"oracle process timed out after {timeout:g} seconds",
            "cases": [],
        }
    except OSError as exc:
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}", "cases": []}
    if result.returncode != 0:
        return {
            "passed": False,
            "error": f"oracle process exited {result.returncode}",
            "stderr": result.stderr[-4000:],
            "cases": [],
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "error": f"oracle process returned invalid JSON: {exc}",
            "stdout": result.stdout[-4000:],
            "cases": [],
        }
    if not isinstance(payload, dict) or type(payload.get("passed")) is not bool:
        return {"passed": False, "error": "oracle result has an invalid shape", "cases": []}
    return payload


def probe_run(
    run_path: Path | str,
    worker_id: str,
    phase: str,
    *,
    cwd: Path | str | None = None,
) -> dict[str, Any]:
    if phase not in {"start", "finish"}:
        raise FixtureError("phase must be start or finish")
    run_path = Path(run_path).expanduser().resolve()
    manifest = load_manifest(run_path)
    task = task_for(manifest, worker_id)
    current = Path(cwd or Path.cwd()).resolve()
    root = Path(git(current, "rev-parse", "--show-toplevel")).resolve()
    try:
        current.relative_to(root)
    except ValueError as exc:
        raise FixtureError(f"probe cwd is outside its Git root: {current}") from exc
    if str(root) in {manifest["paths"]["caller"], manifest["paths"]["primary"]}:
        raise FixtureError("probe must run from a distinct child worktree")
    common_dir = resolve_git_path(root, git(root, "rev-parse", "--git-common-dir"))
    if str(common_dir) != manifest["primary_snapshot"]["common_dir"]:
        raise FixtureError("probe Git common directory does not match the prepared fixture")
    commit_context = (
        _load_commit_delivery_context(run_path, manifest, worker_id, root)
        if fixture_delivery_mode(manifest) == "commits"
        else None
    )
    commit_kwargs = _commit_state_kwargs(commit_context)

    record_path = run_path / "operator" / "probes" / f"worker-{worker_id}-{phase}.json"
    marker_path = root / MARKER_RELATIVE_PATH
    if record_path.exists():
        raise FixtureError(f"{phase} probe already exists: {record_path}")
    if phase == "start" and marker_path.exists():
        raise FixtureError(f"worker marker already exists: {marker_path}")
    errors: list[str] = []
    checks: dict[str, bool] = {}
    hold_started = None
    hold_started_monotonic = None
    hold_finished = None
    hold_finished_monotonic = None
    hold_elapsed = None
    start_record: dict[str, Any] | None = None

    if phase == "start":
        initial_state = capture_repo_state(root, worker_mode=True)
        initial_checks, initial_details = state_checks(
            initial_state, manifest, worker_id, "start", **commit_kwargs
        )
        checks.update({f"before_hold.{key}": value for key, value in initial_checks.items()})
        if any(not value for value in initial_checks.values()):
            errors.append("child snapshot did not match the prepared caller state")
        if not errors:
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            write_exclusive_text(marker_path, task["marker_value"])
        hold_started = utc_now()
        hold_started_monotonic = time.monotonic()
        if not errors and manifest["hold_seconds"] > 0:
            time.sleep(manifest["hold_seconds"])
        marker_intact = marker_matches(marker_path, task["marker_value"])
        hold_finished = utc_now()
        hold_finished_monotonic = time.monotonic()
        hold_elapsed = round(hold_finished_monotonic - hold_started_monotonic, 6)
        final_state = capture_repo_state(root, worker_mode=True)
        final_checks, final_details = state_checks(
            final_state, manifest, worker_id, "start", **commit_kwargs
        )
        checks.update({f"after_hold.{key}": value for key, value in final_checks.items()})
        checks["marker_intact_after_hold"] = marker_intact
        if not marker_intact:
            errors.append("owner marker changed or disappeared during the hold interval")
        if any(not value for value in final_checks.values()):
            errors.append("child snapshot changed during the hold interval")
        state = final_state
        details = {"before_hold": initial_details, "after_hold": final_details}
        start_record = None
    else:
        start_path = run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        if not start_path.is_file():
            errors.append(f"start probe is missing: {start_path}")
        else:
            try:
                start_record = json.loads(start_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"start probe is unreadable: {exc}")
        marker_intact = marker_matches(marker_path, task["marker_value"])
        state = capture_repo_state(root, worker_mode=True)
        final_checks, details = state_checks(
            state, manifest, worker_id, "finish", **commit_kwargs
        )
        checks.update(final_checks)
        checks["marker_intact_at_finish"] = marker_intact
        if not marker_intact:
            errors.append("owner marker changed or disappeared before finish")
        if any(not value for value in final_checks.values()):
            errors.append("child finish snapshot did not match the allowed task changes")
        if start_record and start_record.get("root") != str(root):
            checks["same_root_as_start"] = False
            errors.append("finish probe root differs from start probe root")
        elif start_record:
            checks["same_root_as_start"] = True
        else:
            checks["same_root_as_start"] = False
        task_oracle = check_module_oracle(root / task["path"], int(worker_id))
        checks["task_result_oracle"] = task_oracle["passed"]
        if not task_oracle["passed"]:
            errors.append("owned task module failed its independent result oracle")
        hold_started = start_record.get("hold_started_at_utc") if start_record else None
        hold_finished = start_record.get("hold_finished_at_utc") if start_record else None
        hold_elapsed = start_record.get("hold_elapsed_seconds") if start_record else None
        hold_started_monotonic = (
            start_record.get("hold_started_monotonic_seconds") if start_record else None
        )
        hold_finished_monotonic = (
            start_record.get("hold_finished_monotonic_seconds") if start_record else None
        )

    record = {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "worker_id": worker_id,
        "phase": phase,
        "recorded_at_utc": utc_now(),
        "cwd": str(current),
        "root": str(root),
        "common_dir": state["common_dir"],
        "branch": state["branch"],
        "head": state["head"],
        "index_path": state["index_path"],
        "index_tree": state["index_tree"],
        "index_entries_sha256": state["index_entries_sha256"],
        "index_raw_sha256": state["index_raw_sha256"],
        "status": state["status"],
        "working_tree": state["working_tree"],
        "checks": checks,
        "details": details,
        "errors": errors,
        "marker_relative_path": MARKER_RELATIVE_PATH,
        "marker_value": task["marker_value"],
        "marker_intact": marker_intact,
        "hold_started_at_utc": hold_started,
        "hold_finished_at_utc": hold_finished,
        "hold_started_monotonic_seconds": hold_started_monotonic,
        "hold_finished_monotonic_seconds": hold_finished_monotonic,
        "hold_elapsed_seconds": hold_elapsed,
        "instrumentation_hold_excluded_from_timing_comparisons": True,
    }
    if phase == "start":
        record["hold_seconds_requested"] = manifest["hold_seconds"]
        record["initial_snapshot_checks"] = initial_checks
        record["initial_snapshot_details"] = initial_details
    else:
        record["task_oracle"] = task_oracle
        record["start_record_path"] = str(
            run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        )

    write_exclusive_json(record_path, record)
    return record


def expected_pipeline(worker_count: int) -> list[int]:
    result: list[int] = []
    for original in PIPELINE_INPUTS:
        value = original
        for task_id in range(1, worker_count + 1):
            value = formula(task_id, value)
        result.append(value)
    return result


def pipeline_oracle(root: Path, worker_count: int) -> dict[str, Any]:
    try:
        result = run_process(
            [sys.executable, str(root / "pipeline.py")],
            cwd=root,
            check=False,
            timeout=10,
        )
        if result.returncode:
            return {
                "passed": False,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        actual = json.loads(result.stdout)
        expected = expected_pipeline(worker_count)
        return {
            "passed": actual == expected,
            "actual": actual,
            "expected": expected,
            "stderr": result.stderr,
        }
    except (FixtureError, json.JSONDecodeError, TypeError) as exc:
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"}


def _read_probe(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, f"missing probe: {path}"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None, f"probe is not a JSON object: {path}"
        return record, None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"unreadable probe {path}: {exc}"


PROBE_BASE_FIELDS = {
    "schema_version", "run_id", "worker_id", "phase", "recorded_at_utc",
    "cwd", "root", "common_dir", "branch", "head", "index_path", "index_tree",
    "index_entries_sha256", "index_raw_sha256", "status", "working_tree", "checks",
    "details", "errors", "marker_relative_path", "marker_value", "marker_intact",
    "hold_started_at_utc", "hold_finished_at_utc", "hold_started_monotonic_seconds",
    "hold_finished_monotonic_seconds", "hold_elapsed_seconds",
    "instrumentation_hold_excluded_from_timing_comparisons",
}


def state_check_keys(manifest: dict[str, Any] | None = None) -> set[str]:
    delivery_mode = fixture_delivery_mode(manifest) if manifest else "patch"
    if delivery_mode == "commits":
        keys = set(COMMIT_STATE_CHECK_KEYS)
    elif delivery_mode == "ephemeral":
        keys = set(EPHEMERAL_STATE_CHECK_KEYS)
    else:
        keys = set(STATE_CHECK_KEYS)
    if manifest and manifest.get("seed_compact_ignore_controls"):
        keys.update({"ignored_root_control_preserved", "unrelated_ignored_input_omitted"})
    return keys


def required_probe_checks(phase: str, manifest: dict[str, Any] | None = None) -> set[str]:
    state_keys = state_check_keys(manifest)
    if phase == "start":
        return (
            {f"before_hold.{key}" for key in state_keys}
            | {f"after_hold.{key}" for key in state_keys}
            | {"marker_intact_after_hold"}
        )
    return state_keys | {
        "marker_intact_at_finish", "same_root_as_start", "task_result_oracle"
    }


def valid_iso_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(value)


def validate_probe_record(
    record: dict[str, Any],
    manifest: dict[str, Any],
    task: dict[str, Any],
    phase: str,
    run_path: Path,
    *,
    delivery_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    extras = (
        {"hold_seconds_requested", "initial_snapshot_checks", "initial_snapshot_details"}
        if phase == "start"
        else {"task_oracle", "start_record_path"}
    )
    expected_fields = PROBE_BASE_FIELDS | extras
    actual_fields = set(record)
    if actual_fields != expected_fields:
        errors.append(
            f"field set differs: missing={sorted(expected_fields - actual_fields)}, "
            f"extra={sorted(actual_fields - expected_fields)}"
        )
    for key, expected in (
        ("schema_version", 1),
        ("run_id", manifest["run_id"]),
        ("worker_id", task["worker_id"]),
        ("phase", phase),
        ("marker_relative_path", MARKER_RELATIVE_PATH),
        ("marker_value", task["marker_value"]),
        ("instrumentation_hold_excluded_from_timing_comparisons", True),
    ):
        if record.get(key) != expected:
            errors.append(f"{key} does not match the prepared {phase} probe")

    root = record.get("root")
    cwd = record.get("cwd")
    if not isinstance(root, str) or not Path(root).is_absolute():
        errors.append("root must be an absolute path")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        errors.append("cwd must be an absolute path")
    if isinstance(root, str) and isinstance(cwd, str):
        try:
            Path(cwd).resolve().relative_to(Path(root).resolve())
        except (OSError, ValueError):
            errors.append("cwd must resolve inside root")
    for key in ("common_dir", "index_path"):
        value = record.get(key)
        if not isinstance(value, str) or not Path(value).is_absolute():
            errors.append(f"{key} must be an absolute path")
    for key in ("head", "index_tree", "index_entries_sha256", "index_raw_sha256"):
        if not isinstance(record.get(key), str) or not record[key]:
            errors.append(f"{key} must be a nonempty string")
    if "branch" not in record or (record["branch"] is not None and not isinstance(record["branch"], str)):
        errors.append("branch must be a string or null")
    if not isinstance(record.get("status"), dict):
        errors.append("status must be an object")
    tree = record.get("working_tree")
    if not isinstance(tree, dict) or set(tree) != {"files", "directories"}:
        errors.append("working_tree must contain files and directories")
    elif not isinstance(tree.get("files"), dict) or not isinstance(tree.get("directories"), list):
        errors.append("working_tree files/directories have invalid types")
    if not isinstance(record.get("details"), dict):
        errors.append("details must be an object")
    if not isinstance(record.get("errors"), list) or any(
        not isinstance(value, str) for value in record.get("errors", [])
    ):
        errors.append("errors must be a list of strings")
    if record.get("errors"):
        errors.append("probe recorded errors")
    if record.get("marker_intact") is not True:
        errors.append("marker_intact must be true")
    if not valid_iso_timestamp(record.get("recorded_at_utc")):
        errors.append("recorded_at_utc is invalid")
    for key in ("hold_started_at_utc", "hold_finished_at_utc"):
        if not valid_iso_timestamp(record.get(key)):
            errors.append(f"{key} is invalid")
    for key in (
        "hold_started_monotonic_seconds", "hold_finished_monotonic_seconds", "hold_elapsed_seconds"
    ):
        if not finite_number(record.get(key)) or record[key] < 0:
            errors.append(f"{key} must be a finite nonnegative number")

    probe_checks = record.get("checks")
    required_checks = required_probe_checks(phase, manifest)
    if not isinstance(probe_checks, dict) or set(probe_checks) != required_checks:
        errors.append("checks do not match the required phase schema")
    elif any(type(value) is not bool for value in probe_checks.values()):
        errors.append("all checks must be booleans")
    elif not all(value is True for value in probe_checks.values()):
        errors.append("one or more required checks failed")

    if phase == "start":
        requested_hold = record.get("hold_seconds_requested")
        if not finite_number(requested_hold) or requested_hold != manifest["hold_seconds"]:
            errors.append("hold_seconds_requested differs from manifest")
        baseline = manifest["caller_snapshot"]
        if fixture_delivery_mode(manifest) == "commits":
            worker_baseline = delivery_context.get("worker_baseline") if delivery_context else None
            delivery_snapshot = (
                delivery_context.get("snapshot")
                if isinstance(delivery_context, dict) else None
            )
            start_snapshot_matches = (
                isinstance(worker_baseline, dict)
                and record.get("root") == worker_baseline.get("root")
                and record.get("working_tree") == _probe_baseline_working_tree(manifest)
                and record.get("status") == {}
                and record.get("head") == delivery_context.get("commit_base")
                and record.get("branch") == worker_baseline.get("branch")
                and isinstance(delivery_snapshot, dict)
                and record.get("index_tree") == delivery_snapshot.get("tree")
                and record.get("index_entries_sha256") == worker_baseline.get("index_entries_sha256")
                and record.get("common_dir") == manifest["primary_snapshot"]["common_dir"]
            )
            details = record.get("initial_snapshot_details", {})
            commit_details = details.get("commit_delivery") if isinstance(details, dict) else None
            expected_commit_details = {
                "commit_base": delivery_context.get("commit_base") if delivery_context else None,
                "snapshot": delivery_context.get("snapshot") if delivery_context else None,
                "receipt_sha256": delivery_context.get("receipt_sha256") if delivery_context else None,
                "baseline_sha256": delivery_context.get("baseline_sha256") if delivery_context else None,
            }
            if not delivery_context or commit_details != expected_commit_details:
                errors.append("start probe is not bound to the validated helper commit baseline")
        else:
            start_snapshot_matches = (
                record.get("working_tree") == _probe_baseline_working_tree(manifest)
                and record.get("status") == manifest["expected_dirty_status"]
                and record.get("head") == baseline["head"]
                and record.get("index_tree") == baseline["index_tree"]
                and record.get("index_entries_sha256") == baseline["index_entries_sha256"]
                and record.get("common_dir") == manifest["primary_snapshot"]["common_dir"]
            )
        if not start_snapshot_matches:
            errors.append("start snapshot does not match the prepared delivery baseline")
        snapshot_checks = record.get("initial_snapshot_checks")
        if not isinstance(snapshot_checks, dict) or set(snapshot_checks) != state_check_keys(manifest):
            errors.append("initial_snapshot_checks do not match the required schema")
        elif any(type(value) is not bool for value in snapshot_checks.values()):
            errors.append("initial_snapshot_checks values must be booleans")
        elif not all(value is True for value in snapshot_checks.values()):
            errors.append("initial snapshot checks failed")
        if not isinstance(record.get("initial_snapshot_details"), dict):
            errors.append("initial_snapshot_details must be an object")
        try:
            wall_seconds = (
                datetime.fromisoformat(record["hold_finished_at_utc"])
                - datetime.fromisoformat(record["hold_started_at_utc"])
            ).total_seconds()
            monotonic_seconds = (
                record["hold_finished_monotonic_seconds"]
                - record["hold_started_monotonic_seconds"]
            )
            if wall_seconds < 0 or monotonic_seconds < 0:
                errors.append("hold interval has negative duration")
            if abs(monotonic_seconds - record["hold_elapsed_seconds"]) > 0.05:
                errors.append("hold_elapsed_seconds differs from monotonic endpoints")
        except (KeyError, TypeError, ValueError):
            errors.append("hold interval endpoints are invalid")
    else:
        expected_start_path = str(run_path / "operator" / "probes" / f"worker-{task['worker_id']}-start.json")
        if record.get("start_record_path") != expected_start_path:
            errors.append("start_record_path does not point to this worker's start probe")
        if fixture_delivery_mode(manifest) == "commits":
            details = record.get("details", {})
            commit_details = details.get("commit_delivery") if isinstance(details, dict) else None
            expected_commit_details = {
                "commit_base": delivery_context.get("commit_base") if delivery_context else None,
                "snapshot": delivery_context.get("snapshot") if delivery_context else None,
                "receipt_sha256": delivery_context.get("receipt_sha256") if delivery_context else None,
                "baseline_sha256": delivery_context.get("baseline_sha256") if delivery_context else None,
            }
            if not delivery_context or commit_details != expected_commit_details:
                errors.append("finish probe is not bound to the validated helper commit baseline")
        task_oracle = record.get("task_oracle")
        if (
            not isinstance(task_oracle, dict)
            or task_oracle.get("passed") is not True
            or not isinstance(task_oracle.get("cases"), list)
            or len(task_oracle["cases"]) != len(ORACLE_INPUTS)
        ):
            errors.append("task_oracle is missing or incomplete")
        elif any(
            not isinstance(case, dict)
            or case.get("input") != expected_input
            or case.get("passed") is not True
            or case.get("expected") != formula(int(task["worker_id"]), expected_input)
            or type(case.get("actual")) is not int
            or case.get("actual") != case.get("expected")
            for case, expected_input in zip(task_oracle["cases"], ORACLE_INPUTS)
        ):
            errors.append("task_oracle cases do not match the required inputs")

    return {"passed": not errors, "errors": errors}


def validate_probe_pair(
    start: dict[str, Any],
    finish: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields = (
        "root", "common_dir", "branch", "head", "index_path", "index_tree",
        "index_entries_sha256", "marker_relative_path", "marker_value",
        "hold_started_at_utc", "hold_finished_at_utc", "hold_started_monotonic_seconds",
        "hold_finished_monotonic_seconds", "hold_elapsed_seconds",
    )
    if manifest and fixture_delivery_mode(manifest) == "commits":
        fields = tuple(
            key for key in fields
            if key not in {"head", "index_tree", "index_entries_sha256"}
        )
    differing = [key for key in fields if start.get(key) != finish.get(key)]
    return {"passed": not differing, "differing_fields": differing}


def _contains_delivery_artifact_fields(value: Any) -> bool:
    forbidden = {
        "action", "actions", "applied", "applied_worker_ids", "commit", "commits",
        "commit_base", "contribution_patch", "diff", "diffs", "patch", "patches",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in forbidden or normalized.startswith("commit_"):
                return True
            if _contains_delivery_artifact_fields(item):
                return True
    elif isinstance(value, list):
        return any(_contains_delivery_artifact_fields(item) for item in value)
    return False


def _validate_ephemeral_finalization(
    run_path: Path,
    manifest: dict[str, Any],
    finish_records: dict[str, dict[str, Any]],
    owner_hashes: dict[str, str],
) -> dict[str, Any]:
    """Validate findings-only finalization without importing caller task modules."""
    path = run_path / "operator" / "integration-result.json"
    errors: list[str] = []
    expected_ids = [task["worker_id"] for task in manifest["task_assignments"]]
    required_fields = {
        "schema", "run_id", "status", "delivery_mode", "worker_ids",
        "parent_asserted_collected_worker_ids", "caller_snapshot", "caller_snapshot_sha256",
        "workers", "retry_semantics", "caller_unchanged", "finished_epoch",
    }
    try:
        if path.is_symlink() or not path.is_file():
            raise FixtureError("ephemeral integration result is missing or is a symlink")
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise FixtureError("ephemeral integration result is not an object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, FixtureError) as exc:
        return {"passed": False, "errors": [f"{type(exc).__name__}: {exc}"], "path": str(path)}

    if not required_fields.issubset(result):
        errors.append(f"ephemeral result is missing fields: {sorted(required_fields - set(result))}")
    if _contains_delivery_artifact_fields(result):
        errors.append("ephemeral result contains patch, commit, diff, applied, or action fields")
    if (
        result.get("schema") != "ask-agent.integration-result/v2"
        or result.get("run_id") != manifest.get("run_id")
        or result.get("status") != "NO_INTEGRATION"
        or result.get("delivery_mode") != "ephemeral"
        or result.get("worker_ids") != expected_ids
        or result.get("parent_asserted_collected_worker_ids") != expected_ids
        or result.get("caller_snapshot") != manifest.get("caller_snapshot")
        or result.get("caller_snapshot_sha256")
        != _canonical_json_sha256(manifest.get("caller_snapshot"))
        or result.get("caller_unchanged") is not True
        or not isinstance(result.get("retry_semantics"), str)
        or not result.get("retry_semantics")
        or not finite_number(result.get("finished_epoch"))
    ):
        errors.append("ephemeral result does not match the frozen NO_INTEGRATION contract")

    setup_path = run_path / "operator" / "setup-result.json"
    setup_by_id: dict[str, dict[str, Any]] = {}
    try:
        if setup_path.is_symlink() or not setup_path.is_file():
            raise FixtureError("ephemeral setup result is missing or is a symlink")
        setup = json.loads(setup_path.read_text(encoding="utf-8"))
        setup_workers = setup.get("workers") if isinstance(setup, dict) else None
        if (
            not isinstance(setup, dict)
            or setup.get("status") != "PREPARED"
            or setup.get("treatment") != "compact"
            or setup.get("delivery_mode") != "ephemeral"
            or not isinstance(setup_workers, list)
        ):
            raise FixtureError("ephemeral setup result is not bound to compact preparation")
        setup_by_id = {
            row["worker_id"]: row for row in setup_workers
            if isinstance(row, dict) and isinstance(row.get("worker_id"), str)
        }
        if set(setup_by_id) != set(expected_ids) or len(setup_by_id) != len(setup_workers):
            raise FixtureError("ephemeral setup workers do not match manifest IDs")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, FixtureError) as exc:
        errors.append(f"ephemeral setup evidence is invalid: {type(exc).__name__}: {exc}")

    workers = result.get("workers")
    if not isinstance(workers, list) or len(workers) != len(expected_ids):
        errors.append("ephemeral result worker list is incomplete")
        workers = []
    for expected_id, worker in zip(expected_ids, workers):
        task = task_for(manifest, expected_id)
        finish = finish_records.get(expected_id)
        if not isinstance(worker, dict) or finish is None:
            errors.append(f"worker {expected_id} finalization evidence is missing")
            continue
        expected_return_path = run_path / "operator" / "compact-returns" / f"worker-{expected_id}.json"
        expected_phase_path = (
            run_path / "operator" / "worker-phases" / f"worker-{expected_id}-finish" / "attempt.json"
        )
        setup_worker = setup_by_id.get(expected_id, {})
        expected_worker_fields = {
            "worker_id", "verify_return_path", "worker_phase_path", "collection_ref",
            "findings", "findings_sha256",
        }
        if set(worker) != expected_worker_fields:
            errors.append(f"worker {expected_id} finalization fields differ from schema")
        if (
            worker.get("worker_id") != expected_id
            or worker.get("verify_return_path") != str(expected_return_path.resolve())
            or worker.get("worker_phase_path") != str(expected_phase_path.resolve())
            or worker.get("collection_ref") != {
                "worker_id": expected_id,
                "kind": "parent-collected-worker-assertion",
            }
        ):
            errors.append(f"worker {expected_id} paths or collection reference are invalid")

        try:
            if expected_return_path.is_symlink() or not expected_return_path.is_file():
                raise FixtureError("compact verify-return evidence is missing or is a symlink")
            returned = json.loads(expected_return_path.read_text(encoding="utf-8"))
            if expected_phase_path.is_symlink() or not expected_phase_path.is_file():
                raise FixtureError("worker phase evidence is missing or is a symlink")
            phase = json.loads(expected_phase_path.read_text(encoding="utf-8"))
            if not isinstance(returned, dict) or not isinstance(phase, dict):
                raise FixtureError("worker evidence is not an object")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, FixtureError) as exc:
            errors.append(f"worker {expected_id} evidence cannot be read: {type(exc).__name__}: {exc}")
            continue

        returned_result = returned.get("result")
        workspace_evidence = (
            returned_result.get("workspace_evidence")
            if isinstance(returned_result, dict) else None
        )
        phase_checks = phase.get("checks") if isinstance(phase.get("checks"), dict) else {}
        returned_audit = (
            workspace_evidence.get("ephemeral_audit")
            if isinstance(workspace_evidence, dict) else None
        )
        phase_audit = phase.get("ephemeral_audit")
        shared_audit_keys = {
            "status", "findings_only", "changed_paths", "baseline_fingerprint",
            "fingerprint", "head", "branch", "scratch_retained",
        }
        phase_shared_audit = (
            {key: phase_audit.get(key) for key in shared_audit_keys}
            if isinstance(phase_audit, dict) else None
        )
        returned_shared_audit = (
            {key: returned_audit.get(key) for key in shared_audit_keys}
            if isinstance(returned_audit, dict) else None
        )
        if (
            returned.get("status") != "PASSED"
            or returned.get("exit_code") != 0
            or returned.get("worker_id") != expected_id
            or returned.get("delivery_mode") != "ephemeral"
            or returned.get("binding_sha256") != setup_worker.get("compact_binding_sha256")
            or returned.get("evidence_path") != str(expected_return_path.resolve())
            or not isinstance(returned_result, dict)
            or returned_result.get("status") != "READY_FOR_PARENT_ACCEPTANCE"
            or returned_result.get("command") != "verify-return"
            or returned_result.get("binding_sha256") != setup_worker.get("compact_binding_sha256")
            or not isinstance(workspace_evidence, dict)
            or workspace_evidence != {"ephemeral_audit": returned_audit}
            or phase.get("status") != "PASSED"
            or phase.get("worker_id") != expected_id
            or phase.get("root") != finish.get("root")
            or phase.get("root") != setup_worker.get("worktree")
            or phase_checks.get("production_worker_finish_passed") is not True
            or phase_checks.get("ephemeral_findings_only") is not True
            or phase_shared_audit != returned_shared_audit
            or not isinstance(phase_audit, dict)
            or phase_audit.get("actual_cwd") != setup_worker.get("worktree")
        ):
            errors.append(f"worker {expected_id} lacks matching production findings-only evidence")
        if _contains_delivery_artifact_fields(returned_result):
            errors.append(f"worker {expected_id} verify-return contains delivery artifacts")

        audit = worker.get("findings", {}).get("ephemeral_audit") if isinstance(worker.get("findings"), dict) else None
        changed_paths = audit.get("changed_paths") if isinstance(audit, dict) else None
        expected_changed_paths = sorted([task["path"], MARKER_RELATIVE_PATH])
        if (
            not isinstance(audit, dict)
            or audit != returned_audit
            or audit.get("status") != "ephemeral-audit"
            or audit.get("findings_only") is not True
            or changed_paths != expected_changed_paths
            or not isinstance(audit.get("baseline_fingerprint"), str)
            or len(audit.get("baseline_fingerprint", "")) != 64
            or any(char not in "0123456789abcdef" for char in audit.get("baseline_fingerprint", ""))
            or not isinstance(audit.get("fingerprint"), str)
            or len(audit.get("fingerprint", "")) != 64
            or any(char not in "0123456789abcdef" for char in audit.get("fingerprint", ""))
            or audit.get("head") != finish.get("head")
            or audit.get("branch") != finish.get("branch")
            or audit.get("scratch_retained") is not True
        ):
            errors.append(f"worker {expected_id} ephemeral audit is invalid or not bound to finish state")

        findings = worker.get("findings")
        expected_finding_fields = {
            "worker_id", "path", "formula", "module_sha256", "oracle", "ephemeral_audit",
        }
        expected_module_hash = owner_hashes.get(expected_id, "").removeprefix("sha256:")
        if (
            not isinstance(findings, dict)
            or set(findings) != expected_finding_fields
            or findings.get("worker_id") != expected_id
            or findings.get("path") != task["path"]
            or findings.get("formula")
            != f"({int(expected_id)}+1)*x+{int(expected_id)}*{int(expected_id)}"
            or findings.get("module_sha256") != expected_module_hash
            or findings.get("oracle") != finish.get("task_oracle")
            or findings.get("ephemeral_audit") != returned_audit
            or worker.get("findings_sha256") != _canonical_json_sha256(findings)
        ):
            errors.append(f"worker {expected_id} findings do not bind its retained scratch output")

    return {
        "passed": not errors,
        "errors": errors,
        "path": str(path),
        "worker_ids": expected_ids,
        "caller_snapshot_sha256": result.get("caller_snapshot_sha256"),
    }


def verify_fixture(run_path: Path | str) -> dict[str, Any]:
    run_path = Path(run_path).expanduser().resolve()
    manifest = load_manifest(run_path)
    delivery_mode = fixture_delivery_mode(manifest)
    errors: list[str] = []
    checks: dict[str, bool] = {}

    package_path = Path(manifest["paths"]["package"])
    package_digest = package_tree_sha256(package_path) if package_path.is_dir() else None
    checks["frozen_package_hash_unchanged"] = (
        package_digest == manifest["source"]["package_tree_sha256"]
    )
    if not checks["frozen_package_hash_unchanged"]:
        errors.append("frozen ask-agent package digest changed or package is missing")

    primary_path = Path(manifest["paths"]["primary"])
    caller_path = Path(manifest["paths"]["caller"])
    primary_index_raw_observation: dict[str, Any] | None = None
    try:
        primary_now = capture_repo_state(primary_path)
        primary_expected = manifest["primary_snapshot"]
        primary_fields = (
            "root", "common_dir", "index_path", "branch", "head", "index_entries",
            "index_tree", "cached_diff_sha256", "status", "working_tree",
        )
        primary_semantic_index_unchanged = all(
            primary_now.get(field) == primary_expected.get(field)
            for field in ("index_entries", "index_tree", "cached_diff_sha256")
        )
        primary_index_raw_observation = {
            "unchanged": primary_now["index_raw_sha256"] == primary_expected["index_raw_sha256"],
            "semantic_index_unchanged": primary_semantic_index_unchanged,
            "expected_sha256": primary_expected["index_raw_sha256"],
            "actual_sha256": primary_now["index_raw_sha256"],
            "metadata_only_difference": (
                primary_now["index_raw_sha256"] != primary_expected["index_raw_sha256"]
                and primary_semantic_index_unchanged
            ),
        }
        checks["primary_pristine_fingerprint_preserved"] = all(
            primary_now.get(field) == primary_expected.get(field) for field in primary_fields
        ) and primary_semantic_index_unchanged
    except Exception as exc:
        primary_now = None
        checks["primary_pristine_fingerprint_preserved"] = False
        errors.append(f"cannot recapture primary fingerprint: {type(exc).__name__}: {exc}")
    if not checks["primary_pristine_fingerprint_preserved"]:
        errors.append("primary working tree, HEAD, index, or fingerprint changed")

    worker_results: list[dict[str, Any]] = []
    start_records: dict[str, dict[str, Any]] = {}
    finish_records: dict[str, dict[str, Any]] = {}
    probe_complete = True
    roots: list[str] = []
    index_paths: list[str] = []
    common_dirs: list[str] = []
    markers: list[tuple[str, str]] = []
    hold_checks: list[bool] = []
    hold_intervals: dict[str, dict[str, float]] = {}
    snapshot_checks: list[bool] = []
    per_worker_oracles: list[bool] = []
    finish_owner_hashes: dict[str, str] = {}
    delivery_contexts: dict[str, dict[str, Any]] = {}

    for task in manifest["task_assignments"]:
        worker_id = task["worker_id"]
        start_path = run_path / "operator" / "probes" / f"worker-{worker_id}-start.json"
        finish_path = run_path / "operator" / "probes" / f"worker-{worker_id}-finish.json"
        start, start_error = _read_probe(start_path)
        finish, finish_error = _read_probe(finish_path)
        if start_error or finish_error:
            probe_complete = False
            errors.extend(error for error in (start_error, finish_error) if error)
        result: dict[str, Any] = {"worker_id": worker_id}
        if start is None or finish is None:
            result["passed"] = False
            result["errors"] = [error for error in (start_error, finish_error) if error]
            worker_results.append(result)
            continue

        start_records[worker_id] = start
        finish_records[worker_id] = finish
        delivery_context: dict[str, Any] | None = None
        if delivery_mode == "commits":
            try:
                finish_root = finish.get("root")
                if not isinstance(finish_root, str) or not Path(finish_root).is_absolute():
                    raise FixtureError("finish probe has no absolute worker root")
                delivery_context = _load_commit_delivery_context(
                    run_path, manifest, worker_id, Path(finish_root), after_integration=True
                )
                delivery_contexts[worker_id] = delivery_context
            except Exception as exc:
                errors.append(
                    f"worker {worker_id} commit baseline binding failed: "
                    f"{type(exc).__name__}: {exc}"
                )
        start_schema = validate_probe_record(
            start, manifest, task, "start", run_path, delivery_context=delivery_context
        )
        finish_schema = validate_probe_record(
            finish, manifest, task, "finish", run_path, delivery_context=delivery_context
        )
        pair_schema = validate_probe_pair(start, finish, manifest)
        if not start_schema["passed"] or not finish_schema["passed"] or not pair_schema["passed"]:
            probe_complete = False
            errors.extend(
                f"worker {worker_id} start schema: {value}"
                for value in start_schema["errors"]
            )
            errors.extend(
                f"worker {worker_id} finish schema: {value}"
                for value in finish_schema["errors"]
            )
            if not pair_schema["passed"]:
                errors.append(
                    f"worker {worker_id} start/finish fields differ: "
                    f"{pair_schema['differing_fields']}"
                )
        root = finish.get("root")
        index_path = finish.get("index_path")
        common_dir = finish.get("common_dir")
        roots.append(root if isinstance(root, str) else "")
        index_paths.append(index_path if isinstance(index_path, str) else "")
        common_dirs.append(common_dir if isinstance(common_dir, str) else "")
        markers.append((finish.get("marker_relative_path", ""), finish.get("marker_value", "")))

        start_checks = start.get("checks") if isinstance(start.get("checks"), dict) else {}
        finish_checks = finish.get("checks") if isinstance(finish.get("checks"), dict) else {}
        record_checks = {
            **{f"start.{key}": value for key, value in start_checks.items()},
            **{f"finish.{key}": value for key, value in finish_checks.items()},
        }
        start_errors = start.get("errors") if isinstance(start.get("errors"), list) else ["invalid errors field"]
        finish_errors = finish.get("errors") if isinstance(finish.get("errors"), list) else ["invalid errors field"]
        record_ok = (
            start_schema["passed"]
            and finish_schema["passed"]
            and pair_schema["passed"]
            and not start_errors
            and not finish_errors
            and bool(record_checks)
            and all(value is True for value in record_checks.values())
        )
        result["record_checks"] = record_checks
        result["record_schema"] = {
            "start": start_schema,
            "finish": finish_schema,
            "pair": pair_schema,
        }
        result["record_errors"] = start_errors + finish_errors
        result["recorded_snapshots_pass"] = record_ok

        valid_root = isinstance(root, str) and bool(root)
        try:
            if not valid_root:
                raise FixtureError("finish probe has no child root")
            actual_root = Path(git(Path(root), "rev-parse", "--show-toplevel")).resolve()
            actual_common = resolve_git_path(actual_root, git(actual_root, "rev-parse", "--git-common-dir"))
            actual_index = resolve_git_path(actual_root, git(actual_root, "rev-parse", "--git-path", "index"))
            root_matches = str(actual_root) == root
            common_matches = str(actual_common) == common_dir == manifest["primary_snapshot"]["common_dir"]
            index_matches = str(actual_index) == index_path
            recaptured = capture_repo_state(actual_root, worker_mode=True)
            recaptured_checks, recaptured_details = state_checks(
                recaptured,
                manifest,
                worker_id,
                "finish",
                **_commit_state_kwargs(delivery_context),
            )
            recaptured_ok = all(recaptured_checks.values())
            finish_tree = finish.get("working_tree")
            finish_snapshot_matches = (
                isinstance(finish_tree, dict)
                and recaptured["branch"] == finish.get("branch")
                and recaptured["head"] == finish.get("head")
                and recaptured["index_tree"] == finish.get("index_tree")
                and recaptured["index_entries_sha256"] == finish.get("index_entries_sha256")
                and recaptured["status"] == finish.get("status")
                and recaptured["working_tree"] == finish_tree
            )
            marker_path = actual_root / MARKER_RELATIVE_PATH
            marker_ok = marker_matches(marker_path, task["marker_value"])
            owner_hash = recaptured["working_tree"]["files"].get(task["path"])
            finish_owner_hashes[worker_id] = owner_hash or ""
            owner_hash_matches_record = (
                owner_hash == finish.get("working_tree", {}).get("files", {}).get(task["path"])
            )
            module_oracle = check_module_oracle(actual_root / task["path"], int(worker_id))
        except Exception as exc:
            root_matches = common_matches = index_matches = recaptured_ok = False
            finish_snapshot_matches = False
            marker_ok = owner_hash_matches_record = False
            recaptured_checks = {}
            recaptured_details = {}
            module_oracle = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
            errors.append(f"worker {worker_id} root recheck failed: {type(exc).__name__}: {exc}")

        root_integration_checks = {
            "root_matches_actual_git_root": root_matches,
            "common_dir_is_shared_fixture_common_dir": common_matches,
            "index_path_matches_actual_git_index": index_matches,
            "current_snapshot_still_matches_finish": recaptured_ok,
            "finish_snapshot_matches_record": finish_snapshot_matches,
            "marker_intact": marker_ok,
            "owner_hash_matches_finish_record": owner_hash_matches_record,
        }
        result["root_rechecks"] = root_integration_checks
        result["recaptured_snapshot_checks"] = recaptured_checks
        result["recaptured_snapshot_details"] = recaptured_details
        result["task_oracle"] = module_oracle
        finish_task_oracle = finish.get("task_oracle")
        finish_oracle_ok = (
            isinstance(finish_task_oracle, dict)
            and finish_task_oracle.get("passed") is True
        )
        snapshot_checks.append(
            record_ok and recaptured_ok and root_matches and common_matches and index_matches
            and finish_snapshot_matches and marker_ok and owner_hash_matches_record
        )
        per_worker_oracles.append(
            bool(module_oracle.get("passed")) and finish_oracle_ok
        )

        marker_content_ok = finish.get("marker_value") == task["marker_value"]
        if finish.get("marker_relative_path") == MARKER_RELATIVE_PATH and marker_content_ok and marker_ok:
            result["collision_marker"] = True
        else:
            result["collision_marker"] = False

        hold_ok = False
        if start.get("phase") == "start" and manifest["hold_seconds"] == 0:
            hold_ok = True
        elif start.get("phase") == "start":
            try:
                started = datetime.fromisoformat(start["hold_started_at_utc"])
                ended = datetime.fromisoformat(start["hold_finished_at_utc"])
                wall_seconds = (ended - started).total_seconds()
                recorded_seconds = float(start["hold_elapsed_seconds"])
                monotonic_started = float(start["hold_started_monotonic_seconds"])
                monotonic_ended = float(start["hold_finished_monotonic_seconds"])
                monotonic_seconds = monotonic_ended - monotonic_started
                hold_intervals[worker_id] = {
                    "start": monotonic_started,
                    "end": monotonic_ended,
                }
                hold_ok = (
                    wall_seconds >= manifest["hold_seconds"] - 0.05
                    and recorded_seconds >= manifest["hold_seconds"] - 0.05
                    and monotonic_seconds >= manifest["hold_seconds"] - 0.05
                    and abs(monotonic_seconds - recorded_seconds) <= 0.05
                    and start.get("instrumentation_hold_excluded_from_timing_comparisons") is True
                )
                result["hold_interval"] = {
                    "started_at_utc": start["hold_started_at_utc"],
                    "finished_at_utc": start["hold_finished_at_utc"],
                    "wall_seconds": wall_seconds,
                    "monotonic_seconds": recorded_seconds,
                    "monotonic_interval_seconds": monotonic_seconds,
                    "requested_seconds": manifest["hold_seconds"],
                }
            except (KeyError, TypeError, ValueError):
                hold_ok = False
        hold_checks.append(hold_ok)
        result["hold_interval_passed"] = hold_ok
        result["passed"] = (
            record_ok
            and all(root_integration_checks.values())
            and bool(module_oracle.get("passed"))
            and finish_oracle_ok
            and result["collision_marker"]
            and hold_ok
        )
        worker_results.append(result)

    checks["worker_probe_completeness"] = probe_complete and len(start_records) == manifest["workers"] and len(finish_records) == manifest["workers"]
    checks["worker_roots_distinct_from_parent_and_each_other"] = (
        len(roots) == manifest["workers"]
        and len(set(roots)) == manifest["workers"]
        and all(root not in {str(primary_path.resolve()), str(caller_path.resolve())} for root in roots)
    )
    base_index_paths = {
        manifest["primary_snapshot"]["index_path"],
        manifest["caller_snapshot"]["index_path"],
    }
    checks["worker_index_paths_unique"] = (
        len(index_paths) == manifest["workers"]
        and len(set(index_paths)) == manifest["workers"]
        and not (set(index_paths) & base_index_paths)
    )
    checks["worker_common_dirs_match_fixture"] = (
        len(common_dirs) == manifest["workers"]
        and all(path == manifest["primary_snapshot"]["common_dir"] for path in common_dirs)
    )
    checks["worker_snapshots_clean_and_exact_dirty_layers"] = (
        len(snapshot_checks) == manifest["workers"] and all(snapshot_checks)
    )
    checks["collision_markers_use_same_path_and_unique_values"] = (
        len(markers) == manifest["workers"]
        and all(path == MARKER_RELATIVE_PATH for path, _ in markers)
        and len({value for _, value in markers}) == manifest["workers"]
        and all(result.get("collision_marker") for result in worker_results)
    )
    checks["per_task_result_oracles_pass"] = (
        len(per_worker_oracles) == manifest["workers"] and all(per_worker_oracles)
    )
    checks["hold_intervals_valid"] = len(hold_checks) == manifest["workers"] and all(hold_checks)

    overlap_required = manifest["mode"] == "parallel" and manifest["hold_seconds"] > 0
    overlap_seconds: float | None = None
    if len(hold_intervals) == manifest["workers"]:
        overlap_seconds = min(item["end"] for item in hold_intervals.values()) - max(
            item["start"] for item in hold_intervals.values()
        )
    overlap_passed = (
        overlap_seconds is not None
        and overlap_seconds >= MIN_PARALLEL_HOLD_OVERLAP_SECONDS
        if overlap_required
        else True
    )
    parallel_overlap = {
        "required": overlap_required,
        "required_overlap_seconds": MIN_PARALLEL_HOLD_OVERLAP_SECONDS,
        "overlap_seconds": overlap_seconds,
        "passed": overlap_passed,
        "intervals": hold_intervals,
    }
    checks["parallel_hold_intervals_overlap"] = overlap_passed
    if overlap_required and not overlap_passed:
        errors.append("parallel worker hold intervals did not overlap by at least 0.1 seconds")

    caller_checks: dict[str, Any] = {}
    caller_index_raw_observation: dict[str, Any] | None = None
    try:
        caller_now = capture_repo_state(caller_path)
        baseline = manifest["caller_snapshot"]
        allowed_paths = (
            set() if delivery_mode == "ephemeral"
            else {task["path"] for task in manifest["task_assignments"]}
        )
        actual_files = caller_now["working_tree"]["files"]
        expected_files = baseline["working_tree"]["files"]
        directories_unchanged = (
            caller_now["working_tree"]["directories"]
            == baseline["working_tree"]["directories"]
        )
        actual_changes = sorted(
            key for key in set(actual_files) | set(expected_files)
            if actual_files.get(key) != expected_files.get(key)
        )
        exact_changes = set(actual_changes) == allowed_paths
        all_module_files_present = all(path in actual_files for path in allowed_paths)
        expected_status = dict(manifest["expected_dirty_status"])
        for path in allowed_paths:
            if actual_files.get(path) != expected_files.get(path):
                expected_status[path] = " M"
        status_exact = caller_now["status"] == expected_status
        index_unchanged = (
            caller_now["index_entries"] == baseline["index_entries"]
            and caller_now["index_tree"] == baseline["index_tree"]
            and caller_now["cached_diff_sha256"] == baseline["cached_diff_sha256"]
        )
        caller_index_raw_observation = {
            "unchanged": caller_now["index_raw_sha256"] == baseline["index_raw_sha256"],
            "semantic_index_unchanged": index_unchanged,
            "expected_sha256": baseline["index_raw_sha256"],
            "actual_sha256": caller_now["index_raw_sha256"],
            "metadata_only_difference": (
                caller_now["index_raw_sha256"] != baseline["index_raw_sha256"]
                and index_unchanged
            ),
        }
        caller_identity_unchanged = (
            caller_now["root"] == baseline["root"]
            and caller_now["branch"] == baseline["branch"]
            and caller_now["head"] == baseline["head"]
        )
        dirty_inputs_unchanged = all(
            actual_files.get(path) == expected_files.get(path) for path in DIRTY_PATHS
        ) and all(
            caller_now["unstaged_dirty_diffs"].get(path)
            == baseline["unstaged_dirty_diffs"].get(path)
            for path in DIRTY_PATHS
            if path != "notes.txt"
        )
        caller_checks = {
            "only_allowed_step_files_changed": exact_changes and all_module_files_present,
            "caller_directories_unchanged": directories_unchanged,
            "caller_index_and_staged_layer_unchanged": index_unchanged,
            "caller_head_branch_and_root_unchanged": caller_identity_unchanged,
            "dirty_input_content_and_unstaged_layers_unchanged": dirty_inputs_unchanged,
            "caller_status_has_only_expected_changes": status_exact,
        }
        if delivery_mode == "ephemeral":
            caller_checks["caller_full_snapshot_unchanged"] = all(
                caller_now.get(key) == value for key, value in baseline.items()
            )
        checks["exact_allowed_caller_source_changes"] = all(caller_checks.values())
        if not checks["exact_allowed_caller_source_changes"]:
            errors.append(f"caller state changed outside the permitted task edits: {caller_checks}")
    except Exception as exc:
        caller_now = None
        checks["exact_allowed_caller_source_changes"] = False
        errors.append(f"cannot verify caller state: {type(exc).__name__}: {exc}")
    if not checks["exact_allowed_caller_source_changes"]:
        checks["caller_dirty_head_index_and_content_preserved"] = False
    else:
        checks["caller_dirty_head_index_and_content_preserved"] = True

    integration_matches = True
    integration_details: dict[str, Any] = {}
    if caller_now is not None:
        caller_files = caller_now["working_tree"]["files"]
        for task in manifest["task_assignments"]:
            worker_id = task["worker_id"]
            child_hash = finish_owner_hashes.get(worker_id)
            caller_hash = caller_files.get(task["path"])
            matches = bool(child_hash) and child_hash == caller_hash
            integration_details[worker_id] = {
                "path": task["path"],
                "worker_sha256": child_hash,
                "caller_sha256": caller_hash,
                "matches": matches,
            }
            integration_matches = integration_matches and matches
    else:
        integration_matches = False
    if delivery_mode != "ephemeral":
        checks["integrated_modules_match_worker_outputs"] = integration_matches
    checks["caller_dirty_head_index_and_content_preserved"] = bool(
        checks.get("caller_dirty_head_index_and_content_preserved")
        and checks["exact_allowed_caller_source_changes"]
    )
    ephemeral_finalization: dict[str, Any] | None = None
    if delivery_mode == "ephemeral":
        checks["ephemeral_parent_unchanged"] = bool(
            caller_now is not None
            and all(
                caller_now.get(key) == value
                for key, value in manifest["caller_snapshot"].items()
            )
        )
        if not checks["ephemeral_parent_unchanged"]:
            errors.append("ephemeral delivery changed the caller snapshot")
        loaded_task_modules = [
            f"src.step_{task['worker_id']}"
            for task in manifest["task_assignments"]
            if f"src.step_{task['worker_id']}" in sys.modules
        ]
        checks["ephemeral_no_caller_task_imports"] = not loaded_task_modules
        if loaded_task_modules:
            errors.append(f"ephemeral verification imported caller task modules: {loaded_task_modules}")
        ephemeral_finalization = _validate_ephemeral_finalization(
            run_path, manifest, finish_records, finish_owner_hashes
        )
        checks["ephemeral_finalization_valid"] = ephemeral_finalization["passed"]
        if not ephemeral_finalization["passed"]:
            errors.extend(ephemeral_finalization["errors"])
        integrated_oracles: dict[str, Any] = {}
        integration_details = {}
        pipeline_result = {
            "not_run": True,
            "reason": "ephemeral delivery records findings and does not integrate task modules",
        }
    else:
        if not integration_matches:
            errors.append("caller task modules do not match the worker finish snapshots")

        integrated_oracles = {
            task["worker_id"]: check_module_oracle(
                caller_path / task["path"], int(task["worker_id"])
            )
            for task in manifest["task_assignments"]
        }
        checks["integrated_per_task_result_oracles_pass"] = all(
            result.get("passed") for result in integrated_oracles.values()
        )
        if not checks["integrated_per_task_result_oracles_pass"]:
            errors.append("one or more integrated task modules failed the independent oracle")

        pipeline_result = pipeline_oracle(caller_path, manifest["workers"])
        checks["combined_pipeline_oracle_passes"] = bool(pipeline_result.get("passed"))
        if not checks["combined_pipeline_oracle_passes"]:
            errors.append("combined pipeline output failed the independent mathematical oracle")

    if delivery_mode == "commits":
        exclusions: dict[str, bool] = {}
        caller_head = caller_now.get("head") if isinstance(caller_now, dict) else None
        for task in manifest["task_assignments"]:
            worker_id = task["worker_id"]
            context = delivery_contexts.get(worker_id)
            commit_base = context.get("commit_base") if isinstance(context, dict) else None
            not_ancestor = False
            if isinstance(commit_base, str) and isinstance(caller_head, str):
                try:
                    ancestry = run_process(
                        ["git", "-C", str(caller_path), "merge-base", "--is-ancestor", commit_base, caller_head],
                        check=False,
                    )
                    not_ancestor = ancestry.returncode == 1
                except FixtureError:
                    not_ancestor = False
            exclusions[worker_id] = (
                bool(context)
                and all(context.get("binding_checks", {}).values())
                and isinstance(commit_base, str)
                and commit_base != caller_head
                and not_ancestor
            )
        checks["private_commit_baselines_excluded"] = (
            caller_now is not None
            and len(exclusions) == manifest["workers"]
            and all(exclusions.values())
        )
        if not checks["private_commit_baselines_excluded"]:
            errors.append(f"private worker snapshots were not excluded from caller history: {exclusions}")

    report = {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "delivery_mode": delivery_mode,
        "run_path": str(run_path),
        "verified_at_utc": utc_now(),
        "passed": all(checks.values()),
        "checks": checks,
        "errors": errors,
        "source": {
            "revision": manifest["source"].get("revision"),
            "source_package_tree_sha256": manifest["source"]["package_tree_sha256"],
            "verified_package_tree_sha256": package_digest,
        },
        "caller_checks": caller_checks,
        "caller_index_raw_observation": caller_index_raw_observation,
        "worker_results": worker_results,
        "parallel_overlap": parallel_overlap,
        "integrated_task_oracles": integrated_oracles,
        "integration_hashes": integration_details,
        "combined_pipeline": pipeline_result,
        "delivery_evidence": ephemeral_finalization if ephemeral_finalization is not None else {
            worker_id: {
                "commit_base": context.get("commit_base"),
                "snapshot": context.get("snapshot"),
                "receipt_sha256": context.get("receipt_sha256"),
                "baseline_sha256": context.get("baseline_sha256"),
                "binding_checks": context.get("binding_checks"),
            }
            for worker_id, context in delivery_contexts.items()
        } if delivery_mode == "commits" else {},
        "primary_fingerprint": {
            "expected": manifest["primary_snapshot"],
            "actual": primary_now,
            "index_raw_observation": primary_index_raw_observation,
        },
        "timing_note": "Probe hold intervals are instrumentation and excluded from timing comparisons.",
        "evidence_scope_note": (
            "This verifier checks fixture invariants and independent code results. "
            "A separate controller must validate raw native lifecycle events."
        ),
    }
    verification_path = Path(manifest["paths"]["verification"])
    verification_path.parent.mkdir(parents=True, exist_ok=True)
    verification_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def summarize_verification(report: dict[str, Any], report_path: Path | str) -> dict[str, Any]:
    """Return a compact summary cryptographically bound to the saved full report."""
    report_path = Path(report_path).expanduser().resolve()
    try:
        payload = report_path.read_bytes()
    except OSError as exc:
        raise FixtureError(f"cannot read saved verification report {report_path}: {exc}") from exc

    run_id = report.get("run_id")
    passed = report.get("passed")
    checks = report.get("checks")
    errors = report.get("errors")
    if (
        not isinstance(run_id, str)
        or not isinstance(passed, bool)
        or not isinstance(checks, dict)
        or not isinstance(errors, list)
        or not all(isinstance(error, str) for error in errors)
        or not all(isinstance(name, str) for name in checks)
    ):
        raise FixtureError("cannot summarize a malformed verification report")

    return {
        "schema": VERIFICATION_SUMMARY_SCHEMA,
        "run_id": run_id,
        "passed": passed,
        "errors": errors,
        "check_count": len(checks),
        "failed_checks": sorted(name for name, value in checks.items() if value is not True),
        "report_path": str(report_path),
        "report_bytes": len(payload),
        "report_sha256": sha256_bytes(payload),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--run", required=True, type=Path)
    prepare_parser.add_argument("--workers", required=True, type=int, choices=WORKER_COUNTS)
    prepare_parser.add_argument("--mode", required=True, choices=("parallel", "sequential"))
    prepare_parser.add_argument("--hold-seconds", type=float, default=0)
    prepare_parser.add_argument(
        "--delivery-mode", choices=DELIVERY_MODES, default="patch",
        help="worker contribution handling; omitted manifests remain legacy patch mode",
    )
    prepare_parser.add_argument(
        "--seed-feedback-backlog",
        action="store_true",
        help="seed the tracked feedback backlog file in the primary baseline",
    )
    prepare_parser.add_argument(
        "--seed-compact-ignore-controls",
        action="store_true",
        help="seed a dirty .gitignore, ignored root .claspignore, and unrelated ignored input",
    )
    prepare_parser.add_argument(
        "--skill-root",
        type=Path,
        help="source skills/ask-agent directory; defaults to the current fixture repository",
    )

    probe_parser = subparsers.add_parser("probe")
    probe_parser.add_argument("--run", required=True, type=Path)
    probe_parser.add_argument("--worker", required=True)
    probe_parser.add_argument("--phase", required=True, choices=("start", "finish"))

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--run", required=True, type=Path)
    verify_parser.add_argument("--summary", action="store_true", help="print a compact summary bound to the full saved report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_fixture(
                args.run,
                args.workers,
                args.mode,
                args.hold_seconds,
                source_skill=args.skill_root,
                seed_feedback_backlog=args.seed_feedback_backlog,
                seed_compact_ignore_controls=args.seed_compact_ignore_controls,
                delivery_mode=args.delivery_mode,
            )
        elif args.command == "probe":
            result = probe_run(args.run, args.worker, args.phase)
        else:
            result = verify_fixture(args.run)
        output_result = result
        if args.command == "verify" and args.summary:
            report_path = Path(result["run_path"]) / "operator" / "verification.json"
            output_result = summarize_verification(result, report_path)
        print(json.dumps(output_result, indent=2, sort_keys=True))
        if args.command in ('probe','verify'):
            report_path = args.run/'operator'/('verification.json' if args.command=='verify' else f'probes/worker-{args.worker}-{args.phase}.json')
            diagnostics = report_check_diagnostics(result, report_path, phase=args.command)
            if (result.get('passed') is False or result.get('errors')) and not diagnostics:
                diagnostics=[make_diagnostic(code='FIXTURE_CHECK_FAILED',severity='error',phase=args.command,
                    expected='Every required fixture check passes with no reported errors',observed={'checks':result.get('checks'),'errors':result.get('errors')},
                    rationale='A failed fixture invariant prevents this run from proving isolated contribution delivery.',
                    rationale_ref='CONTRACT.md#pass-gates',evidence=[evidence_reference(report_path)],
                    recovery='Inspect the named checks and retained snapshots before a new run.',retry_safety='Do not repeat probes or integration in this run.')]
            # Probe writers each have their own diagnostic log; there is no shared append race.
            log=report_path.with_suffix('.diagnostics.jsonl')
            emit_diagnostics(diagnostics,jsonl_path=log)

        if args.command == "probe":
            return 0 if not result["errors"] and all(result["checks"].values()) else 1
        if args.command == "verify":
            return 0 if result["passed"] else 1
        return 0
    except (FixtureError, OSError, ValueError, KeyError) as exc:
        emit_diagnostics([make_diagnostic(code='FIXTURE_OPERATION_FAILED',severity='error',phase=args.command,
            expected='The requested fixture phase has valid inputs and satisfies its preconditions',
            observed={'exception':type(exc).__name__,'detail':str(exc)},
            rationale='Incomplete or malformed fixture evidence cannot qualify workspace preservation.',
            rationale_ref='CONTRACT.md#phase-sequence',evidence=[evidence_reference(args.run/'manifest.json')],
            recovery='Inspect the cited manifest and exception; retain the failed attempt.',retry_safety='A new run is required after a partially completed setup or probe.')])
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
