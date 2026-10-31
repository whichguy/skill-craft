#!/usr/bin/env python3
"""The stage suite's scenarios and their builder (docs/plans/shiploop-stage-suite.md, "A scenario is a directory").

It sits below the harness's top level, so it is in neither the evaluator digest (boundary.evaluator_files reads the top level
only) nor the qualification snapshot, and run.py never calls it. It reads scenario folders (``stage_cases/<stage>/<name>/``),
checks them, and builds a ShipLoop run for one, all under a folder the caller gives it.

A scenario folder holds ``scenario.json`` and, optionally:

    repo/                files laid over the fixture BEFORE the baseline commit (where a planted fault lives)
    worktree/            files laid into the execution checkout at the seed point (what earlier stages left)
    notes/               files laid into RUN/notes/
    reference/good/      result.json (the stage's accepted result, an object with "outcome") and tree/ (laid over the seed tree)
    reference/bad-<slug>/ the same, plus meta.json {"fails": ["P1", ...], "why": "..."}: the ids this output must make the
                         oracle FAIL. A name in deleted.txt (one path per line) is removed from the tree.

scenario.json keys (unknown keys are rejected): stage (a stage_spec stage, or ``improve@<stage>``, which loads and validates but
does not build yet), about, tags, tiers (verify, render, live; default all three), fixture (a folder of test/shiploop_e2e/
fixtures/), request_from (a key of step_cases.json: prompt, work_item and checks), options {delegation}, seed_records, worktree_mode,
planted [{id P<n>, what, signature}], controls [{id C<n>, what}], render [check], oracle [check], live {samples, pass}.
``about`` and ``fixture`` are required; ``request_from`` is required once the render or live tier is on (the verify tier reads
no request). Every other key has its default.

The rules ``validate`` keeps, each pinned by test/shiploop-e2e-stage-build.test.py:
- ids are unique, ``P<n>`` for a planted condition and ``C<n>`` for a control; checks are stage_oracle's (``validate_checks``);
- with the verify or live tier on, every id is proven by at least one check in ``oracle``;
- with the verify tier on, ``reference/good`` exists and every id is failed by at least one ``reference/bad-*`` (that is the proof
  the oracle can fail it); a ``meta.json`` parses and names known ids; a ``result.json`` is an object with an "outcome".

The two tiers that need a tree, and what they build:
- ``compose_seed_tree`` is pure file composition (the fixture, then ``repo/``, then ``worktree/``): no ShipLoop and no Git. The
  verify tier checks a reference output against that, through ``reference_bundle``.
- ``build`` starts a real run (``run.seed_run``: the workspace, the baseline commit, the neutral knowledge home, the item base)
  and records the stages before the scenario's through the engine's own seam, ``navigator.accept_effects``, so the script-owned
  effects of each stage run as they do in a real run (the checks validate-existing runs on entry, the item and step bases, the
  iteration record, the step's commit). ``run.seed_run`` is the harness's and is not edited: ``seam_seed`` substitutes its module
  global ``SEED_SCRIPT`` for the one call and restores it, whatever happens; it holds a lock while it does, so builds in several
  threads take turns (the global and the environment are the process's). ``render`` then runs ``shiploop next`` and reads the
  packet. The worktree overlay is laid just before implement is recorded when the scenario is past implement (otherwise the
  document stage records itself not applicable for want of a change), else at the seed point. A scenario at or before
  validate-existing may not have a ``worktree/``: nothing before implement changes the tree, and the checks validate-existing runs
  on entry run before the seed point, so such files belong in ``repo/``.

Build and render write under the ``out`` folder they are given. A render's ``next`` runs with the progress observer and the
keepalive off, stdin closed and a timeout, so no detached process outlives it. The seed phase is ``run.seed_run``'s: its child
processes inherit this one's standard input and have no timeout of their own, and a hung validate-existing check is bounded only
by the engine's own check timeout. The seed child runs with PYTHONSAFEPATH=1, so a render started from a folder that holds a
module named like a standard-library one does not import it.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
ROOT = HARNESS.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HARNESS))
import run  # noqa: E402  (also puts skills/shiploop/scripts on sys.path)
import stage_oracle  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

SCENARIOS_DIR = HARNESS / "stage_cases"
FIXTURES = HARNESS / "fixtures"
STEP_CASES = HARNESS / "step_cases.json"
DEFAULT_CLI = ROOT / "skills" / "shiploop" / "scripts" / "shiploop"
IMPROVE = "improve@"
TIERS = ("verify", "render", "live")
DELEGATIONS = ("inline", "ask-agent")
WORKTREE_MODES = ("committed", "uncommitted")
NEXT_SECONDS = 120  # a `shiploop next` that takes longer is stuck
KEYS = ("stage", "about", "tags", "tiers", "fixture", "request_from", "options", "seed_records", "worktree_mode", "planted",
        "controls", "render", "oracle", "live")
PLANTED_ID = re.compile(r"^P[1-9][0-9]*$")
CONTROL_ID = re.compile(r"^C[1-9][0-9]*$")
TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
REFERENCE_BAD = "bad-"
NO_WORKTREE_UP_TO = "validate-existing"  # a scenario of this stage or an earlier one may not have a worktree/
WORKTREE_ENV = "STAGE_SUITE_WORKTREE"  # the folder SEAM_SEED_SCRIPT lays into the execution checkout
SEEDING = threading.RLock()  # seam_seed substitutes process-wide state (a module global, the environment): one at a time


class ScenarioError(ValueError):
    """Scenarios that do not load. The message lists EVERY problem found, each with its scenario id; ``problems`` holds the lines."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__(f"{len(self.problems)} problem{'s' if len(self.problems) != 1 else ''}:\n  " + "\n  ".join(self.problems))


