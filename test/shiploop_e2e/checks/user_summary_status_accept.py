"""Held-out user-summary checks plus a finite reader for this fixture's living status fields."""
from __future__ import annotations

import importlib.util
from pathlib import Path, PurePosixPath
import re

_SPEC = importlib.util.spec_from_file_location(
    "shiploop_e2e_user_summary_accept", Path(__file__).with_name("user_summary_accept.py"))
T = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(T)

REQUIRED_IDS = ("R-1", "R-2", "R-3", "R-4")
FROZEN_HISTORY = "As of 2026-10-31: R-3 was accepted; implementation was pending; verification was not run."
CURRENT_FIELDS = {"current implementation", "current verification"}
FILE_PATH = re.compile(r"(?<![A-Za-z0-9_.-])(/?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:js|cjs|mjs))(?![A-Za-z0-9_.-])")


def _plain(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", text)
    return " ".join(text.split())


def _unfenced(lines: list[str]) -> list[tuple[int, str]]:
    kept = []
    fence: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is not None:
            if (marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1]
                    and not marker.group(2).strip()):
                fence = None
            continue
        if marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
            continue
        kept.append((index, line))
    return kept


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    found = []
    for index, line in _unfenced(lines):
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            found.append((index, len(match.group(1)), match.group(2).strip()))
    return found


def _records(spec: str) -> dict[str, list[list[str]]]:
    lines = spec.splitlines()
    headings = _headings(lines)
    requirements = [(index, level) for index, level, title in headings
                    if level == 2 and title.casefold() == "requirements"]
    if len(requirements) != 1:
        return {}
    root_start, root_level = requirements[0]
    root_end = len(lines)
    for index, level, _title in headings:
        if index > root_start and level <= root_level:
            root_end = index
            break
    active = [(index, level, title) for index, level, title in headings if root_start < index < root_end]
    records: dict[str, list[list[str]]] = {}
    for position, (start, level, title) in enumerate(active):
        match = re.match(r"^(R-\d+)\b", title)
        if not match:
            continue
        end = root_end
        for next_start, next_level, _next_title in active[position + 1:]:
            if next_level <= level:
                end = next_start
                break
        records.setdefault(match.group(1), []).append(lines[start:end])
    return records


def _field(line: str) -> tuple[str, str] | None:
    candidate = line.strip()
    while True:
        if candidate.startswith(">"):
            candidate = candidate[1:].lstrip()
        elif re.match(r"^[-*+]\s+", candidate):
            candidate = re.sub(r"^[-*+]\s+", "", candidate, count=1)
        else:
            break
    patterns = (
        r"^\*\*([A-Za-z][A-Za-z ]*?):\*\*\s*(.*)$",
        r"^\*\*([A-Za-z][A-Za-z ]*)\*\*:\s*(.*)$",
        r"^([A-Za-z][A-Za-z ]*):\s*(.*)$",
    )
    for pattern in patterns:
        match = re.match(pattern, candidate)
        if match:
            return match.group(1).strip().casefold(), match.group(2).strip()
    return None


