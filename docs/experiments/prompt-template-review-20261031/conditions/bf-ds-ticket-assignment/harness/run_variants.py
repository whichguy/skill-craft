#!/usr/bin/env python3
"""Apply each condition's variant to the scratch copy, run witness + full suite, restore, record."""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variants import V  # noqa: E402

S = "/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/bf-ds-ticket-assignment"
B = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/bf-ds-ticket-assignment"
WORK = f"{S}/work"
OUTP = f"{S}/results_partial.json"
env = {**os.environ, "WORK": WORK}


def sh(cmd, cwd=None, timeout=300, check=False):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
    return r


def restore():
    sh(["git", "-C", WORK, "checkout", "--", "."])
    sh(["git", "-C", WORK, "clean", "-fdq"])


def apply_edits(edits):
    for rel, old, new in edits:
        p = os.path.join(WORK, rel)
        text = open(p).read()
        n = text.count(old)
        if n != 1:
            raise RuntimeError(f"{rel}: expected exactly one match, found {n}: {old[:80]!r}")
        open(p, "w").write(text.replace(old, new))


def witness(id_, timeout=120):
    t = time.time()
    try:
        r = subprocess.run(["node", f"{B}/witnesses/{id_}.js"], cwd=B, env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stderr.strip()[-600:], round(time.time() - t, 1)
    except subprocess.TimeoutExpired:
        return 124, "timeout", round(time.time() - t, 1)


FAIL_RE = re.compile(r"^\s*✖ (.*?) \(([\d.]+)ms\)\s*$", re.M)


def suite():
    r = subprocess.run("npm test", cwd=WORK, shell=True, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    names = []
    for m in FAIL_RE.finditer(out):
        if m.group(1) not in names:
            names.append(m.group(1))
    summary = {k: None for k in ("tests", "pass", "fail")}
    for k in summary:
        m = re.search(rf"ℹ {k} (\d+)", out)
        if m:
            summary[k] = int(m.group(1))
    return r.returncode, names, summary, out


def run_variant(id_, idx, note, edits):
    restore()
    apply_edits(edits)
    diff = sh(["git", "-C", WORK, "diff"]).stdout
    suffix = "" if idx == 0 else f".extra{idx}"
    patch_path = f"{B}/patches/{id_}{suffix}.patch"
    open(patch_path, "w").write(diff)
    wcode, wmsg, wsecs = witness(id_)
    code, names, summ, out = suite()
    runs = [code]
    flaky = False
    if code != 0:
        code2, names2, summ2, out2 = suite()
        runs.append(code2)
        if code2 == 0:
            code3, names3, summ3, out3 = suite()
            runs.append(code3)
            flaky = True
            if code3 != 0:
                names = names3
        else:
            names = list(dict.fromkeys(names + names2))
    restore()
    return {
        "note": note,
        "patch": os.path.relpath(patch_path, os.path.dirname(B)),
        "witness_exit_variant": wcode,
        "witness_variant_message": wmsg,
        "suite_runs_exit": runs,
        "suite_exit_variant": 0 if (code == 0 or (flaky and runs[-1] == 0)) else (runs[-1] if runs[-1] else code),
        "suite_summary": summ,
        "failing_tests": names[:40],
        "flaky": flaky,
    }


def main():
    conds = [r for r in json.load(open(f"{B}/conditions.json")) if r["candidate"]]
    only = sys.argv[1:]
    results = json.load(open(OUTP)) if os.path.exists(OUTP) else {}
    restore()
    for i, c in enumerate(conds):
        id_ = c["id"]
        if only and id_ not in only:
            continue
        if id_ in results and not only:
            continue
        if id_ not in V:
            results[id_] = {"error": "no variant defined"}
            continue
        restore()
        wo, wo_msg, wo_secs = witness(id_)
        rec = {"witness_exit_original": wo, "witness_original_message": wo_msg, "variants": []}
        if wo != 0:
            rec["note"] = "witness fails on the unchanged copy"
        else:
            for idx, (note, edits) in enumerate(V[id_]):
                try:
                    rec["variants"].append(run_variant(id_, idx, note, edits))
                except Exception as e:  # noqa: BLE001
                    restore()
                    rec["variants"].append({"note": note, "error": str(e)})
        results[id_] = rec
        json.dump(results, open(OUTP, "w"), indent=1)
        v = rec["variants"][0] if rec["variants"] else {}
        print(f"{id_}: orig={wo} variant_witness={v.get('witness_exit_variant')} suite={v.get('suite_runs_exit')} fails={len(v.get('failing_tests', []))}", flush=True)
        if (i + 1) % 5 == 0:
            restore()
            code, _, summ, _ = suite()
            print(f"  sanity baseline after {id_}: exit={code} {summ}", flush=True)
    restore()


if __name__ == "__main__":
    main()
