#!/usr/bin/env python3
"""Compile results.json from conditions.json + results_partial.json + survivor_notes.json."""
import json, os

S = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/bf-ds-ticket-assignment"
B = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/bf-ds-ticket-assignment"

conds = json.load(open(f"{B}/conditions.json"))
part = json.load(open(f"{S}/results_partial.json"))
notes = json.load(open(f"{S}/survivor_notes.json")) if os.path.exists(f"{S}/survivor_notes.json") else {}
meta = json.load(open(f"{S}/meta.json"))

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
    p = part[c["id"]]
    row["witness"] = f"witnesses/{c['id']}.js"
    row["witness_exit_original"] = p.get("witness_exit_original")
    vs = p.get("variants", [])
    witnessed = [v for v in vs if v.get("witness_exit_variant") not in (0, None) and p.get("witness_exit_original") == 0]
    primary = vs[0] if vs else {}
    row["patch"] = primary.get("patch")
    row["variant_note"] = primary.get("note")
    row["witness_exit_variant"] = primary.get("witness_exit_variant")
    row["suite_exit_variant"] = primary.get("suite_exit_variant")
    row["failing_tests"] = primary.get("failing_tests", [])
    row["suite_runs_exit"] = primary.get("suite_runs_exit")
    if len(vs) > 1:
        row["extra_variants"] = vs[1:]
    if not witnessed:
        row["verdict"] = "unwitnessed"
        counts["unwitnessed"] += 1
    else:
        counts["witnessed"] += 1
        survivors = [v for v in witnessed if v.get("suite_exit_variant") == 0]
        if survivors:
            row["verdict"] = "survived"
            counts["survived"] += 1
            row["survivor_variant"] = survivors[0]["note"]
            row.update(notes.get(c["id"], {}))
        else:
            row["verdict"] = "killed"
            counts["killed"] += 1
    rows.append(row)

out = {**meta, "conditions": rows, "counts": counts}
json.dump(out, open(f"{B}/results.json", "w"), indent=1, ensure_ascii=False)
print(counts)
