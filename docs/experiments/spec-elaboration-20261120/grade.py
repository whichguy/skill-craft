#!/usr/bin/env python3
"""Grade a round of the spec-elaboration experiment.

Every command is resumable and none ever rewrites a verdict that exists (score-predictions-as-registered: a
re-reading is a new set of verdicts beside the first, never an edit of it).

  counts ROUND        Script-only metrics of every kept spec.md: use cases, clauses, the mix of Source kinds, words,
                      numbering gaps, clauses that bundle two behaviours behind "and", the passes an arm recorded,
                      minutes, cost and the tools the session used. Writes evidence/<round>/counts.json.
  leaks ROUND         Script-only check of every subject stream for a path under the real HOME outside the session's
                      own working directory and throwaway profile (a user-level skill, memory or config that reached
                      the subject). Writes evidence/<round>/leaks.txt and exits 1 when any session leaked.
  judge ROUND         One headless judge session per kept spec, reading that spec and that case's held-out nuance
                      checklist, and writing a verdict per nuance: covered, partial or absent, the clause that states
                      it, and a quote. Writes grades/<round>/<slot>.json.
                        --tag=T      a second set of verdicts beside the first, in grades/<round>@T/ (a repeat draw,
                                     or another judge); the untagged set is the registered one and is never replaced
                        --judge=J    opus (default: claude-opus-5-5 at high) or astra (Codex gpt-6.2-astra at high,
                                     the E2E harness's own judge role); any judge but opus needs a tag
  board ROUND         The scoreboard: coverage by arm, driver and nuance category, beside the counts. --tag=T reads
                      the tagged verdicts. Writes evidence/<round>/scoreboard[@T].txt.
  agree ROUND         How far tagged verdict sets agree with the registered one: --tags=r2,gpt. Per specification and
                      pooled, and nuance by nuance. Writes evidence/<round>/agreement.txt.
  audit ROUND         One headless Opus session per kept spec, reading the request and the spec, putting every clause
                      in one class: request, needed, decision, extra, empty or wrong. Writes audits/<round>/<slot>.json.
                      --arms=A,B limits it to those arms (it reads C-n clauses, which ShipLoop's own form has none of).
  audit-board ROUND   The share of clauses in each class by arm and driver, with the clauses called extra, empty or
                      wrong. Writes evidence/<round>/audit.txt.

Usage: python3 -I grade.py COMMAND ROUND [--parallel=3] [--timeout=1800] [--tag=T] [--judge=J] [--tags=a,b]
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
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
import hosts  # the E2E harness host interface: its Codex profile isolation is used as it stands

CLAUDE = shutil.which("claude") or "/Users/dadleet/.local/bin/claude"
WORK = Path(os.environ.get("SPEC_ELAB_WORK") or Path.home() / "e2e-runs" / "spec-elaboration-20261120")
JUDGES = {
    "opus": {"host": "claude", "model": "claude-opus-5-5", "effort": "high"},
    "astra": {"host": "codex", "model": "gpt-6.2-astra", "effort": "high"},
}
JUDGE_MODEL, JUDGE_EFFORT = JUDGES["opus"]["model"], JUDGES["opus"]["effort"]
PRINT = threading.Lock()
STATES = ("covered", "partial", "absent")
CLASSES = ("request", "needed", "decision", "extra", "empty", "wrong")

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

AUDIT_PROMPT = """You are auditing one written specification, clause by clause, against the one-sentence request it
was written from. You judge; you change nothing but your own verdict file.

Two files are in your working directory:
- `request.txt` holds the request exactly as the requester wrote it. It is all the requester said.
- `spec.md` is a specification somebody wrote from it, with numbered clauses (C-n).

Put every clause into exactly one class:

- `request`: the clause says something the request's own words say, or that follows from them directly.
- `needed`: the request does not say it, but what was asked for cannot work, or cannot safely be given to the
  people it is for, without it. A builder who left it out would deliver something broken, unsafe or unusable for the
  request's own purpose.
- `decision`: the request is silent, a builder could not build what was asked without settling this one way or
  another, and the clause records the choice. The requester might have chosen differently; they could not have
  avoided choosing.
- `extra`: the clause adds a capability, a duty or a restriction that the request's purpose does not call for. A
  builder could leave out everything it asks for and still deliver what was requested, with nothing the requester
  would call missing or broken; building it costs real work.
- `empty`: the clause decides nothing a builder can act on: it names a limit without the limit, a rule without its
  content, or a behaviour so general it would be true of any product.
