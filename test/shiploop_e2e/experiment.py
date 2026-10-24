#!/usr/bin/env python3
"""Template-field experiments: run arms as step slices, score them with a script, decide between two arms.

    python3 test/shiploop_e2e/experiment.py run E1 --arm A [--samples 4 | --sample N] [--host grok] [--out DIR]
    python3 test/shiploop_e2e/experiment.py score E1 [--out DIR]
    python3 test/shiploop_e2e/experiment.py verify E1                 # the evaluator (and the case) tell bad from good
    python3 test/shiploop_e2e/experiment.py decide E1 A T [--out DIR] # also: decide E1 T B; default A B, else A T
    python3 test/shiploop_e2e/experiment.py list

experiments.json holds each experiment: its claim, step case, seed and stop points, arms and evaluator. An arm builds
its plugin from a git ref (read-only, overlay.build_ref) and may lay a prompt overlay over that build copy (overlay.py)
and add seeded records. ``run`` starts one slice.py per sample into ``<out>/<id>/<arm>/<n>/slice`` (a sample whose slice
finished is skipped; one cut off is moved aside to ``slice.cut-<time>`` and run again): samples 1..``--samples`` (default
the experiment's ``samples``, 4 everywhere), or with ``--sample N`` exactly sample N, so a coordinator can give each
sample its own background task and a task time limit costs at most one sample. ``score`` runs the evaluator on
every finished sample and writes ``<out>/<id>/<arm>/<n>/score.json``. ``decide X Y`` compares the mean ``value`` of the
two arms (each ``value`` lies in 0-1); the A/A spread is the difference between X's samples 1-2 and 3-4 (arms.aa_spread
on their means), the only threshold, so X needs scored samples 1-4 and every experiment runs 4 samples per arm:
  ceiling       every sample of both arms scored 1 (floor: 0), whatever n: the case cannot separate the arms, so
                the case, not the arms, needs changing (round 1's E1 and E3);
  supports      Y's mean is above X's by more than the spread (and, with a ``gate``, Y's gate rate is not below X's);
  contradicts   Y is no better than X (difference <= 0), or the gate rate fell;
  inconclusive  Y is better by no more than the spread, or X lacks scored samples 1-4 (the reason says which).
It writes ``<out>/<id>/decision-<X>-<Y>.json`` (and ``decision.json``, the latest) and appends one line to
docs/shiploop-template-experiments-journal.md. Default out: $SHIPLOOP_EXPERIMENTS_OUT, else ~/e2e-runs/experiments.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import arms  # noqa: E402

EXPERIMENTS = HERE / "experiments.json"
JOURNAL = ROOT / "docs" / "shiploop-template-experiments-journal.md"
JOURNAL_HEAD = """# ShipLoop template-field experiments journal

