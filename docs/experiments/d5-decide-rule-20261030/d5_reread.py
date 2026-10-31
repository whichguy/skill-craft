"""D5 (docs/shiploop-test-stage-prompt-design-2026-10-30.md §9): read every stored `experiment.py decide` record again under
the permutation rule, and write d5-reread.json beside this file.

    python3 docs/experiments/d5-decide-rule-20261030/d5_reread.py [OUTPUT_ROOT ...]

Each OUTPUT_ROOT is an experiments output folder (default: the e2e-runs folders that hold decision records). For each
`<root>/<experiment>/decision-<X>-<Y>.json` it reads the arms' `<arm>/<n>/score.json` records as they are now and
judges them with `experiment.judge`. `samples_match` says whether the arms' sample counts and means equal those the
record was made from (more samples may have been scored after it), and only a matching row compares like with like.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "test/shiploop_e2e"))
import experiment  # noqa: E402

RUNS = Path.home() / "e2e-runs"
DEFAULT_ROOTS = [RUNS / name for name in ("experiments-r1-20261024", "experiments-r2-20261024", "e6-r1-20261024",
                                         "e6d2-deepseek-20261028", "e7-20261030")]


def scores(folder: Path, arm: str) -> list[dict]:
    rows = []
    for path in sorted((folder / arm).glob("*/score.json"), key=lambda p: int(p.parent.name)):
        try:
            rows.append(json.loads(path.read_text()))
        except (OSError, ValueError):
            continue
    return rows


def reread(roots: list[Path]) -> list[dict]:
    out = []
    for root in roots:
        for record_path in sorted(root.glob("*/decision-*.json")):
            old = json.loads(record_path.read_text())
            folder = record_path.parent
            x, y = old["arms"]
            rows_x, rows_y = scores(folder, x), scores(folder, y)
            new = experiment.judge(rows_x, rows_y, old.get("gate"))
            same = (new["n"] == old["n"] and all(abs(a - b) < 5e-3 for a, b in zip(new["means"], old["means"], strict=True)))
            out.append({"experiment": old["experiment"], "arms": [x, y], "n": old["n"], "means": old["means"],
                        "old_verdict": old["verdict"], "old_spread": old.get("spread"), "new_verdict": new["verdict"],
                        "p": new["p"], "difference": new["difference"], "samples_match": same,
                        "changed": new["verdict"] != old["verdict"], "record": str(record_path)})
    return out


def main(argv: list[str]) -> None:
    roots = [Path(a).expanduser() for a in argv] or [r for r in DEFAULT_ROOTS if r.is_dir()]
    rows = reread(roots)
    (HERE / "d5-reread.json").write_text(json.dumps({
        "about": ("Every stored experiment.py decide record read again by the permutation rule (docs/shiploop-test-stage-prompt-"
                  "design-2026-10-30.md §9 D5): the arms' score.json records as they are now, judged by experiment.judge. "
                  "samples_match is false when more or fewer samples exist now than the record was made from."),
        "roots": [str(r) for r in roots], "rows": rows}, indent=1) + "\n")
    print(len(rows), "records;", sum(r["changed"] for r in rows), "change verdict;",
          sum(r["changed"] for r in rows if r["samples_match"]), "of the", sum(r["samples_match"] for r in rows),
          "whose samples still match")
    for r in rows:
        if r["changed"] or not r["samples_match"]:
            print(f"  {r['experiment']:8} {r['arms'][0]} vs {r['arms'][1]}  n={r['n']}  {r['old_verdict']:12} -> "
                  f"{r['new_verdict']:12} p={'-' if r['p'] is None else format(r['p'], '.3g'):6} "
                  f"{'' if r['samples_match'] else '(samples differ now)'}")


if __name__ == "__main__":
    main(sys.argv[1:])
