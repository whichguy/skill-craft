#!/usr/bin/env python3
"""A blind packet of the requirements closing looks added, and the score of independent judges' labels.

    python3 judge.py packet OUT_DIR RUN...               # OUT_DIR/packet.md (for judges), OUT_DIR/key.json (never shown)
    python3 judge.py score OUT_DIR NAME=ANSWER_FILE...   # OUT_DIR/score.json, and a table on stdout

A judge sees the request, the existing product's documents where the request changes one, and each added
requirement with how it would be observed. A judge does not see which run or cycle added it, whether the product
kept to it, or what the closing look wrote. The answer file is whatever the judge returned; the first JSON list in
it is read.
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SEED = 20261120
LABELS = ("R", "E", "C", "X")
BELONGS = {"R": True, "E": True, "C": False, "X": False}

QUESTION = """# Added requirements to classify

A product was built from a written request and passed all of its tests. A review stage then used the running
product and ADDED requirements to the specification, each one something the specification "did not yet say". Your
job is to judge each added requirement against the request it belongs to: does it belong in the specification of
THAT request?

Give every item exactly one label:

- R, required: the request's words, or what they plainly imply, or (where the request changes an existing product)
  the documented behaviour of that product, require it. A delivery that does not do this is wrong.
- E, expected: the request does not require it, but without it a user would meet a real defect (data lost or
  corrupted, a crash, a wrong or misleading answer). A careful engineer would do it unasked.
- C, choice: the request is silent and more than one behaviour would be correct. The item picks one of them; a
  correct delivery could do otherwise.
- X, excess or wrong: it adds scope the request does not ask for, or it goes against the request.

Judge the requirement, not how well it is worded. Use only what is on this page: do not look for files, and do not
run anything. Where you are unsure between two labels, choose the one further down the list.

Answer with one JSON list and nothing else, one object for each item, in the order given:

