"""Shared names for the question-record experiments (README.md): cases, subjects, where each output lives."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
X1 = HERE.parent / "key-questions-intake-20261030"
SKILL_SCRIPTS = HERE.parents[2] / "skills" / "shiploop" / "scripts"
CASES = json.loads((X1 / "cases.json").read_text())["cases"]
CASE = {case["id"]: case for case in CASES}

# slug -> the SUBJECT run.py understands
SUBJECTS = {"terra": "codex:gpt-6.1-terra:high"}  # the owner, 2026-10-31: "Focus using Terra 6.1 high for now"
SAMPLES = (1, 2, 3, 4)


def intake_out(slug: str, case_id: str, arm: str, sample: int) -> Path:
    """Sonnet's samples 1 and 2 are X1's own outputs; every other intake output lives here."""
    if slug == "sonnet" and sample in (1, 2):
        return X1 / "outputs" / f"{case_id}-{arm}-s{sample}.json"
    return HERE / "intake" / slug / f"{case_id}-{arm}-s{sample}.json"


def envelope_text(path: Path) -> str:
    return json.loads(path.read_text()).get("text") or ""


def state_block(text: str):
    """The parsed ```shiploop-state result, or None."""
    match = re.search(r"```shiploop-state\s*(\{.*?\})\s*```", text, re.S)
    if not match:
        match = re.search(r"```shiploop-state\s*(\{.*\})\s*```", text, re.S)
    try:
        return json.loads(match.group(1)) if match else None
    except json.JSONDecodeError:
        return None


def spec_block(text: str) -> str:
    """The ```spec.md block a spec output writes, or the text before its result block when the fence is missing."""
    match = re.search(r"```spec\.md\s*\n(.*?)\n```(?=\s*(?:```shiploop-state|$))", text, re.S)
    if match:
        return match.group(1)
    match = re.search(r"```spec\.md\s*\n(.*)```shiploop-state", text, re.S)
    if match:
        return match.group(1).rstrip().removesuffix("```")
    head = text.split("```shiploop-state")[0]
    return head
