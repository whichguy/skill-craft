#!/usr/bin/env python3
"""The results page: report.py's report.json drawn as one HTML page (no model, no network).

    python3 page.py REPORT_DIR OUT.html [--judge SCORE.json] [--note TEXT]

Static HTML with inline SVG charts drawn to scale from the numbers in report.json; a small script adds hover tips.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

CASES = (("shared-expenses", "Shared expenses", "new service"), ("node-chess-engine", "Chess engine", "new library"),
         ("ticket-assignment", "Ticket assignment", "change to a 1,700-line service"),
         ("grokbot-local", "Grokbot-local", "new chat app with a page"))
ARMS = (("shiploop", "ShipLoop"), ("ratchet", "Ratchet"))
READINGS = (("R1 time", "Time"), ("R2 tokens", "Tokens"), ("R3 breadth", "Breadth"), ("R4 depth", "Depth"),
            ("R5 coverage", "Coverage"), ("R6 documentation", "Docs"), ("R7 code quality", "Code (judge)"))

STYLE = """
/* Layout: one reading column; a scorecard first, then cost, then each result, then limits. */
:root {
  --bg: #f7f8f9; --surface: #ffffff; --fg: #14171a; --muted: #5a6470; --rule: #dde1e6; --soft: #eef1f4;
  --ship: #2a78d6; --ratchet: #eb6834; --none: #8a939c;
  --font-text: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-head: "Space Grotesk", "Inter", system-ui, sans-serif;
  --font-data: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121416; --surface: #1a1d20; --fg: #eef0f2; --muted: #a3acb6; --rule: #30353b; --soft: #22262a;
    --ship: #3987e5; --ratchet: #d95926; --none: #7d868f; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #121416; --surface: #1a1d20; --fg: #eef0f2; --muted: #a3acb6; --rule: #30353b; --soft: #22262a;
  --ship: #3987e5; --ratchet: #d95926; --none: #7d868f; color-scheme: dark;
}
body { background: var(--bg); color: var(--fg); font-family: var(--font-text); font-size: 15px; line-height: 1.55; }
.page { max-width: 1040px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px));
        padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 32px 64px; display: grid; gap: 40px; }
h1, h2, h3 { font-family: var(--font-head); text-wrap: balance; margin: 0; letter-spacing: -0.01em; }
h1 { font-size: 34px; line-height: 1.15; }
h2 { font-size: 22px; }
h3 { font-size: 16px; }
p { margin: 0; max-width: 68ch; }
.eyebrow { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
.stack { display: grid; gap: 12px; }
.verdict { font-size: 19px; font-weight: 600; }
.meta { color: var(--muted); font-size: 13px; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-weight: 600; color: var(--muted); font-size: 12px; letter-spacing: 0.02em; }
tr:last-child td { border-bottom: none; }
td.num { font-family: var(--font-data); text-align: right; white-space: nowrap; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px; font-size: 12px;
        white-space: nowrap; border: 1px solid var(--rule); color: var(--fg); background: var(--soft); }
.chip::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--none); }
.chip.ship::before { background: var(--ship); }
.chip.ratchet::before { background: var(--ratchet); }
.chip.none { color: var(--muted); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr)); gap: 24px; }
.chart { background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 16px; display: grid; gap: 8px; min-width: 0; }
.chart svg { width: 100%; height: auto; display: block; }
.chart .note { font-size: 12px; color: var(--muted); }
svg text { fill: var(--fg); font-family: var(--font-text); font-size: 12px; }
svg text.muted { fill: var(--muted); }
svg text.value { font-family: var(--font-data); font-size: 11.5px; }
svg .bar-ship { fill: var(--ship); }
svg .bar-ratchet { fill: var(--ratchet); }
svg .tick { stroke: var(--fg); stroke-width: 2; }
svg .base { stroke: var(--rule); stroke-width: 1; }
svg rect.hit { fill: transparent; cursor: default; }
.tip { position: fixed; pointer-events: none; background: var(--fg); color: var(--bg); font-size: 12px; padding: 6px 8px;
       border-radius: 6px; max-width: 260px; z-index: 20; }