- `wrong`: the clause contradicts another clause, cannot hold on the platform the request names, or states a fact
  about that platform that is false. Use it only when you can say what is wrong.

Decide by what the clause requires, not by how it is labelled: its `Source:` line is the writer's own claim and may
be mistaken. When a clause sits between `decision` and `extra`, ask whether a builder asked only for what the request
names would have had to face this question at all. If so, it is a decision. If the question arises only because the
specification itself introduced something beyond the request, it is extra.

Write `verdict.json` in your working directory, and nothing else, in exactly this shape:

{"clauses": [{"id": "C-1", "class": "request"}, {"id": "C-2", "class": "extra", "why": "<one sentence>"}]}

One entry per clause in `spec.md`, in order, with no clause left out. Give `why` for every `extra`, `empty` and
`wrong`, and for no other class. Keep each `why` under 30 words.
"""


def say(*parts):
    with PRINT:
        print(*parts, flush=True)


def slots(round_name):
    root = HERE / "results" / round_name
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "spec.md").is_file()) if root.is_dir() else []


def cases():
    return {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())["cases"]}


def flags_and_args(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {}
    for flag in (a for a in argv if a.startswith("--")):
        key, _, value = flag[2:].partition("=")
        flags[key] = value or "1"
    return args, flags


def grades_dir(round_name, tag=None):
    return HERE / "grades" / (f"{round_name}@{tag}" if tag else round_name)


def judged_text(slot):
    """What the judge is given as spec.md: the specification, then any other document the same stage wrote."""
    text = (slot / "spec.md").read_text()
    for other in sorted((slot / "also").glob("*.md")) if (slot / "also").is_dir() else []:
        text += f"\n\n---\n\n# Also written by this stage: {other.name}\n\n" + other.read_text()
    return text


def clause_ids(text):
    return [f"C-{n}" for n in dict.fromkeys(re.findall(r"^#{2,4}\s*C-(\d+)\b", text, re.MULTILINE))]


def parse_spec(text):
    use_cases = re.findall(r"^#{2,4}\s*U-(\d+)\b", text, re.MULTILINE)
    clauses = re.findall(r"^#{2,4}\s*C-(\d+)\b", text, re.MULTILINE)
    sources = [m.group(1).lower() for m in re.finditer(r"^Source:\s*([A-Za-z]+)", text, re.MULTILINE)]
    mix = {kind: sources.count(kind) for kind in sorted(set(sources))}

    def gaps(found):
        numbers = sorted(int(n) for n in found)
        return [n for n in range(1, (numbers[-1] if numbers else 0) + 1) if n not in numbers]

    bundled = [m.group(1)[:70] for m in re.finditer(r"^#{2,4}\s*C-\d+:\s*(.+)$", text, re.MULTILINE)
               if " and " in m.group(1)]
    requirements = re.findall(r"^#{2,4}\s*R-(\d+)\b", text, re.MULTILINE)
    return {"use_cases": len(set(use_cases)), "clauses": len(set(clauses)), "requirements": len(set(requirements)),
            "source_mix": mix,
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
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
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
        row["words_judged"] = len(judged_text(slot).split())
        usage = meta.get("usage") or {}
        row.update(seconds=meta.get("seconds"), rc=meta.get("rc"), arm=meta.get("arm"), driver=meta.get("driver"),
                   case=meta.get("case"), cost_usd=meta.get("cost_usd"), turns=meta.get("turns"),
                   output_tokens=usage.get("output_tokens"), tools=tool_use(slot),
                   also=sorted(p.name for p in (slot / "also").glob("*.md")) if (slot / "also").is_dir() else [])
        if (slot / "stream.jsonl").is_file():
            opened = sorted({found for text in session_texts(slot / "stream.jsonl")
                             for found in re.findall(r"GUIDES/([\w./-]+\.md)", text)})
            if opened:
                row["guides_opened"] = opened
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
        say(f"{name:52s} U={row['use_cases']:3d} C={row['clauses']:3d} R={row['requirements']:3d} "
            f"words={row['words']:6d} passes={row.get('passes_recorded', '-'):>3} mix={row['source_mix']}")
    say(f"\n{len(out)} specs -> {(target / 'counts.json').relative_to(HERE)}")


def session_texts(stream):
    """Every command and file path a subject session passed to a tool, from its recorded stream (either host)."""
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            yield item.get("command") or ""
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                given = block.get("input") or {}
                yield " ".join(str(given.get(key) or "") for key in ("command", "file_path", "path", "pattern"))


def cmd_leaks(round_name, _flags):
    """Did any subject session reach outside its own working directory and throwaway profile?"""
    real_home = str(Path.home())
    lines, leaking = [], 0
    for slot in slots(round_name):
        meta = json.loads((slot / "meta.json").read_text()) if (slot / "meta.json").is_file() else {}
        workdir = meta.get("workdir") or ""
        own = [workdir, str(Path(workdir).parent / ".homes")] if workdir else []
        outside, system = defaultdict(int), 0
        for text in session_texts(slot / "stream.jsonl") if (slot / "stream.jsonl").is_file() else []:
            found = re.findall(r"(/(?:Users|home|private|tmp|etc|var|opt|usr|Library)/[^\s'\"\\);|&<>]*)", text)
            if meta.get("host") == "claude":
                found += [real_home + part[1:] for part in re.findall(r"(?<![\w/])(~/[^\s'\"\\);|&<>]*)", text)]
            for path in found:
                if any(path.startswith(prefix) for prefix in own if prefix):
                    continue
                if path.startswith(real_home):
                    outside[path.rstrip(";,")] += 1
                else:
                    system += 1
        if outside:
            leaking += 1
            lines.append(f"LEAK  {slot.name}")
            lines.extend(f"        {count}x {path}" for path, count in sorted(outside.items()))
        else:
            lines.append(f"clean {slot.name}   (system paths referenced: {system})")
    lines.append("")
    lines.append(f"{leaking} of {len(slots(round_name))} sessions referenced a path under the real HOME outside their own "
                 f"working directory and throwaway profile")
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "leaks.txt").write_text(text)
    print(text)
    if leaking:
        raise SystemExit(1)


def run_session(prompt, cwd, judge, timeout):
    """One headless judging session in cwd on either host, customizations off. Returns (rc, cost in dollars or None)."""
    (cwd / ".tmp").mkdir(parents=True, exist_ok=True)
    if judge["host"] == "claude":
        argv = [CLAUDE, "-p", prompt, "--safe-mode", "--strict-mcp-config", "--model", judge["model"],
                "--effort", judge["effort"], "--permission-mode", "acceptEdits", "--output-format", "stream-json",
                "--verbose", "--no-session-persistence", "--add-dir", str(cwd)]
        env = {**os.environ, "NO_COLOR": "1", "TMPDIR": str(cwd / ".tmp")}
    else:
        home = cwd.parent / ".homes" / cwd.name
        home.mkdir(parents=True, exist_ok=True)
        env = hosts.CodexHost().env(home)
        argv = ["codex", "exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
                "-s", "workspace-write", "-c", 'approval_policy="never"',
                "-c", f"model_reasoning_effort={judge['effort']}", "-m", judge["model"], "-C", str(cwd),
                "-o", str(cwd / ".last-message.txt"), prompt]
    with open(cwd / ".stream.jsonl", "w") as stream, open(cwd / ".stderr.txt", "w") as err:
        try:
            rc = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stream, stderr=err, env=env,
                                timeout=timeout, check=False).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    cost = None
    for line in (cwd / ".stream.jsonl").read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            cost = event.get("total_cost_usd")
    return rc, cost


def read_verdict(cwd, key):
    """The list under `key` in the session's verdict.json, or (None, why)."""
    verdict_file = cwd / "verdict.json"
    if not verdict_file.is_file():
        return None, "no verdict.json"
    try:
        return json.loads(verdict_file.read_text())[key], None
    except (ValueError, KeyError, TypeError) as problem:
        return None, f"unreadable verdict: {problem}"


