"""SG1 of docs/shiploop-sdlc-gates-proposal-2026-10-30.md §5: replay a proof-order check at step-plan on saved runs.

A step's Proof runs when the step's implement stage completes, before that step's test stage writes its tests. The
candidate check flags a step whose Proof names:
- rule A: a path in the ``test`` path class that does not exist yet, so only a test stage can write it later;
- rule B: a path that does not exist yet and that only a later step of the same plan declares in its ``paths``.

"Does not exist yet" is read from the step's base commit in the iteration ledger (``git`` mode) when the run's
worktree still holds it. Otherwise it is inferred from the plan alone:
- missing: an ``absent`` expectation names the path and no earlier step declares it, in its ``paths`` or through the
  ``steps`` of an ``absent`` expectation (a step's ``paths`` are optional, so a plan may say who creates a file there only);
- present: a ``works`` or ``broken`` expectation names it, or an earlier step declares it;
- unknown: no expectation names it. A step with an unknown path and no flag is counted unjudged, never clean.

Live positives the bar names:
- DeepSeek W1, 2026-10-26 (test/shiploop_e2e/LEARNINGS.md:3652);
- Grok chess 5b's S3, if its Proof names a path only S4 declares (docs/shiploop-improve-schedule-proposal-2026-10-25.md:62).

The bar also asks that no step whose Proof passed at implement is flagged. Each row therefore lists the item's
implement outcomes after that step plan, so a W1-like send-back can be told from a false flag. The send-back count is
the item's, not the flagged step's: history rows carry no step id. Read-only: it changes nothing.

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
# The run folders a harness output can hold (test/shiploop_e2e/lifecycle.py RUN_DIR_GLOBS).
RUN_GLOBS = (".shiploop-runs/*/run", "work/.shiploop")


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


def _declared(steps: list[dict[str, Any]], expectations: list[dict[str, Any]]) -> dict[str, set[str]]:
    """{path: ids of the steps that declare it}: each step's ``paths``, and the ``steps`` of an ``absent`` expectation that
    names the path."""
    declared: dict[str, set[str]] = {}
    for step in steps:
        for path in _paths(step):
            declared.setdefault(path, set()).add(str(step.get("id")))
    for row in expectations:
        if row.get("state") == "absent":
            for path in row.get("paths") or ():
                for step_id in row.get("steps") or ():
                    declared.setdefault(str(path), set()).add(str(step_id))
    return declared


def check_plan(plan: dict[str, Any], classify: Callable[[str], str],
               exists_at: Optional[Callable[[str, str], Optional[bool]]] = None) -> dict[str, Any]:
    """The flags for one accepted step plan. ``exists_at(step_id, path)`` answers from the step's base commit, or None
    when it cannot tell; without an answer the check infers from the plan's expectations and the earlier steps' paths."""
    steps = [step for step in plan.get("steps") or () if isinstance(step, dict)]
    expectations = [row for row in plan.get("expectations") or () if isinstance(row, dict)]
    absent = {str(path) for row in expectations if row.get("state") == "absent" for path in row.get("paths") or ()}
    present = {str(path) for row in expectations if row.get("state") in ("works", "broken")
               for path in row.get("paths") or ()}
    declared = _declared(steps, expectations)
    ids = [str(step.get("id")) for step in steps]
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
        earlier_ids, later_ids = set(ids[:index]), set(ids[index + 1:])
        step_flags, undecided = [], False
        for path in names:
            who = declared.get(path, set())
            answer = exists_at(str(step.get("id")), path) if exists_at else None
            if answer is None:
                mode = "inferred"
                if who & earlier_ids or path in present:
                    missing = False
                elif path in absent:
                    missing = True
                else:
                    undecided = True  # no expectation says whether it exists
                    continue
            else:
                mode, missing = "git", not answer
            if not missing:
                continue
            if classify(path) == "test":
                step_flags.append({"step": step.get("id"), "rule": "A", "path": path, "mode": mode, "proof": proof})
            elif who & later_ids and str(step.get("id")) not in who and not who & earlier_ids:
                step_flags.append({"step": step.get("id"), "rule": "B", "path": path, "mode": mode, "proof": proof})
        if undecided and not step_flags:
            unjudged += 1
        else:
            judged += 1
        flags += step_flags
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
            for run in sorted(path for glob_pattern in RUN_GLOBS for path in out.glob(glob_pattern)):
                try:
                    state = store.read_record(run / "state.md")
                except Exception as exc:  # noqa: BLE001 - a saved run the current reader refuses is reported, not fatal
                    print(json.dumps({"run": str(out), "skipped": str(exc)[:120]}))
                    continue
                totals["runs"] += 1
                history = state.get("history") or []
                accepted = state.get("accepted") or {}
                bases = _bases(run)
                repo = state.get("repo")
                git = _git_exists(Path(str(repo))) if repo else (lambda base, path: None)  # no repo: Path("") is the cwd
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

    def with_expectations(steps: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {"steps": steps, "expectations": rows}

    # A step's paths are optional: who creates a file may be said by an absent expectation's steps alone.
    only_by_expectation = with_expectations(
        [{"id": "S1", "task": "a"}, {"id": "S2", "task": "b", "proof": "node --test test/a.test.js"}],
        [{"id": "E1", "state": "absent", "steps": ["S1"], "paths": ["test/a.test.js"]}])
    assert check_plan(only_by_expectation, scope.classify) == {"judged": 1, "unjudged": 0, "flags": []}, \
        "S1 creates the test through its expectation: S2's Proof is not flagged"
    b_by_expectation = with_expectations(
        [{"id": "S1", "task": "a", "proof": "node scripts/check.js"}, {"id": "S2", "task": "b"}],
        [{"id": "E1", "state": "absent", "steps": ["S2"], "paths": ["scripts/check.js"]}])
    assert [f["rule"] for f in check_plan(b_by_expectation, scope.classify)["flags"]] == ["B"], "a later step, by expectation"
    mystery = check_plan(plan([{"id": "S1", "task": "a", "proof": "node --test test/mystery.test.js"}], []), scope.classify)
    assert mystery == {"judged": 0, "unjudged": 1, "flags": []}, "a path no expectation mentions is unjudged, not clean"
    own_path = with_expectations([{"id": "S1", "task": "a", "proof": "node scripts/check.js", "paths": ["scripts/check.js"]}],
                                 [{"id": "E1", "state": "absent", "steps": ["S1"], "paths": ["scripts/check.js"]}])
    assert check_plan(own_path, scope.classify)["flags"] == [], "a step's own path is not rule B"
    earlier_path = with_expectations([{"id": "S1", "task": "a", "paths": ["scripts/x.js"]},
                                      {"id": "S2", "task": "b", "proof": "node scripts/x.js"}],
                                     [{"id": "E1", "state": "absent", "steps": ["S1"], "paths": ["scripts/x.js"]}])
    assert check_plan(earlier_path, scope.classify)["flags"] == [], "an earlier step's path exists by S2's implement"
    print("sg1 self-test: 12 cases pass")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    SCRIPTS = Path(sys.argv[1]).resolve()
    if sys.argv[2:] == ["--self-test"]:
        self_test(SCRIPTS)
    else:
        replay(SCRIPTS, sys.argv[2:] or ["~/e2e-runs/2026*/*"])
