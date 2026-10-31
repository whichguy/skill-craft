import json
CD = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/claude-csv-report"
S = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/claude-csv-report"
cond = json.load(open(CD + "/conditions.json"))
raw = json.load(open(S + "/raw_all.json"))
extras = json.load(open(S + "/raw_extras.json"))
coll = json.load(open(S + "/collateral_all.json"))

SURV = {
 "R-1.3": ("none", "S2 (C3 'two files aggregate rows'); no criterion or case names a repeated FILE",
           "absent: R-1 marks the boundary 'n/a: a repeated FILE is simply read twice', so the test-spec wrote no case; the variant (dedupe the argument list) passes every suite test"),
 "R-2.2": ("none", "S2 (task text 'skip header'); no criterion names 'unvalidated'",
           "absent: every test header is the valid 5-column header; no case feeds a malformed header, so validating the header goes unseen"),
 "R-2.20": ("TC_R2_02 (claims every exact reason string, but all 17 inputs are unpadded)", "S1 (C1: 'valid, padded, boundary and 17 invalid field lists'; padded appears only among the valid ones)",
            "weak: no padded invalid field; the variant echoes the raw padded text in the reason and no case has one"),
 "R-2.23": ("none", "S1 (parse_row); no criterion names that date is unvalidated",
            "absent: negative requirement ('not validated'); all test rows carry well-formed dates, so a date check passes"),
 "R-2.24": ("none", "S1 (parse_row); no criterion names that region is unvalidated",
            "absent: negative requirement; all test rows carry non-empty regions"),
 "R-2.25": ("none", "S1 (parse_row); no criterion names that product is unvalidated",
            "absent: negative requirement; all test rows carry non-empty products"),
 "R-2.31": ("TC_R2_03 (title '-0 is rejected'; its oracle checks units '-0' only)", "S1 (C1)",
            "weak: the spec's '`-0` is rejected as negative' names no field; the case and TC_R2_02 test units '-0' and unit_price '-0.5' only"),
 "R-2.32": ("TC_R2_02 (generic negative unit_price, input '-0.5' only)", "S1 (C1)",
            "weak: only '-0.5' and '-1' exercise the leading-minus rule; no dot-form ('-.5', '-5.') input, which the price regex also admits"),
 "R-3.6": ("TC_R3_02 (claims 'half-up on Decimal, not float'; one row 2.675)", "S2 (C2; task 'aggregate with Decimal')",
           "weak: the case exercises float rounding of one value, not float accumulation; no multi-row sum where binary-float addition drifts across a half cent"),
 "R-3.8": ("TC_R3_02 (claims 'half-up')", "S2 (C2; task 'quantize ROUND_HALF_UP')",
           "weak assertion: 2.675 rounds to 2.68 under half-even as well (7 is odd), so the spec's own example cannot tell half-up from half-even; it only kills half-down and float rounding"),
 "R-3.15": ("none (nearest: TC_R3_01, whose exact line has regions already in sorted order)", "S2 (task 'nested keys sorted'); C2 does not name it",
            "weak: the only multi-region exact-output case feeds north then south, so insertion order equals sorted order; ST_1 compares through dict equality, which ignores order"),
 "R-3.16": ("none (nearest: TC_R3_01, whose only product is 'widget')", "S2 (task 'nested keys sorted'); C2 does not name it",
            "absent: no exact-output case has two products; ST_1 has two products but compares through dict equality, which ignores order"),
 "R-4.2": ("none (TC_R4_02 has one bad row; TC_R4_05 has one bad row per file)", "S3 (C4: 'Skipped rows are reported')",
           "absent: no case has two skipped rows in the same file, so reporting only the first per file goes unseen"),
 "R-4.9": ("TC_R4_05 (weak: both files bad); ST_1 (bad row only in the last file)", "S3 (C4; task 'exit 2 when any row was skipped')",
           "weak: every multi-file case that expects exit 2 has a skipped row in the last file; a variant that keeps only the last file's skip count passes"),
 "R-5.3": ("none (R-5 lists 'unreadable' in prose; no Failure case for it)", "S4 (C5 lists missing, directory, invalid UTF-8, 200000-char field, good-then-missing, bad-row-then-missing)",
           "absent: no permission-denied case; the variant changes the wording for PermissionError only"),
 "R-6.5": ("TC_R6_02 (header-only file next to a normal file)", "S2 (C3: 'header-only plus a normal file equals the normal file alone')",
           "weak: the case runs only the order (header-only, normal); the variant clears totals when a header-only file follows a normal one"),
 "R-6.6": ("none (TC_R6_03 runs a zero-byte file alone)", "S2 (C3 names zero-byte alone, not combined)",
           "absent: the spec's 'zero-byte file behaves the same' for the combined case has no case; the variant clears totals when a zero-byte file is read"),
}

