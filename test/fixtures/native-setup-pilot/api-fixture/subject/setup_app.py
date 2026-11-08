"""Small in-memory setup API. State is deterministic and provider-free."""

_INITIAL = {"display_name": "Demo", "mode": "safe"}
_config = dict(_INITIAL)


def _failure(error_type, parameter, message):
    return {"ok": False, "error": f"{error_type}: {parameter} {message}"}


def fixture_seed(config):
    """Set a known precondition in tests; this bypasses authorization."""
    global _config
    _config = dict(config)


def read_config():
    """Read a copy of the non-secret setup configuration."""
    return dict(_config)


def save_setup(actor, values):
    """Save exact, validated fields for the authorized admin."""
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if actor != "admin":
        return _failure("PermissionError", "actor", "is not authorized")
    if not isinstance(values, dict):
        return _failure("TypeError", "values", "must be a dict")
    if set(values) != {"display_name", "mode"}:
        return _failure("ValueError", "values", "must contain display_name and mode only")
    name, mode = values["display_name"], values["mode"]
    if not isinstance(name, str):
        return _failure("TypeError", "display_name", "must be a string")
    if not name.strip():
        return _failure("ValueError", "display_name", "must contain non-whitespace characters")
    if not isinstance(mode, str):
        return _failure("TypeError", "mode", "must be a string")
    if mode not in {"safe", "review"}:
        return _failure("ValueError", "mode", "must be safe or review")
    global _config
    _config = {"display_name": name, "mode": mode}
    return {"ok": True}
