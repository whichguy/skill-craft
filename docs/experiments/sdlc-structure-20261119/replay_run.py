#!/usr/bin/env python3
"""Run the reader replay: six read-only reviewers per case, all reading one shared case folder at once.

Slots per case: p1, p2, p3 are the same plain brief (the whole review, three independent draws); lb, lt and ld are
the three lens briefs (behaviour, tests, documents and craft). Every reviewer is a headless Claude Code session with
only Read, Grep, Glob and Bash, started in its own empty working directory (TMPDIR inside it) with the case folder
added read-only. Its last message is its report. The script records each session's stream, cost, turns and seconds,
every path and command it used (to audit reads that reach the judges' key, other reports, another case or the
original runs), and a content manifest of the case folder before and after its six readers (to show that nothing
was written there).

Usage: python3 -I replay_run.py WORK [--cases c01,c02] [--parallel 12] [--budget-total 60] [--briefs]
  --briefs prints the four briefs and exits. A finished slot is skipped, so a rerun resumes.
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time

CLAUDE = "/Users/dadleet/.local/bin/claude"
MODEL = "claude-sonnet-5-5"
EFFORT = "high"
PER_RUN_BUDGET = "2.00"
TIMEOUT = 25 * 60
SLOTS = ("p1", "p2", "p3", "lb", "lt", "ld")

SHARED = """You are one reviewer of one step of a software change. You report; you change nothing.

The case folder is CASE = {case} (read-only):
- CASE/tree/ is the working tree as it stood when this step had been built, tested and documented.
- CASE/step-change.diff is this step's change: what the step added to the tree.
- CASE/review-focus.md says what this review looks for, the code craft rules it applies, what the step worked from
  (the step, its criteria, its test cases and its proof) and the step's own result. Where it says "fix", report the
  fix you would make. TREE in it means CASE/tree; a file it names as RECORDS/... is under CASE/records/; files it
  names under GUIDES are not provided.
- CASE/records/ holds the run records that file names: the request, the spec, plan, step-plan and test-spec results
  and the test runs.

Rules:
- Write nothing inside CASE. To run the code, its tests or a one-line probe, first copy the tree into your current
  working directory (cp -R CASE/tree ./tree) and run there.
- Read only inside CASE and your current working directory.
- Create every temporary file inside your current working directory, never in /tmp or any other shared place:
  other reviewers are running on this machine at the same time.
- Judge the change on what the files and your own runs show. The step's recorded tests passed; that alone does not
  show that a behaviour is right or that a test would catch it breaking.
- Report a finding only when you can point at a wrong or failing behaviour, a requirement or criterion not met, a
  behaviour no test would catch if it broke, or a rule of the focus file that the change breaks. A review that
  finds none is a valid result.

{role}

End with exactly this report and nothing after it:

FINDINGS
1. file: <path in the tree> | where: <function, test or line> | weight: material or minor
   problem: <what is wrong or missing, in one or two sentences>
   basis: <the requirement, criterion or rule, or the command you ran and what it printed>
   change: <the edit or the test you would make>
(more numbered findings in the same form, most important first; or the single line "none" in place of the list)
READ: <the files you read>
RAN: <the commands you ran, or none>
"""

PLAIN = """Your part: the whole review. Review this step's change against every condition in the focus file's "What this
review looks for" list."""

LENS = """Your part: one lens of three. Three reviewers are reading this same change at the same time, each through one
lens, and their reports will be combined. Yours is the {name} lens: {question}
{look}
Go as deep as you can through this lens and leave everything else to the other two reviewers."""

