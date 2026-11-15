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
from typing import Any, Dict, List, Optional, Sequence, Tuple

_INT = r"(\d+)"
# How much of an output line a refusal quotes when it shows where an ID sits inside a longer token.  Display only: it
# decides nothing.
INSIDE_CHARS = 100


def _sum_matches(text: str, pattern: str) -> int:
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
        failed += _sum_matches(line, _INT + r" failed")
        ran += _sum_matches(line, _INT + r" failed") + _sum_matches(line, _INT + r" passed")
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
        failed += _sum_matches(line, _INT + r" failed")
        ran += _sum_matches(line, _INT + r" failed") + _sum_matches(line, _INT + r" passed")
    return {"ran": ran, "failed": failed}


_PYTEST_SUMMARY = re.compile(
    r"^=*\s*((?:\d+ (?:passed|failed|skipped|deselected|errors?|xfailed|xpassed|warnings?)"
    r"(?:, )?)+) in [\d.]+s", re.MULTILINE)


def _pytest(text: str, exit_code: Optional[int]) -> Optional[Dict[str, int]]:
    """pytest: ``==== 3 passed, 1 skipped in 0.12s ====``, ``no tests ran`` or exit 5."""
    summaries = _PYTEST_SUMMARY.findall(text)
    if summaries:
        line = summaries[-1]
        failed = _sum_matches(line, _INT + r" failed")
        ran = failed + _sum_matches(line, _INT + r" passed") + _sum_matches(line, _INT + r" xfailed") + _sum_matches(line, _INT + r" xpassed")
        # Summary errors may be setup/collection failures: they fail the run, but
        # cannot certify that another test executed.
        failed += _sum_matches(line, _INT + r" errors?\b")
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
    skipped = _sum_matches(text, r"\bskipped=" + _INT)
    failed = _sum_matches(text, r"\bfailures=" + _INT) + _sum_matches(text, r"\berrors=" + _INT) - unloadable
    return {"ran": max(total - skipped, 0), "failed": max(failed, 0)}


def _mocha(text: str) -> Optional[Dict[str, int]]:
    """Mocha: ``  3 passing (12ms)`` and ``  1 failing``."""
    passing = re.findall(r"^\s*(\d+) passing \(", text, re.MULTILINE)
    if not passing:
        return None
    failed = _sum_matches(text, r"(?m)^\s*" + _INT + r" failing\b")
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


# A TAP test point (``ok 3 - title``, ``not ok 4 title``) and what follows its ``ok``; the plan line ``1..N``, which may
# carry a ``# reason``; a test point or plan indented at all (TAP 14 nests a subtest four spaces in and leaves any other
# indent outside the stream, so either way the stream is not one flat stream); a YAML diagnostic block, from an
# indented ``---`` to its ``...``; and TAP's ``Bail out!``, which ends the run early.
_TAP_POINT = re.compile(r"^(not )?ok\b(.*)$")
_TAP_POINT_LINE = re.compile(r"^\s*(?:not )?ok\b(.*)$")
_TAP_PLAN = re.compile(r"^1\.\.(\d+)(?:\s+#.*)?\s*$")
_TAP_NUMBER = re.compile(r" (\d+)\b")
_TAP_INDENTED = re.compile(r"^\s+(?:(?:not )?ok\b|1\.\.\d+)")
_TAP_YAML_START = re.compile(r"^\s+---\s*$")
_TAP_YAML_END = re.compile(r"^\s+\.\.\.\s*$")
_TAP_BAIL = re.compile(r"^bail out!", re.IGNORECASE)
_TAP_DIRECTIVE = re.compile(r"#\s*(?:SKIP|TODO)\S*(?:\s|$)", re.IGNORECASE)


def _tap_directive(rest: str) -> bool:
    """Whether a TAP test point carries a SKIP or TODO directive, read as TAP 14 defines it.

    ``rest`` is the point's text after ``ok`` / ``not ok``.  The directive starts at the first unescaped ``#`` that
    follows whitespace, and is ``SKIP`` or ``TODO`` with any suffix (``# skipped``, ``# todo later``) in any case.
    ``\\#`` is a ``#`` of the description and ``\\\\`` a backslash, so neither starts a directive.
    """
    index = 0
    while index < len(rest):
        char = rest[index]
        if char == "\\":
            index += 2
            continue
        if char == "#" and index and rest[index - 1].isspace():
            return _TAP_DIRECTIVE.match(rest, index) is not None
        index += 1
    return False


