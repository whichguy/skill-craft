#!/usr/bin/env python3
"""Backchain's structural check, ported from the Backchain checkout's ``harness/lib.js``.

``lib.js`` is the arbiter, not Backchain's SKILL.md: ``test/fixtures/backchain-check`` holds its recorded
verdicts and the port reproduces each one, failure messages and details included.  Every function
mirrors the JS function of the same name; JS semantics that Python does not share are explicit:
missing properties (``_MISSING``), insertion-ordered sets (dicts), object key order, ECMAScript
whitespace, JS number text and JSON.stringify.

``shiploop backchain-check --candidate PATH`` records only: it prints a receipt, writes a snapshot of
the bytes checked and the receipt under ``<run>/backchain/<action>/``, and never changes run state.
"""

from __future__ import annotations

import argparse
import decimal
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA = "shiploop-backchain-check/v1"
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_UNAVAILABLE = 3
CONFIRM_LEVELS = ("execute", "inspect", "unconfirmable")
_ACTION_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,159}")

# ECMAScript WhiteSpace and LineTerminator: what JS ``trim`` strips and ``\s`` matches.
JS_WHITESPACE = ("\t\n\x0b\x0c\r           "
                 "       　﻿")
_JS_SPACE_RUN = re.compile("[" + JS_WHITESPACE + "]+")
_INDEX_KEY = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_SAFE_INTEGER = 2 ** 53


class _Missing:
    """A JS ``undefined``: an absent property."""

    def __repr__(self) -> str:
        return "undefined"


_MISSING = _Missing()


class CheckUnavailable(Exception):
    """The candidate could not be read or parsed; never a finding."""


# ---------------------------------------------------------------- JS semantics

def js_trim(value: str) -> str:
    return value.strip(JS_WHITESPACE)


def normalize_need_string(value: str) -> str:
    """``normalizeNeedString``: trim, then collapse each whitespace run to one space."""
    return _JS_SPACE_RUN.sub(" ", js_trim(value))


def _get(value: Any, key: str) -> Any:
    return value.get(key, _MISSING) if isinstance(value, dict) else _MISSING


def _js_keys(value: Dict[str, Any]) -> List[str]:
    """``Object.keys`` order: array-index keys ascending, then the rest in insertion order."""
    index = sorted((key for key in value if _INDEX_KEY.match(key) and int(key) < 2 ** 32 - 1), key=int)
    taken = set(index)
    return index + [key for key in value if key not in taken]


def _is_str(value: Any) -> bool:
    return isinstance(value, str)


def _member(ids: Dict[str, bool], value: Any) -> bool:
    """``Set.has`` over step ids, which are strings only."""
    return isinstance(value, str) and value in ids


def _detail(*pairs: Tuple[str, Any]) -> Dict[str, Any]:
    """An object literal as JSON keeps it: undefined members are dropped."""
    return {key: value for key, value in pairs if value is not _MISSING}


def _number(value: float) -> Any:
    """A JS number: integral values in the safe range are ints, the rest floats."""
    if math.isfinite(value) and value.is_integer() and abs(value) <= _SAFE_INTEGER:
        return int(value)
    return value


def _parse_int(text: str) -> Any:
    value = int(text)
    if abs(value) <= _SAFE_INTEGER:
        return value
    try:
        return _number(float(value))
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not JSON")


