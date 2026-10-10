#!/usr/bin/env python3
"""Cut the compact extracts of saved E2E runs that test/shiploop-e2e-commit-counters.test.py reads.

Run once by hand from the repository root, with the saved runs in place (they are run products and are not committed):

    python3 test/fixtures/commit-counters/cut_fixtures.py [--runs /Users/dadleet/e2e-runs]

The tests never read the saved runs: they read what this script wrote here. Each extract keeps, in their original order, the
host events the test needs (a tool call and its result, byte for byte), a trimmed copy of each packet file they name (the first
2,000 characters and a marker, so a packet file's size on disk is the fixture's own), and an invocation.json naming the case and
host. The host events are kept whole except for the copies of a tool result the host repeats (see `pruned`).
messages.json holds real commit messages from the saved runs' product repositories.

What each extract is for (a test names the extract by its folder):

  claude          r3-battleship-sonnet (2026-10-08, ShipLoop 0.58.0): a whole head behind a two-line preamble (intake); a head the
                  model cut after the Keepalive marker (discovery); a head cut by `| head` (research); a Read of a whole packet
                  and a `sed` of one (calls that name a packet file); the done packet printed as a pointer and a prefix.
  claude-wholes   s6-after-spec (2026-10-09, hello): heads printed whole by `complete` (one of them an Improve child's second
                  packet, `<action>-improve`), a stem printed cut twice and then whole (the first whole print counts), and a
                  whole head followed by other output.
  claude-columns  s6-inside-implement-mtime: a head whose lines the model cut by column (`cut -c`): every line is there, the
                  Callback line is shortened.
  grok            r3-battleship-grok-none: heads as Grok's final tool_call_update records them (`output_for_prompt` with its
                  `exit: 0` line, and the host's own `total_bytes`); packets nobody printed.
  codex           v1210-battleship-luna-xhigh: heads as Codex records them after the harness translator, one followed by an
                  `ls` the model chained.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
import metrics  # noqa: E402

KEEP = 2000  # characters of each packet file the extract keeps

# extract name -> (run folder under --runs, events to keep by line number, extra packet stems to keep without a printed head)
EXTRACTS = {
    "claude": ("20261008/r3-battleship-sonnet", [9, 25, 31, 41, 57, 492], ["nav-c0f5c72b6e24473f96badbeb0dcdea9f"]),
    "claude-wholes": ("20261009/s6-after-spec", [33, 42, 51, 57, 75, 120, 126, 209, 204, 215], []),
    "claude-columns": ("20261009/s6-inside-implement-mtime", [148], []),
    "grok": ("20261008/r3-battleship-grok-none", [140, 432, 690], []),
    "codex": ("20261005/v1210-battleship-luna-xhigh", [18, 33, 35], []),
}

# (name, run folder, commit prefix): real messages of the saved runs' product repositories
MESSAGES = [
    ("improve-six-labels", "20261008/r3-battleship-sonnet", "7e11860"),
    ("improve-free-prose", "20261007/v1230-battleship-sonnet", "e363bc6"),
    ("knowledge-with-learned", "20261008/r3-battleship-sonnet", "a7c16af"),
    ("knowledge-subject-only", "20261008/r3-battleship-sonnet", "e2f70e4"),
    ("item", "20261008/r3-battleship-sonnet", "65cd022"),
    ("raw-readme", "20261008/r3-battleship-sonnet", "9e28b73"),
    ("raw-with-key-learnings", "20261006/v1220-battleship-sonnet", "d7b380f"),
    ("leftovers", "20261007/v1230-battleship-sonnet", "9b3cc84"),
    ("baseline", "20261008/r3-battleship-sonnet", "d82b183"),
]


def run_dir_of(folder: Path) -> Path:
    for state in sorted(folder.rglob("state.md")):
        parts = state.relative_to(folder).parts
        if parts[0] not in ("home", "build") and "worktree" not in parts and state.parent.name == "run":
            return state.parent
    raise SystemExit(f"no run directory under {folder}")


def lines_of(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()


def pruned(event: dict) -> dict:
    """The event without the copies of a tool result the host repeats (Grok's `content` and `rawOutput.output` beside
    `output_for_prompt`, Claude's `tool_use_result` beside the tool_result block); the readers use the one that is kept."""
    event = dict(event)
    event.pop("tool_use_result", None)
    if event.get("type") == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
        event.pop("content", None)
        event["rawOutput"] = {k: v for k, v in event["rawOutput"].items() if k != "output"}
    return event


def call_ids_of(event: dict) -> list[str]:
    return [str(cid) for cid, _shown in metrics.tool_results(event)]


def cut(runs: Path, name: str) -> None:
    folder_name, wanted, extra = EXTRACTS[name]
    folder = runs / folder_name
    out = HERE / name
    lines = lines_of(folder / "events.jsonl")
    keep = set(wanted)
    # the call that started each kept result is kept with it, in its own position
    starts: dict[str, int] = {}
    for number, line in enumerate(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for call_id, _tool, _arg in metrics.tool_call_events(event):
            starts.setdefault(str(call_id), number)
    for number in sorted(keep):
        for call_id in call_ids_of(json.loads(lines[number])):
            if call_id in starts:
                keep.add(starts[call_id])
    out.mkdir(parents=True, exist_ok=True)
    (out / "events.jsonl").write_text("".join(json.dumps(pruned(json.loads(lines[n])), ensure_ascii=False) + "\n"
                                              for n in sorted(keep)))
    stems = set(extra)
    for number in sorted(keep):
        for _cid, shown in metrics.tool_results(json.loads(lines[number])):
            stems.update(Path(m.group(1)).stem for m in re.finditer(r"^Full packet: (\S[^\n]*\.md)$", shown, re.M))
    packets = out / "run" / "packets"
    packets.mkdir(parents=True, exist_ok=True)
    source = run_dir_of(folder) / "packets"
    for stem in sorted(stems):
        text = (source / f"{stem}.md").read_text(errors="replace")
        marker = f"\n[trimmed in the fixture; the run's packet file was {(source / f'{stem}.md').stat().st_size} bytes]\n"
        (packets / f"{stem}.md").write_text(text[:KEEP] + marker if len(text) > KEEP else text)
    invocation = json.loads((folder / "invocation.json").read_text())
    (out / "invocation.json").write_text(json.dumps({key: invocation.get(key) for key in (
        "case", "host", "model", "effort", "follow_on", "seeded")}, indent=2) + "\n")
    print(f"{name}: {len(keep)} events, {len(stems)} packet files from {folder_name}")


def messages(runs: Path) -> None:
    found = []
    for name, folder_name, prefix in MESSAGES:
        work = runs / folder_name / "work"
        full = subprocess.run(["git", "-C", str(work), "rev-parse", "--verify", "--quiet", prefix + "^{commit}"],
                              capture_output=True, text=True, check=True).stdout.strip()
        body = subprocess.run(["git", "-C", str(work), "cat-file", "commit", full], capture_output=True, text=True,
                              check=True).stdout.split("\n\n", 1)[1]
        found.append({"name": name, "source": f"{folder_name} {prefix}", "message": body.rstrip("\n") + "\n"})
    (HERE / "messages.json").write_text(json.dumps(found, indent=2, ensure_ascii=False) + "\n")
    print(f"messages.json: {len(found)} real commit messages")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--runs", type=Path, default=Path.home() / "e2e-runs")
    args = parser.parse_args()
    for name in EXTRACTS:
        cut(args.runs, name)
    messages(args.runs)


if __name__ == "__main__":
    main()
