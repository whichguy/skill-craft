"""Per-packet section sizes (characters), an estimated printed head, and cross-packet repetition.

Usage: python3 -I measure.py <tools_dir> <packets_dir> <out_json>
"""
import json
import re
import sys
from collections import Counter, defaultdict, OrderedDict
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import segment as seg  # noqa: E402

PRINT_LIMIT, HEAD_LIMIT, HEAD_REQUIRED_END = 16_000, 20_000, 19_500
REQUIRED = {"P0", "P1"}
OPTIONAL = {"lookup", "chrome", "quoted"}
GROUPS = OrderedDict([
    ("instruction_frame", ["top", "goal", "loop", "status", "rules", "chrome", "pass-halt", "delegation"]),
    ("stage_method", ["duties", "backchain", "craft"]),
    ("step_and_stage_input", ["step", "stage-input"]),
    ("result_contract", ["result"]),
    ("locators", ["references", "guides", "builds-on", "run-context", "discovery-links"]),
    ("quoted_state", ["quoted-knowledge", "quoted-handoff", "last-accepted", "deltas"]),
])


def blocks(segs):
    """Consecutive runs of one section, in order: [(section, text)]."""
    out = []
    for sec, line in segs:
        if out and out[-1][0] == sec:
            out[-1][1].append(line)
        else:
            out.append((sec, [line]))
    return [(s, "\n".join(ls)) for s, ls in out]


def head_estimate(segs):
    text = "\n".join(l for _, l in segs)
    if len(text) <= PRINT_LIMIT:
        return len(text), "whole", []
    bl = blocks(segs)
    req = sum(len(t) + 1 for s, t in bl if seg.TIER[s] in REQUIRED)
    trailing = any(seg.TIER[s] in REQUIRED for s, _ in bl[[i for i, (s, _) in enumerate(bl) if seg.TIER[s] in OPTIONAL][0]:])
    limit = HEAD_REQUIRED_END if trailing else HEAD_LIMIT
    used, dropped, stop = req, [], False
    for s, t in bl:
        if seg.TIER[s] in OPTIONAL:
            if stop or used + len(t) + 1 > limit:
                stop = True
                dropped.append(s)
                continue
            used += len(t) + 1
    return used, "head", sorted(set(dropped))


def main():
    tools, src, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    packets = sorted(p for p in src.glob("*.packet.md") if "-improve-" not in p.name)
    rows, segs_of = [], {}
    line_where: dict[str, set] = defaultdict(set)
    for p in packets:
        text = p.read_text()
        segs = seg.segment(text)
        segs_of[p.name] = segs
        sizes = Counter()
        for s, l in segs:
            sizes[s] += len(l) + 1
            k = seg.norm(l).strip()
            if k:
                line_where[k].add(p.name)
        groups = {g: sum(sizes.get(s, 0) for s in ss) for g, ss in GROUPS.items()}
        h, mode, dropped = head_estimate(segs)
        rows.append({"packet": p.name, "chars": len(text), "sections": dict(sizes), "groups": groups,
                     "printed_estimate": h, "printed_mode": mode, "head_drops": dropped})
    n = len(packets)
    for r in rows:
        every = half = 0
        sec_common = Counter()
        for s, l in segs_of[r["packet"]]:
            k = seg.norm(l).strip()
            if not k:
                continue
            c = len(line_where[k])
            if c == n:
                every += len(l) + 1
            if c >= n / 2:
                half += len(l) + 1
                sec_common[s] += len(l) + 1
        r["chars_in_all_packets"] = every
        r["chars_in_half_or_more_packets"] = half
        r["common_by_section"] = dict(sec_common)
    total = sum(r["chars"] for r in rows)
    agg = Counter()
    for r in rows:
        for g, b in r["groups"].items():
            agg[g] += b
    sec_agg = Counter()
    for r in rows:
        for s, b in r["sections"].items():
            sec_agg[s] += b
    top = sorted(([len(v), len(k), k[:220]] for k, v in line_where.items() if len(v) >= 8 and len(k) >= 40),
                 key=lambda t: -(t[0] * t[1]))[:50]
    json.dump({"n_packets": n, "total_chars": total, "groups_total": dict(agg), "sections_total": dict(sec_agg),
               "rows": rows, "top_repeated_lines": top}, dst.open("w"), indent=1)


if __name__ == "__main__":
    main()
