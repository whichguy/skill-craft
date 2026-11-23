#!/usr/bin/env python3
"""Prove read_samples.py on hand-made samples: no model, no network. Run with a TMPDIR of its own; it keeps nothing but its output.

    python3 prove_reader.py [--keep DIR]      # exit 0 when every sample reads as expected; prints the reader's lines for each

Every sample is a real build of a scenario (stage_build.build) whose spec, product or result was then written by hand, with the files a
live sample leaves (seed-export, export, invocation.json, sessions.jsonl, drive.json) and stage_live's own grade. Two routes:
- ``gates``: the result goes through the real commands, as the packet prints them (until loop, ``check``, done, ``complete``), so the
  trace rows and the acceptance are ShipLoop's. It also shows that a right amendment is acceptable in this scenario;
- ``apply``: the result is recorded by navigator.apply (what the harness's own fake host does), for outputs the real gates would refuse;
  its trace rows are written by hand.

Then the normative measure alone on single sentences, and the reader broken one part at a time: every break must be noticed.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE), str(ROOT / "test/shiploop_e2e/stage_suite"), str(ROOT / "test/shiploop_e2e"),
                str(ROOT / "skills/shiploop/scripts")]
import read_samples as reader  # noqa: E402
import stage_build as sb  # noqa: E402
import stage_live  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402

CASE = reader.CASE
RN, T_SCENARIO, P_SCENARIO = CASE["requirement"], CASE["requirement_scenario"], CASE["proof_scenario"]
ENV = {**os.environ, "SHIPLOOP_PROGRESS": "off", "SHIPLOOP_KEEPALIVE": "off", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
       "PYTHONDONTWRITEBYTECODE": "1"}
LOOP = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
EXACT = "`<author> commented on <ticket> (no preview).`"
NEW_LINE = (f"- The message delivered for a comment has exactly the body {EXACT} and holds none of the comment's content. Confirm by a "
            "worker delivery test that reads the delivered body.")
WHY = ("Source: docs/operations.md (Notifications). Step-plan revised this clause because the relay shows every message on the lobby wall "
       "display, where visitors read it.")


def revised(line: str = NEW_LINE, why: str = WHY):
    """The right rewrite: the changed line replaced, the source and reason added after the siblings."""
    def edit(text: str) -> str:
        last = CASE["siblings"][-1]
        return text.replace(CASE["changed_line"], line).replace(last, last + "\n- " + why)
    return edit


def both(*edits):
    def edit(text: str) -> str:
        for one in edits:
            text = one(text)
        return text
    return edit


def swap(old: str, new: str):
    def edit(text: str) -> str:
        assert text.count(old) == 1, old
        return text.replace(old, new)
    return edit


def amended(previous: dict, *, text: str | None = None, summary: str | None = None) -> dict:
    """The amended plan a right answer submits: the done row marked, S2's criterion and Proof for the new meaning."""
    plan = copy.deepcopy(previous)
    plan["steps"][0]["done"] = True
    body = text or (f"{RN} the message delivered for a comment has exactly the body {EXACT} and none of the comment's content, and its "
                    "subject begins with the ticket ID. Confirm by: TC_Comments_Notify; pass when the delivered body equals "
                    "`guest commented on T-0001 (no preview).`.")
    for row in plan["criteria"]:
        if row["id"] == "C3":
            row["text"] = body
    for step in plan["steps"]:
        if step["criteria"] == ["C3"]:
            step["proof"] = step["proof"].replace(
                "a.match(m.body,/hello/);a.match(m.body,/a/);", "a.equal(m.body,'\"'\"'a commented on T-0001 (no preview).'\"'\"');")
    plan["summary"] = summary or (f"Revised {RN}: a notified agent reads who commented on which ticket and none of the comment's text, "
                                  "because the relay shows every message on the lobby wall display. S2 is replanned for it; S1 and S3 are "
                                  "carried over.")
    return plan


def repaired(previous: dict) -> dict:
    plan = copy.deepcopy(previous)
    plan["steps"][0]["done"] = True
    plan["steps"][1]["proof"] = plan["steps"][1]["proof"].replace(CASE["api_proof"]["from"], CASE["api_proof"]["to"])
    plan["summary"] = "S2's Proof is quoted right; every other row is carried over."
    return plan


