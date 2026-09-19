"""Mutant: a cleanup failure replaces the child process's causal error."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run_child(child: Path, audit: Path, mode: str) -> str:
    workspace = Path(tempfile.mkdtemp(prefix="shiploop-python-subprocess-"))
    audit.write_text(str(workspace), encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(child), str(workspace), mode],
            check=True,
            text=True,
            capture_output=True,
        )
        return completed.stdout.strip()
    finally:
        shutil.rmtree(workspace)
        if mode == "fail":
            raise RuntimeError("cleanup telemetry failed")
