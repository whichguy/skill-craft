"""Generated knowledge homes for offline packet measurements: a long one and a small one (ShipLoop efficiency plan, unit U5).

A packet quotes the knowledge files its stage reads whole (KNOWLEDGE/spec.md, environment.md, architecture.md under the repository's
docs/shiploop), so how many characters a change saves depends on how much the home holds. A recorded long hosted-platform run had files of
16.3, 14.2 and 5.8 KB; a one-line bug fix has none. This module writes both kinds, neutral and deterministic (no domain words, the
same bytes every time), and walks the navigator's dry-run delivery graph over them with no model and no project:

    python3 test/shiploop_e2e/home_fixtures.py [long|small|empty] [inline|ask-agent]     # per-stage printed and file characters

``LONG`` is about 16/14/6 KB (spec, environment, architecture); ``SMALL`` is a few hundred characters each, a home a short run
writes. A change that should not touch small homes is checked with ``fingerprints``: the same hashes before and after.
"""
from __future__ import annotations

import hashlib
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "skills" / "shiploop" / "scripts"
FILES = ("spec.md", "environment.md", "architecture.md")
LONG = {"spec.md": 16_000, "environment.md": 14_000, "architecture.md": 6_000}
SMALL = {"spec.md": 900, "environment.md": 600, "architecture.md": 500}
KINDS = {"long": LONG, "small": SMALL, "empty": {}}


def _imports():
    for path in (str(SCRIPTS), str(HERE)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import shiploop_knowledge_home as home
    import shiploop_navigator as navigator
    import shiploop_navigator_dry_run as dry_run
    return home, navigator, dry_run


def document(name: str, size: int) -> str:
    """One living file of ``size`` characters (to the end of the line that reaches it): its sections in the order the knowledge
    home defines, filled with numbered neutral lines. Requirements are ``R-<n>`` lines, as the spec stage writes them."""
    home, _navigator, _dry_run = _imports()
    sections = home.SECTIONS[name]
    lines = [f"# Synthetic {name.removesuffix('.md')}", ""]
    number, section = 0, 0
    while sum(len(line) + 1 for line in lines) < size:
        if number % 6 == 0:
            lines += [f"## {sections[section % len(sections)]}", ""]
            section += 1
        number += 1
        label = f"R-{number}" if name == "spec.md" else f"{name.removesuffix('.md')}-{number}"
        lines.append(f"- {label}: Synthetic entry {number} states that item {number} keeps its record consistent with item "
                     f"{max(1, number - 1)} and is checked by step {number % 7 + 1} of the run.")
        if number % 6 == 5:
            lines.append("")
    return "\n".join(lines) + "\n"


def write_home(repo: Path, kind: str) -> dict[str, int]:
    """Write the ``kind`` home ('long', 'small' or 'empty') under ``repo``/docs/shiploop; returns each file's size."""
    sizes = KINDS[kind]
    target = Path(repo) / "docs" / "shiploop"
    target.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, size in sizes.items():
        text = document(name, size)
        (target / name).write_text(text)
        written[name] = len(text)
    return written


def walk(kind: str, route: str = "inline", scenario: str = "delivery") -> list[dict]:
    """Every packet of the dry-run ``scenario`` over a ``kind`` home: ``{"stage", "kind", "file", "printed"}`` for each (``file``
    is the packet file, ``printed`` what emit prints for it: the whole text up to PRINT_LIMIT, else the head)."""
    _home, navigator, dry_run = _imports()
    found = []
    with tempfile.TemporaryDirectory(prefix="shiploop-home-") as temp:
        repo = Path(temp) / "repo"
        repo.mkdir()
        write_home(repo, kind)
        state = navigator.new_state(str(repo), "Inspect the SDLC graph with synthetic declarations.",
                                    improve_skill=str(dry_run.stage_loops.BUNDLED_IMPROVE_CARD), delegation=route)
        run = Path(temp) / "run"
        run.mkdir()
        for step in dry_run.scenarios()[scenario]["steps"]:
            stage = navigator.sequence_stage(state)
            action = navigator.current_action(state)
            text = navigator.render(dry_run.CORE, run, state)
            printed = text if len(text) <= navigator.PRINT_LIMIT else navigator.packet_head(
                dry_run.CORE, run, state, navigator.packet_path(run, state))
            found.append({"stage": stage, "kind": "improve" if stage == navigator.IMPROVE_STAGE else "producer",
                          "file": text.replace(temp, "TMP"), "printed": printed.replace(temp, "TMP")})
            if step.get("command", "done") == "finish-improve":
                state = navigator.finish_improve(state, state["active_improve"]["action_id"], step.get("receipt"),
                                                 step.get("final_result"))
            else:
                state = navigator.apply(state, action["id"], step.get("result", {"outcome": "done", "summary": "Synthetic."}))
    return found


def sizes(kind: str, route: str = "inline") -> dict:
    """The packet characters of a walk over a ``kind`` home: the total of the packet files, the total printed, and per stage."""
    packets = walk(kind, route)
    return {"kind": kind, "route": route, "packets": len(packets), "file_chars": sum(len(p["file"]) for p in packets),
            "printed_chars": sum(len(p["printed"]) for p in packets),
            "by_stage": [(p["stage"], len(p["file"]), len(p["printed"])) for p in packets]}


def normalised(text: str) -> str:
    """The text without what differs from one walk to the next: action and run ids, the request's tag, a run's start time."""
    text = re.sub(r"nav-[0-9a-f]{32}", "nav-ID", text)
    text = re.sub(r"(?<=ORIGINAL REQUEST )[0-9a-f]+|(?<=carrying tag )[0-9a-f]+", "TAG", text)
    return re.sub(r"run=nav-ID", "run=ID", text)


def fingerprints(kind: str, route: str = "inline") -> list[str]:
    """One hash per packet (file and printed text, ids and temporary paths normalised): equal before and after a change means the
    change left that home's packets byte-identical."""
    return [hashlib.sha256(normalised(p["file"] + "\0" + p["printed"]).encode()).hexdigest()[:16] for p in walk(kind, route)]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    kind = args[0] if args else "long"
    route = args[1] if len(args) > 1 else "inline"
    if kind not in KINDS:
        sys.stderr.write(__doc__)
        return 2
    found = sizes(kind, route)
    print(f"{kind} home, {route}: {found['packets']} packets, {found['file_chars']:,} file characters, "
          f"{found['printed_chars']:,} printed")
    for stage, whole, printed in found["by_stage"]:
        print(f"  {stage:20} {whole:7,} {printed:7,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
