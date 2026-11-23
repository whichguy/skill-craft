#!/usr/bin/env python3
"""Render both scenarios' step-plan packets from one ShipLoop build, save them, and check what they hold. No model.

    python3 render_packet.py NAME [--ref REF] [--overlay FILE]

The build is the one ``stages.py live`` would make: of this checkout, or of ``--ref``, with ``--overlay`` applied to the copy. Saved as
``packets/NAME--<scenario>.md``: what ``shiploop next`` issues, whole, with the run's own paths, IDs and times replaced by names, so two
builds' packets can be compared with ``diff``. Prints sizes and the checks as JSON; exits 1 when a check fails.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "test/shiploop_e2e/stage_suite"), str(ROOT / "test/shiploop_e2e"), str(ROOT / "skills/shiploop/scripts")]
import overlay as overlays  # noqa: E402
import run  # noqa: E402
import stage_build as sb  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

CASE = json.loads((HERE / "case.json").read_text())


def normalise(text: str, out: Path, plugin: Path) -> str:
    text = text.replace(str(plugin), "<PLUGIN>").replace(str(out), "<OUT>")
    seen: dict[str, str] = {}
    return re.sub(r"nav-[0-9a-f]{32}", lambda m: seen.setdefault(m.group(0), f"nav-<{len(seen) + 1}>"), text)


def one(sc, out: Path, plugin: Path) -> tuple[str, dict]:
    bundle = sb.render(sc, out, cli=run.shiploop_cli(plugin))
    packet, head = bundle.packet, bundle.packet_head
    summary = sc.data["seed_route"][-1]["result"]["summary"]
    rows = [json.loads(line) for line in packet.splitlines() if line.startswith("{") and '"done": true' in line]
    expected = json.loads((sc.dir / "oracle/expected.json").read_text())["done_rows"]
    duty = re.search(r"^10\. \*\*Knowledge\.\*\*.*?(?=^11\. )", packet, re.M | re.S)
    spec = (bundle.tree / "docs/shiploop/spec.md").read_text()
    entries = re.findall(r"^### (R-\d+)", spec, re.M)
    contents = next((line for line in packet.splitlines() if line.strip().startswith("## Requirements: R-1")), "")
    checks = {
        "revisit line": "Revisit: implement sent W1 back to step-plan (send-back 1)" in packet,
        "summary whole in the revisit line": 'Why (its summary, untrusted): "' + summary + '"' in packet,
        "summary not cut": "[truncated; read the durable state/result record" not in packet,
        "sending result's file named": bool(re.search(r"Evidence: RUN/results/nav-[0-9a-f]{32}\.md", packet)),
        "done rows printed as they must be copied": rows == expected,
        "spec outline lists every R-n": bool(entries) and all(ident in contents for ident in entries),
        "duty 10 whole": duty is not None,
        "no owner note owed": "owner note this stage owes" not in packet.replace(duty.group(0) if duty else "", ""),
        "printed packet is the packet file": packet.strip() in head,
    }
    facts = {"packet_characters": len(packet), "printed_characters": len(head), "summary_characters": len(summary),
             "revisit_summary_limit": navigator.REVISIT_SUMMARY, "duty_10": duty.group(0) if duty else None,
             "summary_printed_times": packet.count(summary), "spec_entries": entries}
    return normalise(packet, out, plugin), {"checks": checks, **facts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--ref")
    parser.add_argument("--overlay")
    args = parser.parse_args()
    report: dict = {"name": args.name, "ref": args.ref, "overlay": args.overlay}
    with tempfile.TemporaryDirectory(prefix="spr-") as temp:
        base = Path(temp).resolve()
        plugin = overlays.build_ref(args.ref, base) if args.ref else run.build_candidate(base)
        if args.overlay:
            report["overlay_modules"] = overlays.apply_to_plugin(Path(args.overlay).resolve(), plugin)["modules"]
        report["versions"] = run.installed_versions(plugin)
        (HERE / "packets").mkdir(exist_ok=True)
        for name in (CASE["requirement_scenario"], CASE["proof_scenario"]):
            sc = sb.load("step-plan/" + name, HERE / "stage_cases")
            text, report[name] = one(sc, base / name, plugin)
            (HERE / "packets" / f"{args.name}--{name}.md").write_text(text)
        shutil.rmtree(base / "build", ignore_errors=True)
    (HERE / "packets" / f"{args.name}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=1, ensure_ascii=False))
    failed = [f"{name}: {check}" for name in (CASE["requirement_scenario"], CASE["proof_scenario"])
              for check, held in report[name]["checks"].items() if not held]
    raise SystemExit(("FAILED: " + "; ".join(failed)) if failed else 0)


if __name__ == "__main__":
    main()
