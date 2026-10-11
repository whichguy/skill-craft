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
from typing import Any, Dict, List, Optional, Sequence

_INT = r"(\d+)"
# How much of an output line a refusal quotes when it shows where an ID sits inside a longer token.  Display only: it
# decides nothing.
INSIDE_CHARS = 100


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
    """unittest: ``Ran 4 tests in 0.01s`` then ``OK (skipped=2)`` or ``FAILED (failures=1)``.

    A module that cannot be imported is reported as one synthetic test (``unittest.loader._FailedTest``) that
    errored, and ``Ran`` and ``errors=`` count it, though no test of that module ran: it is taken out of both.
    """
    ran_lines = re.findall(r"^Ran (\d+) tests? in ", text, re.MULTILINE)
    if not ran_lines:
        if "NO TESTS RAN" in text:
            return {"ran": 0, "failed": 0}
        return None
    unloadable = len(re.findall(r"^ERROR: .*\(unittest\.loader\._FailedTest[.)]", text, re.MULTILINE))
    total = sum(int(value) for value in ran_lines) - unloadable
    skipped = _sum(text, r"\bskipped=" + _INT)
    failed = _sum(text, r"\bfailures=" + _INT) + _sum(text, r"\berrors=" + _INT) - unloadable
    return {"ran": max(total - skipped, 0), "failed": max(failed, 0)}


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
    # ``ok  <package>  0.12s`` or ``(cached)``; TAP's ``ok 1 - title`` is not a Go package line.
    ok_lines = re.findall(r"^ok\s+(?!\d+ - )\S+\s+(?:[\d.]+s|\(cached\)).*$", text, re.MULTILINE)
    empty = re.findall(r"\[no test files\]|\[no tests to run\]|testing: warning: no tests to run", text)
    ran_packages = [line for line in ok_lines if "[no tests to run]" not in line]
    fail_packages = re.findall(r"^FAIL\s+\S+\s+[\d.]+s", text, re.MULTILINE)
    if ran_packages or fail_packages:
        # Package lines give a lower bound: each counted package ran at least one test.
        return {"ran": len(ran_packages) + len(fail_packages), "failed": len(fail_packages)}
    if empty:
        return {"ran": 0, "failed": 0}
    return None


_NODE_FILE_FAILURE = re.compile(r"^(?:\u2716 |not ok \d+ - )(\S+\.[cm]?[jt]s)(?: \(|\s*$)", re.MULTILINE)


def _node(text: str) -> Optional[Dict[str, int]]:
    """``node --test``: spec ``\u2139 tests 4`` or TAP ``# tests 4``, then ``pass``, ``fail`` and ``cancelled`` lines.

    ``skipped`` and ``todo`` tests are in ``tests`` but not in ``pass``, so they are not counted as run.  A test file
    that fails to load is one synthetic failing "test" named by its path (the summary counts it); no test of that
    file ran, so it is taken out of both counts, as ``_unittest`` does.  The ``dot`` and junit reporters print no
    summary and are not guessed.
    """
    totals = {}
    for key in ("tests", "pass", "fail", "cancelled"):
        found = re.findall(r"^(?:\u2139|#) " + key + r" (\d+)\s*$", text, re.MULTILINE)
        if not found:
            return None
        totals[key] = sum(int(value) for value in found)
    unloadable = len(set(_NODE_FILE_FAILURE.findall(text)))
    failed = totals["fail"] + totals["cancelled"]
    return {"ran": max(totals["pass"] + failed - unloadable, 0), "failed": max(failed - unloadable, 0)}


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
    output = _plain(output)
    found: List[str] = []
    ran = failed = 0
    for name, reader in (
        ("jest", _jest), ("vitest", _vitest), ("unittest", _unittest), ("mocha", _mocha),
        ("cargo", _cargo), ("go", _go), ("dotnet", _dotnet), ("node", _node),
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


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _plain(text: str) -> str:
    """Output without terminal colour codes (``FORCE_COLOR``, a TTY runner)."""
    return _ANSI.sub("", text)


# A skipped test is marked by each runner's own syntax, never by a word in a test title: a leading skip glyph (jest
# and vitest, node spec), mocha's pending ``- title``, a trailing ``# SKIP``/``# TODO`` (TAP, node), pytest's
# ``SKIPPED``, unittest's ``... skipped`` and go's ``--- SKIP:``.  ``# Subtest:`` is TAP's announcement of a test,
# printed before its result line, so it shows nothing about the outcome.
_SKIP_LINE = re.compile(
    r"^\s*[○✎﹣↓] |^\s*- |#\s*(?:SKIP|TODO)\b|\bSKIPPED\b|\.\.\. skipped\b|--- SKIP: |\[skipped\]", re.IGNORECASE)
_ANNOUNCEMENT = re.compile(r"^\s*# Subtest:")


def _id_pattern(test_id: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![\w-])" + re.escape(test_id) + r"(?![\w])")


def _inside_pattern(test_id: str) -> "re.Pattern[str]":
    """The longer token that starts with the ID and whose next character begins a new run: ``TC-4a`` for ``TC-4``.

    A digit after a digit (or a letter after a letter) continues the ID's own kind of character, which makes a different
    ID (``TC-10`` is not ``TC-1`` inside a longer token), so only a character of another kind counts.  Group 1 is the
    whole token, so a caller can tell a token that is itself another listed ID (``TC-4a`` beside a listed ``TC-4``).
    """
    last = test_id[-1:]
    new_run = r"[^\W\d]" if last.isdigit() else r"[\d_]" if last.isalpha() else r"\w"
    return re.compile(r"(?<![\w-])(" + re.escape(test_id) + "(?=" + new_run + r")\w+)")


def named(output: str, ids: Sequence[str]) -> Dict[str, Any]:
    """Split declared IDs into ``shown`` (on a non-skip output line) and ``missing``.

    ``inside`` maps each missing ID to the first non-skip line that holds it at the start of a longer token of the same
    word (``TC-4`` inside ``TC-4a``): the ID is printed, but not as its own word, which is what the match requires.  A
    longer token that is itself a listed ID is that ID shown, not the shorter one inside it, so such a line is not
    counted.  An ID that no line holds that way is just absent and has no entry.
    """
    lines = [line for line in _plain(output).splitlines() if not _ANNOUNCEMENT.match(line)]
    text = "\n".join(lines)
    listed = set(ids)
    shown: List[str] = []
    missing: List[str] = []
    inside: Dict[str, str] = {}
    for test_id in ids:
        pattern = _id_pattern(test_id)
        if any(pattern.search(line) and not _SKIP_LINE.search(line) for line in lines):
            shown.append(test_id)
            continue
        missing.append(test_id)
        if test_id not in text:
            continue  # printed nowhere, so no longer token holds it either: no second pass over the lines
        pattern = _inside_pattern(test_id)
        first = next((line.strip() for line in lines
                      if any(match.group(1) not in listed for match in pattern.finditer(line))
                      and not _SKIP_LINE.search(line)), None)
        if first is not None:
            inside[test_id] = first[:INSIDE_CHARS]
    return {"shown": shown, "missing": missing, "inside": inside}


__all__ = ("count", "named")
