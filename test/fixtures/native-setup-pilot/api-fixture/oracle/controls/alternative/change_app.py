"""Independent equivalent record API used as a calibration control."""
_record = {"id": "demo-1", "owner": "alice", "amount": 10, "version": 1}
_pending, _by_key, _counter = {}, {}, 0


def _failure(error_type, parameter, message):
    return {"ok": False, "error": f"{error_type}: {parameter} {message}"}


def fixture_seed(record=None):
    global _pending, _by_key, _counter
    initial = {"id": "demo-1", "owner": "alice", "amount": 10, "version": 1}
    _record.clear()
    _record.update(initial if record is None else record)
    _pending, _by_key, _counter = {}, {}, 0


def read_record(actor, record_id):
    if isinstance(actor, str) and isinstance(record_id, str):
        if actor == _record["owner"] and record_id == _record["id"]:
            return dict(_record)
    return None


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    global _counter
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if not isinstance(record_id, str):
        return _failure("TypeError", "record_id", "must be a string")
    if type(expected_version) is not int:
        return _failure("TypeError", "expected_version", "must be an integer")
    if not isinstance(idempotency_key, str):
        return _failure("TypeError", "idempotency_key", "must be a string")
    if not idempotency_key:
        return _failure("ValueError", "idempotency_key", "must be nonempty")
    if not isinstance(changes, dict):
        return _failure("TypeError", "changes", "must be a dict")
    if set(changes) != {"amount"}:
        return _failure("ValueError", "changes", "must contain only amount")
    amount = changes["amount"]
    if type(amount) is not int:
        return _failure("TypeError", "amount", "must be an integer")
    if amount < 1 or amount > 100:
        return _failure("ValueError", "amount", "must be between 1 and 100")

    request = (actor, record_id, expected_version, amount)
    previous = _by_key.get(idempotency_key)
    if previous is not None:
        old_request, old_id = previous
        if old_request == request:
            return {"ok": True, "proposal_id": old_id}
        return _failure("ValueError", "idempotency_key", "was reused for a different request")
    if record_id != _record["id"]:
        return _failure("KeyError", "record_id", "was not found")
    if actor != _record["owner"]:
        return _failure("PermissionError", "actor", "does not own the record")
    if expected_version != _record["version"]:
        return _failure("ValueError", "expected_version", "is stale")

    _counter += 1
    proposal_id = f"p{_counter}"
    _pending[proposal_id] = {
        "owner": actor,
        "record_id": record_id,
        "snapshot": expected_version,
        "value": amount,
        "state": "pending",
    }
    _by_key[idempotency_key] = (request, proposal_id)
    return {"ok": True, "proposal_id": proposal_id}


def confirm_change(actor, proposal_id):
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if not isinstance(proposal_id, str):
        return _failure("TypeError", "proposal_id", "must be a string")
    item = _pending.get(proposal_id)
    if item is None:
        return _failure("KeyError", "proposal_id", "was not found")
    if actor != item["owner"]:
        return _failure("PermissionError", "actor", "does not own the proposal")
    if item["state"] == "applied":
        return {"ok": True, "replayed": True}
    if item["state"] != "pending":
        return _failure("ValueError", "proposal_id", "is not pending")
    if item["snapshot"] != _record["version"]:
        return _failure("ValueError", "proposal_id", "has stale expected_version")
    _record["amount"] = item["value"]
    _record["version"] = _record["version"] + 1
    item["state"] = "applied"
    return {"ok": True, "replayed": False}


def cancel_change(actor, proposal_id):
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if not isinstance(proposal_id, str):
        return _failure("TypeError", "proposal_id", "must be a string")
    item = _pending.get(proposal_id)
    if item is None:
        return _failure("KeyError", "proposal_id", "was not found")
    if actor != item["owner"]:
        return _failure("PermissionError", "actor", "does not own the proposal")
    if item["state"] == "cancelled":
        return {"ok": True, "replayed": True}
    if item["state"] != "pending":
        return _failure("ValueError", "proposal_id", "is not pending")
    item["state"] = "cancelled"
    return {"ok": True, "replayed": False}