def judge_one(round_name, slot, case, timeout, tag, judge_name):
    kept = grades_dir(round_name, tag)
    kept.mkdir(parents=True, exist_ok=True)
    out = kept / f"{slot.name}.json"
    if out.is_file():
        say("SKIP", slot.name)
        return
    judge = JUDGES[judge_name]
    cwd = WORK / round_name / f"judge{'-' + tag if tag else ''}-{slot.name}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    (cwd / "spec.md").write_text(judged_text(slot))
    (cwd / "checklist.json").write_text(json.dumps(
        [{"id": n["id"], "nuance": n["nuance"]} for n in case["nuances"]], indent=1) + "\n")
    rc, cost = run_session(JUDGE_PROMPT, cwd, judge, timeout)
    verdicts, problem = read_verdict(cwd, "verdicts")
    if rc != 0 or verdicts is None:
        say("FAIL", slot.name, f"rc={rc}", problem or "")
        return
    wanted = [n["id"] for n in case["nuances"]]
    seen = {}
    for verdict in verdicts:
        if isinstance(verdict, dict) and "id" in verdict:
            verdict["state"] = str(verdict.get("state") or "").strip().lower()
            seen[verdict["id"]] = verdict
    missing = [i for i in wanted if i not in seen]
    odd = [i for i in wanted if i in seen and seen[i]["state"] not in STATES]
    out.write_text(json.dumps({"slot": slot.name, "case": case["id"], "judge": judge["model"],
                               "judge_effort": judge["effort"], "tag": tag, "cost_usd": cost,
                               "missing_ids": missing, "unknown_states": odd,
                               "verdicts": [seen[i] for i in wanted if i in seen]}, indent=1) + "\n")
    covered = sum(1 for i in wanted if seen.get(i, {}).get("state") == "covered")
    partial = sum(1 for i in wanted if seen.get(i, {}).get("state") == "partial")
    say("DONE", slot.name, f"covered={covered}/{len(wanted)} partial={partial}",
        f"missing={len(missing)}" if missing else "")


