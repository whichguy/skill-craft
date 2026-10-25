"""D1: the last passing baseline row per case and driver, against the ShipLoop version origin/main publishes. Read-only.
usage: python3 -B d1_staleness.py <baselines.jsonl>"""
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
last = {}
for row in rows:
    key = f"{row['case']} | {row.get('host')}/{row.get('model')}/{row.get('effort')}"
    if row.get("pass"):
        last[key] = {"shiploop_version": row.get("shiploop_version"), "date": str(row.get("date"))[:10]}
print(json.dumps(last, indent=1, sort_keys=True))
