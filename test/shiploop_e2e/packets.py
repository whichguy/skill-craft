#!/usr/bin/env python3
"""What ShipLoop sent and what it cost: every packet and every stage of one run, from its files only.

    python3 test/shiploop_e2e/packets.py <output directory>
    python3 test/shiploop_e2e/packets.py <output directory> --compare <earlier output directory>
    python3 test/shiploop_e2e/packets.py --offline node-fix-bug     # no model: the case's inner-loop packets as rendered

--offline drives the checkout's navigator through a step case with synthetic results (the seed's pattern, no project
work) and reports the packets of the item's inner loop as a cleared model would read them: the zero-cost check of a
prompt edit's effect on packet size and shape before a live slice.

Writes packet-report.json and packet-report.md into the output directory (with --compare, packet-compare.md too) and
prints the Markdown. It reads any E2E output directory: a step slice (slice.py), whose poll archived every distinct
packet the run emitted under packet-archive/, or a full run, which keeps only the last copy of each packet
(run/packets/<action>.md is rewritten on every `next`), so its rows say "retained only".

Nothing here is the model's account. Per packet: its stage and kind (producer or Improve), size, an estimated token
count (characters / 4, not a tokenizer), its largest sections, the skill references it names and whether each exists,
how many distinct emissions were observed, and how many `next` calls the host made for that action (from the event
stream). Per stage: metrics.py's seconds, turns, tool calls and context peak. Across packets: the share of each
packet's text already sent in an earlier packet. That is reported, not flagged, because restating how a stage
operates is the main tenet (context may be cleared between stages); the figure shows what it costs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

ARCHIVE = "packet-archive"
REPORT_JSON, REPORT_MD, COMPARE_MD = "packet-report.json", "packet-report.md", "packet-compare.md"
ESTIMATE = "characters / 4 (an estimate, not a tokenizer count)"
# Absolute paths a packet names; only those under a skills/<leaf>/ directory are references that must exist (a path in
# the run directory is often a file the stage is about to write).
PATH = re.compile(r"(/[\w.@+~-]+(?:/[\w.@+~-]+)+\.(?:md|py|json|html|txt|sh))")
SKILL_PATH = re.compile(r"/skills/[\w-]+/")
# A packet's section starts at a line that is a `=== ... ===` marker, a Markdown heading, or a short label ending in ':'.
SECTION = re.compile(r"(?m)^(=== .{1,80} ===|#{1,4} .{1,80}|[A-Z][\w ,()'/-]{2,60}:)$")
NEXT_CALL = re.compile(r"""(?:scripts/shiploop["']?\s+next\b|\bshiploop-next\b|\bshiploop\s+next\b)""")
OVERLAP_MIN_LINE = 20  # shorter lines (a bare heading, a brace) say nothing about repetition


def find_run_dir(out: Path) -> Path | None:
    """The ShipLoop run directory under an output directory (the throwaway home and plugin build are not searched)."""
    for state_path in sorted(out.rglob("state.md")):
        parts = state_path.relative_to(out).parts
        if parts[0] in ("home", "build", "export", ARCHIVE):
            continue
        try:
            state = store.read_record(state_path)
        except store.StorageError:
            continue
        if isinstance(state, dict) and "status" in state:
            return state_path.parent
    return None


def archive_packets(run_dir: Path, out: Path) -> int:
    """Copy each packet whose content changed since its last archived copy; return how many were new.

    ShipLoop rewrites run/packets/<action>.md on every `next`, so a poll calling this keeps every distinct emission it
    saw: packet-archive/<action>/<seq>-<sha8>.md. A packet rewritten and changed back between two polls is not seen.
    """
    source = run_dir / "packets"
    if not source.is_dir():
        return 0
    added = 0
    for packet in sorted(source.glob("*.md")):
        try:
            data = packet.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()[:8]
        folder = out / ARCHIVE / packet.stem
        kept = sorted(folder.glob("*.md")) if folder.is_dir() else []
        if kept and kept[-1].stem.endswith(digest):
            continue
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{len(kept) + 1:03d}-{digest}.md").write_bytes(data)
        added += 1
    return added


def emissions(out: Path, run_dir: Path) -> tuple[dict[str, list[str]], bool]:
    """{packet key: the texts emitted, oldest first} and whether they come from the archive (else retained only)."""
    archive = out / ARCHIVE
    if archive.is_dir() and any(archive.iterdir()):
        return ({folder.name: [p.read_text(errors="replace") for p in sorted(folder.glob("*.md"))]
                 for folder in sorted(archive.iterdir()) if folder.is_dir()}, True)
    retained = run_dir / "packets"
    return ({p.stem: [p.read_text(errors="replace")] for p in sorted(retained.glob("*.md"))} if retained.is_dir() else {},
            False)


def sections(text: str, top: int = 5) -> list[dict]:
    """The largest sections of a packet, by characters (a heuristic split at labels and markers)."""
    marks = [(m.start(), m.group(0).strip()[:70]) for m in SECTION.finditer(text)]
    if not marks or marks[0][0] > 0:
        marks.insert(0, (0, "(opening)"))
    marks.append((len(text), None))
    found = [{"section": name, "chars": end - start} for (start, name), (end, _) in zip(marks, marks[1:])]
    return sorted(found, key=lambda row: -row["chars"])[:top]


def references(text: str) -> dict:
    named = sorted(set(PATH.findall(text)))
    skill = [path for path in named if SKILL_PATH.search(path)]
    return {"paths_named": len(named), "skill_references": len(skill),
            "missing": [path for path in skill if not Path(path).exists()]}


def next_calls(tool_log: metrics.ToolLog) -> list[float]:
    """Times of the host's `next` calls to the ShipLoop CLI (the recovery command: it reprints the current packet)."""
    return sorted(call["t"] for call in tool_log.calls.values()
                  if call.get("t") is not None and NEXT_CALL.search(str(call.get("command") or "")))


def attribute(times: list[float], accepted: list[dict], pending: str | None) -> dict[str, int]:
    """{action id: `next` calls made while it was current}: a call belongs to the first action accepted after it."""
    counts: dict[str, int] = {}
    timed = [row for row in accepted if row.get("action") and row.get("t") is not None]
    for t in times:
        owner = next((row["action"] for row in timed if row["t"] >= t), pending)
        if owner:
            counts[owner] = counts.get(owner, 0) + 1
    return counts


def overlap_shares(texts: list[str]) -> list[float | None]:
    """For each text in order: the share of its characters on lines already sent in an earlier text."""
    seen: set[str] = set()
    shares: list[float | None] = []
    for text in texts:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        lines = [line for line in lines if len(line) >= OVERLAP_MIN_LINE]
        total = sum(map(len, lines))
        shares.append(round(sum(len(line) for line in lines if line in seen) / total, 3) if total else None)
        seen.update(lines)
    return shares


def effectiveness(state: dict, out: Path) -> dict:
    """Script facts on whether the stages did their job (the slice verdicts when slice.py wrote them)."""
    history = [row for row in state.get("history") or [] if isinstance(row, dict)]
    order = [row.get("stage") for row in history]
    red = order.index("test-red") if "test-red" in order else None
    green = order.index("test-green") if "test-green" in order else None
    found = {"stage_outcomes": [{"stage": row.get("stage"), "outcome": row.get("outcome"), "work_item": row.get("workitem")}
                                for row in history],
             "revise_loops": sum(1 for row in history if row.get("outcome") == "revise"),
             "test_red_before_green": None if red is None or green is None else red < green}
    try:
        found["slice"] = json.loads((out / "slice-result.json").read_text())
    except (OSError, ValueError):
        found["slice"] = None
    return found


def build(out: Path) -> dict:
    out = out.resolve()
    run_dir = find_run_dir(out)
    if run_dir is None:
        raise SystemExit(f"no ShipLoop state.md under {out}")
    state = store.read_record(run_dir / "state.md")
    tool_log = metrics.ToolLog()
    run_metrics = metrics.collect(out, run_dir, tools=tool_log)
    accepted = metrics.stage_results(run_dir, state)
    try:
        pending_action = str(navigator.current_action(state)["id"]) if state.get("status") == "active" else None
    except Exception:  # noqa: BLE001 - a record, never a refusal
        pending_action = None
    by_action = {row["action"]: row for row in accepted if row.get("action")}
    texts, archived = emissions(out, run_dir)
    calls = attribute(next_calls(tool_log), accepted, pending_action)
    order = {row["action"]: i for i, row in enumerate(accepted) if row.get("action")}

    def key_order(key: str) -> tuple:
        action = key.removesuffix("-improve")
        return (order.get(action, len(order)), key.endswith("-improve"))

    keys = sorted(texts, key=key_order)
    shares = overlap_shares([texts[key][-1] for key in keys])
    rows = []
    for key, share in zip(keys, shares):
        action = key.removesuffix("-improve")
        sent = texts[key]
        last = sent[-1]
        known = by_action.get(action) or {}
        stage = known.get("stage")
        if stage is None:
            found = metrics.PACKET_STAGE.search(last)
            stage = found.group("stage") if found else None
        rows.append({"packet": key, "action": action, "kind": "improve" if key.endswith("-improve") else "producer",
                     "stage": stage, "work_item": known.get("work_item"), "outcome": known.get("outcome"),
                     "emissions": len(sent), "chars": len(last), "est_tokens": len(last) // 4,
                     "chars_all_emissions": sum(map(len, sent)), "repeated_share": share,
                     "next_calls": None if key.endswith("-improve") else calls.get(action, 0),
                     "sections": sections(last), **references(last)})
    usage = run_metrics.get("tool_use") or {}
    report = {
        "output": str(out), "run_dir": str(run_dir), "status": state.get("status"),
        "emissions_source": "packet-archive (every distinct emission a 2-s poll saw)" if archived
                            else "retained only (run/packets keeps the last copy of each packet)",
        "token_estimate": ESTIMATE,
        "totals": {"packets": len(rows), "emissions": sum(r["emissions"] for r in rows),
                   "chars_sent": sum(r["chars_all_emissions"] for r in rows),
                   "est_tokens_sent": sum(r["chars_all_emissions"] for r in rows) // 4,
                   "next_calls": sum(calls.values()), "shiploop_failures": len(run_metrics.get("shiploop_failures") or []),
                   "model_glue": len(run_metrics.get("model_glue") or []), "turns": run_metrics.get("turns"),
                   "cost_usd": run_metrics.get("cost_usd"),
                   "packet_reads": usage.get("packets") if isinstance(usage, dict) else None},
        "packets": rows,
        "stages": run_metrics.get("stages") or [],
        "effectiveness": effectiveness(state, out),
    }
    return report


def offline_packets(case: dict, delegation: str = "inline") -> dict[str, str]:
    """{"<nn>-<stage>[-improve]": packet text} for one step case's inner loop, rendered from a cold read of state.md.

    Synthetic results throughout (no model, no project work): the plan's only item is the case's work item and the
    step plan records the case's first check as its test command.
    """
    found: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="shiploop-step-packets-") as temp:
        run_dir = Path(temp) / "run"
        run_dir.mkdir()

        def cold(current: dict) -> str:
            store.write_record(run_dir / "state.md", current)
            return navigator.render(None, run_dir, store.read_record(run_dir / "state.md"))

        state = navigator.new_state(temp, case["prompt"], delegation=delegation)
        for _ in range(200):
            stage = navigator.current_stage(state)
            if state["status"] != "active" or stage in stage_spec.OUTER:
                break
            action = navigator.current_action(state)
            inner = stage in stage_spec.INNER
            if inner:
                found[f"{len(found) + 1:02d}-{stage}"] = cold(state)
            extra: dict = {}
            if stage == "plan":
                extra["work_items"] = [case["work_item"]]
            if stage == "step-plan":
                extra["test_commands"] = [{"command": case["checks"][0], "suite": "focused"}]
            waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": "Synthetic", **extra})
            if waiting.get("active_improve") is not None:
                if inner:
                    found[f"{len(found) + 1:02d}-{stage}-improve"] = cold(waiting)
                waiting = navigator.finish_improve(waiting, action["id"], {"summary": "Synthetic review", "lessons": "x"})
            state = waiting
    return found


