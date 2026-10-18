#!/usr/bin/env python3
"""One run's analysis report: the three answers, the gaps, the flow, and every step's prompt, the model's response
(reasoning, words, calls, outputs), result and Improve review.

    python3 build_report.py DIR META.json OUT.html

DIR is a run_steps.py layout with analysis-*.json beside index.json; META.json gives the title, subtitle, figures and
optional earlier review files (packet scores by tag).
"""
import glob, html, json, os, re, sys

DIR, META, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
meta = json.load(open(META))
index = json.load(open(DIR + "/index.json"))["steps"]
analysis = {}
run_level, best, worst = {}, [], []
for path in sorted(glob.glob(DIR + "/analysis-*.json")):
    d = json.load(open(path))
    for s in d.get("steps", []):
        analysis[s["tag"]] = s
    for k, v in (d.get("run_level") or {}).items():
        run_level.setdefault(k, []).append((d.get("group", os.path.basename(path)), v))
    best += d.get("best", [])
    worst += d.get("worst", [])
scores = {}
for path in meta.get("packet_reviews", []):
    for s in json.load(open(path)).get("steps", []):
        scores[s["tag"]] = s


def esc(t):
    return html.escape(("" if t is None else str(t)).replace("\x00", ""))


def rd(name):
    p = DIR + "/in/" + name
    return open(p, errors="replace").read() if os.path.exists(p) else None


def det(title, text, cls="raw", open_=False):
    if not text:
        return ""
    return ('<details class="blk"%s><summary>%s <span class="sz">%s characters</span></summary><pre class="%s">%s</pre></details>'
            % (" open" if open_ else "", esc(title), format(len(text), ","), cls, esc(text)))


TAG = {"THINK": ("think", "Reasoning"), "SAY  ": ("say", "Said"), "CALL ": ("call", "Tool call"), "OUT  ": ("out", "Output")}


def transcript(text, limit=500):
    if not text:
        return ""
    entries, cur = [], None
    for line in text.split("\n"):
        head = line[:5]
        if head in TAG:
            cur = [TAG[head], line[6:]]
            entries.append(cur)
        elif cur is not None:
            cur[1] += "\n" + line[6:] if line.startswith("      ") else "\n" + line
    counts = {}
    for (k, _), _ in entries:
        counts[k] = counts.get(k, 0) + 1
    shown = entries[:limit]
    rows = []
    for (cls, label), body in shown:
        body = body.strip()
        if cls == "out":
            rows.append('<div class="ev out"><div class="tag">%s</div><pre>%s</pre></div>' % (label, esc(body)))
        elif cls == "call":
            rows.append('<div class="ev call"><div class="tag">%s</div><code>%s</code></div>' % (label, esc(body)))
        else:
            rows.append('<div class="ev %s"><div class="tag">%s</div><p>%s</p></div>' % (cls, label, esc(body)))
    more = ("<p class='muted small'>%d more entries not shown.</p>" % (len(entries) - limit)) if len(entries) > limit else ""
    summary = ", ".join("%d %s" % (counts.get(k, 0), n) for k, n in (("think", "reasoning"), ("say", "said"), ("call", "calls"), ("out", "outputs")))
    return ('<details class="blk"><summary>The model\'s response, in order <span class="sz">%s</span></summary>'
            '<div class="transcript">%s%s</div></details>' % (summary, "".join(rows), more))


def chip(v, lo=1, hi=5):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return '<span class="chip n">·</span>'
    cls = "g" if v >= 4 else ("w" if v == 3 else "b")
    return '<span class="chip %s">%d</span>' % (cls, v)


PHASE = {}
for names, ph in [(["intake", "discovery", "research", "spec"], "Understand and specify"),
                  (["test-strategy", "plan", "prepare"], "Plan the work"),
                  (["step-plan", "test-spec", "validate-existing", "implement"], "Build"),
                  (["test", "document", "verify", "carry-forward"], "Verify"),
                  (["system-test-author", "system-test", "product-acceptance", "release-plan", "release-check", "release",
                    "release-verify", "operations", "handoff"], "System test and release")]:
    for n in names:
        PHASE[n] = ph

