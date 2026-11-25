"""Google Gemini / Material Design 3 single-page Multi-Run Hub template for ``shiploop view --serve``.

Zero external network dependencies: all CSS, SVG icons, and reactive vanilla JS
live inline so the viewer stays strictly loopback-only and CSP-compliant.
All dynamic text is inserted via ``textContent`` / DOM helpers (never ``innerHTML``
on untrusted data), and the unified poller enforces a hard ``>= 2000 ms`` floor.
"""
from __future__ import annotations

HUB_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>ShipLoop Hub · Concurrent Runs</title>
<style>
:root{
  --bg:#f4f7fc;--surface:#ffffff;--surface-2:#edf2fa;--surface-3:#e3eaf6;--surface-hover:#e8effa;
  --ink:#1b1f27;--ink-2:#444c5c;--muted:#687387;--line:#d8e1ee;--line-strong:#c0cde0;
  --primary:#1a73e8;--primary-ink:#ffffff;--primary-soft:#e8f0fe;--primary-text:#174ea6;
  --violet:#7627bb;--violet-soft:#f3e8fd;--emerald:#137333;--emerald-soft:#e6f4ea;
  --amber:#b06000;--amber-soft:#fef7e0;--rose:#c5221f;--rose-soft:#fce8e6;
  --cyan:#00639b;--cyan-soft:#dff1ff;
  --aurora:linear-gradient(135deg,#1a73e8 0%,#7b5cd6 52%,#d96570 100%);
  --aurora-soft:linear-gradient(135deg,rgba(26,115,232,.11) 0%,rgba(123,92,214,.09) 55%,rgba(217,101,112,.09) 100%);
  --shadow-1:0 1px 3px rgba(16,24,40,.06),0 1px 2px rgba(16,24,40,.04);
  --shadow-2:0 10px 30px rgba(20,34,66,.08);
  --shadow-drawer:-16px 0 42px rgba(15,23,42,.18);
  --font-sans:"Google Sans","Plus Jakarta Sans",ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --font-mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --ease:cubic-bezier(0.2,0,0,1);
}
:root[data-theme="dark"]{
  --bg:#0b0f17;--surface:#121824;--surface-2:#182030;--surface-3:#202b40;--surface-hover:#222e46;
  --ink:#eef2fb;--ink-2:#c2cbdc;--muted:#8d99b2;--line:rgba(255,255,255,.09);--line-strong:rgba(255,255,255,.16);
  --primary:#8ab4f8;--primary-ink:#072047;--primary-soft:rgba(138,180,248,.16);--primary-text:#aecbfa;
  --violet:#c58af9;--violet-soft:rgba(197,138,249,.16);--emerald:#81c995;--emerald-soft:rgba(129,201,149,.16);
  --amber:#fdd663;--amber-soft:rgba(253,214,99,.15);--rose:#f28b82;--rose-soft:rgba(242,139,130,.16);
  --cyan:#78d9ec;--cyan-soft:rgba(120,217,236,.15);
  --aurora:linear-gradient(135deg,#669df6 0%,#b485f6 52%,#f28b82 100%);
  --aurora-soft:linear-gradient(135deg,rgba(102,157,246,.15) 0%,rgba(180,133,246,.13) 55%,rgba(242,139,130,.12) 100%);
  --shadow-1:0 1px 3px rgba(0,0,0,.35);--shadow-2:0 16px 40px rgba(0,0,0,.42);--shadow-drawer:-16px 0 48px rgba(0,0,0,.55);
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 var(--font-sans);-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
button,input,textarea,select{font:inherit;color:inherit}
a{color:var(--primary);text-decoration:none}a:hover{text-decoration:underline}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
.mono{font-family:var(--font-mono);font-size:.82em}
.muted{color:var(--muted)}
.app-shell{min-height:100vh;display:flex;flex-direction:column}

/* Top App Bar */
.topbar{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:12px;padding:10px 18px;background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.brand-wrap{display:flex;align-items:center;gap:10px;min-width:0}
.spark-badge{width:34px;height:34px;border-radius:12px;background:var(--aurora-soft);border:1px solid var(--line-strong);display:grid;place-items:center;flex:none}
.brand-title{font-weight:700;font-size:1rem;letter-spacing:-.02em;white-space:nowrap}
.brand-sub{font-size:.74rem;color:var(--muted);display:none}
@media(min-width:960px){.brand-sub{display:inline}}
.top-stats{display:flex;flex-wrap:wrap;gap:6px;margin-left:8px}
.stat-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:.75rem;font-weight:600;background:var(--surface-2);border:1px solid var(--line);color:var(--ink-2)}
.stat-chip.warn{background:var(--amber-soft);color:var(--amber);border-color:transparent}
.stat-chip.live{background:var(--primary-soft);color:var(--primary-text);border-color:transparent}
.top-spacer{flex:1}
.top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.icon-btn,.m3-btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink-2);border-radius:999px;padding:6px 12px;font-size:.78rem;font-weight:600;cursor:pointer;transition:background .18s var(--ease),border-color .18s var(--ease),transform .12s var(--ease)}
.icon-btn{padding:6px 9px}
.icon-btn:hover,.m3-btn:hover{background:var(--surface-2);border-color:var(--line-strong)}
.m3-btn.tonal{background:var(--primary-soft);color:var(--primary-text);border-color:transparent}
.m3-btn.primary{background:var(--primary);color:var(--primary-ink);border-color:transparent}
.m3-btn.active{background:var(--primary);color:var(--primary-ink);border-color:transparent}
.m3-btn:disabled{opacity:.5;cursor:default}
.cadence-select{border:1px solid var(--line);background:var(--surface);color:var(--ink-2);border-radius:999px;padding:5px 10px;font-size:.76rem;font-weight:600;cursor:pointer}
.poll-pill{display:inline-flex;align-items:center;gap:7px;padding:5px 11px;border-radius:999px;background:var(--surface-2);border:1px solid var(--line);font-size:.74rem;color:var(--ink-2)}
.pulse-dot{width:8px;height:8px;border-radius:50%;background:var(--emerald);position:relative;flex:none}
.pulse-dot.anim::after{content:"";position:absolute;inset:-4px;border-radius:50%;border:2px solid currentColor;opacity:.45;animation:ping 1.8s cubic-bezier(0,0,.2,1) infinite}
.pulse-dot.paused{background:var(--muted)}.pulse-dot.warn{background:var(--amber)}
@keyframes ping{75%,100%{transform:scale(1.9);opacity:0}}

/* Workspace Grid */
.workspace{flex:1;display:grid;grid-template-columns:332px minmax(0,1fr);min-height:0}
.workspace.rail-collapsed{grid-template-columns:0 minmax(0,1fr)}
.workspace.rail-collapsed .rail{display:none}

/* Session Rail */
.rail{background:var(--surface);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0;max-height:calc(100vh - 57px);position:sticky;top:57px}
.rail-head{padding:12px 14px 10px;border-bottom:1px solid var(--line);display:grid;gap:8px}
.search-box{width:100%;padding:8px 12px;border-radius:12px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink);font-size:.82rem}
.search-box::placeholder{color:var(--muted)}
.filter-row{display:flex;gap:5px;flex-wrap:wrap}
.filter-pill{border:1px solid var(--line);background:transparent;color:var(--muted);border-radius:999px;padding:3px 10px;font-size:.73rem;font-weight:600;cursor:pointer}
.filter-pill.active{background:var(--primary-soft);color:var(--primary-text);border-color:transparent}
.rail-scroll{flex:1;overflow-y:auto;padding:10px 10px 24px;display:grid;gap:14px;align-content:start}
.rail-group-title{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:4px 8px 2px;display:flex;justify-content:space-between}
.rail-list{display:grid;gap:6px}
.rail-item{text-align:left;width:100%;border:1px solid var(--line);background:var(--surface-2);border-radius:16px;padding:11px 12px;cursor:pointer;display:grid;gap:6px;transition:background .16s var(--ease),border-color .16s var(--ease),transform .12s var(--ease)}
.rail-item:hover{background:var(--surface-hover);border-color:var(--line-strong)}
.rail-item.selected{background:var(--primary-soft);border-color:color-mix(in srgb,var(--primary) 55%,transparent);box-shadow:inset 3px 0 0 var(--primary)}
.rail-item.attention{border-left:3px solid var(--amber)}
.rail-item.blocked{border-left:3px solid var(--rose)}
.rail-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.rail-repo{font-size:.72rem;font-weight:700;color:var(--ink-2);display:flex;align-items:center;gap:6px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rail-title{font-size:.84rem;font-weight:600;line-height:1.3;color:var(--ink);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rail-meta{display:flex;flex-wrap:wrap;gap:4px 8px;font-size:.71rem;color:var(--muted);align-items:center}
.mini-bars{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.mini-bar{height:3px;border-radius:99px;background:var(--line);overflow:hidden}
.mini-bar span{display:block;height:100%;background:var(--primary);border-radius:inherit}

/* Main Canvas */
.stage-canvas{min-width:0;padding:20px 24px 72px;max-width:1320px;width:100%;margin:0 auto;display:grid;gap:18px;align-content:start}
.banner{padding:12px 16px;border-radius:16px;background:var(--amber-soft);color:var(--amber);border:1px solid color-mix(in srgb,var(--amber) 30%,transparent);font-size:.84rem;display:flex;gap:10px;align-items:flex-start}
.banner.danger{background:var(--rose-soft);color:var(--rose);border-color:color-mix(in srgb,var(--rose) 30%,transparent)}

/* Status Pills */
.pill{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:3px 10px;font-size:.72rem;font-weight:700;white-space:nowrap;background:var(--surface-3);color:var(--ink-2)}
.pill-active{background:var(--emerald-soft);color:var(--emerald)}
.pill-reviewing{background:var(--violet-soft);color:var(--violet)}
.pill-awaiting,.pill-service,.pill-paused{background:var(--amber-soft);color:var(--amber)}
.pill-blocked,.pill-halted{background:var(--rose-soft);color:var(--rose)}
.pill-done{background:var(--emerald-soft);color:var(--emerald)}
.pill-primary{background:var(--primary-soft);color:var(--primary-text)}
.pill-cyan{background:var(--cyan-soft);color:var(--cyan)}

/* Overview Grid */
.overview-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:18px 20px;box-shadow:var(--shadow-1);display:grid;gap:12px}
.ov-card{transition:transform .16s var(--ease),border-color .16s var(--ease)}
.ov-card:hover{transform:translateY(-2px);border-color:var(--line-strong)}
.ov-card.attention{border-left:4px solid var(--amber)}
.ov-card.blocked{border-left:4px solid var(--rose)}
.card-title{margin:0;font-size:1.02rem;line-height:1.35;overflow-wrap:anywhere}
.subline{font-size:.76rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 12px}
.where-box{font-size:.82rem;background:var(--surface-2);border-left:3px solid var(--primary);padding:9px 12px;border-radius:0 12px 12px 0;overflow-wrap:anywhere}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:.72rem;padding:3px 9px;border-radius:999px;background:var(--surface-2);border:1px solid var(--line);color:var(--ink-2)}
.chip.warn{background:var(--amber-soft);color:var(--amber);border-color:transparent;font-weight:600}
.chip.danger{background:var(--rose-soft);color:var(--rose);border-color:transparent;font-weight:600}
.chip.good{background:var(--emerald-soft);color:var(--emerald);border-color:transparent;font-weight:600}
.chip.violet{background:var(--violet-soft);color:var(--violet);border-color:transparent;font-weight:600}
.phases{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.phase{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:8px 10px;font-size:.74rem}
.bar{height:5px;border-radius:999px;background:var(--surface-3);margin-top:6px;overflow:hidden}.bar span{display:block;height:100%;background:var(--aurora);border-radius:inherit;transition:width .35s var(--ease)}
.links{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.btn-copy,.mini-link{font-size:.76rem;font-weight:600;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);border-radius:999px;padding:5px 11px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.btn-copy:hover,.mini-link:hover{background:var(--surface-3);text-decoration:none}

/* Gemini Prompt Hero */
.hero{position:relative;overflow:hidden;border-radius:24px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-2);padding:22px 24px;display:grid;gap:16px}
.hero::before{content:"";position:absolute;inset:0 0 auto 0;height:4px;background:var(--aurora)}
.hero.is-live::after{content:"";position:absolute;top:-80px;right:-60px;width:320px;height:220px;background:radial-gradient(circle,rgba(102,157,246,.18),transparent 70%);pointer-events:none}
.hero-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
.eyebrow{font-size:.69rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
.hero h1{margin:0;font-size:clamp(1.25rem,2.4vw,1.72rem);line-height:1.25;letter-spacing:-.025em;overflow-wrap:anywhere}
.hero-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.prompt-details{border:1px solid var(--line);background:var(--surface-2);border-radius:14px;padding:10px 14px}
.prompt-details summary{cursor:pointer;font-size:.8rem;font-weight:600;color:var(--ink-2);display:flex;justify-content:space-between;align-items:center;list-style:none}
.prompt-details summary::-webkit-details-marker{display:none}
.prompt-pre{margin:10px 0 0;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.84rem;line-height:1.55;max-height:280px;overflow:auto;color:var(--ink)}

/* Segmented Tabs */
.tabbar{display:flex;gap:6px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--line);padding:6px;border-radius:999px;box-shadow:var(--shadow-1);width:fit-content;max-width:100%}
.tab-btn{border:0;background:transparent;color:var(--muted);padding:7px 15px;border-radius:999px;font-size:.8rem;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:background .16s var(--ease),color .16s var(--ease)}
.tab-btn:hover{color:var(--ink);background:var(--surface-2)}
.tab-btn.active{background:var(--primary-soft);color:var(--primary-text)}

/* Live Focus Card */
.focus-card{border-radius:22px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow-1);padding:20px 22px;display:grid;gap:14px;position:relative;overflow:hidden}
.focus-card.active{background-image:var(--aurora-soft)}
.focus-card.attention{border-left:5px solid var(--amber)}
.focus-card.blocked{border-left:5px solid var(--rose)}
.focus-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.focus-where{font-size:1.08rem;font-weight:700;letter-spacing:-.015em}
.dwell-clock{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;background:var(--surface-2);border:1px solid var(--line);font-size:.78rem;font-weight:700;color:var(--ink)}
.focus-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.mini-panel{background:var(--surface-2);border:1px solid var(--line);border-radius:14px;padding:11px 13px;display:grid;gap:5px;align-content:start}
.mini-panel h4{margin:0;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.pass-log-pre{margin:4px 0 0;font-family:var(--font-mono);font-size:.74rem;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--ink-2);max-height:110px;overflow:auto}

/* Pipeline Sequence Map */
.pipeline-panel{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:18px 20px;display:grid;gap:14px}
.pipe-row{display:grid;grid-template-columns:220px 1fr;gap:12px;align-items:start;padding:8px 0;border-top:1px solid var(--line)}
.pipe-row:first-of-type{border-top:0;padding-top:0}
.pipe-label{font-weight:600;font-size:.84rem;display:grid;gap:3px}
.pipe-nodes{display:flex;flex-wrap:wrap;gap:7px}
.stage-node{display:inline-flex;align-items:center;gap:6px;padding:6px 11px;border-radius:12px;font-size:.76rem;font-weight:600;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);cursor:pointer;transition:transform .12s var(--ease),border-color .14s var(--ease)}
.stage-node:hover{transform:translateY(-1px);border-color:var(--primary)}
.stage-node.done{background:var(--emerald-soft);color:var(--emerald);border-color:transparent}
.stage-node.current{background:var(--primary-soft);color:var(--primary-text);border-color:var(--primary);box-shadow:0 0 0 2px color-mix(in srgb,var(--primary) 20%,transparent)}
.stage-node.reopened{background:var(--amber-soft);color:var(--amber);border:1px dashed var(--amber)}
.stage-node.pending{background:transparent;border-style:dashed;color:var(--muted);cursor:default}
.micro{font-size:.66rem;padding:1px 5px;border-radius:999px;background:rgba(127,127,127,.16);font-weight:700}
.micro.imp{background:var(--violet-soft);color:var(--violet)}
.micro.back{background:var(--amber-soft);color:var(--amber)}
.micro.ref{background:var(--rose-soft);color:var(--rose)}
.dwell-strip{display:grid;gap:6px;padding-top:6px;border-top:1px solid var(--line)}
.dwell-bar{height:10px;border-radius:999px;overflow:hidden;display:flex;background:var(--surface-2);gap:2px}
.dwell-seg{height:100%;min-width:4px}
.dwell-legend{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:.72rem;color:var(--muted)}
.swatch{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;vertical-align:middle}

