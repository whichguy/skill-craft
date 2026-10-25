"""The run-trace page template: ``shiploop trace --html`` replaces ``DATA_MARK`` with the model as JSON.

Kept as a Python string because every file in ``scripts/`` must compile (test/shiploop-package-integrity.test.py).
"""

DATA_MARK = "/*TRACE-DATA*/null"

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShipLoop Run Trace</title>
<style>
:root {
  --bg: #f6f6f3; --panel: #ffffff; --ink: #1c1c1e; --muted: #6b6b70; --line: #e2e2de; --chip: #f0f0ec;
  --accent: #2a78d6; --accent-soft: #e5effb; --amber: #b9800f; --amber-soft: #fbf0d8;
  --red: #c4372b; --red-soft: #fbe6e3; --violet: #7349c9; --violet-soft: #eee7fb; --green: #2d8547; --green-soft: #e3f3e7;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121214; --panel: #1b1b1f; --ink: #ececef; --muted: #9a9aa2; --line: #2e2e34; --chip: #26262c;
    --accent: #5b9cf0; --accent-soft: #1c2b40; --amber: #e2a93a; --amber-soft: #3a2e14;
    --red: #ef6b5f; --red-soft: #3d1d1a; --violet: #a68af0; --violet-soft: #2b2340; --green: #5cc27b; --green-soft: #18301f;
  }
}
:root[data-theme="dark"] {
  --bg: #121214; --panel: #1b1b1f; --ink: #ececef; --muted: #9a9aa2; --line: #2e2e34; --chip: #26262c;
  --accent: #5b9cf0; --accent-soft: #1c2b40; --amber: #e2a93a; --amber-soft: #3a2e14;
  --red: #ef6b5f; --red-soft: #3d1d1a; --violet: #a68af0; --violet-soft: #2b2340; --green: #5cc27b; --green-soft: #18301f;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 var(--sans); }
main { max-width: 1180px; margin: 0 auto; padding: 20px 16px 64px; }
h1 { font-size: 20px; margin: 0 0 6px; line-height: 1.3; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 28px 0 10px; }
.meta { color: var(--muted); font-size: 12.5px; display: flex; flex-wrap: wrap; gap: 4px 14px; }
.mono { font-family: var(--mono); font-size: 12px; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pill.active { background: var(--amber-soft); color: var(--amber); }
.pill.done { background: var(--green-soft); color: var(--green); }
.pill.paused, .pill.blocked, .pill.halted { background: var(--red-soft); color: var(--red); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.pill.active .dot { animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: .25; } }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(128px, 1fr)); gap: 10px; margin-top: 16px; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }
.tile b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
.tile span { color: var(--muted); font-size: 12px; }
.tile.warn b { color: var(--red); }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.now { border-left: 4px solid var(--amber); display: grid; gap: 4px; }
.now.stopped { border-left-color: var(--red); }
.now.finished { border-left-color: var(--green); }
.now .where { font-weight: 600; font-size: 15px; }
.row-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
button { font: inherit; font-size: 12.5px; border: 1px solid var(--line); background: var(--chip); color: var(--ink);
  border-radius: 7px; padding: 4px 10px; cursor: pointer; }