[{"id": "D01", "label": "R", "why": "one short sentence"}, ...]
"""


def items_of(run: Path) -> list[dict]:
    record = json.loads((run / "run.json").read_text())
    spec = (run / "work" / "ratchet" / "spec.md").read_text()
    blocks = {
        found.group(1): found
        for found in re.finditer(
            r"^### ((?:C|U)-\d+): *(.+)\n((?:(?!^### ).*\n?)*)", spec, re.MULTILINE
        )
    }
    out = []
    for cycle in record.get("cycles", []):
        report = run / "work" / "ratchet" / f"delta-{cycle['cycle']}.md"
        text = report.read_text() if report.exists() else ""
        for ident in list(cycle.get("delta_clauses") or {}):
            found = blocks.get(ident)
            if not found:
                continue
            observable = re.search(
                r"^(?:Observable|Flow): *(.+)$", found.group(3), re.MULTILINE
            )
            line = next(
                (
                    each.strip()
                    for each in text.splitlines()
                    if re.search(rf"\b{ident}\b", each)
                    and "keeps to it" in each.lower()
                ),
                "",
            )
            if re.search(r"keeps to it:\s*\**\s*no\b", line, re.IGNORECASE):
                kept = "no"
            elif re.search(r"keeps to it:\s*\**\s*yes\b", line, re.IGNORECASE):
                kept = "yes"
            else:
                kept = "not stated"
            out.append(
                {
                    "run": run.name,
                    "case": record["case"],
                    "cycle": cycle["cycle"],
                    "clause": ident,
                    "statement": found.group(2).strip(),
                    "observable": observable.group(1).strip() if observable else "",
                    "kept": kept,
                    "found": line,
                }
            )
    return out


def existing_documents(case: dict) -> list[tuple[str, str]]:
    fixture = REPO / "test" / "shiploop_e2e" / "fixtures" / case["fixture"]
    names = [
        "README.md",
        *sorted(
            str(path.relative_to(fixture)) for path in (fixture / "docs").glob("*.md")
        ),
    ]
    return [
        (name, (fixture / name).read_text())
        for name in names
        if (fixture / name).is_file()
    ]


def packet(args: argparse.Namespace) -> int:
    cases = json.loads((HERE / "cases.json").read_text())
    items = [item for run in args.runs for item in items_of(Path(run))]
    random.Random(SEED).shuffle(items)
    for number, item in enumerate(items, 1):
        item["id"] = f"D{number:02d}"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "key.json").write_text(json.dumps(items, indent=1) + "\n")
    lines = [QUESTION]
    for name in sorted({item["case"] for item in items}):
        lines += [f'## Request "{name}"', "", cases[name]["request"], ""]
        documents = existing_documents(cases[name])
        if documents:
            lines += [
                "This request changes an existing product. Its documents, before the change:",
                "",
            ]
            for title, text in documents:
                lines += [
                    f'<document name="{title}">',
                    text.rstrip(),
                    "</document>",
                    "",
                ]
        else:
            lines += ["This request starts from an empty project.", ""]
        lines += [f'### Items for request "{name}"', ""]
        for item in items:
            if item["case"] == name:
                lines += [
                    f"{item['id']}. Added requirement: {item['statement']}",
                    f"    How it would be observed: {item['observable']}",
                    "",
                ]
    (out / "packet.md").write_text("\n".join(lines))
    kept = collections.Counter(item["kept"] for item in items)
    print(
        f"{len(items)} items; product kept to it: {dict(kept)}; packet {len((out / 'packet.md').read_text())} chars"
    )
    return 0


def labels_in(path: Path) -> dict[str, dict]:
    text = path.read_text()
    try:
        envelope = json.loads(text)
        if isinstance(envelope, dict) and "text" in envelope:
            text = envelope["text"]
    except json.JSONDecodeError:
        pass
    start = text.find("[")
    end = text.rfind("]")
    rows = json.loads(text[start : end + 1])
    return {row["id"]: row for row in rows if row.get("label") in LABELS}


def kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    if not pairs:
        return None
    agree = sum(1 for first, second in pairs if first == second) / len(pairs)
    share_first = sum(1 for first, _ in pairs if first) / len(pairs)
    share_second = sum(1 for _, second in pairs if second) / len(pairs)
    chance = share_first * share_second + (1 - share_first) * (1 - share_second)
    return None if chance == 1 else round((agree - chance) / (1 - chance), 2)


def score(args: argparse.Namespace) -> int:
    out = Path(args.out)
    key = json.loads((out / "key.json").read_text())
    judges = {}
    for spec in args.answers:
        name, _, path = spec.partition("=")
        judges[name] = labels_in(Path(path))
    report: dict = {"items": len(key), "judges": {}, "pairs": {}, "by_item": []}
    for name, labels in judges.items():
        missing = [item["id"] for item in key if item["id"] not in labels]
        counts = collections.Counter(
            labels[item["id"]]["label"] for item in key if item["id"] in labels
        )
        by_kept = {
            kept: dict(
                collections.Counter(
                    labels[item["id"]]["label"]
                    for item in key
                    if item["kept"] == kept and item["id"] in labels
                )
            )
            for kept in ("no", "yes")
        }
        by_case = {
            case: dict(
                collections.Counter(
                    labels[item["id"]]["label"]
                    for item in key
                    if item["case"] == case and item["id"] in labels
                )
            )
            for case in sorted({item["case"] for item in key})
        }
        report["judges"][name] = {
            "labels": {label: counts.get(label, 0) for label in LABELS},
            "belongs": sum(counts.get(label, 0) for label in LABELS if BELONGS[label]),
            "not_labelled": missing,
            "by_product_kept_to_it": by_kept,
            "by_case": by_case,
        }
    names = list(judges)
    for index, first in enumerate(names):
        for second in names[index + 1 :]:
            both = [
                item
                for item in key
                if item["id"] in judges[first] and item["id"] in judges[second]
            ]
            pairs = [
                (
                    BELONGS[judges[first][item["id"]]["label"]],
                    BELONGS[judges[second][item["id"]]["label"]],
                )
                for item in both
            ]
            gaps = [item for item in both if item["kept"] == "no"]

            def verdicts(
                group: list[dict], first: str = first, second: str = second
            ) -> dict:
                belongs = [
                    (
                        BELONGS[judges[first][item["id"]]["label"]],
                        BELONGS[judges[second][item["id"]]["label"]],
                    )
                    for item in group
                ]
                return {
                    "items": len(group),
                    "both_belongs": sum(1 for one, two in belongs if one and two),
                    "both_not": sum(1 for one, two in belongs if not one and not two),
                    "split": sum(1 for one, two in belongs if one != two),
                }

            report["pairs"][f"{first}+{second}"] = {
                "same_label": sum(
                    1
                    for item in both
                    if judges[first][item["id"]]["label"]
                    == judges[second][item["id"]]["label"]
                ),
                "same_side": sum(1 for one, two in pairs if one == two),
                "kappa_on_side": kappa(pairs),
                "all": verdicts(both),
                "product_did_not_keep_to_it": verdicts(gaps),
                "product_kept_to_it": verdicts(
                    [item for item in both if item["kept"] == "yes"]
                ),
                "by_case": {
                    case: verdicts([item for item in both if item["case"] == case])
                    for case in sorted({item["case"] for item in both})
                },
                "by_cycle": {
                    str(cycle): verdicts(
                        [item for item in both if item["cycle"] == cycle]
                    )
                    for cycle in sorted({item["cycle"] for item in both})
                },
            }
    for item in key:
        report["by_item"].append(
            {
                "id": item["id"],
                "run": item["run"],
                "cycle": item["cycle"],
                "clause": item["clause"],
                "kept": item["kept"],
                "statement": item["statement"],
                "labels": {
                    name: labels.get(item["id"], {}).get("label")
                    for name, labels in judges.items()
                },
                "why": {
                    name: labels.get(item["id"], {}).get("why")
                    for name, labels in judges.items()
                },
            }
        )
    (out / "score.json").write_text(json.dumps(report, indent=1) + "\n")
    for name, row in report["judges"].items():
        print(
            f"{name}: {row['labels']} belongs {row['belongs']} of {report['items']};"
            f" not kept {row['by_product_kept_to_it']['no']}; kept {row['by_product_kept_to_it']['yes']};"
            f" unlabelled {len(row['not_labelled'])}"
        )
    for name, row in report["pairs"].items():
        print(
            f"{name}: same label {row['same_label']}, same side {row['same_side']} of {row['all']['items']},"
            f" kappa {row['kappa_on_side']}; all {row['all']}; not kept {row['product_did_not_keep_to_it']};"
            f" kept {row['product_kept_to_it']}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("packet")
    make.add_argument("out")
    make.add_argument("runs", nargs="+")
    make.set_defaults(run=packet)
    read = commands.add_parser("score")
    read.add_argument("out")
    read.add_argument("answers", nargs="+")
    read.set_defaults(run=score)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
