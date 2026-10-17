#!/usr/bin/env python3
"""The sequence of one E2E run, for the flow viewer: each packet ShipLoop sent, what the model saw, and what it did.

    python3 test/shiploop_e2e/flow.py <output>                       # writes <output>/flow.json and <output>/flow.html
    python3 test/shiploop_e2e/flow.py --bundle viewer.html <output>...  # one page that browses several runs

`flow.json` (schema `FLOW_VERSION`) is built from the run's files only:
- state.md history, which gives the actions in the order the graph took them;
- the packet archive (slice.py) or run/packets (a full run keeps only each packet's last copy);
- the host's event stream.

The packet archive and run/packets supply the text of each packet.

Each action has one phase. The Improve stage is an action of its own (stage `improve`, its own id and packet file), listed
after the action it reviews and linked to it (`reviewed`, `reviewed_stage`); its phase has kind `improve`. A saved run of
the older layout has the Improve child's packet beside the producer's (`<action>-improve.md`): its action keeps two
phases, the producer and the Improve child. A phase holds:
- the packet: its text, size and largest sections;
- the head the model received, as printed in a tool result;
- how the model opened the packet file, if it did;
- the model's own events.

On Claude, the events are its text, tool calls and tool results, and hook messages. An event belongs to the action
named by the last packet head the model had received, which is exact, because each `complete` call prints the next
head. Other hosts' streams give tool calls only (metrics.ToolLog), attributed by ShipLoop's acceptance times.

Calls are flagged by script, never by a model:
- a script the model wrote to drive ShipLoop or Improve (`defines-script`) and every run of it (`runs-script`);
- a self-reported trivial Until Loop pass (`trivial-pass`);
- a scripted review: a review file a model-written script writes, so its text is fixed before anything is checked
  (`scripted-review`).

`flow_viewer.html` is the template: `--bundle` inlines any number of flow.json files into one self-contained page, and
the page also opens flow.json files by drag and drop.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
import packets  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402

FLOW_VERSION = 2  # 2: the Improve stage is an action row of its own (`reviewed`, `reviewed_stage`); version 1 files still open.
# `clear` is a list, one entry per clear of the run (several clears per slice); a flow written before that holds an object or null there,
# which the viewer shows as no clear.
TEMPLATE = HERE / "flow_viewer.html"
DATA_MARK = "<!--FLOW-RUNS-->"
HEAD = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<rev>\d+)")
ACTION = re.compile(r"--action=(nav-[0-9a-f]{32})")
ANY_ACTION = re.compile(r"(nav-[0-9a-f]{32})")
PACKET_FILE = re.compile(r"packets/(nav-[0-9a-f]{32}(?:-improve(?:-bind)?|-bind)?)\.md")
# An Improve packet's head, old layout: the producer's stage with `| Improve` or an improve-* verb in its first lines. New layout:
# stage `improve` (a worktree path that merely contains "improve-" is not a sign).
OLD_IMPROVE_HEAD = re.compile(r"\| Improve\b|Current action: Improve|improve-(?:bind|start|complete)\b")
SCRIPT_DEF = re.compile(r"cat\s+>\s*(\S+\.sh)\s+<<|(\w+)\(\)\s*\{")
TRIVIAL = re.compile(r'\\?"classification\\?"\s*:\s*\\?"trivial')
REVIEW_FILE = re.compile(r"cat\s+>\s*\S*reviews/review-\d+\.md\s+<<")
STATUS_END = "=== end ShipLoop status ==="
HEAD_END = "=== end ShipLoop head ==="  # the closing line of a printed head from 2026-10-16; older heads end at the status block
CALL_LIMIT, RESULT_LIMIT, TEXT_LIMIT = 6000, 6000, 4000


class Shortener:
    """Long absolute paths shortened to labels the page can show (the labels are listed in flow.json)."""

    def __init__(self, out: Path, run_dir: Path):
        worktree = run_dir.parent / "worktree"
        self.pairs = [(str(run_dir), "<run>"), (str(worktree), "<worktree>"),
                      (str(out / "build/plugins/skill-craft/skills"), "<skills>"), (str(out), "<out>")]

    def __call__(self, text: str) -> str:
        for path, label in self.pairs:
            text = text.replace(path, label)
        return text

    def legend(self) -> dict:
        return {label: path for path, label in self.pairs}


def clip(text: str, limit: int, short: Shortener) -> dict:
    return {"text": short(text[:limit]), "chars": len(text), "clipped": len(text) > limit}


def call_flags(body: str, scripts: dict[str, bool]) -> list[str]:
    """`scripts` maps each script the model defined so far to whether its body writes a review file."""
    flags = []
    defined = [Path(a or b).name for a, b in SCRIPT_DEF.findall(body)]
    for name in defined:
        scripts[name] = bool(REVIEW_FILE.search(body))
        flags.append(f"defines-script:{name}")
    ran = [name for name in sorted(scripts) if name not in defined
           and re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", body)]
    flags += [f"runs-script:{name}" for name in ran]
    # A review the script writes is the same text whatever it reviews: written before anything is checked.
    if any(scripts.get(name) for name in [*defined, *ran]):
        flags.append("scripted-review")
    if TRIVIAL.search(body):
        flags.append("trivial-pass")
    return flags


def packet_texts(out: Path, run_dir: Path) -> tuple[dict[str, str], dict[str, int], str]:
    texts, archived = packets.emissions(out, run_dir)
    source = "archive" if archived else "retained"
    return {k: v[-1] for k, v in texts.items()}, {k: len(v) for k, v in texts.items()}, source


def claude_items(out: Path, short: Shortener, first_action: str | None) -> tuple[list[dict], dict, dict, float | None]:
    """Claude's stream: text, calls, results and hook messages, each attributed to the action of the last head seen."""
    stamps = {}
    for row in (out / "timeline.jsonl").read_text().splitlines() if (out / "timeline.jsonl").is_file() else []:
        try:
            r = json.loads(row)
            stamps[r["line"]] = r["t"]
        except (ValueError, KeyError):
            continue
    t0 = min(stamps.values()) if stamps else 0.0
    current = {"action": first_action, "improve": False}
    items, heads, reads, scripts = [], {}, {}, {}
    for number, raw in enumerate((out / "events.jsonl").read_text().splitlines()):
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        t = round(stamps.get(number, t0) - t0, 1)
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "informational":
            items.append({"kind": "hook", "t": t, "line": number, **current, "body": clip(event.get("content", ""), 1500, short)})
            continue
        if kind not in ("assistant", "user") or not isinstance((event.get("message") or {}).get("content"), list):
            continue
        for block in event["message"]["content"]:
            if block.get("type") == "text" and block.get("text", "").strip():
                items.append({"kind": "say", "t": t, "line": number, **current, "body": clip(block["text"], TEXT_LIMIT, short)})
            elif block.get("type") == "tool_use":
                call = block.get("input") or {}
                body = call.get("command") or call.get("file_path") or json.dumps(call)
                for key in sorted(set(PACKET_FILE.findall(body))):
                    whole = block.get("name") == "Read" and "offset" not in call and "limit" not in call
                    reads.setdefault(key, []).append("read tool, whole file" if whole else (
                        "read tool, part" if block.get("name") == "Read" else
                        "shell, " + next((w for w in ("grep", "sed", "head", "tail", "cat") if w in body), "other")))
                items.append({"kind": "call", "t": t, "line": number, **current, "tool": block.get("name"),
                              "body": clip(body, CALL_LIMIT, short), "flags": call_flags(body, scripts),
                              "reads_packets": sorted(set(PACKET_FILE.findall(body)))})
            elif block.get("type") == "tool_result":
                content = block.get("content")
                content = content if isinstance(content, str) else "\n".join(
                    part.get("text", "") for part in content or [] if isinstance(part, dict))
                items.append({"kind": "result", "t": t, "line": number, **current, "body": clip(content, RESULT_LIMIT, short)})
                for match in HEAD.finditer(content):
                    tail = content[match.start():]
                    found = ACTION.search(tail[:3000]) or ANY_ACTION.search(tail[:3000])
                    if not found:
                        continue
                    # New layout: an `improve` head names the Improve stage's own id, so it is an ordinary action key.
                    improve = match.group("stage") != navigator.IMPROVE_STAGE and bool(OLD_IMPROVE_HEAD.search(tail[:400]))
                    key = found.group(1) + ("-improve" if improve else "")
                    end = content.find(STATUS_END, match.start())
                    closing = content.find(HEAD_END, match.start())
                    stop = closing + len(HEAD_END) if closing > 0 else end + len(STATUS_END) if end > 0 else len(content)
                    heads.setdefault(key, short(content[match.start(): stop]))
                    current = {"action": found.group(1), "improve": improve}
    return items, heads, reads, (t0 if stamps else None)