def cmd_judge(round_name, flags):
    tag, judge_name = flags.get("tag"), flags.get("judge", "opus")
    if judge_name not in JUDGES:
        raise SystemExit(f"no judge {judge_name!r}; there are {', '.join(JUDGES)}")
    if judge_name != "opus" and not tag:
        raise SystemExit("a judge other than opus needs --tag, so its verdicts never land in the registered set")
    by_case = cases()
    jobs = [(s, by_case[json.loads((s / "meta.json").read_text())["case"]]) for s in slots(round_name)]
    timeout, width = int(flags.get("timeout", 1800)), int(flags.get("parallel", 3))
    judge = JUDGES[judge_name]
    say(f"judging {len(jobs)} specs on {judge['model']} ({judge['effort']}), {width} at a time"
        + (f", tag {tag}" if tag else ""))
    with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(judge_one, round_name, s, c, timeout, tag, judge_name) for s, c in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def cmd_board(round_name, flags):
    tag = flags.get("tag")
    counts_file = HERE / "evidence" / round_name / "counts.json"
    counts = json.loads(counts_file.read_text()) if counts_file.is_file() else {}
    by_case, lines = cases(), []
    folder = grades_dir(round_name, tag)
    grades = sorted(folder.glob("*.json")) if folder.is_dir() else []
    rows, per_arm, per_cat = [], defaultdict(lambda: [0, 0, 0, 0]), defaultdict(lambda: defaultdict(lambda: [0, 0]))
    judge_label = f"{JUDGE_MODEL} {JUDGE_EFFORT}"
    for path in grades:
        grade = json.loads(path.read_text())
        judge_label = f"{grade.get('judge', JUDGE_MODEL)} {grade.get('judge_effort', JUDGE_EFFORT)}"
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
    lines.append(f"ROUND {round_name}{'@' + tag if tag else ''}   judge {judge_label}   {len(rows)} graded specs")
    lines.append("")
    lines.append(f"{'case':20s} {'arm':18s} {'driver':12s} {'covered':>9s} {'part':>5s} {'of':>4s} "
                 f"{'U':>3s} {'C':>4s} {'words':>6s} {'min':>5s}")
    for case_id, arm, driver, covered, partial, total, row in sorted(rows):
        minutes = f"{row.get('seconds') / 60:.1f}" if row.get("seconds") else "-"
        lines.append(f"{case_id:20s} {arm:18s} {driver:12s} {covered:9d} {partial:5d} {total:4d} "
                     f"{row.get('use_cases', 0):3d} {row.get('clauses', 0):4d} {row.get('words', 0):6d} "
                     f"{minutes:>5s}")
    lines.append("")
    lines.append("BY ARM AND DRIVER (pooled over cases)")
    for (arm, driver), (covered, partial, total, n) in sorted(per_arm.items()):
        share = f"{100 * covered / total:.0f}%" if total else "-"
        lines.append(f"  {arm:18s} {driver:12s} covered {covered:3d}/{total:3d} ({share:>4s})  "
                     f"partial {partial:3d}  over {n} cases")
    lines.append("")
    lines.append("BY NUANCE CATEGORY (covered / of)")
    arms_seen = sorted({k for cell in per_cat.values() for k in cell})
    lines.append("  " + f"{'category':14s}" + "".join(f"{a[:12] + ' ' + d[:6]:>21s}" for a, d in arms_seen))
    for category in sorted(per_cat):
        cells = "".join(f"{str(per_cat[category][k][0]) + '/' + str(per_cat[category][k][1]):>21s}" for k in arms_seen)
        lines.append(f"  {category:14s}{cells}")
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / f"scoreboard{'@' + tag if tag else ''}.txt").write_text(text)
    print(text)


