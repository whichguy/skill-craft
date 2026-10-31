#!/usr/bin/env python3
"""Score X2 (README.md, "X2") from the Opus judge answers and apply the pre-registered rules.

A decision is `carried` only when the judge's quote is found in the output; `spec_pinned` and `acceptance` only when the
quote is found in the output's spec.md block.  Per run: the share of the case's decisions acceptance-lined, pinned and
carried; agreement = matches yes / (yes + no) over carried decisions; flagged share over pinned.  Writes
scores-<tag>-<slug>.json.  Usage: score_spec.py [SUBJECT_SLUG] [TAG: spec (X2, arms A, D, C) or spec-x2b (A, B)]
"""
import importlib.util
import json
import re
import sys

from common import CASE, HERE, X1, envelope_text, spec_block
from stats import mean, permutation_p, sign_flip_p

_spec = importlib.util.spec_from_file_location("x1_score", X1 / "score.py")
x1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x1)
ARMS = ("A", "D", "C")
MEASURES = ("acceptance", "spec_pinned", "carried")


def judge_json(path):
    text = json.loads(path.read_text()).get("text") or ""
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    tag = sys.argv[2] if len(sys.argv) > 2 else "spec"          # X2b: spec-x2b
    global ARMS
    ARMS = ("A", "B") if tag == "spec-x2b" else ("A", "D", "C")
    mapping = json.loads((HERE / "judge" / f"{tag}-{slug}-mapping.json").read_text())
    runs, unverified = [], []
    for name, labels in mapping.items():
        case_id = name.split(f"{tag}-{slug}-", 1)[1].rsplit("-p", 1)[0]
        verdict = judge_json(HERE / "judge" / f"{name}.out.json")["outputs"]
        decisions = [g["id"] for g in CASE[case_id]["ground_truth"]]
        for label, info in labels.items():
            path = HERE / info["file"]
            text = envelope_text(path)
            spec_text = spec_block(text)
            meta = json.loads(path.with_name(path.stem + ".meta.json").read_text())
            grade = verdict.get(label, {})
            counts = dict.fromkeys(MEASURES, 0)
            yes = no = flagged = 0
            detail = {}
            for ident in decisions:
                row = (grade.get("decisions") or {}).get(ident) or {}
                quote = row.get("quote") or ""
                in_spec = bool(quote) and x1.norm(quote) in x1.norm(spec_text)
                in_text = bool(quote) and x1.norm(quote) in x1.norm(text)
                carried = bool(row.get("carried")) and in_text
                pinned = bool(row.get("spec_pinned")) and in_spec
                accepted = bool(row.get("acceptance")) and pinned
                if row.get("carried") and not in_text:
                    unverified.append({"judge": name, "label": label, "decision": ident, "quote": quote})
                counts["carried"] += carried
                counts["spec_pinned"] += pinned
                counts["acceptance"] += accepted
                if carried:
                    yes += row.get("matches") == "yes"
                    no += row.get("matches") == "no"
                if pinned and row.get("flagged"):
                    flagged += 1
                detail[ident] = {"carried": carried, "pinned": pinned, "acceptance": accepted,
                                 "matches": row.get("matches") if carried else "na", "flagged": bool(row.get("flagged"))}
            usage = json.loads(path.read_text()).get("usage") or {}
            runs.append({"case": case_id, "arm": info["arm"], "sample": info["sample"], "label": label, "judge": name,
                         **{m: round(counts[m] / len(decisions), 4) for m in MEASURES},
                         "agree_yes": yes, "agree_no": no, "flagged": flagged, "pinned_n": counts["spec_pinned"],
                         "requirements": grade.get("requirements"), "scope_additions": grade.get("scope_additions"),
                         "scope_examples": grade.get("scope_examples"), "chars": len(text), "spec_chars": len(spec_text),
                         "seconds": meta.get("seconds"), "output_tokens": usage.get("output_tokens"), "decisions": detail})
    report = {"subject": slug, "runs": runs, "unverified_quotes": unverified, "arms": {}, "tests": {}, "rules": {}}
    for arm in ARMS:
        rows = [r for r in runs if r["arm"] == arm]
        yes, no = sum(r["agree_yes"] for r in rows), sum(r["agree_no"] for r in rows)
        report["arms"][arm] = {"n": len(rows), **{m: mean(r[m] for r in rows) for m in MEASURES},
                               "agreement": yes / (yes + no) if yes + no else None, "agree_yes": yes, "agree_no": no,
                               "flagged_share": (sum(r["flagged"] for r in rows) / max(1, sum(r["pinned_n"] for r in rows))),
                               "requirements": mean(r["requirements"] or 0 for r in rows),
                               "scope_additions": mean(r["scope_additions"] or 0 for r in rows),
                               "chars": mean(r["chars"] for r in rows), "seconds": mean(r["seconds"] or 0 for r in rows),
                               "output_tokens": mean(r["output_tokens"] or 0 for r in rows)}

    def values(arm, measure):
        rows = sorted((r for r in runs if r["arm"] == arm), key=lambda r: (r["case"], r["sample"]))
        return [r[measure] for r in rows]

    pairs = (("A", "B"),) if tag == "spec-x2b" else (("A", "C"), ("A", "D"), ("D", "C"))
    for x, y in pairs:
        for m in MEASURES:
            a, b = values(x, m), values(y, m)
            test = {"diff": mean(b) - mean(a), "p_one_sided": permutation_p(a, b)}
            if (x, y) in (("A", "D"), ("A", "B")):
                test["p_paired"] = sign_flip_p(a, b)
            report["tests"][f"{y} vs {x} {m}"] = test
    arms = report["arms"]

    def agree_ok(arm):
        return (arms[arm]["agreement"] or 0) >= (arms["A"]["agreement"] or 0) - 0.02

    if tag == "spec-x2b":
        gains = [report["tests"][f"B vs A {m}"] for m in ("carried", "spec_pinned")]
        report["rules"] = {"intake catalog adopted (B - A >= 0.05 on carried or spec_pinned, p < 0.05, agreement held)":
                           any(g["diff"] >= 0.05 and g["p_one_sided"] < 0.05 for g in gains) and agree_ok("B")}
    else:
        c_gain = report["tests"]["C vs A acceptance"]
        d_gain = report["tests"]["D vs A acceptance"]
        cd = report["tests"]["C vs D acceptance"]
        report["rules"] = {
            "1 phase 1 adopted (C - A >= 0.10 acceptance, p < 0.05, agreement held)":
                c_gain["diff"] >= 0.10 and c_gain["p_one_sided"] < 0.05 and agree_ok("C"),
            "2 duty line adopted instead (D - A >= 0.10, p < 0.05, agreement held, C - D < 0.05)":
                d_gain["diff"] >= 0.10 and d_gain["p_one_sided"] < 0.05 and agree_ok("D") and cd["diff"] < 0.05,
            "3 prose carries (A carried >= 0.95)": arms["A"]["carried"] >= 0.95,
        }
    (HERE / f"scores-{tag}-{slug}.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"subject {slug}: runs {len(runs)}, unverified judge quotes {len(unverified)}")
    print(f"{'arm':4} {'accept':>7} {'pinned':>7} {'carried':>8} {'agree':>6} {'flag':>5} {'reqs':>5} {'scope':>6} {'chars':>7} {'secs':>6}")
    for arm in ARMS:
        a = arms[arm]
        print(f"{arm:4} {a['acceptance']:7.3f} {a['spec_pinned']:7.3f} {a['carried']:8.3f} {a['agreement'] or 0:6.2f} "
              f"{a['flagged_share']:5.2f} {a['requirements']:5.1f} {a['scope_additions']:6.1f} {a['chars']:7.0f} {a['seconds']:6.1f}")
    for key, value in report["tests"].items():
        extra = f", paired p = {value['p_paired']:.4f}" if "p_paired" in value else ""
        print(f"  {key}: diff {value['diff']:+.3f}, one-sided p = {value['p_one_sided']:.4f}{extra}")
    print("per case acceptance:")
    for case_id in CASE:
        print(f"  {case_id:18} " + " ".join(f"{arm} {mean(r['acceptance'] for r in runs if r['case'] == case_id and r['arm'] == arm):.3f}" for arm in ARMS))
    print("rules:", json.dumps(report["rules"], indent=1))


if __name__ == "__main__":
    main()
