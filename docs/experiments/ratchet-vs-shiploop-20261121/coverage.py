#!/usr/bin/env python3
"""How much of a delivered product's JavaScript its tests run (M5): line, function and branch coverage. No model.

    python3 coverage.py TREE BASE OUT.json --command CMD [--command CMD ...] [--manifest] [--seconds N]

TREE is a product's Git work tree; BASE is the commit the delivery started from ("-" for none). The tree is cloned with
its history into a scratch folder next to OUT.json (a plain folder: tests that watch `npm test` by path fail under the
macOS temporary folder, which is a symbolic link), and every command runs there with

  NODE_V8_COVERAGE   one folder, so every Node process the tests start writes its coverage there when it exits
  NODE_OPTIONS       --require cov-flush.cjs: a process stopped by SIGTERM, SIGINT or SIGHUP writes its coverage
                     first (v8.takeCoverage) and 100 ms later dies of the signal as it would have (when no handler of
                     its own is listening; with one, that handler decides); a server a test spawns and stops with a
                     signal is otherwise never counted. A process killed with SIGKILL writes nothing.

--manifest adds every distinct command of the tree's ratchet/acceptance.json (Ratchet's acceptance suite), after the
--command ones. The commands run one after another; each gets --seconds (default 900) and its process group is stopped
when it ends.

What is counted: the product files of static.py (JavaScript outside test folders and the arms' process folders). A
line is a line holding code (comments and blank lines left out); it is run when the V8 count at its first code
character is above 0 in any process. A function is one V8 reports (the script's top level left out); a branch is a
block range V8 reports inside a function. A product file no process loaded counts with all its lines and functions
unrun. Two scopes: `all` (every product file) and `changed` (lines and functions the delivery added or changed since
BASE, as static.changed_lines reads them). V8 offsets count UTF-16 units; the reading converts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import static

PRELOAD = """'use strict';
// The comparison's coverage reader: when a signal stops this process, write its V8 coverage first, then let the signal act.
// The write is not finished when takeCoverage returns: raising the signal at once lost the file in 4 of 8 toy runs, a
// 100 ms wait lost it in none of 8 (journal section 4, the instrument checks).
const v8 = require('v8');
for (const signal of ['SIGTERM', 'SIGINT', 'SIGHUP']) {
  const flush = () => {
    try { v8.takeCoverage(); } catch (error) { /* no coverage in this process */ }
    if (process.listenerCount(signal) === 1) {
      process.removeListener(signal, flush);
      setTimeout(() => process.kill(process.pid, signal), 100);
    }
  };
  process.on(signal, flush);
}
"""
TALLY = re.compile(r"^\s*(?:#|ℹ)\s*(tests|pass|fail|cancelled|skipped|todo)\s+(\d+)\s*$", re.MULTILINE)


def stop_group(proc: subprocess.Popen) -> None:
    for sig, wait in ((signal.SIGTERM, 3.0), (signal.SIGKILL, 1.0)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        deadline = time.time() + wait
        while time.time() < deadline:
            try:
                os.killpg(proc.pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.1)


def run_command(command: str, copy: Path, env: dict, seconds: int, log: Path) -> dict:
    started = time.time()
    with log.open("w") as handle:
        proc = subprocess.Popen(command, shell=True, cwd=copy, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            proc.wait(timeout=seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
        stop_group(proc)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    output = log.read_text(errors="replace")
    tally = {}
    for name, value in TALLY.findall(output):
        tally[name] = int(value)  # the last summary in the output wins (a run of several node --test)
    return {"command": command, "returncode": None if timed_out else proc.returncode, "timed_out": timed_out,
            "seconds": round(time.time() - started, 1), "tests": tally, "log": str(log)}


def utf16_offsets(text: str) -> list[int]:
    """offsets[i] is the UTF-16 offset of text[i]; offsets[len(text)] is the total length."""
    offsets, unit = [], 0
    for c in text:
        offsets.append(unit)
        unit += 2 if ord(c) > 0xFFFF else 1
    offsets.append(unit)
    return offsets


def paint(length: int, functions: list[dict]) -> list[int]:
    """The V8 count at each UTF-16 offset: the innermost range that holds it (ranges nest, so later-sorted wins)."""
    counts = [0] * length
    ranges = [(r["startOffset"], r["endOffset"], r["count"]) for fn in functions for r in fn.get("ranges", [])]
    ranges.sort(key=lambda r: (r[0], -r[1]))
    for start, end, count in ranges:
        start, end = max(0, start), min(length, end)
        if end > start:
            counts[start:end] = [count] * (end - start)
    return counts


def read_coverage(folder: Path, copy: Path, files: list[Path], base: str | None) -> dict:
    by_path = {str((copy / relative).resolve()): relative for relative in files}
    texts = {relative: (copy / relative).read_text(errors="replace") for relative in files}
    kinds = {relative: static.classify(texts[relative]) for relative in files}
    lines = {relative: static.code_lines(texts[relative], kinds[relative]) for relative in files}
    offsets = {relative: utf16_offsets(texts[relative]) for relative in files}
    changed = {relative: static.changed_lines(copy, base, relative) for relative in files}
    starts = {relative: static.line_starts(texts[relative]) for relative in files}
    run_lines = {relative: set() for relative in files}
    seen_functions = {relative: {} for relative in files}
    seen_branches = {relative: {} for relative in files}
    loaded, processes = set(), 0
    for record in sorted(folder.glob("*.json")):
        try:
            data = json.loads(record.read_text())
        except (OSError, ValueError):
            continue
        processes += 1
        for script in data.get("result", []):
            url = script.get("url", "")
            if not url.startswith("file://"):
                continue
            path = url[len("file://"):]
            path = re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), path)
            relative = by_path.get(str(Path(path).resolve())) if os.path.exists(path) else None
            if relative is None:
                continue
            loaded.add(relative)
            total = offsets[relative][-1]
            fns = script.get("functions", [])
            counts = paint(total, fns)
            for line, index in lines[relative].items():
                unit = offsets[relative][index]
                if unit < total and counts[unit] > 0:
                    run_lines[relative].add(line)
            for fn in fns:
                ranges = fn.get("ranges") or []
                if not ranges:
                    continue
                head = ranges[0]
                if head["startOffset"] == 0 and head["endOffset"] >= total - 1 and not fn.get("functionName"):
                    continue  # the script's top level
                key = (head["startOffset"], head["endOffset"])
                seen_functions[relative][key] = seen_functions[relative].get(key, False) or head["count"] > 0
                if fn.get("isBlockCoverage"):
                    for block in ranges[1:]:
                        bkey = (block["startOffset"], block["endOffset"])
                        seen_branches[relative][bkey] = seen_branches[relative].get(bkey, False) or block["count"] > 0

    def line_of_unit(relative, unit):
        # the line of a UTF-16 offset: find the character index, then the line
        table = offsets[relative]
        low, high = 0, len(table) - 1
        while low < high:
            mid = (low + high) // 2
            if table[mid] < unit:
                low = mid + 1
            else:
                high = mid
        line_starts = starts[relative]
        low2, high2 = 0, len(line_starts) - 1
        while low2 < high2:
            mid = (low2 + high2 + 1) // 2
            if line_starts[mid] <= low:
                low2 = mid
            else:
                high2 = mid - 1
        return low2 + 1

    rows, totals = {}, {scope: dict.fromkeys(("lines", "run", "functions", "functions_run", "branches", "branches_run"), 0)
                        for scope in ("all", "changed")}
    for relative in files:
        new = changed[relative]
        code = set(lines[relative])
        in_scope = code if new is None else {line for line in code if line in new}
        if relative in loaded:
            fn_rows = [(line_of_unit(relative, key[0]), ran) for key, ran in seen_functions[relative].items()]
            br_rows = [(line_of_unit(relative, key[0]), ran) for key, ran in seen_branches[relative].items()]
        else:
            fn_rows = [(row["line"], False) for row in static.functions(texts[relative], kinds[relative])]
            br_rows = []
        row = {"loaded": relative in loaded, "lines": len(code), "run": len(run_lines[relative] & code),
               "changed_lines": len(in_scope), "changed_run": len(run_lines[relative] & in_scope),
               "functions": len(fn_rows), "functions_run": sum(1 for _, ran in fn_rows if ran),
               "changed_functions": sum(1 for line, _ in fn_rows if new is None or line in new),
               "changed_functions_run": sum(1 for line, ran in fn_rows if ran and (new is None or line in new)),
               "branches": len(br_rows), "branches_run": sum(1 for _, ran in br_rows if ran),
               "changed_branches": sum(1 for line, _ in br_rows if new is None or line in new),
               "changed_branches_run": sum(1 for line, ran in br_rows if ran and (new is None or line in new))}
        rows[relative.as_posix()] = row
        for scope, prefix in (("all", ""), ("changed", "changed_")):
            totals[scope]["lines"] += row[f"{prefix}lines"] if prefix else row["lines"]
            totals[scope]["run"] += row[f"{prefix}run"]
            totals[scope]["functions"] += row[f"{prefix}functions"]
            totals[scope]["functions_run"] += row[f"{prefix}functions_run"]
            totals[scope]["branches"] += row[f"{prefix}branches"]
            totals[scope]["branches_run"] += row[f"{prefix}branches_run"]
    for scope in totals.values():
        scope["line_share"] = round(scope["run"] / scope["lines"], 4) if scope["lines"] else None
        scope["function_share"] = round(scope["functions_run"] / scope["functions"], 4) if scope["functions"] else None
        scope["branch_share"] = round(scope["branches_run"] / scope["branches"], 4) if scope["branches"] else None
    return {"files": rows, "all": totals["all"], "changed": totals["changed"], "processes": processes,
            "unloaded": sorted(relative.as_posix() for relative in files if relative not in loaded)}


def measure(tree: Path, base: str | None, out: Path, commands: list[str], manifest: bool, seconds: int, commit: str = "HEAD") -> dict:
    scratch = out.parent / (out.stem + "-scratch")
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    copy = scratch / "copy"
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(tree), str(copy)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(copy), "checkout", "-q", commit], check=True, capture_output=True)
    copy = copy.resolve()
    if manifest:
        path = copy / "ratchet" / "acceptance.json"
        clauses = json.loads(path.read_text()) if path.exists() else {}
        for clause in clauses.values():
            command = clause.get("command") if isinstance(clause, dict) else None
            if command and command not in commands:
                commands = [*commands, command]
    covdir = scratch / "v8"
    covdir.mkdir()
    preload = scratch / "cov-flush.cjs"
    preload.write_text(PRELOAD)
    env = dict(os.environ, NODE_V8_COVERAGE=str(covdir), CI="1", NO_COLOR="1", FORCE_COLOR="0",
               NODE_OPTIONS=(os.environ.get("NODE_OPTIONS", "") + f" --require {preload}").strip())
    env.pop("PROVIDER_TOKEN", None)
    ran = []
    for index, command in enumerate(commands):
        ran.append(run_command(command, copy, env, seconds, scratch / f"command-{index + 1}.log"))
    files = static.product_files(copy)
    result = read_coverage(covdir, copy, files, base)
    result.update(commands=ran, tree=str(tree), commit=subprocess.run(["git", "-C", str(copy), "rev-parse", "HEAD"],
                                                                      capture_output=True, text=True, check=False).stdout.strip(),
                  base=base, manifest=manifest)
    out.write_text(json.dumps(result, indent=1) + "\n")
    shutil.rmtree(copy, ignore_errors=True)
    shutil.rmtree(covdir, ignore_errors=True)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tree", type=Path)
    parser.add_argument("base")
    parser.add_argument("out", type=Path)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--commit", default="HEAD")
    args = parser.parse_args(argv)
    if not args.command and not args.manifest:
        parser.error("give --command, --manifest or both")
    result = measure(args.tree.resolve(), None if args.base == "-" else args.base, args.out.resolve(), args.command, args.manifest,
                     args.seconds, args.commit)
    for scope in ("all", "changed"):
        row = result[scope]
        print(f"{scope:<8} lines {row['run']}/{row['lines']} ({row['line_share']}), functions {row['functions_run']}/{row['functions']} "
              f"({row['function_share']}), branches {row['branches_run']}/{row['branches']} ({row['branch_share']})")
    print("commands:", [(row["returncode"], row["tests"], row["seconds"]) for row in result["commands"]], "processes", result["processes"],
          "unloaded", result["unloaded"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
