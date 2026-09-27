"""Grade finished reviews' revised plans with judge v2 (skips unfinished, missing or already graded ones)."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import judge2
def res(f):
    r = ""
    for l in f.read_text().splitlines():
        try: e = json.loads(l)
        except Exception: continue
        if e.get("type") == "result": r = e.get("result", "")
    return r
jobs, lens = [], json.loads((HERE / "lengths.json").read_text()) if (HERE / "lengths.json").exists() else {}
for f in sorted((HERE / "out").glob("*.jsonl")):
    r = res(f); i = r.find("## Revised plan")
    if i < 0 or len(r[i:].split()) < 150: continue
    sid, rt, arm, k = f.stem.split("_"); d = HERE / "judge" / (f.stem + ".json")
    if not d.exists(): jobs.append((r[i:], sid, rt, d))
judge2.run(jobs, workers=10)
print(len(jobs), "reviews graded this pass")
