"""Controlled child process used by the subprocess-preservation fixture."""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    workspace = Path(sys.argv[1])
    mode = sys.argv[2]
    (workspace / "child-ran").write_text("ran\n", encoding="utf-8")
    if mode == "fail":
        print("root-cause: fixture child failed", file=sys.stderr)
        return 17
    if mode == "ok":
        print("child-ok")
        return 0
    raise ValueError(f"unknown mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
