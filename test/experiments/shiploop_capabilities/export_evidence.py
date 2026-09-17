#!/usr/bin/env python3
"""Export a curated, redacted receipt set; never export raw platform source."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    study = args.study.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    selected = [
        "manifest.json", "frozen/candidate.md", "frozen/plan.md",
        "reports/run-inventory.json", "reports/runtime-amendment.json",
        "reports/runtime-v2-smoke.json", "reports/stage-gates.json",
        "reports/study-closeout.json", "reports/review.json",
        "reports/runner-final-audit.json", "reports/collector-audit.json",
        "private/calibration/calibration.json",
        "private/calibration/baked-inner-baseline.json",
        "private/calibration/thin-test-mutation-baseline.json",
        "private/calibration/hash-provenance.json",
        "private/calibration/reviewer-summary.md",
        "private/grades/index.json", "private/grades/coverage-inventory.json",
        "private/grades/shared-fixed-reference-malformed-actor.json",
    ]
    selected += [str(p.relative_to(study)) for p in sorted((study / "private/grades").glob("*.summary.json"))]
    selected += [str(p.relative_to(study)) for p in sorted((study / "private/grades").glob("*.oracle.json"))]
    selected += [str(p.relative_to(study)) for p in sorted((study / "private/grades").glob("*.procedure-access-audit.json"))]
    selected += [str(p.relative_to(study)) for p in sorted((study / "private/semantic-grades").glob("*.json"))]
    selected += [str(p.relative_to(study)) for p in sorted((study / "private/blind-supplements").glob("*.json"))]
    # Account-specific identifiers are read only to remove exact occurrences.
    identifiers = []
    for config in (study / "arms").glob("platform-*/gateway.json"):
        data = json.loads(config.read_text())
        value = data.get("gas", {}).get("selectedScriptId")
        if value:
            identifiers.append(value)

    def redact(text: str) -> str:
        for value in identifiers:
            text = text.replace(value, "<PINNED_TARGET>")
        text = text.replace(str(study), "<STUDY>")
        text = re.sub(r"/Users/[^/\s\"']+", "/Users/<USER>", text)
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<EMAIL>", text)
        return text

    index = []
    for relative in selected:
        source = study / relative
        if not source.is_file():
            continue
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        original = source.read_bytes()
        result = redact(original.decode()).encode()
        dest.write_bytes(result)
        index.append({"source": relative, "original_sha256": hashlib.sha256(original).hexdigest(),
                      "export_sha256": hashlib.sha256(result).hexdigest(), "bytes": len(result)})
    (output / "index.json").write_text(json.dumps({
        "policy": "Curated receipts only. Raw platform source, target configuration, transcripts and credentials are excluded. Redacted exports have distinct hashes.",
        "entries": index,
    }, indent=2) + "\n")
    print(json.dumps({"files": len(index), "output": str(output)}))


if __name__ == "__main__":
    main()
