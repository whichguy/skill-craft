#!/usr/bin/env python3
"""Choose between two arms of a ShipLoop comparison from the runs' own records: hard gates first, then bytes, then time.

    python3 test/shiploop_e2e/arms.py CONTROL CANDIDATE [--aa PAIR_A PAIR_B] [--json]
    python3 test/shiploop_e2e/arms.py DIR [--json]        # DIR holds control/ and candidate/ (and aa-1/ aa-2/, the A/A pair)
    python3 test/shiploop_e2e/arms.py summarise SLICE_OUTPUT_DIR            # one slice's summary record, as JSON

An arm is a folder of slice outputs (a subfolder with an events.jsonl each; ``summarise`` reads their records) or of summary
files (``<slice>.summary.json``, what ``summarise`` prints). ``--aa`` names the two control runs of the A/A pair: their
difference per metric is the spread, the only threshold there is. Nothing here is invented: no percentage, no minimum n.

The rule (plan 7.2 and 8.5, owner decision order):
  1. Hard gates reject the candidate: redone state-changing work after a clear; first-pass refusals above control plus the
     spread; more warm `next` calls than control plus the spread; a lost ledger obligation or a flipped SPEC clause; on Claude an
     Improve stage with no recorded improve call; a lower catch rate of the seeded defects than control. A gate on a count needs
     the A/A spread of its slice; a slice without one is reported and not gated on that count (the Grok and ask-agent slices).
  2. Otherwise the bytes the model took in (the reading path's `ingest_chars`) and the bytes it read to orient after a clear
     (`orientation_bytes`) decide: the arm with fewer, by more than the spread, wins; two metrics that disagree decide nothing.
  3. Time, turns and cost are printed, never decide.

Exit 0 only with a decision (control or candidate). Exit 2: no decision, the difference is inside the A/A spread (or the two byte
metrics disagree). Exit 3: nothing to decide from (no slice in common, or no spread for any byte metric).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clear  # noqa: E402
import metrics  # noqa: E402

SUMMARY_SUFFIX = ".summary.json"
# The count metrics whose gate is "not above control plus the spread" (the A/A difference of that slice and metric).
SPREAD_GATES = ("refusals", "warm_next_calls")
# The bytes metrics; fewer is better. A difference counts only beyond the spread.
BYTE_METRICS = ("ingest_chars", "orientation_bytes")
# Reported beside the decision, never gating (7.3: piped and variable-built calls, packet-file opens after a cut print).
DESCRIPTIVE = ("piped_shiploop_calls", "variable_built_shiploop_calls", "packet_file_opens", "turns", "cost_usd", "seconds")


def _count(block: object) -> int | None:
    """The ``count`` of a reading-path counter (a dict with a count), or a bare number, else None."""
    if isinstance(block, dict):
        block = block.get("count")
    return block if isinstance(block, int) and not isinstance(block, bool) else None


def _bytes(clear_record: dict) -> int | None:
    """The characters one clear's fresh session read before it changed anything, None where that was not measured."""
    found = (clear_record.get("orientation") or {}).get("orientation_bytes")
    return found.get("total") if isinstance(found, dict) else None


