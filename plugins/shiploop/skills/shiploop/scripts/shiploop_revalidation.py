"""Pure validation for host-reported, action-bound platform revalidation.

The host—not this module—runs a documented non-mutating safe probe before an
authorized external operation.  These validators preserve only a
non-secret attestation tied to the action and frozen environment that selected
the route.  They do not run a probe or independently establish its timing.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from shiploop_privacy import sensitive_text


VERSION = 1
TRIGGERS = frozenset(("before-external-operation", "before-promotion"))
ROW_KEYS = frozenset(
    (
        "platform_id",
        "trigger",
        "action_id",
        "environment_sha256",
        "observed_role",
        "status",
        "evidence",
        "performed_before_operation",
    )
)


def _text(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a nonempty string")
        return None
    return value


def _requirements(
    value: Any, errors: list[str]
) -> dict[tuple[str, str], Mapping[str, Any]]:
    """Normalize protocol-owned requirements without accepting ambiguity."""
    if not isinstance(value, list):
        errors.append("platform revalidation requirements must be a list")
        return {}
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for index, raw in enumerate(value):
        label = f"platform revalidation requirement[{index}]"
        if not isinstance(raw, Mapping):
            errors.append(f"{label} must be an object")
            continue
        platform_id = _text(raw.get("platform_id"), f"{label}.platform_id", errors)
        trigger = raw.get("trigger")
        valid_trigger = isinstance(trigger, str) and trigger in TRIGGERS
        if not valid_trigger:
            errors.append(f"{label}.trigger must be a supported trigger")
        role = _text(raw.get("observed_role"), f"{label}.observed_role", errors)
        environment = _text(
            raw.get("environment_sha256"), f"{label}.environment_sha256", errors
        )
        if platform_id is None or not valid_trigger or role is None or environment is None:
            continue
        pair = (platform_id, trigger)
        if pair in out:
            errors.append("platform revalidation requirements duplicate platform/trigger")
            continue
        out[pair] = raw
    return out


def validate_result(
    result: Any,
    requirements: Any,
    *,
    action_id: Any,
) -> list[str]:
    """Return attestation gaps for one host completion result.

    An empty requirement list deliberately preserves the legacy result shape:
    callers need not add a ``platform_revalidation`` field.  If one is
    supplied anyway, it can only be an explicit empty list, preventing an
    unbound secret-like or misleading external-operation claim from becoming
    an unvalidated result field.
    """
    errors: list[str] = []
    expected = _requirements(requirements, errors)
    if not isinstance(result, Mapping):
        return errors + ["platform revalidation result must be an object"]
    if not expected:
        if "platform_revalidation" not in result:
            return errors
        if result.get("platform_revalidation") != []:
            errors.append(
                "platform_revalidation must be omitted or [] when no external route is selected"
            )
        return errors
    if "platform_revalidation" not in result:
        return errors + ["platform_revalidation is required before the selected external operation"]
    rows = result.get("platform_revalidation")
    if not isinstance(rows, list):
        return errors + ["platform_revalidation must be a list"]
    seen: set[tuple[str, str]] = set()
    for index, raw in enumerate(rows):
        label = f"platform_revalidation[{index}]"
        if not isinstance(raw, Mapping):
            errors.append(f"{label} must be an object")
            continue
        string_keys = {key for key in raw if isinstance(key, str)}
        missing = sorted(ROW_KEYS - string_keys)
        unsupported = any(
            not isinstance(key, str) or key not in ROW_KEYS for key in raw
        )
        if missing:
            errors.append(f"{label} is missing keys: {', '.join(missing)}")
        if unsupported:
            errors.append(f"{label} has unsupported or non-string keys")
        platform_id = _text(raw.get("platform_id"), f"{label}.platform_id", errors)
        trigger = raw.get("trigger")
        valid_trigger = isinstance(trigger, str) and trigger in TRIGGERS
        if not valid_trigger:
            errors.append(f"{label}.trigger must be a supported trigger")
        pair = (platform_id, trigger) if platform_id is not None and valid_trigger else None
        if pair is not None:
            if pair in seen:
                errors.append("platform_revalidation duplicates platform/trigger")
            seen.add(pair)
            requirement = expected.get(pair)
            if requirement is None:
                errors.append("platform_revalidation has unexpected platform/trigger")
            else:
                expected_environment = requirement["environment_sha256"]
                expected_role = requirement["observed_role"]
                if raw.get("environment_sha256") != expected_environment:
                    errors.append(
                        f"{label}.environment_sha256 does not match the frozen environment"
                    )
                if raw.get("observed_role") != expected_role:
                    errors.append(
                        f"{label}.observed_role does not match the selected platform role"
                    )
        if raw.get("action_id") != action_id:
            errors.append(f"{label}.action_id must bind the current action")
        if raw.get("status") != "ready":
            errors.append(f"{label}.status must be ready")
        _text(raw.get("evidence"), f"{label}.evidence", errors)
        for key in ROW_KEYS:
            value = raw.get(key)
            if isinstance(value, str) and sensitive_text(value):
                errors.append(f"{label}.{key} must not contain credential-like text")
        if raw.get("performed_before_operation") is not True:
            errors.append(f"{label}.performed_before_operation must be true")
    for platform_id, trigger in expected:
        if (platform_id, trigger) not in seen:
            errors.append(
                "platform_revalidation is missing required platform/trigger: "
                f"{platform_id}/{trigger}"
            )
    return errors
