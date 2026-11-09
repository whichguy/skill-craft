#!/usr/bin/env python3
"""Qualify one recorded Plan stop and one explicitly selected initial quote."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

import metrics
import planning_boundary

_AUDIT = Path(__file__).resolve().parents[2] / "skills/shiploop-e2e-audit/harness"
# The audit helper also runs directly inside its installed package and imports
# its sibling reader by name.
sys.path.insert(0, str(_AUDIT))
try:
    import planning_evidence
    import planning_trace
finally:
    sys.path.pop(0)

_SHIPLOOP = _AUDIT.parents[1] / "shiploop/scripts"
sys.path.insert(0, str(_SHIPLOOP))
try:
    import shiploop_store as store
finally:
    sys.path.pop(0)

ExpectedPlan = planning_evidence.ExpectedPlan
BUNDLE_NAME = "planning-evidence"
PIN_NAME = "planning-evidence.sha256"
_RECORD_LIMIT = 2 * 1024 * 1024


def _read(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError(f"expected a regular evidence file at {path}")
        data = handle.read(_RECORD_LIMIT + 1)
    if len(data) > _RECORD_LIMIT:
        raise ValueError(f"evidence exceeds the size bound at {path}")
    return data


def apparatus_identity() -> dict:
    paths = (Path(__file__), Path(metrics.__file__), Path(planning_boundary.__file__),
             Path(planning_evidence.__file__), Path(planning_trace.__file__))
    return {"schema": "shiploop-planning-apparatus/v1",
            "sha256": {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}}


def expected_from_run(run_dir: Path, *, run_id: str, repo: str, repo_prefix: str,
                      source_hashes: dict | None = None) -> tuple[ExpectedPlan, dict]:
    """Join caller-registered scope to the saved Plan seed and strict producer trace."""
    state_bytes = _read(run_dir / "state.md")
    trace = planning_trace.read_trace(run_dir / "trace.jsonl")
    if trace["status"] != "ok":
        raise ValueError(f"strict producer trace {trace['status']}: {trace['reason']}")
    hashes = {"state": sha256(state_bytes).hexdigest(), "trace": trace["sha256"]}
    if source_hashes and any(source_hashes.get(name) not in (None, digest) for name, digest in hashes.items()):
        raise ValueError("state or trace changed after boundary analysis")
    state = store.loads(state_bytes.decode("utf-8"))
    if not isinstance(state, dict) or state.get("run_id") != run_id or state.get("repo") != repo:
        raise ValueError("saved run or repository differs from the registered scope")
    plans = [row for row in state.get("history") or [] if isinstance(row, dict)
             and row.get("stage") == "plan" and row.get("outcome") == "done"]
    if len(plans) != 1 or not isinstance(plan := plans[0].get("action"), str):
        raise ValueError("one saved done Plan action is required")
    receipt = (state.get("improve_results") or {}).get(plan) or {}
    improve, seed = receipt.get("improve_action"), receipt.get("seed_result")
    if not isinstance(improve, str) or not isinstance(seed, dict) or receipt.get("workspace") != repo:
        raise ValueError("the accepted Plan lacks a saved initial seed and Improve scope")
    producers = [row["record"]["rev"][1] for row in trace["rows"]
                 if _producer(row["record"], plan, improve)]
    if len(producers) != 1:
        raise ValueError("one recorded Plan producer revision is required")
    return ExpectedPlan(run_id, plan, improve, producers[0], planning_evidence.seed_digest(seed),
                        repo, repo_prefix), hashes


def _producer(row: dict, plan: str, improve: str) -> bool:
    rev = row.get("rev")
    return (row.get("kind") == "command" and row.get("verb") == "complete"
            and row.get("action") == plan and type(row.get("exit")) is int and row["exit"] == 0
            and row.get("v") == 1 and row.get("status") == "active"
            and not any(row.get(key) for key in ("held", "check_only", "crashed", "error"))
            and row.get("stage") == ["plan", "improve"] and row.get("cursor") == [plan, improve]
            and isinstance(rev, list) and len(rev) == 2 and all(type(n) is int for n in rev)
            and rev[1] == rev[0] + 1 and not row.get("accepted"))


def collect_bundle(run_dir: Path, output: Path, *, expected: ExpectedPlan) -> dict:
    """Collect the portable bundle and publish the fixed archive pin beside it."""
    result = planning_evidence.collect_initial_artifacts(run_dir, output / BUNDLE_NAME, expected=expected)
    if result["status"] != "captured":
        return result
    pin = output / PIN_NAME
    data = (result["manifest_sha256"] + "\n").encode("ascii")
    try:
        with tempfile.NamedTemporaryFile(dir=output, prefix=".planning-pin-") as temporary:
            temporary.write(data)
            temporary.flush()
            try:
                os.link(temporary.name, pin)
            except FileExistsError:
                if _read(pin) != data:
                    raise ValueError("existing planning evidence pin conflicts with the captured manifest")
    except (OSError, ValueError) as exc:
        return {"status": "invalid", "reason": str(exc)}
    return result


def _quote(run_dir: Path, output: Path, expected: ExpectedPlan, quote: str, *, field: str | None,
           locator: str | None, bundle_dir: Path | None, manifest_sha256: str | None,
           source_hashes: dict) -> tuple[dict, dict | None]:
    if field is not None:
        result = planning_evidence.verify_initial_field(
            run_dir, run_id=expected.run_id, plan_action=expected.plan_action,
            improve_action=expected.improve_action, seed_sha256=expected.seed_sha256,
            phase=expected.phase, field=field, quote=quote)
        return result, None

    capture = None
    if bundle_dir is None:
        capture = collect_bundle(run_dir, output, expected=expected)
        if capture["status"] != "captured":
            return {"status": capture["status"], "reason": capture["reason"]}, capture
        bundle_dir, manifest_sha256 = output / BUNDLE_NAME, capture["manifest_sha256"]
    result = planning_evidence.verify_linked_quote(
        bundle_dir, expected=expected, manifest_sha256=manifest_sha256, locator=locator, quote=quote)
    if result["status"] == "matched":
        # The verified manifest must describe the same state/trace bytes as this
        # admission, even when the caller supplied a previously archived copy.
        data = _read(bundle_dir / planning_evidence.MANIFEST_NAME)
        if sha256(data).hexdigest() != manifest_sha256:
            return {"status": "invalid", "reason": "portable manifest changed during verification"}, capture
        captured_hashes = json.loads(data)["source_sha256"]
        if any(captured_hashes.get(name) != digest for name, digest in source_hashes.items()):
            result = {"status": "invalid", "reason": "portable evidence differs from the recorded state or trace"}
    return result, capture


def evaluate(recording: Path, run_dir: Path, cli: Path, *, expected: ExpectedPlan, output: Path,
             quote: str, field: str | None = None, locator: str | None = None,
             bundle_dir: Path | None = None, manifest_sha256: str | None = None) -> dict:
    """Write a comparison receipt in a new external directory and return its structured result."""
    if (field is None) == (locator is None):
        raise ValueError("select exactly one initial result field or linked locator")
    if (bundle_dir is None) != (manifest_sha256 is None) or (field is not None and bundle_dir is not None):
        raise ValueError("a prior bundle and its independent pin apply together to linked verification")
    if not all(path.is_absolute() for path in (recording, run_dir, cli)):
        raise ValueError("recording, run directory and installed CLI must be their recorded absolute paths")
    output = output.expanduser().absolute()
    if not Path(expected.repo).is_absolute():
        raise ValueError("expected repository must be its recorded absolute path")
    # Keep replay output outside all source trees, including a scoped Git repo's
    # parent checkout and any portable input bundle.
    repo = Path(expected.repo)
    if expected.repo_prefix != ".":
        parts = Path(expected.repo_prefix).parts
        if not parts or repo.parts[-len(parts):] != parts:
            raise ValueError("expected repository and prefix disagree")
        repo = repo.parents[len(parts) - 1]
    roots = [recording, run_dir, repo, cli.parent.parent]
    if bundle_dir is not None:
        roots.append(bundle_dir)
    if any(output.resolve().is_relative_to(root.resolve()) for root in roots):
        raise ValueError("comparison output must be outside the source recording, run, package and repository")
    output.mkdir()
    boundary = planning_boundary.analyze(recording, run_dir, cli, run_id=expected.run_id)
    result = {
        "schema": "shiploop-planning-comparison/v1", "apparatus": apparatus_identity(),
        "boundary": boundary, "expected": asdict(expected),
        "quote_request": {"field": field, "locator": locator, "quote": quote},
        "bundle_input": {"directory": str(bundle_dir), "manifest_sha256": manifest_sha256} if bundle_dir else None,
        "capture": None, "quote": None, "admitted": False,
    }
    if boundary["status"] == "established":
        try:
            actual, hashes = expected_from_run(run_dir, run_id=expected.run_id, repo=expected.repo,
                                               repo_prefix=expected.repo_prefix,
                                               source_hashes=boundary["sources"]["sha256"])
            if actual != expected:
                result["quote"] = {"status": "invalid" if expected.phase == "initial" else "unsupported",
                                   "reason": "registered Plan identities or phase differ from the run"}
            else:
                result["quote"], result["capture"] = _quote(
                    run_dir, output, expected, quote, field=field, locator=locator, bundle_dir=bundle_dir,
                    manifest_sha256=manifest_sha256, source_hashes=hashes)
                # Discard a successful match if its saved state or trace changed
                # during the verifier read.
                if result["quote"]["status"] == "matched":
                    expected_from_run(run_dir, run_id=expected.run_id, repo=expected.repo,
                                      repo_prefix=expected.repo_prefix, source_hashes=hashes)
                    result["admitted"] = True
        except (OSError, ValueError, store.StorageError, AttributeError, RecursionError) as exc:
            result["quote"] = {"status": "invalid", "reason": str(exc)}
    (output / "planning-comparison.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recording", required=True, type=Path, help="absolute retained host recording directory")
    parser.add_argument("--run-dir", required=True, type=Path, help="recorded absolute ShipLoop run directory")
    parser.add_argument("--cli", required=True, type=Path, help="recorded absolute installed ShipLoop CLI")
    parser.add_argument("--expected", required=True, type=Path, help="caller-registered ExpectedPlan JSON object")
    parser.add_argument("--output", required=True, type=Path, help="new external receipt directory under an existing parent")
    parser.add_argument("--quote", required=True)
    selected = parser.add_mutually_exclusive_group(required=True)
    selected.add_argument("--field")
    selected.add_argument("--locator")
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args(argv)
    try:
        expected = ExpectedPlan(**json.loads(_read(args.expected)))
        result = evaluate(args.recording, args.run_dir, args.cli, expected=expected, output=args.output,
                          quote=args.quote, field=args.field, locator=args.locator, bundle_dir=args.bundle_dir,
                          manifest_sha256=args.manifest_sha256)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps({"status": "invalid", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["admitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
