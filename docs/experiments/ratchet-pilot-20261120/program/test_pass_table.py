#!/usr/bin/env python3
"""One table over the test-pass runs of parts C and T of the program (journal section 26). No model is called.

    python3 test_pass_table.py RUNS_ROOT GRADED_DIR OUT.json RUN [RUN ...]

For each RUN (a name under RUNS_ROOT) it reads what the graders left:

  RUNS_ROOT/RUN/run.json            the arm (--prove-fail, --tests-question), the test sessions and their seconds,
                                    and for --prove-fail what the script found before and after its refusal
  RUNS_ROOT/RUN/strength.json       grade.py strength: planted defects caught, checks failing on the reference and on
                                    the second correct delivery
  GRADED_DIR/RUN.existing.json      mutate.py --unchanged --manifest: seeded faults on existing lines
  GRADED_DIR/RUN.sabotage.json      prove_fail.py --only sabotage: does a check fail when an existing test is broken

Yardstick Y2 is read on the faults that sit on odd-numbered lines (the proof of failure shows a session only faults
on even-numbered lines) and, beside it, on all lines. A run whose grading is missing is listed as such.
"""
import json
import sys
from pathlib import Path


def arm_of(record):
    if record.get("prove_fail_asked") or record.get("prove_fail"):
        return "proof of failure"
    return {"general": "question, general", "grounded": "question, grounded"}.get(record.get("tests_question"), "plain")


def faults_row(path):
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    rows = data["faults"]

    def count(subset):
        return {"faults": len(subset), "own": sum(1 for row in subset if row.get("own") is True),
                "acceptance": sum(1 for row in subset if row.get("acceptance") is True),
                "acceptance_beyond_own": sum(1 for row in subset if row.get("acceptance") is True and row.get("own") is not True),
                "survive_both": sum(1 for row in subset if row.get("own") is not True and row.get("acceptance") is not True)}
    return {"all_lines": count(rows), "odd_lines": count([row for row in rows if row["line"] % 2 == 1]),
            "even_lines": count([row for row in rows if row["line"] % 2 == 0]),
            "left_out": len(data.get("commands_failing_on_the_untouched_copy") or [])}


def read(root, graded, name):
    run = root / name
    record = json.loads((run / "run.json").read_text())
    tests = [row for row in record["sessions"] if row["role"] == "tests"]
    row = {"run": name, "arm": arm_of(record), "stop": record.get("stop"), "final_gate": record.get("final_pass"),
           "test_sessions": len(tests), "test_seconds": round(sum(item["seconds"] for item in tests)),
           "proof": record.get("prove_fail") or None}
    strength = run / "strength.json"
    if strength.is_file():
        data = json.loads(strength.read_text())
        missed = sorted(name_ for name_, entry in data["defects"].items() if not (entry.get("caught") if isinstance(entry, dict) else entry))
        row.update({"checks": data["items"], "caught": data["caught"], "pool": data["pool"], "missed": missed,
                    "update_rejects_resolved_caught": "update-rejects-resolved" not in missed,
                    "failing_on_reference": data["reference"]["failing"],
                    "failing_on_second_correct": (data.get("controls") or {}).get("alternative", {}).get("failing")
                    if isinstance((data.get("controls") or {}).get("alternative"), dict) else (data.get("controls") or {}).get("alternative")})
    row["existing"] = faults_row(graded / f"{name}.existing.json")
    sabotage = graded / f"{name}.sabotage.json"
    if sabotage.is_file():
        data = json.loads(sabotage.read_text())
        row["sabotage"] = "no existing test file" if not data.get("sabotaged_file") else (
            "unnoticed" if "sabotage" in data.get("copies_unnoticed", []) else "noticed")
    return row


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 4:
        raise SystemExit(__doc__)
    root, graded, out, names = Path(argv[0]), Path(argv[1]), Path(argv[2]), argv[3:]
    rows = [read(root, graded, name) for name in names]
    out.write_text(json.dumps(rows, indent=1) + "\n")
    print("run | arm | test sessions (seconds) | checks | planted defects caught | update-rejects-resolved | fail on the reference | "
          "fail on the second correct delivery | odd-line faults: acceptance / own / acceptance beyond own | all lines: the same | sabotaged copy")
    def part(existing, key):
        if not existing:
            return "not graded"
        cell = existing[key]
        return f"{cell['acceptance']} / {cell['own']} / {cell['acceptance_beyond_own']} of {cell['faults']}"

    for row in rows:
        existing = row.get("existing")
        second = row.get("failing_on_second_correct")
        print(f"{row['run']} | {row['arm']} | {row['test_sessions']} ({row['test_seconds']}) | {row.get('checks', 'not graded')} | "
              f"{row.get('caught', '?')} of {row.get('pool', '?')} | {'caught' if row.get('update_rejects_resolved_caught') else 'missed' if 'missed' in row else '?'} | "
              f"{len(row['failing_on_reference']) if 'failing_on_reference' in row else '?'} | {len(second) if second is not None else '?'} | "
              f"{part(existing, 'odd_lines')} | {part(existing, 'all_lines')} | {row.get('sabotage', 'not graded')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
