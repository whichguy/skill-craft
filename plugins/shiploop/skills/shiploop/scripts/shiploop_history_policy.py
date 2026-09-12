"""Immutable per-run Git-history review policy for ShipLoop."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


LEGACY_VERSION = 1
LEGACY_REQUIRED_LIMIT = 10
VERSION = 2
REQUIRED_LIMIT = 7

_MARKER = "history_policy"
_MISSING = object()


class HistoryPolicyError(ValueError):
    """The durable history policy cannot be safely interpreted."""


def _legacy() -> dict[str, int]:
    return {"version": LEGACY_VERSION, "required_limit": LEGACY_REQUIRED_LIMIT}


def _current() -> dict[str, int]:
    return {"version": VERSION, "required_limit": REQUIRED_LIMIT}


def _current_marker(value: Any, *, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != {"version", "required_limit"}:
        raise HistoryPolicyError(f"{label} is malformed")
    if type(value["version"]) is not int or type(value["required_limit"]) is not int:
        raise HistoryPolicyError(f"{label} is malformed")
    if dict(value) != _current():
        raise HistoryPolicyError(f"{label} is unsupported")
    return _current()


def resolve(state: Mapping[str, Any]) -> dict[str, int]:
    """Return this run's policy; a missing marker is the immutable legacy mode."""
    if not isinstance(state, Mapping):
        raise HistoryPolicyError("history policy state is malformed")
    marker = state.get(_MARKER, _MISSING)
    if marker is _MISSING:
        return _legacy()
    return _current_marker(marker, label="history policy")


def required_limit(state: Mapping[str, Any]) -> int:
    """Return the policy-owned number of current full bodies required for review."""
    return resolve(state)["required_limit"]


def bind(iteration: MutableMapping[str, Any], state: Mapping[str, Any]) -> dict[str, int]:
    """Bind a policy to a current pass before recording history evidence."""
    if not isinstance(iteration, MutableMapping):
        raise HistoryPolicyError("history pass is malformed")
    policy = resolve(state)
    marker = iteration.get(_MARKER, _MISSING)
    if policy == _legacy():
        if marker is not _MISSING:
            raise HistoryPolicyError("legacy history pass has an unsupported policy binding")
        return policy
    if marker is _MISSING:
        iteration[_MARKER] = dict(policy)
        return policy
    if _current_marker(marker, label="history pass policy") != policy:
        raise HistoryPolicyError("history pass policy does not match the run policy")
    return policy


def bound(iteration: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, int]:
    """Require the pass policy to match its immutable run policy.

    Existing legacy receipts predate the binding field, so their absent field is
    deliberately accepted only when the run itself has no policy marker.
    """
    if not isinstance(iteration, Mapping):
        raise HistoryPolicyError("history pass is malformed")
    policy = resolve(state)
    marker = iteration.get(_MARKER, _MISSING)
    if marker is _MISSING:
        if policy == _legacy():
            return policy
        raise HistoryPolicyError("history pass policy binding is missing")
    if policy == _legacy():
        raise HistoryPolicyError("legacy history pass has an unsupported policy binding")
    if _current_marker(marker, label="history pass policy") != policy:
        raise HistoryPolicyError("history pass policy does not match the run policy")
    return policy