def cli(built, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(built.cli), *args], capture_output=True, text=True, env=ENV, input=stdin or "",
                          timeout=180, check=False)


def through_gates(built, results: list[dict]) -> None:
    """Submit ``results`` in order by the packet's own commands; the last one is completed, the ones before it are checked and refused."""
    run_dir, action = built.run_dir, built.seeded["action"]
    assert cli(built, "next", f"--run-dir={run_dir}").returncode == 0
    loops = run_dir / "loops"
    receipt = loops / f"{action}-terminal.json"
    started = subprocess.run([sys.executable, "-B", str(LOOP), "start", "--receipt", str(receipt), "--directory", str(loops)],
                             input=(loops / f"{action}-contract.json").read_text(), capture_output=True, text=True, env=ENV, timeout=60,
                             check=True)
    done_argv = json.loads(started.stdout)["done_argv"]
    inbox = run_dir / "inbox" / f"{action}.md"
    inbox.parent.mkdir(exist_ok=True)
    for index, result in enumerate(results):
        result = {**result, "evidence_refs": [str(receipt)]}
        inbox.write_text("```shiploop-state\n" + json.dumps(result, indent=1) + "\n```\n")
        checked = cli(built, "check", f"--run-dir={run_dir}", f"--action={action}")
        if index < len(results) - 1:
            assert checked.returncode == 2, "expected a refusal, got " + checked.stdout[-400:] + checked.stderr[-400:]
            continue
        assert checked.returncode == 0, checked.stderr[-1500:]
    report = {"classification": "trivial", "exit_assessment": "satisfied", "continuation_assessment": "blocked",
              "evidence": "The check says yes; the amended plan and the spec entry read back.", "handoff": "Submit the callback."}
    ended = subprocess.run(done_argv, input=json.dumps(report), capture_output=True, text=True, env=ENV, timeout=60, check=False)
    assert ended.returncode == 0, ended.stdout[-800:] + ended.stderr[-800:]
    completed = cli(built, "complete", f"--run-dir={run_dir}", f"--action={action}")
    assert completed.returncode == 0, completed.stderr[-1500:]


def through_apply(built, result: dict, calls: list[tuple]) -> None:
    run_dir, action = built.run_dir, built.seeded["action"]
    state = store.read_record(run_dir / "state.md")
    with contextlib.redirect_stdout(io.StringIO()):
        navigator.save(run_dir, navigator.apply(state, action, result))
    with (run_dir / "trace.jsonl").open("a") as handle:
        for verb, code, error in calls:
            row = {"v": 1, "kind": "command", "verb": verb, "action": action, "exit": code, "stage": ["step-plan", "step-plan"]}
            handle.write(json.dumps({**row, "error": error} if code else row) + "\n")


def build(sc, out: Path):
    """stage_build.build, again when the fixture's own suite (expectation E2, test/api.test.js) failed or hung while the seed ran it: an
    old flake of the product's tests, seen twice in about 320 builds (README, "Noted")."""
    for attempt in range(3):
        try:
            out.mkdir(parents=True)
            return sb.build(sc, out)
        except SystemExit as error:
            if attempt == 2 or "the run is at validate-existing" not in str(error.code):
                raise
            print("(seed build repeated: " + " ".join(str(error.code).split())[:120] + ")", flush=True)
            shutil.rmtree(out)


