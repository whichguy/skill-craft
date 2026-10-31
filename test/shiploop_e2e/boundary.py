"""The evaluator boundary (SPEC "The promotion contract", build step 3): what grades a run, what a candidate may change,
and which files are held out from every model.

* ``fingerprint`` digests what grades a run: the harness's code (``evaluator``), its checks and fixtures (``oracle``) and the case's
  catalog entry (``case``). ``run.py`` records it in result.json as ``boundary`` each time it grades, a regrade included; the
  candidate's digest is the plugin tree the host loaded (``versions.plugin_sha256``). ``promotion.py`` compares a case only
  across attempts with equal digests, so a harness or oracle change is an experiment of its own.
* ``candidate_path`` is what the improver of ``iterate.py`` may change: the skill, its notes and ShipLoop's own tests, never
  the E2E harness, the test runner or the suite catalog.
* ``held_out_files`` are a case's acceptance module and its ``calibration`` files. ``withheld`` takes them out of a worktree
  while a model works in it; ``named`` counts the model's tool calls that name one. Only calls: the SPEC, which is in the
  improver's prompt, and ShipLoop's own docs name these files, so a match in prose or a file's text would prove nothing.

The hosts run unsandboxed: withholding closes the default path, and a tool call that names a held-out file is detected; a
read that never names one is not.
Reads files only; ``withheld`` alone writes, and only the held-out files of the worktree it is given, which it restores.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402  (metrics.tool_call_events: the one reader of a host event's tool calls)

CHECKS = "test/shiploop_e2e/checks"  # the oracle folder, as a repository path

# What the improver may change: the skill, its change notes and ShipLoop's own tests and their fixtures.
CANDIDATE_PREFIXES = ("skills/shiploop/", "changes/shiploop/", "test/shiploop-", "test/shiploop_",
                      "test/fixtures/shiploop-", "test/experiments/shiploop_")
# The E2E harness and its suites, which the prefixes above would otherwise admit.
HARNESS_PREFIXES = ("test/shiploop_e2e/", "test/shiploop-e2e")
GROUPS = ("evaluator", "oracle", "case")  # the digests a candidate must leave unchanged
QUALIFICATION_CONTRACT = "qualification-inputs/1"


def candidate_path(path: str) -> bool:
    """Whether a repository path is the candidate's to change (SPEC: the improver may change only the candidate)."""
    return path.startswith(CANDIDATE_PREFIXES) and not path.startswith(HARNESS_PREFIXES)


def files_digest(root: Path, files: list[Path]) -> tuple[str | None, str | None]:
    """(12 hex, None) over each file's path relative to `root` and the sha256 of its bytes, or (None, why) when one cannot
    be read: a digest of the readable part would name other bytes."""
    digest = hashlib.sha256()
    for path in sorted(files):
        try:
            data = path.read_bytes()
        except OSError as error:
            return None, f"{path}: {error.strerror}"
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n")
    return digest.hexdigest()[:12], None


def evaluator_files(harness: Path) -> list[Path]:
    """The harness's code: the ``*.py`` and ``*.cjs`` files at the top of the harness folder."""
    return [path for path in harness.iterdir() if path.suffix in (".py", ".cjs") and path.is_file()]


def oracle_files(harness: Path) -> list[Path]:
    """Checks and fixture inputs, excluding generated Python caches."""
    return _tree_files(harness / "checks") + _tree_files(harness / "fixtures")


