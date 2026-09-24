#!/usr/bin/env python3
"""Build every plugin package and catalog from source into a separate directory.

skills/, agents/ and bundles/ are the source of truth. The committed plugins/,
host catalogs and README inventory are release output: only
scripts/release.py rewrites them. Tests and CI use this script to build the
same output from the current working tree without touching the checkout.

Usage:
  build-packages.py OUT     # OUT must not exist; prints OUT on success

OUT receives a copy of the source inputs plus freshly generated plugins/,
catalogs and README.md. Nothing is read from the committed plugins/ tree, so
a skill added or removed since the last release is reflected exactly.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Inputs the generator reads. Generated trees (plugins/, catalogs) are
# deliberately absent so the build cannot inherit stale release output.
SOURCE_PREFIXES = ("skills/", "agents/", "bundles/", "catalog/", "scripts/")
SOURCE_FILES = (".gitattributes", "LICENSE", "README.md")


def source_files(root):
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True, capture_output=True).stdout.decode().split("\0")
    for rel in listed:
        if not rel or not (rel.startswith(SOURCE_PREFIXES) or rel in SOURCE_FILES):
            continue
        path = root / rel
        # A tracked file deleted in the working tree is not part of the source.
        if path.is_file() or path.is_symlink():
            yield rel


def build(out, root=ROOT):
    if out.exists():
        raise SystemExit(f"build-packages: {out} already exists; name a new directory")
    for rel in source_files(root):
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target, follow_symlinks=False)
    for step in ([], ["--check"]):
        subprocess.run(["bash", str(out / "scripts/sync-plugin-views.sh"), *step],
                       cwd=out, check=True, stdout=subprocess.DEVNULL)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    try:
        print(build(args.out.resolve()))
    except subprocess.CalledProcessError as exc:
        print(f"build-packages: {' '.join(map(str, exc.cmd))} failed ({exc.returncode})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
