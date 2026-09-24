#!/usr/bin/env python3
"""Build small, opt-in repository-local-skill trial fixtures (no model runner)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "skills" / "shiploop"
TASKS = {
    "initial": "Triage the bundle and assess whether reusable repository-local work is warranted.",
    "reuse": "Triage the new bundle from cold context and assess whether the durable local skill already fits.",
    "evolve": "Triage the v2 bundle and assess whether the existing local skill already covers it or needs a compatible update.",
    "fork": "Triage the incident bundle and assess whether existing local skill work fits or needs a compatible separate path.",
    "noop": "Triage the corrected bundle and assess whether any local skill work is warranted.",
    "relocate": "Triage the bundle after the repository's contract-location change; assess whether the local skill remains usable.",
}


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(repo: Path) -> dict[str, str]:
    root = repo / "skills"
    result = {}
    for card in sorted(root.glob("*/SKILL.md")) if root.exists() else ():
        folder = card.parent
        hasher = hashlib.sha256()
        for file in sorted(path for path in folder.rglob("*") if path.is_file()):
            hasher.update(str(file.relative_to(folder)).encode() + b"\0" + file.read_bytes())
        result[str(folder.relative_to(repo))] = hasher.hexdigest()
    return result


def manifest(path: Path, repo: Path, *, source: Path | None = None) -> Path:
    record = {"fixture": str(repo), "skills": inventory(repo),
              "contracts": {str(p.relative_to(repo)): digest(p)
                            for folder in ("docs", "specs")
                            for p in sorted((repo / folder).glob("*contract*.md"))}}
    if source is not None:
        record["source"] = str(source)
    put(path, json.dumps(record, indent=2, sort_keys=True))
    return path


def contract_v1() -> str:
    return """# Release-evidence triage contract v1

This document is the authority for this repository's release-evidence decision.

Read `data/bundle.json`. It supplies a string `candidate`, optional string
`target`, optional ordered `required_checks`, and `receipts`. The default target
is `staging`; the default required checks are `unit` then `integration`.
Each receipt has `candidate`, `target`, `check`, numeric integer `attempt`, and
`status` (`pass`, `fail`, or `block`). Ignore a receipt whose candidate or target
does not match the current request. For each required check, use only the matching
receipt with the largest numeric attempt. Missing receipts remain missing.

Write exactly this object to `output/decision.json`, preserving required-check
order and using a selected row of `{\"check\", \"attempt\", \"status\"}`; use
`null` and `\"missing\"` for a missing row:

```json
{
  "workflow": "release-v1",
  "candidate": "input candidate",
  "target": "resolved target",
  "required_checks": ["resolved checks"],
  "selected_receipts": [{"check": "unit", "attempt": 2, "status": "pass"}],
  "decision": "clear or blocked",
  "deployment_authorized": false
}
```

The decision is `clear` only when every selected required receipt is `pass`.
Any missing, `block`, or `fail` result is `blocked`. This local triage does not
authorize a deployment.
"""


def contract_v2() -> str:
    return """# Release-evidence triage contract v2

This is an additive contract. `docs/release-contract.md` remains the v1 authority.
Use this version when `data/bundle.json` has `workflow: "release-v2"`. Apply every
v1 matching, latest-numeric-attempt, output, and no-deployment rule. It adds an
optional numeric `max_age`, whose default is `null`. When `max_age` is not null,
each selected receipt must contain numeric `age`; a selected `pass` whose age is
missing or greater than `max_age` makes the decision `blocked`.

For v2 write the v1 object with `workflow: "release-v2"`, add top-level
`"max_age": <input value>`, and add `age` to every selected row (or `null` for a
missing row). This does not alter v1 input or output behavior.
"""


INCIDENT_CONTRACT = """# Incident-evidence triage contract v1

This document is authority only for incident triage. Read `data/bundle.json` with
`incident`, optional `target` (default `production`), ordered `checks`, and
receipt rows containing `incident`, `target`, `check`, numeric `attempt`, and
`status`. Select the latest matching numeric attempt for each requested check.

Each selected output row contains only `check`, `attempt`, and `status`, with
one row per requested check in its given order. For a missing receipt use
`attempt: null` and `status: "missing"`.

Write exactly `output/decision.json` with `workflow: "incident-v1"`, the resolved
`incident`, `target`, `required_checks`, ordered `selected_receipts`, and a
`decision` of `clear` only when every selected receipt is `pass`; otherwise use
`investigate`. There is no release pass/fail or deployment authorization in this
incident output. This contract does not replace either release contract.
"""


LESSONS = """# Durable lessons

