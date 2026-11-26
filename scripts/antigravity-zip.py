#!/usr/bin/env python3
"""Build a deterministic ZIP_STORED Antigravity archive and compute its sha256.

Using ZIP_STORED (compression method 0), fixed timestamps (1980-01-01 00:00:00),
UTF-8 path ordering, and normalized Unix file modes ensures identical archive
bytes and sha256 digests across macOS and Linux CI runners.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

sys.dont_write_bytecode = True

FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)
IGNORED_DIRS = frozenset({"__pycache__", ".ruff_cache", ".git"})
IGNORED_FILES = frozenset({".DS_Store"})


class ZipBuildError(Exception):
    pass


def _collect_files(source: Path) -> list[tuple[str, Path]]:
    if not source.is_dir() or source.is_symlink():
        raise ZipBuildError(f"source must be a real directory: {source}")
    collected: list[tuple[str, Path]] = []

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.encode("utf-8")):
            if entry.is_symlink():
                rel = entry.relative_to(source).as_posix()
                raise ZipBuildError(f"refusing symlink in archive source: {rel}")
            if entry.is_dir():
                if entry.name in IGNORED_DIRS:
                    continue
                walk(entry)
            elif entry.is_file():
                if entry.name in IGNORED_FILES or entry.name.endswith(".pyc"):
                    continue
                rel = entry.relative_to(source).as_posix()
                collected.append((rel, entry))
            else:
                rel = entry.relative_to(source).as_posix()
                raise ZipBuildError(f"unsupported non-regular entry in archive source: {rel}")

    walk(source)
    collected.sort(key=lambda item: item[0].encode("utf-8"))
    if not collected:
        raise ZipBuildError(f"no files found under archive source: {source}")
    return collected


def build_archive(source: Path) -> tuple[bytes, str, int]:
    """Return (zip_bytes, sha256_hex, file_count) deterministically from source."""
    files = _collect_files(source)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel, file_path in files:
            st = file_path.stat()
            perm = 0o755 if (st.st_mode & 0o111) else 0o644
            info = zipfile.ZipInfo(filename=rel, date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | perm) << 16
            zf.writestr(info, file_path.read_bytes(), compress_type=zipfile.ZIP_STORED)
    raw = buffer.getvalue()
    return raw, hashlib.sha256(raw).hexdigest(), len(files)


def write_archive(source: Path, output: Path) -> dict:
    """Build archive from source and atomically write it when output is given."""
    raw, sha256, count = build_archive(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output.with_name(f".{output.name}.tmp.{os.getpid()}")
    try:
        tmp_path.write_bytes(raw)
        tmp_path.replace(output)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return {"sha256": sha256, "bytes": len(raw), "files": count, "output": str(output)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="materialized plugin directory (e.g. plugins/skill-craft)")
    parser.add_argument("--output", type=Path, help="optional path to write the deterministic .zip archive")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--sha256", action="store_true", help="print the 64-char hex sha256 digest only")
    mode.add_argument("--json", action="store_true", help="print JSON metadata for the archive")
    args = parser.parse_args(argv)

    try:
        if args.output is not None:
            info = write_archive(args.source, args.output)
        else:
            raw, sha256, count = build_archive(args.source)
            info = {"sha256": sha256, "bytes": len(raw), "files": count, "output": None}
    except (ZipBuildError, OSError) as exc:
        print(f"antigravity-zip: {exc}", file=sys.stderr)
        return 1

    if args.sha256:
        print(info["sha256"])
    else:
        print(json.dumps(info, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
