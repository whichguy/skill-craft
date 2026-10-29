"""Per run trace: check-only and complete calls on inner, Improve and outer stages, refusals after a passing check-only, and
refusal classes. Usage: trace_check_pairs.py TRACE [...]"""
import collections, json, re, sys

INNER = {"step-plan", "test-spec", "validate-existing", "implement", "test", "document", "verify", "carry-forward"}
CLASSES = [("loop", r"Until Loop|receipt|loop is still active|has not run"),
           ("tests", r"base run|candidate|floor|mutation|step proof|Proof|recorded command|ShipLoop ran"),
           ("lint", r"lint"),
           ("shape", r"unsupported field|must be|needs |is missing|bound|characters|refuses|names no|lists")]

def cls(err):
    for name, pat in CLASSES:
        if re.search(pat, err or ""):
            return name
    return "other"

for path in sys.argv[1:]:
    events = [json.loads(l) for l in open(path) if l.strip()]
    cmds = [e for e in events if e.get("kind") == "command" and e.get("verb") == "complete"]
    c = collections.Counter()
    after_yes = []
    post_loop = collections.Counter()
    last = {}
    for e in cmds:
        st = (e.get("stage") or [None, None])[0]
        where = "inner" if st in INNER else "improve" if st == "improve" else "outer"
        chk = bool(e.get("check_only"))
        ok = e.get("exit") == 0
        c[("check" if chk else "complete", where, "ok" if ok else "no")] += 1
        a = e.get("action")
        if not chk and not ok:
            k = cls(e.get("error"))
            c[("refusal-class", k)] += 1
            prev = last.get(a)
            if prev and prev.get("check_only") and prev.get("exit") == 0:
                after_yes.append((st, k, (e.get("error") or "")[:110]))
        last[a] = e
    print("==", path.split("/e2e-runs")[-1])
    for k in sorted(c, key=str):
        print("  ", k, c[k])
    print("   refused complete right after a passing check-only on the same action:", len(after_yes))
    for row in after_yes:
        print("     ", row)
