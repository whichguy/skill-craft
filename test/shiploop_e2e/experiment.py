#!/usr/bin/env python3
"""Template-field experiments: run arms as step slices, score them with a script, decide between two arms.

    python3 test/shiploop_e2e/experiment.py run E1 --arm A [--samples 4 | --sample N] [--host grok] [--out DIR]
    python3 test/shiploop_e2e/experiment.py queue E6-K2 E6-K4 --arms T,Cg [--jobs 4] [--samples 4] [--no-early-stop]
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

``queue`` runs a round as one ordered list of slices (sample 1 of every experiment and arm, then sample 2, ...), at most
``--jobs`` at a time, so no slot idles while another lane has work and no two runners ever take the same sample (a
lock file in ``<out>`` refuses a second queue there). Before it launches a sample it checks the experiment: when every
way the missing samples could still come out gives the first arm and each other arm the same verdict, the verdict cannot
change and the experiment's remaining samples are skipped (``--no-early-stop`` runs them all). That check needs a binary
value (the evaluator's ``BINARY``) and no gate; other experiments run every sample. Options ``run`` does not know (for
example ``--planning-review none``, which skips the planning stages' Improve children in a shape round) go to slice.py;
each sample records them, and ``decide`` refuses arms whose samples ran under different planning-review options.
A sample whose host refused its calls (HTTP 401, 402 or 403 in its stderr: an exhausted balance or a lost sign-in) and
that did not pass is a host failure, not a result: ``score`` records it without a value, ``run`` stops there, ``queue``
starts no more samples, and the next ``run`` or ``queue`` moves the slice aside to ``slice.host-failed-<time>`` and runs
it again.
An experiment marked ``descriptive`` runs fewer samples (3) and is reported, not decided: without samples 1-4 of the
first arm the A/A spread is unmeasured, so ``decide`` can only answer "inconclusive" (or ceiling or floor), and
``queue`` never stops it early. An experiment without ``stop_after`` runs the item to its end.
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
            *(["--stop-after", exp["stop_after"]] if exp.get("stop_after") else []),
            "--host", host, "--output", str(output), "--quiet"]
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


# A host that refuses every call (an exhausted balance, a lost sign-in) ends the slice before the arm is tried: R3 on
# 2026-10-26, Grok's "API error (status 402 Payment Required): Grok Build usage balance exhausted" (journal F37). Its
# HTTP status is 401, 402 or 403, in the message or in the error's http_status field.
HOST_REFUSAL = re.compile(r'API error \(status (?P<status>40[123])[^)]*\):?\s*(?P<text>[^"\n]{0,120})'
                          r'|"http_status"\s*:\s*(?P<field>40[123])\b')


def host_failure(sample: Path) -> str | None:
    """Why the host refused the sample's calls (its slice's stderr.txt), else None; never for a slice that passed.

    Such a slice says nothing about its arm, so it is not scored, and the next ``run`` or ``queue`` moves it aside and runs
    it again. Grok's "cancelled" stop has several causes (metrics.session_stop), so a cancelled session alone is not a
    refusal; the downstream evaluator counts it."""
    try:
        text = (sample / "slice" / "stderr.txt").read_text(errors="ignore")
    except OSError:
        return None
    match = HOST_REFUSAL.search(text)
    if match is None:
        return None
    try:
        if json.loads((sample / "slice" / "slice-result.json").read_text()).get("pass") is True:
            return None
    except (OSError, ValueError, AttributeError):
        pass
    if match.group("status"):
        return f"HTTP {match.group('status')}: {match.group('text').strip()}".rstrip(": ")
    return f"HTTP {match.group('field')}"


def finished(sample: Path) -> bool:
    """The sample's slice wrote its result and its host did not refuse its calls (host_failure)."""
    return (sample / "slice" / "slice-result.json").is_file() and host_failure(sample) is None


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


def _sample_planning_review(sample: Path) -> str:
    """The planning-review option a sample's slice ran under (slice.py --planning-review; unset is the engine's stage)."""
    try:
        argv = json.loads((sample / "command.json").read_text()).get("argv") or []
    except (OSError, ValueError):
        return "stage"
    for number, word in enumerate(argv):
        if word == "--planning-review" and number + 1 < len(argv):
            return argv[number + 1]
        if word.startswith("--planning-review="):
            return word.split("=", 1)[1]
    return "stage"


