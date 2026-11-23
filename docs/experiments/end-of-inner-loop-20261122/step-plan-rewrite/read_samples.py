#!/usr/bin/env python3
"""Read ``stages.py live`` samples by the design's measures (step-plan-rewrite-design.md, revision 1, "The deciding check").

    python3 read_samples.py ROOT [ROOT ...] [--json OUT]

ROOT is a ``stages.py live --out`` folder. Script only: no model, no ShipLoop command, nothing written but OUT. Per sample it compares
``export/`` with ``seed-export/`` (the tree when the host was ended, and as the seed left it), reads the stage's result from the run's
state, and the refusals from its trace. Requirement entries are cut by ShipLoop's own parser (``shiploop_knowledge_home._entries``).

A measure is ``yes``, ``no`` or ``read``: ``read`` is what a script cannot decide (a paraphrase without the exact text), never a failure.
The cell is P for the Proof-only scenario, else C for a sample built from case.json's ``released_ref``, else T.

The NORMATIVE measure (``normative``): the entry's sentences are split (code spans kept whole, wrapped lines joined). A sentence that opens
with Basis, Source, Reason or the like is a reason; what follows "because", "since", "revised" or "the send-back asks" (says, wants,
names) in any sentence is too, and so are a leading "Because ...," and a parenthesis holding such a word. The exact new text (case.json
``new_token``) must stand in what is left, outside a negation, a "Confirm" sentence and a sentence that opens by saying what was revised:
- ``yes``: it does;
- ``no``: the entry is gone or unchanged, or the text stands only in a reason or a negation, or it is absent and the old clause is still
  there word for word;
- ``read``: the old clause is gone and the new text is absent (a paraphrase), or stands only in a "Confirm" sentence or in one that opens
  by saying what was revised.

Verdict of T (and, for reading only, of C): ``met`` when every measure is yes, ``not met`` when one is no, else ``read``. P: ``met``
when spec.md is byte-identical and the failing step's Proof differs from the recorded one. STOP lines name what the design says is
read before anything else.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "test/shiploop_e2e/stage_suite"), str(ROOT / "test/shiploop_e2e"), str(ROOT / "skills/shiploop/scripts")]
import slice as step_slice  # noqa: E402
import stage_live  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402

CASE = json.loads((HERE / "case.json").read_text())
CASES = HERE / "stage_cases" / "step-plan"
SPEC = "docs/shiploop/spec.md"
HOME = "docs/shiploop/"
YES, NO, READ = "yes", "no", "read"
# The fix-forward gate's refusals (shiploop_navigator._fix_forward_refusal), as the 2026-11-13 replay's score_q1.py matched them.
FIX_FORWARD = [r"are done \(reviewed and committed\) and stay as they are", r"done step \S+ differs from its accepted row",
               r"no step of \S+ is done, so no step carries", r"every step is done: an amendment keeps",
               r"whose cases are due at done step", r"no step still to run lists", r"belongs to a done step and stays as accepted"]
REASON_HEAD = re.compile(r"^(?:[-*]\s+)?(?:\*\*|_)?(?:basis|source|reason|why|previously|formerly)\b", re.I)
# A sentence that opens by saying something was revised may still state the rule after it: never a failure, read by hand.
REVISED_HEAD = re.compile(r"^(?:[-*]\s+)?(?:\*\*|_)?(?:revised|revision|amended|updated|note|changed|step[- ]plan|this (?:clause|entry|requirement) (?:was|is))"
                          r"\b(?:[^:`\"]{0,80}:)?", re.I)
BECAUSE_FIRST = re.compile(r"^(?:[-*]\s+)?(?:because|since|as (?:docs/|the operations))[^,`\"]*,\s*", re.I)
BLOCK = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s)")
REASON_TAIL = re.compile(r"(?:^|[,;:(—–-]|\s)\s*\b(?:because|since|revised|as (?:docs/|the operations)|per docs/|(?:the )?send-back (?:that )?"
                         r"(?:asks|asked|says|said|wants|wanted|requires|required|names|named)\b)", re.I)
REASON_WORD = re.compile(r"\b(?:because|since|revised|source|basis|per docs)\b", re.I)
CONFIRM = re.compile(r"^(?:[-*]\s+)?confirm(?:ed)?\b", re.I)
NEGATED = re.compile(r"\b(?:not|never|no longer|instead of|rather than|cannot)\b(?:\s+(?:be|read|reads|say|says|carry|carries|contain|show|have|use"
                     r"|exactly|just|as|the|a|an|text|message|body|words))*\s*$", re.I)


def flat(text: str) -> str:
    return " ".join(text.split())


def blocks(text: str) -> list[str]:
    """An entry's headings, list items and paragraphs, each on one line however it was wrapped."""
    found: list[str] = []
    fresh = True
    for line in text.splitlines():
        if not line.strip():
            fresh = True
            continue
        if fresh or BLOCK.match(line):
            found.append(line.strip())
        else:
            found[-1] += " " + line.strip()
        fresh = bool(re.match(r"\s*#{1,6}\s", line))
    return found


