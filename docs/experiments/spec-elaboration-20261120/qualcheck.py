#!/usr/bin/env python3
"""Sample check for the qualification evaluation registered in journal section 32.

Reads one finished ShipLoop E2E run folder and the checkout it was built from, and prints the values the
evaluation's checks rest on, each taken from the run's own files. It only reads, and it grades nothing: the
harness's verdicts are printed as recorded.

usage: qualcheck.py RUN_DIR CHECKOUT
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

CARD_SENTENCE = "Run options are the user's to set"
PID_RULE = "Record the PID of a background process"
VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
# A command word that stops a process; "skill" in a plugin path must not match.
STOP_WORD = re.compile(r"(?<![A-Za-z_])(pkill|killall|fuser|kill)(?![A-Za-z_])")
BACKGROUND = re.compile(
    r"(?<![&|>])&\s*(\\n|\"|$)|nohup|\$!|disown|setsid|run_in_background\W+true"
)
RUN_OPTION = re.compile(r"--(planning-review|delegation|lint)\b")
CHANGED_TEXT = re.compile(
    r"planning-review|delegation|--lint|\bPID\b|pkill|killall|behavioral-requirements|requirements guide"
    r"|Requirements definition",
    re.IGNORECASE,
)
# A host tool that ends a background shell or task, as opposed to a shell command that does.
HOST_STOP = re.compile(r"(?<![A-Za-z])kill|stop", re.IGNORECASE)
# Looking for processes by name or by port, which is not a stop unless its result is fed to one.
LOOK_WORD = re.compile(r"(?<![A-Za-z_])(pgrep|lsof)(?![A-Za-z_])")
# A shell `kill` whose target is a number, a variable or a command substitution (the text is JSON, so a quote is escaped).
SHELL_STOP_BY_ID = re.compile(
    r"(?<![A-Za-z_.])kill\s+(?:-\w+\s+)?(?:\\?\"?\$[({A-Za-z_][^;|&]{0,40}|[0-9]+)"
)
REFERENCE = re.compile(r"skills/shiploop/references/([A-Za-z0-9_.-]+\.md)")
GUIDE_SENTENCE = "Store the proposed product behavior in"
# A shell job sent to the background: an `&` that is not `&&`, a redirection or part of `2>&1`. The call's text is
# JSON, so a newline is the two characters backslash and n; a heredoc's body is text written to a file, not a start.
HEREDOC = re.compile(r"<<-?\s*(?:\\?[\"'])?(\w+)(?:\\?[\"'])?.*?\\n\1\b", re.DOTALL)
SHELL_JOB = re.compile(r"(?<![&>|<\d\\])&(?![&>\d])")
START = re.compile(r"workspace start|shiploop['\"]? init\b")


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def builder_calls(events: list[dict]) -> list[tuple[int, str, str]]:
    """Each command, edit or other tool call the builder made: event index, tool name, the call as text.

    Codex events arrive normalised by the harness as `tool_call` rows; Claude's stream keeps each call as a
    `tool_use` block inside an `assistant` event, a subagent's calls included.
    """
    calls = []
    for n, event in enumerate(events):
        if event.get("type") == "tool_call":
            calls.append(
                (n, str(event.get("toolName")), json.dumps(event, ensure_ascii=False))
            )
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append(
                        (
                            n,
                            str(block.get("name")),
                            json.dumps(block, ensure_ascii=False),
                        )
                    )
    return calls


def tree_differences(left: Path, right: Path) -> int:
    done = subprocess.run(
        ["diff", "-rq", str(left), str(right)],
        capture_output=True,
        text=True,
        check=False,
    )
    return len(done.stdout.splitlines())


def main() -> int:
    run, checkout = Path(sys.argv[1]), Path(sys.argv[2])
    result = json.loads((run / "result.json").read_text())
    invocation = json.loads((run / "invocation.json").read_text())

    print(f"run {run.name}")
    print(
        "A1 checkout HEAD",
        git(checkout, "rev-parse", "HEAD"),
        "| tree",
        git(checkout, "rev-parse", "HEAD^{tree}"),
    )
    print(
        "A1 checkout status lines", len(git(checkout, "status", "--short").splitlines())
    )
    print(
        "A1 recorded versions", json.dumps(invocation.get("versions"), sort_keys=True)
    )
    plugin = invocation.get("plugin") or result.get("plugin") or {}
    built = (
        Path(plugin.get("wanted") or invocation["plugin_dir"]) / "skills" / "shiploop"
    )
    print(
        "A1 built skill against the checkout's: differing entries",
        tree_differences(built, checkout / "skills/shiploop"),
    )
    if not plugin.get("path"):
        print(
            "A2 the session loaded the built plugin itself; no installed copy:",
            plugin.get("loaded"),
        )
        card = built / "SKILL.md"
    elif (installed := Path(plugin["path"]) / "skills" / "shiploop").is_dir():
        print(
            "A2 installed skill against the built one: differing entries",
            tree_differences(installed, built),
        )
        card = installed / "SKILL.md"
    else:
        print(
            "A2 no installed copy at the recorded path; the built one is read:",
            plugin["path"],
        )
        card = built / "SKILL.md"
    lines = [
        f"{n}:{text}"
        for n, text in enumerate(card.read_text().splitlines(), 1)
        if CARD_SENTENCE in text
    ]
    print("A2 card sentence", lines)
    events = rows(run / "events.jsonl")
    with_rule = [
        n
        for n, event in enumerate(events)
        if PID_RULE in json.dumps(event, ensure_ascii=False)
    ]
    print(
        "A2 events carrying the PID rule",
        len(with_rule),
        "of",
        len(events),
        "| first",
        with_rule[:1],
    )
    print(
        "A3 host",
        invocation.get("host"),
        "|",
        invocation.get("host_build"),
        "| model",
        invocation.get("model"),
    )
    print("A3 effort", invocation.get("effort"), "| case", invocation.get("case"))
    process = result.get("process") or {}
    print(
        "A3 sessions",
        len(process.get("sessions") or []),
        "| resumes",
        process.get("resumes"),
    )
    cases = json.loads((checkout / "test/shiploop_e2e/cases.json").read_text())
    request = cases[invocation["case"]]["prompt"]
    given = (run / "prompt.txt").read_text()
    print(
        "A3 request equals the catalog's",
        given.rstrip("\n") == request,
        "| characters",
        len(request),
    )

    print(
        "B1 pass",
        result.get("pass"),
        "|",
        result.get("outcome_class"),
        "|",
        result.get("outcome_basis"),
    )
    for name in VERDICTS:
        verdict = result.get(name) or {}
        extra = {
            key: verdict[key]
            for key in ("status", "returncode", "stop")
            if key in verdict
        }
        print("B1 verdict", name, verdict.get("pass"), extra or "")
    checks = result.get("checks") or []
    print(
        "B2 case checks",
        sum(1 for check in checks if check.get("pass")),
        "of",
        len(checks),
    )
    acceptance = (result.get("quality") or {}).get("acceptance")
    if acceptance:
        passed, declared = acceptance.get("passed") or [], acceptance.get("ids") or []
        print(
            "B2 held-out acceptance",
            len(passed),
            "of",
            len(declared),
            "| not passed",
            sorted(set(declared) - set(passed)),
        )
    else:
        print("B2 held-out acceptance: none recorded for this case")
    committed = result.get("committed") or {}
    product = run / "work"
    print(
        "B3 recorded head",
        committed.get("head"),
        "| recorded uncommitted",
        committed.get("uncommitted"),
    )
    print(
        "B3 product HEAD",
        git(product, "rev-parse", "HEAD"),
        "| status lines",
        len(git(product, "status", "--short").splitlines()),
    )

    print(
        "C1 option recorded by the harness at launch (invocation.planning_review)",
        invocation.get("planning_review"),
    )
    for state in sorted(run.glob(".shiploop-runs/*/run/state.md")):
        found = [
            line.strip()
            for line in state.read_text().splitlines()
            if '"planning_review"' in line
        ]
        print("C1 state.md", found)
    metrics = json.loads((run / "metrics.json").read_text())
    reviews = metrics.get("improve_reviews") or {}
    stages = sorted(
        str(child.get("child")).rsplit("-", 1)[0]
        for child in reviews.get("per_child") or []
    )
    print(
        "C1 Improve reviews",
        reviews.get("children"),
        "| edited",
        reviews.get("edited_children"),
        "|",
        stages,
    )
    named = builder_calls(events)
    calls = [(n, text) for n, _, text in named]
    print("C2 commands and edits the builder made", len(calls))
    tools = sorted({name for _, name, _ in named})
    print(
        "C2 tools called",
        {tool: sum(1 for _, name, _ in named if name == tool) for tool in tools},
    )
    inside = sum(
        1
        for event in events
        if event.get("type") == "assistant" and event.get("parent_tool_use_id")
    )
    print("C2 events from inside a subagent, included in the scan", inside)
    host_stops = [(n, name, text) for n, name, text in named if HOST_STOP.search(name)]
    print(
        "C2 stops through a host tool",
        [(n, name, text[:160]) for n, name, text in host_stops],
    )
    starts = [(n, text) for n, text in calls if START.search(text)]
    if starts:
        n, text = starts[0]
        print(
            "C1 first start call: event",
            n,
            "| run option flags in it",
            sorted(set(RUN_OPTION.findall(text))),
        )
    print(
        "C1 calls passing a run option flag",
        [n for n, text in calls if RUN_OPTION.search(text)],
    )
    stops = [(n, text) for n, text in calls if STOP_WORD.search(text)]
    print("C2 calls with kill, pkill, killall or fuser as a word", len(stops))
    for n, text in stops:
        for match in STOP_WORD.finditer(text):
            around = text[max(0, match.start() - 90) : match.end() + 90].replace(
                "\\n", " "
            )
            print(f"C2   event {n}: …{around}…")
    print(
        "C2 calls that look like a background start",
        [n for n, text in calls if BACKGROUND.search(text)],
    )
    looks = [(n, text) for n, text in calls if LOOK_WORD.search(text)]
    print(
        "C2 calls that search processes by name or port (pgrep, lsof)",
        [n for n, _ in looks],
    )
    for n, text in looks:
        for match in LOOK_WORD.finditer(text):
            around = text[max(0, match.start() - 90) : match.end() + 90].replace(
                "\\n", " "
            )
            print(f"C2   event {n}: …{around}…")
    by_id = [
        (n, match.group(0))
        for n, text in calls
        for match in SHELL_STOP_BY_ID.finditer(text)
    ]
    print("C2 shell stops that name a number, a variable or a file", by_id)
    print("C2 calls that record $!", [n for n, text in calls if "$!" in text])
    jobs = [
        (n, "$!" in HEREDOC.sub(" ", text))
        for n, text in calls
        if SHELL_JOB.search(HEREDOC.sub(" ", text))
    ]
    print(
        "C2 calls that start a shell job in the background, heredoc bodies left out (event, records $!)",
        jobs,
    )
    print("C2 left behind", json.dumps(result.get("left_behind"), sort_keys=True))
    references = sorted({name for _, text in calls for name in REFERENCE.findall(text)})
    print("C3 reference files named in the builder's calls", references)
    with_sentence = sum(
        1 for event in events if GUIDE_SENTENCE in json.dumps(event, ensure_ascii=False)
    )
    print(
        "C3 events carrying the requirements guide's corrected sentence", with_sentence
    )
    spec = product / "docs/shiploop/spec.md"
    if spec.is_file():
        ids = sorted(
            set(re.findall(r"\bR-[0-9]+\b", spec.read_text())),
            key=lambda name: int(name[2:]),
        )
        print(
            "C3 spec",
            spec.relative_to(product),
            spec.stat().st_size,
            "bytes | requirement ids",
            len(ids),
            ids[:3],
            "…",
        )
        print(
            "C3 added by",
            git(
                product,
                "log",
                "--diff-filter=A",
                "--format=%h %ad %s",
                "--date=iso",
                "--",
                str(spec.relative_to(product)),
            ),
        )
    else:
        print("C3 no spec at docs/shiploop/spec.md")
    refusals = [
        row
        for trace in sorted(run.glob(".shiploop-runs/*/run/trace.jsonl"))
        for row in rows(trace)
        if row.get("exit") == 2
    ]
    named = [row for row in refusals if CHANGED_TEXT.search(str(row.get("error")))]
    print(
        "C4 refused ShipLoop commands",
        len(refusals),
        "| naming the changed text",
        len(named),
    )
    for row in refusals:
        stage = row.get("stage")
        print(
            "C4  ",
            stage[0] if isinstance(stage, list) else stage,
            "|",
            row.get("verb"),
            "|",
            " ".join(str(row.get("error")).split())[:150],
        )
    print(
        "D elapsed seconds",
        process.get("elapsed_seconds"),
        "| returncode",
        process.get("returncode"),
        "| stop",
        process.get("stop"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