def _tree_files(folder: Path) -> list[Path]:
    """All readable input files below a frozen evaluator tree, excluding generated Python cache files."""
    found = []
    if not folder.is_dir():
        return found
    def unreadable(error: OSError) -> None:
        raise error

    for here, folders, names in os.walk(folder, onerror=unreadable):
        folders[:] = [name for name in folders if name != "__pycache__"]
        found += [Path(here) / name for name in names if not name.endswith(".pyc")]
    return sorted(found)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def qualification_snapshot(harness: Path, case_names=None) -> dict:
    """Freeze the scorecard inputs and their current bytes for a strict promotion/5 registration.

    ``cases`` and ``suites`` are snapshots, so an old run is scored with the registered requiredness even if the live
    catalogs later change. ``files`` binds the snapshot to the evaluator, recursive checks/fixtures/evaluators, SPEC, catalogs and
    the scorecard's source modules; a comparison recomputes this record before it can qualify anything. Paths are relative
    to the repository root (the parent of ``test/``), not to a machine-specific checkout path.
    """
    harness = Path(harness).resolve()
    repo = harness.parent.parent
    try:
        cases = json.loads((harness / "cases.json").read_text())
        suites = json.loads((harness / "suites.json").read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f"qualification catalogs cannot be read: {error}") from None
    if not isinstance(cases, dict) or not isinstance(suites, dict):
        raise TypeError("qualification cases.json and suites.json must contain objects")
    names = sorted(set(cases) if case_names is None else case_names)
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("qualification snapshot needs non-empty case names")
    missing = [name for name in names if name not in cases or not isinstance(cases[name], dict)]
    if missing:
        raise ValueError("qualification snapshot cannot find case definitions for " + ", ".join(map(str, missing)))
    files = [harness / "SPEC.md", harness / "cases.json", harness / "suites.json"]
    files += evaluator_files(harness)
    files += oracle_files(harness)
    files += _tree_files(harness / "evaluators")
    # These modules are read by scorecard.py for validity and metrics. They are also top-level evaluator files today;
    # spelling the dependency set out makes the frozen scorecard inputs explicit if their layout changes later.
    files += [harness / name for name in ("scorecard.py", "boundary.py", "metrics.py", "delivery.py",
                                           "environment.py", "runrecord.py")]
    files = sorted({path.resolve() for path in files})
    hashes = {}
    for path in files:
        try:
            hashes[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except (OSError, ValueError) as error:
            raise ValueError(f"qualification input cannot be read: {path}: {error}") from None
    frozen = {"contract": QUALIFICATION_CONTRACT, "scorecard": "scorecard/6", "files": hashes,
              "cases": {name: cases[name] for name in names}, "suites": suites}
    frozen["sha256"] = hashlib.sha256(_canonical(frozen)).hexdigest()
    return frozen


def qualification_changes(frozen: dict, harness: Path, case_names=None) -> list[str]:
    """The strict qualification inputs that differ now from a registration, or a reason the current inputs are unknown."""
    try:
        current = qualification_snapshot(harness, case_names)
    except (OSError, ValueError) as error:
        return [f"current qualification inputs are unavailable: {error}"]
    if not isinstance(frozen, dict) or frozen.get("contract") != QUALIFICATION_CONTRACT:
        return ["the registration has no supported qualification-input snapshot"]
    try:
        digest = hashlib.sha256(_canonical({key: value for key, value in frozen.items() if key != "sha256"})).hexdigest()
    except (TypeError, ValueError):
        return ["the registered qualification snapshot digest is malformed"]
    if frozen.get("sha256") != digest:
        return ["the registered qualification snapshot digest is malformed"]
    changed = sorted(set(frozen.get("files") or {}) | set(current["files"]))
    changed = [name for name in changed if (frozen.get("files") or {}).get(name) != current["files"].get(name)]
    if frozen.get("cases") != current.get("cases"):
        changed.append("case requiredness snapshot")
    if frozen.get("suites") != current.get("suites"):
        changed.append("suite requiredness snapshot")
    if frozen.get("scorecard") != current.get("scorecard"):
        changed.append("scorecard version")
    return changed


def fingerprint(harness: Path, case: dict | None) -> dict:
    """``{evaluator, oracle, case}`` (12 hex each) for the harness folder `harness` and the case's catalog entry as the run
    read it; a part that could not be made is null with its reason under ``unmeasured``. A custom prompt has no entry."""
    harness = Path(harness)
    found: dict = {}
    unmeasured: dict = {}
    for name, files in (("evaluator", evaluator_files), ("oracle", oracle_files)):
        try:
            found[name], why = files_digest(harness, files(harness))
        except OSError as error:
            found[name], why = None, f"{harness}: {error.strerror}"
        if why:
            unmeasured[name] = why
    if case:
        found["case"] = hashlib.sha256(json.dumps(case, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]
    else:
        found["case"], unmeasured["case"] = None, "a custom prompt has no catalog entry"
    return {**found, **({"unmeasured": unmeasured} if unmeasured else {})}


def changed(before: dict, after: dict) -> list[str]:
    """The groups whose digest differs, or that are null on either side (a digest that could not be made proves nothing)."""
    return [name for name in GROUPS if before.get(name) is None or before.get(name) != after.get(name)]


def held_out_files(cases: dict) -> list[str]:
    """The repository paths of every case's held-out files: its acceptance module and its acceptance block's ``calibration``."""
    paths = set()
    for spec in cases.values():
        block = (spec.get("quality") or {}).get("acceptance") if isinstance(spec, dict) else None
        if block:
            paths.add(f"{CHECKS}/{block['module']}.py")
            paths.update(block.get("calibration") or [])
    return sorted(paths)


def named(events_path: Path, paths: list[str]) -> int | None:
    """How many of a host's tool calls name a held-out file by its stem (the module name, or the calibration file's name
    without its suffix) in their input: a command, a path, a search. None when the events cannot be read; 0 is a measured
    none of such calls, not proof of no read (a call can reach a file without naming it)."""
    stems = sorted({Path(path).stem for path in paths})
    if not Path(events_path).is_file():
        return None
    try:
        calls = [arg for _, event in metrics.events(Path(events_path)) for _, _, arg in metrics.tool_call_events(event)]
    except OSError:
        return None
    return sum(1 for arg in calls if any(stem in json.dumps(arg) for stem in stems)) if stems else 0


def _git(worktree: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(worktree), *args], check=True, capture_output=True)


@contextlib.contextmanager
def withheld(worktree: Path, paths: list[str]):
    """Take the held-out files out of `worktree` while the block runs, then put the same bytes back.

    Each file is marked skip-worktree in that worktree's own index first, so its absence is not an uncommitted change, and
    no shared configuration (sparse checkout) is touched. Yields the paths withheld."""
    saved = {path: (worktree / path).read_bytes() for path in paths if (worktree / path).is_file()}
    if saved:
        _git(worktree, "update-index", "--skip-worktree", "--", *saved)
        for path in saved:
            (worktree / path).unlink()
    try:
        yield sorted(saved)
    finally:
        for path, data in saved.items():
            (worktree / path).parent.mkdir(parents=True, exist_ok=True)
            (worktree / path).write_bytes(data)
        if saved:
            subprocess.run(["git", "-C", str(worktree), "update-index", "--no-skip-worktree", "--", *saved],
                           capture_output=True)  # a path the improver removed from the index has no flag left to clear
