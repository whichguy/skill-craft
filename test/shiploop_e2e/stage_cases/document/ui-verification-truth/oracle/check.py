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
    summary = str(result().get("summary", "")).lower()
    required = (
        "choose a square",
        "node --test",
        "scripts/check-board-browser.cjs",
        "--summary-below",
        "--summary-max 32rem",
        "--summary-gap 1rem",
    )
    missing = [item for item in required if item not in normalize_cli(readme)]
    if missing:
        fail("README lacks the implemented behavior or concrete rerun procedure: " + ", ".join(missing))
    if "coordinate" not in readme or "summary" not in readme or not re.search(r"(?:summary|status).{0,60}(?:below|under|after|beneath).{0,20}board", readme):
        fail("README does not explain the selected-coordinate summary placement")
    if not all(item in spec for item in ("r-1", "r-2", "ad-2")):
        fail("living spec does not retain R-1, R-2 and the accepted AD-2 reference")
    if "node --test" not in summary or not re.search(r"\b(?:passed|passing|successful|green)\b", summary):
        fail("document result does not report the seeded node --test rerun as passing")


def pending():
    architecture = read("docs/shiploop/architecture.md").lower()
    environment = read("docs/shiploop/environment.md").lower()
    readme = read("README.md").lower()
    value = result()
    summary = str(value.get("summary", "")).lower()
    combined = readme + " " + summary
    required = ("tc-layout",)
    missing = [item for item in required if item not in combined]
    if missing:
        fail("documentation does not preserve the historical rendered-check gap: " + ", ".join(missing))
    if not any(term in combined for term in ("pending", "not run", "unrun", "failed", "failure", "unavailable", "not available")):
        fail("documentation does not retain an open/failed implementation-stage rendered disposition")
    no_observation = (
        re.search(r"\b(?:no|not|without|did not|never|none)\b.{0,50}\b(?:product )?browser\b.{0,50}\bobserv", combined)
        or re.search(r"\bbrowser\b.{0,50}\bobserv\w*\b.{0,50}\b(?:not|never|absent)", combined)
    )
    if not no_observation:
        fail("documentation does not distinguish the historical browser gap from a product observation")
    if not any(word in environment for word in ("playwright", "browser", "capability")):
        fail("environment record omits the browser capability context")
    # Keep fields and evidence lines separate so pending wording in another
    # field cannot negate a positive claim or manufacture a browser output row.
    evidence_parts = [*strings(value), architecture, readme]
    evidence_text = "\n".join(evidence_parts)
    output = normalize_cli(evidence_text)
    anchors = (
        "node scripts/check-board-browser.cjs",
        "--light-page #f4f1e9",
        "--dark-page #17201f",
        "--square-a #e7dcc5",
        "--square-b #34746b",
        "--board-max 32rem",
        "--focus-color #214c46",
        "--dark-focus-color #f3c15b",
        "--dark-class theme-dark",
        "--summary-below",
        "--summary-max 32rem",
        "--summary-gap 1rem",
    )
    rendered_output = all(anchor in output for anchor in anchors) and all(
        re.search(rf"(?im)^\s*tc-layout\s+{viewport}\s+{theme}\s*[:=-]?\s*pass\b", evidence_text)
        for viewport in ("390x844", "1440x1000")
        for theme in ("light", "dark")
    )
    claims_pass = any(positive_visual_claim(part) for part in evidence_parts)
    if claims_pass and not rendered_output:
        fail("documentation claims a rendered pass without the saved browser command and concrete viewport/theme output")


def knowledge():
    record = result().get("knowledge")
    keys = {"spec", "architecture", "environment"}
    if not isinstance(record, dict) or set(record) != keys:
        fail("knowledge must disposition exactly spec, architecture, and environment")
    for key in sorted(keys):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip() or key + ".md" not in value.lower():
            fail(f"knowledge.{key} does not name its living file and disposition")
    # A disposition may point to the existing environment record without
    # repeating its command/configuration details in this result field.


def ad():
    architecture = read("docs/shiploop/architecture.md")
    lower = architecture.lower()
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
