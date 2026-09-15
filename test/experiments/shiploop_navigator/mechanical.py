#!/usr/bin/env python3
"""Opt-in stdlib-only mechanical checks for the ShipLoop navigator.

This is a standalone experiment, not a normal test module. It drives only the
navigator API and its generated CLI callbacks. All repositories and run state
are temporary directories outside the source tree; it never initializes Git or
asks ShipLoop to perform project work.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
NAVIGATOR = SCRIPTS / "shiploop_navigator.py"
REFERENCE = ROOT / "skills" / "shiploop" / "references" / "navigator.md"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402


# Independent oracle: the runner never reads navigator.STAGES or its routing
# helpers. document and carry-forward are the two graph-dependent special cases.
FLOW = (
    "intake discovery research research-improve spec spec-improve test-strategy "
    "plan plan-improve step-plan step-plan-improve implement test-refine test-author "
    "document verify product-improve integrate carry-forward system-test outer-improve "
    "release-plan release release-verify handoff done"
).split()
NEXT = dict(zip(FLOW, FLOW[1:])) | {"skill-validate": "verify"}
RACE_PROMPT_BYTES = 196_608


def fail(kind: str, message: str) -> None:
    raise RuntimeError(f"{kind}: {message}")


def need(condition: bool, message: str, kind: str = "product") -> None:
    if not condition:
        fail(kind, message)


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def canonical(path: str | Path) -> Path:
    """Normalize macOS's /var and /private/var aliases before comparison."""
    return Path(os.path.realpath(os.fspath(path)))


def deadline(end: float, label: str, maximum: float = 20.0) -> float:
    remaining = end - time.monotonic()
    need(remaining > 0, f"deadline expired while {label}", "harness")
    return min(maximum, remaining)


def result(outcome: str, summary: str, **extra: Any) -> dict[str, Any]:
    return {"outcome": outcome, "summary": summary, **extra}


def route(stage: str, *, skill: bool = False, future: bool = False) -> str:
    if stage == "document":
        return "skill-validate" if skill else "verify"
    if stage == "carry-forward":
        return "step-plan" if future else "system-test"
    try:
        return NEXT[stage]
    except KeyError:
        fail("oracle", f"missing route for {stage}")


def verify_oracle() -> None:
    need(FLOW[-1] == "done" and len(FLOW) == len(set(FLOW)), "invalid frozen stage list", "oracle")
    need(route("handoff") == "done", "handoff must be terminal", "oracle")
    need(route("document") == "verify" and route("document", skill=True) == "skill-validate", "invalid document edges", "oracle")
    need(route("carry-forward", future=True) == "step-plan", "invalid work continuation", "oracle")
    need(route("carry-forward") == "system-test", "invalid final work edge", "oracle")


def invoke(state: Mapping[str, Any], operation: Callable[[], dict[str, Any]], label: str, *, reject: bool = False) -> dict[str, Any] | None:
    """Call one public navigator operation and prove rejected input is unchanged."""
    before = copy.deepcopy(state)
    try:
        updated = operation()
    except navigator.NavigatorError as exc:
        if not reject:
            fail("product", f"{label}: legal operation rejected: {exc}")
        need(state == before, f"{label}: rejected operation changed input")
        return None
    if reject:
        fail("product", f"{label}: illegal operation was accepted")
    need(state == before, f"{label}: operation mutated input")
    return updated


def expect(state: Mapping[str, Any], stage: str, status: str, queue: list[dict[str, str]], index: int, completed: list[str], counts: Counter[str], label: str) -> None:
    action = state.get("action", {})
    need(state.get("stage") == stage and state.get("status") == status and action.get("stage") == stage, f"{label}: expected {stage}/{status}, got {state.get('stage')}/{state.get('status')}")
    need(state.get("work_items") == queue and state.get("work_index") == index and state.get("completed_work_items") == completed, f"{label}: work queue changed unexpectedly")
    counts["work_queue_assertions"] += 1


