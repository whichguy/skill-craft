#!/usr/bin/env python3
"""The guides test (journal sections 39 and 40): real ShipLoop runs from one sentence, read at the accepted specification.

Three arms of one build: A, ShipLoop as it is; C, the same with one cue sentence at the head of the spec stage; X, the
cue and, after the stage's duties, the text of two guide sections. Each sample is a real run of
test/shiploop_e2e/run.py on a small existing user service, started from the sentence REQUEST and ended through the
harness's own stop file once the navigator has accepted the specification (the `complete` that enters
`test-strategy`). The specification is then read from the commit ShipLoop made for it, not from the working files.

  overlays                      no model: write the two overlays from the guide text in this checkout
  prepare ROOT [--allow-dirty]  no model: lay the base down, build the three arms, enforce that they differ as written
  sort JUDGE                    one sorter session (opus | astra): which checklist items apply to this base
  run ROOT SET DRIVER           launch one set (A, C and X together) on sol or sonnet; stop each at acceptance
  collect ROOT SET              no model: endings, what each author was shown, snapshots, counts; blind copies for the judges
  judge SET                     both judges on the set's blind copies
  score ROOT SET                no model: item-by-item differences between the arms
  replay DEST OUT [OUT ...]     no model: read existing run folders the way collect would, writing only under DEST
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import grade
import qualcheck
import run_choice

REQUEST = "Let admins upload a CSV to bulk-create users."
CASE = "csv-user-import"  # the bench case whose checklist grades the specification
BASE_CASE = "user-listing"  # its base, fixtures/node-base, is laid down by the harness's own brownfield.start
BUILD_ARM = "docs/experiments/sdlc-structure-20261119/build_arm.py"
OVERLAYS = HERE / "overlays"
LABELS = HERE / "labels"
ARMS = ("A", "C", "X")
ARM_OVERLAY = {"A": None, "C": "guides-cue.json", "X": "guides-excerpt.json"}
DRIVERS = {
    "sol": {
        "host": "codex",
        "model": "gpt-6.2-sol",
        "effort": "medium",
        "extra": [],
        "cell": "sol-medium",
    },
    "sonnet": {
        "host": "claude",
        "model": "claude-sonnet-5-5",
        "effort": "high",
        "extra": ["--max-budget-usd", "12"],
        "cell": "sonnet-high",
    },
}
GUIDES = REPO / "skills" / "shiploop" / "references"
SECTIONS = (
    ("behavioral-requirements.md", "## Behavior model"),
    ("requirements-definition.md", "## State and data change assessment"),
)
DUTY_ONE = (
    "1. Read KNOWLEDGE/spec.md whole, the research and discovery results; reopen the selected baseline in Discovery's `evidence_refs`\n"
    "   (Current-system baseline guide)."
)
CUE = "1. Before you write, work out the behaviour model and the state and data changes for this request.\n   "
DUTY_LAST = (
    "12. A complete spec establishes acceptance lines, not implementation or test success. `evidence_refs`: KNOWLEDGE/spec.md, each\n"
    "    requirement section and source used."
)
EXCERPT_MARK = "GUIDE TEXT for duty 1's behaviour model and state and data changes"
END_MARK = "=== end ShipLoop print ==="
RANK = {"absent": 0, "partial": 1, "covered": 2}
HERE_LABELS = ("applies", "capability", "unclear")
SORT_PROMPT = """You are sorting the items of a fixed checklist. You judge; you change nothing but the one file named at the end.

In your working directory: `request.txt`, one sentence asking for a change to an existing program; `base/`, that program
as it is before the change (read all of it: it is small); and `items.json`, a list of items. Each item names something a
written specification for the request might settle. You are shown no specification and need none.

Give every item one label, `here`, by this rule, which comes from the owner of the delivery tooling these
specifications are written for. Engineering rigour (tests against the real runtime, correct deployment steps, quotas,
failure routing and ownership, data retention, security checks, marked assumptions) is the expected standard even for
a small request. Product capability the request does not need (features, stores, services, sign-in, channels the user
sees or the product runs) is overbuilding.
- "applies": a correct and safe version of what the sentence asks for, built into this program as it is, has to settle
  the item. It is the requested behaviour's own conduct, its boundaries and errors, who may use it, what of the existing
  program must be preserved, or rigour in the rule's sense. A specification that left it unsettled would leave the
  requested thing wrong or unsafe to build here.
