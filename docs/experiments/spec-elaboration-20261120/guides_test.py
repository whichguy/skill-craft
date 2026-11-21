#!/usr/bin/env python3
"""The guides test (journal section 39): real ShipLoop runs from one sentence, ended when the specification is accepted.

Two arms: ShipLoop as released, and the same build with one sentence added to the spec stage
(overlays/guides-read.json). Each sample is a real run of test/shiploop_e2e/run.py on a small existing user service,
started from the sentence REQUEST and ended through the harness's own stop file when the navigator enters
`test-strategy`: the spec stage and its review are then done. The watcher follows
docs/experiments/sdlc-structure-20261119/stage_stop_samples.py, which is tied to catalog cases on Codex.

  prepare ROOT --checkout DIR     no model: lay the base down, build the two arms, show they differ by the sentence
  run ROOT NAME:ARM:DRIVER ...    launch the samples together; ARM is A or B, DRIVER is sol or sonnet
  collect ROOT ROUND NAME ...     no model: what each sample opened and wrote; copies its specification into
                                  results/ROUND/ for grade.py
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guide_reads
import qualcheck

REQUEST = "Let admins upload a CSV to bulk-create users."
CASE = "csv-user-import"  # the bench case whose checklist grades the specification
BASE_CASE = "user-listing"  # its base, fixtures/node-base, is laid down by the harness's own brownfield.start
OVERLAY = "docs/experiments/spec-elaboration-20261120/overlays/guides-read.json"
BUILD_ARM = "docs/experiments/sdlc-structure-20261119/build_arm.py"
ARMS = {"A": "RA-real-released", "B": "RB-real-guides"}
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
        "extra": ["--max-budget-usd", "6"],
        "cell": "sonnet-high",
    },
}
# The four guide sections arm B's sentence names, by the heading each one opens with.
SECTIONS = {
    "Behavior-model guidance": "## Behavior model",
    "Behavior traceability guidance": "## Traceability and review",
    "State and data assessment": "## State and data change assessment",
    "Requirements definition guide": "# Existing specs and non-functional requirements",
}
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
            f"failed ({done.returncode}): {' '.join(argv[:4])} ...\n{done.stderr[-800:]}"
        )
    return done.stdout


def prepare(root: Path, checkout: Path) -> int:
    dirty = sh(["git", "status", "--short"], checkout).splitlines()
    head = sh(["git", "rev-parse", "HEAD"], checkout).strip()
    root.mkdir(parents=True, exist_ok=True)
    base = json.loads(
        sh(
            [sys.executable, "-c", LAY_BASE, str(root / "prior" / "work"), BASE_CASE],
            checkout,
        )
    )
    plugins, prompts = {}, {}
    for arm in ARMS:
        argv = [sys.executable, BUILD_ARM, str(root / f"arm-{arm}")] + (
            [OVERLAY] if arm == "B" else []
        )
        plugins[arm] = sh(argv, checkout).strip().splitlines()[-1]
        scripts = Path(plugins[arm]) / "skills" / "shiploop" / "scripts"
        prompts[arm] = sh([sys.executable, "-c", RENDER, str(scripts)], checkout)
    differing = subprocess.run(
        ["diff", "-rq", "-x", "__pycache__", plugins["A"], plugins["B"]],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    delta = [
        line
        for line in difflib.unified_diff(
            prompts["A"].splitlines(), prompts["B"].splitlines(), lineterm="", n=0
        )
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    record = {
        "checkout": str(checkout),
        "head": head,
        "checkout_status_lines": len(dirty),
        "base": base,
        "plugins": plugins,
        "spec_prompt_sha256": {
            arm: hashlib.sha256(text.encode()).hexdigest()[:12]
            for arm, text in prompts.items()
        },
        "files_differing_between_arms": differing,
        "spec_prompt_delta": delta,
    }
    (root / "prepare.json").write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 0


def run_dir(out: Path) -> Path | None:
    found = sorted(out.glob(".shiploop-runs/*/run"))
    return found[0] if found else None


def trace(out: Path) -> list[dict]:
    run = run_dir(out)
    try:
        return qualcheck.rows(run / "trace.jsonl") if run else []
    except (OSError, ValueError):
        return []


def past_spec(out: Path) -> bool:
    """The first accepted `complete` that enters test-strategy: the spec stage and its review are done."""
    return any(
        row.get("kind") == "command"
        and row.get("verb") == "complete"
        and row.get("exit") == 0
        and isinstance(row.get("stage"), list)
        and row["stage"][1] == "test-strategy"
        for row in trace(out)
    )


def save_specs(out: Path) -> None:
    """The spec as its stage wrote it (the tree bound for its review) and as it stood at the stop."""
    run = run_dir(out)
    worktree = run.parent / "worktree" if run else None
    if not worktree or not worktree.exists():
        return
    current = worktree / "docs" / "shiploop" / "spec.md"
    if current.exists():
        (out / "spec-as-accepted.md").write_text(current.read_text(errors="replace"))
    for bind in sorted(
        (run / "improve").glob("*-bind.md"), key=lambda path: path.stat().st_mtime
    ):
        tree = re.search(r'"tree": "([0-9a-f]{40})"', bind.read_text(errors="replace"))
        if not tree:
            continue
        shown = subprocess.run(
            [
                "git",
                "-C",
                str(worktree),
                "show",
                f"{tree.group(1)}:docs/shiploop/spec.md",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if shown.returncode == 0 and shown.stdout.strip():
            (out / "spec-as-written.md").write_text(shown.stdout)
        break  # the first review bound in a run is the spec's


def launch(root: Path, samples: list[str], limit: float) -> int:
    ready = json.loads((root / "prepare.json").read_text())
    checkout = Path(ready["checkout"])
    (root / "samples").mkdir(exist_ok=True)
    live = []
    for sample in samples:
        name, arm, driver = sample.split(":")
        chosen = DRIVERS[driver]
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
        process = subprocess.Popen(
            argv, cwd=checkout, stdout=log, stderr=subprocess.STDOUT
        )
        live.append(
            {
                "name": name,
                "arm": arm,
                "driver": driver,
                "out": out,
                "process": process,
                "pid": process.pid,
            }
        )
        live[-1].update(started=time.time(), stopped=None, reached=False, why=None)
    while any(s["stopped"] is None for s in live):
        for s in live:
            if s["stopped"] is not None:
                continue
            reached = past_spec(s["out"])
            over = time.time() - s["started"] > limit * 60
            ended = s["process"].poll() is not None
            if reached or over or ended:
                s.update(stopped=time.time(), reached=reached)
                s["why"] = (
                    "entered test-strategy"
                    if reached
                    else "run ended by itself"
                    if ended
                    else "time limit"
                )
                if not ended and s["out"].is_dir():
                    (s["out"] / "stop").write_text(f"guides test: {s['why']}\n")
        time.sleep(5)
    for s in live:
        try:
            s["process"].wait(timeout=600)
        except subprocess.TimeoutExpired:
            s["why"] += "; run.py still running 10 minutes after the stop file"
        save_specs(s["out"])
        row = {
            key: s[key] for key in ("name", "arm", "driver", "pid", "reached", "why")
        }
        row.update(
            minutes=round((s["stopped"] - s["started"]) / 60, 1),
            returncode=s["process"].poll(),
        )
        (root / "samples" / f"{s['name']}.sample.json").write_text(
            json.dumps(row) + "\n"
        )
        print(json.dumps(row))
    return 0


def first_seen(out: Path) -> dict[str, float | None]:
    """When each named section's heading first appears in the session's stream (epoch seconds), or None."""
    times = {}
    try:
        clock = {
            row["line"]: row["t"] for row in qualcheck.rows(out / "timeline.jsonl")
        }
    except (OSError, ValueError, KeyError):
        clock = {}
    seen: dict[str, float | None] = {}
    for n, line in enumerate(
        (out / "events.jsonl").read_text(errors="replace").splitlines()
    ):
        found = set(guide_reads.HEADING.findall(line))
        found |= {text.rstrip() for text in found}
        for label, heading in SECTIONS.items():
            if label not in seen and heading in found:
                seen[label] = clock.get(n) or clock.get(n + 1) or times.get("last")
        times["last"] = clock.get(n, times.get("last"))
    return {label: seen.get(label) for label in SECTIONS} | {
        "_present": {label: label in seen for label in SECTIONS}
    }


def measures(text: str) -> dict:
    return {
        "words": len(text.split()),
        "requirements": len(set(re.findall(r"\bR-[0-9]+\b", text))),
        "nonfunctional_section": bool(
            re.search(r"^#+ Non-functional requirements", text, re.MULTILINE)
        ),
        "lines_naming_an_assumption": len(
            re.findall(r"(?im)^.*\bassum(?:e|ed|ption)", text)
        ),
        "lines_naming_an_open_gap": len(
            re.findall(r"(?im)^.*\b(?:open gap|unresolved|undecided)\b", text)
        ),
    }


def collect(root: Path, round_name: str, names: list[str]) -> int:
    for name in names:
        out = root / "samples" / name
        sample = json.loads((root / "samples" / f"{name}.sample.json").read_text())
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
        rows = trace(out)
        accepted_at = next(
            (
                r.get("ts")
                for r in rows
                if r.get("verb") == "complete"
                and r.get("exit") == 0
                and (r.get("stage") or [None])[0] == "spec"
            ),
            None,
        )
        spec_action = next(
            (
                r.get("action")
                for r in rows
                if r.get("verb") == "complete"
                and r.get("exit") == 0
                and (r.get("stage") or [None])[0] == "spec"
            ),
            None,
        )
        seen = first_seen(out) if (out / "events.jsonl").is_file() else {"_present": {}}
        present = seen.pop("_present")
        before = {
            label: bool(t and accepted_at and t <= accepted_at)
            for label, t in seen.items()
        }
        stream = out / "events.jsonl"
        guides = (
            sorted(guide_reads.seen_by_content(stream, guide_reads.MARKS))
            if stream.is_file()
            else []
        )
        stages = {row.get("stage"): row for row in metrics.get("stages") or []}
        written = out / "spec-as-written.md"
        accepted = out / "spec-as-accepted.md"
        row = {
            **sample,
            "process": (result.get("process") or {}).get("status"),
            "engine_stage_at_stop": (result.get("termination") or {}).get(
                "engine_stage"
            ),
            "planning_review": (
                re.search(
                    r'"planning_review": "([a-z]+)"',
                    (run_dir(out) / "state.md").read_text(),
                )
                or [None, None]
            )[1]
            if run_dir(out)
            else None,
            "sections_seen": present,
            "sections_seen_before_the_spec_was_accepted": before,
            "guides_seen": [g[:-3] for g in guides],
            "spec_as_written": measures(written.read_text())
            if written.is_file()
            else None,
            "spec_as_accepted": measures(accepted.read_text())
            if accepted.is_file()
            else None,
            "spec_stage_seconds": (stages.get("spec") or {}).get("seconds"),
            "spec_review_seconds": (stages.get("spec") or {}).get("improve_seconds"),
            "turns": metrics.get("turns"),
            "cost_usd": metrics.get("cost_usd"),
            "refusals": sum(1 for r in rows if r.get("exit") == 2),
        }
        print(json.dumps(row))
        if not (sample["reached"] and accepted.is_file()):
            continue
        cell = (
            HERE
            / "results"
            / round_name
            / f"{CASE}__{ARMS[sample['arm']]}__{DRIVERS[sample['driver']]['cell']}"
        )
        (cell / "also").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(accepted, cell / "spec.md")
        run = run_dir(out)
        architecture = run.parent / "worktree" / "docs" / "shiploop" / "architecture.md"
        if architecture.is_file():
            shutil.copyfile(architecture, cell / "also" / "architecture.md")
        if spec_action and (run / "results" / f"{spec_action}.md").is_file():
            shutil.copyfile(
                run / "results" / f"{spec_action}.md", cell / "also" / "submission.md"
            )
        (cell / "meta.json").write_text(
            json.dumps({"sample": name, "root": str(root), **sample}, indent=1) + "\n"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=("prepare", "run", "collect"))
    parser.add_argument("root", type=Path)
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--limit", type=float, default=20.0)
    args = parser.parse_args()
    if args.command == "prepare":
        return prepare(args.root.resolve(), args.checkout.resolve())
    if args.command == "run":
        return launch(args.root.resolve(), args.rest, args.limit)
    return collect(args.root.resolve(), args.rest[0], args.rest[1:])


if __name__ == "__main__":
    sys.exit(main())
