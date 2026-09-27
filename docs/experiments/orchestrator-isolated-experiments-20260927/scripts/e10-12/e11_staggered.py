"""E11 add-on b3: same two different results, but B writes+completes 0.6 s after A (A already accepted)."""
import subprocess, sys, time, json
import e11_concurrent as e
rows = []
for rep in range(10):
    run, action = e.fixture(f"b3-{rep}")
    t = time.time() + 1.0
    procs = []
    for delay, summ in ((0.0, "result-from-A"), (0.6, "result-from-B")):
        procs.append(subprocess.Popen([sys.executable, str(e.WORKER_PATH), "write", repr(t + delay), str(run), action,
                                       summ, "complete", str(e.CLI)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, env=e.ENV))
    calls = [dict(zip(("stdout", "stderr"), p.communicate())) | {"exit": p.returncode} for p in procs]
    post = e.inspect(run, action)
    rows.append({"rep": rep, "exits": [c["exit"] for c in calls], **post, "B_stderr": calls[1]["stderr"]})
    print(f"b3 rep{rep}: exits={[c['exit'] for c in calls]} accepted={post['accepted_summary']!r} rows={post['history_rows_for_action']} "
          f"valid={post['state_valid']} B: {calls[1]['stderr'].splitlines()[0] if calls[1]['stderr'] else calls[1]['stdout'].splitlines()[0]}")
open("e11_staggered_results.json", "w").write(json.dumps(rows, indent=1))
