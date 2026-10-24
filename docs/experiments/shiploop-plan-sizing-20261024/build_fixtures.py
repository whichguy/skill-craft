#!/usr/bin/env python3
"""Build E6's step cases from the saved runs they replay (docs/shiploop-plan-sizing-experiment-plan-2026-10-24.md).

    python3 -B docs/experiments/shiploop-plan-sizing-20261024/build_fixtures.py [--check]

Each replay case starts where a real run's step plan started: the run's worktree at the commit before that item's
step-plan (its knowledge home and any earlier items' product), the run's request verbatim, the plan's work item, and the
plan's concern map, open assumptions and summary as seeded records. Writes, under test/shiploop_e2e/:

  fixtures/chess-sf-w1/       chess run 4 (2026-10-20, Grok 4.7) at a6044d1, before W1 (the engine, one step there)
  fixtures/chess-sf-w3/       chess run 4 at 5383110, before W3 (board, tab, app and flexipage, one step there)
  fixtures/battleship-w2/     battleship-1 (2026-10-18, Grok 4.7) at 69b31b9, before W2 (server and page, six steps)
  fixtures/chess-node-w1/     chess-sf-w1 ported to a Node.js module: the same engine requirements and oracles
  evaluators/e6_records/      compact excerpts of four accepted step plans, which `e6_step_size.py verify` reads
  step_cases.json             the four cases (inserted or replaced) and a `shape` band on three existing small cases

The source runs are read-only. `--check` rebuilds into a temporary folder and exits 1 when a committed file differs, or
0 with a note when a source run is missing (the committed fixtures are then the record).
"""
from __future__ import annotations

import argparse
import filecmp
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E2E = ROOT / "test" / "shiploop_e2e"
RUN4 = Path("/Users/dadleet/e2e-runs/20261020/chess-sf-full-9e52e8/.shiploop-runs/work-20261021-030256-ada3c6")
BATTLESHIP1 = Path("/Users/dadleet/e2e-runs/2026-10-18/battleship-1/.shiploop-runs/work-20261018-212526-5fb41b")
CHECKERS1 = Path("/Users/dadleet/e2e-runs/20261010/checkers-1/.shiploop-runs/work-20261010-153302-c82ae6")
_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
# This repository is public: the org and user IDs and the instance host a run recorded are replaced in everything written.
REDACT = [(re.compile(r"\b00D[A-Za-z0-9]{15}\b"), "00D000000000000AAA"),
          (re.compile(r"\b005[A-Za-z0-9]{15}\b"), "005000000000000AAA"),
          (re.compile(r"\borgfarm-[a-z0-9]+-dev-ed\b"), "example-dev-ed")]


def redact(text: str) -> str:
    for pattern, placeholder in REDACT:
        text = pattern.sub(placeholder, text)
    return text


def redacted(value):
    """``value`` (JSON data) with every string redacted."""
    return json.loads(redact(json.dumps(value, ensure_ascii=False)))

# (case, source run, base commit, item, fixture, fake_sf, checks, shape). Checks are the slice's grading commands; the
# Salesforce ones never call sf (a stopped slice only records them, and the shim guards the rest).
REPLAYS = [
    ("sf-chess-engine", RUN4, "a6044d1", "W1", "chess-sf-w1", True,
     ["test -f sfdx-project.json && test -f force-app/main/default/classes/SLChessEngine.cls"],
     {"steps": [3, None], "about": "The engine item: run 4 put it in one step of 7 criteria (793 lines, 21 minutes)."}),
    ("sf-chess-board-entry", RUN4, "5383110", "W3", "chess-sf-w3", True,
     ["test -f force-app/main/default/lwc/slChessBoard/slChessBoard.js && "
      "test -f force-app/main/default/tabs/SLChess_Board.tab-meta.xml"],
     {"steps": [2, None], "separate": [[["**/lwc/**"], ["**/tabs/**", "**/applications/**", "**/flexipages/**"]]],
      "about": "A component and the org entry metadata that opens it: two layers, one step in run 4."}),
    ("node-battleship-server", BATTLESHIP1, "69b31b9", "W2", "battleship-w2", False, ["node --test"],
     {"steps": [2, 7], "about": "Grok split this item into 6 steps after STEP_SIZING: a guard against over-tightening."}),
]
# Bands on existing small cases (step_cases.json): over-splitting guards.
SMALL = {"node-fix-bug": {"steps": [1, 1], "about": "One bug fix is one step."},
         "node-rename": {"steps": [1, 1], "about": "A mechanical rename is one step."},
         "node-add-function": {"steps": [1, 2], "about": "One small function."}}
