"""Mutation: stringify a non-string idempotency key before validation."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
confirm_change = base_change.confirm_change
cancel_change = base_change.cancel_change


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    if not isinstance(idempotency_key, str):
        idempotency_key = str(idempotency_key)
    return base_change.propose_change(
        actor, record_id, expected_version, changes, idempotency_key
    )
