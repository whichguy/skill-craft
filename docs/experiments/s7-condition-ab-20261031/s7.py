#!/usr/bin/env python3
"""S7: the "nearest wrong rule" clause as a frozen-input test-authoring A/B (plan.md, predeclared 2026-10-31).

Subcommands:
  prepare                       build each run's base (final product, the run's own tests removed) and the fixed sample
  generate RUN ARM SAMPLE       one Codex Terra session that writes the tests (ARM A or B)
  lane RUN                      generate RUN's eight sessions in order: A1 B1 A2 B2 A3 B3 A4 B4
  score RUN                     run every valid session's suite on each verified survivor and sampled killed variant
  decide                        the plan's decision rule over every scored session
Everything is written under $S7_OUT (default ~/e2e-runs-s7/20261031). Originals are only read.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COND = ROOT / "docs" / "experiments" / "prompt-template-review-20261031" / "conditions"
OUT = Path(os.environ.get("S7_OUT", "~/e2e-runs-s7/20261031")).expanduser()
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import hosts
import shiploop_item_scope as item_scope

SUITES = {
    "codex-r2-user-listing": "npm test",
    "claude-csv-report": "python3 -m unittest",
    "bf-ds-ticket-assignment": "npm test",
    "grok-web-battleship": "node --test",
    "v2170-ds-battleship": "node --test",
}
# Test harnesses a run wrote whose paths ShipLoop classifies as product.
RUN_HARNESSES = {"v2170-ds-battleship": ("browser-check/", "system-check/")}
SKIP = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".shiploop-improve")
MODEL, EFFORT = "gpt-6.1-terra", "high"
SEED = 31107
CLAUSE = (" For each condition a requirement states, give a case whose input makes the stated rule and its nearest wrong "
          "rule disagree, such as an input out of the required order, a half-way value, both sides of a range edge, each "
          "member of an enumerated class, or each axis of a symmetric rule.")
FRAME = """You are writing the automated tests for work that is already built in this repository. The product is accepted
as it is: do not change any product file.

The accepted requirements this work added or changed (they are also in docs/shiploop/spec.md):

{requirements}

Do this:
1. Design the test cases. For each requirement, give cases for its positive, failure and boundary behaviour as its text
   states. Each case has an ID (TC-1, TC-2, ...), an input or action, and the exact expected result taken from the
   requirement text, never from the code.{clause}
2. Write each case as an automated test in this repository's own test suite, with the case ID in the test's name. The
   whole suite runs with `{suite}` from the repository root. Use only what the repository already uses: no new
   dependency and no network. A test that starts a server uses a free port (port 0, or a PORT it sets), never a fixed
   one, because other suites run on this machine at the same time.
3. Run the suite until every test passes on the current product. If the product disagrees with a requirement, do not
   change the product: drop that assertion and say so in your final message.

