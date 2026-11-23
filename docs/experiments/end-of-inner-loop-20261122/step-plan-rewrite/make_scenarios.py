#!/usr/bin/env python3
"""Make the experiment's two scenarios from the committed replay they are copied from (case.json, "copied_from").

    python3 make_scenarios.py        # rewrites stage_cases/step-plan/ beside this file

``replay-ticket-comments-late-send-back`` (cell P) is the original less the old run's absolute paths (5 below, done the same way for both):
its send-back is a fault of one step's Proof. Every other byte is the original's.

``send-back-revises-r9`` (cells T and C) is the original with these changes and no other. Each replaced text must occur as often as
said here, so a changed original stops this script instead of giving another scenario:

1. R-9. The original's spec has one requirement for the whole item (R-8), and the done step S1 serves it, so no requirement there
   is served by unfinished steps only. The notification bullet's MESSAGE (what is delivered) becomes its own entry, R-9, with two
   sibling clauses; R-8 keeps who is notified and that each comment queues its own event. C3 and its case TC_Comments_Notify, which
   already were the message's criterion and case, name R-9; the item follows R-9 too. The spec stays the original's otherwise
   (R-1 to R-7 and the rest of R-8 byte for byte), in the baseline and in the copy S1's document stage left.
2. The step order. S2 is the message (originally S3) and is the interrupted step; S3 is the HTTP API (originally S2), not begun. So
   the step that sends back is the one that serves R-9. Their content and criteria are the original's; S2's Proof also reads the
   subject; S3's Proof is quoted right (the original's fault was that Proof; here the requirement is the only open point).
3. S2's draft is a template that does what R-9 says today, left uncommitted; it passes S2's recorded Proof. The reason for the change
   is independent of it: ``planted_fact``, two lines of the product's own docs/operations.md, in the run's baseline commit.
4. The last send-back's result is case.json's ``send_back``; the stage that sends is the original's, implement. No owner note.
5. The old run's absolute paths become paths of this run: worktree files are repository-relative, the two planning notes are copied
   to ``notes/`` (RUN/notes), the baseline log is named by the environment file that records it. The retained run still exists on
   this machine, so a model could otherwise read it, or edit its spec.md in place of the sample's. No ``/Users/`` is left in a scenario.
6. about, tags, planted, render, oracle and live are this experiment's.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CASE = json.loads((HERE / "case.json").read_text())
SOURCE = ROOT / CASE["copied_from"]
CASES = HERE / "stage_cases" / "step-plan"
OUT = CASES / CASE["requirement_scenario"]
RN = CASE["requirement"]

R8_OLD = ("- A comment by someone other than the current assigned agent queues a distinct notification with comment content for that "
          "agent; no assignment or self-comment produces none. Audit each change. Confirm outbox and worker delivery tests, including "
          "multiple pending comments.\n")
R8_NEW = ("- A comment by someone other than the current assigned agent queues a distinct notification for that agent; no assignment or "
          "self-comment produces none. Audit each change. Confirm outbox tests, including multiple pending comments.\n")
BEFORE_R9 = "\n## Non-functional requirements\n"
DRAFT_AFTER = "const TEMPLATES = Object.freeze({\n"
DRAFT = ("  'ticket.commented': (event) => ({\n"
         "    subject: `[${event.ticket}] New comment`,\n"
         "    body: `${event.data.author} commented on ${event.ticket} \"${event.data.title}\": ${event.data.body}`,\n"
         "  }),\n")
C3 = ("R-9 the message delivered for a comment carries its author and content in the body and the ticket ID first in the subject, and a "
      "failed delivery is retried. Confirm by: TC_Comments_Notify; pass when the assigned recipient receives the authored text under that "
      "subject, a failing delivery stays pending, and self/unassigned cases do not enqueue.")


def once(text: str, old: str, new: str, what: str, times: int = 1) -> str:
    found = text.count(old)
    if found != times:
        raise SystemExit(f"{what}: {old[:80]!r} occurs {found} times, not {times}")
    return text.replace(old, new)


def edit(path: Path, *changes: tuple) -> None:
    text = path.read_text()
    for old, new in changes:
        text = once(text, old, new, str(path.relative_to(OUT)))
    path.write_text(text)


def spec_and_tree() -> None:
    entry = "\n".join([CASE["heading"], CASE["basis_line"], CASE["changed_line"], *CASE["siblings"]]) + "\n"
    for folder in ("repo", "route/1-document"):
        edit(OUT / folder / "docs/shiploop/spec.md", (R8_OLD, R8_NEW), (BEFORE_R9, "\n" + entry + BEFORE_R9))
        edit(OUT / folder / "docs/shiploop/environment.md", ("Planned R-8: node:test", "Planned R-8 and R-9: node:test"))
    fact = CASE["planted_fact"]
    edit(OUT / "repo" / fact["file"], (fact["after"], fact["after"] + fact["text"]))
    shutil.rmtree(OUT / "route/2-draft")
    draft = OUT / "route/2-draft/src/templates.js"
    draft.parent.mkdir(parents=True)
    draft.write_text(once((OUT / "repo/src/templates.js").read_text(), DRAFT_AFTER, DRAFT_AFTER + DRAFT, "the draft template"))


def plan_and_cases(data: dict) -> None:
    plan, spec = data["seed_route"][0]["result"], data["seed_route"][1]["result"]
    if (data["seed_route"][0]["stage"], data["seed_route"][1]["stage"]) != ("step-plan", "test-spec"):
        raise SystemExit("the original's route does not start with step-plan and test-spec")
    s1, api, message = plan["steps"]
    if (api["criteria"], message["criteria"]) != (["C2", "C4"], ["C3"]):
        raise SystemExit("the original's steps are not the ones this script renames")
    api["proof"] = once(api["proof"], CASE["api_proof"]["from"], CASE["api_proof"]["to"], "the API step's proof")
    message["proof"] = once(message["proof"], "a.match(m.body,/a/);", "a.match(m.body,/a/);a.match(m.subject,/^\\[T-0001\\]/);",
                            "the message step's proof")
    message["id"], api["id"] = "S2", "S3"
    plan["steps"] = [s1, message, api]
    renamed = {"S1": "S1", "S2": "S3", "S3": "S2"}
    for row in (*plan["concerns"], *plan["expectations"]):
        row["steps"] = sorted(renamed[step] for step in row["steps"])
    plan["summary"] = once(plan["summary"], "S2 owns API and input safety; S3 owns notification rendering.",
                           "S2 owns notification rendering; S3 owns API and input safety.", "the plan's summary")
    for row in plan["criteria"]:
        if row["id"] == "C3":
            row["text"] = C3
    plan["follows"] = ["R-8", RN, "AD-4"]
    case = next(row for row in spec["test_cases"] if row["id"] == "TC_Comments_Notify")
    case["requirement"] = RN
    case["oracle"] = once(case["oracle"], "check recipient and authored bodies;",
                          "check recipient, subject and authored bodies; a throwing notifier leaves its event pending;", "TC_Comments_Notify")
    item = data["request"]["work_item"]
    item["follows"] = ["R-8", RN, "AD-4"]
    item["context"] = once(item["context"], "Implement R-8 and AD-4 in", "Implement R-8, R-9 and AD-4 in", "the item's context")
    item["context"] = once(item["context"], "documentation pass and R-8 is observed", "documentation pass and R-8 and R-9 are observed",
                           "the item's context")
    data["seed_records"]["spec"]["primary"] = ["R-8", RN]


def own_paths(text: str, folder: Path) -> str:
    """``text`` (a scenario.json) with the old run's paths made this run's, and the two notes it then names laid into ``folder``/notes."""
    old = CASE["old_run"]
    text = once(text, " passed 124 cases, " + old + "/run/scratch/baseline.log.", " passed 124 cases (docs/shiploop/environment.md).",
                "the item context's baseline log")
    text = once(text, '"' + old + '/run/scratch/baseline.log"', '"docs/shiploop/environment.md"', "assumption A2's evidence")
    for name in CASE["notes"]:
        text = once(text, old + "/run/notes/" + name, "RUN/notes/" + name, name)
    text = once(text, old + "/worktree/", "", "the old worktree's files", 9)
    (folder / "notes").mkdir()
    for name in CASE["notes"]:
        shutil.copy2(HERE / "notes-source" / name, folder / "notes" / name)  # copied once from the retained run
    return text


def no_absolute_path(folder: Path) -> None:
    left = [str(path.relative_to(folder)) for path in sorted(folder.rglob("*")) if path.is_file() and b"/Users/" in path.read_bytes()]
    if left:
        raise SystemExit(f"{folder.name}: an absolute path is left in " + ", ".join(left))


def own_checks(data: dict) -> None:
    token = CASE["new_token"].replace("(", r"\(").replace(")", r"\)")
    data["about"] = (
        "The 2026-11-01 ticket-comments run at its late send-back, changed so that a requirement is what is wrong: S1 is done; S2 (the "
        "message, R-9) was being built when implement sent the item back, because the product's own operations document makes one clause "
        "of R-9 wrong. No owner note covers it. R-9 is served by S2 alone. The redone step-plan is to rewrite that clause in place and "
        "plan the steps for the new text.")
    data["tags"] = ["replay", "fix-forward", "requirement-change"]
    data["planted"] = [
        {"id": "P1", "what": "S1 is done; the amendment keeps it exactly", "signature": "Fix forward:"},
        {"id": "P2", "what": RN + "'s clause the send-back names is rewritten in place in docs/shiploop/spec.md"},
        {"id": "P3", "what": "the amended plan has a criterion that states the new meaning"}]
    data["render"] = [{"proves": "P1", "packet_contains": "Fix forward: S1"},
                      {"proves": "P2", "packet_contains": RN + " must say instead"},
                      {"proves": "P3", "packet_contains": token}]
    data["oracle"] = [
        {"proves": "P1", "outcome": ["done"]},
        {"proves": "P1", "command": 'python3 "$STAGE_ORACLE/q1_oracle.py" fidelity', "exit": 0},
        {"proves": "P2", "file": "docs/shiploop/spec.md", "contains": token},
        {"proves": "P2", "file": "docs/shiploop/spec.md", "not_contains": CASE["old_clause"]},
        {"proves": "P3", "field": "criteria[*].text", "matches": token, "any": True}]
    data["live"] = {"samples": 1, "pass": "all"}


def main() -> None:
    if CASES.exists():
        shutil.rmtree(CASES)
    skip = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in (CASE["proof_scenario"], CASE["requirement_scenario"]):
        shutil.copytree(SOURCE, CASES / name, symlinks=True, ignore=skip)
    data = json.loads((OUT / "scenario.json").read_text())
    last = data["seed_route"][-1]
    if (last["stage"], last["result"]["outcome"]) != ("implement", "send-back"):
        raise SystemExit("the original's last route entry is not implement's send-back")
    last["result"] = CASE["send_back"]
    spec_and_tree()
    plan_and_cases(data)
    data = json.loads(own_paths(json.dumps(data, ensure_ascii=False), OUT))
    own_checks(data)
    (OUT / "scenario.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    expected = json.loads((OUT / "oracle/expected.json").read_text())
    expected.pop("correction")  # the original's correction (a Proof) is not this scenario's
    (OUT / "oracle/expected.json").write_text(json.dumps(expected, indent=1) + "\n")
    proof = CASES / CASE["proof_scenario"]
    (proof / "scenario.json").write_text(own_paths((proof / "scenario.json").read_text(), proof))
    for folder in (OUT, proof):
        no_absolute_path(folder)
    print(CASES)


if __name__ == "__main__":
    main()