- "capability": the item is about a product capability that this program does not have and the sentence does not ask
  for (mail, sign-in, background jobs, another screen, and the like). A specification may leave it out and say so;
  building it would be overbuilding.
- "unclear": the sentence and the program do not let you tell.

Judge against this program and this sentence only. Do not ask whether the item would be good to have: ask what the
rule says it is.

Write `verdict.json` in your working directory, and nothing else:
{"labels": [{"id": "<item id>", "here": "applies|capability|unclear", "why": "<one line>"}, ...]}
One entry for every item, in the order given.
"""
LAY_BASE = (
    "import sys; sys.path.insert(0, 'test/shiploop_e2e'); import brownfield, run; from pathlib import Path; "
    "work = Path(sys.argv[1]); work.mkdir(parents=True); "
    "print(__import__('json').dumps(brownfield.start(work, run.catalog()[sys.argv[2]])))"
)
RENDER = "import sys; sys.path.insert(0, sys.argv[1]); import shiploop_prompts as p; sys.stdout.write(p.prompt('spec'))"


def sh(argv: list[str], cwd: Path) -> str:
    done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(
            f"failed ({done.returncode}): {' '.join(str(a) for a in argv[:5])} ...\n{done.stderr[-800:]}"
        )
    return done.stdout


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else ""


# ------------------------------------------------------------------ the two overlays


def section(file: str, heading: str) -> str:
    lines = (GUIDES / file).read_text().splitlines()
    start = next(n for n, line in enumerate(lines) if line.strip() == heading)
    end = next(
        (n for n in range(start + 1, len(lines)) if lines[n].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).rstrip()


def overlay_docs() -> dict[str, dict]:
    excerpt = "\n\n".join(section(file, heading) for file, heading in SECTIONS)
    if '"""' in excerpt or "\\" in excerpt or excerpt.endswith('"'):
        raise SystemExit(
            "the guide text cannot sit inside the duties' string literal as it is"
        )
    edit = {"module": "shiploop_prompts.py", "constant": "DUTIES", "key": "spec"}
    cue = {**edit, "old": DUTY_ONE, "new": CUE + DUTY_ONE[3:]}
    block = (
        f"\n\n{EXCERPT_MARK} (the sections this packet lists as Behavior-model\n"
        "guidance and State and data assessment, unchanged):\n\n" + excerpt
    )
    tail = {**edit, "old": DUTY_LAST, "new": DUTY_LAST + block}
    return {
        "guides-cue.json": {
            "about": "Spec-elaboration journal section 40, arm C of the guides test: one cue sentence at the head of the "
            "spec stage's first duty. It names two things to work out and delivers no guide text. For an experiment "
            "only; not a proposed change to ShipLoop.",
            "edits": [cue],
        },
        "guides-excerpt.json": {
            "about": "Spec-elaboration journal section 40, arm X of the guides test: arm C's cue sentence, and after the "
            "stage's last duty the unchanged text of two guide sections (behavioral-requirements.md '## Behavior "
            "model' and requirements-definition.md '## State and data change assessment'). For an experiment only; "
            "not a proposed change to ShipLoop.",
            "edits": [cue, tail],
        },
    }


def cmd_overlays() -> int:
    OVERLAYS.mkdir(exist_ok=True)
    for name, doc in overlay_docs().items():
        (OVERLAYS / name).write_text(json.dumps(doc, indent=1) + "\n")
        added = sum(
            len(edit["new"].split()) - len(edit["old"].split()) for edit in doc["edits"]
        )
        chars = sum(len(edit["new"]) - len(edit["old"]) for edit in doc["edits"])
        print(
            f"{name}: {len(doc['edits'])} edit(s), {added} words and {chars} characters added"
        )
    return 0


# ------------------------------------------------------------------ prepare