button:hover { border-color: var(--accent); }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
.plan { display: grid; gap: 8px; }
.plan-row { display: grid; grid-template-columns: 210px 1fr; gap: 10px; align-items: start; }
.plan-label { font-weight: 600; font-size: 13px; padding-top: 4px; overflow: hidden; text-overflow: ellipsis; }
.plan-label small { display: block; color: var(--muted); font-weight: 400; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { display: inline-flex; align-items: center; gap: 5px; border-radius: 8px; padding: 4px 9px; font-size: 12.5px;
  border: 1px solid transparent; cursor: pointer; background: var(--chip); color: var(--ink); }
.chip.done { background: var(--accent-soft); color: var(--accent); }
.chip.current { background: var(--amber-soft); color: var(--amber); border-color: var(--amber); font-weight: 600; }
.chip.current::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; animation: pulse 1.4s infinite; }
.chip.sample { cursor: default; }
.chip.sample::before { animation: none; }
.b.back { background: var(--amber-soft); color: var(--amber); }
.tile.muted b { color: var(--muted); }
.chip.pending { background: transparent; border: 1px dashed var(--line); color: var(--muted); cursor: default; }
.chip.reopened { background: transparent; border: 1px dashed var(--amber); color: var(--amber); }
.b { font-size: 10.5px; font-weight: 700; padding: 0 4px; border-radius: 5px; background: rgba(127,127,127,.16); }
.b.ref { background: var(--red-soft); color: var(--red); }
.b.imp { background: var(--violet-soft); color: var(--violet); }
.note { color: var(--muted); font-style: italic; padding-top: 4px; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; color: var(--muted); font-size: 12px; margin-top: 10px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; margin-bottom: 10px; font-size: 12.5px; }
.toolbar label { display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
.toolbar input[type=search] { font: inherit; padding: 5px 9px; border-radius: 7px; border: 1px solid var(--line);
  background: var(--panel); color: var(--ink); min-width: 220px; flex: 1; max-width: 360px; }
details.group { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 8px; }
details.group[open] { box-shadow: 0 1px 0 var(--line); }
details.group.has-refusal { border-color: var(--red); }
details.group.is-now { border-color: var(--amber); }
summary { list-style: none; cursor: pointer; padding: 10px 14px; display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: baseline; }
summary::-webkit-details-marker { display: none; }
summary .n { color: var(--muted); font-variant-numeric: tabular-nums; min-width: 34px; }
summary .t { font-weight: 600; }
summary .h { color: var(--muted); font-weight: 400; margin-left: 6px; }
summary .c { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.tag { font-size: 11px; border-radius: 6px; padding: 1px 7px; background: var(--chip); color: var(--muted); white-space: nowrap; }
.tag.red { background: var(--red-soft); color: var(--red); }
.tag.amber { background: var(--amber-soft); color: var(--amber); }
.tag.violet { background: var(--violet-soft); color: var(--violet); }
.tag.green { background: var(--green-soft); color: var(--green); }
.events { border-top: 1px solid var(--line); padding: 6px 0; }
.ev { display: grid; grid-template-columns: 88px 78px 1fr; gap: 10px; padding: 5px 14px; align-items: start; }
.ev:hover { background: var(--chip); }
.ev time { color: var(--muted); font-family: var(--mono); font-size: 11.5px; padding-top: 2px; }
.kind { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; padding-top: 2px; }
.kind.command { color: var(--accent); } .kind.packet { color: var(--green); } .kind.hook { color: var(--violet); }
.kind.skill { color: var(--amber); } .kind.accepted { color: var(--green); } .kind.refused { color: var(--red); }
.kind.check { color: var(--amber); }
.ev.check pre { background: var(--amber-soft); }
.ev .body { min-width: 0; overflow-wrap: anywhere; }
.ev pre, .viewer pre { white-space: pre-wrap; overflow-wrap: anywhere; font-family: var(--mono); font-size: 12px; margin: 6px 0 0;
  background: var(--chip); border-radius: 8px; padding: 8px 10px; max-height: 260px; overflow: auto; }
.ev.refusal pre { background: var(--red-soft); }
.ev.hook pre { background: var(--violet-soft); }
.empty { color: var(--muted); padding: 16px; text-align: center; }
.viewer { position: fixed; inset: 0 0 0 auto; width: min(760px, 100%); background: var(--panel); border-left: 1px solid var(--line);
  box-shadow: -12px 0 30px rgba(0,0,0,.18); display: none; flex-direction: column; z-index: 10; }
.viewer.open { display: flex; }
.viewer header { padding: 12px 16px; border-bottom: 1px solid var(--line); display: grid; gap: 4px; }
.viewer header .top { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.viewer pre { max-height: none; flex: 1; margin: 0; border-radius: 0; padding: 14px 16px; background: var(--panel); }
.viewer .scroll { flex: 1; overflow: auto; }
footer { color: var(--muted); font-size: 12px; margin-top: 30px; }
.request { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.request h3 { font-size: 13px; margin: 0 0 6px; }
.request .verbatim, .item .verbatim { white-space: pre-wrap; overflow-wrap: anywhere; font: 13px/1.5 var(--sans); max-height: 320px; overflow: auto;
  background: var(--chip); border-radius: 8px; padding: 10px 12px; margin: 0; }
.stage-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.stage-list li { display: grid; grid-template-columns: 18px 110px 1fr; gap: 6px; align-items: baseline; font-size: 13px; }
.stage-list .pending { color: var(--muted); }
.counts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
details.more { margin-top: 10px; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
details.more > summary { display: block; padding: 9px 14px; font-weight: 600; }
details.more > div { border-top: 1px solid var(--line); padding: 8px 14px; }
.sentences { display: grid; gap: 0; }
.sentence { display: grid; grid-template-columns: 44px 1fr 1fr; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.sentence:last-child { border-bottom: 0; }
.sentence .sn { color: var(--muted); font-family: var(--mono); font-size: 12px; }
.sentence .reading { color: var(--ink); }
.sentence .reading.none { color: var(--muted); font-style: italic; }
.req { padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.req:last-child { border-bottom: 0; }
.req summary { display: block; padding: 0; cursor: pointer; }
.req pre { white-space: pre-wrap; font-family: var(--sans); font-size: 12.5px; margin: 6px 0 0; color: var(--muted); }
.item { padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.item:last-child { border-bottom: 0; }
.item ol { margin: 6px 0 0 18px; padding: 0; }
.item li { margin: 2px 0; }
@media (max-width: 720px) {
  .request { grid-template-columns: 1fr; }
  .sentence { grid-template-columns: 34px 1fr; }
  .sentence .reading { grid-column: 2; }
  .plan-row { grid-template-columns: 1fr; gap: 4px; }
  .ev { grid-template-columns: 70px 1fr; }
  .ev .kind { grid-column: 2; grid-row: 1; }
  .ev .body { grid-column: 1 / -1; }
  summary { grid-template-columns: auto 1fr; }
  summary .c { grid-column: 1 / -1; justify-content: flex-start; }
}
</style>
</head>
<body>
<main id="app"><p class="empty">This page has no run data; write it with <span class="mono">shiploop trace --run-dir RUN --html</span>.</p></main>
<aside class="viewer" id="viewer" aria-label="Packet viewer">
  <header>
    <div class="top"><strong id="viewer-title">Packet</strong>
      <span><button id="viewer-copy">Copy</button> <button id="viewer-close" class="primary">Close</button></span></div>
    <div class="meta" id="viewer-meta"></div>
  </header>
  <div class="scroll"><pre id="viewer-text"></pre></div>
</aside>
<script>
const TRACE = /*TRACE-DATA*/null;
(function () {
  if (!TRACE) return;
  const KINDS = ["command", "packet", "hook", "skill", "accepted"];
  const store = {
    get(key, fallback) { try { const v = sessionStorage.getItem("trace:" + (TRACE.run.id || "") + ":" + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
    set(key, value) { try { sessionStorage.setItem("trace:" + (TRACE.run.id || "") + ":" + key, JSON.stringify(value)); } catch (e) { /* storage unavailable */ } },
  };
  const ui = Object.assign({kinds: KINDS.slice(), refusalsOnly: false, query: "", live: true, open: null}, store.get("ui", {}));

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }
  const num = (n) => (n || 0).toLocaleString("en-US");
  function clock(stamp) {
    if (!stamp) return "";
    const d = typeof stamp === "number" ? new Date(stamp * 1000) : new Date(stamp);
    return isNaN(d) ? "" : d.toISOString().slice(11, 19) + "Z";
  }
  function span(s) {
    if (s === null || s === undefined) return "?";
    s = Math.round(s);
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m" + String(s % 60).padStart(2, "0") + "s";
    return Math.floor(s / 3600) + "h" + String(Math.floor(s % 3600 / 60)).padStart(2, "0") + "m";
  }
  const short = (a) => a && a.length > 13 ? a.slice(0, 12) + "…" : (a || "");
  const where = (o) => (o.item ? o.item + " " : "") + (o.stage || "");

  const run = TRACE.run, counts = TRACE.counts;
  const steps = new Map(TRACE.steps.map((s) => [s.action, s]));
  const nowAction = TRACE.now && TRACE.now.action;

  // ---------------------------------------------------------------- viewer
  const viewer = document.getElementById("viewer");
  function openPacket(file, label, info) {
    const text = TRACE.texts[file];
    document.getElementById("viewer-title").textContent = label || file;
    document.getElementById("viewer-meta").replaceChildren(...[
      el("span", {class: "mono"}, "RUN/" + file), info ? el("span", {}, info) : null,
      text === undefined ? el("span", {}, "not embedded (too large, or missing); open the file") : null].filter(Boolean));
    document.getElementById("viewer-text").textContent = text === undefined ? "" : text;
    viewer.classList.add("open");
    ui.open = {file, label, info}; save();
  }
  document.getElementById("viewer-close").onclick = () => { viewer.classList.remove("open"); ui.open = null; save(); };
  document.getElementById("viewer-copy").onclick = () => {
    const text = document.getElementById("viewer-text").textContent;
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
  };
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") document.getElementById("viewer-close").click(); });

  // ---------------------------------------------------------------- header, now, plan
  function header() {
    const pill = el("span", {class: "pill " + run.status}, el("span", {class: "dot"}), run.status);
    const tiles = [
      ["Steps accepted", counts.accepted], ["Packets sent", counts.packets, counts.reprints ? counts.reprints + " reprints" : "", false, true],
      ["Refused", counts.refusals, "", counts.refusals > 0, true], ["Hook continuations", counts.continuations, "", false, true],
      ["Skill calls", counts.skills], ["Commands", counts.commands, "", false, true],
    ];
    return el("header", {},
      el("div", {class: "meta"}, "ShipLoop run trace"),
      el("h1", {}, run.goal || "ShipLoop run"),
      el("div", {class: "meta"}, pill, el("span", {class: "mono"}, run.id || ""), el("span", {}, "revision " + run.revision),
        run.started ? el("span", {}, "started " + run.started.replace("T", " ")) : null, el("span", {}, "elapsed " + span(run.elapsed)),
        run.last_event ? el("span", {}, "last event " + clock(run.last_event)) : null, el("span", {}, "page written " + clock(TRACE.generated)),
        run.status === "active" ? el("label", {}, el("input", {type: "checkbox", checked: ui.live, onchange: (e) => { ui.live = e.target.checked; save(); schedule(); }}), " live (reload every 10 s)") : null),
      run.traced ? null : el("p", {class: "note"}, "This run predates the trace: steps come from state.md and timeline.json, and each packet is its last copy, not every copy sent."),
      // Not measured is not zero: a run before the trace recorded no packets, refusals, hook stops or commands.
      el("div", {class: "tiles"}, tiles.map(([label, value, sub, warn, traceOnly]) => traceOnly && !run.traced
        ? el("div", {class: "tile muted", title: "not recorded: the run predates the trace"}, el("b", {}, "—"), el("span", {}, label + " · not recorded"))
        : el("div", {class: "tile" + (warn ? " warn" : "")}, el("b", {}, num(value)), el("span", {}, label + (sub ? " · " + sub : ""))))));
  }

  function nowCard() {
    const now = TRACE.now;
    if (!now) return el("section", {}, el("h2", {}, "Now"),
      el("div", {class: "card now finished"}, el("div", {class: "where"}, "The run is complete"),
        el("div", {class: "meta"}, run.status_reason || "report.html holds the achievement report")));
    const stopped = run.status !== "active";
    const packetFile = now.packet;
    return el("section", {}, el("h2", {}, "Now"),
      el("div", {class: "card now" + (stopped ? " stopped" : "")},
        el("div", {class: "where"}, where(now) + (now.reviewing ? " · reviewing " + now.reviewing : "")),
        el("div", {}, now.purpose || ""),
        stopped ? el("div", {class: "tag red"}, run.status + ": " + (run.status_reason || "")) : null,
        el("div", {class: "meta"}, el("span", {class: "mono"}, now.action || ""),
          now.since ? el("span", {}, "first packet " + clock(now.since)) : null,
          now.packets ? el("span", {}, now.packets + " packets") : null, now.refusals ? el("span", {}, now.refusals + " refused") : null),
        el("div", {class: "row-actions"},
          packetFile ? el("button", {class: "primary", onclick: () => openPacket(packetFile, "Current packet: " + where(now))}, "Open current packet") : null,
          el("button", {onclick: () => focusAction(now.action)}, "Show its events"))));
  }

  // A slot's marks, shared by the chips and the legend: [kind, text, explanation].
  function marks(slot) {
    const out = [];
    const accepted = slot.runs - (slot.sent_back || 0);
    if (slot.steps !== null && slot.steps !== undefined) out.push(["steps", slot.steps + (slot.steps === 1 ? " step" : " steps"), "implement is accepted once per step: " + accepted + " accepted results"]);
    else if (accepted > 1) out.push(["runs", "×" + accepted, "accepted " + accepted + " times (re-planned or redone)"]);
    if (slot.sent_back) out.push(["back", "↩" + slot.sent_back, "sent back " + slot.sent_back + (slot.sent_back > 1 ? " times" : " time")]);
    if (slot.improve) out.push(["imp", "I", "reviewed by an Improve stage"]);
    if (slot.refusals) out.push(["ref", "!" + slot.refusals, slot.refusals + " callback" + (slot.refusals > 1 ? "s" : "") + " refused"]);
    return out;
  }
  const BADGE = {steps: "b", runs: "b", back: "b back", imp: "b imp", ref: "b ref"};

  // ---------------------------------------------------------------- request: original beside expanded
  function requestSection() {
    const req = TRACE.request;
    if (!req) return null;
    const original = req.original, ex = req.expanded;
    const steps = ex.work_items.reduce((sum, item) => sum + item.steps.length, 0);
    const counts = [
      ex.through ? "expanded through " + ex.through : "not expanded yet",
      "intake read " + ex.mapped + " of " + original.sentences.length + " sentences",
      ex.requirements.length + " requirements", ex.work_items.length + " work items" + (steps ? ", " + steps + " steps" : ""),
      ex.assumptions.length + " assumptions", ex.answers.length + " owner answers",
    ].concat(ex.superseded ? [ex.superseded + " superseded"] : []);
    const more = (title, count, body, open) => el("details", {class: "more", open: open || null},
      el("summary", {}, title + " (" + count + ")"), el("div", {}, body));
    return el("section", {}, el("h2", {}, "Request: original and expanded"),
      el("div", {class: "request"},
        el("div", {class: "card"}, el("h3", {}, "Original, verbatim"),
          el("div", {class: "meta"}, el("span", {}, num(original.chars) + " chars"), el("span", {}, original.sentences.length + " sentences"),
            el("span", {class: "mono"}, "RUN/" + original.file)),
          el("pre", {class: "verbatim"}, original.text)),
        el("div", {class: "card"}, el("h3", {}, "Expanded by planning"),
          el("ul", {class: "stage-list"}, ex.stages.map((stage) => el("li", {class: stage.state === "accepted" ? "" : "pending", title: stage.summary || ""},
            el("span", {}, stage.state === "accepted" ? "✓" : "·"), el("strong", {}, stage.stage),
            el("span", {}, stage.headline || "pending", stage.improve ? " " : null, stage.improve ? el("span", {class: "b imp"}, "I") : null)))),
          el("div", {class: "counts"}, counts.map((text) => el("span", {class: "tag"}, text))))),
      more("Sentence by sentence: the original, then how intake read it", original.sentences.length,
        el("div", {class: "sentences"}, original.sentences.map((sentence) => el("div", {class: "sentence"},
          el("span", {class: "sn"}, "S" + sentence.n), el("span", {}, sentence.text),
          sentence.readings.length
            ? el("span", {class: "reading"}, sentence.readings.map((r) => el("div", {}, el("span", {class: "tag " + (r.kind === "boundary" ? "amber" : r.kind.includes("question") ? "red" : "green")}, r.kind), " " + r.text)))
            : el("span", {class: "reading none"}, ex.through ? "not read by intake" : "intake not accepted yet")))), true),
      more("Requirements in the living spec", ex.requirements.length,
        ex.requirements.length ? [el("div", {class: "meta"}, el("span", {class: "mono"}, ex.spec_file))].concat(ex.requirements.map((r) =>
          el("details", {class: "req"}, el("summary", {}, el("strong", {}, r.id), " " + r.title + " ", el("span", {class: "tag"}, r.section)), el("pre", {}, r.body))))
          : el("div", {class: "note"}, "none yet")),
      more("Work items and their steps", ex.work_items.length,
        ex.work_items.length ? ex.work_items.map((item) => el("div", {class: "item"}, el("strong", {}, item.id + " " + item.title),
          el("div", {class: "meta"}, item.context),
          item.steps.length ? el("ol", {}, item.steps.map((step) => el("li", {}, el("span", {class: "mono"}, step.id), " " + step.task + (step.deps.length ? " (after " + step.deps.join(", ") + ")" : "")))) : null))
          : el("div", {class: "note"}, "set by the plan stage")),
      more("Assumptions the plan recorded", ex.assumptions.length,
        ex.assumptions.length ? ex.assumptions.map((a) => el("div", {class: "item"}, el("span", {class: "mono"}, a.id || ""), " ",
          el("span", {class: "tag"}, a.disposition || ""), " " + a.assumption)) : el("div", {class: "note"}, "none")),
      more("Owner answers", ex.answers.length,
        ex.answers.length ? ex.answers.map((a) => el("div", {class: "item"}, el("span", {class: "mono"}, "RUN/" + a.file), el("pre", {class: "verbatim"}, a.text)))
          : el("div", {class: "note"}, "none")),
      more("Planning summaries", ex.stages.filter((s) => s.state === "accepted").length,
        ex.stages.filter((s) => s.state === "accepted").map((s) => el("div", {class: "item"}, el("strong", {}, s.stage), " " + (s.headline || ""),
          el("div", {class: "meta"}, s.summary || "")))));
  }

  function chip(slot) {
    const found = marks(slot);
    const badges = found.map(([kind, text]) => el("span", {class: BADGE[kind]}, text));
    const title = [slot.stage + (slot.group ? " (" + slot.group + ")" : "") + ": " + slot.state, slot.purpose,
      ...found.map((m) => m[2]), slot.headline ? "Result: " + slot.headline : "", slot.at ? "Accepted " + slot.at : ""].filter(Boolean).join("\n");
    return el("span", {class: "chip " + slot.state, title, role: slot.action ? "button" : null, tabindex: slot.action ? "0" : null,
      onclick: slot.action ? () => focusAction(slot.action) : null}, slot.stage, badges);
  }

  function plan() {
    return el("section", {}, el("h2", {}, "Plan: every stage"),
      el("div", {class: "card plan"}, TRACE.plan.map((row) => el("div", {class: "plan-row"},
        el("div", {class: "plan-label", title: row.label}, row.label,
          row.slots.length ? el("small", {}, [row.position, row.done + " of " + row.slots.length + " done"].filter(Boolean).join(" · ")) : null),
        row.slots.length ? el("div", {class: "chips"}, row.slots.map(chip)) : el("div", {class: "note"}, row.note || ""))),
        legend()));
  }

  // The legend names only what this run's plan shows; its samples never animate.
  function legend() {
    const slots = TRACE.plan.flatMap((row) => row.slots);
    const states = ["done", "current", "reopened", "pending"].filter((name) => slots.some((slot) => slot.state === name));
    const seen = new Map();
    for (const slot of slots) for (const [kind] of marks(slot)) seen.set(kind, true);
    const words = {steps: ["N steps", "implement, once per step"], runs: ["×N", "accepted N times"], back: ["↩N", "sent back"],
      imp: ["I", "Improve reviewed"], ref: ["!N", "refused"]};
    return el("div", {class: "legend"},
      states.map((name) => el("span", {}, el("span", {class: "chip sample " + name}, name))),
      [...seen.keys()].map((kind) => el("span", {}, el("span", {class: BADGE[kind]}, words[kind][0]), " " + words[kind][1])),
      el("span", {}, "click a stage for its events"));
  }

  // ---------------------------------------------------------------- timeline
  function eventRow(ev) {
    const failed = ev.kind === "command" && ev.exit;
    const refusal = failed && !ev.check_only;
    const kind = failed ? (ev.check_only ? "check" : "refused") : ev.kind;
    let body = [];
    if (ev.kind === "command") {
      body.push(el("span", {class: "mono"}, ev.verb + (ev.action ? " " + short(ev.action) : "")), " → exit " + ev.exit);
      for (const a of ev.accepted || []) body.push(" · ", el("span", {class: "tag green"}, "accepted " + where(a) + " (" + a.outcome + ")"));
      const rev = ev.rev || [];
      if (rev[0] === null || rev[0] === undefined) { if (ev.stage && ev.stage[1]) body.push(" · at " + ev.stage[1]); }
      else if (rev[0] !== rev[1] && rev[1] !== undefined && rev[1] !== null) body.push(" · r" + rev[0] + "→r" + rev[1]);
      if (ev.stage && ev.stage[0] && ev.stage[0] !== ev.stage[1]) body.push(" · " + ev.stage[0] + " → " + ev.stage[1]);
      body.push(el("span", {class: "tag"}, ev.ms + " ms"));
      if (failed) body.push(el("pre", {}, ev.error || "(no message recorded)"));
    } else if (ev.kind === "packet") {
      body.push(where(ev) + (ev.reviewed ? " (reviewing " + ev.reviewed + ")" : "") + " · " + num(ev.chars) + " chars · ",
        ev.whole ? "printed whole" : "printed head " + num(ev.printed) + " chars", " ");
      if (ev.repeat) body.push(el("span", {class: "tag"}, "reprint, same text"));
      body.push(el("button", {onclick: () => openPacket(ev.file, "Packet: " + where(ev), clock(ev.at) + " · " + num(ev.chars) + " chars")}, "view packet"));
      if (ev.head_file) body.push(" ", el("button", {onclick: () => openPacket(ev.head_file, "Printed head: " + where(ev))}, "view printed head"));
    } else if (ev.kind === "hook") {
      body.push(ev.hook + " → ", el("span", {class: "tag " + (ev.decision === "continue" ? "violet" : "")}, ev.decision), " " + (ev.why || ""));
      if (ev.host) body.push(el("span", {class: "tag"}, ev.host));
      if (ev.text) body.push(el("pre", {}, ev.text));
    } else if (ev.kind === "skill") {
      body.push(ev.gate ? "gate " + ev.gate + ": " + (ev.why || "") : el("span", {class: "mono"}, ev.skill), ev.args ? " “" + ev.args + "”" : "");
    } else if (ev.kind === "accepted") {
      body.push("accepted " + where(ev) + " (" + ev.outcome + ")");
    }
    return el("div", {class: "ev" + (refusal ? " refusal" : "") + (failed && !refusal ? " check" : "") + (ev.kind === "hook" ? " hook" : "")},
      el("time", {}, clock(ev.at || ev.ts)), el("span", {class: "kind " + (failed ? kind : ev.kind)}, kind), el("div", {class: "body"}, body));
  }

  function groups() {
    const list = [];
    const index = new Map();
    for (const ev of TRACE.events) {
      const owner = ev.action || ev.for_action || "(before the first packet)";
      if (!index.has(owner)) { index.set(owner, list.length); list.push({action: owner, events: []}); }
      list[index.get(owner)].events.push(ev);
    }
    if (nowAction && !index.has(nowAction)) list.push({action: nowAction, events: []});
    return list;
  }

  function matches(ev) {
    const refusal = ev.kind === "command" && ev.exit && !ev.check_only;
    if (ui.refusalsOnly && !refusal) return false;
    if (!ui.kinds.includes(ev.kind)) return false;
    if (ui.query) return JSON.stringify(ev).toLowerCase().includes(ui.query.toLowerCase());
    return true;
  }

  let timelineBox;
  function timeline() {
    const toolbar = el("div", {class: "toolbar"},
      KINDS.map((k) => el("label", {}, el("input", {type: "checkbox", checked: ui.kinds.includes(k), onchange: (e) => {
        ui.kinds = e.target.checked ? ui.kinds.concat(k) : ui.kinds.filter((x) => x !== k); save(); fill(); }}), k)),
      el("label", {}, el("input", {type: "checkbox", checked: ui.refusalsOnly, onchange: (e) => { ui.refusalsOnly = e.target.checked; save(); fill(); }}), "refusals only"),
      el("input", {type: "search", placeholder: "search events, ids, text…", value: ui.query, oninput: (e) => { ui.query = e.target.value; save(); fill(); }}),
      el("button", {onclick: () => toggleAll(true)}, "expand all"), el("button", {onclick: () => toggleAll(false)}, "collapse all"));
    timelineBox = el("div", {});
    fill();
    return el("section", {}, el("h2", {}, "Steps and events, in order"), toolbar, timelineBox);
  }

  function toggleAll(open) { for (const d of timelineBox.querySelectorAll("details")) d.open = open; rememberOpen(); }
  function rememberOpen() { store.set("open", [...timelineBox.querySelectorAll("details[open]")].map((d) => d.dataset.action)); }

  function fill() {
    const remembered = store.get("open", null);
    const all = groups();
    const shown = [];
    all.forEach((group, position) => {
      const events = group.events.filter(matches);
      const filtering = ui.refusalsOnly || ui.query || ui.kinds.length < KINDS.length;
      if (filtering && !events.length) return;
      const step = steps.get(group.action);
      const packet = group.events.find((e) => e.kind === "packet");
      const refused = group.events.filter((e) => e.kind === "command" && e.exit && !e.check_only).length;
      const hooks = group.events.filter((e) => e.kind === "hook").length;
      const packets = group.events.filter((e) => e.kind === "packet").length;
      const isNow = group.action === nowAction;
      let title, n, headline = "";
      if (step) { n = "#" + step.n; title = where(step); headline = step.headline; }
      else if (isNow) { n = "now"; title = where(TRACE.now); headline = TRACE.now.purpose; }
      else if (packet) { n = packet.stage === "improve" ? "I" : "–"; title = where(packet) + (packet.reviewed ? " (reviewing " + packet.reviewed + ")" : ""); }
      else if (group.events.length && group.events.every((e) => e.kind === "skill")) { n = "–"; title = "Skill calls"; headline = short(group.action); }
      else { n = "–"; title = short(group.action); }
      const tags = [];
      if (step) tags.push(el("span", {class: "tag " + (step.outcome === "done" ? "green" : "amber")}, step.outcome));
      if (isNow) tags.push(el("span", {class: "tag amber"}, "current"));
      if (step && step.improve) tags.push(el("span", {class: "tag violet"}, "Improve reviewed"));
      if (step && step.seconds !== null && step.seconds !== undefined) tags.push(el("span", {class: "tag"}, span(step.seconds)));
      if (packets) tags.push(el("span", {class: "tag"}, packets + " packet" + (packets > 1 ? "s" : "")));
      if (refused) tags.push(el("span", {class: "tag red"}, refused + " refused"));
      if (hooks) tags.push(el("span", {class: "tag violet"}, hooks + " hook"));
      if (step && step.at) tags.push(el("span", {class: "tag"}, clock(step.at)));
      const lastCopy = !run.traced && TRACE.texts["packets/" + group.action + ".md"] !== undefined;
      const open = remembered ? remembered.includes(group.action) : (isNow || position >= all.length - 3);
      const details = el("details", {class: "group" + (refused ? " has-refusal" : "") + (isNow ? " is-now" : ""), "data-action": group.action, open},
        el("summary", {}, el("span", {class: "n"}, n), el("span", {}, el("span", {class: "t"}, title), el("span", {class: "h"}, headline || "")), el("span", {class: "c"}, tags)),
        el("div", {class: "events"},
          lastCopy ? el("div", {class: "ev"}, el("time", {}, ""), el("span", {class: "kind packet"}, "packet"),
            el("div", {class: "body"}, "last copy ", el("button", {onclick: () => openPacket("packets/" + group.action + ".md", "Packet (last copy): " + title)}, "view packet"))) : null,
          events.length ? events.map(eventRow) : el("div", {class: "empty"}, "no recorded events"),
          el("div", {class: "ev"}, el("time", {}, ""), el("span", {}, ""), el("div", {class: "body meta"}, el("span", {class: "mono"}, group.action),
            step && step.result ? el("span", {class: "mono"}, "RUN/" + step.result) : null))));
      details.addEventListener("toggle", rememberOpen);
      shown.push(details);
    });
    timelineBox.replaceChildren(...(shown.length ? shown : [el("div", {class: "empty card"}, "No events match.")]));
  }

  function focusAction(action) {
    if (!action) return;
    ui.refusalsOnly = false; ui.query = ""; ui.kinds = KINDS.slice(); save();
    render();
    const target = timelineBox.querySelector('details[data-action="' + CSS.escape(action) + '"]');
    if (target) { target.open = true; rememberOpen(); target.scrollIntoView({behavior: "smooth", block: "start"}); }
  }

  // ---------------------------------------------------------------- page, live reload
  function save() { store.set("ui", ui); }
  function render() {
    const app = document.getElementById("app");
    app.replaceChildren(...[header(), nowCard(), requestSection(), plan(), timeline(),
      el("footer", {}, "Written by ", el("span", {class: "mono"}, "shiploop trace"), " from ", el("span", {class: "mono"}, run.dir),
        " · trace.jsonl " + num(run.trace_bytes) + " bytes" + (run.capped ? " (stopped growing at its cap)" : "") +
        " · state.md stays the authority; this page is a display.")].filter(Boolean));
  }
  let timer = null;
  function schedule() {
    clearTimeout(timer);
    if (run.status !== "active" || !ui.live) return;
    timer = setTimeout(() => {
      const busy = viewer.classList.contains("open") || document.activeElement && document.activeElement.type === "search";
      if (busy) return schedule();
      store.set("scroll", window.scrollY);
      location.reload();
    }, 10000);
  }
  render();
  const scroll = store.get("scroll", null);
  if (scroll !== null) { window.scrollTo(0, scroll); store.set("scroll", null); }
  if (ui.open && TRACE.texts[ui.open.file] !== undefined) openPacket(ui.open.file, ui.open.label, ui.open.info);
  schedule();
})();
</script>
</body>
</html>
"""
