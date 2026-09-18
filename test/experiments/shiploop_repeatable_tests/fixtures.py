#!/usr/bin/env python3
"""Create small worker-visible repositories for repeatable-test trials."""

from __future__ import annotations

import hashlib
from pathlib import Path
import os
import subprocess
from textwrap import dedent
from typing import Any


CASES = ("price-format", "sqlite-catalog", "expected-red")
PRIOR_NOTE = "# Prior run note\nA historical prior run recorded the command `pytest -q`.\n"


RUNNER = r'''
#!/usr/bin/env python3
"""Stdlib unittest selector used by this fixture."""
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

def discovered():
    loader = unittest.TestLoader()
    return list(flatten(loader.discover(str(ROOT), pattern="test_*.py", top_level_dir=str(ROOT))))

def tags(test):
    method = getattr(test, getattr(test, "_testMethodName", ""), None)
    return frozenset(getattr(method, "__shiploop_suites__", getattr(type(test), "__shiploop_suites__", ())))

def selected(tests, suite):
    return tests if suite == "full" else [test for test in tests if suite in tags(test)]

def selections():
    tests = discovered()
    return {name: [test.id() for test in selected(tests, name)] for name in ("focused", "smoke", "full")}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=("focused", "smoke", "full"))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1 or not args.suite and not args.list:
        parser.error("choose --list or --suite and use a positive --repeat")
    listed = selections()
    if args.list:
        print(json.dumps(listed, sort_keys=True))
        if not args.suite:
            return 0
    selected_ids = listed[args.suite]
    print("SHIPLOOP_SELECTION=" + json.dumps({"suite": args.suite, "ids": selected_ids, "repeat": args.repeat, "reverse": args.reverse}))
    ok = True
    for _ in range(args.repeat):
        tests = selected(discovered(), args.suite)
        if args.reverse:
            tests.reverse()
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.TestSuite(tests))
        ok = ok and result.wasSuccessful()
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
'''


SUPPORT = r'''
from __future__ import annotations

def suite(*names):
    """Mark a unittest method or class for focused and/or smoke selection."""
    def apply(target):
        target.__shiploop_suites__ = frozenset(names)
        return target
    return apply
'''


PRICE = r'''
def price_cents(quantity, unit_cents):
    if type(quantity) is not int or quantity < 0:
        raise ValueError("quantity")
    if type(unit_cents) is not int or unit_cents < 0:
        raise ValueError("unit_cents")
    return quantity * unit_cents

def format_price(cents):
    if type(cents) is not int or cents < 0:
        raise ValueError("cents")
    return f"${cents // 100}.{cents % 100:02d}"
'''

PRICE_MUTANT = PRICE.replace("{cents % 100:02d}", "{cents % 100}")

CATALOG = r'''
import sqlite3
import time
from pathlib import Path

STARTUP_DELAY_SECONDS = 0.15
INITIAL_ITEMS = (("bookmark", 125), ("notebook", 450))

class Catalog:
    @classmethod
    def open(cls, path, *, fail_after_open=False):
        self = cls.__new__(cls)
        self._connection = None
        time.sleep(STARTUP_DELAY_SECONDS)
        try:
            self._connection = sqlite3.connect(str(Path(path)))
            self._connection.execute("CREATE TABLE IF NOT EXISTS items (name TEXT PRIMARY KEY, cents INTEGER NOT NULL)")
            self._connection.executemany("INSERT OR IGNORE INTO items VALUES (?, ?)", INITIAL_ITEMS)
            self._connection.commit()
            if fail_after_open:
                raise RuntimeError("simulated partial setup failure")
            return self
        except Exception:
            self.close()
            raise

    def list_items(self):
        return self._connection.execute("SELECT name, cents FROM items ORDER BY name").fetchall()

    def add(self, name, cents):
        if not isinstance(name, str) or not name.strip() or type(cents) is not int or cents <= 0:
            raise ValueError("item")
        try:
            self._connection.execute("INSERT INTO items VALUES (?, ?)", (name, cents))
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise ValueError("duplicate item") from error

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
'''

CATALOG_MUTANT = CATALOG.replace(
    'raise ValueError("duplicate item") from error',
    'self._connection.execute("UPDATE items SET cents = ? WHERE name = ?", (cents, name))\n            self._connection.commit()',
)

CATALOG_SUPPORT = SUPPORT + r'''
from contextlib import contextmanager
from pathlib import Path
import tempfile
from catalog import Catalog

@contextmanager
def isolated_catalog():
    with tempfile.TemporaryDirectory(prefix="catalog-test-") as directory:
        catalog = None
        try:
            catalog = Catalog.open(Path(directory) / "catalog.sqlite")
            yield catalog
        finally:
            if catalog is not None:
                catalog.close()

@contextmanager
def partial_setup():
    with tempfile.TemporaryDirectory(prefix="catalog-partial-") as directory:
        try:
            Catalog.open(Path(directory) / "catalog.sqlite", fail_after_open=True)
        except RuntimeError:
            yield
        else:
            raise AssertionError("partial setup did not fail")
'''

