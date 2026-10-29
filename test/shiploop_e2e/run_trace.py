#!/usr/bin/env python3
"""ShipLoop's run trace, read for the harness: the facts a run records about itself, where the host stream only hints.

Since shiploop 1.12.0 every run appends ``RUN/trace.jsonl`` (``skills/shiploop/scripts/shiploop_trace.py``): each command
that named the run, with its exit code and refusal text; each packet printed, with the copy kept as sent
(``packets/sent/<sha>.md``); each keepalive stop decision, with the text it put into the turn. This module reads it through
that script's own reader (``shiploop_trace.build``), so the harness and ``shiploop trace`` attribute events the same way, and
gives the harness's readers one shape:

- ``failures``: every traced command that exited non-zero, in order (a failed check included and flagged: ``shiploop check``, or ``complete --check-only`` before it; as the
  host stream counted them), with the stage the run was in, the action, the refusal text and its first line;
- ``packets``: per action, every print, with its text as sent, its size as printed and whether it repeated an earlier one;
- ``hooks``: every keepalive stop decision with its text;
- ``notes``: every owner note and where it stands (waiting, shown, delivered), as ``shiploop trace`` reads it.

``checks`` reads three live behaviours from them (keepalive text, packet copies, owner notes) into metrics.json.

The host stream stays the source of what the model did (its calls, text and turns); the trace is ShipLoop's account of what it
sent and refused. A run with no ``trace.jsonl`` (before 1.12.0) reads None and its readers keep their stream sources.

``covers`` says whether the trace holds every refusal of a command on the run: false when a step the model accepted was
accepted outside the trace (the run predates it, or began before an upgrade) or the trace reached its size cap. A step the
harness seeded (its result is synthetic) is not the model's, so a step slice's trace still covers it.

The trace records only navigator commands that loaded the run. A command that named no run (``workspace plan-return
--workspace-root W``, whose refusal reads ``ShipLoop workspace blocked:``) or failed on its own command line (argparse:
``shiploop complete: error: ...``) is in the host stream only, and so are the routed verbs (ROUTED_VERBS): shiploop 1.13.1
stopped tracing them, and 1.12.0 traced their exit without text. Their failures are read from the stream on every release,
so runs on either side of 1.13.1 count them with one instrument, and ``read`` leaves them out of ``failures``.
``metrics.outside_trace`` tells such a stream failure, and the readers add it to the trace's, marked with its source.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
import shiploop_store as store  # noqa: E402
import shiploop_trace  # noqa: E402

FILE = shiploop_trace.TRACE_FILE
LINE_LIMIT = 200  # characters of a refusal's first line, as metrics.failure_line keeps a stream refusal's
NO_TEXT = "no refusal text recorded"
# What argparse prints when a ShipLoop command line does not parse (``usage: shiploop complete ...``, then
# ``shiploop complete: error: the following arguments are required: --action``): the run is never loaded, so never traced.
USAGE_ERROR = re.compile(r"^(?:usage: shiploop\b|shiploop(?: [\w-]+)?: error: )", re.M)
RUN_DIR_FLAG = re.compile(r"--run-dir\b")
# The verbs shiploop_protocol hands to their own modules before the navigator loads the run: not traced from 1.13.1, traced
# with an exit and no text in 1.12.0. The harness reads their failures from the host stream on every release.
ROUTED_VERBS = frozenset(("chain", "lint", "red-check", "backchain-check"))


def first_line(text: str | None, limit: int | None = LINE_LIMIT) -> str:
    """The first non-blank line of a refusal's text (``limit`` characters), or NO_TEXT for a command that recorded none."""
    line = next((row.strip() for row in str(text or "").splitlines() if row.strip()), NO_TEXT)
    return line if limit is None else line[:limit]


def _seeded(state: dict, action: str | None) -> bool:
    record = (state.get("accepted") or {}).get(action) or {}
    result = record.get("result", record) if isinstance(record, dict) else {}
    return str((result or {}).get("summary", "")).startswith("Synthetic")


