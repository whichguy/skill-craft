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
  assertion lines it removed and added. A step is told from its ``feat(item/step):`` subject; a run with no such subject
  cannot say which step wrote a test, so it is unmeasured, and a commit with another subject is owner ``?``.
* P3 ``model_commits``: read from the run's own metrics.json, never recounted (S-12). It reports ``commits.other.n``
  (counters.history: commits ShipLoop did not make), and the fidelity block's ``model_commits`` and ``script_owned`` edits
  (for example a ``sed -i`` of return-plan.md).
* P5 ``new_dependencies``: dependency names a manifest gained (package.json, requirements*.txt, pyproject.toml, go.mod,
  and an Apps Script project's appsscript.json: its libraries and enabled advanced services). A repository with no such
  manifest at the start or at HEAD is unmeasured, never "none": it may declare its dependencies where this reader does
  not look. A manifest that does not parse, or a pyproject.toml read on a Python without tomllib (3.11+), makes the probe
  unmeasured. A changed manifest of another kind (Cargo.toml, Gemfile, pom.xml, ...) is listed with ``name`` null and an
  ``unread`` note, so ``n`` is a floor and a zero means zero in the manifests this reader parses.
* P6 ``secret_like``: added lines that match a known credential format, the first format that matches per line. It
  reports the format and path, never the value. Only the net diff from the start to HEAD is scanned, so a secret
  committed and removed within the run is not reported.
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
MANIFESTS = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|go\.mod|appsscript\.json)$")
# Manifests of other ecosystems: a change to one is listed as unread, never counted as no change.
UNREAD_MANIFESTS = re.compile(r"(^|/)(Cargo\.toml|Gemfile|pom\.xml|Pipfile|setup\.py|setup\.cfg|build\.gradle(\.kts)?|"
                              r"composer\.json|mix\.exs|pubspec\.yaml|Package\.swift|environment\.ya?ml)$")
# A requirement line's name, when it is followed by a specifier, an extra, a marker or nothing (not a ``git+https`` URL).
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[|[<>=!~;@ ,]|$)")
DIFF_PROBES = ("suppressions", "secret_like", "swallowed_errors")


class GitError(RuntimeError):
    """A git command the reader needs failed. Its probes are unmeasured: a failure must never read as a count of nothing."""


def git(tree: Path, *args: str) -> str:
    """Stdout of a git command run in ``tree``; raises GitError when it fails. Undecodable bytes are replaced, and paths
    are not quoted, so a non-UTF-8 or non-ASCII file never stops the reader or changes its name."""
    done = subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(tree), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=GIT_ENV, check=False)
    if done.returncode != 0:
        raise GitError(f"git {args[0] if args else ''} failed (exit {done.returncode}): " + " ".join(done.stderr.split())[:160])
    return done.stdout


HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _header_path(target: str) -> Optional[str]:
    target = target.strip()
    if target.startswith('"') and target.endswith('"'):
        try:
            target = json.loads(target)
        except ValueError:
            target = target[1:-1]
    return None if target == "/dev/null" else target[2:] if target.startswith("b/") else target


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """(path, new line number, text) for every added line of a unified diff.

    A hunk is read by the counts in its header, so a line whose own text starts with ``++`` or ``--`` is not taken for a
    file header, and a ``\\ No newline at end of file`` marker is not a line."""
    rows, path, lines, index = [], None, diff.splitlines(), 0
    while index < len(lines):
        line = lines[index]
        index += 1
        hunk = HUNK.match(line)
        if line.startswith("+++ "):
            path = _header_path(line[4:])
        elif hunk:
            old = int(hunk.group(1)) if hunk.group(1) is not None else 1
            new = int(hunk.group(3)) if hunk.group(3) is not None else 1
            number = int(hunk.group(2))
            while (old > 0 or new > 0) and index < len(lines):
                body = lines[index]
                if body.startswith("\\"):
                    index += 1
                    continue
                if body.startswith("+") and new > 0:
                    if path is not None:
                        rows.append((path, number, body[1:]))
                    number, new = number + 1, new - 1
                elif body.startswith("-") and old > 0:
                    old -= 1
                elif body.startswith(" "):
                    old, new, number = old - 1, new - 1, number + 1
                else:
                    break
                index += 1
    return rows


def suppressions(added: Iterable[tuple[str, int, str]], classify: Callable[[str], str]) -> list[dict]:
    """P1: suppression comments on added code and test lines."""
    return [{"path": path, "line": number, "kind": kind} for path, number, text in added
            if classify(path) in ("code", "test")
            for kind, pattern in SUPPRESSIONS.items() if pattern.search(text)]