SLUG_BAD = r'''
def slugify(title):
    if not isinstance(title, str):
        raise ValueError("title")
    return title.strip().lower().replace(" ", "-")
'''

SLUG_REFERENCE = r'''
def slugify(title):
    if not isinstance(title, str):
        raise ValueError("title")
    output = []
    for character in title:
        if character.isascii() and character.isalnum():
            output.append(character.lower())
        elif output and output[-1] != "-":
            output.append("-")
    result = "".join(output).strip("-")
    if not result:
        raise ValueError("title")
    return result
'''

SLUG_MUTANT = r'''
def slugify(title):
    if not isinstance(title, str):
        raise ValueError("title")
    output = []
    for character in title:
        if character.isascii() and character.isalnum():
            output.append(character.lower())
        elif output:
            output.append("-")
    result = "".join(output).strip("-")
    if not result:
        raise ValueError("title")
    return result
'''


CASE_DATA: dict[str, dict[str, Any]] = {
    "price-format": {
        "production": {"pricing.py": PRICE}, "mutant": {"pricing.py": PRICE_MUTANT},
        "spec": """# Price and format contract

`price_cents(quantity, unit_cents)` accepts non-negative `int` values (never
`bool`) and returns their product. `format_price(cents)` accepts a non-negative
`int` (never `bool`) and returns dollars with exactly two decimal digits. Bad
inputs raise `ValueError`. Both functions are stateless.
""",
        "starter": '''import unittest
from pricing import format_price, price_cents
from test_support import suite

@suite("focused", "smoke")
class PriceFormatStarter(unittest.TestCase):
    def test_common_price_and_format(self):
        self.assertEqual(price_cents(3, 125), 375)
        self.assertEqual(format_price(375), "$3.75")
''',
        "testing": """# Running tests

Use `python3 -B run_tests.py --list` to inspect real unittest discovery, and
`--suite focused`, `--suite smoke`, or `--suite full` to run a selection.
`full` is every discovered `test_*.py` test. Mark a test or class with
`test_support.suite("focused", "smoke")` when a shorter selection is useful.
Stateless tests need no setup or teardown.
""",
        "note": PRIOR_NOTE,
        "reference_tests": '''import unittest
from pricing import format_price, price_cents
class Calibration(unittest.TestCase):
    def test_cents_are_zero_padded(self): self.assertEqual(format_price(5), "$0.05")
    def test_price_validates(self):
        with self.assertRaises(ValueError): price_cents(True, 1)
''',
    },
    "sqlite-catalog": {
        "production": {"catalog.py": CATALOG}, "mutant": {"catalog.py": CATALOG_MUTANT},
        "spec": """# SQLite catalog contract

`Catalog.open(path)` creates a SQLite catalog seeded with `bookmark` (125) and
`notebook` (450), after an intentionally simulated 0.15 second startup cost.
`list_items()` returns name/cents pairs sorted by name. `add(name, cents)` takes
a nonblank string and positive `int` (never `bool`), rejects duplicates without
changing their existing value, and raises `ValueError` for bad input. `close()`
is safe to call more than once. `fail_after_open=True` simulates failure after
resource acquisition and must close the acquired connection.
""",
        "starter": '''import unittest
from test_support import isolated_catalog, suite

@suite("focused", "smoke")
class CatalogStarter(unittest.TestCase):
    def test_seeded_items_are_sorted(self):
        with isolated_catalog() as catalog:
            self.assertEqual(catalog.list_items(), [("bookmark", 125), ("notebook", 450)])
''',
        "testing": """# Running tests

Use `python3 -B run_tests.py --list` and the focused, smoke, or full suites.
`full` discovers every `test_*.py` test. `isolated_catalog()` owns a writable
temporary database and closes it. Read-only expectations may share immutable
constants, but tests that mutate a catalog need their own `isolated_catalog()`.
Use `partial_setup()` when checking a setup failure so cleanup remains explicit.
""",
        "note": PRIOR_NOTE,
        "reference_tests": '''import unittest
from pathlib import Path
import tempfile
from catalog import Catalog
class Calibration(unittest.TestCase):
    def test_duplicate_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Catalog.open(Path(directory) / "catalog.sqlite")
            try:
                with self.assertRaises(ValueError): catalog.add("bookmark", 999)
                self.assertIn(("bookmark", 125), catalog.list_items())
            finally: catalog.close()
''',
    },
    "expected-red": {
        "production": {"slug.py": SLUG_BAD}, "mutant": {"slug.py": SLUG_MUTANT},
        "spec": """# Slug contract

`slugify(title)` accepts a nonempty string. ASCII letters become lowercase,
digits remain, and each maximal run of other characters becomes one hyphen;
leading/trailing hyphens are removed. A value with no resulting alphanumeric
characters, or a non-string input, raises `ValueError`.

The checked-in implementation deliberately lacks part of this behavior. This
trial is test authoring only: production must remain unchanged, and a correct
new test may make the current full suite red.
""",
        "starter": '''import unittest
from slug import slugify
from test_support import suite

@suite("focused", "smoke")
class SlugStarter(unittest.TestCase):
    def test_simple_words(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
''',
        "testing": """# Running tests

Use `python3 -B run_tests.py --list` and the focused, smoke, or full suites.
`full` discovers every `test_*.py` test. This is a pure function, so test setup
and teardown are normally unnecessary. Do not change `slug.py`: retain any
behavioral failure that newly authored contract tests expose.
""",
        "note": PRIOR_NOTE,
        "reference_tests": '''import unittest
from slug import slugify
class Calibration(unittest.TestCase):
    def test_punctuation_and_spaces_collapse(self): self.assertEqual(slugify("  A -- B!  "), "a-b")
    def test_empty_result_rejected(self):
        with self.assertRaises(ValueError): slugify(" -- ")
''',
    },
}