def cmd_prepare(root: Path, allow_dirty: bool) -> int:
    dirty = sh(["git", "status", "--short"], REPO).splitlines()
    if dirty and not allow_dirty:
        raise SystemExit(
            f"the checkout is not clean ({len(dirty)} paths): build from a clean detached worktree"
        )
    for name, doc in overlay_docs().items():
        if json.loads((OVERLAYS / name).read_text()) != doc:
            raise SystemExit(
                f"overlays/{name} does not match the guide text in this checkout: run `overlays` and commit"
            )
    root.mkdir(parents=True, exist_ok=True)
    base = json.loads(
        sh(
            [sys.executable, "-c", LAY_BASE, str(root / "prior" / "work"), BASE_CASE],
            REPO,
        )
    )
    plugins, prompts = {}, {}
    for arm in ARMS:
        argv = [sys.executable, BUILD_ARM, str(root / f"arm-{arm}")]
        argv += [str(OVERLAYS / ARM_OVERLAY[arm])] if ARM_OVERLAY[arm] else []
        plugins[arm] = sh(argv, REPO).strip().splitlines()[-1]
        scripts = Path(plugins[arm]) / "skills" / "shiploop" / "scripts"
        prompts[arm] = sh([sys.executable, "-c", RENDER, str(scripts)], REPO)
    problems = []
    for arm in ("C", "X"):
        expected = prompts["A"]
        for edit in overlay_docs()[ARM_OVERLAY[arm]]["edits"]:
            if expected.count(edit["old"]) != 1:
                problems.append(
                    f"arm {arm}: an edit's anchor is not in the rendered spec stage exactly once"
                )
            expected = expected.replace(edit["old"], edit["new"])
        differing = subprocess.run(
            ["diff", "-rq", "-x", "__pycache__", plugins["A"], plugins[arm]],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()
        if len(differing) != 1 or "shiploop_prompts.py" not in differing[0]:
            problems.append(
                f"arm {arm} differs from A in {len(differing)} files, not in shiploop_prompts.py alone"
            )
        if prompts[arm] != expected:
            problems.append(
                f"arm {arm}'s rendered spec stage is not A's with the overlay's edits and nothing else"
            )
    deltas = {}
    for arm in ("C", "X"):
        diff = difflib.unified_diff(
            prompts["A"].splitlines(), prompts[arm].splitlines(), lineterm="", n=0
        )
        deltas[arm] = sum(
            1 for line in diff if line[:1] in "+-" and line[:3] not in ("+++", "---")
        )
    record = {
        "checkout": str(REPO),
        "head": sh(["git", "rev-parse", "HEAD"], REPO).strip(),
        "checkout_status_lines": len(dirty),
        "base": base,
        "plugins": plugins,
        "spec_prompt_sha256": {
            arm: hashlib.sha256(text.encode()).hexdigest()[:12]
            for arm, text in prompts.items()
        },
        "spec_prompt_characters": {arm: len(text) for arm, text in prompts.items()},
        "delta_lines": deltas,
        "problems": problems,
    }
    (root / "prepare.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 1 if problems else 0


# ------------------------------------------------------------------ reading a run


def chosen_run(out: Path) -> Path | None:
    """The run the harness itself would grade for this output folder, or None while there is none or a tie."""
    try:
        choice = run_choice.choose(out)
    except Exception:  # noqa: BLE001  a folder that is still being written can be unreadable for a moment
        return None
    return Path(choice.chosen["run_dir"]) if choice.chosen else None


def trace(run: Path | None) -> list[dict]:
    try:
        return qualcheck.rows(run / "trace.jsonl") if run else []
    except (OSError, ValueError):
        return []


def completes(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("kind") == "command"
        and row.get("verb") == "complete"
        and row.get("exit") == 0
        and isinstance(row.get("stage"), list)
    ]


def acceptance(rows: list[dict]) -> dict | None:
    """The accepted `complete` that enters test-strategy: the specification is accepted at this row."""
    return next(
        (row for row in completes(rows) if row["stage"][1] == "test-strategy"), None
    )


def submission(rows: list[dict]) -> dict | None:
    """The author's last `complete` that leaves spec before the acceptance (with no review, the acceptance itself)."""
    accepted = acceptance(rows)
    before = [
        row
        for row in completes(rows)
        if row["stage"][0] == "spec"
        and (accepted is None or row["ts"] <= accepted["ts"])
    ]
    return before[-1] if before else None


def snapshot(out: Path, dest: Path) -> dict:
    """What cannot move after the stop: the accepted specification from its commit, the submitted one from the bind tree."""
    run = chosen_run(out)
    rows = trace(run)
    accepted, submitted = acceptance(rows), submission(rows)
    record = {
        "run_dir": str(run) if run else None,
        "accepted_at": (accepted or {}).get("at"),
        "spec_action": (submitted or {}).get("action"),
    }
    if not (run and accepted):
        return record
    tree = run.parent / "worktree"
    commit = git(tree, "log", "-1", "--format=%H", "--", "docs/shiploop/spec.md")
    record["spec_commit"] = commit or None
    record["spec_commit_subject"] = (
        git(tree, "log", "-1", "--format=%s", commit) if commit else None
    )
    record["test_strategy_completed"] = any(
        row["stage"][0] == "test-strategy" for row in completes(rows)
    )
    record["spec_edited_after_its_commit"] = bool(
        git(tree, "status", "--porcelain", "--", "docs/shiploop/spec.md")
    )
    if commit:
        (dest / "spec-accepted.md").write_text(
            git(tree, "show", f"{commit}:docs/shiploop/spec.md") + "\n"
        )
    if submitted:
        bind = run / "improve" / f"{submitted['action']}-bind.md"
        found = (
            re.search(r'"tree": "([0-9a-f]{40})"', bind.read_text(errors="replace"))
            if bind.is_file()
            else None
        )
        record["reviewed"] = bind.is_file()
        if found:
            (dest / "spec-submitted.md").write_text(
                git(tree, "show", f"{found.group(1)}:docs/shiploop/spec.md") + "\n"
            )
        inbox = run / "inbox" / f"{submitted['action']}.md"
        if inbox.is_file():
            shutil.copyfile(inbox, dest / "spec-submission-result.md")
    upstream = dest / "upstream"
    upstream.mkdir(exist_ok=True)
    for row in completes(rows):
        result = run / "results" / f"{row.get('action')}.md"
        if row["stage"][0] in ("intake", "discovery", "research") and result.is_file():
            shutil.copyfile(result, upstream / f"{row['stage'][0]}.md")
    return record


def calls(out: Path) -> list[dict]:
    """Every tool call of the session with its result, in order: Codex's normalised rows or Claude's stream."""
    order, by_id = [], {}
    for n, event in enumerate(qualcheck.rows(out / "events.jsonl")):
        kind = event.get("type")
        if kind == "tool_call":
            by_id[event.get("toolCallId")] = {
                "at": n,
                "input": json.dumps(event.get("rawInput"), ensure_ascii=False),
                "result": "",
            }
            order.append(by_id[event.get("toolCallId")])
        elif kind == "tool_call_update" and event.get("toolCallId") in by_id:
            parts = [c for c in event.get("content") or [] if isinstance(c, dict)]
            texts = [
                str((part.get("content") or {}).get("text") or "") for part in parts
            ]
            by_id[event["toolCallId"]]["result"] += "\n".join(texts) or json.dumps(
                event.get("rawOutput"), ensure_ascii=False
            )
        elif kind == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    by_id[block.get("id")] = {
                        "at": n,
                        "input": json.dumps(block.get("input"), ensure_ascii=False),
                        "result": "",
                    }
                    order.append(by_id[block.get("id")])
        elif kind == "user":
            content = (event.get("message") or {}).get("content")
            for block in content if isinstance(content, list) else []:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_result"
                    and block.get("tool_use_id") in by_id
                ):
                    inner = block.get("content")
                    parts = (
                        [inner]
                        if isinstance(inner, str)
                        else [
                            str(x.get("text") or "")
                            for x in inner or []
                            if isinstance(x, dict)
                        ]
                    )
                    by_id[block["tool_use_id"]]["result"] += "\n".join(parts)
    return order


def exposure(out: Path) -> dict:
    """What the specification's author was shown: the spec packet as received, and guide files read with their text."""
    order = calls(out)
    packet = next(
        (
            n
            for n, call in enumerate(order)
            if "ShipLoop navigator | spec | revision" in call["result"]
        ),
        None,
    )
    later = re.compile(r"ShipLoop navigator \| (improve|test-strategy) \|")
    after = next(
        (
            n
            for n, call in enumerate(order)
            if packet is not None and n > packet and later.search(call["result"])
        ),
        None,
    )
    text = order[packet]["result"] if packet is not None else ""
    record = {
        "spec_packet_received": packet is not None,
        "spec_packet_whole": END_MARK in text,
        "spec_packet_characters": len(text),
        "spec_packet_has_cue": CUE.strip()[3:] in text,
        "spec_packet_has_guide_text": EXCERPT_MARK in text
        and all(heading in text for _, heading in SECTIONS),
        "submission_found": after is not None,
    }
    reads = {
        "before the spec packet": set(),
        "while writing the spec": set(),
        "after the submission": set(),
    }
    own = {}
    for file, _ in SECTIONS:
        own[file] = [
            line.strip()
            for line in (GUIDES / file).read_text().splitlines()
            if line.startswith("#")
        ]
    for n, call in enumerate(order):
        for file, found in own.items():
            # a read counts when the call names the file and its result returns one of that file's own headings
            if file in call["input"] and any(
                heading in call["result"] for heading in found
            ):
                if packet is None or n <= packet:
                    reads["before the spec packet"].add(file)
                elif after is None or n <= after:
                    reads["while writing the spec"].add(file)
                else:
                    reads["after the submission"].add(file)
    record["guide_files_read"] = {when: sorted(files) for when, files in reads.items()}
    return record


def measures(text: str) -> dict:
    return {
        "words": len(text.split()),
        "requirement_ids": len(set(re.findall(r"\bR-[0-9]+\b", text))),
    }


def ending(result: dict, reached: bool) -> str:
    if not result:
        return "harness failure"
    process, termination = result.get("process") or {}, result.get("termination") or {}
    if "max_budget" in str(process.get("stop")):
        return "capped"
    if result.get("outcome_class") == "BLOCKED":
        return "blocked"
    if process.get("status") == "timeout":
        return "harness timeout"
    if str(termination.get("resume_stop") or "").startswith("stopped by"):
        return "stopped at acceptance" if reached else "stopped at the time limit"
    return "ended by itself"


def read_sample(out: Path, dest: Path | None = None) -> dict:
    dest = dest or out  # this test's own samples keep their copies beside the run
    result = (
        json.loads((out / "result.json").read_text())
        if (out / "result.json").is_file()
        else {}
    )
    metrics = (
        json.loads((out / "metrics.json").read_text())
        if (out / "metrics.json").is_file()
        else {}
    )
    snap = snapshot(out, dest)
    planning = {
        row.get("stage"): row
        for row in (metrics.get("planning") or {}).get("stages") or []
    }
    spec = planning.get("spec") or {}
    usable = bool(
        snap.get("spec_commit")
        and snap.get("accepted_at")
        and not snap.get("test_strategy_completed")
    )
    seconds, review = spec.get("seconds"), spec.get("improve_seconds") or 0
    submitted = dest / "spec-submitted.md"
    return {
        "ending": ending(result, bool(snap.get("accepted_at"))),
        "usable": usable,
        **snap,
        "start_head": (result.get("follow_on") or {}).get("start_head"),
        "case_recorded": result.get("case"),
        "exposure": exposure(out) if (out / "events.jsonl").is_file() else None,
        "accepted": measures((dest / "spec-accepted.md").read_text())
        if usable
        else None,
        "submitted": measures(submitted.read_text()) if submitted.is_file() else None,
        "spec_seconds": seconds,
        "spec_review_seconds": spec.get("improve_seconds"),
        "spec_author_seconds": round(seconds - review, 1)
        if seconds is not None
        else None,
        "turns": metrics.get("turns"),
        "tokens": metrics.get("tokens"),
        "cost_usd": metrics.get("cost_usd"),
        "refusals": sum(
            1 for row in trace(Path(snap["run_dir"])) if row.get("exit") == 2
        )
        if snap.get("run_dir")
        else None,
    }


# ------------------------------------------------------------------ launching one set


def cmd_run(root: Path, set_name: str, driver: str, limit: float) -> int:
    ready = json.loads((root / "prepare.json").read_text())
    if ready["checkout"] != str(REPO) or ready["problems"]:
        raise SystemExit(
            "prepare.json is of another checkout, or records problems: prepare again"
        )
    chosen = DRIVERS[driver]
    (root / "samples").mkdir(exist_ok=True)
    turn = int(re.sub(r"\D", "", set_name) or 0) % len(ARMS)
    live = []
    for arm in (
        ARMS[turn:] + ARMS[:turn]
    ):  # the arm that launches first rotates with the set
        name = f"{set_name}-{driver}-{arm}"
        out = root / "samples" / name
        argv = [
            sys.executable,
            "test/shiploop_e2e/run.py",
            "--prompt",
            REQUEST,
            "--continue-from",
            str(root / "prior"),
        ]
        argv += [
            "--host",
            chosen["host"],
            "--model",
            chosen["model"],
            "--effort",
            chosen["effort"],
        ]
        argv += [
            "--source",
            "checkout",
            "--plugin-dir",
            ready["plugins"][arm],
            "--output",
            str(out),
        ]
        argv += [
            "--baseline",
            str(root / "baselines.jsonl"),
            "--quiet",
            *chosen["extra"],
        ]
        log = (root / "samples" / f"{name}.log").open("w")
        process = subprocess.Popen(argv, cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        sample = {
            "name": name,
            "set": set_name,
            "arm": arm,
            "driver": driver,
            "out": out,
            "process": process,
            "pid": process.pid,
        }
        sample.update(
            started=time.time(),
            stopped=None,
            reached=False,
            why=None,
            stop_written=False,
        )
        live.append(sample)
    while any(s["stopped"] is None for s in live):
        for s in live:
            if s["stopped"] is not None:
                continue
            reached = (
                acceptance(trace(chosen_run(s["out"]))) is not None
                if s["out"].is_dir()
                else False
            )
            over = time.time() - s["started"] > limit * 60
            ended = s["process"].poll() is not None
            if reached or over or ended:
                s.update(stopped=time.time(), reached=reached)
                s["why"] = (
                    "accepted"
                    if reached
                    else "run ended by itself"
                    if ended
                    else "time limit"
                )
                if not ended and s["out"].is_dir():
                    (s["out"] / "stop").write_text(f"guides test: {s['why']}\n")
                    s["stop_written"] = True
        time.sleep(1)
    failed = 0
    for s in live:
        try:
            s["process"].wait(timeout=600)
        except subprocess.TimeoutExpired:
            s["why"] += "; run.py still running ten minutes after the stop"
            failed += 1
        row = {
            key: s[key]
            for key in (
                "name",
                "set",
                "arm",
                "driver",
                "pid",
                "reached",
                "why",
                "stop_written",
            )
        }
        row.update(
            minutes=round((s["stopped"] - s["started"]) / 60, 1),
            returncode=s["process"].poll(),
        )
        (root / "samples" / f"{s['name']}.sample.json").write_text(
            json.dumps(row) + "\n"
        )
        print(json.dumps(row))
    return 1 if failed else 0


# ------------------------------------------------------------------ collecting, blind copies, judging, scoring


def round_of(set_name: str) -> str:
    return f"round-g{re.sub(r'[^0-9a-z]', '', set_name.lower())}"


def cmd_collect(root: Path, set_name: str) -> int:
    samples = sorted((root / "samples").glob(f"{set_name}-*.sample.json"))
    if not samples:
        raise SystemExit(f"no samples of set {set_name} under {root / 'samples'}")
    blind = root / f"blind-{set_name}.json"
    if blind.is_file():
        raise SystemExit(f"{blind.name} exists: this set already has blind copies")
    records = []
    for path in samples:
        sample = json.loads(path.read_text())
        if sample.get("returncode") is None:
            raise SystemExit(
                f"{sample['name']}: run.py has not exited; nothing is collected from a live run"
            )
        records.append({**sample, **read_sample(root / "samples" / sample["name"])})
    (root / f"collect-{set_name}.json").write_text(json.dumps(records, indent=1) + "\n")
    for record in records:
        print(
            json.dumps({key: value for key, value in record.items() if key != "tokens"})
        )
    usable = [record for record in records if record["usable"]]
    codes = [f"K{n}" for n in range(1, len(usable) + 1)]
    random.SystemRandom().shuffle(codes)
    mapping = {}
    for record, code in zip(usable, codes, strict=True):
        slot = (
            HERE
            / "results"
            / round_of(set_name)
            / f"{CASE}__{code}__{DRIVERS[record['driver']]['cell']}"
        )
        if slot.exists():
            raise SystemExit(f"{slot} exists: a slot is written once")
        slot.mkdir(parents=True)
        shutil.copyfile(
            root / "samples" / record["name"] / "spec-accepted.md", slot / "spec.md"
        )
        (slot / "meta.json").write_text(
            json.dumps({"case": CASE, "set": set_name, "code": code}, indent=1) + "\n"
        )
        mapping[code] = {
            "arm": record["arm"],
            "sample": record["name"],
            "driver": record["driver"],
        }
    blind.write_text(json.dumps(mapping, indent=1) + "\n")
    print(
        f"{len(usable)} of {len(records)} samples usable; blind copies in results/{round_of(set_name)}"
    )
    return 0


def cmd_judge(set_name: str, timeout: int) -> int:
    case = grade.cases()[CASE]
    slots = sorted(
        p
        for p in (HERE / "results" / round_of(set_name)).iterdir()
        if (p / "spec.md").is_file()
    )
    for judge_name, tag in (("opus", None), ("astra", "gpt")):
        for slot in slots:
            grade.judge_one(round_of(set_name), slot, case, timeout, tag, judge_name)
    wanted = [n["id"] for n in case["nuances"]]
    problems = 0
    for tag in (None, "gpt"):
        for slot in slots:
            kept = grade.grades_dir(round_of(set_name), tag) / f"{slot.name}.json"
            states = (
                {
                    v["id"]: v.get("state")
                    for v in json.loads(kept.read_text())["verdicts"]
                }
                if kept.is_file()
                else {}
            )
            missing = [i for i in wanted if states.get(i) not in RANK]
            problems += bool(missing)
            print(
                f"{'astra' if tag else 'opus'} {slot.name}: {len(wanted) - len(missing)} of {len(wanted)} items judged",
                missing or "",
            )
    return 1 if problems else 0


def here_sets() -> dict[str, list[str]]:
    sorts = []
    for name in ("opus", "astra"):
        sorts.append(
            {
                row["id"]: row["here"]
                for row in json.loads((LABELS / f"here-{name}.json").read_text())[
                    "labels"
                ]
            }
        )
    ids = list(sorts[0])
    return {
        "applies": [i for i in ids if all(s.get(i) == "applies" for s in sorts)],
        "capability": [i for i in ids if all(s.get(i) == "capability" for s in sorts)],
        "split": [
            i
            for i in ids
            if not all(s.get(i) == sorts[0].get(i) for s in sorts)
            or sorts[0].get(i) == "unclear"
        ],
    }


def cmd_score(root: Path, set_name: str) -> int:
    mapping = json.loads((root / f"blind-{set_name}.json").read_text())
    sets = here_sets()
    states = {}
    for code, info in mapping.items():
        slot = f"{CASE}__{code}__{DRIVERS[info['driver']]['cell']}"
        both = []
        for tag in (None, "gpt"):
            kept = grade.grades_dir(round_of(set_name), tag) / f"{slot}.json"
            both.append(
                {
                    v["id"]: RANK[v["state"]]
                    for v in json.loads(kept.read_text())["verdicts"]
                }
            )
        states[info["arm"]] = both
    print(
        f"set {set_name}: arms read {sorted(states)}; items that apply here (both sorters): {sets['applies']}"
    )
    for arm, both in sorted(states.items()):
        for which, judge in enumerate(("opus", "astra")):
            row = [both[which][i] for i in sets["applies"]]
            print(
                f"  {arm} {judge}: covered {row.count(2)}, partly {row.count(1)}, absent {row.count(0)}"
            )
    for high, low in (("X", "C"), ("C", "A"), ("X", "A")):
        if high not in states or low not in states:
            continue
        up = [
            i
            for i in sets["applies"]
            if all(states[high][j][i] > states[low][j][i] for j in (0, 1))
        ]
        down = [
            i
            for i in sets["applies"]
            if all(states[high][j][i] < states[low][j][i] for j in (0, 1))
        ]
        new = [i for i in up if all(states[low][j][i] == 0 for j in (0, 1))]
        print(
            f"  {high} over {low}: higher under both judges {up} (newly raised {new}); lower {down}; net {len(up) - len(down)}"
        )
    return 0


def cmd_sort(judge_name: str, timeout: int) -> int:
    out = LABELS / f"here-{judge_name}.json"
    if out.is_file():
        raise SystemExit(f"{out.name} exists: the sort is done once")
    judge = grade.JUDGES[judge_name]
    case = grade.cases()[CASE]
    wanted = [n["id"] for n in case["nuances"]]
    cwd = grade.WORK / "labels" / f"here-{judge_name}-{uuid.uuid4().hex[:6]}"
    cwd.mkdir(parents=True)
    (cwd / "request.txt").write_text(REQUEST + "\n")
    shutil.copytree(
        REPO / "test" / "shiploop_e2e" / "fixtures" / "node-base", cwd / "base"
    )
    items = [{"id": n["id"], "item": n["nuance"]} for n in case["nuances"]]
    (cwd / "items.json").write_text(json.dumps(items, indent=1) + "\n")
    rc, cost = grade.run_session(SORT_PROMPT, cwd, judge, timeout)
    labels, problem = grade.read_verdict(cwd, "labels")
    if rc != 0 or labels is None:
        raise SystemExit(
            f"FAIL sort {judge_name}: rc={rc} {problem or ''}  (session folder {cwd})"
        )
    seen = {}
    for entry in labels:
        if isinstance(entry, dict) and "id" in entry:
            entry["here"] = str(entry.get("here") or "").strip().lower()
            seen[entry["id"]] = entry
    missing = [i for i in wanted if i not in seen or seen[i]["here"] not in HERE_LABELS]
    if missing:
        raise SystemExit(
            f"FAIL sort {judge_name}: no usable label for {missing}  (session folder {cwd})"
        )
    record = {
        "judge": judge["model"],
        "judge_effort": judge["effort"],
        "cost_usd": cost,
        "prompt_sha256": hashlib.sha256(SORT_PROMPT.encode()).hexdigest(),
        "request": REQUEST,
        "base": "test/shiploop_e2e/fixtures/node-base",
        "labels": [seen[i] for i in wanted],
    }
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(
        f"DONE sort {judge_name}:",
        {
            label: sum(1 for i in wanted if seen[i]["here"] == label)
            for label in HERE_LABELS
        },
    )
    return 0


def cmd_replay(dest: Path, outs: list[Path]) -> int:
    for out in outs:
        copy = dest / out.name
        copy.mkdir(parents=True, exist_ok=True)
        record = read_sample(
            out, copy
        )  # reads the run where it is; writes only under dest
        print(
            json.dumps(
                {key: value for key, value in record.items() if key != "tokens"},
                indent=1,
            )
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "command",
        choices=(
            "overlays",
            "prepare",
            "sort",
            "run",
            "collect",
            "judge",
            "score",
            "replay",
        ),
    )
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--limit", type=float, default=20.0)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    rest = args.rest
    if args.command == "overlays":
        return cmd_overlays()
    if args.command == "prepare":
        return cmd_prepare(Path(rest[0]).resolve(), args.allow_dirty)
    if args.command == "sort":
        return cmd_sort(rest[0], args.timeout)
    if args.command == "run":
        return cmd_run(Path(rest[0]).resolve(), rest[1], rest[2], args.limit)
    if args.command == "collect":
        return cmd_collect(Path(rest[0]).resolve(), rest[1])
    if args.command == "judge":
        return cmd_judge(rest[0], args.timeout)
    if args.command == "score":
        return cmd_score(Path(rest[0]).resolve(), rest[1])
    return cmd_replay(
        Path(rest[0]).resolve(), [Path(path).resolve() for path in rest[1:]]
    )


if __name__ == "__main__":
    sys.exit(main())
