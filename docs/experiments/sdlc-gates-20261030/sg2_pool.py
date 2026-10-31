#!/usr/bin/env python3
"""SG2 read as one experiment of four cases: the pooled verdict, fixed before any SG2 run.

Owner decision, 2026-10-31, on an Astra review of "SG2-K1..K4 and AS1 at 8 samples per arm": keep 4 samples per arm and
pool SG2's four cases into one blocked analysis. `experiment.py decide` reads one case at a time, and with 4 binary
samples per arm only a 4-against-0 split reaches p < 0.05, so a real 25% -> 75% catch-rate gain is detected 10% of the
time per case. The pooled test below has 85% power for that gain over the same 32 slices (docs/experiments/
sdlc-gates-20261030/README.md, "SG2", for the table and how it was computed).

    python3 docs/experiments/sdlc-gates-20261030/sg2_pool.py [--out DIR] [--arms A B] [--dry-run]

It reads the scored samples of every `SG2-K*` experiment in experiments.json (`experiment.py score` writes them), the
same way `decide` does, and writes `<out>/SG2/decision-<X>-<Y>.json`, `decision.json`, and one line in
docs/shiploop-template-experiments-journal.md (`--dry-run` only prints). It changes nothing in the harness: this file sits
in docs/, so it is in neither the evaluator digest nor the qualification snapshot (f8eec07c moved both with its
experiment.py change, and an epoch registered before that refuses to run), and `decide` still gives the per-case verdicts.

The rule, fixed here before the runs:
- **Statistic.** The mean over the cases of (B's mean score minus A's mean score), each case weighted alike. The cases
  are blocks: they differ in how hard the seeded defect is, so a score is compared only with scores from its own case.
- **Test.** The exact one-sided permutation p, with the arm labels permuted within each case (a stratified permutation
  test: a dynamic programme over each case's group sums, convolved across the cases, on exact decimals as
  `experiment.permutation_p` does for one case). `supports` needs B's mean case difference above 0 and p below
  `experiment.SIGNIFICANCE` (0.05); with one case it equals `permutation_p`.
- **The other verdicts** are `decide`'s, applied to the pool: `ceiling`/`floor` when every sample of every case scored the
  bound; `inconclusive` when even a perfect split could not reach p < 0.05; `contradicts` when B's mean case difference is
  not above 0 (a point estimate, as in `decide`); otherwise `inconclusive` with the p.
- **Completeness.** The pool is read only when every case has the same number of scored samples in each arm, because the
  equal weighting needs it. Otherwise this exits with the counts and writes nothing: a case `queue` stopped early (it
  stops a case once `contradicts` cannot change) or a host failure leaves one short. Run the queue with `--no-early-stop`
  and run it again; a finished sample is skipped.
- **What a verdict says.** About the average over these four seeded cases, not about every case or unseen defects. The
  per-case rows beside it (n, means, `decide`'s p and verdict) are diagnostics, not a second test.
- **Same build.** Each arm must be the same ref, overlay and delegation in every case and every sample must record one
  commit per arm, as `decide` checks per case.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from decimal import Decimal
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test" / "shiploop_e2e"))
import experiment

PREFIX = "SG2-K"
POOL = "SG2"


def members() -> list[str]:
    return sorted(exp_id for exp_id in experiment.load() if exp_id.startswith(PREFIX))


def pooled_p(blocks: list[tuple[list[float], list[float]]]) -> float:
    """The exact one-sided p that the second group beat the first by chance, over blocks of (control, candidate) values:
    the share of the ways to permute the labels within every block whose candidate sums, added over the blocks, are at
    least the observed. Every block must have the same two group sizes, which makes the sum of candidate sums a fixed
    increasing function of the mean of the blocks' candidate-minus-control mean differences (each block's pooled total is
    unchanged by a permutation of its labels)."""
    values = [Decimal(repr(float(v))) for control, candidate in blocks for v in control + candidate]
    exponent = min(v.as_tuple().exponent for v in values)

    def scale(value: float) -> int:
        return int(Decimal(repr(float(value))).scaleb(-exponent))

    sums, ways, observed = Counter({0: 1}), 1, 0
    for control, candidate in blocks:
        scaled = [scale(v) for v in control + candidate]
        size = len(candidate)
        table = [Counter() for _ in range(size + 1)]
        table[0][0] = 1
        for number, value in enumerate(scaled, start=1):
            for taken in range(min(number, size), 0, -1):
                for total, count in list(table[taken - 1].items()):
                    table[taken][total + value] += count
        merged = Counter()
        for before, count_before in sums.items():
            for here, count_here in table[size].items():
                merged[before + here] += count_before * count_here
        sums, ways = merged, ways * comb(len(scaled), size)
        observed += sum(scale(v) for v in candidate)
    return sum(count for total, count in sums.items() if total >= observed) / ways


def _numbers(rows: list[dict]) -> list[float]:
    return [r["value"] for r in rows if isinstance(r.get("value"), (int, float))]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def judge_pool(cases: dict[str, tuple[list[dict], list[dict]]]) -> dict:
    """The pooled verdict on Y against X from each case's (X rows, Y rows) of score records (see the module doc)."""
    blocks = {name: (_numbers(x), _numbers(y)) for name, (x, y) in cases.items()}
    counts = {name: (len(x), len(y)) for name, (x, y) in blocks.items()}
    if len(set(counts.values())) != 1 or 0 in next(iter(counts.values())):
        raise SystemExit("the SG2 pool is read only when every case has the same number of scored samples in each arm "
                         "(X/Y per case: " + ", ".join(f"{name} {a}/{b}" for name, (a, b) in counts.items()) + "); run "
                         "the queue with --no-early-stop and run it again, a finished sample is skipped")
    nx, ny = next(iter(counts.values()))
    differences = {name: _mean(y) - _mean(x) for name, (x, y) in blocks.items()}
    report = {"n": [nx * len(blocks), ny * len(blocks)],
              "means": [_mean([_mean(x) for x, _ in blocks.values()]), _mean([_mean(y) for _, y in blocks.values()])],
              "p": None, "difference": _mean(list(differences.values())), "gate": None, "gate_rates": [None, None],
              "verdict": "inconclusive", "reason": "",
              "cases": [{"experiment": name, "n": list(counts[name]), "means": [_mean(x), _mean(y)],
                         "difference": differences[name], **{k: v for k, v in experiment.judge(*cases[name]).items()
                                                             if k in ("p", "verdict")}}
                        for name, (x, y) in blocks.items()]}
    everything = [v for x, y in blocks.values() for v in x + y]
    for bound, name in ((experiment.BOUNDS[1], "ceiling"), (experiment.BOUNDS[0], "floor")):
        if all(v == bound for v in everything):
            report.update(verdict=name, reason=f"every sample of every case and both arms scored {bound}: the cases do "
                          f"not separate the arms at this bound, so change the cases before adding samples")
            return report
    report["p"] = pooled_p(list(blocks.values()))
    best = pooled_p([(sorted(x + y)[:nx], sorted(x + y)[nx:]) for x, y in blocks.values()])
    where = f"pooled over {len(blocks)} cases of {nx} against {ny}"
    if best >= experiment.SIGNIFICANCE:
        report["reason"] = f"{where}: even a perfect split gives p {best:.2g}, not below {experiment.SIGNIFICANCE}"
    elif report["difference"] > 0 and report["p"] < experiment.SIGNIFICANCE:
        report.update(verdict="supports", reason=f"{where}: mean case difference +{report['difference']:.2f} (mean "
                      f"{report['means'][1]:.2f} vs {report['means'][0]:.2f}), exact one-sided stratified permutation "
                      f"p {report['p']:.2g}")
    elif report["difference"] <= 0:
        report.update(verdict="contradicts", reason=f"{where}: no better, mean case difference "
                      f"{report['difference']:+.2f} (mean {report['means'][1]:.2f} vs {report['means'][0]:.2f})")
    else:
        report["reason"] = (f"{where}: +{report['difference']:.2f} is within noise, exact one-sided stratified "
                            f"permutation p {report['p']:.2g} (supports needs below {experiment.SIGNIFICANCE})")
    return report


