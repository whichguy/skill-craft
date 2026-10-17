"""Fixed-text renders of a rich two-item run, for render_diff.py (efficiency plan G-RENDER, unit U13).

The standard offline render (packets.py --offline) walks one item's inner stages over a repository with no knowledge home
and no delivery contract, so it cannot show the hand-off block's followed entries, the delivery block or the last
accepted transition of an outer stage.  This walk can: all 24 stages of a two-item run (multi-step plans, test cases, not
covered behaviours, lessons), over a git repository whose run baseline holds no living file and whose long knowledge home
(30 requirements, 8 decisions, an environment file) is committed after it, with an opt-in delivery contract and its
observations.  Neutral text throughout; no model and no project work.

    python3 rich_render.py <checkout root> <out dir> [inline|ask-agent] [--run-dir-length 83] [--cli-path-length 96]
                           [--home long|small]

Run it on the base tree and on the changed tree with the same options, then
    python3 test/shiploop_e2e/render_diff.py <base out> <changed out> --unit U13 --no-head-table
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def build(root: Path, out: Path, route: str, run_dir_length: int, cli_path_length: int, home_kind: str) -> None:
    for path in (root / "skills" / "shiploop" / "scripts", root / "test" / "shiploop_e2e", root / "test"):
        sys.path.insert(0, str(path))
    # Fixed commit dates: the commit IDs the packets quote (the intake lists the repository's recent commits) are then the
    # same in every render of one tree, so two renders differ only where their packets do.
    os.environ.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, PYTHONDONTWRITEBYTECODE="1",
                      GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    import packets
    import shiploop_consumer_delivery as consumer_delivery
    import shiploop_loops as loops
    import shiploop_navigator as navigator
    import shiploop_navigator_dry_run as dry
    import shiploop_knowledge_home as knowledge
    import shiploop_store as store
    from shiploop_consumer_delivery_support import contract

    def git(repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout

    def spec_text() -> str:
        lines = ["# Living spec", "", "## Requirements", ""]
        for n in range(1, 31):
            lines += [f"### R-{n} Requirement number {n}", "", f"Basis: the request names thing {n} as needed by its reader.", "",
                      f"Behavior: the system performs behaviour {n} on the documented input of kind {n}.", "", "Acceptance:", "",
                      f"- Positive: behaviour {n} happens for a valid input of kind {n}.",
                      f"- Failure: an invalid input for {n} is refused with reason {n}.", ""]
        return "\n".join(lines + ["## Non-functional requirements", "", "- The product runs offline, with no network.", "",
                                   "## Retired", ""]) + "\n"

    def architecture_text() -> str:
        lines = ["## Stack", "", "Python 3.12 with the standard library only.", "", "## Decisions", ""]
        for n in range(1, 9):
            lines += [f"### AD-{n} Decision {n}", "", f"Choice: a plain module for concern {n}, owned by one file.",
                      f"Why: the simplest thing that works for concern {n}.", ""]
        return "\n".join(lines + ["## Superseded", ""]) + "\n"

    def environment_text() -> str:
        return "\n".join(["## Targets and runtimes", "", "python 3.12", "", "## Commands", ""]
                         + [f"- `python3 tests/task{n}.py`: runs task {n}" for n in range(1, 25)]) + "\n"

    small = {"spec.md": "## Requirements\n\n### R-1 One\n\nBehavior: the system does one thing.\n\n### R-2 Two\n\nBehavior: it does a second.\n\n## Retired\n",
             "architecture.md": "## Stack\n\nPython.\n\n## Decisions\n\n### AD-1 Plain\n\nChoice: plain modules.\n\n## Superseded\n",
             "environment.md": "## Commands\n\n- `python3 -m unittest`: runs the tests\n"}
    home = small if home_kind == "small" else {"spec.md": spec_text(), "architecture.md": architecture_text(),
                                               "environment.md": environment_text()}
    ids = ["W1", "W2"]

    def result_for(stage: str, state: dict, item: str | None) -> dict:
        result = {"outcome": "done", "summary": f"Synthetic declaration; no work executed for {stage}."}
        if stage == "plan":
            result["work_items"] = [{"id": i, "title": f"Synthetic item {i}", "context": f"Context of {i}."} for i in ids]
            result["delivery_assessment"] = {"kind": "contract", "contract": contract()}
        elif stage == "step-plan":
            result.update(follows=["R-1", "R-2", "AD-1"], paths=[f"src/{item}.py", f"tests/test_{item}.py"],
                          criteria=[{"id": "C1", "text": f"Criterion one of {item} holds."},
                                    {"id": "C2", "text": f"Criterion two of {item} holds."}],
                          test_commands=[{"command": f"python3 -m unittest tests.test_{item}", "suite": "focused",
                                          "ids": ["TC-1", "TC-2"], "criteria": ["C1", "C2"]}],
                          steps=[{"id": "S1", "task": f"First step of {item}.", "deps": [], "criteria": ["C1"], "paths": [f"src/{item}.py"]},
                                 {"id": "S2", "task": f"Second step of {item}.", "deps": ["S1"], "criteria": ["C2"],
                                  "paths": [f"src/{item}.py", f"tests/test_{item}.py"]}])
        elif stage == "test-spec":
            result["test_cases"] = [
                {"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": f"the output of the command of {item}",
                 "red": f"fails before in {item}", "green": f"passes after in {item}"},
                {"id": "TC-2", "criterion": "C2", "requirement": "R-2", "oracle": f"the stored record of {item}",
                 "red": f"no record in {item}", "green": f"the record of {item} exists"}]
        elif stage == "implement":
            step_no = navigator.implement_progress(state, item)[0] + 1
            result["not_covered"] = [{"behaviour": f"An uncovered behaviour of {item} step {step_no}.",
                                      "reason": f"No test case of {item} reaches it in step {step_no}."}]
        elif stage == "system-test-author":
            result["system_commands"] = [{"command": "python3 -m unittest discover", "suite": "regression"}]
        elif stage == "release-verify":
            result["lessons"] = {"learned": "Learned one thing about the run.", "considerations": "The decisions and risks that matter next time.",
                                 "open_next": "none"}
        if stage in ("system-test", "release", "release-verify"):
            kinds = {"system-test": ("pre-update",), "release": ("effect", "identity"), "release-verify": ("behavior",)}[stage]
            projection = consumer_delivery.project(state)
            result["delivery_assessment"] = {"kind": "observation", "contract_anchor": projection["anchor"], "observations": [
                {"obligation_id": row["id"], "status": "passed", "candidate": "candidate-v1", "target": "fixture-head",
                 "evidence_refs": [f"evidence/{row['id']}.md"]} for row in contract()["obligations"] if row["kind"] in kinds]}
        return result

    def walk(case: dict, delegation: str, work: str, run_dir: Path):
        repo = Path(work)
        git(repo, "init", "-q")
        for key, value in (("user.email", "r@example.invalid"), ("user.name", "R"), ("commit.gpgsign", "false"),
                           ("core.hooksPath", os.devnull)):
            git(repo, "config", key, value)
        (repo / "app.py").write_text("x = 1\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base")
        (run_dir / knowledge.RUN_BASELINE).write_text(git(repo, "rev-parse", "HEAD").strip() + "\n")
        (repo / knowledge.HOME).mkdir(parents=True)
        for name, text in home.items():
            (repo / knowledge.HOME / name).write_text(text)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "home")
        state = navigator.new_state(work, case["prompt"], delegation=delegation, improve_skill=str(dry.stage_loops.BUNDLED_IMPROVE_CARD),
                                    delivery_contract=True)
        count = 0

        def cold(current: dict) -> dict:
            store.write_record(run_dir / "state.md", current)
            read = store.read_record(run_dir / "state.md")
            if read["status"] == "active" and not read.get("active_improve"):
                try:
                    for relative, text in loops.contract_writes(run_dir, read).items():
                        store.atomic_write_text(run_dir / relative, text)
                except loops.LoopError:
                    pass
            return read

        for _ in range(400):
            if state["status"] != "active":
                return
            stage = navigator.sequence_stage(state)
            action = navigator.current_action(state)
            count += 1
            yield f"{count:02d}-{stage}", cold(state)
            if stage == navigator.IMPROVE_STAGE:
                reviewed = state["active_improve"]["stage"]
                state = navigator.finish_improve(state, state["active_improve"]["action_id"], dry._improve_receipt(reviewed), None)
            else:
                item = navigator._current_work_item(state)
                state = navigator.apply(state, action["id"], result_for(stage, state, item))

    case = {"prompt": "Inspect the SDLC graph with synthetic declarations."}
    renders = packets.offline_renders(case, route, run_dir_length=run_dir_length, cli_path_length=cli_path_length, walk=walk)
    packets.write_text_dir(out, "rich-" + home_kind, route, renders, cli_path_length)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("route", nargs="?", default="inline", choices=("inline", "ask-agent"))
    parser.add_argument("--run-dir-length", type=int, default=83)
    parser.add_argument("--cli-path-length", type=int, default=96)
    parser.add_argument("--home", default="long", choices=("long", "small"))
    args = parser.parse_args(argv)
    build(args.root.resolve(), args.out.resolve(), args.route, args.run_dir_length, args.cli_path_length, args.home)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