def _tap(text: str) -> Optional[Dict[str, int]]:
    """A plain TAP stream: ``1..9`` and nine ``ok N name`` lines (a runner's ``tap`` result format, mocha's tap
    reporter).

    ShipLoop reads one flat stream: exactly one plan, before every test point or after them all, and points numbered
    1..N in order, so the plan the producer declared is checked against the points it printed.  A point whose
    directive is SKIP or TODO (``_tap_directive``) did not run and its ``not ok`` is no failure.  Comments, blank lines,
    ``TAP version`` and YAML diagnostic blocks are skipped.  Any other shape is not read (``None``, the caller decides
    what an uncounted run may prove): points with no number or out of order, an indented point or plan, nested or not
    (counting only the top level would undercount a stream whose tests are its leaves), a second plan or one in the
    middle, a point count the plan does not declare, and a ``Bail out!``.  ``1..0`` reads as zero tests.
    """
    plans: List[Tuple[int, int]] = []
    points: List[Tuple[int, "re.Match[str]"]] = []
    in_yaml = False
    for index, line in enumerate(text.splitlines()):
        if in_yaml:
            in_yaml = not _TAP_YAML_END.match(line)
            continue
        if _TAP_YAML_START.match(line):
            in_yaml = True
            continue
        if _TAP_BAIL.match(line) or _TAP_INDENTED.match(line):
            return None
        plan = _TAP_PLAN.match(line)
        if plan:
            plans.append((index, int(plan.group(1))))
            continue
        point = _TAP_POINT.match(line)
        if point:
            points.append((index, point))
    if len(plans) != 1 or len(points) != plans[0][1]:
        return None
    where = plans[0][0]
    if points and points[0][0] < where < points[-1][0]:
        return None
    ran = failed = 0
    for expected, (_index, point) in enumerate(points, 1):
        number = _TAP_NUMBER.match(point.group(2))
        if number is None or int(number.group(1)) != expected:
            return None
        if _tap_directive(point.group(2)):
            continue
        ran += 1
        failed += point.group(1) is not None
    return {"ran": ran, "failed": failed}


# The reader table: every runner whose summary ``count`` reads, in the order it tries them.  Then pytest, whose reader
# also guesses from exit status 5 ("no tests collected"), and plain TAP: a declared plan checked against its points is
# evidence, so TAP is read before that guess, but only when no runner's own summary matched (``node --test`` prints
# TAP lines beside its ``# tests``, ``# pass``, ``# fail`` and ``# cancelled`` totals, which its own reader counts;
# mocha's tap reporter prints no ``# cancelled`` line, so its stream is read here).  RUNNERS is generated from these, and the text that names the runners
# ShipLoop reads prints RUNNERS, so the list cannot drift from the code.
READERS = (
    ("jest", _jest), ("vitest", _vitest), ("unittest", _unittest), ("mocha", _mocha),
    ("cargo", _cargo), ("go", _go), ("dotnet", _dotnet), ("node", _node),
)
RUNNERS = ", ".join([name for name, _reader in READERS] + ["pytest", "tap"])


def count(output: str, exit_code: Optional[int]) -> Optional[Dict[str, object]]:
    """Return ``{"ran", "failed", "runners"}`` summed over every recognised runner, or ``None``.

    Every runner whose own summary matched is summed (pytest's summary line or its ``no tests ran`` included).  When none
    matched, a TAP stream is read, and only then pytest's exit-status-5 guess.
    """
    output = _plain(output)
    found: List[Tuple[str, Dict[str, int]]] = []
    for name, reader in READERS:
        result = reader(output)
        if result is not None:
            found.append((name, result))
    result = _pytest(output, None)
    if result is not None:
        found.append(("pytest", result))
    if not found:
        result = _tap(output)
        if result is not None:
            found.append(("tap", result))
    if not found:
        result = _pytest(output, exit_code)
        if result is not None:
            found.append(("pytest", result))
    if not found:
        return None
    return {"ran": sum(result["ran"] for _name, result in found), "failed": sum(result["failed"] for _name, result in found),
            "runners": [name for name, _result in found]}


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _plain(text: str) -> str:
    """Output without terminal colour codes (``FORCE_COLOR``, a TTY runner)."""
    return _ANSI.sub("", text)


