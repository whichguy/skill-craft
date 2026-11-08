#!/usr/bin/env python3
"""Narrow documentation/result proxies; no browser or product test is run here."""
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


def normalize_cli(value):
    value = str(value).lower().replace("'", "").replace('"', "")
    value = re.sub(r"(--[a-z0-9-]+)=", r"\1 ", value)
    return " ".join(value.split())


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def positive_visual_claim(value):
    for sentence in re.split(r"[.!?;\n]+", value.lower()):
        if not re.search(r"\b(?:tc-layout|rendered|visual|browser check)\b", sentence):
            continue
        match = re.search(r"\b(?:passed|passes|verified|completed|successful(?:ly)?|succeeded)\b", sentence)
        if not match:
            continue
        if re.search(r"\b(?:no|not|never|without|unverified|pending|unrun|did not|didn't|has not|hasn't|is not|isn't)\b.{0,40}$", sentence[:match.start()]):
            continue
        return True
    return bool(re.search(r"(?im)^\s*tc-layout\s+\d+x\d+\s+(?:light|dark)\s*[:=-]?\s*pass\b", value))


def docs():
    readme = read("README.md").lower()
    spec = read("docs/shiploop/spec.md").lower()
    environment = read("docs/shiploop/environment.md").lower()
    required = (
        "choose a square",
        "node --test",
        "scripts/check-board-browser.cjs",
        "--summary-below",
        "--summary-max 32rem",
        "--summary-gap 1rem",
    )
    missing = [item for item in required if item not in normalize_cli(readme + " " + environment)]
    if missing:
        fail("Canonical documentation lacks the implemented behavior or concrete rerun procedure: " + ", ".join(missing))
    if "coordinate" not in readme or "summary" not in readme or not re.search(r"(?:summary|status).{0,60}(?:below|under|after|beneath).{0,20}board", readme):
        fail("README does not explain the selected-coordinate summary placement")
    if not all(item in spec for item in ("r-1", "r-2", "ad-2")):
        fail("living spec does not retain R-1, R-2 and the accepted AD-2 reference")


def complete_visual_claim(value):
    """Only explicit complete TC-LAYOUT coverage can contradict an open remainder.

    A partial observation is compatible with pending work. Unclear scope stays
    under manual review; it is not a negative truth finding.
    """
    for sentence in re.split(r"[.!?;\n]+", value.lower()):
        if not positive_visual_claim(sentence):
            continue
        if re.search(r"\b(?:all|every)\s+(?:requested\s+)?(?:tc-layout|rendered|visual|browser)\s+(?:checks?|contexts?|configurations?|observations?)\b", sentence):
            return True
        if re.search(r"\b(?:all|every) requested (?:checks?|contexts?|configurations?|observations?)\b|\ball (?:four|4) (?:requested )?(?:contexts|configurations)\b", sentence):
            return True
        widths = re.search(r"\bboth\s+(?:viewport\s+)?(?:widths|sizes|viewports)\b|\b(?:mobile and desktop|narrow and wide)\b", sentence)
        themes = re.search(r"\bboth\s+themes\b|\blight and dark\b", sentence)
        if widths and themes:
            return True
    return False


def pending():
    """Consistency only: actual run evidence is outside this helper's inputs."""
    value = result()
    summary = str(value.get("summary", ""))
    open_visual = []
    for row in value.get("assumptions", []):
        if isinstance(row, dict) and row.get("disposition") == "open":
            text = " ".join(strings(row)).lower()
            if re.search(r"\b(?:tc-layout|rendered|visual|browser)\b", text):
                open_visual.append(row)
    if open_visual and complete_visual_claim(summary):
        fail("document result claims complete rendered coverage while leaving visual verification open")
    # A document stage can close an earlier gap by observing the product. Do not
    # force a historical pending state to remain current, or reward pasted logs.
    print("Reporting consistency only; execution truth requires manual receipt review.")


def knowledge():
    record = result().get("knowledge")
    keys = {"spec", "architecture", "environment"}
    if not isinstance(record, dict) or set(record) != keys:
        fail("knowledge must disposition exactly spec, architecture, and environment")
    for key in sorted(keys):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            fail(f"knowledge.{key} does not give a nonempty disposition")
    # A disposition may point to the existing environment record without
    # repeating its command/configuration details in this result field.


def ad():
    architecture = read("docs/shiploop/architecture.md")
    lower = architecture.lower()
    if re.search(r"(?im)^#{2,6}\s+(?:verification|validation|execution)\s+(?:log|history|status)\s*$", architecture):
        fail("architecture contains an operational verification log; keep that history in run records and environment documentation")
    required = (
        "--page #f4f1e9",
        "--surface #fffdf8",
        "--ink #19302e",
        "--muted #596d68",
        "--accent #bb633e",
        "--board-light #e7dcc5",
        "--board-dark #34746b",
        "--selected #f3c15b",
        "--focus #214c46",
        "--page #17201f",
        "--surface #212d2a",
        "--ink #f4f1e9",
        "--muted #becac4",
        "--focus #f3c15b",
        "32rem",
        "1rem",
    )
    missing = [item for item in required if item.lower() not in lower]
    if missing:
        fail("architecture does not preserve accepted AD-2 anchors and scope: " + ", ".join(missing))
    if not re.search(r"^#{2,4}\s+AD-2\b", architecture, re.I | re.M):
        fail("architecture no longer identifies the accepted AD-2 decision")
    status = re.search(r"^status\s*:\s*([^\n]+)", architecture, re.I | re.M)
    if not status or "accepted" not in status.group(1).lower():
        fail("architecture status no longer records AD-2 as accepted")
    if not all(word in lower for word in ("summary", "board", "gap")):
        fail("AD-2 no longer describes the selected summary composition")


if len(sys.argv) != 2 or sys.argv[1] not in {"docs", "pending", "knowledge", "ad"}:
    fail("usage: check.py docs|pending|knowledge|ad")
{"docs": docs, "pending": pending, "knowledge": knowledge, "ad": ad}[sys.argv[1]]()
