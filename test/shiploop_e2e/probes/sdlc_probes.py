#!/usr/bin/env python3
"""Descriptive SDLC probes over a finished E2E run (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §4, Track A).

This is a reader, not part of the grade. It sits below the harness's top level, so it is in neither the evaluator digest
(boundary.evaluator_files reads the top level only) nor the qualification snapshot, and run.py never calls it. It reads an
output folder the harness wrote (``<out>``) and prints facts. It writes nothing into the run, changes no verdict and sends
nothing to a model.

Its lists follow the fidelity block's rules (SPEC.md, "A fidelity block is a record, never a verdict"):
- each probe is a list of facts for a reviewer to confirm;
- an input the run did not keep is null, with its reason in ``unmeasured``, never 0;
- a probe that raises is unmeasured, never a failure of the reader.

The probes:
* P1 ``suppressions``: lint and type suppression comments added to code or tests (``# noqa``, ``eslint-disable``, ...).
* P2 ``earlier_test_edits``: a commit that changes a test file an earlier step or item of the run created, with the
  assertion lines it removed and added.
* P3 ``model_commits``: read from the run's own metrics.json, never recounted (S-12). It reports ``commits.other.n``
  (counters.history: commits ShipLoop did not make), and the fidelity block's ``model_commits`` and ``script_owned`` edits
  (for example a ``sed -i`` of return-plan.md).
* P5 ``new_dependencies``: dependency names a manifest gained (package.json, requirements*.txt, pyproject.toml, go.mod).
* P6 ``secret_like``: added lines that match a known credential format. It reports the format and path, never the value.
* P7 ``swallowed_errors``: added product-code lines that discard an error (``except: pass``, an empty ``catch``,
  ``|| true`` in a shell script).

P4 (an earlier item's test IDs missing from a later item's full regression) is not built. It needs every item's IDs mapped
across the verify records, and fidelity.validation reads one record at a time. It is reported as unmeasured.

The repository is ``<out>/work`` while the run's folders exist; after ``lifecycle.py dispose`` it is the delivery bundle,
rebuilt with ``delivery.restore``. The run's commits are those after the start head that counters reads from
invocation.json; for a fresh run, the whole history.

    python3 test/shiploop_e2e/probes/sdlc_probes.py OUT [OUT ...]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

HARNESS = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HARNESS))
import counters  # noqa: E402
import delivery  # noqa: E402

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
LIMIT = 20  # facts kept per probe; ``n`` is always the whole count
NOT_BUILT_P4 = ("not built: needs every item's test IDs mapped across the verify records (fidelity.validation reads one "
                "record at a time)")

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
MANIFESTS = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|go\.mod)$")


def git(tree: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, env=GIT_ENV, check=False)
    return done.stdout if done.returncode == 0 else ""


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """(path, new line number, text) for every added line of a unified diff."""
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
    """P7: added product-code lines that discard an error: one line, or an opener and its body on the next added line."""
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
                if isinstance(data.get(field), dict) for key in data[field]}
    if name.startswith("requirements") and name.endswith(".txt"):
        found = (re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line) for line in text.splitlines()
                 if line.strip() and not line.lstrip().startswith(("#", "-")))
        return {match.group(1).lower() for match in found if match}
    if name == "pyproject.toml":
        import tomllib  # noqa: PLC0415 - Python 3.11+
        data = tomllib.loads(text)
        project = data.get("project") or {}
        listed = list(project.get("dependencies") or [])
        for extra in (project.get("optional-dependencies") or {}).values():
            listed += list(extra or [])
        names = {match.group(1).lower() for match in (re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", str(item))
                                                      for item in listed) if match}
        poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
        return names | {key.lower() for key in poetry if key.lower() != "python"}
    if name == "go.mod":
        return set(re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/[^\s]+)\s+v\d", text, re.M))
    return set()


def new_dependencies(tree: Path, start: Optional[str]) -> list[dict]:
    """P5: dependency names each manifest has at HEAD and did not have at ``start``."""
    base = start or EMPTY_TREE
    changed = [path for path in git(tree, "diff", "--name-only", base, "HEAD").splitlines() if MANIFESTS.search(path)]
    rows = []
    for manifest in changed:
        before = _names(manifest, git(tree, "show", f"{start}:{manifest}")) if start else set()
        after = _names(manifest, git(tree, "show", f"HEAD:{manifest}"))
        rows += [{"manifest": manifest, "name": name} for name in sorted(after - before)]
    return rows


def earlier_test_edits(tree: Path, start: Optional[str], classify: Callable[[str], str]) -> list[dict]:
    """P2: a commit that modifies a test file an earlier commit of the run added under another item or step.

    Each fact names the file, the step that created it, the commit's own step (from ShipLoop's ``feat(item/step)``
    subject; ``?`` for any other commit) and the assertion lines removed and added. It walks every ref (``--all``), as
    counters.history does."""
    created: dict[str, str] = {}
    rows = []
    for sha in git(tree, "rev-list", "--reverse", "--topo-order", "--all", *(["--not", start] if start else [])).split():
        subject = git(tree, "log", "-1", "--format=%s", sha).strip()
        match = STEP_SUBJECT.match(subject)
        owner = f"{match.group('item')}/{match.group('step')}" if match else "?"
        for status_line in git(tree, "diff-tree", "--root", "--no-commit-id", "-r", "--name-status", sha).splitlines():
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


def model_commits(out: Path) -> dict[str, Any]:
    """P3, read from the run's metrics.json (counters and the fidelity block), never recounted."""
    record = json.loads((out / "metrics.json").read_text())
    other = ((record.get("commits") or {}).get("other") or {}).get("n")
    edits = (record.get("fidelity") or {}).get("edits") or {}
    if other is None and not edits:
        raise LookupError("metrics.json has no commits or fidelity edits block (a run graded before 2026-10-10)")
    return {"commits_other": other,
            "model_commits": len(edits["model_commits"]) if isinstance(edits.get("model_commits"), list) else None,
            "script_owned_edits": len(edits["script_owned"]) if isinstance(edits.get("script_owned"), list) else None}


