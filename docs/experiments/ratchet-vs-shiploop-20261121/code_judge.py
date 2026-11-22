#!/usr/bin/env python3
"""R7, a blind reading of code quality: packets for a judge, and the score of its answers.

    python3 code_judge.py packet ROOT OUT_DIR      OUT_DIR/<n>/packet-1.md and packet-2.md per case, OUT_DIR/key.json
    python3 code_judge.py score OUT_DIR            OUT_DIR/score.json from OUT_DIR/<n>/answer-1.json and answer-2.json

A packet holds the request and both final products of one case, labelled X and Y by a coin seeded with the case's name.
Packet 1 shows X first, packet 2 shows Y first; the labels do not move. A product is its JavaScript source and the tests
its own test command runs (test/), the files the delivery added or changed since its start: a new file whole, a changed
file as a diff with ten lines of context. Left out: Markdown (documentation is measured apart), the arms' process
folders (docs/shiploop, ratchet, acceptance), node_modules, data, and starting files the delivery did not touch. In
what is shown, the tools' names, requirement ids (C-12, R-3, W1, AD-2), run folders and labels are masked. The folder
names under OUT_DIR are numbers; key.json, which says which label is which arm, is never shown to a judge.

The judge scores each product from 1 to 5 on five criteria and names the better product or neither; score counts an
arm as preferred only when both packets name it (registered reading R7).
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import static

PILOT = HERE.parent / "ratchet-pilot-20261120"
CRITERIA = ("correctness risk (5 = least likely to hide defects)", "structure and modularity", "readability and naming",
            "error handling and input validation", "tests (how well they pin the behaviour)")
MASKS = [(re.compile(r"ship\s*loop", re.IGNORECASE), "[tool]"), (re.compile(r"ratchet", re.IGNORECASE), "[tool]"),
         (re.compile(r"\b(?:C|R|W|AD|NFR|AC|UC)-?\d+\b"), "[id]"), (re.compile(r"d20261122-360a9f"), "[run]"),
         (re.compile(r"\b(?:expenses|chess|tickets|grokbot)-[12]\b"), "[run]")]
INSTRUCTIONS = """# Two products built from the same request: which is the better code?

You are reviewing the code of two products, X and Y, built independently from the request below by two different
development processes. Both are JavaScript (Node.js, no npm dependencies). Judge the code and its tests as a senior
engineer would before accepting it: how likely it is to hide defects, how well it is structured, how readable it is,
how it handles bad input and errors, and how well its tests pin the behaviour the request asks for. Do not judge
documentation (it is not shown) and do not run anything. The order in which X and Y appear is random.

{brownfield}
Score each product from 1 (poor) to 5 (excellent) on each criterion, with one short reason, then name the better
product overall, or "neither" if you see no material difference. Answer with one JSON object and nothing else:

{{"X": {{"scores": {{{fields}}}, "reasons": {{{fields_reason}}}}},
 "Y": {{"scores": {{...same keys...}}, "reasons": {{...}}}},
 "better": "X" | "Y" | "neither",
 "why": "<two or three sentences>"}}

Criteria keys: {keys}

## The request

