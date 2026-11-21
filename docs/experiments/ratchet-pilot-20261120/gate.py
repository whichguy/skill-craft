#!/usr/bin/env python3
"""The Ratchet pilot's gate: run every check of a work folder and say which fail.

    python3 gate.py WORK [--record FILE] [--clauses-only] [--no-restore]

WORK is the product's Git repository. The gate reads three things from it:

  ratchet/acceptance.json   {"C-1": {"command": "<shell command, run in WORK; exit 0 means the clause holds>"}, ...}
  .git/ratchet-gate.json    written by ratchet.py, never by a model: {"base": <commit the work began from>,
                            "frozen": <commit whose acceptance tests and spec are frozen, or null>,
                            "checks": [<the project's own commands, such as "npm test">]}
  the files changed since `base`, for the syntax check

and does four things, in this order:

  1. restore   while a frozen commit is set, any difference from it under acceptance/, ratchet/spec.md and
               ratchet/acceptance.json is put back, and each restored path is appended to .git/ratchet-tamper.log
  2. clauses   each clause's command; a failure is run once more, and a command that passes the second time is
               recorded as unstable and counted as passing
  3. checks    the project's own commands, the same way
  4. syntax    `node --check` on every JavaScript file changed since the base (the pilot's stand-in for a lint pass)

It prints one line per failing check with the last lines of its output and exits 0 only when nothing fails. It uses
the standard library alone and names no file outside WORK, so a copy of this file can be handed to a model session as
its exit check without showing it this repository.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

FROZEN_PATHS = ("acceptance", "ratchet/spec.md", "ratchet/acceptance.json")
COMMAND_SECONDS = 180
TAIL_LINES = 14


def git(work, *args, check=False):
    done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True, check=check)
    return done.stdout if done.returncode == 0 else None


def run(command, work, seconds=COMMAND_SECONDS):
    """One shell command in `work`, in a process group of its own; {rc, seconds, tail}. rc None means it did not end."""
    env = {key: value for key, value in os.environ.items() if key != "PORT"}
    began = time.time()
    proc = subprocess.Popen(command, shell=True, cwd=str(work), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=seconds)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # this command's own group, never a name
        except ProcessLookupError:
            pass
        output, _ = proc.communicate()
        rc = None
        output = (output or "") + f"\n(did not end within {seconds} s)"
    lines = [line for line in (output or "").splitlines() if line.strip()]
    return {"rc": rc, "seconds": round(time.time() - began, 1), "tail": lines[-TAIL_LINES:]}


def twice(command, work):
    """Run a command; run a failure once more. `pass` is true when either run exits 0; `unstable` when only the second did."""
    first = run(command, work)
    if first["rc"] == 0:
        return {"pass": True, "unstable": False, **first}
    second = run(command, work)
    return {"pass": second["rc"] == 0, "unstable": second["rc"] == 0, "first_rc": first["rc"], "first_tail": first["tail"], **second}


def restore(work, frozen):
    """Put the frozen paths back as the frozen commit has them; the paths that were changed or added."""
    changed = []
    listed = git(work, "status", "--porcelain", "--untracked-files=all", "--", *FROZEN_PATHS) or ""
    differs = git(work, "diff", "--name-only", frozen, "--", *FROZEN_PATHS) or ""
    changed += [line for line in differs.splitlines() if line]
    untracked = [line[3:] for line in listed.splitlines() if line.startswith("??")]
    for name in untracked:
        if git(work, "cat-file", "-e", f"{frozen}:{name}") is None:  # a file the frozen commit does not have
            target = Path(work) / name
            if target.is_file() or target.is_symlink():
                target.unlink()
                changed.append(name)
    if changed:
        present = [path for path in FROZEN_PATHS if git(work, "cat-file", "-e", f"{frozen}:{path}") is not None]
        tracked_now = (git(work, "ls-files", "--", *FROZEN_PATHS) or "").splitlines()
        for name in tracked_now:
            if git(work, "cat-file", "-e", f"{frozen}:{name}") is None:
                git(work, "rm", "-q", "--cached", "--", name)
                target = Path(work) / name
                if target.exists():
                    target.unlink()
        if present:
            subprocess.run(["git", "-C", str(work), "checkout", "-q", frozen, "--", *present], check=True)
        log = Path(work) / ".git" / "ratchet-tamper.log"
        with log.open("a") as handle:
            for name in sorted(set(changed)):
                handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{name}\n")
    return sorted(set(changed))


def changed_scripts(work, base):
    names = set((git(work, "diff", "--name-only", base, "--") or "").splitlines())
    names |= set((git(work, "ls-files", "--others", "--exclude-standard") or "").splitlines())
    return sorted(name for name in names if name.endswith((".js", ".cjs", ".mjs")) and (Path(work) / name).is_file())


def gate(work, clauses_only=False, no_restore=False):
    work = Path(work).resolve()
    config_file = work / ".git" / "ratchet-gate.json"
    config = json.loads(config_file.read_text()) if config_file.exists() else {}
    record = {"restored": [], "clauses": {}, "checks": {}, "syntax": {}, "failing": []}
    if config.get("frozen") and not no_restore:
        record["restored"] = restore(work, config["frozen"])
    manifest_file = work / "ratchet" / "acceptance.json"
    manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    for ident, entry in manifest.items():
        result = twice(entry["command"], work)
        record["clauses"][ident] = {"command": entry["command"], **result}
        if not result["pass"]:
            record["failing"].append(ident)
    if not clauses_only:
        for command in config.get("checks") or []:
            result = twice(command, work)
            record["checks"][command] = result
            if not result["pass"]:
                record["failing"].append(f"check: {command}")
        for name in changed_scripts(work, config["base"]) if config.get("base") else []:
            result = run(f"node --check {json.dumps(name)}", work, 30)
            if result["rc"] != 0:
                record["syntax"][name] = result
                record["failing"].append(f"syntax: {name}")
    record["pass"] = not record["failing"]
    return record


def render(record):
    lines = []
    if record["restored"]:
        lines.append("Restored frozen files that had been changed (they are read-only here): " + ", ".join(record["restored"]))
    total = len(record["clauses"])
    held = sum(1 for row in record["clauses"].values() if row["pass"])
    lines.append(f"Acceptance clauses passing: {held} of {total}. Other checks failing: "
                 f"{sum(1 for name in record['failing'] if not name.startswith('C-'))}.")
    for name in record["failing"]:
        row = (record["clauses"].get(name) or record["checks"].get(name.removeprefix("check: "))
               or record["syntax"].get(name.removeprefix("syntax: ")) or {})
        lines.append(f"\nFAILING {name}" + (f"\n  command: {row['command']}" if row.get("command") else ""))
        lines += ["  | " + line for line in row.get("tail") or []]
    lines.append("\nGATE " + ("PASS" if record["pass"] else "FAIL"))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("work")
    parser.add_argument("--record", help="also write the full result as JSON to this file")
    parser.add_argument("--clauses-only", action="store_true", help="run the clause commands only")
    parser.add_argument("--no-restore", action="store_true", help="leave the frozen paths as they are")
    args = parser.parse_args(argv)
    record = gate(args.work, args.clauses_only, args.no_restore)
    if args.record:
        Path(args.record).write_text(json.dumps(record, indent=1) + "\n")
    print(render(record))
    return 0 if record["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
