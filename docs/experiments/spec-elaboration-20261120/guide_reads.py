#!/usr/bin/env python3
"""Which of ShipLoop's reference guides a delivery's builder opened, and at which stage.

Reads finished E2E run folders (result.json, events.jsonl, the product's docs/shiploop/spec.md) and calls no model.
A guide counts as opened when a command or file read the builder made names it under skills/shiploop/references/
(the stage is the one in the last packet header printed before that call), or when a heading that only that guide
has appears anywhere in the session's stream, which catches a read made through a variable or another path. A read
of a passage that holds no heading is missed.

usage: guide_reads.py RUNS_ROOT [RUNS_ROOT ...]
       guide_reads.py --bench BENCH_ROOT      (the spec-elaboration bench: round-*/<case>__<arm>__<driver>-*/)
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

import qualcheck

HEADER = re.compile(r"ShipLoop navigator \| ([a-z-]+) \| revision \d+")
SPEC_STAGES = {"intake", "discovery", "research", "spec"}
TEST_STAGES = {
    "test-strategy",
    "test-spec",
    "test",
    "system-test-author",
    "system-test",
}
SPEC_GUIDES = {
    "behavioral-requirements.md",
    "requirements-definition.md",
    "current-system-baseline.md",
}
TEST_GUIDES = {
    "testing-and-documentation.md",
    "test-loop.md",
    "repeatable-test-suites.md",
    "system-tests.md",
}


HEADING = re.compile(r"#{1,4} [^\\\"]{10,100}")
REPO = Path(__file__).resolve().parents[3]


def fingerprints(guides: Path, also: tuple[Path, ...] = ()) -> dict[str, set[str]]:
    """For each guide, the headings no other guide has and that the stage text itself never prints."""
    heads = {}
    for path in sorted(guides.glob("*.md")):
        lines = {
            line.strip()
            for line in path.read_text().splitlines()
            if line.startswith("#")
        }
        heads[path.name] = {
            line
            for line in lines
            if len(line) >= 14 and '"' not in line and "\\" not in line
        }
    elsewhere = "\n".join(path.read_text() for path in also if path.is_file())
    unique = {}
    for name, mine in heads.items():
        others = set().union(
            *(theirs for other, theirs in heads.items() if other != name)
        )
        unique[name] = {line for line in mine - others if line not in elsewhere}
    return unique


def seen_by_content(stream: Path, marks: dict[str, set[str]]) -> set[str]:
    found = set(HEADING.findall(stream.read_text(errors="replace")))
    found |= {text.rstrip() for text in found}
    return {name for name, mine in marks.items() if mine & found}


def family(model: str) -> str:
    return (
        "Sonnet"
        if "sonnet" in model
        else "Sol"
        if "sol" in model
        else "Grok"
        if "grok" in model
        else model
    )


def read_run(run: Path) -> dict | None:
    try:
        result = json.loads((run / "result.json").read_text())
        events = qualcheck.rows(run / "events.jsonl")
    except (OSError, ValueError):
        return None
    if (result.get("shiploop") or {}).get("status") != "done":
        return None
    stage, opened = None, {}
    calls = {n: text for n, _, text in qualcheck.builder_calls(events)}
    for n, event in enumerate(events):
        if n in calls:
            for name in qualcheck.REFERENCE.findall(calls[n]):
                opened.setdefault(name, stage)
        found = HEADER.findall(json.dumps(event, ensure_ascii=False))
        if found:
            stage = found[-1]
    for name in seen_by_content(run / "events.jsonl", MARKS):
        opened.setdefault(name, "seen in output")
    spec = run / "work/docs/shiploop/spec.md"
    text = spec.read_text() if spec.is_file() else ""
    case = result.get("case")
    return {
        "run": f"{run.parent.parent.name}/{run.name}",
        "case": case.get("name") if isinstance(case, dict) else str(case),
        "family": family(str(result.get("model"))),
        "effort": str(result.get("effort")),
        "version": str((result.get("versions") or {}).get("shiploop_version")),
        "words": len(text.split()),
        "requirements": len(set(re.findall(r"\bR-[0-9]+\b", text))),
        "opened": opened,
    }


def share(rows: list[dict], test) -> str:
    hits = sum(1 for row in rows if test(row))
    return f"{hits} of {len(rows)}"


BENCH_PATH = re.compile(r"GUIDES/([A-Za-z0-9_-]+\.md)")


def named_in_commands(stream: Path) -> set[str]:
    """Guide files a bench session named in a command or a file read (Claude tool inputs, Codex commands)."""
    named = set()
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        texts = []
        if event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    texts.append(json.dumps(block.get("input")))
        item = event.get("item") or {}
        if item.get("type") == "command_execution":
            texts.append(str(item.get("command")))
        for text in texts:
            named |= set(BENCH_PATH.findall(text))
    return named - {"README.md"}


def bench(root: Path) -> int:
    cells = {}
    for stream in sorted(root.glob("round-*/*/.stream.jsonl")):
        cell = stream.parent
        if not (cell / "GUIDES").is_dir():
            continue
        _, arm, driver = cell.name.split("__")
        seen = seen_by_content(stream, fingerprints(cell / "GUIDES"))
        cells.setdefault((arm.split("-")[0], driver.rsplit("-", 1)[0]), []).append(
            (seen, named_in_commands(stream))
        )
    total = sum(len(rows) for rows in cells.values())
    print("bench sessions that had the guides beside them:", total)
    print(
        "each count is given twice: named in a command or file read / a heading of the guide seen in the stream"
    )
    print()
    print(
        "arm | driver | sessions | behavioral-requirements | requirements-definition | guide files named (median, range)"
    )
    for (arm, driver), rows in sorted(cells.items()):
        counts = [len(named) for _, named in rows]
        pairs = []
        for guide in ("behavioral-requirements.md", "requirements-definition.md"):
            pairs.append(
                f"{sum(guide in named for _, named in rows)} / {sum(guide in seen for seen, _ in rows)}"
            )
        print(
            f"{arm} | {driver} | {len(rows)} | {pairs[0]} | {pairs[1]} | "
            f"{statistics.median(counts)}, {min(counts)} to {max(counts)}"
        )
    print()
    by_name, by_content = {}, {}
    for rows in cells.values():
        for seen, named in rows:
            for name in named:
                by_name[name] = by_name.get(name, 0) + 1
            for name in seen:
                by_content[name] = by_content.get(name, 0) + 1
    print("guide | sessions that named it / saw its content, of", total)
    for name, count in sorted(by_content.items(), key=lambda item: -item[1])[:10]:
        print(f"  {name[:-3]} | {by_name.get(name, 0)} / {count}")
    return 0


MARKS = fingerprints(
    REPO / "skills/shiploop/references",
    (
        REPO / "skills/shiploop/scripts/shiploop_prompts.py",
        REPO / "skills/shiploop/SKILL.md",
    ),
)


def main() -> int:
    if sys.argv[1:2] == ["--bench"]:
        return bench(Path(sys.argv[2]))
    runs = []
    for root in sys.argv[1:]:
        for result in sorted(Path(root).glob("*/*/result.json")):
            row = read_run(result.parent)
            if row:
                runs.append(row)
    print(f"whole deliveries read: {len(runs)} (engine status done)")
    print()
    print(
        "run | case | model, effort | ShipLoop | spec words | requirements | guides opened (stage at first open)"
    )
    for row in runs:
        opened = (
            ", ".join(
                f"{name[:-3]} ({stage})"
                for name, stage in sorted(row["opened"].items())
            )
            or "none"
        )
        print(
            f"{row['run']} | {row['case']} | {row['family']} {row['effort']} | {row['version']} | {row['words']} | "
            f"{row['requirements']} | {opened}"
        )
    print()
    for fam in sorted({row["family"] for row in runs}):
        mine = [row for row in runs if row["family"] == fam]
        print(f"== {fam}: {len(mine)} deliveries")
        print(
            "   opened any reference guide:", share(mine, lambda r: bool(r["opened"]))
        )
        print(
            "   opened a spec guide (behavioral-requirements, requirements-definition, current-system-baseline):",
            share(mine, lambda r: bool(SPEC_GUIDES & set(r["opened"]))),
        )
        print(
            "   ... and did so before the spec stage ended:",
            share(
                mine,
                lambda r: any(r["opened"].get(g) in SPEC_STAGES for g in SPEC_GUIDES),
            ),
        )
        print(
            "   opened behavioral-requirements:",
            share(mine, lambda r: "behavioral-requirements.md" in r["opened"]),
        )
        print(
            "   opened requirements-definition:",
            share(mine, lambda r: "requirements-definition.md" in r["opened"]),
        )
        print(
            "   opened a test guide (testing-and-documentation, test-loop, repeatable-test-suites, system-tests):",
            share(mine, lambda r: bool(TEST_GUIDES & set(r["opened"]))),
        )
        print(
            "   opened testing-and-documentation:",
            share(mine, lambda r: "testing-and-documentation.md" in r["opened"]),
        )
        counts = [len(row["opened"]) for row in mine]
        print(
            "   distinct guides opened a delivery: median",
            statistics.median(counts),
            "range",
            min(counts),
            "to",
            max(counts),
        )
        with_guide = [row["words"] for row in mine if SPEC_GUIDES & set(row["opened"])]
        without = [row["words"] for row in mine if not SPEC_GUIDES & set(row["opened"])]
        for label, words in (
            ("with a spec guide opened", with_guide),
            ("without", without),
        ):
            if words:
                print(
                    f"   final spec words {label}: median {statistics.median(words):.0f} "
                    f"({min(words)} to {max(words)}; {len(words)} deliveries)"
                )
    print()
    every = {}
    for row in runs:
        for name in row["opened"]:
            every[name] = every.get(name, 0) + 1
    print("guide | deliveries that opened it, of", len(runs))
    for name, count in sorted(every.items(), key=lambda item: -item[1]):
        print(f"  {name[:-3]} | {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