@dataclass(frozen=True)
class Scenario:
    """One scenario: ``id`` is ``<stage>/<name>``, ``data`` the validated scenario.json, ``tiers`` the tiers it supports."""
    id: str
    stage: str
    name: str
    dir: Path
    data: dict = field(hash=False)
    tiers: tuple = TIERS
    tags: tuple = ()


@dataclass
class Built:
    """What ``build`` left under its ``out`` folder.

    ``run_dir`` and ``worktree`` (the execution checkout) are the run's; ``cli`` the ShipLoop CLI that built it; ``stage`` the
    scenario's stage; ``issued`` whether ShipLoop will issue that stage's packet (False: the stage was ``settled`` by script during
    the seed and the run stands at ``current_stage``, past it); ``history_added`` the history rows the seed recorded (``stage``,
    ``outcome``, ``action``), the whole history of a fresh run; ``seeded`` what ``run.seed_run`` returned.
    """
    run_dir: Path
    worktree: Path
    cli: Path
    stage: str
    issued: bool
    settled: bool
    current_stage: str
    history_added: list
    seeded: dict


# ---------------------------------------------------------------------------------------------------------- validation

def base_stage(stage: Any) -> str | None:
    """The stage_spec stage a scenario stage names (``improve@spec`` names spec), or None when it names none."""
    if not isinstance(stage, str):
        return None
    name = stage[len(IMPROVE):] if stage.startswith(IMPROVE) else stage
    return name if name in stage_spec.STAGES else None


def step_cases() -> dict:
    """The catalog of step cases (step_cases.json) without its underscore keys."""
    return {key: value for key, value in json.loads(STEP_CASES.read_text()).items() if not key.startswith("_")}


def _text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _safe_path(path: str) -> str | None:
    """Why `path` cannot name a file below a tree, or None."""
    if "\0" in path:
        return "holds a NUL"
    if path.startswith("/"):
        return "is absolute"
    if ".." in path.split("/"):
        return "climbs out with '..'"
    return None


def _id_problems(entries: Any, label: str, pattern: re.Pattern, extra: tuple, seen: dict) -> list[str]:
    """Problems with a list of planted conditions or controls; the ids found go into `seen` (id -> label)."""
    if not isinstance(entries, list):
        return [f"{label} must be a list"]
    problems = []
    for index, entry in enumerate(entries):
        here = f"{label}[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{here} must be an object")
            continue
        problems += [f"{here}: unknown key {key!r}" for key in entry if key not in ("id", "what", *extra)]
        ident = entry.get("id")
        if not isinstance(ident, str) or not pattern.match(ident):
            problems.append(f"{here}: id {ident!r} must look like {pattern.pattern[1:-1].replace('[1-9][0-9]*', '<n>')}")
        elif ident in seen:
            problems.append(f"{here}: id {ident} is already used by {seen[ident]}")
        else:
            seen[ident] = here
        if not _text(entry.get("what")):
            problems.append(f"{here}: what must be a non-empty string")
        for key in extra:
            if key in entry and not _text(entry[key]):
                problems.append(f"{here}: {key} must be a non-empty string")
    return problems