def make(root: Path, number: int, name: str, scenario: str, *, spec=None, plan=None, product=None, route="apply", calls=None, ref=None,
         first=None, result=None) -> Path:
    sc = sb.load("step-plan/" + scenario, HERE / "stage_cases")
    out = root / "step-plan" / scenario / str(number)
    built = build(sc, out)
    stage_live.snapshot(built.worktree, out / "seed-export")
    (out / stage_live.INVOCATION).write_text(json.dumps({
        "scenario": sc.id, "stage": sc.stage, "sample": number, "host": "hand-made", "backend": None, "model": name, "effort": "medium",
        "versions": {"shiploop_version": "hand-made", "plugin_sha256": "hand-made"}, "ref": ref, "overlay": None, "seeded": built.seeded,
        "action_id": built.seeded["action"]}) + "\n")
    previous = sc.data["seed_route"][0]["result"]
    if spec is not None:
        path = built.worktree / reader.SPEC
        path.write_text(spec(path.read_text()))
    for path, text in (product or {}).items():
        (built.worktree / path).write_text(text)
    submitted = result or (plan or amended)(previous)
    if route == "gates":
        through_gates(built, [*(first(previous) if first else []), submitted])
    else:
        through_apply(built, submitted, calls or [("check", 0, None), ("complete", 0, None)])
    now = time.time()
    (out / "sessions.jsonl").write_text(
        json.dumps({"row": "start", "n": 1, "kind": "first", "reason": "stage", "host": "hand-made", "model": name, "t": now - 90, "events_line": 0}) + "\n"
        + json.dumps({"row": "end", "n": 1, "t": now, "events_line": 0, "status": "interrupted", "returncode": -9, "engine": None}) + "\n")
    (out / "drive.json").write_text(json.dumps({"resumes": 0, "resume_stop": None, "settles": [], "abandoned": False}) + "\n")
    stage_live.snapshot(built.worktree, out / "export")
    stage_live.grade_sample(sc, out, regraded=False)
    return out


def drop_mark(previous: dict) -> list[dict]:
    plan = amended(previous)
    plan["steps"][0].pop("done")
    return [plan]


def on_done_step(previous: dict) -> dict:
    plan = amended(previous, text="R-9 the message names author and ticket. Confirm by: TC_Comments_Notify; pass when it does.")
    plan["criteria"].append({"id": "C9", "confirm": "executed", "text": f"{RN} exact body {EXACT}. Confirm by: TC_Comments_Store; pass when equal."})
    plan["steps"][0]["criteria"] = ["C1", "C9"]
    next(row for row in plan["test_commands"] if row["suite"] == "focused")["criteria"].append("C9")
    return plan


BLOCKED = {"outcome": "blocked", "summary": "R-9 must change and step-plan may not write spec.md; the owner decides.",
           "headline": "R-9 needs the owner", "evidence_refs": [],
           "awaiting": {"kind": "answer", "question": "May R-9 change as the send-back says?",
                        "no_default": "The requirement is the requester's."}}
PARAPHRASE = ("- The message delivered for a comment tells the agent who commented and on which ticket, and never any of the comment's own words. "
              "Confirm by a worker delivery test that reads the delivered body.")
R3_OLD = "unassignment and no-op produce none."
SUBJECT, RETRY = CASE["siblings"]


