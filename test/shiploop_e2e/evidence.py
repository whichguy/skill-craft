"""Frozen inputs and integrity checks for developer E2E trials.

Digests detect changes to retained evidence. They are not a filesystem sandbox.
Python bytecode is not an authoritative input.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "__pycache__"}
SCHEMA = "shiploop-e2e-evidence/1"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def object_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def tree_digest(root: Path) -> str:
    """Hash path, mode and bytes; symlinks are hashed, never traversed."""
    root = Path(root)
    digest = hashlib.sha256()
    if not root.exists() and not root.is_symlink():
        return object_digest({"missing": True})
    paths = [root]
    if root.is_dir() and not root.is_symlink():
        for parent, directories, files in os.walk(root, followlinks=False):
            directories[:] = sorted(d for d in directories if d not in SKIP_DIRS)
            paths.extend(Path(parent) / d for d in directories)
            paths.extend(Path(parent) / f for f in files if not f.endswith(".pyc"))
    for path in sorted(paths):
        relative = "." if path == root else path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        digest.update(relative.encode() + b"\0" + str(stat.S_IMODE(mode)).encode() + b"\0")
        if path.is_symlink():
            digest.update(b"link\0" + os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.is_dir():
            digest.update(b"dir\0")
        else:
            raise ValueError(f"non-regular evidence file: {path}")
        digest.update(b"\0")
    return digest.hexdigest()


def git_state(root: Path) -> dict:
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    return {"head": git("rev-parse", "HEAD"), "status": git("status", "--porcelain", "--untracked-files=all"),
            "refs": git("show-ref", "--head")}


def fingerprint(root: Path) -> dict:
    return {"files": tree_digest(root), "git": git_state(root)}


def evaluator_recipe() -> dict:
    return {"spec": tree_digest(HERE / "SPEC.md"), "checks": tree_digest(HERE / "checks"),
            "code": {p.name: tree_digest(p) for p in sorted(HERE.glob("*.py"))}}


def validate_criteria(criteria: dict) -> None:
    if criteria.get("kind") not in {"delivery", "boundary", "noop"} or not criteria.get("expected_terminal"):
        raise ValueError("case must declare a supported kind and expected terminal")
    for group in ("requirements", "workflow"):
        rows = criteria.get(group)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"case {group} must be a nonempty list")
        ids = [row.get("id") if isinstance(row, dict) else row for row in rows]
        if any(not isinstance(identifier, str) or not identifier.strip() for identifier in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"case {group} needs unique nonempty ids")


def freeze(out: Path, plugin_dir: Path, case: dict, checks: list[str], invocation_id: str) -> dict:
    frozen = out / "evaluation"
    frozen.mkdir()
    shutil.copy2(HERE / "SPEC.md", frozen / "SPEC.md")
    shutil.copytree(HERE / "checks", frozen / "checks", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(plugin_dir, frozen / "subject", symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    criteria = {"requirements": case.get("requirements") or [{"id": "request", "description": case["prompt"]}],
                "workflow": case.get("workflow") or [f"S-{i}" for i in range(1, 15)],
                "kind": case.get("kind", "delivery"), "expected_terminal": case.get("expected_terminal", "done")}
    validate_criteria(criteria)
    recipe = {"case": case, "checks": checks, "criteria": criteria}
    atomic_json(frozen / "case.json", recipe)
    evaluator = evaluator_recipe()
    identity = {"invocation_id": invocation_id, "subject_digest": tree_digest(plugin_dir),
                "evaluator_digest": object_digest(evaluator), "case_digest": object_digest(recipe)}
    manifest = {"schema": SCHEMA, "identity": identity, "criteria": criteria, "evaluator": evaluator,
                "plugin_dir": str(plugin_dir.resolve()), "frozen_subject": "evaluation/subject",
                "frozen_digest": tree_digest(frozen)}
    atomic_json(out / "evaluation.json", manifest)
    return manifest


def sealed_inputs(out: Path) -> dict:
    names = ("prompt.txt", "host-prompt.txt", "invocation.json", "evaluation.json", "evaluation", "run-binding.json",
             "result.json", "events.jsonl", "timeline.jsonl", "transcript.md", "stderr.txt", "metrics.json", "work",
             "attempt.json", "attempts", "checks")
    values = {name: tree_digest(out / name) for name in names}
    values["resume_inputs"] = {p.name: tree_digest(p) for pattern in ("invocation-resume-*.json", "resume-*.txt")
                              for p in sorted(out.glob(pattern))}
    values["work_git"] = git_state(out / "work")
    result = read_json(out / "result.json")
    run_dir = (result.get("shiploop") or {}).get("run_dir")
    if run_dir:
        path = Path(run_dir).resolve()
        if not path.is_relative_to(out.resolve()):
            raise ValueError("run evidence escapes the retained output directory")
        values["run_dir"] = {"path": str(path), "digest": tree_digest(path)}
    prior = (result.get("follow_on") or {}).get("prior")
    if prior:
        values["predecessor"] = {"path": str(Path(prior).resolve()), "state": fingerprint(Path(prior) / "work")}
    return values


def seal(out: Path) -> dict:
    record = {"schema": SCHEMA, "identity": read_json(out / "result.json").get("identity"),
              "inputs": sealed_inputs(out)}
    atomic_json(out / "evidence-seal.json", record)
    return record


def verify_seal(out: Path) -> list[str]:
    try:
        record = read_json(out / "evidence-seal.json")
        result = read_json(out / "result.json")
        manifest = read_json(out / "evaluation.json")
        reasons = []
        if record.get("schema") != SCHEMA or not record.get("identity"):
            reasons.append("missing or unsupported evidence seal")
        if record.get("identity") != result.get("identity"):
            reasons.append("candidate identity changed")
        if manifest.get("frozen_digest") != tree_digest(out / "evaluation"):
            reasons.append("frozen evaluator or subject changed")
        current = sealed_inputs(out)
        if current != record.get("inputs"):
            reasons.extend(f"evidence changed: {key}" for key in sorted(set(current) | set(record.get("inputs", {})))
                           if current.get(key) != record.get("inputs", {}).get(key))
        return reasons
    except (OSError, ValueError, TypeError) as exc:
        return [f"evidence unavailable: {exc}"]


def stream_errors(path: Path) -> list[str]:
    """A nonempty JSONL stream must contain complete object records."""
    if not path.is_file() or not path.stat().st_size:
        return ["event stream is missing or empty"]
    errors = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        try:
            if not isinstance(json.loads(line), dict):
                raise ValueError("not an object")
        except ValueError:
            errors.append(f"malformed event at line {number}")
    return errors