# Flow table and step cards
rows, cards, seen = [], [], None
for s in index:
    a = analysis.get(s["tag"], {})
    sc = scores.get(s["tag"], {})
    name = ("Improve of " + s["reviews"]) if s["reviews"] else s["stage"]
    ph = PHASE.get(s["reviews"] or s["stage"], "Other")
    rows.append('<tr><td class="num">%d</td><td><a href="#s%d">%s</a></td><td>%s</td><td class="num">%s</td>'
                '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td><td>%s</td></tr>' % (
                    s["n"], s["n"], esc(name), esc(s["outcome"] or "open"), s["calls"],
                    round(s["model_seconds"]) if s.get("model_seconds") else "·",
                    format(round(s["packet_chars"] / 1024), ",") if s["packet_chars"] else "·",
                    format(s["think_chars"], ","), chip(a.get("directive"))))
    head = ""
    if ph != seen:
        head = '<h2 class="phase">%s</h2>' % esc(ph)
        seen = ph
    notes = []
    if a.get("purpose"):
        notes.append('<p><span class="lbl">Purpose</span>%s</p>' % esc(a["purpose"]))
    if a.get("directive_evidence"):
        notes.append('<p><span class="lbl">Directive %s</span>%s</p>' % (chip(a.get("directive")), esc(a["directive_evidence"])))
    if a.get("response"):
        notes.append('<p><span class="lbl">Response</span>%s</p>' % esc(a["response"]))
    if a.get("step_by_step"):
        notes.append('<p><span class="lbl">Step by step</span>%s</p>' % esc(a["step_by_step"]))
    if a.get("improve"):
        notes.append('<p><span class="lbl">Improve</span>%s</p>' % esc(a["improve"]))
    if sc:
        notes.append('<p><span class="lbl">Packet review</span>concise %s accurate %s effective %s · %s</p>' % (
            chip(sc.get("concise")), chip(sc.get("accurate")), chip(sc.get("effective")), esc(sc.get("one_line", ""))))
    gaps = a.get("gaps") or []
    if gaps:
        notes.append('<ul class="gaps">%s</ul>' % "".join("<li>%s</li>" % esc(g) for g in gaps))
    body = [det("The prompt ShipLoop wrote", rd(s["tag"] + ".packet.md")),
            transcript(rd(s["tag"] + ".transcript.md")),
            det("The result the model submitted", rd(s["tag"] + ".result.md"))]
    if s["reviews"]:
        body += [det("The review's prompt (hand-off)", rd(s["tag"] + ".improve-handoff.md")),
                 det("ShipLoop's opening for the review", rd(s["tag"] + ".improve-opening.md"))]
        for rv in sorted(glob.glob(DIR + "/in/" + s["tag"] + ".improve-review-*.md")):
            body.append(det("Review " + os.path.basename(rv).split("improve-")[1][:-3], open(rv, errors="replace").read()))
        body += [det("Passes", rd(s["tag"] + ".improve-passes.md")), det("Receipt", rd(s["tag"] + ".improve-receipt.md"))]
    meta_line = " · ".join(x for x in [
        "%d calls" % s["calls"], ("%d s in the model" % round(s["model_seconds"])) if s.get("model_seconds") else "",
        ("%s KB prompt" % format(round(s["packet_chars"] / 1024), ",")) if s["packet_chars"] else "",
        ("%s characters of reasoning" % format(s["think_chars"], ",")) if s["think_chars"] else "",
        ("outcome " + s["outcome"]) if s["outcome"] and s["outcome"] != "done" else ""] if x)
    cards.append('%s<article class="step%s" id="s%d"><header><span class="idx num">%d</span><div><div class="eyebrow">%s</div>'
                 '<h3>%s</h3><p class="meta num">%s</p></div></header>%s%s</article>' % (
                     head, " imp" if s["reviews"] else "", s["n"], s["n"], esc(ph), esc(name), esc(meta_line),
                     '<div class="notes">%s</div>' % "".join(notes) if notes else "", "".join(body)))

answers = []
for key, title in (("step_by_step", "Was implementation step by step?"), ("improve", "Was the Improve loop effective?"),
                   ("directive", "Did the prompts say how to carry out each stage?")):
    verdict = meta.get("answers", {}).get(key, {})
    parts = "".join('<p><span class="lbl">%s</span>%s</p>' % (esc(g), esc(v)) for g, v in run_level.get(key, []))
    answers.append('<section class="answer"><div class="q"><h3>%s</h3>%s</div><p class="verdict">%s</p>'
                   '<details class="blk"><summary>Evidence by part of the run</summary>%s</details></section>' % (
                       esc(title), ('<span class="pill %s">%s</span>' % (verdict.get("tone", "n"), esc(verdict.get("label", "")))) if verdict else "",
                       esc(verdict.get("text", "")), parts))

