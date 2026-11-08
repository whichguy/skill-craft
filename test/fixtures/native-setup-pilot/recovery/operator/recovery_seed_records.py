#!/usr/bin/env python3
"""Export actual accepted upstream plans from the preparation slice for its test seed."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def load_slice(harness_root: Path):
    source = harness_root / "test" / "shiploop_e2e" / "slice.py"
    if not source.is_file():
        raise SystemExit(f"frozen native slice not found: {source}")
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location("recovery_frozen_slice", source)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load frozen slice: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--first-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-catalog", type=Path)
    parser.add_argument("--output-catalog", type=Path)
    parser.add_argument("--case", default="readiness-recovery")
    args = parser.parse_args(argv)
    if bool(args.case_catalog) != bool(args.output_catalog):
        parser.error("--case-catalog and --output-catalog must be supplied together")
    harness_root = args.harness_root.expanduser().resolve()
    first = args.first_output.expanduser().resolve()
    output = args.output.expanduser().resolve()
    head = subprocess.run(
        ["git", "-C", str(harness_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=10
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(harness_root), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=True, timeout=10
    ).stdout
    if head != args.expected_head or status:
        raise SystemExit(f"frozen harness identity mismatch: head={head} clean={not bool(status)}")
    result = json.loads((first / "slice-result.json").read_text(encoding="utf-8"))
    run_dir = Path(result["run_dir"])
    module = load_slice(harness_root)
    state = module.read_state(run_dir)
    if state is None:
        raise SystemExit(f"first slice run state is unreadable: {run_dir}")
    records = {}
    actions = {}
    for stage in ("test-strategy", "plan", "prepare", "step-plan"):
        accepted = [row for row in state.get("history") or []
                    if row.get("stage") == stage and row.get("outcome") == "done"]
        if not accepted or not accepted[-1].get("action"):
            raise SystemExit(f"first slice has no accepted {stage} result")
        action = accepted[-1]["action"]
        record = module.store.read_record(run_dir / "results" / f"{action}.md").get("result")
        if not isinstance(record, dict):
            raise SystemExit(f"accepted {stage} result is not an object")
        records[stage] = record
        actions[stage] = action
    if not records["step-plan"].get("steps"):
        raise SystemExit("accepted step-plan result has no steps")
    # Reconstructing outer plan from catalog bookkeeping can introduce unsupported
    # fields; preserve the exact accepted plan and its readiness history instead.
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    catalog_output = None
    if args.case_catalog:
        catalog = json.loads(args.case_catalog.read_text(encoding="utf-8"))
        items = records["plan"].get("work_items") or []
        if len(items) != 1 or args.case not in catalog:
            raise SystemExit("recovery continuation needs its one accepted work item and named case")
        original_item = catalog[args.case].get("work_item") or {}
        if items[0].get("id") != original_item.get("id"):
            raise SystemExit("accepted item does not match the case item")
        # The frozen seed overwrites plan.work_items with the catalog item after
        # applying seed records. Forward the accepted item at both input seams.
        catalog[args.case]["work_item"] = items[0]
        catalog_output = args.output_catalog.expanduser().resolve()
        if catalog_output.exists() or catalog_output == output:
            raise SystemExit(f"refusing conflicting or existing catalog output {catalog_output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if catalog_output:
        catalog_output.parent.mkdir(parents=True, exist_ok=True)
        catalog_output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "actions": actions,
        "steps": len(records["step-plan"]["steps"]),
        "source": str(first),
        "output": str(output),
        "normalized_catalog": str(catalog_output) if catalog_output else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
