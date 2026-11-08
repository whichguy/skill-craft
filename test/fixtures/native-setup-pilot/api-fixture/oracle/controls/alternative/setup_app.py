"""Independent equivalent setup implementation used as a calibration control."""
_state = {"display_name": "Demo", "mode": "safe"}


def _failure(error_type, parameter, message):
    return {"ok": False, "error": f"{error_type}: {parameter} {message}"}


def fixture_seed(config):
    _state.clear()
    _state.update(config)


def read_config():
    return {key: value for key, value in _state.items()}


def save_setup(actor, values):
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if actor != "admin":
        return _failure("PermissionError", "actor", "is not authorized")
    if not isinstance(values, dict):
        return _failure("TypeError", "values", "must be a dict")
    if set(values) != {"display_name", "mode"}:
        return _failure("ValueError", "values", "must contain display_name and mode only")
    name = values["display_name"]
    mode = values["mode"]
    if not isinstance(name, str):
        return _failure("TypeError", "display_name", "must be a string")
    if not name.strip():
        return _failure("ValueError", "display_name", "must contain non-whitespace characters")
    if not isinstance(mode, str):
        return _failure("TypeError", "mode", "must be a string")
    if mode not in ("safe", "review"):
        return _failure("ValueError", "mode", "must be safe or review")
    _state["display_name"], _state["mode"] = name, mode
    return {"ok": True}