def offline_report(name: str, case: dict, delegation: str = "inline") -> dict:
    texts = offline_packets(case, delegation)
    keys = list(texts)
    rows = [{"packet": key, "stage": key.split("-", 1)[1].removesuffix("-improve"),
             "kind": "improve" if key.endswith("-improve") else "producer", "chars": len(texts[key]),
             "est_tokens": len(texts[key]) // 4, "repeated_share": share, "sections": sections(texts[key]),
             **references(texts[key])}
            for key, share in zip(keys, overlap_shares([texts[key] for key in keys]))]
    return {"case": name, "delegation": delegation, "offline": True, "token_estimate": ESTIMATE,
            "totals": {"packets": len(rows), "chars": sum(r["chars"] for r in rows),
                       "est_tokens": sum(r["chars"] for r in rows) // 4},
            "packets": rows}


def render_offline(report: dict) -> str:
    t = report["totals"]
    lines = [f"# Offline packets: {report['case']} ({report['delegation']})", "",
             f"No model: synthetic results on this checkout's navigator. Tokens: {report['token_estimate']}.", "",
             f"- packets {t['packets']}, characters {t['chars']} (~{t['est_tokens']} tokens)", "",
             "| packet | chars | ~tokens | repeated | skill refs | missing | largest sections |", "|---|---|---|---|---|---|---|"]
    for row in report["packets"]:
        big = "; ".join(f"{s['section']} ({s['chars']})" for s in row["sections"][:3])
        lines.append(f"| {row['packet']} | {row['chars']} | {row['est_tokens']} | {_cell(row['repeated_share'])} "
                     f"| {row['skill_references']} | {len(row['missing'])} | {big} |")
    return "\n".join(lines) + "\n"


def _cell(value) -> str:
    return "–" if value is None else f"{value:.0%}" if isinstance(value, float) and value <= 1 else str(value)


def render(report: dict) -> str:
    t = report["totals"]
    lines = [f"# Packet report: {report['output']}", "",
             f"Run status **{report['status']}**. Emissions: {report['emissions_source']}. Tokens: {report['token_estimate']}.",
             "", f"- packets {t['packets']}, emissions {t['emissions']}, characters sent {t['chars_sent']} "
                 f"(~{t['est_tokens_sent']} tokens)",
             f"- `next` calls {t['next_calls']}, ShipLoop failures {t['shiploop_failures']}, model glue {t['model_glue']}, "
             f"turns {_cell(t['turns'])}, cost {_cell(t['cost_usd'])}", ""]
    slice_result = report["effectiveness"].get("slice")
    if slice_result:
        verdicts = ", ".join(f"{name} {'PASS' if ok else 'FAIL'}" for name, ok in slice_result.get("verdicts", {}).items())
        lines += [f"**Slice {'PASS' if slice_result.get('pass') else 'FAIL'}**: {verdicts}", ""]
    eff = report["effectiveness"]
    lines += [f"Revise loops {eff['revise_loops']}; test-red before test-green: {_cell(eff['test_red_before_green'])}.", "",
              "## Packets", "",
              "| # | stage | kind | outcome | chars | ~tokens | emissions | next | repeated | skill refs | missing | largest section |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, row in enumerate(report["packets"], 1):
        big = row["sections"][0] if row["sections"] else {"section": "–", "chars": 0}
        lines.append(f"| {i} | {row['stage']} | {row['kind']} | {_cell(row['outcome'])} | {row['chars']} | {row['est_tokens']} "
                     f"| {row['emissions']} | {_cell(row['next_calls'])} | {_cell(row['repeated_share'])} "
                     f"| {row['skill_references']} | {len(row['missing'])} | {big['section']} ({big['chars']}) |")
    lines += ["", "## Stages (metrics.py)", "", "| stage | outcome | seconds | turns | tool calls | context peak |",
              "|---|---|---|---|---|---|"]
    for row in report["stages"]:
        peak = (row.get("context") or {}).get("peak")
        lines.append(f"| {row.get('stage')}{' (incomplete)' if row.get('incomplete') else ''} | {_cell(row.get('outcome'))} "
                     f"| {_cell(row.get('seconds'))} | {_cell(row.get('turns'))} | {_cell(row.get('tool_calls'))} | {_cell(peak)} |")
    missing = sorted({path for row in report["packets"] for path in row["missing"]})
    if missing:
        lines += ["", "## Missing skill references", "", *(f"- {path}" for path in missing)]
    return "\n".join(lines) + "\n"


def compare(now: dict, before: dict) -> str:
    """Per-stage and per-packet change from `before` to `now` (the same case before and after an edit, say)."""
    def by_stage(rows, field):
        found: dict[str, float] = {}
        for row in rows:
            if isinstance(row.get(field), (int, float)) and row.get("stage"):
                found[row["stage"]] = found.get(row["stage"], 0) + row[field]
        return found

    lines = [f"# Packet comparison", "", f"- now: {now['output']}", f"- before: {before['output']}", ""]
    for name in ("chars_sent", "next_calls", "shiploop_failures", "model_glue", "turns", "cost_usd"):
        a, b = now["totals"].get(name), before["totals"].get(name)
        delta = round(a - b, 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else "–"
        lines.append(f"- {name}: {_cell(b)} → {_cell(a)} (Δ {delta})")
    seconds_now, seconds_before = by_stage(now["stages"], "seconds"), by_stage(before["stages"], "seconds")
    turns_now, turns_before = by_stage(now["stages"], "turns"), by_stage(before["stages"], "turns")
    chars_now, chars_before = by_stage(now["packets"], "chars"), by_stage(before["packets"], "chars")
    stages = list(dict.fromkeys([*(r.get("stage") for r in before["stages"]), *(r.get("stage") for r in now["stages"])]))
    lines += ["", "| stage | Δ seconds | Δ turns | Δ packet chars |", "|---|---|---|---|"]
    for stage in stages:
        if not stage:
            continue
        cells = [round(new.get(stage, 0) - old.get(stage, 0), 1) if stage in new or stage in old else "–"
                 for new, old in ((seconds_now, seconds_before), (turns_now, turns_before), (chars_now, chars_before))]
        lines.append(f"| {stage} | " + " | ".join(map(str, cells)) + " |")
    v_now = ((now["effectiveness"].get("slice") or {}).get("verdicts") or {})
    v_before = ((before["effectiveness"].get("slice") or {}).get("verdicts") or {})
    changed = [f"- {name}: {v_before.get(name)} → {v_now.get(name)}" for name in sorted({*v_now, *v_before})
               if v_now.get(name) != v_before.get(name)]
    lines += ["", "## Verdict changes", "", *(changed or ["- none"])]
    return "\n".join(lines) + "\n"


def write_report(out: Path) -> dict:
    report = build(out)
    (out / REPORT_JSON).write_text(json.dumps(report, indent=2) + "\n")
    (out / REPORT_MD).write_text(render(report))
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", type=Path, nargs="?", help="an E2E output directory (slice.py or run.py)")
    p.add_argument("--compare", type=Path, help="an earlier output directory to compare this one with")
    p.add_argument("--offline", metavar="CASE", help="render a step case's inner-loop packets with no model")
    p.add_argument("--delegation", choices=("inline", "ask-agent"), default="inline", help="with --offline")
    p.add_argument("--json", action="store_true", help="with --offline: print JSON instead of Markdown")
    args = p.parse_args(argv)
    if args.offline:
        cases = json.loads((HERE / "step_cases.json").read_text())
        if args.offline not in cases or args.offline.startswith("_"):
            raise SystemExit(f"unknown step case {args.offline!r}")
        report = offline_report(args.offline, cases[args.offline], args.delegation)
        print(json.dumps(report, indent=2) if args.json else render_offline(report), end="\n" if args.json else "")
        return 0
    if args.output is None:
        p.error("an output directory, or --offline CASE")
    out = args.output.expanduser().resolve()
    report = write_report(out)
    print(render(report), end="")
    if args.compare:
        earlier = args.compare.expanduser().resolve()
        before = (json.loads((earlier / REPORT_JSON).read_text()) if (earlier / REPORT_JSON).is_file()
                  else write_report(earlier))
        text = compare(report, before)
        (out / COMPARE_MD).write_text(text)
        print("\n" + text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
