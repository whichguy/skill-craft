#!/usr/bin/env python3
"""Whether a ShipLoop delivery loaded a platform card: named at discovery, linked by the script, opened, shown.

Reads finished E2E run folders (result.json, events.jsonl, the product's docs/shiploop/environment.md, the host's own
session record) and calls no model. For each run it reads four things, in the order a card reaches a model:

  asked    the discovery packet asked for "the platform guide each target follows" (ShipLoop since 2026-10-20)
  named    what the delivered docs/shiploop/environment.md says under "## Targets and runtimes": the cards it names
           (platforms/<name>.md); or it mentions a platform guide or card and names none (counted as "none":
           every such wording read by hand denies one, for example "No platform guide applies"); or it says
           nothing about a platform guide
  linked   the "Platform testing guide: ...platforms/<name>.md#testing" lines the script printed in a packet
  opened   a command or file read the builder made names a card file (with the stage of the first one)
  shown    how many of a card's own lines stand in the output the model was given: on Codex the host's session
           record (the model chooses what of a command's output to show itself), on Claude the tool results, on any
           other host the event stream (what the commands printed). A card's own lines are its lines of 20
           characters or more that no other card and no stage text holds, read from the run's own copy of the skill.

usage: card_reads.py [--repo SKILL_CRAFT_CHECKOUT] RUNS_ROOT [RUNS_ROOT ...]
       every folder under a root, to three levels, that holds result.json
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

CARD = re.compile(r"platforms/([a-z0-9-]+)\.md")
LINK = re.compile(
    r"Platform testing guide: [^\s\"\\]*platforms/([a-z0-9-]+)\.md#testing"
)
HEADER = re.compile(r"ShipLoop navigator \| ([a-z-]+) \| revision \d+")
ASKED = "the platform guide each target follows"
MENTION = re.compile(r"platform (?:guide|card)s?", re.IGNORECASE)


def squeeze(text: str) -> str:
    return " ".join(text.split())


def lines_of(text: str) -> list[str]:
    return list(
        dict.fromkeys(
            line for line in map(squeeze, text.splitlines()) if len(line) >= 20
        )
    )


def own_lines(cards: Path, prompts: str) -> dict[str, list[str]]:
    """For each card, its lines that no other card and no stage text holds."""
    every = {
        path.stem: lines_of(path.read_text(errors="replace"))
        for path in sorted(cards.glob("*.md"))
    }
    own = {}
    for name, mine in every.items():
        others = (
            set().union(
                *(set(theirs) for other, theirs in every.items() if other != name)
            )
            if len(every) > 1
            else set()
        )
        own[name] = [
            line for line in mine if line not in others and line not in prompts
        ]
    return own


def skill_copy(out: Path, repo: Path) -> Path:
    """The run's own copy of the skill's references folder, else the checkout's."""
    for pattern in (
        "build/plugins/*/skills/shiploop/references",
        "home/.grok/installed-plugins/*/skills/shiploop/references",
        "home/.codex/plugins/**/skills/shiploop/references",
        "home/.claude/plugins/**/skills/shiploop/references",
        "home/**/skills/shiploop/references",
    ):
        found = sorted(out.glob(pattern))
        if found:
            return found[0]
    return repo / "skills/shiploop/references"


def environment(out: Path) -> tuple[str | None, str]:
    """The delivered environment.md: its "## Targets and runtimes" section (None when no file) and the whole text."""
    for where in ("work", "export", "delivery"):
        path = out / where / "docs/shiploop/environment.md"
        if path.is_file():
            text = path.read_text(errors="replace")
            if "## Targets and runtimes" not in text:
                return "", text
            return text.split("## Targets and runtimes", 1)[1].split("\n## ", 1)[
                0
            ], text
    return None, ""


def family(model: str) -> str:
    low = model.lower()
    for name in ("sonnet", "opus", "sol", "terra", "luna", "grok", "deepseek"):
        if name in low:
            return name
    return low