def read_pool(out: Path, x: str, y: str, ids: list[str] | None = None) -> tuple[list[str], dict]:
    """Each member's scored samples of arms X and Y, after `decide`'s checks and the checks that the pool is one build."""
    ids = ids or members()
    if not ids:
        raise SystemExit(f"experiments.json has no {PREFIX}* experiment")
    cases = {}
    for exp_id in ids:
        exp = experiment.load(exp_id)
        for name in (x, y):
            if name not in exp["arms"]:
                raise SystemExit(f"{exp_id} has no arm {name!r}; arms: {', '.join(exp['arms'])}")
        rows_x, rows_y = experiment.read_scores(out, exp_id, x), experiment.read_scores(out, exp_id, y)
        experiment._check_single_commit(rows_x, exp_id, x)
        experiment._check_single_commit(rows_y, exp_id, y)
        experiment._check_one_planning_review(rows_x + rows_y, exp_id, f"{x} and {y}")
        cases[exp_id] = (rows_x, rows_y)
    for number, arm in enumerate((x, y)):
        specs = {json.dumps(experiment.load(i)["arms"][arm], sort_keys=True) for i in ids}
        if len(specs) > 1:
            raise SystemExit(f"arm {arm} is not the same ref, overlay and delegation in every {PREFIX}* experiment")
        commits = experiment._distinct_commits([row for pair in cases.values() for row in pair[number]])
        if len(commits) > 1:
            raise SystemExit(f"arm {arm}: the cases' samples were built from different commits ({', '.join(sorted(commits))})")
    return ids, cases


def decide_pool(out: Path, x: str, y: str, journal: Path = experiment.JOURNAL, record: bool = True) -> dict:
    ids, cases = read_pool(out, x, y)
    exp = experiment.load(ids[0])
    report = {"experiment": POOL, "members": ids, "claim": exp["claim"], "arms": [x, y],
              "arm_specs": {x: exp["arms"][x], y: exp["arms"][y]}, **judge_pool(cases)}
    if not record:
        return report
    folder = out / POOL
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"decision-{x}-{y}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    shutil.copyfile(path, folder / "decision.json")
    if not journal.exists():
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(experiment.JOURNAL_HEAD)
    with journal.open("a") as handle:
        handle.write(experiment.journal_line(POOL, exp, x, y, report, path))
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=None, help="the experiments output folder (default: experiment.py's)")
    p.add_argument("--arms", nargs=2, default=["A", "B"], metavar=("X", "Y"), help="control first (default A B)")
    p.add_argument("--dry-run", action="store_true", help="print the verdict; write no record and no journal line")
    args = p.parse_args(argv)
    out = (args.out or experiment.default_out()).expanduser().resolve()
    report = decide_pool(out, *args.arms, record=not args.dry_run)
    print(json.dumps({k: report[k] for k in ("experiment", "members", "arms", "n", "means", "p", "difference", "verdict",
                                             "reason", "cases")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
