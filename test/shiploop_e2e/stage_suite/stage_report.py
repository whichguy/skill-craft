#!/usr/bin/env python3
"""The stage suite's live report (docs/plans/shiploop-stage-suite.md, "Runner and selectors"): read a results root, render the
matrix of catch rates, and compare two roots. Files only: no host, no ShipLoop, no scenario folder.

A results root holds one folder per sample, ``<root>/<stage>/<scenario>/<n>/``, as ``stage_live.run_sample`` leaves it, and
``live-plan.json`` (``PLAN``), which ``stages.py live`` writes before it starts anything: the samples it planned per scenario
and the pass rule. A root made by hand, with no plan, reports what is on disk.

A sample is **graded** when its ``stage-result.json`` is there, whole and well-formed. Every other sample is **not run**: a
folder with no result (the host never started, the sample crashed or timed out, ``error.txt`` says why when it could), a result
that is half written (``stage-result.json.partial``) or malformed, and a sample the plan named whose folder is missing. A sample
that was not run counts in the denominator and never in a numerator: it is not a pass, not a catch and not a hold.

The matrix has a row per scenario and the columns

    ran         graded samples / samples
    P1 ... C2   the planted ids caught and the controls held, k/n (n counts the samples not run)
    overshoot   graded samples whose host accepted a stage after the seeded one, k/n (``-`` when no sample was graded)
    pass        samples that passed (every verdict true, every id caught or held), k/n
    rule        met / NOT MET against the scenario's ``live.pass`` rule, from the plan (``-`` without a plan)
    driver      host[:backend]/model/effort of the graded samples

A cell for an id the scenario does not have is ``-``. The plan's planted and control ids give the cells of a scenario none of whose
samples was graded (each reads 0/n), so its row keeps its id columns. The JSON row's ``value`` is the mean of the samples' ``value`` with a
sample not run counting 0; ``builds`` lists the plugin builds (ref, overlay, head, versions) of the graded samples, and a root with
more than one carries a note: results of different builds are shown together, never refused (comparing refs is what ``compare``
is for). A result that checked no id, lacks an id the plan names or has a ``value`` outside 0-1 is not run. A folder whose name
is not a sample number as ``str(int(n))`` (``01``, a non-ASCII digit, ``x``) is not a sample: it is listed as ``ignored``.
``compare(root_a, root_b)`` refuses roots whose drivers differ (SPEC S-12:
results of different hosts, backends, models or efforts are different baselines and are never compared), naming both; otherwise
it gives, per cell, both counts and the change in rate (a minus b). Standard library only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PLAN = "live-plan.json"
RESULT = "stage-result.json"
ERROR = "error.txt"
VERDICTS = ("process", "accepted", "no_overshoot", "oracle")
ID = re.compile(r"^([PC])([0-9]+)$")
DRIVER_KEYS = ("host", "backend", "model", "effort")


class ReportError(ValueError):
    """A results root that cannot be reported on; the message says why."""


class DriverMismatch(ReportError):
    """Two roots that ran on different drivers; the message names both."""


# ------------------------------------------------------------------------------------------------------------------ reading

def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _flags(value: Any) -> dict | None:
    """``value`` as a dict of id -> bool, or None when it is not one."""
    if isinstance(value, dict) and all(isinstance(key, str) and isinstance(item, bool) for key, item in value.items()):
        return value
    return None


def _graded(document: Any) -> str | None:
    """Why ``document`` (a parsed stage-result.json) is not a result the report can count, or None when it is."""
    if not isinstance(document, dict):
        return "stage-result.json cannot be parsed or is not an object"
    verdicts = document.get("verdicts")
    if not isinstance(verdicts, dict) or any(not isinstance(verdicts.get(name), bool) for name in VERDICTS):
        return "stage-result.json has no verdicts"
    caught, held = _flags(document.get("caught")), _flags(document.get("held"))
    if caught is None or held is None:
        return "stage-result.json has no caught and held"
    if not caught and not held:
        return "stage-result.json checked no planted or control id"
    value = document.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        return "stage-result.json has no value between 0 and 1"
    if not isinstance(document.get("pass"), bool):
        return "stage-result.json has no pass"
    return None


def _why(sample: Path) -> str:
    """Why a sample folder holds no result: what error.txt says, else what is missing."""
    note = ""
    try:
        note = " ".join((sample / ERROR).read_text().split())[:300]
    except OSError:
        pass
    if (sample / (RESULT + ".partial")).exists():
        return "stage-result.json was half written" + (f" ({note})" if note else "")
    if note:
        return note
    return f"no {RESULT}"


def read_sample(sample: Path, planned: dict | None = None) -> dict:
    """One sample folder: ``{"graded": True, "result": {...}}`` or ``{"graded": False, "reason": ...}``. ``planned`` is the plan's
    entry for the scenario: a result that lacks an id the plan names is not a result of that scenario's checks."""
    if not (sample / RESULT).is_file():
        return {"graded": False, "reason": _why(sample)}
    document = _json(sample / RESULT)
    if (problem := _graded(document)) is not None:
        return {"graded": False, "reason": problem}
    lacking = [ident for ident in (*(planned or {}).get("planted", []), *(planned or {}).get("controls", []))
               if ident not in document["caught"] and ident not in document["held"]]
    if lacking:
        return {"graded": False, "reason": f"stage-result.json lacks the planned id{'s' if len(lacking) != 1 else ''} {', '.join(lacking)}"}
    return {"graded": True, "result": document}


