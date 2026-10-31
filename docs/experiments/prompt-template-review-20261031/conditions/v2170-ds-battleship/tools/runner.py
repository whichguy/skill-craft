#!/usr/bin/env python3
"""runner.py <workdir> <shard-name> <id> [<id>...]: per condition run witness on the unchanged copy, apply the
patch, run witness + full local suite on the variant, record, restore. Appends JSON lines to log_<shard>.jsonl."""
import subprocess, sys, os, json, time, re
S = os.path.dirname(os.path.abspath(__file__))
O = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship'
work, shard, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
env = dict(os.environ, WORK=work)
def git(*a): return subprocess.run(['git', '-C', work, *a], capture_output=True, text=True)
def restore(): git('checkout', '--', '.'); git('clean', '-fdq')
def witness(wid):
    f = os.path.join(O, 'witnesses', wid + '.js')
    try:
        p = subprocess.run(['node', f], env=env, capture_output=True, text=True, timeout=150, cwd=O + '/witnesses')
        return p.returncode, (p.stdout + p.stderr).strip()[-300:]
    except subprocess.TimeoutExpired:
        return 124, 'witness timeout'
def suite(tag):
    out = os.path.join(S, 'logs', f'{shard}_{tag}.txt')
    p = subprocess.run([os.path.join(S, 'run_suite.sh'), work, out])
    txt = open(out, errors='replace').read()
    fails = sorted(set(re.sub(r'\s*\([\d.]+ms\)$', '', m.strip()) for m in re.findall(r'^\s*✖ (.+)$', txt, re.M)) - {'failing tests:'})
    # keep only leaf test names (drop file-level / parent duplicates by keeping all, de-duplicated)
    summ = re.findall(r'^### (node --test.*)$|^### exit=(\d+)$|^ℹ (tests|pass|fail) (\d+)$', txt, re.M)
    return p.returncode, fails, txt
os.makedirs(os.path.join(S, 'logs'), exist_ok=True)
logf = open(os.path.join(S, f'log_{shard}.jsonl'), 'a')
count = 0
for wid in ids:
    restore()
    t0 = time.time()
    w0, w0out = witness(wid)
    patch = os.path.join(O, 'patches', wid + '.patch')
    a = git('apply', patch)
    if a.returncode:
        rec = dict(id=wid, error='patch did not apply: ' + a.stderr[:200]); logf.write(json.dumps(rec) + '\n'); logf.flush(); continue
    w1, w1out = witness(wid)
    sx, fails, txt = suite(wid.replace('R-', ''))
    restore()
    rec = dict(id=wid, witness_exit_original=w0, witness_out_original=w0out, witness_exit_variant=w1, witness_out_variant=w1out,
               suite_exit_variant=sx, failing_tests=fails, secs=round(time.time() - t0, 1))
    logf.write(json.dumps(rec, ensure_ascii=False) + '\n'); logf.flush()
    print(wid, 'orig', w0, 'variant', w1, 'suite', sx, len(fails), 'failing', flush=True)
    count += 1
    if count % 6 == 0:
        bx, bf, _ = suite('baseline')
        rec = dict(baseline_after=wid, suite_exit=bx, failing_tests=bf)
        logf.write(json.dumps(rec) + '\n'); logf.flush()
        print('  baseline after', wid, 'exit', bx, flush=True)
restore()
