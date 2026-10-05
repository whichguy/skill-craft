"""adversarial-review: have an independent model try to break a proposed change, as testable findings.

Composes rubric-eval's `call` (one isolated model call) rather than launching models itself.
Output contract: findings.json (references/findings.schema.json), consumed by rubric-eval experiments.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC_EVAL = HERE.parents[1] / "rubric-eval" / "scripts"
SEVERITIES = ("high", "medium", "low")
CATEGORIES = ("regression", "overreach", "untested-case", "measurement", "wording", "scope")
EXPERIMENTS = ("scenario", "arm", "metric", "judge")

PROMPT = """You are an adversarial reviewer. Your job is to find how the proposed change below could make things worse, or how the evidence for it could be wrong. Do not praise it and do not rewrite it.

Change: {name}

What changes:
<<<
{change}
>>>

Evidence offered for it:
<<<
{evidence}
>>>

Look for: regressions on criteria the evidence did not measure; overreach (the change applying where it should not); untested cases (scenarios, runtimes or inputs the evidence does not cover); measurement problems (judge bias, sample size, condition mismatches, a baseline that is not comparable); wording that a model could misread; scope the change adds.

For each finding, say whether an experiment could test it, and if so describe the smallest experiment and the observable result that would refute your claim. Report at most {max} findings, the strongest first. If you find nothing substantive, return an empty list.

Return only JSON:
{{"findings": [{{"id": "F1", "claim": "...", "severity": "high|medium|low", "category": "regression|overreach|untested-case|measurement|wording|scope", "evidence": "...", "testable": true, "experiment": {{"type": "scenario|arm|metric|judge", "description": "...", "success": "..."}}}}]}}
"""


def build_prompt(name: str, change: str, evidence: str, max_findings: int = 8) -> str:
    return (PROMPT.replace("{name}", name).replace("{change}", change).replace("{evidence}", evidence)
            .replace("{max}", str(max_findings)).replace("{{", "{").replace("}}", "}"))


def validate(doc: dict) -> list[str]:
    """Return schema problems (empty when valid)."""
    errs = []
    for k in ("change", "reviewer", "findings"):
        if k not in doc:
            errs.append(f"missing {k}")
    for i, f in enumerate(doc.get("findings", [])):
        where = f"findings[{i}]"
        for k in ("id", "claim", "severity", "category", "testable"):
            if k not in f:
                errs.append(f"{where}: missing {k}")
        if not re.fullmatch(r"F\d+", str(f.get("id", ""))):
            errs.append(f"{where}: id must look like F1")
        if f.get("severity") not in SEVERITIES:
            errs.append(f"{where}: severity must be one of {SEVERITIES}")
        if f.get("category") not in CATEGORIES:
            errs.append(f"{where}: category must be one of {CATEGORIES}")
        if f.get("testable") is True:
            e = f.get("experiment") or {}
            if e.get("type") not in EXPERIMENTS or not e.get("description") or not e.get("success"):
                errs.append(f"{where}: a testable finding needs experiment.type/description/success")
    return errs


def parse(output: str) -> dict | None:
    m = re.search(r"\{.*\}", output or "", re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def review(name: str, change: str, evidence: str, reviewer: str, *, max_findings: int = 8, attempts: int = 3) -> dict:
    sys.path.insert(0, str(RUBRIC_EVAL))
    try:
        import rubric_eval
    except ImportError:
        raise SystemExit(f"adversarial-review: needs the rubric-eval skill beside it ({RUBRIC_EVAL})")
    prompt = build_prompt(name, change, evidence, max_findings)
    for _ in range(attempts):
        doc = parse(rubric_eval.call(reviewer, prompt, timeout=900))
        if doc is None:
            continue
        doc = {"change": name, "reviewer": reviewer, "findings": doc.get("findings", [])}
        if not validate(doc):
            return doc
    raise SystemExit("adversarial-review: the reviewer did not return valid findings after retries")


def to_markdown(doc: dict) -> str:
    lines = [f"# Adversarial review: {doc['change']}", "", f"Reviewer: {doc['reviewer']}", ""]
    if not doc["findings"]:
        lines.append("No substantive findings.")
    for f in doc["findings"]:
        lines.append(f"- **{f['id']} ({f['severity']}, {f['category']})** {f['claim']}")
        if f.get("testable") and f.get("experiment"):
            e = f["experiment"]
            lines.append(f"  - Experiment ({e['type']}): {e['description']} Refuted if: {e['success']}")
        elif not f.get("testable"):
            lines.append("  - Not testable by experiment; decide by judgement and record the reason.")
    return "\n".join(lines) + "\n"
