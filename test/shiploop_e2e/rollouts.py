"""A Codex run's per-call context, read from the rollout files Codex keeps under its CODEX_HOME.

Codex's own event stream carries no per-call usage and no compaction. Each thread writes one rollout file,
``<run>/home/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl``, a record per line, and three record types matter:

  token_usage_record   one per model request: thread_id, session_id, response_id and ``usage`` (total_tokens is
                       the request's input plus its output, which is the context the thread held after it)
  compacted            one per compaction; ``compaction_response_id`` names the token_usage_record that was the
                       compaction request
  event_msg            payload.type token_count: info.model_context_window (and last_token_usage)

Counting rule (read from the Luna 1.16.1 battleship run, 168 MB, and tested on a synthetic fixture):

* A **call** is a ``token_usage_record`` that is not a compaction request. The request is the record whose
  ``response_id`` equals a ``compacted`` record's ``compaction_response_id`` in the same file. It directly
  precedes that ``compacted`` record, has no ``token_count`` event of its own, and holds the whole context to
  summarise it (253,846 tokens against the heaviest real call's 250,042), so counting it would inflate both the
  call count (2,599 records against 2,565 calls in the main thread) and the peak.
* ``token_count`` events are never counted: after a ``compacted`` record one reports the context after the
  compaction (input 0), and 35 more in the three Luna files repeat the previous event's cumulative total.
  They supply only the context window.
* A **compaction** is a ``compacted`` record whose request is a record in the same file. A sub-agent's rollout
  begins with a copy of its parent's last ``compacted`` record, stamped at the fork, whose request lives in the
  parent's file: that one is inherited history and is not counted.
* The **main thread** is every record whose thread_id equals its session_id (the root thread; a resumed run is a
  new root session in a new file, and counts too). Records of any other thread are sub-agents'. The headline
  and the per-stage figures are the main thread's. Sub-agent work is not dropped: it is reported once, for the
  whole run, under ``subagents`` (calls, peak, compactions), because a stage window cannot tell a sub-agent's
  work from the thread that waited for it.

Records are read one line at a time and only calls, compactions and the window are kept (a few thousand small
tuples), so memory does not grow with the file. A line that is not JSON (the half-written last line of a rollout
a live run is still writing) is skipped.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

NO_ROLLOUTS = ("no rollout-*.jsonl under home/.codex/sessions: Codex records per-call usage and compactions only "
               "in those files, not in its events")
NO_CALLS = "the rollouts hold no main-thread token_usage_record, so no call was recorded"


def rollout_files(out: Path) -> list[Path]:
    """The rollout files of a run output directory, oldest name first (the harness gives Codex a run-owned home)."""
    root = out / "home" / ".codex" / "sessions"
    return sorted(root.rglob("rollout-*.jsonl")) if root.is_dir() else []


def _records(path: Path):
    with path.open(errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def _epoch(text: object) -> float | None:
    if not isinstance(text, str):
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _read(path: Path) -> dict:
    """One rollout's calls, compactions and window: {"calls": [(t, total, main)], "compactions": [(t, main)], ...}."""
    usage: list[tuple] = []  # (response id, t, total, main) in file order
    compactions: list[tuple] = []  # (compaction_response_id, t)
    windows = {True: None, False: None}  # the last window a token_count reported, by thread kind
    current = None  # whether the latest token_usage_record was the main thread's: a token_count follows its call
    for record in _records(path):
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        kind = record.get("type")
        if kind == "token_usage_record":
            thread, session = payload.get("thread_id"), payload.get("session_id")
            # Sub-agent only on positive evidence: both ids present and different.
            current = not (isinstance(thread, str) and isinstance(session, str) and thread != session)
            used = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
            usage.append((payload.get("response_id"), _epoch(record.get("timestamp")),
                          _number(used.get("total_tokens")), current))
        elif kind == "compacted":
            compactions.append((payload.get("compaction_response_id"), _epoch(record.get("timestamp"))))
        elif kind == "event_msg" and payload.get("type") == "token_count" and current is not None:
            info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
            if _number(info.get("model_context_window")):
                windows[current] = info["model_context_window"]
    requests = {response for response, _, _, _ in usage if response is not None} & \
        {response for response, _ in compactions if response is not None}
    kind_of = {response: main for response, _, _, main in usage if response in requests}
    return {"calls": [(t, total, main) for response, t, total, main in usage if response not in requests],
            # Own compactions only: the request is in this file, and says which thread was compacted.
            "compactions": [(t, kind_of[response]) for response, t in compactions if response in requests],
            "windows": windows}


def _share(peak: int | None, window: int | None) -> float | None:
    return round(100 * peak / window, 1) if peak is not None and window else None


def rollout_context(out: Path, windows: list | None = None) -> dict:
    """The run's context, main thread first, or ``{"unmeasured": reason}`` when no rollout can show it.

    ``out`` is the run's output directory (the one holding events.jsonl and home/). ``windows`` is one
    ``[start, end]`` pair of epoch seconds per stage row, ``None`` for a stage with no known window; a record
    belongs to a window when start < t <= end, the rule the harness uses for turns. Returns ``window`` (the
    model context window a main-thread token_count reported), ``calls``, ``peak`` (the largest total_tokens of a
    call), ``peakPct`` (peak as a percentage of the window), ``compactions``, ``subagents`` and ``perStage``
    (one {calls, peak, peakPct, compactions} per window, or None where the window was None).
    """
    files = rollout_files(out)
    if not files:
        return {"unmeasured": NO_ROLLOUTS}
    calls: list[tuple] = []
    compactions: list[tuple] = []
    window = None
    for path in files:
        found = _read(path)
        calls += found["calls"]
        compactions += found["compactions"]
        window = found["windows"][True] or window
    main = [(t, total) for t, total, is_main in calls if is_main]
    if not main:
        return {"unmeasured": NO_CALLS}
    side = [total for _, total, is_main in calls if not is_main and total is not None]

    def figures(t_calls: list[tuple], t_compactions: list[float | None]) -> dict:
        peak = max((total for _, total in t_calls if total is not None), default=None)
        return {"calls": len(t_calls), "peak": peak, "peakPct": _share(peak, window),
                "compactions": len(t_compactions)}

    own = [t for t, is_main in compactions if is_main]
    per_stage = [None if w is None else figures(
        [(t, total) for t, total in main if t is not None and w[0] < t <= w[1]],
        [t for t in own if t is not None and w[0] < t <= w[1]]) for w in (windows or [])]
    return {"window": window, **figures(main, own), "perStage": per_stage,
            "subagents": {"calls": sum(1 for _, _, is_main in calls if not is_main),
                          "peak": max(side, default=None),
                          "compactions": sum(1 for _, is_main in compactions if not is_main)}}