def toollog_items(out: Path, run_dir: Path, short: Shortener, order: list[str], accepted_t: dict) -> list[dict]:
    """Other hosts: calls only, each attributed to the first action accepted at or after it."""
    log = metrics.ToolLog()
    metrics.collect(out, run_dir, tools=log)
    timed = [(accepted_t.get(a), a) for a in order if accepted_t.get(a) is not None]
    items, scripts = [], {}
    starts = [row["t"] for row in log.sequence if row.get("t") is not None]
    t0 = min(starts) if starts else 0.0
    for row in log.sequence:
        t = row.get("t")
        owner = next((a for at, a in timed if t is not None and at >= t), order[-1] if order else None)
        body = str(row.get("command") or "")
        items.append({"kind": "call", "t": round((t or t0) - t0, 1), "action": owner, "improve": False,
                      "tool": row.get("tool"), "body": clip(body, CALL_LIMIT, short), "flags": call_flags(body, scripts),
                      "reads_packets": sorted(set(PACKET_FILE.findall(body)))})
    return items


def build(out: Path) -> dict:
    out = out.resolve()
    run_dir = packets.find_run_dir(out)
    if run_dir is None:
        raise SystemExit(f"no ShipLoop state.md under {out}")
    short = Shortener(out, run_dir)
    state = store.read_record(run_dir / "state.md")
    accepted = state.get("accepted") or {}
    history = [h for h in state.get("history") or [] if isinstance(h, dict) and h.get("action")]

    def seeded(action: str) -> bool:
        action = reviewed_by.get(action, action)
        record = accepted.get(action) or {}
        result = record.get("result", record) if isinstance(record, dict) else {}
        return str((result or {}).get("summary", "")).startswith("Synthetic")

    links = packets.improve_links(state)  # {Improve stage id: reviewed action}
    reviewed_by = dict(links)
    improve_of = {reviewed: stage_id for stage_id, reviewed in links.items()}
    order = []
    for h in history:
        order.append(h["action"])
        if h["action"] in improve_of:
            order.append(improve_of[h["action"]])  # the Improve stage ran after its reviewed action and before its accept
    by_action = {h["action"]: h for h in history}
    stamps = {row["action"]: row["t"] for row in metrics.stage_results(run_dir, state) if row.get("action")}
    texts, emissions, source = packet_texts(out, run_dir)
    claude = (out / "events.jsonl").is_file() and '"tool_use"' in (out / "events.jsonl").read_text()[:2_000_000]
    try:
        pending = str(navigator.current_action(state)["id"]) if state.get("status") == "active" else None
        pending_stage = navigator.current_stage(state) if pending else None
    except Exception:  # noqa: BLE001 - a record, never a refusal
        pending, pending_stage = None, None
    child = state.get("active_improve") if isinstance(state.get("active_improve"), dict) else None
    if pending is not None and child and isinstance(child.get("improve_action"), str):
        # The run stands at an Improve stage: the cursor still names the reviewed action; the stage is the Improve one.
        order.extend(a for a in (pending, child["improve_action"]) if a not in order)
        pending, pending_stage = child["improve_action"], packets.IMPROVE_STAGE
    # Events before the first head belong to the first live action: accepted already, or the one the run is at.
    first_live = next((a for a in order if not seeded(a)), pending)
    if claude:
        items, heads, reads, started = claude_items(out, short, first_live)
    else:
        items, heads, reads = toollog_items(out, run_dir, short, order, stamps), {}, {}
        started = metrics.span(out / "timeline.jsonl").get("started") if (out / "timeline.jsonl").is_file() else None
    # The action the run stopped in is named by a head (or an event), not yet in history.
    # A head the model cut short (it piped `complete` through tail) names nothing, so the ledger's current action is added too.
    for action in [*(i["action"] for i in items), *(k.removesuffix("-improve") for k in heads), pending]:
        if action and action not in order:
            order.append(action)
    actions = []
    for index, action in enumerate(order):
        reviewed = reviewed_by.get(action)  # set only for an Improve stage's own id
        h = by_action.get(reviewed or action, {})
        stage = packets.IMPROVE_STAGE if reviewed else h.get("stage")
        if stage is None:
            found = HEAD.search(texts.get(action, "") or texts.get(action + "-improve", ""))
            # The ledger's current action has no history row and may have no packet yet: a slice stop that lands between
            # the host saving the state and its `next` writing the packet.  The ledger still names its stage.
            stage = found.group("stage") if found else pending_stage if action == pending and pending_stage else "?"
        if reviewed:
            # The Improve stage: one phase, its packet (the bind packet when no card was ever bound), linked to the reviewed action.
            candidates = [(action, "improve", False)]
        else:
            candidates = [(action, "producer", False), (action + "-improve", "improve", True)]
        phases = []
        for key, kind, legacy in candidates:
            mine = [i for i in items if i["action"] == action and i["improve"] == legacy]
            text_key = key if key in texts else f"{key}-bind" if f"{key}-bind" in texts else key
            if text_key not in texts and not mine:
                continue
            text = texts.get(text_key, "")
            times = [i["t"] for i in mine]
            phases.append({
                "kind": kind, "key": key,
                "packet": {"text": short(text), "chars": len(text), "emissions": emissions.get(text_key, 0),
                           "sections": packets.sections(text, top=12), **packets.references(text)},
                "head": heads.get(key) or heads.get(f"{key}-bind"), "head_chars": len(heads.get(key) or heads.get(f"{key}-bind") or ""),
                "reads": [*reads.get(key, []), *reads.get(f"{key}-bind", [])],
                "events": mine, "calls": sum(1 for i in mine if i["kind"] == "call"),
                "span_seconds": round(max(times) - min(times), 1) if times else None,
                "flags": sorted({f for i in mine if i["kind"] == "call" for f in i["flags"]}),
            })
        row = {"index": index, "action": action, "stage": stage, "outcome": h.get("outcome"),
               "work_item": h.get("workitem"), "seeded": seeded(action), "accepted": (reviewed or action) in by_action,
               "phases": phases}
        if reviewed:  # the Improve stage's accept is the reviewed action's: its `complete` imports the review
            row.update({"reviewed": reviewed, "reviewed_stage": h.get("stage")})
        actions.append(row)

    def json_file(name: str) -> dict:
        try:
            return json.loads((out / name).read_text())
        except (OSError, ValueError):
            return {}

    invocation, result = json_file("invocation.json"), json_file("slice-result.json") or json_file("result.json")
    report = json_file(packets.REPORT_JSON) or packets.build(out)
    prompt = (out / "prompt.txt").read_text().strip() if (out / "prompt.txt").is_file() else state.get("prompt", "")
    sessions = result.get("sessions") or (result.get("process") or {}).get("sessions") or []
    return {
        "flow_version": FLOW_VERSION, "output": str(out), "kind": invocation.get("kind") or "run",
        "case": invocation.get("case") or result.get("case"), "host": invocation.get("host"),
        "model": invocation.get("model"), "effort": invocation.get("effort"), "delegation": state.get("delegation"),
        "versions": invocation.get("versions") or {},
        "started": datetime.fromtimestamp(started, timezone.utc).isoformat(timespec="seconds") if started else None,
        "seconds": sum(s.get("elapsed_seconds") or 0 for s in sessions) or None,
        "pass": result.get("pass"), "verdicts": result.get("verdicts") or {},
        "run_status": state.get("status"), "prompt": prompt, "events_source": "claude" if claude else "toollog",
        "packets_source": source, "paths": short.legend(), "totals": report.get("totals") or {},
        "stages": report.get("stages") or [], "actions": actions,
        "case_details": {
            "expect_paths": invocation.get("expect_paths") or [],
            "checks": [{"command": c.get("command"), "pass": c.get("pass"), "output": short(str(c.get("output") or ""))[-1500:]}
                       for c in (result.get("checks") or []) if isinstance(c, dict)],
            "assembled": {k: (result.get("assembled") or {}).get(k) for k in ("changed", "missing", "uncommitted_product")}
                         if result.get("assembled") else None,
            "item_history": result.get("item_history") or [],
            "overshoot": result.get("overshoot"), "queue_growth": result.get("queue_growth"),
        },
        # One entry per clear, in the order they fired (slice.py writes a list; a slice-result from before it holds one
        # object, which this does not read: the viewer shows no clear for it rather than a wrong one).
        "clear": [{**{k: c.get(k) for k in ("n", "stage", "inside")}, "stopped": c.get("stopped"),
                   "redone": c.get("redone"), "pass": c.get("pass")}
                  for c in (result.get("clear") if isinstance(result.get("clear"), list) else []) if isinstance(c, dict)],
        "unattributed": [i for i in items if not i["action"]],
    }


