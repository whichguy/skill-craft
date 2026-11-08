"""Synthetic record-change API with deterministic in-memory state."""

_INITIAL = {"id": "demo-1", "owner": "alice", "amount": 10, "version": 1}
_record = dict(_INITIAL)
_proposals = {}
_keys = {}
_next_id = 1


def _failure(error_type, parameter, message):
    return {"ok": False, "error": f"{error_type}: {parameter} {message}"}


def fixture_seed(record=None):
    """Reset known record state for a test precondition."""
    global _record, _proposals, _keys, _next_id
    _record = dict(_INITIAL if record is None else record)
    _proposals, _keys, _next_id = {}, {}, 1


def read_record(actor, record_id):
    if not isinstance(actor, str) or not isinstance(record_id, str):
        return None
    if record_id != _record["id"] or actor != _record["owner"]:
        return None
    return dict(_record)


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    global _next_id
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
    if not 1 <= amount <= 100:
        return _failure("ValueError", "amount", "must be between 1 and 100")

    fingerprint = (actor, record_id, expected_version, amount)
    if idempotency_key in _keys:
        old_fingerprint, proposal_id = _keys[idempotency_key]
        if old_fingerprint == fingerprint:
            return {"ok": True, "proposal_id": proposal_id}
        return _failure("ValueError", "idempotency_key", "was reused for a different request")
    if record_id != _record["id"]:
        return _failure("KeyError", "record_id", "was not found")
    if actor != _record["owner"]:
        return _failure("PermissionError", "actor", "does not own the record")
    if expected_version != _record["version"]:
        return _failure("ValueError", "expected_version", "is stale")

    proposal_id = f"p{_next_id}"
    _next_id += 1
    _proposals[proposal_id] = {
        "owner": actor,
        "record_id": record_id,
        "expected_version": expected_version,
        "amount": amount,
        "status": "pending",
    }
    _keys[idempotency_key] = (fingerprint, proposal_id)
    return {"ok": True, "proposal_id": proposal_id}


def confirm_change(actor, proposal_id):
    """Confirm a proposal once, preserving successful retries after a lost response.

    actor and proposal_id must be strings identifying an owned, known proposal.
    A pending proposal must still match the record version. Applied proposals
    replay successfully; cancelled proposals cannot be confirmed.

    Return {"ok": True, "replayed": False} for the first application or
    {"ok": True, "replayed": True} for an already applied proposal. The first
    application sets the record amount to the proposed amount, increments its
    version once, and marks the proposal applied. Replay changes no state.

    Invalid types, unknown IDs, foreign ownership, non-pending status and stale
    versions return {"ok": False, "error": <typed diagnostic string>} with no
    state change. Expected validation failures are returned, not raised.
    """
    if not isinstance(actor, str):
        return _failure("TypeError", "confirm_change actor", f"expected a string; received {actor!r}")
    if not isinstance(proposal_id, str):
        return _failure("TypeError", "confirm_change proposal_id", f"expected a string; received {proposal_id!r}")
    proposal = _proposals.get(proposal_id)
    if proposal is None:
        return _failure("KeyError", "confirm_change proposal_id", f"expected a known proposal; received {proposal_id!r}")
    if actor != proposal["owner"]:
        return _failure("PermissionError", "confirm_change actor", f"expected the authorized owner for {proposal_id!r}; received {actor!r}")
    # A retry can arrive after its first write succeeded but the response was lost.
    # Resolve applied proposals before checking the captured version: that version
    # is stale after success. Moving/removing this guard used to reject valid replay.
    if proposal["status"] == "applied":
        return {"ok": True, "replayed": True}
    if proposal["status"] != "pending":
        return _failure("ValueError", "confirm_change proposal_id", f"{proposal_id!r} expected pending status; received {proposal['status']!r}")
    if _record["version"] != proposal["expected_version"]:
        return _failure("ValueError", "confirm_change proposal_id", f"{proposal_id!r} expected record version {proposal['expected_version']}; received {_record['version']}")
    _record["amount"] = proposal["amount"]
    _record["version"] += 1
    proposal["status"] = "applied"
    return {"ok": True, "replayed": False}


def cancel_change(actor, proposal_id):
    if not isinstance(actor, str):
        return _failure("TypeError", "actor", "must be a string")
    if not isinstance(proposal_id, str):
        return _failure("TypeError", "proposal_id", "must be a string")
    proposal = _proposals.get(proposal_id)
    if proposal is None:
        return _failure("KeyError", "proposal_id", "was not found")
    if actor != proposal["owner"]:
        return _failure("PermissionError", "actor", "does not own the proposal")
    if proposal["status"] == "cancelled":
        return {"ok": True, "replayed": True}
    if proposal["status"] != "pending":
        return _failure("ValueError", "proposal_id", "is not pending")
    proposal["status"] = "cancelled"
    return {"ok": True, "replayed": False}