def _tiers(data: dict, problems: list[str]) -> tuple:
    """The tiers a scenario supports; a malformed list is reported and counts as all three, so the other rules still run."""
    if "tiers" not in data:
        return TIERS
    value = data["tiers"]
    if not isinstance(value, list) or not value:
        problems.append(f"tiers must be a non-empty list of {', '.join(TIERS)}")
        return TIERS
    bad = [tier for tier in value if tier not in TIERS]
    if bad:
        problems.append(f"unknown tier {bad[0]!r}: one of {', '.join(TIERS)}")
        return TIERS
    if len(set(value)) != len(value):
        problems.append("tiers names a tier twice")
    return tuple(tier for tier in TIERS if tier in value)


def _reference_result(folder: Path, label: str) -> list[str]:
    path = folder / "result.json"
    if not path.is_file():
        return [f"{label}/result.json is missing"]
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return [f"{label}/result.json is not valid JSON: {error}"]
    if not isinstance(result, dict) or not _text(result.get("outcome")):
        return [f"{label}/result.json must be an object with an \"outcome\""]
    return []


def _reference_tree(folder: Path, label: str) -> list[str]:
    problems = []
    if (folder / "tree").exists() and not (folder / "tree").is_dir():
        problems.append(f"{label}/tree must be a folder")
    deleted = folder / "deleted.txt"
    if deleted.exists():
        if not deleted.is_file():
            return problems + [f"{label}/deleted.txt must be a file"]
        for line in _deleted(deleted):
            if problem := _safe_path(line):
                problems.append(f"{label}/deleted.txt: {line!r} {problem}")
    return problems


def _deleted(path: Path) -> list[str]:
    """The paths a deleted.txt names, one per line (blank lines ignored)."""
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def _reference_problems(scenario_dir: Path, ids: dict) -> list[str]:
    """The verify tier's rules for ``reference/``: a good output, and for every id a bad one that must fail it."""
    reference = scenario_dir / "reference"
    problems = []
    good = reference / "good"
    if not good.is_dir():
        problems.append("reference/good is missing: the oracle must pass an accepted output")
    else:
        problems += _reference_result(good, "reference/good") + _reference_tree(good, "reference/good")
    failed: set = set()
    if reference.is_dir():
        for folder in sorted(reference.iterdir()):
            label = f"reference/{folder.name}"
            if folder.name == "good" or folder.name.startswith("_"):
                continue
            if not folder.is_dir() or not folder.name.startswith(REFERENCE_BAD) or folder.name == REFERENCE_BAD:
                problems.append(f"{label}: a reference folder is good or bad-<slug>")
                continue
            problems += _reference_result(folder, label) + _reference_tree(folder, label)
            meta = folder / "meta.json"
            if not meta.is_file():
                problems.append(f"{label}/meta.json is missing: it names the ids this output must fail")
                continue
            try:
                found = json.loads(meta.read_text())
            except (OSError, ValueError) as error:
                problems.append(f"{label}/meta.json is not valid JSON: {error}")
                continue
            fails = found.get("fails") if isinstance(found, dict) else None
            if not isinstance(fails, list) or not fails or not all(isinstance(item, str) for item in fails):
                problems.append(f"{label}/meta.json must be an object with \"fails\": a non-empty list of ids")
                continue
            if "why" in found and not _text(found["why"]):
                problems.append(f"{label}/meta.json: why must be a non-empty string")
            problems += [f"{label}/meta.json fails {item!r}, which is not a planted or control id" for item in fails
                         if item not in ids]
            failed |= set(fails)
    problems += [f"{ident} is failed by no reference/bad-*: nothing shows the oracle can fail it" for ident in ids
                 if ident not in failed]
    return problems


