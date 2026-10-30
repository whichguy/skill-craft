"""SG1 of docs/shiploop-sdlc-gates-proposal-2026-10-30.md §5: replay a proof-order check at step-plan on saved runs.

A step's Proof runs when the step's implement stage completes, before that step's test stage writes its tests. The
candidate check flags a step whose Proof names:
- rule A: a path in the ``test`` path class that does not exist yet, so only a test stage can write it later;
- rule B: a path that does not exist yet and that only a later step of the same plan declares in its ``paths``.

"Does not exist yet" is read from the step's base commit in the iteration ledger (``git`` mode) when the run's
worktree still holds it. Otherwise it is inferred from the plan alone: an ``absent`` expectation that no earlier step
declares in its ``paths``.

Live positives the bar names:
- DeepSeek W1, 2026-10-26 (test/shiploop_e2e/LEARNINGS.md:3652);
- Grok chess 5b's S3, if its Proof names a path only S4 declares (docs/shiploop-improve-schedule-proposal-2026-10-25.md:62).

The bar also asks that no step whose Proof passed at implement is flagged. Each row therefore lists the item's
implement outcomes after that step plan, so a W1-like send-back can be told from a false flag. Read-only: it changes
nothing.

    python3 -I sg1_proof_order.py <repo>/skills/shiploop/scripts [RUN_ROOT_GLOB ...]   # default ~/e2e-runs/2026*/*
    python3 -I sg1_proof_order.py <repo>/skills/shiploop/scripts --self-test
"""
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

PATHLIKE = re.compile(r"^[\w.@-][\w./@+-]*$")
EXTENSION = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")
SHELL_WORDS = {"&&", "||", "|", ";", ">", ">>", "<", "2>&1", "&"}


def proof_paths(proof: str) -> list[str]:
    """The repository-relative file paths a Proof command line names, best effort: options, words without a slash or
    an extension, absolute paths, URLs and code passed inline (``node -e "..."``) are skipped."""
    try:
        words = shlex.split(proof)
    except ValueError:
        words = proof.split()
    paths = []
    for word in words:
        if word in SHELL_WORDS or word.startswith("-") or "://" in word or word.startswith("/") or "=" in word:
            continue
        word = word.split("::", 1)[0]
        word = word[2:] if word.startswith("./") else word
        if PATHLIKE.match(word) and ("/" in word or EXTENSION.search(word)) and not word.endswith("/"):
            paths.append(word)
    return list(dict.fromkeys(paths))


def _paths(step: dict[str, Any]) -> set[str]:
    return {str(path) for path in step.get("paths") or () if isinstance(path, str)}


def check_plan(plan: dict[str, Any], classify: Callable[[str], str],
               exists_at: Optional[Callable[[str, str], Optional[bool]]] = None) -> dict[str, Any]:
    """The flags for one accepted step plan. ``exists_at(step_id, path)`` answers from the step's base commit, or None
    when it cannot tell; without an answer the check infers from the plan's expectations and the earlier steps' paths."""
    steps = [step for step in plan.get("steps") or () if isinstance(step, dict)]
    absent = {str(path) for row in plan.get("expectations") or () if isinstance(row, dict)
              and row.get("state") == "absent" for path in row.get("paths") or ()}
    flags: list[dict[str, Any]] = []
    judged = unjudged = 0
    for index, step in enumerate(steps):
        proof = step.get("proof")
        if not isinstance(proof, str) or not proof.strip():
            continue
        names = proof_paths(proof)
        if not names:
            unjudged += 1
            continue
        judged += 1
        earlier = {path for before in steps[:index] for path in _paths(before)}
        own = _paths(step)
        later = {path for after in steps[index + 1:] for path in _paths(after)}
        for path in names:
            answer = exists_at(str(step.get("id")), path) if exists_at else None
            if answer is None:
                mode, missing = "inferred", path in absent and path not in earlier
            else:
                mode, missing = "git", not answer
            if not missing:
                continue
            if classify(path) == "test":
                flags.append({"step": step.get("id"), "rule": "A", "path": path, "mode": mode, "proof": proof})
            elif path in later and path not in own | earlier:
                flags.append({"step": step.get("id"), "rule": "B", "path": path, "mode": mode, "proof": proof})
    return {"judged": judged, "unjudged": unjudged, "flags": flags}


def _git_exists(repo: Path) -> Callable[[Optional[str], str], Optional[bool]]:
    known: dict[str, bool] = {}

    def exists(base: Optional[str], path: str) -> Optional[bool]:
        if not base or not (repo / ".git").exists():
            return None
        if base not in known:
            known[base] = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", base + "^{commit}"],
                                         capture_output=True).returncode == 0
        if not known[base]:
            return None
        return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", base + ":" + path],
                              capture_output=True).returncode == 0
    return exists


def _bases(run: Path) -> dict[str, dict[str, str]]:
    """{step plan action: {step: base commit}} from the run's iteration ledgers (``iterations/<item>.json``)."""
    bases: dict[str, dict[str, str]] = {}
    for ledger in sorted(run.glob("iterations/*.json")):
        try:
            plans = json.loads(ledger.read_text(encoding="utf-8")).get("plans") or {}
        except (OSError, ValueError, AttributeError):
            continue
        for action, steps in plans.items():
            for step, row in (steps or {}).items():
                if isinstance(row, dict) and row.get("base"):
                    bases.setdefault(action, {})[step] = str(row["base"])
    return bases