def summarise(out: Path, run_dir: Path | None = None) -> dict:
    """One slice output folder as the record arms.py compares. Unknown is None, never 0.

    From the folder's own files: the reading path (events.jsonl and the run directory), slice-result.json (the clear probe's
    redone work, per clear), metrics.json (refusals, turns, cost, seconds: written by slice.py) and the seeded-defect score.
    ``arm-checks.json`` may hold what the battery decided about the packets: ``{"obligations_lost": [...], "spec_flipped": [...]}``.
    """
    out = Path(out)
    path = metrics.reading_path(out, run_dir)

    def read(name: str) -> dict:
        try:
            value = json.loads((out / name).read_text())
        except (OSError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    result, recorded, checks = read("slice-result.json"), read("metrics.json"), read("arm-checks.json")
    clear_record = result.get("clear")
    clears = [dict(c, orientation=clear.orientation(out / "events.jsonl", c["stopped"]["events_line"]))
              if isinstance(c.get("stopped"), dict) and isinstance(c["stopped"].get("events_line"), int) else dict(c)
              for c in (clear_record if isinstance(clear_record, list) else [clear_record] if isinstance(clear_record, dict) else [])]
    failures = recorded.get("shiploop_failures")
    improve = path["improve_skill_invoked"]
    import seeded_defects  # noqa: E402 - the scorer reads the cases file and runs commands only when asked
    seeded = seeded_defects.score_output(out)
    span = recorded.get("span") if isinstance(recorded.get("span"), dict) else {}
    seconds = None if span.get("started") is None or span.get("ended") is None else round(span["ended"] - span["started"], 1)
    return {
        "slice": out.name, "host": path["host"], "events": path["events"],
        "ingest_chars": path["result_chars"],
        "orientation_bytes": sum(_bytes(c) for c in clears) if clears and all(_bytes(c) is not None for c in clears) else None,
        "clears": [{"position": c.get("stage"), "inside": c.get("inside"), "redone": len(c.get("redone") or []),
                    "orientation_bytes": _bytes(c),
                    "time_to_first_state_changing_call": (c.get("orientation") or {}).get("time_to_first_state_changing_call")}
                   for c in clears],
        "redone": sum(len(c.get("redone") or []) for c in clears) if clears else None,
        "refusals": sum(1 for f in failures if f.get("verb") == "complete") if isinstance(failures, list) else None,
        "warm_next_calls": _count(path["warm_next_calls"]),
        "piped_shiploop_calls": _count(path["piped_shiploop_calls"]),
        "variable_built_shiploop_calls": _count(path["variable_built_shiploop_calls"]),
        "packet_file_opens": _count(path["packet_file_opens"]),
        "improve_skill": {"invoked": improve["count"], "of": improve["of"]} if improve["count"] is not None else None,
        "obligations_lost": checks.get("obligations_lost"), "spec_flipped": checks.get("spec_flipped"),
        "seeded_defect_caught": None if seeded is None else not seeded["present"],
        "turns": recorded.get("turns"), "cost_usd": recorded.get("cost_usd"), "seconds": seconds,
    }


def load_arm(path: Path) -> dict[str, dict]:
    """The summaries of an arm, by slice name: its ``*.summary.json`` files, else one summary per subfolder with an
    events.jsonl (or the folder itself when it is a slice output)."""
    path = Path(path)
    found = {p.name[:-len(SUMMARY_SUFFIX)]: json.loads(p.read_text()) for p in sorted(path.glob("*" + SUMMARY_SUFFIX))}
    if found:
        return found
    folders = [path] if (path / "events.jsonl").is_file() else sorted(p for p in path.iterdir() if (p / "events.jsonl").is_file())
    return {folder.name: summarise(folder) for folder in folders}


def aa_spread(first: float, second: float) -> float:
    """The A/A rule, the only threshold there is: the difference between two runs of the same arm."""
    return abs(first - second)


def spread(first: dict[str, dict], second: dict[str, dict]) -> dict[str, dict]:
    """The A/A spread by slice: for each numeric metric, the difference between the two control runs of the slice."""
    found: dict[str, dict] = {}
    for name in sorted(set(first) & set(second)):
        row = {}
        for key in (*SPREAD_GATES, *BYTE_METRICS):
            a, b = first[name].get(key), second[name].get(key)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                row[key] = aa_spread(a, b)
        found[name] = row
    return found


def _gates(name: str, control: dict, candidate: dict, aa: dict | None) -> tuple[list[dict], list[str]]:
    """(failed gates, notes) for one slice: what rejects the candidate, and what could not be gated."""
    failed, notes = [], []

    def fail(gate: str, why: str) -> None:
        failed.append({"slice": name, "gate": gate, "why": why})

    if candidate.get("redone"):
        fail("redone", f"{candidate['redone']} state-changing call(s) repeated after a clear")
    if candidate.get("obligations_lost"):
        fail("obligations", "ledger obligations lost: " + ", ".join(map(str, candidate["obligations_lost"])))
    if candidate.get("spec_flipped"):
        fail("spec", "SPEC clauses flipped: " + ", ".join(map(str, candidate["spec_flipped"])))
    skill = candidate.get("improve_skill")
    if candidate.get("host") == "claude" and isinstance(skill, dict) and skill.get("of") and skill["invoked"] < skill["of"]:
        fail("improve_skill", f"{skill['of'] - skill['invoked']} of {skill['of']} Improve stages had no improve call")
    if control.get("seeded_defect_caught") and candidate.get("seeded_defect_caught") is False:
        fail("seeded_defect", "the control's final tree is free of the planted defect and the candidate's is not")
    for key in SPREAD_GATES:
        c, a = control.get(key), candidate.get(key)
        if not isinstance(c, (int, float)) or not isinstance(a, (int, float)):
            notes.append(f"{name}: {key} not measured on both arms")
            failed.append({"slice": name, "gate": key, "why": "not measured on both arms", "unmeasured": True})
        elif aa is None or key not in aa:
            notes.append(f"{name}: {key} is descriptive here (control {c}, candidate {a}): no A/A spread for this slice")
        elif a > c + aa[key]:
            fail(key, f"candidate {a} is above control {c} plus the A/A spread {aa[key]}")
    return failed, notes


def decide(control: dict[str, dict], candidate: dict[str, dict], aa: dict[str, dict] | None = None) -> dict:
    """The decision over the two arms' slices. ``decision`` is "control", "candidate" or None; ``exit`` is the process status
    (0 decided, 2 inside the spread, 3 nothing to decide from).

    Missing evidence never decides (build step 2, R2 of docs/shiploop-e2e-loop-recommendations-2026-10-25.md). A slice that
    one arm has and the other lacks, and a hard-gate field not measured on both arms, leave the decision open. Before
    2026-10-25 the slices were silently cut to the common ones, and an unmeasured gate was only a note, so a candidate could
    win with a missing slice or missing gate fields (Astra's probe, final verdict)."""
    common = sorted(set(control) & set(candidate))
    report = {"slices": common, "gates_failed": [], "notes": [], "bytes": {}, "descriptive": {}, "decision": None,
              "reason": "", "exit": 3}
    if not common:
        report["reason"] = "the two arms have no slice in common"
        return report
    one_sided = sorted(set(control) ^ set(candidate))
    if one_sided:
        report["reason"] = "slices missing from an arm: " + ", ".join(
            f"{name} ({'control only' if name in control else 'candidate only'})" for name in one_sided)
        return report
    unmeasured = []
    for name in common:
        failed, notes = _gates(name, control[name], candidate[name], (aa or {}).get(name))
        unmeasured += [g for g in failed if g.get("unmeasured")]
        report["gates_failed"] += [g for g in failed if not g.get("unmeasured")]
        report["notes"] += notes
        report["descriptive"][name] = {key: {"control": control[name].get(key), "candidate": candidate[name].get(key)}
                                       for key in DESCRIPTIVE}
    if report["gates_failed"]:  # a failure that was measured rejects the candidate even beside an unmeasured gate
        report.update(decision="control", exit=0, reason="a hard gate rejects the candidate: "
                      + "; ".join(f"{g['slice']} {g['gate']}: {g['why']}" for g in report["gates_failed"]))
        return report
    if unmeasured:
        report["reason"] = "a hard-gate field is not measured on both arms: " + ", ".join(
            f"{g['slice']} {g['gate']}" for g in unmeasured)
        return report
    for key in BYTE_METRICS:
        total_c = total_a = threshold = measured = 0
        for name in common:
            c, a = control[name].get(key), candidate[name].get(key)
            band = ((aa or {}).get(name) or {}).get(key)
            if isinstance(c, (int, float)) and isinstance(a, (int, float)) and band is not None:
                total_c, total_a, threshold, measured = total_c + c, total_a + a, threshold + band, measured + 1
        if not measured:
            report["bytes"][key] = {"measured": 0, "vote": None, "why": "no slice has both arms and an A/A spread for it"}
            continue
        difference = total_a - total_c
        report["bytes"][key] = {"measured": measured, "control": total_c, "candidate": total_a, "difference": difference,
                                "spread": threshold,
                                "vote": None if abs(difference) <= threshold else "candidate" if difference < 0 else "control"}
    voting = {key: row["vote"] for key, row in report["bytes"].items() if row["measured"]}
    if not voting:
        report["reason"] = "no byte metric has an A/A spread, so nothing separates the arms"
        return report
    cast = {vote for vote in voting.values() if vote}
    if len(cast) == 1:
        winner = next(iter(cast))
        report.update(decision=winner, exit=0, reason=f"fewer bytes by more than the A/A spread, and no byte metric favours the "
                      f"other arm: {winner}")
    elif cast:
        report.update(exit=2, reason="the byte metrics disagree: " + ", ".join(f"{k} favours {v}" for k, v in voting.items() if v))
    else:
        report.update(exit=2, reason="the difference is inside the A/A spread: " + ", ".join(
            f"{k} {report['bytes'][k]['difference']:+,} against {report['bytes'][k]['spread']:,}" for k in voting))
    return report


def lines(report: dict) -> list[str]:
    """The report as text for a person."""
    out = [f"slices: {', '.join(report['slices']) or 'none'}"]
    out += [f"gate failed: {g['slice']} {g['gate']}: {g['why']}" for g in report["gates_failed"]]
    out += [f"note: {n}" for n in report["notes"]]
    for key, row in report["bytes"].items():
        out.append(f"{key}: " + (row["why"] if row.get("why") else
                                  f"control {row['control']:,}, candidate {row['candidate']:,} ({row['difference']:+,}), "
                                  f"A/A spread {row['spread']:,}, favours {row['vote'] or 'neither'}"))
    for name, rows in report["descriptive"].items():
        shown = [f"{k} {v['control']} -> {v['candidate']}" for k, v in rows.items() if v["control"] is not None or v["candidate"] is not None]
        out.append(f"{name} (descriptive): " + (", ".join(shown) or "nothing measured on both arms"))
    out.append(("DECISION: " + report["decision"] if report["decision"] else "NO DECISION") + f" - {report['reason']}")
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["summarise"] and len(args) == 2:
        json.dump(summarise(Path(args[1])), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("control", type=Path, help="the control arm, or a folder holding control/ and candidate/")
    parser.add_argument("candidate", type=Path, nargs="?")
    parser.add_argument("--aa", nargs=2, type=Path, metavar=("A", "B"), help="the two control runs of the A/A pair")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parsed = parser.parse_args(args)
    control, candidate, pair = parsed.control, parsed.candidate, parsed.aa
    if candidate is None:
        if not (control / "control").is_dir() or not (control / "candidate").is_dir():
            parser.error("one folder must hold control/ and candidate/ (and aa-1/ and aa-2/ for the A/A pair)")
        folder = control
        control, candidate = folder / "control", folder / "candidate"
        pair = pair or ((folder / "aa-1", folder / "aa-2") if (folder / "aa-1").is_dir() and (folder / "aa-2").is_dir() else None)
    aa = spread(load_arm(pair[0]), load_arm(pair[1])) if pair else None
    report = decide(load_arm(control), load_arm(candidate), aa)
    if parsed.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write("\n".join(lines(report)) + "\n")
    return report["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