def samples() -> list[tuple]:
    """(name, scenario, keyword arguments of make, expected: verdict, {measure: value}, text every STOP needs or None)."""
    norm, gone = "normative clause states the new meaning", "old clause gone"
    crit = "criterion of a step not done states it"
    return [
        ("right, through the real gates", T_SCENARIO, dict(spec=revised(), route="gates"), "met", {}, None),
        ("right, after a fix-forward refusal on the first check (real gates)", T_SCENARIO, dict(spec=revised(), route="gates", first=drop_mark),
         "met", {"fix_forward_first": "no"}, None),
        ("right, built from the released ref: cell C", T_SCENARIO, dict(spec=revised(), ref=CASE["released_ref"]), "met", {"cell": "C"}, None),
        ("first check refused by another gate", T_SCENARIO,
         dict(spec=revised(), calls=[("check", 2, "test_commands has a check row, so drop check_na"), ("check", 0, None), ("complete", 0, None)]),
         "met", {"fix_forward_first": "read"}, None),
        ("leaves the spec alone", T_SCENARIO, dict(), "not met", {norm: "no", gone: "no", "entry gives a source": "no"}, None),
        ("changes a second R-n", T_SCENARIO, dict(spec=both(revised(), swap(R3_OLD, "unassignment produces none."))), "not met",
         {"every other R-n byte-identical": "no", norm: "yes"}, "another requirement changed: R-3"),
        ("keeps the old clause beside the new one", T_SCENARIO, dict(spec=revised(CASE["changed_line"] + "\n" + NEW_LINE)), "not met",
         {gone: "no", norm: "yes"}, None),
        ("drops the ID", T_SCENARIO, dict(spec=swap(CASE["heading"], "### Comment notification message")), "not met",
         {"ID kept": "no", "no R-n added, removed or retired": "no"}, "a requirement removed: R-9"),
        ("moves R-9 under Retired", T_SCENARIO,
         dict(spec=lambda text: text.replace("## Non-functional", "## Retired by this run\n\n" + CASE["heading"] + "\nReplaced.\n\n## Non-functional")
              .replace(CASE["heading"] + "\n" + CASE["basis_line"], "### Old R9 text\n" + CASE["basis_line"])), "not met", {"ID kept": "no"},
         "a requirement retired: R-9"),
        ("adds R-10 instead", T_SCENARIO,
         dict(spec=swap("\n## Non-functional requirements", "\n### R-10 Comment message body\n" + NEW_LINE + "\n\n## Non-functional requirements")),
         "not met", {"no R-n added, removed or retired": "no", norm: "no"}, "a requirement added: R-10"),
        ("weakens a sibling clause", T_SCENARIO, dict(spec=both(revised(), swap(RETRY, "- A message that cannot be delivered is dropped."))),
         "not met", {"sibling clauses byte-identical": "no", norm: "yes"}, "a sibling clause changed"),
        ("a valid paraphrase without the exact token", T_SCENARIO, dict(
            spec=revised(PARAPHRASE), plan=lambda p: amended(p, text="R-9 the delivered message names author and ticket and holds no word of the "
                                                             "comment. Confirm by: TC_Comments_Notify; pass when the body holds none of it.")),
         "read", {norm: "read", gone: "yes", crit: "read"}, None),
        ("the token only in the reason, the clause a paraphrase of the OLD meaning", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment shows who wrote it and what they wrote. Confirm by a worker delivery test.",
                         "Step-plan revised this entry because the send-back asks for the body " + EXACT + " (docs/operations.md, wall display).")),
         "not met", {norm: "no"}, None),
        ("the token only in the reason, the old clause kept", T_SCENARIO, dict(
            spec=swap(SUBJECT, SUBJECT + "\n- Revised by step-plan: the send-back says the body must be " + EXACT + ", see docs/operations.md.")),
         "not met", {norm: "no", gone: "no"}, None),
        ("the token only after 'because' in a normative sentence", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment shows who wrote it, because the send-back wanted the body " + EXACT + ".")),
         "not met", {norm: "no"}, None),
        ("the token only in the Basis sentence", T_SCENARIO, dict(
            spec=both(revised("- The message delivered for a comment shows who wrote it and what they wrote. Confirm by a worker delivery test."),
                      swap(CASE["basis_line"], CASE["basis_line"].replace("and CONTRIBUTING.md.", "CONTRIBUTING.md; docs/operations.md; the text " + EXACT)))),
         "not met", {norm: "no"}, None),
        ("the right clause in an R-1 style paragraph after its Basis", T_SCENARIO, dict(
            spec=both(revised(), swap("\n" + CASE["basis_line"], "\nBasis: request S6; docs/operations.md (Notifications). The delivered body is exactly " + EXACT
                                      + " and holds nothing else."))), "met", {norm: "yes"}, None),
        ("the token in the Basis line as what the send-back asks for", T_SCENARIO, dict(
            spec=both(revised("- The message delivered for a comment shows who wrote it and what they wrote. Confirm by a worker delivery test."),
                      swap(CASE["basis_line"], CASE["basis_line"].replace("Pending", "docs/operations.md; the send-back asks for " + EXACT + " Pending")))),
         "not met", {norm: "no"}, None),
        ("a wrapped reason whose second line holds the token", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment shows who wrote it, because the send-back from implement wants the body\n  to be "
                         + EXACT + " on the wall display.")),
         "not met", {norm: "no"}, None),
        ("the right clause wrapped over two lines", T_SCENARIO, dict(
            spec=revised(NEW_LINE.replace(" commented on <ticket>", " commented on\n  <ticket>"))), "met", {norm: "yes"}, None),
        ("the right clause with its reason in a parenthesis of the same sentence", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment has exactly the body " + EXACT + " and holds none of the comment's content (step-plan "
                         "revised this because the relay shows messages on the wall display: docs/operations.md). Confirm by a worker delivery test.",
                         "Source: docs/operations.md.")),
         "met", {norm: "yes"}, None),
        ("the right clause with its reason after a dash", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment has exactly the body " + EXACT + " — revised by step-plan because visitors read the "
                         "wall display (docs/operations.md). Confirm by a worker delivery test.")),
         "met", {norm: "yes"}, None),
        ("the right clause with its reason first", T_SCENARIO, dict(
            spec=revised("- Because the relay shows every message on the lobby wall display, the body delivered for a comment is exactly " + EXACT
                         + " Confirm by a worker delivery test.", "Source: docs/operations.md.")),
         "met", {norm: "yes"}, None),
        ("the right clause opened with 'Revised by step-plan:'", T_SCENARIO, dict(
            spec=revised("- Revised by step-plan: the body delivered for a comment is exactly " + EXACT + " Confirm by a worker delivery test.")),
         "read", {norm: "read", gone: "yes"}, None),
        ("the new text negated", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment shows what was written and must not be " + EXACT + ". Confirm by a test.")),
         "not met", {norm: "no"}, None),
        ("the new text stated after an unrelated 'not'", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment does not quote it and is exactly " + EXACT + ". Confirm by a test.")),
         "met", {norm: "yes"}, None),
        ("the new text only in the Confirm sentence", T_SCENARIO, dict(
            spec=revised("- The message delivered for a comment names its author and ticket and nothing else. Confirm by a test that reads " + EXACT + ".")),
         "read", {norm: "read"}, None),
        ("the old clause quoted only in the reason", T_SCENARIO, dict(
            spec=revised(why="Source: docs/operations.md. Step-plan revised \"" + CASE["old_clause"] + "\" because visitors read the wall display.")),
         "read", {gone: "read", norm: "yes"}, None),
        ("no reason and no source in the entry", T_SCENARIO, dict(spec=swap(CASE["changed_line"], NEW_LINE)), "read",
         {"entry gives a source": "read", "entry gives a reason": "read"}, None),
        ("summary does not begin Revised R-9, follows drops it", T_SCENARIO, dict(
            spec=revised(), plan=lambda p: {**amended(p, summary="S2 is replanned; R-9 was revised."), "follows": ["R-8", "AD-4"]}),
         "not met", {"summary begins 'Revised R-9'": "no", "follows names it": "no"}, None),
        ("the criterion stays the old one", T_SCENARIO, dict(
            spec=revised(), plan=lambda p: {**amended(p), "criteria": copy.deepcopy(p["criteria"])}), "not met", {crit: "no"}, None),
        ("the new meaning only on the done step's criterion", T_SCENARIO, dict(spec=revised(), plan=on_done_step), "not met", {crit: "no"}, None),
        ("a product file changed", T_SCENARIO, dict(spec=revised(), product={"src/templates.js": "'use strict';\n"}), "not met",
         {"no product file changed": "no"}, None),
        ("blocked", T_SCENARIO, dict(result=BLOCKED, calls=[("complete", 0, None)]), "not met", {"accepted": "no", norm: "no"}, None),
        ("P: the Proof repaired, the spec alone (real gates)", P_SCENARIO, dict(plan=repaired, route="gates"), "met", {"cell": "P"}, None),
        ("P: the Proof as recorded", P_SCENARIO, dict(plan=lambda p: {**repaired(p), "steps": [{**p["steps"][0], "done": True}, *p["steps"][1:]]}),
         "not met", {"failing Proof repaired": "no"}, None),
        ("P: rewrites R-8 too", P_SCENARIO, dict(plan=repaired, spec=swap("timestamps may tie", "timestamps are unique")), "not met",
         {"spec byte-identical": "no"}, "spec.md was rewritten on a Proof-only send-back: R-8"),
    ]


