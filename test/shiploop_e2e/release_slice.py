"""The release slice: a ShipLoop run that starts at its release stages with an already-built product.

`run.py --seed-at release-plan` (or `system-test-author`) records every stage before the seed point as done without doing it, as
`--seed-at step-plan` does, and also hands the run a product: the case's prebuilt project is committed in the run's worktree as the
delivered candidate of its only work item, and the knowledge home the outer stages read (HOME/spec.md, architecture.md,
environment.md) is the case's own, committed before the run's baseline. The host then plans, checks, performs and verifies the
release with ShipLoop's own packets, so a run costs minutes of the platform and none of the build.

Nothing here knows a platform. A case opts in with these keys in cases.json:

  seed_product   a folder under test/shiploop_e2e/fixtures/: the built project
  seed_home      a folder under fixtures/: spec.md, environment.md and architecture.md (copied to docs/shiploop) and records.json
                 (not copied): the work item, and the fields to merge into the synthetic result of a stage the seed records
  seed_release   {"source_checks": [words], "product_exclude": [names], "operation": {"name", "stage", "log", "argv"}, "source": why}
                 source_checks are words of the case's own checks that read the source checkout (they run only once the product has
                 been returned to it); product_exclude names top-level entries of the product folder that are the fixture's own
                 (its README) and so are never committed into the run; operation is the platform change whose timing the release
                 verdict reads: every allowed call of the guard log (`log`, relative to the run's output folder) whose argv starts
                 with `argv` must fall in the window of `stage` (after the stage before it was accepted, until it was), and at
                 least one must have exited 0

``grade`` reads what the run left (ShipLoop's state, its timeline and the guard log) and answers: which of the stages from the seed
point on ShipLoop accepted, where it stopped and why if it did, and whether the platform change happened in the stage that owns it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

FIXTURES = HERE / "fixtures"
RECORDS = "records.json"
# The seed points that deliver a product: every INNER stage is done, so the item is built and the OUTER stages remain.
DELIVERED = tuple(stage for stage in ("system-test-author", "release-plan") if stage in stage_spec.OUTER)


def delivered(stage: str | None) -> bool:
    """Whether a seed at ``stage`` starts a release slice (the item is delivered) and not an inner-loop slice."""
    return stage in DELIVERED


def graded_stages(stage: str) -> tuple[str, ...]:
    """The outer stages ShipLoop must accept in a run seeded at ``stage``: that stage and every later one."""
    return tuple(stage_spec.OUTER[stage_spec.OUTER.index(stage):])


# ------------------------------------------------------------------------------------------------------- the case's keys

def _fixture(name: object, label: str, problems: list[str]) -> Path | None:
    if not (isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)):
        problems.append(f"{label} must be the name of a folder under test/shiploop_e2e/fixtures/")
        return None
    folder = FIXTURES / name
    if not folder.is_dir():
        problems.append(f"{label} {name!r} is not a folder under test/shiploop_e2e/fixtures/")
        return None
    return folder


def validate_case(name: str, case: dict) -> list[str]:
    """What is wrong with the case's seed_product, seed_home and seed_release keys (empty: nothing). A case that has none of
    them has nothing to validate; a case that has one needs all three."""
    keys = ("seed_product", "seed_home", "seed_release")
    if not any(key in case for key in keys):
        return []
    problems = [f"{key} is missing" for key in keys if key not in case]
    product = _fixture(case.get("seed_product"), "seed_product", problems) if "seed_product" in case else None
    home = _fixture(case.get("seed_home"), "seed_home", problems) if "seed_home" in case else None
    if home is not None:
        problems += [f"seed_home has no {file}" for file in (*knowledge_home.LIVING, RECORDS) if not (home / file).is_file()]
        if (home / RECORDS).is_file():
            try:
                records = json.loads((home / RECORDS).read_text())
            except ValueError as exc:
                records = None
                problems.append(f"seed_home {RECORDS} is not JSON ({exc})")
            if records is not None:
                item = records.get("work_item") if isinstance(records, dict) else None
                if not (isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("title"), str)):
                    problems.append(f"seed_home {RECORDS} needs a work_item with an id and a title")
                results = records.get("results", {}) if isinstance(records, dict) else None
                if not (isinstance(results, dict) and all(isinstance(key, str) and isinstance(value, dict)
                                                          for key, value in results.items())):
                    problems.append(f"seed_home {RECORDS} results must map stage names to objects")
                else:
                    problems += [f"seed_home {RECORDS} results names {key!r}, which is not a stage"
                                 for key in results if key not in stage_spec.STAGES]
    release = case.get("seed_release")
    if "seed_release" in case:
        if not isinstance(release, dict):
            problems.append("seed_release must be an object")
        else:
            for key in ("source_checks", "product_exclude"):
                value = release.get(key, [])
                if not (isinstance(value, list) and all(isinstance(word, str) and word.strip() for word in value)):
                    problems.append(f"seed_release {key} must be a list of non-empty strings")
            if product is not None:
                problems += [f"seed_release product_exclude names {entry!r}, which is not in the product folder"
                             for entry in release.get("product_exclude", []) if isinstance(entry, str) and not (product / entry).exists()]
            checks = [str(check) for check in case.get("checks", [])]
            problems += [f"seed_release source_checks names {word!r}, which is no word of any of the case's checks"
                         for word in release.get("source_checks", []) if isinstance(word, str)
                         and not any(word in check.split() for check in checks)]
            operation = release.get("operation")
            if operation is not None:
                if not (isinstance(operation, dict) and set(operation) == {"name", "stage", "log", "argv"}
                        and all(isinstance(operation[key], str) and operation[key].strip() for key in ("name", "stage", "log"))
                        and isinstance(operation["argv"], list) and operation["argv"]
                        and all(isinstance(word, str) and word for word in operation["argv"])):
                    problems.append("seed_release operation is {name, stage, log, argv}: three non-empty strings and a non-empty list of words")
                elif operation["stage"] not in stage_spec.OUTER or stage_spec.OUTER.index(operation["stage"]) == 0:
                    problems.append("seed_release operation stage must be an OUTER stage that another OUTER stage precedes")
                elif Path(operation["log"]).is_absolute() or ".." in Path(operation["log"]).parts:
                    problems.append("seed_release operation log is a path relative to the run's output folder")
    return [f"case {name!r}: {problem}" for problem in problems]


def materials(name: str, case: dict, stage: str) -> dict:
    """What a seed at ``stage`` takes from the case: ``product`` and ``home_fixture`` (folders), ``work_item``, ``records`` (by
    stage) and ``exclude`` (product entries never committed). A SystemExit names what the case lacks."""
    if not any(key in case for key in ("seed_product", "seed_home", "seed_release")):
        raise SystemExit(f"--seed-at {stage} starts at a stage that comes after the build, so the case needs a built product: "
                         f"case {name!r} has no seed_product, seed_home and seed_release in cases.json")
    problems = validate_case(name, case)
    if problems:
        raise SystemExit("; ".join(problems))
    home = FIXTURES / case["seed_home"]
    records = json.loads((home / RECORDS).read_text())
    return {"product": FIXTURES / case["seed_product"], "home_fixture": home, "work_item": records["work_item"],
            "records": records.get("results", {}), "exclude": list(case["seed_release"].get("product_exclude", []))}


def release_spec(case: dict) -> dict:
    """The case's seed_release object ({} for a case without one)."""
    spec = case.get("seed_release")
    return spec if isinstance(spec, dict) else {}