def sentences(text: str) -> list[str]:
    """The sentences of an entry: each block apart, a code span never split."""
    found = []
    for line in blocks(text):
        spans: list[str] = []

        def hide(match: re.Match) -> str:
            spans.append(match.group(0))
            return f"\x00{len(spans) - 1}\x00"

        hidden = re.sub(r"`[^`]*`|\"[^\"]*\"", hide, line)
        for sentence in re.split(r"(?<=\.)\s+|(?<=\x00)\s+(?=[A-Z])", hidden):
            # a reason stays whole ("Basis: a; b; c."); any other sentence is read clause by clause
            for piece in [sentence] if REASON_HEAD.match(sentence) else re.split(r"(?<=;)\s+", sentence):
                piece = re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], piece).strip()
                if piece:
                    found.append(piece)
    return found


def part_of(sentence: str) -> tuple[str, str]:
    """(the normative part, the reason part) of one sentence."""
    if REASON_HEAD.match(sentence):
        return "", sentence
    kept, reasons = sentence, []
    for opening in (BECAUSE_FIRST.match(kept), REVISED_HEAD.match(kept)):
        if opening:
            reasons.append(opening.group(0))
            kept = kept[opening.end():]
            break
    kept = re.sub(re.escape(CASE["new_token"]), "\x01", kept, flags=re.I)  # the new text holds parentheses of its own
    for bracket in re.findall(r"\([^()]*\)", kept):
        if REASON_WORD.search(bracket):
            kept = kept.replace(bracket, " ")
            reasons.append(bracket)
    cut = REASON_TAIL.search(kept)
    if cut:
        reasons.append(kept[cut.start():])
        kept = kept[:cut.start()]
    return kept.replace("\x01", CASE["new_token"]), " ".join(reasons).replace("\x01", CASE["new_token"])


def holds(text: str) -> bool:
    return CASE["new_token"].lower() in text.lower()


def negated(sentence: str) -> bool:
    """Whether the new text in ``sentence`` is what the sentence says it is NOT."""
    at = sentence.lower().index(CASE["new_token"].lower())
    for opening in ("`", '"', "“", "'"):
        before = sentence[:at]
        if before.count(opening) % 2 or (opening == "“" and before.count("“") > before.count("”")):
            at = before.rindex(opening)
            break
    return bool(NEGATED.search(sentence[:at]))