One line per `experiment.py decide`: the experiment, the arms compared (ref and overlay), n per arm, the mean score of
each arm, the A/A spread (the first arm's samples 1-2 vs 3-4), the verdict and the decision file. The plan, cases,
evaluators and arms are in test/shiploop_e2e/experiments.json; run outputs are not committed.

| date | experiment | arms | n | means | spread | gate | verdict | record |
|---|---|---|---|---|---|---|---|---|
"""


def load(exp_id: str | None = None) -> dict:
    data = {k: v for k, v in json.loads(EXPERIMENTS.read_text()).items() if not k.startswith("_")}
    if exp_id is None:
        return data
    if exp_id not in data:
        raise SystemExit(f"unknown experiment {exp_id!r}; known: {', '.join(sorted(data))}")
    return data[exp_id]


def default_out() -> Path:
    return Path(os.environ.get("SHIPLOOP_EXPERIMENTS_OUT") or Path.home() / "e2e-runs" / "experiments").expanduser()


def evaluator(exp: dict):
    path = HERE / exp["evaluator"]
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module


def slice_argv(exp: dict, arm: dict, output: Path, host: str, extra_records: Path | None) -> list[str]:
    argv = [sys.executable, str(HERE / "slice.py"), "--case", exp["case"], "--seed-at", exp["seed_at"],
            "--stop-after", exp["stop_after"], "--host", host, "--output", str(output), "--quiet"]
    if arm.get("ref"):
        argv += ["--ref", arm["ref"]]
    if arm.get("overlay"):
        argv += ["--overlay", str(HERE / arm["overlay"])]
    if exp.get("opening_note"):
        argv += ["--opening-note", str(HERE / exp["opening_note"])]
    if extra_records:
        argv += ["--seed-records", str(extra_records)]
    return argv


def samples(out: Path, exp_id: str, arm: str) -> list[Path]:
    folder = out / exp_id / arm
    found = [p for p in folder.iterdir() if p.is_dir() and p.name.isdigit()] if folder.is_dir() else []
    return sorted(found, key=lambda p: int(p.name))


def finished(sample: Path) -> bool:
    return (sample / "slice" / "slice-result.json").is_file()


def _resolved_commit(ref: str | None) -> str | None:
    """The commit a sample's arm actually built from, so a branch ref that moves mid-round is traceable, not silent."""
    if not ref:
        return None
    import overlay  # noqa: PLC0415
    return overlay.resolve_ref(ref)


def _sample_commit(sample: Path) -> str | None:
    path = sample / "command.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text()).get("commit")
    except (OSError, ValueError):
        return None


def _distinct_commits(rows: list[dict]) -> set[str]:
    return {r["commit"] for r in rows if r.get("commit")}


def _check_single_commit(rows: list[dict], exp_id: str, arm: str) -> None:
    """Refuse to mix samples built from different resolved commits of the same arm (a moving branch ref)."""
    commits = _distinct_commits(rows)
    if len(commits) > 1:
        raise SystemExit(f"{exp_id}/{arm}: its samples were built from different commits of the arm's ref "
                          f"({', '.join(sorted(commits))}); the ref moved mid-round. Pin the arm to one commit, "
                          f"move the stale samples aside, and re-run before scoring or deciding.")


def run(exp_id: str, arm_name: str, count: int, host: str, out: Path, extra: list[str], only: int | None = None) -> int:
    exp = load(exp_id)
    if arm_name not in exp["arms"]:
        raise SystemExit(f"{exp_id} has no arm {arm_name!r}; arms: {', '.join(exp['arms'])}")
    arm = exp["arms"][arm_name]
    commit = _resolved_commit(arm.get("ref"))
    status = 0
    if only is not None and only < 1:
        raise SystemExit(f"--sample must be 1 or more, not {only}")
    for n in ([only] if only is not None else range(1, count + 1)):
        sample = out / exp_id / arm_name / str(n)
        if finished(sample):
            print(f"{exp_id}/{arm_name}/{n}: finished earlier, skipped", flush=True)
            continue
        sample.mkdir(parents=True, exist_ok=True)
        if (sample / "slice").exists():
            (sample / "slice").rename(sample / f"slice.cut-{time.strftime('%Y%m%d-%H%M%S')}")
        records = None
        if arm.get("seed_records"):
            records = sample / "seed-records.json"
            records.write_text(json.dumps(arm["seed_records"], indent=2) + "\n")
        argv = slice_argv(exp, arm, sample / "slice", host, records) + extra
        (sample / "command.json").write_text(
            json.dumps({"argv": argv, "arm": arm, "commit": commit, "started": time.time()}, indent=2) + "\n")
        print(f"{exp_id}/{arm_name}/{n}: {' '.join(argv)}", flush=True)
        started = time.time()
        done = subprocess.run(argv)
        print(f"{exp_id}/{arm_name}/{n}: slice exit {done.returncode} after {round((time.time() - started) / 60, 1)} min",
              flush=True)
        status = status or (0 if finished(sample) else 1)
    return status


def score(exp_id: str, out: Path) -> dict:
    exp = load(exp_id)
    module = evaluator(exp)
    table: dict[str, list] = {}
    for arm_name in exp["arms"]:
        rows: list[dict] = []
        for sample in samples(out, exp_id, arm_name):
            if not finished(sample):
                continue
            found = module.score(sample / "slice")
            result = json.loads((sample / "slice" / "slice-result.json").read_text())
            span = (json.loads((sample / "slice" / "metrics.json").read_text()).get("span") or {}) \
                if (sample / "slice" / "metrics.json").is_file() else {}
            seconds = (round(span["ended"] - span["started"], 1)
                       if span.get("ended") is not None and span.get("started") is not None else None)
            commit = _sample_commit(sample)
            record = {"experiment": exp_id, "arm": arm_name, "sample": int(sample.name), **found,
                      "slice_pass": result.get("pass"), "slice_verdicts": result.get("verdicts"), "seconds": seconds,
                      "commit": commit}
            (sample / "score.json").write_text(json.dumps(record, indent=2, default=str) + "\n")
            rows.append({"sample": int(sample.name), "value": found.get("value"), "commit": commit,
                        "slice_pass": result.get("pass"), "seconds": seconds})
        _check_single_commit(rows, exp_id, arm_name)
        if rows:
            table[arm_name] = rows
    return table


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def read_scores(out: Path, exp_id: str, arm: str) -> list[dict]:
    rows = []
    for sample in samples(out, exp_id, arm):
        try:
            rows.append(json.loads((sample / "score.json").read_text()))
        except (OSError, ValueError):
            continue
    return rows


BOUNDS = (0, 1)  # every evaluator's value lies in 0-1


def judge(x: list[dict], y: list[dict], gate: str | None = None) -> dict:
    """The verdict on Y against X from their score records (see the module doc)."""
    def values(rows):
        return [r["value"] for r in rows if isinstance(r.get("value"), (int, float))]

    def gate_rate(rows):
        seen = [bool(r[gate]) for r in rows if gate and r.get(gate) is not None]
        return _mean(seen) if seen else None

    vx, vy = values(x), values(y)
    by_n = {r["sample"]: r["value"] for r in x if isinstance(r.get("value"), (int, float))}
    report = {"n": [len(vx), len(vy)], "means": [_mean(vx), _mean(vy)], "spread": None, "difference": None,
              "gate": gate, "gate_rates": [gate_rate(x), gate_rate(y)], "verdict": "inconclusive", "reason": ""}
    if not vx or not vy:
        report["reason"] = "an arm has no scored sample"
        return report
    report["difference"] = report["means"][1] - report["means"][0]
    for bound, name in ((BOUNDS[1], "ceiling"), (BOUNDS[0], "floor")):
        if all(v == bound for v in vx + vy):
            report.update(verdict=name, reason=f"every sample of both arms scored {bound}: the case does not separate "
                          f"the arms at this bound, so change the case before adding samples")
            return report
    if not all(n in by_n for n in (1, 2, 3, 4)):
        report["reason"] = "the first arm needs scored samples 1-4 for the A/A spread"
        return report
    spread = arms.aa_spread(_mean([by_n[1], by_n[2]]), _mean([by_n[3], by_n[4]]))
    report["spread"] = spread
    rates = report["gate_rates"]
    if gate and None not in rates and rates[1] < rates[0]:
        report.update(verdict="contradicts", reason=f"the {gate} rate fell from {rates[0]:.2f} to {rates[1]:.2f}")
    elif report["difference"] > spread:
        report.update(verdict="supports", reason=f"mean {report['means'][1]:.2f} vs {report['means'][0]:.2f}: "
                      f"+{report['difference']:.2f} beyond the A/A spread {spread:.2f}")
    elif report["difference"] <= 0:
        report.update(verdict="contradicts", reason=f"no better: mean {report['means'][1]:.2f} vs {report['means'][0]:.2f}")
    else:
        report.update(reason=f"+{report['difference']:.2f} is inside the A/A spread {spread:.2f}")
    return report


def journal_line(exp_id: str, exp: dict, x: str, y: str, report: dict, record: Path) -> str:
    def arm_text(name):
        arm = exp["arms"][name]
        return f"{name}={arm.get('ref')}" + (f"+{Path(arm['overlay']).name}" if arm.get("overlay") else "")

    def num(v):
        return "-" if v is None else f"{v:.2f}"

    gates = "-" if not report["gate"] else f"{report['gate']} {num(report['gate_rates'][0])}/{num(report['gate_rates'][1])}"
    return (f"| {time.strftime('%Y-%m-%d')} | {exp_id} | {arm_text(x)} vs {arm_text(y)} | {report['n'][0]}/{report['n'][1]} | "
            f"{num(report['means'][0])}/{num(report['means'][1])} | {num(report['spread'])} | {gates} | "
            f"**{report['verdict']}**: {report['reason']} | {record} |\n")


def decide(exp_id: str, x: str, y: str, out: Path, journal: Path = JOURNAL) -> dict:
    exp = load(exp_id)
    for name in (x, y):
        if name not in exp["arms"]:
            raise SystemExit(f"{exp_id} has no arm {name!r}; arms: {', '.join(exp['arms'])}")
    rows_x, rows_y = read_scores(out, exp_id, x), read_scores(out, exp_id, y)
    _check_single_commit(rows_x, exp_id, x)
    _check_single_commit(rows_y, exp_id, y)
    report = {"experiment": exp_id, "claim": exp["claim"], "arms": [x, y],
              "arm_specs": {x: exp["arms"][x], y: exp["arms"][y]},
              **judge(rows_x, rows_y, exp.get("gate"))}
    folder = out / exp_id
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / f"decision-{x}-{y}.json"
    record.write_text(json.dumps(report, indent=2) + "\n")
    shutil.copyfile(record, folder / "decision.json")
    if not journal.exists():
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(JOURNAL_HEAD)
    with journal.open("a") as handle:
        handle.write(journal_line(exp_id, exp, x, y, report, record))
    return report


def verify(exp_id: str) -> list[dict]:
    exp = load(exp_id)
    rows = [{"part": exp["evaluator"], "rows": evaluator(exp).verify()}]
    rows[0]["ok"] = bool(rows[0]["rows"]) and all(r["ok"] for r in rows[0]["rows"])
    import overlay  # noqa: PLC0415
    for name, arm in exp["arms"].items():
        if arm.get("overlay"):
            problems = _overlay_problems(overlay, HERE / arm["overlay"], arm.get("ref"))
            rows.append({"part": f"arm {name} overlay {arm['overlay']} on {arm.get('ref')}", "problems": problems,
                         "ok": not problems})
    return rows


def _overlay_problems(overlay, path: Path, ref: str | None) -> list[str]:
    """Whether the overlay applies to the scripts of ``ref`` (git archive into a temporary folder), else this checkout's."""
    if not ref:
        return overlay.check(path)
    with tempfile.TemporaryDirectory() as tmp:
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", overlay.resolve_ref(ref), "skills/shiploop/scripts"],
                                 capture_output=True)
        if archive.returncode:
            return [f"git archive {ref} failed"]
        subprocess.run(["tar", "-x", "-C", tmp], input=archive.stdout, check=True)
        return overlay.check(path, Path(tmp) / "skills" / "shiploop" / "scripts")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=("run", "score", "verify", "decide", "list"))
    p.add_argument("id", nargs="?")
    p.add_argument("pair", nargs="*", help="decide: the two arms, control first (default A B, else A T)")
    p.add_argument("--arm")
    p.add_argument("--samples", type=int, default=None, help="run: samples 1..N (default: the experiment's samples)")
    p.add_argument("--sample", type=int, default=None, help="run: exactly this one sample (its own background task)")
    p.add_argument("--host", default="grok")
    p.add_argument("--out", type=Path, default=None)
    args, extra = p.parse_known_args(argv)
    out = (args.out or default_out()).expanduser().resolve()
    if args.command == "list":
        for exp_id, exp in load().items():
            print(f"{exp_id} [{exp['fix']}] {exp['case']} {exp['seed_at']}->{exp['stop_after']} arms {', '.join(exp['arms'])}: "
                  f"{exp['claim']}")
        return 0
    if not args.id:
        p.error("an experiment id is required")
    if args.command == "run":
        if not args.arm:
            p.error("run needs --arm")
        if args.sample is not None and args.samples is not None:
            p.error("run takes --samples or --sample, not both")
        return run(args.id, args.arm, args.samples or load(args.id).get("samples", 4), args.host, out, extra, args.sample)
    if args.command == "score":
        print(json.dumps(score(args.id, out), indent=2))
        return 0
    if args.command == "verify":
        rows = verify(args.id)
        print(json.dumps(rows, indent=2, default=str))
        return 0 if all(r["ok"] for r in rows) else 1
    arms_of = load(args.id)["arms"]
    pair = args.pair or (["A", "B"] if "B" in arms_of else ["A", "T"])
    if len(pair) != 2:
        p.error("decide takes two arms")
    report = decide(args.id, pair[0], pair[1], out)
    print(json.dumps({k: report[k] for k in ("experiment", "arms", "n", "means", "spread", "gate_rates", "verdict", "reason")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