# ------------------------------------------------------------------------------------------------------------ the product

def copy_home(work: Path, home_fixture: Path) -> list[str]:
    """Copy the three living files of ``home_fixture`` to ``work``/docs/shiploop (a file already there is kept); the paths written,
    relative to ``work``. records.json stays behind: it is the seed's, not the repository's."""
    written = []
    for name in knowledge_home.LIVING:
        target = work / knowledge_home.HOME / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(home_fixture / name, target)
            written.append(f"{knowledge_home.HOME}/{name}")
    return written


def product_files(product: Path, exclude: list[str]) -> list[str]:
    """The files of the product folder, as paths relative to it, without the excluded top-level entries and what is under them."""
    skip = set(exclude)
    return sorted(str(path.relative_to(product)) for path in product.rglob("*")
                  if path.is_file() and path.relative_to(product).parts[0] not in skip)


def commit_product(worktree: Path, product: Path, exclude: list[str], item: dict, env: dict, identity: list[str]) -> dict:
    """Copy the built product into the run's worktree and commit it, by explicit path, as the work item's delivered candidate."""
    files = product_files(product, exclude)
    if not files:
        raise SystemExit(f"seed: the product folder {product} holds no file to commit")
    for relative in files:
        target = worktree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(product / relative, target)
    git = ["git", "-C", str(worktree)]
    subprocess.run([*git, "add", "-f", "--", *files], check=True, capture_output=True, text=True, env=env)
    subprocess.run([*git, *identity, "commit", "-q", "-m", f"feat: {item['id']} {item['title']}", "-m",
                    f"The built product ({product.name}), committed by the E2E release-slice seed as the item's delivered "
                    "candidate. The item's stages were recorded without doing them."],
                   check=True, capture_output=True, text=True, env=env)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=env).stdout.strip()
    return {"fixture": product.name, "commit": head, "files": len(files)}


