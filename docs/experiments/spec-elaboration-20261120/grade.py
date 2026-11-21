#!/usr/bin/env python3
"""Grade a round of the spec-elaboration experiment.

Three commands, each resumable; none ever rewrites a verdict that exists (score-predictions-as-registered: a
re-reading is a new round, not an edit of this one).

  counts ROUND   Script-only metrics of every kept spec.md: use cases, clauses, the mix of Source kinds, words,
                 numbering gaps, clauses that bundle two behaviours behind "and", and the passes an arm recorded.
                 No model runs. Writes evidence/<round>/counts.json.
  judge ROUND    One headless Opus session per kept spec, reading that spec and that case's held-out nuance
                 checklist, and writing a verdict per nuance: covered or not, the clause that states it, and a
                 quote from the spec. Writes grades/<round>/<slot>.json (skipped if already there).
  board ROUND    The scoreboard: coverage by arm, driver and nuance category, beside the counts. Writes
                 evidence/<round>/scoreboard.txt and prints it.

Usage: python3 -I grade.py {counts|judge|board} ROUND [--parallel 3] [--timeout 1800]
"""
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE = shutil.which("claude") or "/Users/dadleet/.local/bin/claude"
WORK = Path(os.environ.get("SPEC_ELAB_WORK") or Path.home() / "e2e-runs" / "spec-elaboration-20261120")
JUDGE_MODEL, JUDGE_EFFORT = "claude-opus-5-5", "high"
PRINT = threading.Lock()

JUDGE_PROMPT = """You are checking one written specification for coverage of a fixed checklist. You judge; you change
nothing but your own verdict file.

Two files are in your working directory:
- `spec.md` is a specification somebody wrote from a one-sentence request. It has numbered use cases (U-n) and
  numbered clauses (C-n).
- `checklist.json` is a list of nuances, each with an id and one sentence. Each was written independently, before
  this specification existed, as something a well-elaborated specification of that request ought to state.

For every nuance in the checklist, decide whether this specification states it.

- `covered`: a use case or clause in `spec.md` states this nuance, specifically enough that a builder reading only
  the specification would handle it. Name the U-n or C-n and quote the words that carry it.
- `partial`: the specification touches the nuance but leaves what a builder would need undecided - it names the
  topic without the behaviour, or states the behaviour without the value or boundary the nuance is about.
- `absent`: nothing in the specification states it.

Judge only what the text says. A nuance is not covered because the specification is long, because a clause is
nearby, or because a competent builder would think of it anyway. Do not reward a general sentence that would be
true of any product ("errors are handled gracefully") for a specific nuance. Equally, a nuance is covered when the
specification states the same thing in its own words, with its own structure, even if it uses none of the
checklist's wording - you are checking meaning, not vocabulary.

Write your answer to `verdict.json` in your working directory, and nothing else, as exactly this shape:

{"verdicts": [{"id": "N-1", "state": "covered", "where": "C-14", "quote": "<the words from spec.md>"},
              {"id": "N-2", "state": "absent", "where": null, "quote": null}]}

One entry per checklist nuance, in the checklist's order, with no nuance left out. For `partial`, name where and
quote it, and add "missing": "<what a builder would still have to decide>". Keep each quote under 40 words.
"""


def say(*parts):
    with PRINT:
        print(*parts, flush=True)


def slots(round_name):
    root = HERE / "results" / round_name
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "spec.md").is_file()) if root.is_dir() else []


def cases():
    return {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())["cases"]}


def parse_spec(text):
    use_cases = re.findall(r"^#{2,4}\s*U-(\d+)\b", text, re.MULTILINE)
    clauses = re.findall(r"^#{2,4}\s*C-(\d+)\b", text, re.MULTILINE)
    sources = [m.group(1).lower() for m in re.finditer(r"^Source:\s*([A-Za-z]+)", text, re.MULTILINE)]
    mix = {kind: sources.count(kind) for kind in sorted(set(sources))}
    def gaps(found):
        numbers = sorted(int(n) for n in found)
        return [n for n in range(1, (numbers[-1] if numbers else 0) + 1) if n not in numbers]
    bundled = [m.group(1)[:70] for m in re.finditer(r"^#{2,4}\s*C-\d+:\s*(.+)$", text, re.MULTILINE) if " and " in m.group(1)]
    return {"use_cases": len(set(use_cases)), "clauses": len(set(clauses)), "source_mix": mix,
            "use_case_gaps": gaps(use_cases), "clause_gaps": gaps(clauses), "words": len(text.split()),
            "bundled_and": len(bundled), "bundled_examples": bundled[:3]}


