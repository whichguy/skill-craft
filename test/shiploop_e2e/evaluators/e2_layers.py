#!/usr/bin/env python3
"""E2: is a missing lower-layer (component or unit) harness recorded as prerequisite work, and are UI criteria executed?

    python3 test/shiploop_e2e/evaluators/e2_layers.py score <sample>
    python3 test/shiploop_e2e/evaluators/e2_layers.py verify

From the records only: the test-strategy result's summary and the knowledge files it wrote
(docs/shiploop/environment.md and architecture.md in the final tree), and the step-plan result.
- ``prerequisite``: a line names a component, unit or DOM harness (or a surfaces row for that layer) together with
  "prerequisite" (or "prepare builds" / "install"), so some stage will build it.
- ``deferred_ui``: a line says no browser (or the UI) is blocked, unverified, deferred or N/A, and no prerequisite line
  exists: the whole UI was decided at once.
- ``inspected_ui``: UI criteria (they name a component, render, click, button, html, aria, display or shows) confirmed
  by inspection with no reason cited (``inspected because`` / ``reason``).
- ``source_search_checks``: step checks and check commands that only search source text: grep, test -f / -e, or a
  script whose every command line is one of those.
``value`` is 1 when prerequisite is recorded, no UI criterion is inspection-only without a reason and no check is a
source search; else 0. ``verify``: run 4's own test-strategy and W3 step-plan are flagged (value 0, deferred_ui and a
source-search check); a planted good record scores 1.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

_LAYER = re.compile(r"\b(component|unit|dom|jsdom|happy-dom|element)\b[^.\n]{0,80}\b(harness|test|layer|runner)", re.I)
_PREREQ = re.compile(r"prerequisite|prepare (builds|installs)|must be (built|installed)|install(s|ed)? (a |the )?\w*\s*harness", re.I)
_DEFERRED = re.compile(r"(no browser|browser tool|\bui\b)[^.\n]{0,120}\b(blocked|unverified|deferred|n/a|not verified)", re.I)
_UI = re.compile(r"\b(component|render\w*|click\w*|button|html|aria|display\w*|shows?|status line|ui)\b", re.I)
_INSPECT = re.compile(r"\b(inspect\w*|inspection)\b", re.I)
_EXEC = re.compile(r"\b(exercised|executed|confirm: executed)\b", re.I)
_REASON = re.compile(r"(inspected because|reason[:=])", re.I)
_SEARCH = re.compile(r"(^|[\s;&|(!])(grep|rg|awk|sed|find|test|\[|ls|stat)(\s|$)", re.M)
# A command or script line that runs code (a runner, a package script, an interpreter or a deploy) is not a source search.
_RUNNER = re.compile(r"(^|[\s;&|(])(node|npm|npx|yarn|pnpm|python3?|pytest|jest|vitest|mocha|deno|bun|java|mvn|gradle|go|"
                     r"cargo|ruby|curl|playwright|make|deploy)(\s|$)", re.M)


def _searches_only(text: str) -> bool:
    return bool(_SEARCH.search(text)) and not _RUNNER.search(text)


def source_search(command: str, tree: Path | None) -> bool:
    """Whether ``command`` only searches source text: each of its parts (split on && ; ||) starts with a search (grep,
    test -f, find...) or a print, or runs a shell script of the tree that runs no code and searches."""
    parts = [p.strip().lstrip("!( ").strip() for p in re.split(r"&&|\|\||;", command) if p.strip()]
    if not parts:
        return False
    for part in parts:
        words = part.split()
        if len(words) == 2 and words[0] in ("sh", "bash") and tree is not None and (tree / words[1]).is_file():
            if not _searches_only((tree / words[1]).read_text()):
                return False
        elif not (words and words[0] in ("grep", "rg", "awk", "sed", "find", "test", "[", "ls", "stat", "printf", "echo")):
            return False
    return True


def judge(strategy_text: str, step_plan: dict | None, tree: Path | None) -> dict:
    lines = strategy_text.splitlines() or [strategy_text]
    prerequisite = any(_LAYER.search(line) and _PREREQ.search(line) for line in lines)
    deferred = (not prerequisite) and any(_DEFERRED.search(line) for line in lines)
    criteria = (step_plan or {}).get("criteria") or []
    ui = [c for c in criteria if _UI.search(c.get("text", ""))]
    inspected = [c["id"] for c in ui if _INSPECT.search(c.get("text", "")) and not _EXEC.search(c.get("text", ""))
                 and not _REASON.search(c.get("text", ""))]
    commands = [s.get("check", "") for s in (step_plan or {}).get("steps") or []]
    commands += [c.get("command", "") for c in (step_plan or {}).get("test_commands") or []]
    searches = sorted({c for c in commands if c and source_search(c, tree)})
    value = int(prerequisite and not inspected and not searches) if step_plan is not None else None
    return {"value": value, "prerequisite": prerequisite, "deferred_ui": deferred, "ui_criteria": len(ui),
            "inspected_ui": inspected, "source_search_checks": searches}


def _strategy_text(folder: Path | None, tree: Path | None) -> str:
    rows = common.results(folder, "test-strategy")
    text = "\n".join((r.get("result") or {}).get("summary", "") for r in rows)
    for name in ("environment.md", "architecture.md"):
        path = (tree / "docs" / "shiploop" / name) if tree else None
        if path and path.is_file():
            text += "\n" + path.read_text()
    return text


def score(sample: Path) -> dict:
    folder, tree = common.run_dir(sample), common.worktree(sample)
    plans = common.results(folder, "step-plan")
    return judge(_strategy_text(folder, tree), (plans[-1].get("result") if plans else None), tree)


GOOD_STRATEGY = ("| layer | harness | state |\n| component | none installed; a DOM test harness is prerequisite work: prepare "
                 "installs it before W1 | prerequisite |\n")
GOOD_PLAN = {"criteria": [{"id": "C1", "text": "Clicking an option marks it pressed. Confirm: executed - TC-1 runs the "
                                               "component in the DOM harness; pass when aria-pressed is true."}],
             "steps": [{"id": "S1", "check": "node --test --test-reporter=spec test/choice.test.js"}],
             "test_commands": [{"command": "node --test --test-reporter=spec test/choice.test.js", "suite": "focused"}]}


def verify() -> list[dict]:
    rows = []
    strategy = common.read_block(common.RUN4 / "run" / "results" / f"{common.RUN4_TEST_STRATEGY}.md")
    plan = common.read_block(common.RUN4 / "run" / "results" / f"{common.RUN4_STEP_PLAN}.md")
    if strategy is None or plan is None:
        rows.append({"record": "run 4", "ok": False, "why": f"run 4's records are not readable under {common.RUN4}"})
    else:
        tree = common.RUN4 / "worktree"
        text = strategy["result"]["summary"]
        for name in ("environment.md", "architecture.md"):
            if (tree / "docs" / "shiploop" / name).is_file():
                text += "\n" + (tree / "docs" / "shiploop" / name).read_text()
        found = judge(text, plan["result"], tree)
        rows.append({"record": "run 4 test-strategy + W3 step-plan", "expect": "flagged", "got": found,
                     "ok": found["value"] == 0 and found["deferred_ui"] and bool(found["source_search_checks"])})
    found = judge(GOOD_STRATEGY, GOOD_PLAN, None)
    rows.append({"record": "planted good", "expect": "value 1", "got": found, "ok": found["value"] == 1})
    return rows


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