# Accepted step plans e6_step_size.py verify scores against a case's band: (record, run, item, case, expected value).
RECORDS = [("run4-w1", RUN4, "W1", "sf-chess-engine", 0), ("run4-w3", RUN4, "W3", "sf-chess-board-entry", 0),
           ("battleship1-w2", BATTLESHIP1, "W2", "node-battleship-server", 1),
           ("checkers1-w1", CHECKERS1, "W1", "node-chess-engine", 1)]


def block(path: Path) -> dict:
    return json.loads(_BLOCK.search(path.read_text(encoding="utf-8")).group(1))


def history(run: Path) -> list[dict]:
    return block(run / "run" / "state.md")["history"]


def result(run: Path, stage: str, item: str | None = None) -> dict:
    """The last accepted done result of ``stage`` (for ``item``) in a saved run."""
    rows = [h for h in history(run) if h["stage"] == stage and h["outcome"] == "done"
            and (item is None or h.get("workitem") == item)]
    return block(run / "run" / "results" / (rows[-1]["action"] + ".md"))["result"]


def request(run: Path) -> str:
    text = (run / "run" / "request.md").read_text(encoding="utf-8")
    return re.search(r"## Verbatim\n\n~~~text\n(.*?)\n~~~", text, re.S).group(1).strip()


