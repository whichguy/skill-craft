"""Mutation: extract a record ID from a mapping passed as record_id."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
confirm_change = base_change.confirm_change
cancel_change = base_change.cancel_change


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    if isinstance(record_id, dict) and isinstance(record_id.get("id"), str):
        record_id = record_id["id"]
    return base_change.propose_change(
        actor, record_id, expected_version, changes, idempotency_key
    )