def semantic_replay(state: dict[str, Any], action: str, payload: dict[str, Any], label: str, counts: Counter[str]) -> None:
    same = {key: clone(payload[key]) for key in ("summary", "evidence_refs", "work_items", "choices", "outcome") if key in payload}
    replay = invoke(state, lambda: navigator.apply(state, action, same), label + " semantic replay")
    need(replay == state, f"{label}: semantic replay changed state")
    conflict = clone(payload)
    conflict["summary"] += " conflicting replay"
    invoke(state, lambda: navigator.apply(state, action, conflict), label + " conflict replay", reject=True)
    counts["semantic_replays"] += 1
    counts["conflicting_rejections"] += 1


def queue_rows(walk: int, count: int, prefix: str) -> list[dict[str, str]]:
    need(count >= 1, "generated empty plan queue", "oracle")
    return [{"id": f"W{i}", "title": f"{prefix} work item {i} for walk {walk}", "context": f"Generated {walk}/{i}."} for i in range(1, count + 1)]


def future_rows(walk: int, count: int) -> list[dict[str, str]]:
    return [{"id": f"F{walk}_{i}", "title": f"Generated future item {i} for walk {walk}", "context": f"Added at carry-forward {walk}."} for i in range(1, count + 1)]


def noise_modes(rng: random.Random, walk: int, stage: str, step: int) -> list[str]:
    modes = [("pause", "repeat", "blocked", "illegal")[walk % 4]] if stage == "intake" and step == 0 else []
    if rng.random() < 0.48:
        modes.append(rng.choice(("pause", "repeat", "blocked", "illegal")))
    if rng.random() < 0.12:
        modes.append(rng.choice(("pause", "repeat", "blocked", "illegal")))
    return modes


def add_noise(state: dict[str, Any], rng: random.Random, walk: int, step: int, queue: list[dict[str, str]], index: int, completed: list[str], counts: Counter[str]) -> dict[str, Any]:
    for number, mode in enumerate(noise_modes(rng, walk, state["stage"], step), 1):
        label = f"walk {walk} {state['stage']} noise {number} {mode}"
        if mode == "illegal":
            choice = rng.choice(("wrong-action", "forged-route", "illegal-resume"))
            if choice == "wrong-action":
                invoke(state, lambda: navigator.apply(state, "nav-mechanical-stale", result("done", "Generated stale action.")), label, reject=True)
            elif choice == "forged-route":
                invoke(state, lambda: navigator.apply(state, state["action"]["id"], result("done", "Generated forged route.", next="done")), label, reject=True)
            else:
                invoke(state, lambda: navigator.control(state, "resume", "Generated illegal resume."), label, reject=True)
            counts["illegal_attempts"] += 1
            counts[f"illegal_{choice}"] += 1
        elif mode == "pause":
            action = state["action"]["id"]
            paused = invoke(state, lambda: navigator.control(state, "pause", "Generated pause."), label + " pause")
            expect(paused, state["stage"], "paused", queue, index, completed, counts, label + " paused")
            need(paused["action"]["id"] == action, f"{label}: pause changed action identity")
            state = invoke(paused, lambda: navigator.control(paused, "resume", "Generated resume."), label + " resume")
            expect(state, paused["stage"], "active", queue, index, completed, counts, label + " resumed")
            need(state["action"]["id"] == action, f"{label}: pause/resume changed action identity")
            counts["pause_resume"] += 1
        elif mode == "repeat":
            stage, action = state["stage"], state["action"]["id"]
            payload = result("repeat", "Generated repeat.", evidence_refs=["mechanical/repeat"])
            state = invoke(state, lambda: navigator.apply(state, action, payload), label)
            expect(state, stage, "active", queue, index, completed, counts, label + " repeated")
            need(state["action"]["id"] != action, f"{label}: repeat did not renew action identity")
            semantic_replay(state, action, payload, label, counts)
            counts["repeat"] += 1
        else:
            action = state["action"]["id"]
            blocked = invoke(state, lambda: navigator.apply(state, action, result("blocked", "Generated blocker.")), label)
            expect(blocked, state["stage"], "blocked", queue, index, completed, counts, label + " blocked")
            need(blocked["action"]["id"] != action, f"{label}: blocked result did not renew pending action")
            pending = blocked["action"]["id"]
            state = invoke(blocked, lambda: navigator.control(blocked, "resume", "Generated blocker resolved."), label + " resume")
            expect(state, blocked["stage"], "active", queue, index, completed, counts, label + " resumed")
            need(state["action"]["id"] == pending, f"{label}: blocked/resume changed pending action")
            counts["blocked_resume"] += 1
    return state