def validate(data: Any, scenario_dir: Path) -> list[str]:
    """What is wrong with a scenario, one sentence each (empty when it is valid). `data` is the parsed scenario.json and
    `scenario_dir` its folder, which the rules about ``reference/``, ``repo/`` and a stand-in overlay read."""
    scenario_dir = Path(scenario_dir)
    if not isinstance(data, dict):
        return [f"scenario.json must be an object, not {type(data).__name__}"]
    problems = [f"unknown key {key!r}" for key in data if key not in KEYS]
    if base_stage(data.get("stage")) is None:
        problems.append(f"stage {data.get('stage')!r} is not a stage ({', '.join(stage_spec.STAGES)}) or {IMPROVE}<stage>")
    if not _text(data.get("about")):
        problems.append("about is required: one sentence on the condition the scenario plants")
    if "tags" in data:
        tags = data["tags"]
        if not isinstance(tags, list) or not all(isinstance(tag, str) and TAG.match(tag) for tag in tags):
            problems.append("tags must be a list of words (letters, digits, - and _)")
        elif len(set(tags)) != len(tags):
            problems.append("tags names a tag twice")
    tiers = _tiers(data, problems)
    fixture = data.get("fixture")
    if not _text(fixture) or "/" in fixture or fixture.startswith("."):
        problems.append("fixture is required: a folder name under test/shiploop_e2e/fixtures/")
    elif not (FIXTURES / fixture).is_dir():
        problems.append(f"fixture {fixture!r} is not a folder of test/shiploop_e2e/fixtures/")
    request = data.get("request_from")
    if request is None:
        if "render" in tiers or "live" in tiers:
            problems.append("request_from is required with the render or live tier: a key of step_cases.json")
    elif not isinstance(request, str) or request not in step_cases():
        problems.append(f"request_from {request!r} is not a key of step_cases.json")
    options = data.get("options", {})
    if not isinstance(options, dict):
        problems.append("options must be an object")
    else:
        problems += [f"options: unknown key {key!r}" for key in options if key != "delegation"]
        if "delegation" in options and options["delegation"] not in DELEGATIONS:
            problems.append(f"options.delegation must be one of {', '.join(DELEGATIONS)}")
    records = data.get("seed_records", {})
    if not isinstance(records, dict):
        problems.append("seed_records must be an object of {stage: fields}")
    else:
        for stage, fields in records.items():
            if stage not in stage_spec.STAGES:
                problems.append(f"seed_records: {stage!r} is not a stage")
            elif not isinstance(fields, dict):
                problems.append(f"seed_records.{stage} must be an object")
    if data.get("worktree_mode", "uncommitted") not in WORKTREE_MODES:
        problems.append(f"worktree_mode must be one of {', '.join(WORKTREE_MODES)}")
    ids: dict = {}
    problems += _id_problems(data.get("planted", []), "planted", PLANTED_ID, ("signature",), ids)
    problems += _id_problems(data.get("controls", []), "controls", CONTROL_ID, (), ids)
    for label in ("render", "oracle"):
        problems += [(label + problem[len("checks"):]) if problem.startswith("checks") else f"{label}: {problem}"
                     for problem in stage_oracle.validate_checks(data.get(label, []), ids)]
    oracle = data.get("oracle", [])
    if isinstance(oracle, list):
        proven = {check.get("proves") for check in oracle if isinstance(check, dict)}
        if "verify" in tiers or "live" in tiers:
            problems += [f"{ident} is proven by no check in oracle" for ident in ids if ident not in proven]
        for index, check in enumerate(oracle):
            overlay = check.get("stand_in") if isinstance(check, dict) else None
            if isinstance(overlay, str) and _text(overlay) and not _safe_path(overlay) \
                    and not (scenario_dir / overlay).is_dir():
                problems.append(f"oracle[{index}]: the stand-in folder {overlay!r} is not a folder of the scenario")
    live = data.get("live", {})
    if not isinstance(live, dict):
        problems.append("live must be an object {samples, pass}")
    else:
        problems += [f"live: unknown key {key!r}" for key in live if key not in ("samples", "pass")]
        samples = live.get("samples", 3)
        if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
            problems.append("live.samples must be a positive integer")
        wanted = live.get("pass", "all")
        if wanted != "all" and (isinstance(wanted, bool) or not isinstance(wanted, int) or wanted < 1
                                or (isinstance(samples, int) and not isinstance(samples, bool) and wanted > samples)):
            problems.append('live.pass must be "all" or a number of samples from 1 to live.samples')
    for name in ("repo", "worktree", "notes"):
        if (scenario_dir / name).exists() and not (scenario_dir / name).is_dir():
            problems.append(f"{name} must be a folder")
    base = base_stage(data.get("stage"))
    if base is not None and (scenario_dir / "worktree").is_dir() \
            and stage_spec.STAGES.index(base) <= stage_spec.STAGES.index(NO_WORKTREE_UP_TO):
        problems.append(f"worktree/ is for a stage after {NO_WORKTREE_UP_TO} (what earlier stages left): nothing before "
                        f"implement changes the tree, and the checks run on entry to {NO_WORKTREE_UP_TO} come before the seed "
                        f"point, so put these files in repo/")
    if "verify" in tiers:
        problems += _reference_problems(scenario_dir, ids)
    return problems


