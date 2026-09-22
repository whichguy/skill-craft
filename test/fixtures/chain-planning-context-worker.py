#!/usr/bin/env python3
"""Deterministic worker proving a ShipLoop packet's planning material is usable.

It deliberately derives source names and contents only from a hashed shared
planning reference.  This is a fixture, not a model or native-host substitute.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_reference(value: object, label: str) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise SystemExit(label + " must be a {path,sha256} reference")
    path = Path(value["path"])
    if not path.is_absolute() or not path.is_file():
        raise SystemExit(label + " is unavailable")
    if sha256(path) != value["sha256"]:
        raise SystemExit(label + " hash changed")
    return path


assignment = json.loads(sys.stdin.readline())
packet = assignment["packet"]
workspace = Path(assignment["workspace"])
os.chdir(workspace)

manifest_path = checked_reference(
    {key: packet["planning_context"].get(key) for key in ("path", "sha256")},
    "planning_context",
)
manifest = json.loads(manifest_path.read_text())

# Read the bridge's package references from the isolated worker, without
# inheriting its parent's cwd, skill context, or conversation. This observes
# transport/readability; it does not simulate a model's engineering judgment.
guidance_references = {}
for label in ("Coding decision guide", "Repeatable test-suite guide", "Implementation constitution"):
    prefix = label + ": "
    locators = [text[len(prefix):] for text in packet["instructions"] if text.startswith(prefix)]
    if len(locators) != 1:
        raise SystemExit("missing or duplicate worker guidance: " + label)
    path = Path(locators[0].split("#", 1)[0])
    if not path.is_absolute() or not path.is_file():
        raise SystemExit("unavailable worker guidance: " + label)
    if not path.read_text().strip():
        raise SystemExit("empty worker guidance: " + label)
    guidance_references[label] = str(path)

brief_path = checked_reference(packet["planning_brief"], "planning_brief")
brief = brief_path.read_text()
if ("# Planning reference statements" not in brief or "Architecture decision" not in brief
        or "Synthetic" not in brief or "sole task prompt" not in brief
        or "ORIGINAL-USER-PROMPT-SENTINEL" in brief):
    raise SystemExit("planning brief did not preserve the consolidated planning pass")

material = packet["reference_material"]
if not isinstance(material, list) or not material:
    raise SystemExit("reference_material is required")
contract: dict | None = None
for reference in material:
    path = checked_reference({key: reference.get(key) for key in ("path", "sha256")}, "reference_material")
    try:
        candidate = json.loads(path.read_text())
    except (UnicodeDecodeError, json.JSONDecodeError):
        continue
    if candidate.get("schema") == "chain-planning-context-fixture/v1":
        contract = candidate
if contract is None:
    raise SystemExit("reference_material omitted the context-code contract")

if manifest.get("briefing") != packet["planning_brief"]:
    raise SystemExit("packet planning_brief differs from the immutable manifest")

step = assignment["step"]
spec = contract.get("steps", {}).get(step)
if not isinstance(spec, dict) or set(spec) != {"path", "source", "check"}:
    raise SystemExit("planning contract lacks a complete step specification")
name, source, check = spec["path"], spec["source"], spec["check"]
if not all(isinstance(value, str) and value for value in (name, source, check)):
    raise SystemExit("planning contract has invalid source data")

(workspace / name).write_text(source)
subprocess.run([sys.executable, "-B", "-c", check], check=True, cwd=workspace)
print(json.dumps({
    "phase": "code_ready",
    "pid": os.getpid(),
    "cwd": str(workspace),
    "step": step,
    "planning_brief": str(brief_path),
    "planning_contract": name,
    "guidance_references": guidance_references,
}), flush=True)
if sys.stdin.readline().strip() != "release":
    raise SystemExit("missing explicit fixture release")

git = ["git", "-c", "user.name=Chain Planning Context Fixture", "-c", "user.email=chain@example.invalid"]
subprocess.run([*git, "add", name], check=True)
subprocess.run([*git, "commit", "-qm", "Implement " + step + " from planning context"], check=True)
commit = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
handoff = workspace / ".shiploop-handoff" / assignment["attempt"] / "handoff.json"
handoff.parent.mkdir(parents=True, exist_ok=True)
checks = handoff.parent / "checks.json"
finding = "Observed " + name + " passes its frozen planning-contract check."
rationale = "Used the immutable source contract so dependent steps receive the agreed interface."
uncertainty = "Only the declared fixture check ran; live service behavior is unverified."
checks.write_text(json.dumps({
    "passed": True,
    "check": check,
    "cwd": str(workspace),
    "commit": commit,
    "planning_context_fixture": True,
    "guidance_references": guidance_references,
    "finding": finding,
    "rationale": rationale,
    "uncertainty": uncertainty,
}) + "\n")
manifest = {
    "schema": "shiploop-chain-handoff/v1",
    "run_id": assignment["run_id"],
    "step": step,
    "attempt": assignment["attempt"],
    "base_commit": assignment["base_commit"],
    "status": "SUCCEEDED",
    "commit": commit,
    "summary": finding + " " + rationale + " " + uncertainty + " Parent: inspect checks.json and verify integration.",
    "files": [{"path": "checks.json", "sha256": sha256(checks)}],
}
handoff.write_text(json.dumps(manifest) + "\n")
print(json.dumps({
    "handoff": str(handoff),
    "sha256": sha256(handoff),
    "commit": commit,
    "phase": "completed",
}), flush=True)
