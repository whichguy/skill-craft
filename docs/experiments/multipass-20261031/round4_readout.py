#!/usr/bin/env python3
"""Read the six live runs of Round 4 against the bar and the predictions the journal fixed before they ran
(docs/shiploop-multipass-journal.md, "Round 4").

    python3 round4_readout.py [--as NAME=FOLDER ...] [--e3 FOLDER] ROOT

ROOT holds the run folders under the names below; ``--as`` points a name at any other folder (it is how the instrument is checked,
with no model call, against the two old-ShipLoop runs it must reproduce: E1 as ``R4a0-comments-seeded-old`` and E3 as
``R4c0-sla-tidy-old``). A bar line or a prediction is ``held``, ``missed`` or ``unknown`` (a run it needs is absent). Nothing is
written. Each run is read through the ledger (test/shiploop_e2e/delta.py) and ``round2_readout.one``, so the instrument does not
depend on the candidate under test.

Three matched pairs, each the same case from the same prior, the first run of each pair without the fix and the second with it:

    a  ticket-comments from bf-codex-r2-ticket-escalation (E1's prior: AD-3 already filed as retired, the file ends with that section)
    b  ticket-comments from E2's B1-ticket-escalation (a pass 2 the fix made: tidy, AD-3 live, the file ends with ## Superseded)
    c  ticket-sla from the output of the b pair's own third pass (the old run from the old third pass, the fix run from the fix's)
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import round2_readout as r2  # noqa: E402

delta, knowledge, verdict = r2.delta, r2.knowledge, r2.verdict

PAIRS = (("a", "R4a0-comments-seeded-old", "R4a-comments-seeded-fix"),
         ("b", "R4b0-comments-tidy-old", "R4b-comments-tidy-fix"),
         ("c", "R4c0-sla-tidy-old", "R4c-sla-tidy-fix"))
NAMES = tuple(name for _, old, fix in PAIRS for name in (old, fix))
E1 = Path.home() / "e2e-runs-multipass" / "20261031" / "mp-codex-ticket-comments"
E3 = Path.home() / "e2e-runs-multipass" / "20261031" / "mp-codex-ticket-sla"


def read_run(folder: Path | None) -> dict | None:
    """One run through round2_readout.one, plus the ledger's entry blocks and the entries still filed as retired at the end."""
    if folder is None or not (folder / "result.json").is_file():
        return None
    run = r2.one(folder)
    saved = delta.saved(folder)
    block = (saved or {}).get("delta") or {}
    ids = block.get("ids") or {}
    final = folder / "work" / "docs" / "shiploop" / knowledge.ARCHITECTURE
    entries = knowledge._entries(final.read_text(errors="replace"), "AD") if final.is_file() else {}
    run.update({"line": delta.line(folder.name, saved).split(": ", 1)[-1] if saved else "(no ledger)",
                "arch": ids.get(knowledge.ARCHITECTURE) or {}, "spec": ids.get("spec.md") or {},
                "retired_now": sorted(ident for ident, entry in entries.items() if entry.retired)})
    return run


def stray(run: dict | None) -> int | None:
    return None if run is None else len(run["stray_added"] or [])


def clean(run: dict | None) -> bool | None:
    return None if run is None else bool(run["pass"]) and not run["failed"] and not run["hidden"]["lost"]


def all_of(values: list) -> bool | None:
    """True when every value is true, False when any is false, None when a run is absent and none is false."""
    if False in values:
        return False
    return None if None in values else True


def leaks(run: dict | None) -> bool | None:
    """The leak the fix is meant to prevent: at least 4 stray headings added, or a new decision filed as retired."""
    return None if run is None else stray(run) >= 4 or bool(run["born_retired"])


