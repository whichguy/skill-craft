#!/usr/bin/env python3
"""Read the E2 A/B of the placement candidate against the bar and the predictions the journal fixed before any run
(docs/shiploop-multipass-journal.md, "Round 2").

    python3 round2_readout.py ROOT [--json]

ROOT holds the run folders ``A1-ticket-assignment``, ``A1-ticket-escalation``, ``B1-...`` and so on (arm A is ShipLoop as it was
at the candidate's base commit, arm B the candidate; a chain is a ticket-assignment run and the ticket-escalation run that continues
it).  Every number comes from the run's own files: ``result.json``, the ``delta`` block of ``metrics.json`` (test/shiploop_e2e/
delta.py, an instrument that does not depend on the candidate), ``events.jsonl`` (the placement notices the run printed) and the final
living files.  A bar line or prediction is ``held``, ``missed`` or ``unknown`` (a part the runs did not record).  Nothing is written.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE.parents[2] / "skills" / "shiploop" / "scripts"))
import delta  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402

# The named sections of architecture.md that hold a live update (Superseded holds what no longer does).
LIVE_ARCHITECTURE = {"Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks", "Decisions"}
NOTICE = re.compile(r"ShipLoop placement notice: (\S+) gained (.*?) \(this stage is accepted\)")
BORN = re.compile(r"((?:(?:AD|R)-\d+(?:, )?)+) under '(\w+)'")
HEADINGS = re.compile(r"new headings ((?:'[^']*'(?:, )?)+) that match")


def verdict(held: bool | None) -> str:
    return "unknown" if held is None else "held" if held else "missed"


def median(values: list) -> float | None:
    return statistics.median(values) if values else None


def notices(out: Path) -> list[dict]:
    """The placement notices a run printed, each once (a host may log one call's stdout in two events), with what each flagged."""
    try:
        text = (out / "events.jsonl").read_text(errors="replace")
    except OSError:
        return []
    found, seen = [], set()
    for line in text.splitlines():
        for match in NOTICE.finditer(line):
            key = (match.group(1), match.group(2))
            if key in seen:
                continue
            seen.add(key)
            clauses = match.group(2)
            born = BORN.search(clauses)
            heads = HEADINGS.search(clauses)
            found.append({"file": Path(match.group(1)).name,
                          "born": re.findall(r"(?:AD|R)-\d+", born.group(1)) if born else [],
                          "headings": re.findall(r"'([^']*)'", heads.group(1)) if heads else []})
    return found


def survivors(out: Path, flagged: list[dict]) -> int:
    """How many of the things the notices flagged are still there in the run's final files: a heading still a level-2 heading, or an
    entry still filed as retired."""
    count = 0
    for item in flagged:
        path = out / "work" / "docs" / "shiploop" / item["file"]
        try:
            final = path.read_text(errors="replace")
        except OSError:
            continue
        titles = [title for _, level, title in knowledge._outline(final.splitlines()) if level == 2]
        count += sum(1 for title in item["headings"] if title in titles)
        prefixes = {"spec.md": "R", knowledge.ARCHITECTURE: "AD"}
        if item["born"] and item["file"] in prefixes:
            entries = knowledge._entries(final, prefixes[item["file"]])
            count += sum(1 for ident in item["born"] if ident in entries and entries[ident].retired)
    return count


def one(out: Path) -> dict:
    result = json.loads((out / "result.json").read_text())
    block = delta.saved(out).get("delta") or {}
    place = block.get("placement") or {}
    env, arch = place.get("environment.md") or {}, place.get(knowledge.ARCHITECTURE) or {}
    ids = ((block.get("ids") or {}).get(knowledge.ARCHITECTURE)) or {}
    acceptance = (result.get("quality") or {}).get("acceptance") or {}
    lost = [row["id"] for row in acceptance.get("checks") or [] if not row.get("pass")]
    printed = notices(out)
    return {"folder": out.name, "pass": bool(result.get("pass")), "seconds": (result.get("process") or {}).get("elapsed_seconds"),
            "failed": [row["command"][:60] for row in result.get("checks") or [] if not row.get("pass")],
            "hidden": {"observed": acceptance.get("observed"), "lost": lost},
            "stray_added": env.get("stray_added") if block else None,
            "env_growth": ((env.get("bytes") or {}).get("final", 0) - (env.get("bytes") or {}).get("prior", 0)) if block else None,
            "decisions_added": ids.get("added") if block else None,
            "born_retired": ids.get("born_retired") if block else None,
            "live_sections_changed": sorted(set(arch.get("changed_sections") or []) & LIVE_ARCHITECTURE) if block else None,
            "notices": printed, "flagged_that_survive": survivors(out, printed)}


def read(root: Path) -> dict:
    runs = {}
    for folder in sorted(root.iterdir()):
        match = re.fullmatch(r"([AB])(\d+)-ticket-(assignment|escalation)", folder.name)
        if match and (folder / "result.json").is_file():
            runs[(match.group(1), int(match.group(2)), 1 if match.group(3) == "assignment" else 2)] = one(folder)

    def of(arm: str, pass_no: int | None = None) -> list[dict]:
        return [row for (a, _, p), row in sorted(runs.items()) if a == arm and (pass_no is None or p == pass_no)]

    def known(rows: list[dict], key: str) -> list:
        return [row[key] for row in rows if row[key] is not None]

    a, b = of("A"), of("B")
    a2, b2 = of("A", 2), of("B", 2)
    bars = []
    born = known(b, "born_retired")
    bars.append({"id": "B1", "bar": "no entry is filed as retired when new in any of B's passes",
                 "observed": f"B born_retired per pass {[len(x) for x in born]}; A {[len(x) for x in known(a, 'born_retired')]}",
                 "verdict": verdict(None if not born else all(not x for x in born))})
    strays_b, strays_a = [len(x) for x in known(b2, "stray_added")], [len(x) for x in known(a2, "stray_added")]
    bars.append({"id": "B2", "bar": "median stray headings added to environment.md in pass 2: B at most 2, A at least 4",
                 "observed": f"B {strays_b} (median {median(strays_b)}); A {strays_a} (median {median(strays_a)})",
                 "verdict": verdict(None if not (strays_a and strays_b) else median(strays_b) <= 2 and median(strays_a) >= 4)})
    added = [row for row in b if row["decisions_added"]]
    bars.append({"id": "B3", "bar": "in B, a pass that added a decision changed a live section of architecture.md",
                 "observed": f"B passes with a decision: {len(added)}; with a live section changed: "
                             f"{sum(1 for row in added if row['live_sections_changed'])}; A: "
                             f"{sum(1 for row in a if row['decisions_added'] and row['live_sections_changed'])} of "
                             f"{sum(1 for row in a if row['decisions_added'])}",
                 "verdict": verdict(None if not added else all(row["live_sections_changed"] for row in added))})
    every = a + b
    bars.append({"id": "B4", "bar": "every run passes and no inherited hidden check is lost, in both arms",
                 "observed": f"{sum(1 for row in every if row['pass'])} of {len(every)} pass; hidden lost "
                             f"{[(row['folder'], row['hidden']['lost']) for row in every if row['hidden']['lost']]}",
                 "verdict": verdict(None if not every else all(row["pass"] and not row["hidden"]["lost"] for row in every))})
    secs_b, secs_a = known(b2, "seconds"), known(a2, "seconds")
    bars.append({"id": "B5", "bar": "B's median pass-2 elapsed time is at most 1.2 times A's",
                 "observed": f"B {median(secs_b)} s, A {median(secs_a)} s",
                 "verdict": verdict(None if not (secs_a and secs_b) else median(secs_b) <= 1.2 * median(secs_a))})
    printed_b = [len(row["notices"]) for row in b]
    survive = sum(row["flagged_that_survive"] for row in b)
    predictions = [
        {"id": "P1", "prediction": "B1 holds", "verdict": bars[0]["verdict"]},
        {"id": "P2", "prediction": "B's median pass-2 stray_added is 2 (1 to 3)",
         "observed": f"{median(strays_b)}", "verdict": verdict(None if not strays_b else 1 <= median(strays_b) <= 3)},
        {"id": "P3", "prediction": "A's median is at least 4 and A files at least one new entry as retired",
         "observed": f"median {median(strays_a)}; born_retired {[len(x) for x in known(a, 'born_retired')]}",
         "verdict": verdict(None if not (strays_a and known(a, "born_retired")) else
                            median(strays_a) >= 4 and any(known(a, "born_retired")))},
        {"id": "P4", "prediction": "B prints a placement notice in at least 4 of its 6 passes and at least one flagged item "
                                   "survives to the end", "observed": f"notices per B pass {printed_b}; flagged that survive {survive}",
         "verdict": verdict(None if len(b) < 6 else sum(1 for n in printed_b if n) >= 4 and survive >= 1)},
        {"id": "P5", "prediction": "all 12 runs pass", "observed": f"{sum(1 for row in every if row['pass'])} of {len(every)}",
         "verdict": verdict(None if len(every) < 12 else all(row["pass"] for row in every))},
        {"id": "P6", "prediction": "B's median pass-2 elapsed time is within 15 percent of A's",
         "observed": f"B {median(secs_b)} s, A {median(secs_a)} s",
         "verdict": verdict(None if not (secs_a and secs_b) else abs(median(secs_b) - median(secs_a)) <= 0.15 * median(secs_a))}]
    return {"root": str(root), "runs": {f"{a_}{n}-pass{p}": row for (a_, n, p), row in sorted(runs.items())}, "bars": bars,
            "predictions": predictions}


def main(argv: list[str]) -> int:
    args = [x for x in argv if not x.startswith("--")]
    report = read(Path(args[0]).expanduser().resolve())
    if "--json" in argv:
        print(json.dumps(report, indent=2))
        return 0
    for name, row in report["runs"].items():
        print(f"{name:10s} {'pass' if row['pass'] else 'FAIL':4s} {row['seconds']}s  env stray +{len(row['stray_added'] or [])}"
              f" ({row['env_growth']} B)  decisions {row['decisions_added']}  born_retired {row['born_retired']}"
              f"  live sections {row['live_sections_changed']}  notices {len(row['notices'])} (survive {row['flagged_that_survive']})")
    for row in report["bars"]:
        print(f"{row['id']} {row['verdict']:8s} {row['bar']}\n     observed: {row['observed']}")
    for row in report["predictions"]:
        print(f"{row['id']} {row['verdict']:8s} {row['prediction']}" + (f"\n     observed: {row['observed']}" if row.get("observed") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
