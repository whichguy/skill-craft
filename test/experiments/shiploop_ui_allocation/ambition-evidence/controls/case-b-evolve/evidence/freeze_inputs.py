#!/usr/bin/env python3
"""Freeze or verify the B producer inputs before its blind launch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT.parent
PACKAGE = STUDY / "package" / "shiploop"
PRIOR = STUDY.parent


def item(path: Path) -> dict[str, object]:
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def records() -> dict[str, dict[str, dict[str, object]]]:
    product = ROOT / "product"
    producer_paths = [
        ROOT / "evidence" / name for name in (
            "request.md", "controlled-status-contract.md", "tooling-facts.md",
            "producer-boundary.md", "seed-claims.md",
        )
    ] + [
        product / name for name in (
            "README.md", "SHIPLOOP.md", "app.js", "index.html", "styles.css",
            "host-observation.json", "docs/api.md", "docs/design.md",
            "docs/platform.md", "scripts/probe_environment.py",
        )
    ] + [
        PACKAGE / "SKILL.md", PACKAGE / "references" / "behavioral-requirements.md",
        PACKAGE / "scripts" / "shiploop", PACKAGE / "scripts" / "shiploop_navigator.py",
        PACKAGE / "scripts" / "shiploop_navigator_v3_prompts.py",
        PRIOR / "frozen" / "improve" / "SKILL.md",
        PRIOR / "frozen" / "improve" / "runtime" / "until-loop" / "ADAPTER.md",
        PRIOR / "capabilities" / "frontend-design" / "SKILL.md",
    ]
    return {
        "producer_inputs": {str(path): item(path) for path in producer_paths},
        "oracle_only": {str(ROOT / "oracle" / "expected.json"): item(ROOT / "oracle" / "expected.json")},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    output = ROOT / "evidence" / "frozen-input-manifest.json"
    current = records()
    if args.verify:
        saved = json.loads(output.read_text(encoding="utf-8"))
        print(json.dumps({"matches": saved.get("records") == current, "manifest": str(output), "current": current}, sort_keys=True))
        raise SystemExit(0 if saved.get("records") == current else 2)
    report = {
        "schema": "shiploop-ui-ambition-followup-freeze/v1",
        "case": ROOT.name,
        "purpose": "Freeze controlled input bytes before one blind planning producer; no product or host claim.",
        "oracle_visibility": "oracle_only records are frozen before launch and excluded from the producer brief.",
        "records": current,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(output), "records": current}, sort_keys=True))


if __name__ == "__main__":
    main()