def _check_one_planning_review(rows: list[dict], exp_id: str, what: str) -> None:
    """Refuse to compare samples that ran under different planning-review options: the packets differ."""
    modes = {r.get("planning_review") or "stage" for r in rows}
    if len(modes) > 1:
        raise SystemExit(f"{exp_id} {what}: samples ran under different planning-review options ({', '.join(sorted(modes))});"
                         " compare arms run the same way, or move the other samples aside")


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
            kind = "host-failed" if host_failure(sample) else "cut"
            (sample / "slice").rename(sample / f"slice.{kind}-{time.strftime('%Y%m%d-%H%M%S')}")
            (sample / "score.json").unlink(missing_ok=True)  # it scored the slice just moved aside
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
        refused = host_failure(sample)
        if refused:
            print(f"{exp_id}/{arm_name}/{n}: the host refused its calls ({refused}); not scored, and no later sample "
                  f"starts. Run the same command once the host works: it moves this slice aside and runs it again",
                  flush=True)
            return 1
        status = status or (0 if finished(sample) else 1)
    return status


def score(exp_id: str, out: Path) -> dict:
    exp = load(exp_id)
    module = evaluator(exp)
    table: dict[str, list] = {}
    for arm_name in exp["arms"]:
        rows: list[dict] = []
        for sample in samples(out, exp_id, arm_name):
            refused = host_failure(sample)
            if refused:  # recorded, never a value: the sample runs again
                (sample / "score.json").write_text(json.dumps(
                    {"experiment": exp_id, "arm": arm_name, "sample": int(sample.name), "value": None,
                     "host_failure": refused}, indent=2) + "\n")
                continue
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
                      "commit": commit, "planning_review": _sample_planning_review(sample)}
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


def possible_verdicts(x: list[dict], y: list[dict], count: int) -> set[str]:
    """Every verdict ``judge`` could still give Y against X once each arm has samples 1..``count``, a missing sample's
    value being 0 or 1 (a binary evaluator's only values); a scored sample keeps its value."""
    def known(rows):
        """Each scored sample's value; a record without one (a host failure's) leaves its sample missing."""
        return {r["sample"]: r["value"] for r in rows
                if 1 <= r["sample"] <= count and isinstance(r.get("value"), (int, float))}

    known_x, known_y = known(x), known(y)
    missing = [(known_x, n) for n in range(1, count + 1) if n not in known_x] + \
              [(known_y, n) for n in range(1, count + 1) if n not in known_y]
    found = set()
    for values in itertools.product((0, 1), repeat=len(missing)):
        full_x, full_y = dict(known_x), dict(known_y)
        for (known, n), value in zip(missing, values):
            (full_x if known is known_x else full_y)[n] = value
        found.add(judge([{"sample": n, "value": v} for n, v in full_x.items()],
                        [{"sample": n, "value": v} for n, v in full_y.items()])["verdict"])
    return found


def settled(exp_id: str, out: Path, arm_names: list[str], count: int) -> str | None:
    """The verdicts of ``exp_id``'s round when no remaining sample can change them, else None.

    Only for a binary value, no gate and 4 or more samples (the module doc; fewer leave the A/A spread unmeasured, so
    every completion would read "inconclusive" and the round would stop at once); the first arm is the control. It
    scores the finished samples (score.json) and reads the rest as unknown."""
    exp = load(exp_id)
    if count < 4 or exp.get("gate") or not getattr(evaluator(exp), "BINARY", False) or len(arm_names) < 2:
        return None
    score(exp_id, out)
    control = read_scores(out, exp_id, arm_names[0])
    verdicts = []
    for arm in arm_names[1:]:
        found = possible_verdicts(control, read_scores(out, exp_id, arm), count)
        if len(found) != 1:
            return None
        verdicts.append(f"{arm_names[0]} vs {arm}: {next(iter(found))}")
    return "; ".join(verdicts)