def _fields(section: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    values: dict[str, list[str]] = {}
    unknown_current = []
    last_label = None
    for _index, line in _unfenced(section):
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            last_label = None
            continue
        parsed = _field(line)
        if parsed:
            label, value = parsed
            if label in {"requirement", "status", *CURRENT_FIELDS}:
                values.setdefault(label, []).append(value)
                last_label = label
            elif label.startswith("current "):
                unknown_current.append(label)
                last_label = None
            else:
                last_label = None
            continue
        if line.strip() and last_label and values.get(last_label):
            values[last_label][-1] += " " + line.strip()
    return values, unknown_current


def _read_spec(product) -> tuple[str | None, str]:
    path = product.folder / "docs/shiploop/spec.md"
    try:
        return path.read_text(), ""
    except OSError as exc:
        return None, f"cannot read docs/shiploop/spec.md: {exc}"


def _one_record(records: dict[str, list[list[str]]], ident: str) -> tuple[list[str] | None, str]:
    found = records.get(ident, [])
    if len(found) != 1:
        return None, f"expected one {ident} requirement section, found {len(found)}"
    return found[0], ""


def summary_status_records(_base: str, product) -> tuple[bool, str]:
    spec, error = _read_spec(product)
    if spec is None:
        return False, error
    records = _records(spec)
    for ident in REQUIRED_IDS:
        section, error = _one_record(records, ident)
        if section is None:
            return False, error
        fields, _unknown = _fields(section)
        requirements = fields.get("requirement", [])
        if len(requirements) != 1 or not _plain(requirements[0]):
            return False, f"{ident} must retain one nonempty Requirement field"
    return True, "R-1 through R-4 retain one requirement heading and nonempty intent field each"


def _current_fields(section: list[str]) -> tuple[dict[str, list[str]], str | None]:
    values, unknown = _fields(section)
    if unknown:
        return values, "unknown current field: " + ", ".join(unknown)
    for label in ("status", "current implementation", "current verification"):
        if len(values.get(label, [])) != 1:
            return values, f"expected one {label} field, found {len(values.get(label, []))}"
    return values, None


def _state_token(value: str) -> str:
    normalized = _plain(value).casefold()
    match = re.match(r"^(not started|not run|implemented|complete|passed|accepted|deferred)(?=$|[\s:;,.—-])", normalized)
    return match.group(1) if match else ""


def _evidence_paths(value: str, product, *, kind: str) -> tuple[bool, str]:
    candidates = FILE_PATH.findall(_plain(value))
    if not candidates:
        return False, f"{kind} evidence must name a repo-relative JavaScript file"
    root = Path(product.folder).resolve()
    rejected = []
    for candidate in candidates:
        path = PurePosixPath(candidate)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            rejected.append(f"path must stay within the delivered repository: {candidate}")
            continue
        if kind == "test" and (not path.parts or path.parts[0] != "test"):
            rejected.append(f"verification evidence must be under test/: {candidate}")
            continue
        if kind == "source" and path.parts and path.parts[0] == "test":
            rejected.append(f"implementation evidence must point to source, not a test: {candidate}")
            continue
        resolved = (root / Path(*path.parts)).resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            rejected.append(f"evidence file does not resolve in the delivered repository: {candidate}")
            continue
        return True, ""
    detail = "; ".join(rejected)
    return False, f"{kind} evidence must include a resolving repo-relative file of the correct kind: {detail}"


def summary_status_current(_base: str, product) -> tuple[bool, str]:
    spec, error = _read_spec(product)
    if spec is None:
        return False, error
    section, error = _one_record(_records(spec), "R-3")
    if section is None:
        return False, error
    fields, error = _current_fields(section)
    if error:
        return False, error
    status = _state_token(fields["status"][0])
    implementation = _state_token(fields["current implementation"][0])
    verification = _state_token(fields["current verification"][0])
    if status != "accepted":
        return False, "R-3 Status must retain the accepted requirement state"
    if implementation not in {"implemented", "complete"}:
        return False, "R-3 Current implementation needs an implemented or complete state token"
    ok, note = _evidence_paths(fields["current implementation"][0], product, kind="source")
    if not ok:
        return False, "R-3 Current implementation: " + note
    if verification != "passed":
        return False, "R-3 Current verification needs a passed state token"
    ok, note = _evidence_paths(fields["current verification"][0], product, kind="test")
    if not ok:
        return False, "R-3 Current verification: " + note
    return True, "R-3 current fields carry completed/pass tokens and resolving source/test evidence"


def _history_text(spec: str) -> tuple[str, str | None]:
    lines = spec.splitlines()
    headings = _headings(lines)
    starts = [(index, level) for index, level, title in headings if level == 2 and title.casefold() == "history"]
    if len(starts) != 1:
        return "", f"expected one ## History section, found {len(starts)}"
    start, level = starts[0]
    end = len(lines)
    for next_start, next_level, _title in headings:
        if next_start > start and next_level <= level:
            end = next_start
            break
    content = []
    for _index, line in _unfenced(lines[start + 1:end]):
        candidate = line.strip()
        if not candidate:
            continue
        while True:
            if candidate.startswith(">"):
                candidate = candidate[1:].lstrip()
            elif re.match(r"^[-*+]\s+", candidate):
                candidate = re.sub(r"^[-*+]\s+", "", candidate, count=1)
            else:
                break
        if candidate:
            content.append(candidate)
    return _plain(" ".join(content)), None


def summary_status_history(_base: str, product) -> tuple[bool, str]:
    spec, error = _read_spec(product)
    if spec is None:
        return False, error
    history, error = _history_text(spec)
    if error:
        return False, error
    if _plain(FROZEN_HISTORY).casefold() not in history.casefold():
        return False, "the frozen 2026-10-31 observation must remain intact in History"
    return True, "the dated earlier R-3 observation remains intact"


def summary_status_deferred(_base: str, product) -> tuple[bool, str]:
    spec, error = _read_spec(product)
    if spec is None:
        return False, error
    section, error = _one_record(_records(spec), "R-4")
    if section is None:
        return False, error
    fields, error = _current_fields(section)
    if error:
        return False, error
    status = _state_token(fields["status"][0])
    implementation = _state_token(fields["current implementation"][0])
    verification = _state_token(fields["current verification"][0])
    if (status, implementation, verification) != ("deferred", "not started", "not run"):
        return False, "R-4 must remain deferred, not started, and not run"
    return True, "R-4 remains deferred with no implementation or verification claim"


CHECKS = {
    **T.CHECKS,
    "summary-status-records": summary_status_records,
    "summary-status-current": summary_status_current,
    "summary-status-history": summary_status_history,
    "summary-status-deferred": summary_status_deferred,
}
