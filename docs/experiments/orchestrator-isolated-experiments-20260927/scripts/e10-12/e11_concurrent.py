"""E11: concurrent callbacks against one run (real CLI processes, released on a shared start instant).

Scenarios (10 fresh runs each, run parked at discovery):
  a  : two identical `complete` calls; result file written once before launch
  b1 : two `complete` calls; each process writes its own (different) result to the one generated
       inbox path with a plain write, then calls complete (what two hosts would do)
  b2 : as b1 but each writes atomically (temp file + os.replace)
  c  : 10 concurrent `next` + one `complete` (result prewritten)
"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "src/skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
ENV = {**os.environ, "SHIPLOOP_KEEPALIVE": "off", "SHIPLOOP_KEEPALIVE_HOME": str(HERE / "keepalive-home"),
       "PYTHONDONTWRITEBYTECODE": "1"}
os.environ.update(SHIPLOOP_KEEPALIVE="off", SHIPLOOP_KEEPALIVE_HOME=ENV["SHIPLOOP_KEEPALIVE_HOME"])
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav, shiploop_store as store  # noqa: E402

WORKER = r'''
import os, sys, time, subprocess
mode, start, run, action, summary, verb, cli = sys.argv[1:8]
path = os.path.join(run, "inbox", action + ".md")
text = "---\n" if False else None
while time.time() < float(start):
    pass
if mode in ("write", "atomic"):
    sys.path.insert(0, os.path.dirname(cli))
    import shiploop_store as store
    body = store.dumps({"outcome": "done", "summary": summary}, "result")
    if mode == "write":
        with open(path, "w") as f:
            f.write(body)
    else:
        tmp = path + ".tmp-" + str(os.getpid())
        with open(tmp, "w") as f:
            f.write(body)
        os.replace(tmp, path)
args = [sys.executable, cli, verb, "--run-dir", run]
if verb == "complete":
    args += ["--action", action, "--result", path]
os.execv(sys.executable, args)
'''
WORKER_PATH = HERE / "e11_worker.py"
WORKER_PATH.write_text(WORKER)
WORK = HERE / "e11-work"


def fixture(tag):
    base = Path(tempfile.mkdtemp(prefix=tag + "-", dir=WORK))
    repo, run = base / "repo", base / "run"
    repo.mkdir(); run.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)
    g("init", "-q"); g("config", "user.email", "e@x.invalid"); g("config", "user.name", "E")
    (repo / "a.py").write_text("x = 1\n"); g("add", "-A"); g("commit", "-qm", "base")
    nav.save(run, nav.new_state(str(repo), "E11 concurrency fixture.", lint_option="off"))
    s = store.read_record(run / "state.md"); a = nav.current_action(s)["id"]
    p = run / "inbox" / (a + ".md"); p.parent.mkdir(exist_ok=True)
    p.write_text(store.dumps({"outcome": "done", "summary": "intake"}, "result"))
    r = subprocess.run([sys.executable, str(CLI), "complete", "--run-dir", str(run), "--action", a, "--result", str(p)],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    s = store.read_record(run / "state.md")
    assert nav.current_stage(s) == "discovery"
    return run, nav.current_action(s)["id"]


def launch(specs, run, action):
    start = time.time() + 1.0
    procs = []
    for mode, summary, verb in specs:
        procs.append(subprocess.Popen([sys.executable, str(WORKER_PATH), mode, repr(start), str(run), action, summary,
                                       verb, str(CLI)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                      env=ENV))
    out = []
    for (mode, summary, verb), p in zip(specs, procs):
        so, se = p.communicate(timeout=120)
        out.append({"verb": verb, "wrote": summary if mode != "none" else None, "exit": p.returncode,
                    "stdout_head": so.splitlines()[0] if so else "", "stderr": se.strip()})
    return out


def inspect(run, action):
    rec = {}
    try:
        s = store.read_record(run / "state.md")
        nav.validate(s)
        rec["state_valid"] = True
    except Exception as exc:  # noqa: BLE001
        rec["state_valid"] = f"INVALID: {exc}"
        return rec
    rows = [r for r in s["history"] if r.get("action") == action]
    rec["history_rows_for_action"] = len(rows)
    rec["history_len"] = len(s["history"])
    actions = [r.get("action") for r in s["history"]]
    rec["duplicate_history_actions"] = len(actions) - len(set(actions))
    rec["accepted_summary"] = (s["accepted"].get(action) or {}).get("summary")
    rec["stage_now"] = nav.current_stage(s)
    rec["revision"] = s["revision"]
    rec["callback_attempts"] = (run / "callback-attempts").read_text().strip() if (run / "callback-attempts").exists() else None
    rec["leftover"] = sorted(p.name for p in run.iterdir() if p.name.startswith((".tx", "tx", ".tmp")) or "journal" in p.name)
    return rec


SCEN = {
    "a": ("prewrite", [("none", "same", "complete"), ("none", "same", "complete")]),
    "b1": (None, [("write", "result-from-A", "complete"), ("write", "result-from-B", "complete")]),
    "b2": (None, [("atomic", "result-from-A", "complete"), ("atomic", "result-from-B", "complete")]),
    "c": ("prewrite", [("none", "", "next")] * 10 + [("none", "same", "complete")]),
}


def main():
    WORK.mkdir(exist_ok=True)
    allrows = []
    for name, (pre, specs) in SCEN.items():
        for rep in range(10):
            run, action = fixture(f"{name}-{rep}")
            if pre:
                (run / "inbox" / (action + ".md")).write_text(store.dumps({"outcome": "done", "summary": "same"}, "result"))
            calls = launch(specs, run, action)
            post = inspect(run, action)
            row = {"scenario": name, "rep": rep, "calls": calls, **post}
            allrows.append(row)
            comp = [c for c in calls if c["verb"] == "complete"]
            nexts = [c for c in calls if c["verb"] == "next"]
            lock_err = any("lock" in c["stderr"].lower() for c in calls)
            silent = [c["wrote"] for c in comp if c["exit"] == 0 and c["wrote"] not in (None, "same")
                      and c["wrote"] != post.get("accepted_summary")]
            print(f"{name} rep{rep}: complete exits={[c['exit'] for c in comp]} next exits={[c['exit'] for c in nexts] or '-'} "
                  f"valid={post['state_valid']} rows={post.get('history_rows_for_action')} dup={post.get('duplicate_history_actions')} "
                  f"accepted={post.get('accepted_summary')!r} stage={post.get('stage_now')} attempts={post.get('callback_attempts')} "
                  f"lock_err={lock_err} exit0-but-other-result-accepted={silent}")
            for c in calls:
                if c["exit"] != 0:
                    print("     refusal:", c["stderr"].splitlines()[0] if c["stderr"] else "(no stderr)")
            if nexts:
                heads = sorted({c["stdout_head"].split("|")[1].strip() if "|" in c["stdout_head"] else c["stdout_head"] for c in nexts})
                print("     next packet stages:", heads)
    (HERE / "e11_results.json").write_text(json.dumps(allrows, indent=1))


if __name__ == "__main__":
    main()