def normative(before: str, after: str | None) -> tuple[str, str, list[str]]:
    """(yes, no or read; why; the entry's sentences that are new)."""
    if after is None:
        return NO, "the entry is gone", []
    old = {flat(s) for s in sentences(before)}
    changed = [flat(s) for s in sentences(after) if flat(s) not in old]
    if after == before:
        return NO, "the entry is unchanged", []
    where = {"norm": [], "confirm": [], "unclear": [], "reason": [], "negated": []}
    for sentence in sentences(after):
        if not holds(sentence):
            continue
        kept, _reason = part_of(sentence)
        if not holds(kept):
            where["reason"].append(sentence)
        elif negated(kept):
            where["negated"].append(sentence)
        elif CONFIRM.match(sentence):
            where["confirm"].append(sentence)
        elif REVISED_HEAD.match(sentence):
            where["unclear"].append(sentence)
        else:
            where["norm"].append(sentence)
    if where["norm"]:
        return YES, where["norm"][0], changed
    if where["confirm"]:
        return READ, "the new text stands only in a Confirm sentence", changed
    if where["unclear"]:
        return READ, "the new text stands only in a sentence that says what was revised: " + where["unclear"][0][:160], changed
    if where["reason"] or where["negated"]:
        return NO, "the new text stands only in " + " and ".join(k for k in ("a reason" if where["reason"] else "",
                                                                             "a negation" if where["negated"] else "") if k), changed
    if flat(CASE["old_clause"]).lower() in flat(after).lower():
        return NO, "the new text is absent and the old clause stands", changed
    return READ, "the new text is absent and the old clause is gone: a paraphrase is read by hand", changed


def old_clause(after: str | None) -> tuple[str, str]:
    """Whether the old clause is gone: ``no`` in a normative part, ``read`` when only a reason quotes it."""
    if after is None:
        return READ, "the entry is gone"
    clause = flat(CASE["old_clause"]).lower()
    if clause not in flat(after).lower():
        return YES, "gone"
    for sentence in sentences(after):
        if clause in flat(part_of(sentence)[0]).lower():
            return NO, "stands: " + flat(sentence)[:200]
    return READ, "quoted in a reason only"


def files(folder: Path) -> dict[str, str]:
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(folder.rglob("*")) if path.is_file() and not path.is_symlink()} if folder.is_dir() else {}


def changed_files(sample: Path) -> list[str] | None:
    if not (sample / "export").is_dir() or not (sample / "seed-export").is_dir():
        return None
    before, after = files(sample / "seed-export"), files(sample / "export")
    return sorted(name for name in set(before) | set(after) if before.get(name) != after.get(name))


def spec_measures(sample: Path) -> dict:
    start, end = sample / "seed-export" / SPEC, sample / "export" / SPEC
    if not start.is_file() or not end.is_file():
        return {"read": False, "why": "no " + SPEC + " in seed-export or export"}
    old_text, new_text = start.read_text(), end.read_text()
    old, new = knowledge._entries(old_text, "R"), knowledge._entries(new_text, "R")
    rn = CASE["requirement"]
    before, after = old.get(rn), new.get(rn)
    out: dict = {"read": True, "spec_identical": old_text == new_text,
                 "others_changed": [i for i in old if i != rn and i in new and new[i] != old[i]],
                 "removed": [i for i in old if i not in new], "added": [i for i in new if i not in old],
                 "retired": [i for i in old if i in new and new[i].retired and not old[i].retired],
                 "rest_identical": (old_text.replace(before.text, "\0").rstrip() == new_text.replace(after.text, "\0").rstrip()
                                    if before and after else None)}
    if before is None:
        return out
    text = after.text if after else None
    found, why, changed = normative(before.text, text)
    clause, clause_why = old_clause(text)
    new_words = "\n".join(changed)
    out.update({
        "normative": found, "normative_why": why, "old_clause_gone": clause, "old_clause_why": clause_why,
        "id_kept": YES if after and not after.retired else NO,
        "siblings_lost": [line for line in CASE["siblings"] if text is None or line not in text.splitlines()],
        "basis_line_changed": text is None or CASE["basis_line"] not in text.splitlines(),
        "source": YES if re.search(CASE["source_pattern"], new_words, re.I) else READ if changed else NO,
        "reason": YES if re.search(CASE["reason_pattern"], new_words, re.I) else READ if changed else NO,
        "says_revised": bool(re.search(r"revis|rewr|amend", new_words, re.I)),
        "changed_sentences": changed, "entry_after": text})
    return out


def rows_of(value: object) -> list[dict]:
    return [row for row in value or () if isinstance(row, dict)] if isinstance(value, list) else []


