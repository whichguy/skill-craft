#!/usr/bin/env python3
"""Require an independent review of the current product before accepting quality.

The operator writes the review; the subject may read findings but never author
the evaluator's receipt. This is a trusted test apparatus, not a hostile-host
security boundary. Human judgment remains explicit rather than a comment quota.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

DIMENSIONS = ("code", "errors", "comments", "tombstones", "tests")
PHASES = {"builder", "final"}
# This is the existing hosted-check observation budget, not a ShipLoop loop cap.
CHECK_SECONDS = 900


def snapshot(root: Path) -> dict:
    root = root.resolve()
    deployable = root / "force-app"
    if not (root / "sfdx-project.json").is_file() or not deployable.is_dir() or deployable.is_symlink():
        raise ValueError("candidate is not a Salesforce source project")
    files = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True, check=True, timeout=20,
    ).stdout.split(b"\0")
    names = {os.fsdecode(raw) for raw in files if raw}
    # Git ignore rules do not prevent Salesforce from deploying local metadata.
    # Include that entire tree so ignored Apex cannot evade source-bound review.
    for path in deployable.rglob("*"):
        if path.is_symlink():
            raise ValueError("deployable source contains a symbolic path")
        if path.is_file():
            names.add(path.relative_to(root).as_posix())
    entries = []
    digest = hashlib.sha256()
    for name in sorted(names):
        raw = os.fsencode(name)
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("candidate has a missing, escaping or symbolic source path")
        content = path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        entries.append({"path": name, "sha256": sha})
        digest.update(raw + b"\0" + content + b"\0")
    if not entries:
        raise ValueError("candidate has no source files")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    return {"repo": str(root), "head": head, "sha256": digest.hexdigest(), "files": entries}


def validate_review(review: dict, expected: dict, directory: Path) -> list[str]:
    errors = []
    if not isinstance(review, dict):
        return ["review-not-an-object"]
    if review.get("schema") != "shiploop-grok-chat-quality-review/1":
        errors.append("review-schema")
    if review.get("source_sha256") != expected["sha256"]:
        errors.append("review-source-mismatch")
    reviewer = review.get("reviewer", {})
    if (not isinstance(reviewer, dict) or reviewer.get("independent") is not True
            or any(not isinstance(reviewer.get(key), str) or not reviewer[key].strip()
                   for key in ("actor", "execution_id", "provenance"))):
        errors.append("independent-reviewer-missing")
    dimensions = review.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        errors.append("review-dimensions-incomplete")
    else:
        for key in DIMENSIONS:
            row = dimensions[key]
            if not isinstance(row, dict) or row.get("status") != "PASS" or not row.get("reason"):
                errors.append("review-dimension-" + key)
    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("review-findings-missing")
    elif any(not isinstance(row, dict) or row.get("actionable") is not False for row in findings):
        errors.append("actionable-findings-remain")
    evidence = review.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("review-evidence-missing")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("review-evidence-invalid")
                continue
            path = directory / item["path"]
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("evidence path escaped review")
                raw = path.read_bytes()
                if not raw or hashlib.sha256(raw).hexdigest() != item.get("sha256"):
                    raise ValueError("evidence hash mismatch")
            except (OSError, ValueError):
                errors.append("review-evidence-invalid")
    if review.get("status") != "PASS":
        errors.append("review-not-passed")
    return sorted(set(errors))


def run(root: Path, platform: Path, phase: str, *, wait_seconds: float = CHECK_SECONDS) -> int:
    if phase not in PHASES:
        print("grok-chat-quality: UNKNOWN (allowed only in builder/final)")
        return 2
    root, platform = root.resolve(), platform.resolve()
    if not root.is_relative_to(platform.parent) or root.is_relative_to(platform):
        print("grok-chat-quality: UNKNOWN (candidate outside this run)")
        return 2
    try:
        expected = snapshot(root)
        directory = platform / "grok-chat-quality" / expected["sha256"]
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        request_path = directory / "request.json"
        if not request_path.exists():
            request = {"schema": "shiploop-grok-chat-quality-request/1",
                       "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "phase": phase, "source": expected, "dimensions": list(DIMENSIONS),
                       "instructions": (
                           "Independent operator review required. Subject must not write review/evidence receipts. "
                           "Cite exact source/test locations, decisive assertions and executed native results for each claim. "
                           "Require field-only denial when object access exists and expired-confirmation evidence. "
                           "Verify authority, replay, transaction ordering, ownership/recovery comments and warranted tombstones. "
                           "Require independent server-side callout evidence tied to the current UI/deployment for testConnection "
                           "and sendMessage; an app-returned ok flag, local nonce read or separate provider preflight is insufficient. "
                           "Retain only closed credential-free callout projections, with org/user, request/log IDs, window, "
                           "controller method, configured endpoint and HTTP outcome; raw debug bodies/headers are excluded. "
                           "Inspect the full test map; missing required observations or generic unsupported review prose are non-pass.")}
            temporary = directory / ("request-" + str(os.getpid()) + ".tmp")
            temporary.write_text(json.dumps(request, indent=2) + "\n")
            temporary.chmod(0o600)
            temporary.replace(request_path)
        print("grok-chat-quality: independent review requested; " + str(request_path), flush=True)
        deadline = time.monotonic() + wait_seconds
        review_path = directory / "review.json"
        while not review_path.exists() and time.monotonic() < deadline:
            time.sleep(min(2, max(0, deadline - time.monotonic())))
        if not review_path.exists():
            print("grok-chat-quality: UNKNOWN (independent review pending; same request retained)")
            return 2
        review = json.loads(review_path.read_text())
        errors = validate_review(review, expected, directory)
        if snapshot(root)["sha256"] != expected["sha256"]:
            errors.append("candidate-changed-during-review")
        result = {"schema": "shiploop-grok-chat-quality-check/1", "phase": phase,
                  "source_sha256": expected["sha256"], "errors": sorted(set(errors)),
                  "status": "FAIL" if errors else "PASS"}
        (directory / ("check-" + phase + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        if errors:
            print("grok-chat-quality: FAIL (" + ", ".join(sorted(set(errors))) + "); findings=" + str(review_path))
            return 1
        print("grok-chat-quality: PASS (independent code/error/comment/tombstone/test review); receipt=" + str(review_path))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        # Provider/session strings and arbitrary source text never enter failure logs.
        print("grok-chat-quality: UNKNOWN (candidate or review evidence unreadable)")
        return 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    platform = os.environ.get("E2E_PLATFORM_DIR")
    if not platform:
        print("grok-chat-quality: UNKNOWN (run-scoped platform directory unavailable)")
        return 2
    return run(args.repo, Path(platform), os.environ.get("E2E_CHECK_PHASE", "unknown"))


if __name__ == "__main__":
    sys.exit(main())