def export(run: Path, commit: str, into: Path) -> None:
    tar = subprocess.run(["git", "-C", str(run / "worktree"), "archive", commit], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as archive:
        archive.extractall(into, filter="data")
    for path in into.rglob("*"):
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if redact(text) != text:
                path.write_text(redact(text), encoding="utf-8")


def item_paths(run: Path, base: str, item: str) -> list[str]:
    """The product files the item changed in the source run (its expect_paths): the diff from ``base`` to the item's
    end, the first commit after ``base`` that is its verify commit (``feat: <item> ...``) or a carry-forward knowledge
    commit, less documentation, proof scripts and files only commits naming another item changed (run 4 fixed W1's
    engine during W3)."""
    git = ["git", "-C", str(run / "worktree")]
    log = subprocess.run([*git, "log", "--reverse", "--format=%H %s", f"{base}..HEAD"], check=True, capture_output=True,
                         text=True).stdout.splitlines()
    end = next(i for i, line in enumerate(log)
               if "after carry-forward" in line or re.match(rf"\S+ feat: {item}\b", line))
    own, other = set(), set()
    for line in log[:end + 1]:
        sha, subject = line.split(" ", 1)
        files = set(subprocess.run([*git, "show", "--name-only", "--format=", sha], check=True, capture_output=True,
                                   text=True).stdout.split())
        (other if set(re.findall(r"\bW\d+\b", subject)) - {item} else own).update(files)
    return sorted(n for n in own if not n.startswith(("docs/", "scripts/")) and not n.endswith(".md"))


def plan_records(run: Path, item: str) -> dict:
    """The plan fields a step plan of ``item`` reads: its concern rows, the assumptions it may consume, the summary."""
    plan = result(run, "plan")
    records = {"summary": plan.get("summary", "")}
    concerns = (plan.get("concerns") or {}).get(item)
    if concerns:
        records["concerns"] = {item: concerns}
    rows = [a for a in plan.get("assumptions") or [] if a.get("consumer") in (None, item)]
    if rows:
        records["assumptions"] = rows
    return records


def replay_case(run: Path, base: str, item: str, fixture: str, fake: bool, checks: list[str], shape: dict) -> dict:
    work_item = next(w for w in result(run, "plan")["work_items"] if w["id"] == item)
    case = {"fixture": fixture, "prompt": request(run), "work_item": work_item,
            "expect_paths": item_paths(run, base, item), "checks": checks,
            "seed_records": {"plan": plan_records(run, item)}, "shape": shape,
            "source": f"{run} worktree {base}, the {item} step-plan point"}
    if fake:
        case["fake_sf"] = {"orgs": "de"}
    return redacted(case)


# The Node twin of chess-sf-w1: run 4's engine requirements R-2 to R-5 and transitions T-1 to T-4, verbatim but for these
# replacements, with a Node project shape (R-1) and budget (NFR-1). No Salesforce word may survive (checked).
NODE_REPLACE = [
    ("`SLChessEngine.IllegalMoveException`", "`IllegalMoveError`"),
    ("`SLChessEngine` static methods", "the `src/chess.js` functions"),
    ("`SLChessEngine` is public and has only static methods.", "`src/chess.js` exports only functions and `IllegalMoveError`."),
    ("SLChessEngine.legalMoves", "legalMoves"), ("SLChessEngine.applyMove", "applyMove"), ("SLChessEngine.status", "status"),
    ("`legalMoves(String fen)`", "`legalMoves(fen)`"), ("`applyMove(String fen, String move)`", "`applyMove(fen, move)`"),
    ("`status(String fen)`", "`status(fen)`"), (" in org `de`", ""), ("an org Apex test", "a `node --test` case"),
    ("org Apex tests", "`node --test` cases"), ("an org test", "a `node --test` case"), ("org tests", "`node --test` cases"),
    ("Apex stores nothing.", "The module stores nothing."), ("`SLChessEngine`", "`src/chess.js`"),
    ("`IllegalMoveException` from the engine", "`IllegalMoveError` from the engine"),
]
NODE_SALESFORCE = re.compile(r"\b(Apex|SLChess\w*|org|sf|LWC|Lightning|AuraEnabled|controller|Controller)\b")
NODE_PROMPT = (
    "Build a chess rules engine as a Node.js module src/chess.js (CommonJS, no dependencies; npm test runs node --test). "
    "A position is a FEN string. startFen() returns the standard start position. legalMoves(fen) returns an array of "
    "every legal move for the side to move in UCI form (for example e2e4, and e7e8q for a promotion), sorted "
    "alphabetically. applyMove(fen, move) returns the FEN after the move, with correct castling rights, en-passant "
    "square, halfmove clock and fullmove number, or throws IllegalMoveError (a class the module also exports) when the "
    "move is not legal. The en-passant target square is set after every two-square pawn push, whether or not a capture "
    "is possible (the FEN-spec convention). status(fen) returns ongoing, check, checkmate or stalemate for the side to "
    "move. Implement all piece moves, castling on both sides (never out of, through or into check; in UCI it is the "
    "king's two-square move: e1g1, e1c1, e8g8, e8c8), en passant, promotion to q, r, b or n, check, checkmate and "
    "stalemate. Cover the rules with node --test tests in test/: known games (fool's mate, scholar's mate), castling, en "
    "passant, promotion, stalemate and move counts from standard test positions. Keep legalMoves on a middlegame "
    "position under 50 ms and a depth-2 legal-move count of the start position under 2 seconds. npm test must pass.")
NODE_ITEM = {
    "id": "W1", "title": "Chess rules engine src/chess.js with rule and budget tests",
    "context": ("Ready: package.json (npm test runs node --test) and the accepted spec R-1 to R-5 and NFR-1. Harness: "
                "docs/shiploop/environment.md section Harnesses and suites. Done: src/chess.js exports startFen, "
                "legalMoves, applyMove, status and IllegalMoveError; test/chess.test.js covers R-2 to R-5 and NFR-1. "
                "Confirm by: node --test; pass when it exits 0. Compare the whole FEN strings in spec R-4. Seam: the tests "
                "require ./src/chess (CommonJS). AD-1 is the integer mailbox. There is no prior product behavior to "
                "preserve.")}
NODE_R1 = """### R-1 Project shape

Basis: request sentences on the Node.js module. The project root holds `package.json` (CommonJS, no dependencies, `npm test` runs `node --test`) and `src/chess.js`; tests live in `test/`.

- Positive: those paths exist and `require('./src/chess')` exports `startFen`, `legalMoves`, `applyMove`, `status` and `IllegalMoveError`. Confirmed by a `node --test` case.
- Failure: n/a: a missing export is the same miss as the positive check.
- Boundary: `package.json` has no dependencies. Confirmed by reading it.
- Surface: the checkout.

"""
NODE_NFR = """## Non-functional requirements

- NFR-1 Performance. Operating condition: Node.js 20 or later on one core. `legalMoves` on middlegame `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` returns within 50 ms; a depth-2 count of the start position (400 replies) returns within 2 seconds. Verified by `node --test` cases that time them with `process.hrtime.bigint()`.
- NFR-2 Compatibility. No third-party chess library and no dependency. Verified by `package.json`.
- Excluded: a board, persistence and anything beyond one call at a time.
"""
NODE_ENVIRONMENT = """# Environment

## Targets and runtimes

Local only: Node.js 20 or later (CommonJS), no network and no deployment target. Fact: `node --version` prints v20 or later.

## Commands

```sh
npm test                                              # node --test: the whole suite
node --test --test-reporter=spec test/chess.test.js   # one file
```

## Harnesses and suites

- Harness: Node's built-in `node:test` with `node:assert/strict`; no test dependency.
- Focused suite: `node --test --test-reporter=spec test/chess.test.js`.
- Regression suite: `node --test`.
- NFR-1 timing runs inside a test with `process.hrtime.bigint()`.

## ID convention

Requirements R-<n> and NFR-<n>; test cases TC-<n>.
"""
NODE_ARCHITECTURE = """# Architecture

## Stack

Node.js CommonJS module with no dependencies; tests on `node:test`.

## Structure

`src/chess.js` (the engine) and `test/` (its tests).

## Decisions

- AD-1 Integer mailbox. Choice: each public function parses the FEN into a 64-entry integer array, works on it and serialises back. Why: simple and fast enough for NFR-1. Alternatives: bitboards (faster, much more code); a board object kept between calls (state the API does not have). Status: accepted.

## Interfaces and boundaries

`src/chess.js` exports `startFen()`, `legalMoves(fen)`, `applyMove(fen, move)`, `status(fen)` and `IllegalMoveError`. A position crosses the boundary only as a FEN string.
"""


def node_spec(sf_spec: str) -> str:
    start, end = sf_spec.index("### R-2 "), sf_spec.index("### R-6 ")
    body = sf_spec[start:end]
    rows = [line for line in sf_spec[sf_spec.index("## Transitions"):sf_spec.index("## Non-functional")].splitlines()
            if line.startswith("| T-") and not line.startswith("| T-5")]
    transitions = ("## Transitions\n\n| ID | Before | Trigger | After | Failure |\n| --- | --- | --- | --- | --- |\n"
                   + "\n".join(rows) + "\n\nNo durable record, no concurrent writers, no queue.\n\n")
    text = ("# Chess engine spec\n\nNo prior product requirements exist. Every ID below is added from the user request. "
            "Nothing is retired.\n\n## Requirements\n\n" + NODE_R1 + body + transitions + NODE_NFR + "\n## Retired\n\nNone.\n")
    for old, new in NODE_REPLACE:
        text = text.replace(old, new)
    left = sorted(set(NODE_SALESFORCE.findall(text)))
    if left:
        raise SystemExit(f"node spec: Salesforce words survive the port: {left}")
    return text


def write_node_fixture(into: Path) -> None:
    sf_spec = subprocess.run(["git", "-C", str(RUN4 / "worktree"), "show", "a6044d1:docs/shiploop/spec.md"], check=True,
                             capture_output=True, text=True).stdout
    home = into / "docs" / "shiploop"
    home.mkdir(parents=True)
    (home / "spec.md").write_text(node_spec(sf_spec))
    (home / "environment.md").write_text(NODE_ENVIRONMENT)
    (home / "architecture.md").write_text(NODE_ARCHITECTURE)
    (into / "package.json").write_text(json.dumps({"name": "chess-engine", "version": "1.0.0", "private": True,
                                                   "scripts": {"test": "node --test"}}, indent=2) + "\n")
    (into / ".gitignore").write_text("node_modules/\n")


NODE_CASE = {"fixture": "chess-node-w1", "prompt": NODE_PROMPT, "work_item": NODE_ITEM, "expect_paths": ["src/chess.js"],
             "checks": ["node --test"],
             "shape": {"steps": [3, None], "about": "sf-chess-engine's item on a local Node route: separates the platform "
                                                    "from the model."},
             "source": "chess-sf-w1 ported to Node.js by build_fixtures.py (NODE_REPLACE)"}


def excerpt(run: Path, item: str) -> dict:
    """A step plan reduced to what the evaluator reads: steps (id, deps, criteria, paths, check), criteria, item paths."""
    plan = result(run, "step-plan", item)
    keep = ("id", "deps", "criteria", "paths", "check")
    return {"source": f"{run} step-plan of {item}",
            "steps": [{k: step[k] for k in keep if k in step} for step in plan.get("steps") or []],
            "criteria": [{"id": c["id"], "text": c.get("text", "")} for c in plan.get("criteria") or []],
            "paths": plan.get("paths") or []}


def insert_cases(text: str, cases: dict) -> str:
    """Insert or replace top-level entries of the hand-formatted step_cases.json, keeping every other byte."""
    data = json.loads(text)
    for name, entry in cases.items():
        body = json.dumps(entry, indent=2, ensure_ascii=False).replace("\n", "\n  ")
        if name in data:
            start = text.index(f'\n  "{name}": ')
            depth, i = 0, text.index("{", start)
            while True:
                depth += {"{": 1, "}": -1}.get(text[i], 0) if not _in_string(text, i) else 0
                if depth == 0:
                    break
                i += 1
            text = text[:start] + f'\n  "{name}": ' + body + text[i + 1:]
        else:
            end = text.rstrip().rindex("}")
            text = text[:end].rstrip() + f',\n  "{name}": ' + body + "\n}\n"
    if json.loads(text).keys() != (data | cases).keys():
        raise SystemExit("step_cases.json: insertion changed the set of cases")
    return text


def set_shape_line(text: str, name: str, shape: dict) -> str:
    """Give an existing case a one-line ``"shape"`` key right after its opening brace, keeping its other lines as they are."""
    opening = f'\n  "{name}": {{'
    at = text.index(opening) + len(opening)
    line = f'\n    "shape": {json.dumps(shape, ensure_ascii=False)},'
    rest = text[at:]
    if rest.startswith('\n    "shape": '):
        rest = rest[rest.index("\n", 1):]
    return text[:at] + line + rest


def _in_string(text: str, index: int) -> bool:
    line_start = text.rfind("\n", 0, index) + 1
    quotes, i = 0, line_start
    while i < index:
        if text[i] == "\\":
            i += 2
            continue
        quotes += text[i] == '"'
        i += 1
    return quotes % 2 == 1


def build(out_e2e: Path) -> None:
    for name in ("chess-sf-w1", "chess-sf-w3", "battleship-w2", "chess-node-w1"):
        shutil.rmtree(out_e2e / "fixtures" / name, ignore_errors=True)
    cases = {}
    for name, run, base, item, fixture, fake, checks, shape in REPLAYS:
        export(run, base, out_e2e / "fixtures" / fixture)
        cases[name] = replay_case(run, base, item, fixture, fake, checks, shape)
    write_node_fixture(out_e2e / "fixtures" / "chess-node-w1")
    cases["node-chess-engine"] = NODE_CASE
    step_cases = out_e2e / "step_cases.json"
    text = insert_cases(step_cases.read_text(), cases)
    for name, shape in SMALL.items():
        text = set_shape_line(text, name, shape)
    if any(json.loads(text)[name].get("shape") != shape for name, shape in SMALL.items()):
        raise SystemExit("step_cases.json: a small case's shape line did not land")
    step_cases.write_text(text)
    records = out_e2e / "evaluators" / "e6_records"
    shutil.rmtree(records, ignore_errors=True)
    records.mkdir(parents=True)
    for name, run, item, case, expected in RECORDS:
        record = redacted({**excerpt(run, item), "case": case, "expected_value": expected})
        (records / f"{name}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    missing = [str(run) for run in (RUN4, BATTLESHIP1, CHECKERS1) if not (run / "run" / "state.md").is_file()]
    if missing:
        print("source runs missing (the committed fixtures are the record): " + ", ".join(missing))
        return 0 if args.check else 1
    if not args.check:
        build(E2E)
        return 0
    with tempfile.TemporaryDirectory() as temp:
        copy = Path(temp) / "e2e"
        shutil.copytree(E2E, copy, ignore=shutil.ignore_patterns("__pycache__"))
        build(copy)
        differ = [str(p.relative_to(copy)) for p in copy.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and (not (E2E / p.relative_to(copy)).is_file() or not filecmp.cmp(p, E2E / p.relative_to(copy), False))]
    print("fixtures match their sources" if not differ else "differ from their sources: " + ", ".join(differ))
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
