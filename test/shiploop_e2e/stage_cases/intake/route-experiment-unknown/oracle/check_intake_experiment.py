"""Deterministic oracle for intake/route-experiment-unknown."""
import json
import os
import re
import sys
from pathlib import Path

EXPECTED_CATEGORIES = [f"K{i}" for i in range(1, 13)]
REQUIRED_Q_FIELDS = ("id", "category", "question", "changes", "route", "default", "blocks")
RUNTIME_TOPIC_RE = re.compile(
    r"\b(legacy[- ]batch|runtime|limit|cap|chunk|multiline|newline|batch|export|behavior|handle)\b",
    re.I,
)
PERSON_RUNTIME_RE = re.compile(
    r"\b(legacy[- ]batch|payload limit|batch cap|multiline|newline)\b",
    re.I,
)
SENTENCE_RE = re.compile(r"\bS\d+\b")


def fail(msg: str) -> None:
    raise SystemExit(msg)


def load_result() -> dict:
    path = os.environ.get("STAGE_RESULT")
    if not path:
        fail("STAGE_RESULT is not set")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("result must be a JSON object")
    return data


def check_p1(result: dict) -> None:
    questions = result.get("questions")
    if not isinstance(questions, list) or not questions:
        fail("intake must emit non-empty questions covering the undocumented legacy-batch runtime behavior")
    exp_rows = [
        q for q in questions
        if isinstance(q, dict) and q.get("route") == "experiment"
        and RUNTIME_TOPIC_RE.search(f"{q.get('question', '')} {q.get('changes', '')}")
    ]
    if not exp_rows:
        fail("questions must include at least one route='experiment' entry targeting legacy-batch runtime/limit/multiline behavior")
    person_misroutes = [
        q for q in questions
        if isinstance(q, dict) and q.get("route") == "person"
        and PERSON_RUNTIME_RE.search(f"{q.get('question', '')} {q.get('changes', '')}")
    ]
    if person_misroutes:
        fail("empirically testable legacy-batch runtime behavior must route to 'experiment', not 'person'")


def check_c1(result: dict) -> None:
    summary = str(result.get("summary") or "")
    if not SENTENCE_RE.search(summary):
        fail("intake summary must cite request sentence indices (S1, ...)")
    cats = result.get("question_categories")
    if not isinstance(cats, list):
        fail("question_categories must list K1..K12")
    cat_ids = [str(row.get("id")) for row in cats if isinstance(row, dict)]
    if sorted(cat_ids, key=lambda s: (len(s), s)) != EXPECTED_CATEGORIES:
        fail(f"question_categories must cover K1..K12 once, found {cat_ids!r}")
    questions = result.get("questions")
    if not isinstance(questions, list) or not questions:
        fail("questions must be a non-empty list")
    for idx, row in enumerate(questions):
        if not isinstance(row, dict):
            fail(f"questions[{idx}] must be an object")
        for key in REQUIRED_Q_FIELDS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                fail(f"questions[{idx}].{key} must be a non-empty string")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("P1", "C1"):
        fail("usage: check_intake_experiment.py <P1|C1>")
    result = load_result()
    check_p1(result) if sys.argv[1] == "P1" else check_c1(result)


if __name__ == "__main__":
    main()