def _text(value: str) -> str:
    return dedent(value).lstrip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_text(text), encoding="utf-8")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job(case: str, data: dict[str, Any]) -> str:
    production = ", ".join(data["production"])
    red = "\n\nThis fixture deliberately has missing behavior: a correct new test is expected to make the current implementation fail, and that red result must be retained." if case == "expected-red" else ""
    return f"""# Test-authoring request: {case}

Add adequate tests for `SPEC.md` using current repository conventions. Retain
the tests and useful instructions for running them.

Production ({production}) and `SPEC.md` are immutable. Add or revise tests and
testing guidance only, then record actual results.{red}
"""


def _seed_git(fixture: Path) -> None:
    environment = dict(os.environ)
    environment.setdefault("DEVELOPER_DIR", "/Library/Developer/CommandLineTools")
    commands = (
        ("git", "init", "-b", "main"),
        ("git", "config", "user.name", "ShipLoop repeatable-tests fixture"),
        ("git", "config", "user.email", "fixture@example.invalid"),
        ("git", "add", "."),
        ("git", "commit", "-m", "Seed repeatable test fixture"),
    )
    for command in commands:
        result = subprocess.run(command, cwd=fixture, env=environment, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)


def prepare(case: str, root: Path) -> dict[str, Any]:
    """Materialize one fresh fixture and its worker-external job/calibration data."""
    if case not in CASE_DATA:
        raise ValueError(f"unknown case {case!r}; choose one of {CASES}")
    root = Path(root).resolve()
    data = CASE_DATA[case]
    fixture = root / "fixtures" / case
    job = root / "jobs" / case / "job.md"
    calibration = root / "calibration" / case
    if any(path.exists() for path in (fixture, job, calibration)):
        raise FileExistsError(f"refusing to overwrite prepared case {case}: {root}")
    for name, source in data["production"].items():
        _write(fixture / name, source)
    _write(fixture / "SPEC.md", data["spec"])
    _write(fixture / "test_support.py", CATALOG_SUPPORT if case == "sqlite-catalog" else SUPPORT)
    _write(fixture / "test_starter.py", data["starter"])
    _write(fixture / "TESTING.md", data["testing"])
    _write(fixture / "PRIOR_RUN.md", data["note"])
    _write(fixture / "run_tests.py", RUNNER)
    _seed_git(fixture)
    for name, source in data["production"].items():
        _write(calibration / "reference" / name, source if case != "expected-red" else SLUG_REFERENCE)
    for name, source in data["mutant"].items():
        _write(calibration / "mutant" / name, source)
    _write(calibration / "test_reference.py", data["reference_tests"])
    initial_hashes = {str((fixture / name).resolve()): _hash(fixture / name) for name in data["production"]}
    immutable_hashes = {**initial_hashes, str((fixture / "SPEC.md").resolve()): _hash(fixture / "SPEC.md")}
    commands = {name: ["python3", "-B", "run_tests.py", "--suite", name] for name in ("focused", "smoke", "full")}
    commands["list"] = ["python3", "-B", "run_tests.py", "--list"]
    record = {"case": case, "fixture": str(fixture), "job": str(job), "production_paths": list(initial_hashes), "immutable_paths": list(immutable_hashes), "initial_hashes": initial_hashes, "immutable_hashes": immutable_hashes, "commands": commands}
    _write(job, _job(case, data))
    return record
