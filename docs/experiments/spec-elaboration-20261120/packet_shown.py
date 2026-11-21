#!/usr/bin/env python3
"""How much of each stage's packet a Codex session's model was given before it submitted that stage.

Reads run folders that exist and calls no model. ShipLoop's trace says when each packet was printed and when its stage
was submitted; the run keeps each packet as it was printed; the host's own session record says what the model was given
as tool output, which on this host is what the model's own script chose to show of a command's output, not all the
command printed. A packet has two parts: the stage's instructions, up to the line "Result template:", and after it the
template and the references (the list that names the guides and where they are). A line counts as shown when it stands
in an output the model was given between the print and the submission. Because every packet repeats lines of the
ones before it, the lines no earlier packet of the same run had printed are also counted on their own.

usage: packet_shown.py RUNS_ROOT [RUNS_ROOT ...]     (every folder under a root, to two levels, that holds result.json)
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import guides_test as g

GUIDE_LINES = (
    "Behavior-model guidance:",
    "State and data assessment:",
    "Requirements definition guide:",
)


def stages_of(out: Path) -> list[dict]:
    run, given = g.chosen_run(out), g.model_outputs(out)
    rows = g.trace(run)
    found, seen, earlier = (
        [],
        set(),
        set(),
    )  # earlier: every instruction line a packet of this run has already printed
    for n, row in enumerate(rows):
        if (
            row.get("kind") != "packet"
            or row.get("stage") == "improve"
            or row.get("action") in seen
            or not given
        ):
            continue
        seen.add(row.get("action"))
        done = next(
            (
                later
                for later in rows[n:]
                if later.get("verb") == "complete"
                and later.get("action") == row.get("action")
                and later.get("exit") == 0
            ),
            None,
        )
        kept = run / str(row.get("file"))
        if done is None or not kept.is_file():
            continue
        writing = g.squeeze(
            "\n".join(
                text for at, text in given if row["ts"] - 1 <= at <= done["ts"] + 1
            )
        )
        head, _, tail = kept.read_text().partition("Result template:")
        parts = [
            [line in writing for line in g.lines_of(part)] for part in (head, tail)
        ]
        own = [line in writing for line in g.lines_of(head) if line not in earlier]
        earlier.update(g.lines_of(head))
        named = {
            label: any(label in line and line in writing for line in g.lines_of(tail))
            for label in GUIDE_LINES
            if label in tail
        }
        found.append(
            {
                "stage": row.get("stage"),
                "instructions": parts[0],
                "own": own,
                "references": parts[1],
                "named": named,
            }
        )
    return found


def main() -> int:
    outs = sorted(
        {
            result.parent
            for root in sys.argv[1:]
            for depth in ("*", "*/*")
            for result in Path(root).glob(f"{depth}/result.json")
        }
    )
    table, read = {}, 0
    print(
        "run | model, effort | spec stage: instruction lines given | reference lines given | guide lines of the list given"
    )
    for out in outs:
        result = g.load(out / "result.json")
        if result.get("host") != "codex":
            continue
        stages = stages_of(out)
        if not stages:
            continue
        read += 1
        for stage in stages:
            table.setdefault(stage["stage"], []).append(stage)
        spec = next((stage for stage in stages if stage["stage"] == "spec"), None)
        if spec:
            named = (
                ", ".join(
                    f"{label[:-1]} {'yes' if held else 'no'}"
                    for label, held in spec["named"].items()
                )
                or "none in this packet"
            )
            where = "/".join(out.parts[-2:])
            print(
                f"{where} | {result.get('model')} {result.get('effort')} | {sum(spec['instructions'])} of {len(spec['instructions'])} | {sum(spec['references'])} of {len(spec['references'])} | {named}"
            )
    print()
    print(
        f"Codex runs read: {read}. By stage, over every packet whose stage was submitted:"
    )
    print(
        "stage | packets | instruction lines given: every one | four fifths or more | under a third | of the lines no earlier packet of the run printed: four fifths or more | under a third | reference lines given: median share (lowest to highest) | a quarter or less"
    )
    for stage, rows in table.items():
        shares = [
            sum(row["references"]) / len(row["references"])
            for row in rows
            if row["references"]
        ]
        whole = sum(1 for row in rows if all(row["instructions"]))
        given = [
            sum(row["instructions"]) / len(row["instructions"])
            for row in rows
            if row["instructions"]
        ]
        own = [sum(row["own"]) / len(row["own"]) for row in rows if row["own"]]
        if shares and given:
            print(
                f"{stage} | {len(rows)} | {whole} | {sum(1 for share in given if share >= 0.8)} | {sum(1 for share in given if share < 1 / 3)} | "
                f"{sum(1 for share in own if share >= 0.8)} of {len(own)} | {sum(1 for share in own if share < 1 / 3)} of {len(own)} | "
                f"{statistics.median(shares):.0%} ({min(shares):.0%} to {max(shares):.0%}) | {sum(1 for share in shares if share <= 0.25)}"
            )
    print()
    print(
        json.dumps(
            {
                "spec packets where the list's line for a guide was given": {
                    label[:-1]: [
                        sum(
                            1
                            for row in table.get("spec", [])
                            if row["named"].get(label)
                        ),
                        sum(
                            1 for row in table.get("spec", []) if label in row["named"]
                        ),
                    ]
                    for label in GUIDE_LINES
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
