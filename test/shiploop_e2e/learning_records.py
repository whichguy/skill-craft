#!/usr/bin/env python3
"""Learning records (SPEC mission clause, amended 2026-10-30): each lesson's history, read alongside the last three
commit messages, never in their place (owner decision D2).

One JSON object per line in ``learning-records.jsonl``, appended only by the harness: the improver may not write
``test/shiploop_e2e/`` (``boundary.HARNESS_PREFIXES``), and the file is not in the evaluator digest (top-level ``.py``
and ``.cjs``, SPEC, the catalogs, ``checks/`` and ``evaluators/``), so appending never invalidates an epoch.

A record's ``event`` rows fold into one status (``current``):

    opened -> open; admitted -> admitted; predicted -> in candidate; rejected_at_purpose -> deferred;
    decided (the promotion decision) then verdict (the prediction's verdict and the record's outcome);
    deferred -> deferred; reopened -> admitted (or open, never admitted); owner -> owner, or its outcome

Ids carry a timestamp and a random suffix and there is no global sequence, so two branches that append at once merge
by union (``.gitattributes``) and the fold accepts any line order. ``reviewer_view`` is what a reviewer reads: titles,
anchors and statuses, never evidence text. ``improver_view`` is one record for the improver, also without evidence, so
held-out detail is not passed on through it.

    python3 test/shiploop_e2e/learning_records.py view            # the reviewer's view
    python3 test/shiploop_e2e/learning_records.py show LR-...     # one record, folded, with its events
    python3 test/shiploop_e2e/learning_records.py new-id
    python3 test/shiploop_e2e/learning_records.py append EVENT RECORD --fields '{"title": ...}'
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "learning-records.jsonl"
CONTRACT = "learning-record/1"
EVENTS = ("opened", "admitted", "predicted", "rejected_at_purpose", "decided", "verdict", "deferred", "reopened", "owner")
RECORD_ID = re.compile(r"LR-\d{8}-[0-9a-f]{6}")
# The reviewer sees these first; the rest are history it should not re-propose.
LIVE = ("in_candidate", "admitted", "open", "owner")
SETTLED = ("refuted", "no_effect", "deferred", "rejected", "unexplained_gain", "verified")
OUTCOMES = ("verified", "unexplained_gain", "refuted", "no_effect", "admitted")
CONFIDENCE = {"high": 0, "medium": 1, "low": 2}
# Fields an "opened" row may carry: what a reviewer or a session says the lesson is. Evidence text stays in its source.
DESCRIBES = ("title", "anchor", "materiality", "confidence", "target", "files", "proposal", "next_experiment")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def new_id(now: datetime.datetime | None = None) -> str:
    return f"LR-{(now or _now()):%Y%m%d}-{secrets.token_hex(3)}"


def append(event: str, record: str, path: Path = LEDGER, **fields) -> dict:
    """Append one event row and return it. Refuses an unknown event, a malformed id, or a field that would overwrite
    the row's own keys."""
    if event not in EVENTS:
        raise ValueError(f"unknown learning-record event {event!r}")
    if not RECORD_ID.fullmatch(record or ""):
        raise ValueError(f"malformed learning-record id {record!r}")
    reserved = {"contract", "event_id", "at", "record", "event"} & set(fields)
    if reserved:
        raise ValueError("fields may not set " + ", ".join(sorted(reserved)))
    at = _now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    row = {"contract": CONTRACT, "event_id": f"{at}-{secrets.token_hex(3)}", "at": at, "record": record,
           "event": event, **fields}
    line = json.dumps(row, ensure_ascii=False, sort_keys=False, allow_nan=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return row


def rows(path: Path = LEDGER) -> list[dict]:
    """Every row, in file order. A line that does not parse is an error naming it: a broken merge must be seen."""
    if not path.is_file():
        return []
    found = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as error:
            raise ValueError(f"{path.name} line {number} is not JSON: {error}") from None
        if not isinstance(row, dict) or row.get("event") not in EVENTS or not RECORD_ID.fullmatch(str(row.get("record"))):
            raise ValueError(f"{path.name} line {number} is not a learning-record row")
        found.append(row)
    return found


def _fold(record: str, events: list[dict]) -> dict:
    state = {"record": record, "status": "open", "events": len(events), "seen": 0, "sources": [], "ever_admitted": False,
             "decision": None, "verdict": None, "prediction": None, "candidate": None, "reason": None,
             "reopen_when": None, "exposure": "development", "first_at": events[0]["at"], "last_at": events[-1]["at"]}
    for row in events:
        event = row["event"]
        if event == "opened":
            for key in DESCRIBES:
                if key in row and (state.get(key) is None or state["seen"] == 0):
                    state[key] = row[key]
            state["seen"] += 1
            if row.get("source"):
                state["sources"].append(row["source"])
                if (row["source"] or {}).get("exposure") == "confirmation":
                    state["exposure"] = "confirmation"
            if state["seen"] == 1:
                state["status"] = "open"
        elif event == "admitted":
            state["status"], state["ever_admitted"] = "admitted", True
        elif event == "predicted":
            state["status"], state["prediction"] = "in_candidate", row.get("prediction")
            state["candidate"] = row.get("candidate")
        elif event == "rejected_at_purpose":
            state["status"], state["reason"] = "deferred", row.get("reason") or "candidate rejected at the purpose check"
            state["reopen_when"] = row.get("reopen_when") or "a reviewer or the owner reopens it"
        elif event == "decided":
            state["decision"] = row.get("decision")
            state["epoch"] = row.get("epoch")
        elif event == "verdict":
            state["verdict"] = row.get("verdict")
            outcome = row.get("outcome")
            state["status"] = outcome if outcome in OUTCOMES else state["status"]
            state["reason"] = row.get("reason") or state["reason"]
            state["reopen_when"] = row.get("reopen_when") or state["reopen_when"]
        elif event == "deferred":
            state["status"], state["reason"], state["reopen_when"] = "deferred", row.get("reason"), row.get("reopen_when")
        elif event == "reopened":
            state["status"] = "admitted" if state["ever_admitted"] else "open"
            state["reason"] = row.get("reason")
        elif event == "owner":
            outcome = row.get("outcome")
            state["status"] = {"accept": "admitted", "reject": "rejected"}.get(outcome, "owner")
            state["ever_admitted"] = state["ever_admitted"] or outcome == "accept"
            state["owner_decision"] = row.get("owner_decision")
            state["reason"] = row.get("reason") or state["reason"]
    return state


def current(path: Path = LEDGER) -> dict[str, dict]:
    """Each record folded to its present state, in order of first appearance. Events apply in time order, whatever
    the line order a union merge left."""
    by_record: dict[str, list[dict]] = {}
    for row in sorted(rows(path), key=lambda r: (str(r.get("at")), str(r.get("event_id")))):
        by_record.setdefault(row["record"], []).append(row)
    folded = {record: _fold(record, events) for record, events in by_record.items()}
    return dict(sorted(folded.items(), key=lambda item: item[1]["first_at"]))


def _anchor_text(anchor) -> str:
    if isinstance(anchor, dict):
        return anchor.get("clause_id") or "novel"
    return str(anchor or "no anchor")


def _line(state: dict) -> str:
    seen = f", seen {state['seen']}x" if state["seen"] > 1 else ""
    tail = f" — {state['reason']}" if state["status"] in SETTLED and state.get("reason") else ""
    return (f"- {state['record']} [{state['status']}] ({_anchor_text(state.get('anchor'))}, "
            f"{state.get('materiality') or '?'}/{state.get('confidence') or '?'}{seen}) {state.get('title') or '(untitled)'}"
            f"{tail}")


def reviewer_view(path: Path = LEDGER, max_chars: int = 6000, settled: int = 10) -> str:
    """What a reviewer reads: the live records, then the most recent settled ones, as titles, anchors and statuses.

    Capped at ``max_chars``; what does not fit is counted, never silently dropped."""
    states = list(current(path).values())
    live = sorted((s for s in states if s["status"] in LIVE),
                  key=lambda s: (LIVE.index(s["status"]), s["first_at"]))
    done = sorted((s for s in states if s["status"] in SETTLED), key=lambda s: s["last_at"], reverse=True)[:settled]
    if not live and not done:
        return ""
    lines = ["Live learning records (open, admitted, in a candidate, or with the owner):"]
    lines += [_line(s) for s in live] or ["- none"]
    lines += ["", "Recently settled (do not propose again unless this run shows new evidence; then set same_as):"]
    lines += [_line(s) for s in done] or ["- none"]
    text, shown = "", 0
    for line in lines:
        if len(text) + len(line) + 1 > max_chars:
            break
        text += line + "\n"
        shown += 1
    if shown < len(lines):
        text += f"... {len(lines) - shown} more lines not shown ({path.name})\n"
    return text


def improver_view(record: str, path: Path = LEDGER) -> dict:
    """The one record an improver works on: what it is and where, never the evidence text."""
    state = current(path).get(record)
    if state is None:
        raise ValueError(f"no learning record {record}")
    return {"record": record, "title": state.get("title"), "anchor": state.get("anchor"),
            "files": state.get("files") or [], "proposal": state.get("proposal"),
            "next_experiment": state.get("next_experiment")}


def select(path: Path = LEDGER) -> str | None:
    """The next record a qualified cycle takes: admitted, material, not confirmation-exposed; highest confidence, then
    oldest. None when no record qualifies."""
    candidates = [s for s in current(path).values() if s["status"] == "admitted" and s.get("materiality") == "material"
                  and s["exposure"] != "confirmation" and s.get("target", "shiploop") == "shiploop"]
    if not candidates:
        return None
    candidates.sort(key=lambda s: (CONFIDENCE.get(s.get("confidence"), 3), s["first_at"]))
    return candidates[0]["record"]


def ingest(review: dict, routes: dict, source: dict, path: Path = LEDGER) -> list[str]:
    """Record the material discoveries a judged review routed, and return their record ids.

    ``implementation`` findings are admitted; ``owner_challenges`` go to the owner; ``harness`` findings are deferred to
    a separate evaluator experiment. A discovery whose ``same_as`` names a known record adds to it; an unknown one opens
    a new record and keeps the claimed id as ``same_as_unknown``."""
    known = set(current(path))
    recorded = []
    for route, follow in (("implementation", "admitted"), ("owner_challenges", "owner"), ("harness", "deferred")):
        for finding in routes.get(route) or []:
            if not isinstance(finding, dict):
                continue
            claimed = finding.get("same_as")
            record = claimed if isinstance(claimed, str) and claimed in known else new_id()
            fields = {key: finding.get(key) for key in ("title", "materiality", "confidence", "target", "files",
                                                         "proposal", "next_experiment")}
            fields["anchor"] = finding.get("mission_anchor")
            fields["source"] = {**source, "finding_id": finding.get("id"), "route": route}
            if claimed and record != claimed:
                fields["same_as_unknown"] = claimed
            append("opened", record, path, **fields)
            if follow == "admitted":
                append("admitted", record, path, reason="supported by the judge and implementation-eligible")
            elif follow == "owner":
                append("owner", record, path, reason="material challenge routed to the owner or an investigation")
            else:
                append("deferred", record, path, reason="harness finding: a separate evaluator experiment",
                       reopen_when="an evaluator experiment is registered for it")
            known.add(record)
            recorded.append(record)
    return recorded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("view", "show", "new-id", "append", "select"))
    parser.add_argument("args", nargs="*")
    parser.add_argument("--fields", default="{}", help="JSON object of the event's fields (append)")
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    args = parser.parse_args(argv)
    try:
        if args.command == "view":
            print(reviewer_view(args.ledger) or "no learning records")
        elif args.command == "show":
            if len(args.args) != 1:
                parser.error("show needs one record id")
            record = args.args[0]
            state = current(args.ledger).get(record)
            if state is None:
                raise ValueError(f"no learning record {record}")
            events = [row for row in rows(args.ledger) if row["record"] == record]
            print(json.dumps({"state": state, "events": events}, indent=2, ensure_ascii=False))
        elif args.command == "new-id":
            print(new_id())
        elif args.command == "select":
            print(select(args.ledger) or "")
        else:
            if len(args.args) != 2:
                parser.error("append needs EVENT RECORD")
            fields = json.loads(args.fields)
            if not isinstance(fields, dict):
                parser.error("--fields must be a JSON object")
            print(json.dumps(append(args.args[0], args.args[1], args.ledger, **fields), ensure_ascii=False))
    except ValueError as error:
        print(f"learning_records: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
