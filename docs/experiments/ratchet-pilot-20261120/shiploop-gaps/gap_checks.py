"""Hermetic, in-memory demonstration of five claimed gaps in ShipLoop's released checks.

Calls the real functions of skills/shiploop/scripts with made-up inputs and prints what they return.  Changes nothing
in the product; the only file system use is a temporary directory for the one check that reads a spec file.
Run: python3 gap_checks.py
"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPTS = HERE.parents[4] / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_concerns as concerns
import shiploop_expectations as expectations
import shiploop_knowledge_home as knowledge
import shiploop_navigator as navigator
import shiploop_test_loop as test_loop
import shiploop_unverified as unverified


def show(label, call, value, verdict):
    print("  call:    " + call)
    print("  " + label + ": " + repr(value))
    print("  verdict: " + verdict)


def attempt(fn):
    """('ok', value) or ('raised', 'ExcType: message')."""
    try:
        return "ok", fn()
    except Exception as exc:  # noqa: BLE001 - the demonstration reports any refusal verbatim
        return "raised", type(exc).__name__ + ": " + str(exc)


# ---------------------------------------------------------------------------------------------------------------
print("CLAIM 1: judge() passes a check row with exit 0 and empty output; no-tests only on a recognised zero tally")
check_row = {"suite": "check", "command": "true"}
got = test_loop.judge(check_row, 0, "")
show("returned", "judge({'suite':'check'}, 0, '')", got,
     "claim holds" if got["status"] == "passed" else "claim does not hold")

for name, text in (("node TAP zero summary", "# tests 0\n# pass 0\n# fail 0\n# cancelled 0\n"),
                   ("pytest 'no tests ran'", "============ no tests ran in 0.01s ============\n"),
                   ("unittest 'Ran 0 tests'", "Ran 0 tests in 0.000s\n\nNO TESTS RAN\n")):
    got = test_loop.judge(check_row, 0, text)
    show("returned", "judge({'suite':'check'}, 0, <" + name + ">)", got,
         "claim holds (zero-test summary judged no-tests)" if got["status"] == "no-tests"
         else "claim does not hold")

got = test_loop.judge(check_row, 0, "nothing was run here, but this line is not a runner summary\n")
show("returned", "judge({'suite':'check'}, 0, 'free text, no runner summary')", got,
     "(extra) any exit-0 check with unrecognised output passes: " + got["status"])

focused_row = {"suite": "focused", "command": "run-tests", "ids": ["T-1", "T-2"]}
got = test_loop.judge(focused_row, 0, "T-1 handles empty input\nT-2 handles repeated input\n")
show("returned", "judge({'suite':'focused','ids':['T-1','T-2']}, 0, 'T-1 ...\\nT-2 ...' (names ids, no tally))", got,
     "claim holds" if got["status"] == "passed" else "claim does not hold")
got = test_loop.judge(focused_row, 0, "")
show("returned", "judge(focused ids T-1,T-2, 0, '')", got,
     "(extra control) same row with empty output: " + got["status"])
got = test_loop.judge(focused_row, 0, "T-1 handles empty input\nT-2 FAILED handles repeated input\n")
show("returned", "judge(focused, 0, 'T-2 FAILED ...' no tally)", got,
     "(extra control) a failure mark on a listed ID: " + got["status"])

# ---------------------------------------------------------------------------------------------------------------
print("\nCLAIM 2: check_test_cases accepts cases whose criterion differs from the one their focused command declares")
with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    (repo / knowledge.HOME).mkdir(parents=True)
    (repo / knowledge.HOME / "spec.md").write_text("R-1 the product does one thing.\n", encoding="utf-8")
    plan = {"outcome": "done",
            "criteria": [{"id": "AC-1", "text": "first R-1", "confirm": "executed"},
                         {"id": "AC-2", "text": "second R-1", "confirm": "executed"}],
            "test_commands": [
                {"suite": "focused", "command": "run T-1", "ids": ["T-1"], "criteria": ["AC-1"]},
                {"suite": "focused", "command": "run T-2", "ids": ["T-2"], "criteria": ["AC-2"]}]}
    state = {"repo": str(repo), "work_items": [{"id": "W1"}], "work_index": 0,
             "inner_loops": {"W1": {"action": "a-inner"}},
             "history": [{"stage": "step-plan", "workitem": "W1", "action": "a-plan", "outcome": "done"}],
             "accepted": {"a-plan": plan}}
    both_ac1 = {"outcome": "done",
                "test_cases": [
                    {"id": "T-1", "criterion": "AC-1", "requirement": "R-1", "oracle": "o", "red": "r", "green": "g"},
                    {"id": "T-2", "criterion": "AC-1", "requirement": "R-1", "oracle": "o", "red": "r", "green": "g"}]}
    got = expectations.check_test_cases(repo, state, both_ac1)
    show("returned", "check_test_cases(repo, state, result: T-1->AC-1, T-2->AC-1 (T-2's command declares AC-2))", got,
         "claim holds (None = accepted)" if got is None else "claim does not hold (refused)")
    got = expectations.coverage_notices(state, both_ac1)
    show("returned", "coverage_notices(state, same result)", got,
         "AC-2 flagged by a notice only (never a refusal)" if got and "AC-2" in got[0] else "no notice for AC-2")
    # controls
    honest = {"outcome": "done", "test_cases": [
        {**both_ac1["test_cases"][0]}, {**both_ac1["test_cases"][1], "criterion": "AC-2"}]}
    show("returned", "(control) check_test_cases with T-2->AC-2", expectations.check_test_cases(repo, state, honest),
         "control: accepted as expected")
    show("returned", "(control) coverage_notices with T-2->AC-2", expectations.coverage_notices(state, honest),
         "control: no notice")
    bogus = {"outcome": "done", "test_cases": [
        {**both_ac1["test_cases"][0]}, {**both_ac1["test_cases"][1], "criterion": "AC-9"}]}
    got = expectations.check_test_cases(repo, state, bogus)
    show("returned", "(control) check_test_cases with T-2->AC-9 (not a criterion of the plan)", got and got[0],
         "control: refused only when the criterion is not in the plan at all")

# ---------------------------------------------------------------------------------------------------------------
print("\nCLAIM 3: intake key-question ledger is optional; a malformed ledger is refused")
got = attempt(lambda: navigator._check_intake_questions("intake", {"outcome": "done"}))
show("returned", "_check_intake_questions('intake', {'outcome':'done'})", got,
     "claim holds (returns None, no refusal)" if got == ("ok", None) else "claim does not hold")
got = attempt(lambda: navigator._check_intake_questions("intake", {"outcome": "done", "summary": "x"}))
show("returned", "_check_intake_questions('intake', {'outcome':'done','summary':'x'})", got,
     "same: no ledger keys, accepted" if got == ("ok", None) else "refused")
got = attempt(lambda: navigator._check_intake_questions(
    "intake", {"outcome": "done", "question_categories": [{"id": "K1", "applies": "yes"}]}))
show("raised", "_check_intake_questions('intake', {question_categories: [K1 only]})", got,
     "malformed ledger refused (claim's second half holds)" if got[0] == "raised" else "NOT refused")
got = attempt(lambda: navigator._check_intake_questions(
    "intake", {"outcome": "done", "questions": [{"id": "Q1", "question": "q?", "route": "bogus"}]}))
show("raised", "_check_intake_questions('intake', {questions: [route 'bogus']})", got,
     "malformed ledger refused" if got[0] == "raised" else "NOT refused")
got = attempt(lambda: navigator._check_intake_questions(
    "intake", {"outcome": "done", "question_categories": [], "questions": []}))
show("raised", "_check_intake_questions('intake', {question_categories: [], questions: []})", got,
     "empty ledger refused" if got[0] == "raised" else "empty list accepted")

# ---------------------------------------------------------------------------------------------------------------
print("\nCLAIM 4: plan concern rows accept arbitrary non-blank decision/anchor; 'no' accepts a one-word reason")


def plan_rows(override):
    rows = [{"id": name, "applies": "no", "reason": "n/a"} for name in concerns.CONCERN_IDS]
    rows[0] = override
    return {"W1": rows}


row = {"id": "ui", "applies": "yes", "decision": "x", "anchor": "x", "owner_stage": "step-plan"}
got = attempt(lambda: concerns.canonical_plan(plan_rows(row))["W1"][0])
show("returned", "canonical_plan({W1: [ui yes decision='x' anchor='x' ...]+14 'no' rows 'n/a'})", got,
     "claim holds (accepted)" if got[0] == "ok" else "claim does not hold")
row = {"id": "ui", "applies": "no", "reason": "n/a"}
got = attempt(lambda: concerns.canonical_plan(plan_rows(row))["W1"][0])
show("returned", "canonical_plan(... ui applies:'no' reason='n/a')", got,
     "claim holds (one-word reason accepted)" if got[0] == "ok" else "claim does not hold")
row = {"id": "ui", "applies": "no", "reason": "no"}
got = attempt(lambda: concerns.canonical_plan(plan_rows(row))["W1"][0])
show("returned", "canonical_plan(... ui applies:'no' reason='no')", got,
     "accepted" if got[0] == "ok" else "refused")
got = attempt(lambda: concerns.canonical_plan(plan_rows({"id": "ui", "applies": "no", "reason": "  "})))
show("raised", "(control) reason is blank", got, "control: blank refused" if got[0] == "raised" else "blank accepted")
got = attempt(lambda: concerns.check_plan(concerns.canonical_plan(plan_rows(
    {"id": "ui", "applies": "no", "reason": "x"})), ["W1"]))
show("returned", "check_plan(canonical_plan(...), ['W1']) (the CLI gate's second step)", got,
     "gate accepts" if got == ("ok", None) else "gate refuses")

# ---------------------------------------------------------------------------------------------------------------
print("\nCLAIM 5: an empty unverified list satisfies the product-acceptance presence requirement")
got = attempt(lambda: unverified.check_submitted("product-acceptance", {"outcome": "done", "unverified": []}))
show("returned", "check_submitted('product-acceptance', {'outcome':'done','unverified':[]})", got,
     "claim holds (accepted)" if got == ("ok", None) else "claim does not hold")
got = attempt(lambda: unverified.check_submitted("product-acceptance", {"outcome": "done"}))
show("raised", "(control) key missing", got, "control: missing key refused" if got[0] == "raised" else "NOT refused")
got = attempt(lambda: unverified.canonical([]))
show("returned", "canonical([])", got, "shape-only canonicalisation accepts []")