def returned(work: Path, product: Path, exclude: list[str]) -> bool:
    """Whether the source checkout holds the product: any file of the product folder (but the excluded ones) is there, committed or
    not. The return puts them all there at once; before that the source holds only what the run started from, which the product's
    files are not part of. One file is enough, so a model that dropped one of them cannot make a check of the source look unrun."""
    return any((work / relative).exists() for relative in product_files(product, exclude))


def split_checks(checks: list[str], words: list[str], work: Path, product: Path, exclude: list[str]) -> tuple[list[str], list[dict]]:
    """(the checks to run, the checks left out with their reason). A check that holds one of ``words`` reads the source checkout and
    is left out while the product has not been returned to it, which says nothing about the delivery."""
    if not words or returned(work, product, exclude):
        return list(checks), []
    entries = ", ".join(sorted({Path(relative).parts[0] for relative in product_files(product, exclude)}))
    run, left = [], []
    for check in checks:
        if any(word in str(check).split() for word in words):
            left.append({"command": check, "reason": f"the product has not been returned to the source checkout ({entries} absent), so "
                                                     "a check of the source has nothing to read"})
        else:
            run.append(check)
    return run, left


# --------------------------------------------------------------------------------------------------------------- grading

LOG_TIME = "%Y-%m-%dT%H:%M:%S%z"


def _epoch(text: object) -> float | None:
    try:
        return datetime.strptime(str(text), LOG_TIME).timestamp()
    except ValueError:
        return None


