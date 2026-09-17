"""Bounded state/rendering experiment for a read-only ShipLoop progress view.

Run from this evidence directory with the committed ShipLoop checkout available
through ``SHIPLOOP_PROGRESS_REPO`` or the default experiment worktree.  The
only writes are synthetic fixture and result files below this directory.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from prototype import (
    MAX_SNAPSHOT_CHARS,
    SCRIPTS,
    _progress_lines,
    navigator,
)

import shiploop_store as store


EVIDENCE_ROOT = Path(__file__).resolve().parent
OUTPUT = Path(os.environ.get("SHIPLOOP_PROGRESS_OUTPUT", str(EVIDENCE_ROOT / "experiment1")))
REPORTING_CUE = EVIDENCE_ROOT / "reporting-cue.txt"
GOAL = "Improve parser validation and CLI documentation."
PLAN_QUEUE_TITLES = (
    ("W1", "Review parser validation coverage"),
    ("W2", "Clarify CLI error documentation"),
)
REVISED_QUEUE_TITLES = (
    ("W1", "Validate parser input errors"),
    ("W2", "Document CLI error messages"),
)


def _check(condition: bool, message: str, checks: list[str]) -> None:
    """Record an independent expectation or stop the experiment clearly."""
    if not condition:
        raise AssertionError(message)
    checks.append(message)


def _result(stage: str, outcome: str = "done", **extra: Any) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "summary": f"Synthetic {stage} {outcome} record.",
        "evidence_refs": [],
        **extra,
    }


def _advance(
    state: dict[str, Any], expected_stage: str, *, outcome: str = "done", **extra: Any
) -> dict[str, Any]:
    """Advance only the current public navigator action and prove input purity."""
    assert navigator.current_stage(state) == expected_stage
    action = navigator.current_action(state)
    before = deepcopy(state)
    updated = navigator.apply(state, action["id"], _result(expected_stage, outcome, **extra))
    assert state == before
    navigator.validate(updated)
    return updated


def _control(state: dict[str, Any], command: str, reason: str) -> dict[str, Any]:
    """Apply a public control transition without mutating the source state."""
    before = deepcopy(state)
    updated = navigator.control(state, command, reason)
    assert state == before
    navigator.validate(updated)
    return updated


def _new_state(protocol_version: int, fixture_repo: Path) -> dict[str, Any]:
    return navigator.new_state(
        str(fixture_repo), GOAL, "", protocol_version=protocol_version
    )


def _items(fixture_repo: Path, titles: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [
        {
            "id": item_id,
            "title": title,
            "context": "Fixture source: "
            + str(fixture_repo / "sources" / f"{item_id.lower()}-context.md"),
        }
        for item_id, title in titles
    ]


def _to_plan(state: dict[str, Any]) -> dict[str, Any]:
    for stage in navigator.PRELUDE[: navigator.PRELUDE.index("plan")]:
        state = _advance(state, stage)
    assert navigator.current_stage(state) == "plan"
    return state


def _start_inner(
    state: dict[str, Any], work_items: list[dict[str, str]]
) -> dict[str, Any]:
    state = _to_plan(state)
    state = _advance(state, "plan", work_items=work_items)
    assert navigator.current_stage(state) == "plan-improve"
    state = _advance(state, "plan-improve")
    assert navigator.current_stage(state) == "step-plan"
    return state


def _to_document(state: dict[str, Any]) -> dict[str, Any]:
    for stage in navigator.INNER[: navigator.INNER.index("document")]:
        state = _advance(state, stage)
    assert navigator.current_stage(state) == "document"
    return state


def _complete_current_item(
    state: dict[str, Any], *, skill_required: bool
) -> dict[str, Any]:
    state = _to_document(state)
    state = _advance(
        state, "document", choices={"skill_required": skill_required}
    )
    if skill_required:
        assert navigator.current_stage(state) == "skill-validate"
        state = _advance(state, "skill-validate")
    assert navigator.current_stage(state) == "verify"
    for stage in ("verify", "product-improve", "integrate", "carry-forward"):
        state = _advance(state, stage)
    return state


def _w2_verify(protocol_version: int, fixture_repo: Path) -> dict[str, Any]:
    state = _start_inner(
        _new_state(protocol_version, fixture_repo), _items(fixture_repo, PLAN_QUEUE_TITLES)
    )
    state = _complete_current_item(state, skill_required=False)
    assert navigator.current_stage(state) == "step-plan"
    state = _to_document(state)
    state = _advance(state, "document", choices={"skill_required": False})
    assert navigator.current_stage(state) == "verify"
    return state


def _repeated_improve(
    protocol_version: int, fixture_repo: Path, *, repeats: int
) -> dict[str, Any]:
    state = _new_state(protocol_version, fixture_repo)
    for stage in ("intake", "discovery", "research"):
        state = _advance(state, stage)
    for _ in range(repeats):
        state = _advance(state, "research-improve", outcome="repeat")
    assert navigator.current_stage(state) == "research-improve"
    return state


def _document_branches(
    protocol_version: int, fixture_repo: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    pending = _to_document(
        _start_inner(
            _new_state(protocol_version, fixture_repo),
            _items(fixture_repo, PLAN_QUEUE_TITLES),
        )
    )
    selected = _advance(
        pending, "document", choices={"skill_required": True}
    )
    skipped = _advance(
        pending, "document", choices={"skill_required": False}
    )
    assert navigator.current_stage(selected) == "skill-validate"
    assert navigator.current_stage(skipped) == "verify"
    return pending, selected, skipped


def _queue_replacement(
    protocol_version: int, fixture_repo: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _to_plan(_new_state(protocol_version, fixture_repo))
    state = _advance(
        state, "plan", work_items=_items(fixture_repo, PLAN_QUEUE_TITLES)
    )
    assert navigator.current_stage(state) == "plan-improve"
    revised = _advance(
        state,
        "plan-improve",
        work_items=_items(fixture_repo, REVISED_QUEUE_TITLES),
    )
    assert navigator.current_stage(revised) == "step-plan"
    return state, revised


def _done_state(protocol_version: int, fixture_repo: Path) -> dict[str, Any]:
    state = _start_inner(
        _new_state(protocol_version, fixture_repo), _items(fixture_repo, PLAN_QUEUE_TITLES)
    )
    state = _complete_current_item(state, skill_required=False)
    state = _complete_current_item(state, skill_required=True)
    assert navigator.current_stage(state) == "system-test"
    for stage in navigator.OUTER:
        state = _advance(state, stage)
    assert (navigator.current_stage(state), state["status"]) == ("done", "done")
    return state


def _long_queue_state(protocol_version: int, fixture_repo: Path) -> dict[str, Any]:
    long_title = "Long parser validation title " + ("x" * 300)
    rows = [
        {
            "id": f"Q{index:04d}",
            "title": long_title + f" {index}",
            "context": "Fixture source: "
            + str(fixture_repo / "sources" / "long-queue-context.md"),
        }
        for index in range(1000)
    ]
    state = _to_plan(_new_state(protocol_version, fixture_repo))
    return _advance(state, "plan", work_items=rows)


def _build_matrix(protocol_version: int, fixture_repo: Path) -> dict[str, dict[str, Any]]:
    repeated = _repeated_improve(protocol_version, fixture_repo, repeats=2)
    blocked = _advance(repeated, "research-improve", outcome="blocked")
    resumed = _control(blocked, "resume", "")
    w2_verify = _w2_verify(protocol_version, fixture_repo)
    document_pending, document_selected, document_skipped = _document_branches(
        protocol_version, fixture_repo
    )
    plan_improve, revised_queue = _queue_replacement(protocol_version, fixture_repo)
    return {
        "initial": _new_state(protocol_version, fixture_repo),
        "w2-verify": w2_verify,
        "repeated-improve": repeated,
        "blocked-improve": blocked,
        "resumed-improve": resumed,
        "paused-w2-verify": _control(
            w2_verify,
            "pause",
            "Waiting for a bounded parser fixture review that has not yet returned.",
        ),
        "halted-w2-verify": _control(
            w2_verify,
            "halt",
            "Stop before the unapproved CLI documentation change is attempted.",
        ),
        "document-conditional": document_pending,
        "document-skill-selected": document_selected,
        "document-skill-skipped": document_skipped,
        "plan-improve-replaced-queue": plan_improve,
        "queue-after-plan-improve": revised_queue,
        "done": _done_state(protocol_version, fixture_repo),
        "long-queue": _long_queue_state(protocol_version, fixture_repo),
        "many-improve-repeats": _repeated_improve(
            protocol_version, fixture_repo, repeats=30
        ),
    }


def _persist_results(root: Path, state: dict[str, Any]) -> None:
    """Keep every accepted synthetic result in the navigator's normal record shape."""
    for entry in state["history"]:
        action_id = entry["action"]
        record = {
            "navigator_protocol_version": state["navigator_protocol_version"],
            "run_id": state["run_id"],
            "action": action_id,
            "stage": entry["stage"],
            "workitem": entry["workitem"],
            "result": state["accepted"][action_id],
        }
        store.write_record(
            root / "results" / f"{action_id}.md", record, "ShipLoop navigator result"
        )