def tool_use(slot):
    """Which tools a subject session actually used, from its recorded stream (Claude names, Codex item types)."""
    stream = slot / "stream.jsonl"
    if not stream.is_file():
        return {}
    used = defaultdict(int)
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                used[block.get("name") or "?"] += 1
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type"):
            used[item["type"]] += 1
    return dict(sorted(used.items()))


def cmd_counts(round_name, _flags):
    out = {}
    for slot in slots(round_name):
        meta = json.loads((slot / "meta.json").read_text()) if (slot / "meta.json").is_file() else {}
        row = parse_spec((slot / "spec.md").read_text())
        row.update(seconds=meta.get("seconds"), rc=meta.get("rc"), arm=meta.get("arm"), driver=meta.get("driver"),
                   case=meta.get("case"), cost_usd=meta.get("cost_usd"), turns=meta.get("turns"),
                   tools=tool_use(slot))
        if (slot / "passes.md").is_file():
            passes = (slot / "passes.md").read_text()
            row["passes_recorded"] = len(re.findall(r"^#{1,4}\s*(?:Pass|pass)\s*\d+", passes, re.MULTILINE)) or \
                len(re.findall(r"^#{1,4}\s", passes, re.MULTILINE))
            row["passes_words"] = len(passes.split())
        out[slot.name] = row
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "counts.json").write_text(json.dumps(out, indent=1) + "\n")
    for name, row in sorted(out.items()):
        say(f"{name:52s} U={row['use_cases']:3d} C={row['clauses']:3d} words={row['words']:6d} "
            f"passes={row.get('passes_recorded', '-'):>3} mix={row['source_mix']}")
    say(f"\n{len(out)} specs -> {(target / 'counts.json').relative_to(HERE)}")


def judge_one(round_name, slot, case, timeout):
    kept = HERE / "grades" / round_name
    kept.mkdir(parents=True, exist_ok=True)
    out = kept / f"{slot.name}.json"
    if out.is_file():
        say("SKIP", slot.name)
        return
    cwd = WORK / round_name / f"judge-{slot.name}-{uuid.uuid4().hex[:6]}"
    (cwd / ".tmp").mkdir(parents=True)
    shutil.copy2(slot / "spec.md", cwd / "spec.md")
    (cwd / "checklist.json").write_text(json.dumps(
        [{"id": n["id"], "nuance": n["nuance"]} for n in case["nuances"]], indent=1) + "\n")
    argv = [CLAUDE, "-p", JUDGE_PROMPT, "--safe-mode", "--strict-mcp-config", "--model", JUDGE_MODEL,
            "--effort", JUDGE_EFFORT, "--permission-mode", "acceptEdits", "--output-format", "stream-json",
            "--verbose", "--no-session-persistence", "--add-dir", str(cwd)]
    env = {**os.environ, "NO_COLOR": "1", "TMPDIR": str(cwd / ".tmp")}
    with open(cwd / ".stream.jsonl", "w") as stream, open(cwd / ".stderr.txt", "w") as err:
        try:
            rc = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stream, stderr=err, env=env,
                                timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    verdict_file = cwd / "verdict.json"
    if rc != 0 or not verdict_file.is_file():
        say("FAIL", slot.name, f"rc={rc}", "no verdict.json" if not verdict_file.is_file() else "")
        return
    try:
        verdicts = json.loads(verdict_file.read_text())["verdicts"]
    except (ValueError, KeyError) as problem:
        say("FAIL", slot.name, f"unreadable verdict: {problem}")
        return
    wanted = [n["id"] for n in case["nuances"]]
    seen = {v["id"]: v for v in verdicts if isinstance(v, dict) and "id" in v}
    missing = [i for i in wanted if i not in seen]
    out.write_text(json.dumps({"slot": slot.name, "case": case["id"], "judge": JUDGE_MODEL,
                               "judge_effort": JUDGE_EFFORT, "missing_ids": missing,
                               "verdicts": [seen[i] for i in wanted if i in seen]}, indent=1) + "\n")
    covered = sum(1 for i in wanted if seen.get(i, {}).get("state") == "covered")
    partial = sum(1 for i in wanted if seen.get(i, {}).get("state") == "partial")
    say("DONE", slot.name, f"covered={covered}/{len(wanted)} partial={partial}")