out_rows = []
counts = {"candidates": 0, "witnessed": 0, "killed": 0, "survived": 0, "unwitnessed": 0, "excluded": 0}
for c in cond:
    row = dict(c)
    cid = c["id"]
    if not c["candidate"]:
        row["verdict"] = "excluded"
        counts["excluded"] += 1
        out_rows.append(row)
        continue
    counts["candidates"] += 1
    r = raw[cid]
    witnessed = r["witness_exit_original"] == 0 and r["witness_exit_variant"] != 0
    row["witness"] = "witnesses/%s.py" % cid
    row["witness_exit_original"] = r["witness_exit_original"]
    row["witness_exit_variant"] = r["witness_exit_variant"]
    row["suite_exit_variant"] = r["suite_exit_variant"]
    row["failing_tests"] = r["failing_tests"]
    row["patch"] = "patches/%s.patch" % cid
    row["collateral_conditions_also_violated"] = coll.get(cid, [])
    if not witnessed:
        row["verdict"] = "unwitnessed"
        counts["unwitnessed"] += 1
    else:
        counts["witnessed"] += 1
        if r["suite_exit_variant"] != 0:
            row["verdict"] = "killed"
            counts["killed"] += 1
        else:
            row["verdict"] = "survived"
            counts["survived"] += 1
            cb, step, why = SURV[cid]
            row["claimed_by"] = cb
            row["owning_step"] = step
            row["why_survived"] = why
    out_rows.append(row)

assert set(SURV) == {r["id"] for r in out_rows if r["verdict"] == "survived"}, (set(SURV) ^ {r["id"] for r in out_rows if r["verdict"] == "survived"})
clean_kills = sum(1 for r in out_rows if r["verdict"] == "killed" and not r["collateral_conditions_also_violated"])

res = {
 "run": "~/e2e-runs/20261024/gate-290-b60ed7-claude-csv-report",
 "suite_command": "python3 -m unittest -v   (run from the repo root; the widest command the run itself ran: tests/nav-daf939...-verify1.md and nav-f97d9f...-verify1.md, 31 tests)",
 "baseline_exit": 0,
 "baseline_summary": "Ran 31 tests in ~0.6s, OK (on the scratch copy, python 3.15.1)",
 "original_hash_before": open(S + "/hash_before.txt").read().split()[0],
 "original_hash_after": open(S + "/hash_after.txt").read().split()[0],
 "conditions_sha256": open(CD + "/conditions.sha256").read().split()[0],
 "copy_note": "The copy's .git pointer file was replaced by a fresh 'git init' + one baseline commit, so git diff/checkout/clean never touch the original repository metadata. __pycache__ was removed from the copy and PYTHONDONTWRITEBYTECODE=1 was set for every run.",
 "conditions": out_rows,
 "counts": counts,
 "kill_rate": round(counts["killed"] / counts["witnessed"], 4),
 "survival_rate": round(counts["survived"] / counts["witnessed"], 4),
 "killed_without_collateral": clean_kills,
 "killed_with_collateral": counts["killed"] - clean_kills,
 "requirements_with_a_survivor": sorted({r["requirement"] for r in out_rows if r["verdict"] == "survived"}),
 "survivor_kinds": {k: sorted(r["id"] for r in out_rows if r["verdict"] == "survived" and r["kind"] == k) for k in sorted({r["kind"] for r in out_rows if r["verdict"] == "survived"})},
 "survivor_claim_split": {
    "claimed_by_a_case_but_weak": sorted(i for i, v in SURV.items() if not v[0].startswith("none")),
    "absent_no_case_claims_it": sorted(i for i, v in SURV.items() if v[0].startswith("none")),
 },
 "extra_probes_not_in_rate": {
    "R-4.5x": {"what": "a bad record that itself spans two lines is reported on its start line (variant numbers it by its end line)", **extras["R-4.5x"],
               "result": "survived (suite passes while the witness fails): the 'starts on' half of R-4's line rule is untested; R-4.5's literal example (valid multi-line record, then a bad one on line 4) is killed"},
    "R-2.35x": {"what": "BOM: encoding utf-8 instead of utf-8-sig", **extras["R-2.35x"],
                "result": "equivalent mutant: the header is skipped unvalidated, so a BOM never reaches data; the witness and the suite both pass. R-2.35 was therefore violated with encoding='ascii' (BOM raises a decode error)"},
 },
 "notes": [
    "Collateral: field 'collateral_conditions_also_violated' lists the other candidate conditions whose witness also fails on that condition's variant (computed for all 91). For killed conditions with collateral, the kill may come from a sibling condition's test; no survivor has collateral.",
    "Mutants for example-driven conditions (specific values such as units '-1', '-0', unit_price '.5') are literal-narrow special cases; mutants for rule-driven conditions (sorting, half-up, line numbering, exit codes) are natural general faults.",
    "R-2.3 variant rejects prices with exactly two fractional digits (any '2.50'); it is killed by 13 tests.",
    "Nothing from the network was installed; no model was called; no listener was started (the suite and witnesses use temp dirs and subprocesses only), so the port range 41400-41499 was not used.",
 ],
}
json.dump(res, open(CD + "/results.json", "w"), indent=1)
print(counts, res["kill_rate"], res["survival_rate"], clean_kills)
print(res["requirements_with_a_survivor"])
print(res["survivor_kinds"])
print(res["survivor_claim_split"])