def plan_measures(state: dict | None, action: str, result: dict | None, scenario: str) -> dict:
    result = result or {}
    previous = next((state["accepted"][row["action"]] for row in (state or {}).get("history") or []
                     if row.get("stage") == "step-plan" and row.get("outcome") == "done" and row.get("action") != action), {})
    rn, summary = CASE["requirement"], str(result.get("summary") or "")
    steps = rows_of(result.get("steps"))
    owners = {c: [s.get("id") for s in steps if c in (s.get("criteria") or []) and s.get("done") is not True] for c in
              (row.get("id") for row in rows_of(result.get("criteria")))}
    was = {row.get("id"): row.get("text") for row in rows_of(previous.get("criteria"))}
    stating = [row for row in rows_of(result.get("criteria")) if holds(str(row.get("text")))]
    maybe = [row for row in rows_of(result.get("criteria")) if row not in stating and row.get("text") != was.get(row.get("id"))]
    criterion = (YES if any(owners.get(row.get("id")) for row in stating) else NO if stating else READ if maybe else NO)
    out = {"summary_begins_revised": YES if re.match(r"\s*Revised " + re.escape(rn) + r"\b", summary) else NO,
           "summary_names": rn in summary, "follows_names": YES if rn in (result.get("follows") or []) else NO,
           "criterion": criterion,
           "criteria_stating": [{"id": row.get("id"), "owners": owners.get(row.get("id")), "text": row.get("text")} for row in stating],
           "criteria_changed_without_the_text": [{"id": row.get("id"), "text": row.get("text")} for row in maybe],
           "steps": [{"id": s.get("id"), "done": s.get("done") is True, "criteria": s.get("criteria")} for s in steps],
           "summary": summary, "headline": result.get("headline")}
    expected = json.loads((CASES / scenario / "oracle" / "expected.json").read_text()) if (CASES / scenario).is_dir() else {}
    correction = expected.get("correction") or {}
    if correction.get("kind") == "step_proof_runs":
        row = next((s for s in steps if s.get("id") == correction["step"]), None)
        out["failing_step"] = correction["step"]
        out["proof_repaired"] = (READ if row is None and steps else NO if row is None or row.get("proof") == correction["recorded_proof"]
                                 else YES)
        out["failing_step_proof"] = row.get("proof") if row else None
    return out


def callback_measures(run_dir: Path, action: str) -> dict:
    calls = []
    path = run_dir / "trace.jsonl"
    for line in path.read_text(errors="replace").splitlines() if path.is_file() else []:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("kind") == "command" and row.get("verb") in ("check", "complete") and row.get("action") == action:
            calls.append(row)
    refused = [{"verb": row["verb"], "fix_forward": any(re.search(p, str(row.get("error"))) for p in FIX_FORWARD),
                "error": flat(str(row.get("error")))[:200]} for row in calls if row.get("exit")]
    first = calls[0] if calls else None
    if first is None:
        gate, why = READ, "no check or complete in the trace"
    elif not first.get("exit"):
        gate, why = YES, "the first " + first["verb"] + " was accepted"
    elif any(re.search(p, str(first.get("error"))) for p in FIX_FORWARD):
        gate, why = NO, flat(str(first.get("error")))[:200]
    else:
        gate, why = READ, "the first " + first["verb"] + " was refused by another gate, which may run before fix forward: " \
            + flat(str(first.get("error")))[:160]
    return {"callbacks": len(calls), "refusals": len(refused), "refused": refused, "fix_forward_refusals": sum(r["fix_forward"] for r in refused),
            "fix_forward_first": gate, "fix_forward_first_why": why}


def old_run_touched() -> list[str]:
    """Files of the retained run the Proof-only packet names by absolute path that no longer read as when this was built."""
    return [path for path, digest in (CASE.get("old_run_files") or {}).items()
            if Path(path).is_file() and hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest]


def verdict(values: list[str]) -> str:
    return "not met" if NO in values else "read" if READ in values else "met"