SHOWS = "- The body shows the author."
# (label, the line in place of the clause to change, the Basis line or None, a line added to the entry or None, expected normative)
SENTENCES = [
    ("plain", f"- The message has the body {EXACT}", None, None, "yes"),
    ("must", f"- The message's body MUST be {EXACT} and hold none of the comment.", None, None, "yes"),
    ("a clause after ;", f"- For a comment the delivered body reads {EXACT}; it holds no comment text.", None, None, "yes"),
    ("quoted, not code", '- The delivered body is exactly "<author> commented on <ticket> (no preview)." and nothing else.', None, None, "yes"),
    ("no quoting", "- The delivered body is exactly <author> commented on <ticket> (no preview). It holds none of the content.", None, None, "yes"),
    ("reason first", f"- Because the relay shows it on the wall display, the body is exactly {EXACT}", None, None, "yes"),
    ("per docs", f"- The body is exactly {EXACT}, per docs/operations.md.", None, None, "yes"),
    ("wrapped over three lines", f"- The body is\n  exactly\n  {EXACT}", None, None, "yes"),
    ("a step's mark at the end", f"- The delivered body is exactly {EXACT} (W1/S2)", None, None, "yes"),
    ("the old meaning named in a parenthesis", f"- The body is exactly {EXACT} (revised: no longer the content).", None, None, "yes"),
    ("a Basis sentence", SHOWS, CASE["basis_line"].replace("Pending", f"The send-back asks for {EXACT} Pending"), None, "no"),
    ("because, with no rule after it", SHOWS, None, f"- Because the send-back asked for {EXACT}", "no"),
    ("step-plan revised this because", SHOWS, None, f"- Step-plan revised this because the send-back asks for {EXACT}", "no"),
    ("revised by step-plan: the send-back says", f"- Revised by step-plan: the send-back says the body must be {EXACT}", None, None, "no"),
    ("only in a parenthesis that names the source", f"- The body shows the author (source: the send-back, {EXACT})", None, None, "no"),
    ("instead of", f"- The body is the comment's text instead of {EXACT}", None, None, "no"),
    ("rather than", f"- The body carries the content rather than {EXACT}", None, None, "no"),
    ("revised by step-plan: the rule", f"- **Revised by step-plan (docs/operations.md):** the body is exactly {EXACT}, because visitors read it.", None, None, "read"),
    ("revised: was, now", SHOWS, None, f"Revised 2026-11-22 by step-plan: was content, now {EXACT}", "read"),
    ("a paraphrase", "- The body says who commented and on what, and quotes nothing.", None, None, "read"),
]