# ----------------------------------------------------------------------------------------------------------- discovery

def _sort_key(sc: Scenario) -> tuple:
    """Stage order of stage_spec, scenarios of an Improve stage after every other, then the scenario's name."""
    return (sc.stage.startswith(IMPROVE), stage_spec.STAGES.index(base_stage(sc.stage)), sc.name)


def _read(folder: Path, stage: str) -> tuple[Scenario | None, list[str]]:
    """The scenario in ``folder`` (``<stage>/<name>``) and its problems, each prefixed with its id."""
    ident = f"{stage}/{folder.name}"
    path = folder / "scenario.json"
    if not path.is_file():
        return None, [f"{ident}: scenario.json is missing"]
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        return None, [f"{ident}: scenario.json is not valid JSON: {error}"]
    problems = validate(data, folder)
    if isinstance(data, dict) and data.get("stage") != stage:
        problems.append(f"stage {data.get('stage')!r} differs from its folder {stage!r}")
    if problems:
        return None, [f"{ident}: {problem}" for problem in problems]
    tiers = _tiers(data, [])
    return Scenario(id=ident, stage=stage, name=folder.name, dir=folder, data=data, tiers=tiers,
                    tags=tuple(data.get("tags") or ())), []


def _folders(parent: Path) -> list[Path]:
    return sorted(path for path in parent.iterdir() if path.is_dir() and not path.name.startswith((".", "_")))


def discover(cases_dir: Path | None = None) -> list[Scenario]:
    """Every scenario under `cases_dir` (default SCENARIOS_DIR), sorted by stage order (Improve stages last) and name. Raises
    ScenarioError listing every problem of every scenario; a folder that does not exist holds none."""
    base = Path(cases_dir) if cases_dir is not None else SCENARIOS_DIR
    found: list[Scenario] = []
    problems: list[str] = []
    for stage_folder in _folders(base) if base.is_dir() else []:
        if base_stage(stage_folder.name) is None:
            problems.append(f"{stage_folder.name}: not a stage folder ({', '.join(stage_spec.STAGES)} or {IMPROVE}<stage>)")
            continue
        for folder in _folders(stage_folder):
            scenario, errors = _read(folder, stage_folder.name)
            problems += errors
            if scenario:
                found.append(scenario)
    if problems:
        raise ScenarioError(problems)
    return sorted(found, key=_sort_key)


def load(scenario_id: str, cases_dir: Path | None = None) -> Scenario:
    """The scenario ``<stage>/<name>``; ScenarioError when it is unknown or does not validate."""
    base = Path(cases_dir) if cases_dir is not None else SCENARIOS_DIR
    parts = scenario_id.split("/") if isinstance(scenario_id, str) else []
    if len(parts) != 2 or any(not part or part.startswith(".") or "\0" in part for part in parts):
        raise ScenarioError([f"{scenario_id!r}: a scenario id is <stage>/<name>"])
    folder = base / parts[0] / parts[1]
    if not folder.is_dir():
        raise ScenarioError([f"{scenario_id}: no such scenario under {base}"])
    scenario, problems = _read(folder, parts[0])
    if scenario is None:
        raise ScenarioError(problems)
    return scenario


# ----------------------------------------------------------------------------------------------------------- the trees

def _skipped(name: str) -> bool:
    return name == "__pycache__" or name.endswith(".pyc")