def sample_row(root: Path, sample: Path) -> dict:
    scenario = sample.parent.name
    row: dict = {"root": str(root), "scenario": scenario, "sample": sample.name}
    try:
        invocation = json.loads((sample / stage_live.INVOCATION).read_text())
    except (OSError, ValueError):
        error = (sample / stage_live.ERROR).read_text(errors="replace").strip() if (sample / stage_live.ERROR).is_file() else "no invocation.json"
        return {**row, "not_run": error, "verdict": "not run"}
    ref = invocation.get("ref")
    cell = "P" if scenario == CASE["proof_scenario"] else "C" if ref and CASE["released_ref"].startswith(str(ref)) else "T"
    run_dir = stage_live._run_dir(sample, invocation)
    state, action = step_slice.read_state(run_dir), invocation["action_id"]
    result, source = stage_live.seeded_result(state, action)
    sessions = stage_live._sessions(sample, stage_live.accepted_reached(state, action))
    versions = invocation.get("versions") or {}
    row.update({"cell": cell, "host": invocation.get("host"), "model": invocation.get("model"), "effort": invocation.get("effort"),
                "text": {"ref": ref, "overlay": bool(invocation.get("overlay")), "shiploop": versions.get("shiploop_version"),
                         "plugin_sha256": versions.get("plugin_sha256")},
                "process": sessions[-1]["status"] if sessions else None,
                "minutes": round(sum(float(s["seconds"] or 0) for s in sessions) / 60, 1),
                "result_source": source, "outcome": (result or {}).get("outcome"), "run_status": (state or {}).get("status"),
                "accepted": YES if source and (result or {}).get("outcome") == "done" else NO})
    row["callbacks"] = callback_measures(run_dir, action)
    row["plan"] = plan_measures(state, action, result, scenario)
    changed = changed_files(sample)
    row["product_files_changed"] = None if changed is None else [name for name in changed if not name.startswith(HOME)]
    row["knowledge_files_changed"] = None if changed is None else [name for name in changed if name.startswith(HOME)]
    row["spec"] = spec_measures(sample)
    scenario_spec = CASES / scenario / "route/1-document" / SPEC
    start = sample / "seed-export" / SPEC
    row["start_is_the_scenarios"] = start.is_file() and scenario_spec.is_file() and start.read_bytes() == scenario_spec.read_bytes()
    try:  # the stage suite's own verdict, for reading only: in P its P2 runs the amended Proof in the sample's tree
        graded = json.loads((sample / stage_live.RESULT).read_text())
        row["suite"] = {"pass": graded.get("pass"), "caught": graded.get("caught"), "verdicts": graded.get("verdicts")}
    except (OSError, ValueError):
        row["suite"] = None
    row["blocked_summary"] = flat(str((result or {}).get("summary")))[:400] if (result or {}).get("outcome") == "blocked" else None
    product = NO if row["product_files_changed"] else READ if row["product_files_changed"] is None else YES
    spec, plan, stop = row["spec"], row["plan"], []
    if not spec["read"]:
        measures = {"accepted": row["accepted"], "spec readable": READ}
    elif cell == "P":
        measures = {"accepted": row["accepted"], "spec byte-identical": YES if spec["spec_identical"] else NO,
                    "failing Proof repaired": plan.get("proof_repaired", READ), "no product file changed": product}
        if not spec["spec_identical"]:
            stop.append("spec.md was rewritten on a Proof-only send-back: " + ", ".join(spec["others_changed"] + spec["added"]
                        + spec["removed"] + spec["retired"] or ["text outside the entries"]))
    else:
        measures = {
            "accepted": row["accepted"], "normative clause states the new meaning": spec["normative"], "old clause gone": spec["old_clause_gone"],
            "ID kept": spec["id_kept"], "sibling clauses byte-identical": NO if spec["siblings_lost"] else YES,
            "every other R-n byte-identical": NO if spec["others_changed"] else YES,
            "no R-n added, removed or retired": NO if spec["added"] or spec["removed"] or spec["retired"] else YES,
            "entry gives a source": spec["source"], "entry gives a reason": spec["reason"],
            "summary begins 'Revised " + CASE["requirement"] + "'": plan["summary_begins_revised"], "follows names it": plan["follows_names"],
            "criterion of a step not done states it": plan["criterion"], "no product file changed": product}
        for label, found in (("another requirement changed", spec["others_changed"]), ("a sibling clause changed", spec["siblings_lost"]),
                             ("a requirement added", spec["added"]), ("a requirement removed", spec["removed"]),
                             ("a requirement retired", spec["retired"])):
            if found:
                stop.append(label + ": " + "; ".join(found))
    touched = old_run_touched()
    if touched:
        stop.append("the retained run's files changed: " + ", ".join(touched))
    if not row["start_is_the_scenarios"]:
        stop.append("the sample's starting spec is not the scenario's: the apparatus, not the model")
    row.update({"measures": measures, "verdict": verdict(list(measures.values())), "stop": stop})
    return row


