"""Segment ShipLoop packet files into the navigator's blocks (heuristic, by line prefix) and measure them.

Usage: python3 -I segment.py <packets_dir> <out_json> [<debug_dir>]
Read-only on the packets; writes only <out_json> (and labelled copies in <debug_dir> when given).
Block names follow shiploop_navigator._producer_blocks; tiers follow its P0/P1/lookup/chrome/quoted/file split.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TIER = {
    "delegation": "file", "top": "P0", "goal": "P0", "step": "P1", "loop": "P0", "status": "P0",
    "duties": "P0", "craft": "P0", "backchain": "P0", "rules": "P0", "stage-input": "P1", "result": "P0",
    "references": "lookup", "guides": "lookup", "builds-on": "lookup", "chrome": "chrome",
    "quoted-knowledge": "quoted", "quoted-handoff": "quoted",
    "run-context": "file", "last-accepted": "file", "deltas": "file", "discovery-links": "file", "pass-halt": "file",
}
STARTS = [
    ("Continue in this context", "delegation"),
    ("ShipLoop navigator |", "top"),
    ("Goal:", "goal"),
    ("Do this stage inside the /until-loop", "step"),
    ("Until Loop (no iteration limit", "loop"),
    ("Keepalive marker:", "status"),
    ("Current stage guidance:", "duties"),
    ("Code craft. Write for", "craft"),
    ("Optional: for a material", "backchain"),
    ("Backchain: the route's paragraph", "backchain"),
    ("RULES (", "rules"),
    ("Result template:", "result"),
    ("References (symbols", "references"),
    ("Results this stage builds on", "builds-on"),
    ("Progress view:", "chrome"),
    ("Knowledge files this stage reads", "quoted-knowledge"),
    ("Handed off by earlier stages", "quoted-handoff"),
    ("This action's pass log", "pass-halt"),
    ("Halt (terminal", "pass-halt"),
    ("State: RUN/state.md", "run-context"),
    ("Last accepted transition", "last-accepted"),
    ("Recursive discovery policy", "discovery-links"),
]
DELTA_PREFIXES = ("This stage keeps these", "ShipLoop refuses ", "If this stage changes HOME/", "Repository knowledge home",
                  "Inherited learnings", "Lessons from earlier runs", "Spec and architecture changes since",
                  "HOME/spec.md: new since", "HOME/architecture.md: new since", "HOME/environment.md: new since",
                  "On done ShipLoop checks these files")
FILE_ZONE = ("pass-halt", "run-context", "last-accepted", "discovery-links", "deltas")
GUIDE_LINE = re.compile(r"^[A-Z][A-Za-z0-9 ,/()'.-]+: (GUIDES/|/\S+/references/|python3 )")
NAV = re.compile(r"nav-[0-9a-f]{32}")


def segment(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    section = "top"
    file_zone = False
    summary_open = False
    summary_done = False
    for line in text.split("\n"):
        new = None
        for prefix, name in STARTS:
            if line.startswith(prefix):
                new = name
                break
        if new is None:
            if file_zone and line.startswith(DELTA_PREFIXES):
                new = "deltas"
            elif section == "rules" and line and not line.startswith(("- ", "  ")):
                new = "stage-input"
            elif section == "references" and GUIDE_LINE.match(line) and not line.startswith(("HOME =", "WORKTREE =")):
                new = "guides"
            elif section == "guides" and line.startswith(("Knowledge files:", "Run records:")):
                new = "references"
            elif section == "last-accepted":
                if line.startswith("----- BEGIN LAST ACCEPTED SUMMARY"):
                    summary_open = True
                elif line.startswith("----- END LAST ACCEPTED SUMMARY"):
                    summary_open, summary_done = False, True
                elif summary_done and line and not line.startswith(("- ", "Evidence references")):
                    new = "run-context"
            elif section == "deltas" and line and not line.startswith(("  ", "- ", "|")):
                new = "run-context"
        if new is not None:
            if new == "last-accepted":
                summary_open, summary_done = False, False
            if new in FILE_ZONE:
                file_zone = True
            section = new
        out.append((section, line))
    return out


def norm(line: str) -> str:
    line = NAV.sub("nav-X", line)
    return re.sub(r"revision \d+|rev=\d+", "rev", line)


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    debug = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    packets = sorted(p for p in src.glob("*.packet.md") if "-improve-" not in p.name)
    rows = []
    line_packets: dict[str, set] = defaultdict(set)
    segs_of = {}
    for p in packets:
        text = p.read_text()
        segs = segment(text)
        segs_of[p.name] = segs
        if debug:
            debug.mkdir(exist_ok=True)
            (debug / p.name).write_text("\n".join(f"{s[:14]:14}| {l}" for s, l in segs))
        sizes: Counter = Counter()
        for sec, line in segs:
            sizes[sec] += len(line.encode()) + 1
            k = norm(line)
            if k.strip():
                line_packets[k].add(p.name)
        stage = re.sub(r"^\d+-", "", p.name.replace(".packet.md", ""))
        tiers: Counter = Counter()
        for sec, b in sizes.items():
            tiers[TIER[sec]] += b
        rows.append({"packet": p.name, "stage": stage, "bytes": len(text.encode()), "sections": dict(sizes),
                     "tiers": dict(tiers)})
    n = len(packets)
    for r in rows:
        every = half = 0
        by_sec: Counter = Counter()
        for sec, line in segs_of[r["packet"]]:
            k = norm(line)
            if not k.strip():
                continue
            c = len(line_packets[k])
            b = len(line.encode()) + 1
            if c == n:
                every += b
            if c >= n / 2:
                half += b
                by_sec[sec] += b
        r["bytes_in_every_packet"] = every
        r["bytes_in_half_or_more"] = half
        r["common_by_section"] = dict(by_sec)
    top = sorted(([len(v), len(k), k[:200]] for k, v in line_packets.items() if len(v) >= 8 and len(k) > 50),
                 key=lambda t: -(t[0] * t[1]))[:60]
    json.dump({"n_packets": n, "rows": rows, "top_repeated_lines": top}, dst.open("w"), indent=1)


if __name__ == "__main__":
    main()
