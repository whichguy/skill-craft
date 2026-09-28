"""Shared fixture: a temp git repo and a ShipLoop run built from the snapshot source."""
import json, os, subprocess, sys, tempfile, types
from pathlib import Path
EXP = Path(__file__).resolve().parents[1]
SRC = EXP / "src"
PKG = SRC / "skills/shiploop"
SCRIPTS = PKG / "scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS)); sys.path.insert(0, str(SRC / "test"))
os.environ.setdefault("SHIPLOOP_KEEPALIVE_HOME", str(EXP / "tier1" / "keepalive-home"))
import shiploop_navigator as nav, shiploop_store as store  # noqa
CORE = types.SimpleNamespace(PACKAGE_ROOT=PKG, REF_DIR=PKG / "references")

def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout

def fixture(prefix="exp-"):
    base = Path(tempfile.mkdtemp(prefix=prefix, dir=EXP / "tier1")).resolve()
    repo, run = base / "repo", base / "run"
    repo.mkdir(); run.mkdir()
    git(repo, "init", "-q"); git(repo, "config", "user.email", "e@example.invalid"); git(repo, "config", "user.name", "Exp")
    (repo / "a.py").write_text("x = 1\n"); git(repo, "add", "-A"); git(repo, "commit", "-qm", "base")
    nav.save(run, nav.new_state(str(repo), "Experiment fixture.", lint_option="off"))
    return repo, run

def state(run): return store.read_record(run / "state.md")

def cli(*args, check=False):
    p = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def submit(run, result, action=None):
    s = state(run); action = action or nav.current_action(s)["id"]
    path = run / "inbox" / (action + ".md"); path.parent.mkdir(exist_ok=True)
    path.write_text(store.dumps(result, "result"))
    return cli("complete", "--run-dir", str(run), "--action", action, "--result", str(path))
