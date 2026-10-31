import json, subprocess, sys, re

SCR = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/grok-web-battleship"
OUT = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/grok-web-battleship"
sys.path.insert(0, SCR)
from survivors import INFO, CLAIMS_CHECKED  # noqa

conds = json.load(open(OUT + "/conditions.json"))
base_w = json.load(open(SCR + "/witness_baseline.json"))
var = {}
for line in open(SCR + "/variant_results.jsonl"):
    r = json.loads(line)
    var[r["id"]] = r  # last record wins (reruns)
stab = {}
for line in open(SCR + "/stability.jsonl"):
    r = json.loads(line)
    stab[r["id"]] = r
after = open(SCR + "/original_hash_after.txt").read().strip().split()[0]
before = open(SCR + "/original_hash_before.txt").read().strip().split()[0]
b = open(SCR + "/baseline.out").read()
summary = "tests %s pass %s fail %s" % (re.search(r"ℹ tests (\d+)", b).group(1), re.search(r"ℹ pass (\d+)", b).group(1), re.search(r"ℹ fail (\d+)", b).group(1))

rows = []
counts = {"candidates": 0, "witnessed": 0, "killed": 0, "survived": 0, "unwitnessed": 0, "excluded": 0}
for c in conds:
    row = dict(c)
    if not c["candidate"]:
        row["verdict"] = "excluded"
        counts["excluded"] += 1
        rows.append(row)
        continue
    counts["candidates"] += 1
    i = c["id"]
    v = var[i]
    wo = base_w[i]["exit"]
    wv = v["witness_exit_variant"]
    row.update({
        "witness": f"witnesses/{i}.js",
        "witness_exit_original": wo,
        "witness_exit_variant": wv,
        "suite_exit_variant": v["suite_exit_variant"],
        "suite_runs_variant": v["suite_runs"],
        "failing_tests": v["failing_tests"],
        "patch": v["patch"],
    })
    if i in stab:
        st = stab[i]
        frac = st["genuine_failures"] / st["runs"]
        row.update({"kill_fraction": round(frac, 3), "stability_runs": st["runs"],
                    "noise_only_failures": st["noise_only_failures"], "stochastic": 0 < frac < 1})
        row["suite_exit_variant"] = 1 if frac >= 0.5 else 0
        row["failing_tests"] = sorted(st["failing_tests"]) if frac >= 0.5 else []
        v = dict(v, suite_exit_variant=row["suite_exit_variant"])
    witnessed = wo == 0 and wv == 1
    if not witnessed:
        row["verdict"] = "unwitnessed"
        row["unwitnessed_reason"] = f"witness exit original {wo}, variant {wv}: {v['witness_out'][:200]}"
        counts["unwitnessed"] += 1
    else:
        counts["witnessed"] += 1
        if v["suite_exit_variant"] != 0:
            row["verdict"] = "killed"
            counts["killed"] += 1
        else:
            row["verdict"] = "survived"
            counts["survived"] += 1
            row.update(INFO[i])
    rows.append(row)

res = {
    "run": "~/e2e-runs/20261025/gate-2132-f7ba78-grok-web/battleship (work-20261026-045417-6440d1 worktree)",
    "suite_command": "node --test --test-reporter=spec   (cwd: the worktree copy; the widest command the run itself ran, nav-717d... verify1)",
    "baseline_exit": 0,
    "baseline_summary": summary,
    "original_hash_before": before,
    "original_hash_after": after,
    "notes": {
        "copy": "the worktree was copied to scratch; its .git worktree pointer file was replaced by a fresh git repo in the copy so that diff/checkout/clean never touch the original's git metadata",
        "survivor_reruns": "a variant whose first suite run passed was rerun four more times (the HTTP tests use a random board); survived = 5 of 5 passes",
        "claims_checked": CLAIMS_CHECKED,
        "stability_rule": "stability.jsonl: a variant whose first run failed only in the shared-port tests (TC-2), or whose kill depends on the random board, was rerun 12 to 60 times; killed means a genuine failure in at least half of the runs; kill_fraction is recorded; a failure of only 'R-2 (TC-2) port' or 'TC-2 (a)' on a non-port variant is port contention with other workers (shared ports 3000 and 3456), counted as noise_only_failures",
        "replay": "WORK=<copy> node witnesses/<id>.js (exit 0 holds, 1 violated, 3 witness error); apply patches/<id>.patch to a copy of the worktree made as in notes.copy, then run node --test --test-reporter=spec in it",
        "natural_gap": "R-4.6 is checked with POST (the spec's confirm line). On the unchanged copy PUT, DELETE and PATCH /api/new return 404, not the 405 the sentence 'A non-GET method returns 405' states; this is a gap of the product itself and no variant was needed to find it",
    },
    "conditions": rows,
    "counts": counts,
}
json.dump(res, open(OUT + "/results.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(counts))
for r in rows:
    if r.get("verdict") in ("survived", "unwitnessed"):
        print(r["id"], r["verdict"], r["kind"], "|", r["quote"][:70])