def _lay(source: Path, target: Path) -> None:
    """Lay the files of `source` over `target`: a file replaces what is there (a folder too), a symlink is copied as a link
    and never followed, compiled files and caches are left out."""
    for here, folders, names in os.walk(source):
        folders[:] = sorted(name for name in folders if not _skipped(name))
        folder = target / Path(here).relative_to(source)
        if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
            folder.unlink()
        folder.mkdir(parents=True, exist_ok=True)
        links = [name for name in folders if (Path(here) / name).is_symlink()]
        folders[:] = [name for name in folders if name not in links]
        for name in sorted([*names, *links]):
            if _skipped(name):
                continue
            origin, goal = Path(here) / name, folder / name
            if goal.is_symlink() or goal.is_file():
                goal.unlink()
            elif goal.is_dir():
                shutil.rmtree(goal)
            if origin.is_symlink():
                os.symlink(os.readlink(origin), goal)
            else:
                shutil.copy2(origin, goal)


def _compose(sc: Scenario, into: Path, layers: tuple) -> Path:
    """The scenario's fixture, then each of `layers` (folders of the scenario) over it, in `into`."""
    into = Path(into)
    into.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURES / sc.data["fixture"], into, symlinks=True, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc"))
    for name in layers:
        if (sc.dir / name).is_dir():
            _lay(sc.dir / name, into)
    return into


def compose_seed_tree(sc: Scenario, into: Path) -> Path:
    """The tree a stage starts from, by file composition only (no ShipLoop, no Git): the fixture, then ``repo/``, then
    ``worktree/``. This is what the verify tier checks a reference output against."""
    return _compose(sc, into, ("repo", "worktree"))


def reference_names(sc: Scenario) -> list[str]:
    """The reference outputs the scenario holds: ``good`` first, then each ``bad-<slug>`` in name order."""
    reference = sc.dir / "reference"
    if not reference.is_dir():
        return []
    names = sorted(path.name for path in reference.iterdir() if path.is_dir() and path.name.startswith(REFERENCE_BAD))
    return (["good"] if (reference / "good").is_dir() else []) + names


def reference_bundle(sc: Scenario, name: str, tmp: Path) -> tuple[stage_oracle.Bundle, dict]:
    """The bundle of reference output `name` and its meta ({} for good). The seed tree is composed in ``<tmp>/<name>/seed``; the
    tree is a copy of it with the reference's ``tree/`` laid over it and the paths of its ``deleted.txt`` removed."""
    if name not in reference_names(sc):
        raise ScenarioError([f"{sc.id}: no reference output {name!r}"])
    folder = sc.dir / "reference" / name
    base = Path(tmp) / name
    if base.exists():
        shutil.rmtree(base)
    seed = compose_seed_tree(sc, base / "seed")
    tree = base / "tree"
    shutil.copytree(seed, tree, symlinks=True)
    if (folder / "tree").is_dir():
        _lay(folder / "tree", tree)
    if (folder / "deleted.txt").is_file():
        for line in _deleted(folder / "deleted.txt"):
            target = tree / line
            if _safe_path(line) or not (target.exists() or target.is_symlink()):
                raise ScenarioError([f"{sc.id}: reference/{name}/deleted.txt names {line!r}, which the tree does not hold"])
            shutil.rmtree(target) if target.is_dir() and not target.is_symlink() else target.unlink()
    meta = json.loads((folder / "meta.json").read_text()) if (folder / "meta.json").is_file() else {}
    bundle = stage_oracle.Bundle(result=json.loads((folder / "result.json").read_text()), tree=tree, seed_tree=seed,
                                 issued=True, scenario_dir=sc.dir)
    return bundle, meta


# ------------------------------------------------------------------------------------------------------------- building

