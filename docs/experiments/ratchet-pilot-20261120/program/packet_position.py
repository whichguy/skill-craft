#!/usr/bin/env python3
"""Where in a ShipLoop packet are the instruction lines a Codex session's model was not given? No model is called.

    python3 packet_position.py RUNS_ROOT [RUNS_ROOT ...]

Part V of the program of journal section 26. It reads archived ShipLoop runs made by the session "Spec elaboration"
(docs/experiments/spec-elaboration-20261120), with that study's own reader (`packet_shown.stages_of`: for each stage
whose packet was printed and submitted, one true or false for each instruction line, in the packet's order, true
when the line stands in an output the model was given). It changes nothing in those runs.

A packet has two parts: the stage's instructions, up to the line "Result template:", and after it the template and
the references. Printed: for each stage, and over all, the share of instruction lines given in the first, middle
and last third of the instructions, and the share of the lines after the result template given (the median over
packets); and the same by the length of the instructions in lines. A packet of fewer than six instruction lines is
left out.
"""
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1] / "spec-elaboration-20261120"
sys.path.insert(0, str(STUDY))
import guides_test as g
import packet_shown


def thirds(flags):
    cut = len(flags) // 3
    parts = (flags[:cut], flags[cut:len(flags) - cut], flags[len(flags) - cut:])
    return [sum(part) / len(part) for part in parts]


def line(label, rows):
    if not rows:
        return f"{label} | 0 | - | - | - | - | - | -"
    columns = list(zip(*(row["thirds"] for row in rows), strict=True))
    whole = [sum(row["flags"]) / len(row["flags"]) for row in rows]
    return (f"{label} | {len(rows)} | {statistics.mean(whole):.0%} | " + " | ".join(f"{statistics.mean(column):.0%}" for column in columns)
            + f" | {statistics.median(len(row['flags']) for row in rows):.0f} | "
            + (f"{statistics.median(after):.0%}" if (after := [row["after"] for row in rows if row["after"] is not None]) else "-"))


def main(argv=None):
    roots = list(sys.argv[1:] if argv is None else argv)
    if not roots:
        raise SystemExit(__doc__)
    outs = sorted({result.parent for root in roots for depth in ("*", "*/*") for result in Path(root).glob(f"{depth}/result.json")})
    rows, read = [], 0
    for out in outs:
        if g.load(out / "result.json").get("host") != "codex":
            continue
        stages = packet_shown.stages_of(out)
        if not stages:
            continue
        read += 1
        for stage in stages:
            flags = stage["instructions"]
            if len(flags) >= 6:
                tail = stage["references"]
                rows.append({"stage": stage["stage"], "flags": flags, "thirds": thirds(flags),
                             "after": sum(tail) / len(tail) if tail else None})
    print(f"Codex runs read: {read}; packets with six instruction lines or more: {len(rows)}")
    print("group | packets | instruction lines given | in the first third | in the middle third | in the last third | "
          "median instruction lines | lines after the result template given (median)")
    for stage in dict.fromkeys(row["stage"] for row in rows):
        print(line(str(stage), [row for row in rows if row["stage"] == stage]))
    print(line("all stages", rows))
    lengths = sorted(len(row["flags"]) for row in rows)
    if lengths:
        low, high = lengths[len(lengths) // 3], lengths[2 * len(lengths) // 3]
        print(line(f"packets of under {low} lines", [row for row in rows if len(row["flags"]) < low]))
        print(line(f"packets of {low} to {high - 1} lines", [row for row in rows if low <= len(row["flags"]) < high]))
        print(line(f"packets of {high} lines or more", [row for row in rows if len(row["flags"]) >= high]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