def main(argv: list[str]) -> int:
    args = list(argv)
    mapping: dict[str, Path] = {}
    e3 = E3
    while args and args[0] in ("--as", "--e3"):
        flag = args.pop(0)
        if flag == "--as":
            name, _, folder = args.pop(0).partition("=")
            mapping[name] = Path(folder).expanduser()
        else:
            e3 = Path(args.pop(0)).expanduser()
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0]).expanduser()
    runs = {name: read_run(mapping.get(name) or (root / name)) for name in NAMES}
    for name in NAMES:
        run = runs[name]
        if run is None:
            print(f"{name:26s} (no result yet)")
            continue
        print(f"{name:26s} pass {run['pass']} · {run['seconds']} s · stray +{stray(run)} · born retired {run['born_retired']}"
              f" · decisions added {run['decisions_added']} · notices {len(run['notices'])} (flagged that survive {run['flagged_that_survive']})"
              f" · still retired at the end {run['retired_now']}")
        print(f"{'':26s} {run['line']}")
    old = {key: runs[o] for key, o, _ in PAIRS}
    fix = {key: runs[f] for key, _, f in PAIRS}
    fixes = list(fix.values())

    print("\nBar, fixed before the runs (the three fix runs)")
    c = fix["c"]
    rows = [
        ("B1", "every fix run passes and loses no hidden check", all_of([clean(run) for run in fixes])),
        ("B2", "every fix run adds at most 2 stray headings to environment.md", all_of([None if run is None else stray(run) <= 2 for run in fixes])),
        ("B3", "no fix run files a new decision as retired", all_of([None if run is None else not run["born_retired"] for run in fixes])),
        ("B4", "pass 4 with the fix: no earlier entry changed that the request did not name (unexplained is empty in spec and architecture)",
         None if c is None else not c["arch"].get("unexplained") and not c["spec"].get("unexplained")),
    ]
    for name, text, held in rows:
        print(f"{name} {verdict(held):8s} {text}")

    print("\nControl, fixed before the runs (what the fix is credited with)")
    for key, label in (("a", "seeded pass 3"), ("b", "tidy pass 3"), ("c", "tidy pass 4")):
        print(f"K{key} {verdict(leaks(old[key])):8s} the run without the fix leaks on the {label}: at least 4 stray headings added, or a new decision filed as retired")
    credited = [key for key in "abc" if leaks(old[key]) and fix[key] is not None and stray(fix[key]) <= 2 and not fix[key]["born_retired"]]
    print(f"   pairs where the fix is credited (the old run leaks, the fix run does not): {credited or 'none yet'}")

    print("\nPredictions, fixed before the runs")
    a, b = fix["a"], fix["b"]
    e1_run, e3_run = read_run(E1), read_run(e3)

    def within(new: dict | None, base: dict | None) -> bool | None:
        return None if not new or not base or not base["seconds"] or not new["seconds"] else new["seconds"] <= 1.3 * base["seconds"]

    preds = [
        ("P1", "R4a prints at least one placement notice and its new decision is not filed as retired",
         None if a is None else bool(a["notices"]) and not a["born_retired"]),
        ("P2", "R4b prints at least one placement notice", None if b is None else bool(b["notices"])),
        ("P3", "R4b adds at most 2 stray headings and files nothing as retired", None if b is None else stray(b) <= 2 and not b["born_retired"]),
        ("P4", "R4c adds at most 2 stray headings and passes with all 16 hidden checks",
         None if c is None else stray(c) <= 2 and bool(clean(c)) and c["hidden"]["observed"] is True),
        ("P5", "R4c touches the old escalation decision (changed in place or moved under Superseded) rather than leaving it standing",
         None if c is None else bool(c["arch"].get("expected_touched") or c["arch"].get("retired_by_run"))),
        ("P6", "R4a leaves the prior's mislabel alone: AD-3 is still filed as retired at the end",
         None if a is None else "AD-3" in a["retired_now"]),
        ("P7a", "R4a0 repeats E1: at least 4 stray headings and a new decision filed as retired",
         None if old["a"] is None else stray(old["a"]) >= 4 and bool(old["a"]["born_retired"])),
        ("P7b", "R4b0 adds at least 4 stray headings", None if old["b"] is None else stray(old["b"]) >= 4),
        ("P7c", "R4c0 adds at least 4 stray headings", None if old["c"] is None else stray(old["c"]) >= 4),
        ("P8", "time: each fix run is within 1.3 times its pair's old run (the fix costs nothing we can measure)",
         all_of([within(fix[key], old[key]) for key in "abc"])),
    ]
    for name, text, held in preds:
        print(f"{name} {verdict(held):8s} {text}")
    for label, ref in (("E1 (old ShipLoop, seeded, pass 3)", e1_run), ("E3 (old ShipLoop, seeded, pass 4)", e3_run)):
        if ref is not None:
            print(f"\nreference {label}: {ref['seconds']} s, stray +{stray(ref)}, born retired {ref['born_retired']}")
    print("\n" + json.dumps({name: ({k: v for k, v in run.items() if k in ("pass", "seconds", "born_retired", "decisions_added")}
                                    if run else None) for name, run in runs.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
