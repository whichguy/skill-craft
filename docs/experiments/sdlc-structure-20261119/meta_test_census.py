#!/usr/bin/env python3
"""Count, in a delivered product's own tests, the tests that do not run the product (round 15).

Three marks, each a list to confirm by reading and not a verdict:
  reads-document   a test file reads a document or package metadata as text (README, CHANGELOG, docs/, *.md,
                   package.json) and the base's copy of that test file did not
  runs-the-suite   a test file starts the test runner itself (a spawn whose arguments hold --test, or npm test)
  counts-files     a test file lists a folder and asserts on how many files it holds
Usage: python3 -I meta_test_census.py NAME=TREE[,BASE_TREE] ...
"""
import re
import sys
from pathlib import Path

MARKS = {
    "reads-document": re.compile(r"readFileSync\([^\n]*(README|CHANGELOG|['\"/]docs['\"/]|\.md['\"]|package\.json)"),
    "runs-the-suite": re.compile(r"spawn(Sync)?\([^\n]*(\[\s*['\"]--test['\"]|['\"]--test['\"]|['\"]npm['\"][^\n]*['\"]test['\"])"),
    "counts-files": re.compile(r"readdirSync\([^\n]*\)[^\n]*\.length|\.length\s*>=\s*\d+[^\n]*(files|sources)|(files|sources)\.length"),
}


def test_files(tree):
    for path in sorted(Path(tree).rglob("*.js")):
        rel = path.relative_to(tree).as_posix()
        if "node_modules" in rel or "test-fixtures" in rel or "/fixtures/" in rel:
            continue
        if rel.startswith(("test/", "tests/", "test-support/", "testlib/")):
            yield rel, path


def main(argv):
    rows = []
    for spec in argv:
        name, trees = spec.split("=")
        tree, _, base = trees.partition(",")
        hits = {}
        for rel, path in test_files(tree):
            text = path.read_text(errors="replace")
            before = (Path(base) / rel).read_text(errors="replace") if base and (Path(base) / rel).is_file() else ""
            for mark, pattern in MARKS.items():
                lines = [m.group(0)[:90] for m in pattern.finditer(text) if m.group(0) not in before]
                if lines:
                    hits.setdefault(mark, []).append((rel, len(lines), lines[0]))
        rows.append((name, hits))
    for name, hits in rows:
        marks = ", ".join(f"{mark} ({sum(n for _, n, _ in found)} in {len(found)} file{'s' if len(found) > 1 else ''})" for mark, found in hits.items())
        print(f"{name:26s} {marks or 'none'}")
        for mark, found in hits.items():
            for rel, n, first in found:
                print(f"    {mark}: {rel}: {first}")
    marked = sum(1 for _, hits in rows if hits)
    print(f"\n{marked} of {len(rows)} deliveries have at least one mark")


main(sys.argv[1:])
