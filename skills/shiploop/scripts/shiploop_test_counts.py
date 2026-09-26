"""Read how many tests a recorded command actually ran, from its own output.

A test command that exits 0 after selecting nothing (``npm test -- -t <filter>``
matching no name, ``pytest -k`` deselecting everything, ``go test -run`` with no
match) is not passing evidence.  ``count`` recognises the summaries of common
runners and returns the executed total; ``named`` reports which declared test
IDs appear on a line that is not a skip line.  Unrecognised output returns
``None`` rather than a guess, and the caller decides what an uncounted run may
prove.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

_INT = r"(\d+)"


def _sum(text: str, pattern: str) -> int:
    return sum(int(match) for match in re.findall(pattern, text))


def _jest(text: str) -> Optional[Dict[str, int]]:
    """Jest: ``Tests:       1 failed, 2 skipped, 3 passed, 6 total`` (one line per run)."""
    lines = re.findall(r"^\s*Tests:\s+(.*\d+ total.*)$", text, re.MULTILINE)
    if not lines:
        if re.search(r"^No tests found", text, re.MULTILINE):
            return {"ran": 0, "failed": 0}
        return None
    ran = failed = 0
    for line in lines:
        failed += _sum(line, _INT + r" failed")
        ran += _sum(line, _INT + r" failed") + _sum(line, _INT + r" passed")
    return {"ran": ran, "failed": failed}


def _vitest(text: str) -> Optional[Dict[str, int]]:
    """Vitest: ``      Tests  1 failed | 3 passed | 2 skipped (6)``."""
    lines = re.findall(r"^\s*Tests\s{2,}(.*\(\d+\))\s*$", text, re.MULTILINE)
    if not lines:
        if re.search(r"No test files found", text):
            return {"ran": 0, "failed": 0}
        return None
    ran = failed = 0
    for line in lines:
        failed += _sum(line, _INT + r" failed")
        ran += _sum(line, _INT + r" failed") + _sum(line, _INT + r" passed")
    return {"ran": ran, "failed": failed}


_PYTEST_SUMMARY = re.compile(
    r"^=*\s*((?:\d+ (?:passed|failed|skipped|deselected|errors?|xfailed|xpassed|warnings?)"
    r"(?:, )?)+) in [\d.]+s", re.MULTILINE)


def _pytest(text: str, exit_code: Optional[int]) -> Optional[Dict[str, int]]:
    """pytest: ``==== 3 passed, 1 skipped in 0.12s ====``, ``no tests ran`` or exit 5."""
    summaries = _PYTEST_SUMMARY.findall(text)
    if summaries:
        line = summaries[-1]
        failed = _sum(line, _INT + r" failed")
        ran = failed + _sum(line, _INT + r" passed") + _sum(line, _INT + r" xfailed") + _sum(line, _INT + r" xpassed")
        return {"ran": ran, "failed": failed}
    if exit_code == 5 or re.search(r"^=*\s*no tests ran in [\d.]+s", text, re.MULTILINE):
        return {"ran": 0, "failed": 0}
    return None


def _unittest(text: str) -> Optional[Dict[str, int]]:
    """unittest: ``Ran 4 tests in 0.01s`` then ``OK (skipped=2)`` or ``FAILED (failures=1)``."""
    ran_lines = re.findall(r"^Ran (\d+) tests? in ", text, re.MULTILINE)
    if not ran_lines:
        if "NO TESTS RAN" in text:
            return {"ran": 0, "failed": 0}
        return None
    total = sum(int(value) for value in ran_lines)
    skipped = _sum(text, r"\bskipped=" + _INT)
    failed = _sum(text, r"\bfailures=" + _INT) + _sum(text, r"\berrors=" + _INT)
    return {"ran": max(total - skipped, 0), "failed": failed}


def _mocha(text: str) -> Optional[Dict[str, int]]:
    """Mocha: ``  3 passing (12ms)`` and ``  1 failing``."""
    passing = re.findall(r"^\s*(\d+) passing \(", text, re.MULTILINE)
    if not passing:
        return None
    failed = _sum(text, r"(?m)^\s*" + _INT + r" failing\b")
    return {"ran": sum(int(value) for value in passing) + failed, "failed": failed}


def _cargo(text: str) -> Optional[Dict[str, int]]:
    """cargo test: ``test result: ok. 3 passed; 0 failed; 1 ignored; 0 measured; 2 filtered out``."""
    results = re.findall(r"^test result: \w+\. (\d+) passed; (\d+) failed;", text, re.MULTILINE)
    if not results:
        return None
    failed = sum(int(fail) for _passed, fail in results)
    return {"ran": sum(int(passed) for passed, _fail in results) + failed, "failed": failed}


def _go(text: str) -> Optional[Dict[str, int]]:
    """go test: ``--- PASS``/``--- FAIL`` lines with -v, else per-package ``ok`` lines."""
    verdicts = re.findall(r"^\s*--- (PASS|FAIL): ", text, re.MULTILINE)
    if verdicts:
        failed = verdicts.count("FAIL")
        return {"ran": len(verdicts), "failed": failed}
    ok_lines = re.findall(r"^ok\s+\S+\s+.*$", text, re.MULTILINE)
    empty = re.findall(r"\[no test files\]|\[no tests to run\]|testing: warning: no tests to run", text)
    ran_packages = [line for line in ok_lines if "[no tests to run]" not in line]
    fail_packages = re.findall(r"^FAIL\s+\S+\s+[\d.]+s", text, re.MULTILINE)
    if ran_packages or fail_packages:
        # Package lines give a lower bound: each counted package ran at least one test.
        return {"ran": len(ran_packages) + len(fail_packages), "failed": len(fail_packages)}
    if empty:
        return {"ran": 0, "failed": 0}
    return None


def _dotnet(text: str) -> Optional[Dict[str, int]]:
    """dotnet test: ``Passed!  - Failed: 0, Passed: 3, Skipped: 0, Total: 3`` or ``No test matches``."""
    rows = re.findall(r"Failed:\s+(\d+), Passed:\s+(\d+), Skipped:\s+\d+, Total:\s+\d+", text)
    if rows:
        failed = sum(int(fail) for fail, _passed in rows)
        return {"ran": failed + sum(int(passed) for _fail, passed in rows), "failed": failed}
    if re.search(r"No test matches the given testcase filter|No test is available in", text):
        return {"ran": 0, "failed": 0}
    return None


def count(output: str, exit_code: Optional[int]) -> Optional[Dict[str, object]]:
    """Return ``{"ran", "failed", "runners"}`` summed over every recognised runner, or ``None``."""
    found: List[str] = []
    ran = failed = 0
    for name, reader in (
        ("jest", _jest), ("vitest", _vitest), ("unittest", _unittest), ("mocha", _mocha),
        ("cargo", _cargo), ("go", _go), ("dotnet", _dotnet),
    ):
        result = reader(output)
        if result is not None:
            found.append(name)
            ran += result["ran"]
            failed += result["failed"]
    result = _pytest(output, exit_code if not found else None)
    if result is not None:
        found.append("pytest")
        ran += result["ran"]
        failed += result["failed"]
    if not found:
        return None
    return {"ran": ran, "failed": failed, "runners": found}


_SKIP_LINE = re.compile(r"\bskipped\b|\bskip\b|\bSKIP\b|\bpending\b|\bdeselected\b|\btodo\b|○|✎", re.IGNORECASE)


def _id_pattern(test_id: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![\w-])" + re.escape(test_id) + r"(?![\w])")


def named(output: str, ids: Sequence[str]) -> Dict[str, List[str]]:
    """Split declared IDs into ``shown`` (on a non-skip output line) and ``missing``."""
    lines = output.splitlines()
    shown: List[str] = []
    missing: List[str] = []
    for test_id in ids:
        pattern = _id_pattern(test_id)
        if any(pattern.search(line) and not _SKIP_LINE.search(line) for line in lines):
            shown.append(test_id)
        else:
            missing.append(test_id)
    return {"shown": shown, "missing": missing}


__all__ = ("count", "named")
