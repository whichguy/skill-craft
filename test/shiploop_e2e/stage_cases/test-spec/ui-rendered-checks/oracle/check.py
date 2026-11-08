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
    value = re.sub(r"\bnode\s+\./", "node ", value)
    return " ".join(value.split())


def focused_command_contract():
    contract_path = Path(__file__).with_name("contract.json")
    try:
        contract = json.loads(contract_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"missing or invalid oracle command contract: {exc}")
    focused = contract.get("focused_command")
    if not isinstance(focused, dict) or not all(
        focused.get(key) == expected
        for key, expected in (("work_item_id", "W1"), ("stage", "step-plan"), ("id", "TC-LAYOUT"))
    ):
        fail("oracle command contract must identify TC-LAYOUT in W1 step-plan")
    command = normalize_cli(focused.get("command", ""))
    match = re.search(r"\bnode\s+(?:\./)?scripts/check-board-browser\.cjs\b", command)
    if not match:
        fail("recorded TC-LAYOUT command does not identify the supplied rendered procedure")
    runner = match.group(0).replace("node ./scripts", "node scripts")
    return focused, command, runner


def references_recorded_browser_command(value, focused):
    """Resolve a named step-plan command through this case's private contract."""
    value = re.sub(r"\bstep[ -]+plan\b", "step-plan", normalize_cli(value))
    location = all(re.search(rf"\b{re.escape(str(focused[key]).lower())}\b", value)
                   for key in ("work_item_id", "stage"))
    command = re.search(r"\brecorded\s+(?:focused\s+)?browser\s+command\b", value)
    return bool(location and command)


def references_shared_command(value):
    value = normalize_cli(value)
    # The enclosing case already identifies TC-LAYOUT. A shared focused command
    # need not repeat that ID or every setup fact in the same sentence.
    return bool(re.search(r"\bfocused\s+browser\s+command\b", value)
                or re.search(r"\bshared\b.{0,35}\b(?:procedure|command|setup)\b.{0,45}\b(?:summary|above)\b", value))


def has_visual_pass(value):
    for sentence in re.split(r"[.!?;\n]+", value.lower()):
        if not re.search(r"\b(?:tc-layout|rendered|visual|browser check)\b", sentence):
            continue
        match = re.search(r"\b(?:passed|verified|completed|successful)\b", sentence)
        if not match:
            continue
        before = sentence[:match.start()]
        after = sentence[match.end():]
        if re.search(
            r"\b(?:not|never|without|no|unverified|pending|unrun|did not|didn't|has not|hasn't|is not|isn't|will|would|could|should|may|might|if|when|once|after|before|until|unless|expected to|planned to)\b.{0,100}$",
            before,
        ) or re.match(r"\s*(?:if|when|once|unless|assuming|provided that)\b", after):
            continue
        return True
    return False


def layout():
    case = cases.get("TC-LAYOUT")
    if not case:
        fail("TC-LAYOUT is missing")
    if str(case.get("criterion", "")) != "C3":
        fail("TC-LAYOUT must cover criterion C3")
    case_oracle = text("TC-LAYOUT", "oracle")
    summary_text = normalize_cli(summary)
    evidence = normalize_cli(summary + " " + " ".join(text("TC-LAYOUT", field) for field in ("oracle", "red", "green")))
    focused, _, runner = focused_command_contract()
    procedure_in_oracle = runner in normalize_cli(case_oracle) or references_recorded_browser_command(case_oracle, focused)
    procedure_in_summary = runner in summary_text or references_recorded_browser_command(summary, focused)
    shared_context = procedure_in_summary and references_shared_command(case_oracle)
    if not procedure_in_oracle and not shared_context:
        fail("TC-LAYOUT must identify the rendered procedure or refer to its shared recorded W1 browser command")
    # Criterion C3 already carries AD-2 and its file context; do not require a duplicate locator here.
    required = ("390x844", "1440x1000", "32rem", "1rem", "light", "dark", "equal", "overflow", "focus", "square")
    if not re.search(r"(?:below|under|after|beneath)(?: the)? board", evidence):
        fail("TC-LAYOUT must locate the summary in relation to the board")
    missing = [item for item in required if item not in evidence]
    if missing:
        fail("TC-LAYOUT lacks concrete browser observations: " + ", ".join(missing))
    if not re.search(r"\b64\b(?:\s+[\w-]+){0,4}\s+\b(?:controls?|buttons?)\b", evidence):
        fail("TC-LAYOUT must count all 64 rendered controls or buttons")


def claim():
    # The summary reports this stage's status; a GREEN field only defines the future pass condition.
    if has_visual_pass(summary):
        fail("summary claims a completed rendered/browser/visual check in this test-spec result")


def board():
    # The structured cases own this coverage; a concise summary need not repeat
    # their commands and every observation. layout() owns the rendered count.
    board_case = cases.get("TC-BOARD")
    if not board_case or str(board_case.get("criterion", "")) != "C2" or str(board_case.get("requirement", "")) != "R-2":
        fail("TC-BOARD must retain the C2/R-2 functional regression case")
    board_oracle = text("TC-BOARD", "oracle")
    concrete_coordinates = all(re.search(rf"\b{coordinate}\b", board_oracle) for coordinate in ("a1", "h8", "i9"))
    if not all(word in board_oracle for word in ("node --test", "selection", "reset")) or not ("coordinate" in board_oracle or concrete_coordinates):
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


if len(sys.argv) != 2 or sys.argv[1] not in {"layout", "claim", "board", "honest", "local"}:
    fail("usage: check.py layout|claim|board|honest|local")
{"layout": layout, "claim": claim, "board": board, "honest": honest, "local": local}[sys.argv[1]]()
