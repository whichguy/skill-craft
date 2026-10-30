#!/usr/bin/env python3
"""Descriptive SDLC probes for a finished run (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §4, Track A).

Each probe counts something a run's kept evidence shows. It is reported beside the scorecard, never scored and outside
every grading digest. A probe becomes a gate only after it fires on a live run, the finding is confirmed real, and a
replay on every saved run shows the gate would refuse no honest run (proposal §4).

* P1 ``suppressions``: lint and type suppression comments the run added to code or tests (``# noqa``,
  ``eslint-disable``, ``@ts-ignore``, ...).
* P2 ``earlier_test_edits``: a commit that changes a test file an earlier step or item of the run created, with the
  assertion lines it removed and added.
* P3 ``foreign_commits``: commits in the run's history that no ShipLoop record of the run names (the model committed
  by hand; seen in 7 of 12 fidelity runs).
* P5 ``new_dependencies``: dependencies a manifest gained (package.json, requirements*.txt, pyproject.toml, go.mod).
* P6 ``secret_like``: added lines that match a known credential format. Only the format and the path are kept, never
  the value.
* P7 ``swallowed_errors``: added product-code lines that discard an error (``except: pass``, an empty ``catch``,
  ``|| true`` in a shell script).

P4 (an earlier item's test IDs missing from a later item's full regression) reads the verify records and is not built
here yet. A probe whose input the run did not keep says ``kept: false``, never 0: silence is not absence.

    python3 test/shiploop_e2e/sdlc_probes.py --worktree DIR --start HEAD0 [--run RUN_DIR] [--root CHECKOUT]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
LIMIT = 20  # rows kept per probe; the count is always whole

SUPPRESSIONS = {
    "noqa": re.compile(r"#\s*noqa\b", re.I),
    "type-ignore": re.compile(r"#\s*type:\s*ignore\b"),
    "pylint-disable": re.compile(r"#\s*pylint:\s*disable\b"),
    "pyright-ignore": re.compile(r"#\s*pyright:\s*ignore\b"),
    "eslint-disable": re.compile(r"eslint-disable(-next-line|-line)?\b"),
    "ts-ignore": re.compile(r"@ts-(ignore|expect-error|nocheck)\b"),
    "nolint": re.compile(r"//\s*nolint\b"),
    "rubocop-disable": re.compile(r"rubocop:disable\b"),
    "suppress-warnings": re.compile(r"@SuppressWarnings\b"),
    "nosonar": re.compile(r"\bNOSONAR\b"),
    "coverage-ignore": re.compile(r"(#\s*pragma:\s*no cover|istanbul ignore|c8 ignore)\b"),
}
SECRET_FORMATS = {
    "aws-access-key": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "stripe-live-key": re.compile(r"\b[rs]k_live_[0-9A-Za-z]{24,}\b"),
    "anthropic-key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "openai-key": re.compile(r"\bsk-(proj-)?[A-Za-z0-9_-]{40,}\b"),
}
SWALLOWS = {
    "except-pass": re.compile(r"^\s*except\b[^:]*:\s*(pass|\.\.\.)\s*(#.*)?$"),
    "empty-catch": re.compile(r"\bcatch\s*(\([^)]*\))?\s*\{\s*\}"),
    "catch-noop": re.compile(r"\.catch\(\s*(\(\s*\w*\s*\)|\w+)\s*=>\s*(\{\s*\}|null|undefined)\s*\)"),
}
OPEN_EXCEPT = re.compile(r"^\s*except\b[^:]*:\s*(#.*)?$")
OPEN_CATCH = re.compile(r"\bcatch\s*(\([^)]*\))?\s*\{\s*$")
PASS_LINE = re.compile(r"^\s*(pass|\.\.\.)\s*(#.*)?$")
CLOSE_BRACE = re.compile(r"^\s*\}")
OR_TRUE = re.compile(r"\|\|\s*true\b")
SHELL = re.compile(r"(\.(sh|bash|zsh|ksh)|(^|/)Makefile|\.mk)$")
ASSERTION = re.compile(r"\bassert\w*\b|\bexpect\s*\(|\.should\b|\bself\.assert\w*\(|\bt\.(equal|deepEqual|ok|is|throws|"
                       r"strictEqual|deepStrictEqual)\b|\bassert\.\w+\(")
STEP_SUBJECT = re.compile(r"^feat\((?P<item>[^/()]+)/(?P<step>[^/()]+)\):")
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")


def git(tree: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, env=GIT_ENV, check=False)
    return done.stdout if done.returncode == 0 else ""


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """(path, new line number, text) for every added line of a unified diff (``git diff`` output, renames followed)."""
    rows, path, number = [], None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            path = None if target == "/dev/null" else target[2:] if target.startswith("b/") else target
        elif line.startswith("@@"):
            found = re.search(r"\+(\d+)", line)
            number = int(found.group(1)) if found else 0
        elif path is not None and line.startswith("+") and not line.startswith("+++"):
            rows.append((path, number, line[1:]))
            number += 1
        elif path is not None and not line.startswith("-"):
            number += 1
    return rows


def suppressions(added: Iterable[tuple[str, int, str]], classify: Callable[[str], str]) -> list[dict]:
    """P1: suppression comments on added code and test lines."""
    return [{"path": path, "line": number, "kind": kind} for path, number, text in added
            if classify(path) in ("code", "test")
            for kind, pattern in SUPPRESSIONS.items() if pattern.search(text)]


def secret_like(added: Iterable[tuple[str, int, str]]) -> list[dict]:
    """P6: added lines that match a known credential format; the value is never returned."""
    return [{"path": path, "line": number, "format": name} for path, number, text in added
            for name, pattern in SECRET_FORMATS.items() if pattern.search(text)]


def swallowed_errors(added: list[tuple[str, int, str]], classify: Callable[[str], str]) -> list[dict]:
    """P7: added product-code lines that discard an error, one line or an opener and its body on the next added line."""
    rows = []
    for index, (path, number, text) in enumerate(added):
        if classify(path) != "code":
            continue
        kinds = [kind for kind, pattern in SWALLOWS.items() if pattern.search(text)]
        follow = added[index + 1] if index + 1 < len(added) else None
        if follow and follow[0] == path and follow[1] == number + 1:
            if OPEN_EXCEPT.search(text) and PASS_LINE.search(follow[2]):
                kinds.append("except-pass")
            if OPEN_CATCH.search(text) and CLOSE_BRACE.search(follow[2]):
                kinds.append("empty-catch")
        if SHELL.search(path) and OR_TRUE.search(text):
            kinds.append("or-true")
        rows += [{"path": path, "line": number, "kind": kind} for kind in kinds]
    return rows


def _names(manifest: str, text: str) -> set[str]:
    if not text:
        return set()
    name = Path(manifest).name
    if name == "package.json":
        try:
            data = json.loads(text)
        except ValueError:
            return set()
        return {key for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
                for key in (data.get(field) or {}) if isinstance(data.get(field), dict)}
    if name.startswith("requirements") and name.endswith(".txt"):
        found = (re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line) for line in text.splitlines()
                 if line.strip() and not line.lstrip().startswith(("#", "-")))
        return {match.group(1).lower() for match in found if match}
    if name == "pyproject.toml":
        try:
            import tomllib  # noqa: PLC0415 - Python 3.11+
            data = tomllib.loads(text)
        except Exception:  # noqa: BLE001 - an unreadable manifest names nothing
            return set()
        project = data.get("project") or {}
        listed = list(project.get("dependencies") or [])
        for extra in (project.get("optional-dependencies") or {}).values():
            listed += list(extra or [])
        names = {re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", str(item)).group(1).lower()
                 for item in listed if re.match(r"^\s*[A-Za-z0-9]", str(item))}
        poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
        return names | {key.lower() for key in poetry if key.lower() != "python"}
    if name == "go.mod":
        return set(re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/[^\s]+)\s+v\d", text, re.M))
    return set()


MANIFESTS = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|go\.mod)$")


def new_dependencies(tree: Path, start: str) -> list[dict]:
    """P5: dependency names each manifest has at HEAD and did not have at ``start``."""
    changed = [path for path in git(tree, "diff", "--name-only", start, "HEAD").splitlines() if MANIFESTS.search(path)]
    rows = []
    for manifest in changed:
        before = _names(manifest, git(tree, "show", f"{start}:{manifest}"))
        after = _names(manifest, git(tree, "show", f"HEAD:{manifest}"))
        rows += [{"manifest": manifest, "name": name} for name in sorted(after - before)]
    return rows


def earlier_test_edits(tree: Path, start: str, classify: Callable[[str], str]) -> list[dict]:
    """P2: a commit that modifies a test file an earlier commit of the run added under another item or step.

    Each row names the file, the step that created it, the commit's own step (from ShipLoop's ``feat(item/step)``
    subject; ``?`` for any other commit) and the assertion lines removed and added."""
    created: dict[str, str] = {}
    rows = []
    for sha in git(tree, "rev-list", "--reverse", f"{start}..HEAD").split():
        subject = git(tree, "log", "-1", "--format=%s", sha).strip()
        match = STEP_SUBJECT.match(subject)
        owner = f"{match.group('item')}/{match.group('step')}" if match else "?"
        for status_line in git(tree, "diff-tree", "--no-commit-id", "-r", "--name-status", sha).splitlines():
            status, _, path = status_line.partition("\t")
            if classify(path) != "test":
                continue
            if status.startswith("A"):
                created.setdefault(path, owner)
            elif status.startswith("M") and path in created and created[path] != owner:
                patch = git(tree, "show", "--format=", "-U0", sha, "--", path).splitlines()
                removed = sum(1 for line in patch if line.startswith("-") and not line.startswith("---")
                              and ASSERTION.search(line))
                added = sum(1 for line in patch if line.startswith("+") and not line.startswith("+++")
                            and ASSERTION.search(line))
                rows.append({"path": path, "created_by": created[path], "changed_by": owner, "commit": sha[:12],
                             "assertions_removed": removed, "assertions_added": added})
    return rows


def foreign_commits(tree: Path, start: str, run: Optional[Path]) -> Optional[list[dict]]:
    """P3: commits after ``start`` whose full ID no record under the run folder names; None without the run folder."""
    if run is None or not run.is_dir():
        return None
    named: set[str] = set()
    for path in run.rglob("*"):
        if path.is_file() and path.suffix in (".md", ".json", ".jsonl", ".txt") and path.stat().st_size < 5_000_000:
            try:
                named.update(HEX40.findall(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    return [{"commit": sha[:12], "subject": git(tree, "log", "-1", "--format=%s", sha).strip()[:80]}
            for sha in git(tree, "rev-list", "--reverse", f"{start}..HEAD").split() if sha not in named]


def _classifier(root: Path) -> Callable[[str], str]:
    sys.path.insert(0, str(root / "skills" / "shiploop" / "scripts"))
    import shiploop_item_scope as scope  # noqa: PLC0415 - ShipLoop's own path classes
    return scope.classify


def _report(rows: Optional[list[dict]]) -> dict[str, Any]:
    if rows is None:
        return {"kept": False}
    return {"kept": True, "count": len(rows), "rows": rows[:LIMIT]}


def probe(worktree: Path, start: str, run: Optional[Path] = None, root: Path = DEFAULT_ROOT,
          classify: Optional[Callable[[str], str]] = None) -> dict[str, Any]:
    """Every probe on one finished run: ``worktree`` holds its history from ``start`` (the seeded or baseline head)."""
    if not worktree.is_dir() or not git(worktree, "rev-parse", "--verify", f"{start}^{{commit}}").strip():
        return {name: {"kept": False} for name in ("suppressions", "earlier_test_edits", "foreign_commits",
                                                   "new_dependencies", "secret_like", "swallowed_errors")}
    classify = classify or _classifier(root)
    added = added_lines(git(worktree, "diff", "-M", "--unified=0", start, "HEAD"))
    return {
        "suppressions": _report(suppressions(added, classify)),
        "earlier_test_edits": _report(earlier_test_edits(worktree, start, classify)),
        "foreign_commits": _report(foreign_commits(worktree, start, run)),
        "new_dependencies": _report(new_dependencies(worktree, start)),
        "secret_like": _report(secret_like(added)),
        "swallowed_errors": _report(swallowed_errors(added, classify)),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--start", required=True, help="the commit the run started from (seeded or baseline head)")
    parser.add_argument("--run", type=Path, help="the ShipLoop run folder, for foreign_commits")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the checkout whose path classes to use")
    args = parser.parse_args(argv)
    print(json.dumps(probe(args.worktree, args.start, args.run, args.root), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