LENSES = {
    "lb": ("behaviour", "does the code do what the spec and the step's criteria say, for every input?",
           ("Walk each new or changed public entry point with valid, boundary and invalid inputs to its return value, "
           "error or side effect, running them where you can. Look for a requirement or criterion the behaviour departs "
           "from, an input the code handles wrongly or not at all, an argument not checked before an effect, an error "
           "swallowed or turned into a success, and a language, library or platform behaviour the code relies on that "
           "nothing has exercised (limits, comparison and case rules, empty and null values, encoding, ordering).")),
    "lt": ("tests", "would the tests catch it if the behaviour broke?",
           ("For each requirement clause, criterion and test-spec case this step serves, find the test that would fail if "
           "that behaviour were wrong. Look for a behaviour or boundary of the step that no test checks, a test that "
           "asserts what the code happens to do instead of its case's oracle, a test-spec case the tests do not build, a "
           "test that cannot fail, and a proof or command that does not exercise the criteria it is recorded against.")),
    "ld": ("documents and craft", "do the documents, the knowledge home and the code's own craft hold?",
           ("Look for a document or knowledge-home line (the README, docs/shiploop/spec.md, architecture.md, "
           "environment.md) that the code or tests contradict, something the step showed that they do not record, and a "
           "break of the focus file's code craft rules: a public function with no contract docstring, dead code or a "
           "comment that restates code, a near-copy of existing logic, a dependency, option or fallback with no present "
           "need, a failure that cannot be diagnosed, a name that collides or is exported wider than needed, a file "
           "changed outside the item's paths.")),
}


def brief(case_dir, slot):
    role = PLAIN if slot.startswith("p") else LENS.format(name=LENSES[slot][0], question=LENSES[slot][1],
                                                           look=LENSES[slot][2])
    return SHARED.format(case=case_dir, role=role)