fixes = "".join('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (esc(f["issue"]), esc(f["fix"]), esc(f.get("where", ""))) for f in meta.get("fixes", []))
figs = "".join('<div class="fig"><div class="v num">%s</div><div class="k">%s</div></div>' % (esc(v), esc(k)) for v, k in meta.get("figures", []))
links = " · ".join('<a href="%s">%s</a>' % (esc(u), esc(t)) for t, u in meta.get("links", []))

page = """<title>%(title)s</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: a run log read top to bottom: verdicts, then fixes, then the flow table, then one card per step. */
:root {
  --bg: #f2f3f5; --panel: #ffffff; --sunk: #eaecf0; --line: #d4d8df; --ink: #1a2030; --muted: #5b6474;
  --say: #2f55c8; --say-soft: #e2e8fb; --call: #6b4fb0; --call-soft: #ece6f8; --out: #1d7a4b; --out-soft: #dff2e7;
  --think: #6a6f7a; --think-soft: #eef0f3; --good: #1d7a4b; --warn: #a2620b; --bad: #b42323;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12151c; --panel: #1a1e27; --sunk: #232836; --line: #333a4a; --ink: #e6e9f0; --muted: #a1a9b8;
  --say: #7d9cff; --say-soft: #222c4a; --call: #b79cf0; --call-soft: #2c2440; --out: #5fcf93; --out-soft: #17331f;
  --think: #a1a9b8; --think-soft: #1f2430; --good: #5fcf93; --warn: #e3b85a; --bad: #ff7b7b; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12151c; --panel: #1a1e27; --sunk: #232836; --line: #333a4a; --ink: #e6e9f0; --muted: #a1a9b8;
  --say: #7d9cff; --say-soft: #222c4a; --call: #b79cf0; --call-soft: #2c2440; --out: #5fcf93; --out-soft: #17331f;
  --think: #a1a9b8; --think-soft: #1f2430; --good: #5fcf93; --warn: #e3b85a; --bad: #ff7b7b; color-scheme: dark }
* { box-sizing: border-box }
body { background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body) }
main { max-width: 1100px; margin: 0 auto; padding-block: 24px 80px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 18px }
h1, h2, h3 { font-family: var(--display); margin: 0; text-wrap: balance }
h1 { font-size: 32px } h2 { font-size: 23px } h3 { font-size: 19px }
h2.phase { margin-top: 18px; padding-bottom: 4px; border-bottom: 1px solid var(--line) }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; min-width: 0 }
.eyebrow { font: 500 12px/1.4 var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .05em }
.muted { color: var(--muted) } .small { font-size: 12px } .num { font-variant-numeric: tabular-nums }
.figs { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 12px }
.fig { background: var(--sunk); border-radius: 10px; padding: 10px 12px; min-width: 0 }
.fig .v { font: 600 21px/1.2 var(--display) } .fig .k { font-size: 13px; color: var(--muted) }
.answers { display: grid; gap: 12px }
.answer { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; min-width: 0 }
.answer .q { display: flex; gap: 10px; align-items: center; flex-wrap: wrap }
.verdict { margin: 8px 0 }
.pill { font: 600 12px/1 var(--mono); padding: 4px 8px; border-radius: 99px; text-transform: uppercase; letter-spacing: .04em }
.pill.g { background: var(--out-soft); color: var(--good) } .pill.w { background: var(--sunk); color: var(--warn) } .pill.b { background: var(--sunk); color: var(--bad) } .pill.n { background: var(--sunk); color: var(--muted) }
.chip { display: inline-block; min-width: 22px; text-align: center; font: 600 12px/20px var(--mono); border-radius: 6px; background: var(--sunk) }
.chip.g { color: var(--good) } .chip.w { color: var(--warn) } .chip.b { color: var(--bad) } .chip.n { color: var(--muted) }
.scroll { overflow-x: auto } table { border-collapse: collapse; width: 100%% }
td, th { border-top: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top } th { font: 500 12px var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .04em }
.step { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; min-width: 0 }
.step.imp { border-style: dashed }
.step header { display: flex; gap: 14px; align-items: flex-start; margin-bottom: 8px }
.idx { font: 600 20px var(--display); background: var(--sunk); border-radius: 8px; min-width: 40px; text-align: center; padding: 3px 6px }
.meta { margin: 2px 0 0; color: var(--muted); font-size: 13px }
.notes p { margin: 6px 0; max-width: 85ch } .lbl { font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-right: 8px }
.gaps { margin: 6px 0; padding-left: 20px; color: var(--ink) } .gaps li { margin: 3px 0 }
details.blk { margin: 8px 0; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: var(--panel) }
summary { cursor: pointer; font-weight: 500 } summary:focus-visible { outline: 2px solid var(--say); outline-offset: 2px }
.sz { font: 400 12px var(--mono); color: var(--muted) }
pre { margin: 8px 0 0; white-space: pre-wrap; word-break: break-word; font: 12px/1.5 var(--mono); background: var(--sunk); border-radius: 8px; padding: 10px; max-height: 520px; overflow: auto }
.transcript { display: grid; gap: 6px; margin-top: 8px }
.ev { border-left: 3px solid var(--line); padding: 5px 10px; border-radius: 0 8px 8px 0; min-width: 0 }
.ev .tag { font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px }
.ev p { margin: 0; white-space: pre-wrap; word-break: break-word } .ev code { font: 12px/1.5 var(--mono); white-space: pre-wrap; word-break: break-all }
.ev pre { max-height: 220px; margin-top: 2px }
.say { border-color: var(--say); background: var(--say-soft) } .say .tag { color: var(--say) }
.call { border-color: var(--call); background: var(--call-soft) } .call .tag { color: var(--call) }
.out { border-color: var(--out); background: var(--out-soft) } .out .tag { color: var(--out) }
.think { border-color: var(--think); background: var(--think-soft) } .think .tag { color: var(--think) } .think p { color: var(--muted); font-size: 14px }
a { color: var(--say) }
ul.list { margin: 6px 0; padding-left: 20px } ul.list li { margin: 4px 0; max-width: 90ch }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto } }
</style>
<main>
  <header class="panel">
    <div class="eyebrow">%(eyebrow)s</div>
    <h1>%(h1)s</h1>
    <p>%(lede)s</p>
    <div class="figs">%(figs)s</div>
    <p class="small muted">%(links)s</p>
  </header>
  <section class="answers">%(answers)s</section>
  <section class="panel"><h2>What to fix</h2><p class="muted small">Ranked by what it cost this run. Generic fixes only; the app is an example.</p>
    <div class="scroll"><table><thead><tr><th>Issue</th><th>Fix</th><th>Where</th></tr></thead><tbody>%(fixes)s</tbody></table></div></section>
  <section class="panel"><h2>What worked and what did not</h2>
    <h3 class="muted small eyebrow">Worked</h3><ul class="list">%(best)s</ul>
    <h3 class="muted small eyebrow">Did not</h3><ul class="list">%(worst)s</ul></section>
  <section class="panel"><h2>The flow</h2><p class="muted small">Every step in order. Directive: did the prompt say how to carry out the stage, 1 to 5, judged from the model's reasoning and actions.</p>
    <div class="scroll"><table><thead><tr><th>#</th><th>Step</th><th>Outcome</th><th>Calls</th><th>Model s</th><th>Prompt KB</th><th>Reasoning chars</th><th>Directive</th></tr></thead><tbody>%(rows)s</tbody></table></div></section>
  %(cards)s
</main>
""" % dict(title=esc(meta["title"]), eyebrow=esc(meta["eyebrow"]), h1=esc(meta["h1"]), lede=esc(meta["lede"]), figs=figs,
           links=links, answers="".join(answers), fixes=fixes,
           best="".join("<li>%s</li>" % esc(b) for b in best[:12]), worst="".join("<li>%s</li>" % esc(w) for w in worst[:12]),
           rows="".join(rows), cards="\n".join(cards))
open(OUT, "w").write(page)
print(OUT, round(len(page) / 1024 / 1024, 2), "MB", len(index), "steps", len(analysis), "analysed")