def _folders(parent: Path) -> list[Path]:
    try:
        return sorted(path for path in parent.iterdir() if path.is_dir() and not path.name.startswith("."))
    except OSError:
        return []


def _id_order(ident: str) -> tuple:
    found = ID.match(ident)
    return (0 if found and found.group(1) == "P" else 1, int(found.group(2)) if found else 0, ident)


def driver_of(result: dict) -> tuple:
    return tuple(result.get(key) for key in DRIVER_KEYS)


def build_of(result: dict) -> str:
    """Which plugin a result ran: ``ref``, ``overlay``, the checkout's head and the plugin and ShipLoop versions it recorded, as
    one label (an absent field reads ``-``). Two results with different labels are different builds of the plugin."""
    versions = result.get("versions") if isinstance(result.get("versions"), dict) else {}
    head = result.get("local_head")
    overlay = result.get("overlay")
    return (f"ref {result.get('ref') or '-'}, overlay {json.dumps(overlay, sort_keys=True) if overlay else '-'}, "
            f"head {head[:12] if isinstance(head, str) and head else '-'}, plugin {versions.get('plugin_version') or '-'} "
            f"{versions.get('plugin_sha256') or '-'}, shiploop {versions.get('shiploop_version') or '-'}")


def driver_label(driver: tuple) -> str:
    """``host[:backend]/model/effort`` of a driver tuple (host, backend, model, effort); an unset effort reads ``default``."""
    host, backend, model, effort = driver
    return f"{host}{':' + backend if backend else ''}/{model or 'default'}/{effort or 'default'}"


def _scenario(identifier: str, folder: Path | None, planned: dict | None) -> dict:
    """The summary of one scenario: its samples (the folders there are, and the ones the plan names that are missing)."""
    found, ignored = {}, []
    if folder is not None:
        for path in _folders(folder):
            if path.name.isascii() and path.name.isdigit() and path.name == str(int(path.name)) and int(path.name) > 0:
                found[int(path.name)] = read_sample(path, planned)
            else:  # '01' would be sample 1 twice, and a name that is no number is no sample: neither is counted, both are shown
                ignored.append(path.name)
    numbers = sorted(set(found) | set(range(1, (planned or {}).get("samples", 0) + 1)))
    count = len(numbers)
    graded = {number: found[number]["result"] for number in numbers if number in found and found[number]["graded"]}
    not_run = [{"sample": number, "reason": found[number]["reason"] if number in found else "no sample folder"}
               for number in numbers if number not in graded]
    ids: dict[str, dict] = {}
    for ident in (*(planned or {}).get("planted", []), *(planned or {}).get("controls", [])):
        if isinstance(ident, str):  # the plan names the ids, so a scenario that graded nothing still has its cells (0/n)
            ids.setdefault(ident, {"kind": "caught" if ident.startswith("P") else "held", "k": 0, "n": count})
    for result in graded.values():
        for ident in (*result["caught"], *result["held"]):
            ids.setdefault(ident, {"kind": "caught" if ident.startswith("P") else "held", "k": 0, "n": count})
    for result in graded.values():
        for ident, value in {**result["caught"], **result["held"]}.items():
            ids[ident]["k"] += 1 if value else 0
    passes = sum(1 for result in graded.values() if passed(result))
    builds = sorted({build_of(result) for result in graded.values()})
    drivers = sorted({driver_of(result) for result in graded.values()}, key=lambda row: tuple(str(item) for item in row))
    stage, _, name = identifier.partition("/")
    row = {"id": identifier, "stage": stage, "scenario": name, "samples": count, "ran": len(graded), "not_run": not_run,
           "ids": dict(sorted(ids.items(), key=lambda item: _id_order(item[0]))),
           "overshoot": ({"k": sum(1 for result in graded.values() if not result["verdicts"]["no_overshoot"]), "n": count}
                         if graded else None),  # nothing graded, nothing counted: not 0/n
           "pass": {"k": passes, "n": count},
           "value": (sum(result["value"] for result in graded.values()) / count) if count else None,
           "builds": builds, "ignored": ignored,
           "drivers": [driver_label(driver) for driver in drivers], "driver_keys": [list(driver) for driver in drivers],
           "rule": None}
    if planned and isinstance(planned.get("required"), int) and not isinstance(planned["required"], bool):
        row["rule"] = {"required": planned["required"], "met": passes >= planned["required"]}
    return row