def show(row: dict) -> None:
    print(f"== {row.get('cell', '?')}  {row['scenario']} #{row['sample']}  ({row['root']})")
    if "not_run" in row:
        print("   NOT RUN: " + row["not_run"][:300])
        return
    text = row["text"]
    print(f"   {row['host']} {row['model']} {row['effort']}  ref {text['ref']}{' + overlay' if text['overlay'] else ''}, ShipLoop "
          f"{text['shiploop']}, build {text['plugin_sha256']}  {row['minutes']} min  process {row['process']}, outcome {row['outcome']} "
          f"({row['result_source']}), run {row['run_status']}")
    calls = row["callbacks"]
    print(f"   refusals before acceptance: {calls['refusals']} (fix forward {calls['fix_forward_refusals']}); fix forward on the first "
          f"callback: {calls['fix_forward_first']} ({calls['fix_forward_first_why']})")
    for refused in calls["refused"]:
        print(f"     refused {refused['verb']}: {refused['error']}")
    for name, value in row["measures"].items():
        print(f"   {value:4}  {name}")
    spec, plan = row["spec"], row["plan"]
    if row["cell"] != "P" and spec.get("read"):
        print(f"   normative: {spec['normative_why'][:220]}")
        print(f"   old clause: {spec['old_clause_why'][:220]}; basis line changed {spec['basis_line_changed']}, says revised {spec['says_revised']}, "
              f"rest of spec.md identical {spec['rest_identical']}")
        for sentence in spec.get("changed_sentences") or []:
            print("     new in the entry: " + sentence[:300])
    for item in plan["criteria_stating"]:
        print(f"     criterion {item['id']} (steps {item['owners']}): {str(item['text'])[:220]}")
    if row["cell"] != "P" and plan["criterion"] == READ:
        for item in plan["criteria_changed_without_the_text"]:
            print(f"     changed criterion {item['id']}: {str(item['text'])[:220]}")
    print(f"   summary: {flat(plan['summary'])[:260]}")
    if row["blocked_summary"]:
        print("   blocked: " + row["blocked_summary"])
    print(f"   the stage suite's own checks (exact text only; for reading): {(row['suite'] or {}).get('caught')}")
    print(f"   product files changed: {row['product_files_changed']}; knowledge files changed: {row['knowledge_files_changed']}")
    for line in row["stop"]:
        print("   STOP: " + line)
    print(f"   VERDICT {row['cell']}: {row['verdict']}")


def read(roots: list[Path]) -> list[dict]:
    rows = []
    for root in roots:
        for sample in sorted(path for path in root.glob("step-plan/*/*") if path.is_dir() and path.name.isdigit()):
            if sample.parent.name in (CASE["requirement_scenario"], CASE["proof_scenario"]):
                rows.append(sample_row(root, sample))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = read(args.roots)
    for row in rows:
        show(row)
    print("\ncell  host    verdict  scenario #sample")
    for row in rows:
        print(f"{row.get('cell', '?'):4}  {str(row.get('host')):6}  {row['verdict']:8} {row['scenario']} #{row['sample']}"
              + ("  STOP" if row.get("stop") else ""))
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