An earlier triage accepted a stale pass. A later retry for the same check failed,
and the previous judgment ignored that later attempt. Re-open the current contract
and select matching identity plus latest numeric attempt before judging release.
"""


def initial_bundle() -> dict:
    return {"workflow": "release-v1", "candidate": "candidate-alpha", "receipts": [
        {"candidate": "candidate-old", "target": "staging", "check": "integration", "attempt": 99, "status": "pass"},
        {"candidate": "candidate-alpha", "target": "production", "check": "unit", "attempt": 88, "status": "pass"},
        {"candidate": "candidate-alpha", "target": "staging", "check": "unit", "attempt": 1, "status": "pass"},
        {"candidate": "candidate-alpha", "target": "staging", "check": "integration", "attempt": 1, "status": "pass"},
        {"candidate": "candidate-alpha", "target": "staging", "check": "integration", "attempt": 2, "status": "fail"},
    ]}


def launch(repo: Path, packet: Path, case: str) -> str:
    task = TASKS[case]
    compatibility = "" if case not in ("evolve", "fork") else "\nAlso locally verify v1 remains usable: apply `docs/release-contract.md` to `data/v1-compatibility-bundle.json` and write the exact v1-schema result to `output/v1-compatibility-decision.json`.\n"
    typo = "" if case != "noop" else "\nCorrect the ordinary `reciept` prose typo in `README.md` while preserving any local-skill index.\n"
    return f"""# Fresh-context local-skill trial

Work only in `{repo}`. {task}

Read `README.md`, `SHIPLOOP.md`, `docs/lessons.md`, the applicable contract, and
`data/bundle.json`. Read the frozen, actually rendered v3 `skill-assess` packet at
`{packet}` for its current stage guidance. Its transition history is synthetic
packet setup: do not run any callback, do not claim Improve ran, and do not use its
paths as a live run.

