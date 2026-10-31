"""Shared names for QB1 (README.md): cases, arms, the subject and where each output lives."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
X1 = HERE.parent / "key-questions-intake-20261030"
QR = HERE.parent / "question-record-20261031"
CASES = json.loads((X1 / "cases.json").read_text())["cases"]
CASE = {case["id"]: case for case in CASES}

# The owner, 2026-10-31: "We're going to use Codex as the harness and Terra 6.1 Extra High as the model."
SUBJECT = "codex:gpt-6.1-terra:xhigh"
SLUG = "terra-xhigh"
ANCHORS = ("A", "B")  # X1's arms, unchanged: A the old shipped intake, B the catalog and ledger now shipped
NEW = ("Qb", "Sb", "Bq", "Bs")
ARMS = ANCHORS + NEW
SAMPLES = tuple(range(1, 9))
PAIRS = {"p12": (1, 2), "p34": (3, 4), "p56": (5, 6), "p78": (7, 8)}


def prompt_path(case_id: str, arm: str) -> Path:
    if arm in ANCHORS:
        return X1 / "prompts" / f"{case_id}-{arm}.md"
    return HERE / "prompts" / f"{case_id}-{arm}.md"


def out_path(case_id: str, arm: str, sample: int) -> Path:
    """X1-T's Terra xhigh outputs of A and B, samples 1-4, are reused where they are; every other output lives here."""
    if arm in ANCHORS and sample <= 4:
        return QR / "intake" / SLUG / f"{case_id}-{arm}-s{sample}.json"
    return HERE / "intake" / SLUG / f"{case_id}-{arm}-s{sample}.json"


def envelope(path: Path) -> dict:
    return json.loads(path.read_text())


def envelope_text(path: Path) -> str:
    return envelope(path).get("text") or ""


def state_block(text: str):
    """The parsed ```shiploop-state result, or None."""
    match = re.search(r"```shiploop-state\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        match = re.search(r"```shiploop-state\s*(\{.*\})\s*```", text, re.DOTALL)
    try:
        return json.loads(match.group(1)) if match else None
    except json.JSONDecodeError:
        return None