def cmd_judge(round_name, flags):
    by_case = cases()
    jobs = [(s, by_case[json.loads((s / "meta.json").read_text())["case"]]) for s in slots(round_name)]
    timeout = int(flags.get("timeout", 1800))
    width = int(flags.get("parallel", 3))
    say(f"judging {len(jobs)} specs on {JUDGE_MODEL} ({JUDGE_EFFORT}), {width} at a time")
    with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(judge_one, round_name, s, c, timeout) for s, c in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def cmd_board(round_name, _flags):
    counts_file = HERE / "evidence" / round_name / "counts.json"
    counts = json.loads(counts_file.read_text()) if counts_file.is_file() else {}
    by_case, lines = cases(), []
    grades = sorted((HERE / "grades" / round_name).glob("*.json")) if (HERE / "grades" / round_name).is_dir() else []
    rows, per_arm, per_cat = [], defaultdict(lambda: [0, 0, 0, 0]), defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for path in grades:
        grade = json.loads(path.read_text())
        slot = grade["slot"]
        case_id, arm, driver = slot.split("__")
        states = {v["id"]: v.get("state") for v in grade["verdicts"]}
        total = len(by_case[case_id]["nuances"])
        covered = sum(1 for s in states.values() if s == "covered")
        partial = sum(1 for s in states.values() if s == "partial")
        row = counts.get(slot, {})
        rows.append((case_id, arm, driver, covered, partial, total, row))
        box = per_arm[(arm, driver)]
        box[0] += covered
        box[1] += partial
        box[2] += total
        box[3] += 1
        for nuance in by_case[case_id]["nuances"]:
            cell = per_cat[nuance["category"]][(arm, driver)]
            cell[0] += 1 if states.get(nuance["id"]) == "covered" else 0
            cell[1] += 1
    lines.append(f"ROUND {round_name}   judge {JUDGE_MODEL} {JUDGE_EFFORT}   {len(rows)} graded specs")
    lines.append("")
    lines.append(f"{'case':20s} {'arm':12s} {'driver':12s} {'covered':>9s} {'part':>5s} {'of':>4s} "
                 f"{'U':>3s} {'C':>4s} {'words':>6s} {'min':>5s}")
    for case_id, arm, driver, covered, partial, total, row in sorted(rows):
        minutes = f"{row.get('seconds') / 60:.1f}" if row.get("seconds") else "-"
        lines.append(f"{case_id:20s} {arm:12s} {driver:12s} {covered:9d} {partial:5d} {total:4d} "
                     f"{row.get('use_cases', 0):3d} {row.get('clauses', 0):4d} {row.get('words', 0):6d} "
                     f"{minutes:>5s}")
    lines.append("")
    lines.append("BY ARM AND DRIVER (pooled over cases)")
    for (arm, driver), (covered, partial, total, n) in sorted(per_arm.items()):
        share = f"{100 * covered / total:.0f}%" if total else "-"
        lines.append(f"  {arm:12s} {driver:12s} covered {covered:3d}/{total:3d} ({share:>4s})  "
                     f"partial {partial:3d}  over {n} cases")
    lines.append("")
    lines.append("BY NUANCE CATEGORY (covered / of)")
    arms_seen = sorted({k for cell in per_cat.values() for k in cell})
    header = "  " + f"{'category':14s}" + "".join(f"{a + ' ' + d:>26s}" for a, d in arms_seen)
    lines.append(header)
    for category in sorted(per_cat):
        cells = "".join(f"{per_cat[category][k][0]:>13d}/{per_cat[category][k][1]:<12d}" for k in arms_seen)
        lines.append(f"  {category:14s}{cells}")
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "scoreboard.txt").write_text(text)
    print(text)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {}
    for flag in (a for a in sys.argv[1:] if a.startswith("--")):
        key, _, value = flag[2:].partition("=")
        flags[key] = value or "1"
    if len(args) < 2 or args[0] not in ("counts", "judge", "board"):
        print(__doc__)
        raise SystemExit(2)
    {"counts": cmd_counts, "judge": cmd_judge, "board": cmd_board}[args[0]](args[1], flags)


if __name__ == "__main__":
    main()