def operation_calls(log: Path, argv: list[str], skip: list[tuple[int, int]] = ()) -> list[dict]:
    """The allowed calls of the guard log whose argv starts with ``argv``, in log order, outside the harness's own preflights
    (``skip``: [from, to) line ranges). Each is {"line", "ts", "t", "call", "exit"}; ``t`` is None for a time that cannot be read,
    ``exit`` the exit code of the call's end line (None where it has none: the call was cut off). A denied call changed nothing
    and a line with an `end` key is the end of a call, so neither counts as a call of its own."""
    found, ends = [], {}
    try:
        lines = log.read_text(errors="replace").splitlines()
    except OSError:
        return found
    for number, line in enumerate(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("end"):
            ends[record.get("call")] = record.get("exit")
        elif (not any(first <= number < last for first, last in skip) and record.get("decision") == "allowed"
              and record.get("name", "sf") == "sf" and isinstance(record.get("argv"), list)
              and record["argv"][:len(argv)] == argv):
            found.append({"line": number, "ts": record.get("ts"), "t": _epoch(record.get("ts")), "call": record.get("call")})
    for call in found:
        call["exit"] = ends.get(call["call"])
    return found


def _accepted(rows: list[dict], stage: str) -> dict | None:
    """The newest accepted (done) row of a stage, or None."""
    done = [row for row in rows if row["stage"] == stage and row["outcome"] == "done"]
    return done[-1] if done else None


def operation_verdict(spec: dict, rows: list[dict], calls: list[dict]) -> dict:
    """Did the platform change happen in the stage that owns it? The window is from the acceptance of the stage before ``stage`` to
    the acceptance of ``stage`` itself (open-ended while it is not accepted); stamps and log times are whole seconds, so the ends
    belong to the window. Every call must be in it, and at least one of them must have succeeded (exit 0): a failed deploy over
    a platform that already holds the product (update mode) would otherwise hide behind the checks that find the earlier one."""
    stage, before = spec["stage"], stage_spec.OUTER[stage_spec.OUTER.index(spec["stage"]) - 1]
    start, end = _accepted(rows, before), _accepted(rows, stage)
    start_t, end_t = (start or {}).get("t"), (end or {}).get("t")
    placed = []
    for call in calls:
        t = call["t"]
        if start is None:
            where = "before"  # the stage before was never accepted, so nothing can be in this stage's window
        elif t is None or start_t is None or (end is not None and end_t is None):
            where = "unknown"
        else:
            where = "before" if t < start_t else "after" if end is not None and t > end_t else "in"
        placed.append({"ts": call["ts"], "call": call["call"], "at": where, "exit": call.get("exit")})
    counts = {key: sum(1 for item in placed if item["at"] == key) for key in ("before", "in", "after", "unknown")}
    worked = sum(1 for item in placed if item["at"] == "in" and item["exit"] == 0)
    if not placed:
        pass_, why = False, f"the guard log holds no allowed {spec['name']} ({' '.join(spec['argv'])})"
    elif counts["before"] or counts["after"] or counts["unknown"]:
        bits = [f"{counts[key]} {label}" for key, label in (("before", f"before {before} was accepted"),
                                                              ("after", f"after {stage} was accepted"),
                                                              ("unknown", "at a time that cannot be read")) if counts[key]]
        pass_, why = False, f"{spec['name']} outside the {stage} stage: " + ", ".join(bits) + f" (of {len(placed)})"
    elif not worked:
        codes = ", ".join("no end line" if item["exit"] is None else f"exit {item['exit']}" for item in placed)
        pass_, why = False, f"no {spec['name']} succeeded in the {stage} stage ({len(placed)} call(s): {codes})"
    else:
        pass_, why = True, (f"{len(placed)} {spec['name']} call(s), all inside the {stage} stage, {worked} exit 0")
    return {"pass": pass_, "name": spec["name"], "stage": stage, "after": before, "reason": why, "calls": placed,
            "window": {"after_t": start_t, "until_t": end_t}}


def grade(*, seeded: dict, run_dir: Path | None, state: dict, out: Path, case: dict, skipped_checks: list[dict],
          preflights: list[tuple[int, int]] = ()) -> dict:
    """The release slice's verdict: ``pass`` when ShipLoop accepted every stage from the seed point on and the case's platform
    change (if it declares one) happened in its own stage. ``stages`` has one row per graded stage ({stage, accepted, outcome, t});
    ``stopped`` says where the run ended and why when it did not accept them all."""
    start = seeded["stage"]
    # The seed stops before its own stage, so no row of a graded stage is the seed's: the history needs no cutting.
    rows = metrics.stage_results(run_dir, state)
    stages = []
    for stage in graded_stages(start):
        row = _accepted(rows, stage)
        stages.append({"stage": stage, "accepted": row is not None, "outcome": "done" if row else None, "t": (row or {}).get("t")})
    missing = next((row["stage"] for row in stages if not row["accepted"]), None)
    stopped = None
    if missing is not None:
        status = state.get("status")
        position = metrics.current_stage(state)
        reason = (str(state.get("status_reason") or "").strip() or None) if status == "blocked" else None
        stopped = {"stage": missing, "engine_status": status, "engine_stage": position,
                   "reason": reason or (f"ShipLoop was {status or 'unknown'} at {position}, so {missing} was not accepted"
                                        if status != "done" else f"ShipLoop is done but never accepted {missing}")}
    operation = release_spec(case).get("operation")
    verdict = None
    if operation:
        verdict = operation_verdict(operation, rows, operation_calls(out / operation["log"], operation["argv"], list(preflights)))
    ok = missing is None and (verdict is None or verdict["pass"])
    return {"pass": ok, "from": start, "stages": stages, "stopped": stopped, **({"operation": verdict} if verdict else {}),
            "skipped_checks": skipped_checks, "source": release_spec(case).get("source")}


def lines(release: dict) -> list[str]:
    """The report lines of a release slice verdict, one per fact."""
    out = []
    accepted = [row["stage"] for row in release["stages"] if row["accepted"]]
    out.append(f"{len(accepted)}/{len(release['stages'])} stages accepted from {release['from']}: "
               + (", ".join(accepted) or "none"))
    if release["stopped"]:
        out.append(f"stopped at {release['stopped']['stage']}: {release['stopped']['reason']}")
    if release.get("operation"):
        out.append(f"{release['operation']['name']}: {release['operation']['reason']}")
    for left in release["skipped_checks"]:
        out.append(f"left out: {left['command']} ({left['reason']})")
    return out