Perform bounded local work and local validation only. Write `output/decision.json`
exactly as the applicable contract specifies. Assess reuse before building. If a
repository-local prompt skill is warranted, keep it under `skills/<slug>/SKILL.md`
and index it in `README.md`; it must refer to the authoritative contract instead of
copying contract-specific defaults. Do not install or create global skills, add
dependencies, publish, commit, push, deploy, or create a replacement ShipLoop run.
{compatibility}{typo}"""


def copy_package(out: Path) -> Path:
    package = out / "shiploop"
    if package.exists():
        return package
    shutil.copytree(SOURCE, package, ignore=shutil.ignore_patterns("*.cover", "__pycache__"))
    return package


def rendered_packets(package: Path, out: Path, repo: Path, goal: str) -> tuple[Path, Path]:
    sys.path.insert(0, str(package / "scripts"))
    import shiploop_navigator as nav  # type: ignore
    state = nav.new_state(str(repo), goal, protocol_version=3)
    found: dict[str, Path] = {}
    for _ in range(64):
        stage = nav.current_stage(state)
        if stage in ("skill-assess", "skill-validate"):
            run = out / "synthetic-packet-state" / stage
            run.mkdir(parents=True, exist_ok=True)
            nav.save(run, state)
            result = subprocess.run([sys.executable, "-B", str(package / "scripts" / "shiploop"), "next", "--run-dir", str(run)], text=True, capture_output=True, check=True).stdout
            destination = out / "packets" / f"{stage}.md"
            put(destination, result)
            found[stage] = destination
            if stage == "skill-validate":
                break
        action = nav.current_action(state)["id"]
        synthetic = {"outcome": "done", "summary": "Synthetic packet setup only; no work, callback, or Improve execution occurred.", "evidence_refs": []}
        state = nav.apply(state, action, synthetic)
        if state["active_improve"] is not None:
            # Only planning checkpoints and the last carry-forward park a child.
            state = nav.finish_improve(state, action, {"synthetic_packet_setup": True})
    if set(found) != {"skill-assess", "skill-validate"}:
        raise RuntimeError("could not render both v3 skill packets")
    return found["skill-assess"], found["skill-validate"]


def seed(repo: Path) -> None:
    put(repo / "docs" / "release-contract.md", contract_v1())
    put(repo / "docs" / "lessons.md", LESSONS)
    put(repo / "README.md", "# Release evidence fixture\n\nRepository-local skills, if created, are indexed here.\n\nA release reciept is an observed record.\n")
    put(repo / "SHIPLOOP.md", "# Repository knowledge\n\n`docs/release-contract.md` is the release decision authority.\n")
    put(repo / "data" / "bundle.json", json.dumps(initial_bundle(), indent=2))


def init(out: Path) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    package = copy_package(out)
    repo = out / "fixture"
    if repo.exists():
        raise ValueError(f"fixture already exists: {repo}")
    repo.mkdir()
    seed(repo)
    assess, validate = rendered_packets(package, out, repo, "Triage the local release-evidence bundle and assess reusable work.")
    before = manifest(out / "control" / "before-manifest.json", repo)
    launch_path = out / "launch-initial.md"
    put(launch_path, launch(repo, assess, "initial"))
    return {"fixture": str(repo), "package": str(package), "skill_assess_packet": str(assess),
            "skill_validate_packet": str(validate), "before_manifest": str(before), "launch": str(launch_path)}


def strip_transient(repo: Path) -> None:
    for name in ("output", "run", "runs", "history", "notes", ".shiploop"):
        target = repo / name
        if target.exists():
            shutil.rmtree(target)
    (repo / "output").mkdir()


def replace_bundle(repo: Path, case: str) -> None:
    if case == "relocate":
        destination = repo / "specs" / "release-contract.md"
        destination.parent.mkdir(exist_ok=True)
        (repo / "docs" / "release-contract.md").rename(destination)
        for path in [repo / "README.md", repo / "SHIPLOOP.md", repo / "docs" / "release-contract-v2.md"]:
            if path.exists():
                put(path, path.read_text().replace("docs/release-contract.md", "specs/release-contract.md"))
        # Deliberately leave the existing skill locator stale for the fresh reader.
        put(repo / "data" / "bundle.json", json.dumps(initial_bundle(), indent=2))
        return
    bundles = {
        "reuse": {"workflow": "release-v1", "candidate": "candidate-bravo", "target": "production", "receipts": [
            {"candidate": "candidate-bravo", "target": "staging", "check": "unit", "attempt": 9, "status": "pass"},
            {"candidate": "candidate-bravo", "target": "production", "check": "unit", "attempt": 1, "status": "fail"},
            {"candidate": "candidate-bravo", "target": "production", "check": "unit", "attempt": 2, "status": "pass"},
            {"candidate": "candidate-bravo", "target": "production", "check": "integration", "attempt": 1, "status": "pass"},
            {"candidate": "candidate-alpha", "target": "production", "check": "integration", "attempt": 99, "status": "pass"},
        ]},
        "evolve": {"workflow": "release-v2", "candidate": "candidate-charlie", "max_age": 3, "receipts": [
            {"candidate": "candidate-charlie", "target": "staging", "check": "unit", "attempt": 1, "status": "pass", "age": 2},
            {"candidate": "candidate-charlie", "target": "staging", "check": "integration", "attempt": 1, "status": "pass", "age": 5},
        ]},
        "fork": {"workflow": "incident-v1", "incident": "INC-42", "target": "production", "checks": ["unit", "integration"], "receipts": [
            {"incident": "INC-42", "target": "production", "check": "unit", "attempt": 1, "status": "pass"},
            {"incident": "INC-42", "target": "production", "check": "integration", "attempt": 1, "status": "fail"},
        ]},
        "noop": {"workflow": "release-v1", "candidate": "candidate-delta", "receipts": [
            {"candidate": "candidate-delta", "target": "staging", "check": "unit", "attempt": 1, "status": "pass"},
            {"candidate": "candidate-delta", "target": "staging", "check": "integration", "attempt": 1, "status": "pass"},
        ]},
    }
    if case == "evolve":
        put(repo / "docs" / "release-contract-v2.md", contract_v2())
    if case == "fork":
        put(repo / "docs" / "incident-contract.md", INCIDENT_CONTRACT)
    if case in ("evolve", "fork"):
        put(repo / "data" / "v1-compatibility-bundle.json", json.dumps({"workflow": "release-v1", "candidate": "candidate-compatible", "receipts": [
            {"candidate": "candidate-compatible", "target": "staging", "check": "unit", "attempt": 1, "status": "pass"},
            {"candidate": "candidate-compatible", "target": "staging", "check": "integration", "attempt": 1, "status": "pass"},
        ]}, indent=2))
    if case == "noop":
        with (repo / "README.md").open("a") as handle:
            handle.write("\nA current reciept is recorded after local triage.\n")
    put(repo / "data" / "bundle.json", json.dumps(bundles[case], indent=2))


def next_case(source: Path, out: Path, case: str) -> dict:
    source, out = source.resolve(), out.resolve()
    if not any((source / name).is_file() for name in ("docs/release-contract.md", "specs/release-contract.md")):
        raise ValueError("source is not a prepared trial fixture")
    if out.exists():
        raise ValueError(f"output already exists: {out}")
    package_source = source.parent / "shiploop"
    if not package_source.is_dir():
        raise ValueError("source study has no frozen ShipLoop package")
    out.mkdir(parents=True)
    before = manifest(out / "control" / "before-manifest.json", source, source=source)
    shutil.copytree(source, out / "fixture")
    shutil.copytree(package_source, out / "shiploop", ignore=shutil.ignore_patterns("*.cover", "__pycache__"))
    repo, package = out / "fixture", out / "shiploop"
    strip_transient(repo)
    replace_bundle(repo, case)
    assess, _ = rendered_packets(package, out, repo, TASKS[case])
    launch_path = out / "launch.md"
    put(launch_path, launch(repo, assess, case))
    return {"fixture": str(repo), "before_manifest": str(before), "launch": str(launch_path), "case": case}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    first = sub.add_parser("init")
    first.add_argument("--output", type=Path, required=True)
    later = sub.add_parser("next")
    later.add_argument("--source", type=Path, required=True)
    later.add_argument("--output", type=Path, required=True)
    later.add_argument("--case", choices=("reuse", "evolve", "fork", "noop", "relocate"), required=True)
    args = parser.parse_args()
    result = init(args.output) if args.command == "init" else next_case(args.source, args.output, args.case)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
