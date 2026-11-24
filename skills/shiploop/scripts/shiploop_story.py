"""Source-derived display story. This projection never decides acceptance or drives work."""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
import shiploop_observation_io as capture
import shiploop_store as store

# Guard/display limits only: optional observer reads and rendered rows, never workflow limits.
STREAM_BYTES = 32 * 1024 * 1024
EVIDENCE_BYTES = 256 * 1024
STORY_ROWS = 2000
EVIDENCE_FILES = 160


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def capture_core(root, *, consistency="shared-lock"):
    """Capture under a shared lock, or explicitly qualify a standalone archive read.

    The archive caller checks for pending transactions before and after capture.
    Parsing happens after capture; this helper never creates locks or recovers.
    """
    state, stamp = capture._read_beneath(root, "state.md", 4 * 1024 * 1024)
    observed_at = utc()
    timeline_capture = capture.capture(root, "timeline.json", 1024 * 1024, observed_at)
    return {"state_raw": state, "state_mtime": stamp, "timeline_raw": timeline_capture["raw"],
            "timeline_source": timeline_capture["source"], "observed_at": observed_at,
            "consistency": consistency}


def core_values(core):
    state = store.loads(core["state_raw"].decode("utf-8"))
    try:
        timeline = store.observation_json(json.loads(core["timeline_raw"]))
        if (not isinstance(timeline, dict) or not isinstance(timeline.get("accepted", {}), dict)):
            timeline = {}
            if core.get("timeline_source"):
                core["timeline_source"].update(status="partial", message="Malformed optional timeline; timestamps unavailable.")
    except (ValueError, UnicodeError, RecursionError):
        timeline = {}
        if core.get("timeline_source") and core["timeline_source"]["status"] == "ok":
            core["timeline_source"].update(status="partial", message="Malformed optional timeline; timestamps unavailable.")
    timeline, malformed = normalise_timeline(timeline)
    if malformed and core.get("timeline_source"):
        core["timeline_source"].update(status="partial", message="Malformed optional timeline timestamps; unknown timestamps withheld.")
    return state, timeline


