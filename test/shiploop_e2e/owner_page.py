#!/usr/bin/env python3
"""The owner's iteration page for one E2E run, rebuilt from the run's files by script (no model writes a figure on it).

    python3 test/shiploop_e2e/owner_page.py <output> --earlier <earlier output> --html <page.html>
        [--control <control output> <control output>] [--decisions <decisions.json>] [--repo <checkout>] [--artifact]

Consumer: the owner, who opens the published page after each run to decide the next change. The first screen is the "Read
first" panel (flow.py `read_first`): ShipLoop commands run, how many were literal, variable-built or cut by a pipe (median
N kept), status displays fired; per producer stage the characters written against those seen after any pipe and whether the
packet file was opened; per stage seconds, turns and context; gates run against skipped; refusals by stage and cause; the
item commit; skills invoked. Each figure names its file. Above it, the staleness banner ("recorded <date> on <sha>, main
<sha>, N packet-generator commits since"); below it, the packet sizes before and now (on-disk characters, both columns
from `packets.py`), the comparison text exactly as `python3 test/shiploop_e2e/packets.py <output> --compare <earlier>`
writes it, the decisions, and a line on what the run cannot show.

A time or turn difference between two runs is shown only with its n and the A/A spread: `--control A B` names two runs of
the same arm, whose own difference is the spread; without it the spread reads "not measured".

Decisions (`--decisions`, a JSON list of {id, title, status, note}) are the page's starting rows. Published with the `db`
capability, the page keeps each decision as a document of the `decisions` collection ({id, title, status, note,
updatedAt}) and the owner edits status and note there; without it the page offers a copy-prompt button instead. This
script writes only the page; it never publishes it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flow  # noqa: E402
import packets  # noqa: E402

TITLE = "ShipLoop run review"
STATUSES = ("open", "accepted", "rejected", "deferred", "done")
NOT_MEASURED = "not measured"


def compare_reports(out: Path, earlier: Path) -> tuple[dict, dict, str]:
    """(now, before, text): the two packet reports and the comparison, read exactly as `packets.py <out> --compare <earlier>`
    reads them (an earlier directory's saved packet-report.json is used when present), but without writing either report."""
    now = packets.build(out)
    saved = earlier / packets.REPORT_JSON
    before = json.loads(saved.read_text()) if saved.is_file() else packets.build(earlier)
    return now, before, packets.compare(now, before)


def _by_stage(rows: list[dict], field: str) -> dict[str, float]:
    found: dict[str, float] = {}
    for row in rows:
        if isinstance(row.get(field), (int, float)) and row.get("stage"):
            found[row["stage"]] = found.get(row["stage"], 0) + row[field]
    return found


def size_rows(now: dict, before: dict, seeded: list[str] = ()) -> list[dict]:
    """Packet characters per stage, before and now: the on-disk sizes `packets.py` reports, so both columns share one basis. A
    stage the harness recorded without the model (``seeded``) is left out: its packet was written, never run."""
    a, b = _by_stage(now["packets"], "chars"), _by_stage(before["packets"], "chars")
    stages = [s for s in dict.fromkeys([*b, *a]) if s not in seeded]
    rows = []
    for stage in stages:
        old, new = b.get(stage), a.get(stage)
        delta = None if old is None or new is None else new - old
        rows.append({"stage": stage, "before": old, "now": new, "delta": delta,
                     "percent": round(100.0 * delta / old, 1) if delta is not None and old else None})
    return rows


def run_totals(report: dict) -> dict:
    """Total seconds (the stages' sum) and turns of one run's packet report; None where it has none."""
    seconds = [r["seconds"] for r in report.get("stages") or [] if isinstance(r.get("seconds"), (int, float))]
    turns = (report.get("totals") or {}).get("turns")
    return {"seconds": round(sum(seconds), 1) if seconds else None, "turns": turns if isinstance(turns, (int, float)) else None}


def aa_spread(control: list[Path] | None) -> dict:
    """The A/A spread: the absolute difference of two runs of one arm, per measure. None (not measured) without two runs."""
    if not control or len(control) != 2:
        return {"seconds": None, "turns": None, "runs": [str(p) for p in control or []]}
    a, b = (run_totals(packets.build(path)) for path in control)
    return {k: (round(abs(a[k] - b[k]), 1) if a[k] is not None and b[k] is not None else None) for k in ("seconds", "turns")} | {
        "runs": [str(p) for p in control]}


def delta_rows(now: dict, before: dict, spread: dict) -> list[dict]:
    """Time and turn differences, each with its n and the A/A spread (the only way the page shows such a difference)."""
    a, b = run_totals(now), run_totals(before)
    rows = []
    for name in ("seconds", "turns"):
        delta = round(a[name] - b[name], 1) if a[name] is not None and b[name] is not None else None
        within = None if delta is None or spread.get(name) is None else abs(delta) <= spread[name]
        rows.append({"measure": name, "before": b[name], "now": a[name], "delta": delta, "n": "1 per side",
                     "aa_spread": spread.get(name), "inside_spread": within})
    return rows


def build(out: Path, earlier: Path, control: list[Path] | None = None, decisions: list[dict] | None = None,
          repo: Path | None = None) -> dict:
    """Everything the page shows, as data (the test reads this; `render` only lays it out)."""
    first = flow.read_first(out, repo=repo)
    now, before, text = compare_reports(out, earlier)
    spread = aa_spread(control)
    return {"read_first": first, "earlier": str(earlier), "compare_text": text, "sizes": size_rows(now, before, first.get("seeded") or []),
            "deltas": delta_rows(now, before, spread), "aa_spread": spread,
            "decisions": [{"id": str(d["id"]), "title": str(d.get("title") or ""), "status": str(d.get("status") or "open"),
                           "note": str(d.get("note") or "")} for d in decisions or []],
            "built": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# --- layout ----------------------------------------------------------------------------------------------------------------

def _e(value) -> str:
    return html.escape("–" if value is None else str(value))


def _n(value) -> str:
    if value is None:
        return "–"
    return f"{value:,}" if isinstance(value, int) else f"{value:,.1f}" if isinstance(value, float) else str(value)


def _src(root: str, relative: str) -> str:
    """A figure's source file: its path relative to the run's output folder, linked to the file on the machine that ran it."""
    target = relative if relative.startswith("/") else f"{root.rstrip('/')}/{relative}"
    return f'<a class="src" href="file://{html.escape(target, quote=True)}" title="{html.escape(target, quote=True)}">{_e(relative)}</a>'


def _table(head: list[str], rows: list[list[str]], numeric: set[int] = frozenset()) -> str:
    th = "".join(f'<th{" class=r" if i in numeric else ""}>{h}</th>' for i, h in enumerate(head))
    body = "".join("<tr>" + "".join(f'<td{" class=r" if i in numeric else ""}>{c}</td>' for i, c in enumerate(row)) + "</tr>"
                   for row in rows)
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


STYLE = """
:root{--bg:#fbfaf7;--panel:#ffffff;--ink:#1d1d1b;--muted:#6b6a64;--line:#e4e1d8;--accent:#2f5d8a;--warn:#9a5b00;--bad:#a23b2c;--good:#2d6a3e;
--chip:#f1efe8;font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161615;--panel:#1f1f1d;--ink:#ecebe6;--muted:#a3a19a;--line:#34332f;
--accent:#8ab4e0;--warn:#e0a54a;--bad:#e58a7a;--good:#86c79a;--chip:#2a2a27;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#161615;--panel:#1f1f1d;--ink:#ecebe6;--muted:#a3a19a;--line:#34332f;--accent:#8ab4e0;--warn:#e0a54a;
--bad:#e58a7a;--good:#86c79a;--chip:#2a2a27;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5}
main{max-width:1080px;margin:0 auto;padding:20px 16px 48px;display:grid;gap:16px}
h1{font-size:22px;margin:0}h2{font-size:17px;margin:0 0 8px}h3{font-size:14px;margin:12px 0 6px;color:var(--muted);font-weight:600}
.banner{border:1px solid var(--line);border-left:4px solid var(--warn);background:var(--panel);padding:10px 12px;border-radius:6px}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-width:0}
.figures{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.fig{border:1px solid var(--line);border-radius:6px;padding:8px 10px;min-width:0}.fig .v{font-size:20px;font-weight:650;font-variant-numeric:tabular-nums}
.fig .k{color:var(--muted);font-size:13px}.src{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--accent);word-break:break-all}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}.r{text-align:right;font-variant-numeric:tabular-nums}
pre{background:var(--chip);padding:10px;border-radius:6px;overflow-x:auto;font-size:12.5px;white-space:pre}
.muted{color:var(--muted)}.pill{display:inline-block;padding:0 8px;border-radius:10px;background:var(--chip);font-size:12px}
.bad{color:var(--bad)}.good{color:var(--good)}
.dec{display:grid;gap:6px;border-top:1px solid var(--line);padding:8px 0}.dec:first-child{border-top:0}
.dec .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}textarea{width:100%;min-height:52px;font:inherit;background:var(--bg);color:var(--ink);
border:1px solid var(--line);border-radius:6px;padding:6px}select,button{font:inherit;background:var(--chip);color:var(--ink);border:1px solid var(--line);
border-radius:6px;padding:3px 10px}button{cursor:pointer}
"""

SCRIPT = """
(function(){
  const seed = JSON.parse(document.getElementById("decision-seed").textContent);
  const statuses = %s;
  const box = document.getElementById("decisions");
  const note = document.getElementById("decisions-mode");
  let rows = new Map(seed.map((d) => [d.id, Object.assign({updatedAt: null, saved: false}, d)]));
  let db = null;
  function render(){
    box.replaceChildren();
    [...rows.values()].sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true})).forEach((d) => {
      const el = document.createElement("div"); el.className = "dec";
      const top = document.createElement("div"); top.className = "row";
      const id = document.createElement("b"); id.textContent = d.id;
      const title = document.createElement("span"); title.textContent = d.title;
      const sel = document.createElement("select");
      statuses.forEach((s) => { const o = document.createElement("option"); o.value = s; o.textContent = s; o.selected = s === d.status; sel.append(o); });
      const when = document.createElement("span"); when.className = "muted";
      when.textContent = d.updatedAt ? "updated " + d.updatedAt : (d.saved ? "" : "from the page, not saved");
      top.append(id, title, sel, when);
      const text = document.createElement("textarea"); text.value = d.note || ""; text.placeholder = "Owner note";
      const act = document.createElement("button");
      act.textContent = db ? "Save" : "Copy update prompt";
      act.addEventListener("click", async () => {
        const next = {id: d.id, title: d.title, status: sel.value, note: text.value, updatedAt: new Date().toISOString()};
        if (db) {
          act.disabled = true;
          try { await db.collection("decisions").doc(d.id).set(next); }
          catch (e) { when.textContent = "not saved: " + (e && e.code || "error"); }
          act.disabled = false;
        } else {
          const prompt = "Decision " + d.id + " (" + d.title + "): status " + next.status + (next.note ? "; owner note: " + next.note : "");
          try { await navigator.clipboard.writeText(prompt); act.textContent = "Copied"; } catch (e) { text.select(); }
        }
      });
      el.append(top, text, act); box.append(el);
    });
  }
  render();
  if (window.claude && typeof window.claude.use === "function") {
    window.claude.use("db").then((found) => {
      if (!found) return;
      db = found;
      note.textContent = "Decisions are kept in this page's database: a saved status or note is shared with every viewer.";
      db.collection("decisions").onSnapshot((snap) => {
        snap.docs.forEach((doc) => { const d = doc.data(); if (d && d.id) rows.set(d.id, Object.assign({}, d, {saved: true})); });
        render();
      }, () => { note.textContent = "The decisions database stopped answering; edits are copied as a prompt instead."; db = null; render(); });
      render();
    });
  }
})();
"""


def render(data: dict, standalone: bool = True) -> str:
    rf = data["read_first"]
    root = rf["output"]
    c = rf["commands"]
    complete = c["by_verb"].get("complete") or {"invocations": 0, "piped": 0}
    displays = c["status_displays"]
    figures = [
        (_n(c["invocations"]), "ShipLoop commands run"),
        (f'{_n(c["literal"])} of {_n(c["invocations"])}', "literal (no pipe, no variable)"),
        (f'{_n(c["variable_built"])} of {_n(c["invocations"])}', f'variable-built ({_n(c["variable_run_dir"])} by the run directory)'),
        (f'{_n(complete["piped"])} of {_n(complete["invocations"])}', "complete calls piped"),
        (_n(c["median_n"]) if c["median_n"] is not None else "–", f'median N kept by a head pipe ({_n(c["cut_by_pipe"])} cut)'),
        (f'{_n(displays)} in {_n(c["invocations"])}' if displays is not None else NOT_MEASURED, "status displays fired"),
    ]
    p = rf["producers"]
    if p["measured"]:
        figures.append((f'{_n(p["count_opened"])} of {_n(p["of"])}', "producer packet files opened"))
    g = rf["gates"]
    if g.get("measured"):
        figures.append((f'{_n(g["ran"])} ran · {_n(g["count"])} skipped', "gates"))
    figures.append((_n(rf["refusals"]["count"]), "refusals"))
    ic = rf["item_commit"]
    figures.append(("present" if ic.get("present") else "absent" if ic.get("measured") else NOT_MEASURED, "item commit"))
    sk = rf["skills"]
    figures.append((f'{_n(sk["improve_invoked"])} of {_n(sk["improve_stages"])}' if sk["improve_invoked"] is not None else NOT_MEASURED,
                    "Improve stages that invoked the improve skill"))
    fig_html = "".join(f'<div class="fig"><div class="v">{_e(v)}</div><div class="k">{_e(k)}</div></div>' for v, k in figures)

    producers = _table(["Stage", "Written (chars)", "Seen by the model (after any head pipe)", "Cut by", "Packet file opened", "File"],
                       [[_e(r["stage"]), _n(r["written"]), _n(r["seen"]), _e(", ".join(r["cut_by"]) or "no pipe"), _e(r["opened"]),
                         _src(root, r["file"])] for r in p["rows"]], {1, 2}) if p["measured"] else f'<p class="muted">{_e(p.get("reason"))}</p>'
    s = rf["steps"]
    steps = _table(["Stage", "Seconds", "Turns", "Tool calls", "Context peak (tokens)"],
                   [[_e(r["stage"]) + (' <span class="pill">incomplete</span>' if r["incomplete"] else ""), _n(r["seconds"]), _n(r["turns"]),
                     _n(r["tool_calls"]), _n(r["context_peak"])] for r in s["rows"]], {1, 2, 3, 4}) if s["rows"] else f'<p class="muted">{NOT_MEASURED}</p>'
    gates = _table(["Gate", "Records", "Skipped", "Why"], [[_e(x["gate"]), _n(x["records"]), _n(x["skipped"]), _e(x["reason"] or "")]
                                                          for x in g.get("gates") or []], {1, 2}) if g.get("gates") else f'<p class="muted">no gate records</p>'
    refusals = _table(["Stage", "Cause", "Count"], [[_e(x["stage"]), _e(x["cause"]), _n(x["count"])] for x in rf["refusals"]["rows"]], {2}) \
        if rf["refusals"]["rows"] else '<p class="muted">none</p>'
    tr = rf.get("trace") or {}
    refusal_source = ((f'From ShipLoop\'s run trace: {_n(rf["refusals"].get("checks_failed"))} failed checks apart; the host stream showed '
                       f'{_n(rf["refusals"].get("stream_count"))}.') if rf["refusals"].get("source") == "trace" else
                      "From the host stream's refusal lines (a refusal a pipe hid is missing)." + (f' {_e(tr.get("reason"))}.' if tr.get("reason") else ""))
    trace_line = (f'Run trace: {_n(tr.get("packets"))} packet prints, {_n(tr.get("reprints"))} reprints, '
                  f'{_n(tr.get("continuations"))} keepalive continuations, {_n(tr.get("stops"))} stops'
                  + ("" if tr.get("covers") else f'; partial: {_e(tr.get("partial"))}') + f' {_src(root, tr["file"])}') if tr.get("measured") else ""
    skills = ", ".join(f"{_e(name)} ×{n}" for name, n in (sk["calls"] or {}).items()) if sk["calls"] is not None else NOT_MEASURED
    commit = (f'{"present" if ic["present"] else "absent"}' + (f': {_e(ic["reason"])}' if ic.get("reason") else "")
              + (f'; uncommitted product: {_e(", ".join(ic["uncommitted_product"]))}' if ic.get("uncommitted_product") else "")
              + f' {_src(root, ic["file"])}') if ic.get("measured") else _e(ic.get("reason"))

    sizes = _table(["Stage", "Before (chars on disk)", "Now (chars on disk)", "Δ", "Δ %"],
                   [[_e(r["stage"]), _n(r["before"]), _n(r["now"]), _n(r["delta"]), _n(r["percent"])] for r in data["sizes"]], {1, 2, 3, 4})
    spread = data["aa_spread"]
    deltas = _table(["Measure", "Before", "Now", "Δ", "n", "A/A spread", "Inside the spread"],
                    [[_e(r["measure"]), _n(r["before"]), _n(r["now"]), _n(r["delta"]), _e(r["n"]),
                      _n(r["aa_spread"]) if r["aa_spread"] is not None else NOT_MEASURED,
                      _e({True: "yes: not a difference", False: "no", None: "unknown"}[r["inside_spread"]])] for r in data["deltas"]], {1, 2, 3})
    spread_text = (f'A/A spread from {len(spread["runs"])} control runs: seconds {_n(spread["seconds"])}, turns {_n(spread["turns"])}'
                   if spread.get("runs") else "A/A spread: not measured (no control runs given)")
    st = rf["staleness"]
    versions = rf.get("versions") or {}
    seed = json.dumps(data["decisions"]).replace("</", "<\\/")
    body = f"""<title>{TITLE}</title>
<style>{STYLE}</style>
<main>
<header><h1>{_e(rf.get("case") or "E2E run")} · {_e(rf.get("host"))}</h1>
<div class="muted">ShipLoop {_e(versions.get("shiploop_version"))} · plugin {_e(versions.get("plugin_version"))} · delegation {_e(rf.get("delegation"))}
· page built {_e(data["built"])} by <span class="src">test/shiploop_e2e/owner_page.py</span></div></header>
<div class="banner" id="staleness"><b>Staleness:</b> {_e(st["text"])} {_src(root, st["file"])}</div>
<section id="read-first"><h2>Read first</h2>
<div class="figures">{fig_html}</div>
<p class="muted">Commands, displays and skills: {_src(root, c["file"])} · skills invoked: {skills}</p>
<h3>Producer stages: written against seen</h3>{producers}
<h3>Per stage</h3>{steps}<p class="muted">{_src(root, s["file"])}</p>
<h3>Gates</h3>{gates}<p class="muted">{_src(root, g["file"])}</p>
<h3>Refusals by stage and cause</h3>{refusals}<p class="muted">{refusal_source} {_src(root, rf["refusals"]["file"])}</p>
{f'<p class="muted">{trace_line}</p>' if trace_line else ""}
<h3>Item commit</h3><p>{commit}</p>
</section>
<section id="sizes"><h2>Packet sizes, before and now</h2>
<p class="muted">Both columns are characters on disk from <span class="src">packets.py</span>; before: <span class="src">{_e(data["earlier"])}</span>.
Stages the harness recorded without the model are left out{": " + _e(", ".join(rf["seeded"])) if rf.get("seeded") else ""}.</p>{sizes}
<h3>Time and turns</h3>{deltas}<p class="muted">{_e(spread_text)}. One run per side: a difference inside the spread is not a difference.</p>
<h3>Comparison (exactly as <span class="src">packets.py &lt;output&gt; --compare &lt;earlier&gt;</span> writes it)</h3>
<p class="muted">Every Δ seconds and Δ turns below is n=1 per side; {_e(spread_text)}.</p>
<pre id="compare">{html.escape(data["compare_text"])}</pre>
</section>
<section id="decisions-section"><h2>Decisions</h2><p class="muted" id="decisions-mode">Without this page's database the edits are copied as a prompt to paste into the session.</p>
<div id="decisions"></div></section>
<section id="cannot-show"><h2>What this run cannot show</h2><ul>{"".join(f"<li>{_e(x)}</li>" for x in rf["cannot_show"])}</ul></section>
</main>
<script id="decision-seed" type="application/json">{seed}</script>
<script>{SCRIPT % json.dumps(list(STATUSES))}</script>
"""
    if not standalone:
        return body
    return ('<!doctype html>\n<html lang="en">\n<head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head>\n<body>\n'
            + body + "</body>\n</html>\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", type=Path, help="the E2E output directory the page is about")
    p.add_argument("--earlier", type=Path, required=True, help="an earlier output directory of the same case, for the comparison")
    p.add_argument("--html", type=Path, required=True, help="where to write the page")
    p.add_argument("--control", type=Path, nargs=2, metavar="DIR", help="two runs of one arm: their difference is the A/A spread")
    p.add_argument("--decisions", type=Path, help="a JSON list of {id, title, status, note}: the page's starting decision rows")
    p.add_argument("--repo", type=Path, help="the checkout the staleness banner reads (default: this one)")
    p.add_argument("--json", type=Path, metavar="FILE", help="also write the page's data as JSON")
    p.add_argument("--artifact", action="store_true", help="leave out the document skeleton, for an Artifact publish")
    args = p.parse_args(argv)
    resolve = lambda path: path.expanduser().resolve()  # noqa: E731
    decisions = json.loads(resolve(args.decisions).read_text()) if args.decisions else []
    if not isinstance(decisions, list) or any(not isinstance(d, dict) or "id" not in d for d in decisions):
        p.error("--decisions is a JSON list of objects, each with an id")
    data = build(resolve(args.output), resolve(args.earlier), [resolve(c) for c in args.control] if args.control else None,
                 decisions, resolve(args.repo) if args.repo else None)
    target = resolve(args.html)
    target.write_text(render(data, standalone=not args.artifact))
    if args.json:
        resolve(args.json).write_text(json.dumps(data, indent=1) + "\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
