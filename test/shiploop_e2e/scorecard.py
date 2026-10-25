#!/usr/bin/env python3
"""One scorecard per E2E run, from the run's own records: the objective of the self-improving loop (P1 of
docs/shiploop-e2e-self-improving-loop-design-2026-10-25.md).

    python3 test/shiploop_e2e/scorecard.py RUN [RUN ...] [--json] [--out FILE]

A RUN is an output folder holding result.json and metrics.json; a folder above run folders is walked to them. Nothing is
written into a run folder and no model is called. Every card carries ``scorecard: SCORECARD_ID``. Two cards are compared
only when their ids are equal, so a change to what a part reads or how a floor is decided takes a new id.

The parts, each read from records the harness already writes:

* ``validity``: was the run clean enough to compare? Resumed, mixed host, a host build that changed, the neighbours it overlapped
  (``environment.overlap``, under the runs root), listeners it left behind, and whether its delivered work tree changed
  after delivery (``git status`` of ``work/``: a check that deleted a product file, as on 2026-10-24, shows here).
  ``comparable`` is false when any of them says no. A record, never a verdict.
* ``accuracy`` (a floor): the verdicts, the checks (a follow-on's include the followed case's and the retention checks),
  the hidden acceptance checks and the mutation ratio where the case declares them.
* ``enterprise`` (a floor): not measured yet. The scripted rubric is P2, so the part says so and decides nothing.
* ``fidelity`` (a floor): the engine ended done, with no unverified entry and no skipped evidence. Edits of script-owned
  files, refusals and retired glossary terms in ShipLoop's replies (``nomenclature``, S-16) are reported beside it; the
  edit list is a heuristic to confirm (SPEC), so it decides nothing. ``improve_reviews`` is left out: on the 2.9.0 runs it
  reads 0 children beside 10 Improve children, a reader that has not followed the Improve route's change.
* ``efficiency`` (the target): minutes, cost, turns, refusals, Improve children, planning minutes and re-orientation
  minutes.

A value nothing measured is null with its reason in ``unmeasured``, never 0. A floor is true, false, or null where its part
was not measured.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import environment  # noqa: E402  (environment.overlap: the one overlap reader)
import metrics  # noqa: E402  (metrics.lower_bound: the one lower-bound rule for cost and turns)

SCORECARD_ID = "scorecard/1"
VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
NOT_YET = "no scripted enterprise rubric yet (design P2)"


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _passed(items) -> dict:
    items = [item for item in items or [] if isinstance(item, dict)]
    return {"passed": sum(1 for item in items if item.get("pass") is True), "total": len(items)}


def work_tree_after(run: Path) -> tuple[list[str] | None, str | None]:
    """The delivered work tree's `git status --porcelain` lines now (empty: clean), or None with the reason."""
    work = run / "work"
    if not (work / ".git").exists():
        return None, "no work/ repository (torn down, or nothing was delivered)"
    done = subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        return None, "git status failed: " + (done.stderr.strip().splitlines() or ["no message"])[0][:160]
    return [line for line in done.stdout.splitlines() if line.strip()], None


def host_builds(result: dict, run_metrics: dict) -> list[str] | None:
    """The distinct host builds the run's launches ran on: Grok and Codex from each launch record's probe, Claude from its
    init events (``claude_code_version``, which names every build its sessions used). None where none was recorded."""
    builds = [entry.get("host_build") for entry in (result.get("environment") or {}).get("environments") or []
              if isinstance(entry, dict) and entry.get("host_build")]
    claude = run_metrics.get("claude_code_version")
    if isinstance(claude, str) and claude:
        builds += [part.strip() for part in claude.split(",") if part.strip()]
    return sorted(set(builds)) or None


def validity(run: Path, result: dict, run_metrics: dict, unmeasured: dict) -> dict:
    environment_block = result.get("environment") or {}
    seen = environment.overlap(run)
    if not seen.get("observed"):
        unmeasured["validity.overlap"] = seen.get("reason")
    left = result.get("left_behind") or {}
    if left.get("observed") is not True:
        unmeasured["validity.left_behind"] = left.get("reason") or "not recorded"
    status, why = work_tree_after(run)
    if why:
        unmeasured["validity.work_tree_after"] = why
    resumed = bool(result.get("resumed_run"))
    mixed = environment_block.get("mixed_host")
    overlapped = len(seen["runs"]) if seen.get("observed") else None
    survived = len(left.get("survived") or []) if left.get("observed") is True else None
    builds = host_builds(result, run_metrics)
    if builds is None:
        unmeasured["validity.host_builds"] = "no launch record or init event names the host build"
    block = {"resumed": resumed, "mixed_host": mixed if isinstance(mixed, bool) else None,
             "host_builds": builds, "overlapped_runs": overlapped, "overlap_root": seen.get("root"),
             "left_behind_survived": survived, "work_tree_after": status}
    # A host build that changed mid-run changes behaviour (inner-loop, 2026-10-25: Grok 1.0.62 to 1.0.70 alone blocked
    # chess run 5's deploy), so its figures are not one build's.
    reasons = [text for text, bad in (("resumed", resumed), ("mixed host", mixed is True),
                                      (f"host build changed: {', '.join(builds or [])}", len(builds or []) > 1),
                                      (f"overlapped {overlapped} run(s)", bool(overlapped)),
                                      (f"{survived} listener(s) survived", bool(survived)),
                                      (f"work tree changed after delivery: {', '.join((status or [])[:3])}", bool(status)))
               if bad]
    block["comparable"] = not reasons
    block["why_not"] = reasons
    return block