Finish with a short list of your cases and the test files you wrote."""


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=S7", "-c", "user.email=s7@example.invalid", *args],
                          capture_output=True, text=True, check=check, env=env)


def frozen(run: str) -> dict:
    return json.loads((COND / (run + ".requirements.json")).read_text())


def is_test(run: str, path: str) -> bool:
    return item_scope.classify(path) == "test" or path.startswith(RUN_HARNESSES.get(run, ()))


def snapshot(source: Path, dest: Path) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(source, dest, ignore=SKIP, symlinks=True)
    git(dest, "init", "-q")
    git(dest, "add", "-A")
    git(dest, "commit", "-qm", "base")


def prepare() -> None:
    for run, suite in SUITES.items():
        spec = frozen(run)
        repo, baseline = Path(spec["repo"]), spec["baseline"]
        base = OUT / "base" / run
        shutil.rmtree(base, ignore_errors=True)
        shutil.copytree(repo, base, ignore=SKIP, symlinks=True)
        removed, restored = [], []
        rows = git(repo, "diff", "--name-status", "--no-renames", baseline, "HEAD").stdout.splitlines()
        for status, path in (row.split("\t", 1) for row in rows):
            if not is_test(run, path):
                continue
            if status == "A":
                (base / path).unlink(missing_ok=True)
                removed.append(path)
            elif status == "M":
                (base / path).write_text(git(repo, "show", baseline + ":" + path).stdout)
                restored.append(path)
        for folder in RUN_HARNESSES.get(run, ()):
            shutil.rmtree(base / folder, ignore_errors=True)
        results = json.loads((COND / run / "results.json").read_text())["conditions"]
        killed = sorted(row["id"] for row in results if row.get("verdict") == "killed" and row.get("patch"))
        sample = {"survivors": [row["id"] for row in results if row.get("verdict") == "survived"],
                  "killed_sample": sorted(random.Random(SEED).sample(killed, min(10, len(killed))))}
        (OUT / "base" / (run + ".json")).write_text(json.dumps(
            {"run": run, "removed": removed, "restored": restored, "suite": suite, **sample}, indent=1) + "\n")
        print(f"{run}: removed {len(removed)}, restored {len(restored)}, survivors {len(sample['survivors'])}, "
              f"killed sample {len(sample['killed_sample'])}")


def prompt(run: str, arm: str) -> str:
    requirements = "\n\n".join(text.strip() for text in frozen(run)["requirements"].values())
    return FRAME.format(requirements=requirements, clause=CLAUSE if arm == "B" else "", suite=SUITES[run])


def usage(events: Path) -> dict:
    total = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
    for line in events.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        found = row.get("usage") if isinstance(row, dict) else None
        if isinstance(found, dict) and row.get("type") == "turn.completed":
            for key in total:
                total[key] += int(found.get(key) or 0)
    return total


def changed_paths(run: str, work: Path) -> dict:
    status = git(work, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
    product, tests, other = [], [], []
    tracked = set(git(work, "ls-files").stdout.splitlines())
    for line in status:
        path = line[3:].strip().strip('"')
        if path.startswith((".shiploop", "node_modules/")) or path.endswith((".pyc", ".log")):
            continue
        if is_test(run, path):
            tests.append(path)
        elif path in tracked:
            product.append(path)   # an existing product file changed or deleted
        else:
            other.append(path)     # a new non-test file (a helper, a fixture)
    return {"product_changed": product, "tests_written": tests, "new_other": other}


def generate(run: str, arm: str, sample: int) -> dict:
    folder = OUT / "sessions" / run / f"{arm}{sample}"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    work = folder / "work"
    snapshot(OUT / "base" / run, work)
    host = hosts.CodexHost()
    env = host.env(folder / "home")
    argv = host.argv(prompt=prompt(run, arm), prompt_file=folder / "prompt.txt", cwd=work, model=MODEL, effort=EFFORT,
                     permission_mode=None, max_turns=None)
    started = time.time()
    with (folder / "events.jsonl").open("w") as stream, (folder / "stderr.txt").open("w") as errors:
        try:
            exit_code = subprocess.run(argv, check=False, stdout=stream, stderr=errors, env=env, cwd=work, timeout=3600).returncode
        except subprocess.TimeoutExpired:
            exit_code = "timeout"
    record = {"run": run, "arm": arm, "sample": sample, "exit": exit_code, "minutes": round((time.time() - started) / 60, 1),
              "usage": usage(folder / "events.jsonl"), **changed_paths(run, work)}
    (folder / "session.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({key: record[key] for key in ("run", "arm", "sample", "exit", "minutes")}), flush=True)
    return record


def suite_exit(work: Path, command: str, timeout: int = 600) -> int | str:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "CI": "1"}
    try:
        return subprocess.run(command, check=False, shell=True, cwd=work, capture_output=True, timeout=timeout, env=env).returncode
    except subprocess.TimeoutExpired:
        return "timeout"


def patch_file(run: str, name: str) -> Path:
    for path in (COND / run / name, COND / name, Path(name)):
        if path.is_file():
            return path
    raise SystemExit(f"{run}: no patch {name}")


def score(run: str) -> None:
    meta = json.loads((OUT / "base" / (run + ".json")).read_text())
    rows = {row["id"]: row for row in json.loads((COND / run / "results.json").read_text())["conditions"]}
    for folder in sorted((OUT / "sessions" / run).glob("[AB][0-9]*")):
        session = json.loads((folder / "session.json").read_text())
        result = {"run": run, "arm": session["arm"], "sample": session["sample"]}
        if session["exit"] != 0 or session["product_changed"] or not session["tests_written"]:
            result["invalid"] = ("exit " + str(session["exit"]) if session["exit"] != 0 else
                                 "product changed: " + ", ".join(session["product_changed"]) if session["product_changed"]
                                 else "no test written")
        else:
            work = folder / "score"
            snapshot(folder / "work", work)
            baseline = [suite_exit(work, meta["suite"]) for _ in range(2)]
            if baseline != [0, 0]:
                result["invalid"] = f"suite on the unmutated tree exited {baseline}"
            else:
                outcomes = {}
                for ident in [*meta["survivors"], *meta["killed_sample"]]:
                    applied = subprocess.run(["patch", "-p1", "-s", "--batch"], check=False, cwd=work, capture_output=True, text=True,
                                             input=patch_file(run, rows[ident]["patch"]).read_text())
                    outcomes[ident] = "patch-failed" if applied.returncode else suite_exit(work, meta["suite"])
                    git(work, "checkout", "-q", "--", ".")
                    git(work, "clean", "-fdq")
                result["survivors"] = {ident: outcomes[ident] for ident in meta["survivors"]}
                result["killed_sample"] = {ident: outcomes[ident] for ident in meta["killed_sample"]}
        (folder / "score.json").write_text(json.dumps(result, indent=1) + "\n")
        print(json.dumps({key: result.get(key) for key in ("run", "arm", "sample", "invalid")}
                         | {"survivors_killed": sum(v not in (0, "patch-failed") for v in (result.get("survivors") or {}).values())}),
              flush=True)


def killed(outcomes: dict) -> tuple[int, int]:
    tried = [value for value in outcomes.values() if value != "patch-failed"]
    return sum(value != 0 for value in tried), len(tried)


def decide() -> dict:
    sessions = []
    for path in sorted((OUT / "sessions").glob("*/[AB][0-9]*/score.json")):
        score_row = json.loads(path.read_text())
        session_row = json.loads((path.parent / "session.json").read_text())
        sessions.append({**score_row, "usage": session_row["usage"], "minutes": session_row["minutes"]})
    valid = [row for row in sessions if "invalid" not in row]

    def pooled(rows: list, field: str) -> float:
        kills = tries = 0
        for row in rows:
            k, t = killed(row[field])
            kills, tries = kills + k, tries + t
        return kills / tries if tries else float("nan")

    def difference(rows: list) -> float:
        return pooled([r for r in rows if r["arm"] == "B"], "survivors") - pooled([r for r in rows if r["arm"] == "A"], "survivors")

    observed = difference(valid)
    rng, runs, beats, draws = random.Random(SEED), sorted({row["run"] for row in valid}), 0, 10000
    for _ in range(draws):
        shuffled = []
        for run in runs:
            group = [row for row in valid if row["run"] == run]
            arms = [row["arm"] for row in group]
            rng.shuffle(arms)
            shuffled += [{**row, "arm": arm} for row, arm in zip(group, arms)]
        beats += difference(shuffled) >= observed - 1e-12
    tokens = {arm: [sum(row["usage"].values()) for row in valid if row["arm"] == arm] for arm in "AB"}
    mean = {arm: (sum(values) / len(values) if values else float("nan")) for arm, values in tokens.items()}
    out = {
        "sessions": len(sessions), "valid": {arm: sum(row["arm"] == arm for row in valid) for arm in "AB"},
        "invalid": [{key: row[key] for key in ("run", "arm", "sample", "invalid")} for row in sessions if "invalid" in row],
        "survivor_kill_share": {arm: round(pooled([r for r in valid if r["arm"] == arm], "survivors"), 3) for arm in "AB"},
        "regression_kill_share": {arm: round(pooled([r for r in valid if r["arm"] == arm], "killed_sample"), 3) for arm in "AB"},
        "per_run": {run: {arm: [killed(r["survivors"]) for r in valid if r["run"] == run and r["arm"] == arm] for arm in "AB"}
                    for run in runs},
        "difference": round(observed, 3), "p_one_sided": round(beats / draws, 4),
        "mean_tokens": {arm: round(value) for arm, value in mean.items()},
        "token_ratio": round(mean["B"] / mean["A"], 3) if mean["A"] else None,
    }
    regression_drop = out["regression_kill_share"]["A"] - out["regression_kill_share"]["B"]
    out["candidate"] = bool(observed >= 0.15 and out["p_one_sided"] < 0.05 and regression_drop <= 0.02
                            and (out["token_ratio"] or 99) <= 1.25)
    (OUT / "decision.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    g = sub.add_parser("generate")
    g.add_argument("run", choices=SUITES)
    g.add_argument("arm", choices=("A", "B"))
    g.add_argument("sample", type=int)
    lane = sub.add_parser("lane")
    lane.add_argument("run", choices=SUITES)
    lane.add_argument("--samples", type=int, default=4)
    s = sub.add_parser("score")
    s.add_argument("run", choices=SUITES)
    sub.add_parser("decide")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "generate":
        generate(args.run, args.arm, args.sample)
    elif args.command == "lane":
        for number in range(1, args.samples + 1):
            for arm in ("A", "B"):
                generate(args.run, arm, number)
    elif args.command == "score":
        score(args.run)
    else:
        decide()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
