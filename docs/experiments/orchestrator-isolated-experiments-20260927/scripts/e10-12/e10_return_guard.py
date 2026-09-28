"""E10: does the workspace return guard protect the user's source edits?

Black-box: real `shiploop workspace start|plan-return|return` CLI calls against a
fresh source repo per trial.  The navigator is advanced to handoff with the
workspace test's pure-apply fixture (synthetic results, no host work).
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
SCRIPTS = SRC / "skills/shiploop/scripts"
CLI = SCRIPTS / "shiploop"
sys.path.insert(0, str(SCRIPTS))
WORK = HERE / "e10-work"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
       "SHIPLOOP_KEEPALIVE": "off", "SHIPLOOP_KEEPALIVE_HOME": str(HERE / "keepalive-home")}
os.environ.update({k: ENV[k] for k in ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "SHIPLOOP_KEEPALIVE",
                                        "SHIPLOOP_KEEPALIVE_HOME")})
import shiploop_store as store  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

BRANCH = "feature/user-branch"


def git(repo, *a, check=True):
    p = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, env=ENV)
    if check and p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout


def cli(*a):
    p = subprocess.run([sys.executable, "-B", str(CLI), *a], capture_output=True, text=True, env=ENV, timeout=60)
    return p.returncode, p.stdout, p.stderr


def advance_to_handoff(state):
    """Same as ShipLoopWorkspaceTests._advance_to_handoff (synthetic transitions)."""
    while state["status"] != "done":
        action = navigator.current_action(state)
        if action["stage"] == "handoff":
            return state
        result = {"outcome": "done", "summary": "Synthetic transition for E10."}
        if action["stage"] == "plan":
            result["work_items"] = [{"id": "W1", "title": "One synthetic item", "context": "E10."}]
        state = navigator.apply(state, action["id"], result)
        if state["active_improve"] is not None:
            state = navigator.finish_improve(state, action["id"], {
                "summary": "Synthetic Improve.", "review_refs": [], "check_refs": [], "lessons": "E10."})
    raise AssertionError("reached done before handoff")


def tree(repo):
    out = {}
    for p in sorted(repo.rglob("*")):
        rel = p.relative_to(repo)
        if ".git" in rel.parts or not p.is_file():
            continue
        out[rel.as_posix()] = p.read_text()
    return out


def source_state(repo):
    return {"head": git(repo, "rev-parse", "HEAD").strip(), "branch": git(repo, "branch", "--show-current").strip(),
            "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--ignored").splitlines(),
            "files": tree(repo)}


EDITS = {
    "none": None,
    "a_same_tracked": ("tracked.txt", "base\nUSER EDIT to a file the run also changed\n"),
    "b_unrelated_tracked": ("other.txt", "other\nUSER EDIT to an unrelated tracked file\n"),
    "c_untracked": ("user-notes.txt", "USER untracked notes\n"),
    "d_ignored": ("debug.log", "USER ignored log file\n"),
    "e_untracked_same_path_as_candidate": ("feature.txt", "USER created the same new path\n"),
}


def trial(edit_name, timing, candidate):
    name = f"{edit_name}--{timing}--{candidate}"
    base = WORK / name
    shutil.rmtree(base, ignore_errors=True)
    repo = base / "source"
    repo.mkdir(parents=True)
    git(repo, "init", "-q"); git(repo, "checkout", "-q", "-b", BRANCH)
    for k, v in (("user.name", "E10"), ("user.email", "e10@example.invalid"), ("commit.gpgsign", "false"),
                 ("core.hooksPath", os.devnull)):
        git(repo, "config", k, v)
    (repo / "tracked.txt").write_text("base\n")
    (repo / "other.txt").write_text("other\n")
    (repo / ".gitignore").write_text("*.log\n")
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "base")
    root = base / "workspace"
    code, out, err = cli("workspace", "start", "--repo", str(repo), "--workspace-root", str(root),
                         "--prompt", "E10: change tracked.txt and add feature.txt.", "--lint", "off")
    assert code == 0, err
    wt = root / "worktree"
    (wt / "tracked.txt").write_text("base\nAGENT change\n")
    (wt / "feature.txt").write_text("AGENT feature\n")
    if candidate == "committed":
        git(wt, "add", "-A"); git(wt, "commit", "-qm", "agent candidate")
    run = root / "run"
    navigator.save(run, advance_to_handoff(store.read_record(run / "state.md")))
    rec = {"trial": name, "edit": edit_name, "timing": timing, "candidate": candidate}
    edit = EDITS[edit_name]

    def do_edit():
        if edit:
            (repo / edit[0]).write_text(edit[1])
        rec["source_after_edit"] = source_state(repo)

    if timing == "before-plan":
        do_edit()
    rec["plan_return"] = cli("workspace", "plan-return", "--workspace-root", str(root))
    if rec["plan_return"][0] == 0:
        plan = store.read_record(root / "return-plan.md")
        for row in plan["paths"]:
            if row["disposition"] != "exclude":
                row["disposition"] = "keep"
        store.write_record(root / "return-plan.md", plan, "ShipLoop workspace return plan")
        rec["plan_paths"] = [(r["path"], r["disposition"]) for r in plan["paths"]]
    if timing == "after-plan":
        do_edit()
    before = source_state(repo)
    rec["return"] = cli("workspace", "return", "--workspace-root", str(root))
    after = source_state(repo)
    rec["source_final"] = after
    rec["source_unchanged_by_return"] = before == after
    if edit:
        rec["user_edit_intact"] = (repo / edit[0]).read_text() == edit[1]
    rec["receipt_exists"] = (root / "return-receipt.md").exists()
    rec["manifest_status"] = store.read_record(root / "workspace.md")["status"]
    return rec


def main():
    WORK.mkdir(exist_ok=True)
    results = []
    for candidate in ("committed", "uncommitted"):
        for timing in ("before-plan", "after-plan"):
            for edit in EDITS:
                if edit == "none" and timing == "after-plan":
                    continue
                r = trial(edit, timing, candidate)
                results.append(r)
                ret = r["return"]; pr = r["plan_return"]
                print(f"{r['trial']:<55} plan-return={pr[0]} return={ret[0]} receipt={r['receipt_exists']} "
                      f"intact={r.get('user_edit_intact')} src_unchanged_by_return={r['source_unchanged_by_return']}")
                for label, res in (("plan-return", pr), ("return", ret)):
                    first = (res[2].strip().splitlines() or res[1].strip().splitlines() or [""])[0]
                    print(f"    {label}: {first}")
                print(f"    final status: {r['source_final']['status']} head={r['source_final']['head'][:10]} "
                      f"branch={r['source_final']['branch']}")
    (HERE / "e10_results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
