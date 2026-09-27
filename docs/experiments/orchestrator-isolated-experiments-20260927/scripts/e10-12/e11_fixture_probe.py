import os, sys, subprocess, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent; SRC = HERE.parent / "src"; SCRIPTS = SRC / "skills/shiploop/scripts"
os.environ.update(SHIPLOOP_KEEPALIVE="off", SHIPLOOP_KEEPALIVE_HOME=str(HERE / "keepalive-home"))
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav, shiploop_store as store
base = Path(tempfile.mkdtemp(prefix="probe-", dir=HERE)); repo = base/"repo"; run = base/"run"; repo.mkdir(); run.mkdir()
g = lambda *a: subprocess.run(["git","-C",str(repo),*a],check=True,capture_output=True)
g("init","-q"); g("config","user.email","e@x.invalid"); g("config","user.name","E"); (repo/"a.py").write_text("x=1\n"); g("add","-A"); g("commit","-qm","b")
nav.save(run, nav.new_state(str(repo), "E11 fixture.", lint_option="off"))
for i in range(4):
    s = store.read_record(run/"state.md"); a = nav.current_action(s)
    print(i, nav.current_stage(s), a["id"], "active_improve=", s.get("active_improve") is not None)
    p = run/"inbox"/(a["id"]+".md"); p.parent.mkdir(exist_ok=True); p.write_text(store.dumps({"outcome":"done","summary":"probe"},"result"))
    r = subprocess.run([sys.executable, str(SCRIPTS/"shiploop"), "complete","--run-dir",str(run),"--action",a["id"],"--result",str(p)],capture_output=True,text=True)
    print("  exit", r.returncode, r.stderr[:300].replace("\n"," | "), "| stdout head:", r.stdout.splitlines()[0] if r.stdout else "")
