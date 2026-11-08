#!/usr/bin/env python3
"""Narrow source and result proxies; these do not establish rendered quality."""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path.cwd()


def fail(message):
    raise SystemExit(message)


def read(name):
    try:
        return (ROOT / name).read_text()
    except OSError as exc:
        fail(f"missing {name}: {exc}")


def result():
    path = os.environ.get("STAGE_RESULT")
    if not path:
        fail("STAGE_RESULT was not supplied")
    value = json.loads(Path(path).read_text())
    if isinstance(value, dict) and isinstance(value.get("result"), dict):
        value = value["result"]
    if not isinstance(value, dict):
        fail("STAGE_RESULT is not an object")
    return value


def one_rem(value, css):
    value = value.strip().lower()
    if value == "1rem":
        return True
    variable = re.fullmatch(r"var\(\s*(--[a-z0-9_-]+)\s*\)", value)
    return bool(variable and re.search(re.escape(variable.group(1)) + r"\s*:\s*1rem\b", css, re.I))


def summary_spacing(css, rules):
    for name in ("margin-top", "margin-block-start"):
        match = re.search(r"\b" + name + r"\s*:\s*([^;]+)", rules)
        if match and one_rem(match.group(1), css):
            return True
    margin = re.search(r"\bmargin\s*:\s*([^;]+)", rules)
    if margin and one_rem(margin.group(1).split()[0], css):
        return True
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.S):
        if not re.search(r"(?:main|\.app\w*|\.board[-_\w]*)", selector, re.I):
            continue
        if not re.search(r"\bdisplay\s*:\s*(?:flex|grid)", declarations, re.I):
            continue
        for name in ("gap", "row-gap"):
            match = re.search(r"\b" + name + r"\s*:\s*([^;]+)", declarations, re.I)
            if match and one_rem(match.group(1), css):
                return True
    return False


def design():
    html = read("index.html")
    css = read("styles.css")
    positions = {}
    for name in ("board", "selection-status", "reset"):
        match = re.search(r"\bid\s*=\s*([\"'])" + re.escape(name) + r"\1", html, re.I)
        if not match:
            fail(f"missing {name} control")
        positions[name] = match.start()
    if not (positions["board"] < positions["selection-status"] < positions["reset"]):
        fail("selection status is not in normal DOM order between the board and Reset")
    if not re.search(r"\brole=[\"']status[\"']", html, re.I) or not re.search(r"\baria-live=[\"']polite[\"']", html, re.I):
        fail("selection status is not politely announced")
    status_tag = re.search(r"<[^>]*\bid\s*=\s*([\"'])selection-status\1[^>]*>", html, re.I)
    classes = set()
    if status_tag:
        class_attr = re.search(r"\bclass\s*=\s*([\"'])(.*?)\1", status_tag.group(0), re.I)
        if class_attr:
            classes = set(class_attr.group(2).split())
    status_blocks = []
    for selector_text, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.S):
        selectors = selector_text.split(",")
        if any(
            re.search(r"(?<![\w-])#selection-status(?![\w-])", selector, re.I)
            or any(re.search(r"(?<![\w-])\." + re.escape(name) + r"(?![\w-])", selector) for name in classes)
            or re.search(r"\[\s*role\s*=\s*[\"']?status[\"']?\s*\]", selector, re.I)
            for selector in selectors
        ):
            status_blocks.append(declarations)
    if not status_blocks:
        fail("selection status style is missing")
    rules = " ".join(status_blocks).lower()
    if re.search(r"position\s*:\s*(?:fixed|absolute)", rules):
        fail("selection status is not in normal flow")
    width_is_capped = (
        re.search(r"(?:width|inline-size)\s*:\s*min\(\s*100%\s*,\s*32rem\s*\)", rules)
        or (re.search(r"(?:width|inline-size)\s*:\s*100%", rules)
            and re.search(r"(?:max-width|max-inline-size)\s*:\s*32rem", rules))
    )
    if not width_is_capped:
        fail("selection status has no viewport-shrinking 32rem width")
    if not summary_spacing(css, rules):
        fail("selection status has no 1rem separation from the board")
    if not re.search(r"\.app-shell\s*\{[^}]*max-width\s*:\s*44rem", css, re.S):
        fail("saved 44rem content width is missing")
    board = re.search(r"\.board\s*\{([^}]*)\}", css, re.S)
    if not board or not re.search(r"width\s*:\s*min\(\s*100%\s*,\s*32rem\s*\)", board.group(1)) or not re.search(r"aspect-ratio\s*:\s*1", board.group(1)):
        fail("saved square board width/aspect is missing")
    for name, value in {
        "--page": "#f4f1e9", "--surface": "#fffdf8", "--ink": "#19302e",
        "--muted": "#596d68", "--accent": "#bb633e", "--board-light": "#e7dcc5",
        "--board-dark": "#34746b", "--selected": "#f3c15b", "--focus": "#214c46",
    }.items():
        if not re.search(re.escape(name) + r"\s*:\s*" + re.escape(value), css, re.I):
            fail(f"saved token {name}={value} is missing")
    if "system-ui, sans-serif" not in css:
        fail("saved system font stack is missing")
    if not all(value in css for value in ("#17201f", "#212d2a", "#f4f1e9", "#becac4", "#f3c15b")):
        fail("saved explicit dark theme is missing")