def _lock(out: Path) -> Path:
    """A queue's lock in ``out``: refuse while another live queue holds it, take over a stale one."""
    out.mkdir(parents=True, exist_ok=True)
    lock = out / ".queue.lock"
    try:
        holder = int(lock.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        holder = None
    if holder and holder != os.getpid():
        try:
            os.kill(holder, 0)
        except ProcessLookupError:
            holder = None
        except PermissionError:
            pass
        if holder:
            raise SystemExit(f"another queue (pid {holder}) is running in {out}; one queue per output folder")
    lock.write_text(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    return lock


def queue(exp_ids: list[str], arm_names: list[str], count: int, jobs: int, host: str, out: Path, extra: list[str],
          early_stop: bool = True, runner=None) -> int:
    """Run every sample of ``exp_ids`` × ``arm_names`` as one queue, ``jobs`` at a time (the module doc)."""
    for exp_id in exp_ids:
        missing = [a for a in arm_names if a not in load(exp_id)["arms"]]
        if missing:
            raise SystemExit(f"{exp_id} has no arm {', '.join(missing)}; arms: {', '.join(load(exp_id)['arms'])}")
    if jobs < 1:
        raise SystemExit(f"--jobs must be 1 or more, not {jobs}")
    runner = runner or run
    lock = _lock(out)
    pending = deque((e, a, n) for n in range(1, count + 1) for e in exp_ids for a in arm_names
                    if not finished(out / e / a / str(n)))
    stopped: dict[str, str] = {}
    refused: list[str] = []  # the first host refusal: every later sample would fail the same way
    printing = threading.Lock()
    status = 0

    def say(text: str) -> None:
        with printing:
            print(text, flush=True)

    def check(exp_id: str) -> None:
        if early_stop and exp_id not in stopped:
            verdict = settled(exp_id, out, arm_names, count)
            if verdict:
                stopped[exp_id] = verdict
                say(f"{exp_id}: settled ({verdict}); its remaining samples are skipped")

    try:
        for exp_id in exp_ids:
            check(exp_id)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            running: dict = {}
            while pending or running:
                while pending and len(running) < jobs and not refused:
                    exp_id, arm, n = pending.popleft()
                    if exp_id in stopped:
                        say(f"{exp_id}/{arm}/{n}: skipped, the verdict cannot change")
                        continue
                    running[pool.submit(runner, exp_id, arm, count, host, out, extra, n)] = (exp_id, arm, n)
                if not running:
                    break
                done, _ = wait(running, return_when=FIRST_COMPLETED)
                for future in done:
                    exp_id, arm, n = running.pop(future)
                    try:
                        status = status or future.result()
                    except (Exception, SystemExit) as exc:  # one sample's failure never stops the others
                        say(f"{exp_id}/{arm}/{n}: failed: {exc}")
                        status = 1
                    why = host_failure(out / exp_id / arm / str(n))
                    if why and not refused:  # a host refusal does stop them: R3 ran six slices into a 402
                        refused.append(why)
                        say(f"{exp_id}/{arm}/{n}: the host refused its calls ({why}); the queue starts no more samples")
                    check(exp_id)
    finally:
        lock.unlink(missing_ok=True)
    for exp_id, verdict in stopped.items():
        say(f"{exp_id}: stopped early, {verdict}")
    if refused:
        say(f"queue: stopped by the host ({refused[0]}) with {len(pending)} sample{'' if len(pending) == 1 else 's'} "
            f"not started; run the same command once the host works: it reruns the refused samples and the rest")
        status = 1
    return status


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
    _check_one_planning_review(rows_x + rows_y, exp_id, f"{x} and {y}")
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
    p.add_argument("command", choices=("run", "queue", "score", "verify", "decide", "list"))
    p.add_argument("id", nargs="?")
    p.add_argument("pair", nargs="*", help="decide: the two arms, control first (default A B, else A T); "
                                          "queue: more experiment ids")
    p.add_argument("--arm")
    p.add_argument("--arms", help="queue: comma-separated, control first (default: the first experiment's arms)")
    p.add_argument("--jobs", type=int, default=4, help="queue: slices at a time (default 4)")
    p.add_argument("--no-early-stop", action="store_true", help="queue: run every sample even once a verdict is settled")
    p.add_argument("--samples", type=int, default=None, help="run: samples 1..N (default: the experiment's samples)")
    p.add_argument("--sample", type=int, default=None, help="run: exactly this one sample (its own background task)")
    p.add_argument("--host", default="grok")
    p.add_argument("--out", type=Path, default=None)
    args, extra = p.parse_known_args(argv)
    out = (args.out or default_out()).expanduser().resolve()
    if args.command == "list":
        for exp_id, exp in load().items():
            print(f"{exp_id} [{exp['fix']}] {exp['case']} {exp['seed_at']}->{exp.get('stop_after') or 'item end'} "
                  f"arms {', '.join(exp['arms'])}: "
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
    if args.command == "queue":
        if args.sample is not None:
            p.error("queue runs samples 1..--samples, not one --sample")
        ids = [args.id, *args.pair]
        names = args.arms.split(",") if args.arms else list(load(args.id)["arms"])
        return queue(ids, names, args.samples or load(args.id).get("samples", 4), args.jobs, args.host, out, extra,
                     early_stop=not args.no_early_stop)
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