def walk(number: int, seed: int, end: float) -> dict[str, Any]:
    rng, counts = random.Random(seed), Counter()
    prompt = f"Mechanical navigator walk {number}: no project work is requested."
    state = navigator.new_state(
        f"/mechanical/no-project-{number}", prompt, protocol_version=1
    )
    queue, index, completed = [{"id": "W1", "title": prompt}], 0, []
    expect(state, "intake", "active", queue, index, completed, counts, f"walk {number} initial")
    carry_decided, steps, skill_edges = False, 0, Counter()
    while state["status"] != "done":
        deadline(end, f"walking model {number}")
        need(steps < 90, f"walk {number} exceeded generated path bound", "harness")
        expect(state, state["stage"], "active", queue, index, completed, counts, f"walk {number} before step")
        state = add_noise(state, rng, number, steps, queue, index, completed, counts)
        stage, action = state["stage"], state["action"]["id"]
        payload = result("done", f"Generated completion for walk {number} at {stage}.", evidence_refs=[f"mechanical/walk-{number}/{stage}"])
        next_queue, next_index, next_completed, skill = clone(queue), index, list(completed), False
        if stage == "plan":
            next_queue = queue_rows(number, rng.randint(1, 3), "planned")
            payload["work_items"] = clone(next_queue)
            counts["plan_queue_replacements"] += 1
        elif stage == "plan-improve" and rng.random() < 0.56:
            next_queue = queue_rows(number, rng.randint(1, 3), "plan-improved")
            payload["work_items"] = clone(next_queue)
            counts["plan_improve_queue_replacements"] += 1
        elif stage == "document":
            skill = bool((number + index + rng.randrange(2)) % 2)
            payload["choices"] = {"skill_required": skill}
            skill_edges["with_skill" if skill else "without_skill"] += 1
        elif stage == "carry-forward":
            need(index < len(queue), f"walk {number} has no current carry-forward item", "oracle")
            if not carry_decided and (number % 3 == 0 or rng.random() < 0.38):
                next_queue = clone(queue[: index + 1]) + future_rows(number, 1 + rng.randrange(2))
                payload["work_items"] = clone(next_queue[index + 1 :])
                counts["carry_forward_queue_replacements"] += 1
            carry_decided = True
            next_completed.append(queue[index]["id"])
            next_index += 1
        target = route(stage, skill=skill, future=stage == "carry-forward" and next_index < len(next_queue))
        state = invoke(state, lambda: navigator.apply(state, action, payload), f"walk {number} {stage}")
        queue, index, completed = next_queue, next_index, next_completed
        expect(state, target, "done" if target == "done" else "active", queue, index, completed, counts, f"walk {number} {stage} route")
        semantic_replay(state, action, payload, f"walk {number} {stage}", counts)
        counts["ordinary_done"] += 1
        steps += 1
    expect(state, "done", "done", queue, index, completed, counts, f"walk {number} terminal")
    invoke(state, lambda: navigator.apply(state, state["action"]["id"], result("done", "Terminal attempt.")), f"walk {number} terminal apply", reject=True)
    invoke(state, lambda: navigator.control(state, "halt", "Terminal attempt."), f"walk {number} terminal control", reject=True)
    counts["terminal_rejections"] += 2
    need(completed == [row["id"] for row in queue], f"walk {number} did not complete queue")
    return {"walk": number, "seed": seed, "cursor_steps": steps, "history_entries": len(state["history"]), "final_work_items": [row["id"] for row in queue], "completed_work_items": completed, "noise_counts": dict(sorted(counts.items())), "skill_edges": dict(skill_edges)}