{request}
"""
KEYS = ("correctness_risk", "structure", "readability", "error_handling", "tests")
BROWNFIELD = ("Both products start from the same existing service, which is not shown. For a file the delivery changed you "
              "see a diff (lines starting with + were added, - removed) with ten lines of context; a new file is shown whole.\n")


def git(tree: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else ""


def mask(text: str) -> str:
    for pattern, replacement in MASKS:
        text = pattern.sub(replacement, text)
    return text


def shown_files(tree: Path, base: str | None) -> list[tuple[str, str]]:
    listed = git(tree, "ls-files").splitlines()
    rows = []
    for name in sorted(listed):
        relative = Path(name)
        if relative.suffix not in static.JS:
            continue
        parts = relative.parts
        if any(parts[:len(prefix)] == prefix for prefix in static.PROCESS_DIRS) or "node_modules" in parts:
            continue
        is_test = parts[0] in ("test", "tests") or re.search(r"\.(test|spec)\.[cm]?js$", relative.name)
        if not is_test and static.excluded(relative):
            continue
        new = static.changed_lines(tree, base, relative)
        if new is not None and not new:
            continue  # a starting file the delivery did not touch
        if new is None:
            rows.append((name, (tree / relative).read_text(errors="replace")))
        else:
            rows.append((name + " (diff against the starting service)", git(tree, "diff", "-U10", "--no-color", base, "--", name)))
    return rows


def product_text(label: str, files: list[tuple[str, str]]) -> str:
    parts = [f"## Product {label}", ""]
    for name, text in files:
        fence = "```diff" if "(diff" in name else "```js"
        parts += [f"### {label}: `{mask(name)}`", "", fence, mask(text).rstrip(), "```", ""]
    return "\n".join(parts)


def packet(root: Path, out: Path) -> None:
    cases = json.loads((PILOT / "cases.json").read_text())
    records = {}
    for path in sorted((root / "measure").glob("*/measures.json")):
        record = json.loads(path.read_text())
        records.setdefault(record["case"], {})[record["arm"]] = record
    out.mkdir(parents=True, exist_ok=True)
    key = {}
    number = 0
    for case in ("shared-expenses", "node-chess-engine", "ticket-assignment", "grokbot-local"):
        pair = records.get(case, {})
        if set(pair) != {"shiploop", "ratchet"}:
            continue
        number += 1
        coin = random.Random(f"code-judge {case}").random() < 0.5
        labels = {"X": "shiploop" if coin else "ratchet", "Y": "ratchet" if coin else "shiploop"}
        texts = {}
        for label, arm in labels.items():
            record = pair[arm]
            tree = root / "measure" / record["label"] / "final" / "tree"
            texts[label] = product_text(label, shown_files(tree, record.get("base")))
        head = INSTRUCTIONS.format(brownfield=BROWNFIELD if case == "ticket-assignment" else "",
                                   fields=", ".join(f'"{name}": <1-5>' for name in KEYS),
                                   fields_reason=", ".join(f'"{name}": "<reason>"' for name in KEYS),
                                   keys=", ".join(f"{name} = {text}" for name, text in zip(KEYS, CRITERIA)),
                                   request=cases[case]["request"])
        folder = out / str(number)
        folder.mkdir(exist_ok=True)
        (folder / "packet-1.md").write_text(head + "\n" + texts["X"] + "\n" + texts["Y"])
        (folder / "packet-2.md").write_text(head + "\n" + texts["Y"] + "\n" + texts["X"])
        key[str(number)] = {"case": case, "labels": labels,
                            "chars": len((folder / "packet-1.md").read_text())}
    (out / "key.json").write_text(json.dumps(key, indent=1) + "\n")
    print(json.dumps(key, indent=1))


def first_json(text: str) -> dict | None:
    start = text.find("{")
    while start >= 0:
        depth = 0
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def score(out: Path) -> None:
    key = json.loads((out / "key.json").read_text())
    verdicts, rows = {}, {}
    for number, entry in key.items():
        answers = []
        for which in ("1", "2"):
            path = out / number / f"answer-{which}.json"
            answers.append(first_json(path.read_text()) if path.exists() else None)
        picks = [entry["labels"].get(answer.get("better")) if answer else None for answer in answers]
        preferred = picks[0] if picks[0] and picks[0] == picks[1] else None
        verdicts[entry["case"]] = preferred
        means = {}
        for label, arm in entry["labels"].items():
            values = [sum(answer[label]["scores"][k] for k in KEYS) / len(KEYS) for answer in answers
                      if answer and label in answer and all(k in answer[label].get("scores", {}) for k in KEYS)]
            means[arm] = round(sum(values) / len(values), 2) if values else None
        rows[entry["case"]] = {"picks": picks, "preferred": preferred, "mean_score": means,
                               "answers_read": sum(1 for answer in answers if answer)}
    (out / "score.json").write_text(json.dumps({"verdicts": verdicts, "rows": rows}, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 3 and argv[0] == "packet":
        packet(Path(argv[1]).resolve(), Path(argv[2]).resolve())
        return 0
    if len(argv) == 2 and argv[0] == "score":
        score(Path(argv[1]).resolve())
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
