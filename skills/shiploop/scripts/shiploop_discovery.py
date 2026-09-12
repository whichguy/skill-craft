"""Pure contracts for generic, Markdown-backed platform discovery.

The survey declares capability and planned routing; it never executes a probe,
uses credentials, grants authority, or publishes an artifact.  Protocol callers
decide when a new run must supply this record and bind it to frozen Markdown.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from shiploop_privacy import redact_text, sensitive_text


VERSION = 1

_MISSING = object()
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_PLATFORM_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
_STEP_ID = re.compile(r"^[SD][0-9]+$")
# ``interfaces`` contains only the selected, required route.  Optional readers
# and alternatives stay in survey prose instead of gaining an accidental gate.
_INTERFACE_STATUS = {"ready", "blocked"}
_IDENTITY_STATUS = {"ready", "blocked"}
_AUTHORITY_STATUS = {"observed", "blocked", "not-required"}
_BOOTSTRAP_MODE = {"none", "dag", "outer-before", "blocked"}
_VALIDATION_DECISION = {"required", "not-applicable", "blocked"}
_PROMOTION_MODE = {"none", "dag", "outer-loop", "blocked"}
_REVALIDATE_AT = {"cold-resume", "before-external-operation", "before-promotion"}


def _text(value: Any, label: str, gaps: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        gaps.append(f"{label} must be a nonempty string")
        return None
    text = value.strip()
    if _CONTROL.search(text):
        gaps.append(f"{label} must not contain control characters")
        return None
    return text


def _string_list(value: Any, label: str, gaps: list[str]) -> list[str]:
    if not isinstance(value, list):
        gaps.append(f"{label} must be a list")
        return []
    out: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{label}[{index}]", gaps)
        if text is not None:
            out.append(text)
    return out


def _mapping(value: Any, label: str, gaps: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        gaps.append(f"{label} must be an object")
        return None
    return value


def _contains_sensitive_text(value: Any) -> bool:
    """Screen nested discovery values without echoing an unsafe value.

    Discovery is JSON-shaped at the durable boundary, but this also keeps the
    pure validator safe when callers pass an in-memory mapping or list.
    """
    pending = [value]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            if sensitive_text(current):
                return True
        elif isinstance(current, Mapping):
            marker = id(current)
            if marker not in seen:
                seen.add(marker)
                pending.extend(current.keys())
                pending.extend(current.values())
        elif isinstance(current, list):
            marker = id(current)
            if marker not in seen:
                seen.add(marker)
                pending.extend(current)
    return False


def _step_id(value: Any, label: str, gaps: list[str]) -> str | None:
    if not isinstance(value, str) or not _STEP_ID.fullmatch(value):
        gaps.append(f"{label} must be a ShipLoop step ID")
        return None
    return value


def _platform_record(machine: Mapping[str, Any]) -> Any:
    return machine.get("platform_discovery", _MISSING)


def _platform_rows(machine: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    record = _platform_record(machine)
    if not isinstance(record, Mapping) or record.get("applicable") is not True:
        return []
    rows = record.get("platforms")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def step_routes(machine: Any, step_id: Any) -> list[dict[str, str]]:
    """Return declared platform routes for one DAG step without I/O or mutation."""
    if not isinstance(machine, Mapping) or not isinstance(step_id, str):
        return []
    if validate_machine(machine, required=False):
        return []
    routes: list[dict[str, str]] = []
    for platform in _platform_rows(machine):
        platform_id = platform.get("id")
        if not isinstance(platform_id, str):
            continue
        bootstrap = platform.get("bootstrap")
        if isinstance(bootstrap, Mapping) and bootstrap.get("mode") == "dag" and bootstrap.get("step_id") == step_id:
            routes.append({"platform": platform_id, "route": "bootstrap"})
        validation = platform.get("development_validation")
        if isinstance(validation, Mapping) and validation.get("decision") == "required" and validation.get("step_id") == step_id:
            routes.append({"platform": platform_id, "route": "development-validation"})
        promotion = platform.get("promotion")
        if isinstance(promotion, Mapping) and promotion.get("mode") == "dag" and promotion.get("step_id") == step_id:
            routes.append({"platform": platform_id, "route": "promotion"})
    return routes


def _blocked_reasons(platform: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    interfaces = platform.get("interfaces")
    if isinstance(interfaces, list) and any(
        isinstance(row, Mapping) and row.get("status") == "blocked" for row in interfaces
    ):
        reasons.append("interface")
    identity = platform.get("identity")
    if isinstance(identity, Mapping) and identity.get("status") == "blocked":
        reasons.append("identity")
    authority = platform.get("authority")
    if isinstance(authority, Mapping) and authority.get("status") == "blocked":
        reasons.append("authority")
    bootstrap = platform.get("bootstrap")
    if isinstance(bootstrap, Mapping) and bootstrap.get("mode") == "blocked":
        reasons.append("bootstrap")
    validation = platform.get("development_validation")
    if isinstance(validation, Mapping) and validation.get("decision") == "blocked":
        reasons.append("development validation")
    promotion = platform.get("promotion")
    if isinstance(promotion, Mapping) and promotion.get("mode") == "blocked":
        reasons.append("promotion")
    return reasons


def _validate_interfaces(value: Any, label: str, gaps: list[str]) -> None:
    if not isinstance(value, list) or not value:
        gaps.append(f"{label} must be a nonempty list")
        return
    for index, row in enumerate(value):
        item = _mapping(row, f"{label}[{index}]", gaps)
        if item is None:
            continue
        for key in ("kind", "name", "version", "reference"):
            _text(item.get(key), f"{label}[{index}].{key}", gaps)
        if item.get("status") not in _INTERFACE_STATUS:
            gaps.append(f"{label}[{index}].status must be ready or blocked")


def _validate_identity(value: Any, label: str, gaps: list[str]) -> None:
    item = _mapping(value, label, gaps)
    if item is None:
        return
    for key in ("expected_role", "observed_role", "safe_probe"):
        _text(item.get(key), f"{label}.{key}", gaps)
    if item.get("status") not in _IDENTITY_STATUS:
        gaps.append(f"{label}.status must be ready or blocked")


def _validate_authority(value: Any, label: str, gaps: list[str]) -> None:
    item = _mapping(value, label, gaps)
    if item is None:
        return
    required = item.get("required")
    if type(required) is not bool:
        gaps.append(f"{label}.required must be a boolean")
    _text(item.get("rationale"), f"{label}.rationale", gaps)
    status = item.get("status")
    if status not in _AUTHORITY_STATUS:
        gaps.append(f"{label}.status must be observed, blocked, or not-required")
    elif required is True and status == "not-required":
        gaps.append(f"{label}.status must be observed or blocked when required")
    elif required is False and status != "not-required":
        gaps.append(f"{label}.status must be not-required when required is false")


def _validate_bootstrap(value: Any, label: str, gaps: list[str]) -> None:
    item = _mapping(value, label, gaps)
    if item is None:
        return
    mode = item.get("mode")
    if mode not in _BOOTSTRAP_MODE:
        gaps.append(f"{label}.mode must be none, dag, outer-before, or blocked")
    step_id = item.get("step_id")
    if mode == "dag":
        _step_id(step_id, f"{label}.step_id", gaps)
    elif step_id is not None:
        gaps.append(f"{label}.step_id must be null unless mode is dag")
    prerequisites = _string_list(item.get("prerequisites"), f"{label}.prerequisites", gaps)
    if mode in ("dag", "outer-before") and not prerequisites:
        gaps.append(f"{label}.prerequisites must be nonempty when bootstrap is required")
    if mode == "none" and prerequisites:
        gaps.append(f"{label}.prerequisites must be empty when mode is none")
    _text(item.get("validation"), f"{label}.validation", gaps)


def _validate_development_validation(value: Any, label: str, gaps: list[str]) -> None:
    item = _mapping(value, label, gaps)
    if item is None:
        return
    decision = item.get("decision")
    if decision not in _VALIDATION_DECISION:
        gaps.append(f"{label}.decision must be required, not-applicable, or blocked")
    step_id = item.get("step_id")
    if decision == "required":
        _step_id(step_id, f"{label}.step_id", gaps)
        _text(item.get("environment"), f"{label}.environment", gaps)
    elif step_id is not None:
        gaps.append(f"{label}.step_id must be null unless decision is required")
    elif item.get("environment") is not None:
        gaps.append(f"{label}.environment must be null when validation is not required")
    _text(item.get("expected_outcome"), f"{label}.expected_outcome", gaps)


def _validate_promotion(value: Any, label: str, gaps: list[str]) -> None:
    item = _mapping(value, label, gaps)
    if item is None:
        return
    mode = item.get("mode")
    if mode not in _PROMOTION_MODE:
        gaps.append(f"{label}.mode must be none, dag, outer-loop, or blocked")
    step_id = item.get("step_id")
    if mode == "dag":
        _step_id(step_id, f"{label}.step_id", gaps)
    elif step_id is not None:
        gaps.append(f"{label}.step_id must be null unless mode is dag")
    if mode in ("dag", "outer-loop"):
        _text(item.get("target"), f"{label}.target", gaps)
    elif item.get("target") is not None:
        gaps.append(f"{label}.target must be null when promotion is none or blocked")
    _text(item.get("verification"), f"{label}.verification", gaps)


def validate_machine(machine: Any, *, required: bool = False) -> list[str]:
    """Validate only the versioned discovery declaration in a machine record.

    Missing discovery is legacy-compatible unless ``required`` is true.  A
    declared but malformed or unknown version is never treated as legacy.
    """
    gaps: list[str] = []
    if not isinstance(machine, Mapping):
        return ["machine must be an object before platform discovery can be checked"]
    record = _platform_record(machine)
    if record is _MISSING:
        return ["machine.platform_discovery is required for this new run"] if required else []
    discovery = _mapping(record, "machine.platform_discovery", gaps)
    if discovery is None:
        return gaps
    if _contains_sensitive_text(discovery):
        return ["machine.platform_discovery must not contain sensitive credential material"]
    if type(discovery.get("version")) is not int or discovery.get("version") != VERSION:
        gaps.append(f"machine.platform_discovery.version must be {VERSION}")
    applicable = discovery.get("applicable")
    if type(applicable) is not bool:
        gaps.append("machine.platform_discovery.applicable must be a boolean")
    _text(discovery.get("rationale"), "machine.platform_discovery.rationale", gaps)
    platforms = discovery.get("platforms")
    if not isinstance(platforms, list):
        gaps.append("machine.platform_discovery.platforms must be a list")
        return gaps
    if applicable is False:
        if platforms:
            gaps.append("machine.platform_discovery.platforms must be empty when applicable is false")
        return gaps
    if applicable is not True:
        return gaps
    if not platforms:
        gaps.append("machine.platform_discovery.platforms must be nonempty when applicable is true")
        return gaps
    exclusive_pairs: set[tuple[str, str]] = set()
    raw_exclusive = machine.get("exclusive", [])
    if isinstance(raw_exclusive, list):
        for index, row in enumerate(raw_exclusive):
            if not isinstance(row, Mapping):
                continue
            artifact = row.get("artifact")
            writer = row.get("use")
            if isinstance(artifact, str) and isinstance(writer, str):
                exclusive_pairs.add((artifact, writer))
            else:
                gaps.append(
                    f"machine.exclusive[{index}] artifact/use must be strings for platform routing"
                )
    seen_ids: set[str] = set()
    for index, row in enumerate(platforms):
        label = f"machine.platform_discovery.platforms[{index}]"
        platform = _mapping(row, label, gaps)
        if platform is None:
            continue
        platform_id = _text(platform.get("id"), f"{label}.id", gaps)
        if platform_id is not None:
            if not _PLATFORM_ID.fullmatch(platform_id):
                gaps.append(f"{label}.id must be a compact platform identifier")
            elif platform_id in seen_ids:
                gaps.append(f"{label}.id must be unique")
            seen_ids.add(platform_id)
        artifact = _text(platform.get("artifact"), f"{label}.artifact", gaps)
        writer = _text(platform.get("writer"), f"{label}.writer", gaps)
        if artifact is not None and writer is not None and (artifact, writer) not in exclusive_pairs:
            gaps.append(f"{label} writer/artifact must match a machine.exclusive row")
        interfaces = platform.get("interfaces")
        _validate_interfaces(interfaces, f"{label}.interfaces", gaps)
        if writer is not None and isinstance(interfaces, list):
            selected_names = {
                item.get("name")
                for item in interfaces
                if isinstance(item, Mapping) and isinstance(item.get("name"), str)
            }
            if writer not in selected_names:
                gaps.append(f"{label}.writer must match a selected interfaces[].name")
        _validate_identity(platform.get("identity"), f"{label}.identity", gaps)
        _validate_authority(platform.get("authority"), f"{label}.authority", gaps)
        _validate_bootstrap(platform.get("bootstrap"), f"{label}.bootstrap", gaps)
        _validate_development_validation(
            platform.get("development_validation"), f"{label}.development_validation", gaps
        )
        _validate_promotion(platform.get("promotion"), f"{label}.promotion", gaps)
        revalidate = _string_list(platform.get("revalidate_at"), f"{label}.revalidate_at", gaps)
        unsupported_triggers = sorted(set(revalidate) - _REVALIDATE_AT)
        if unsupported_triggers:
            gaps.append(
                f"{label}.revalidate_at has unsupported trigger(s): "
                + ", ".join(unsupported_triggers)
            )
        required_triggers = {"cold-resume", "before-external-operation"}
        promotion = platform.get("promotion")
        if isinstance(promotion, Mapping) and promotion.get("mode") in ("dag", "outer-loop"):
            required_triggers.add("before-promotion")
        missing_triggers = sorted(required_triggers - set(revalidate))
        if missing_triggers:
            gaps.append(
                f"{label}.revalidate_at is missing required trigger(s): "
                + ", ".join(missing_triggers)
            )
        blocked_paths = _string_list(
            platform.get("blocked_paths"), f"{label}.blocked_paths", gaps
        )
        blocked_reasons = _blocked_reasons(platform)
        if blocked_reasons and not blocked_paths:
            gaps.append(
                f"{label}.blocked_paths must contain an aggregate explanation "
                "when a route is blocked"
            )
        elif not blocked_reasons and blocked_paths:
            gaps.append(
                f"{label}.blocked_paths must be empty when no platform route is blocked"
            )
    return gaps


def _step_map(dag: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(dag, Mapping) or not isinstance(dag.get("steps"), list):
        return {}
    return {
        step["id"]: step
        for step in dag["steps"]
        if isinstance(step, Mapping) and isinstance(step.get("id"), str)
    }


def _depends_on(steps: Mapping[str, Mapping[str, Any]], descendant: str, ancestor: str) -> bool:
    """Return whether descendant has a strict transitive dependency on ancestor."""
    pending = [descendant]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        raw_inputs = steps.get(current, {}).get("inputs")
        if not isinstance(raw_inputs, list):
            continue
        for item in raw_inputs:
            parent = item.get("from") if isinstance(item, Mapping) else None
            if parent == ancestor:
                return True
            if isinstance(parent, str):
                pending.append(parent)
    return False


def _require_step(
    steps: Mapping[str, Mapping[str, Any]],
    step_id: Any,
    label: str,
    gaps: list[str],
    *,
    activity: str | None = None,
) -> str | None:
    if not isinstance(step_id, str) or step_id not in steps:
        gaps.append(f"{label} must reference an existing DAG step")
        return None
    if activity is not None and steps[step_id].get("activity") != activity:
        gaps.append(f"{label} must reference a DAG step with activity {activity}")
    return step_id


def validate_lifecycle(machine: Any, lifecycle: Any, dag: Any) -> list[str]:
    """Bind resolved platform declarations to the existing lifecycle and DAG.

    This is deliberately a planning gate.  It validates declared routes and
    ordering only; it neither runs probes nor treats the declaration as proof
    that a host can mutate a platform.
    """
    gaps = validate_machine(machine, required=False)
    if gaps or not isinstance(machine, Mapping):
        return gaps
    record = _platform_record(machine)
    if not isinstance(record, Mapping) or record.get("applicable") is not True:
        return []
    if not isinstance(lifecycle, Mapping):
        return ["lifecycle must be an object for applicable platform discovery"]
    steps = _step_map(dag)
    if not steps:
        return ["platform discovery requires a valid DAG before lifecycle routing"]
    rows = _platform_rows(machine)
    bootstrap_modes = {row.get("bootstrap", {}).get("mode") for row in rows if isinstance(row.get("bootstrap"), Mapping)}
    promotion_modes = {row.get("promotion", {}).get("mode") for row in rows if isinstance(row.get("promotion"), Mapping)}
    if "dag" in bootstrap_modes and "outer-before" in bootstrap_modes:
        gaps.append("platform bootstrap cannot mix dag and outer-before modes")
    if "dag" in bootstrap_modes and lifecycle.get("preparation") != "dag":
        gaps.append("platform bootstrap dag requires lifecycle.preparation=dag")
    if "outer-before" in bootstrap_modes and lifecycle.get("preparation") != "outer-before":
        gaps.append("platform bootstrap outer-before requires lifecycle.preparation=outer-before")
    if "dag" in promotion_modes and "outer-loop" in promotion_modes:
        gaps.append("platform promotion cannot mix dag and outer-loop modes")
    if "dag" in promotion_modes and lifecycle.get("publish") != "dag":
        gaps.append("platform promotion dag requires lifecycle.publish=dag")
    if "outer-loop" in promotion_modes and lifecycle.get("publish") != "outer-loop":
        gaps.append("platform promotion outer-loop requires lifecycle.publish=outer-loop")
    for row in rows:
        platform_id = row.get("id", "<invalid-platform>")
        if not isinstance(platform_id, str):
            platform_id = "<invalid-platform>"
        else:
            platform_id = redact_text(platform_id)
        label = f"platform {platform_id}"
        blocked = _blocked_reasons(row)
        if blocked:
            gaps.append(f"{label} has blocked route(s): {', '.join(blocked)}")
        authority = row.get("authority")
        if isinstance(authority, Mapping) and authority.get("required") is True and authority.get("status") != "observed":
            gaps.append(f"{label} requires observed non-secret authority before sequence")
        bootstrap = row.get("bootstrap") if isinstance(row.get("bootstrap"), Mapping) else {}
        validation = row.get("development_validation") if isinstance(row.get("development_validation"), Mapping) else {}
        promotion = row.get("promotion") if isinstance(row.get("promotion"), Mapping) else {}
        bootstrap_step: str | None = None
        if bootstrap.get("mode") == "dag":
            bootstrap_step = _require_step(
                steps, bootstrap.get("step_id"), f"{label} bootstrap.step_id", gaps, activity="preparation"
            )
        validation_step: str | None = None
        if validation.get("decision") == "required":
            validation_step = _require_step(
                steps, validation.get("step_id"), f"{label} development_validation.step_id", gaps
            )
        promotion_step: str | None = None
        if promotion.get("mode") == "dag":
            promotion_step = _require_step(
                steps, promotion.get("step_id"), f"{label} promotion.step_id", gaps, activity="publish"
            )
        if bootstrap_step is not None and validation_step is not None and not _depends_on(steps, validation_step, bootstrap_step):
            gaps.append(f"{label} development validation must depend on its bootstrap producer")
        if bootstrap_step is not None and promotion_step is not None and not _depends_on(steps, promotion_step, bootstrap_step):
            gaps.append(f"{label} promotion must depend on its bootstrap producer")
        if validation_step is not None and promotion_step is not None and not _depends_on(steps, promotion_step, validation_step):
            gaps.append(f"{label} promotion must depend on development validation")
    return gaps


_COLD_PLATFORM_LIMIT = 3
_COLD_INTERFACE_LIMIT = 2
_COLD_TEXT_LIMIT = 80


def _cold_text(value: Any) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    if sensitive_text(value):
        return redact_text(value), False
    if len(value) <= _COLD_TEXT_LIMIT:
        return value, False
    return value[:_COLD_TEXT_LIMIT], True


def _cold_named_fields(row: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    truncated: list[str] = []
    for key in keys:
        value, was_truncated = _cold_text(row.get(key))
        if value is not None:
            compact[key] = value
        if was_truncated:
            truncated.append(key)
    if truncated:
        compact["truncated"] = truncated
    return compact


def _cold_platform(row: Mapping[str, Any]) -> dict[str, Any]:
    identity = row.get("identity") if isinstance(row.get("identity"), Mapping) else {}
    authority = row.get("authority") if isinstance(row.get("authority"), Mapping) else {}
    bootstrap = row.get("bootstrap") if isinstance(row.get("bootstrap"), Mapping) else {}
    validation = (
        row.get("development_validation")
        if isinstance(row.get("development_validation"), Mapping)
        else {}
    )
    promotion = row.get("promotion") if isinstance(row.get("promotion"), Mapping) else {}
    interfaces = row.get("interfaces") if isinstance(row.get("interfaces"), list) else []
    compact = _cold_named_fields(row, ("id", "artifact", "writer"))
    compact["interfaces"] = [
        _cold_named_fields(interface, ("kind", "name", "version", "status"))
        for interface in interfaces[:_COLD_INTERFACE_LIMIT]
        if isinstance(interface, Mapping)
    ]
    if len(interfaces) > _COLD_INTERFACE_LIMIT:
        compact["interfaces_omitted"] = len(interfaces) - _COLD_INTERFACE_LIMIT
    compact["identity"] = {
        "status": identity.get("status"),
        "safe_probe_declared": bool(identity.get("safe_probe")),
    }
    compact["authority"] = {
        "required": authority.get("required"),
        "status": authority.get("status"),
    }
    compact["bootstrap"] = _cold_named_fields(bootstrap, ("mode", "step_id"))
    compact["development_validation"] = _cold_named_fields(
        validation, ("decision", "step_id")
    )
    compact["promotion"] = _cold_named_fields(promotion, ("mode", "step_id"))
    revalidate = row.get("revalidate_at") if isinstance(row.get("revalidate_at"), list) else []
    compact["revalidate_at"] = revalidate[:len(_REVALIDATE_AT)]
    if len(revalidate) > len(_REVALIDATE_AT):
        compact["revalidate_at_omitted"] = len(revalidate) - len(_REVALIDATE_AT)
    blocked_paths = row.get("blocked_paths") if isinstance(row.get("blocked_paths"), list) else []
    compact["blocked_path_count"] = len(blocked_paths)
    compact["details_in_environment"] = True
    return compact


def cold_projection(machine: Any) -> dict[str, Any]:
    """Return a bounded, non-secret declaration suitable for a cold packet.

    Narrative, probes, references, and outcomes remain in environment.md.  The
    packet carries only enough selected-route identity to choose that durable
    page after a context reset.
    """
    if not isinstance(machine, Mapping):
        return {"status": "unavailable"}
    record = _platform_record(machine)
    if record is _MISSING:
        return {"status": "legacy-not-recorded"}
    gaps = validate_machine(machine, required=False)
    if gaps:
        return {"status": "invalid", "gap_count": len(gaps)}
    assert isinstance(record, Mapping)
    applicable = record.get("applicable")
    if applicable is False:
        return {
            "status": "local-only",
            "applicable": False,
            "rationale_recorded": True,
            "details_in_environment": True,
        }
    rows = _platform_rows(machine)
    platforms = [_cold_platform(row) for row in rows[:_COLD_PLATFORM_LIMIT]]
    projection: dict[str, Any] = {
        "status": "recorded",
        "applicable": True,
        "rationale_recorded": True,
        "platforms": platforms,
        "details_in_environment": True,
    }
    if len(rows) > _COLD_PLATFORM_LIMIT:
        projection["platforms_omitted"] = len(rows) - _COLD_PLATFORM_LIMIT
    return projection
