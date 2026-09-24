#!/usr/bin/env python3
"""Create two frozen, offline ShipLoop discovery acceptance fixtures."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file() and p.suffix not in (".pyc", ".cover") and "__pycache__" not in p.parts}


def receipt(stage: str) -> dict[str, object]:
    return {"summary": f"Synthetic traversal setup through {stage}; no Improve execution occurred.",
            "review_refs": [], "check_refs": [], "lessons": "Synthetic setup only; revalidate real work."}


def render_packet(package: Path, case: Path, workspace: Path, task: str) -> tuple[Path, str]:
    sys.path.insert(0, str(package / "scripts"))
    for name in tuple(sys.modules):
        if name.startswith("shiploop_"):
            sys.modules.pop(name)
    navigator = importlib.import_module("shiploop_navigator")
    store = importlib.import_module("shiploop_store")
    loaded = Path(navigator.__file__).resolve()
    if not loaded.is_relative_to(package.resolve()):
        raise RuntimeError(f"navigator escaped frozen package: {loaded}")
    state = navigator.new_state(str(workspace), task, improve_skill="")
    while navigator.current_stage(state) != "discovery":
        stage, action = navigator.current_stage(state), navigator.current_action(state)["id"]
        seed = {"outcome": "done", "summary": "Synthetic fixture traversal; no project work claimed.", "evidence_refs": []}
        state = navigator.apply(state, action, seed)
        if state["active_improve"] is not None:  # Only planning checkpoints and the last carry-forward park an Improve child.
            state = navigator.finish_improve(state, action, receipt(stage))
    run = case / "run"
    run.mkdir()
    navigator.save(run, state)
    packet = case / "participant" / "PACKET.md"
    put(packet, navigator.render(type("FrozenPacket", (), {"PACKAGE_ROOT": package})(), run, store.read_record(run / "state.md")))
    return packet, str(loaded)


def common(workspace: Path, task: str, multi: bool) -> None:
    put(workspace / "README.md", f"# Discovery fixture\n\n{task}\n\nRun `python3 -B -m unittest discover -v` before work. It is a narrow existing fixture check. All remote observations are synthetic.\n")
    put(workspace / "SHIPLOOP.md", "# Project knowledge\n\nRead current source and docs/environment.md, then retain the discovery decision and exact evidence locators in this index.\n")
    if not multi:
        put(workspace / "src/app.py", "def normalize_name(value):\n    return value.strip()\n")
        put(workspace / "test_fixture.py", '''import unittest
from src.app import normalize_name

class Baseline(unittest.TestCase):
    def test_edges(self):
        self.assertEqual(normalize_name("  Ada  "), "Ada")
''')
        put(workspace / "docs/environment.md", "# Existing environment\n\nLocal pure Python string helper; no remote services, state or deployment configuration.\n")
        return
    put(workspace / "src/app.py", 'CRM_RUNTIME_ALIAS = "crm-review-service"\nDOCUMENT_RUNTIME_ALIAS = "document-worker"\n')
    put(workspace / "test_fixture.py", "import unittest\nfrom src.app import CRM_RUNTIME_ALIAS\n\nclass Baseline(unittest.TestCase):\n    def test_binding_name(self):\n        self.assertEqual(CRM_RUNTIME_ALIAS, \"crm-review-service\")\n")
    put(workspace / "docs/environment.md", "# Historical environment note\n\nEarlier synthetic inventory used tenant-blue. Both runtime writers were reported enabled. CRM owns review data and a separately executing script produces documents. Revalidate these dated observations before design.\n")


def launch(case: Path, workspace: Path, packet: Path, task: str, multi: bool) -> None:
    route = "There is no remote fixture or remote configuration for this local case.\n" if not multi else f"Use the documented synthetic CLI beginning with `python3 -B {case / 'participant/probe.py'} --help`; do not read its implementation.\n"
    put(case / "participant" / "LAUNCH.md", f"""# Bounded discovery

Work only in {workspace}. {task}

Read README.md, SHIPLOOP.md, relevant source/docs, and the actually rendered discovery packet at {packet}. Follow the packet's current discovery guidance. Run the baseline before proposing a product edit and retain its command/output in BASELINE.txt. {route}Write DISCOVERY.md (at most 900 words) and update SHIPLOOP.md.

Only DISCOVERY.md, BASELINE.txt and SHIPLOOP.md may be changed in the workspace; the probe may append receipts. Stop after 8 elapsed minutes or 24 host actions with an honest partial result. No implementation, source/note deletion, callbacks, Improve, network, credentials, provisioning, installs, commits or deployment. Prior packet transitions and Improve receipts are synthetic fixture setup, not completed work. Do not inspect other cases or the coordinator protocol.
""")


def prepare(source: Path, output: Path) -> Path:
    if not source.is_absolute() or not output.is_absolute():
        raise ValueError("--source and --output must be absolute")
    source, output = source.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(source.parents[1]):
        raise ValueError("--output must be new and outside the source checkout")
    if not (source / "scripts/shiploop_navigator.py").is_file():
        raise ValueError("--source must be a ShipLoop package")
    output.mkdir(parents=True)
    package = output / "source-snapshot/skills/shiploop"
    shutil.copytree(source, package, ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "*.cover"))
    task = {"local": "Discover the change needed to normalize names by trimming edges and collapsing repeated internal whitespace; do not implement it.", "multi": "Discover the design and prerequisites for CRM review to generate remote documents independently of the developer workstation; do not implement it."}
    cases, loaded = {}, ""
    for name in ("local", "multi"):
        case, workspace = output / "cases" / name, output / "cases" / name / "workspace"
        common(workspace, task[name], name == "multi")
        (case / "participant").mkdir(parents=True)
        if name == "multi":
            shutil.copy2(HERE / "probe.py", case / "participant/probe.py")
        packet, loaded = render_packet(package, case, workspace, task[name])
        launch(case, workspace, packet, task[name], name == "multi")
        cases[name] = {"workspace": str(workspace), "packet": str(packet), "launch": str(case / "participant/LAUNCH.md"), "input_hashes": hashes(workspace), "packet_sha256": digest(packet)}
    manifest = {"schema": "shiploop-discovery-acceptance-v1", "source": str(source), "source_hashes": hashes(source), "snapshot_hashes": hashes(package), "loaded_navigator": loaded, "apparatus_hashes": {p.name: digest(p) for p in (HERE / "prepare.py", HERE / "probe.py")}, "protocol_hash": digest(HERE.parent / "SEMANTIC-PROTOCOL.md"), "cases": cases, "limits": "Offline synthetic fixtures only; no model, agent, callback, Improve execution, remote access, installation, or product edit occurred."}
    put(output / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    print(prepare(**vars(parser.parse_args())))