def passed(result: dict) -> bool:
    """A graded sample passed: its own pass flag AND every verdict, every caught id and every held id. A document that claims a
    pass its fields do not show is not one."""
    return (result["pass"] and all(result["verdicts"][name] for name in VERDICTS)
            and all(result["caught"].values()) and all(result["held"].values()))


def read_root(root: Path) -> dict:
    """The report of the results root ``root``: ``root``, ``plan`` (live-plan.json or None), ``drivers`` (the labels of every
    graded sample's driver), ``ids`` (every planted and control id, planted first) and ``scenarios`` (one summary per scenario,
    sorted; see the module docstring). ReportError for a root that is not a folder or holds no scenario."""
    root = Path(root).expanduser()
    if not root.is_dir():
        raise ReportError(f"{root} is not a folder: a results root is the --out folder of a stages.py live run")
    plan = _json(root / PLAN)
    plan = plan if isinstance(plan, dict) else None
    plans = {key: value for key, value in ((plan or {}).get("scenarios") or {}).items()
             if isinstance(value, dict) and isinstance(value.get("samples"), int) and value["samples"] >= 0}
    names: dict[str, Path | None] = {}
    for stage in _folders(root):
        for scenario in _folders(stage):
            names[f"{stage.name}/{scenario.name}"] = scenario
    for identifier in plans:
        names.setdefault(identifier, None)
    if not names:
        raise ReportError(f"{root} holds no sample: nothing was run there")
    scenarios = [_scenario(identifier, names[identifier], plans.get(identifier)) for identifier in sorted(names)]
    drivers = sorted({label for row in scenarios for label in row["drivers"]})
    keys = sorted({tuple(key) for row in scenarios for key in row["driver_keys"]}, key=lambda row: tuple(str(item) for item in row))
    ids = sorted({ident for row in scenarios for ident in row["ids"]}, key=_id_order)
    builds = sorted({label for row in scenarios for label in row["builds"]})
    return {"root": str(root), "plan": plan, "drivers": drivers, "driver_keys": [list(key) for key in keys], "builds": builds,
            "ids": ids, "scenarios": scenarios}


# ---------------------------------------------------------------------------------------------------------------------- text

def _table(rows: list[list[str]]) -> str:
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)


def _cell(count: dict | None) -> str:
    return "-" if count is None else f"{count['k']}/{count['n']}"


def _rule(row: dict) -> str:
    if row["rule"] is None:
        return "-"
    return "met" if row["rule"]["met"] else "NOT MET"