def read(run_dir: Path | str | None) -> dict | None:
    """The trace of ``run_dir`` in the harness's shape; None when the run has none, ``{"error": ...}`` when it cannot be read."""
    if run_dir is None or not (Path(run_dir) / FILE).is_file():
        return None
    run = Path(run_dir)
    try:
        model = shiploop_trace.build(run)
        state = store.read_record(run / "state.md")
    except Exception as exc:  # noqa: BLE001 - a record, never a refusal: the reader falls back to the stream
        return {"error": f"{type(exc).__name__}: {' '.join(str(exc).split())[:300]}"}
    facts, events = model["run"], model["events"]
    failures, completes, packets, hooks = [], [], {}, []
    for event in events:
        owner = event.get("action") or event.get("for_action")
        if event["kind"] == "command" and event.get("verb") == "complete" and not event.get("check_only"):
            completes.append({"i": event["i"], "action": event.get("action") or (event.get("cursor") or [None])[0],
                              "accepted": event.get("exit") == 0})
        if event["kind"] == "command" and event.get("exit") not in (0, None) and event.get("verb") not in ROUTED_VERBS:
            before = (event.get("stage") or [None])[0]
            text = shiploop_trace._screened(event["error"]) if isinstance(event.get("error"), str) else None
            failures.append({"i": event["i"], "ts": event.get("ts"), "at": event.get("at"), "verb": event.get("verb") or "unknown",
                             "exit": event.get("exit"),
                             "check_only": bool(event.get("check_only") or event.get("verb") == "check"),
                             "action": event.get("action") or (event.get("cursor") or [None])[0] or owner,
                             "stage": before, "text": text, "line": first_line(text)})
        elif event["kind"] == "packet" and owner:
            packets.setdefault(owner, []).append({key: event.get(key) for key in (
                "i", "ts", "at", "stage", "item", "reviewed", "rev", "chars", "printed", "whole", "sha", "file", "head_file",
                "repeat")})
        elif event["kind"] == "hook":
            hooks.append({"i": event["i"], "ts": event.get("ts"), "at": event.get("at"), "action": owner,
                          "decision": event.get("decision"), "why": event.get("why"), "host": event.get("host"),
                          "text": shiploop_trace._screened(event["text"]) if isinstance(event.get("text"), str) else None})
    # Steps the trace did not see are the reader's `accepted` events; the harness's seeded ones were never the model's.
    unseen = [event.get("action") for event in events if event["kind"] == "accepted"]
    missed = [action for action in unseen if not _seeded(state, action)]
    reason = None
    if facts.get("capped"):
        reason = "the trace reached its size cap and stopped growing"
    elif missed:
        reason = (f"{len(missed)} accepted step{'s' if len(missed) != 1 else ''} the model ran before the trace began "
                  f"(traced since {facts.get('traced_since')})")
    return {
        "file": FILE, "covers": reason is None, "partial": reason, "traced_since": facts.get("traced_since"),
        "untraced_steps": facts.get("untraced_steps"), "seeded_steps": len(unseen) - len(missed),
        "failures": failures, "completes": completes, "packets": packets, "hooks": hooks, "counts": model["counts"],
        "run_dir": str(run), "status": facts.get("status"), "notes": model.get("notes") or [],
    }


def covers(traced: dict | None) -> bool:
    """Whether ``traced`` (``read``'s value) holds every refusal of a navigator command that loaded the run
    (``metrics.outside_trace`` names the others)."""
    return bool(traced) and "error" not in traced and bool(traced.get("covers"))


def why_not(traced: dict | None) -> str:
    """Why a reader keeps its stream source for this run."""
    if traced is None:
        return f"the run has no {FILE} (ShipLoop before 1.12.0)"
    if "error" in traced:
        return f"{FILE} could not be read: {traced['error']}"
    return f"{FILE} does not cover the run: {traced.get('partial')}"


def metric_failure(row: dict) -> dict:
    """One failure as metrics.json's ``shiploop_failures`` lists it: verb, exit and first line; a failed check is flagged, and a
    failure only the host stream shows (``source`` events.jsonl, see ``metrics.outside_trace``) names that source."""
    return {"verb": row["verb"], "exit": row["exit"], "line": row["line"], **({"check_only": True} if row.get("check_only") else {}),
            **({"source": "events.jsonl"} if row.get("source") == "events.jsonl" else {})}


def sent_texts(run_dir: Path, traced: dict) -> dict[str, list[str]]:
    """{action: the distinct texts its packet was sent with, oldest first}; a reprint of the same text is not a new one."""
    texts: dict[str, list[str]] = {}
    for action, sends in traced["packets"].items():
        for send in sends:
            if send.get("repeat") or not send.get("file"):
                continue
            try:
                texts.setdefault(action, []).append((Path(run_dir) / send["file"]).read_text(errors="replace"))
            except OSError:
                continue
    return texts


def _check(verdict: str, evidence: str, lines: list | None = None) -> dict:
    return {"verdict": verdict, "evidence": evidence, "lines": lines or []}


