#!/usr/bin/env python3
"""render_html.py: one self-contained HTML page that shows what ran when, and what interleaved.

Apparatus for docs/experiments/parallel-plan-execution-20261114. For each trial folder it draws a swim-lane timeline:
one lane per step (a bar from its start to its end, taken from the kit's ledger, the ground truth), one lane for the parent
and one per child agent the host's stream attributes (a mark per host event, by arrival time), marks for claims, ready
calls and refused attempts, and the merged event log beneath. Several trials share one time axis so a serial run and a
parallel run of the same plan can be read against each other. No script is needed to read it; a few lines of script add
log filters.

  render_html.py TRIAL... --out PAGE.html [--title TEXT]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dagkit  # noqa: E402
import score  # noqa: E402

CSS = """
:root{--bg:#fbfbfa;--panel:#ffffff;--ink:#1d2330;--muted:#5d6678;--line:#dfe3ea;--accent:#2f6fed;--ok:#1f9d6b;--bad:#d4412f;
--warn:#b7791f;--bar:#2f6fed;--bar-ink:#ffffff;--grid:#edf0f5;--chip:#eef2fb}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12151c;--panel:#1a1f2a;--ink:#e8ebf2;--muted:#9aa3b5;
--line:#2b3242;--accent:#7aa2ff;--ok:#49c796;--bad:#ff7a66;--warn:#e0b34f;--bar:#5b8cff;--bar-ink:#0e1220;--grid:#232a38;--chip:#232b3d}}
:root[data-theme=dark]{--bg:#12151c;--panel:#1a1f2a;--ink:#e8ebf2;--muted:#9aa3b5;--line:#2b3242;--accent:#7aa2ff;--ok:#49c796;
--bad:#ff7a66;--warn:#e0b34f;--bar:#5b8cff;--bar-ink:#0e1220;--grid:#232a38;--chip:#232b3d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:0}
.sub{color:var(--muted);margin:0 0 20px}.legend{display:flex;flex-wrap:wrap;gap:6px 16px;color:var(--muted);font-size:13px;margin:0 0 20px}
.legend span{display:inline-flex;align-items:center;gap:6px}.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:14px 14px 10px;margin:0 0 18px}.head{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;margin:0 0 10px}
.chip{background:var(--chip);border-radius:999px;padding:2px 10px;font-size:12.5px;white-space:nowrap}
.chip.ok{color:var(--ok)}.chip.bad{color:var(--bad)}.chip.strong{font-weight:600}
.svgwrap{overflow-x:auto}.svgwrap svg{display:block;min-width:720px;width:100%;height:auto}.legend svg{display:inline-block;flex:none}
svg text{fill:var(--ink);font:11px system-ui,sans-serif}svg .m{fill:var(--muted)}svg .grid{stroke:var(--grid);stroke-width:1}
svg .bar{fill:var(--bar)}svg .bar.fail{fill:var(--bad)}svg .bar.open{fill:var(--warn)}svg .barlabel{fill:var(--bar-ink);font-weight:600}
svg .lane{fill:none;stroke:var(--line)}svg .agentbar{fill:var(--accent);opacity:.22}svg .mark{fill:var(--muted)}svg .spawn{fill:var(--accent)}svg .ret{fill:var(--ok)}
svg .refused{stroke:var(--bad);stroke-width:1.6;fill:none}svg .claim{stroke:var(--accent);fill:none;stroke-width:1.4}
.group{margin:28px 0 10px;font-size:15px;color:var(--muted);font-weight:500}.note{color:var(--muted);font-size:12.5px;margin:6px 0 0}details{margin-top:10px}summary{cursor:pointer;color:var(--muted);font-size:13px}
.filters{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;margin:8px 0}table.log{border-collapse:collapse;width:100%;font-size:12.5px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.log th{text-align:left;color:var(--muted);font-weight:500;border-bottom:1px solid var(--line);
padding:2px 6px}.log td{padding:1px 6px;border-bottom:1px solid var(--grid);vertical-align:top}.log td.t{text-align:right;white-space:nowrap}
.log tr.L td.s{color:var(--accent)}.log tr.hidden{display:none}.nums{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:4px 14px;
margin:8px 0 0;font-size:12.5px;color:var(--muted)}.nums b{color:var(--ink);font-weight:600}
@media (max-width:640px){main{padding:16px 12px 48px}}
"""

JS = """
for (const box of document.querySelectorAll('.filters input')) box.addEventListener('change', () => {
  const card = box.closest('.card'); const on = new Set([...card.querySelectorAll('.filters input:checked')].map(b => b.value));
  for (const row of card.querySelectorAll('table.log tbody tr')) row.classList.toggle('hidden', !on.has(row.dataset.f));
});
"""


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def nice_step(span: float) -> float:
    for step in (1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600):
        if span / step <= 12:
            return float(step)
    return 900.0


def load(trial: Path) -> dict:
    trial = Path(trial)
    plan = json.loads((trial / "work" / "plan.json").read_text())
    events = dagkit.Run(trial / "work" / "run").events()
    inv = json.loads((trial / "invocation.json").read_text()) if (trial / "invocation.json").is_file() else {}
    view = score.host_view(trial, inv.get("host", ""))
    m = json.loads((trial / "score.json").read_text()) if (trial / "score.json").is_file() else score.score_trial(trial)
    native = score.native_agents(trial, inv.get("host", ""))["agents"]
    times = [e["ts"] for e in events] + [i["t"] for i in view if i["t"]] + [a["start"] for a in native if a.get("start")] + [a["end"] for a in native if a.get("end")]
    return {"trial": trial, "plan": plan, "events": events, "inv": inv, "view": view, "m": m, "native": native, "t0": min(times), "t1": max(times)}


def card(d: dict, span: float, uid: str) -> str:
    plan, events, view, m = d["plan"], d["events"], d["view"], d["m"]
    t0 = d["t0"]
    state = dagkit.derive(plan, events)
    actors = sorted({i["actor"] for i in view if i["actor"] != "parent" and i["t"]} | {a["actor"] for a in d["native"] if a.get("start")})
    lanes = ["parent"] + actors + [s["id"] for s in plan["steps"]]
    left, width, lane_h, pad = 96, 1000, 22, 26
    inner = width - left - 12
    height = pad + lane_h * len(lanes) + 24

    def x(t):
        return left + (t - t0) / span * inner
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Timeline of trial {esc(d["trial"].name)}">']
    step = nice_step(span)
    k = 0.0
    while k <= span + 1e-9:
        out.append(f'<line class="grid" x1="{x(t0 + k):.1f}" y1="{pad - 6}" x2="{x(t0 + k):.1f}" y2="{height - 22}"/>'
                   f'<text class="m" x="{x(t0 + k):.1f}" y="{height - 8}" text-anchor="middle">{k:g}s</text>')
        k += step
    for n, name in enumerate(lanes):
        y = pad + n * lane_h
        out.append(f'<rect class="lane" x="{left}" y="{y}" width="{inner}" height="{lane_h - 2}" rx="3"/>'
                   f'<text x="{left - 8}" y="{y + 14}" text-anchor="end">{esc(name)}</text>')
    row = {name: pad + n * lane_h for n, name in enumerate(lanes)}
    for a in d["native"]:
        if a.get("start") and a.get("end") and a["actor"] in row:
            tip = f'{a["actor"]} ({a.get("kind") or "sub-agent"}): {a["start"] - t0:.1f}s to {a["end"] - t0:.1f}s, the host\'s own record'
            out.append(f'<g><title>{esc(tip)}</title><rect class="agentbar" x="{x(a["start"]):.1f}" y="{row[a["actor"]] + 3}" '
                       f'width="{max(2.0, x(a["end"]) - x(a["start"])):.1f}" height="{lane_h - 8}" rx="3"/></g>')
    for s in plan["steps"]:
        item = state[s["id"]]
        if item["start"] is None:
            continue
        end = item["end"] if item["end"] is not None else d["t1"]
        cls = "fail" if item["state"] == "failed" else "open" if item["state"] == "running" else ""
        w = max(2.0, x(end) - x(item["start"]))
        y = row[s["id"]]
        out.append(f'<g><title>{esc(s["id"])}: {item["start"] - t0:.1f}s to {end - t0:.1f}s ({end - item["start"]:.1f}s), {esc(item["state"])}</title>'
                   f'<rect class="bar {cls}" x="{x(item["start"]):.1f}" y="{y + 2}" width="{w:.1f}" height="{lane_h - 6}" rx="3"/>'
                   + (f'<text class="barlabel" x="{x(item["start"]) + 5:.1f}" y="{y + 14}">{esc(s["id"])} {end - item["start"]:.0f}s</text>' if w > 52 else "")
                   + "</g>")
    for e in events:
        if e["kind"] == "claim" and e["step"] in row:
            out.append(f'<circle class="claim" cx="{x(e["ts"]):.1f}" cy="{row[e["step"]] + 10}" r="4"><title>claimed {esc(e["step"])} at {e["ts"] - t0:.1f}s</title></circle>')
        elif e["kind"] == "refused" and e["step"] in row:
            cx, cy = x(e["ts"]), row[e["step"]] + 10
            out.append(f'<g class="refused"><title>refused {esc(e["step"])} ({esc(e["detail"].get("category"))}) at {e["ts"] - t0:.1f}s</title>'
                       f'<path d="M{cx - 4:.1f} {cy - 4} L{cx + 4:.1f} {cy + 4} M{cx + 4:.1f} {cy - 4} L{cx - 4:.1f} {cy + 4}"/></g>')
        elif e["kind"] == "ready":
            out.append(f'<line class="grid" x1="{x(e["ts"]):.1f}" y1="{row["parent"] + 3}" x2="{x(e["ts"]):.1f}" y2="{row["parent"] + lane_h - 5}" '
                       f'style="stroke:var(--accent)"><title>ready call at {e["ts"] - t0:.1f}s</title></line>')
    for i in view:
        if not i["t"] or i["kind"] in ("usage", "system"):
            continue
        lane = row.get(i["actor"], row["parent"])
        cx, cy = x(i["t"]), lane + 10
        tip = f'{i["kind"]} {i["name"]} {i["text"][:90]} at {i["t"] - t0:.1f}s'.replace("\n", " ")
        if i["kind"] == "spawn":
            out.append(f'<path class="spawn" d="M{cx:.1f} {cy - 5} L{cx + 5:.1f} {cy + 4} L{cx - 5:.1f} {cy + 4} Z"><title>{esc(tip)}</title></path>')
        elif i["kind"] in ("return", "wait"):
            out.append(f'<path class="{"ret" if i["kind"] == "return" else "mark"}" d="M{cx:.1f} {cy - 4} L{cx + 4:.1f} {cy} L{cx:.1f} {cy + 4} L{cx - 4:.1f} {cy} Z"><title>{esc(tip)}</title></path>')
        else:
            out.append(f'<circle class="mark" cx="{cx:.1f}" cy="{cy}" r="2"><title>{esc(tip)}</title></circle>')
    out.append("</svg>")
    ident = m["identity"]
    tag = "+v2" if "multi_agent_v2" in (ident.get("enabled_features") or []) else ""
    chips = [f'<span class="chip strong">{esc(ident.get("host"))}{tag} {esc(ident.get("version"))}</span>',
             f'<span class="chip">{esc(ident.get("model"))} {esc(ident.get("effort") or "")}</span>',
             f'<span class="chip">arm {esc(ident.get("arm"))}, packet {esc(ident.get("variant") or "N")}</span>',
             f'<span class="chip">plan {esc(ident.get("plan"))}</span>',
             f'<span class="chip {"ok" if m.get("valid") else "bad"}">{"valid" if m.get("valid") else "not valid"}</span>',
             f'<span class="chip">peak {m.get("peak_concurrency")}</span>',
             f'<span class="chip">mechanism {esc(m["mechanism"]["kind"])}</span>']
    t = m["timings"]
    nums = [("makespan", m.get("makespan_s")), ("critical path", m.get("critical_path_declared_s")), ("serial sum", m.get("serial_sum_declared_s")),
            ("launch to first start", t.get("launch_to_first_start_s")), ("launch to verified", t.get("launch_to_verified_s")),
            ("launch to exit", t.get("launch_to_exit_s")), ("refused", m.get("refused")), ("verify", m.get("verify")),
            ("tail since final report", m["process"].get("tail_from_final_report_s")),
            ("input tokens, all contexts", m["tokens"].get("input_all")), ("of which the parent", m["tokens"].get("parent_input_all")),
            ("output tokens", m["tokens"].get("output_all"))]
    if m.get("answers"):
        nums.insert(0, ("answers correct", f'{m["answers"]["correct"]} of {m["answers"]["total"]}'))
    numhtml = "".join(f'<span>{esc(k)} <b>{esc(v if v is not None else "not recorded")}</b></span>' for k, v in nums)
    rows = []
    for e in events:
        extra = {k: v for k, v in e["detail"].items() if k in ("reason", "category", "seconds", "line")}
        rows.append((e["ts"], 0, f'L|{e["kind"]}', "L", "ledger", e["kind"], e["step"] or "-", json.dumps(extra) if extra else ""))
    for i in view:
        if i["t"] and i["kind"] != "usage":
            rows.append((i["t"], 1, f'H|{i["kind"]}', "H", i["actor"], i["kind"], i["name"] or "-", (i["text"] or "").replace("\n", " ")[:160]))
    rows.sort(key=lambda r: (r[0], r[1]))
    log = "".join(f'<tr class="{r[3]}" data-f="{"L" if r[3] == "L" else "H"}"><td class="t">+{r[0] - t0:.3f}</td><td class="s">{r[3]}</td>'
                  f'<td>{esc(r[4])}</td><td>{esc(r[5])}</td><td>{esc(r[6])}</td><td>{esc(r[7])}</td></tr>' for r in rows[:1500])
    more = f'<p class="note">The first 1,500 of {len(rows)} events are shown.</p>' if len(rows) > 1500 else ""
    return (f'<section class="card" id="{uid}"><div class="head"><h2>{esc(d["trial"].name)}</h2>{"".join(chips)}</div>'
            f'<div class="svgwrap">{"".join(out)}</div><div class="nums">{numhtml}</div>'
            f'<details><summary>Event log, {len(rows)} events, seconds from the first event</summary>'
            f'<div class="filters"><label><input type="checkbox" value="L" checked> kit ledger (L)</label>'
            f'<label><input type="checkbox" value="H" checked> host events (H)</label></div>'
            f'<table class="log"><thead><tr><th>t</th><th>src</th><th>actor</th><th>kind</th><th>name</th><th>detail</th></tr></thead>'
            f'<tbody>{log}</tbody></table>{more}</details></section>')


def page(trials: list, title: str) -> str:
    data = [load(Path(t)) for t in trials]
    kinds = {i["kind"] for d in data for i in d["view"]} | {e["kind"] for d in data for e in d["events"]}
    states = {s for d in data for s in d["m"]["states"].values()}
    items = [('<svg width="26" height="12"><rect x="0" y="1" width="26" height="10" rx="3" style="fill:var(--bar)"/></svg>a step ran (kit ledger)', True),
             ('<svg width="26" height="12"><rect x="0" y="1" width="26" height="10" rx="3" style="fill:var(--accent);opacity:.22"/></svg>a sub-agent was alive (the host\'s own record)', any(d["native"] for d in data)),
             ('<svg width="26" height="12"><rect x="0" y="1" width="26" height="10" rx="3" style="fill:var(--bad)"/></svg>a step failed', "failed" in states),
             ('<svg width="12" height="12"><path d="M6 1 L11 10 L1 10 Z" style="fill:var(--accent)"/></svg>a sub-agent was started', "spawn" in kinds),
             ('<svg width="12" height="12"><path d="M6 1 L11 6 L6 11 L1 6 Z" style="fill:var(--ok)"/></svg>a collection returned', "return" in kinds),
             ('<svg width="12" height="12"><circle cx="6" cy="6" r="2.4" style="fill:var(--muted)"/></svg>another host event', True),
             ('<svg width="12" height="12"><circle cx="6" cy="6" r="4" style="fill:none;stroke:var(--accent);stroke-width:1.4"/></svg>a step was claimed', "claim" in kinds),
             ('<svg width="12" height="12"><path d="M2 2 L10 10 M10 2 L2 10" style="stroke:var(--bad);stroke-width:1.6;fill:none"/></svg>a refused attempt', "refused" in kinds)]
    legend = '<p class="legend">' + "".join(f"<span>{html_}</span>" for html_, shown in items if shown) + "</p>"
    groups: dict = {}
    for d in data:
        groups.setdefault(d["m"]["identity"].get("host"), []).append(d)
    cards, n = "", 0
    for host, ds in groups.items():
        gspan = max(max(d["t1"] - d["t0"], 1.0) for d in ds)
        cards += f'<h2 class="group">{esc(host)}: its trials share one time axis of {gspan:.0f} s</h2>'
        cards += "".join(card(d, gspan, f"t{n + i}") for i, d in enumerate(ds))
        n += len(ds)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main><h1>{esc(title)}</h1>'
            f'<p class="sub">Trials of one host share one time axis, in seconds from each trial\'s first event. Bars come from the kit\'s ledger; '
            f'marks come from the host\'s own event stream by arrival time. A bar that is not under a sub-agent lane means the host does not say who ran it.</p>'
            f'{legend}{cards}<script>{JS}</script></main></body></html>')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trials", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="Parallel plan execution: what ran when")
    args = parser.parse_args(argv)
    Path(args.out).write_text(page(args.trials, args.title))
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
