#!/usr/bin/env python3
"""Render a test-only cold plan packet; the index is the reader's entry point."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source, case, output):
    source, case, output = source.resolve(), case.resolve(), output.resolve()
    workspace = case / "workspace"
    if not (workspace / "SHIPLOOP.md").is_file():
        raise ValueError("completed discovery project index required")
    if (workspace / "PLAN.md").exists():
        raise ValueError("refusing to overwrite a previous cold plan")
    if output.exists() or output.is_relative_to(source) or output.is_relative_to(case):
        raise ValueError("output must be new and outside source and case")
    if any(name.startswith("shiploop_") for name in sys.modules):
        raise ValueError("use a fresh Python process for source binding")
    sys.path.insert(0, str(source / "scripts"))
    navigator = importlib.import_module("shiploop_navigator")
    store = importlib.import_module("shiploop_store")
    loaded = Path(navigator.__file__).resolve()
    if not loaded.is_relative_to(source):
        raise ValueError("Navigator import escaped selected frozen source")
    state = navigator.new_state(
        str(workspace), "Outline a conditional delivery plan from retained discovery findings.",
        protocol_version=3, improve_skill="",
    )
    while navigator.current_stage(state) != "plan":
        action = navigator.current_action(state)["id"]
        seed = {"outcome": "done", "summary": "Synthetic traversal only; no project work or review claimed.", "evidence_refs": []}
        state = navigator.apply(state, action, seed)
        if state["active_improve"] is not None:  # Only planning checkpoints and the last carry-forward park an Improve child.
            state = navigator.finish_improve(state, action, {
                "summary": "Synthetic setup, not actual Improve.", "lessons": "Revalidate real prerequisites.",
            })
    run, participant = output / "run", output / "participant"
    run.mkdir(parents=True)
    participant.mkdir()
    navigator.save(run, state)
    packet = participant / "PACKET.md"
    packet.write_text(navigator.render(
        type("FrozenPacket", (), {"PACKAGE_ROOT": source})(), run,
        store.read_record(run / "state.md")), encoding="utf-8")
    (participant / "LAUNCH.md").write_text(f"""# Cold planning sample

Work in {workspace}. Read the rendered plan packet {packet}, then SHIPLOOP.md.
Follow its links to discover the retained decisions and evidence. No other note
or receipt locator is supplied: report a missing handoff without coordinator rescue.
Write only PLAN.md, at most 600 words within five elapsed minutes, with ordered
work, facts versus proposals, prerequisites, evidence locators and revalidation.
Identify which work is eligible and which consumers need missing evidence.
The packet's predecessor transitions are synthetic; do not infer accepted scope,
specification, tests or Improve reviews from them. No earlier conversation is
available. No tests, probes, callbacks, agents, network, implementation or writes
other than PLAN.md. Stop after the conditional outline; do not claim acceptance.
""", encoding="utf-8")
    manifest = {"loaded_navigator": str(loaded), "apparatus_sha256": digest(Path(__file__)),
                "source_hashes": {str(p.relative_to(source)): digest(p) for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts},
                "case_hashes": {str(p.relative_to(case)): digest(p) for p in case.rglob("*") if p.is_file() and "__pycache__" not in p.parts}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return participant / "LAUNCH.md"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    print(prepare(**vars(parser.parse_args())))