def _text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return ""


def _sentences(value):
    return [part.strip().lower() for part in re.split(r"[.!?;\n]+", value) if part.strip()]


def _positive_visual_claim(value):
    for sentence in _sentences(value):
        if not re.search(r"\b(?:tc-layout|rendered|visual|browser check)\b", sentence):
            continue
        match = re.search(r"\b(?:passed|verified|completed|succeeded|successful)\b", sentence)
        if match:
            prefix = sentence[:match.start()]
            if re.search(r"\b(?:not|never|without|no|unverified|pending|unrun|did not|didn't|has not|hasn't|is not|isn't)\b.{0,40}$", prefix):
                continue
            return True
    return bool(re.search(r"(?im)^\s*tc-layout\s+\d+x\d+\s+(?:light|dark)\s*[:=-]?\s*pass\b", value))


def _browser_evidence(value):
    if "check-board-browser.cjs" not in value.lower():
        return False
    return all(
        re.search(rf"(?im)^\s*tc-layout\s+{viewport}\s+{theme}\s*[:=-]?\s*pass\b", value)
        for viewport in ("390x844", "1440x1000")
        for theme in ("light", "dark")
    )


def visual_truth():
    value = result()
    rows = value.get("not_covered")
    if value.get("outcome") != "done":
        fail("implement result must be done")
    if not isinstance(rows, list):
        fail("implement result must include not_covered, including an empty list after verified coverage")
    visual_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        fields = [str(row.get(key, "")) for key in ("behaviour", "reason", "evidence", "result")]
        if any(word in " ".join(fields).lower() for word in ("visual", "render", "layout", "mobile", "tc-layout")):
            visual_rows.append(fields)
    summary = str(value.get("summary", ""))
    evidence_fields = [_text(value.get(key, "")) for key in (
        "evidence", "notes", "verification", "observations", "test_output",
        "command_output", "browser_output", "rendered_checks", "test_results", "checks",
    )]
    claims = any(_positive_visual_claim(text) for text in [summary, *evidence_fields, *(field for row in visual_rows for field in row)])
    if visual_rows:
        # A not_covered item is open work. Words such as “not verified” and
        # “must pass before acceptance” describe that state, not successful evidence.
        if not claims:
            return
        fail("a not_covered visual item conflicts with an affirmative TC-LAYOUT observation")
    evidence = "\n".join([summary, *evidence_fields])
    if claims and _browser_evidence(evidence):
        return
    fail("rendered verification must remain in not_covered when unrun, or include the browser command and TC-LAYOUT output for each viewport/theme")


def board():
    state = read("src/board-state.mjs")
    ui = read("src/board-ui.mjs")
    tests = read("test/board-state.test.mjs")
    if not all(name in state for name in ("createBoardState", "selectSquare", "resetBoard")):
        fail("existing board state helpers are missing")
    if not re.search(r"selected\s*:\s*null", state) or 'status: "Choose a square"' not in state:
        fail("initial board state or prompt changed")
    if not re.search(r"status:\s*\"Selected:\s*\"\s*\+\s*square", state):
        fail("selected coordinate status changed")
    if 'return { selected: null, status: "Choose a square" }' not in state:
        fail("Reset no longer restores the empty selection state")
    if "row = 8" not in ui or "column < 8" not in ui or "data-square" not in ui:
        fail("the existing 64 square controls are not generated")
    if not all(term in tests for term in ("a1", "resetBoard")):
        fail("existing selection/reset tests are absent")


def local():
    html = read("index.html")
    ui = read("src/board-ui.mjs")
    if re.search(r"(?:src|href)\s*=\s*['\"]https?://", html, re.I):
        fail("page adds a remote script or asset")
    if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket)\b", ui):
        fail("board UI adds a network request")


if len(sys.argv) != 2 or sys.argv[1] not in {"design", "visual-truth", "board", "local"}:
    fail("usage: check.py design|visual-truth|board|local")
{"design": design, "visual-truth": visual_truth, "board": board, "local": local}[sys.argv[1]]()