def read_run(out: Path, repo: Path, g) -> dict | None:
    result = g.load(out / "result.json")
    stream = out / "events.jsonl"
    if not result or not stream.is_file():
        return None
    raw = stream.read_text(errors="replace")
    case = result.get("case")
    row = {
        "run": "/".join(out.parts[-3:]),
        "case": case.get("name") if isinstance(case, dict) else str(case),
        "host": str(result.get("host")),
        "model": str(result.get("model")),
        "effort": str(result.get("effort")),
        "version": str((result.get("versions") or {}).get("shiploop_version")),
        "status": str((result.get("shiploop") or {}).get("status")),
        "asked": ASKED in squeeze(raw.replace("\\n", " ")),
    }
    section, whole = environment(out)
    row["family"] = family(row["model"])
    row["anywhere"] = sorted(set(CARD.findall(whole)))
    row["mentions"] = bool(MENTION.search(whole))
    row["named"] = sorted(set(CARD.findall(section))) if section else []
    row["says"] = (
        "no record"
        if section is None
        else "cards"
        if row["named"]
        else "none"
        if MENTION.search(section)
        else "nothing said"
    )
    row["said"] = next(
        (
            squeeze(line)[:160]
            for line in (section or "").splitlines()
            if MENTION.search(line)
        ),
        "",
    )
    row["linked"] = sorted(set(LINK.findall(raw)))
    # opened: a builder call that names a card file, with the stage printed last before it
    stage, opened = None, {}
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except ValueError:
        events = []
    calls = {}
    for n, _, text in g.qualcheck.builder_calls(events):
        calls.setdefault(n, []).append(text)
    for n, event in enumerate(events):
        for text in calls.get(n, ()):
            for name in CARD.findall(text):
                opened.setdefault(name, stage)
        found = HEADER.findall(json.dumps(event, ensure_ascii=False))
        if found:
            stage = found[-1]
    row["opened"] = opened
    # shown: the card's own lines in what the model was given
    given = g.model_outputs(out)
    rollout = bool(sorted(out.glob("home/.codex/sessions/**/rollout-*.jsonl")))
    if given is None:
        writing, row["basis"] = (
            squeeze(raw.replace("\\n", "\n").replace('\\"', '"')),
            "printed",
        )
    else:
        writing, row["basis"] = (
            squeeze("\n".join(text for _, text in given)),
            ("session record" if rollout else "tool results"),
        )
    references = skill_copy(out, repo)
    prompts = references.parent / "scripts/shiploop_prompts.py"
    own = own_lines(
        references / "platforms",
        squeeze(prompts.read_text(errors="replace")) if prompts.is_file() else "",
    )
    row["shown"] = {
        name: (sum(1 for line in lines if line in writing), len(lines))
        for name, lines in own.items()
        if lines
    }
    row["shown"] = {name: pair for name, pair in row["shown"].items() if pair[0]}
    row["link_shown"] = bool(LINK.search(writing))
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--json", help="also write every row to this file")
    parser.add_argument("roots", nargs="+")
    args = parser.parse_args()
    repo = Path(args.repo)
    sys.path.insert(0, str(repo / "docs/experiments/spec-elaboration-20261120"))
    import guides_test as g  # the readers of a run's session record, kept in one place

    outs = sorted(
        {
            result.parent
            for root in args.roots
            for depth in ("*", "*/*", "*/*/*")
            for result in Path(root).glob(f"{depth}/result.json")
        }
    )
    rows = []
    for out in outs:
        try:
            row = read_run(out, repo, g)
        except Exception as error:  # noqa: BLE001  one unreadable folder must not end the reading
            print(f"unread: {out} ({type(error).__name__}: {error})", file=sys.stderr)
            continue
        if row:
            rows.append(row)
    if args.json:
        Path(args.json).write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows if row["asked"])
            + "\n"
        )

    asked = [row for row in rows if row["asked"]]
    print(
        f"run folders read: {len(rows)}; whose discovery packet asked for the platform guide: {len(asked)}"
    )
    print()
    print(
        "run | case | host model effort | ShipLoop | status | targets section says | linked | opened (stage) | shown: card own-lines given of all (basis)"
    )
    for row in asked:
        opened = (
            ", ".join(
                f"{name} ({stage})" for name, stage in sorted(row["opened"].items())
            )
            or "-"
        )
        shown = (
            ", ".join(
                f"{name} {got} of {total}"
                for name, (got, total) in sorted(row["shown"].items())
            )
            or "-"
        )
        says = row["says"] + (": " + ", ".join(row["named"]) if row["named"] else "")
        print(
            f"{row['run']} | {row['case']} | {row['host']} {row['model']} {row['effort']} | {row['version']} | {row['status']} | "
            f"{says} | {', '.join(row['linked']) or '-'} | {opened} | {shown} ({row['basis']})"
        )
    print()

    def share(found: list[dict], test) -> str:
        return f"{sum(1 for row in found if test(row))} of {len(found)}"

    recorded = [row for row in asked if row["says"] != "no record"]
    print(
        f"== of the {len(asked)} asked runs, {len(recorded)} delivered a docs/shiploop/environment.md"
    )
    for label in ("cards", "none", "nothing said"):
        print(
            f"   targets section: {label}: {share(recorded, lambda r, label=label: r['says'] == label)}"
        )
    named = [row for row in recorded if row["named"]]
    print(f"== of the {len(named)} runs that named a card")
    print(
        "   the script printed its testing link:",
        share(named, lambda r: bool(r["linked"])),
    )
    print(
        "   the model was given that link line:",
        share(named, lambda r: r["link_shown"]),
    )
    print(
        "   the builder opened a named card:",
        share(named, lambda r: bool(set(r["named"]) & set(r["opened"]))),
    )
    print(
        "   the model was given at least one own line of a named card:",
        share(named, lambda r: bool(set(r["named"]) & set(r["shown"]))),
    )
    fractions = [
        got / total
        for row in named
        for name, (got, total) in row["shown"].items()
        if name in row["named"]
    ]
    if fractions:
        print(
            f"   share of a named card's own lines given, where any: median {statistics.median(fractions):.0%} "
            f"({min(fractions):.0%} to {max(fractions):.0%}; {len(fractions)} cards)"
        )
    print(f"== of all {len(asked)} asked runs")
    print("   the builder opened any card:", share(asked, lambda r: bool(r["opened"])))
    print(
        "   the model was given an own line of any card:",
        share(asked, lambda r: bool(r["shown"])),
    )
    print()
    print(
        "   the file names a card anywhere, not only in the targets section:",
        share(recorded, lambda r: bool(r["anywhere"])),
    )
    print(
        "   the file mentions a platform guide or card anywhere:",
        share(recorded, lambda r: r["mentions"]),
    )
    print()
    print(
        "== by model family, runs with a delivered environment.md: runs | named a card | said none | nothing said | "
        "opened any card | given any card line"
    )
    for value in sorted(
        {row["family"] for row in recorded},
        key=lambda v: -sum(1 for r in recorded if r["family"] == v),
    ):
        mine = [row for row in recorded if row["family"] == value]
        print(
            f"   {value} | {len(mine)} | {sum(1 for r in mine if r['named'])} | {sum(1 for r in mine if r['says'] == 'none')} | "
            f"{sum(1 for r in mine if r['says'] == 'nothing said')} | {sum(1 for r in mine if r['opened'])} | "
            f"{sum(1 for r in mine if r['shown'])}"
        )
    print()
    stages = {}
    for row in asked:
        for stage in row["opened"].values():
            stages[str(stage)] = stages.get(str(stage), 0) + 1
    print(
        "== stage of the first open of each card, all asked runs:",
        ", ".join(
            f"{stage} {count}"
            for stage, count in sorted(stages.items(), key=lambda item: -item[1])
        ),
    )
    print()
    for key in ("host", "case"):
        print(
            f"== by {key}: runs | named a card | said none | opened any card | given any card line"
        )
        for value in sorted({row[key] for row in asked}):
            mine = [row for row in asked if row[key] == value]
            print(
                f"   {value} | {len(mine)} | {sum(1 for r in mine if r['named'])} | {sum(1 for r in mine if r['says'] == 'none')} | "
                f"{sum(1 for r in mine if r['opened'])} | {sum(1 for r in mine if r['shown'])}"
            )
    print()
    every, opened, shown = {}, {}, {}
    for row in asked:
        for name in row["named"]:
            every[name] = every.get(name, 0) + 1
        for name in row["opened"]:
            opened[name] = opened.get(name, 0) + 1
        for name in row["shown"]:
            shown[name] = shown.get(name, 0) + 1
    print("card | runs that named it | opened it | were given a line of it")
    for name in sorted(set(every) | set(opened) | set(shown)):
        print(
            f"   {name} | {every.get(name, 0)} | {opened.get(name, 0)} | {shown.get(name, 0)}"
        )
    print()
    print(
        "what the targets section says about the platform guide, first such line of each run that names no card:"
    )
    seen = {}
    for row in recorded:
        if not row["named"] and row["said"]:
            seen.setdefault(row["said"][:110], []).append(row["run"])
    for said, runs in sorted(seen.items(), key=lambda item: -len(item[1]))[:25]:
        print(f"   {len(runs)} x {said}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
