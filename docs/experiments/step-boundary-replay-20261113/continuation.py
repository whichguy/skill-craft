#!/usr/bin/env python3
"""The replay's continuation (Astra's review, revision 1): each sample's own amendment, carried on through the route.

For every Q1 sample: a fresh build of its scenario, then through the engine's own seam (navigator.apply, finish_improve
for the amendment's review, accept_effects), with no model:
1. the sample's producer result (its run's ``active_improve.seed_result``) is applied and its review imported, and
   finish_improve rechecks fix forward;
2. test-spec is the previous accepted spec's cases, which the frozen-case gate must accept;
3. validate-existing settles by script or is recorded;
then the asserts:
- HEAD is still S1's step commit;
- the step cursor names S2;
- done_steps and built_steps are 1;
- S2's draft is still uncommitted;
- S2 is the plan's last step, and its test stage runs every unmarked regression command (the full regression).
Usage: continuation.py RESULTS_ROOT. The claim covers the route only: no model continues the item.
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "test/shiploop_e2e/stage_suite"), str(ROOT / "test/shiploop_e2e"),
                str(ROOT / "skills/shiploop/scripts")]
import stage_build as sb  # noqa: E402
import shiploop_iteration as iteration  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402


def git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(tree), *args], check=True, capture_output=True, text=True).stdout.strip()


def record(core, run_dir: Path, state: dict, result: dict | None, improve_final: dict | None = None) -> dict:
    action = str(nav.current_action(state)["id"])
    before = state
    after = nav.apply(before, action, result)
    if after["active_improve"] is not None:
        after = nav.finish_improve(after, action, {"summary": "Synthetic review receipt (continuation)."}, improve_final)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return nav.accept_effects(core, run_dir, before, after, action_id=action)


def one(sample: Path) -> dict:
    scenario = sample.parent.name
    sc = sb.load("step-plan/" + scenario)
    run = sample / ".shiploop-runs/seed/run"
    produced = store.read_record(run / "state.md")["active_improve"]["seed_result"]
    with tempfile.TemporaryDirectory(prefix="continuation-") as temp:
        built = sb.build(sc, Path(temp) / "run")
        run_dir, tree = built.run_dir, built.worktree
        core = types.SimpleNamespace(PACKAGE_ROOT=sb.DEFAULT_CLI.parent.parent.parent)
        state = store.read_record(run_dir / "state.md")
        item = nav._current_work_item(state)
        s1_commit = git(tree, "rev-parse", "HEAD")
        spec_before = nav._sent_back_results(state, "test-spec", item).spec_before
        frozen = state["accepted"][spec_before]
        state = record(core, run_dir, state, dict(produced))                     # 1. the sample's amendment + review
        checks = {"amendment_imported": nav.current_stage(state) == "test-spec"}
        spec = {"outcome": "done", "summary": "Continuation: the accepted cases, kept.",
                "test_cases": frozen.get("test_cases") or [], "assumptions": []}
        checks["frozen_cases_accepted"] = nav._frozen_case_refusal(state, item, spec) is None
        state = record(core, run_dir, state, spec)                               # 2. test-spec
        if nav.current_stage(state) == "validate-existing":                      # 3. when it did not settle by script
            state = record(core, run_dir, state, {"outcome": "done", "summary": "Continuation."})
        view = nav.step_view(state, item)
        _action, plan = test_loop._step_plan(state, item)
        steps = plan.get("steps") or []
        dirty = git(tree, "status", "--porcelain")
        checks.update({
            "at_implement": nav.current_stage(state) == "implement",
            "cursor_names_S2": view is not None and view.step.get("id") == "S2",
            "done_and_built_1": (nav.planning_revision.done_steps(state, item),
                                 nav.planning_revision.built_steps(state, item)) == (1, 1),
            "S1_commit_kept": git(tree, "rev-parse", "HEAD") == s1_commit,
            "S2_draft_uncommitted": bool(dirty),
        })
        if view is not None and view.number == len(steps):
            cases = (state["accepted"][nav.planning_revision.current_actions(state)[(item, "test-spec")]]
                     .get("test_cases") or [])
            active = iteration.active_commands(plan.get("test_commands") or [], cases, steps, view.number)
            full = [row["command"] for row in plan.get("test_commands") or []
                    if row.get("suite") == "regression" and not row.get("minimum")]
            checks["last_step_runs_full_regression"] = all(any(a["command"] == c for a in active) for c in full)
        return {"scenario": scenario, "sample": sample.name, "steps": [s.get("id") for s in steps], **checks}


def main(root: str) -> None:
    rows = [one(folder) for folder in sorted(Path(root).glob("step-plan/*/*")) if (folder / "stage-result.json").is_file()]
    for row in rows:
        print(json.dumps(row))
    keys = [key for key in rows[0] if key not in ("scenario", "sample", "steps")] if rows else []
    for key in keys:
        print(f"{key}: {sum(1 for row in rows if row.get(key) is True)} of {sum(1 for row in rows if key in row)}")


if __name__ == "__main__":
    main(sys.argv[1])
