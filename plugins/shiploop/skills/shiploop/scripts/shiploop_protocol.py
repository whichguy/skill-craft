"""Action-oriented ShipLoop protocol. Markdown is the only mutable state authority.

The host supplies judgment and edits; this module selects the next action and
executes/checks evidence. Calls are serialized by the run lock. A completion
consumes its action only after a recoverable Markdown transaction is durable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shlex
import sys
import tempfile
import uuid

import shiploop_store as store
import shiploop_evidence as evidence


class ProtocolError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise ProtocolError(message)


def text_field(obj, key):
    value = obj.get(key)
    need(
        isinstance(value, str) and bool(value.strip()),
        f"result requires nonempty {key}",
    )
    return value.strip()


def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def resolve_draft(result):
    """Import a large Markdown draft without requiring its body in the host turn."""
    need(isinstance(result, dict), "result must be an object")
    result = dict(result)
    if "dag_file" in result:
        need("dag" not in result, "provide either dag or dag_file, not both")
        path = Path(text_field(result, "dag_file"))
        need(
            path.is_absolute()
            and path.suffix.lower() == ".md"
            and not path.is_symlink(),
            "dag_file must name an absolute, non-symlink Markdown draft",
        )
        result["dag"] = store.read_record(path)
    return result


def safe_run_path(root, relative):
    path = root / relative
    need(
        not Path(relative).is_absolute() and ".." not in Path(relative).parts,
        "unsafe run-relative path",
    )
    for parent in [path, *path.parents]:
        need(not parent.is_symlink(), "run path contains a symlink")
        if parent == root:
            break
    return path


def validate_state(state):
    need(
        state.get("version") == 3 and isinstance(state.get("action"), dict),
        "unsupported protocol; migrate or restore authoritative state",
    )
    aid = state["action"].get("id")
    need(
        isinstance(aid, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,160}", aid),
        "unsafe action ID in authoritative state",
    )
    need(
        state["action"].get("stage") == state.get("stage"),
        "action stage does not match state cursor",
    )
    need(
        state.get("stage") in set(PROMPTS) | {"schedule", "done", "halted"},
        "unknown action stage",
    )
    need(
        isinstance(state.get("completed_actions"), dict),
        "invalid completed action ledger",
    )


def git(core, repo, *args):
    result = core.git_run(repo, *args)
    need(
        result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}"
    )
    return result.stdout.strip()


def action(state, phase, stage):
    state["phase"], state["stage"] = phase, stage
    state["action"] = {
        "id": f"{state['run_id']}-{uuid.uuid4().hex[:12]}",
        "stage": stage,
    }


def persist(root, state, event, writes=None):
    writes = dict(writes or {})
    history_path = root / "history.md"
    history = store.read_record(history_path) if history_path.exists() else []
    history.append(
        {"event": event, "action": state.get("action"), "revision": state["revision"]}
    )
    writes["state.md"] = store.dumps(state, "ShipLoop state")
    writes["history.md"] = store.dumps(history, "ShipLoop history")
    store.transaction(root, writes)


def rec_path(state):
    need(
        isinstance(state.get("active_step"), str)
        and re.fullmatch(r"[SD][0-9]+", state["active_step"]),
        "unsafe active step ID",
    )
    return f"steps/{state['active_step']}.md"


def active(root, state):
    path = safe_run_path(root, rec_path(state))
    need(not path.is_symlink(), "receipt cannot be a symlink")
    rec = store.read_record(path)
    sid = state["active_step"]
    run_id = state.get("run_id", "")
    need(re.fullmatch(r"[A-Za-z0-9_-]+", run_id), "unsafe run ID")
    need(
        rec.get("id") == sid and rec.get("run_id") == run_id,
        "receipt identity mismatch",
    )
    expected = Path(state["repo_root"]) / ".worktrees" / "shiploop" / run_id / sid
    need(rec.get("worktree") == str(expected), "receipt points to a foreign worktree")
    need(
        rec.get("branch") == f"shiploop/{run_id}/{sid}",
        "receipt points to a foreign branch",
    )
    need(
        re.fullmatch(r"[0-9a-f]{40,64}", rec.get("base_sha", "")),
        "invalid receipt baseline",
    )
    for parent in [expected, *expected.parents]:
        need(not parent.is_symlink(), "worktree path contains a symlink")
        if parent == Path(state["repo_root"]):
            break
    return rec


def repo_for(root, state):
    return (
        Path(active(root, state)["worktree"])
        if state.get("active_step")
        else Path(state["repo_root"])
    )


def exclusions(root, repo):
    try:
        return [str(root.relative_to(repo))]
    except ValueError:
        return []


def check_target(core, root, state):
    if state.get("active_step"):
        produces = core.produces_texts(
            core.steps_by_id(root)[state["active_step"]]["produces"]
        )
    else:
        produces = store.read_record(root / "lifecycle.md")["acceptance"]
    return repo_for(root, state), produces


def verified(core, root, state, action_id=None):
    aid = action_id or state["action"]["id"]
    record = store.read_record(root / "checks" / f"{aid}.md")
    repo, produces = check_target(core, root, state)
    evidence.validate_manifest(record["manifest"], produces)
    need(
        any(x["kind"] == "lint" for x in record["manifest"]["checks"]),
        "each iteration requires a lint process",
    )
    evidence.validate_results(
        record["results"],
        repo,
        record["manifest"],
        aid,
        excluded=exclusions(root, repo),
    )
    return record


def proposal_entries(root, state, entries):
    need(
        isinstance(entries, list),
        "journal must be a list (empty is an explicit no-proposal decision)",
    )
    path = root / "shiploop-improvements.md"
    journal = store.read_record(path) if path.exists() else []
    for entry in entries:
        need(isinstance(entry, dict), "journal entry must be an object")
        for field in ("title", "evidence", "impact", "proposal", "test_idea"):
            text_field(entry, field)
        key = digest(
            {
                "title": entry["title"].strip().lower(),
                "proposal": entry["proposal"].strip(),
            }
        )
        source = {"action": state["action"]["id"], "step": state.get("active_step")}
        old = next((x for x in journal if x["key"] == key), None)
        if old:
            if source not in old["sources"]:
                old["sources"].append(source)
            observation = {
                "source": source,
                "evidence": entry["evidence"],
                "impact": entry["impact"],
            }
            if observation not in old.setdefault("observations", []):
                old["observations"].append(observation)
        else:
            journal.append(
                dict(
                    entry,
                    key=key,
                    status="proposed",
                    sources=[source],
                    observations=[
                        {
                            "source": source,
                            "evidence": entry["evidence"],
                            "impact": entry["impact"],
                        }
                    ],
                )
            )
    return store.dumps(
        journal, "ShipLoop improvement proposals — not automatically applied"
    )


def validate_candidate(core, root, writes, state):
    """Validate a candidate snapshot without mutating authoritative files."""
    with tempfile.TemporaryDirectory(prefix="shiploop-candidate-") as tmp:
        stage = Path(tmp)
        for name in ("environment.md", "spec.md", "plan.md", "backchain/plan.md"):
            body = writes.get(name)
            if body is None and (root / name).is_file():
                body = (root / name).read_text()
            if body is not None:
                store.atomic_write_text(stage / name, body)
        env, gaps = core.load_environment(stage)
        spec, sgaps = core.load_spec(stage)
        need(not gaps + sgaps, "; ".join(gaps + sgaps))
        gates = (
            core.handles_block_plan(env)
            + core.exclusive_gaps(env)
            + core.ui_craft_gaps(env)
        )
        need(not gates, "; ".join(gates))
        need(spec["checkable"], "spec must be checkable; resolve ask_user first")
        gaps = core.wrapper_pair(stage, spec) + core.dag_gaps(stage, spec)
        need(not gaps, "; ".join(gaps))
        dag = core.load_dag(stage)
        producers = {
            step["id"]: set(core.produces_texts(step["produces"]))
            for step in dag["steps"]
        }
        for step in dag["steps"]:
            for dependency in step["inputs"]:
                if dependency["from"] is not None:
                    need(
                        dependency["need"] in producers[dependency["from"]],
                        f"{step['id']} dependency need is not produced by {dependency['from']}",
                    )
        if (root / "lifecycle.md").exists():
            lifecycle = store.read_record(root / "lifecycle.md")
            for key in ("preparation", "publish"):
                if lifecycle[key] == "dag":
                    need(
                        any(x.get("activity") == key for x in dag["steps"]),
                        f"lifecycle requires a DAG {key} step marked activity: {key}",
                    )
            if lifecycle["publish"] == "outer-loop":
                need(
                    not any(x.get("activity") == "publish" for x in dag["steps"]),
                    "outer publication must not also occur in DAG",
                )
    return spec


def schedule(core, root, state):
    """Persist allocation intent before Git; only one step runs at a time."""
    if state.get("active_step"):
        return
    classes = core.classify_steps(root, state)
    running = [sid for sid, kind in classes.items() if kind == "running"]
    if running:
        state["active_step"] = running[0]
        action(state, "implement", "implement")
        active(root, state)  # Validate a migrated receipt before any Git action.
        persist(root, state, "resume-migrated-step")
        return
    ready = [sid for sid, kind in classes.items() if kind == "ready"]
    if not ready:
        need(
            all(x == "done" for x in classes.values()),
            "DAG has no ready step; inspect dependency receipts",
        )
        action(state, "residual", "coverage")
        persist(root, state, "walk-drained")
        return
    sid = ready[0]
    repo = Path(state["repo_root"])
    record = {
        "id": sid,
        "run_id": state["run_id"],
        "status": "running",
        "plan_sha256": state["plan_sha256"],
        "inner": "A",
        "improve_cycles": [],
        "branch": core.worktree_branch(state["run_id"], sid),
        "worktree": str(core.worktree_path(repo, state["run_id"], sid)),
        "base_sha": git(core, repo, "rev-parse", "HEAD"),
        "allocation": "pending",
    }
    state["active_step"] = sid
    action(state, "implement", "implement")
    persist(root, state, "allocate-intent", {rec_path(state): store.dumps(record)})


def ensure_worktree(core, root, state):
    if not state.get("active_step"):
        return
    rec = active(root, state)
    if rec.get("allocation") != "pending":
        return
    repo, wt, branch = Path(state["repo_root"]), Path(rec["worktree"]), rec["branch"]
    need(not wt.is_symlink(), "worktree path must not be a symlink")
    if wt.exists():
        need(
            git(core, wt, "symbolic-ref", "--short", "HEAD") == branch,
            "allocation path belongs to another branch",
        )
        need(
            git(core, wt, "rev-parse", "--show-toplevel") == str(wt),
            "allocation path is not its own worktree",
        )
    else:
        wt.parent.mkdir(parents=True, exist_ok=True)
        core.ensure_worktrees_excluded(repo)
        exists = (
            core.git_run(
                repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"
            ).returncode
            == 0
        )
        if exists:
            need(
                git(core, repo, "rev-parse", branch) == rec["base_sha"],
                "allocation branch changed; inspect before recovery",
            )
            git(core, repo, "worktree", "add", str(wt), branch)
        else:
            git(core, repo, "worktree", "add", "-b", branch, str(wt), rec["base_sha"])
    rec["allocation"] = "ready"
    persist(root, state, "allocated", {rec_path(state): store.dumps(rec)})


def start_iteration(core, root, state, rec):
    rec["inner"] = "B"
    rec["iteration"] = {
        "id": f"{state['run_id']}-{rec['id']}-I{len(rec['improve_cycles']) + 1}",
        "previous_sha": git(core, Path(rec["worktree"]), "rev-parse", "HEAD"),
    }
    action(state, "implement", "review")


def revision(core, root, state, result, writes):
    decision = text_field(result, "plan_decision")
    need(
        decision in ("no-change", "revise"), "plan_decision must be no-change or revise"
    )
    text_field(result, "plan_reason")
    if decision == "no-change":
        need("dag" not in result, "no-change cannot include a replacement DAG")
        return
    old = core.load_dag(root)
    new = result.get("dag")
    need(isinstance(new, dict), "revise requires a complete candidate dag object")
    need(
        new.get("goal") == old.get("goal")
        and new.get("initial_state") == old.get("initial_state"),
        "plan revision cannot silently change goal or baseline",
    )
    by_id = {x["id"]: x for x in new.get("steps", [])}
    for oldstep in old["steps"]:
        receipt = core.load_receipt(root, oldstep["id"])
        if receipt and receipt["status"] in ("complete", "running"):
            need(
                by_id.get(oldstep["id"]) == oldstep,
                "cannot revise completed or running step; add a corrective pending step",
            )
    writes["backchain/plan.md"] = store.dumps(new, "ShipLoop dependency sequence")
    writes["plan.md"] = text_field(result, "plan")
    validate_candidate(core, root, writes, state)
    state["plan_sha256"] = hashlib.sha256(
        writes["backchain/plan.md"].encode()
    ).hexdigest()
    for path in sorted((root / "steps").glob("*.md")):
        receipt = store.read_record(path)
        receipt["plan_sha256"] = state["plan_sha256"]
        writes[str(path.relative_to(root))] = store.dumps(receipt)
    state["plan_revision"] = state.get("plan_revision", 0) + 1
    if state.get("bound_plan") == str(root / "plan.md"):
        state["bound_plan_hash"] = hashlib.sha256(
            writes["plan.md"].encode()
        ).hexdigest()
    state["plan_wrapper_sha256"] = hashlib.sha256(
        writes["plan.md"].encode()
    ).hexdigest()


def finish_merge(core, root, state, rec):
    """A merge is replayable; never delete the branch or force-remove a worktree."""
    repo, wt = Path(state["repo_root"]), Path(rec["worktree"])
    target = rec["merge_target"]
    need(
        git(core, repo, "rev-parse", rec["branch"]) == target,
        "branch changed after merge intent",
    )
    if wt.exists():
        need(
            not git(core, wt, "status", "--porcelain"),
            "worktree changed after final checks; commit and reverify",
        )
        verified(core, root, state, rec["final_check_action"])
    else:
        need(
            core.git_run(repo, "merge-base", "--is-ancestor", target, "HEAD").returncode
            == 0,
            "worktree missing before merge landed; recover it before retry",
        )
    if (
        core.git_run(repo, "merge-base", "--is-ancestor", target, "HEAD").returncode
        != 0
    ):
        need(
            git(core, repo, "rev-parse", "HEAD") == rec["base_sha"],
            "session baseline changed; integrate it into the step worktree and use repair before revalidation",
        )
        # Existing unrelated dirt is preserved, but never implicitly included in a merge.
        need(
            not git(core, repo, "status", "--porcelain", "--untracked-files=no"),
            "session checkout has tracked changes; resolve them explicitly before merging",
        )
        git(core, repo, "merge", "--no-ff", "--no-edit", target)
    need(
        core.git_run(repo, "merge-base", "--is-ancestor", target, "HEAD").returncode
        == 0,
        "merge ancestry not established",
    )
    if wt.exists():
        git(core, repo, "worktree", "remove", str(wt))
    rec.update(
        status="complete", merged_sha=git(core, repo, "rev-parse", "HEAD"), worktree=""
    )
    return rec


def complete(core, root, state, aid, result):
    need(
        isinstance(result, dict),
        "result must be an object in a shiploop-state Markdown fence",
    )
    result = resolve_draft(result)
    fingerprint = digest(result)
    previous = state["completed_actions"].get(aid)
    if previous:
        need(previous == fingerprint, "conflicting replay of a completed action")
        return
    need(aid == state["action"]["id"], "stale action ID; run next")
    stage = state["stage"]
    writes = {f"results/{aid}.md": store.dumps(result, f"ShipLoop result {stage}")}
    text_field(result, "summary")
    if "journal" in result:
        writes["shiploop-improvements.md"] = proposal_entries(
            root, state, result["journal"]
        )
    if stage == "preflight":
        repo = Path(state["repo_root"])
        need(core.git_repo_ready(repo), "preflight requires a Git repository with HEAD")
        need(
            result.get("baseline") == "committed-head",
            "explicitly select baseline: committed-head; uncommitted files are not included",
        )
        facts = dict(
            result,
            repo=str(repo),
            head=git(core, repo, "rev-parse", "HEAD"),
            dirty=git(core, repo, "status", "--porcelain"),
        )
        writes["preflight.md"] = store.dumps(facts, "ShipLoop readiness and baseline")
        action(state, "intake", "approach")
    elif stage == "approach":
        writes["approach.md"] = text_field(result, "body")
        action(state, "validate-spec", "survey")
    elif stage == "survey":
        writes["environment.md"] = text_field(result, "body")
        with tempfile.TemporaryDirectory(prefix="shiploop-survey-") as tmp:
            store.atomic_write_text(
                Path(tmp) / "environment.md", writes["environment.md"]
            )
            environment, gaps = core.load_environment(Path(tmp))
            if not gaps:
                gaps += core.exclusive_gaps(environment) + core.ui_craft_gaps(
                    environment
                )
            need(not gaps, "; ".join(gaps))
        state["environment_sha256"] = hashlib.sha256(
            writes["environment.md"].encode()
        ).hexdigest()
        action(state, "validate-spec", "research")
    elif stage == "research":
        writes["research.md"] = text_field(result, "body")
        action(state, "validate-spec", "spec")
    elif stage == "spec":
        writes["spec.md"] = text_field(result, "body")
        lifecycle = result.get("lifecycle")
        need(isinstance(lifecycle, dict), "spec requires lifecycle object")
        need(
            isinstance(lifecycle.get("acceptance"), list)
            and lifecycle["acceptance"]
            and all(isinstance(x, str) and x.strip() for x in lifecycle["acceptance"]),
            "lifecycle needs acceptance criteria",
        )
        need(
            lifecycle.get("preparation") in ("none", "dag", "outer-before"),
            "preparation must be none, dag, or outer-before",
        )
        need(
            lifecycle.get("publish") in ("none", "dag", "outer-loop"),
            "publish must be none, dag, or outer-loop",
        )
        need(type(lifecycle.get("quality")) is bool, "quality must be a boolean")
        text_field(lifecycle, "reason")
        with tempfile.TemporaryDirectory(prefix="shiploop-spec-") as tmp:
            store.atomic_write_text(Path(tmp) / "spec.md", writes["spec.md"])
            spec, gaps = core.load_spec(Path(tmp))
            need(
                not gaps and spec["checkable"],
                "; ".join(gaps) or "spec must be checkable",
            )
        state["spec_sha256"] = hashlib.sha256(writes["spec.md"].encode()).hexdigest()
        writes["lifecycle.md"] = store.dumps(lifecycle, "ShipLoop lifecycle placement")
        state["lifecycle_sha256"] = hashlib.sha256(
            writes["lifecycle.md"].encode()
        ).hexdigest()
        action(state, "plan", "sequence")
    elif stage == "sequence":
        text_field(result, "dependency_review")
        dag = result.get("dag")
        need(isinstance(dag, dict), "sequence requires dag object")
        writes["backchain/plan.md"] = store.dumps(dag, "ShipLoop dependency sequence")
        writes["plan.md"] = text_field(result, "plan")
        validate_candidate(core, root, writes, state)
        old_dag = core.load_dag(root)
        if old_dag:
            proposed = {x["id"]: x for x in dag["steps"]}
            for previous in old_dag["steps"]:
                receipt = core.load_receipt(root, previous["id"])
                if receipt and receipt.get("status") in ("complete", "running"):
                    need(
                        proposed.get(previous["id"]) == previous,
                        "migration must preserve completed/running step definitions; add corrective steps instead",
                    )
        lifecycle = store.read_record(root / "lifecycle.md")
        for kind, key in (("preparation", "preparation"), ("publish", "publish")):
            if lifecycle[key] == "dag":
                need(
                    any(x.get("activity") == kind for x in dag["steps"]),
                    f"lifecycle requires a DAG {kind} step marked activity: {kind}",
                )
        need(
            lifecycle["publish"] != "outer-loop"
            or not any(x.get("activity") == "publish" for x in dag["steps"]),
            "outer publish cannot also be in DAG",
        )
        state["plan_sha256"] = hashlib.sha256(
            writes["backchain/plan.md"].encode()
        ).hexdigest()
        for path in (root / "steps").glob("*.md"):
            record = store.read_record(path)
            record["plan_sha256"] = state["plan_sha256"]
            writes[str(path.relative_to(root))] = store.dumps(record)
        state["plan_wrapper_sha256"] = hashlib.sha256(
            writes["plan.md"].encode()
        ).hexdigest()
        if not state.get("bound_plan"):
            state["bound_plan"] = str(root / "plan.md")
            state["bound_plan_hash"] = hashlib.sha256(
                writes["plan.md"].encode()
            ).hexdigest()
        action(
            state,
            "plan" if lifecycle["preparation"] == "outer-before" else "implement",
            "prepare" if lifecycle["preparation"] == "outer-before" else "schedule",
        )
    elif stage == "prepare":
        text_field(result, "evidence")
        writes["preparation.md"] = store.dumps(
            result, "Outer preparation evidence — host reported"
        )
        action(state, "implement", "schedule")
    elif stage == "implement":
        verified(core, root, state)
        text_field(result, "test_review")
        rec = active(root, state)
        rec["implementation_check_action"] = aid
        start_iteration(core, root, state, rec)
        writes[rec_path(state)] = store.dumps(rec)
    elif stage in (
        "review",
        "improve-plan",
        "improve-apply",
        "verify",
        "commit",
        "final-verify",
        "post-inner",
        "merge",
    ):
        rec = active(root, state)
        it = rec.get("iteration", {})
        if stage == "review":
            history = it.get("history")
            need(
                history
                and history.get("head")
                == git(core, Path(rec["worktree"]), "rev-parse", "HEAD"),
                "read current Git history with shiploop history before reviewing",
            )
            required = {
                row["sha"].strip()
                for row in evidence.history(Path(rec["worktree"]), 7, 0)
            }
            need(
                required.issubset(set(history["commits"])),
                "read the latest seven commit bodies (or all available), paging history as needed",
            )
            findings = result.get("findings")
            need(
                isinstance(findings, list)
                and all(
                    isinstance(x, dict)
                    and x.get("severity") in ("trivial", "material")
                    and x.get("summary")
                    for x in findings
                ),
                "findings must list severity and summary",
            )
            text_field(result, "test_review")
            text_field(result, "learnings")
            it["review"] = result
            action(state, "implement", "improve-plan")
        elif stage == "improve-plan":
            text_field(result, "body")
            it["plan"] = result
            action(state, "implement", "improve-apply")
        elif stage == "improve-apply":
            need(
                type(result.get("material")) is bool, "apply requires material boolean"
            )
            text_field(result, "test_changes")
            text_field(result, "learnings")
            it["applied"] = result
            it["applied_fingerprint"] = evidence.fingerprint(
                Path(rec["worktree"]), excluded=exclusions(root, Path(rec["worktree"]))
            )
            action(state, "implement", "verify")
        elif stage == "verify":
            verified(core, root, state)
            # Fixes made while getting checks green were not part of the earlier
            # classification. Conservatively treat them as material, never as a
            # second trivial pass merely because an old result said so.
            it["late_edits"] = it.get("applied_fingerprint") != evidence.fingerprint(
                Path(rec["worktree"]), excluded=exclusions(root, Path(rec["worktree"]))
            )
            it["check_action"] = aid
            action(state, "implement", "commit")
        elif stage == "commit":
            verified(core, root, state, it["check_action"])
            wt = Path(rec["worktree"])
            need(
                not git(core, wt, "status", "--porcelain"),
                "commit all scoped iteration changes before completing commit",
            )
            commit = evidence.validate_commit(
                wt, text_field(result, "commit"), it["previous_sha"], it["id"]
            )
            body = git(core, wt, "show", "-s", "--format=%B", result["commit"])
            for learned in (it["review"]["learnings"], it["applied"]["learnings"]):
                need(
                    learned.strip() in body,
                    "primary commit must include the recorded review and apply learnings verbatim",
                )
            need(
                not any(
                    x.get("primary_commit") == result["commit"]
                    for x in rec["improve_cycles"]
                ),
                "primary commit already used",
            )
            material = (
                it["applied"]["material"]
                or it.get("late_edits", False)
                or any(x["severity"] == "material" for x in it["review"]["findings"])
            )
            outcome = "material" if material else "trivial"
            rec["improve_cycles"].append(
                dict(
                    it, outcome=outcome, primary_commit=result["commit"], commit=commit
                )
            )
            if core.improve_two_clean(rec):
                action(state, "implement", "final-verify")
            else:
                start_iteration(core, root, state, rec)
        elif stage == "final-verify":
            verified(core, root, state)
            rec["final_check_action"] = aid
            rec["final_head"] = git(core, Path(rec["worktree"]), "rev-parse", "HEAD")
            action(state, "implement", "post-inner")
        elif stage == "post-inner":
            need(
                "journal" in result,
                "post-inner requires journal, including [] when no generic proposals",
            )
            verified(core, root, state, rec["final_check_action"])
            revision(core, root, state, result, writes)
            if rec_path(state) in writes:
                rec["plan_sha256"] = state["plan_sha256"]
            rec["plan_review"] = result
            action(state, "implement", "merge")
        else:
            need(
                core.improve_two_clean(rec),
                "two consecutive trivial iterations required",
            )
            if not rec.get("merge_target"):
                need(
                    git(core, Path(state["repo_root"]), "rev-parse", "HEAD")
                    == rec["base_sha"],
                    "session baseline changed; integrate it into the step worktree, then repair and revalidate",
                )
            rec["merge_target"] = rec["final_head"]
            # Durable intent makes an interrupted Git merge recoverable without counting twice.
            persist(root, state, "merge-intent", {rec_path(state): store.dumps(rec)})
            rec = finish_merge(core, root, state, rec)
            writes[rec_path(state)] = store.dumps(rec)
            state.pop("active_step")
            action(state, "implement", "schedule")
        if state.get("active_step"):
            writes[rec_path(state)] = store.dumps(rec)
    elif stage == "coverage":
        gaps = core.residual_gaps(state, "done")
        need(not gaps, "; ".join(gaps))
        writes["coverage.md"] = store.dumps(result, "Outer review coverage")
        action(state, "residual", "quality")
    elif stage == "quality":
        verified(core, root, state)
        text_field(result, "test_review")
        state["outer_check_action"] = aid
        writes["quality.md"] = store.dumps(
            result, "Outer acceptance and integration checks"
        )
        lifecycle = store.read_record(root / "lifecycle.md")
        if lifecycle["quality"]:
            text_field(result, "quality_review")
        action(
            state,
            "residual",
            "publish" if lifecycle["publish"] == "outer-loop" else "handoff",
        )
    elif stage == "publish":
        # No script-triggered external side effects. On ambiguity stay here and inspect.
        verified(core, root, state, state["outer_check_action"])
        for field in ("artifact", "verification", "evidence"):
            text_field(result, field)
        writes["delivery.md"] = store.dumps(
            result, "Publication evidence — host reported"
        )
        action(state, "residual", "handoff")
    elif stage == "handoff":
        verified(core, root, state, state["outer_check_action"])
        need(
            "journal" in result, "handoff requires journal review ([] if no additions)"
        )
        writes["handoff.md"] = store.dumps(result, "ShipLoop final handoff")
        action(state, "done", "done")
    else:
        raise ProtocolError(f"cannot complete stage {stage}")
    state["completed_actions"][aid] = fingerprint
    state["revision"] += 1
    persist(root, state, f"complete:{stage}", writes)


PROMPTS = {
    "preflight": 'Inspect Git baseline, dirty files, runtime, credentials availability (never record secrets), existing lint/tests and any environment preparation needed. Preserve user dirt. Result: summary, baseline="committed-head"; include readiness and preparation findings.',
    "approach": "Create the initial delivery approach before the spec: scope, risks, milestones, prep candidates, and acceptance strategy. Result: summary, body (Markdown).",
    "survey": "Survey existing artifacts, references and tool/writer routes. If a client will call a service, freeze both sides' invocation protocol (service-visible operations and client/HTML call conventions) before any communication is authored. Read references/survey.md and references/activities/validate-spec.md section for environment.md. Result: summary, body (complete environment Markdown with ## machine fenced JSON).",
    "research": "Resolve uncertainties from the survey using evidence; record assumptions and source pointers, or a reason research is not applicable. If a client–service API exists, resolve the real invocation contract from primary docs (service-visible operations; client/HTML call conventions) before spec; do not author communication yet. Result: summary, body (Markdown).",
    "spec": 'Create the checkable spec from approach and research. Result: summary, body (Markdown with done_sentence: and checkable: true), lifecycle={acceptance:[criteria],preparation:"none|dag|outer-before",publish:"none|dag|outer-loop",quality:boolean,reason:"placement rationale"}. Obtain user direction for scope/acceptance ambiguity.',
    "sequence": "Use ShipLoop native dependency planning: draft forward steps, then audit prerequisites backwards one step at a time. Add missing producers or unresolved questions; never invent initial facts. Read the compact references/activities/plan.md (no external planner skill required). Return summary, dependency_review, plan (Markdown with matching done_sentence and Review Coverage), and dag={goal,initial_state,steps,unresolved:[]} OR dag_file (absolute Markdown draft path). Import validates the complete DAG without needing it in chat. Mark required prep/publish steps activity: preparation/publish; plan tests for every produces. When a client will call a service, a producer must freeze the invocation contract before the step that authors call sites.",
    "prepare": "Perform only authorized outer-before preparation. Verify readiness; stop for new permission or external uncertainty. Result: summary, evidence (specific commands/probes/results).",
    "implement": "Implement only the active step; create or expand meaningful tests mapped to each produces. When the step authors client–service calls, tests must cover the real client/HTML invocation path, not only a substitute exec of internals. Run verify with a lint/test manifest, fix failures and repeat until all pass. Then return summary and test_review explaining coverage and changes.",
    "review": 'Run history for this action and read the returned commit bodies and linked evidence. Review code, tests, regressions, and prior learnings. Result: summary, findings:[{severity:"material|trivial",summary}], test_review, learnings. Empty findings is valid; missing tests are material.',
    "improve-plan": "Plan fixes for every finding, test additions/changes and prevention based on Git learnings. Result: summary, body (Markdown plan).",
    "improve-apply": "Apply the improvement plan including trivial fixes and necessary tests. Do not weaken tests to get green. Result: summary, material:boolean, test_changes, learnings. Material findings reset the streak even if this edit is small.",
    "verify": "Run verify for fresh lint and every declared step acceptance test. Repair failures and rerun; completion is refused until all checks pass on unchanged files. Result: summary.",
    "commit": "Create a distinct verbose primary commit on the step branch (not branch main). Include Review:, Changes:, Validation:, Key learnings: sections and the exact ShipLoop-Iteration trailer using the iteration ID above. Include the recorded review.learnings and applied.learnings strings verbatim (retrieve context --section iteration); honest no-new-findings is valid. Use an empty audit commit if no files changed. Stage explicit paths only. Result: summary, commit (full HEAD SHA).",
    "final-verify": "Two trivial-only iterations are recorded. Run verify again on the final tree, including all applied trivial fixes. No stale results or failed tests may exit the inner loop. Result: summary.",
    "post-inner": 'After improvements and passing tests: do the overall learnings require changing broader steps, dependencies, prep, or test strategy? Result: summary, plan_decision="no-change|revise", plan_reason, journal:[proposals]. For revise include complete dag and plan; only pending steps can change. Generic ShipLoop proposals require title,evidence,impact,proposal,test_idea. Do not self-modify the harness.',
    "merge": "The step passed convergence, final checks and broader-plan review. Return summary to merge into the session checkout. Merge is local only; no push or publication.",
    "coverage": "Run the bound Review Coverage activity and commit its ledger. Complete only with a complete, bound, actually tracked clean ledger or an existing explicit bound-plan waiver. Result: summary.",
    "quality": "Run whole-product acceptance/integration checks with verify. Test manifest acceptance entries must cover every exact string in lifecycle.acceptance (retrieve context --section lifecycle), not the prior step's produces. Include a lint check. If lifecycle quality=true, also review broader product quality and record quality_review. Put needed code/test improvements into corrective pending DAG steps with replan; do not bypass inner loops by patching the session checkout. Result: summary, test_review, quality_review when applicable. Failure remains unfinished.",
    "publish": "Perform publication only if authorized and specified. Inspect any existing delivery before retrying to avoid duplicate external effects. Verify the actual entrypoint. Result: summary, artifact, verification, evidence. These publication facts remain host-reported.",
    "handoff": "Summarize delivery, checked acceptance, limitations and a prioritized proposal list from shiploop-improvements.md. Result: summary, journal ([] if no additions). Do not apply generic skill proposals automatically.",
}


def packet(core, root, state):
    stage = state["stage"]
    print(
        f"ShipLoop {core.VERSION} | {state['phase']} / {stage} | revision {state['revision']}"
    )
    print(
        f"Run: {root}\nState: {root / 'state.md'}\nJournal: {root / 'shiploop-improvements.md'}"
    )
    if state.get("paused"):
        print(
            f"Paused, unfinished: {str(state['paused'])[:320]}\nUse shiploop resume --run-dir {shlex.quote(str(root))} when resolved. The full reason and action cursor remain in state.md."
        )
        return
    if stage in ("done", "halted"):
        print(
            f"Stop. Handoff: {root / 'handoff.md'}\nReview and propose journal entries; no automatic harness updates."
        )
        entries = store.read_record(root / "shiploop-improvements.md")
        print(f"ShipLoop proposals recorded: {len(entries)}")
        for entry in entries[:5]:
            print(f"- {entry['title'][:120]}: {entry['impact'][:180]}")
        if len(entries) > 5:
            print(
                "Additional proposals are in the linked journal; use context --section journal to page through them."
            )
        return
    aid = state["action"]["id"]
    print(f"Action: {aid}\nWorking directory: {repo_for(root, state)}")
    if state.get("active_step"):
        rec = active(root, state)
        print(f"Step: {rec['id']} | receipt: {root / rec_path(state)}")
        print(
            f"Step prompt/produces: {root / 'backchain/plan.md'} (select only {rec['id']})"
        )
        if rec.get("iteration"):
            print(f"Iteration: {rec['iteration']['id']}")
            print(
                "Use context --section iteration for only the current review/plan, not the full receipt history."
            )
    available = [
        name
        for name in (
            "prompt",
            "approach",
            "environment",
            "research",
            "spec",
            "lifecycle",
            "plan",
        )
        if (root / f"{name}.md").is_file()
    ]
    print(
        "Available durable context: "
        + ", ".join(
            available
            + ["journal"]
            + (["step", "iteration"] if state.get("active_step") else [])
        )
    )
    if state.get("previous_planning"):
        print(
            f"Previous planning evidence (archived, not active): {state['previous_planning']}"
        )
    instruction = PROMPTS.get(stage, "Run next to resume scheduling.")
    print(instruction.replace("references/", str(core.REF_DIR) + "/"))
    cmd = f"{shlex.quote(str(core.PACKAGE_ROOT / 'scripts/shiploop'))}"
    options = f"--run-dir {shlex.quote(str(root))} --action {aid}"
    print(
        f"Bounded context: {cmd} context --run-dir {shlex.quote(str(root))} --section <available-section> --offset 0 --limit 4000"
    )
    if stage in ("implement", "verify", "final-verify", "quality"):
        manifest_input = (
            root / "inbox" / f"checks-{state.get('active_step', 'outer')}.md"
        )
        print(f"Author/update manifest: {manifest_input}")
        print(
            f"Checks: {cmd} verify {options} --manifest {shlex.quote(str(manifest_input))}"
        )
    if stage == "review":
        print(f"History: {cmd} history {options} --limit 7 --skip 0")
    print(
        f"Result format: one ```shiploop-state JSON object fence in a Markdown file. Protocol/schema: {core.REF_DIR / 'action-protocol.md'}"
    )
    result_input = root / "inbox" / f"{aid}.md"
    print(f"Write the result to {result_input} (metadata, not product files).")
    print(
        f"When done: {cmd} complete {options} --result {shlex.quote(str(result_input))}"
    )
    print(
        "Use the returned next action; do not infer completion from chat memory. If blocked, report the exact blocker; do not certify success."
    )


def migrate(core, root):
    need(
        not (root / "state.md").exists() and not (root / "migration.md").exists(),
        "Markdown authority already exists or was removed; refusing JSON resurrection",
    )
    oldpath = root / "state.json"
    need(
        oldpath.is_file() and not oldpath.is_symlink(),
        "no legacy state.json to migrate",
    )
    need(
        not (root / "legacy-backup").exists(),
        "legacy backup already exists; inspect/restore it instead of overwriting",
    )
    old = json.loads(oldpath.read_text())
    need(isinstance(old, dict) and old.get("run_id"), "invalid legacy state")
    writes, deletes = {}, []
    sources = [oldpath]
    sources += [x for x in (root / "steps").glob("*.json")]
    if (root / "backchain/plan.json").exists():
        sources.append(root / "backchain/plan.json")
    # Only known legacy ShipLoop sidecars: a custom run directory can share a
    # product checkout, so a JSON glob would wrongly move package/tsconfig data.
    sources += [
        root / name for name in ("spec.json", "plan.json") if (root / name).exists()
    ]
    for path in sources:
        need(not path.is_symlink(), "legacy symlink refused")
        relative = str(path.relative_to(root))
        body = path.read_text()
        writes[f"legacy-backup/{relative}"] = body
        if path != oldpath and (
            relative.startswith("steps/") or relative == "backchain/plan.json"
        ):
            record = json.loads(body)
            if relative.startswith("steps/"):
                record["legacy_improve_cycles"] = record.pop("improve_cycles", [])
                if record.get("status") == "running":
                    record.update(inner="A", improve_cycles=[])
            writes[str(Path(relative).with_suffix(".md"))] = store.dumps(record)
        deletes.append(relative)
    old.update(
        version=3, revision=0, completed_actions={}, legacy_phase=old.get("phase")
    )
    # Restart planning checkpoints, never erase code, branches, or historical receipts.
    action(old, "intake", "preflight")
    old["environment_sha256"] = old["spec_sha256"] = old["plan_sha256"] = ""
    old["artifacts"] = dict(
        old.get("artifacts", {}),
        backchain=str(root / "backchain/plan.md"),
        handoff_md=str(root / "handoff.md"),
        journal_md=str(root / "shiploop-improvements.md"),
    )
    old["artifacts"].pop("recap_html", None)
    old.pop("active_step", None)
    writes["state.md"] = store.dumps(old, "ShipLoop migrated state")
    writes["run.md"] = store.dumps({"run_id": old["run_id"], "authority": "state.md"})
    writes["migration.md"] = store.dumps(
        {
            "from": 2,
            "to": 3,
            "backup": str(root / "legacy-backup"),
            "note": "Revalidate planning; running work must pass new evidence gates. No branches deleted.",
        }
    )
    writes["history.md"] = store.dumps(
        [{"event": "migrate", "legacy_phase": old["legacy_phase"]}]
    )
    if (root / "history.jsonl").exists():
        writes["legacy-backup/history.jsonl"] = (root / "history.jsonl").read_text()
        deletes.append("history.jsonl")
    if not (root / "shiploop-improvements.md").exists():
        writes["shiploop-improvements.md"] = store.dumps(
            [], "ShipLoop improvement proposals"
        )
    store.transaction(root, writes, deletes)


def main(core, argv=None):
    parser = argparse.ArgumentParser(
        prog="shiploop",
        description="Markdown-authoritative, action-oriented session harness",
    )
    subs = parser.add_subparsers(dest="command", required=True)
    for name in (
        "init",
        "next",
        "status",
        "context",
        "complete",
        "verify",
        "history",
        "journal",
        "halt",
        "pause",
        "resume",
        "repair",
        "replan",
        "revisit",
        "migrate",
    ):
        sub = subs.add_parser(name)
        sub.add_argument("--run-dir")
        if name == "init":
            sub.add_argument("--prompt", required=True)
            sub.add_argument("--repo")
            sub.add_argument("--bound-plan", default="")
            sub.add_argument("--force", action="store_true")
        if name in (
            "complete",
            "verify",
            "history",
            "journal",
            "repair",
            "replan",
            "revisit",
        ):
            sub.add_argument("--action", required=True)
        if name in ("complete", "journal", "replan"):
            sub.add_argument("--result", required=True)
        if name == "verify":
            sub.add_argument("--manifest", required=True)
            sub.add_argument("--timeout", type=float, default=60)
            sub.add_argument("--reason", default="")
        if name == "history":
            sub.add_argument("--limit", type=int, default=7)
            sub.add_argument("--skip", type=int, default=0)
            sub.add_argument("--full", action="store_true")
        if name == "context":
            sub.add_argument(
                "--section",
                required=True,
                choices=(
                    "prompt",
                    "step",
                    "iteration",
                    "spec",
                    "environment",
                    "plan",
                    "lifecycle",
                    "journal",
                    "approach",
                    "research",
                ),
            )
            sub.add_argument("--offset", type=int, default=0)
            sub.add_argument("--limit", type=int, default=4000)
            sub.add_argument("--digest")
        if name == "revisit":
            sub.add_argument("--to", required=True, choices=("survey", "spec"))
        if name in ("halt", "pause", "repair", "revisit"):
            sub.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    raw_root = args.run_dir
    if args.command == "init" and not raw_root and args.repo:
        raw_root = str(Path(args.repo) / ".shiploop")
    unresolved_root = core.run_dir_from_arg(raw_root, walk=args.command != "init")
    if unresolved_root.is_symlink():
        print("ShipLoop blocked: run directory must not be a symlink", file=sys.stderr)
        return 2
    root = unresolved_root.resolve()
    try:
        with core.run_lock(root):
            if args.command == "init":
                need(bool(args.prompt.strip()), "prompt must not be empty")
                need(
                    not args.force,
                    "--force is no longer destructive: use a fresh --run-dir; existing journals and worktrees are preserved",
                )
                if (root / "state.md").exists():
                    packet(core, root, core.load_state(root))
                    return 0
                need(
                    not (root / "state.json").exists(),
                    "legacy run: migrate explicitly first",
                )
                need(
                    not (root / "migration.md").exists(),
                    "missing Markdown authority; restore it, do not reinitialize",
                )
                need(
                    not (root / "run.md").exists()
                    and not (root / "history.md").exists(),
                    "existing run lost state.md; restore it instead of reinitializing",
                )
                need(
                    not any(path.name != ".lock" for path in root.iterdir()),
                    "new run directory must be dedicated and empty; choose a fresh --run-dir to preserve existing files",
                )
                need(
                    root != Path(args.repo or os.getcwd()).resolve(),
                    "run directory cannot be the product repository root",
                )
                state = core.default_state(
                    root,
                    prompt=args.prompt,
                    implementer="host",
                    bound_plan=str(Path(args.bound_plan).resolve())
                    if args.bound_plan
                    else "",
                    repo=str(Path(args.repo or os.getcwd()).resolve()),
                )
                action(state, "intake", "preflight")
                persist(
                    root,
                    state,
                    "init",
                    {
                        "run.md": store.dumps(
                            {"run_id": state["run_id"], "authority": "state.md"}
                        ),
                        "prompt.md": args.prompt + "\n",
                        "shiploop-improvements.md": store.dumps(
                            [], "ShipLoop improvement proposals"
                        ),
                    },
                )
            elif args.command == "migrate":
                migrate(core, root)
                state = core.load_state(root)
            else:
                state = core.load_state(root)
                validate_state(state)
                if args.command not in (
                    "halt",
                    "pause",
                    "status",
                    "context",
                    "revisit",
                ):
                    core.check_frozen_hashes(state, root, None)
                    for key, name in (
                        ("lifecycle_sha256", "lifecycle.md"),
                        ("plan_wrapper_sha256", "plan.md"),
                    ):
                        if state.get(key):
                            need(
                                core.sha256_file(root / name) == state[key],
                                f"{name} hash drift; restore frozen content or use a validated plan revision",
                            )
                if state.get("paused") and args.command not in (
                    "resume",
                    "halt",
                    "pause",
                    "status",
                    "next",
                    "journal",
                    "context",
                    "revisit",
                ):
                    raise ProtocolError(
                        "run paused; resolve the blocker and resume before continuing"
                    )
                if args.command == "context":
                    need(
                        0 <= args.offset and 1 <= args.limit <= 8000,
                        "context offset >= 0 and limit 1..8000 characters",
                    )
                    if args.section == "step":
                        need(state.get("active_step"), "no active step")
                        body = store.dumps(
                            core.steps_by_id(root)[state["active_step"]], "Current step"
                        )
                    elif args.section == "iteration":
                        body = store.dumps(
                            active(root, state).get("iteration", {}),
                            "Current iteration",
                        )
                    else:
                        name = (
                            "shiploop-improvements"
                            if args.section == "journal"
                            else args.section
                        )
                        path = safe_run_path(root, f"{name}.md")
                        need(
                            path.is_file(),
                            f"{args.section} is not created yet at stage {state['stage']}; use an available context section from next",
                        )
                        body = path.read_text()
                    checksum = hashlib.sha256(body.encode()).hexdigest()
                    need(
                        not args.digest or args.digest == checksum,
                        "context changed between pages; restart at offset 0",
                    )
                    end = min(len(body), args.offset + args.limit)
                    print(
                        f"Context {args.section}; digest {checksum}; characters {args.offset}:{end}/{len(body)}"
                    )
                    print(body[args.offset : end])
                    if end < len(body):
                        print(
                            f"Continue: --offset {end} --limit {args.limit} --digest {checksum}"
                        )
                    return 0
                elif args.command == "complete":
                    complete(
                        core,
                        root,
                        state,
                        args.action,
                        store.read_record(Path(args.result)),
                    )
                elif args.command in ("verify", "history", "journal"):
                    need(args.action == state["action"]["id"], "stale action ID")
                    if args.command == "verify":
                        need(
                            state["stage"]
                            in ("implement", "verify", "final-verify", "quality"),
                            "verify is not the active activity",
                        )
                        need(
                            0 < args.timeout <= 3600,
                            "timeout must be in (0, 3600] seconds per check",
                        )
                        manifest = store.read_record(Path(args.manifest))
                        repo, produces = check_target(core, root, state)
                        evidence.validate_manifest(manifest, produces)
                        need(
                            any(x["kind"] == "lint" for x in manifest["checks"]),
                            "every iteration requires a lint process; no public waiver",
                        )
                        manifest_path = (
                            f"manifests/{state.get('active_step', 'outer')}.md"
                        )
                        old = (
                            store.read_record(root / manifest_path)
                            if (root / manifest_path).exists()
                            else None
                        )
                        if old and digest(old["manifest"]) != digest(manifest):
                            need(
                                bool(args.reason.strip()),
                                "changed manifest requires --reason explaining test expansion or correction; never weaken acceptance to get green",
                            )
                        attempt = uuid.uuid4().hex
                        log_directory = safe_run_path(
                            root, f"logs/{args.action}/{attempt}"
                        )
                        results = evidence.run_checks(
                            repo,
                            manifest,
                            log_directory,
                            args.action,
                            timeout=args.timeout,
                            excluded=exclusions(root, repo),
                        )
                        record = {
                            "manifest": manifest,
                            "results": results,
                            "reason": args.reason,
                            "previous_manifest_digest": digest(old["manifest"])
                            if old
                            else None,
                        }
                        persist(
                            root,
                            state,
                            "checks",
                            {
                                f"checks/{args.action}.md": store.dumps(record),
                                f"check-attempts/{args.action}-{attempt}.md": store.dumps(
                                    record
                                ),
                                manifest_path: store.dumps(
                                    {
                                        "manifest": manifest,
                                        "reason": args.reason,
                                        "action": args.action,
                                    }
                                ),
                            },
                        )
                        print(
                            f"Checks {'PASS' if results['all_passed'] else 'FAIL'}: {root / 'checks' / (args.action + '.md')}"
                        )
                        if not results["all_passed"]:
                            print(
                                "The current action remains unfinished. Read the check record and logs, repair failures, and rerun verify with the same action ID; do not complete or skip the tests."
                            )
                            return 2
                    elif args.command == "history":
                        need(
                            state["stage"] == "review",
                            "history recording requires Improve review stage",
                        )
                        need(
                            1 <= args.limit <= 20 and args.skip >= 0,
                            "history limit 1..20; skip >= 0",
                        )
                        rec = active(root, state)
                        rows = evidence.history(
                            Path(rec["worktree"]), args.limit, args.skip
                        )
                        need(bool(rows), "history page is empty")
                        old = rec["iteration"].get("history", {})
                        current = git(core, Path(rec["worktree"]), "rev-parse", "HEAD")
                        seen = (
                            old.get("commits", []) if old.get("head") == current else []
                        )
                        rec["iteration"]["history"] = {
                            "head": current,
                            "commits": list(
                                dict.fromkeys(seen + [r["sha"].strip() for r in rows])
                            ),
                        }
                        persist(
                            root,
                            state,
                            "history-reviewed",
                            {
                                rec_path(state): store.dumps(rec),
                                f"history-pages/{args.action}-{args.skip}.md": store.dumps(
                                    rows
                                ),
                            },
                        )
                        if args.full:
                            print(store.dumps(rows, "Git history — full commit bodies"))
                        else:
                            for row in rows:
                                print(
                                    f"{row['sha'].strip()} {row['body'].splitlines()[0][:160] if row['body'].splitlines() else ''}"
                                )
                            print(
                                f"Read full bodies from {root / 'history-pages' / (args.action + '-' + str(args.skip) + '.md')}; use --limit 1 --skip N --full to retrieve one at a time. Follow relevant learning references."
                            )
                        return 0
                    else:
                        entry = store.read_record(Path(args.result))
                        persist(
                            root,
                            state,
                            "journal",
                            {
                                "shiploop-improvements.md": proposal_entries(
                                    root, state, entry
                                )
                            },
                        )
                elif args.command == "halt":
                    action(state, "halted", "halted")
                    state["halt_reason"] = args.reason
                    persist(
                        root,
                        state,
                        "halt",
                        {
                            "handoff.md": store.dumps(
                                {
                                    "status": "unfinished",
                                    "reason": args.reason,
                                    "journal": str(root / "shiploop-improvements.md"),
                                }
                            )
                        },
                    )
                elif args.command == "pause":
                    need(bool(args.reason.strip()), "pause needs a reason")
                    state["paused"] = args.reason
                    persist(root, state, "pause")
                elif args.command == "resume":
                    need(state.get("paused"), "run is not paused")
                    state.pop("paused")
                    persist(root, state, "resume")
                elif args.command == "repair":
                    need(args.action == state["action"]["id"], "stale action ID")
                    need(
                        state.get("active_step")
                        and state["stage"]
                        in (
                            "review",
                            "improve-plan",
                            "improve-apply",
                            "verify",
                            "commit",
                            "final-verify",
                            "post-inner",
                            "merge",
                        ),
                        "repair requires an active inner loop",
                    )
                    rec = active(root, state)
                    need(
                        not rec.get("merge_target"),
                        "merge already started; inspect Git and retry merge, do not rewrite its branch",
                    )
                    need(bool(args.reason.strip()), "repair needs a reason")
                    baseline = git(core, Path(state["repo_root"]), "rev-parse", "HEAD")
                    if baseline != rec["base_sha"]:
                        need(
                            core.git_run(
                                Path(rec["worktree"]),
                                "merge-base",
                                "--is-ancestor",
                                baseline,
                                "HEAD",
                            ).returncode
                            == 0,
                            "integrate the current session HEAD into the step worktree before repair",
                        )
                        rec["base_sha"] = baseline
                    rec["improve_cycles"].append(
                        {
                            "outcome": "material",
                            "kind": "repair-checkpoint",
                            "reason": args.reason,
                            "interrupted_iteration": rec.get("iteration"),
                        }
                    )
                    start_iteration(core, root, state, rec)
                    persist(root, state, "repair", {rec_path(state): store.dumps(rec)})
                elif args.command == "revisit":
                    need(args.action == state["action"]["id"], "stale action ID")
                    need(
                        state["stage"]
                        in (
                            "approach",
                            "survey",
                            "research",
                            "spec",
                            "sequence",
                            "prepare",
                        ),
                        "revisit is only for planning before execution",
                    )
                    need(
                        not list((root / "steps").glob("*.md")),
                        "cannot revisit frozen contracts underneath running or completed work; seek user direction",
                    )
                    need(bool(args.reason.strip()), "revisit needs a reason")
                    if args.to == "spec":
                        need(
                            (root / "environment.md").is_file(),
                            "survey must be completed before revisiting spec",
                        )
                    names = ["spec.md", "lifecycle.md", "plan.md", "backchain/plan.md"]
                    keys = [
                        "spec_sha256",
                        "lifecycle_sha256",
                        "plan_sha256",
                        "plan_wrapper_sha256",
                    ]
                    if args.to == "survey":
                        names += ["environment.md", "research.md"]
                        keys += ["environment_sha256"]
                    writes, deletes = {}, []
                    for name in names:
                        source = safe_run_path(root, name)
                        if source.is_file():
                            writes[f"planning-history/{args.action}/{name}"] = (
                                source.read_text()
                            )
                            deletes.append(name)
                    for key in keys:
                        state[key] = ""
                    if state.get("bound_plan") == str(root / "plan.md"):
                        state["bound_plan"] = state["bound_plan_hash"] = ""
                    writes[f"planning-history/{args.action}/reason.md"] = store.dumps(
                        {"reason": args.reason, "to": args.to}
                    )
                    state["completed_actions"][args.action] = digest(
                        {"command": "revisit", "to": args.to, "reason": args.reason}
                    )
                    state["previous_planning"] = str(
                        root / "planning-history" / args.action
                    )
                    state.pop("paused", None)
                    state["revision"] += 1
                    action(state, "validate-spec", args.to)
                    # Include both the action and archived dependent files in one WAL.
                    events = store.read_record(root / "history.md")
                    events.append(
                        {
                            "event": "revisit",
                            "reason": args.reason,
                            "action": state["action"],
                        }
                    )
                    writes["state.md"], writes["history.md"] = (
                        store.dumps(state),
                        store.dumps(events),
                    )
                    store.transaction(root, writes, deletes)
                elif args.command == "replan":
                    need(args.action == state["action"]["id"], "stale action ID")
                    need(
                        state["stage"] in ("coverage", "quality")
                        and not state.get("active_step"),
                        "outer replan requires coverage or quality stage",
                    )
                    result = resolve_draft(store.read_record(Path(args.result)))
                    need(
                        result.get("plan_decision") == "revise",
                        "outer replan must propose a revision",
                    )
                    text_field(result, "summary")
                    writes = {
                        f"results/{args.action}.md": store.dumps(
                            result, "Outer-loop corrective plan"
                        )
                    }
                    revision(core, root, state, result, writes)
                    revised_dag = store.loads(writes["backchain/plan.md"])
                    need(
                        any(
                            core.load_receipt(root, x["id"]) is None
                            for x in revised_dag["steps"]
                        ),
                        "outer replan must add a corrective step",
                    )
                    if "journal" in result:
                        writes["shiploop-improvements.md"] = proposal_entries(
                            root, state, result["journal"]
                        )
                    state.pop("outer_check_action", None)
                    state["completed_actions"][args.action] = digest(result)
                    state["revision"] += 1
                    action(state, "implement", "schedule")
                    persist(root, state, "outer-replan", writes)
            if (
                state["stage"] == "schedule"
                and not state.get("paused")
                and args.command != "status"
            ):
                schedule(core, root, state)
            if args.command != "status" and not state.get("paused"):
                ensure_worktree(core, root, state)
            packet(core, root, state)
        return 0
    except (
        ProtocolError,
        store.StorageError,
        evidence.EvidenceError,
        OSError,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        print(f"ShipLoop blocked: {exc}", file=sys.stderr)
        return 2
