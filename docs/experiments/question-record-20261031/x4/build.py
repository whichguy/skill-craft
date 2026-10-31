#!/usr/bin/env python3
"""Build X4's step-plan prompts (README.md, "X4"): archived step-plan packets, today's duty (A) or today's duty plus the
pre-registered Proof-input sentence (Q).

Each packet is the full packet file the run sent for W1's first step-plan (``trace.jsonl`` row ``kind: packet``).  Its
"Current stage guidance" block is replaced by ``shiploop_prompts.duty("step-plan", delegation="inline")`` from this
checkout; the run's absolute root is rewritten to /exercise so no path leads back to the saved run (whose later results
would leak the outcome); the harness lines (callback, Until Loop block, recovery pointers) are removed and an exercise
preface says the harness runs the loop and the callback.  A first version kept those lines and said only "no tools":
Terra answered `blocked` in 64 of 64 samples (x4/terra-v1-blocked/), so nothing was measured.  The item base's file list (``git ls-tree`` at the
first step's base commit, from the run's iteration ledger) is saved beside each packet for the grader.

Writes x4/prompts/<packet>-<arm>.md, x4/packets/<packet>.json and ../jobs-x4-<slug>.tsv.  Usage: x4/build.py [SLUG]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import SKILL_SCRIPTS, SUBJECTS  # noqa: E402

sys.path.insert(0, str(SKILL_SCRIPTS))
import shiploop_prompts  # noqa: E402
import shiploop_store as store  # noqa: E402

ROOT = Path.home() / "e2e-runs-brownfield" / "20261029"
PACKETS = {  # name: (run folder, role)
    "f1-ticket-assignment": ("hooks-before-ticket-assignment", "fault"),
    "f2-ticket-escalation": ("bf-codex-r1-ticket-escalation", "fault"),
    "f3-user-listing": ("hooks-after-user-listing", "fault"),
    "c1-user-listing": ("hooks-before-user-listing", "control"),
}
SAMPLES = 8
ANCHOR = "None runs now: change the step boundary."
SENTENCE = ("For each step's Proof, name what it reads and which earlier step or the item base provides it; a test file "
            "the test stage writes later is not provided.")
PREFACE = """\
EXERCISE (read this first). You are the host model of ShipLoop doing the step-plan stage whose packet follows, in a
planning exercise. The harness, not you, runs this stage's Until Loop and its callback once you answer, so the loop
commands, the receipt and the callback are not yours to run, and their absence is not a blocker. You have no tools:
everything you may use is quoted in the packet (its hand-offs, knowledge files and request). Plan the item as the stage
guidance asks and answer with the filled result only, in one ```shiploop-state fenced block with outcome `done`; record
anything you would have checked as an expectation with its check command, as the guidance says.

"""
# Packet lines the exercise removes: the inline-delegation preamble, the recovery and full-packet pointers, the callback,
# the Until Loop block (start command, contract, receipt) and the keepalive marker; the harness owns them here.
DROP_PREFIXES = ("Continue in this context and execute the prompt.", "yourself; never clear or hand it off.",
                 "Lost context, or unsure?", "Full packet:", "Callback for this stage", "Keepalive marker:")


def strip_harness_lines(packet: str) -> str:
    lines = packet.split("\n")
    out, skipping = [], False
    for line in lines:
        if line.startswith("Until Loop (no iteration limit"):
            skipping = True
            continue
        if skipping:
            if line.startswith("Call an exit condition satisfied"):
                skipping = False
            continue
        if line.startswith(DROP_PREFIXES):
            continue
        out.append(line)
    return "\n".join(out)


def duty(arm: str) -> str:
    text = shiploop_prompts.duty("step-plan", delegation="inline").rstrip("\n")
    if arm == "Q":
        if ANCHOR not in text:
            raise SystemExit(f"the step-plan duty no longer contains {ANCHOR!r}")
        text = text.replace(ANCHOR, ANCHOR + " " + SENTENCE, 1)
    return text


def first_packet(run: Path) -> tuple[Path, str]:
    rows = [json.loads(line) for line in (run / "trace.jsonl").read_text().splitlines() if line.strip()]
    row = next(r for r in rows if r.get("kind") == "packet" and r.get("stage") == "step-plan" and r.get("item") == "W1")
    return run / row["file"], row["action"]


def base_files(run: Path, action: str) -> tuple[str, list[str]]:
    """The first step's base from the iteration ledger; without one (a plan sent back before its ledger was written),
    the planning close, the last commit whose subject records the knowledge "at prepare"."""
    repo = store.read_record(run / "state.md")["repo"]
    ledger = run / "iterations" / "W1.json"
    if ledger.is_file():
        base = json.loads(ledger.read_text())["plans"][action]["S1"]["base"]
    else:
        base = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%H", "--grep", "knowledge at prepare"],
                              capture_output=True, text=True, check=True).stdout.strip()
    listing = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", base], capture_output=True, text=True,
                             check=True).stdout.split()
    return base, listing


def main() -> None:
    slug = sys.argv[1] if len(sys.argv) > 1 else "terra"
    (HERE / "prompts").mkdir(exist_ok=True)
    (HERE / "packets").mkdir(exist_ok=True)
    jobs = []
    for name, (folder, role) in PACKETS.items():
        out = ROOT / folder
        run = next(out.glob(".shiploop-runs/*/run"))
        packet_path, action = first_packet(run)
        packet = packet_path.read_text()
        base, files = base_files(run, action)
        start = packet.index("Current stage guidance:\n") + len("Current stage guidance:\n")
        end = packet.index("\n\nRULES", start)
        packet = strip_harness_lines(re.sub(re.escape(str(out)), "/exercise", packet))
        for arm in ("A", "Q"):
            body = packet.replace(packet[packet.index("Current stage guidance:\n") + len("Current stage guidance:\n"):
                                         packet.index("\n\nRULES", packet.index("Current stage guidance:\n"))],
                                  duty(arm), 1)
            (HERE / "prompts" / f"{name}-{arm}.md").write_text(PREFACE + body)
            for sample in range(1, SAMPLES + 1):
                jobs.append(f"{SUBJECTS[slug]}\tx4/prompts/{name}-{arm}.md\tx4/{slug}/{name}-{arm}-s{sample}.json")
        (HERE / "packets" / f"{name}.json").write_text(json.dumps({
            "run": str(out), "role": role, "packet": str(packet_path), "action": action, "base": base,
            "base_files": files, "original_guidance_chars": end - start}, indent=1) + "\n")
    (HERE.parent / f"jobs-x4-{slug}.tsv").write_text("\n".join(jobs) + "\n")
    print(f"wrote {len(jobs)} X4 jobs for {slug}")


if __name__ == "__main__":
    main()
