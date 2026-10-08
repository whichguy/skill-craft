#!/usr/bin/env python3
"""Recount the return receipts of the recorded E2E runs (batch 1008, item B3). Read-only.

For every run under /Users/dadleet/e2e-runs/*/*/.shiploop-runs/*/ that has a return-receipt.md, record the return
kind, whether the start was clean, how many consumer checks release-plan recorded and how many of those commands name
the source checkout's path or the work area's path, and where each release-verify test record ran its commands.
Prints the JSON that is committed next to this script as receipt-recount.json:

    python3 recount.py > receipt-recount.json
"""
import glob
import json
import os
import re
import sys

BASE = "/Users/dadleet/e2e-runs"


def record(path):
    text = open(path, encoding="utf-8").read()
    return json.loads(re.search(r"```shiploop-state\n(.*?)\n```", text, re.S).group(1))


rows = []
for receipt_path in sorted(glob.glob(BASE + "/*/*/.shiploop-runs/*/return-receipt.md")):
    work = os.path.dirname(receipt_path)
    receipt, manifest, state = record(receipt_path), record(work + "/workspace.md"), record(work + "/run/state.md")
    source, worktree = manifest["source_repo"], manifest["worktree"]
    plan_action = next((h["action"] for h in reversed(state["history"])
                        if h["stage"] == "release-plan" and h.get("outcome") == "done"), None)
    result = state["accepted"].get(plan_action, {}) if plan_action else {}
    result = result.get("result", result)
    commands = [row["command"] for row in result.get("consumer_checks") or ()]
    verify = []
    for path in sorted(glob.glob(work + "/run/tests/*verify*.md")):
        found = record(path)
        if found.get("stage") == "release-verify":
            verify.append({"cwd_is_work_area": found["cwd"] == worktree, "disposition": found.get("disposition"),
                           "has_observed": "observed" in found})
    rows.append({
        "run": os.path.relpath(work, BASE).split("/.shiploop-runs/")[0],
        "receipt_kind": receipt["kind"], "receipt_status": receipt["status"],
        "start_clean": manifest["start_clean"],
        "follow_up_receipt": "previous_receipt" in receipt,
        "consumer_checks": len(commands),
        "consumer_checks_na": bool(result.get("consumer_checks_na")),
        "commands_naming_source_path": sum(1 for command in commands if source in command),
        "commands_naming_work_area_path": sum(1 for command in commands if worktree in command),
        "release_verify_records": verify,
    })

summary = {
    "runs_with_a_return_receipt": len(rows),
    "receipt_kinds": {k: sum(1 for r in rows if r["receipt_kind"] == k) for k in sorted({r["receipt_kind"] for r in rows})},
    "start_clean_true": sum(1 for r in rows if r["start_clean"] is True),
    "runs_with_a_follow_up_receipt": sum(1 for r in rows if r["follow_up_receipt"]),
    "runs_whose_consumer_checks_name_the_source_path": sum(1 for r in rows if r["commands_naming_source_path"]),
    "runs_whose_consumer_checks_name_the_work_area_path": sum(1 for r in rows if r["commands_naming_work_area_path"]),
    "runs_whose_every_release_verify_record_ran_in_the_work_area": sum(
        1 for r in rows if r["release_verify_records"] and all(v["cwd_is_work_area"] for v in r["release_verify_records"])),
    "runs_with_no_release_verify_record": sum(1 for r in rows if not r["release_verify_records"]),
    "release_verify_records_with_an_observed_key": sum(v["has_observed"] for r in rows for v in r["release_verify_records"]),
}
meta = {
    "recounted": "2026-10-08",
    "what": "return receipts of the recorded E2E runs, for the release-verify observes the returned result change (B3)",
    "glob": BASE + "/*/*/.shiploop-runs/*/return-receipt.md",
    "reading": ("disposition null is a release-verify record written before the disposition field existed; "
                "has_observed false everywhere because the observed key is new in this batch; a command naming the "
                "source path runs in the user's checkout whatever directory release-verify uses"),
    "script": "recount.py in this directory",
}
json.dump({"meta": meta, "summary": summary, "runs": rows}, sys.stdout, indent=1)
print()