ul.limits { margin: 0; padding-left: 20px; display: grid; gap: 6px; max-width: 72ch; }
code { font-family: var(--font-data); font-size: 12.5px; }
a { color: var(--ship); }
"""

TIP = """
<script>
(() => {
  const tip = document.createElement('div'); tip.className = 'tip'; tip.hidden = true; document.body.appendChild(tip);
  document.querySelectorAll('[data-tip]').forEach((el) => {
    el.addEventListener('mousemove', (e) => { tip.textContent = el.dataset.tip; tip.hidden = false;
      tip.style.left = Math.min(e.clientX + 12, innerWidth - 270) + 'px'; tip.style.top = (e.clientY + 12) + 'px'; });
    el.addEventListener('mouseleave', () => { tip.hidden = true; });
  });
})();
</script>
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def num(value, kind="n") -> str:
    if value is None:
        return "–"
    if kind == "pct":
        return f"{100 * value:.0f}%"
    if kind == "k":
        return f"{value / 1000:,.0f}k"
    if kind == "m":
        return f"{value / 1e6:.1f}M"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{value:,}"


def chip(value) -> str:
    if value == "shiploop":
        return '<span class="chip ship">ShipLoop ahead</span>'
    if value == "ratchet":
        return '<span class="chip ratchet">Ratchet ahead</span>'
    if value == "not measured":
        return '<span class="chip none">not measured</span>'
    return '<span class="chip none">no difference</span>'


def bars(title: str, note: str, rows: list[tuple[str, float | None, float | None, float | None]], kind: str, unit: str,
         maximum: float | None = None, labels: list[tuple[str, str]] | None = None) -> str:
    """Paired horizontal bars, one pair per case: (case label, ShipLoop value, Ratchet value, Ratchet first-build mark)."""
    values = [v for _, a, b, f in rows for v in (a, b, f) if v is not None]
    top = maximum or (max(values) if values else 1) or 1
    label_w, bar_w, row_h, bar_h = 150, 330, 46, 14
    width, height = label_w + bar_w + 70, len(rows) * row_h + 8
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    for index, (label, ship, ratchet, first) in enumerate(rows):
        y = 4 + index * row_h
        parts.append(f'<text x="0" y="{y + 18}">{esc(label)}</text>')
        for offset, (arm, value, css) in enumerate((("ShipLoop", ship, "bar-ship"), ("Ratchet", ratchet, "bar-ratchet"))):
            by = y + 4 + offset * (bar_h + 4)
            length = 0 if value is None else max(2, bar_w * value / top)
            shown = labels[index][offset] if labels else num(value, kind)
            tip = f"{label}, {arm}: {shown}{unit}"
            if arm == "Ratchet" and first is not None:
                tip += f" (first build {num(first, kind)}{unit})"
            parts.append(f'<rect class="{css}" x="{label_w}" y="{by}" width="{length:.1f}" height="{bar_h}" rx="3"/>')
            if arm == "Ratchet" and first is not None:
                fx = label_w + bar_w * first / top
                parts.append(f'<line class="tick" x1="{fx:.1f}" x2="{fx:.1f}" y1="{by - 2}" y2="{by + bar_h + 2}"/>')
            parts.append(f'<text class="value" x="{label_w + length + 6:.1f}" y="{by + bar_h - 3}">{esc(shown)}</text>')
            parts.append(f'<rect class="hit" x="0" y="{by - 2}" width="{width}" height="{bar_h + 4}" data-tip="{esc(tip)}"/>')
        parts.append(f'<line class="base" x1="{label_w}" x2="{label_w}" y1="{y}" y2="{y + 2 * bar_h + 10}"/>')
    parts.append("</svg>")
    return (f'<figure class="chart"><h3>{esc(title)}</h3>' + "".join(parts) +
            (f'<figcaption class="note">{esc(note)}</figcaption>' if note else "") + "</figure>")