def checks(traced: dict | None) -> dict | None:
    """Three live behaviours the trace's fixtures prove (docs/shiploop-run-trace-journal.md, 2026-10-28), each read from
    the trace as {verdict, evidence, lines}: ``pass``, ``fail``, ``open`` (a note the run had not delivered when it
    stopped short of done) or ``not exercised`` (the run never did the thing, which is not a pass).

    - ``keepalive_text``: every keepalive stop decision that continued a turn recorded the text it put into the turn;
    - ``packet_copies``: every printed packet names a kept copy (``packets/sent/<sha>.md``) whose text has that hash, the
      copy the Run Review page reads; reprints are counted (``lines``). Until 2026-10-28 this was ``packet_reprint`` and
      read identical reprints only, which a fresh session's ``next`` reprint never is;
    - ``owner_note``: every owner note was delivered (a step accepted with it shown); ``--owner-note-at`` writes one mid-step.
    """
    if traced is None or "error" in traced:
        return None
    def lines(rows: list[dict]) -> list:
        return [row.get("i") for row in rows]

    continued = [hook for hook in traced["hooks"] if hook.get("decision") == "continue"]
    silent = [hook for hook in continued if not (hook.get("text") or "").strip()]
    keepalive = (_check("not exercised", "no stop decision continued a turn") if not continued else
                 _check("fail", f"{len(silent)} of {len(continued)} continuations recorded no text", lines(silent)) if silent else
                 _check("pass", f"{len(continued)} continuation{'s' if len(continued) != 1 else ''} with text; first: "
                                f"{first_line(continued[0]['text'], 120)}", lines(continued)))
    sends = [send for rows in traced["packets"].values() for send in rows]
    repeats = [send for send in sends if send.get("repeat")]
    broken = []
    for send in sends:
        try:
            text = (Path(traced["run_dir"]) / str(send.get("file"))).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        if text is None or not send.get("sha") or hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] != send["sha"]:
            broken.append(send)
    copies = (_check("not exercised", "no packet was printed") if not sends else
              _check("fail", f"{len(broken)} of {len(sends)} prints name no kept copy with their hash", lines(broken))
              if broken else _check("pass", f"{len(sends)} print{'s' if len(sends) != 1 else ''} ({len(repeats)} "
                                            f"reprint{'s' if len(repeats) != 1 else ''}), each with its kept copy",
                                    lines(repeats)))
    notes = traced.get("notes") or []
    undelivered = [note for note in notes if note.get("state") != "delivered"]
    told = "; ".join(f"{note['id']} {note.get('state')}" + (f" by {note['delivered_by']}" if note.get("delivered_by") else "")
                     + (f", held once in {', '.join(map(str, note['held_in']))}" if note.get("held_in") else "")
                     + ("" if note.get("cited") is None else ", cited" if note["cited"] else ", not cited") for note in notes)
    note = (_check("not exercised", "no owner note was written to the run") if not notes else
            _check("pass", told) if not undelivered else
            _check("fail" if traced.get("status") == "done" else "open", told))
    return {"keepalive_text": keepalive, "packet_copies": copies, "owner_note": note}


def checks_line(found: dict | None) -> str | None:
    """The run's printed line for ``checks``: each check's verdict, the evidence of any that is not ``not exercised``."""
    if not found:
        return None
    return "; ".join(f"{name.replace('_', ' ')} {row['verdict']}" + ("" if row["verdict"] == "not exercised" else
                                                                       f" ({row['evidence']})") for name, row in found.items())


def summary(traced: dict | None, stream_failures: int | None = None) -> dict | None:
    """The record metrics.json keeps of the trace: what it counted, whether it covers the run, the stream's own count, and the
    live checks (``checks``)."""
    if traced is None:
        return None
    if "error" in traced:
        return {"file": FILE, "error": traced["error"]}
    counts = traced["counts"]
    refusals = [f for f in traced["failures"] if not f["check_only"]]
    notes = traced.get("notes") or []
    return {"file": FILE, "covers": traced["covers"], "partial": traced["partial"], "traced_since": traced["traced_since"],
            "untraced_steps": traced["untraced_steps"], "seeded_steps": traced["seeded_steps"],
            "commands": counts.get("commands"), "refusals": len(refusals), "checks_failed": counts.get("checks_failed"),
            "packets": counts.get("packets"), "reprints": counts.get("reprints"),
            "continuations": counts.get("continuations"), "stops": counts.get("stops"),
            "notes": {"written": len(notes), "held": sum(bool(n.get("held_in")) for n in notes),
                      "delivered": sum(n.get("state") == "delivered" for n in notes), "cited": sum(bool(n.get("cited")) for n in notes)},
            "stream_failures": stream_failures, "checks": checks(traced)}
