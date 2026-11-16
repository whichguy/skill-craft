#!/usr/bin/env python3
"""How much instruction text each arm of the 2026-11-15 value study gave the planner, and where Backchain's code goes.

Writes design-inventory.json beside this script. The Backchain arm's reads come from the route tables in
skills/backchain/scripts/backchain.py (DRAFTING, REVIEWING) plus SKILL.md and the bundled Until Loop adapter card; the
no-skill arm's only instruction file was plan-format.md. Journal R10-9 found that every 2026-11-01 cohort run also read
the Until Loop runtime reference and technical-interactions.md whole, so the upper figure adds the runtime
reference, the elaborator and every lens card. Run from the repository root:
    python3 -I docs/experiments/backchain-premise-20261115/design_inventory.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BC = ROOT / "skills" / "backchain"
UL = ROOT / "skills" / "improve" / "runtime" / "until-loop"
FORMAT = ROOT / "docs" / "experiments" / "backchain-value-20261115" / "plan-format.md"

FRESH_ROUTE = [BC / "SKILL.md", BC / "prompts" / "direct.v1.md", BC / "prompts" / "dependency-review.prompt.md",
               BC / "references" / "convergence.md", BC / "prompts" / "convergence-review.prompt.md",
               BC / "references" / "technical-lenses.md", BC / "references" / "technical-interactions.md",
               UL / "ADAPTER.md"]
ON_DEMAND = [BC / "prompts" / "elaborator.v1.md", BC / "references" / "technical-lens-cards.md",
             UL / "references" / "runtime-ephemeral.md"]


def size(path: Path) -> int:
    return path.stat().st_size


def main() -> None:
    fresh = {str(p.relative_to(ROOT)): size(p) for p in FRESH_ROUTE}
    extra = {str(p.relative_to(ROOT)): size(p) for p in ON_DEMAND}
    fmt = size(FORMAT)
    low, high = sum(fresh.values()), sum(fresh.values()) + sum(extra.values())
    scripts = {p.name: sum(1 for _ in p.open()) for p in sorted((BC / "scripts").glob("*.py"))}
    out = {
        "no_skill_arm": {str(FORMAT.relative_to(ROOT)): fmt},
        "backchain_fresh_route_reads": fresh,
        "backchain_reads_when_needed": extra,
        "bytes": {"no_skill": fmt, "backchain_low": low, "backchain_high": high,
                  "ratio_low": round(low / fmt, 1), "ratio_high": round(high / fmt, 1)},
        "script_lines": scripts,
        "note": "backchain_graph.py holds the seven invariants, packaging and export; backchain.py holds the run "
                "machinery (prepare, freeze, record, verify, finish, lenses); check_preservation.py compares a "
                "candidate with what it must keep.",
    }
    (Path(__file__).resolve().parent / "design-inventory.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"no-skill {fmt} bytes; Backchain {low}-{high} bytes ({out['bytes']['ratio_low']}x-"
          f"{out['bytes']['ratio_high']}x); script lines {scripts}")


if __name__ == "__main__":
    main()