DEEP_CASES = (("expenses", "Shared expenses"), ("chess", "Chess engine"), ("tickets", "Ticket assignment"), ("grokbot", "Grokbot"))
DEEP_ROWS = (("Stated requirements built", lambda f: f"{f['built']} of {f['stated']}"),
             ("Tests proved by breaking the behaviour", lambda f: f"{f['proved']} of {f['proved_of']}"),
             ("Unsaid points handled", lambda f: f"{f['handled']} of {f['unstated']}"),
             ("Unsaid points told in delivered documents", lambda f: f"{f['told']} of {f['unstated']}"),
             ("Defects that reproduce: medium (low)", lambda f: f"{f['defects']} ({f['defects_low']})"))


def side(pair: dict | None, first: str, names: dict) -> str:
    """A chip for the better feature of a pair: the ShipLoop side blue, the Ratchet side orange, grey for neither."""
    if not pair:
        return '<span class="chip none">not judged</span>'
    better = pair.get("better")
    if better is None:
        return '<span class="chip none">no difference shown</span>'
    return f'<span class="chip {"ship" if better == first else "ratchet"}">{esc(names[better])}</span>'


def readings_table(facts: dict, names: dict) -> str:
    head = "".join(f"<th>{esc(names[point])}</th>" for point in "SFL")
    body = "".join(f"<tr><td>{esc(label)}</td>" + "".join(f"<td class='num'>{esc(show(facts[point]))}</td>" for point in "SFL") + "</tr>"
                   for label, show in DEEP_ROWS)
    return f'<div class="table-wrap"><table><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def deep_sections(deep: dict, costs: dict | None) -> list[str]:
    """Two sections from the deep judge's deep.json: the twelve products, and the clean ShipLoop runs with one look and
    one fix (journal sections 12 and 15)."""
    out = []
    names = {"S": "ShipLoop", "F": "Ratchet, first build", "L": "Ratchet, final"}
    rows = []
    for case, label in DEEP_CASES:
        entry = deep.get(case)
        if not entry:
            continue
        pairs = entry["pairs"]
        rows.append(f"<tr><td><strong>{esc(label)}</strong></td><td>{side(pairs.get('S-L'), 'S', names)}</td>"
                    f"<td>{side(pairs.get('S-F'), 'S', names)}</td><td>{side(pairs.get('F-L'), 'F', names)}</td>"
                    f"<td>{'yes' if entry['nearly_competitive'] else 'no'}</td></tr>")
    if rows:
        out.append('<section class="stack"><h2>A deeper judge: each product run and checked item by item</h2>'
                   '<p>Every product was audited by running it against a list written without seeing any product: what the '
                   'request states, and what it leaves unsaid that a customer would care about. Every disagreement and every '
                   'reported defect was then tried on all three products of a case, and two judges of different model families '
                   'read the audits. Ratchet\'s first build costs the same as ShipLoop\'s whole delivery.</p>'
                   '<div class="table-wrap"><table><thead><tr><th>Case</th><th>ShipLoop against Ratchet\'s final</th>'
                   '<th>ShipLoop against Ratchet\'s first build</th><th>Ratchet: first build against final</th>'
                   '<th>ShipLoop nearly competitive</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
                   '<p class="meta">The chip names the better feature of the pair by rules fixed before any product was read: '
                   'ahead on at least two more of six readings, or fewer serious failures.</p>')
        for case, label in DEEP_CASES:
            if case in deep:
                out.append(f"<h3>{esc(label)}</h3>" + readings_table(deep[case]["facts"], names))
        out.append("</section>")
    clean = {"S": "Fresh ShipLoop + look + fix", "F": "Fresh ShipLoop only", "L": "Ratchet, final (audited again)"}
    rows, tables, times = [], [], []
    for case, label in DEEP_CASES:
        entry = deep.get(f"{case}-clean")
        if not entry:
            continue
        pairs = entry["pairs"]
        cost = (costs or {}).get(case) or {}
        total = sum(cost.get(name) or 0 for name in ("run", "look", "fix")) or None
        if total:
            times.append((label, total, cost.get("ratchet"), cost.get("run")))
        rows.append(f"<tr><td><strong>{esc(label)}</strong></td><td>{side(pairs.get('S-L'), 'S', clean)}</td>"
                    f"<td>{side(pairs.get('S-F'), 'S', clean)}</td><td>{side(pairs.get('F-L'), 'F', clean)}</td>"
                    f"<td class='num'>{num(total)} of {num(cost.get('ratchet'))} min</td></tr>")
        tables.append(f"<h3>{esc(label)}</h3>" + readings_table(entry["facts"], clean))
    if rows:
        out.append('<section class="stack"><h2>Clean runs: ShipLoop, then one look, then one fix</h2>'
                   '<p>A fresh ShipLoop run of each case from scratch (ShipLoop 2.6.0), one short look at the running product by '
                   'the builder\'s model that writes down what falls short, and one fix pass by Opus at extra-high effort. All '
                   'three products of a case were audited afresh in the same round; Ratchet\'s final is last night\'s single '
                   'run.</p><div class="table-wrap"><table><thead><tr><th>Case</th><th>With look and fix, against Ratchet\'s final</th>'
                   '<th>With look and fix, against ShipLoop alone</th><th>ShipLoop alone, against Ratchet\'s final</th>'
                   '<th>Minutes</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")
        if times:
            out.append('<div class="charts">' + bars("Minutes: fresh run, look and fix together", "The tick: the fresh ShipLoop run alone. "
                                                     "Ratchet's bar is its whole run.", times, "n", " min") + "</div>")
        out.append("".join(tables) + '<p class="meta">One judge (Opus) for these cases. The fixer is a stronger model than either '
                   "builder; a fresh run and a newer ShipLoop version changed together.</p></section>")
    return out


def build(report: dict, judge: dict | None, note: str | None, deep: dict | None = None, costs: dict | None = None,
          verdict: str | None = None) -> str:
    facts, readings, overall = report["facts"], report["readings"], report["overall"]
    f = lambda case, arm: (facts.get(case) or {}).get(arm) or {}
    label = {case: name for case, name, _ in CASES}
    out = ['<title>Ratchet or ShipLoop?</title>', '<meta name="claude:viewport-fit-sides" content="cover">',
           '<link rel="preconnect" href="https://fonts.googleapis.com">',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&display=swap">',
           f"<style>{STYLE}</style>", '<main class="page">']
    out.append('<header class="stack"><div class="eyebrow">Head-to-head · four cases · one run each</div>'
               '<h1>Ratchet or ShipLoop?</h1>'
               f'<p class="verdict">{esc(verdict or overall["verdict"].capitalize() + ".")}</p>')
    if note:
        out.append(f"<p>{esc(note)}</p>")
    out.append('<p class="meta">Each arm ran on its own in a new Git repository, on Codex <code>gpt-6.2-sol</code> at medium '
               'effort, from one checkout: ShipLoop 2.4.1 through the E2E harness, Ratchet through the pilot loop with its '
               'reworded specification text. Margins for “ahead” were registered before any run.</p>'
               '<div class="legend"><span><span class="swatch" style="background:var(--ship)"></span>ShipLoop</span>'
               '<span><span class="swatch" style="background:var(--ratchet)"></span>Ratchet</span>'
               '<span>▏ Ratchet at its first build</span></div></header>')
    if deep:
        out += deep_sections(deep, costs)
        out.append('<section class="stack"><h2>The first instruments</h2><p class="meta">What follows is the first round of '
                   "measures, by script, on the eight original runs.</p></section>")
    # scorecard
    out.append('<section class="stack"><h2>Scorecard</h2><p class="meta">Who is ahead on each measure, by the registered '
               'margins. Time and tokens are cost; the other five are results.</p><div class="table-wrap"><table>'
               '<thead><tr><th>Case</th>' + "".join(f"<th>{esc(name)}</th>" for _, name in READINGS) + "</tr></thead><tbody>")
    for case, name, kind in CASES:
        if case not in readings:
            continue
        cells = "".join(f"<td>{chip(readings[case].get(key))}</td>" for key, _ in READINGS)
        out.append(f'<tr><td><strong>{esc(name)}</strong><br><span class="meta">{esc(kind)}</span></td>{cells}</tr>')
    ahead = overall["quality_cells_ahead"]
    out.append(f'</tbody></table></div><p class="meta">Result cells ahead: ShipLoop {ahead["shiploop"]}, Ratchet '
               f'{ahead["ratchet"]}. Rule: an arm produces better results if it is ahead in at least three more result '
               'cells and behind on breadth in no case.</p></section>')
    # cost
    rows_t = [(label[c], f(c, "shiploop").get("minutes"), f(c, "ratchet").get("minutes"), f(c, "ratchet").get("first_build_minutes"))
              for c, _, _ in CASES if c in facts]
    rows_o = [(label[c], f(c, "shiploop").get("output"), f(c, "ratchet").get("output"), f(c, "ratchet").get("first_build_output"))
              for c, _, _ in CASES if c in facts]
    out.append('<section class="stack"><h2>What each cost</h2><div class="charts">')
    out.append(bars("Minutes, start to finish", "Ratchet's tick: minutes to its first build.", rows_t, "n", " min"))
    out.append(bars("Output tokens", "From the Codex rollouts of every session. Ratchet's tick: through its first build.",
                    rows_o, "k", ""))
    out.append("</div></section>")
    # results
    share = lambda row, key: (row.get(key) / row.get("held_out_of")) if row.get(key) is not None and row.get("held_out_of") else None
    held = [(label[c], share(f(c, "shiploop"), "held_out"), share(f(c, "ratchet"), "held_out"),
             share(f(c, "ratchet"), "first_build_held_out")) for c, _, _ in CASES if c in facts]
    held_labels = [(f"{num(f(c, 'shiploop').get('held_out'))} of {num(f(c, 'shiploop').get('held_out_of'))}",
                    f"{num(f(c, 'ratchet').get('held_out'))} of {num(f(c, 'ratchet').get('held_out_of'))}")
                   for c, _, _ in CASES if c in facts]
    faults = [(label[c], f(c, "shiploop").get("faults_own"), f(c, "ratchet").get("faults_own"), None) for c, _, _ in CASES if c in facts]
    cover = [(label[c], f(c, "shiploop").get("line_coverage"), f(c, "ratchet").get("line_coverage"), None) for c, _, _ in CASES if c in facts]
    docs = [(label[c], f(c, "shiploop").get("docs_share"), f(c, "ratchet").get("docs_share"), None) for c, _, _ in CASES if c in facts]
    out.append('<section class="stack"><h2>What each delivered</h2><div class="charts">')
    out.append(bars("Breadth: held-out checks passed", "Checks no session saw, as a share of each case's checks. "
                    "Ratchet's tick: at its first build.", held, "pct", "", 1.0, held_labels))
    out.append(bars("Depth: seeded faults its own tests catch", "60 planted bugs on the lines each delivery wrote; share "
                    "the product's own test command catches.", faults, "pct", "", 1.0))
    out.append(bars("Test coverage of the lines it wrote", "Lines Node runs (page scripts left out), by the own test command.",
                    cover, "pct", "", 1.0))
    out.append(bars("Docs: new surfaces its documents name", "Settings, routes, query filters, scripts, flags and exports, "
                    "named in README and docs outside the tools' own folders.", docs, "pct", "", 1.0))
    out.append("</div></section>")
    # full table
    out.append('<section class="stack"><h2>Every number</h2><div class="table-wrap"><table><thead><tr>'
               '<th>Case</th><th>Arm</th><th>Minutes</th><th>Output tokens</th><th>Input tokens</th><th>Held-out</th>'
               '<th>Faults, own tests</th><th>Faults, all suites</th><th>Calibrated defects</th><th>Line coverage</th>'
               '<th>Tests</th><th>Docs (user)</th><th>Docs (all)</th><th>Code lines</th><th>Mean complexity</th>'
               '<th>Commented functions</th></tr></thead><tbody>')
    for case, name, _ in CASES:
        for arm, arm_name in ARMS:
            row = f(case, arm)
            if not row:
                continue
            code = row.get("code") or {}
            cal = f"{row['calibrated']} of {row['calibrated_pool']}" if row.get("calibrated") is not None else "–"
            out.append(f"<tr><td>{esc(name)}</td><td>{arm_name}</td><td class='num'>{num(row.get('minutes'))}</td>"
                       f"<td class='num'>{num(row.get('output'), 'k')}</td><td class='num'>{num(row.get('input'), 'm')}</td>"
                       f"<td class='num'>{num(row.get('held_out'))} of {num(row.get('held_out_of'))}</td>"
                       f"<td class='num'>{num(row.get('faults_own'), 'pct')}</td><td class='num'>{num(row.get('faults_either'), 'pct')}</td>"
                       f"<td class='num'>{esc(cal)}</td><td class='num'>{num(row.get('line_coverage'), 'pct')}</td>"
                       f"<td class='num'>{num(row.get('tests_run'))}</td>"
                       f"<td class='num'>{num(row.get('docs_documented'))} of {num(row.get('docs_surfaces'))}</td>"
                       f"<td class='num'>{num(row.get('docs_share_all'), 'pct')}</td>"
                       f"<td class='num'>{num(code.get('changed_code_lines'))}</td><td class='num'>{num(code.get('complexity_mean'))}</td>"
                       f"<td class='num'>{num(row.get('comment_share'), 'pct')}</td></tr>")
    out.append("</tbody></table></div></section>")
    if judge:
        out.append('<section class="stack"><h2>Code quality, read blind</h2><div class="table-wrap"><table><thead><tr><th>Case</th>'
                   '<th>Reading 1 prefers</th><th>Reading 2 prefers</th><th>Mean score ShipLoop</th><th>Mean score Ratchet</th>'
                   '</tr></thead><tbody>')
        for case, name, _ in CASES:
            row = (judge.get("rows") or {}).get(case)
            if not row:
                continue
            picks = [({"shiploop": "ShipLoop", "ratchet": "Ratchet"}.get(p) or "neither") for p in row["picks"]]
            means = row.get("mean_score") or {}
            out.append(f"<tr><td>{esc(name)}</td><td>{picks[0]}</td><td>{picks[1]}</td><td class='num'>{num(means.get('shiploop'))}</td>"
                       f"<td class='num'>{num(means.get('ratchet'))}</td></tr>")
        out.append("</tbody></table></div><p class='meta'>One judge (Opus), both products side by side with tool names masked, "
                   "read twice with the order swapped; a product counts as better only when both readings name it.</p></section>")
    out.append("</main>" + TIP)
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--judge", type=Path)
    parser.add_argument("--note")
    parser.add_argument("--deep", type=Path, help="the deep judge's deep.json")
    parser.add_argument("--costs", type=Path, help="minutes of each clean run, look and fix, and of Ratchet's run, a case")
    parser.add_argument("--verdict", help="the headline, replacing the first report's verdict")
    args = parser.parse_args(argv)
    report = json.loads((args.report_dir / "report.json").read_text())
    judge = json.loads(args.judge.read_text()) if args.judge else None
    deep = json.loads(args.deep.read_text()) if args.deep else None
    costs = json.loads(args.costs.read_text()) if args.costs else None
    args.out.write_text(build(report, judge, args.note, deep, costs, args.verdict))
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