def replay(scripts: Path, patterns: list[str]) -> dict[str, Any]:
    sys.path.insert(0, str(scripts))
    import shiploop_item_scope as scope  # noqa: E402 - ShipLoop's own path classes, from the checkout given
    import shiploop_store as store  # noqa: E402

    totals = {"runs": 0, "plans": 0, "judged": 0, "unjudged": 0, "flags": 0, "flags_before_send_back": 0}
    for pattern in patterns:
        for out in sorted(Path(match) for match in glob.glob(os.path.expanduser(pattern))):
            for run in sorted(out.glob(".shiploop-runs/*/run")):
                try:
                    state = store.read_record(run / "state.md")
                except Exception as exc:  # noqa: BLE001 - a saved run the current reader refuses is reported, not fatal
                    print(json.dumps({"run": str(out), "skipped": str(exc)[:120]}))
                    continue
                totals["runs"] += 1
                history = state.get("history") or []
                accepted = state.get("accepted") or {}
                bases = _bases(run)
                git = _git_exists(Path(str(state.get("repo") or "")))
                for index, row in enumerate(history):
                    plan = accepted.get(row.get("action"))
                    if row.get("stage") != "step-plan" or row.get("outcome") != "done" or not isinstance(plan, dict):
                        continue
                    steps = bases.get(row["action"], {})
                    result = check_plan(plan, scope.classify, lambda step, path: git(steps.get(step), path))
                    outcomes = []
                    for later in history[index + 1:]:
                        if later.get("workitem") != row.get("workitem"):
                            continue
                        if later.get("stage") == "step-plan":
                            break
                        if later.get("stage") == "implement":
                            outcomes.append(later.get("outcome"))
                    totals["plans"] += 1
                    totals["judged"] += result["judged"]
                    totals["unjudged"] += result["unjudged"]
                    totals["flags"] += len(result["flags"])
                    if result["flags"] and "send-back" in outcomes:
                        totals["flags_before_send_back"] += 1
                    print(json.dumps({"run": f"{out.parent.name}/{out.name}", "item": row.get("workitem"),
                                      "action": row["action"], **result, "implement_outcomes": outcomes}))
    print(json.dumps({"summary": totals}))
    return totals


def self_test(scripts: Path) -> None:
    sys.path.insert(0, str(scripts))
    import shiploop_item_scope as scope  # noqa: E402

    assert proof_paths("node --test test/game.test.js") == ["test/game.test.js"]
    assert proof_paths("python3 -m pytest tests/test_app.py::test_one -q") == ["tests/test_app.py"]
    assert proof_paths("npm test") == [] and proof_paths("node -e \"require('./src/a')\"") == []
    assert proof_paths("node scripts/deploy.js && node -e \"require('./src/pricing')\"") == ["scripts/deploy.js"]

    def plan(steps: list[dict[str, Any]], absent: list[str]) -> dict[str, Any]:
        return {"steps": steps, "expectations": [{"id": "E1", "state": "absent", "paths": absent}]}

    w1 = plan([{"id": "S1", "task": "game", "proof": "node --test test/game.test.js"}],
              ["src/game.js", "test/game.test.js"])
    assert [f["rule"] for f in check_plan(w1, scope.classify)["flags"]] == ["A"], "the W1 pattern is flagged"
    chess = plan([{"id": "S3", "task": "moves", "proof": "node scripts/castling-check.js", "paths": ["src/moves.js"]},
                  {"id": "S4", "task": "castling", "paths": ["src/castling.js", "scripts/castling-check.js"]}],
                 ["scripts/castling-check.js", "src/castling.js"])
    assert [f["rule"] for f in check_plan(chess, scope.classify)["flags"]] == ["B"], "a later step's path is flagged"
    later_step = plan([{"id": "S1", "task": "a", "paths": ["src/a.js", "test/a.test.js"], "proof": "node src/a.js"},
                       {"id": "S2", "task": "b", "proof": "node --test test/a.test.js"}],
                      ["src/a.js", "test/a.test.js"])
    assert check_plan(later_step, scope.classify)["flags"] == [], "an earlier step's test exists by S2's implement"
    existing = {"steps": [{"id": "S1", "task": "a", "proof": "node --test test/old.test.js"}],
                "expectations": [{"id": "E1", "state": "works", "paths": ["test/old.test.js"]}]}
    assert check_plan(existing, scope.classify)["flags"] == [], "a test that exists is not flagged"
    unjudged = check_plan(plan([{"id": "S1", "task": "a", "proof": "npm test"}], []), scope.classify)
    assert unjudged == {"judged": 0, "unjudged": 1, "flags": []}
    gitmode = check_plan(w1, scope.classify, lambda step, path: path != "test/game.test.js")
    assert [(f["rule"], f["mode"]) for f in gitmode["flags"]] == [("A", "git")]
    assert check_plan(w1, scope.classify, lambda step, path: True)["flags"] == [], "git says it exists: no flag"
    print("sg1 self-test: 7 cases pass")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    SCRIPTS = Path(sys.argv[1]).resolve()
    if sys.argv[2:] == ["--self-test"]:
        self_test(SCRIPTS)
    else:
        replay(SCRIPTS, sys.argv[2:] or ["~/e2e-runs/2026*/*"])
