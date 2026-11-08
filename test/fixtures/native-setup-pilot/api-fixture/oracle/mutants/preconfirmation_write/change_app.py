"""Mutation: proposal creation applies the change before confirmation."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
confirm_change = base_change.confirm_change
cancel_change = base_change.cancel_change


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    result = base_change.propose_change(
        actor, record_id, expected_version, changes, idempotency_key
    )
    if result["ok"]:
        base_change.confirm_change(actor, result["proposal_id"])
    return result