def loads(data: bytes) -> Any:
    """``JSON.parse`` of strict UTF-8 bytes, with JS number precision."""
    try:
        text = data.decode("utf-8")
        return json.loads(text, parse_int=_parse_int, parse_float=lambda text: _number(float(text)),
                          parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise CheckUnavailable(f"not JSON: {exc}") from exc


def js_number_text(value: Any) -> str:
    """``Number.prototype.toString()`` for an int or float."""
    if isinstance(value, int) and abs(value) < 10 ** 21:
        return str(value)
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    if value < 0:
        return "-" + js_number_text(-value)
    sign, digits, exponent = decimal.Decimal(repr(value)).normalize().as_tuple()
    del sign
    text = "".join(map(str, digits))
    k = len(text)
    n = int(exponent) + k
    if k <= n <= 21:
        return text + "0" * (n - k)
    if 0 < n <= 21:
        return text[:n] + "." + text[n:]
    if -6 < n <= 0:
        return "0." + "0" * -n + text
    power = n - 1
    mark = "e+" if power >= 0 else "e-"
    return (text if k == 1 else text[0] + "." + text[1:]) + mark + str(abs(power))


def _js_string(value: Any) -> str:
    """``String(value)``; arrays join their members, where null becomes empty."""
    if isinstance(value, str):
        return value
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return js_number_text(value)
    if isinstance(value, list):
        return ",".join(_join_member(member) for member in value)
    return "[object Object]"


def _join_member(value: Any) -> str:
    return "" if value is None else _js_string(value)


def _utf16(text: str) -> bytes:
    """A sort key in UTF-16 code-unit order, as JS ``sort`` compares strings."""
    return text.encode("utf-16-be", "surrogatepass")


def _same_value_zero(value: Any) -> Tuple[Any, ...]:
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        return ("number", float(value))
    if isinstance(value, str):
        return ("string", value)
    if value is None:
        return ("null",)
    return ("object", id(value))


_ESCAPES = {"\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r", '"': '\\"', "\\": "\\\\"}


def _js_quote(text: str) -> str:
    out = ['"']
    for char in text:
        code = ord(char)
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif code < 0x20 or 0xD800 <= code <= 0xDFFF:
            out.append("\\u%04x" % code)
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def js_stringify(value: Any) -> str:
    """Compact ``JSON.stringify`` of parsed JSON data."""
    if value is None or value is _MISSING:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return js_number_text(value) if math.isfinite(value) else "null"
    if isinstance(value, str):
        return _js_quote(value)
    if isinstance(value, list):
        return "[" + ",".join(js_stringify(member) for member in value) + "]"
    return "{" + ",".join(_js_quote(key) + ":" + js_stringify(value[key]) for key in _js_keys(value)) + "}"


def jsonable(value: Any) -> Any:
    """Data as JSON.stringify would emit it: no undefined members, non-finite numbers as null."""
    if isinstance(value, float):
        return _number(value) if math.isfinite(value) else None
    if isinstance(value, list):
        return [None if member is _MISSING else jsonable(member) for member in value]
    if isinstance(value, dict):
        return {key: jsonable(value[key]) for key in _js_keys(value) if value[key] is not _MISSING}
    return value


# ---------------------------------------------------------------- lib.js port

def schema_errors(plan: Any) -> List[str]:
    errors: List[str] = []

    def report(path: str, message: str) -> None:
        errors.append(f"{path} {message}")

    def closed(value: Any, path: str, required: Iterable[str], allowed: Iterable[str]) -> bool:
        if not isinstance(value, dict):
            report(path, "must be an object")
            return False
        for key in required:
            if key not in value:
                report(path, f"is missing required property {key}")
        allowed = tuple(allowed)
        for key in _js_keys(value):
            if key not in allowed:
                report(path, f"has unknown property {key}")
        return True

    plan_keys = ("goal", "initial_state", "steps", "parallel_groups", "unresolved")
    if not closed(plan, "plan", plan_keys, plan_keys + ("goal_needs",)):
        return errors

    goal = _get(plan, "goal")
    if not _is_str(goal) or goal == "":
        report("goal", "must be a non-empty string")
    initial = _get(plan, "initial_state")
    if not isinstance(initial, list) or any(not _is_str(item) for item in initial):
        report("initial_state", "must be an array of strings")

    steps = _get(plan, "steps")
    if not isinstance(steps, list) or not steps:
        report("steps", "must be a non-empty array")
    else:
        step_ids: Dict[str, bool] = {}
        for step_index, step in enumerate(steps):
            step_path = f"steps[{step_index}]"
            step_keys = ("id", "statement", "produces", "inputs", "origin")
            if not closed(step, step_path, step_keys, step_keys + ("confirm",)):
                continue
            identifier = _get(step, "id")
            if not _is_str(identifier) or identifier == "":
                report(f"{step_path}.id", "must be a non-empty string")
            elif identifier in step_ids:
                report(f"{step_path}.id", f"duplicates step ID {identifier}")
            else:
                step_ids[identifier] = True
            statement = _get(step, "statement")
            if not _is_str(statement) or statement == "":
                report(f"{step_path}.statement", "must be a non-empty string")
            produces = _get(step, "produces")
            if (not isinstance(produces, list) or not produces
                    or any(not _is_str(item) or item == "" for item in produces)):
                report(f"{step_path}.produces", "must be a non-empty array of non-empty strings")
            inputs = _get(step, "inputs")
            if not isinstance(inputs, list):
                report(f"{step_path}.inputs", "must be an array")
            else:
                for input_index, entry in enumerate(inputs):
                    input_path = f"{step_path}.inputs[{input_index}]"
                    if not closed(entry, input_path, ("need", "from"), ("need", "from", "artifact", "match")):
                        continue
                    need = _get(entry, "need")
                    if not _is_str(need) or need == "":
                        report(f"{input_path}.need", "must be a non-empty string")
                    source = _get(entry, "from")
                    if not (source is None or (_is_str(source) and source != "" and source != "initial")):
                        report(f"{input_path}.from", 'must be null or a non-empty step ID other than "initial"')
                    if "artifact" in entry and not _is_str(entry["artifact"]):
                        report(f"{input_path}.artifact", "must be a string")
                    if "match" in entry and not _is_str(entry["match"]):
                        report(f"{input_path}.match", "must be a string")
            origin = _get(step, "origin")
            if not (_is_str(origin) and origin in ("seed", "discovered")):
                report(f"{step_path}.origin", "must be seed or discovered")
            if "confirm" in step:
                confirm = step["confirm"]
                if not isinstance(confirm, list):
                    report(f"{step_path}.confirm", "must be an array")
                else:
                    known = produces if isinstance(produces, list) else []
                    confirmed: Dict[str, bool] = {}
                    for entry_index, entry in enumerate(confirm):
                        entry_path = f"{step_path}.confirm[{entry_index}]"
                        confirm_keys = ("produces", "by", "level")
                        if not closed(entry, entry_path, confirm_keys, confirm_keys):
                            continue
                        produce = _get(entry, "produces")
                        if not _is_str(produce) or produce == "":
                            report(f"{entry_path}.produces", "must be a non-empty string")
                        elif produce not in known:
                            report(f"{entry_path}.produces", "must be the exact text of one of this step's produces")
                        elif produce in confirmed:
                            report(f"{entry_path}.produces",
                                   "duplicates an earlier confirm entry for the same produce")
                        else:
                            confirmed[produce] = True
                        by = _get(entry, "by")
                        if not _is_str(by) or js_trim(by) == "":
                            report(f"{entry_path}.by", "must be a non-blank string")
                        level = _get(entry, "level")
                        if not (_is_str(level) and level in CONFIRM_LEVELS):
                            report(f"{entry_path}.level", "must be execute, inspect, or unconfirmable")

    groups = _get(plan, "parallel_groups")
    if not isinstance(groups, list):
        report("parallel_groups", "must be an array")
    else:
        for group_index, group in enumerate(groups):
            if not isinstance(group, list) or any(not _is_str(item) for item in group):
                report(f"parallel_groups[{group_index}]", "must be an array of strings")

    unresolved = _get(plan, "unresolved")
    if not isinstance(unresolved, list):
        report("unresolved", "must be an array")
    else:
        for entry_index, entry in enumerate(unresolved):
            entry_path = f"unresolved[{entry_index}]"
            if not closed(entry, entry_path, ("step", "need", "reason"), ("step", "need", "reason", "cycle")):
                continue
            step_id = _get(entry, "step")
            if not _is_str(step_id) or step_id == "":
                report(f"{entry_path}.step", "must be a non-empty string")
            need = _get(entry, "need")
            if not _is_str(need) or need == "":
                report(f"{entry_path}.need", "must be a non-empty string")
            reason = _get(entry, "reason")
            if not (_is_str(reason) and reason in ("residual-risk", "circular")):
                report(f"{entry_path}.reason", "must be residual-risk or circular")
            cycle = _get(entry, "cycle")
            if "cycle" in entry and (not isinstance(cycle, list) or len(cycle) < 2
                                     or any(not _is_str(item) for item in cycle)):
                report(f"{entry_path}.cycle", "must be an array of at least two strings")
            if reason == "circular" and "cycle" not in entry:
                report(entry_path, "requires cycle when reason is circular")
            if reason == "residual-risk" and "cycle" in entry:
                report(entry_path, "must not contain cycle when reason is residual-risk")

    if "goal_needs" in plan:
        goal_needs = plan["goal_needs"]
        if not isinstance(goal_needs, list):
            report("goal_needs", "must be an array")
        else:
            for need_index, need in enumerate(goal_needs):
                need_path = f"goal_needs[{need_index}]"
                if not _is_str(need) or need == "":
                    report(need_path, "must be a non-empty string")
                elif normalize_need_string(need) == "":
                    report(need_path, "must be non-empty after whitespace normalization")
    return errors


def existing_steps(plan: Any) -> List[Dict[str, Any]]:
    steps = _get(plan, "steps")
    return [step for step in steps if isinstance(step, dict)] if isinstance(steps, list) else []


def known_step_ids(plan: Any) -> Dict[str, bool]:
    return dict.fromkeys(step["id"] for step in existing_steps(plan) if _is_str(_get(step, "id")))


def committed_edges(plan: Any, ids: Iterable[str]) -> Dict[str, Dict[str, bool]]:
    """Consumer id -> its committed suppliers, both insertion-ordered as in the JS Map of Sets."""
    edges: Dict[str, Dict[str, bool]] = {identifier: {} for identifier in ids}
    for step in existing_steps(plan):
        identifier, inputs = _get(step, "id"), _get(step, "inputs")
        if not _is_str(identifier) or not isinstance(inputs, list):
            continue
        edges.setdefault(identifier, {})
        for entry in inputs:
            source = _get(entry, "from")
            if isinstance(entry, dict) and _is_str(source):
                edges.setdefault(source, {})
                edges[identifier][source] = True
    return edges


def find_directed_cycle(edges: Dict[str, Dict[str, bool]]) -> Optional[List[str]]:
    """The first cycle a depth-first walk in insertion order meets (iterative ``findDirectedCycle``)."""
    visiting: set = set()
    visited: set = set()
    stack: List[str] = []
    for start in edges:
        if start in visited:
            continue
        visiting.add(start)
        stack.append(start)
        frames = [(start, iter(edges.get(start, {})))]
        while frames:
            node, neighbors = frames[-1]
            descended = False
            for neighbor in neighbors:
                if neighbor in visiting:
                    return stack[stack.index(neighbor):] + [neighbor]
                if neighbor not in visited:
                    visiting.add(neighbor)
                    stack.append(neighbor)
                    frames.append((neighbor, iter(edges.get(neighbor, {}))))
                    descended = True
                    break
            if not descended:
                frames.pop()
                stack.pop()
                visiting.discard(node)
                visited.add(node)
    return None


def depth_groups(plan: Any) -> List[List[str]]:
    """Step ids by longest-path depth; re-entry on a cycle counts as depth 0 (iterative ``depthGroups``)."""
    ids = known_step_ids(plan)
    dependencies = committed_edges(plan, ids)
    depths: Dict[str, int] = {}
    in_progress: set = set()

    def depth_for(root: str) -> int:
        if root in depths:
            return depths[root]
        in_progress.add(root)
        frames: List[list] = [[root, iter(dependencies.get(root, {})), -1]]
        result: Optional[int] = None
        while frames:
            frame = frames[-1]
            if result is not None:
                frame[2] = max(frame[2], result)
                result = None
            supplier = next(frame[1], _MISSING)
            if supplier is _MISSING:
                node = frame[0]
                in_progress.discard(node)
                frames.pop()
                if node not in depths:
                    depths[node] = 0 if frame[2] < 0 else frame[2] + 1
                result = depths[node]
            elif supplier in depths:
                result = depths[supplier]
            elif supplier in in_progress:
                depths[supplier] = 0
                result = 0
            else:
                in_progress.add(supplier)
                frames.append([supplier, iter(dependencies.get(supplier, {})), -1])
        assert result is not None
        return result

    groups: Dict[int, List[str]] = {}
    for identifier in ids:
        groups.setdefault(depth_for(identifier), []).append(identifier)
    return [groups[depth] for depth in sorted(groups)]


def compute_parallel_groups(plan: Any) -> List[List[str]]:
    return [group for group in depth_groups(plan) if len(group) > 1]


def unconfirmed_produces(plan: Any) -> List[Dict[str, str]]:
    """Advisory: produces that no confirm entry names; never a failure."""
    advisories = []
    for step in existing_steps(plan):
        identifier, produces = _get(step, "id"), _get(step, "produces")
        if not _is_str(identifier) or not isinstance(produces, list):
            continue
        confirm = _get(step, "confirm")
        confirmed = {entry["produces"] for entry in (confirm if isinstance(confirm, list) else [])
                     if _is_str(_get(entry, "produces"))}
        seen = set()
        for produce in produces:
            if not _is_str(produce) or produce in confirmed or produce in seen:
                continue
            seen.add(produce)
            advisories.append({"stepId": identifier, "produces": produce})
    return advisories


def _js_clone(value: Any) -> Any:
    """``JSON.parse(JSON.stringify(value))``."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, list):
        return [_js_clone(member) for member in value]
    if isinstance(value, dict):
        return {key: _js_clone(value[key]) for key in _js_keys(value)}
    return value


def package(plan: Any) -> Any:
    """The packaged clone ``packagePlan(plan).plan``: a JSON copy with recomputed ``parallel_groups``."""
    clone = _js_clone(plan)
    if isinstance(clone, dict):
        clone["parallel_groups"] = compute_parallel_groups(clone)
    return clone


def groups_equal_as_sets(left: Any, right: Any) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False

    def normalized(groups: List[Any]) -> List[Optional[str]]:
        out: List[Optional[str]] = []
        for group in groups:
            if not isinstance(group, list):
                out.append(None)
                continue
            unique: Dict[Tuple[Any, ...], Any] = {}
            for member in group:
                unique.setdefault(_same_value_zero(member), member)
            members = sorted(unique.values(), key=lambda member: _utf16(_js_string(member)))
            out.append("\x00".join(_join_member(member) for member in members))
        return sorted(out, key=lambda text: _utf16("null" if text is None else text))

    left_keys, right_keys = normalized(left), normalized(right)
    return len(left_keys) == len(right_keys) and all(a == b for a, b in zip(left_keys, right_keys))


def validate_structure(plan: Any) -> Dict[str, Any]:
    """The seven invariants: ``{ok, failures: [{invariant, message, detail?}]}``."""
    failures: List[Dict[str, Any]] = []

    def fail(invariant: int, message: str, detail: Optional[Dict[str, Any]] = None) -> None:
        failure: Dict[str, Any] = {"invariant": invariant, "message": message}
        if detail is not None:
            failure["detail"] = detail
        failures.append(failure)

    for message in schema_errors(plan):
        fail(1, message)

    steps = existing_steps(plan)
    ids = known_step_ids(plan)
    edges = committed_edges(plan, ids)
    cycle = find_directed_cycle(edges)
    if cycle:
        fail(2, "Committed dependency graph contains a cycle", {"cycle": cycle})

    unresolved_list = _get(plan, "unresolved")
    unresolved = [entry for entry in unresolved_list if isinstance(entry, dict)] \
        if isinstance(unresolved_list, list) else []
    for entry in unresolved:
        reason, refused = _get(entry, "reason"), _get(entry, "cycle")
        if reason == "circular":
            if not isinstance(refused, list) or len(refused) < 2 or any(not _is_str(item) for item in refused):
                fail(2, "Circular unresolved entry must carry a cycle array of at least two step IDs",
                     {"entry": entry})
            else:
                missing = next((item for item in refused if item not in ids), _MISSING)
                if missing is not _MISSING:
                    fail(2, "Circular unresolved cycle references a nonexistent step",
                         {"stepId": missing, "cycle": refused})
                else:
                    if refused[0] != _get(entry, "step"):
                        fail(2, "Circular unresolved cycle must start with the refused step",
                             _detail(("stepId", _get(entry, "step")), ("cycle", refused)))
                    for index in range(1, len(refused)):
                        source, target = refused[index], refused[(index + 1) % len(refused)]
                        if target not in edges[source]:
                            fail(2, "Circular unresolved cycle does not contain the committed loop-back path",
                                 {"from": source, "to": target, "cycle": refused})
                            break
                    if refused[1] in edges[refused[0]]:
                        fail(2, "Circular unresolved cycle has an already committed refused edge",
                             {"from": refused[0], "to": refused[1], "cycle": refused})
        if reason == "residual-risk" and "cycle" in entry:
            fail(2, "Residual-risk unresolved entry must not carry cycle bookkeeping", {"entry": entry})

    for step in steps:
        inputs = _get(step, "inputs")
        if not isinstance(inputs, list):
            continue
        for entry in inputs:
            if not isinstance(entry, dict):
                continue
            source = _get(entry, "from")
            if source is not None and not _member(ids, source):
                fail(3, "Input supplier reference does not name an existing step",
                     _detail(("stepId", _get(step, "id")), ("from", source)))

    initial = _get(plan, "initial_state")
    initial_facts = {normalize_need_string(fact) for fact in (initial if isinstance(initial, list) else [])
                     if _is_str(fact)}
    for step in steps:
        inputs = _get(step, "inputs")
        if not isinstance(inputs, list) or not _is_str(_get(step, "id")):
            continue
        for entry in inputs:
            if not isinstance(entry, dict) or _get(entry, "from") is not None:
                continue
            need = _get(entry, "need")
            if _is_str(need) and normalize_need_string(need) not in initial_facts:
                fail(7, "Null-origin need is not declared in initial_state", {"stepId": step["id"], "need": need})

    goal_needs = _get(plan, "goal_needs")
    goal_needs_text = [normalize_need_string(need) for need in goal_needs if _is_str(need)] \
        if isinstance(goal_needs, list) else []
    goal = _get(plan, "goal")
    goal_text = normalize_need_string(goal) if _is_str(goal) else ""

    def satisfies_goal(step: Dict[str, Any]) -> bool:
        produces = _get(step, "produces")
        for raw in (produces if isinstance(produces, list) else []):
            if not _is_str(raw):
                continue
            text = normalize_need_string(raw)
            if not text:
                continue
            if text in goal_needs_text or (goal_text and text in goal_text):
                return True
        return False

    for discovered in steps:
        if _get(discovered, "origin") != "discovered" or not _is_str(_get(discovered, "id")):
            continue
        consumed = any(
            other is not discovered and isinstance(_get(other, "inputs"), list)
            and any(isinstance(entry, dict) and _get(entry, "from") == discovered["id"] for entry in other["inputs"])
            for other in steps)
        if consumed or satisfies_goal(discovered):
            continue
        fail(4, "Discovered step is neither consumed by another step nor satisfies a declared goal_needs entry",
             {"stepId": discovered["id"]})

    needs_by_step: Dict[str, set] = {}
    for step in steps:
        identifier, inputs = _get(step, "id"), _get(step, "inputs")
        if not _is_str(identifier) or not isinstance(inputs, list):
            continue
        needs = needs_by_step.setdefault(identifier, set())
        for entry in inputs:
            need = _get(entry, "need")
            if isinstance(entry, dict) and _is_str(need):
                needs.add(normalize_need_string(need))
    for entry in unresolved:
        step_id, need = _get(entry, "step"), _get(entry, "need")
        if (_is_str(step_id) and _is_str(need) and step_id in needs_by_step
                and normalize_need_string(need) in needs_by_step[step_id]):
            fail(5, "Need is tracked both as an input and unresolved for the same step",
                 {"stepId": step_id, "need": need})

    stored = _get(plan, "parallel_groups")
    if isinstance(stored, list):
        for group in stored:
            if not isinstance(group, list):
                continue
            for identifier in group:
                if not _member(ids, identifier):
                    fail(6, "parallel_groups references a nonexistent step", {"stepId": identifier})
    for entry in unresolved:
        step_id, refused = _get(entry, "step"), _get(entry, "cycle")
        if _is_str(step_id) and step_id not in ids:
            fail(6, "unresolved entry references a nonexistent step", {"stepId": step_id})
        if isinstance(refused, list):
            for identifier in refused:
                if _is_str(identifier) and identifier not in ids:
                    fail(6, "unresolved cycle references a nonexistent step", {"stepId": identifier})
    if isinstance(stored, list):
        computed = compute_parallel_groups(plan)
        if not groups_equal_as_sets(stored, computed):
            fail(6, "Stored parallel_groups does not match recomputed longest-path depth groups",
                 {"expected": computed, "actual": stored})

    return {"ok": not failures, "failures": jsonable(failures)}


def completion_status(plan: Any, structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """``completionStatus``: invalid, incomplete (unresolved or open goal needs) or complete."""
    structure = structure if structure is not None else validate_structure(plan)
    unresolved = _get(plan, "unresolved")
    unresolved_count = len(unresolved) if isinstance(unresolved, list) else 0
    if not structure["ok"]:
        return {"status": "invalid", "ok": False, "complete": False, "open_goal_needs": [],
                "unresolved_count": unresolved_count, "failures": structure["failures"]}
    open_goal_needs = []
    goal_needs = _get(plan, "goal_needs")
    if isinstance(goal_needs, list):
        initial = _get(plan, "initial_state")
        supplied = {normalize_need_string(fact) for fact in (initial if isinstance(initial, list) else [])
                    if _is_str(fact)}
        for step in existing_steps(plan):
            produces = _get(step, "produces")
            if isinstance(produces, list):
                supplied.update(normalize_need_string(item) for item in produces if _is_str(item))
        for need in goal_needs:
            if not _is_str(need):
                continue
            key = normalize_need_string(need)
            if key and key not in supplied:
                open_goal_needs.append(need)
    complete = unresolved_count == 0 and not open_goal_needs
    return {"status": "complete" if complete else "incomplete", "ok": True, "complete": complete,
            "open_goal_needs": open_goal_needs, "unresolved_count": unresolved_count, "failures": []}


# ---------------------------------------------------------------- receipt and CLI

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _counts(plan: Any) -> Dict[str, int]:
    """Plain-object steps, inputs and confirm entries, string produces, unresolved entries, discovered steps."""
    steps = existing_steps(plan)

    def entries(step: Dict[str, Any], key: str, kind: type) -> int:
        value = _get(step, key)
        return sum(isinstance(item, kind) for item in value) if isinstance(value, list) else 0

    unresolved = _get(plan, "unresolved")
    return {
        "steps": len(steps),
        "inputs": sum(entries(step, "inputs", dict) for step in steps),
        "produces": sum(entries(step, "produces", str) for step in steps),
        "confirms": sum(entries(step, "confirm", dict) for step in steps),
        "unresolved": len(unresolved) if isinstance(unresolved, list) else 0,
        "discovered": sum(_get(step, "origin") == "discovered" for step in steps),
    }


def receipt(data: bytes, candidate: str) -> Dict[str, Any]:
    """Check candidate bytes; raises CheckUnavailable when they are not JSON."""
    packaged = package(loads(data))
    structure = validate_structure(packaged)
    return {
        "schema": SCHEMA,
        "candidate": candidate,
        "candidate_sha256": _sha256(data),
        "packaged_sha256": _sha256(js_stringify(packaged).encode("utf-8")),
        "ok": structure["ok"],
        "failures": structure["failures"],
        "completion": completion_status(packaged, structure)["status"],
        "parallel_groups": compute_parallel_groups(packaged),
        "counts": _counts(packaged),
        "unconfirmed_produces": unconfirmed_produces(packaged),
    }


def check(path: Any) -> Dict[str, Any]:
    """Read and check one candidate file and return its receipt."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise CheckUnavailable(f"cannot read {path}: {exc.strerror or exc}") from exc
    return receipt(data, os.fspath(path))


def receipt_text(record: Dict[str, Any]) -> str:
    return json.dumps(record, indent=2) + "\n"


def _current_action(core: Any, run_dir: Optional[str]) -> Tuple[Optional[Path], Optional[str], str]:
    """(run root, current action id, reason) from saved state; reads only."""
    import shiploop_navigator as navigator
    import shiploop_store as store

    root = Path(core.run_dir_from_arg(run_dir, walk=True)).resolve()
    if not (root / "state.md").is_file():
        return None, None, f"no ShipLoop run at {root}"
    try:
        state = store.read_record(root / "state.md")
        action = navigator.current_action(state)["id"]
    except Exception as exc:  # noqa: BLE001 - any unreadable state only skips the files
        return None, None, f"run state at {root} cannot be read: {type(exc).__name__}: {exc}"
    if not isinstance(action, str) or not _ACTION_RE.fullmatch(action):
        return None, None, "the run has no current action"
    return root, action, ""


def _record_dir(root: Path, action: str) -> Path:
    directory = root / "backchain" / action
    for part in (root / "backchain", directory):
        if part.is_symlink():
            raise OSError(f"refusing symlink {part}")
    return directory


def record(root: Path, action: str, data: bytes, record_: Dict[str, Any]) -> Path:
    """Write ``candidate-<sha12>.json`` once and ``check-<sha12>.json`` when it changed; returns the receipt path."""
    import shiploop_store as store

    directory = _record_dir(root, action)
    digest = record_["candidate_sha256"][:12]
    snapshot = directory / f"candidate-{digest}.json"
    if snapshot.is_symlink():
        raise OSError(f"refusing symlink {snapshot}")
    if snapshot.exists():
        if snapshot.read_bytes() != data:
            raise OSError(f"{snapshot} holds other bytes")
    else:
        store.atomic_write_text(snapshot, data.decode("utf-8"))
    path = directory / f"check-{digest}.json"
    text = receipt_text(record_)
    if path.is_symlink():
        raise OSError(f"refusing symlink {path}")
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        store.atomic_write_text(path, text)
    return path


def summary(record_: Dict[str, Any]) -> str:
    counts = record_["counts"]
    if record_["ok"]:
        verdict = f"valid, {record_['completion']}"
    else:
        invariants = sorted({failure["invariant"] for failure in record_["failures"]})
        verdict = (f"invalid, {len(record_['failures'])} failure(s) on invariant(s) "
                   + ", ".join(map(str, invariants)))
    return (f"ShipLoop backchain-check: {verdict}; {counts['steps']} steps, "
            f"{len(record_['parallel_groups'])} parallel groups")


def main(core: Any, argv: Optional[List[str]] = None) -> int:
    """``shiploop backchain-check``: exit 0 valid, 1 invalid structure, 3 could not run."""
    parser = argparse.ArgumentParser(
        prog="shiploop backchain-check",
        description="Record-only check of a Backchain candidate plan against Backchain's structural "
                    "invariants (packaged first). Exit 0 valid, 1 invalid structure, 3 could not run.")
    parser.add_argument("--candidate", required=True, help="the candidate plan JSON file")
    parser.add_argument("--run-dir", help="the ShipLoop run; found from the working directory when omitted")
    args = parser.parse_args(list(argv or ()))
    try:
        data = Path(args.candidate).read_bytes()
        record_ = receipt(data, os.fspath(Path(args.candidate).absolute()))
    except OSError as exc:
        print(f"ShipLoop backchain-check could not run: cannot read {args.candidate}: {exc.strerror or exc}; "
              "this is not a finding", file=sys.stderr)
        return EXIT_UNAVAILABLE
    except CheckUnavailable as exc:
        hint = ""
        if str(exc).startswith("not JSON"):
            # Both round-1 runs passed the Markdown plan note; say what the candidate is and where its shape is defined.
            from shiploop_prompts import backchain_skills_root
            hint = ("; the candidate is the Backchain plan graph as a JSON file, not a Markdown plan note (its shape is "
                    f"defined in {backchain_skills_root() / 'backchain' / 'prompts' / 'generator.v1.md'})")
        print(f"ShipLoop backchain-check could not run: {exc}{hint}; this is not a finding", file=sys.stderr)
        return EXIT_UNAVAILABLE
    sys.stdout.write(receipt_text(record_))
    root, action, reason = _current_action(core, args.run_dir)
    note = f"not recorded: {reason}"
    if root is not None and action is not None:
        try:
            note = f"receipt {record(root, action, data, record_)}"
        except Exception as exc:  # noqa: BLE001 - recording is best effort; the receipt is printed
            note = f"not recorded: {type(exc).__name__}: {exc}"
    print(f"{summary(record_)}; {note}", file=sys.stderr)
    return EXIT_CLEAN if record_["ok"] else EXIT_FINDINGS