def sentence_cases() -> list[str]:
    start = "\n".join([CASE["heading"], CASE["basis_line"], CASE["changed_line"], *CASE["siblings"]])
    wrong = []
    for label, line, basis, extra, want in SENTENCES:
        entry = start.replace(CASE["changed_line"], line).replace(CASE["basis_line"], basis or CASE["basis_line"]) + ("\n" + extra if extra else "")
        found = reader.normative(start, entry)[0]
        print(f"  sentence '{label}': {found}" + ("" if found == want else f"  WRONG, expected {want}"))
        wrong += [label] if found != want else []
    return wrong


def broken_readers(root: Path) -> list[str]:
    """Break one part of the reader at a time, in memory, and read the kept samples and sentences again: each break must be noticed."""
    never = re.compile(r"(?!x)x")
    parts = [("a negation is not looked for", "NEGATED", never), ("any earlier 'not' is a negation", "NEGATED", re.compile(r"\bnot\b", re.I)),
             ("a reason's tail is kept", "REASON_TAIL", never), ("Basis and Source sentences count", "REASON_HEAD", never),
             ("'Revised ...' sentences count", "REVISED_HEAD", never), ("a leading Because is not cut", "BECAUSE_FIRST", never),
             ("Confirm sentences count", "CONFIRM", never), ("a reason in a parenthesis is kept", "REASON_WORD", never),
             ("fix-forward refusals are not known", "FIX_FORWARD", []), ("the old clause is not looked for", "old_clause", lambda text: ("yes", "")),
             ("files never differ", "changed_files", lambda sample: []), ("no sibling is named", "CASE", {**CASE, "siblings": []}),
             ("the released ref is another", "CASE", {**CASE, "released_ref": "zzz"}), ("wrapped lines are not joined", "blocks", str.splitlines)]
    unnoticed = []
    for label, name, value in parts:
        kept = getattr(reader, name)
        setattr(reader, name, value)
        try:
            noticed = [f"#{n}" for n, (_, scenario, _options, want, values, stop) in enumerate(samples(), 1)
                       if problems(reader.sample_row(root, root / "step-plan" / scenario / str(n)), want, values, stop)]
            with contextlib.redirect_stdout(io.StringIO()):
                noticed += [f"'{label_}'" for label_ in sentence_cases()]
        finally:
            setattr(reader, name, kept)
        print(f"  {label}: " + ("noticed by " + ", ".join(noticed) if noticed else "NOT NOTICED"))
        unnoticed += [] if noticed else [label]
    return unnoticed


