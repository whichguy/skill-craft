#!/usr/bin/env python3
"""Narrow checks of the authored plan; no browser is launched here."""
import json
import os
import re
import sys
from pathlib import Path


def fail(message):
    raise SystemExit(message)


path = os.environ.get("STAGE_RESULT")
if not path:
    fail("STAGE_RESULT was not supplied")
value = json.loads(Path(path).read_text())
if isinstance(value, dict) and isinstance(value.get("result"), dict):
    value = value["result"]
if not isinstance(value, dict):
    fail("STAGE_RESULT is not an object")
summary = str(value.get("summary", "")).lower()
cases = {str(row.get("id")): row for row in value.get("test_cases", []) if isinstance(row, dict)}


def text(case_id, field):
    return str(cases.get(case_id, {}).get(field, "")).lower()


def normalize_cli(value):
    value = str(value).lower().replace("'", "").replace('"', "")
    value = re.sub(r"(--[a-z0-9-]+)=", r"\1 ", value)
    return " ".join(value.split())


def has_visual_pass(value):
    for sentence in re.split(r"[.!?;\n]+", value.lower()):
        if not re.search(r"\b(?:tc-layout|rendered|visual|browser check)\b", sentence):
            continue
        match = re.search(r"\b(?:passed|verified|completed|successful)\b", sentence)
        if not match:
            continue
        if re.search(r"\b(?:not|never|without|no|unverified|pending|unrun|did not|didn't|has not|hasn't|is not|isn't)\b.{0,40}$", sentence[:match.start()]):
            continue
        return True
    return False


def layout():
    case = cases.get("TC-LAYOUT")
    if not case:
        fail("TC-LAYOUT is missing")
    if str(case.get("criterion", "")) != "C3":
        fail("TC-LAYOUT must cover criterion C3")
    evidence = normalize_cli(" ".join(text("TC-LAYOUT", field) for field in ("oracle", "red", "green")))
    command = re.search(r"\bnode\s+(?:\./)?scripts/check-board-browser\.cjs\b", evidence)
    locator = ("docs/shiploop/architecture.md" in evidence or "knowledge/architecture.md" in evidence) and "ad-2" in evidence
    required = ("390x844", "1440x1000", "32rem", "1rem", "light", "dark", "equal", "overflow", "focus", "64", "square", "button")
    if not command:
        fail("TC-LAYOUT must name the supplied rendered browser procedure")
    if not locator:
        fail("TC-LAYOUT must link criterion C3 to the accepted AD-2 file and identifier")
    if not re.search(r"(?:below|under|after|beneath)(?: the)? board", evidence):
        fail("TC-LAYOUT must locate the summary in relation to the board")
    missing = [item for item in required if item not in evidence]
    if missing:
        fail("TC-LAYOUT lacks concrete browser observations: " + ", ".join(missing))


def pending():
    if not any(word in summary for word in ("pending", "not run", "unrun", "failed", "failure", "unavailable", "not available")):
        fail("summary does not leave rendered validation pending")
    if has_visual_pass(summary):
        fail("summary claims rendered/browser/visual checks passed")
    try:
        environment = Path("docs/shiploop/environment.md").read_text().lower()
    except OSError as exc:
        fail(f"missing docs/shiploop/environment.md: {exc}")
    if not all(name in environment for name in ("playwright_node_path", "browser_executable_path")):
        fail("environment record omits the supplied browser capability facts")
    if not any(term in text("TC-LAYOUT", "oracle") for term in ("probe", "check the supplied", "confirm the browser route")):
        fail("TC-LAYOUT does not direct a capability probe before relying on the rendered command")


def board():
    # The structured cases own this coverage; a concise summary need not repeat
    # their commands and every observation. layout() owns the rendered count.
    board_case = cases.get("TC-BOARD")
    if not board_case or str(board_case.get("criterion", "")) != "C2" or str(board_case.get("requirement", "")) != "R-2":
        fail("TC-BOARD must retain the C2/R-2 functional regression case")
    if not all(word in text("TC-BOARD", "oracle") for word in ("node --test", "selection", "reset", "coordinate")):
        fail("TC-BOARD does not specify the existing functional regression")
    case = cases.get("TC-SUMMARY")
    if not case or str(case.get("criterion", "")) != "C1":
        fail("TC-SUMMARY must cover criterion C1")
    summary_oracle = text("TC-SUMMARY", "oracle")
    if not all(word in summary_oracle for word in ("node --test", "selected:", "reset", "choose a square")) or not re.search(r"selected:\s*(?:[a-h][1-8]|<coordinate>|coordinate)", summary_oracle):
        fail("TC-SUMMARY does not preserve selected status/reset state assertions")


def honest():
    oracle = text("TC-LAYOUT", "oracle")
    if "TC-LAYOUT" not in cases:
        fail("TC-LAYOUT is missing")
    if re.search(r"node --test.{0,80}(?:assert|check|verify).{0,60}(?:screenshot|render|visual|layout)", oracle):
        fail("TC-LAYOUT assigns rendered observations to the node state-test command")


def local():
    combined = summary + " " + " ".join(
        str(row.get(key, "")).lower()
        for row in cases.values()
        for key in ("oracle", "red", "green")
    )
    if any(word in combined for word in ("cdn", "remote package", "install puppeteer", "install playwright")):
        fail("test plan adds a remote dependency or package installation")


if len(sys.argv) != 2 or sys.argv[1] not in {"layout", "pending", "board", "honest", "local"}:
    fail("usage: check.py layout|pending|board|honest|local")
{"layout": layout, "pending": pending, "board": board, "honest": honest, "local": local}[sys.argv[1]]()
