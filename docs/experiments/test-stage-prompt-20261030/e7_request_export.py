"""E7-F by the request: export every sample's request-score.json (test/shiploop_e2e/evaluators/e7_request.py) with its mutant
score into e7-request-results.json, and print the table docs/experiments/test-stage-prompt-20261030/e7-request.md reads.

    python3 docs/experiments/test-stage-prompt-20261030/e7_request_export.py [ARM ...]    (default: every arm scored)

Reads ~/e2e-runs/e7-20261030/E7-F/<arm>/<n>/{request-score.json,score.json}; run e7_request.py score on a sample first.
"""
import json
import statistics as st
import sys
from pathlib import Path

OUT = Path.home() / "e2e-runs/e7-20261030/E7-F"
DEST = Path(__file__).resolve().parent / "e7-request-results.json"
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "test/shiploop_e2e/evaluators"))
import e7_request  # noqa: E402


def main(arms: list[str]) -> None:
    rows = []
    for folder in sorted(OUT.glob("*/*/request-score.json"), key=lambda p: (p.parent.parent.name, int(p.parent.name))):
        arm = folder.parent.parent.name
        if arms and arm not in arms:
            continue
        request = json.loads(folder.read_text())
        mutant = json.loads((folder.parent / "score.json").read_text())
        rows.append({"arm": arm, "sample": int(folder.parent.name), "unmutated": request["unmutated"],
                     "request_value": request.get("value"), "request_added_value": request.get("added_value"),
                     "request_survived": request.get("survived"), "earlier_tests_kill": request.get("earlier_tests_kill"),
                     "flaky": [name for name, row in (request.get("variants") or {}).items() if row.get("flaky")],
                     "mutant_value": mutant["value"],
                     "mutant_survivors": [[m["file"], m["line"], m["op"]] for m in mutant.get("survivors", [])
                                          if m["op"] in ("rel-bound", "logic-flip")]})
    variants = e7_request.verify()
    DEST.write_text(json.dumps({
        "about": ("E7-F by the request (docs/experiments/test-stage-prompt-20261030/e7-request.md): each sample's tests run "
                  "against the ten request-breaking variants of the recorded implementation (evaluators/e7_request.py), "
                  "beside the mutant score of e7_tests.py. `variants` is verify(): each variant's witness passes on the "
                  "recorded implementation and fails on the variant, and whether the case's own hidden check catches it."),
        "variants": [{k: v for k, v in row.items() if k != "detail"} for row in variants], "samples": rows},
        indent=1, ensure_ascii=False) + "\n")
    print(DEST, len(rows), "samples")
    for arm in dict.fromkeys(row["arm"] for row in rows):
        got = [row for row in rows if row["arm"] == arm]
        print(f"{arm}: n={len(got)} request mean={st.mean(r['request_value'] for r in got):.3f} "
              f"mutant mean={st.mean(r['mutant_value'] for r in got):.3f} "
              f"variants killed by the earlier tests={sum(len(r['earlier_tests_kill']) for r in got)} "
              f"flaky={sum(len(r['flaky']) for r in got)}")
    print("variants the hidden check catches:", [v["variant"] for v in variants if v["hidden_check_catches"]])


if __name__ == "__main__":
    main(sys.argv[1:])
