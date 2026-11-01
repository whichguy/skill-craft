#!/usr/bin/env python3
"""The cost side of the E2 readout: where a run's minutes and tokens went, so a time bar that misses can be read. Reads only.

    python3 round2_cost.py ~/e2e-runs-multipass/20261031/e2 [--ledgers OUT.json]

``round2_readout.py`` scores the pre-registered bar (B5 is the elapsed-time bar: B's median pass-2 time at most 1.2 times A's). It says
how long a run took, not why. This script splits each run's stage seconds into three groups and counts the rounds the quality gates
fired, using each run's own ``metrics.json`` and ``result.json``:

* files: for every run, the three living files as the run left them: bytes, how many of the engine's named sections are present, and how many
  bytes sit under named sections and under any other level-2 heading (a stray), and how many headings repeat one already seen in the file (a
  second ``## Commands``) with the bytes under the repeats. The bar counts stray headings; this view also shows whether a
  file got smaller because strays went or because less was written under the named sections.
* wording: the seven stages whose packets or duties the placement candidate changed (spec, prepare, carry-forward,
  system-test-author, release-plan, release-verify, operations). A cost of the candidate would show here first.
* product work: implement, test, document, test-spec, step-plan, validate-existing. Every extra round of a gate lands here.
* the rest: intake, discovery, research, test-strategy, plan, system-test, product-acceptance, release-check, release, handoff.

A gate that "fired" sent the run back or refused a result; ``mutation_not_done`` is ShipLoop's test-quality gate (it breaks copies of the
new code and refuses a test stage whose tests do not catch them). Nothing here changes a bar; it only points at a cause. ``--ledgers OUT.json`` also writes each run's ``delta`` block (the run ledger:
ids, placement, footprint, writes, plan, hand-off) keyed by run name, so the evidence is kept in the repository and not only in the run folders.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

WORDING = ("spec", "prepare", "carry-forward", "system-test-author", "release-plan", "release-verify", "operations")
PRODUCT = ("implement", "test", "document", "test-spec", "step-plan", "validate-existing")
NAMED = {  # shiploop_knowledge_home.SECTIONS
    "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
    "environment.md": ("Targets and runtimes", "Commands", "Skills", "Harnesses and suites", "ID convention", "Access and accounts", "Platform facts"),
    "architecture.md": ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks", "Decisions", "Superseded"),
}
RUNS = [f"{arm}{n}-ticket-{case}" for n in (1, 2, 3) for arm in ("A", "B") for case in ("assignment", "escalation")]


def row(folder: Path) -> dict | None:
    result_file, metrics_file = folder / "result.json", folder / "metrics.json"
    if not result_file.exists() or not metrics_file.exists():
        return None
    result, metrics = json.loads(result_file.read_text()), json.loads(metrics_file.read_text())
    seconds: dict[str, float] = defaultdict(float)
    sent_back = 0
    for stage in metrics.get("stages") or []:
        seconds[stage["stage"]] += stage.get("seconds") or 0.0
        sent_back += stage.get("outcome") not in ("done", None)
    gates = metrics.get("gate_counts") or {}
    wording = sum(seconds[name] for name in WORDING)
    product = sum(seconds[name] for name in PRODUCT)
    total = sum(seconds.values())
    return {"run": folder.name, "pass": bool(result.get("pass")), "process": (result.get("process") or {}).get("elapsed_seconds"),
            "stage_total": round(total, 1), "wording": round(wording, 1), "product": round(product, 1), "rest": round(total - wording - product, 1),
            "handoff": round(seconds["handoff"], 1), "sent_back": sent_back,
            "mutation_rounds": (gates.get("mutation_not_done") or {}).get("fired", 0),
            "other_refusals": sum((value or {}).get("fired", 0) for key, value in gates.items() if key != "mutation_not_done"),
            "model_calls": metrics.get("model_calls"), "tokens_m": round(((metrics.get("tokens") or {}).get("processed") or 0) / 1e6, 1)}


def file_view(path: Path, named: tuple[str, ...]) -> dict:
    """Bytes under each level-2 heading of a living file, split into named sections and strays (any other heading), plus the repeats."""
    if not path.exists():
        return {}
    sections: dict[str, int] = {}
    repeats = repeat_bytes = 0
    current = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True):
        if line.startswith("## "):
            current = line[3:].strip()
            if current in sections:
                repeats += 1
                repeat_bytes += len(line.encode())
                current = (current, repeats)  # the repeat's own body is counted as a repeat below
                sections[current] = len(line.encode())
            else:
                sections[current] = len(line.encode())
        elif current is not None:
            sections[current] += len(line.encode())
            if isinstance(current, tuple):
                repeat_bytes += len(line.encode())
    kept = {name: size for name, size in sections.items() if name in named}
    stray = {name: size for name, size in sections.items() if isinstance(name, str) and name not in named}
    return {"bytes": path.stat().st_size, "named_present": len(kept), "named_total": len(named), "named_bytes": sum(kept.values()),
            "stray_headings": len(stray), "stray_bytes": sum(stray.values()), "repeat_headings": repeats, "repeat_bytes": repeat_bytes,
            "missing": [name for name in named if name not in sections]}


def files_table(root: Path) -> list[str]:
    lines = [f"{'run':24s} {'file':15s} {'bytes':>6s} {'named':>6s} {'namedB':>7s} {'stray#':>6s} {'strayB':>6s} {'rep#':>4s} {'repB':>6s}  missing named sections"]
    for name in RUNS:
        for file, named in NAMED.items():
            view = file_view(root / name / "work" / "docs" / "shiploop" / file, named)
            if view:
                lines.append(f"{name:24s} {file:15s} {view['bytes']:6d} {view['named_present']:>3d}/{view['named_total']:<2d} {view['named_bytes']:7d} "
                             f"{view['stray_headings']:6d} {view['stray_bytes']:6d} {view['repeat_headings']:4d} {view['repeat_bytes']:6d}  {', '.join(view['missing'])}")
    return lines


def ledgers(root: Path) -> dict:
    found = {}
    for name in RUNS:
        metrics_file = root / name / "metrics.json"
        if metrics_file.exists():
            found[name] = json.loads(metrics_file.read_text()).get("delta")
    return found


def main(argv: list[str]) -> int:
    argv = list(argv)
    out = None
    if "--ledgers" in argv:
        at = argv.index("--ledgers")
        out = Path(argv[at + 1])
        del argv[at:at + 2]
    root = Path(argv[0]).expanduser() if argv else Path.home() / "e2e-runs-multipass/20261031/e2"
    rows = [found for name in RUNS if (found := row(root / name))]
    head = f"{'run':24s} {'pass':4s} {'secs':>7s} {'wording':>7s} {'product':>7s} {'rest':>6s} {'handoff':>7s} {'sent':>4s} {'mut':>3s} {'oth':>3s} {'calls':>5s} {'tokM':>5s}"
    print(head)
    for r in rows:
        print(f"{r['run']:24s} {'yes' if r['pass'] else 'NO':4s} {r['process'] or 0:7.1f} {r['wording']:7.1f} {r['product']:7.1f} {r['rest']:6.1f} {r['handoff']:7.1f} "
              f"{r['sent_back']:4d} {r['mutation_rounds']:3d} {r['other_refusals']:3d} {r['model_calls'] or 0:5d} {r['tokens_m']:5.1f}")
    for case in ("assignment", "escalation"):
        for arm in ("A", "B"):
            picked = [r for r in rows if r["run"].startswith(arm) and r["run"].endswith(case)]
            if picked:
                print(f"median {arm} {case:10s} secs {statistics.median(r['process'] for r in picked):7.1f}  product {statistics.median(r['product'] for r in picked):7.1f}  "
                      f"wording {statistics.median(r['wording'] for r in picked):6.1f}  mutation rounds {statistics.median(r['mutation_rounds'] for r in picked):g}  (n={len(picked)})")
    print()
    print("\n".join(line.rstrip() for line in files_table(root)))
    if out:
        out.write_text(json.dumps(ledgers(root), indent=1, sort_keys=True) + "\n")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