def _classifier(root: Path) -> Callable[[str], str]:
    sys.path.insert(0, str(root / "skills" / "shiploop" / "scripts"))
    import shiploop_item_scope as scope  # noqa: PLC0415 - ShipLoop's own path classes
    return scope.classify


def _facts(rows: list[dict]) -> dict[str, Any]:
    return {"n": len(rows), "facts": rows[:LIMIT]}


def _why(exc: BaseException) -> str:
    return "failed: " + type(exc).__name__ + ": " + " ".join(str(exc).split())[:200]


def probe(out: Path, root: Path = ROOT, classify: Optional[Callable[[str], str]] = None) -> dict[str, Any]:
    """Every probe on one finished run's output folder: ``{"probes": {name: value or None}, "unmeasured": {name: why}}``."""
    out = Path(out)
    found: dict[str, Any] = {name: None for name in ("suppressions", "earlier_test_edits", "model_commits",
                                                     "earlier_ids_in_regressions", "new_dependencies", "secret_like",
                                                     "swallowed_errors")}
    unmeasured: dict[str, str] = {"earlier_ids_in_regressions": NOT_BUILT_P4}
    try:
        found["model_commits"] = model_commits(out)
    except Exception as exc:  # noqa: BLE001 - a record that cannot be read is unmeasured, never 0
        unmeasured["model_commits"] = exc.args[0] if isinstance(exc, LookupError) else _why(exc)
    git_probes = ("suppressions", "earlier_test_edits", "new_dependencies", "secret_like", "swallowed_errors")
    with tempfile.TemporaryDirectory(prefix="sdlc-probes-") as tmp:
        work, why = out / "work", None
        if not (work / ".git").exists():
            try:
                work = delivery.restore(out, Path(tmp) / "work")
            except (FileNotFoundError, RuntimeError) as exc:
                why = "no work repository and no delivery bundle: " + " ".join(str(exc).split())[:160]
        start = None
        if why is None:
            start, why = counters._starting_point(out, work)  # the run's start head, read once (S-12)
        if why is not None:
            unmeasured.update({name: why for name in git_probes})
            return {"probes": found, "unmeasured": unmeasured}
        classify = classify or _classifier(root)
        added = added_lines(git(work, "diff", "-M", "--unified=0", start or EMPTY_TREE, "HEAD"))
        runs = {"suppressions": lambda: suppressions(added, classify),
                "earlier_test_edits": lambda: earlier_test_edits(work, start, classify),
                "new_dependencies": lambda: new_dependencies(work, start),
                "secret_like": lambda: secret_like(added),
                "swallowed_errors": lambda: swallowed_errors(added, classify)}
        for name, run in runs.items():
            try:
                found[name] = _facts(run())
            except Exception as exc:  # noqa: BLE001 - fail open: one probe that raises is unmeasured, never 0
                unmeasured[name] = _why(exc)
    return {"probes": found, "unmeasured": unmeasured}


def main(argv: Optional[list[str]] = None) -> int:
    folders = list(argv if argv is not None else sys.argv[1:])
    if not folders:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    for folder in folders:
        print(json.dumps({"out": str(folder), **probe(Path(folder))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