def accuracy(result: dict, unmeasured: dict) -> dict:
    quality = result.get("quality") or {}
    acceptance = quality.get("acceptance")
    mutation = quality.get("mutation")
    block = {"pass": result.get("pass") is True,
             "verdicts": {name: (result.get(name) or {}).get("pass") for name in VERDICTS},
             "checks": _passed(result.get("checks")), "acceptance": None, "mutation": None}
    if isinstance(acceptance, dict) and acceptance.get("observed") is True:
        block["acceptance"] = _passed(acceptance.get("checks"))
    else:
        unmeasured["accuracy.acceptance"] = ((acceptance or {}).get("reason") if isinstance(acceptance, dict)
                                             else "the case declares no hidden acceptance checks")
    if isinstance(mutation, dict) and mutation.get("observed") is True:
        block["mutation"] = {"ratio": mutation.get("ratio"), "operator_id": mutation.get("operator_id")}
    else:
        unmeasured["accuracy.mutation"] = ((mutation or {}).get("reason") if isinstance(mutation, dict)
                                           else "the case declares no mutation measure")
    hidden = block["acceptance"]
    block["floor"] = block["pass"] and (hidden is None or hidden["passed"] == hidden["total"])
    return block


def fidelity(run_metrics: dict, unmeasured: dict) -> dict:
    record = run_metrics.get("fidelity") or {}
    if not record:
        unmeasured["fidelity"] = "metrics.json has no fidelity block"
        return {"floor": None}
    end = record.get("end_state") or {}
    unverified = (end.get("unverified") or {}).get("entries")
    skipped = ((record.get("evidence") or {}).get("counts") or {}).get("skipped")
    edits = (record.get("edits") or {}).get("script_owned")
    refusals = record.get("refusals") or {}
    # The edit list is a heuristic the SPEC calls a list to confirm, not a count to trust, so it is reported and never
    # decides the floor: an Improve stage's own investigation file can land in it.
    block = {"end_status": end.get("status"), "unverified": unverified, "skipped_evidence": skipped,
             "script_owned_edits_to_confirm": len(edits) if isinstance(edits, list) else edits,
             "refusals": refusals.get("count"), "repeated_refusals": refusals.get("repeated"),
             "retired_terms": None}
    nomenclature = run_metrics.get("nomenclature")
    if isinstance(nomenclature, dict) and isinstance(nomenclature.get("retired"), dict):
        # Each retired term carries the number of ShipLoop texts (replies, refusal first lines) it appeared in.
        block["retired_terms"] = sum(int(hit.get("texts") or 0) for hit in nomenclature["retired"].values() if isinstance(hit, dict))
    else:
        unmeasured["fidelity.retired_terms"] = "metrics.json has no nomenclature record (it predates 2026-10-24)"
    missing = [name for name in ("unverified", "skipped_evidence") if block[name] is None]
    for name in missing:
        unmeasured[f"fidelity.{name}"] = "the fidelity block does not carry it"
    block["floor"] = (None if missing or end.get("status") is None else
                      end.get("status") == "done" and unverified == 0 and skipped == 0)
    return block


def efficiency(run_metrics: dict, unmeasured: dict) -> dict:
    span = run_metrics.get("span") or {}
    minutes = (round((span["ended"] - span["started"]) / 60, 1)
               if isinstance(span.get("started"), (int, float)) and isinstance(span.get("ended"), (int, float)) else None)
    window = (run_metrics.get("planning") or {}).get("window") or {}
    planning = round(window["seconds"] / 60, 1) if window.get("closed") and isinstance(window.get("seconds"), (int, float)) else None
    starts = run_metrics.get("fresh_starts")
    measured = ([s["reorientation"] for s in starts if isinstance(s, dict) and isinstance(s.get("reorientation"), dict)
                 and s["reorientation"].get("measured") is True and isinstance(s["reorientation"].get("seconds"), (int, float))]
                if isinstance(starts, list) else None)
    reorientation = round(sum(r["seconds"] for r in measured) / 60, 1) if measured is not None else None
    if isinstance(starts, list) and len(measured) < len(starts):
        unmeasured["efficiency.reorientation_minutes"] = (f"{len(starts) - len(measured)} of {len(starts)} fresh starts "
                                                          "have no measured re-orientation: a lower bound")
    block = {"minutes": minutes, "cost_usd": run_metrics.get("cost_usd"),
             "cost_lower_bound": metrics.lower_bound(run_metrics), "turns": run_metrics.get("turns"),
             "refusals": len(run_metrics["shiploop_failures"]) if isinstance(run_metrics.get("shiploop_failures"), list) else None,
             "improve_children": run_metrics.get("improve_children"), "planning_minutes": planning,
             "reorientation_minutes": reorientation}
    reasons = {"minutes": "the run's stream has no readable span", "cost_usd": "the host reports no cost",
               "turns": "the host reports no turns", "planning_minutes": "the planning window did not close",
               "reorientation_minutes": (run_metrics.get("fresh_starts_unmeasured") or "no fresh-start record")}
    for name, reason in reasons.items():
        if block[name] is None:
            unmeasured.setdefault(f"efficiency.{name}", reason)
    return block