def secret_like(added: Iterable[tuple[str, int, str]]) -> list[dict]:
    """P6: added lines that match a known credential format (the first that matches); the value is never returned."""
    rows = []
    for path, number, text in added:
        name = next((name for name, pattern in SECRET_FORMATS.items() if pattern.search(text)), None)
        if name:
            rows.append({"path": path, "line": number, "format": name})
    return rows


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
        data = json.loads(text)  # a manifest that does not parse raises ValueError: the probe is then unmeasured
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
        return {key for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
                if isinstance(data.get(field), dict) for key in data[field]}
    if name.startswith("requirements") and name.endswith(".txt"):
        found = (REQUIREMENT.match(line) for line in text.splitlines()
                 if line.strip() and not line.lstrip().startswith(("#", "-")))
        return {match.group(1).lower() for match in found if match}
    if name == "pyproject.toml":
        try:
            import tomllib  # noqa: PLC0415 - Python 3.11+
        except ImportError:
            raise LookupError("pyproject.toml changed and this Python has no tomllib (3.11+), so its dependencies cannot "
                              "be read") from None
        data = tomllib.loads(text)
        project = data.get("project") or {}
        listed = list(project.get("dependencies") or [])
        for extra in (project.get("optional-dependencies") or {}).values():
            listed += list(extra or [])
        for group in (data.get("dependency-groups") or {}).values():  # PEP 735; an include-group entry is a table
            listed += [item for item in group or () if isinstance(item, str)]
        names = {match.group(1).lower() for match in (REQUIREMENT.match(str(item)) for item in listed) if match}
        poetry = (data.get("tool") or {}).get("poetry") or {}
        tables = [poetry.get("dependencies") or {}, poetry.get("dev-dependencies") or {}]
        tables += [(group or {}).get("dependencies") or {} for group in (poetry.get("group") or {}).values()]
        return names | {key.lower() for table in tables for key in table if key.lower() != "python"}
    if name == "go.mod":
        return set(re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/[^\s]+)\s+v\d", text, re.M))
    if name == "appsscript.json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
        declared = data.get("dependencies") if isinstance(data.get("dependencies"), dict) else {}
        libraries = {"library:" + str(row["libraryId"]) for row in declared.get("libraries") or ()
                     if isinstance(row, dict) and row.get("libraryId")}
        services = {"service:" + str(row["serviceId"]) for row in declared.get("enabledAdvancedServices") or ()
                    if isinstance(row, dict) and row.get("serviceId")}
        return libraries | services
    return set()


def new_dependencies(tree: Path, start: Optional[str]) -> list[dict]:
    """P5: dependency names each manifest has at HEAD and did not have at ``start``.

    A repository with no supported manifest at ``start`` or at HEAD cannot show a dependency to this reader, so that is
    unmeasured (a plain ``LookupError``, which ``probe`` records with its reason), never none. An Apps Script project
    declares its dependencies in appsscript.json, and a project with no manifest at all may declare them anywhere."""
    base = start or EMPTY_TREE
    at_start = set(git(tree, "ls-tree", "-r", "--name-only", start).splitlines()) if start else set()
    at_head = set(git(tree, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    if not any(MANIFESTS.search(path) for path in at_start | at_head):
        raise LookupError("no supported manifest (package.json, requirements*.txt, pyproject.toml, go.mod or "
                          "appsscript.json) at the start or at HEAD, so dependencies cannot be measured")
    changed = git(tree, "diff", "--name-only", base, "HEAD").splitlines()
    rows = []
    for manifest in (path for path in changed if MANIFESTS.search(path)):
        try:
            before = _names(manifest, git(tree, "show", f"{start}:{manifest}")) if manifest in at_start else set()
            after = _names(manifest, git(tree, "show", f"HEAD:{manifest}")) if manifest in at_head else set()
        except ValueError as exc:  # a manifest that does not parse would read as every name new, or none
            raise ValueError(f"{manifest} does not parse: " + " ".join(str(exc).split())[:100]) from None
        rows += [{"manifest": manifest, "name": name} for name in sorted(after - before)]
    rows += [{"manifest": path, "name": None, "unread": "a manifest this reader does not parse"}
             for path in changed if UNREAD_MANIFESTS.search(path)]
    return rows


def earlier_test_edits(tree: Path, start: Optional[str], classify: Callable[[str], str]) -> list[dict]:
    """P2: a commit that modifies a test file an earlier commit of the run added under another item or step.

    Each fact names the file, the step that created it, the commit's own step (from ShipLoop's ``feat(item/step)``
    subject; ``?`` for any other commit) and the assertion lines removed and added. It walks every ref (``--all``), as
    counters.history does."""
    created: dict[str, str] = {}
    rows = []
    commits = git(tree, "rev-list", "--reverse", "--topo-order", "--all", *(["--not", start] if start else [])).split()
    attributed = False
    for sha in commits:
        subject = git(tree, "log", "-1", "--format=%s", sha).strip()
        match = STEP_SUBJECT.match(subject)
        attributed = attributed or bool(match)
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
    if commits and not attributed:
        raise LookupError("no commit of the run has a ShipLoop feat(item/step) subject, so which step wrote a test cannot "
                          "be told from which changed it")
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
        unmeasured["model_commits"] = str(exc.args[0]) if type(exc) is LookupError else _why(exc)
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
        try:
            added, diff_why = added_lines(git(work, "diff", "-M", "--unified=0", start or EMPTY_TREE, "HEAD")), None
        except Exception as exc:  # noqa: BLE001 - a diff that cannot be read leaves its probes unmeasured, never 0
            added, diff_why = [], _why(exc)
        runs = {"suppressions": lambda: suppressions(added, classify),
                "earlier_test_edits": lambda: earlier_test_edits(work, start, classify),
                "new_dependencies": lambda: new_dependencies(work, start),
                "secret_like": lambda: secret_like(added),
                "swallowed_errors": lambda: swallowed_errors(added, classify)}
        for name, run in runs.items():
            if diff_why and name in DIFF_PROBES:
                unmeasured[name] = diff_why
                continue
            try:
                found[name] = _facts(run())
            except LookupError as exc:  # a plain LookupError is a probe saying its input is not here: unmeasured, with why
                unmeasured[name] = str(exc.args[0]) if type(exc) is LookupError else _why(exc)
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