# The seed with the engine's seam: the same argv as run.SEED_SCRIPT (the shiploop scripts folder, the run directory, the stop
# stage, the work item and the records as JSON) and one JSON object printed. It records each stage before the stop with the pure
# navigator.apply (and finish_improve when the stage parks at Improve), then hands the whole change to navigator.accept_effects,
# which runs what a real `complete` runs after its gates: the entry effects of the next stage (the checks of validate-existing), the
# item base, the iteration record, the step's commit. Gates are skipped (the results are synthetic), the effects never. It stops
# when the stop stage is current, or when the transition recorded it done by script (validate-existing with every check matching),
# which is found among the history rows the call added, and says so in "settled". A scenario's worktree overlay (the folder in
# STAGE_SUITE_WORKTREE) is laid into the execution checkout just before implement is recorded, else at the end.
SEAM_SEED_SCRIPT = """
import contextlib, io, json, os, shutil, sys, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_lint as lint, shiploop_navigator as nav, shiploop_store as store
run_dir, stop = Path(sys.argv[2]), sys.argv[3]
item = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {"id": "seeded-request", "title": "The whole request"}
records = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}  # {stage: fields merged into that stage's synthetic result}
overlay = os.environ.get("STAGE_SUITE_WORKTREE")  # a folder laid into the execution checkout (what earlier stages left)
core = types.SimpleNamespace(PACKAGE_ROOT=Path(sys.argv[1]).parent)  # read only for the names an Improve stage's files carry
state = store.read_record(run_dir / "state.md")
skipped, settled, laid = [], False, False


def lay():
    global laid
    laid = True
    if overlay:
        shutil.copytree(overlay, state["repo"], symlinks=True, dirs_exist_ok=True)


for _ in range(60):
    stage = nav.current_stage(state)
    if stage == stop:
        break
    action = str(nav.current_action(state)["id"])
    result = {"outcome": "done", "summary": "Synthetic: recorded by the stage suite's seed without doing it; "
              "the request is the specification."}
    result.update(records.get(stage) or {})
    if stage == "plan":
        result["work_items"] = [item]
    if stage == "step-plan":  # one step over the paths and no test commands, unless the scenario's records say otherwise
        result.setdefault("paths", ["src/**"])
        result.setdefault("test_commands", [])
        if not result["test_commands"]:
            result.setdefault("test_commands_na", "Synthetic: the stage suite's seed records no test commands.")
        result.setdefault("follows", [])
        result.setdefault("steps", [{"id": "S1", "task": "Make the planned change.", "paths": list(result["paths"]),
                                     "skills": [], "proof": "true"}])
    if stage == "implement" and not laid:
        lay()
    before = state
    state = nav.apply(before, action, result)
    if state["active_improve"] is not None:
        state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt from the stage suite's seed."})
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):  # what the effects print
        state = nav.accept_effects(core, run_dir, before, state, action_id=action)
    skipped.append(stage)
    if stop in [row["stage"] for row in state["history"][len(before["history"]):]]:
        settled = True
        break
else:
    raise SystemExit("the seed did not reach " + stop)
if not laid:
    lay()
bases = [ident for ident in sorted(state.get("inner_loops") or {}) if lint.read_base(run_dir, ident) is not None]
print(json.dumps({"skipped": skipped, "stage": nav.current_stage(state), "action": str(nav.current_action(state)["id"]),
                  "delegation": state.get("delegation"), "item_bases": bases, "settled": settled}))
"""


@contextlib.contextmanager
def seam_seed(overlay: Path | None = None) -> Iterator[None]:
    """For the duration of the block ``run.seed_run`` seeds through the seam: the module global ``run.SEED_SCRIPT`` is
    SEAM_SEED_SCRIPT, `overlay` is the folder it lays into the execution checkout, the progress observer a printed packet would
    start is off, and the seed child does not put its working directory on its import path. All are restored when the block
    ends, also when it raises. They are the process's, so the block holds SEEDING: a second thread waits for the first."""
    keys = (WORKTREE_ENV, "SHIPLOOP_PROGRESS", "PYTHONSAFEPATH")
    with SEEDING:
        saved_script = run.SEED_SCRIPT
        saved_env = {key: os.environ.get(key) for key in keys}
        run.SEED_SCRIPT = SEAM_SEED_SCRIPT
        os.environ["SHIPLOOP_PROGRESS"] = "off"
        os.environ["PYTHONSAFEPATH"] = "1"
        if overlay is not None:
            os.environ[WORKTREE_ENV] = str(overlay)
        else:
            os.environ.pop(WORKTREE_ENV, None)
        try:
            yield
        finally:
            run.SEED_SCRIPT = saved_script
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _buildable(sc: Scenario) -> dict:
    """The step case a scenario requests, or the reason it cannot be built yet."""
    if sc.stage.startswith(IMPROVE):
        raise NotImplementedError("improve@ scenarios arrive with wave 2")
    if sc.stage in stage_spec.OUTER:
        raise NotImplementedError("outer-stage scenarios arrive with wave 3")
    if sc.data.get("worktree_mode", "uncommitted") != "uncommitted":
        raise NotImplementedError("worktree_mode committed is reserved: only uncommitted is built")
    request = sc.data.get("request_from")
    if request is None:
        raise ScenarioError([f"{sc.id}: request_from is required to build a run"])
    return step_cases()[request]