def score(run) -> dict:
    """The scorecard of one run folder; a folder without readable records gives a card that says so."""
    run = Path(run)
    result, run_metrics = _read(run / "result.json"), _read(run / "metrics.json")
    if result is None:
        return {"scorecard": SCORECARD_ID, "run": str(run), "observed": False, "reason": "no readable result.json"}
    run_metrics = run_metrics or result.get("metrics") or {}
    unmeasured: dict[str, str] = {}
    versions = result.get("versions") or {}
    card = {"scorecard": SCORECARD_ID, "run": str(run), "observed": True, "case": result.get("case"),
            "driver": {k: result.get(k) for k in ("host", "model", "effort")},
            "versions": {"source": str(versions["source"]).split(" (")[0] if versions.get("source") else None,
                         "plugin_version": versions.get("plugin_version"), "shiploop_version": versions.get("shiploop_version")},
            "outcome_class": result.get("outcome_class"),
            "validity": validity(run, result, run_metrics, unmeasured), "accuracy": accuracy(result, unmeasured),
            "enterprise": {"observed": False, "reason": NOT_YET, "floor": None},
            "fidelity": fidelity(run_metrics, unmeasured), "efficiency": efficiency(run_metrics, unmeasured)}
    card["floors"] = {name: card[name]["floor"] for name in ("accuracy", "enterprise", "fidelity")}
    card["unmeasured"] = unmeasured
    return card


def run_folders(paths) -> list[Path]:
    """The run folders named, or found under a folder named (a folder holding result.json; the walk stops there)."""
    found = []
    for path in map(Path, paths):
        if (path / "result.json").is_file():
            found.append(path)
            continue
        found += [folder for folder in environment.run_folders(path) if (folder / "result.json").is_file()]
    return sorted(dict.fromkeys(found))


def _cell(value, unit: str = "") -> str:
    return "-" if value is None else f"{value}{unit}"


def render(cards: list[dict]) -> str:
    """One line per run: floors, then the target's main figures, then why a run is not comparable."""
    lines = [f"{SCORECARD_ID}: {len(cards)} run(s); floors accuracy/enterprise/fidelity (Y yes, n no, - not measured)"]
    mark = {True: "Y", False: "n", None: "-"}
    for card in cards:
        name = Path(card["run"]).name if Path(card["run"]).name not in ("", ".") else card["run"]
        if not card.get("observed"):
            lines.append(f"  {name:<34} {card['reason']}")
            continue
        floors = "/".join(mark[card["floors"][k]] for k in ("accuracy", "enterprise", "fidelity"))
        e, v = card["efficiency"], card["validity"]
        driver = card["driver"].get("host") or "?"
        cost = _cell(e["cost_usd"]) if not e["cost_lower_bound"] or e["cost_usd"] is None else f"{e['cost_usd']}+"
        lines.append(f"  {(card['case'] or '?') + ' ' + driver:<26} {floors}  {_cell(e['minutes'], 'm'):>7} ${cost:<8} "
                     f"{_cell(e['turns']):>4}t {_cell(e['refusals']):>3}r plan {_cell(e['planning_minutes'], 'm'):>6}  "
                     + ("comparable" if v["comparable"] else "not comparable: " + "; ".join(v["why_not"])))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("runs", nargs="+", help="run folders, or folders above them")
    parser.add_argument("--json", action="store_true", help="print the cards as JSON")
    parser.add_argument("--out", type=Path, help="also write the cards as JSON to this file (never inside a run folder)")
    args = parser.parse_args(argv)
    folders = run_folders(args.runs)
    if args.out and any(args.out.resolve().is_relative_to(folder.resolve()) for folder in folders):
        raise SystemExit("--out names a file inside a run folder; a scorecard never writes there")
    cards = [score(folder) for folder in folders]
    if args.out:
        args.out.write_text(json.dumps({"scorecard": SCORECARD_ID, "cards": cards}, indent=1) + "\n")
    print(json.dumps({"scorecard": SCORECARD_ID, "cards": cards}, indent=1) if args.json else render(cards), end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
