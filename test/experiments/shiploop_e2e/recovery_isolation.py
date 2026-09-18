"""Audit a new request's isolation from prior runs without driving ShipLoop."""
from __future__ import annotations

from pathlib import Path


def _states(navigation: dict) -> dict[str, dict]:
    return {row["state"]["run_id"]: row for row in navigation.get("states", [])
            if isinstance(row.get("state"), dict) and isinstance(row["state"].get("run_id"), str)}


def assess_isolation(initial: dict, final: dict, events: dict, *, prompt: str, mode: str = "fresh-request") -> dict:
    """Initial/final inputs are inspect_run_artifacts results, events adapter output.

    An explicit recovery experiment is a different scope. Successful `next` on
    an initial run is evidence of crossed request boundaries for a fresh request;
    merely reading the old Markdown is permitted and is not such evidence.
    """
    if mode not in {"fresh-request", "explicit-recovery"}:
        raise ValueError("unknown isolation experiment mode")
    if mode == "explicit-recovery":
        return {"status": "not-applicable", "mode": mode, "note": "A recovery invocation is not a fresh one-shot request."}
    old, current = _states(initial), _states(final)
    old_dirs = {str(Path(row["source_path"]).parent.resolve()): key for key, row in old.items() if row.get("source_path")}
    recovered, completed = [], []
    for call in events.get("cli_calls", []):
        # Unknown exit status is insufficient for a supported violation.
        codes = call.get("exit_codes", [])
        if call.get("failed") or not call.get("completed") or not codes or any(code != 0 for code in codes):
            continue
        argv = call.get("argv_tail", [])
        flags = {}
        for index, token in enumerate(argv):
            if isinstance(token, str) and token.startswith("--"):
                name, equal, value = token.partition("=")
                if not equal and index + 1 < len(argv):
                    value = argv[index + 1]
                flags[name] = value
        directory = flags.get("--run-dir")
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            continue
        key = old_dirs.get(str(Path(directory).resolve()))
        if key and argv[:1] == ["next"]:
            recovered.append({"run_id": key, "call_id": call.get("call_id"), "run_dir": directory})
        if key and argv[:1] in (["complete"], ["done"], ["improve-complete"]):
            completed.append({"run_id": key, "call_id": call.get("call_id"), "action": flags.get("--action")})
    changed = sorted(key for key in old.keys() & current.keys() if old[key]["state"] != current[key]["state"])
    accepted_prompts = {prompt, prompt.removeprefix("/shiploop ")}
    fresh = sorted(key for key, row in current.items() if key not in old and row["state"].get("prompt") in accepted_prompts)
    # A changed snapshot alone cannot attribute the write to this Grok process:
    # sibling artifact roots can contain a separately running experiment.
    status = "fail" if recovered or completed else "pass" if len(fresh) == 1 and not changed else "unverified"
    return {"schema": "shiploop-e2e-recovery-isolation/1", "status": status, "mode": mode,
            "prior_run_count": len(old), "fresh_matching_runs": fresh, "prior_runs_recovered": recovered,
            "prior_run_callbacks": completed, "prior_state_changed": changed,
            "note": "Fresh identity evidence only; product behavior and complete lifecycle remain separate. Concurrent unrelated writers require analyst attribution."}
