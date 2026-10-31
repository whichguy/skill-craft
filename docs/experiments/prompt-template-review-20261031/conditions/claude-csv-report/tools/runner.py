#!/usr/bin/env python3
"""Run every candidate condition: witness on original, mutate, witness on variant, full suite, restore."""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutants import M, X  # noqa: E402

S = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/claude-csv-report"
WORK = S + "/work"
CD = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/claude-csv-report"
ENV = dict(os.environ, WORK=WORK, PYTHONDONTWRITEBYTECODE="1", TMPDIR=S + "/tmp")
SUITE = ["python3", "-m", "unittest", "-v"]
GIT = ["git", "-C", WORK]


def sh(cmd, cwd=None, timeout=240):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=ENV, timeout=timeout)


def clean():
    sh(GIT + ["checkout", "--", "."])
    sh(GIT + ["clean", "-fdq"])
    for root, dirs, _ in os.walk(WORK):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)


def suite():
    try:
        r = sh(SUITE, cwd=WORK, timeout=240)
    except subprocess.TimeoutExpired:
        return 124, ["TIMEOUT"], ""
    text = r.stderr + r.stdout
    failing = []
    for m in re.finditer(r"^(FAIL|ERROR): (\S+) \(([^)]*)\)", text, re.M):
        name = "%s (%s)" % (m.group(2), m.group(3))
        if name not in failing:
            failing.append(name)
    last = [l for l in text.strip().splitlines() if l.strip()][-1:] or [""]
    return r.returncode, failing, text.strip().splitlines()[-3:] and " | ".join(text.strip().splitlines()[-3:])


def witness(cid):
    try:
        r = sh([sys.executable, cid + ".py"], cwd=CD + "/witnesses", timeout=120)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    return r.returncode, (r.stdout + r.stderr).strip()[:300]


def apply(cid):
    path = WORK + "/report.py"
    src = open(path).read()
    for old, new in (M.get(cid) or X[cid]):
        n = src.count(old)
        if n != 1:
            raise SystemExit("%s: pattern found %d times: %r" % (cid, n, old[:80]))
        src = src.replace(old, new)
    open(path, "w").write(src)
    r = sh([sys.executable, "-c", "import ast,sys;ast.parse(open(sys.argv[1]).read())", path])
    if r.returncode:
        raise SystemExit("%s: syntax error %s" % (cid, r.stderr))


def main():
    cond = json.load(open(CD + "/conditions.json"))
    ids = [c["id"] for c in cond if c["candidate"]]
    only = sys.argv[1:]
    mode = "all"
    out = {}
    clean()
    base = suite()
    print("baseline suite", base[0], base[2], flush=True)
    if base[0] != 0:
        raise SystemExit("baseline suite fails")
    # witnesses on original
    orig = {}
    for cid in ids:
        orig[cid] = witness(cid)
    bad = [cid for cid in ids if orig[cid][0] != 0]
    print("witnesses failing on original:", [(c, orig[c][1][:120]) for c in bad], flush=True)
    missing = [cid for cid in ids if cid not in M]
    print("no mutant for:", missing, flush=True)
    todo = only or ids
    k = 0
    for cid in todo:
        if cid not in M:
            continue
        clean()
        apply(cid)
        diff = sh(GIT + ["diff"]).stdout
        open("%s/patches/%s.patch" % (CD, cid), "w").write(diff)
        wc, wmsg = witness(cid)
        sc, failing, tail = suite()
        out[cid] = {"witness_exit_original": orig[cid][0], "witness_exit_variant": wc, "witness_msg_variant": wmsg,
                    "suite_exit_variant": sc, "failing_tests": failing, "suite_tail": tail}
        print(cid, "orig=%s variant=%s suite=%s failing=%d" % (orig[cid][0], wc, sc, len(failing)), flush=True)
        clean()
        k += 1
        if k % 5 == 0:
            b = suite()
            if b[0] != 0:
                raise SystemExit("baseline suite broke after restore at %s" % cid)
            out.setdefault("_baseline_checks", []).append({"after": cid, "exit": b[0], "tail": b[2]})
    clean()
    final = suite()
    out["_final_baseline"] = {"exit": final[0], "tail": final[2]}
    out["_orig_witness_fail"] = bad
    json.dump(out, open(S + "/raw_%s.json" % ("part" if only else "all"), "w"), indent=1)


def extras():
    clean()
    out = {}
    for cid, wit in (("R-4.5x", "R-4.5x"), ("R-2.35x", "R-2.35")):
        clean()
        o = witness(wit)
        apply(cid)
        open("%s/patches/%s.patch" % (CD, cid), "w").write(sh(GIT + ["diff"]).stdout)
        wc, wmsg = witness(wit)
        sc, failing, tail = suite()
        out[cid] = {"witness": wit, "witness_exit_original": o[0], "witness_exit_variant": wc, "witness_msg_variant": wmsg,
                    "suite_exit_variant": sc, "failing_tests": failing, "suite_tail": tail}
        print(cid, out[cid]["witness_exit_original"], wc, sc, flush=True)
        clean()
    json.dump(out, open(S + "/raw_extras.json", "w"), indent=1)


if __name__ == "__main__":
    if sys.argv[1:] == ["extras"]:
        extras()
    else:
        main()