/* Accomplishment Story Feed */
.feed-toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
.story-timeline{position:relative;padding-left:22px;display:grid;gap:12px}
.story-timeline::before{content:"";position:absolute;left:7px;top:12px;bottom:12px;width:2px;background:var(--line)}
.story-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:14px 16px;display:grid;gap:9px;transition:border-color .16s var(--ease)}
.story-card::before{content:"";position:absolute;left:-19px;top:20px;width:10px;height:10px;border-radius:50%;background:var(--emerald);border:2px solid var(--bg)}
.story-card.current::before{background:var(--primary);box-shadow:0 0 0 4px var(--primary-soft)}
.story-card.send-back::before,.story-card.replan::before{background:var(--amber)}
.story-card.blocked::before{background:var(--rose)}
.story-card.highlight{border-color:var(--primary);box-shadow:0 0 0 2px var(--primary-soft)}
.story-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}
.story-headline{font-size:.95rem;font-weight:600;line-height:1.4;color:var(--ink)}
.trans-callout{padding:7px 11px;border-radius:10px;font-size:.78rem;display:flex;align-items:center;gap:8px;background:var(--surface-2);color:var(--ink-2)}
.trans-callout.send-back,.trans-callout.replan{background:var(--amber-soft);color:var(--amber)}
.trans-callout.blocked{background:var(--rose-soft);color:var(--rose)}
.trans-callout.add-work{background:var(--violet-soft);color:var(--violet)}
.story-expand{border-top:1px solid var(--line);padding-top:10px;margin-top:2px;display:grid;gap:10px}
.story-expand summary{cursor:pointer;font-size:.77rem;font-weight:600;color:var(--primary);list-style:none}
.story-expand summary::-webkit-details-marker{display:none}
.ev-list{display:grid;gap:6px;margin-top:6px}
.ev-row{display:grid;grid-template-columns:72px 76px minmax(0,1fr);gap:8px;font-size:.76rem;padding:6px 9px;border-radius:10px;background:var(--surface-2);align-items:baseline}
.ev-row.refused{background:var(--rose-soft)}

/* Tables, DAG, Docs, Notes */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.table-wrap{overflow-x:auto}
table.m3{width:100%;border-collapse:collapse;font-size:.8rem}
table.m3 th{text-align:left;font-size:.71rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:8px 10px;border-bottom:1px solid var(--line)}
table.m3 td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.graph-viewport{overflow:auto;border:1px solid var(--line);border-radius:14px;background:var(--surface-2);padding:10px;max-height:62vh}
.note-composer{display:grid;gap:10px;border-left:4px solid var(--primary)}
.note-composer textarea{width:100%;min-height:80px;border-radius:12px;border:1px solid var(--line);background:var(--surface-2);padding:10px 12px;resize:vertical}

/* Slide-over Artifact Drawer & Snackbar */
.drawer-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.38);z-index:50;display:none}
.drawer-backdrop.open{display:block}
.drawer{position:fixed;inset:0 0 0 auto;width:min(780px,96vw);background:var(--surface);border-left:1px solid var(--line);box-shadow:var(--shadow-drawer);z-index:60;display:flex;flex-direction:column;transform:translateX(100%);transition:transform .24s var(--ease)}
.drawer.open{transform:translateX(0)}
.drawer-head{padding:16px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.drawer-body{flex:1;overflow:auto;padding:16px 20px}
.drawer-pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;font-family:var(--font-mono);font-size:.8rem;line-height:1.58;background:var(--surface-2);padding:14px 16px;border-radius:14px;border:1px solid var(--line)}
.snackbar{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--ink);color:var(--bg);padding:9px 18px;border-radius:999px;font-size:.8rem;font-weight:600;opacity:0;pointer-events:none;transition:opacity .2s var(--ease),transform .2s var(--ease);z-index:80;box-shadow:var(--shadow-2)}
.snackbar.show{opacity:1;transform:translateX(-50%) translateY(0)}
.empty{background:var(--surface);border:1px dashed var(--line-strong);border-radius:18px;padding:28px;text-align:center;color:var(--muted)}