def cmd_agree(round_name, flags):
    """How far each tagged verdict set agrees with the registered one, on the same specifications."""
    tags = [t for t in flags.get("tags", "").split(",") if t]
    if not tags:
        raise SystemExit("agree needs --tags=a,b")
    base = {p.stem: json.loads(p.read_text()) for p in sorted(grades_dir(round_name).glob("*.json"))}
    lines = [f"ROUND {round_name}: agreement of tagged verdict sets with the registered one ({len(base)} specifications)", ""]
    for tag in tags:
        other = {p.stem: json.loads(p.read_text()) for p in sorted(grades_dir(round_name, tag).glob("*.json"))}
        shared = sorted(set(base) & set(other))
        if not shared:
            lines.append(f"@{tag}: no specification judged in both sets")
            continue
        judge = f"{other[shared[0]].get('judge')} {other[shared[0]].get('judge_effort')}"
        lines.append(f"@{tag}  ({judge}), {len(shared)} specifications in both sets")
        lines.append(f"  {'specification':56s} {'registered':>10s} {'@' + tag:>8s} {'diff':>5s}")
        same_state = same_cover = total = 0
        diffs, pooled = [], defaultdict(lambda: [0, 0])
        flips = defaultdict(int)
        for name in shared:
            first = {v["id"]: v.get("state") for v in base[name]["verdicts"]}
            second = {v["id"]: v.get("state") for v in other[name]["verdicts"]}
            ids = [i for i in first if i in second]
            a = sum(1 for i in ids if first[i] == "covered")
            b = sum(1 for i in ids if second[i] == "covered")
            diffs.append(b - a)
            _case, arm, driver = name.split("__")
            pooled[(arm, driver)][0] += a
            pooled[(arm, driver)][1] += b
            for i in ids:
                total += 1
                same_state += first[i] == second[i]
                same_cover += (first[i] == "covered") == (second[i] == "covered")
                if first[i] != second[i]:
                    flips[f"{first[i]} -> {second[i]}"] += 1
            lines.append(f"  {name:56s} {a:10d} {b:8d} {b - a:+5d}")
        mean_abs = sum(abs(d) for d in diffs) / len(diffs)
        lines.append(f"  per specification: mean |diff| {mean_abs:.2f}, largest {max(abs(d) for d in diffs)}, "
                     f"sum of diffs {sum(diffs):+d}")
        lines.append(f"  nuance by nuance ({total}): same state {100 * same_state / total:.0f}%, "
                     f"same covered-or-not {100 * same_cover / total:.0f}%")
        lines.append("  changes: " + (", ".join(f"{k} x{v}" for k, v in sorted(flips.items(), key=lambda kv: -kv[1])) or "none"))
        lines.append("  pooled by arm and driver, registered -> @" + tag + ":")
        for (arm, driver), (a, b) in sorted(pooled.items()):
            lines.append(f"    {arm:18s} {driver:12s} {a:3d} -> {b:3d}  ({b - a:+d})")
        lines.append("")
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "agreement.txt").write_text(text)
    print(text)


def audit_one(round_name, slot, case, timeout):
    kept = HERE / "audits" / round_name
    kept.mkdir(parents=True, exist_ok=True)
    out = kept / f"{slot.name}.json"
    if out.is_file():
        say("SKIP", slot.name)
        return
    cwd = WORK / round_name / f"audit-{slot.name}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    spec = (slot / "spec.md").read_text()
    (cwd / "spec.md").write_text(spec)
    (cwd / "request.txt").write_text(case["request"] + "\n")
    rc, cost = run_session(AUDIT_PROMPT, cwd, JUDGES["opus"], timeout)
    rows, problem = read_verdict(cwd, "clauses")
    if rc != 0 or rows is None:
        say("FAIL", slot.name, f"rc={rc}", problem or "")
        return
    wanted = clause_ids(spec)
    seen = {}
    for row in rows:
        if isinstance(row, dict) and "id" in row:
            row["class"] = str(row.get("class") or "").strip().lower()
            seen[row["id"]] = row
    missing = [i for i in wanted if i not in seen]
    out.write_text(json.dumps({"slot": slot.name, "case": case["id"], "judge": JUDGES["opus"]["model"],
                               "judge_effort": JUDGES["opus"]["effort"], "cost_usd": cost, "missing_ids": missing,
                               "clauses": [seen[i] for i in wanted if i in seen]}, indent=1) + "\n")
    tally = defaultdict(int)
    for i in wanted:
        tally[seen.get(i, {}).get("class", "missing")] += 1
    say("DONE", slot.name, " ".join(f"{k}={tally[k]}" for k in (*CLASSES, "missing") if tally[k]))


