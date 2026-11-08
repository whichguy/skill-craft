"""Mutation: convert pair-list changes to a dict before validation."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
confirm_change = base_change.confirm_change
cancel_change = base_change.cancel_change


def propose_change(actor, record_id, expected_version, changes, idempotency_key):
    if isinstance(changes, list):
        try:
            changes = dict(changes)
        except (TypeError, ValueError):
            pass
    return base_change.propose_change(
        actor, record_id, expected_version, changes, idempotency_key
    )