# A skipped test is marked by each runner's own syntax, never by a word in a test title: a leading skip glyph (jest
# and vitest, node spec), mocha's pending ``- title``, a trailing ``# SKIP``/``# TODO`` (node's spec reporter), pytest's
# ``SKIPPED``, unittest's ``... skipped`` and go's ``--- SKIP:``.  A TAP test point is read by its own directive
# instead (``_skip_line``, the TAP 14 rule ``_tap`` counts by).  ``# Subtest:`` is TAP's announcement of a test,
# printed before its result line, so it shows nothing about the outcome.
_SKIP_LINE = re.compile(
    r"^\s*[○✎﹣↓] |^\s*- |#\s*(?:SKIP|TODO)\b|\bSKIPPED\b|\.\.\. skipped\b|--- SKIP: |\[skipped\]", re.IGNORECASE)
_ANNOUNCEMENT = re.compile(r"^\s*# Subtest:")


def _skip_line(line: str) -> bool:
    """Whether an output line marks the test it names as not run.  A TAP test point (``ok 3 - title``, indented or not)
    is read by its own directive, the one rule ``_tap`` counts by, so a count and the IDs it shows agree; every other line
    by the runner marks of ``_SKIP_LINE``."""
    point = _TAP_POINT_LINE.match(line)
    return _tap_directive(point.group(1)) if point else _SKIP_LINE.search(line) is not None


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
        if any(pattern.search(line) and not _skip_line(line) for line in lines):
            shown.append(test_id)
            continue
        missing.append(test_id)
        if test_id not in text:
            continue  # printed nowhere, so no longer token holds it either: no second pass over the lines
        pattern = _inside_pattern(test_id)
        first = next((line.strip() for line in lines
                      if any(match.group(1) not in listed for match in pattern.finditer(line))
                      and not _skip_line(line)), None)
        if first is not None:
            inside[test_id] = first[:INSIDE_CHARS]
    return {"shown": shown, "missing": missing, "inside": inside}


# A runner's own mark that one test passed or failed, on the line that names it: spec, TAP, verbose unittest and
# pytest, go -v, cargo, mocha, jest and vitest, dotnet.  A failure mark wins over a pass mark for the same ID (a failing
# test is often printed twice: in the run and again in the failure summary).
_PASS_LINE = re.compile(
    r"^\s*(?:[\u2713\u2714\u221a]\s|ok \d+\b)|\.\.\.\s*ok\s*$|\bPASSED\b|--- PASS: |^\s*Passed\s")
_FAIL_LINE = re.compile(
    r"^\s*(?:[\u2717\u2715\u2716\u00d7]\s|not ok \d+\b|\d+\) |\u25cf |(?:FAIL|ERROR):? )"
    r"|\.\.\.\s*(?:FAIL|ERROR|FAILED)\s*$|\bFAILED\b|--- FAIL: |^\s*Failed\s")
# unittest without -v prints ``FAIL: test_x (module.Case.test_x)`` and the docstring (where the ID is) on the next line.
_FAIL_HEADER = re.compile(r"^(?:FAIL|ERROR): ")


def outcomes(output: str, ids: Sequence[str]) -> Dict[str, str]:
    """Per declared ID, what the output says about that one test: ``failed``, ``passed``, ``shown`` or ``missing``.

    Built on ``named``'s line rule: only a non-skip line holding the ID as its own word counts.  ``failed`` when such a
    line carries the runner's failure mark (or follows unittest's ``FAIL:``/``ERROR:`` header), else ``passed`` when one
    carries its pass mark, else ``shown`` (named, but no line says how it ended: a reporter that marks no outcome), and
    ``missing`` when no line names it (it did not run, or the file holding it failed to load).
    """
    lines = [line for line in _plain(output).splitlines() if not _ANNOUNCEMENT.match(line)]
    result: Dict[str, str] = {}
    for test_id in ids:
        pattern = _id_pattern(test_id)
        hits = [index for index, line in enumerate(lines) if pattern.search(line) and not _skip_line(line)]
        if not hits:
            result[test_id] = "missing"
        elif any(_FAIL_LINE.search(lines[index]) or (index and _FAIL_HEADER.match(lines[index - 1]))
                 for index in hits):
            result[test_id] = "failed"
        elif any(_PASS_LINE.search(lines[index]) for index in hits):
            result[test_id] = "passed"
        else:
            result[test_id] = "shown"
    return result


__all__ = ("count", "named", "outcomes")