def manifest(root):
    """One hash over every file's path, mode and bytes under the case folder."""
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            digest.update(str(path.relative_to(root)).encode() + b"\0" + oct(path.stat().st_mode).encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            count += 1
    return {"files": count, "sha256": digest.hexdigest()}


def audit(events, case, slot, work):
    """Every path and command the session used; the ones that reach what a reader must not see (the judges' key,
    other reports, another case, the original runs, this repository) and the ones merely outside its two folders."""
    used, forbidden, elsewhere = [], [], []
    own = (str(work / "rv" / "cases" / case), str(work / "rv" / "work" / case / slot))
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            given = block.get("input") or {}
            text = given.get("command") or given.get("file_path") or given.get("path") or given.get("pattern") or ""
            used.append(f"{block.get('name')}: {text[:300]}")
            blob = json.dumps(given)
            for found in re.findall(r"/(?:Users|private/tmp|tmp|var)/[^\s\"'`;|&)]+", blob):
                if found.startswith(own) or f"rv-work-{case}-{slot}" in found:
                    continue
                reaches = any(mark in found for mark in ("/key", "/replay", "e2e-run", "skill-craft", "/rv/cases/",
                                                         "/rv/work/"))
                (forbidden if reaches else elsewhere).append(f"{block.get('name')}: {found[:160]}")
    return used, sorted(set(forbidden)), sorted(set(elsewhere))


def run_slot(work, case, slot):
    case_dir = work / "rv" / "cases" / case
    out = work / "replay" / "out" / case
    out.mkdir(parents=True, exist_ok=True)
    summary = out / f"{slot}.json"
    if summary.exists() and json.loads(summary.read_text()).get("report"):
        return json.loads(summary.read_text())
    cwd = work / "rv" / "work" / case / slot
    if cwd.exists():
        subprocess.run(["rm", "-rf", str(cwd)], check=False)
    cwd.mkdir(parents=True)
    argv = [CLAUDE, "-p", "--safe-mode", "--no-chrome", "--strict-mcp-config", "--model", MODEL, "--effort", EFFORT,
            "--tools", "Read,Grep,Glob,Bash", "--allowedTools", "Read,Grep,Glob,Bash", "--permission-mode", "dontAsk",
            "--add-dir", str(case_dir), "--no-session-persistence", "--max-budget-usd", PER_RUN_BUDGET,
            "--output-format", "stream-json", "--verbose"]
    started = time.time()
    stream = out / f"{slot}.jsonl"
    with stream.open("w") as sink, (out / f"{slot}.err").open("w") as err:
        (cwd / "tmp").mkdir()
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE, stdout=sink, stderr=err, text=True,
                                start_new_session=True, env=dict(os.environ, TMPDIR=str(cwd / "tmp")))
        try:
            proc.communicate(brief(case_dir, slot), timeout=TIMEOUT)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)  # this session's own process group only
            proc.wait()
            timed_out = True
    events = []
    for line in stream.read_text(errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    text = final.get("result") or ""
    report = text[text.rfind("FINDINGS"):] if "FINDINGS" in text else ""
    used, forbidden, elsewhere = audit(events, case, slot, work)
    usage = final.get("usage") or {}
    record = {
        "case": case, "slot": slot, "model": MODEL, "effort": EFFORT, "exit": proc.returncode, "timed_out": timed_out,
        "seconds": round(time.time() - started, 1), "api_seconds": round((final.get("duration_api_ms") or 0) / 1000, 1),
        "turns": final.get("num_turns"), "cost_usd": final.get("total_cost_usd"), "is_error": final.get("is_error"),
        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "cache_write_tokens": usage.get("cache_creation_input_tokens"),
        "served_models": sorted((final.get("modelUsage") or {}).keys()), "tool_calls": len(used), "used": used,
        "forbidden_reads": forbidden, "paths_elsewhere": elsewhere, "report": report, "full_text_chars": len(text),
    }
    summary.write_text(json.dumps(record, indent=1))
    (out / f"{slot}.md").write_text(report or text)
    return record


def main(argv):
    if "--briefs" in argv:
        for slot in ("p1", "lb", "lt", "ld"):
            print(f"===== {'plain (p1, p2, p3)' if slot == 'p1' else 'lens ' + LENSES[slot][0] + ' (' + slot + ')'} =====\n")
            print(brief(pathlib.Path("<the case folder>"), slot))
        return
    work = pathlib.Path(argv[0]).resolve()
    option = {argv[n]: argv[n + 1] for n in range(1, len(argv) - 1) if argv[n].startswith("--")}
    cases = option.get("--cases", "").split(",") if option.get("--cases") else sorted(
        p.name for p in (work / "rv" / "cases").iterdir() if p.name[0] in "cm")
    parallel = int(option.get("--parallel", "12"))
    budget = float(option.get("--budget-total", "60"))
    spent = [0.0]
    lock = threading.Lock()
    before = {case: manifest(work / "rv" / "cases" / case) for case in cases}
    left = {case: len(SLOTS) for case in cases}

    def job(case, slot):
        with lock:
            if spent[0] >= budget:
                return {"case": case, "slot": slot, "skipped": "total budget reached"}
        record = run_slot(work, case, slot)
        with lock:
            spent[0] += record.get("cost_usd") or 0.0
            left[case] -= 1
            words = "report" if record.get("report") else "NO REPORT"
            print(f"{time.strftime('%H:%M:%S')} {case} {slot} {words} {record.get('seconds')}s "
                  f"${record.get('cost_usd') or 0:.2f} turns {record.get('turns')} "
                  f"forbidden {len(record.get('forbidden_reads') or [])} elsewhere {len(record.get('paths_elsewhere') or [])} "
                  f"| spent ${spent[0]:.2f}", flush=True)
            if left[case] == 0:
                after = manifest(work / "rv" / "cases" / case)
                drift = {"before": before[case], "after": after, "unchanged": before[case] == after}
                (work / "replay" / "out" / case / "drift.json").write_text(json.dumps(drift, indent=1))
                print(f"{time.strftime('%H:%M:%S')} {case} case folder unchanged after its readers: {drift['unchanged']}",
                      flush=True)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
        list(pool.map(lambda pair: job(*pair), [(case, slot) for case in cases for slot in SLOTS]))
    print(f"done; spent ${spent[0]:.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