def render(report: dict) -> str:
    """The matrix of one results root as plain text: a row per scenario, then the samples that were not run and why."""
    ids = report["ids"]
    table = [["scenario", "ran", *ids, "overshoot", "pass", "rule", "driver"]]
    for row in report["scenarios"]:
        table.append([row["id"], f"{row['ran']}/{row['samples']}", *[_cell(row["ids"].get(ident)) for ident in ids],
                      _cell(row["overshoot"]), _cell(row["pass"]), _rule(row), ", ".join(row["drivers"]) or "-"])
    lines = [f"results root: {report['root']}", _table(table),
             "P = planted condition caught, C = control held; k/n counts samples not run in n (they are never a catch or a pass)"]
    if len(report["drivers"]) > 1:
        lines.append("note: this root mixes drivers: " + "; ".join(report["drivers"]))
    if len(report["builds"]) > 1:
        lines.append("note: this root mixes plugin builds, refs or overlays: " + "; ".join(report["builds"]))
    for row in report["scenarios"]:
        for name in row["ignored"]:
            lines.append(f"ignored: {row['id']}/{name} is not a sample folder (a sample is a folder named by its number, 1, 2, ...)")
    for row in report["scenarios"]:
        for item in row["not_run"]:
            lines.append(f"not run: {row['id']} #{item['sample']}: {item['reason']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------------------------------- compare

def _rate(count: dict | None) -> float | None:
    return None if count is None or not count["n"] else count["k"] / count["n"]


def _delta(a: dict | None, b: dict | None) -> float | None:
    rate_a, rate_b = _rate(a), _rate(b)
    return None if rate_a is None or rate_b is None else round(rate_a - rate_b, 4)


def _same_driver(a: dict, b: dict) -> None:
    """Raise DriverMismatch, naming both roots' drivers, unless both ran on the same one driver (host, backend, model, effort)."""
    for name, report in (("first", a), ("second", b)):
        if not report["driver_keys"]:
            raise ReportError(f"the {name} root {report['root']} has no graded sample, so its driver is unknown and there is "
                              "nothing to compare")
    keys_a = {tuple(key) for key in a["driver_keys"]}
    keys_b = {tuple(key) for key in b["driver_keys"]}
    if keys_a != keys_b or len(keys_a) != 1:
        raise DriverMismatch(
            f"the roots ran on different drivers, so their results are different baselines and are not compared (SPEC S-12): "
            f"{a['root']} ran on {', '.join(a['drivers'])}; {b['root']} ran on {', '.join(b['drivers'])}"
            if keys_a != keys_b else
            f"{a['root']} and {b['root']} each mix drivers ({', '.join(a['drivers'])}), so a driver cannot be named for them")


def compare(root_a: Path, root_b: Path) -> dict:
    """The change from ``root_b`` (the earlier root) to ``root_a``: per scenario and cell the counts in each and the change in
    rate (a minus b, None where either has no count). DriverMismatch, naming both drivers, when the roots ran on different hosts,
    backends, models or efforts; ReportError for a root that cannot be read."""
    a, b = read_root(root_a), read_root(root_b)
    _same_driver(a, b)
    rows_a = {row["id"]: row for row in a["scenarios"]}
    rows_b = {row["id"]: row for row in b["scenarios"]}
    ids = sorted({*a["ids"], *b["ids"]}, key=_id_order)
    rows = []
    for identifier in sorted({*rows_a, *rows_b}):
        one, two = rows_a.get(identifier), rows_b.get(identifier)
        cells = {}
        for name in (*ids, "overshoot", "pass"):
            first = (one["ids"].get(name) if name not in ("overshoot", "pass") else one[name]) if one else None
            second = (two["ids"].get(name) if name not in ("overshoot", "pass") else two[name]) if two else None
            cells[name] = {"a": first and {"k": first["k"], "n": first["n"]}, "b": second and {"k": second["k"], "n": second["n"]},
                           "delta": _delta(first, second)}
        rows.append({"id": identifier, "in": "both" if one and two else "a" if one else "b", "cells": cells,
                     "ran": {"a": one and {"k": one["ran"], "n": one["samples"]}, "b": two and {"k": two["ran"], "n": two["samples"]}}})
    return {"a": a["root"], "b": b["root"], "driver": a["drivers"][0], "ids": ids, "scenarios": rows}


def _change(cell: dict) -> str:
    first, second, delta = cell["a"], cell["b"], cell["delta"]
    if first is None and second is None:
        return "-"
    if first is None:
        return f"- (was {_cell(second)})"
    if second is None:
        return f"{_cell(first)} (new)"
    if delta is None or delta == 0:
        return f"{_cell(first)} (=)" if delta == 0 else f"{_cell(first)} (was {_cell(second)})"
    return f"{_cell(first)} (was {_cell(second)}, {delta:+.2f})"


def render_compare(comparison: dict) -> str:
    """The comparison as plain text: each cell is the count in the first root, then the second root's count and the change."""
    ids = comparison["ids"]
    table = [["scenario", *ids, "overshoot", "pass"]]
    for row in comparison["scenarios"]:
        label = row["id"] + {"both": "", "a": " (only in the first root)", "b": " (only in the earlier root)"}[row["in"]]
        table.append([label, *[_change(row["cells"][name]) for name in (*ids, "overshoot", "pass")]])
    return "\n".join([f"driver (the same in both): {comparison['driver']}", f"first root:   {comparison['a']}",
                      f"earlier root: {comparison['b']}", _table(table),
                      "each cell: k/n in the first root, then (was k/n in the earlier root, change in rate)"])