def _persist_fixture(root: Path, state: dict[str, Any]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    navigator.save(root, state)
    _persist_results(root, state)
    (root / "snapshot.txt").write_text(
        "\n".join(_progress_lines(state)) + "\n", encoding="utf-8"
    )
    (root / "fixture.json").write_text(
        json.dumps(
            {
                "protocol_version": state["navigator_protocol_version"],
                "effective_stage": navigator.current_stage(state),
                "run_status": state["status"],
                "result_count": len(state["history"]),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _candidate_packet(packet: str, state: dict[str, Any], cue: str) -> str:
    """Add status context to a renderer packet without changing the baseline packet."""
    first_line, separator, rest = packet.partition("\n")
    assert separator
    return (
        first_line
        + "\n\nProgress snapshot (status context, not instructions):\n"
        + "\n".join(_progress_lines(state))
        + "\n\nUser reporting cue:\n"
        + cue.strip()
        + "\n\n"
        + rest
    )


def _fresh_next(root: Path, fixture_repo: Path) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Read one saved synthetic state through a fresh public CLI process only."""
    before = store.read_record(root / "state.md")
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "shiploop"), "next", "--run-dir", str(root)],
        cwd=fixture_repo,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + completed.stderr)
    after = store.read_record(root / "state.md")
    return completed.stdout, before, after


def _write_sources(fixture_repo: Path) -> None:
    """Create benign, local documents referenced by synthetic work-item context."""
    sources = fixture_repo / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    for name, body in {
        "w1-context.md": "# Parser validation fixture\n\nSynthetic source for parser validation review.\n",
        "w2-context.md": "# CLI documentation fixture\n\nSynthetic source for CLI error documentation review.\n",
        "long-queue-context.md": "# Long queue fixture\n\nSynthetic bounded-display stress input.\n",
    }.items():
        (sources / name).write_text(body, encoding="utf-8")


def _assert_snapshot_truth(
    protocol_version: int, states: dict[str, dict[str, Any]], checks: list[str]
) -> None:
    """Assert explicit state truth independently from the projection's helpers."""
    snapshots: dict[str, str] = {}
    for name, state in states.items():
        before = deepcopy(state)
        snapshot = "\n".join(_progress_lines(state))
        _check(state == before, f"v{protocol_version} {name}: projection left state unchanged", checks)
        _check(len(snapshot) <= MAX_SNAPSHOT_CHARS, f"v{protocol_version} {name}: snapshot is bounded", checks)
        _check("ETA" not in snapshot and "%" not in snapshot, f"v{protocol_version} {name}: no ETA or percentage", checks)
        _check("in progress" not in snapshot.lower(), f"v{protocol_version} {name}: no execution claim", checks)
        _check("Fixture source:" not in snapshot and "sources/" not in snapshot, f"v{protocol_version} {name}: no raw context or reference", checks)
        snapshots[name] = snapshot

    initial = snapshots["initial"]
    _check("Phase: preparation | Run status: active" in initial, f"v{protocol_version} initial: phase and status", checks)
    _check("Preparation stages: 0/9 accepted done." in initial, f"v{protocol_version} initial: no completed preparation stages", checks)
    _check("Work items: completed 0; current 0; queued 1 (provisional" in initial, f"v{protocol_version} initial: queue stays provisional", checks)

    w2_verify = snapshots["w2-verify"]
    _check("Phase: inner | Run status: active" in w2_verify, f"v{protocol_version} W2: effective inner phase", checks)
    _check("Current: verify (assigned; execution unproven)." in w2_verify, f"v{protocol_version} W2: current verify assignment", checks)
    _check("Owner: W2 (current work-item assignment)." in w2_verify, f"v{protocol_version} W2: owner", checks)
    _check("Continuation: only the current action packet is available; execution remains unproven." in w2_verify, f"v{protocol_version} W2: no predicted successor", checks)
    _check("Work items: completed 1; current 1; queued 0" in w2_verify, f"v{protocol_version} W2: work counts", checks)
    _check("Current work item: W2: Clarify CLI error documentation" in w2_verify, f"v{protocol_version} W2: current owner", checks)
    _check("Skill validation: skipped because this owner's document result selected false." in w2_verify, f"v{protocol_version} W2: explicit skipped skill", checks)

    repeated = snapshots["repeated-improve"]
    _check("Preparation stages: 3/9 accepted done." in repeated, f"v{protocol_version} repeated Improve: repeat is not completion", checks)
    _check("Current: research-improve (assigned; execution unproven)." in repeated, f"v{protocol_version} repeated Improve: current stage", checks)
    _check("Improve detail: one host-owned campaign; internal phase and iterations are unavailable." in repeated, f"v{protocol_version} repeated Improve: no child counter", checks)
    _check("repeat" not in repeated.lower(), f"v{protocol_version} repeated Improve: no repeat count", checks)
    _check(snapshots["many-improve-repeats"] == repeated, f"v{protocol_version} repeated Improve: output does not grow with history", checks)

    blocked = snapshots["blocked-improve"]
    _check("Run status: blocked (unfinished:" in blocked, f"v{protocol_version} blocked: unfinished status", checks)
    _check("Current: research-improve (assigned; awaits resume; execution unproven)." in blocked, f"v{protocol_version} blocked: assignment awaits resume", checks)
    _check("Continuation: no action is runnable until the recorded condition is resolved and the run is resumed." in blocked, f"v{protocol_version} blocked: nonrunnable condition", checks)
    _check("Preparation stages: 3/9 accepted done." in blocked, f"v{protocol_version} blocked: blocked result is not completion", checks)
    resumed = snapshots["resumed-improve"]
    _check("Run status: active" in resumed and "unfinished:" not in resumed, f"v{protocol_version} resumed: status cleared", checks)

    paused = snapshots["paused-w2-verify"]
    _check("Run status: paused (unfinished:" in paused, f"v{protocol_version} paused: unfinished status", checks)
    _check("Current: verify (assigned; awaits resume; execution unproven)." in paused, f"v{protocol_version} paused: assignment awaits resume", checks)
    halted = snapshots["halted-w2-verify"]
    _check("Run status: halted (unfinished:" in halted, f"v{protocol_version} halted: stays unfinished", checks)
    _check("Current: none (halted; no runnable current or next action)." in halted, f"v{protocol_version} halted: no runnable action", checks)
    _check("Continuation: no current or next action is runnable." in halted, f"v{protocol_version} halted: no successor claim", checks)

    conditional = snapshots["document-conditional"]
    _check("Skill validation: conditional until this owner's document result is accepted done." in conditional, f"v{protocol_version} document: unresolved branch is conditional", checks)
    selected = snapshots["document-skill-selected"]
    _check("Skill validation: current because this owner's document result selected true." in selected, f"v{protocol_version} document: true branch is current", checks)
    _check("Current owner stages pending: skill-validate" not in selected, f"v{protocol_version} document: assigned stage is not pending", checks)
    skipped = snapshots["document-skill-skipped"]
    _check("Skill validation: skipped because this owner's document result selected false." in skipped, f"v{protocol_version} document: false branch is skipped", checks)

    plan_improve = snapshots["plan-improve-replaced-queue"]
    _check("Current: plan-improve (assigned; execution unproven)." in plan_improve, f"v{protocol_version} plan Improve: current stage", checks)
    _check("Review parser validation coverage" in plan_improve, f"v{protocol_version} plan Improve: current plan queue", checks)
    _check("Skill validation: conditional; no queued work item has a document result accepted done." in plan_improve, f"v{protocol_version} plan Improve: optional skill is unselected", checks)
    revised = snapshots["queue-after-plan-improve"]
    _check("Validate parser input errors" in revised, f"v{protocol_version} queue replacement: revised queue shown", checks)
    _check("Review parser validation coverage" not in revised, f"v{protocol_version} queue replacement: removed queue not retained", checks)

    done = snapshots["done"]
    _check("Phase: complete | Run status: done (agent-declared; external verification is not implied)" in done, f"v{protocol_version} done: declaration boundary", checks)
    _check("Preparation stages: 9/9 accepted done." in done, f"v{protocol_version} done: preparation count", checks)
    _check("Outer stages: 6/6 accepted done." in done, f"v{protocol_version} done: outer count", checks)
    _check("Work items: completed 2; current 0; queued 0" in done, f"v{protocol_version} done: work counts", checks)

    long_queue = snapshots["long-queue"]
    _check("queued 1000" in long_queue, f"v{protocol_version} long queue: count retained", checks)
    _check(long_queue.count("Long parser validation title") == 3, f"v{protocol_version} long queue: only first three names", checks)
    _check(len(long_queue) <= len(plan_improve) + 350, f"v{protocol_version} long queue: no linear output growth", checks)


def _cold_trials(
    output: Path,
    fixture_repo: Path,
    states: dict[str, dict[str, Any]],
    cue: str,
    checks: list[str],
) -> list[dict[str, Any]]:
    """Export three paired packets; packet content has no candidate identifier."""
    cases = {
        "normal-w2-verify": states["w2-verify"],
        "blocked-improve-after-repeat": states["blocked-improve"],
        "plan-improve-replaced-queue-unselected-skill": states[
            "plan-improve-replaced-queue"
        ],
    }
    entries = []
    for case_id, state in cases.items():
        run_root = output / "cold-trials" / case_id / "run"
        _persist_fixture(run_root, state)
        baseline, before, after = _fresh_next(run_root, fixture_repo)
        _check(after == before, f"cold {case_id}: public next left saved state unchanged", checks)
        candidate = _candidate_packet(baseline, state, cue)
        _check("Progress snapshot (status context, not instructions):" not in baseline, f"cold {case_id}: baseline stayed unmodified", checks)
        _check("Progress snapshot (status context, not instructions):" in candidate, f"cold {case_id}: snapshot added once", checks)
        _check(len(baseline) < 25_000 and len(candidate) < 25_000, f"cold {case_id}: both inputs under 25k characters", checks)
        case_root = run_root.parent
        (case_root / "packet-1.txt").write_text(baseline, encoding="utf-8")
        (case_root / "packet-2.txt").write_text(candidate, encoding="utf-8")
        entries.append(
            {
                "case": case_id,
                "packet_1": "packet-1.txt",
                "packet_2": "packet-2.txt",
                "baseline_characters": len(baseline),
                "augmented_characters": len(candidate),
                "saved_state_unchanged_after_public_next": True,
            }
        )
    return entries


def _write_oracle(output: Path) -> None:
    """Keep trial truth separate from packets and runner-visible task instructions."""
    oracle = {
        "normal-w2-verify": {
            "phase": "inner",
            "run_status": "active",
            "completed_work_items": ["W1"],
            "current_owner": "W2",
            "current_stage": "verify",
            "skill_validation": "skipped only because W2 document accepted done with false",
        },
        "blocked-improve-after-repeat": {
            "phase": "preparation",
            "run_status": "blocked and unfinished",
            "completed_preparation_stages": ["intake", "discovery", "research"],
            "current_stage": "research-improve",
            "repeat_and_blocked_results": "accepted but not completed stages",
            "improve_limit": "one host-owned campaign; no stored internal phase or iteration count",
        },
        "plan-improve-replaced-queue-unselected-skill": {
            "phase": "preparation",
            "run_status": "active",
            "current_stage": "plan-improve",
            "queue": "current plan queue is provisional until plan-improve accepted done",
            "optional_skill": "conditional; no document result accepted done",
        },
        "limitations": [
            "Accepted done is a navigator declaration, not proof of tests, deployment, or consumer behavior.",
            "The snapshot does not establish that an LLM reads, follows, or reports any packet correctly.",
            "The state does not expose Improve subiterations, elapsed time, percentage, ETA, or real execution start.",
            "Future labels describe current recorded status and are not instructions or extra graph actions.",
        ],
    }
    (output / "truth-oracle.json").write_text(
        json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_readme(output: Path) -> None:
    (output / "README.md").write_text(
        """# ShipLoop progress experiment 1\n\nThis is a synthetic, read-only state experiment against committed ShipLoop `ddca30d`. `fixtures/` retains valid navigator Markdown state plus each accepted synthetic result. `cold-trials/` contains three fresh public `next` packets and a paired packet with a derived snapshot and reporting cue.\n\nGive a fresh report-only runner one packet at a time. Do not provide `trial-manifest.json` or `truth-oracle.json` to that runner, do not run a callback, and do not perform repository, network, Git, or implementation work. The two packet files use neutral names; their mapping is retained only for the coordinator.\n\n`truth-oracle.json` is for independent judging after responses are collected. It records mechanical state facts and limitations; it is not evidence that a model follows a packet or that a real delivery occurred.\n""",
        encoding="utf-8",
    )


def main() -> int:
    if not REPORTING_CUE.is_file():
        raise RuntimeError(f"missing root-owned reporting cue: {REPORTING_CUE}")
    cue = REPORTING_CUE.read_text(encoding="utf-8").strip()
    if not cue:
        raise RuntimeError("root-owned reporting cue is empty")
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to replace frozen experiment evidence: {OUTPUT}")
    OUTPUT.mkdir()
    fixture_repo = OUTPUT / "synthetic-repository"
    _write_sources(fixture_repo)
    checks: list[str] = []
    matrices: dict[int, dict[str, dict[str, Any]]] = {}
    for protocol_version in (1, navigator.PROTOCOL_VERSION):
        states = _build_matrix(protocol_version, fixture_repo)
        matrices[protocol_version] = states
        _assert_snapshot_truth(protocol_version, states, checks)
        for name, state in states.items():
            _persist_fixture(OUTPUT / "fixtures" / f"v{protocol_version}" / name, state)

    trials = _cold_trials(
        OUTPUT, fixture_repo, matrices[navigator.PROTOCOL_VERSION], cue, checks
    )
    _write_oracle(OUTPUT)
    _write_readme(OUTPUT)
    results = {
        "base_commit": "ddca30d",
        "prototype": str(EVIDENCE_ROOT / "prototype.py"),
        "protocols": [1, navigator.PROTOCOL_VERSION],
        "fixture_scenarios": sorted(matrices[navigator.PROTOCOL_VERSION]),
        "checks_passed": len(checks),
        "checks": checks,
        "cold_trials": trials,
        "limitations": [
            "This is a pure prototype and did not modify ShipLoop production code, state schema, callbacks, routes, or prompts.",
            "Fresh public CLI reads used only `next` on synthetic run directories and left saved state unchanged.",
            "No test compares whole packet bytes or claims LLM behavior.",
        ],
        "smallest_implementation_lessons": [
            "A bounded projection can use the existing effective cursor, accepted done outcomes, queue, and work index without persistent progress state.",
            "Skill validation needs an explicit conditional/skipped/pending label tied to the current owner's done document result.",
            "Improve remains one stage-level host-owned campaign because no internal iteration state exists to report.",
        ],
    }
    (OUTPUT / "experiment1-results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "trial-manifest.json").write_text(
        json.dumps({"coordinator_mapping": trials}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"checks_passed": len(checks), "output": str(OUTPUT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