def build(sc: Scenario, out: Path, *, cli: Path | None = None) -> Built:
    """Build the scenario's run under `out`: the product repository (``out/work``), the run directory and the execution checkout
    (``out/.shiploop-runs/seed/{run,worktree}``, as slice.py lays them out). Only `out` is written. `cli` defaults to this
    checkout's ShipLoop. Every path returned is under `out` resolved: ShipLoop records the execution checkout resolved in
    state.md, so an unresolved `out` (macOS's /var/folders is /private/var/folders) would mix two spellings of one folder."""
    case = _buildable(sc)
    cli = Path(cli) if cli is not None else DEFAULT_CLI
    out = Path(out).resolve()
    if (out / ".shiploop-runs").exists():
        raise FileExistsError(f"{out} already holds a run: build into a new folder")
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    material = out / ".stage-suite"
    if material.exists():
        shutil.rmtree(material)
    fixture = _compose(sc, material / "fixture", ("repo",))
    overlay = sc.dir / "worktree"
    with seam_seed(overlay if overlay.is_dir() else None):
        seeded = run.seed_run(cli, work, out, case["prompt"], sc.stage, fixture=fixture, work_item=case["work_item"],
                              delegation=(sc.data.get("options") or {}).get("delegation", "inline"), checks=case["checks"],
                              records=sc.data.get("seed_records") or None)
    run_dir = Path(seeded["run_dir"])
    state = store.read_record(run_dir / "state.md")
    if (sc.dir / "notes").is_dir():
        _lay(sc.dir / "notes", run_dir / "notes")
    return Built(run_dir=run_dir, worktree=Path(state["repo"]), cli=cli, stage=sc.stage, issued=not seeded["settled"],
                 settled=seeded["settled"], current_stage=seeded["stage"],
                 history_added=[{key: row.get(key) for key in ("stage", "outcome", "action")}
                                for row in state.get("history") or []], seeded=seeded)


def _trace(run_dir: Path) -> list | None:
    """The rows of RUN/trace.jsonl, or None when the run wrote none."""
    path = run_dir / "trace.jsonl"
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        with contextlib.suppress(ValueError):
            rows.append(json.loads(line))
    return rows


def render(sc: Scenario, out: Path, *, cli: Path | None = None) -> stage_oracle.Bundle:
    """Build the scenario, run ``shiploop next`` on its run, and return the bundle the render checks read: ``packet_head`` is
    what `next` printed, ``packet`` the packet file it issued (RUN/packets/<action>.md). A stage the seed settled by script is
    never issued: ``issued`` is False, ``packet`` None, and ``packet_head`` is what `next` printed for the stage the run moved to.
    ``result`` is None; ``tree`` is the execution checkout and ``seed_tree`` a copy of it as the seed left it."""
    built = build(sc, out, cli=cli)
    out = Path(out).resolve()  # as build resolved it
    snapshot = out / ".stage-suite" / "seed-tree"
    if snapshot.exists():
        shutil.rmtree(snapshot)
    shutil.copytree(built.worktree, snapshot, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    quiet = {"SHIPLOOP_PROGRESS": "off", "SHIPLOOP_KEEPALIVE": "off", "PYTHONDONTWRITEBYTECODE": "1",
             "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    done = subprocess.run([sys.executable, str(built.cli), "next", f"--run-dir={built.run_dir}"], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, check=False, timeout=NEXT_SECONDS, env={**os.environ, **quiet})
    if done.returncode:
        raise RuntimeError(f"{sc.id}: shiploop next exited {done.returncode}: {(done.stderr or done.stdout)[-1500:]}")
    packet = None
    if built.issued:
        file = built.run_dir / "packets" / (built.seeded["action"] + ".md")
        if not file.is_file():  # the head is not the packet: a check on one must not quietly read the other
            raise RuntimeError(f"{sc.id}: shiploop next issued no packet file at {file}")
        packet = file.read_text(encoding="utf-8")
    state = store.read_record(built.run_dir / "state.md")
    return stage_oracle.Bundle(result=None, tree=built.worktree, seed_tree=snapshot, run_dir=built.run_dir,
                               trace=_trace(built.run_dir), packet=packet, packet_head=done.stdout, issued=built.issued,
                               settled=built.settled, current_stage=navigator.current_stage(state), scenario_dir=sc.dir)