def cmd_audit(round_name, flags):
    by_case = cases()
    arms = [a for a in flags.get("arms", "").split(",") if a]
    jobs = [(s, by_case[json.loads((s / "meta.json").read_text())["case"]]) for s in slots(round_name)
            if not arms or s.name.split("__")[1] in arms]
    timeout, width = int(flags.get("timeout", 2400)), int(flags.get("parallel", 3))
    say(f"auditing {len(jobs)} specs clause by clause on {JUDGES['opus']['model']} ({JUDGES['opus']['effort']}), "
        f"{width} at a time")
    with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
        futures = [pool.submit(audit_one, round_name, s, c, timeout) for s, c in jobs]
        for future in concurrent.futures.as_completed(futures):
            future.result()


def cmd_audit_board(round_name, _flags):
    folder = HERE / "audits" / round_name
    audits = sorted(folder.glob("*.json")) if folder.is_dir() else []
    pooled, notes, rows = defaultdict(lambda: defaultdict(int)), defaultdict(list), []
    for path in audits:
        audit = json.loads(path.read_text())
        case_id, arm, driver = audit["slot"].split("__")
        tally = defaultdict(int)
        for row in audit["clauses"]:
            kind = row.get("class") if row.get("class") in CLASSES else "unknown"
            tally[kind] += 1
            pooled[(arm, driver)][kind] += 1
            if kind in ("extra", "empty", "wrong"):
                notes[(arm, driver, kind)].append(f"{case_id} {row['id']}: {str(row.get('why') or '')[:150]}")
        tally["missing"] = len(audit.get("missing_ids") or [])
        rows.append((case_id, arm, driver, tally))
    judge = f"{JUDGES['opus']['model']} {JUDGES['opus']['effort']}"
    lines = [f"ROUND {round_name}: every clause put in one class by {judge}; {len(rows)} specifications", ""]
    lines.append(f"{'case':20s} {'arm':18s} {'driver':12s} " + " ".join(f"{k:>8s}" for k in CLASSES) + f" {'missing':>8s}")
    for case_id, arm, driver, tally in sorted(rows):
        lines.append(f"{case_id:20s} {arm:18s} {driver:12s} " + " ".join(f"{tally[k]:8d}" for k in CLASSES)
                     + f" {tally['missing']:8d}")
    lines.append("")
    lines.append("POOLED BY ARM AND DRIVER: clauses, then the share of them in each class")
    for (arm, driver), tally in sorted(pooled.items()):
        total = sum(tally.values())
        lines.append(f"  {arm:18s} {driver:12s} {total:4d} clauses  "
                     + "  ".join(f"{k} {100 * tally[k] / total:.0f}%" for k in CLASSES)
                     + f"   | extra+empty+wrong {tally['extra'] + tally['empty'] + tally['wrong']} "
                       f"({100 * (tally['extra'] + tally['empty'] + tally['wrong']) / total:.0f}%)")
    for kind in ("extra", "empty", "wrong"):
        lines.append("")
        lines.append(f"CLAUSES CALLED {kind.upper()} (up to 8 per arm and driver)")
        for (arm, driver, found), items in sorted(notes.items()):
            if found != kind:
                continue
            lines.append(f"  {arm} {driver}: {len(items)}")
            lines.extend(f"      {item}" for item in items[:8])
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / round_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "audit.txt").write_text(text)
    print(text)


def main():
    args, flags = flags_and_args(sys.argv[1:])
    commands = {"counts": cmd_counts, "leaks": cmd_leaks, "judge": cmd_judge, "board": cmd_board,
                "agree": cmd_agree, "audit": cmd_audit, "audit-board": cmd_audit_board}
    if len(args) < 2 or args[0] not in commands:
        print(__doc__)
        raise SystemExit(2)
    commands[args[0]](args[1], flags)


if __name__ == "__main__":
    main()