def models(seed: int, walks: int, end: float) -> dict[str, Any]:
    rng, totals, summaries, failures = random.Random(seed), Counter(), [], []
    for number in range(walks):
        case_seed = rng.getrandbits(64)
        try:
            summary = walk(number, case_seed, end)
        except Exception as exc:  # Independent walks can still report later failures.
            failures.append({"walk": number, "failure": str(exc)})
            continue
        summaries.append(summary)
        totals.update(summary["noise_counts"])
    coverage = {"pause_resume": totals["pause_resume"], "repeat_identity_renewal": totals["repeat"], "blocked_resume": totals["blocked_resume"], "illegal_rejections": totals["illegal_attempts"], "semantic_replay": totals["semantic_replays"], "conflict_rejections": totals["conflicting_rejections"], "terminal_rejections": totals["terminal_rejections"], "queue_preservation_assertions": totals["work_queue_assertions"], "carry_forward_queue_replacements": totals["carry_forward_queue_replacements"]}
    if missing := [name for name, value in coverage.items() if not value]:
        failures.append({"walk": "coverage", "failure": "harness: missing " + ", ".join(missing)})
    samples = summaries[:3] + (summaries[-1:] if len(summaries) > 3 else [])
    return {"status": "passed" if not failures and len(summaries) == walks else "failed", "master_seed": seed, "walk_seed_derivation": "random.Random(master_seed).getrandbits(64), ascending walk order", "walks_requested": walks, "walks_completed": len(summaries), "walks_failed": len(failures), "counts": dict(sorted(totals.items())), "coverage": coverage, "walk_summary_samples": samples, "failures": failures}


def run(argv: list[str], cwd: Path, end: float, label: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, cwd=cwd, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, text=True, capture_output=True, timeout=deadline(end, label), check=False)
    except subprocess.TimeoutExpired:
        fail("harness", f"{label} timed out")


def state_at(root: Path, label: str) -> dict[str, Any]:
    try:
        value = store.read_record(root / "state.md")
    except (OSError, store.StorageError) as exc:
        fail("harness", f"{label} cannot read state: {exc}")
    need(isinstance(value, dict), f"{label} state is not an object")
    return value


def flag(argv: list[str], name: str) -> str:
    for index, value in enumerate(argv):
        if value.startswith(name + "="):
            return value[len(name) + 1 :]
        if value == name and index + 1 < len(argv):
            return argv[index + 1]
    fail("product", f"packet omitted {name}")


def packet(text: str, root: Path, action: str, label: str) -> dict[str, Any]:
    try:
        callback = text.split("Write the structured result to: ", 1)[1].splitlines()[0].strip()
        command = text.split("Call this when done:\n", 1)[1].splitlines()[0].strip()
        argv = shlex.split(command)
    except (IndexError, ValueError) as exc:
        fail("product", f"{label} malformed packet: {exc}")
    expected = root / "inbox" / f"{action}.md"
    need(len(argv) >= 2 and argv[0] == "python3" and canonical(argv[1]) == canonical(CLI), f"{label} did not return canonical CLI command")
    need(canonical(callback) == canonical(expected) == canonical(flag(argv, "--result")), f"{label} did not return generated callback path")
    need(canonical(flag(argv, "--run-dir")) == canonical(root) and flag(argv, "--action") == action, f"{label} callback did not bind current run/action")
    return {"action": action, "callback": Path(callback), "argv": argv}


def write_callback(info: Mapping[str, Any], payload: Mapping[str, Any], label: str) -> str:
    body = store.dumps(dict(payload), "Mechanical navigator callback: " + label)
    store.atomic_write_text(info["callback"], body)
    return body


