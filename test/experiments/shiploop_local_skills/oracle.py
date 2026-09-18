#!/usr/bin/env python3
"""Grade deterministic fixture output; skill content remains for human review."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skills(repo: Path) -> dict[str, str]:
    root = repo / "skills"
    result = {}
    for card in sorted(root.glob("*/SKILL.md")) if root.exists() else ():
        folder, hasher = card.parent, hashlib.sha256()
        for file in sorted(path for path in folder.rglob("*") if path.is_file()):
            hasher.update(str(file.relative_to(folder)).encode() + b"\0" + file.read_bytes())
        result[str(folder.relative_to(repo))] = hasher.hexdigest()
    return result


def release(candidate: str, target: str, rows: list[dict], decision: str, *, workflow="release-v1", max_age=None) -> dict:
    value = {"workflow": workflow, "candidate": candidate, "target": target,
             "required_checks": ["unit", "integration"], "selected_receipts": rows,
             "decision": decision, "deployment_authorized": False}
    if workflow == "release-v2":
        value["max_age"] = max_age
    return value


EXPECTED = {
    "initial": release("candidate-alpha", "staging", [
        {"check": "unit", "attempt": 1, "status": "pass"},
        {"check": "integration", "attempt": 2, "status": "fail"}], "blocked"),
    "reuse": release("candidate-bravo", "production", [
        {"check": "unit", "attempt": 2, "status": "pass"},
        {"check": "integration", "attempt": 1, "status": "pass"}], "clear"),
    "evolve": release("candidate-charlie", "staging", [
        {"check": "unit", "attempt": 1, "status": "pass", "age": 2},
        {"check": "integration", "attempt": 1, "status": "pass", "age": 5}],
        "blocked", workflow="release-v2", max_age=3),
    "fork": {"workflow": "incident-v1", "incident": "INC-42", "target": "production",
             "required_checks": ["unit", "integration"], "selected_receipts": [
                 {"check": "unit", "attempt": 1, "status": "pass"},
                 {"check": "integration", "attempt": 1, "status": "fail"}],
             "decision": "investigate"},
    "noop": release("candidate-delta", "staging", [
        {"check": "unit", "attempt": 1, "status": "pass"},
        {"check": "integration", "attempt": 1, "status": "pass"}], "clear"),
}
COMPAT = release("candidate-compatible", "staging", [
    {"check": "unit", "attempt": 1, "status": "pass"},
    {"check": "integration", "attempt": 1, "status": "pass"}], "clear")
EXPECTED["relocate"] = EXPECTED["initial"]


def read_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def exact_json(actual: object, expected: object) -> bool:
    """Ignore object key order without conflating JSON booleans and numbers."""
    return json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)


def grade(case: str, fixture: Path, before_manifest: Path) -> dict:
    before, error = read_json(before_manifest)
    if error or not isinstance(before, dict):
        raise ValueError(f"invalid before manifest: {error or 'not an object'}")
    actual, error = read_json(fixture / "output" / "decision.json")
    checks = [{"name": "exact decision.json", "passed": error is None and exact_json(actual, EXPECTED[case])}]
    prior_skills = before.get("skills", {})
    current_skills = skills(fixture)
    checks.append({"name": "skill inventory captured", "passed": isinstance(prior_skills, dict)})
    # Artifact checks do not judge whether creation or evolution was warranted.
    cards = sorted((fixture / "skills").glob("*/SKILL.md"))
    readme = (fixture / "README.md").read_text()
    indexed = all(str(card.relative_to(fixture)) in readme for card in cards)
    broken = []
    for card in cards:
        for link in re.findall(r"\]\(([^)]+)\)", card.read_text()):
            path = link.split("#", 1)[0]
            if not path or "://" in path:
                continue
            target = (card.parent / path).resolve()
            if not target.is_relative_to(fixture.resolve()) or not target.exists():
                broken.append({"card": str(card.relative_to(fixture)), "link": link})
    checks.append({"name": "existing local skill entrypoints indexed", "passed": indexed})
    checks.append({"name": "existing local skill links resolve inside repo", "passed": not broken})
    prior_contracts = before.get("contracts", {})
    if case == "reuse":
        checks.append({"name": "preexisting local skills preserved", "passed": prior_skills == current_skills})
    if case == "relocate":
        moved = fixture / "specs" / "release-contract.md"
        checks.append({"name": "relocated v1 contract preserved", "passed": moved.is_file() and
                       sha(moved) == prior_contracts.get("docs/release-contract.md")})
        checks.append({"name": "old contract path remains retired", "passed": not (fixture / "docs/release-contract.md").exists()})
    if case == "noop":
        readme = (fixture / "README.md").read_text()
        checks.append({"name": "local skill packages unchanged", "passed": prior_skills == current_skills})
        checks.append({"name": "README prose typo corrected", "passed": "receipt" in readme and "reciept" not in readme})
    if case in ("evolve", "fork"):
        v1 = fixture / "docs" / "release-contract.md"
        checks.append({"name": "v1 contract preserved", "passed": v1.is_file() and prior_contracts.get("docs/release-contract.md") == sha(v1)})
        compatible, compatible_error = read_json(fixture / "output" / "v1-compatibility-decision.json")
        checks.append({"name": "v1 compatibility output", "passed": compatible_error is None and exact_json(compatible, COMPAT)})
    return {"case": case, "fixture": str(fixture), "checks": checks,
            "observed_skill_count": len(cards), "broken_skill_links": broken,
            "before_skill_digests": prior_skills, "after_skill_digests": current_skills,
            "skill_inventory_changed": prior_skills != current_skills,
            "passed": all(row["passed"] for row in checks)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=tuple(EXPECTED), required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--before-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = grade(args.case, args.fixture.resolve(), args.before_manifest.resolve())
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