def _timestamp(value):
    """Only timezone-bearing recorded timestamps establish cross-source ordering."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None


def normalise_timeline(value):
    """Return recorded timezone-bearing timestamps or unknown, with a diagnostic bit."""
    if not isinstance(value, dict) or not isinstance(value.get("accepted", {}), dict):
        return {"started": None, "accepted": {}}, True
    malformed = value.get("_display_malformed") is True
    def stamp(raw):
        nonlocal malformed
        if raw is None:
            return None
        if _timestamp(raw) is None:
            malformed = True
            return None
        return raw
    return {"started": stamp(value.get("started")),
            "accepted": {action: stamp(at) for action, at in value.get("accepted", {}).items()}}, malformed


def _observation_activity(row):
    return {key: value for key, value in row.items() if key not in ("observed_at", "logged_at")}


def _exit_code(row):
    code = row.get("exit")
    return code if isinstance(code, int) and not isinstance(code, bool) else None


def _event_status(name, kind, row, code):
    """Plain words for one trace/skill-call row; same refusal vocabulary as `event_line` in shiploop_trace.py.

    The raw exit code stays on the event beside this. Kinds without a status word get None, never a placeholder.
    """
    if name == "skill-calls.jsonl" or kind == "skill":
        gate = row.get("gate")
        return gate if isinstance(gate, str) and gate else "called"
    if kind == "command":
        if code is None:
            return None
        if code == 0:
            return "ok"
        word = ("not passed" if row.get("verb") == "check"
                else "interrupted" if row.get("crashed") == "KeyboardInterrupt"
                else "crashed" if row.get("crashed") else "refused")
        return f"{word} (exit {code})"
    if kind == "packet":
        return "sent again (same text)" if row.get("repeat") else "sent"
    if kind == "hook":
        decision = row.get("decision")
        return decision if isinstance(decision, str) and decision else None
    return None


def _packet_summary(row):
    """E.g. "W2 improve packet (reviewing document), 1,504 chars, printed whole"; absent parts are omitted."""
    text = " ".join(str(row[key]) for key in ("item", "stage") if row.get(key)) + " packet"
    text = text.strip()
    if row.get("reviewed"):
        text += f" (reviewing {row['reviewed']})"
    parts = [text]
    chars, printed = row.get("chars"), row.get("printed")
    if isinstance(chars, int) and not isinstance(chars, bool):
        parts.append(f"{chars:,} chars")
    if row.get("whole"):
        parts.append("printed whole")
    elif isinstance(printed, int) and not isinstance(printed, bool):
        parts.append(f"printed head {printed:,} chars")
    return ", ".join(parts)


def _record_status(record):
    """Status of one structured record; an expectations record reports how many of its checks matched."""
    results = record.get("results")
    if record.get("schema") == "shiploop-expectations/v1" and isinstance(results, list) and results:
        matched = sum(1 for result in results if isinstance(result, dict) and result.get("matches") is True)
        return f"{matched} of {len(results)} matched"
    return record.get("status", record.get("answer", record.get("disposition", record.get("passed"))))


def _listing(root, directory):
    """Sorted names in one run subdirectory, read through the same no-follow descriptors; none when absent or unsafe."""
    try:
        fd = capture._parent_fd(root, (directory,))
        try:
            return sorted(os.listdir(fd))
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return []


def _record_binding(record, action, state, root, relative):
    """Display provenance, never the engine's acceptance/contract validator."""
    if not isinstance(record, dict):
        return "unbound", "Structured source is not an object."
    identified = False
    for container in (record, record.get("binding"), record.get("context")):
        if not isinstance(container, dict):
            continue
        for key, expected in (("run_id", state.get("run_id")), ("action", action), ("action_id", action)):
            if key in container:
                actual = container[key]
                if key == "action" and isinstance(actual, dict):
                    actual = actual.get("id")
                if actual != expected:
                    return "unbound", "Identity mismatch: " + key + "."
                identified = True
    if relative.startswith("loops/"):
        receipt = record.get("receipt")
        if receipt is not None:
            if not isinstance(receipt, str) or Path(receipt).name != action + "-terminal.json":
                return "unbound", "Identity mismatch: receipt action locator."
            # A copied artifact may retain its original absolute locator. Its
            # action must also agree with the machine-readable context resources.
        if "workspace" in record and record["workspace"] != state.get("repo"):
            return "unbound", "Identity mismatch: receipt workspace."
        context = record.get("context")
        resources = context.get("resources") if isinstance(context, dict) else None
        for resource in resources if isinstance(resources, list) else []:
            locator = resource.get("locator") if isinstance(resource, dict) else None
            if isinstance(locator, str) and Path(locator).parent.name in ("packets", "notes"):
                if Path(locator).name != action + ".md":
                    return "unbound", "Identity mismatch: Until context action locator."
                identified = True
        # Without a run ID the receipt's contextual/action match is useful but
        # cannot attest a copied receipt's original run identity.
        if record.get("run_id") is None:
            return "contextual", "Action/context association; no explicit receipt run ID recorded."
    return ("explicit", "Recorded identity fields match where present; absent fields are not attested.") if identified else ("contextual", "Filename association only; source has no recorded action/run identity.")