def fresh(base: Path, name: str, end: float, *, padded: bool = False) -> tuple[Path, Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    repo, root = base / name / "ordinary-project", base / name / "run-state"
    repo.mkdir(parents=True)
    prompt = f"Mechanical CLI {name}; no project work is requested." + ("\n" + "x" * RACE_PROMPT_BYTES if padded else "")
    init = run(
        [
            sys.executable,
            str(CLI),
            "init",
            "--repo",
            str(repo),
            "--run-dir",
            str(root),
            "--prompt",
            prompt,
            "--execution-mode=navigator-v1",
        ],
        repo,
        end,
        name + " init",
    )
    need(init.returncode == 0, f"{name} init failed: {(init.stdout + init.stderr)[:500]}")
    state = state_at(root, name + " init")
    need(state["stage"] == "intake" and state["status"] == "active", f"{name} did not initialize intake")
    return repo, root, packet(init.stdout, root, state["action"]["id"], name + " init"), state, {"prompt_bytes": len(prompt.encode()), "init_stdout_bytes": len(init.stdout.encode())}


def cold(repo: Path, root: Path, action: str, end: float, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    outcome = run([sys.executable, str(CLI), "next", "--run-dir", str(root)], repo, end, label + " cold next")
    need(outcome.returncode == 0, f"{label} cold next failed: {(outcome.stdout + outcome.stderr)[:500]}")
    state = state_at(root, label + " cold")
    need(state["action"]["id"] == action and state["prompt"] in outcome.stdout and action in outcome.stdout, f"{label} cold packet lost context or action")
    return packet(outcome.stdout, root, action, label + " cold"), state


def empty_repo(repo: Path, label: str) -> list[str]:
    entries = sorted(path.name for path in repo.iterdir())
    need(not entries and not (repo / ".git").exists(), f"{label} created project entries: {entries}")
    return entries


def base_case(base: Path, end: float) -> dict[str, Any]:
    repo, root, original_packet, initial, info = fresh(base, "base-cold-replay", end)
    original = result("done", "Mechanical cold callback completion.", evidence_refs=["mechanical/base-cold"])
    body = write_callback(original_packet, original, "before cold next")
    cold_packet, _ = cold(repo, root, initial["action"]["id"], end, "base")
    need(canonical(cold_packet["callback"]) == canonical(original_packet["callback"]), "base cold packet changed callback")
    complete = run(original_packet["argv"], repo, end, "base original completion")
    accepted = state_at(root, "base accepted")
    need(complete.returncode == 0 and accepted["stage"] == "discovery" and len(accepted["history"]) == 1 and accepted["accepted"][original_packet["action"]] == original, "base original completion did not produce one transition")
    bytes_after = (root / "state.md").read_bytes()
    replay = run(original_packet["argv"], repo, end, "base replay")
    need(replay.returncode == 0 and (root / "state.md").read_bytes() == bytes_after and original_packet["callback"].read_text() == body, "base replay was not idempotent")
    recovered = state_at(root, "base recovered")
    cold(repo, root, recovered["action"]["id"], end, "base recovery")
    return {"status": "passed", "init": info, "original_completion_returncode": complete.returncode, "replay_returncode": replay.returncode, "accepted_transitions": len(accepted["history"]), "later_cold_stage": recovered["stage"], "temporary_repo_entries": empty_repo(repo, "base")}


def collect(process: subprocess.Popen[str], end: float, label: str) -> dict[str, Any]:
    try:
        stdout, stderr = process.communicate(timeout=deadline(end, label))
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        fail("harness", f"{label} timed out")
    return {"returncode": process.returncode, "stdout_bytes": len(stdout.encode()), "stderr": stderr.strip()[:500]}


def race(base: Path, kind: str, number: int, end: float) -> dict[str, Any]:
    label = f"{kind}-race-{number}"
    repo, root, original_packet, initial, info = fresh(base, label, end, padded=True)
    winner = result("done", f"Mechanical {kind} race winner {number}.", evidence_refs=[f"mechanical/{kind}/{number}/winner"])
    conflict = result("done", f"Mechanical {kind} race conflict {number}.", evidence_refs=[f"mechanical/{kind}/{number}/conflict"])
    write_callback(original_packet, winner, label + " before cold next")
    cold(repo, root, initial["action"]["id"], end, label)
    first = second = None
    try:
        first = subprocess.Popen(original_packet["argv"], cwd=repo, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            deadline(end, label + " waiting for winner")
            try:
                current = store.read_record(root / "state.md")
            except (OSError, store.StorageError):
                current = None
            if isinstance(current, dict) and len(current.get("history", [])) == 1:
                need(current["history"][0]["action"] == original_packet["action"] and current["accepted"].get(original_packet["action"]) == winner and first.poll() is None, f"{label} did not establish first-winner lock window")
                break
            need(first.poll() is None, f"{label} first contender exited without one transition")
            time.sleep(0.002)
        if kind == "conflict":
            write_callback(original_packet, conflict, label + " conflicting callback")
        second = subprocess.Popen(original_packet["argv"], cwd=repo, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        first_result, second_result = collect(first, end, label + " first"), collect(second, end, label + " second")
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
    after = state_at(root, label + " after")
    issues = []
    if first_result["returncode"] != 0 or len(after["history"]) != 1 or set(after["accepted"]) != {original_packet["action"]} or after["accepted"][original_packet["action"]] != winner:
        issues.append("winner did not leave exactly one original accepted transition")
    follow_up = None
    if kind == "duplicate":
        if second_result["returncode"] != 0:
            retry = run(original_packet["argv"], repo, end, label + " retry after winner")
            follow_up = {"returncode": retry.returncode, "stderr": retry.stderr.strip()[:500]}
            issues.append("duplicate contender returned nonzero" if retry.returncode == 0 else "duplicate contender and post-winner retry failed")
    else:
        if second_result["returncode"] != 2 or "conflicting result replay" not in second_result["stderr"]:
            issues.append("conflicting contender was not rejected")
        write_callback(original_packet, winner, label + " restore accepted callback")
        replay = run(original_packet["argv"], repo, end, label + " replay after conflict")
        follow_up = {"returncode": replay.returncode, "stderr": replay.stderr.strip()[:500]}
        if replay.returncode != 0:
            issues.append("accepted replay failed after conflict")
    recovered = state_at(root, label + " recovery")
    cold(repo, root, recovered["action"]["id"], end, label + " recovery")
    row = {"number": number, "kind": kind, "status": "passed" if not issues else "failed", "init": info, "lock_window_observed": True, "first_process": first_result, "second_process": second_result, "accepted_transitions": len(after["history"]), "later_cold_stage": recovered["stage"], "temporary_repo_entries": empty_repo(repo, label)}
    if follow_up:
        row["post_winner_replay_or_retry"] = follow_up
    if issues:
        row["issues"] = issues
    return row


def cli_cases(seed: int, race_count: int, end: float) -> dict[str, Any]:
    failures, races = [], []
    with tempfile.TemporaryDirectory(prefix="shiploop-navigator-mechanical-") as raw:
        base = Path(raw)
        try:
            base_result = base_case(base, end)
        except Exception as exc:
            base_result = {"status": "failed", "failure": str(exc)}
            failures.append({"case": "base-cold-replay", "failure": str(exc)})
        order = ["duplicate"] * race_count + ["conflict"] * race_count
        random.Random(seed ^ 0x5A17).shuffle(order)
        seen = Counter()
        for kind in order:
            seen[kind] += 1
            try:
                row = race(base, kind, seen[kind], end)
            except Exception as exc:
                row = {"number": seen[kind], "kind": kind, "status": "failed", "failure": str(exc)}
            races.append(row)
            if row["status"] != "passed":
                failures.append({"case": f"{kind}-race-{seen[kind]}", "failure": row.get("failure", "; ".join(row.get("issues", [])))})
    duplicate = [row for row in races if row["kind"] == "duplicate"]
    conflict = [row for row in races if row["kind"] == "conflict"]
    return {"status": "passed" if not failures else "failed", "race_seed": seed ^ 0x5A17, "race_order": order, "counts": {"duplicate_races_requested": race_count, "duplicate_races_passed": sum(row["status"] == "passed" for row in duplicate), "conflicting_races_requested": race_count, "conflicting_races_passed": sum(row["status"] == "passed" for row in conflict), "two_process_races_completed": len(races)}, "base_cold_next_original_completion_and_replay": base_result, "races": races, "failures": failures, "lock_note": "The CLI's blocking fcntl.flock lock is exercised with two real subprocesses. The first is held while printing its padded post-save packet; an unexpected duplicate contender error gets one serialized post-winner replay attempt and remains a failure."}


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write JSON here; stdout when omitted")
    parser.add_argument("--seed", type=int, default=20_260_914)
    parser.add_argument("--walks", type=int, default=100)
    parser.add_argument("--race-count", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)
    if not 1 <= args.walks <= 500 or not 1 <= args.race_count <= 20 or not 5 <= args.timeout_seconds <= 300:
        raise SystemExit("walks=1..500, race-count=1..20, timeout-seconds=5..300")
    if not CLI.is_file() or not NAVIGATOR.is_file() or not REFERENCE.is_file():
        raise SystemExit("current ShipLoop navigator sources were not found")
    started, end, oracle_error = time.monotonic(), time.monotonic() + args.timeout_seconds, None
    try:
        verify_oracle()
    except Exception as exc:
        oracle_error = str(exc)
    model = models(args.seed, args.walks, end) if oracle_error is None else {"status": "not-run", "failures": [{"walk": "oracle", "failure": oracle_error}]}
    cli = cli_cases(args.seed, args.race_count, end) if oracle_error is None else {"status": "not-run", "failures": []}
    failures = [*model.get("failures", []), *cli.get("failures", [])]
    report = {"schema": "shiploop-navigator-mechanical-experiment/v1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "scope": {"opt_in": True, "stdlib_only": True, "normal_shiploop_suite_run": False, "project_work_or_git_requested": False, "temporary_repositories_and_run_state": "system temporary directory outside source", "reliability_claim": "Deterministic mechanical samples are not a reliability rate, delivery proof, or production certification."}, "source": {"repo_root": str(ROOT), "navigator": str(NAVIGATOR), "navigator_sha256": hashlib.sha256(NAVIGATOR.read_bytes()).hexdigest(), "navigator_reference": str(REFERENCE), "navigator_reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(), "cli": str(CLI)}, "configuration": {"master_seed": args.seed, "walks_requested": args.walks, "race_count_each_requested": args.race_count, "timeout_seconds": args.timeout_seconds, "elapsed_seconds": round(time.monotonic() - started, 3), "reproduce_command": f"python3 test/experiments/shiploop_navigator/mechanical.py --output test/experiments/shiploop_navigator/results/mechanical.json --seed {args.seed} --walks {args.walks} --race-count {args.race_count} --timeout-seconds {args.timeout_seconds:g}"}, "frozen_oracle": {"validated_before_execution": oracle_error is None, "default_path": FLOW, "special_edges": {"document_without_skill": "verify", "document_with_skill": "skill-validate", "carry_forward_with_future_work": "step-plan", "carry_forward_after_final_work": "system-test"}, "expected_rejections": ["stale or forged action/result leaves input unchanged", "semantic replay is idempotent and changed replay is rejected", "terminal apply/control is rejected without mutation"]}, "experiments": {"generated_model_walks": model, "real_cli_processes": cli}, "failures": failures, "overall_status": "passed" if not failures and model["status"] == cli["status"] == "passed" else "failed", "limitations": ["Generated API walks do not prove every state combination.", "Two-process races do not establish distributed-lock behavior or crash durability.", "No project command, Git initialization, implementation action, test command, or deployment is requested."]}
    if args.output:
        write_json(args.output, report)
        print(f"wrote {args.output}: {report['overall_status']}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
