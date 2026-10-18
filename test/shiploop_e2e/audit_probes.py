#!/usr/bin/env python3
"""The prompt-and-file audit's three size probes, with their path constants made parameters (efficiency plan step 1.1).

The audit of 2026-10-16 (docs/experiments/shiploop-audit-20261016/, measure.py and context_probe.py) measured a checkout at
2686b427 with fixed paths. This runs the same measurements on any checkout, so a change's effect is read beside the audited figure:

    python3 test/shiploop_e2e/audit_probes.py [--repo ROOT] [--json]

* ``delivery_packet_chars``: the characters of the 33 packets of the dry-run delivery graph (`shiploop graph-dry-run`), the audit's
  375,278 at 2686b427;
* ``bound_handoff_chars``: the nine bound Improve handoffs of the same walk over an empty knowledge home, the audit's 276,270;
* ``entry_card_chars``: skills/shiploop/SKILL.md, the audit's 79,647.

Each probe runs in a child process against ROOT's own scripts (never this process's imports), so measuring an older checkout cannot
mix its modules with the harness's. Synthetic declarations only: no model, no project work, no Git operation on ROOT.

A packet prints the checkout's path (the CLI, the improve card and the references) many times, so its size depends on how long that
path is: the audit's checkout, /Users/dadleet/src/skill-craft, is 30 characters. ``--root-length N`` reports the sizes as they would
be at a root N characters long (each literal occurrence of ROOT in a packet counts N, not its own length), which is how an older
checkout extracted somewhere else is read against the audit; the figures say when they were adjusted.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT_LENGTH = len("/Users/dadleet/src/skill-craft")
# The audit's context_probe.py kept its run and repository under /tmp/shiploop-audit-20261016-analysis.
AUDIT_RUN_LENGTH = len("/tmp/shiploop-audit-20261016-analysis/fixture-run")
AUDIT_REPO_LENGTH = len("/tmp/shiploop-audit-20261016-analysis/fixture-repo")
# The dry run prints the interpreter's path; the audit ran Homebrew's Python 3.14 (a CI runner's toolcache path is longer).
AUDIT_PYTHON_LENGTH = len("/opt/homebrew/opt/python@3.14/bin/python3.14")
# The audit's figures at 2686b427, to read a measurement against.
AUDITED = {"delivery_packet_chars": 375_278, "bound_handoff_chars": 276_270, "entry_card_chars": 79_647}

HANDOFF_PROBE = r'''
import copy, json, sys
from pathlib import Path
root = Path(sys.argv[1]); work = Path(sys.argv[2])
sys.path.insert(0, str(root / "skills/shiploop/scripts"))
import shiploop_navigator as nav
import shiploop_navigator_dry_run as driver
import shiploop_standalone_improve as bridge
repo = work / "repo"; repo.mkdir()
run = work / "run"; run.mkdir()
(repo / "docs/shiploop").mkdir(parents=True)
selected = bridge.resolve_skill(str(root / "skills/improve/SKILL.md"))
state = nav.new_state(str(repo), "Inspect the SDLC graph with synthetic declarations.", improve_skill=str(root / "skills/improve/SKILL.md"))
handoffs = []
for row in driver.scenarios()["delivery"]["steps"]:
    current = nav.current_action(state)
    if row.get("command") == "finish-improve":
        child = state["active_improve"]
        bound = copy.deepcopy(state)
        bound["active_improve"] = bridge.binding(state, child["action_id"], child["stage"], child["seed_result"], selected,
                                                 improve_action=child["improve_action"])
        text = nav.improve_handoff_text(driver.CORE, run, bound)
        handoffs.append({"stage": child["stage"], "characters": len(text), "root_mentions": text.count(str(root)),
                         "run_mentions": text.count(str(run)), "repo_mentions": text.count(str(repo)),
                         "run_length": len(str(run)), "repo_length": len(str(repo))})
        state = nav.finish_improve(state, child["action_id"], row["receipt"], row.get("final_result"))
    else:
        state = nav.apply(state, current["id"], row["result"])
print(json.dumps(handoffs))
'''


def delivery_packet_chars(root: Path) -> dict:
    """The dry-run delivery scenario's packets under ``root``: count, total characters, longest, and how many pass 16,000."""
    done = subprocess.run([sys.executable, "-B", str(root / "skills/shiploop/scripts/shiploop"), "graph-dry-run", "--format", "json"],
                          cwd=root, capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise RuntimeError(f"graph-dry-run exited {done.returncode}: {done.stderr[-400:]}")
    delivery = next(s for s in json.loads(done.stdout)["scenarios"] if s["name"] == "delivery")
    prompts = [event["prompt"] for event in delivery["events"]]
    counts = [len(p) for p in prompts]
    return {"packets": len(counts), "characters": sum(counts), "max": max(counts), "over_16000": sum(c > 16_000 for c in counts),
            "root_mentions": sum(p.count(str(root)) for p in prompts),
            "python_excess": sum(p.count(sys.executable) for p in prompts) * (len(sys.executable) - AUDIT_PYTHON_LENGTH)}


def bound_handoff_chars(root: Path) -> dict:
    """The bound Improve handoffs of the dry-run delivery walk over an empty home: count, total characters and each stage's."""
    with tempfile.TemporaryDirectory(prefix="shiploop-audit-") as work:
        done = subprocess.run([sys.executable, "-B", "-c", HANDOFF_PROBE, str(root), work], capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise RuntimeError(f"handoff probe exited {done.returncode}: {done.stderr[-400:]}")
    handoffs = json.loads(done.stdout)
    return {"handoffs": len(handoffs), "characters": sum(h["characters"] for h in handoffs),
            "root_mentions": sum(h["root_mentions"] for h in handoffs),
            "run_excess": sum(h["run_mentions"] * (h["run_length"] - AUDIT_RUN_LENGTH) for h in handoffs),
            "repo_excess": sum(h["repo_mentions"] * (h["repo_length"] - AUDIT_REPO_LENGTH) for h in handoffs),
            "per_stage": handoffs}


def entry_card_chars(root: Path) -> int:
    return len((root / "skills/shiploop/SKILL.md").read_text())


def measure(root: Path = DEFAULT_ROOT, root_length: int | None = None) -> dict:
    """The three figures for the checkout at ``root``, beside the audited ones. With ``root_length`` the two packet figures are
    those of a root that long (each mention of ``root`` in a packet counts ``root_length`` characters), and the handoffs' temporary run and
    repository paths and the interpreter path the dry run prints count as long as the audit's were."""
    root = Path(root).resolve()
    delivery, handoffs, card = delivery_packet_chars(root), bound_handoff_chars(root), entry_card_chars(root)
    shrink = 0 if root_length is None else len(str(root)) - root_length
    found = {"delivery_packet_chars": delivery["characters"] - shrink * delivery["root_mentions"]
             - (0 if root_length is None else delivery["python_excess"]),
             "bound_handoff_chars": handoffs["characters"] - shrink * handoffs["root_mentions"]
             - (0 if root_length is None else handoffs["run_excess"] + handoffs["repo_excess"]), "entry_card_chars": card}
    return {"root": str(root), "root_length": len(str(root)), "adjusted_to_root_length": root_length, "figures": found,
            "audited_at_2686b427": AUDITED,
            "ratio_to_audit": {k: round(found[k] / AUDITED[k], 4) for k in AUDITED},
            "delivery": delivery, "handoffs": handoffs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=DEFAULT_ROOT, help="a checkout (default: this one)")
    parser.add_argument("--root-length", type=int, nargs="?", const=AUDIT_ROOT_LENGTH,
                        help=f"report the sizes at a root this many characters long (no value: the audit's {AUDIT_ROOT_LENGTH})")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    found = measure(args.repo, args.root_length)
    if args.json:
        json.dump(found, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"checkout {found['root']} ({found['root_length']} characters"
              + (f", sizes adjusted to a {found['adjusted_to_root_length']}-character root" if found["adjusted_to_root_length"] else "") + ")")
        for name, value in found["figures"].items():
            print(f"  {name:24} {value:>9,}   audited {AUDITED[name]:>9,}   x{found['ratio_to_audit'][name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
