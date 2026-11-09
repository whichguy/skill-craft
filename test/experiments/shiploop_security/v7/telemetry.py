"""Retain and replay invocation-bound parent Codex usage for the private cohort."""

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re


FIELDS = {
    "input_tokens": "input_tokens",
    "cache_read_input_tokens": "cached_input_tokens",
    "output_tokens": "output_tokens",
    "reasoning_tokens": "reasoning_output_tokens",
}
REQUIRED = ("input_tokens", "output_tokens")
ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
CONTEXT = ("cwd", "model", "effort", "started_at", "ended_at", "resumed_thread_id")
TERMINALS = ("turn.completed", "turn.failed")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _need(condition, reason):
    if not condition:
        raise ValueError(reason)


def _id(value):
    return isinstance(value, str) and ID.fullmatch(value) is not None


def _stamp(value):
    _need(isinstance(value, str), "missing timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _need(stamp.utcoffset() is not None, "timestamp lacks timezone")
    return stamp


def _json_object(pairs):
    row = {}
    for key, value in pairs:
        _need(key not in row, "duplicate JSON key")
        row[key] = value
    return row


def _no_constant(_):
    raise ValueError("non-JSON number")


def _rows(data, start=0, *, stop_at_malformed=False):
    """Keep absolute half-open byte offsets; a torn line cannot be a receipt."""
    rows, malformed = [], []
    cursor = start
    for line in data.splitlines(keepends=True):
        location = [cursor, cursor + len(line)]
        cursor = location[1]
        try:
            _need(line.endswith(b"\n"), "unterminated JSONL")
            row = json.loads(line, object_pairs_hook=_json_object, parse_constant=_no_constant)
            _need(isinstance(row, dict) and isinstance(row.get("type"), str), "missing event type")
        except (ValueError, RecursionError):
            malformed.append(location)
            if stop_at_malformed:
                break
        else:
            rows.append((location, row))
    return rows, malformed


def _bounds(value, size):
    return (isinstance(value, list) and len(value) == 2
            and all(type(x) is int for x in value)
            and 0 <= value[0] <= value[1] <= size)


def _raw_invocation(data, bounds):
    _need(_bounds(bounds, len(data)), "invalid stdout range")
    start, end = bounds
    _need(not start or data[start - 1:start] == b"\n", "stdout begins inside a line")
    source = data[start:end]
    rows, malformed = _rows(source, start)
    threads = [(span, row.get("thread_id")) for span, row in rows if row["type"] == "thread.started"]
    _need(len(threads) == 1 and rows[0][0] == threads[0][0] and _id(threads[0][1]),
          "stdout does not identify one parent thread")
    thread = threads[0][1]
    _need(all(row.get("thread_id", thread) == thread for _, row in rows), "mixed stdout threads")
    return source, rows, malformed, thread


def _context(context):
    _need(isinstance(context, dict) and all(k in context for k in CONTEXT),
          "missing invocation controls")
    context = {key: context[key] for key in CONTEXT}
    _need(all(isinstance(context[k], str) and context[k] for k in ("cwd", "model", "effort"))
          and Path(context["cwd"]).is_absolute(), "invalid cwd or model controls")
    _need(context["resumed_thread_id"] is None or _id(context["resumed_thread_id"]), "invalid resume id")
    start, end = (_stamp(context[key]) for key in ("started_at", "ended_at"))
    _need(start <= end, "reversed invocation window")
    return context, start, end


def _local_file(root, path):
    # Reject symlinks throughout the path, including links inside the owned home.
    return path.is_relative_to(root) and path.resolve() == path and path.is_file()


def _evidence_path(trial, index, thread):
    return trial / "native-usage" / f"{index:03d}-{thread}.jsonl"


def capture_native_usage(trial, codex_home, sessions, invocation_context):
    """Call after stdout drain and process exit; attach the receipt to sessions[-1]."""
    receipt = {}
    try:
        _need(bool(sessions), "no invocation to capture")
        trial = Path(trial).resolve()
        home = Path(codex_home).absolute()
        _need(home != trial and home.is_relative_to(trial) and home.resolve() == home,
              "Codex home is not owned by the trial")
        context, opened, closed = _context(invocation_context)
        receipt["invocation_context"] = context
        raw_path = trial / "raw-events.jsonl"
        _need(_local_file(trial, raw_path), "missing owned stdout")
        raw = raw_path.read_bytes()
        bounds = sessions[-1].get("raw_usage_bytes")
        source, _, _, thread = _raw_invocation(raw, bounds)
        receipt.update(raw_usage_bytes=bounds, raw_sha256=_sha(source), thread_id=thread)
        _need(bounds[1] == len(raw), "capture is not at invocation end")
        resumed = context["resumed_thread_id"]
        _need((len(sessions) == 1 and resumed is None)
              or (len(sessions) > 1 and resumed == thread), "stdout disagrees with resume controls")
        matches = list((home / "sessions").glob(
            f"[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/rollout-*-{thread}.jsonl"
        ))
        _need(len(matches) == 1 and _local_file(home, matches[0]), "missing or ambiguous owned rollout")
        native = matches[0]
        # A continuation must still address the exact prior rollout.
        prior_end = 0
        if resumed is not None:
            previous = sessions[-2].get("native_usage", {})
            _need(not previous.get("error") and previous.get("thread_id") == thread
                  and previous.get("native_source") == str(native.relative_to(trial)),
                  "continuation has no matching prior capture")
            prior_end = previous.get("native_bytes", [None, None])[1]
        before = native.stat()
        data = native.read_bytes()
        after = native.stat()
        _need((before.st_ino, before.st_size, before.st_mtime_ns)
              == (after.st_ino, len(data), after.st_mtime_ns), "rollout changed during capture")
        if prior_end:
            _need(type(prior_end) is int and 0 < prior_end < len(data)
                  and _sha(data[:prior_end]) == previous.get("native_sha256"),
                  "continuation did not extend the prior capture")
        else:
            _need(resumed is None, "missing continuation offset")
        _native_metadata(data, prior_end, thread, context, opened, closed)
        copy = _evidence_path(trial, len(sessions), thread)
        copy.parent.mkdir(mode=0o700, exist_ok=True)
        _need(copy.parent.resolve() == copy.parent, "capture directory escapes trial")
        # Exclusive create prevents an accidental recapture from overwriting evidence.
        with open(copy, "xb", opener=_private_create) as output:
            output.write(data)
        receipt.update(native_source=str(native.relative_to(trial)),
                       native_copy=str(copy.relative_to(trial)), native_sha256=_sha(data),
                       native_bytes=[prior_end, len(data)])
    except (OSError, ValueError, TypeError, AttributeError, IndexError, RuntimeError) as exc:
        receipt["error"] = str(exc)
    return receipt


def _private_create(path, flags):
    return os.open(path, flags | os.O_NOFOLLOW, 0o600)


def _metrics(values):
    _need(isinstance(values, dict), "missing token metrics")
    result = {}
    for key, name in FIELDS.items():
        value = values.get(name)
        _need(value is None and key not in REQUIRED or type(value) is int and value >= 0,
              f"invalid {name}")
        result[key] = value
    for subset, total in (("cache_read_input_tokens", "input_tokens"),
                          ("reasoning_tokens", "output_tokens")):
        _need(result[subset] is None or result[subset] <= result[total], "invalid usage subset")
    return result


def _compatible(left, right):
    return all(left[k] == right[k] or None in (left[k], right[k]) for k in FIELDS)


def _delta(current, baseline):
    return {k: current[k] - baseline[k] if None not in (current[k], baseline[k]) else None
            for k in FIELDS}


def _same_cwd(actual, expected):
    return (isinstance(actual, str) and Path(actual).is_absolute()
            and Path(actual) == Path(expected))


def _native_metadata(data, begin, thread, context, opened, closed):
    metadata_end = data.find(b"\n") + 1
    metadata, _ = _rows(data[:metadata_end])
    _need(metadata and metadata[0][1]["type"] == "session_meta", "missing native session metadata")
    meta_span, meta = metadata[0]
    payload = meta.get("payload")
    _need(isinstance(payload, dict) and payload.get("id") == thread and payload.get("source") == "exec"
          and payload.get("session_id", thread) == thread
          and _same_cwd(payload.get("cwd"), context["cwd"]), "wrong native parent metadata")
    created = _stamp(meta.get("timestamp"))
    _need(opened <= created <= closed if not begin else created <= opened,
          "native session metadata outside invocation window")
    return meta_span


def _native_turn(data, begin, thread, context, opened, closed, prior):
    meta_span = _native_metadata(data, begin, thread, context, opened, closed)
    start = max(begin, meta_span[1])
    rows, malformed = _rows(data[start:], start, stop_at_malformed=True)
    task = turn = terminal = observed = counter = counter_span = None
    baseline = {key: 0 for key in FIELDS} if not begin else None
    previous_ordinal = None
    for span, row in rows:
        stamp = _stamp(row["timestamp"])
        _need(opened <= stamp <= closed, "native record outside invocation window")
        kind, payload = row["type"], row.get("payload")
        ordinal = row.get("ordinal")
        if ordinal is not None:
            _need(type(ordinal) is int and (previous_ordinal is None or previous_ordinal < ordinal),
                  "duplicate or disordered native ordinal")
            previous_ordinal = ordinal
        _need(kind != "session_meta" and isinstance(payload, dict), "mixed native session records")
        _need(all(payload.get(key, thread) == thread for key in ("thread_id", "session_id")),
              "wrong thread in native record")
        event = payload.get("type") if kind == "event_msg" else None
        if event == "task_started":
            _need(task is None and _id(payload.get("turn_id")), "duplicate or invalid native start")
            task = (span, payload["turn_id"])
        if kind == "turn_context":
            _need(task is not None and turn is None and payload.get("turn_id") == task[1]
                  and payload.get("root_turn_id", task[1]) == task[1]
                  and _same_cwd(payload.get("cwd"), context["cwd"])
                  and all(payload.get(k) == context[k] for k in ("model", "effort")),
                  "duplicate or mismatched native turn context")
            turn = span
        if task is not None:
            _need(all(payload.get(key, task[1]) == task[1] for key in ("turn_id", "root_turn_id")),
                  "mixed native turns")
        if event in ("task_complete", "turn_aborted"):
            _need(turn is not None and terminal is None and payload.get("turn_id") == task[1],
                  "duplicate or invalid native terminal")
            terminal = (span, event)
        if event != "token_count":
            continue
        _need(turn is not None and terminal is None, "token count outside native turn")
        info = payload.get("info")
        if info is None:  # Context-window notification without token metrics.
            continue
        _need(isinstance(info, dict), "malformed native token count")
        current = _metrics(info.get("total_token_usage"))
        if baseline is None:
            # A resumed process may reset its counters or carry forward the last
            # observed cumulative total. Its first request distinguishes the two.
            last = _metrics(info.get("last_token_usage"))
            _need(prior is not None, "no prior native counter for resume")
            reset = _compatible(current, last)
            carried = _compatible(_delta(current, prior), last)
            # A repeated prior total with its old last-call count can look like
            # a reset. Without a distinguishable boundary it is not new usage.
            repeated_prior = all(current[k] == prior[k] for k in REQUIRED)
            _need((reset or carried) and not (reset and not carried and repeated_prior),
                  "ambiguous continuation counter")
            if reset and carried:
                _need(all(prior[k] == 0 for k in REQUIRED), "ambiguous continuation baseline")
                baseline = {k: 0 if prior[k] == 0 else None for k in FIELDS}
            else:
                baseline = {k: 0 for k in FIELDS} if reset else prior
        _need(counter is None or all(current[k] >= counter[k] for k in REQUIRED),
              "native token counters moved backwards")
        candidate = _delta(current, baseline)
        _need(all(candidate[k] >= 0 for k in REQUIRED), "native count predates its baseline")
        observed = {k: value if value is None or value >= 0 else None for k, value in candidate.items()}
        counter, counter_span = current, span
    _need(turn is not None, "missing bound native turn context")
    return {
        "session_meta_bytes": meta_span, "task_started_bytes": task[0],
        "turn_context_bytes": turn, "turn_id": task[1], "token_count_bytes": counter_span,
        "native_terminal_bytes": terminal[0] if terminal else None,
        "native_terminal_type": terminal[1] if terminal else None,
        "native_malformed_bytes": malformed,
        "observed": observed, "counter": counter, "baseline": baseline,
    }


def _replay(trial, raw, session, index, previous):
    bounds = session.get("raw_usage_bytes")
    receipt = {"range": bounds, "fields": dict.fromkeys(FIELDS), "complete": False, "observed": None}
    next_prior = None
    try:
        source, rows, malformed, thread = _raw_invocation(raw, bounds)
        terminals = [(span, row) for span, row in rows if row["type"] in TERMINALS]
        starts = [span for span, row in rows if row["type"] == "turn.started"]
        receipt.update(thread_id=thread, raw_malformed_bytes=malformed,
                       terminal_events=len(terminals))
        captured = session.get("native_usage")
        _need(isinstance(captured, dict), "missing native capture")
        _need(not captured.get("error"), captured.get("error"))
        _need(captured.get("thread_id") == thread and captured.get("raw_sha256") == _sha(source)
              and captured.get("raw_usage_bytes") == bounds, "capture differs from raw invocation")
        context, opened, closed = _context(captured.get("invocation_context"))
        copy = _evidence_path(trial, index, thread)
        _need(captured.get("native_copy") == str(copy.relative_to(trial))
              and _local_file(trial, copy), "missing or mismatched native copy")
        data = copy.read_bytes()
        _need(_sha(data) == captured.get("native_sha256"), "native copy hash mismatch")
        offset = captured.get("native_bytes")
        _need(_bounds(offset, len(data)) and offset[1] == len(data), "invalid native capture range")
        begin = offset[0]
        if index == 1:
            _need(begin == 0 and context["resumed_thread_id"] is None, "invalid first capture")
        else:
            _need(previous is not None and begin > 0 and context["resumed_thread_id"] == thread
                  and previous["thread"] == thread and previous["end"] == begin
                  and previous["closed"] <= opened
                  and previous["source"] == captured.get("native_source")
                  and _sha(data[:begin]) == previous["sha"], "unbound native continuation")
        native = _native_turn(data, begin, thread, context, opened, closed,
                              previous["counter"] if previous else None)
        _need(all(row.get("turn_id", native["turn_id"]) == native["turn_id"] for _, row in rows),
              "stdout turn disagrees with native turn")
        _need(not previous or native["turn_id"] not in previous["turns"],
              "duplicate native turn across invocations")
        receipt.update(native, native_copy=captured["native_copy"], native_sha256=captured["native_sha256"],
                       native_source=captured.get("native_source"), native_bytes=offset,
                       raw_sha256=captured["raw_sha256"], invocation_context=context)
        if not native["native_malformed_bytes"]:
            next_prior = {"thread": thread, "end": len(data), "sha": captured["native_sha256"],
                          "closed": closed, "counter": native["counter"],
                          "source": captured.get("native_source"),
                          "turns": (previous["turns"] if previous else set()) | {native["turn_id"]}}
        _need(not malformed and not native["native_malformed_bytes"], "malformed JSONL")
        _need(len(starts) == 1 and len(terminals) == 1
              and starts[0][0] < terminals[0][0][0] and terminals[0][0] == rows[-1][0],
              "missing, duplicate or misordered stdout turn events")
        terminal_span, terminal = terminals[0]
        receipt.update(type=terminal["type"], raw_terminal_bytes=terminal_span)
        _need(terminal["type"] == "turn.completed" and native["native_terminal_type"] == "task_complete"
              and native["observed"] is not None, "turn lacks a completed usage boundary")
        final = _metrics(terminal.get("usage"))
        observed = native["observed"]
        if _compatible(final, observed):
            local = final
        elif begin and _compatible(final, native["counter"]):
            local = _delta(final, native["baseline"])
        else:
            raise ValueError("terminal usage disagrees with native count")
        _need(_compatible(local, observed), "terminal usage disagrees with invocation count")
        # Required totals agree in both sources. An optional value must be
        # available in both sources to be reported as a complete metric.
        receipt["fields"] = {k: local[k] if observed[k] is not None else None for k in FIELDS}
        receipt["complete"] = True
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
        receipt["error"] = str(exc)
    return receipt, next_prior


def _sum(rows):
    return {k: sum(row[k] for row in rows) if all(row[k] is not None for row in rows) else None
            for k in FIELDS}


def usage(raw_path, sessions, expected):
    """Replay captured bytes; aggregate each invocation's usage once."""
    path = Path(raw_path).absolute()
    trial = path.parent.resolve()
    path = trial / path.name
    try:
        raw = path.read_bytes() if _local_file(trial, path) else b""
    except OSError:
        raw = b""
    receipts, observed, previous = [], [], None
    cursor = 0
    ranges_bound = True
    for index, session in enumerate(sessions, 1):
        session = session if isinstance(session, dict) else {}
        bounds = session.get("raw_usage_bytes")
        if not _bounds(bounds, len(raw)) or bounds[0] != cursor:
            ranges_bound = False
            previous = None
            receipts.append({"range": bounds, "complete": False, "error": "noncontiguous raw invocation"})
            continue
        cursor = bounds[1]
        receipt, previous = _replay(trial, raw, session, index, previous)
        receipts.append(receipt)
        if receipt["observed"] is not None:
            observed.append(receipt["observed"])
    ranges_bound = ranges_bound and cursor == len(raw)
    complete = (type(expected) is int and expected > 0 and expected == len(receipts)
                and ranges_bound and all(row["complete"] for row in receipts))
    measured = _sum([row["fields"] for row in receipts]) if complete else None
    return {
        "source": "bound parent Codex stdout and native rollout JSONL", "raw_sha256": _sha(raw),
        "expected_sessions": expected, "ranges_bound": ranges_bound, "sessions": receipts,
        "totals": measured if complete else dict.fromkeys(FIELDS), "coverage_complete": complete,
        "usage_complete": complete, "measured_usage": measured,
        "observed_usage": _sum(observed) if observed else None, "cost_usd": None,
    }


LEDGER = "started-invocations.jsonl"
LEDGER_SCHEMA = "shiploop-security-started-invocation/v1"


def append_start(trial, binding, *, cwd, home, model, effort, started_at, resumed, raw_start, argv):
    """Record an admitted spawn before Popen; a failed spawn remains accounted for."""
    trial = Path(trial).resolve()
    path = trial / LEDGER
    rows = read_starts(trial, binding) if os.path.lexists(path) else []
    row = {"type": LEDGER_SCHEMA, "binding": binding, "sequence": len(rows) + 1,
           "cwd": str(Path(cwd).resolve()), "home": str(Path(home).resolve().relative_to(trial)),
           "model": model, "effort": effort, "started_at": started_at,
           "resumed_thread_id": resumed, "raw_start": raw_start,
           "argv_sha256": _sha(json.dumps(argv, separators=(",", ":")).encode())}
    raw = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with open(path, "ab", opener=_private_create) as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return row


def read_starts(trial, binding):
    trial = Path(trial).resolve()
    path = trial / LEDGER
    _need(_local_file(trial, path), "missing or linked started-invocation ledger")
    data = path.read_bytes()
    rows, malformed = _rows(data)
    _need(not malformed and rows, "invalid started-invocation ledger")
    previous = None
    result = []
    for sequence, (_, row) in enumerate(rows, 1):
        _need(row.get("type") == LEDGER_SCHEMA and row.get("binding") == binding
              and type(row.get("sequence")) is int and row["sequence"] == sequence
              and type(row.get("raw_start")) is int and row["raw_start"] >= 0
              and bool(re.fullmatch("[0-9a-f]{64}", row.get("argv_sha256", ""))),
              "unbound started-invocation row")
        home = Path(row["home"])
        _need(home.parts and not home.is_absolute() and ".." not in home.parts
              and Path(row["cwd"]).is_absolute(), "unowned start controls")
        stamp = _stamp(row["started_at"])
        if previous:
            _need(stamp >= _stamp(previous["started_at"]) and row["raw_start"] >= previous["raw_start"]
                  and _id(row.get("resumed_thread_id")), "invalid continuation launch")
        else:
            _need(row.get("resumed_thread_id") is None and row["raw_start"] == 0,
                  "invalid first launch")
        result.append(row)
        previous = row
    return result


def _matches_start(session, row):
    captured = session.get("native_usage", {})
    context = captured.get("invocation_context", {})
    source = Path(captured.get("native_source") or ".")
    home = Path(row["home"])
    bounds = session.get("raw_usage_bytes")
    return (session.get("launch") == row and isinstance(bounds, list) and len(bounds) == 2
            and bounds[0] == row["raw_start"]
            and source.is_relative_to(home / "sessions") and ".." not in source.parts
            and all(context.get(k) == row[k] for k in CONTEXT if k != "ended_at"))


def ledger_usage(trial, sessions, binding, *, roles):
    """Use only the independently retained launch ledger to establish completeness."""
    trial = Path(trial).resolve()
    raw = trial / "raw-events.jsonl"
    problem = None
    starts = []
    try:
        starts = read_starts(trial, binding)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        problem = "invalid_started_ledger"
    prefix = []
    for index, (session, start) in enumerate(zip(sessions, starts)):
        try:
            if not isinstance(session, dict) or not _matches_start(session, start):
                break
            if any(start.get(key) != roles[key] for key in ("model", "effort")):
                break
            if index + 1 < len(starts) and session["raw_usage_bytes"][1] != starts[index + 1]["raw_start"]:
                break
        except (TypeError, KeyError, AttributeError):
            break
        prefix.append(session)
    result = usage(raw, prefix, len(starts))
    if len(sessions) != len(starts):
        problem = problem or "started_session_count_mismatch"
    if len(prefix) != len(sessions):
        problem = problem or "unbound_invocation"
    if problem:
        result.update(totals=dict.fromkeys(FIELDS), coverage_complete=False,
                      usage_complete=False, measured_usage=None)
    result.update(ledger_problem=problem,
                  started_invocations=len(starts) if problem != "invalid_started_ledger" else None,
                  bound_invocations=sum("native_sha256" in item for item in result["sessions"]),
                  complete_invocations=sum(item["complete"] for item in result["sessions"]))
    return result
