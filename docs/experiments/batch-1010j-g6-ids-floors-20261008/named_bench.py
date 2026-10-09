#!/usr/bin/env python3
"""Time ``shiploop_test_counts.named`` on a 100,000-line runner output: ``python3 named_bench.py <ref|WORKTREE> ...``.

A ref is read with ``git show <ref>:skills/shiploop/scripts/shiploop_test_counts.py`` (``named`` of a ref before the change
returns no ``inside`` key); ``WORKTREE`` is the checked-out file.  Three cases, best of 3 each: 30 listed IDs that all show,
30 IDs the runner never printed, and 30 IDs that are only a prefix of printed ones (``TC-1`` against ``TC-100``), which is the
only case that needs the second, inside, pass over the lines.
"""
import importlib.util
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELATIVE = "skills/shiploop/scripts/shiploop_test_counts.py"


def load(ref: str):
    path = ROOT / RELATIVE
    if ref != "WORKTREE":
        temp = Path(tempfile.mkdtemp(prefix="named-bench-")) / "shiploop_test_counts.py"
        temp.write_text(subprocess.run(["git", "-C", str(ROOT), "show", ref + ":" + RELATIVE], check=True,
                                       capture_output=True, text=True).stdout)
        path = temp
    spec = importlib.util.spec_from_file_location("counts_" + ref.replace("/", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(refs: list) -> None:
    lines = ["✔ TC-%d title number %d with some words (1ms)" % (i % 500 + 100, i) for i in range(100000)]
    output = "\n".join(lines) + "\nRan 100000 tests in 1s\n\nOK\n"
    cases = {"30 IDs that all show": ["TC-%d" % (n + 100) for n in range(30)],
             "30 IDs never printed": ["TC-X%d" % n for n in range(30)],
             "30 IDs that are a prefix of printed ones": ["TC-%d" % n for n in range(1, 31)]}
    for ref in refs:
        module = load(ref)
        row = []
        for label, ids in cases.items():
            best = min(_time(module, output, ids) for _ in range(3))
            row.append("%s: %.2f s" % (label, best))
        print("%-10s" % ref[:10], " | ".join(row))


def _time(module, output: str, ids: list) -> float:
    start = time.perf_counter()
    module.named(output, ids)
    return time.perf_counter() - start


if __name__ == "__main__":
    main(sys.argv[1:] or ["WORKTREE"])