@media(max-width:980px){
  .workspace{grid-template-columns:1fr}
  .rail{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line)}
  .two-col,.pipe-row{grid-template-columns:1fr}
}
@media(max-width:640px){
  .stage-canvas{padding:14px 12px 56px}
  .phases{grid-template-columns:1fr}
  .ev-row{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){
  *{transition:none!important;animation:none!important}
}
</style>
</head>
<body>
<div class="app-shell">
  <header class="topbar">
    <div class="brand-wrap">
      <button class="icon-btn" id="toggle-rail" type="button" title="Toggle session rail" aria-label="Toggle session rail"></button>
      <div class="spark-badge" id="brand-spark" aria-hidden="true"></div>
      <div>
        <div class="brand-title">ShipLoop Hub</div>
        <span class="brand-sub">Concurrent Delivery Studio</span>
      </div>
    </div>
    <div class="top-stats" id="top-stats"></div>
    <div class="top-spacer"></div>
    <div class="top-actions">
      <button class="m3-btn" id="mode-overview" type="button">All Runs</button>
      <div class="poll-pill" id="poll-pill">
        <span class="pulse-dot anim" id="poll-dot"></span>
        <span id="poll-status">Connecting…</span>
      </div>
      <select class="cadence-select" id="cadence-select" aria-label="Polling interval (minimum 2 seconds)">
        <option value="2000">Poll: 2s</option>
        <option value="3000">Poll: 3s</option>
        <option value="5000">Poll: 5s</option>
        <option value="10000">Poll: 10s</option>
      </select>
      <button class="m3-btn" id="toggle-live" type="button">Pause</button>
      <button class="m3-btn" id="refresh-now" type="button">Check now</button>
      <button class="icon-btn" id="theme-toggle" type="button" title="Toggle light/dark theme" aria-label="Toggle theme"></button>
    </div>
  </header>

  <div class="workspace" id="workspace">
    <aside class="rail" aria-label="Concurrent ShipLoop sessions">
      <div class="rail-head">
        <input class="search-box" id="q" type="search" placeholder="Search runs, repos, prompts… (/)">
        <div class="filter-row" id="rail-filters">
          <button class="filter-pill active" data-filter="all" type="button">All</button>
          <button class="filter-pill" data-filter="attention" type="button">Attention</button>
          <button class="filter-pill" data-filter="active" type="button">Active</button>
          <button class="filter-pill" data-filter="done" type="button">Finished</button>
        </div>
      </div>
      <div class="rail-scroll" id="rail-list"><div class="empty">Scanning runs…</div></div>
    </aside>

    <main class="stage-canvas" id="main-canvas">
      <div class="empty">Loading ShipLoop sessions…</div>
    </main>
  </div>
</div>

<div class="drawer-backdrop" id="drawer-backdrop"></div>
<aside class="drawer" id="drawer" aria-label="Artifact inspector" aria-hidden="true">
  <div class="drawer-head">
    <div style="min-width:0">
      <div class="eyebrow" id="drawer-eyebrow">ARTIFACT</div>
      <h3 id="drawer-title" style="margin:0;font-size:1.02rem;overflow-wrap:anywhere">Inspector</h3>
      <div class="subline" id="drawer-meta" style="margin-top:4px"></div>
    </div>
    <div style="display:flex;gap:8px;flex:none">
      <button class="m3-btn" id="drawer-copy" type="button">Copy</button>
      <button class="m3-btn primary" id="drawer-close" type="button">Close</button>
    </div>
  </div>
  <div class="drawer-body" id="drawer-body"><pre class="drawer-pre" id="drawer-text"></pre></div>
</aside>
<div class="snackbar" id="snackbar" role="status" aria-live="polite"></div>

<script>
(() => {
  "use strict";

  // Hard polling floor: NEVER exceed 1 poll per 2000 ms under any circumstance.
  const MIN_POLL_MS = 2000;
  const HIDDEN_POLL_MS = 10000;

  // ---- Theme init ----
  const rootEl = document.documentElement;
  const readTheme = () => {
    try {
      const saved = localStorage.getItem("shiploop-hub-theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch (_) {}
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };
  const applyTheme = (theme) => {
    rootEl.setAttribute("data-theme", theme);
    try { localStorage.setItem("shiploop-hub-theme", theme); } catch (_) {}
    const btn = document.getElementById("theme-toggle");
    if (btn) btn.replaceChildren(iconSvg(theme === "dark" ? "sun" : "moon"));
  };

  // ---- Safe DOM & SVG Icon Helpers ----
  const el = (tag, attrs, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = String(v);
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    for (const ch of children.flat(Infinity)) {
      if (ch === null || ch === undefined || ch === false) continue;
      node.append(ch instanceof Node ? ch : document.createTextNode(String(ch)));
    }
    return node;
  };
  const svgEl = (tag, attrs, ...children) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v !== null && v !== undefined && v !== false) node.setAttribute(k, String(v));
    }
    for (const ch of children.flat(Infinity)) {
      if (ch instanceof Node) node.append(ch);
    }
    return node;
  };
  const iconSvg = (name, size = 16) => {
    const paths = {
      spark: ["M12 2L14.6 9.4L22 12L14.6 14.6L12 22L9.4 14.6L2 12L9.4 9.4Z"],
      sidebar: ["M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5zm6-2v18"],
      sun: ["M12 4V2m0 20v-2m8-8h2M2 12h2m13.66-5.66 1.41-1.41M4.93 19.07l1.41-1.41m0-11.32L4.93 4.93m14.14 14.14-1.41-1.41M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"],
      moon: ["M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"],
      clock: ["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 5v5l3.5 2"],
      copy: ["M8 8V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-3m-2-6H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2z"],
      commit: ["M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-9-4h5m8 0h5"],
      check: ["M5 13l4 4L19 7"],
      alert: ["M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"],
      file: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm0 0v6h6"],
      arrow: ["M5 12h14m-6-6 6 6-6 6"],
    };
    const isSpark = name === "spark";
    const s = svgEl("svg", {width: size, height: size, viewBox: "0 0 24 24", fill: isSpark ? "url(#gemGrad)" : "none", stroke: isSpark ? "none" : "currentColor", "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round"});
    if (isSpark) {
      s.append(svgEl("defs", {}, svgEl("linearGradient", {id: "gemGrad", x1: "0%", y1: "0%", x2: "100%", y2: "100%"},
        svgEl("stop", {offset: "0%", "stop-color": "#4285f4"}),
        svgEl("stop", {offset: "52%", "stop-color": "#9b72cb"}),
        svgEl("stop", {offset: "100%", "stop-color": "#d96570"}))));
    }
    for (const d of (paths[name] || paths.file)) s.append(svgEl("path", {d}));
    return s;
  };

  // ---- Formatters ----
  const parseDate = (s) => {
    if (!s) return null;
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  };
  const ageText = (stamp) => {
    const d = parseDate(stamp);
    if (!d) return "time unknown";
    const s = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    if (s < 86400) return Math.floor(s / 3600) + "h ago";
    return Math.floor(s / 86400) + "d ago";
  };
  const fmtSpan = (sec) => {
    if (sec === null || sec === undefined || !Number.isFinite(Number(sec)) || Number(sec) < 0) return "—";
    const s = Math.round(Number(sec));
    if (s < 60) return s + "s";
    if (s < 3600) return Math.floor(s / 60) + "m " + String(s % 60).padStart(2, "0") + "s";
    return Math.floor(s / 3600) + "h " + String(Math.floor((s % 3600) / 60)).padStart(2, "0") + "m";
  };
  const fmtClock = (stamp) => {
    const d = parseDate(stamp);
    return d ? d.toLocaleTimeString(undefined, {hour: "2-digit", minute: "2-digit", second: "2-digit"}) : "";
  };
  const fmtTokens = (n) => {
    const v = Number(n);
    if (!Number.isFinite(v) || v < 0) return "";
    if (v < 1000) return String(Math.round(v)) + " tok";
    if (v < 1e6) return (v / 1000).toFixed(1).replace(/\.0$/, "") + "k tok";
    return (v / 1e6).toFixed(2).replace(/\.00$/, "") + "M tok";
  };
  const tokenTip = (u) => {
    if (!u || typeof u !== "object") return "";
    const bits = [];
    if (u.input_tokens !== undefined) bits.push("in: " + u.input_tokens);
    if (u.output_tokens !== undefined) bits.push("out: " + u.output_tokens);
    if (u.cached_tokens !== undefined) bits.push("cached: " + u.cached_tokens);
    if (u.cache_write_tokens !== undefined) bits.push("cache_write: " + u.cache_write_tokens);
    if (u.reasoning_tokens !== undefined) bits.push("reasoning: " + u.reasoning_tokens);
    if (u.total_tokens !== undefined) bits.push("total: " + u.total_tokens);
    if (u.peak_context !== undefined) bits.push("peak: " + u.peak_context);
    if (u.turns !== undefined) bits.push("turns: " + u.turns);
    return bits.join(" · ");
  };
  const shQuote = (s) => /^[A-Za-z0-9_./:=+-]+$/.test(String(s || "")) ? String(s) : "'" + String(s || "").replace(/'/g, "'\"'\"'") + "'";
  const snack = (msg) => {
    const bar = document.getElementById("snackbar");
    bar.textContent = msg;
    bar.classList.add("show");
    clearTimeout(snack._t);
    snack._t = setTimeout(() => bar.classList.remove("show"), 2200);
  };
  const copyText = (text, label = "Copied to clipboard") => {
    try { navigator.clipboard?.writeText(text); snack(label); } catch (_) { snack("Clipboard unavailable"); }
  };

  // ---- Application State ----
  const urlParams = new URLSearchParams(location.search);
  const state = {
    filter: "all",
    query: "",
    overview: urlParams.get("view") === "overview",
    selectedKey: urlParams.get("run") || "",
    activeTab: urlParams.get("tab") || "story",
    storyFilter: "all",
    storySort: "newest",
    storyQuery: "",
    traceKinds: new Set(["command", "packet", "hook", "skill", "accepted"]),
    traceRefusalsOnly: false,
    traceQuery: "",
    openCards: new Set(),
    openDetails: new Set(),
    noteDrafts: new Map(),
    runsPayload: null,
    runsVersion: "",
    detail: null,
    runVersion: "",
    paused: false,
    pollMs: Math.max(MIN_POLL_MS, Number(localStorage.getItem("shiploop-hub-poll") || MIN_POLL_MS) || MIN_POLL_MS),
    lastPollStart: 0,
    inFlight: false,
    wantSoon: false,
    timer: null,
    pendingRender: false,
    highlightAction: "",
  };

  const syncUrl = () => {
    const p = new URLSearchParams();
    if (state.overview) p.set("view", "overview");
    else if (state.selectedKey) p.set("run", state.selectedKey);
    if (!state.overview && state.activeTab && state.activeTab !== "story") p.set("tab", state.activeTab);
    const qs = p.toString();
    const nextUrl = location.pathname + (qs ? "?" + qs : "");
    try { history.replaceState(null, "", nextUrl); } catch (_) {}
  };

  // ---- Inspector Drawer ----
  const openDrawer = async ({eyebrow, title, meta, text, scope, relative}) => {
    const drawer = document.getElementById("drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    document.getElementById("drawer-eyebrow").textContent = eyebrow || "ARTIFACT";
    document.getElementById("drawer-title").textContent = title || relative || "Inspector";
    document.getElementById("drawer-meta").textContent = meta || "";
    const pre = document.getElementById("drawer-text");
    pre.textContent = text !== undefined ? text : "Loading artifact…";
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    if (text === undefined && state.selectedKey && relative) {
      try {
        const resp = await fetch(
          "/api/runs/" + encodeURIComponent(state.selectedKey) + "/artifact?scope="
          + encodeURIComponent(scope || "run") + "&path=" + encodeURIComponent(relative),
          {cache: "no-store"}
        );
        if (!resp.ok) {
          pre.textContent = "Unable to load artifact (" + resp.status + ").";
          return;
        }
        const data = await resp.json();
        document.getElementById("drawer-meta").textContent =
          data.path + " · " + data.bytes + " bytes · sha256 " + String(data.sha256 || "").slice(0, 12)
          + (data.truncated ? " (truncated at 256 KB)" : "");
        pre.textContent = data.content || "(empty file)";
      } catch (_) {
        pre.textContent = "Failed to fetch artifact from Hub.";
      }
    }
  };
  const closeDrawer = () => {
    document.getElementById("drawer").classList.remove("open");
    document.getElementById("drawer").setAttribute("aria-hidden", "true");
    document.getElementById("drawer-backdrop").classList.remove("open");
  };

  // ---- Busy guard so polling never interrupts selection or typing ----
  const isUserBusy = () => {
    try {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && String(sel).length > 0) return true;
    } catch (_) {}
    const act = document.activeElement;
    return !!(act && (act.tagName === "TEXTAREA" || (act.tagName === "INPUT" && act.type === "search")));
  };

  // ---- Render Top Stats & Session Rail ----
  const renderTopAndRail = () => {
    const data = state.runsPayload;
    if (!data) return;
    const c = data.counts || {};
    document.title = (c.attention > 0 ? "(" + c.attention + ") " : "") + "ShipLoop Hub · Concurrent Runs";
    document.getElementById("top-stats").replaceChildren(
      el("span", {class: "stat-chip"}, (c.total || 0) + " runs"),
      c.attention ? el("span", {class: "stat-chip warn"}, c.attention + " needs attention") : null,
      el("span", {class: "stat-chip live"}, (c.active || 0) + " active"),
      c.paused ? el("span", {class: "stat-chip"}, c.paused + " paused") : null,
      el("span", {class: "stat-chip"}, (c.done || 0) + " finished")
    );

    const needle = state.query.trim().toLowerCase();
    const visible = (data.runs || []).filter((r) => {
      if (state.filter === "attention" && r.priority_bucket !== 0) return false;
      if (state.filter === "active" && !["active", "reviewing"].includes(r.display_status)) return false;
      if (state.filter === "done" && !["done", "halted"].includes(r.display_status)) return false;
      if (!needle) return true;
      return [r.goal, r.run_id, r.repo_name, r.source_repo, r.where, r.display_label, r.model]
        .join(" ").toLowerCase().includes(needle);
    });

    const groups = [
      ["Needs attention", visible.filter((r) => r.priority_bucket === 0)],
      ["Active & Reviewing", visible.filter((r) => r.priority_bucket === 1)],
      ["Paused", visible.filter((r) => r.priority_bucket === 2)],
      ["Completed & Halted", visible.filter((r) => r.priority_bucket === 3)],
    ];
    const railNodes = [];
    for (const [title, rows] of groups) {
      if (!rows.length) continue;
      railNodes.push(el("div", {},
        el("div", {class: "rail-group-title"}, el("span", {}, title), el("span", {}, String(rows.length))),
        el("div", {class: "rail-list"}, rows.map((r) => {
          const inf = r.inflight || {};
          const selected = !state.overview && state.selectedKey === r.run_key;
          const cls = "rail-item" + (selected ? " selected" : "")
            + (r.display_status === "blocked" || r.display_status === "halted" ? " blocked" : (r.priority_bucket === 0 ? " attention" : ""));
          const stepTxt = inf.step_id && inf.step_total ? ` · ${inf.step_id} (${inf.step_number}/${inf.step_total})` : "";
          const modelTxt = r.model ? (r.model + (r.effort ? "/" + r.effort : "")) : (r.host || "");
          const bars = (r.phases || []).map((p) => {
            const tot = Number(p.total) || 0, dn = Number(p.done) || 0;
            const pct = p.state === "done" ? 100 : (tot > 0 ? Math.min(100, Math.round(100 * dn / tot)) : 0);
            return el("div", {class: "mini-bar"}, el("span", {style: "width:" + pct + "%"}));
          });
          return el("button", {
            type: "button",
            class: cls,
            onclick: () => selectRun(r.run_key),
          },
            el("div", {class: "rail-top"},
              el("span", {class: "rail-repo"},
                ["active", "reviewing"].includes(r.display_status) ? el("span", {class: "pulse-dot anim"}) : null,
                r.repo_name || r.repo || "repo"),
              el("span", {class: "pill pill-" + (r.display_status || "active")}, r.display_label || r.status)),
            el("div", {class: "rail-title"}, r.goal || r.run_id),
            el("div", {class: "mini-bars"}, bars),
            el("div", {class: "rail-meta"},
              el("span", {}, (r.stage || "") + stepTxt),
              modelTxt ? el("span", {}, modelTxt) : null,
              el("span", {"data-live-age": inf.last_event_at || ""}, ageText(inf.last_event_at))),
            (r.attention_reasons || []).length
              ? el("div", {class: "chips"}, r.attention_reasons.map((why) =>
                  el("span", {class: r.display_status === "blocked" ? "chip danger" : "chip warn"}, why)))
              : null);
        }))));
    }
    if (!railNodes.length) railNodes.push(el("div", {class: "empty"}, "No sessions match filter."));
    document.getElementById("rail-list").replaceChildren(...railNodes);
  };

  // ---- Overview Card Grid ----
  const renderOverview = () => {
    const data = state.runsPayload;
    const canvas = document.getElementById("main-canvas");
    if (!data) return;
    const conflicts = Object.entries(data.shared_repo_conflicts || {}).map(([repo, ids]) =>
      el("div", {class: "banner"},
        iconSvg("alert", 18),
        el("div", {}, "Shared source repo warning: ", el("strong", {}, repo),
          " has " + ids.length + " concurrent non-terminal runs (" + ids.join(", ") + "). Each builds in an isolated worktree; the second workspace return reconciles against the first.")));

    const needle = state.query.trim().toLowerCase();
    const runs = (data.runs || []).filter((r) => {
      if (state.filter === "attention" && r.priority_bucket !== 0) return false;
      if (state.filter === "active" && !["active", "reviewing"].includes(r.display_status)) return false;
      if (state.filter === "done" && !["done", "halted"].includes(r.display_status)) return false;
      if (!needle) return true;
      return [r.goal, r.run_id, r.repo_name, r.source_repo, r.where, r.display_label, r.model].join(" ").toLowerCase().includes(needle);
    });

    const cards = runs.map((r) => {
      const inf = r.inflight || {};
      const chips = [
        el("span", {class: "chip"}, "rev " + r.revision),
        el("span", {class: "chip"}, r.delegation || "inline"),
        r.host ? el("span", {class: "chip"}, r.host + (r.model ? ":" + r.model : "") + (r.effort ? "/" + r.effort : "")) : null,
        r.planning_summary ? el("span", {class: "chip"}, r.planning_summary) : null,
        inf.step_id && inf.step_total ? el("span", {class: "chip"}, "Step " + inf.step_id + " (" + inf.step_number + "/" + inf.step_total + ")") : null,
        inf.loop_iteration ? el("span", {class: "chip"}, "Loop pass " + inf.loop_iteration) : null,
        inf.plan_sandboxes ? el("span", {class: "chip"}, "Sandboxes " + inf.plan_sandboxes) : null,
        inf.plan_questions ? el("span", {class: "chip"}, "Exp Qs " + inf.plan_questions) : null,
        inf.improve_active ? el("span", {class: "chip violet"}, "Improve " + (inf.improve_review_mode || "") + (inf.improve_passes ? " · pass " + inf.improve_passes : "")) : null,
        typeof inf.last_check_yes === "boolean" ? el("span", {class: inf.last_check_yes ? "chip good" : "chip warn"}, "Check: " + (inf.last_check_yes ? "yes" : "no")) : null,
        (inf.open_notes || inf.carried_notes) ? el("span", {class: "chip warn"}, (inf.open_notes || 0) + " open note(s)") : null,
        ...(r.attention_reasons || []).map((why) => el("span", {class: r.display_status === "blocked" ? "chip danger" : "chip warn"}, why)),
      ];
      let copyBtn = null;
      if (r.run_dir && ["awaiting", "service", "paused", "blocked"].includes(r.display_status)) {
        const verb = r.display_status === "paused" ? "resume" : "status";
        const cmd = "python3 shiploop " + verb + " --run-dir=" + shQuote(r.run_dir);
        const baseLabel = r.display_status === "paused" ? "Copy resume cmd" : "Copy status cmd";
        copyBtn = el("button", {type: "button", class: "btn-copy", title: cmd, onclick: () => copyText(cmd, baseLabel + " copied")}, baseLabel);
      }
      const acc = r.latest_accomplishment;
      const cls = "card ov-card" + (r.display_status === "blocked" || r.display_status === "halted" ? " blocked" : (r.priority_bucket === 0 ? " attention" : ""));
      return el("article", {class: cls},
        el("div", {class: "hero-top"},
          el("div", {style: "min-width:0;flex:1"},
            el("h3", {class: "card-title"}, r.goal || r.run_id),
            el("div", {class: "subline"},
              el("span", {}, el("strong", {}, r.repo_name || r.repo)),
              el("span", {class: "mono"}, r.run_id),
              el("span", {"data-live-age": inf.last_event_at || ""}, ageText(inf.last_event_at)))),
          el("span", {class: "pill pill-" + (r.display_status || "active")}, r.display_label || r.status)),
        el("div", {class: "where-box"}, r.where || r.stage),
        acc && acc.headline ? el("div", {class: "subline"}, el("strong", {}, "Latest (" + acc.stage + "): "), acc.headline) : null,
        el("div", {class: "phases"}, (r.phases || []).map((p) => {
          const tot = Number(p.total) || 0, dn = Number(p.done) || 0;
          const pct = p.state === "done" ? 100 : (tot > 0 ? Math.min(100, Math.round(100 * dn / tot)) : 0);
          const lbl = p.state === "done" ? "done" : (tot > 0 ? p.done_label + "/" + tot : (p.state === "current" ? "active" : "pending"));
          return el("div", {class: "phase"}, el("div", {}, el("strong", {}, p.name), " · ", lbl), el("div", {class: "bar"}, el("span", {style: "width:" + pct + "%"})));
        })),
        el("div", {class: "chips"}, chips),
        el("div", {class: "links"},
          el("button", {type: "button", class: "m3-btn tonal", onclick: () => selectRun(r.run_key)}, "Open Studio →"),
          el("a", {class: "mini-link", href: r.urls.progress}, "Standalone"),
          el("a", {class: "mini-link", href: r.urls.trace}, "Trace"),
          r.urls.report ? el("a", {class: "mini-link", href: r.urls.report}, "Report") : null,
          copyBtn));
    });

    canvas.replaceChildren(
      ...conflicts,
      el("div", {class: "feed-toolbar"},
        el("div", {}, el("div", {class: "eyebrow"}, "MULTI-RUN OVERVIEW"), el("h2", {style: "margin:0"}, "All Concurrent Sessions (" + runs.length + ")")),
        el("span", {class: "muted", style: "font-size:.8rem"}, "Click any session to inspect its live story, gates, and artifacts")),
      runs.length ? el("div", {class: "overview-grid"}, cards) : el("div", {class: "empty"}, "No ShipLoop runs match the current filter.")
    );
  };

  // ---- Selected Run Detail Tabs ----
  const renderHero = (d) => {
    const r = d.run || {};
    const isLive = ["active", "reviewing"].includes(r.display_status);
    const runKey = r.run_key || state.selectedKey;
    const modelChip = r.model ? (r.host ? r.host + ":" : "") + r.model + (r.effort ? "/" + r.effort : "") : (r.host || "");
    const phaseNodes = (d.phases || []).map((p, idx) => {
      const tot = Number(p.total) || 0, dn = Number(p.done) || 0;
      const pct = p.state === "done" ? 100 : (tot > 0 ? Math.min(100, Math.round(100 * dn / tot)) : 0);
      const lbl = p.state === "done" ? "Complete" : (tot > 0 ? p.done_label + "/" + tot : (p.state === "current" ? "In progress" : "Pending"));
      return el("div", {class: "phase"},
        el("div", {style: "display:flex;justify-content:space-between"}, el("strong", {}, "0" + (idx + 1) + " " + p.name), el("span", {class: "muted"}, lbl)),
        el("div", {class: "bar"}, el("span", {style: "width:" + pct + "%"})));
    });
    const listEntry = (state.runsPayload && state.runsPayload.runs || []).find((x) => x.run_key === runKey);
    const conflictPeers = listEntry && listEntry.shared_repo_peers || [];
    return [
      conflictPeers.length ? el("div", {class: "banner"}, iconSvg("alert", 18),
        el("div", {}, "Shares source repo ", el("strong", {}, r.source_repo || r.repo), " with: " + conflictPeers.join(", "))) : null,
      el("section", {class: "hero" + (isLive ? " is-live" : "")},
        el("div", {class: "hero-top"},
          el("div", {style: "min-width:0;flex:1"},
            el("div", {class: "eyebrow"}, "ACTIVE PROMPT · " + (PathName(r.source_repo || r.repo) || "REPOSITORY")),
            el("h1", {}, r.goal || r.run_id)),
          el("div", {class: "hero-actions"},
            el("span", {class: "pill pill-" + (r.display_status || "active")},
              isLive ? el("span", {class: "pulse-dot anim"}) : null, r.display_label || r.status),
            el("a", {class: "mini-link", href: "/runs/" + encodeURIComponent(runKey) + "/progress.html"}, "Progress HTML"),
            el("a", {class: "mini-link", href: "/runs/" + encodeURIComponent(runKey) + "/trace.html"}, "Trace HTML"),
            r.has_report ? el("a", {class: "mini-link", href: "/runs/" + encodeURIComponent(runKey) + "/report.html"}, "Report HTML") : null)),
        el("div", {class: "chips"},
          el("span", {class: "chip mono"}, r.run_id),
          el("span", {class: "chip"}, "rev " + r.revision),
          modelChip ? el("span", {class: "chip pill-primary"}, modelChip) : null,
          el("span", {class: "chip"}, "delegation: " + (r.delegation || "inline")),
          r.planning_review ? el("span", {class: "chip"}, "plan-review: " + r.planning_review) : null,
          r.lint ? el("span", {class: "chip"}, "lint: " + r.lint) : null,
          r.elapsed_seconds !== null && r.elapsed_seconds !== undefined
            ? el("span", {class: "chip", title: "Recorded wall-clock span from start to last event; not model compute."
                + (r.paused_seconds && r.active_seconds !== null && r.active_seconds !== undefined
                    ? ` (active ${fmtSpan(r.active_seconds)}, paused ${fmtSpan(r.paused_seconds)})` : "")},
                "span: " + fmtSpan(r.elapsed_seconds)) : null,
          r.token_usage && r.token_usage.total_tokens
            ? el("span", {class: "chip", title: tokenTip(r.token_usage)}, fmtTokens(r.token_usage.total_tokens)) : null,
          r.owner_alive === false && r.status === "active"
            ? el("span", {class: "chip danger"}, "Host owner process not running") : null),
        (() => {
          const promptKey = "hero-prompt:" + runKey;
          const det = el("details", {class: "prompt-details", open: state.openDetails.has(promptKey) || null},
            el("summary", {}, el("span", {}, "Full Verbatim Prompt"),
              el("button", {type: "button", class: "btn-copy", onclick: (e) => { e.preventDefault(); e.stopPropagation(); copyText(r.prompt || "", "Prompt copied"); }}, iconSvg("copy", 13), "Copy prompt")),
            el("pre", {class: "prompt-pre"}, r.prompt || "Prompt unavailable."));
          det.addEventListener("toggle", () => {
            if (det.open) state.openDetails.add(promptKey);
            else state.openDetails.delete(promptKey);
          });
          return det;
        })(),
        el("div", {class: "phases"}, phaseNodes))
    ];
  };
  const PathName = (p) => { const s = String(p || "").replace(/\/+$/, ""); const i = s.lastIndexOf("/"); return i >= 0 ? s.slice(i + 1) : s; };

  const renderTabs = (d) => {
    const r = d.run || {};
    const tabs = [
      ["story", "Story & Flow"],
      ["plan", "Prompt & Plan"],
      ["gates", "Gates & Evidence"],
      ["trace", "Trace & Packets"],
      ["notes", "Notes (" + ((d.notes || []).length) + ")"],
    ];
    if (r.has_report || r.status === "done" || r.status === "halted") tabs.push(["report", "Report"]);
    if (!tabs.some(([id]) => id === state.activeTab)) state.activeTab = "story";
    return el("nav", {class: "tabbar", role: "tablist"}, tabs.map(([id, label]) =>
      el("button", {
        type: "button", role: "tab", "aria-selected": state.activeTab === id ? "true" : "false",
        class: "tab-btn" + (state.activeTab === id ? " active" : ""),
        onclick: () => { state.activeTab = id; syncUrl(); renderDetailOnly(); },
      }, label)));
  };

  const renderStoryTab = (d) => {
    const now = d.live_now || {};
    const r = d.run || {};
    const isStopped = !["active", "reviewing", "done"].includes(now.display_status);
    const liveSince = now.stage_started_at;
    const focusCls = "focus-card" + (["active", "reviewing"].includes(now.display_status) ? " active" : "")
      + (now.display_status === "blocked" || now.display_status === "halted" ? " blocked" : (isStopped ? " attention" : ""));

    const focusSubPanels = [];
    if (now.improve) {
      focusSubPanels.push(el("div", {class: "mini-panel"},
        el("h4", {}, "Improve Review Child"),
        el("div", {}, el("strong", {}, "Reviewing " + (now.improve.stage || "")),
          " · " + (now.improve.review_mode || "inline") + (now.improve.passes ? " · pass " + now.improve.passes : ""))));
    } else if (now.loop) {
      focusSubPanels.push(el("div", {class: "mini-panel"},
        el("h4", {}, "Until Loop"),
        el("div", {}, el("strong", {}, "Pass #" + now.loop.iteration), " · ", now.loop.status || "active",
          now.loop.exit_assessment ? " (" + now.loop.exit_assessment + ")" : ""),
        now.loop.handoff ? el("div", {class: "muted", style: "font-size:.77rem"}, now.loop.handoff) : null));
    }
    if (now.last_check) {
      focusSubPanels.push(el("div", {class: "mini-panel"},
        el("h4", {}, "Latest Check (" + (now.last_check.yes ? "Yes" : "Refused") + ")"),
        (now.last_check.gates || []).length
          ? el("div", {class: "chips"}, now.last_check.gates.map((g) =>
              el("span", {class: "chip " + (g.ok === true ? "good" : (g.ok === false ? "danger" : ""))}, g.label + ": " + g.detail)))
          : el("div", {class: "muted", style: "font-size:.78rem"}, now.last_check.reason || "Check recorded")));
    }
    if (now.pass_log) {
      focusSubPanels.push(el("div", {class: "mini-panel"},
        el("div", {style: "display:flex;justify-content:space-between;align-items:center"},
          el("h4", {}, "Live Pass Log"),
          el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({
            eyebrow: "PASS LOG", title: now.pass_log.path, scope: "run", relative: now.pass_log.path,
          })}, "Open full")),
        el("pre", {class: "pass-log-pre"}, now.pass_log.tail || "(empty)")));
    }

    const cliCmds = now.cli_commands || {};
    const focusCard = el("section", {class: focusCls},
      el("div", {class: "focus-head"},
        el("div", {style: "min-width:0;flex:1"},
          el("div", {class: "eyebrow"}, r.status === "done" ? "RUN COMPLETE" : "CURRENT STAGE"),
          el("div", {class: "focus-where"}, now.where || now.stage || r.status),
          el("div", {class: "muted", style: "font-size:.82rem;margin-top:3px"},
            now.step_task ? (now.step_id + ": " + now.step_task) : (now.next_text || now.purpose || ""))),
        el("div", {style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap"},
          liveSince && r.status !== "done" && r.status !== "halted"
            ? el("span", {class: "dwell-clock", title: "Wall-clock dwell since " + liveSince + " (not compute time)"},
                iconSvg("clock", 14),
                el("span", {"data-live-clock": liveSince}, fmtSpan(Math.max(0, (Date.now() - (parseDate(liveSince)?.getTime() || Date.now())) / 1000))))
            : null,
          now.packet_file
            ? el("button", {type: "button", class: "m3-btn tonal", onclick: () => openDrawer({
                eyebrow: "CURRENT PACKET", title: now.where || "Current packet", scope: "run", relative: now.packet_file,
              })}, iconSvg("file", 14), "View packet")
            : null)),
      now.reason ? el("div", {class: "banner" + (now.display_status === "blocked" ? " danger" : "")},
        iconSvg("alert", 17), el("div", {style: "flex:1"}, el("strong", {}, (now.display_label || "Stopped") + ": "), now.reason),
        cliCmds.primary ? el("button", {type: "button", class: "btn-copy", onclick: () => copyText(cliCmds.primary, "Command copied")},
          now.display_status === "paused" ? "Copy resume cmd" : "Copy status cmd") : null) : null,
      focusSubPanels.length ? el("div", {class: "focus-grid"}, focusSubPanels) : null);

    // Pipeline sequence map + dwell breakdown
    const dwellColors = ["#4285f4", "#9b72cb", "#137333", "#00897b", "#f9ab00", "#d96570"];
    const dwell = d.dwell_breakdown || [];
    const pipePanel = el("section", {class: "pipeline-panel"},
      el("div", {style: "display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px"},
        el("div", {}, el("div", {class: "eyebrow"}, "SEQUENCE & DWELL"), el("h3", {style: "margin:0;font-size:1rem"}, "Pipeline Map")),
        el("span", {class: "muted", style: "font-size:.75rem"}, "Click any stage to jump to its story card · durations are recorded dwell")),
      (d.pipeline || []).map((row) => el("div", {class: "pipe-row"},
        el("div", {class: "pipe-label"},
          el("span", {}, row.label),
          el("div", {class: "chips"},
            row.slice ? el("span", {class: "chip pill-cyan"}, row.slice) : null,
            row.concerns_mode === "deferred" ? el("span", {class: "chip violet"}, "rolling-wave") : null,
            row.duration_seconds !== null && row.duration_seconds !== undefined
              ? el("span", {class: "chip"}, fmtSpan(row.duration_seconds)) : null)),
        row.slots && row.slots.length
          ? el("div", {class: "pipe-nodes"}, row.slots.map((s) => {
              const badges = [];
              if (s.steps !== null && s.steps !== undefined) badges.push(el("span", {class: "micro"}, s.steps + "s"));
              else if ((s.runs - (s.sent_back || 0)) > 1) badges.push(el("span", {class: "micro"}, "×" + (s.runs - (s.sent_back || 0))));
              if (s.sent_back) badges.push(el("span", {class: "micro back"}, "↩" + s.sent_back));
              if (s.improve) badges.push(el("span", {class: "micro imp"}, "I"));
              if (s.refusals) badges.push(el("span", {class: "micro ref"}, "!" + s.refusals));
              return el("button", {
                type: "button",
                class: "stage-node " + (s.state || "pending"),
                disabled: !s.action && s.state === "pending",
                title: [s.stage, s.purpose, s.headline ? "Result: " + s.headline : ""].filter(Boolean).join("\n"),
                onclick: s.action ? () => jumpToAction(s.action) : null,
              },
                s.state === "done" ? "✓" : (s.state === "current" ? "▶" : (s.state === "reopened" ? "↺" : "·")),
                " ", s.stage,
                s.duration_seconds !== null && s.duration_seconds !== undefined ? el("span", {class: "muted", style: "font-weight:500"}, fmtSpan(s.duration_seconds)) : null,
                badges);
            }))
          : el("span", {class: "muted", style: "font-style:italic;font-size:.8rem"}, row.note || "Set by plan"))),
      dwell.length ? el("div", {class: "dwell-strip"},
        el("div", {class: "dwell-bar"}, dwell.map((seg, i) =>
          el("div", {class: "dwell-seg", style: `width:${Math.max(2, seg.pct)}%;background:${dwellColors[i % dwellColors.length]}`,
            title: `${seg.label}: ${fmtSpan(seg.seconds)} (${seg.pct}%)`}))),
        el("div", {class: "dwell-legend"}, dwell.map((seg, i) =>
          el("span", {}, el("span", {class: "swatch", style: "background:" + dwellColors[i % dwellColors.length]}),
            `${seg.label} · ${fmtSpan(seg.seconds)} (${seg.pct}%)`)))) : null);

    // Story feed
    const filterStoryCards = () => {
      const cardsAll = (d.story_cards || []).slice();
      const out = cardsAll.filter((c) => {
        if (state.storyFilter === "milestones") {
          const m = new Set(["intake", "plan", "prepare", "reflect-and-revise", "product-acceptance", "release", "handoff"]);
          if (!m.has(c.stage) && !c.is_current) return false;
        } else if (state.storyFilter === "issues") {
          if (c.outcome !== "send-back" && c.outcome !== "blocked" && !(c.counts && c.counts.refusals > 0)) return false;
        } else if (state.storyFilter === "improve") {
          if (!c.improve) return false;
        } else if (state.storyFilter === "gates") {
          if (!(c.gates && c.gates.length)) return false;
        }
        if (state.storyQuery.trim()) {
          const q = state.storyQuery.trim().toLowerCase();
          const blob = [c.stage, c.item, c.headline, c.summary, c.transition_note && c.transition_note.text, c.commit_sha].join(" ").toLowerCase();
          if (!blob.includes(q)) return false;
        }
        return true;
      });
      if (state.storySort === "newest") out.reverse();
      return out;
    };

    const buildStoryTimeline = (cards) => {
      const timelineNodes = cards.map((c) => {
        const tn = c.transition_note || {};
        const cardCls = "story-card" + (c.is_current ? " current" : "")
          + (tn.kind === "send-back" || tn.kind === "replan" ? " send-back" : (tn.kind === "blocked" ? " blocked" : ""))
          + (state.highlightAction === c.action ? " highlight" : "");
        const isOpen = state.openCards.has(c.action) || c.is_current;
        const summaryLabel = (open) => open ? "Hide details & events" : "Inspect summary, gates & " + ((c.events || []).length) + " trace events";
        const summaryEl = el("summary", {}, summaryLabel(isOpen));
        const details = el("details", {class: "story-expand", open: isOpen || null, "data-action": c.action},
          summaryEl,
          el("div", {style: "display:grid;gap:8px;margin-top:8px"},
            c.summary ? el("p", {style: "margin:0;font-size:.83rem;white-space:pre-wrap"}, c.summary) : null,
            c.lessons ? el("div", {class: "mini-panel"}, el("h4", {}, "Lessons Recorded"), el("div", {style: "font-size:.8rem"}, c.lessons)) : null,
            c.improve && c.improve.lessons ? el("div", {class: "mini-panel"}, el("h4", {}, "Improve Lessons"), el("div", {style: "font-size:.8rem"}, c.improve.lessons)) : null,
            c.decision_answer ? el("div", {class: "mini-panel"}, el("h4", {}, "Owner Answer (decisions/)"), el("div", {style: "font-size:.8rem"}, c.decision_answer)) : null,
            (c.owner_notes_handled || []).length ? el("div", {class: "mini-panel"}, el("h4", {}, "Owner Notes Accounted"),
              c.owner_notes_handled.map((nr) => el("div", {style: "font-size:.78rem"}, el("strong", {}, nr.note + " (" + nr.did + "): "), nr.detail))) : null,
            (c.refusal_previews || []).length ? el("div", {class: "mini-panel", style: "background:var(--rose-soft)"},
              el("h4", {style: "color:var(--rose)"}, "Callback Refusals"),
              c.refusal_previews.map((rp) => el("div", {style: "font-size:.77rem;color:var(--rose)"}, rp))) : null,
            (c.gates || []).length ? el("div", {class: "chips"}, c.gates.map((g) =>
              el("button", {type: "button", class: "chip " + (g.passed === true ? "good" : (g.passed === false ? "danger" : "")),
                style: "cursor:pointer", title: g.detail || g.path,
                onclick: () => openDrawer({eyebrow: "GATE RECORD", title: g.label + " · " + g.disposition, scope: "run", relative: g.path})},
                g.label + ": " + g.disposition + (g.reused ? " (reused)" : "")))) : null,
            el("div", {class: "links"},
              c.result_path ? el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({eyebrow: "ACCEPTED RESULT", title: c.result_path, scope: "run", relative: c.result_path})}, "View result file") : null,
              c.improve && c.improve.receipt_path ? el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({eyebrow: "IMPROVE RECEIPT", title: c.improve.receipt_path, scope: "run", relative: c.improve.receipt_path})}, "View Improve receipt") : null),
            (c.events || []).length ? el("div", {class: "ev-list"}, c.events.map((ev) =>
              el("div", {class: "ev-row" + (ev.refused ? " refused" : "")},
                el("span", {class: "mono muted"}, fmtClock(ev.at)),
                el("strong", {style: "text-transform:uppercase;font-size:.7rem"}, ev.refused ? "refused" : ev.kind),
                el("div", {style: "min-width:0;overflow-wrap:anywhere"},
                  ev.summary,
                  ev.ms !== null && ev.ms !== undefined ? el("span", {class: "muted"}, " · " + fmtSpan(ev.ms / 1000)) : null,
                  ev.usage && ev.usage.total_tokens ? el("span", {class: "muted", title: tokenTip(ev.usage)}, " · " + fmtTokens(ev.usage.total_tokens)) : null,
                  ev.file ? el("button", {type: "button", class: "btn-copy", style: "margin-left:8px;padding:2px 8px;font-size:.7rem",
                    onclick: () => openDrawer({eyebrow: "SENT PACKET", title: c.stage + " packet", scope: "run", relative: ev.file})}, "View packet") : null)))) : null));
        details.addEventListener("toggle", () => {
          if (details.open) state.openCards.add(c.action);
          else state.openCards.delete(c.action);
          summaryEl.textContent = summaryLabel(details.open);
        });

        return el("article", {class: cardCls, id: "story-" + c.action},
          el("div", {class: "story-top"},
            el("div", {class: "chips"},
              el("span", {class: "chip mono"}, "#" + c.seq),
              el("strong", {}, (c.item ? c.item + " · " : "") + c.stage + (c.reviewing_stage ? " (" + c.reviewing_stage + ")" : "")),
              el("span", {class: "pill pill-" + (c.outcome === "done" ? "done" : (c.outcome === "blocked" ? "blocked" : (c.outcome === "send-back" ? "paused" : "active")))}, c.outcome),
              c.duration_seconds !== null && c.duration_seconds !== undefined
                ? el("span", {class: "chip", title: (c.duration_basis || "dwell") + ": " + (c.started_at || "?") + " → " + (c.ended_at || "?")
                    + (c.paused_seconds && c.active_seconds !== null && c.active_seconds !== undefined
                        ? ` (active ${fmtSpan(c.active_seconds)}, paused ${fmtSpan(c.paused_seconds)})` : "")},
                    iconSvg("clock", 12), fmtSpan(c.duration_seconds)) : null,
              c.token_usage && c.token_usage.total_tokens
                ? el("span", {class: "chip", title: tokenTip(c.token_usage)}, fmtTokens(c.token_usage.total_tokens)) : null,
              c.commit_sha ? el("button", {type: "button", class: "chip mono", style: "cursor:pointer", title: "Copy commit SHA " + c.commit_sha,
                onclick: () => copyText(c.commit_sha, "Commit SHA copied")}, iconSvg("commit", 12), c.commit_sha.slice(0, 8)) : null,
              c.improve ? el("span", {class: "chip violet"}, "Improve" + (c.improve.passes ? " · " + c.improve.passes + "p" : "")) : null,
              c.model_label ? el("span", {class: "chip"}, c.model_label) : null,
              c.counts && c.counts.refusals ? el("span", {class: "chip danger"}, "!" + c.counts.refusals + " refused") : null),
            el("span", {class: "muted mono", style: "font-size:.72rem"}, fmtClock(c.ended_at || c.started_at))),
          el("div", {class: "story-headline"}, c.headline || c.stage),
          tn.text ? el("div", {class: "trans-callout " + (tn.kind || "")}, iconSvg("arrow", 14), el("span", {}, tn.text)) : null,
          ((c.gates || []).length || c.loop || c.lint) ? el("div", {class: "chips"},
            (c.gates || []).map((g) => el("span", {class: "chip " + (g.passed === true ? "good" : (g.passed === false ? "danger" : ""))},
              g.label + ": " + g.disposition + (g.reused ? " · reused" : ""))),
            c.loop ? el("span", {class: "chip"}, "Loop: " + c.loop.iterations + " pass(es) · " + (c.loop.status || "")) : null,
            c.lint ? el("span", {class: "chip"}, "Lint: " + (c.lint.summary || c.lint.kind)) : null) : null,
          details);
      });
      return timelineNodes.length ? el("div", {class: "story-timeline"}, timelineNodes) : el("div", {class: "empty"}, "No story visits match this filter.");
    };

    const initialCards = filterStoryCards();
    const storyCountEl = el("h3", {id: "story-count", style: "margin:0;font-size:1.02rem"}, "Accomplishments & Transitions (" + initialCards.length + ")");
    const storyListWrap = el("div", {id: "story-list-wrap"}, buildStoryTimeline(initialCards));
    const feedToolbar = el("div", {class: "feed-toolbar"},
      el("div", {}, el("div", {class: "eyebrow"}, "CHRONOLOGICAL STORY"), storyCountEl),
      el("div", {class: "chips"},
        [["all", "All"], ["milestones", "Milestones"], ["issues", "Send-backs & Refusals"], ["improve", "Improve"], ["gates", "Gates"]].map(([fid, flbl]) =>
          el("button", {type: "button", class: "filter-pill" + (state.storyFilter === fid ? " active" : ""),
            onclick: () => { state.storyFilter = fid; renderDetailOnly(); }}, flbl)),
        el("button", {type: "button", class: "filter-pill",
          onclick: () => { state.storySort = state.storySort === "newest" ? "oldest" : "newest"; renderDetailOnly(); }},
          state.storySort === "newest" ? "Newest first ↓" : "Oldest first ↑"),
        el("input", {type: "search", class: "search-box", style: "width:190px;padding:4px 10px", placeholder: "Filter story…", value: state.storyQuery,
          oninput: (e) => {
            state.storyQuery = e.target.value;
            const filteredCards = filterStoryCards();
            storyCountEl.textContent = "Accomplishments & Transitions (" + filteredCards.length + ")";
            storyListWrap.replaceChildren(buildStoryTimeline(filteredCards));
          }})));

    return [
      focusCard,
      pipePanel,
      el("section", {class: "card"}, feedToolbar, storyListWrap),
    ];
  };

  // ---- Tab 2: Prompt & Plan ----
  const renderDagSvg = (graph, idx) => {
    const nodes = graph.nodes || [];
    if (!nodes.length) return el("div", {class: "muted"}, "No steps in graph.");
    const edges = graph.edges || [];
    const known = !!graph.dependencies_known;
    const byId = new Map(nodes.map((n, i) => [n.id, i]));
    const ranks = new Array(nodes.length).fill(0);
    let hasCycle = false;
    if (known) {
      for (let pass = 0; pass < nodes.length; pass++) {
        let changed = false;
        for (const e of edges) {
          const s = byId.get(e.from), t = byId.get(e.to);
          if (s !== undefined && t !== undefined && ranks[t] <= ranks[s]) {
            ranks[t] = Math.min(nodes.length, ranks[s] + 1);
            changed = true;
          }
        }
        if (!changed) break;
        if (pass === nodes.length - 1) hasCycle = true;
      }
    }
    const cols = known ? ranks : nodes.map((_, i) => i % 3);
    const rowsByCol = new Map();
    const rowPos = new Array(nodes.length).fill(0);
    nodes.forEach((_, i) => {
      const c = cols[i];
      const r = rowsByCol.get(c) || 0;
      rowPos[i] = r;
      rowsByCol.set(c, r + 1);
    });
    const w = 220, h = 104, gx = 68, gy = 26, mx = 20, my = 20;
    const maxC = Math.max(0, ...cols), maxR = Math.max(0, ...rowPos);
    const svgW = Math.max(540, mx * 2 + (maxC + 1) * w + maxC * gx);
    const svgH = my * 2 + (maxR + 1) * h + maxR * gy;
    const pos = nodes.map((_, i) => [mx + cols[i] * (w + gx), my + rowPos[i] * (h + gy)]);
    const svg = svgEl("svg", {width: svgW, height: svgH, viewBox: `0 0 ${svgW} ${svgH}`});
    const markerId = "arr-" + idx;
    svg.append(svgEl("defs", {}, svgEl("marker", {id: markerId, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto"},
      svgEl("path", {d: "M0,0 L8,4 L0,8 z", fill: "var(--muted)"}))));
    if (known) {
      for (const e of edges) {
        const si = byId.get(e.from), ti = byId.get(e.to);
        if (si === undefined || ti === undefined) continue;
        const [sx, sy] = pos[si], [tx, ty] = pos[ti];
        const x1 = sx + w, y1 = sy + h / 2, x2 = tx, y2 = ty + h / 2, mid = (x1 + x2) / 2;
        svg.append(svgEl("path", {d: `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`,
          fill: "none", stroke: "var(--muted)", "stroke-width": 2, "marker-end": `url(#${markerId})`}));
      }
    }
    nodes.forEach((n, i) => {
      const [x, y] = pos[i];
      const st = String(n.status || "queued");
      const fill = st === "done" ? "var(--emerald-soft)" : (st === "active" ? "var(--primary-soft)" : "var(--surface)");
      const stroke = st === "done" ? "var(--emerald)" : (st === "active" ? "var(--primary)" : "var(--line-strong)");
      const g = svgEl("g", {});
      g.append(svgEl("rect", {x, y, width: w, height: h, rx: 14, fill, stroke, "stroke-width": 1.6}));
      const idLbl = svgEl("text", {x: x + 12, y: y + 22, fill: "var(--primary)", "font-size": 11, "font-weight": 700});
      idLbl.textContent = (n.id || "S?") + (n.commit_sha ? " · " + String(n.commit_sha).slice(0, 7) : "");
      const titleLbl = svgEl("text", {x: x + 12, y: y + 45, fill: "var(--ink)", "font-size": 12.5, "font-weight": 600});
      const ttl = String(n.title || "Step");
      titleLbl.textContent = ttl.length > 28 ? ttl.slice(0, 27) + "…" : ttl;
      const stLbl = svgEl("text", {x: x + 12, y: y + 86, fill: "var(--muted)", "font-size": 10.5});
      stLbl.textContent = st + (n.proof_passed === true ? " · proof ✓" : (n.proof_passed === false ? " · proof ✗" : ""));
      g.append(idLbl, titleLbl, stLbl);
      svg.append(g);
    });
    return el("div", {class: "graph-viewport"},
      hasCycle ? el("div", {class: "chip warn", style: "margin-bottom:8px"}, "Cycle detected in step edges — bounded layout") : null,
      svg);
  };

  const renderPlanTab = (d) => {
    const req = d.request;
    const plan = d.planning || {};
    const runKey = (d.run && d.run.run_key) || state.selectedKey;
    const out = [];
    if (req && req.original) {
      const sentences = req.original.sentences || [];
      const ex = req.expanded || {};
      const reqsKey = "plan-reqs:" + runKey;
      const reqsDet = (ex.requirements || []).length ? el("details", {class: "prompt-details", open: state.openDetails.has(reqsKey) || null},
        el("summary", {}, "Living Specification Requirements (" + ex.requirements.length + ")"),
        el("div", {style: "display:grid;gap:8px;margin-top:10px"}, ex.requirements.map((rq) =>
          el("div", {class: "mini-panel"}, el("strong", {}, rq.id + " · " + rq.title + " (" + rq.section + ")"),
            el("div", {class: "muted", style: "font-size:.79rem;white-space:pre-wrap"}, rq.body || ""))))) : null;
      if (reqsDet) {
        reqsDet.addEventListener("toggle", () => {
          if (reqsDet.open) state.openDetails.add(reqsKey);
          else state.openDetails.delete(reqsKey);
        });
      }
      out.push(el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "REQUEST DECOMPOSITION"),
        el("h3", {style: "margin:0"}, "Verbatim Request & Intake Mapping (" + sentences.length + " sentences)"),
        el("div", {class: "table-wrap"}, el("table", {class: "m3"},
          el("thead", {}, el("tr", {}, el("th", {}, "#"), el("th", {}, "Original Sentence"), el("th", {}, "Intake Reading"))),
          el("tbody", {}, sentences.map((s) => el("tr", {},
            el("td", {class: "mono"}, "S" + s.n),
            el("td", {}, s.text),
            el("td", {}, (s.readings || []).length
              ? s.readings.map((rd) => el("div", {}, el("span", {class: "pill"}, rd.kind), " ", rd.text))
              : el("span", {class: "muted"}, "No clause cites it yet"))))))),
        reqsDet));
    }

    if ((plan.experiment_questions || []).length || (plan.experiments || []).length || (plan.probed_rows || []).length || (plan.snapshots || []).length) {
      out.push(el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "PLANNING LOOP & EXPERIMENTS"),
        el("h3", {style: "margin:0"}, "Assumptions, Probes & Draft Snapshots"),
        (plan.experiment_questions || []).length ? el("div", {class: "chips"}, plan.experiment_questions.map((q) =>
          el("span", {class: "chip " + (q.status === "probed" || q.status === "evidenced" ? "good" : (q.status === "probing" ? "warn" : ""))},
            q.id + ": " + q.status + " — " + q.question))) : null,
        (plan.experiments || []).length ? el("div", {class: "overview-grid"}, plan.experiments.map((exp) =>
          el("div", {class: "mini-panel"},
            el("div", {style: "display:flex;justify-content:space-between;gap:8px"},
              el("strong", {}, exp.id), el("span", {class: "pill pill-primary"}, exp.status)),
            el("div", {class: "muted", style: "font-size:.75rem"}, `${exp.origin} · ${exp.file_count} file(s)` + (exp.question ? ` · ${exp.question}` : "")),
            exp.summary ? el("div", {style: "font-size:.79rem"}, exp.summary) : null,
            exp.relative && String(exp.relative).endsWith(".md")
              ? el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({eyebrow: "EXPERIMENT", title: exp.id, scope: "run", relative: exp.relative})}, "Open decision") : null))) : null));
    }

    const items = d.work_items || [];
    out.push(el("section", {class: "card"},
      el("div", {class: "eyebrow"}, "WORK QUEUE"),
      el("h3", {style: "margin:0"}, "Work Items (" + items.length + ")"),
      items.length ? el("div", {class: "overview-grid"}, items.map((it) => el("div", {class: "mini-panel"},
        el("div", {style: "display:flex;justify-content:space-between;gap:8px"},
          el("strong", {}, it.id + " · " + it.title),
          el("div", {class: "chips"},
            it.slice ? el("span", {class: "chip pill-cyan"}, it.slice) : null,
            it.concerns_mode === "deferred" ? el("span", {class: "chip violet"}, "rolling-wave") : null,
            el("span", {class: "pill pill-" + (it.status === "done" ? "done" : (it.status === "current" ? "active" : "paused"))}, it.status))),
        it.plan ? el("div", {class: "muted", style: "font-size:.8rem"}, it.plan) : null)))
        : el("div", {class: "empty"}, "Plan pending — work items not accepted yet.")));

    const graphs = d.graphs || [];
    if (graphs.length) {
      out.push(el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "GENERATED IMPLEMENTATION"),
        el("h3", {style: "margin:0"}, "Step Dependency Graphs"),
        graphs.map((g, i) => el("div", {style: "display:grid;gap:8px"},
          el("strong", {}, g.label || "Graph"),
          renderDagSvg(g, i)))));
    }
    return out;
  };

  // ---- Tab 3: Gates & Evidence ----
  const renderGatesTab = (d) => {
    const out = [];
    const te = d.testing_evidence || {};
    if (te.has_evidence) {
      out.push(el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "TESTING EVIDENCE & FIX-FORWARD"),
        el("h3", {style: "margin:0"}, "Findings, Replans, Sub-cases & Mutants"),
        el("div", {class: "chips"},
          el("span", {class: "chip"}, "Findings: " + (te.findings || []).length + " (" + (te.findings_settled || 0) + " settled)"),
          el("span", {class: "chip"}, "Replans: " + (te.replans || []).length),
          el("span", {class: "chip"}, "Auto sub-cases: " + (te.auto_subcases_count || 0)),
          el("span", {class: "chip"}, "Added tests: " + (te.added_tests_count || 0)),
          el("span", {class: "chip"}, "Test Proof re-checks: " + (te.test_proof_rechecks || 0))),
        (te.findings || []).length ? el("div", {class: "table-wrap"}, el("table", {class: "m3"},
          el("thead", {}, el("tr", {}, el("th", {}, "ID"), el("th", {}, "Impact"), el("th", {}, "Status"), el("th", {}, "Finding"))),
          el("tbody", {}, te.findings.map((f) => el("tr", {},
            el("td", {class: "mono"}, f.id),
            el("td", {}, el("span", {class: "pill"}, f.impact)),
            el("td", {}, el("span", {class: "pill " + (f.settled ? "pill-done" : "pill-paused")}, f.settled ? "settled" : "open")),
            el("td", {}, f.finding)))))) : null));
    }

    const gateRows = [];
    for (const c of (d.story_cards || [])) {
      for (const g of (c.gates || [])) gateRows.push({card: c, gate: g});
    }
    out.push(el("section", {class: "card"},
      el("div", {class: "eyebrow"}, "VERIFICATION MATRIX"),
      el("h3", {style: "margin:0"}, "Recorded Gate, Check & Test Runs (" + gateRows.length + ")"),
      gateRows.length ? el("div", {class: "table-wrap"}, el("table", {class: "m3"},
        el("thead", {}, el("tr", {}, el("th", {}, "Stage"), el("th", {}, "Gate"), el("th", {}, "Result"), el("th", {}, "Detail"), el("th", {}, ""))),
        el("tbody", {}, gateRows.map(({card, gate}) => el("tr", {},
          el("td", {}, (card.item ? card.item + " · " : "") + card.stage),
          el("td", {}, gate.label),
          el("td", {}, el("span", {class: "pill " + (gate.passed === true ? "pill-done" : (gate.passed === false ? "pill-blocked" : ""))},
            gate.disposition + (gate.reused ? " (reused)" : ""))),
          el("td", {}, gate.detail || ""),
          el("td", {}, el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({
            eyebrow: "GATE RECORD", title: gate.label + " · " + card.stage, scope: "run", relative: gate.path,
          })}, "Inspect"))))))) : el("div", {class: "empty"}, "No test, check, or expectation records yet.")));

    const docs = d.documents || [];
    out.push(el("section", {class: "card"},
      el("div", {class: "eyebrow"}, "DOCUMENTS & SPECS"),
      el("h3", {style: "margin:0"}, "Key Run & Repository Files (" + docs.length + ")"),
      el("div", {class: "overview-grid"}, docs.map((doc) => el("div", {class: "mini-panel"},
        el("div", {style: "display:flex;justify-content:space-between;gap:8px"},
          el("strong", {}, doc.title || doc.id), el("span", {class: "pill"}, doc.status)),
        doc.summary ? el("div", {class: "muted", style: "font-size:.77rem"}, doc.summary) : null,
        doc.relative ? el("button", {type: "button", class: "btn-copy", onclick: () => openDrawer({
          eyebrow: doc.scope === "repo" ? "REPOSITORY DOC" : "RUN ARTIFACT", title: doc.title, scope: doc.scope, relative: doc.relative,
        })}, "Open preview") : el("span", {class: "muted", style: "font-size:.73rem"}, doc.path || ""))))));

    const gov = d.governance || {};
    if ((gov.defaults && gov.defaults.length) || (gov.unverified && gov.unverified.length) || (gov.reconciliations && gov.reconciliations.length) || gov.workspace_return) {
      out.push(el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "GOVERNANCE & DELIVERY"),
        el("h3", {style: "margin:0"}, "Defaults, Unverified & Workspace Return"),
        gov.workspace_return ? el("div", {class: "mini-panel"}, el("h4", {}, "Workspace Return"),
          el("div", {}, "Status: ", el("strong", {}, gov.workspace_return.status), gov.workspace_return.kind ? " (" + gov.workspace_return.kind + ")" : "")) : null,
        (gov.defaults || []).length ? el("div", {class: "mini-panel"}, el("h4", {}, "Spec Defaults (" + gov.defaults.length + ")"),
          gov.defaults.map((df) => el("div", {style: "font-size:.79rem"}, el("strong", {}, df.requirement + ": "), df.default + " — ", el("span", {class: "muted"}, df.why)))) : null,
        (gov.unverified || []).length ? el("div", {class: "mini-panel"}, el("h4", {}, "Unverified Outcomes (" + gov.unverified.length + ")"),
          gov.unverified.map((uv) => el("div", {style: "font-size:.79rem"}, el("strong", {}, uv.requirement + ": "), uv.outcome + " (due " + uv.due_stage + ")"))) : null));
    }
    return out;
  };

  // ---- Tab 4: Trace & Packets ----
  const renderTraceTab = (d) => {
    const tr = d.trace_summary || {};
    const cnt = tr.counts || {};
    const filterEvents = () => (tr.events || []).filter((ev) => {
      if (state.traceRefusalsOnly && !ev.refused) return false;
      if (!state.traceKinds.has(ev.kind)) return false;
      if (state.traceQuery.trim()) {
        const q = state.traceQuery.trim().toLowerCase();
        if (![ev.kind, ev.action, ev.stage, ev.verb, ev.summary, ev.hook].join(" ").toLowerCase().includes(q)) return false;
      }
      return true;
    }).slice().reverse();

    const buildTraceList = () => {
      const events = filterEvents();
      return events.length ? el("div", {class: "ev-list"}, events.slice(0, 200).map((ev) =>
        el("div", {class: "ev-row" + (ev.refused ? " refused" : "")},
          el("span", {class: "mono muted"}, fmtClock(ev.at)),
          el("strong", {style: "text-transform:uppercase;font-size:.7rem"}, ev.refused ? "refused" : ev.kind),
          el("div", {style: "min-width:0;overflow-wrap:anywhere"},
            ev.stage ? el("span", {class: "chip", style: "margin-right:6px"}, (ev.item ? ev.item + " " : "") + ev.stage) : null,
            ev.summary,
            ev.ms !== null && ev.ms !== undefined ? el("span", {class: "muted"}, " · " + fmtSpan(ev.ms / 1000)) : null,
            ev.usage && ev.usage.total_tokens ? el("span", {class: "muted", title: tokenTip(ev.usage)}, " · " + fmtTokens(ev.usage.total_tokens)) : null,
            ev.file ? el("button", {type: "button", class: "btn-copy", style: "margin-left:8px;padding:2px 8px;font-size:.7rem",
              onclick: () => openDrawer({eyebrow: "PACKET", title: (ev.stage || "") + " packet", scope: "run", relative: ev.file})}, "View packet") : null))))
        : el("div", {class: "empty"}, "No trace events match.");
    };

    const traceListWrap = el("div", {id: "trace-list-wrap"}, buildTraceList());
    const kinds = ["command", "packet", "hook", "skill", "accepted"];
    return [
      el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "TELEMETRY COUNTS"),
        el("div", {class: "chips"},
          el("span", {class: "chip"}, "Accepted: " + (cnt.accepted || 0)),
          el("span", {class: "chip"}, "Commands: " + (cnt.commands || 0)),
          el("span", {class: "chip"}, "Packets: " + (cnt.packets || 0)),
          el("span", {class: "chip " + (cnt.refusals ? "danger" : "")}, "Refusals: " + (cnt.refusals || 0)),
          el("span", {class: "chip"}, "Hook continuations: " + (cnt.continuations || 0)),
          el("span", {class: "chip"}, "Skill calls: " + (cnt.skills || 0)),
          tr.token_usage && tr.token_usage.total_tokens
            ? el("span", {class: "chip", title: tokenTip(tr.token_usage)}, "Recorded tokens: " + fmtTokens(tr.token_usage.total_tokens)) : null)),
      el("section", {class: "card"},
        el("div", {class: "feed-toolbar"},
          el("div", {class: "chips"}, kinds.map((k) =>
            el("button", {type: "button", class: "filter-pill" + (state.traceKinds.has(k) ? " active" : ""),
              onclick: () => { if (state.traceKinds.has(k)) state.traceKinds.delete(k); else state.traceKinds.add(k); renderDetailOnly(); }}, k)),
            el("button", {type: "button", class: "filter-pill" + (state.traceRefusalsOnly ? " active" : ""),
              onclick: () => { state.traceRefusalsOnly = !state.traceRefusalsOnly; renderDetailOnly(); }}, "Refusals only")),
          el("input", {type: "search", class: "search-box", style: "width:220px;padding:5px 10px", placeholder: "Search trace events…",
            value: state.traceQuery, oninput: (e) => {
              state.traceQuery = e.target.value;
              traceListWrap.replaceChildren(buildTraceList());
            }})),
        traceListWrap),
      el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "COVERAGE & SOURCES"),
        el("div", {class: "chips"}, (tr.sources || []).map((s) =>
          el("span", {class: "chip " + (s.status === "ok" ? "good" : (s.status === "missing" ? "" : "warn"))}, s.id + ": " + s.status))),
        (tr.warnings || []).length ? el("ul", {style: "margin:6px 0 0;padding-left:20px;font-size:.8rem;color:var(--amber)"},
          tr.warnings.map((w) => el("li", {}, w))) : null),
    ];
  };

  // ---- Tab 5: Owner Notes ----
  const renderNotesTab = (d) => {
    const notes = d.notes || [];
    const r = d.run || {};
    const runKey = r.run_key || state.selectedKey || "default";
    const cmdPrefix = ((d.live_now || {}).cli_commands || {}).note_prefix || ("python3 shiploop note --run-dir=" + shQuote(r.run_dir) + " --text ");
    const draft = state.noteDrafts.get(runKey) || "";
    const box = el("textarea", {placeholder: "Write an instruction for the next active stage…"});
    box.value = draft;
    const trimmedInit = draft.trim();
    const cmdPre = el("pre", {class: "prompt-pre mono", style: "min-height:1.8em"}, trimmedInit ? (cmdPrefix + shQuote(trimmedInit)) : "");
    const copyBtn = el("button", {type: "button", class: "m3-btn primary", disabled: !trimmedInit, onclick: () => copyText(cmdPre.textContent, "Note command copied")}, "Copy note command");
    box.addEventListener("input", () => {
      state.noteDrafts.set(runKey, box.value);
      const txt = box.value.trim();
      cmdPre.textContent = txt ? (cmdPrefix + shQuote(txt)) : "";
      copyBtn.disabled = !txt;
    });

    return [
      el("section", {class: "card note-composer"},
        el("div", {class: "eyebrow"}, "READ-ONLY VIEWER COMPOSER"),
        el("h3", {style: "margin:0"}, "Leave an Owner Note"),
        el("div", {class: "muted", style: "font-size:.8rem"}, "This viewer is strictly read-only. Compose your note below and run the generated command in your terminal:"),
        box, cmdPre, el("div", {class: "links"}, copyBtn)),
      el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "LEDGER"),
        el("h3", {style: "margin:0"}, "Recorded Owner Notes (" + notes.length + ")"),
        notes.length ? notes.map((n) => el("div", {class: "mini-panel"},
          el("div", {style: "display:flex;justify-content:space-between;gap:8px"},
            el("strong", {}, n.id), el("span", {class: "pill " + (n.state === "settled" ? "pill-done" : "pill-paused")}, n.state)),
          n.text ? el("pre", {class: "prompt-pre"}, n.text) : null,
          (n.rows || []).map((row) => el("div", {class: "muted", style: "font-size:.78rem"},
            `#${row.step} ${row.where}: ${row.did} — ${row.detail}`)))) : el("div", {class: "empty"}, "No owner notes recorded for this run.")),
    ];
  };

  // ---- Tab 6: Terminal Report ----
  const renderReportTab = (d) => {
    const r = d.run || {};
    const gov = d.governance || {};
    const runKey = r.run_key || state.selectedKey;
    const title = r.status === "done" ? "Run Completed" : (r.status === "halted" ? "Run Halted" : "Report Pending");
    return [
      el("section", {class: "card"},
        el("div", {class: "eyebrow"}, "TERMINAL SUMMARY"),
        el("h3", {style: "margin:0"}, title),
        el("div", {class: "muted", style: "font-size:.82rem"},
          "Agent-declared completion; this view summarizes recorded state without independently proving external effects."),
        r.has_report ? el("div", {class: "links"},
          el("a", {class: "m3-btn primary", href: "/runs/" + encodeURIComponent(runKey) + "/report.html"}, "Open Full report.html →")) : null,
        gov.follow_on_request ? el("div", {class: "mini-panel"},
          el("h4", {}, "Recommended Follow-On Request"),
          el("pre", {class: "prompt-pre"}, gov.follow_on_request)) : null,
        gov.leftovers && gov.leftovers.items && gov.leftovers.items.length ? el("div", {class: "mini-panel"},
          el("h4", {}, "Leftover Worktrees & Branches"),
          gov.leftovers.items.map((it) => el("div", {style: "font-size:.79rem"},
            el("strong", {}, `${it.kind} (${it.branch}): `), it.note,
            it.commands && it.commands.length ? el("pre", {class: "pass-log-pre"}, it.commands.join("\n")) : null))) : null),
    ];
  };

  const renderDetailOnly = () => {
    const canvas = document.getElementById("main-canvas");
    if (state.overview) return renderOverview();
    const d = state.detail;
    if (!d) {
      canvas.replaceChildren(el("div", {class: "empty"}, state.selectedKey ? "Loading selected session…" : "Select a ShipLoop session from the left rail."));
      return;
    }
    const y = window.scrollY;
    let body = [];
    if (state.activeTab === "story") body = renderStoryTab(d);
    else if (state.activeTab === "plan") body = renderPlanTab(d);
    else if (state.activeTab === "gates") body = renderGatesTab(d);
    else if (state.activeTab === "trace") body = renderTraceTab(d);
    else if (state.activeTab === "notes") body = renderNotesTab(d);
    else if (state.activeTab === "report") body = renderReportTab(d);
    canvas.replaceChildren(...renderHero(d).filter(Boolean), renderTabs(d), ...body.filter(Boolean));
    if (Math.abs(window.scrollY - y) >= 2) window.scrollTo({top: y, behavior: "instant"});
  };

  const jumpToAction = (actionId) => {
    state.activeTab = "story";
    state.storyFilter = "all";
    state.openCards.add(actionId);
    state.highlightAction = actionId;
    syncUrl();
    renderDetailOnly();
    const node = document.getElementById("story-" + actionId);
    if (node) node.scrollIntoView({behavior: "smooth", block: "center"});
  };

  const selectRun = (runKey) => {
    state.overview = false;
    state.selectedKey = runKey;
    state.runVersion = "";
    state.detail = null;
    document.getElementById("mode-overview").classList.remove("active");
    syncUrl();
    renderTopAndRail();
    renderDetailOnly();
    triggerImmediateFetch();
  };

  // ---- Single Unified Poller (Hard floor: >= MIN_POLL_MS = 2000) ----
  const updatePollPill = (msg, mode = "ok") => {
    const lbl = document.getElementById("poll-status");
    const dot = document.getElementById("poll-dot");
    if (lbl) lbl.textContent = msg;
    if (dot) {
      dot.className = "pulse-dot" + (mode === "paused" ? " paused" : (mode === "warn" ? " warn" : " anim"));
    }
  };

  const applyPendingIfReady = () => {
    if (!state.pendingRender || isUserBusy()) return;
    state.pendingRender = false;
    renderTopAndRail();
    renderDetailOnly();
  };

  const scheduleNext = () => {
    clearTimeout(state.timer);
    state.timer = null;
    if (state.paused) {
      updatePollPill("Paused", "paused");
      return;
    }
    const elapsed = Math.max(0, Date.now() - state.lastPollStart);
    const minWait = Math.max(0, MIN_POLL_MS - elapsed);
    const baseMs = document.hidden ? Math.max(HIDDEN_POLL_MS, state.pollMs) : Math.max(MIN_POLL_MS, state.pollMs);
    const waitMs = state.wantSoon ? minWait : Math.max(minWait, baseMs - elapsed);
    state.timer = setTimeout(() => { doPoll(); }, waitMs);
  };

  const doPoll = async () => {
    if (state.inFlight) return;
    const sinceLast = Date.now() - state.lastPollStart;
    if (state.lastPollStart > 0 && sinceLast < MIN_POLL_MS) {
      scheduleNext();
      return;
    }
    state.inFlight = true;
    state.wantSoon = false;
    state.lastPollStart = Date.now();
    const wantRun = (!state.overview && state.selectedKey) ? state.selectedKey : "";
    const wantAuto = (!state.overview && !state.selectedKey);
    const qs = new URLSearchParams({
      run: wantRun,
      auto: wantAuto ? "1" : "",
      runs_v: state.runsVersion,
      run_v: wantRun ? state.runVersion : "",
    });
    try {
      const resp = await fetch("/api/poll?" + qs.toString(), {cache: "no-store"});
      if (!resp.ok) {
        updatePollPill("Hub error " + resp.status, "warn");
        return;
      }
      const data = await resp.json();
      let changed = false;
      if (data.runs_payload) {
        state.runsPayload = data.runs_payload;
        state.runsVersion = data.runs_version || "";
        const runs = state.runsPayload.runs || [];
        if (!state.overview && (!state.selectedKey || !runs.some((r) => r.run_key === state.selectedKey))) {
          if (runs.length) state.selectedKey = (wantAuto && data.selected_run) ? data.selected_run : runs[0].run_key;
          else state.overview = true;
          syncUrl();
        }
        changed = true;
      } else if (wantAuto && data.selected_run && !state.overview && !state.selectedKey) {
        state.selectedKey = data.selected_run;
        syncUrl();
      }
      const targetMatch = (wantRun && wantRun === state.selectedKey) || (wantAuto && data.selected_run && data.selected_run === state.selectedKey);
      if (targetMatch && data.detail) {
        state.detail = data.detail;
        state.runVersion = data.run_version || "";
        changed = true;
      } else if (targetMatch && data.detail_error) {
        state.detail = null;
        state.runVersion = "";
        changed = true;
      } else if (!state.overview && state.selectedKey && (!state.detail || (state.detail.run && state.detail.run.run_key !== state.selectedKey))) {
        state.wantSoon = true;
      }
      if (changed) {
        if (isUserBusy()) {
          state.pendingRender = true;
        } else {
          renderTopAndRail();
          renderDetailOnly();
        }
      }
      const sec = Math.round((document.hidden ? Math.max(HIDDEN_POLL_MS, state.pollMs) : state.pollMs) / 1000);
      updatePollPill((data.unchanged ? "Live · " : "Synced · ") + sec + "s", "ok");
    } catch (_) {
      updatePollPill("Disconnected · retrying", "warn");
    } finally {
      state.inFlight = false;
      scheduleNext();
    }
  };

  const triggerImmediateFetch = () => {
    state.wantSoon = true;
    const wait = Math.max(0, MIN_POLL_MS - (Date.now() - state.lastPollStart));
    if (state.inFlight) {
      updatePollPill("Queued…", "ok");
      return;
    }
    clearTimeout(state.timer);
    if (wait === 0) {
      doPoll();
    } else {
      updatePollPill("Queued (" + Math.ceil(wait / 1000) + "s)", "ok");
      state.timer = setTimeout(() => { doPoll(); }, wait);
    }
  };

  // ---- Wire Controls & Keyboard Shortcuts ----
  document.getElementById("brand-spark").append(iconSvg("spark", 20));
  document.getElementById("toggle-rail").append(iconSvg("sidebar", 16));
  applyTheme(readTheme());

  document.getElementById("theme-toggle").addEventListener("click", () => {
    applyTheme(rootEl.getAttribute("data-theme") === "dark" ? "light" : "dark");
  });
  document.getElementById("toggle-rail").addEventListener("click", () => {
    document.getElementById("workspace").classList.toggle("rail-collapsed");
  });
  document.getElementById("mode-overview").addEventListener("click", () => {
    state.overview = !state.overview;
    document.getElementById("mode-overview").classList.toggle("active", state.overview);
    if (!state.overview) {
      const runs = (state.runsPayload && state.runsPayload.runs) || [];
      if (!state.selectedKey && runs.length) state.selectedKey = runs[0].run_key;
      if (state.selectedKey && (!state.detail || (state.detail.run && state.detail.run.run_key !== state.selectedKey))) {
        triggerImmediateFetch();
      }
    }
    syncUrl();
    renderTopAndRail();
    renderDetailOnly();
  });
  if (state.overview) document.getElementById("mode-overview").classList.add("active");

  const cadSel = document.getElementById("cadence-select");
  cadSel.value = String(state.pollMs);
  cadSel.addEventListener("change", () => {
    state.pollMs = Math.max(MIN_POLL_MS, Number(cadSel.value) || MIN_POLL_MS);
    try { localStorage.setItem("shiploop-hub-poll", String(state.pollMs)); } catch (_) {}
    scheduleNext();
  });

  document.getElementById("toggle-live").addEventListener("click", (e) => {
    state.paused = !state.paused;
    e.target.textContent = state.paused ? "Resume" : "Pause";
    if (!state.paused) triggerImmediateFetch();
    else scheduleNext();
  });
  document.getElementById("refresh-now").addEventListener("click", () => {
    triggerImmediateFetch();
  });

  document.getElementById("q").addEventListener("input", (e) => {
    state.query = e.target.value;
    renderTopAndRail();
    if (state.overview) renderDetailOnly();
  });
  document.querySelectorAll("#rail-filters .filter-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.filter = btn.dataset.filter;
      document.querySelectorAll("#rail-filters .filter-pill").forEach((b) => b.classList.toggle("active", b === btn));
      renderTopAndRail();
      if (state.overview) renderDetailOnly();
    });
  });

  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.getElementById("drawer-backdrop").addEventListener("click", closeDrawer);
  document.getElementById("drawer-copy").addEventListener("click", () => {
    copyText(document.getElementById("drawer-text").textContent || "", "Artifact copied");
  });

  document.addEventListener("selectionchange", () => { if (!isUserBusy()) applyPendingIfReady(); });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !state.paused) triggerImmediateFetch();
    else scheduleNext();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") return closeDrawer();
    const act = document.activeElement;
    if (act && (act.tagName === "INPUT" || act.tagName === "TEXTAREA" || act.tagName === "SELECT")) return;
    if (e.key === "/") { e.preventDefault(); document.getElementById("q").focus(); }
    else if (e.key === "o") { document.getElementById("mode-overview").click(); }
    else if (e.key === "j" || e.key === "k") {
      const runs = (state.runsPayload && state.runsPayload.runs) || [];
      if (!runs.length) return;
      const idx = runs.findIndex((r) => r.run_key === state.selectedKey);
      const next = e.key === "j" ? (idx + 1) % runs.length : (idx - 1 + runs.length) % runs.length;
      selectRun(runs[next].run_key);
    } else if (/^[1-6]$/.test(e.key) && !state.overview) {
      const tabOrder = ["story", "plan", "gates", "trace", "notes", "report"];
      const t = tabOrder[Number(e.key) - 1];
      const dr = state.detail && state.detail.run;
      const canReport = !!(dr && (dr.has_report || dr.status === "done" || dr.status === "halted"));
      if (t && (t !== "report" || canReport)) { state.activeTab = t; syncUrl(); renderDetailOnly(); }
    }
  });

  // Lightweight 1-second local clock tick (NO network request) for live dwell timer & relative ages.
  setInterval(() => {
    if (state.pendingRender && !isUserBusy()) applyPendingIfReady();
    document.querySelectorAll("[data-live-clock]").forEach((node) => {
      const d = parseDate(node.getAttribute("data-live-clock"));
      if (d) node.textContent = fmtSpan(Math.max(0, (Date.now() - d.getTime()) / 1000));
    });
    document.querySelectorAll("[data-live-age]").forEach((node) => {
      const stamp = node.getAttribute("data-live-age");
      if (stamp) node.textContent = ageText(stamp);
    });
  }, 1000);

  // Initial load
  doPoll();
})();
</script>
</body>
</html>
"""
