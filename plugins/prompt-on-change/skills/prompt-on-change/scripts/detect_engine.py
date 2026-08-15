#!/usr/bin/env python3
"""Universal Change-Detection Guard Engine — config-driven URL monitoring with
deterministic condition evaluation and LLM escalation on edge conditions.

# Flow diagram:
#   main → run_engine
#   run_engine: load_config → StateManager.load → FetchAgent.fetch → ExtractAgent.extract
#           → TriggerAgent.evaluate → GroupEvaluator.evaluate_group → ActionAgent.execute
#           → LLMEscalationAgent.escalate / write_fetch_failure_escalation
#           → StateManager.save → write_health
# Called by: CLI (main), cron jobs, tests
# Calls: gws_utils, httpx, pydantic, yaml, jsonpath_ng, selectolax

Two-layer architecture:
  Layer 1 (this script, no LLM): fetch → extract → compare → evaluate → act
  Layer 2 (LLM agent cron, fires on escalation): reads evidence file → reasons

Usage:
  python detect_engine.py --config configs/as706_flight.yaml
  python detect_engine.py --config configs/as706_flight.yaml --dry-run
  python detect_engine.py --config configs/as706_flight.yaml --validate
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from zoneinfo import ZoneInfo

# ── Third-party imports ──
import httpx
from jsonpath_ng import parse as jsonpath_parse
from selectolax.parser import HTMLParser
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
import yaml

# ── Local imports ──
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_ROOT = Path(os.environ.get("SKILL_ROOT", str(SCRIPT_DIR.parent))).resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# Calendar adapter is optional. Prompt-event core must import without gws.
try:
    from gws_utils import gws_get_event, gws_patch_event, gws_delete_event  # noqa: E402
except ImportError:  # pragma: no cover — gws_utils ships with the package
    def gws_get_event(*_args, **_kwargs):
        return None

    def gws_patch_event(*_args, **_kwargs):
        return False

    def gws_delete_event(*_args, **_kwargs):
        return False


def _default_state_dir() -> Path:
    """Write-safe runtime home. Distinct from SKILL_ROOT (package) and transport bins."""
    override = os.environ.get("POC_STATE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg) / "prompt-on-change"
    return Path.home() / ".local" / "state" / "prompt-on-change"


# ── Constants ──
_STATE_DIR = _default_state_dir()
LOG_FILE = Path(os.environ.get("DETECT_ENGINE_LOG_FILE", str(_STATE_DIR / "detect-engine.log")))
# HEALTH_DIR / ESCALATION_DIR are env-overridable at import; tests may still
# monkeypatch the module globals after import (env is only the default).
HEALTH_DIR = Path(os.environ.get("DETECT_ENGINE_HEALTH_DIR", str(_STATE_DIR)))
ESCALATION_DIR = Path(os.environ.get("DETECT_ENGINE_ESCALATION_DIR", str(_STATE_DIR / "escalations")))
# Cap for regex-scanned text (extract body, preserve_from_desc) to limit ReDoS.
REGEX_INPUT_CAP = 100000
# Cap for condition-op `matches` scanned value (same ReDoS class as REGEX_INPUT_CAP).
MATCHES_INPUT_CAP = 10000
# Persisted timestamps farther ahead than this are treated as invalid clock skew.
CLOCK_SKEW_TOLERANCE = timedelta(seconds=60)
# Max and:/or:/not:/unless: nesting under a top-level condition (cross-ref + evaluate).
# Far below sys.getrecursionlimit(); pathological trees fail validation cleanly.
MAX_CONDITION_DEPTH = 32
DEFAULT_TZ = ZoneInfo("America/Los_Angeles")
# F4.3 FIX: Distinguish an unavailable calendar baseline from a real JSON null value.
BASELINE_UNAVAILABLE = object()
# Optional-source fetch failures shadow stale state for this poll only.
VALUE_UNAVAILABLE = object()


class UnavailableTemplateVar(Exception):
    """An action template referenced a value unavailable for this poll."""
    def __init__(self, var_name: str):
        self.var_name = var_name
        super().__init__(var_name)


log = logging.getLogger("detect_engine")


# ═══════════════════════════════════════════════════════════════
#  Pydantic Config Schema
# ═══════════════════════════════════════════════════════════════

class ExtractSpec(BaseModel):
    # State: Pydantic schema item for one extraction rule
    id: str
    type: str  # jsonpath | css | regex | jsonpath_from_html | header
    path: Optional[str] = None
    selector: Optional[str] = None
    pattern: Optional[str] = None
    group: int = 0
    transform: Optional[str] = None  # "text" | "attr:href" | "text|upper"
    name: Optional[str] = None  # for header type


class RetryConfig(BaseModel):
    # State: Pydantic schema for fetch retry policy
    count: int = 2
    backoff: int = 3  # seconds, exponential: 3, 6, 12...
    # If all retries fail and this is set, write a fetch-failure escalation file
    # that an LLM agent cron can pick up. Contains: URL, error, attempts, source config.
    escalate_on_failure: bool = False


class Source(BaseModel):
    # State: Pydantic schema for one URL source
    id: str
    url: str
    method: str = "GET"
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    required: bool = True
    timeout: int = 15
    retry: Optional[RetryConfig] = None
    extract: list[ExtractSpec] = []
    # Allow per-source LLM prompt for fetch-failure escalation
    failure_prompt: Optional[str] = None


class Condition(BaseModel):
    # State: Pydantic schema for one condition or nested combinator
    model_config = ConfigDict(populate_by_name=True)

    id: str = ""  # Optional for nested conditions inside and/or/not/unless
    field: Optional[str] = None
    op: Optional[str] = None
    value: Optional[Any] = None
    compared_to: Optional[str] = None
    min_value: Optional[Any] = Field(None, alias="min")
    max_value: Optional[Any] = Field(None, alias="max")
    fields: list[str] = []
    delta: Optional[dict[str, Any]] = None
    for_: Optional[str] = Field(None, alias="for")
    and_: Optional[list[dict]] = Field(None, alias="and")
    or_: Optional[list[dict]] = Field(None, alias="or")
    not_: Optional[list[dict]] = Field(None, alias="not")
    baseline: Optional[dict] = None
    unless: Optional[dict] = None
    refire_after: Optional[str] = None

    # ── Validate op values ──
    VALID_OPS: ClassVar[set[str]] = {
        "changed", "eq", "ne", "contains", "exists", "matches", "empty",
        "became_empty", "became_nonempty",
        "gt", "gte", "lt", "lte", "between",
        "delta_gt", "delta_gte", "delta_lt", "delta_lte", "delta_between",
        "time_diff_gt", "time_diff_lt",
        "time_shift_gt", "time_shift_lt",
        "any_changed", "all_changed", "any_empty", "all_empty",
        "any_became_empty", "all_became_empty",
        "any_became_nonempty", "all_became_nonempty",
    }
    FIELDLESS_OPS: ClassVar[set[str]] = {
        "any_changed", "all_changed", "any_empty", "all_empty",
        "any_became_empty", "all_became_empty",
        "any_became_nonempty", "all_became_nonempty",
    }
    RANGE_OPS: ClassVar[set[str]] = {"between", "delta_between"}
    DELTA_OPS: ClassVar[set[str]] = {
        "delta_gt", "delta_gte", "delta_lt", "delta_lte", "delta_between",
    }

    @field_validator("op")
    @classmethod
    def validate_op(cls, v):
        if v is not None and v not in cls.VALID_OPS:
            raise ValueError(f"invalid op '{v}' — must be one of {sorted(cls.VALID_OPS)}")
        return v

    @model_validator(mode="after")
    def validate_range_and_compound(self):
        op = self.op
        if op in self.FIELDLESS_OPS and not self.fields:
            raise ValueError(f"op '{op}' requires a non-empty fields: list")
        if op in self.RANGE_OPS:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"op '{op}' requires min and max")
        if op in self.DELTA_OPS and op != "delta_between" and self.value is None:
            raise ValueError(f"op '{op}' requires value")
        if self.delta is not None:
            if not isinstance(self.delta, dict):
                raise ValueError("delta: must be a mapping")
            allowed = {
                "any", "all", "empty", "nonempty", "became_empty",
                "became_nonempty", "range",
            }
            unknown = set(self.delta) - allowed
            if unknown:
                raise ValueError(f"delta: unknown keys {sorted(unknown)}")
            has_clause = any(
                self.delta.get(k) for k in (
                    "any", "all", "empty", "nonempty",
                    "became_empty", "became_nonempty", "range",
                )
            )
            if not has_clause:
                raise ValueError("delta: needs at least one of any/all/empty/nonempty/became_empty/became_nonempty/range")
            range_spec = self.delta.get("range")
            if range_spec is not None:
                if not isinstance(range_spec, dict) or not range_spec.get("field"):
                    raise ValueError("delta.range requires field")
                if range_spec.get("min") is None or range_spec.get("max") is None:
                    raise ValueError("delta.range requires min and max")
        return self


class Group(BaseModel):
    # State: Pydantic schema for a condition group (any/all) + actions
    name: str
    any: list[str] = []
    all: list[str] = []
    actions: list[str] = []

    @model_validator(mode="after")
    def validate_any_all_exclusive(self):
        """Reject ambiguous groups that would otherwise give ``any`` precedence."""
        if self.any and self.all:
            raise ValueError(f"group '{self.name}' cannot declare both non-empty any and all")
        return self


class ActionDef(BaseModel):
    # State: Pydantic schema for one calendar action definition
    type: str = "calendar_patch"
    event_id: Optional[Any] = None  # str or {from_state: ...}
    calendar_id: str = "primary"
    fields: dict[str, Any] = {}
    offset_minutes: Optional[int] = None
    computed: dict[str, str] = {}


class LLMEscalation(BaseModel):
    # State: Pydantic schema for LLM escalation config
    trigger_groups: list[str] = []
    fire_once: bool = True
    model: Optional[str] = None
    deliver: str = "origin"
    prompt: str = ""
    evidence: dict[str, bool] = {}
    escalation_backoff: str = "1h"


class StateConfig(BaseModel):
    # State: Pydantic schema for state file config
    file: str = "state.json"
    initial: dict[str, Any] = {}


class DetectConfig(BaseModel):
    # State: Pydantic root config schema
    name: str
    expires: Optional[str] = None
    enabled: bool = True
    seed_mode: bool = True  # True = first poll observes only, saves state, no actions
    sources: list[Source] = []
    conditions: list[Condition] = []
    groups: list[Group] = []
    actions: dict[str, dict] = {}
    llm_escalation: Optional[LLMEscalation] = None
    state: StateConfig = StateConfig()


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _fire_once_enabled(config: DetectConfig) -> bool:
    """P0-3 FIX: fire_once is independent of llm_escalation presence.
    Defaults to True if llm_escalation is not configured (fire_once is the
    safe default — don't re-fire for the same value).
    """
    if config.llm_escalation:
        return config.llm_escalation.fire_once
    return True  # Default: always fire_once


def _collect_leaf_fields(cond: Condition) -> list[str]:
    """Stable unique leaf field names under a condition tree (and/or/not/unless/delta)."""
    seen: list[str] = []

    def add(name: Optional[str]) -> None:
        if name and name not in seen:
            seen.append(name)

    def walk(c: Condition) -> None:
        add(c.field)
        for name in c.fields:
            add(name)
        if c.delta:
            for key in ("any", "all", "empty", "nonempty", "became_empty", "became_nonempty"):
                for name in c.delta.get(key) or []:
                    add(name)
            range_spec = c.delta.get("range") or {}
            if isinstance(range_spec, dict):
                add(range_spec.get("field"))
        for kids in (c.and_, c.or_, c.not_):
            if kids:
                for raw in kids:
                    walk(Condition(**raw))
        if c.unless:
            walk(Condition(**c.unless))

    walk(cond)
    return seen


def _is_empty_value(val: Any) -> bool:
    """Treat None, whitespace-only strings, and empty collections as empty."""
    if val is None or val is VALUE_UNAVAILABLE:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    if isinstance(val, (list, dict, tuple, set)):
        return len(val) == 0
    return False


def _as_float(val: Any) -> Optional[float]:
    if val is None or val is VALUE_UNAVAILABLE:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _numeric_delta(previous: Any, current: Any) -> Optional[float]:
    prev_n = _as_float(previous)
    new_n = _as_float(current)
    if prev_n is None or new_n is None:
        return None
    return new_n - prev_n


def _state_delta(prev_snapshot: dict, current_snapshot: dict) -> dict:
    """Per-field prev→new map for values that actually changed."""
    keys = set(prev_snapshot) | set(current_snapshot)
    fields: dict[str, dict[str, Any]] = {}
    for key in sorted(keys):
        previous = prev_snapshot.get(key)
        new = current_snapshot.get(key)
        if previous == new:
            continue
        fields[key] = {
            "previous": previous,
            "new": new,
            "numeric_delta": _numeric_delta(previous, new),
            "became_empty": (not _is_empty_value(previous)) and _is_empty_value(new),
            "became_nonempty": _is_empty_value(previous) and (not _is_empty_value(new)),
        }
    return {"fields": fields, "changed_fields": list(fields.keys())}


def write_health(health_file: str | Path, status: str, config_name: str = "", detail: str = ""):
    """Write health status to a JSON file (atomic: tmp → rename)."""
    try:
        health_file = Path(health_file)
        health_file.parent.mkdir(parents=True, exist_ok=True)
        health = {
            "status": status,
            "config": config_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
        tmp = health_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(health, indent=2) + "\n")
        tmp.replace(health_file)
    except Exception as exc:
        log.error(f"write_health({health_file}): failed: {exc}")


def _condition_ack_value(cond: Condition, eval_context: dict) -> Any:
    """Value used for fire_once acknowledgement comparison.

    Leaf conditions key on their field's current value (enables A→B→A re-fire).
    Fieldless composites (top-level and:/or:/not:) have no ``field``, so a bare
    ``eval_context.get(cond.field)`` is always None and would permanently suppress
    after the first fire. Instead key on a stable signature of all leaf field
    values so Delayed→Cancelled (etc.) re-fires while identical signatures stay
    suppressed.
    """
    if (
        cond.and_ is not None
        or cond.or_ is not None
        or cond.not_ is not None
        or cond.delta is not None
        or (cond.op in Condition.FIELDLESS_OPS)
    ):
        fields = _collect_leaf_fields(cond)
        return {
            f: None if eval_context.get(f) is VALUE_UNAVAILABLE else eval_context.get(f)
            for f in fields
        }
    if cond.field:
        value = eval_context.get(cond.field)
        return None if value is VALUE_UNAVAILABLE else value
    return None


def _fields_to_hold(cond: Condition) -> list[str]:
    """Fields whose extracted values must be held while this condition is gated.

    Leaf conditions hold ``cond.field``. Composites hold every nested leaf field
    so a ``for:`` / ``refire_after`` gate cannot consume a nested ``changed``
    baseline before the gate opens.
    """
    return _collect_leaf_fields(cond)


# ── H8 FIX: Redact secret-like keys from dicts before serialization ──
_SECRET_KEY_PATTERNS = re.compile(
    r"(authorization|x-api-key|api[_-]?key|token|secret|password|bearer|credential)",
    re.IGNORECASE,
)


def _redact_secrets(d: dict[str, str]) -> dict[str, str]:
    """Return a copy of dict with secret-like keys replaced by '***REDACTED***'."""
    if not d:
        return {}
    redacted = {}
    for k, v in d.items():
        if _SECRET_KEY_PATTERNS.search(k):
            redacted[k] = "***REDACTED***"
        else:
            redacted[k] = v
    return redacted


# Query/userinfo keys whose values must never land in evidence or LLM prompts.
_SENSITIVE_URL_QUERY_KEYS = re.compile(
    r"^(token|key|secret|sig|password|access_token|api[_-]?key|auth|authorization|bearer)$",
    re.IGNORECASE,
)


def _redact_url(url: str) -> str:
    """Strip userinfo and mask sensitive query values from a source URL for evidence/prompts."""
    if not url:
        return url
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    # Mask userinfo: https://user:pass@host → https://***REDACTED***@host
    netloc = parsed.netloc
    if "@" in netloc:
        host = netloc.rsplit("@", 1)[-1]
        netloc = f"***REDACTED***@{host}"
    # Mask sensitive query values while preserving key names and non-sensitive params.
    if parsed.query:
        pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if _SENSITIVE_URL_QUERY_KEYS.search(key) or _SECRET_KEY_PATTERNS.search(key):
                pairs.append((key, "***REDACTED***"))
            else:
                pairs.append((key, value))
        query = urlencode(pairs)
    else:
        query = parsed.query
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, query, parsed.fragment))


def _canonical_slug(value: str) -> str:
    """Return the bounded, filesystem-safe identity slug for a config name."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    slug = slug[:80].rstrip("-")
    return slug or "unnamed"


def _safe_path_component(value: str) -> str:
    """Return a safe evidence filename component while retaining readable case."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", value) or "unnamed"


def _derived_path_within(base_dir: Path, filename: str, purpose: str) -> Optional[Path]:
    """Build a derived path only when it resolves beneath its intended directory."""
    path = base_dir / filename
    try:
        if not path.resolve().is_relative_to(base_dir.resolve()):
            log.error(f"Engine: refusing {purpose} path outside {base_dir}: {path}")
            return None
    except (OSError, RuntimeError) as exc:
        log.error(f"Engine: could not validate {purpose} path {path}: {exc}")
        return None
    return path


def _resolve_baseline_event(
    cond: Condition, prev_state: dict, calendar_events: dict[str, dict]
) -> Optional[dict]:
    """Resolve a calendar-baseline event from its id spec, cache, or Calendar API."""
    if not cond.baseline:
        return None
    event_id_ref = cond.baseline.get("event_id", {})
    if isinstance(event_id_ref, dict) and "from_state" in event_id_ref:
        event_id = prev_state.get(event_id_ref["from_state"], "")
    elif isinstance(event_id_ref, str):
        event_id = event_id_ref
    else:
        event_id = ""

    for cal_ev in calendar_events.values():
        if cal_ev and cal_ev.get("id") == event_id:
            return cal_ev
    return gws_get_event(event_id) if event_id else None


def _calendar_event_evidence_slice(ev: Any) -> dict[str, Any]:
    """Safe summary/start/end projection for LLM evidence (tolerates malformed events)."""
    if not isinstance(ev, dict):
        return {"summary": "", "start": "", "end": ""}
    start = ev.get("start")
    end = ev.get("end")
    return {
        "summary": ev.get("summary", ""),
        "start": start.get("dateTime", "") if isinstance(start, dict) else "",
        "end": end.get("dateTime", "") if isinstance(end, dict) else "",
    }


def _parse_datetime_iso(val: Any) -> Optional[datetime]:
    """Parse every datetime format accepted by condition and action paths."""
    if not val or val == "None":
        return None
    s = str(val)
    for candidate in [s, s.replace("Z", "+00:00")]:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S %p"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _filter_add_minutes(val: Any, filter_text: str) -> tuple[Any, bool]:
    """Apply ``add_minutes``; True means template replacement should stop."""
    minutes_str = filter_text.split(":", 1)[1]
    try:
        minutes = int(minutes_str)
    except ValueError:
        log.warning(f"_render_template: malformed add_minutes filter '{filter_text}'")
        return "", True
    dt = _parse_datetime_iso(val)
    return ((dt + timedelta(minutes=minutes)).isoformat(), False) if dt else ("", True)


def _short_timezone_name(dt_local: datetime, use_named_fallback: bool = False) -> str:
    """Render the compact timezone names used in calendar templates."""
    full_tz = dt_local.tzname() or ""
    if full_tz.startswith(("PS", "PD")):
        return "PT"
    if full_tz.startswith(("ES", "ED")):
        return "ET"
    if full_tz.startswith(("CS", "CD")):
        return "CT"
    if full_tz.startswith(("MS", "MD")):
        return "MT"
    if full_tz.startswith(("AK",)):
        return "AKT"
    if full_tz.startswith(("HS", "HA")):
        return "HST"
    if use_named_fallback:
        return full_tz[:3] if full_tz else "UTC"
    if full_tz.startswith("UTC"):
        utc_off = dt_local.utcoffset()
        if utc_off is None:
            return "UTC"
        sign = "+" if utc_off.total_seconds() >= 0 else "-"
        off_h = int(abs(utc_off.total_seconds()) / 3600)
        off_m = int((abs(utc_off.total_seconds()) % 3600) / 60)
        return f"UTC{sign}{off_h:02d}:{off_m:02d}" if off_m else f"UTC{sign}{off_h:02d}"
    utc_off = dt_local.utcoffset()
    if utc_off is None:
        return "UTC"
    sign = "+" if utc_off.total_seconds() >= 0 else "-"
    off_h = int(abs(utc_off.total_seconds()) / 3600)
    off_m = int((abs(utc_off.total_seconds()) % 3600) / 60)
    return f"UTC{sign}{off_h:02d}:{off_m:02d}"


def _filter_fmt_time(val: Any, filter_text: str) -> tuple[Any, bool]:
    """Apply ``fmt_time`` with the existing explicit/default timezone behavior."""
    dt = _parse_datetime_iso(val)
    if not dt:
        return "N/A", False
    tz_arg = filter_text.split(":", 1)[1].strip() if ":" in filter_text and not filter_text.endswith(":") else None
    try:
        tz = ZoneInfo(tz_arg) if tz_arg else (dt.tzinfo or DEFAULT_TZ)
    except Exception as exc:
        # Invalid IANA name must not crash the poll (ZoneInfoNotFoundError, etc.).
        log.warning(f"_render_template: invalid fmt_time timezone {tz_arg!r}: {exc}")
        return "N/A", False
    dt_local = dt.astimezone(tz)
    return dt_local.strftime("%-I:%M %p ") + _short_timezone_name(dt_local, bool(tz_arg)), False


def _filter_default(val: Any, filter_text: str) -> tuple[Any, bool]:
    """Apply ``default`` when the value is absent."""
    if val is None or val == "" or val == "None":
        return filter_text.split(":", 1)[1].strip(), False
    return val, False


def _filter_if_present(val: Any, _filter_text: str) -> tuple[Any, bool]:
    """Suppress the current template token when the value is absent."""
    return ("", True) if val is None or val == "" or val == "None" else (val, False)


TEMPLATE_FILTERS = {
    "add_minutes": _filter_add_minutes,
    "fmt_time": _filter_fmt_time,
    "default": _filter_default,
    "if_present": _filter_if_present,
}


def _template_filter_handler(filter_text: str):
    """Return the registered handler while preserving the original prefix matching."""
    if filter_text.startswith("add_minutes:"):
        return TEMPLATE_FILTERS["add_minutes"]
    if filter_text.startswith("fmt_time"):
        return TEMPLATE_FILTERS["fmt_time"]
    if filter_text.startswith("default:"):
        return TEMPLATE_FILTERS["default"]
    return TEMPLATE_FILTERS.get(filter_text)


def _render_template_vars(
    template: str, context: dict, *, strict_unavailable: bool = False,
) -> str:
    """Render ``{{ var }}`` expressions with the shared template filters."""
    def replace_match(match):
        expr = match.group(1).strip()
        parts = [part.strip() for part in expr.split("|")]
        var_name = parts[0]
        val = context.get(var_name, "")
        if strict_unavailable and val is VALUE_UNAVAILABLE:
            raise UnavailableTemplateVar(var_name)

        for filter_text in parts[1:]:
            handler = _template_filter_handler(filter_text)
            if handler:
                val, stop = handler(val, filter_text)
                if stop:
                    return ""

        return "" if val is None else str(val)

    return re.sub(r"\{\{([^}]+)\}\}", replace_match, template)

# ═══════════════════════════════════════════════════════════════
#  FetchAgent — HTTP GET with retry/backoff
# ═══════════════════════════════════════════════════════════════

class FetchResult:
    # State: ok=True (status<400, no error) | ok=False (error or status>=400)
    # Called by: FetchAgent.fetch → run_engine step 4
    def __init__(self, status_code: int, headers: dict, body: str, error: str = "",
                 attempts: int = 0, last_error_type: str = ""):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.error = error
        self.attempts = attempts  # Total attempts made (including first)
        self.last_error_type = last_error_type  # Exception class name

    @property
    def ok(self) -> bool:
        return self.error == "" and self.status_code < 400


def _is_retryable_http_status(status_code: int) -> bool:
    """Return whether an HTTP status should be retried (408, 429, 5xx). Other 4xx fail-fast."""
    return status_code == 408 or status_code == 429 or status_code >= 500


class FetchAgent:
    # Called by: run_engine step 4. Calls: httpx.Client.request. Returns: FetchResult.
    def fetch(self, source: Source) -> FetchResult:
        """Fetch a URL with retry/backoff. Returns FetchResult with attempt details."""
        retry_cfg = source.retry or RetryConfig()
        env_params = self._resolve_env_vars(source.params)
        # P2: also resolve {{env:VAR}} in headers and URL (params already supported).
        env_headers = self._resolve_env_vars(source.headers)
        env_url = self._resolve_env_string(source.url)
        total_attempts = retry_cfg.count + 1

        # httpx 0.28+ defaults follow_redirects=False; without following, a 3xx is
        # status<400 so FetchResult.ok is True with an empty/redirect body and
        # extraction silently returns None (state clobber risk on successful polls).
        with httpx.Client(timeout=source.timeout, follow_redirects=True) as client:
            for attempt in range(total_attempts):
                try:
                    resp = client.request(
                        source.method,
                        env_url,
                        headers=env_headers,
                        params=env_params,
                    )
                    # Retry transient HTTP statuses (CDN 503/502, rate-limit 429, request timeout 408).
                    # Fail-fast on other 4xx (including intentional non-retry of 404).
                    if _is_retryable_http_status(resp.status_code) and attempt < retry_cfg.count:
                        wait = retry_cfg.backoff * (2 ** attempt)
                        log.warning(
                            f"FetchAgent({source.id}): attempt {attempt+1}/{total_attempts} "
                            f"HTTP {resp.status_code}, retrying in {wait}s"
                        )
                        time.sleep(wait)
                        continue
                    return FetchResult(resp.status_code, dict(resp.headers), resp.text,
                                       attempts=attempt + 1)
                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError,
                        httpx.RemoteProtocolError, httpx.PoolTimeout,
                        httpx.NetworkError) as exc:
                    error_type = type(exc).__name__
                    if attempt < retry_cfg.count:
                        wait = retry_cfg.backoff * (2 ** attempt)
                        log.warning(f"FetchAgent({source.id}): attempt {attempt+1}/{total_attempts} "
                                    f"failed ({error_type}: {exc}), retrying in {wait}s")
                        time.sleep(wait)
                    else:
                        log.error(f"FetchAgent({source.id}): all {total_attempts} attempts failed "
                                  f"({error_type}: {exc})")
                        return FetchResult(0, {}, "", str(exc),
                                           attempts=total_attempts, last_error_type=error_type)
                except Exception as exc:
                    # Unexpected error — don't retry, escalate immediately
                    error_type = type(exc).__name__
                    log.error(f"FetchAgent({source.id}): unexpected error ({error_type}: {exc})")
                    return FetchResult(0, {}, "", f"{error_type}: {exc}",
                                       attempts=attempt + 1, last_error_type=error_type)
        return FetchResult(0, {}, "", "unreachable", attempts=total_attempts, last_error_type="Unreachable")

    def _resolve_env_string(self, value: str) -> str:
        """Resolve {{env:VAR_NAME}} patterns in a single string (supports mixed strings)."""
        if not isinstance(value, str) or "{{env:" not in value:
            return value
        pattern = re.compile(r"\{\{env:(\w+)\}\}")

        def repl(m):
            var = m.group(1)
            val = os.environ.get(var)
            if val is None:
                log.warning(f"FetchAgent: env var '{var}' not found, using empty string")
                return ""
            return val

        return pattern.sub(repl, value)

    def _resolve_env_vars(self, params: dict) -> dict:
        """Resolve {{env:VAR_NAME}} patterns in a string-valued dict (params/headers)."""
        if not params:
            return {}
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str):
                # H6 FIX: Use re.sub to interpolate env vars in mixed strings
                resolved[k] = self._resolve_env_string(v)
            else:
                resolved[k] = v
        return resolved


# ═══════════════════════════════════════════════════════════════
#  ExtractAgent — JSONPath / CSS / regex / jsonpath_from_html
# ═══════════════════════════════════════════════════════════════

class ExtractAgent:
    # Called by: run_engine step 4. Calls: jsonpath_ng, selectolax, re. Returns: {spec.id: value|None}.
    def extract(self, fetch_result: FetchResult, specs: list[ExtractSpec]) -> dict[str, Any]:
        """Extract values from a fetch result based on extraction specs."""
        values = {}
        for spec in specs:
            try:
                val = self._extract_one(fetch_result, spec)
                values[spec.id] = val
            except Exception as exc:
                log.warning(f"ExtractAgent({spec.id}): extraction failed: {exc}")
                values[spec.id] = None
        return values

    def _extract_one(self, result: FetchResult, spec: ExtractSpec) -> Any:
        if spec.type == "jsonpath":
            try:
                data = json.loads(result.body)
            except (json.JSONDecodeError, TypeError):
                log.warning(f"ExtractAgent({spec.id}): invalid JSON body for jsonpath")
                return None
            matches = [m.value for m in jsonpath_parse(spec.path).find(data)]
            return self._apply_transform(matches[0] if matches else None, spec.transform)

        elif spec.type == "jsonpath_from_html":
            # Find <script type="application/ld+json"> tags, parse JSON, apply JSONPath.
            # Type may include a charset parameter (application/ld+json; charset=utf-8);
            # exact CSS [type="..."] misses those — match by media-type prefix.
            tree = HTMLParser(result.body)
            scripts = []
            for node in tree.css("script[type]"):
                script_type = (node.attributes.get("type") or "").strip().lower()
                if script_type == "application/ld+json" or script_type.startswith(
                    "application/ld+json;"
                ):
                    scripts.append(node)
            for script in scripts:
                try:
                    data = json.loads(script.text())
                    # List-root and schema.org @graph are multi-entity payloads;
                    # try the wrapper first, then each entity (same convenience as list-root).
                    if isinstance(data, list):
                        candidates = data
                    elif isinstance(data, dict) and isinstance(data.get("@graph"), list):
                        candidates = [data] + data["@graph"]
                    else:
                        candidates = [data]
                    for item in candidates:
                        matches = [m.value for m in jsonpath_parse(spec.path).find(item)]
                        if matches:
                            return self._apply_transform(matches[0], spec.transform)
                except json.JSONDecodeError:
                    continue
            return None

        elif spec.type == "css":
            tree = HTMLParser(result.body)
            nodes = tree.css(spec.selector or "")
            if not nodes:
                return None
            node = nodes[0]
            if spec.transform and spec.transform.startswith("attr:"):
                attr_name = spec.transform.split(":", 1)[1]
                return node.attributes.get(attr_name)
            text = node.text(strip=True)
            return self._apply_transform(text, spec.transform)

        elif spec.type == "regex":
            if not spec.pattern:  # P2 FIX: missing pattern → None, not ""
                return None
            # H4 FIX: Pre-compile regex to catch invalid patterns; cap input length
            try:
                regex = re.compile(spec.pattern)
            except re.error as exc:
                log.warning(f"ExtractAgent({spec.id}): invalid regex pattern '{spec.pattern}': {exc}")
                return None
            match = regex.search(result.body[:REGEX_INPUT_CAP])  # cap input to prevent ReDoS
            if match:
                return match.group(spec.group) if spec.group else match.group(0)
            return None

        elif spec.type == "header":
            if spec.name == "status_code":
                return result.status_code
            if not spec.name:
                return ""
            # HTTP headers are case-insensitive. httpx lowercases keys in
            # dict(resp.headers); configs typically use Content-Type / ETag.
            wanted = spec.name.lower()
            for key, val in result.headers.items():
                if str(key).lower() == wanted:
                    return val
            return ""

        return None

    def _apply_transform(self, value: Any, transform: Optional[str]) -> Any:
        if value is None or not transform:
            return value
        if transform == "text":
            return value
        if transform.endswith("|upper"):
            return str(value).upper()
        if transform.endswith("|lower"):
            return str(value).lower()
        if transform.startswith("attr:"):
            return value  # handled in css branch
        return value


# ═══════════════════════════════════════════════════════════════
#  StateManager — JSON state with atomic writes, acknowledged, anti-bounce
# ═══════════════════════════════════════════════════════════════

class StateManager:
    # Called by: run_engine steps 3, 9, 10. Calls: json, pathlib. Returns: state dict.
    # State: {field: value, acknowledged: {cond_id: {at, value}}, first_seen, last_fired, last_checked}
    def __init__(self, state_path: Path, initial: Optional[dict[str, Any]] = None):
        self.path = state_path
        self.initial = initial or {}
        self.state: dict[str, Any] = {}

    def _backup_corrupt_state(self) -> None:
        """Best-effort rename of an unusable state file for forensics."""
        try:
            backup = self.path.with_suffix(
                f".corrupt.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
            )
            self.path.rename(backup)
            log.warning(f"StateManager: corrupt state backed up to {backup}")
        except OSError:
            pass  # Can't rename — proceed with reinit

    def _normalize_internal_maps(self) -> None:
        """Ensure acknowledged/first_seen/last_fired are dicts (missing or wrong type)."""
        for key in ("acknowledged", "first_seen", "last_fired"):
            if not isinstance(self.state.get(key), dict):
                self.state[key] = {}

    @staticmethod
    def _parse_state_timestamp(ts: Any) -> Optional[datetime]:
        """Parse a state timestamp; invalid/non-string values degrade to None."""
        if not isinstance(ts, str) or not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > datetime.now(timezone.utc) + CLOCK_SKEW_TOLERANCE:
            log.warning(f"StateManager: future state timestamp {ts!r}, treating as absent")
            return None
        return dt

    def load(self) -> dict[str, Any]:
        """Load state from JSON file, or initialize with defaults."""
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                # C2 FIX: Preserve corrupt file for forensics before reinitializing
                log.error(f"StateManager: corrupt state file {self.path}, reinitializing")
                self._backup_corrupt_state()
                self.state = dict(self.initial)
            else:
                # R7: valid JSON that is not an object (list/scalar/null) must not
                # crash on setdefault — same reinit path as decode failures.
                if not isinstance(raw, dict):
                    log.error(
                        f"StateManager: non-object state file {self.path} "
                        f"(got {type(raw).__name__}), reinitializing"
                    )
                    self._backup_corrupt_state()
                    self.state = dict(self.initial)
                else:
                    self.state = raw
        else:
            self.state = dict(self.initial)
        # Missing keys OR wrong types (string/list/null) — coerce to empty maps
        # so acknowledge/is_acknowledged/set_first_seen cannot TypeError mid-poll.
        self._normalize_internal_maps()
        return self.state

    def save(self):
        """Atomic write: tmp → rename."""
        try:
            self.state["last_checked"] = datetime.now(timezone.utc).isoformat()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state, indent=2) + "\n")
            tmp.replace(self.path)
            log.info(f"StateManager: saved state to {self.path}")
            return True
        except Exception as exc:
            log.error(f"StateManager: failed to save state to {self.path}: {exc}")
            return False

    def is_acknowledged(self, condition_id: str, current_value: Any) -> bool:
        """Check if condition is acknowledged with the SAME value (anti-bounce)."""
        acks = self.state.get("acknowledged", {})
        if not isinstance(acks, dict):
            return False
        ack = acks.get(condition_id)
        # R7: malformed entries (string/list legacy or corrupt) are not acknowledgements
        if not isinstance(ack, dict):
            return False
        return ack.get("value") == current_value

    def acknowledge(self, condition_id: str, value: Any):
        """Mark condition as acknowledged with its current value."""
        if not isinstance(self.state.get("acknowledged"), dict):
            self.state["acknowledged"] = {}
        self.state["acknowledged"][condition_id] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "value": value,
        }

    def remove_acknowledged(self, condition_id: str):
        """Remove a stale acknowledged entry (condition stopped matching)."""
        acks = self.state.get("acknowledged")
        if isinstance(acks, dict):
            acks.pop(condition_id, None)

    def set_last_fired(self, condition_id: str):
        """Update last_fired timestamp for refire_after tracking."""
        if not isinstance(self.state.get("last_fired"), dict):
            self.state["last_fired"] = {}
        self.state["last_fired"][condition_id] = datetime.now(timezone.utc).isoformat()

    def get_last_fired(self, condition_id: str) -> Optional[datetime]:
        fired = self.state.get("last_fired")
        if not isinstance(fired, dict):
            return None
        return self._parse_state_timestamp(fired.get(condition_id))

    def set_first_seen(self, condition_id: str):
        """Record first-seen timestamp for duration gate."""
        if not isinstance(self.state.get("first_seen"), dict):
            self.state["first_seen"] = {}
        self.state["first_seen"][condition_id] = datetime.now(timezone.utc).isoformat()

    def get_first_seen(self, condition_id: str) -> Optional[datetime]:
        seen = self.state.get("first_seen")
        if not isinstance(seen, dict):
            return None
        return self._parse_state_timestamp(seen.get(condition_id))

    def clear_first_seen(self, condition_id: str):
        """Reset duration gate (condition stopped matching)."""
        seen = self.state.get("first_seen")
        if isinstance(seen, dict):
            seen.pop(condition_id, None)

    def update_extracted(self, extracted: dict[str, Any]):
        """Update state with newly extracted values (but don't save yet)."""
        for k, v in extracted.items():
            self.state[k] = v


# ═══════════════════════════════════════════════════════════════
#  TriggerAgent — structured YAML condition evaluation (no eval())
# ═══════════════════════════════════════════════════════════════

class ConditionResult:
    def __init__(self, matched: bool, reason: str = "", submatches: Optional[list["ConditionResult"]] = None,
                 indeterminate: bool = False):
        self.matched = matched
        self.reason = reason
        self.submatches = submatches or []
        self.indeterminate = indeterminate


class TriggerAgent:
    # Called by: run_engine step 7. Calls: _get_value, _get_baseline (→ gws_get_event). Returns: ConditionResult.
    def __init__(self, prev_state: dict, current_values: dict, calendar_events: dict[str, dict]):
        """prev_state: state from last poll. current_values: freshly extracted values."""
        self.prev_state = prev_state
        self.current_values = current_values
        self.calendar_events = calendar_events

    def evaluate(self, cond: Condition) -> ConditionResult:
        """Evaluate a single condition (recursively for and/or/not)."""
        # Args: Condition. Returns: ConditionResult(matched, reason, submatches)
        # Apply unless before either a composite or leaf primary condition.
        if cond.unless:
            unless_cond = Condition(**cond.unless)
            unless_result = self.evaluate(unless_cond)
            if unless_result.matched:
                return ConditionResult(False, f"suppressed by unless: {unless_result.reason}")
            if unless_result.indeterminate:
                return ConditionResult(False, f"unless indeterminate: {unless_result.reason}", indeterminate=True)

        # Boolean combinators
        if cond.and_:
            # Evaluate ALL children. A definite-false (matched=False, not indeterminate)
            # must win over indeterminate so a duration gate cannot fire when a later
            # conjunct is already definitely False (mirrors not_ branch priority).
            subresults = []
            for sub in cond.and_:
                sub_cond = Condition(**sub)
                subresults.append(self.evaluate(sub_cond))
            has_definite_false = any(
                not r.matched and not r.indeterminate for r in subresults
            )
            has_indeterminate = any(r.indeterminate for r in subresults)
            if has_definite_false:
                first_false = next(
                    r for r in subresults if not r.matched and not r.indeterminate
                )
                return ConditionResult(False, f"AND: {first_false.reason}", subresults)
            if has_indeterminate:
                first_ind = next(r for r in subresults if r.indeterminate)
                return ConditionResult(
                    False, f"AND: {first_ind.reason}", subresults, indeterminate=True,
                )
            return ConditionResult(True, "AND: all matched", subresults)

        if cond.or_:
            subresults = []
            has_indeterminate = False
            for sub in cond.or_:
                sub_cond = Condition(**sub)
                sub_res = self.evaluate(sub_cond)
                subresults.append(sub_res)
                if sub_res.matched:
                    # Cite the matching (deciding) sub-result, not always index 0.
                    return ConditionResult(True, f"OR: {sub_res.reason}", subresults)
                has_indeterminate = has_indeterminate or sub_res.indeterminate
            if has_indeterminate:
                first_ind = next(r for r in subresults if r.indeterminate)
                return ConditionResult(
                    False, f"OR: {first_ind.reason}", subresults, indeterminate=True,
                )
            return ConditionResult(False, "OR: none matched", subresults)

        if cond.not_ is not None:
            if not cond.not_:  # P1 FIX: empty not: list → no-op, don't crash
                return ConditionResult(True, "NOT: empty list (no-op)")
            # P1-C FIX: Handle not: with multiple items as NOT(AND([...]))
            sub_results = []
            for raw_sub in cond.not_:
                sub_cond = Condition(**raw_sub)
                sub_results.append(self.evaluate(sub_cond))
            has_definite_false = any(not r.matched and not r.indeterminate for r in sub_results)
            has_indeterminate = any(r.indeterminate for r in sub_results)
            # P2: cite the deciding sub-result (definite-false / indeterminate), not always [0].
            if has_definite_false:
                first_false = next(
                    r for r in sub_results if not r.matched and not r.indeterminate
                )
                return ConditionResult(True, f"NOT: {first_false.reason}", sub_results)
            if has_indeterminate:
                first_ind = next(r for r in sub_results if r.indeterminate)
                return ConditionResult(
                    False, f"NOT: {first_ind.reason}", sub_results, indeterminate=True,
                )
            return ConditionResult(False, f"NOT: {sub_results[0].reason}", sub_results)

        # Compound prev→new delta: any/all/empty/nonempty/became_* plus optional numeric range.
        if cond.delta is not None:
            return self._eval_delta_compound(cond)

        # Leaf condition: field + op + value (or fieldless compound ops)
        if not cond.op:
            return ConditionResult(False, "missing field or op")
        if cond.op in Condition.FIELDLESS_OPS:
            return self._eval_field_list_op(cond)
        if not cond.field:
            return ConditionResult(False, "missing field or op")

        actual = self._get_value(cond.field)
        expected = cond.value
        if actual is VALUE_UNAVAILABLE:
            return ConditionResult(
                False, f"{cond.field}: source unavailable", indeterminate=True,
            )

        # Evaluate the operator
        op = cond.op
        if op == "changed":
            baseline_val = self._get_baseline(cond)
            # F4.3 FIX: A failed calendar lookup must not be interpreted as a changed value.
            if baseline_val is BASELINE_UNAVAILABLE:
                reason = "changed: baseline unavailable (calendar lookup failed)"
                log.warning(reason)
                return ConditionResult(False, reason, indeterminate=True)
            matched = actual != baseline_val
            reason = f"{cond.field} changed: {baseline_val} → {actual}" if matched else f"{cond.field} unchanged ({actual})"
            return ConditionResult(matched, reason)

        elif op == "eq":
            matched = str(actual) == str(expected) if actual is not None else False
            return ConditionResult(matched, f"{cond.field} == {expected}" if matched else f"{cond.field} != {expected} (got {actual})")

        elif op == "ne":
            matched = str(actual) != str(expected) if actual is not None else True
            return ConditionResult(matched, f"{cond.field} != {expected}" if matched else f"{cond.field} == {expected}")

        elif op == "contains":
            if actual is None or expected is None:
                return ConditionResult(False, f"{cond.field} contains: None operand")
            matched = str(expected) in str(actual)
            return ConditionResult(matched, f"{cond.field} contains '{expected}'" if matched else f"{cond.field} does not contain '{expected}'")

        elif op in ("gt", "gte", "lt", "lte"):
            if actual is None or expected is None:
                return ConditionResult(False, f"{cond.field} {op}: None operand")
            try:
                a = float(actual)
                b = float(expected)
            except (TypeError, ValueError):
                return ConditionResult(False, f"numeric comparison failed: {actual} vs {expected}")
            ops = {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}
            matched = ops[op]
            return ConditionResult(matched, f"{cond.field} {op} {expected}: {matched}")

        elif op == "time_diff_gt":
            if actual is None or expected is None:
                return ConditionResult(False, "time_diff_gt: None operand")
            diff_min = self._time_diff_minutes(actual, cond.compared_to or "")
            if diff_min is None:
                return ConditionResult(False, "time_diff_gt: could not compute")
            try:
                threshold = float(expected)
            except (TypeError, ValueError):
                log.warning(f"TriggerAgent: time_diff_gt field={cond.field!r} non-numeric value={expected!r}")
                return ConditionResult(False, f"time_diff_gt: non-numeric threshold {expected!r}")
            matched = abs(diff_min) > threshold
            return ConditionResult(matched, f"time_diff({cond.field}) > {expected}min: {diff_min}min")

        elif op == "time_diff_lt":
            if actual is None or expected is None:
                return ConditionResult(False, "time_diff_lt: None operand")
            diff_min = self._time_diff_minutes(actual, cond.compared_to or "")
            if diff_min is None:
                return ConditionResult(False, "time_diff_lt: could not compute")
            try:
                threshold = float(expected)
            except (TypeError, ValueError):
                log.warning(f"TriggerAgent: time_diff_lt field={cond.field!r} non-numeric value={expected!r}")
                return ConditionResult(False, f"time_diff_lt: non-numeric threshold {expected!r}")
            matched = abs(diff_min) < threshold
            return ConditionResult(matched, f"time_diff({cond.field}) < {expected}min: {diff_min}min")

        elif op == "time_shift_gt":
            if actual is None or expected is None:
                return ConditionResult(False, "time_shift_gt: None operand")
            diff_min = self._time_diff_minutes(actual, cond.compared_to or "")
            if diff_min is None:
                return ConditionResult(False, "time_shift_gt: could not compute")
            try:
                threshold = float(expected)
            except (TypeError, ValueError):
                log.warning(f"TriggerAgent: time_shift_gt field={cond.field!r} non-numeric value={expected!r}")
                return ConditionResult(False, f"time_shift_gt: non-numeric threshold {expected!r}")
            matched = diff_min > threshold
            return ConditionResult(matched, f"time_shift({cond.field}) > {expected}min: {diff_min}min")

        elif op == "time_shift_lt":
            if actual is None or expected is None:
                return ConditionResult(False, "time_shift_lt: None operand")
            diff_min = self._time_diff_minutes(actual, cond.compared_to or "")
            if diff_min is None:
                return ConditionResult(False, "time_shift_lt: could not compute")
            try:
                threshold = float(expected)
            except (TypeError, ValueError):
                log.warning(f"TriggerAgent: time_shift_lt field={cond.field!r} non-numeric value={expected!r}")
                return ConditionResult(False, f"time_shift_lt: non-numeric threshold {expected!r}")
            matched = diff_min < threshold
            return ConditionResult(matched, f"time_shift({cond.field}) < {expected}min: {diff_min}min")

        elif op == "exists":
            matched = actual is not None and (actual.strip() != "" if isinstance(actual, str) else True)
            return ConditionResult(matched, f"{cond.field} exists: {matched}")

        elif op == "matches":
            if not expected or not actual:
                return ConditionResult(False, f"{cond.field} matches: None operand")
            # H4 FIX: Pre-compile regex to catch invalid patterns; cap input length to mitigate ReDoS
            try:
                regex = re.compile(str(expected))
            except re.error as exc:
                log.warning(f"TriggerAgent: invalid matches regex '{expected}': {exc}")
                return ConditionResult(False, f"matches: invalid regex '{expected}'")
            input_str = str(actual)[:MATCHES_INPUT_CAP]  # cap input to prevent catastrophic backtracking
            matched = bool(regex.search(input_str))
            return ConditionResult(matched, f"{cond.field} matches '{expected}': {matched}")

        elif op == "empty":
            matched = _is_empty_value(actual)
            return ConditionResult(matched, f"{cond.field} empty: {matched}")

        elif op == "became_empty":
            previous = self._previous_value(cond.field)
            if previous is VALUE_UNAVAILABLE:
                return ConditionResult(False, f"{cond.field}: previous unavailable", indeterminate=True)
            matched = (not _is_empty_value(previous)) and _is_empty_value(actual)
            reason = (
                f"{cond.field} became empty: {previous} → {actual}"
                if matched else f"{cond.field} did not become empty ({previous} → {actual})"
            )
            return ConditionResult(matched, reason)

        elif op == "became_nonempty":
            previous = self._previous_value(cond.field)
            if previous is VALUE_UNAVAILABLE:
                return ConditionResult(False, f"{cond.field}: previous unavailable", indeterminate=True)
            matched = _is_empty_value(previous) and (not _is_empty_value(actual))
            reason = (
                f"{cond.field} became nonempty: {previous} → {actual}"
                if matched else f"{cond.field} did not become nonempty ({previous} → {actual})"
            )
            return ConditionResult(matched, reason)

        elif op == "between":
            number = _as_float(actual)
            lo = _as_float(cond.min_value)
            hi = _as_float(cond.max_value)
            if number is None or lo is None or hi is None:
                return ConditionResult(False, f"{cond.field} between: non-numeric operand")
            if lo > hi:
                lo, hi = hi, lo
            matched = lo <= number <= hi
            return ConditionResult(
                matched,
                f"{cond.field} between {lo} and {hi}: {number}" if matched
                else f"{cond.field} {number} not in [{lo}, {hi}]",
            )

        elif op in Condition.DELTA_OPS:
            return self._eval_numeric_delta(cond, actual)

        return ConditionResult(False, f"unknown op: {op}")

    def _previous_value(self, field: str) -> Any:
        """Previous-poll value for delta ops. Does not fall back to current."""
        if field in self.prev_state:
            return self.prev_state[field]
        return None

    def _field_changed(self, field: str) -> ConditionResult:
        actual = self._get_value(field)
        if actual is VALUE_UNAVAILABLE:
            return ConditionResult(False, f"{field}: source unavailable", indeterminate=True)
        previous = self._previous_value(field)
        matched = actual != previous
        reason = (
            f"{field} changed: {previous} → {actual}"
            if matched else f"{field} unchanged ({actual})"
        )
        return ConditionResult(matched, reason)

    def _eval_numeric_delta(self, cond: Condition, actual: Any) -> ConditionResult:
        previous = self._previous_value(cond.field or "")
        if previous is VALUE_UNAVAILABLE or actual is VALUE_UNAVAILABLE:
            return ConditionResult(False, f"{cond.field}: source unavailable", indeterminate=True)
        delta = _numeric_delta(previous, actual)
        if delta is None:
            return ConditionResult(False, f"{cond.field} delta: non-numeric {previous} → {actual}")
        op = cond.op
        if op == "delta_between":
            lo = _as_float(cond.min_value)
            hi = _as_float(cond.max_value)
            if lo is None or hi is None:
                return ConditionResult(False, f"{cond.field} delta_between: non-numeric bounds")
            if lo > hi:
                lo, hi = hi, lo
            matched = lo <= delta <= hi
            return ConditionResult(
                matched,
                f"{cond.field} delta {delta} in [{lo}, {hi}] ({previous} → {actual})"
                if matched else f"{cond.field} delta {delta} not in [{lo}, {hi}] ({previous} → {actual})",
            )
        threshold = _as_float(cond.value)
        if threshold is None:
            return ConditionResult(False, f"{cond.field} {op}: non-numeric threshold {cond.value!r}")
        ops = {
            "delta_gt": delta > threshold,
            "delta_gte": delta >= threshold,
            "delta_lt": delta < threshold,
            "delta_lte": delta <= threshold,
        }
        matched = ops[op]
        return ConditionResult(
            matched,
            f"{cond.field} {op} {threshold}: delta {delta} ({previous} → {actual})",
        )

    def _combine_any(self, results: list[ConditionResult], label: str) -> ConditionResult:
        if not results:
            return ConditionResult(False, f"{label}: empty field list")
        if any(r.matched for r in results):
            hit = next(r for r in results if r.matched)
            return ConditionResult(True, f"{label}: {hit.reason}", results)
        if any(r.indeterminate for r in results):
            hit = next(r for r in results if r.indeterminate)
            return ConditionResult(False, f"{label}: {hit.reason}", results, indeterminate=True)
        return ConditionResult(False, f"{label}: none matched", results)

    def _combine_all(self, results: list[ConditionResult], label: str) -> ConditionResult:
        if not results:
            return ConditionResult(False, f"{label}: empty field list")
        if any(not r.matched and not r.indeterminate for r in results):
            hit = next(r for r in results if not r.matched and not r.indeterminate)
            return ConditionResult(False, f"{label}: {hit.reason}", results)
        if any(r.indeterminate for r in results):
            hit = next(r for r in results if r.indeterminate)
            return ConditionResult(False, f"{label}: {hit.reason}", results, indeterminate=True)
        return ConditionResult(True, f"{label}: all matched", results)

    def _eval_field_predicate(self, field: str, kind: str) -> ConditionResult:
        actual = self._get_value(field)
        if actual is VALUE_UNAVAILABLE:
            return ConditionResult(False, f"{field}: source unavailable", indeterminate=True)
        previous = self._previous_value(field)
        if kind == "changed":
            return self._field_changed(field)
        if kind == "empty":
            matched = _is_empty_value(actual)
            return ConditionResult(matched, f"{field} empty: {matched}")
        if kind == "nonempty":
            matched = not _is_empty_value(actual)
            return ConditionResult(matched, f"{field} nonempty: {matched}")
        if kind == "became_empty":
            matched = (not _is_empty_value(previous)) and _is_empty_value(actual)
            return ConditionResult(
                matched,
                f"{field} became empty: {previous} → {actual}" if matched
                else f"{field} did not become empty ({previous} → {actual})",
            )
        if kind == "became_nonempty":
            matched = _is_empty_value(previous) and (not _is_empty_value(actual))
            return ConditionResult(
                matched,
                f"{field} became nonempty: {previous} → {actual}" if matched
                else f"{field} did not become nonempty ({previous} → {actual})",
            )
        return ConditionResult(False, f"unknown delta kind: {kind}")

    def _eval_field_list_op(self, cond: Condition) -> ConditionResult:
        kind_map = {
            "any_changed": ("changed", "any"),
            "all_changed": ("changed", "all"),
            "any_empty": ("empty", "any"),
            "all_empty": ("empty", "all"),
            "any_became_empty": ("became_empty", "any"),
            "all_became_empty": ("became_empty", "all"),
            "any_became_nonempty": ("became_nonempty", "any"),
            "all_became_nonempty": ("became_nonempty", "all"),
        }
        kind, combiner = kind_map[cond.op]
        results = [self._eval_field_predicate(name, kind) for name in cond.fields]
        label = cond.op
        if combiner == "any":
            return self._combine_any(results, label)
        return self._combine_all(results, label)

    def _eval_delta_compound(self, cond: Condition) -> ConditionResult:
        spec = cond.delta or {}
        clause_results: list[ConditionResult] = []
        for key, kind, combiner in (
            ("any", "changed", "any"),
            ("all", "changed", "all"),
            ("empty", "empty", "all"),
            ("nonempty", "nonempty", "all"),
            ("became_empty", "became_empty", "all"),
            ("became_nonempty", "became_nonempty", "all"),
        ):
            names = spec.get(key) or []
            if not names:
                continue
            results = [self._eval_field_predicate(name, kind) for name in names]
            if combiner == "any":
                clause_results.append(self._combine_any(results, f"delta.{key}"))
            else:
                clause_results.append(self._combine_all(results, f"delta.{key}"))
        range_spec = spec.get("range")
        if range_spec:
            field = range_spec.get("field")
            actual = self._get_value(field)
            previous = self._previous_value(field)
            if actual is VALUE_UNAVAILABLE:
                clause_results.append(
                    ConditionResult(False, f"{field}: source unavailable", indeterminate=True)
                )
            else:
                delta = _numeric_delta(previous, actual)
                lo = _as_float(range_spec.get("min"))
                hi = _as_float(range_spec.get("max"))
                if delta is None or lo is None or hi is None:
                    clause_results.append(
                        ConditionResult(False, f"delta.range {field}: non-numeric {previous} → {actual}")
                    )
                else:
                    if lo > hi:
                        lo, hi = hi, lo
                    matched = lo <= delta <= hi
                    clause_results.append(ConditionResult(
                        matched,
                        f"delta.range {field} {delta} in [{lo}, {hi}] ({previous} → {actual})"
                        if matched else
                        f"delta.range {field} {delta} not in [{lo}, {hi}] ({previous} → {actual})",
                    ))
        if not clause_results:
            return ConditionResult(False, "delta: no clauses")
        return self._combine_all(clause_results, "delta")

    def _get_value(self, field: str) -> Any:
        """Get a field value — from current extracted values, falling back to prev_state."""
        if field == "cal_title":
            # F4.2 FIX: Preserve the calendar_patch title placed in the evaluation context.
            if self.current_values.get("cal_title"):
                return self.current_values["cal_title"]
            for ev in self.calendar_events.values():
                if ev and "summary" in ev:
                    return ev["summary"]
            return self.prev_state.get("cal_title", "")
        # Current extracted values take priority
        if field in self.current_values:
            return self.current_values[field]
        if field in self.prev_state:
            return self.prev_state[field]
        return None

    def _get_baseline(self, cond: Condition) -> Any:
        """Get the baseline value for 'changed' op — from calendar or prev_state."""
        if cond.baseline:
            source = cond.baseline.get("source", "state")
            if source == "calendar":
                field = cond.baseline.get("field", "")
                # P0-4 FIX: Resolve the configured calendar event through the shared helper.
                ev = _resolve_baseline_event(cond, self.prev_state, self.calendar_events)
                # F4.3 FIX: Do not fall back to state when the calendar baseline is unavailable.
                if not ev:
                    return BASELINE_UNAVAILABLE
                parts = field.split(".")
                val = ev
                for part in parts:
                    if isinstance(val, dict) and part in val:
                        val = val[part]
                    else:
                        return BASELINE_UNAVAILABLE
                return val
            elif source == "state":
                return self.prev_state.get(cond.baseline.get("field", cond.field))
        # Default: compare against previous state value
        return self.prev_state.get(cond.field)

    def _time_diff_minutes(self, actual: Any, compared_to: str) -> Optional[float]:
        """Compute time difference in minutes between actual and compared_to value.

        ``compared_to`` may be:
        - ``state.<field>`` — previous-state lookup
        - a bare field name — current then previous state lookup
        - a literal datetime string
        Mixed-offset datetimes are normalized to UTC before differencing.
        """
        try:
            actual_dt = _parse_datetime_iso(actual)
            if compared_to and compared_to.startswith("state."):
                baseline = self.prev_state.get(compared_to[6:])
            elif compared_to and compared_to in self.current_values:
                baseline = self.current_values[compared_to]
            elif compared_to and compared_to in self.prev_state:
                baseline = self.prev_state[compared_to]
            else:
                baseline = compared_to
            if baseline is VALUE_UNAVAILABLE:
                return None
            baseline_dt = _parse_datetime_iso(baseline)
            if not actual_dt or not baseline_dt:
                return None
            if actual_dt.tzinfo is None:
                actual_dt = actual_dt.replace(tzinfo=timezone.utc)
            else:
                actual_dt = actual_dt.astimezone(timezone.utc)
            if baseline_dt.tzinfo is None:
                baseline_dt = baseline_dt.replace(tzinfo=timezone.utc)
            else:
                baseline_dt = baseline_dt.astimezone(timezone.utc)
            diff = (actual_dt - baseline_dt).total_seconds() / 60.0
            return diff
        except Exception as exc:
            log.warning(f"time_diff_minutes: {exc}")
            return None

# ═══════════════════════════════════════════════════════════════
#  GroupEvaluator — any/all over condition IDs
# ═══════════════════════════════════════════════════════════════

class GroupEvaluator:
    # Called by: run_engine step 8. Returns: (bool matched, list of matched cond_ids).
    def evaluate_group(self, group: Group, condition_results: dict[str, ConditionResult]) -> tuple[bool, list[str]]:
        """Returns (matched, list of matched condition IDs in this group)."""
        matched_ids = []
        if group.any:
            for cid in group.any:
                if cid in condition_results and condition_results[cid].matched:
                    matched_ids.append(cid)
            return (len(matched_ids) > 0, matched_ids)

        if group.all:
            all_matched = True
            for cid in group.all:
                if cid not in condition_results or not condition_results[cid].matched:
                    all_matched = False
                    break
                matched_ids.append(cid)
            return (all_matched, matched_ids)

        return (False, [])


# ═══════════════════════════════════════════════════════════════
#  ActionAgent — calendar patch with dynamic event IDs
# ═══════════════════════════════════════════════════════════════

class ActionAgent:
    # Called by: run_engine step 10. Calls: gws_patch_event, gws_delete_event. Returns: bool per action.
    # State: self.state (template context), self.calendar_events (for preserve_from_desc)
    def __init__(self, state: dict, dry_run: bool = False, calendar_events: Optional[dict] = None):
        self.state = state
        self.dry_run = dry_run
        self.calendar_events = calendar_events or {}
        self.results: list[str] = []

    def execute(self, action_name: str, action_def: dict) -> bool:
        """Execute an action. Returns True on success."""
        try:
            action_type = action_def.get("type", "calendar_patch")

            if action_type == "calendar_patch":
                return self._calendar_patch(action_name, action_def)
            elif action_type == "calendar_delete":
                return self._calendar_delete(action_name, action_def)
            else:
                log.warning(f"ActionAgent: unknown action type '{action_type}'")
                return False
        except Exception as exc:
            # Template/filter bugs must become action failures (retry + evidence),
            # not uncaught exceptions that skip health/evidence and abort the poll.
            log.error(f"ActionAgent({action_name}): unexpected error: {exc}")
            self.results.append(f"{action_name} ❌")
            return False

    def _resolve_event_id(self, event_id_spec: Any) -> str:
        """Resolve event ID — either a string or {from_state: key} dict."""
        if isinstance(event_id_spec, str):
            return event_id_spec
        if isinstance(event_id_spec, dict) and "from_state" in event_id_spec:
            key = event_id_spec["from_state"]
            val = self.state.get(key, "")
            if val is VALUE_UNAVAILABLE:
                return ""
            if not val and event_id_spec.get("required", False):
                log.error(f"ActionAgent: required state key '{key}' is missing")
            return val
        return str(event_id_spec) if event_id_spec else ""

    def _render_template(self, template: str, context: dict) -> str:
        """{{ var }} template rendering with filters: fmt_time, add_minutes, default, if_present."""
        return _render_template_vars(template, context, strict_unavailable=True)

    def _calendar_patch(self, action_name: str, action_def: dict) -> bool:
        """Patch a Google Calendar event."""
        event_id = self._resolve_event_id(action_def.get("event_id"))
        calendar_id = action_def.get("calendar_id", "primary")
        fields = action_def.get("fields", {})

        if not event_id:
            log.error(f"ActionAgent({action_name}): no event ID resolved")
            return False

        # Build context for template rendering
        context = dict(self.state)

        # ── Preserve fields from existing calendar event description ──
        # If the action has `preserve_from_desc` (list of regex patterns),
        # extract matching content from the existing description and inject
        # into context so templates can reference them.
        preserve_patterns = action_def.get("preserve_from_desc", [])
        existing_event = self.calendar_events.get(action_name)
        if preserve_patterns and existing_event:
            # P2/H4: cap description length before re.search (same cap as extract regex).
            existing_desc = (existing_event.get("description", "") or "")[:REGEX_INPUT_CAP]
            for p in preserve_patterns:
                if isinstance(p, dict):
                    name = p.get("as", "")
                    pattern = p.get("pattern", "")
                    if name and pattern:
                        # H2 FIX: Guard against invalid regex patterns crashing the engine
                        try:
                            m = re.search(pattern, existing_desc)
                            context[name] = m.group(0) if m else ""
                        except re.error as exc:
                            log.error(f"ActionAgent({action_name}): invalid preserve_from_desc regex '{pattern}': {exc}")
                            context[name] = ""

        try:
            # Compute derived values
            for var_name, template in action_def.get("computed", {}).items():
                context[var_name] = self._render_template(template, context)

            # Render field templates
            patch = {}
            for field_name, field_val in fields.items():
                if isinstance(field_val, str) and "{{" in field_val:
                    patch[field_name] = self._render_template(field_val, context)
                elif isinstance(field_val, dict):
                    # Nested dict (e.g., start: {dateTime: "...", timeZone: "..."})
                    rendered = {}
                    for k, v in field_val.items():
                        if isinstance(v, str) and "{{" in v:
                            rendered[k] = self._render_template(v, context)
                        else:
                            rendered[k] = v
                    patch[field_name] = rendered
                else:
                    patch[field_name] = field_val
        except UnavailableTemplateVar as exc:
            log.error(f"ActionAgent({action_name}): field references unavailable source var {exc}")
            self.results.append(f"{action_name} ❌")
            return False

        if self.dry_run:
            msg = f"DRY-RUN: would patch {event_id} with {json.dumps(patch, default=str)[:200]}"
            self.results.append(msg)
            return True

        success = gws_patch_event(event_id, patch, calendar_id)
        status = "✅" if success else "❌"
        self.results.append(f"{action_name} {status}")
        return success

    def _calendar_delete(self, action_name: str, action_def: dict) -> bool:
        """Delete a Google Calendar event."""
        event_id = self._resolve_event_id(action_def.get("event_id"))
        calendar_id = action_def.get("calendar_id", "primary")

        if not event_id:
            log.error(f"ActionAgent({action_name}): no event ID resolved")
            return False

        if self.dry_run:
            msg = f"DRY-RUN: would delete event {event_id} from {calendar_id}"
            self.results.append(msg)
            return True

        success = gws_delete_event(event_id, calendar_id)
        status = "✅" if success else "❌"
        self.results.append(f"{action_name} {status}")
        return success


# ═══════════════════════════════════════════════════════════════
#  LLMEscalationAgent — build evidence payload
# ═══════════════════════════════════════════════════════════════

class LLMEscalationAgent:
    # Called by: run_engine step 11. Calls: json, pathlib. Returns: list of evidence file paths.
    # State: prev_state (before poll), current_state (after merge), actions_taken, calendar_events
    def __init__(self, config: DetectConfig, prev_state: dict, current_state: dict,
                 actions_taken: list[str], calendar_events: Optional[dict] = None):
        self.config = config
        self.prev_state = prev_state      # State BEFORE this poll (the baseline)
        self.current_state = current_state  # State AFTER extracted values merged
        self.actions_taken = actions_taken
        self.calendar_events = calendar_events or {}

    def escalate(self, matched_conditions: list[tuple[str, ConditionResult, Condition]]) -> list[str]:
        """Build evidence payloads for each matched condition. Returns list of file paths."""
        escalation_files = []
        for cond_id, result, cond in matched_conditions:
            evidence = self._build_evidence(cond_id, result, cond)
            filepath = self._write_evidence(evidence, cond_id)
            if filepath:
                escalation_files.append(filepath)
        return escalation_files

    def _build_evidence(self, cond_id: str, result: ConditionResult, cond: Condition) -> dict:
        """Build a comprehensive evidence payload for LLM consumption.

        Includes:
        - The condition that fired (full definition)
        - Why it fired (match reason + recursive submatch tree)
        - Previous state (what the engine knew before this poll)
        - Current state (what was extracted this poll)
        - The specific field values that changed (previous → new)
        - Actions already taken
        - Calendar event state (what the calendar currently shows)
        - The LLM prompt
        """
        # Determine previous and new values for the condition's field(s)
        involved = _collect_leaf_fields(cond)
        field = cond.field
        if not field and len(involved) == 1:
            field = involved[0]
        prev_value = self.prev_state.get(field) if field else None
        new_value = self.current_state.get(field) if field else None

        # For baseline-based 'changed' conditions, get the baseline value
        baseline_value = None
        if cond.baseline:
            baseline_source = cond.baseline.get("source", "state")
            if baseline_source == "state":
                baseline_value = self.prev_state.get(cond.baseline.get("field", field))
            elif baseline_source == "calendar":
                # C1 FIX: Resolve the configured calendar event through the shared helper.
                ev = _resolve_baseline_event(cond, self.prev_state, self.calendar_events)
                if ev:
                    parts = cond.baseline.get("field", "").split(".")
                    val: Any = ev
                    for part in parts:
                        if isinstance(val, dict) and part in val:
                            val = val[part]
                        else:
                            val = None
                            break
                    baseline_value = val

        # Build recursive submatch tree for AND/OR/NOT conditions
        submatch_tree = self._extract_submatches(result)

        # Filter out internal state keys for the state snapshots
        internal_keys = {"acknowledged", "first_seen", "last_fired", "last_checked"}
        prev_snapshot = {k: v for k, v in self.prev_state.items() if k not in internal_keys}
        current_snapshot = {k: v for k, v in self.current_state.items() if k not in internal_keys}
        delta = _state_delta(prev_snapshot, current_snapshot)

        evidence = {
            "escalation_type": "condition_matched",
            "config_name": self.config.name,
            "condition_id": cond_id,
            "condition_definition": cond.model_dump(by_alias=True),
            "match_reason": result.reason,
            "submatches": submatch_tree,
            # The specific values that caused this condition to fire
            "field": field,
            "fields": involved,
            "previous_value": prev_value,
            "new_value": new_value,
            "baseline_value": baseline_value,
            "numeric_delta": _numeric_delta(prev_value, new_value) if not isinstance(prev_value, dict) else None,
            # Full state snapshots for LLM context
            "previous_state": prev_snapshot,
            "current_state": current_snapshot,
            "delta": delta,
            "changed_fields": list(delta["fields"].keys()),
            # Calendar context — start/end may be null or non-dict (malformed gws
            # payload); never chain .get on a present-but-wrong-type value
            # (``ev.get("start", {}).get(...)`` still crashes when start is None).
            "calendar_events": {
                name: _calendar_event_evidence_slice(ev)
                for name, ev in self.calendar_events.items()
            } if self.calendar_events else {},
            # What was already done about it
            "actions_taken": self.actions_taken,
            # The LLM prompt
            "prompt": self._render_prompt(cond_id, result, prev_value, new_value, delta),
        }
        return evidence

    def _extract_submatches(self, result: ConditionResult) -> list[dict]:
        """Recursively extract submatch tree from a ConditionResult."""
        tree = []
        for sub in result.submatches:
            node = {
                "matched": sub.matched,
                "reason": sub.reason,
            }
            if sub.submatches:
                node["submatches"] = self._extract_submatches(sub)
            tree.append(node)
        return tree

    def _render_prompt(self, cond_id: str, result: ConditionResult,
                       prev_value: Any = None, new_value: Any = None,
                       delta: Optional[dict] = None) -> str:
        """Render the LLM prompt template with condition-specific values."""
        template = self.config.llm_escalation.prompt if self.config.llm_escalation else ""
        delta = delta or {"fields": {}, "changed_fields": []}
        changed_fields = delta.get("changed_fields") or list((delta.get("fields") or {}).keys())
        if not template:
            # Build a default prompt with the rich context
            lines = [
                f"Change detected in '{self.config.name}':",
                f"  Condition: {cond_id}",
                f"  Reason: {result.reason}",
            ]
            if prev_value is not None or new_value is not None:
                lines.append(f"  Previous value: {prev_value}")
                lines.append(f"  New value: {new_value}")
            if changed_fields:
                lines.append("  Delta:")
                for name in changed_fields:
                    item = (delta.get("fields") or {}).get(name, {})
                    lines.append(
                        f"    {name}: {item.get('previous')} → {item.get('new')}"
                        + (f" (Δ {item['numeric_delta']})" if item.get("numeric_delta") is not None else "")
                    )
            if self.actions_taken:
                lines.append(f"  Actions already taken: {', '.join(self.actions_taken)}")
            lines.append("")
            lines.append("Evaluate whether this change requires additional action beyond what was already done.")
            return "\n".join(lines)

        context = dict(self.current_state)
        context.update({
            "config_name": self.config.name,
            "condition_id": cond_id,
            "match_reason": result.reason,
            "actions_taken": ", ".join(self.actions_taken),
            "previous_value": str(prev_value) if prev_value is not None else "N/A",
            "new_value": str(new_value) if new_value is not None else "N/A",
            "previous_state": json.dumps(self.prev_state, default=str, sort_keys=True),
            "current_state": json.dumps(self.current_state, default=str, sort_keys=True),
            "delta": json.dumps(delta, default=str, sort_keys=True),
            "changed_fields": ", ".join(changed_fields),
        })
        return _render_template_vars(template, context)

    def _write_evidence(self, evidence: dict, cond_id: str) -> Optional[str]:
        """Write evidence to a file. Returns the file path."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        # H5 FIX: Sanitize cond_id to prevent path traversal
        safe_cond_id = _safe_path_component(cond_id)
        filepath = _derived_path_within(
            ESCALATION_DIR,
            f"{_canonical_slug(self.config.name)}_{safe_cond_id}_{ts}.json",
            "condition evidence",
        )
        if filepath is None:
            return None
        try:
            ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
            tmp = filepath.with_suffix(".tmp")
            tmp.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
            tmp.replace(filepath)
            return str(filepath)
        except Exception as exc:
            log.error(f"LLMEscalationAgent: failed to write evidence: {exc}")
            return None


# ═══════════════════════════════════════════════════════════════
#  FetchFailureEscalation — LLM escalation when all retries fail
# ═══════════════════════════════════════════════════════════════

def _render_failure_prompt(
    template: str,
    *,
    url: str,
    source_id: str,
    config_name: str,
    attempts: int,
    error: str,
    error_type: str,
    status_code: int,
) -> str:
    """Render fixed placeholders in a custom fetch-failure prompt (URL already redacted)."""
    rendered = template
    for key, value in (
        ("{{ url }}", url),
        ("{{ source_id }}", source_id),
        ("{{ config_name }}", config_name),
        ("{{ attempts }}", str(attempts)),
        ("{{ error }}", error),
        ("{{ error_type }}", error_type),
        ("{{ status_code }}", str(status_code)),
    ):
        rendered = rendered.replace(key, value)
    return rendered


def write_fetch_failure_escalation(source: Source, result: FetchResult, config_name: str) -> Optional[str]:
    """Write a fetch-failure evidence file for LLM agent to pick up.

    Contains: redacted URL, error, error type, attempts, source config, config name,
    and a prompt for the LLM to reason about the failure.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    safe_url = _redact_url(source.url)

    # Build the default failure prompt (URL redacted — never emit credentials)
    default_prompt = (
        f"Source '{source.id}' for config '{config_name}' failed after {result.attempts} attempts.\n"
        f"URL: {safe_url}\n"
        f"Error type: {result.last_error_type}\n"
        f"Error: {result.error}\n\n"
        f"This may be a transient network/HTTP error. Evaluate:\n"
        f"1. Is the URL still valid?\n"
        f"2. Is this a known outage?\n"
        f"3. Should monitoring be paused?\n"
        f"4. Are there alternative sources for this data?"
    )

    if source.failure_prompt:
        prompt = _render_failure_prompt(
            source.failure_prompt,
            url=safe_url,
            source_id=source.id,
            config_name=config_name,
            attempts=result.attempts,
            error=result.error or "",
            error_type=result.last_error_type or "",
            status_code=result.status_code,
        )
    else:
        prompt = default_prompt

    evidence = {
        "escalation_type": "fetch_failure",
        "config_name": config_name,
        "source_id": source.id,
        "url": safe_url,
        "method": source.method,
        "error": result.error,
        "error_type": result.last_error_type,
        "attempts": result.attempts,
        "status_code": result.status_code,
        "source_config": {
            "required": source.required,
            "timeout": source.timeout,
            "retry": {"count": source.retry.count if source.retry else 0,
                      "backoff": source.retry.backoff if source.retry else 0},
            # H8 FIX: Redact secret-like header/param keys to prevent credential leakage
            "headers": _redact_secrets(source.headers),
            "params": _redact_secrets(source.params),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
    }

    filepath = _derived_path_within(
        ESCALATION_DIR,
        f"fetch_failure_{_canonical_slug(config_name)}_{_safe_path_component(source.id)}_{ts}.json",
        "fetch-failure evidence",
    )
    if filepath is None:
        return None
    try:
        ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
        tmp.replace(filepath)
        log.info(f"FetchFailureEscalation: wrote evidence to {filepath}")
        return str(filepath)
    except Exception as exc:
        log.error(f"FetchFailureEscalation: failed to write evidence: {exc}")
        return None


def write_state_commit_failure_evidence(
    config_name: str, actions_attempted: list[str], action_results: list[str]
) -> Optional[str]:
    """Write evidence when actions succeeded but their state acknowledgement did not persist."""
    written_at = datetime.now(timezone.utc).isoformat()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    filepath = _derived_path_within(
        ESCALATION_DIR,
        f"action_failure_{_canonical_slug(config_name)}_state_commit_{ts}.json",
        "state-commit failure evidence",
    )
    if filepath is None:
        return None
    evidence = {
        "escalation_type": "state_commit_failure",
        "config_name": config_name,
        "actions_attempted": actions_attempted,
        "action_results": action_results,
        "external_actions_succeeded": True,
        "state_committed": False,
        "timestamp": written_at,
        "prompt": (
            f"State commit failure in '{config_name}':\n"
            f"  Actions succeeded: {', '.join(action_results) or 'none'}\n"
            "  The external action may be retried because the new state was not saved.\n\n"
            "Investigate the state storage failure before allowing another poll."
        ),
    }
    try:
        ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
        tmp = filepath.with_suffix(".tmp")
        tmp.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
        tmp.replace(filepath)
        log.error(f"Engine: wrote state-commit failure evidence to {filepath}")
        return str(filepath)
    except OSError as exc:
        log.error(f"Engine: failed to write state-commit failure evidence {filepath}: {exc}")
        return None


# ═══════════════════════════════════════════════════════════════
#  Duration gate helper
# ═══════════════════════════════════════════════════════════════

def parse_duration(s: str) -> timedelta:
    """Parse duration strings like '5m', '30m', '1h', '2h30m'."""
    total = timedelta()
    matches = list(re.finditer(r"(\d+)([smhd])", s))
    for match in matches:
        n = int(match.group(1))
        unit = match.group(2)
        if unit == "s":
            total += timedelta(seconds=n)
        elif unit == "m":
            total += timedelta(minutes=n)
        elif unit == "h":
            total += timedelta(hours=n)
        elif unit == "d":
            total += timedelta(days=n)
    if not matches:
        log.warning(f"parse_duration({s!r}): no valid duration tokens, returning 0")
    return total


def _is_explicit_zero_duration(value: str) -> bool:
    """Return whether value is an intentional all-zero duration such as ``0s``."""
    return bool(re.fullmatch(r"(?:0+[smhd])+", value.strip()))


def _is_valid_duration(value: str) -> bool:
    """Return whether a duration is entirely made of supported duration tokens."""
    return bool(re.fullmatch(r"(?:\d+[smhd])+", value.strip()))


def _escalation_backoff_path(config_name: str) -> Optional[Path]:
    """Return the per-config side file without matching the watchdog health glob."""
    return _derived_path_within(
        HEALTH_DIR,
        f"{_canonical_slug(config_name)}-escalation-backoff.json",
        "escalation backoff",
    )


def _escalation_backoff_allows(config_name: str, escalation_type: str, backoff: str) -> bool:
    """Check whether this escalation type may emit evidence on this poll."""
    if not _is_valid_duration(backoff):
        return True
    duration = parse_duration(backoff)
    if duration == timedelta():
        return True

    path = _escalation_backoff_path(config_name)
    if path is None:
        return True
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Engine: could not read escalation backoff {path}: {exc}; allowing escalation")
        return True
    # R9: valid JSON that is not an object (array/null/scalar) must fail-open — .get would crash.
    if not isinstance(data, dict):
        log.warning(
            f"Engine: escalation backoff {path} is not an object ({type(data).__name__}); "
            "allowing escalation"
        )
        return True

    last_written = data.get(escalation_type)
    if not last_written:
        return True
    try:
        last_written_at = datetime.fromisoformat(last_written.replace("Z", "+00:00"))
        if last_written_at.tzinfo is None:
            last_written_at = last_written_at.replace(tzinfo=timezone.utc)
    except (AttributeError, ValueError):
        log.warning(f"Engine: invalid escalation backoff timestamp for {escalation_type}; allowing escalation")
        return True
    if last_written_at > datetime.now(timezone.utc) + CLOCK_SKEW_TOLERANCE:
        log.warning(
            f"Engine: future escalation backoff timestamp for {escalation_type}; allowing escalation"
        )
        return True
    return datetime.now(timezone.utc) - last_written_at >= duration


def _record_escalation_backoff(config_name: str, escalation_type: str, written_at: str) -> None:
    """Atomically record a successfully written escalation evidence timestamp."""
    path = _escalation_backoff_path(config_name)
    if path is None:
        return
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(f"Engine: could not read escalation backoff {path}: {exc}; resetting it")
        data = {}
    # R9: non-object JSON would TypeError on data[type]= — reset rather than crash the poll.
    if not isinstance(data, dict):
        log.warning(
            f"Engine: escalation backoff {path} is not an object ({type(data).__name__}); resetting it"
        )
        data = {}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data[escalation_type] = written_at
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        tmp.replace(path)
    except OSError as exc:
        log.error(f"Engine: failed to save escalation backoff {path}: {exc}")


def _save_state(sm: StateManager, config_name: str, context: str) -> bool:
    """Save state without allowing storage failures to escape a poll."""
    try:
        saved = sm.save()
    except Exception as exc:
        log.error(f"Engine({config_name}): state save failed ({context}): {exc}")
        return False
    if not saved:
        log.error(f"Engine({config_name}): state save failed ({context})")
    return bool(saved)


# ═══════════════════════════════════════════════════════════════
#  Main engine
# ═══════════════════════════════════════════════════════════════

def load_config(config_path: str) -> DetectConfig:
    """Load and validate a YAML config file. Expands `transitions:` shortcut.

    Raises ValueError (in addition to pydantic ValidationError / OSError) for
    unrecoverable structural problems so run_engine can exit 1 without an
    uncaught crash — notably RecursionError from deeply nested YAML and
    malformed ``transitions:`` entries.
    """
    path = Path(config_path)
    with open(path, encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except RecursionError as exc:
            # PyYAML raises RecursionError (not YAMLError) on pathological nesting.
            raise ValueError(
                f"config YAML nesting exceeds parser limits: {config_path}"
            ) from exc
    if raw is None:
        log.warning(f"load_config({config_path}): empty YAML, using defaults")
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(
            f"config root must be a mapping, got {type(raw).__name__}"
        )
    # Expand transitions: shortcut into conditions + groups + actions
    raw = _expand_transitions(raw)
    return DetectConfig(**raw)


def _expand_transitions(raw: dict) -> dict:
    """Expand `transitions:` section into `conditions:` + `groups:` + wire actions.
    
    This is a config-layer shortcut — no engine changes. A transition like:
    
      transitions:
        - field: dep_time
          on_change: [patch_flight, patch_uber]
        - field: status
          on_change: [patch_flight]
          when: {op: eq, value: "Delayed"}
    
    Compiles to:
      conditions:
        - id: transition_dep_time
          field: dep_time
          op: changed
          baseline: {source: state, field: dep_time}
        - id: transition_status
          and:
            - field: status
              op: changed
              baseline: {source: state, field: status}
            - field: status
              op: eq
              value: "Delayed"
      groups:
        - name: transition_dep_time_group
          any: [transition_dep_time]
          actions: [patch_flight, patch_uber]
        - name: transition_status_group
          all: [transition_status]
          actions: [patch_flight]
    """
    transitions = raw.pop("transitions", None)
    if not transitions:
        return raw
    if not isinstance(transitions, list):
        raise ValueError(
            f"transitions: must be a list, got {type(transitions).__name__}"
        )

    conditions = raw.get("conditions", [])
    groups = raw.get("groups", [])
    if conditions is None:
        conditions = []
    if groups is None:
        groups = []
    if not isinstance(conditions, list) or not isinstance(groups, list):
        raise ValueError("conditions: and groups: must be lists when using transitions:")

    for idx, t in enumerate(transitions):
        if not isinstance(t, dict):
            raise ValueError(
                f"transitions[{idx}]: must be a mapping, got {type(t).__name__}"
            )
        field = t.get("field", "")
        on_change = t.get("on_change", [])
        when = t.get("when")
        unless = t.get("unless")
        refire_after = t.get("refire_after")
        for_ = t.get("for")
        if when is not None and not isinstance(when, dict):
            raise ValueError(
                f"transitions[{idx}].when must be a mapping, got {type(when).__name__}"
            )
        if unless is not None and not isinstance(unless, dict):
            raise ValueError(
                f"transitions[{idx}].unless must be a mapping, got {type(unless).__name__}"
            )

        cond_id = f"transition_{field}"

        if when:
            # Build AND: [changed, when_clause]
            # Inject field into when if missing (shorthand: {op: eq, value: X} → {field: field, op: eq, value: X})
            when_with_field = dict(when)
            if "field" not in when_with_field:
                when_with_field["field"] = field
            cond = {
                "id": cond_id,
                "and": [
                    {"field": field, "op": "changed", "baseline": {"source": "state", "field": field}},
                    when_with_field,
                ],
            }
        else:
            cond = {
                "id": cond_id,
                "field": field,
                "op": "changed",
                "baseline": {"source": "state", "field": field},
            }

        if unless:
            cond["unless"] = unless
        if refire_after:
            cond["refire_after"] = refire_after
        if for_:
            cond["for"] = for_

        conditions.append(cond)

        group_name = f"{cond_id}_group"
        group = {
            "name": group_name,
            "any" if not when else "all": [cond_id],
            "actions": on_change,
        }
        groups.append(group)

    raw["conditions"] = conditions
    raw["groups"] = groups
    log.info(f"_expand_transitions: expanded {len(transitions)} transitions into {len(transitions)} conditions + {len(transitions)} groups")
    return raw


_TIME_OPS = frozenset({"time_diff_gt", "time_diff_lt", "time_shift_gt", "time_shift_lt"})


def _validate_time_op_thresholds(cond: Condition, errors: list[str], path: str = "") -> None:
    """Reject non-numeric thresholds on time ops at config validation (no runtime crash)."""
    label = cond.id or path or "(anonymous)"
    if cond.op in _TIME_OPS and cond.value is not None:
        try:
            float(cond.value)
        except (TypeError, ValueError):
            errors.append(
                f"condition '{label}' op '{cond.op}' has non-numeric value {cond.value!r}"
            )
    for idx, sub in enumerate(cond.and_ or []):
        try:
            _validate_time_op_thresholds(Condition(**sub), errors, f"{label}.and[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.or_ or []):
        try:
            _validate_time_op_thresholds(Condition(**sub), errors, f"{label}.or[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.not_ or []):
        try:
            _validate_time_op_thresholds(Condition(**sub), errors, f"{label}.not[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    if cond.unless:
        try:
            _validate_time_op_thresholds(Condition(**cond.unless), errors, f"{label}.unless")
        except (ValidationError, TypeError, ValueError):
            pass


def _validate_condition_durations(cond: Condition, errors: list[str], path: str = "") -> None:
    """Reject invalid ``for:`` / ``refire_after`` duration strings at config validation.

    ``parse_duration`` returns zero for garbage like ``bogus`` / ``5x``, which would
    silently defeat duration gates and refire throttles at runtime.
    """
    label = cond.id or path or "(anonymous)"
    if cond.for_ is not None and not _is_valid_duration(cond.for_):
        errors.append(
            f"condition '{label}' has invalid for duration {cond.for_!r}"
        )
    if cond.refire_after is not None and not _is_valid_duration(cond.refire_after):
        errors.append(
            f"condition '{label}' has invalid refire_after duration {cond.refire_after!r}"
        )
    for idx, sub in enumerate(cond.and_ or []):
        try:
            _validate_condition_durations(Condition(**sub), errors, f"{label}.and[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.or_ or []):
        try:
            _validate_condition_durations(Condition(**sub), errors, f"{label}.or[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.not_ or []):
        try:
            _validate_condition_durations(Condition(**sub), errors, f"{label}.not[{idx}]")
        except (ValidationError, TypeError, ValueError):
            pass
    if cond.unless:
        try:
            _validate_condition_durations(Condition(**cond.unless), errors, f"{label}.unless")
        except (ValidationError, TypeError, ValueError):
            pass


def _validate_condition_depth(
    cond: Condition, errors: list[str], depth: int = 0, path: str = ""
) -> None:
    """Reject and:/or:/not:/unless: trees deeper than MAX_CONDITION_DEPTH.

    Unbounded nesting can raise RecursionError in evaluate / leaf-field walks /
    duration validators and crash the poll. Fail at config validation instead.
    """
    label = cond.id or path or "(anonymous)"
    if depth > MAX_CONDITION_DEPTH:
        errors.append(
            f"condition '{label}' exceeds max nesting depth {MAX_CONDITION_DEPTH}"
        )
        return
    for idx, sub in enumerate(cond.and_ or []):
        try:
            _validate_condition_depth(
                Condition(**sub), errors, depth + 1, f"{label}.and[{idx}]"
            )
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.or_ or []):
        try:
            _validate_condition_depth(
                Condition(**sub), errors, depth + 1, f"{label}.or[{idx}]"
            )
        except (ValidationError, TypeError, ValueError):
            pass
    for idx, sub in enumerate(cond.not_ or []):
        try:
            _validate_condition_depth(
                Condition(**sub), errors, depth + 1, f"{label}.not[{idx}]"
            )
        except (ValidationError, TypeError, ValueError):
            pass
    if cond.unless:
        try:
            _validate_condition_depth(
                Condition(**cond.unless), errors, depth + 1, f"{label}.unless"
            )
        except (ValidationError, TypeError, ValueError):
            pass


def validate_config_cross_refs(config: DetectConfig) -> list[str]:
    """Validate cross-references between conditions, groups, and actions.
    Returns list of error messages (empty = valid)."""
    errors = []
    seen_source_ids = set()
    for source in config.sources:
        if source.id in seen_source_ids:
            errors.append(f"duplicate source id '{source.id}'")
        else:
            seen_source_ids.add(source.id)
    cond_ids = {c.id for c in config.conditions if c.id}
    # F4.5 FIX: Condition results are keyed by id, so duplicate non-empty ids are invalid.
    seen_cond_ids = set()
    for cond in config.conditions:
        if cond.id and cond.id in seen_cond_ids:
            errors.append(f"duplicate condition id '{cond.id}'")
        elif cond.id:
            seen_cond_ids.add(cond.id)
        _validate_condition_depth(cond, errors)
        _validate_time_op_thresholds(cond, errors)
        _validate_condition_durations(cond, errors)
    action_names = set(config.actions.keys())
    group_names = {g.name for g in config.groups}
    seen_group_names = set()
    for group in config.groups:
        if group.name in seen_group_names:
            errors.append(f"duplicate group name '{group.name}'")
        else:
            seen_group_names.add(group.name)

    # P2: extract ids are merged into a flat eval context — duplicates silently last-write-win.
    seen_extract_ids: set[str] = set()
    for source in config.sources:
        for spec in source.extract:
            if spec.id in seen_extract_ids:
                errors.append(
                    f"duplicate extract id '{spec.id}' across sources "
                    f"(extract ids must be unique in the shared eval context)"
                )
            else:
                seen_extract_ids.add(spec.id)

    # Check group condition references
    for group in config.groups:
        for cid in group.any + group.all:
            if cid not in cond_ids:
                errors.append(f"group '{group.name}' references unknown condition '{cid}'")
        for an in group.actions:
            if an not in action_names:
                errors.append(f"group '{group.name}' references unknown action '{an}'")

    # Check LLM escalation group references
    if config.llm_escalation:
        for gn in config.llm_escalation.trigger_groups:
            if gn not in group_names:
                errors.append(f"llm_escalation references unknown group '{gn}'")
        backoff = config.llm_escalation.escalation_backoff
        if (not _is_valid_duration(backoff)
                or (parse_duration(backoff) == timedelta() and not _is_explicit_zero_duration(backoff))):
            log.warning(
                f"Engine: llm_escalation escalation_backoff {backoff!r} is invalid; "
                "using unthrottled escalation"
            )

    # Check action type values
    valid_action_types = {"calendar_patch", "calendar_delete"}
    for an, ad in config.actions.items():
        at = ad.get("type", "calendar_patch")
        if at not in valid_action_types:
            errors.append(f"action '{an}' has invalid type '{at}' — must be one of {sorted(valid_action_types)}")

    return errors


def run_engine(config_path: str, dry_run: bool = False) -> int:
    """Main engine flow. Returns exit code (0 = ok, 1 = error).

    Steps: load → check enabled/expires → load state → fetch → extract
    → fetch calendar events → evaluate conditions → evaluate groups
    → (no match: save+exit) | (match: execute actions → acknowledge → escalate → save)
    """
    # ── Step 0: Guard empty inputs ──
    if not config_path:
        log.error("run_engine: empty config_path")
        return 1

    # ── Step 1: Load config ──
    try:
        config = load_config(config_path)
    except (ValidationError, yaml.YAMLError, FileNotFoundError, OSError, ValueError, RecursionError) as exc:
        # H3 FIX: Catch OSError (permission denied, I/O errors) not just FileNotFoundError
        # R10: ValueError covers deep-YAML / malformed transitions; RecursionError is a
        # belt-and-suspenders catch if any load path still overflows the stack.
        print(f"ERROR: config validation failed: {exc}", file=sys.stderr)
        return 1

    cross_ref_errors = validate_config_cross_refs(config)
    if cross_ref_errors:
        for error in cross_ref_errors:
            log.error(f"Engine: config cross-reference validation failed: {error}")
        return 1

    config_name_slug = _canonical_slug(config.name)
    health_path = _derived_path_within(
        HEALTH_DIR, f"{config_name_slug}-health.json", "health"
    )

    # ── Step 2: Check expires / enabled ──
    if not config.enabled:
        return 0  # silently skip
    if config.expires:
        try:
            expires_dt = datetime.fromisoformat(config.expires)
            # Handle naive datetime: attach UTC if no tzinfo
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_dt:
                # Config expired — clean up its health file so the watchdog
                # doesn't keep alerting on a stale orphaned file
                for suffix in ["-health.json", "_health.json"]:
                    health_file = _derived_path_within(
                        HEALTH_DIR, f"{config_name_slug}{suffix}", "expired health cleanup"
                    )
                    if not dry_run and health_file is not None and health_file.exists():
                        try:
                            health_file.unlink()
                            log.info(f"Engine: cleaned up expired health file {health_file.name}")
                        except OSError:
                            pass
                return 0  # expired — silently skip
        except (ValueError, TypeError):
            log.warning(f"Engine: invalid expires value '{config.expires}', ignoring")

    # ── Step 3: Load state (prev_state_snapshot saved for LLM evidence) ──
    config_dir = Path(config_path).parent
    # H5 FIX: Validate state.file stays inside config_dir to prevent path traversal
    state_path = (config_dir / config.state.file).resolve()
    # F4.4 FIX: Path-aware containment rejects sibling paths such as configs-evil/.
    if not state_path.is_relative_to(config_dir.resolve()):
        log.error(f"Engine: state.file must be inside config directory: {config.state.file}")
        return 1
    sm = StateManager(state_path, config.state.initial)
    sm.load()
    # Save a snapshot of the previous state for LLM escalation evidence
    prev_state_snapshot = dict(sm.state)

    # ── Step 4: Fetch sources + extract values ──
    # all_extracted State: {} (all failed) | {source_id: {field: value|None}}
    fetcher = FetchAgent()
    extractor = ExtractAgent()
    all_extracted = {}  # State: {} (no sources / all failed) | {source_id: {field: value}}
    unavailable_fields: set[str] = set()
    fetch_failure_escalations: list[str] = []
    escalation_backoff = (
        config.llm_escalation.escalation_backoff if config.llm_escalation else "1h"
    )

    if not config.sources:
        log.warning(f"Engine({config.name}): no sources configured")

    for source in config.sources:
        result = fetcher.fetch(source)
        if not result.ok:
            retry_cfg = source.retry or RetryConfig()

            # Write LLM escalation if configured
            if (not dry_run and retry_cfg.escalate_on_failure
                    and _escalation_backoff_allows(config.name, "fetch_failure", escalation_backoff)):
                esc_path = write_fetch_failure_escalation(source, result, config.name)
                if esc_path:
                    fetch_failure_escalations.append(esc_path)
                    _record_escalation_backoff(
                        config.name, "fetch_failure", datetime.now(timezone.utc).isoformat()
                    )

            if source.required:
                log.error(f"Engine: required source '{source.id}' failed after {result.attempts} "
                          f"attempts ({result.last_error_type}): {result.error}")
                if not dry_run and health_path is not None:
                    write_health(health_path, "error", config.name,
                                 f"source {source.id} failed ({result.last_error_type})")
                # Output escalation files even on hard failure
                for esc_path in fetch_failure_escalations:
                    print(f"LLM_ESCALATION: {esc_path}")
                return 1
            else:
                log.warning(f"Engine: optional source '{source.id}' failed after {result.attempts} "
                            f"attempts ({result.last_error_type}), continuing with partial data")
                unavailable_fields.update(spec.id for spec in source.extract)
                continue

        extracted = extractor.extract(result, source.extract)
        all_extracted[source.id] = extracted
        # NOTE: Do NOT update state with extracted values yet —
        # conditions must be evaluated against PREVIOUS state (anti-bounce)

    # ── Step 5: Fetch calendar events for comparison + preserve_from_desc ──
    # calendar_events State: {} (gws failure/no events) | {action_name: event_dict}
    # Prefetch must use each action's calendar_id (not always primary) so
    # preserve_from_desc / cal_title / suppression see the right event.
    calendar_events = {}  # State: {} (no events/gws failure) | {name: event_dict} (populated)
    for action_name, action_def in config.actions.items():
        event_id_spec = action_def.get("event_id")
        calendar_id = action_def.get("calendar_id", "primary")
        if isinstance(event_id_spec, str):
            ev = gws_get_event(event_id_spec, calendar_id)
            if ev:
                calendar_events[action_name] = ev
        elif isinstance(event_id_spec, dict) and "from_state" in event_id_spec:
            eid = sm.state.get(event_id_spec["from_state"], "")
            if eid:
                ev = gws_get_event(eid, calendar_id)
                if ev:
                    calendar_events[action_name] = ev

    # ── Step 6: Build cal_title for condition eval only (NOT written to state yet) ──
    # (don't write cal_title to state until actions succeed — blocker fix)
    # P1-B FIX: Use the calendar_patch action's event title, not arbitrary first event.
    # Prefer the first calendar_patch action (flight event), not calendar_delete actions.
    cal_title_from_events = ""
    for ev_name, ev in calendar_events.items():
        if ev and "summary" in ev:
            action_def = config.actions.get(ev_name, {})
            if action_def.get("type") == "calendar_patch":
                cal_title_from_events = ev["summary"]
                break  # use first calendar_patch event's title

    # 6b. Build evaluation context: previous state + extracted values + cal_title
    #     The TriggerAgent needs both the PREVIOUS state (for changed op baseline)
    #     and the CURRENT extracted values (for the actual value)
    eval_context = dict(sm.state)
    eval_context["cal_title"] = cal_title_from_events or sm.state.get("cal_title", "")
    for source_id, extracted in all_extracted.items():
        eval_context.update(extracted)
    successfully_extracted_fields = {
        field for extracted in all_extracted.values() for field in extracted
    }
    for field in unavailable_fields - successfully_extracted_fields:
        eval_context[field] = VALUE_UNAVAILABLE

    # Also pass cal_title to TriggerAgent via calendar_events so _get_value works
    # Inject cal_title into a synthetic event so TriggerAgent._get_value("cal_title") finds it
    if cal_title_from_events and not any(
        ev and ev.get("summary") == cal_title_from_events for ev in calendar_events.values()
    ):
        calendar_events["__cal_title__"] = {"summary": cal_title_from_events}

    # ── Step 6b: Seed mode — first poll saves state without executing actions ──
    # StateManager.save stamps last_checked, so it is the durable first-run marker.
    is_first_run = not sm.state.get("last_checked")
    if config.seed_mode and is_first_run:
        log.info(f"Engine({config.name}): seed_mode first run — saving state, no actions")
        for source_id, extracted in all_extracted.items():
            sm.update_extracted(extracted)
        if not dry_run:
            if not _save_state(sm, config.name, "seed mode"):
                if health_path is not None:
                    write_health(health_path, "error", config.name, "seed mode state save failed")
                # R9: still emit any fetch-failure evidence written earlier this poll.
                for esc_path in fetch_failure_escalations:
                    print(f"LLM_ESCALATION: {esc_path}")
                return 1
            if health_path is not None:
                write_health(health_path, "ok", config.name, "seed mode: initial state saved")
        # R9: seed exit previously dropped optional-source fetch-failure stdout pointers.
        for esc_path in fetch_failure_escalations:
            print(f"LLM_ESCALATION: {esc_path}")
        print(f"🌱 {config.name}: seed mode — initial state saved, actions deferred to next poll")
        return 0

    # ── Step 7: Evaluate conditions (changed/eq/ne/gt/lt/exists/matches/time_diff) ──
    # Duration gate, fire_once, refire_after applied here. Anti-bounce: prune stale acks.
    trigger = TriggerAgent(sm.state, eval_context, calendar_events)
    condition_results: dict[str, ConditionResult] = {}  # State: {} (no conditions) | {cond.id: result}
    # F4.1 FIX: Hold field baselines when a matched condition is temporarily suppressed.
    held_extracted_fields: set[str] = set()

    if not config.conditions:
        log.warning(f"Engine({config.name}): no conditions configured")

    for cond in config.conditions:
        result = trigger.evaluate(cond)
        condition_results[cond.id] = result

        # Duration gate
        if cond.for_ and result.matched:
            first_seen = sm.get_first_seen(cond.id)
            if not first_seen:
                sm.set_first_seen(cond.id)
                result.matched = False
                result.reason = f"duration gate: first seen, waiting {cond.for_}"
                held_extracted_fields.update(_fields_to_hold(cond))
            else:
                elapsed = datetime.now(timezone.utc) - first_seen
                duration = parse_duration(cond.for_)
                if elapsed < duration:
                    result.matched = False
                    result.reason = f"duration gate: {elapsed} < {cond.for_}"
                    held_extracted_fields.update(_fields_to_hold(cond))
        elif cond.for_ and result.indeterminate:
            # An unavailable baseline is unknown, not a definite recovery.
            pass
        elif cond.for_ and not result.matched:
            # Reset duration gate when condition stops matching
            sm.clear_first_seen(cond.id)

        # P0-1 FIX: Prune stale acknowledged entries BEFORE fire-once/refire check.
        # Only prune when the underlying condition evaluation is False (not when
        # suppressed by fire_once/refire_after). This prevents fire_once from
        # being defeated by the pruning deleting the ack entry.
        if not result.indeterminate:
            underlying_matched = result.matched
            if not underlying_matched:
                sm.remove_acknowledged(cond.id)

        # Fire-once check (anti-bounce)
        # P0-3 FIX: fire_once is independent of llm_escalation presence.
        # It applies whenever fire_once is True (default behavior).
        if result.matched:
            current_value = _condition_ack_value(cond, eval_context)
            if cond.refire_after:
                # refire_after takes precedence over fire_once
                last_fired = sm.get_last_fired(cond.id)
                if last_fired:
                    elapsed = datetime.now(timezone.utc) - last_fired
                    duration = parse_duration(cond.refire_after)
                    if elapsed < duration:
                        result.matched = False
                        result.reason = f"refire_after: {elapsed} < {cond.refire_after}"
                        held_extracted_fields.update(_fields_to_hold(cond))
            elif _fire_once_enabled(config):
                if sm.is_acknowledged(cond.id, current_value):
                    result.matched = False
                    result.reason = "fire_once: acknowledged with same value"

    # ── Step 8: Evaluate groups (any/all over condition IDs) ──
    # matched_groups State: [] (no match) | [(group, [cond_ids])]
    group_eval = GroupEvaluator()
    matched_groups = []  # State: [] (no match) | [(group, [cond_ids])]
    for group in config.groups:
        matched, matched_ids = group_eval.evaluate_group(group, condition_results)
        if matched:
            matched_groups.append((group, matched_ids))

    # ── Step 9: No match → update state + save + SILENT exit ──
    # R9: still emit LLM_ESCALATION for any fetch-failure evidence written this poll
    # (optional sources with escalate_on_failure) — silence applies to condition-match only.
    if not matched_groups:
        # Now safe to update state with extracted values (no actions to execute)
        for source_id, extracted in all_extracted.items():
            # F4.1 FIX: Preserve held fields while their matched condition is gated.
            sm.update_extracted({k: v for k, v in extracted.items() if k not in held_extracted_fields})
        # P0-2 FIX: dry-run does NOT save state or write health
        if not dry_run:
            if not _save_state(sm, config.name, "no changes path"):
                if health_path is not None:
                    write_health(health_path, "error", config.name, "no-change state save failed")
                for esc_path in fetch_failure_escalations:
                    print(f"LLM_ESCALATION: {esc_path}")
                return 1
            if health_path is not None:
                write_health(health_path, "ok", config.name, "no changes")
        for esc_path in fetch_failure_escalations:
            print(f"LLM_ESCALATION: {esc_path}")
        return 0

    # ── Step 10: Match → execute actions → acknowledge → save ──
    # all_actions_succeeded State: True (all ok) | False (at least one gws call failed)
    # P0-B FIX: Do NOT update sm.state with extracted values before actions succeed.
    # If actions fail, the baseline must remain unchanged so `changed` re-fires next poll.
    # Templates use eval_context (which has the new values) — they don't need sm.state updated yet.
    action_agent = ActionAgent(eval_context, dry_run, calendar_events=calendar_events)
    all_actions_succeeded = True

    # F4.5 FIX: Execute each action once, preserving first occurrence across matched groups.
    executed_actions = set()
    for group, matched_ids in matched_groups:
        for action_name in group.actions:
            if action_name in executed_actions:
                continue
            executed_actions.add(action_name)
            action_def = config.actions.get(action_name, {})
            success = action_agent.execute(action_name, action_def)
            if not success:
                all_actions_succeeded = False
                log.error(f"Engine: action '{action_name}' failed")

    # Acknowledge only if actions succeeded (anti-bounce)
    if all_actions_succeeded:
        # P0-B FIX: NOW safe to update state with extracted values (actions succeeded)
        for source_id, extracted in all_extracted.items():
            # F4.1 FIX: Preserve held fields even when another group fired successfully.
            sm.update_extracted({k: v for k, v in extracted.items() if k not in held_extracted_fields})
        # NOW safe to write cal_title to state (actions succeeded), unless it is gated.
        if cal_title_from_events and "cal_title" not in held_extracted_fields:
            sm.state["cal_title"] = cal_title_from_events
        for group, matched_ids in matched_groups:
            for cond_id in matched_ids:
                cond = next((c for c in config.conditions if c.id == cond_id), None)
                if cond:
                    current_value = _condition_ack_value(cond, eval_context)
                    sm.acknowledge(cond_id, current_value)
                    sm.set_last_fired(cond_id)
    else:
        log.error("Engine: one or more actions failed, not acknowledging — will retry next poll")
        # Action-failure evidence is independent of llm_escalation.trigger_groups
        # (symmetric with fetch escalate_on_failure). Still dry_run-gated + backoff-throttled.
        # escalation_backoff defaults to "1h" when llm_escalation is absent.
        if (not dry_run
                and _escalation_backoff_allows(config.name, "action_failure", escalation_backoff)):
            written_at = datetime.now(timezone.utc).isoformat()
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            esc_path = _derived_path_within(
                ESCALATION_DIR,
                f"action_failure_{_canonical_slug(config.name)}_{ts}.json",
                "action-failure evidence",
            )
            evidence = {
                "escalation_type": "action_failure",
                "config_name": config.name,
                "actions_attempted": [a for g, _ in matched_groups for a in g.actions],
                "action_results": action_agent.results,
                "timestamp": written_at,
                "prompt": (
                    f"Action failure in '{config.name}':\n"
                    f"  Actions attempted: {', '.join(a for g, _ in matched_groups for a in g.actions)}\n"
                    f"  Results: {', '.join(action_agent.results)}\n\n"
                    f"The engine will retry on the next poll. Evaluate:\n"
                    f"  1. Is this an auth/token issue?\n"
                    f"  2. Is the calendar event deleted or inaccessible?\n"
                    f"  3. Should monitoring be paused?"
                ),
            }
            if esc_path is not None:
                try:
                    ESCALATION_DIR.mkdir(parents=True, exist_ok=True)
                    tmp = esc_path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
                    tmp.replace(esc_path)
                    _record_escalation_backoff(config.name, "action_failure", written_at)
                    print(f"LLM_ESCALATION: {esc_path}")
                except OSError as exc:
                    log.error(f"Engine: failed to write action-failure evidence {esc_path}: {exc}")
        # R9: action-failure return previously dropped optional fetch-failure stdout pointers.
        for esc_path in fetch_failure_escalations:
            print(f"LLM_ESCALATION: {esc_path}")
        # P0-2 FIX: dry-run does NOT save state
        if not dry_run:
            if health_path is not None:
                write_health(health_path, "error", config.name, "action failed")
            # P0-B FIX: Do NOT save state on action failure — baseline must remain
            # unchanged so `changed` conditions re-fire on next poll (retry the action).
            # sm.save() is intentionally omitted here.
        return 1

    # ── Step 11: LLM escalation (write evidence files for agent cron) ──
    escalation_files = []
    # P0-2 FIX: dry-run does NOT write escalation files
    if not dry_run and config.llm_escalation and config.llm_escalation.trigger_groups:
        matched_conditions = []
        for group, matched_ids in matched_groups:
            if group.name in config.llm_escalation.trigger_groups:
                for cond_id in matched_ids:
                    cond = next((c for c in config.conditions if c.id == cond_id), None)
                    if cond:
                        matched_conditions.append((cond_id, condition_results[cond_id], cond))

        if matched_conditions:
            # Pass previous state (sm.state before extracted merge), current state (sm.state after merge),
            # actions taken, and calendar events for rich LLM context
            esc_agent = LLMEscalationAgent(
                config=config,
                prev_state=prev_state_snapshot,  # State before this poll
                current_state=sm.state,          # State after extracted values merged
                actions_taken=action_agent.results,
                calendar_events=calendar_events,
            )
            escalation_files = esc_agent.escalate(matched_conditions)

    # ── Step 12: Save state + write health + output ──
    # P0-2 FIX: dry-run does NOT save state
    if not dry_run:
        if not _save_state(sm, config.name, "after successful actions"):
            if health_path is not None:
                write_health(
                    health_path, "error", config.name,
                    "actions applied but state commit failed",
                )
            state_commit_evidence = write_state_commit_failure_evidence(
                config.name,
                [action for group, _ in matched_groups for action in group.actions],
                action_agent.results,
            )
            for fpath in fetch_failure_escalations + escalation_files:
                print(f"LLM_ESCALATION: {fpath}")
            if state_commit_evidence:
                print(f"LLM_ESCALATION: {state_commit_evidence}")
            return 1

    # Write health
    if not dry_run:
        detail = f"{sum(len(m) for _, m in matched_groups)} conditions matched"
        if health_path is not None:
            write_health(health_path, "ok", config.name, detail)
    else:
        detail = f"[DRY-RUN] {sum(len(m) for _, m in matched_groups)} conditions matched"

    # Output — fetch-failure escalations are output first, then condition escalations
    all_escalations = fetch_failure_escalations + escalation_files
    if all_escalations:
        for fpath in all_escalations:
            print(f"LLM_ESCALATION: {fpath}")
    elif dry_run:
        for msg in action_agent.results:
            print(msg)
    else:
        print(f"✅ {config.name}: {detail}, actions executed")

    return 0


# ═══════════════════════════════════════════════════════════════
#  CLI entry point
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Universal Change-Detection Guard Engine")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute actions, just print what would happen")
    parser.add_argument("--validate", action="store_true", help="Validate config and exit")
    args = parser.parse_args()

    # Setup logging
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except OSError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    if args.validate:
        try:
            config = load_config(args.config)
            # Cross-reference validation
            errors = validate_config_cross_refs(config)
            if errors:
                for e in errors:
                    print(f"❌ {e}", file=sys.stderr)
                return 1
            print(f"✅ Config valid: {config.name}")
            print(f"   Sources: {[s.id for s in config.sources]}")
            print(f"   Conditions: {len(config.conditions)}")
            print(f"   Groups: {[g.name for g in config.groups]}")
            print(f"   Actions: {list(config.actions.keys())}")
            return 0
        except Exception as exc:
            print(f"❌ Config invalid: {exc}", file=sys.stderr)
            return 1

    return run_engine(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
