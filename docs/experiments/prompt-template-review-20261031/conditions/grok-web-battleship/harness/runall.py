import json, os, re, subprocess, sys, time

SCR = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/grok-web-battleship"
OUT = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/grok-web-battleship"
WORK = SCR + "/work"
sys.path.insert(0, SCR)
from mut import MUT

SUITE = ["node", "--test", "--test-reporter=spec"]
LOG = SCR + "/variant_results.jsonl"


def git(*a):
    return subprocess.run(["git", "-C", WORK, *a], capture_output=True, text=True)


def restore():
    assert git("rev-parse", "--show-toplevel").stdout.strip() == WORK, "wrong repo"
    git("checkout", "--", ".")
    git("clean", "-fdq")


def shared_ports_busy():
    p = subprocess.run("lsof -nP -iTCP:3000 -iTCP:3456 -sTCP:LISTEN", shell=True, capture_output=True, text=True)
    return p.stdout.strip()


def run_suite():
    t = time.time()
    p = subprocess.run(SUITE, cwd=WORK, capture_output=True, text=True, timeout=180)
    out = p.stdout + p.stderr
    failing = []
    for line in out.splitlines():
        m = re.match(r"^\s*✖ (.+?) \(\d", line)
        if m and m.group(1) not in failing and not m.group(1).startswith("failing tests"):
            failing.append(m.group(1))
    m = re.search(r"ℹ tests (\d+)", out)
    mp = re.search(r"ℹ pass (\d+)", out)
    mf = re.search(r"ℹ fail (\d+)", out)
    return {"exit": p.returncode, "failing": failing, "tests": int(m.group(1)) if m else None,
            "pass": int(mp.group(1)) if mp else None, "fail": int(mf.group(1)) if mf else None,
            "seconds": round(time.time() - t, 1), "eaddrinuse": "EADDRINUSE" in out, "tail": out[-600:] if p.returncode else ""}


def suite_with_port_guard():
    """Run the suite; wait for shared ports 3000/3456 first; retry (max 2) when a failure looks like port contention."""
    attempts = []
    for _ in range(3):
        for _ in range(30):
            if not shared_ports_busy():
                break
            time.sleep(1)
        r = run_suite()
        busy_after = bool(shared_ports_busy())
        r["shared_ports_busy_after"] = busy_after
        attempts.append(r)
        if r["exit"] == 0:
            break
        if not (r["eaddrinuse"] or busy_after):
            break
    return attempts


def apply(id_):
    for f, old, new in MUT[id_]:
        path = WORK + "/" + f
        s = open(path).read()
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{id_}: edit target occurs {n} times in {f}: {old[:60]!r}")
        open(path, "w").write(s.replace(old, new))


def run_witness(id_):
    t = time.time()
    try:
        p = subprocess.run(["node", f"{OUT}/witnesses/{id_}.js"], capture_output=True, text=True, timeout=120, env={**os.environ, "WORK": WORK})
        return {"exit": p.returncode, "out": (p.stdout + p.stderr).strip()[:400], "seconds": round(time.time() - t, 1)}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "out": "witness timed out", "seconds": 120}


def one(id_):
    restore()
    apply(id_)
    patch = git("diff").stdout
    open(f"{OUT}/patches/{id_}.patch", "w").write(patch)
    syntax = []
    for f in sorted({e[0] for e in MUT[id_]}):
        c = subprocess.run(["node", "--check", WORK + "/" + f], capture_output=True, text=True)
        if c.returncode:
            syntax.append(c.stderr[:200])
    w = run_witness(id_)
    attempts = suite_with_port_guard()
    runs = [attempts[-1]]
    if attempts[-1]["exit"] == 0:
        # survivors: the HTTP tests use a random board, so repeat the suite on the variant
        for _ in range(4):
            runs.append(suite_with_port_guard()[-1])
    rec = {"id": id_, "patch": f"patches/{id_}.patch", "syntax_errors": syntax,
           "witness_exit_variant": w["exit"], "witness_out": w["out"],
           "attempts_first": [{k: a[k] for k in ("exit", "failing", "eaddrinuse", "shared_ports_busy_after")} for a in attempts],
           "suite_runs": [r["exit"] for r in runs],
           "suite_exit_variant": next((r["exit"] for r in runs if r["exit"] != 0), 0),
           "failing_tests": next((r["failing"] for r in runs if r["exit"] != 0), []),
           "suite_tests": runs[0]["tests"], "suite_tail": next((r["tail"] for r in runs if r["exit"] != 0), "")}
    restore()
    open(LOG, "a").write(json.dumps(rec) + "\n")
    return rec


if __name__ == "__main__":
    ids = sys.argv[1:] or list(MUT)
    n = 0
    for i in ids:
        rec = one(i)
        n += 1
        verdict = "KILLED " if rec["suite_exit_variant"] else "SURVIVED"
        print(f"{i:8} witness={rec['witness_exit_variant']} suite={verdict} runs={rec['suite_runs']} fail={rec['failing_tests'][:3]} {rec['syntax_errors'] or ''}", flush=True)
        if n % 6 == 0:
            b = run_suite()
            print("  baseline recheck exit", b["exit"], "tests", b["tests"], flush=True)
            if b["exit"] != 0:
                print("  BASELINE BROKEN", b["tail"])
                break
