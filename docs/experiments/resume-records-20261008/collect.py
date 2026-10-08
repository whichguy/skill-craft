#!/usr/bin/env python3
"""Recompute the evidence behind the 2026-10-08 RESUME item from the recorded harness run folders.

  python3 docs/experiments/resume-records-20261008/collect.py [/Users/dadleet/e2e-runs] > evidence.json

Reads, never writes, the run folders (outside the repository, as the SPEC requires). The old resume prompt is
recomputed from the harness as it was at 8a198cdd (the `git show` of run.py and hosts.py), the new one from the
current harness, so the two columns can be compared on the same folders.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
BASE = "8a198cdd"


def harness(directory: Path, name: str):
    """Import test/shiploop_e2e/<name>.py from `directory` as its own module (run.py imports hosts and metrics)."""
    sys.path.insert(0, str(directory))
    for module in ("hosts", "metrics", "rollouts", "run"):
        sys.modules.pop(module, None)
    spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
    return spec, directory


def old_prompt(out: Path, run_dir: str, host_name: str) -> str:
    """The prompt the harness at BASE built for this run folder."""
    with tempfile.TemporaryDirectory() as temp:
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", BASE, "test/shiploop_e2e", "skills/shiploop/scripts"],
                                 check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", temp], input=archive, check=True)
        code = ("import sys; sys.path.insert(0, 'test/shiploop_e2e'); sys.path.insert(0, 'skills/shiploop/scripts');"
                "import hosts, run; from pathlib import Path;"
                f"print(run.resume_prompt(Path({str(out)!r}), {run_dir!r}, hosts.host({host_name!r})))")
        return subprocess.run([sys.executable, "-c", code], cwd=temp, check=True, capture_output=True, text=True).stdout.strip()


def new_prompt(invocation: dict, run_dir: str) -> str:
    sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
    sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
    import run
    out = Path(invocation["cwd"]).parent
    return run.resume_prompt(run_dir, run.run_cli(invocation["host"], out, Path(invocation["plugin_dir"])))


def main() -> None:
    rows = []
    for folder in sorted(p for day in sorted(RUNS.glob("2026100[4-7]")) for p in day.iterdir()):
        if (folder / "invocation.json").is_file():
            rows.append({"run": f"{folder.parent.name}/{folder.name}",
                         **{name: (folder / name).exists() for name in ("result.json", "metrics.json", "review-export")}})
    prompts = {}
    for name in ("20261007/v1230-battleship-sonnet", "20261007/v1230-battleship-grok-none"):
        out = RUNS / name
        invocation = json.loads((out / "invocation.json").read_text())
        run_dir = next(str(p.parent) for p in sorted(out.rglob("state.md")) if p.relative_to(out).parts[0] not in ("home", "build"))
        prompts[name] = {"host": invocation["host"], "source": (invocation.get("versions") or {}).get("source"),
                         "old": old_prompt(out, run_dir, invocation["host"]), "new": new_prompt(invocation, run_dir)}
    luna = RUNS / "20261005" / "v1210-battleship-luna-xhigh"
    stamps = sorted(int(p.stem.rsplit("-", 1)[1]) for p in luna.glob("invocation-resume-codex-*.json"))
    first_next = []
    for number, line in enumerate(open(luna / "events.jsonl", errors="replace")):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        command = str((event.get("rawInput") or {}).get("command") or "") if event.get("type") == "tool_call" else ""
        if event.get("toolCallId") == "item_2" and "shiploop/scripts/shiploop\" next --run-dir" in command:
            first_next.append({"events_line_0_based": number,
                               "run_dir_argument": command.split("--run-dir ", 1)[1].split('"')[1]})
    print(json.dumps({"harness_runs_2026-10-04_to_2026-10-07": rows,
                      "claude_checkout_resume_prompt": prompts,
                      "luna_xhigh_relaunch_gaps_seconds": [b - a for a, b in zip(stamps, stamps[1:])],
                      "luna_xhigh_first_next_of_fresh_sessions": first_next}, indent=1))


if __name__ == "__main__":
    main()