def build(root, state, timeline, *, previous=None, observed_at=None, captured=None, core=None):
    root = Path(os.path.abspath(os.fspath(root)))
    observed_at = observed_at or utc()
    previous = previous or {}
    captures = dict(captured or {})
    sources, events, evidence, observations, warnings = [value["source"] for value in captures.values()], [], [], [], []
    activity_records = []
    timeline, malformed_timeline = normalise_timeline(timeline)
    if malformed_timeline:
        warnings.append("Malformed optional timeline timestamps; unknown timestamps withheld.")
        source = next((row for row in sources if row.get("id") == "timeline.json"), None)
        if source is None and core and core.get("timeline_source"):
            source = core["timeline_source"]
        if source is None:
            source = {"id": "timeline.json", "path": "timeline.json", "observed_at": observed_at,
                      "changed_at": None, "last_event_at": None, "rows": 0, "omitted": None}
            sources.append(source)
        source.update(status="partial", message=warnings[-1])
    lifecycle = {key: {"status": "unknown", "summary": "Not recorded by a bound producer.",
                       "at": None, "producer": None, "evidence": []}
                 for key in ("engine", "execution", "acceptance", "source_return", "owner_hold")}
    lifecycle["engine"] = {"status": state.get("status"), "summary": state.get("status_reason") or "Engine state.",
                            "at": None, "producer": "state.md", "evidence": []}

    def read(relative, limit=EVIDENCE_BYTES, *, reuse=False):
        if relative not in captures:
            prior = previous.get(relative)
            if reuse and prior and capture.unchanged(root, relative, prior):
                # Same file by device:inode, mtime and size: keep its bytes, only the read clock moves.
                source = dict(prior["source"], observed_at=observed_at)
                if source.get("message", "").startswith("Source replaced"):
                    source["message"] = ""
                value = {"raw": prior["raw"], "source": source, "generation": prior["generation"],
                         "mtime_ns": prior["mtime_ns"]}
            else:
                value = capture.capture(root, relative, limit, observed_at, prior)
            captures[relative] = value
            sources.append(value["source"])
        return captures[relative]

    evidence_by_path = {}
    priorities = {}

    def add_evidence(relative, title, line=1, selector=None, priority=(4, 0), qualification=None):
        if not isinstance(relative, str):
            return None
        try:
            capture._relative_parts(relative)
        except (ValueError, TypeError):
            warnings.append("Unsafe evidence reference omitted.")
            return None
        # One retained source gets one preview identity even when packets repeat
        # or several producer selectors reference it. References never spend a
        # second preview read from the bounded budget.
        if relative in evidence_by_path:
            priorities[relative] = min(priorities[relative], priority)
            reference = {"line": line, "selector": selector, **(qualification or {})}
            if reference not in evidence_by_path[relative]["references"]:
                evidence_by_path[relative]["references"].append(reference)
            return evidence_by_path[relative]["id"]
        eid = "evidence:" + digest(relative)[:20]
        entry = {"id": eid, "title": title, "path": str(root / relative), "relative_path": relative,
                 "line": line, "selector": selector, "references": [{"line": line, "selector": selector, **(qualification or {})}], "sha256": None, "status": "unavailable",
                 "content": "", "summary": "Preview not yet captured."}
        evidence.append(entry)
        evidence_by_path[relative] = entry
        priorities[relative] = priority
        return eid

    if core:
        consistency = core.get("consistency", "shared-lock")
        unlocked = consistency != "shared-lock"
        message = ("Archive display capture without a shared lock; cross-file consistency is not guaranteed."
                   if unlocked else "Shared-lock core generation.")
        if unlocked:
            warnings.append(message)
        for name, raw in (("state.md", core["state_raw"]), ("timeline.json", core["timeline_raw"])):
            if name == "timeline.json" and core.get("timeline_source"):
                source = dict(core["timeline_source"], consistency=consistency)
                if unlocked:
                    source["message"] = (source.get("message", "") + " " + message).strip()
                    if source["status"] == "ok":
                        source["status"] = "partial"
                sources.append(source)
                continue
            sources.append({"id": name, "path": name, "status": "partial" if unlocked else "ok",
                            "observed_at": core["observed_at"], "changed_at": None, "last_event_at": None,
                            "rows": 1, "omitted": 0, "message": message, "consistency": consistency,
                            "sha256": hashlib.sha256(raw).hexdigest()})
    for name in ("trace.jsonl", "skill-calls.jsonl", "progress-observations.jsonl"):
        contextual = None  # source-local inference only; no final-trace cursor leaks into another stream
        value = read(name, STREAM_BYTES)
        rows = capture.stream(value)
        if name == "trace.jsonl" and len(value["raw"]) >= STREAM_BYTES:
            value["source"].update(status="partial", message="Trace reached its writer/read size cap; coverage incomplete.")
        omitted = max(0, len(rows) - STORY_ROWS)
        if omitted:
            value["source"].update(status="partial", omitted=value["source"]["omitted"] + omitted,
                                   message="Earlier records omitted at display bound.")
        physical = value["raw"].split(b"\n")
        for line, row in rows[-STORY_ROWS:]:
            if row.get("run_id", state.get("run_id")) != state.get("run_id"):
                warnings.append(f"Foreign-run record ignored in {name} at line {line}.")
                value["source"].update(status="partial", message="Foreign-run records ignored.")
                continue
            row_hash = hashlib.sha256(physical[line - 1]).hexdigest()[:16]
            sid = f"{name}:{value['generation']}:{line}:{row_hash}"
            source = {"path": name, "line": line, "sha256": value["source"].get("sha256")}
            if name == "progress-observations.jsonl":
                valid = (row.get("schema") == "shiploop-progress-observation/v1"
                         and isinstance(state.get("run_id"), str) and state["run_id"].strip()
                         and row.get("run_id") == state.get("run_id")
                         and all(isinstance(row.get(key), str) and row[key].strip()
                                 for key in ("id", "producer", "scope", "title", "summary", "status", "observed_at", "logged_at"))
                         and row.get("kind") in ("fact", "derived", "interpretation"))
                if not valid:
                    warnings.append(f"Ignored unbound or invalid producer observation at line {line}.")
                    value["source"].update(status="partial", message="Invalid or foreign-run observations ignored.")
                    continue
                refs = []
                for ref in row.get("evidence", []) if isinstance(row.get("evidence", []), list) else []:
                    if isinstance(ref, dict):
                        eid = add_evidence(ref.get("path"), "Producer evidence", ref.get("line", 1), ref.get("selector"), priority=(2, -1))
                        if eid:
                            refs.append(eid)
                observation = dict(row, id="observation:" + row["producer"] + ":" + row["id"], evidence=refs)
                old_index = next((i for i, old in enumerate(observations) if old["id"] == observation["id"]), None)
                if old_index is not None and _observation_activity(observations[old_index]) == _observation_activity(observation):
                    observations[old_index] = observation  # heartbeat does not change causal precedence
                else:
                    if old_index is not None:
                        observations.pop(old_index)
                    observations.append(observation)
                continue
            activity_records.append([name, row])
            kind = row.get("kind", "skill" if name == "skill-calls.jsonl" else "unknown")
            kind = kind if isinstance(kind, str) else "unknown"
            action = row.get("action") if isinstance(row.get("action"), str) else None
            cursor = row.get("cursor")
            if not action and kind == "command" and isinstance(cursor, list) and len(cursor) == 2 and isinstance(cursor[0], str):
                action = cursor[0]
            binding = "explicit" if action else "contextual" if contextual else "unbound"
            if kind == "packet":
                contextual = action
            refs = []
            if kind == "packet":
                for field in ("file", "head_file"):
                    if row.get(field):
                        expected = row.get("sha") if field == "file" else None
                        if field == "head_file":
                            match = re.fullmatch(r"packets/sent/([0-9a-fA-F]{16}|[0-9a-fA-F]{64})\.md", str(row[field]))
                            expected = match.group(1) if match else None
                        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{16}|[0-9a-fA-F]{64}", expected):
                            expected = None
                        eid = add_evidence(row[field], "Packet source preview", priority=(4, -line),
                                           qualification={"packet_event": sid, "field": field,
                                                          "expected_sha256": expected.lower() if expected else None})
                        if eid:
                            refs.append(eid)
            code = _exit_code(row)
            summary = (row.get("error") or row.get("why") or row.get("text") or row.get("verb") or row.get("skill")
                       or (_packet_summary(row) if kind == "packet" else kind))
            event = {"id": sid, "kind": kind, "at": row.get("at"), "action": action or contextual,
                     "stage": row.get("stage")[0] if kind == "command" and isinstance(row.get("stage"), list) and row["stage"] else row.get("stage"), "summary": str(summary),
                     "status": _event_status(name, kind, row, code), "exit": code,
                     "duration_ms": row.get("ms") if isinstance(row.get("ms"), (float, int)) else None,
                     "binding": binding, "source": source, "evidence": refs}
            events.append(event)
            stamp = _timestamp(row.get("at"))
            previous_stamp = _timestamp(value["source"].get("last_event_at"))
            if stamp is not None and (previous_stamp is None or stamp > previous_stamp):
                value["source"]["last_event_at"] = row["at"]
    for observation in observations:
        for key, assertion in (observation.get("lifecycle") or {}).items() if isinstance(observation.get("lifecycle"), dict) else []:
            if key in lifecycle and key != "engine" and isinstance(assertion, dict) and isinstance(assertion.get("status"), str):
                lifecycle[key] = {"status": assertion["status"], "summary": assertion.get("summary", ""),
                                  "at": assertion.get("at"), "producer": observation["producer"],
                                  "scope": observation["scope"], "evidence": observation["evidence"]}
    # State owns acceptance. Commands remain attempts; arrival never adds a second acceptance.
    visits = []
    accepted_at = timeline.get("accepted") if isinstance(timeline.get("accepted"), dict) else {}
    previous_end = timeline.get("started")
    for ordinal, entry in enumerate(state.get("history", []), 1):
        action = entry.get("action")
        action = action if isinstance(action, str) and action else None
        identity = action if action is not None else "history-row:" + str(ordinal)
        ended = accepted_at.get(action) if action is not None else None
        result = state.get("accepted", {}).get(action, {}) if action is not None else {}
        activity_records.append(["state.md", {"action": action, "history": entry, "result": result, "at": ended}])
        events.append({"id": "accepted:" + identity, "kind": "accepted", "at": ended, "action": action,
                       "stage": entry.get("stage"), "summary": result.get("summary", entry.get("summary", "Accepted from state.")),
                       "status": entry.get("outcome"), "duration_ms": None, "binding": "explicit" if action else "unbound",
                       "source": {"path": "state.md", "line": None, "sha256": hashlib.sha256(core["state_raw"]).hexdigest() if core else None}, "evidence": []})
        visits.append({"id": "visit:" + identity, "action": action, "stage": entry.get("stage"),
                       "item": entry.get("workitem"), "status": entry.get("outcome") or result.get("outcome") or "unknown",
                       "callback_accepted": True, "summary": result.get("summary", ""),
                       "started_at": previous_end, "ended_at": ended, "duration_seconds": None,
                       "duration_basis": "inferred visit dwell", "events": [], "evidence": []})
        begin_seconds, end_seconds = _timestamp(previous_end), _timestamp(ended)
        if begin_seconds is not None and end_seconds is not None:
            seconds = end_seconds - begin_seconds
            visits[-1]["duration_seconds"] = seconds if seconds >= 0 else None
        previous_end = ended or previous_end
    import shiploop_navigator as navigator
    try:
        stage, action, item = navigator._active_cursor(state)
    except (KeyError, IndexError, TypeError, ValueError):
        stage, action, item = state.get("stage"), None, None
    improve = state.get("active_improve") or {}
    parent_stage = improve.get("stage") or stage if improve else None
    if improve:
        stage = "improve"
    current = improve.get("improve_action") or (action or {}).get("id")
    if not current and state.get("status") != "done":
        warnings.append("Current action is unknown in retained state; no active visit or action-bound evidence inferred.")
    if current and current not in {v["action"] for v in visits}:
        reviewed = improve.get("action_id") if improve else None
        visits.append({"id": "visit:" + current, "action": current, "stage": stage, "parent_stage": parent_stage, "item": item,
                       "reviewed_action": reviewed if isinstance(reviewed, str) and reviewed else None,
                       "status": state.get("status"), "summary": state.get("status_reason", "Current visit."),
                       "started_at": previous_end, "ended_at": None, "duration_seconds": None,
                       "duration_basis": "inferred visit dwell", "events": [], "evidence": []})
    # Plan preview priorities independently of chronological visit presentation.
    # Current gates first, then all recent/prior Until receipts, then checks and
    # other structured records, and finally prompt copies. Missing files do not
    # spend a successful-preview slot. Each structured directory is listed once and
    # only names that exist become candidates: most stages write none of them.
    test_names = _listing(root, "tests")
    listed = {directory: set(_listing(root, directory)) for directory in ("loops", "checks", "expectations")}
    structured = []
    for recency, visit in enumerate(reversed(visits)):
        action = visit["action"]
        if not action:
            continue
        try:
            if len(capture._relative_parts(action)) != 1:
                continue
        except ValueError:
            continue
        candidates = [f"{directory}/{action}{suffix}" for directory, suffix in
                      (("loops", "-terminal.json"), ("checks", ".md"), ("expectations", ".md"))
                      if action + suffix in listed[directory]]
        names = ["tests/" + name for name in test_names if name.startswith(action + "-") and name.endswith(".md")]
        candidates += names
        if visit["stage"] == "plan":
            import shiploop_planning_status as planning_status
            plan_exps, plan_snaps = planning_status.scan_experiments(root, state)
            for exp in plan_exps[:4]:
                rel = exp.get("relative")
                if exp.get("origin") == "plan" and isinstance(rel, str) and rel.endswith("decision.md"):
                    eid = add_evidence(rel, "Experiment finding (" + str(exp.get("id")) + ")", priority=(2, recency))
                    if eid:
                        visit["evidence"].append(eid)
            for snap in plan_snaps[:4]:
                rel = snap.get("relative")
                if isinstance(rel, str):
                    eid = add_evidence(rel, "Plan draft snapshot (iter " + str(snap.get("iteration")) + ")",
                                       priority=(2, recency))
                    if eid:
                        visit["evidence"].append(eid)
        for relative in candidates:
            is_current = action == current
            tier = (0 if is_current and not relative.startswith("tests/") else 1 if relative.startswith("loops/")
                    else 2 if is_current or relative.startswith(("checks/", "expectations/")) else 3)
            title = "Until receipt" if relative.startswith("loops/") else "Structured execution record"
            eid = add_evidence(relative, title, priority=(tier, recency))
            structured.append((visit, relative, eid))
        if action == current:
            eid = add_evidence(f"packets/{action}.md", "Current packet copy", priority=(4, -STORY_ROWS),
                               qualification={"field": "current", "expected_sha256": None})
            if eid:
                visit["evidence"].append(eid)

    # The file budget bounds how many previews embed their content. A structured record
    # (Until receipt, check, expectations, test) is always read, so its event reports the
    # record's own status; past the budget it is read but not embedded.
    structured_paths = {relative for _, relative, _ in structured}
    left_out = f"Preview left out at the {EVIDENCE_FILES}-file display budget; the record itself was read."
    loaded = omitted_previews = 0
    not_embedded = set()
    for relative in sorted(evidence_by_path, key=lambda path: priorities[path]):
        entry = evidence_by_path[relative]
        over_budget = loaded >= EVIDENCE_FILES
        if over_budget and relative not in structured_paths:
            omitted_previews += 1
            message = "Preview omitted at the bounded file budget; source was not read in this generation."
            entry.update(status="not loaded", summary=message)
            sources.append({"id": relative, "path": relative, "status": "partial", "observed_at": None,
                            "changed_at": None, "last_event_at": None, "rows": 0, "omitted": None, "message": message})
            continue
        value = read(relative, reuse=True)
        source = value["source"]
        if over_budget and source.get("sha256") is not None:
            not_embedded.add(relative)
            entry.update(sha256=source["sha256"], status="not embedded", content="", summary=left_out)
            continue
        if source.get("sha256") is not None:
            loaded += 1
        entry.update(sha256=source.get("sha256"), status=source["status"],
                     content=value["raw"].decode("utf-8", errors="replace"),
                     summary=entry["title"] if source["status"] == "ok" else source["message"])
    if omitted_previews:
        warnings.append(f"{omitted_previews} registered source previews were not read at the {EVIDENCE_FILES}-file display bound; structured records are always read, so these are packet copies and producer evidence. File existence/content beyond that budget is unknown.")

    for relative, entry in evidence_by_path.items():
        packet_refs = [ref for ref in entry["references"] if "field" in ref]
        if not packet_refs:
            continue
        messages = []
        for ref in packet_refs:
            expected, actual = ref.get("expected_sha256"), entry.get("sha256")
            if actual is None:
                verdict, message = "unavailable", "Packet bytes unavailable; issued digest not checked."
            elif expected is None:
                verdict, message = "current-file-unverified", "Current file; no supported issued digest recorded."
            elif actual.startswith(expected):
                verdict, message = "digest-match", "Captured bytes match recorded issued SHA-256" + (" prefix" if len(expected) < 64 else "") + " " + expected + "."
            else:
                verdict, message = "digest-mismatch", "Captured current bytes differ from recorded issued SHA-256 " + expected + "."
            ref.update(status=verdict, summary=message)
            if message not in messages:
                messages.append(message)
        statuses = {ref["status"] for ref in packet_refs}
        entry["title"] = "Packet source preview"
        if "digest-mismatch" in statuses:
            entry["status"] = "mismatched"
            warnings.append("Packet issued-digest mismatch: " + relative)
        elif "current-file-unverified" in statuses:
            entry["status"] = "unverified"
        # Missing, unsafe, stale and budget-omitted coverage stays visible even
        # when an earlier captured prefix happens to match one reference.
        entry["summary"] = " ".join(messages) + " " + entry["summary"]

    for visit, relative, eid in structured:
        entry = evidence_by_path[relative]
        value = captures.get(relative)
        record = None
        message = entry["summary"]
        if value and value["source"].get("sha256") is not None:
            try:
                record = store.observation_json(json.loads(value["raw"]) if relative.endswith(".json") else store.loads(value["raw"].decode("utf-8")))
            except (ValueError, UnicodeError, store.StorageError, RecursionError):
                message = ("Malformed structured evidence; its screened source preview is retained." if relative not in not_embedded
                           else "Malformed structured evidence; its preview is left out at the display budget.")
                entry.update(status="partial", summary=message)
                value["source"].update(status="partial", message=message)
        if record is not None:
            activity_records.append([relative, record])
        binding, provenance = _record_binding(record, visit["action"], state, root, relative)
        mismatch = provenance.startswith("Identity mismatch")
        if mismatch:
            entry.update(status="mismatched", summary=provenance)
            warnings.append(provenance + " " + relative)
        status = _record_status(record) if isinstance(record, dict) and not mismatch else "mismatched" if mismatch else entry["status"]
        reused = isinstance(record, dict) and bool(record.get("reused"))
        progress = record.get("progress") if isinstance(record, dict) and isinstance(record.get("progress"), dict) else {}
        last_report = record.get("last_report") if isinstance(record, dict) and isinstance(record.get("last_report"), dict) else {}
        raw_iter = progress.get("action_number", record.get("action_number") if isinstance(record, dict) else None)
        iter_num = raw_iter if isinstance(raw_iter, int) and not isinstance(raw_iter, bool) else None
        if isinstance(record, dict) and not mismatch:
            iter_note = f"iter {iter_num} · " if relative.startswith("loops/") and iter_num is not None else ""
            summary = ("Reused result; not a new execution. " if reused
                       else entry["title"] + ": " + iter_note + str(status if status is not None else "no status recorded") + ". ")
            detail = (record.get("reason") or record.get("summary")
                      or last_report.get("handoff") or last_report.get("evidence") or "")
            summary += str(detail) + " " + provenance
        else:
            summary = provenance if mismatch else message
        summary += " " + relative
        at = record.get("at", record.get("created_at")) if isinstance(record, dict) and not mismatch else None
        event_row = {"id": "record:" + digest(relative)[:20], "kind": "until" if relative.startswith("loops/") else "test" if relative.startswith("tests/") else "expectation" if relative.startswith("expectations/") else "check",
                     "at": at, "action": visit["action"], "stage": visit["stage"], "summary": summary, "status": status,
                     "duration_ms": None, "binding": binding, "source": {"path": relative, "line": 1,
                     "sha256": entry["sha256"]}, "evidence": [eid]}
        if relative.startswith("loops/") and iter_num is not None:
            event_row["iteration"] = iter_num
        events.append(event_row)
        entry["summary"] = summary + (" " + left_out if relative in not_embedded and left_out not in summary else "")
    # An Improve pass is not a history row: its events belong to the visit it reviewed.
    visit_by_action = {v["action"]: v for v in visits if v["action"]}
    improve_parent = {}
    for reviewed, record in (state.get("improve_results") or {}).items():
        child = record.get("improve_action") if isinstance(record, dict) else None
        if isinstance(reviewed, str) and isinstance(child, str) and child and reviewed in visit_by_action and child not in visit_by_action:
            improve_parent[child] = reviewed
            phase = record.get("runtime_phase")
            visit_by_action[reviewed]["improve"] = {"action": child, "phase": phase if isinstance(phase, str) else None}
    for event in events:
        if event.get("action") in improve_parent:
            event["improve_of"] = improve_parent[event["action"]]
    for visit in visits:
        # Unknown actions are separate history rows, never a common null join key.
        # The stage an active Improve pass is reviewing has no history row yet: its packet, checks and callback
        # show in the one current visit, with the pass's own events.
        reviewed = visit.get("reviewed_action")
        reviewed = reviewed if reviewed and reviewed not in visit_by_action else None
        own = [e for e in events if e.get("action") == visit["action"] or e.get("improve_of") == visit["action"]
               or (reviewed and e.get("action") == reviewed)] if visit["action"] else [
            e for e in events if e["id"] == "accepted:" + visit["id"][len("visit:"):]]
        visit["events"] = [e["id"] for e in own]
        visit["evidence"] = list(dict.fromkeys(visit["evidence"] + [ref for e in own for ref in e["evidence"]]))
    timed = [(stamp, event) for event in events for stamp in [_timestamp(event.get("at"))] if stamp is not None]
    timed += [(stamp, {"at": row["event_at"], "summary": row["summary"]}) for row in observations
              for stamp in [_timestamp(row.get("event_at"))] if stamp is not None]
    latest = max(timed, key=lambda pair: pair[0])[1] if timed else None
    changed = latest["summary"] if latest else "No reliably timestamped event recorded; source order alone does not establish latest activity."
    knowledge_times = [row.get("logged_at") for row in observations if _timestamp(row.get("logged_at")) is not None]
    last_knowledge_at = max(knowledge_times, key=_timestamp) if knowledge_times else None
    try:
        next_label, next_text = navigator._status_next(state)
        now_where = navigator._status_where(state)
        summary_next = f"{next_label}: {next_text}"
    except (KeyError, ValueError, TypeError, StopIteration, IndexError):
        now_where = str(stage or state.get("status"))
        summary_next = "Await the recorded current action." if current else "No current action."
    story = {"schema": "shiploop-progress-story/v1", "summary": {"now": now_where,
             "changed": changed,
             "waiting": state.get("status_reason") or "", "next": summary_next},
             "run_root": str(root), "visits": visits, "events": events, "evidence": evidence, "sources": sources,
             "lifecycle": lifecycle, "observations": observations,
             "last_event_at": latest["at"] if latest else None,
             "last_knowledge_at": last_knowledge_at,
             "coverage": {"preview_candidates": len(evidence_by_path), "previews_read": loaded, "previews_not_read": omitted_previews, "previews_not_embedded": len(not_embedded),
                          "scope": "Registered source candidates only; not an inventory of every on-disk artifact."},
             "warnings": list(dict.fromkeys(warnings))}
    story = capture.screen(story)
    # Observation read clocks and source replacement diagnostics are coverage, not activity.
    meaningful = {"events": activity_records,
                  "observations": sorted((_observation_activity(row) for row in observations), key=lambda row: row["id"]),
                  "lifecycle": story["lifecycle"]}
    story["activity_fingerprint"] = digest(meaningful)
    content = {**story, "sources": [{k:v for k,v in row.items() if k != "observed_at" and not (row.get("path") == "progress-observations.jsonl" and k in ("sha256", "changed_at", "rows"))} for row in story["sources"]],
               "observations": meaningful["observations"]}
    content.pop("last_knowledge_at", None)
    story["content_fingerprint"] = digest(content)
    return story, captures