STANDALONE_HEAD = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')


def bundle(target: Path, flows: list[dict], standalone: bool = True) -> Path:
    """The viewer with `flows` inlined. A standalone page (opened from disk) gets its own doctype and charset; an
    Artifact publish adds its own skeleton, so `standalone=False` leaves them out."""
    page = TEMPLATE.read_text()
    if DATA_MARK not in page:
        raise SystemExit(f"{TEMPLATE} has no {DATA_MARK} marker")
    data = json.dumps(flows).replace("</", "<\\/")  # nothing in the data can close the script element
    page = page.replace(DATA_MARK, f'<script id="flow-runs" type="application/json">{data}</script>')
    target.write_text((STANDALONE_HEAD if standalone else "") + page)
    return target


def write(out: Path) -> dict:
    """flow.json and a one-run flow.html in the output directory."""
    flow = build(out)
    (out / "flow.json").write_text(json.dumps(flow) + "\n")
    bundle(out / "flow.html", [flow])
    return flow


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("outputs", type=Path, nargs="+", help="E2E output directories (or flow.json files with --bundle)")
    p.add_argument("--bundle", type=Path, metavar="HTML", help="write one viewer page holding every given run")
    p.add_argument("--artifact", action="store_true", help="with --bundle: leave out the doctype for an Artifact publish")
    args = p.parse_args(argv)
    flows = []
    for given in args.outputs:
        given = given.expanduser().resolve()
        if given.is_file():
            flows.append(json.loads(given.read_text()))
        else:
            flows.append(write(given) if not args.bundle else (
                json.loads((given / "flow.json").read_text()) if (given / "flow.json").is_file() else write(given)))
            if not args.bundle:
                print(given / "flow.html")
    if args.bundle:
        print(bundle(args.bundle.expanduser().resolve(), flows, standalone=not args.artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
