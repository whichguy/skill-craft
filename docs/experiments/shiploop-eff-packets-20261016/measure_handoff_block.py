"""Characters of the quoted-files-and-hand-offs block (navigator._consumer_lines) per stage, on a long-knowledge fixture: a
temporary git repo whose baseline holds no living file, then docs/shiploop/{spec (20 KB), architecture, environment}.md committed.
measure_handoff_block.py <checkout root with skills/shiploop> [--show STAGE]   (run it on the base and on the changed checkout)"""
import os, sys, subprocess, tempfile
from pathlib import Path
root_src = Path(sys.argv[1])
sys.path.insert(0, str(root_src / "skills/shiploop/scripts"))
import shiploop_navigator as nav, shiploop_knowledge_home as knowledge

def git(repo, *a): return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout
os.environ.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

def spec_text():
    out = ["## Requirements", ""]
    for n in range(1, 31):
        out += [f"### R-{n} Requirement number {n}", "", f"Basis: the request says the product must do thing {n} reliably.", "",
                f"Behavior: " + ("the system performs behaviour %d on the documented input and reports the result. " % n) * 4, "",
                "Acceptance:", "", f"- Positive: behaviour {n} happens for a valid input, confirmed by reading the output. " * 1,
                f"- Failure: an invalid input for {n} is refused with a reason.", f"- Boundary: the limit for {n} is exact.", "",
                f"State: files only; no records for {n}.", ""]
    return "\n".join(out + ["## Non-functional requirements", "", "- The product runs offline.", "", "## Retired", ""]) + "\n"

def arch_text():
    out = ["## Stack", "", "Python 3.12, standard library only.", "", "## Structure", "", "src/ holds the modules; tests/ holds the suites.", "",
           "## Decisions", ""]
    for n in range(1, 9):
        out += [f"### AD-{n} Decision {n}", "", "Choice: " + ("a plain module for concern %d. " % n) * 6, "Why: " + "simplest thing that works. " * 6, ""]
    return "\n".join(out + ["## Superseded", ""]) + "\n"

def env_text():
    return "\n".join(["## Targets and runtimes", "", "node 22, python 3.12", "", "## Commands", ""] +
                     [f"- `npm run task{n}`: does task {n}" for n in range(1, 40)] + ["", "## Harnesses and suites", ""] +
                     [f"- suite {n}: `python3 tests/s{n}.py`" for n in range(1, 30)]) + "\n"

with tempfile.TemporaryDirectory() as temp:
    repo, run = Path(temp) / "repo", Path(temp) / "run"
    repo.mkdir(); run.mkdir()
    git(repo, "init", "-q"); git(repo, "config", "user.email", "a@b.c"); git(repo, "config", "user.name", "n"); git(repo, "config", "commit.gpgsign", "false")
    (repo / "app.py").write_text("x = 1\n"); git(repo, "add", "-A"); git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD").strip()
    (run / knowledge.RUN_BASELINE).write_text(base + "\n")
    home = repo / knowledge.HOME; home.mkdir(parents=True)
    (home / "spec.md").write_text(spec_text()); (home / "architecture.md").write_text(arch_text()); (home / "environment.md").write_text(env_text())
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "home")
    follows = [f"R-{n}" for n in range(1, 13)] + ["AD-1", "AD-2"]
    rows = [("sp1", "step-plan", "W1", {"follows": follows, "criteria": [{"id": "C1", "text": "one"}],
                                        "test_commands": [{"command": "t", "suite": "focused", "ids": ["TC-1"]}]}),
            ("ts1", "test-spec", "W1", {"test_cases": [{"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "o", "red": "r", "green": "g"}]})]
    history = [{"action": a, "stage": s, "workitem": w, "outcome": "done"} for a, s, w, _ in rows]
    accepted = {a: dict({"outcome": "done", "summary": a}, **r) for a, _, _, r in rows}
    sizes = {}
    for stage in ("plan", "test-strategy", "test-spec", "implement", "test", "document", "verify", "carry-forward", "product-acceptance", "system-test-author"):
        state = {"repo": str(repo), "prompt": "x", "run_id": "nav-0123456789abcdef", "execution_mode": "navigator", "status": "active",
                 "stage": "inner-loop", "work_items": [{"id": "W1", "title": "one"}], "work_index": 0,
                 "inner_loops": {"W1": {"stage": stage, "action": {"id": "nav-current", "stage": stage}}},
                 "history": history, "accepted": accepted, "revisions": {}}
        text = "\n".join(nav._consumer_lines(run, state, stage))
        sizes[stage] = len(text)
        if "--show" in sys.argv and sys.argv[sys.argv.index("--show") + 1] == stage:
            print(text)
    if "--show" not in sys.argv:
        for stage, n in sizes.items(): print(f"{stage:20s} {n:7d}")
        print(f"{'TOTAL':20s} {sum(sizes.values()):7d}")