def guard_cases(root: Path) -> list[str]:
    """The second guard: a retained file that no longer has its recorded sha256 is a STOP (a file of this proof stands in for one)."""
    sample = root / "step-plan" / P_SCENARIO / str(next(n for n, row in enumerate(samples(), 1) if row[1] == P_SCENARIO))
    kept, wrong = reader.CASE, []
    path = root / "retained-spec.md"
    path.write_text("as recorded\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        reader.CASE = {**kept, "old_run_files": {str(path): digest}}
        for text, want in (("as recorded\n", False), ("edited\n", True)):
            path.write_text(text)
            found = any("the retained run's files changed" in line for line in reader.sample_row(root, sample)["stop"])
            print(f"  retained file {text.strip()}: {'STOP' if found else 'no STOP'}" + ("" if found == want else "  WRONG"))
            wrong += [f"retained file {text.strip()}"] if found != want else []
    finally:
        reader.CASE = kept
    return wrong


def problems(row: dict, want: str, values: dict, stop: str | None) -> list[str]:
    found = {**row["measures"], "cell": row["cell"], "fix_forward_first": row["callbacks"]["fix_forward_first"]}
    wrong = [f"{key} is {found.get(key)}, expected {value}" for key, value in values.items() if found.get(key) != value]
    if row["verdict"] != want:
        wrong.append(f"verdict is {row['verdict']}, expected {want}")
    if bool(stop) != bool(row["stop"]) or (stop and not any(stop in line for line in row["stop"])):
        wrong.append(f"STOP is {row['stop']}, expected {stop}")
    return wrong


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=Path)
    args = parser.parse_args()
    failures = []
    with tempfile.TemporaryDirectory(prefix="spr-proof-") as temp:
        os.environ["XDG_STATE_HOME"] = ENV["XDG_STATE_HOME"] = str(Path(temp).resolve() / "state")
        root = args.keep or Path(temp).resolve() / "root"
        for number, (name, scenario, options, want, values, stop) in enumerate(samples(), 1):
            sample = make(root, number, name, scenario, **options)
            row = reader.sample_row(root, sample)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                reader.show(row)
            wrong = problems(row, want, values, stop)
            print(f"#{number} {name}: expected {want}" + (f", {values}" if values else "") + (f", STOP {stop}" if stop else "")
                  + " -> " + ("AS EXPECTED" if not wrong else "WRONG: " + "; ".join(wrong)))
            print("\n".join("    " + line for line in out.getvalue().replace(str(root), "<ROOT>").rstrip().splitlines()), flush=True)
            failures += [name] if wrong else []
        print("\nThe normative measure alone, on sentences:")
        failures += sentence_cases()
        print("\nThe retained run's guard:")
        failures += guard_cases(root)
        print("\nThe reader broken one part at a time:")
        unnoticed = broken_readers(root)
    total = len(samples()) + len(SENTENCES) + 2
    print(f"\n{total - len(failures)} of {total} as expected ({len(samples())} samples, {len(SENTENCES)} sentences, 2 guard cases)"
          + ("" if not failures else "; WRONG: " + "; ".join(failures))
          + ("; every break noticed" if not unnoticed else "; NOT NOTICED: " + "; ".join(unnoticed)))
    raise SystemExit(1 if failures or unnoticed else 0)


if __name__ == "__main__":
    main()
