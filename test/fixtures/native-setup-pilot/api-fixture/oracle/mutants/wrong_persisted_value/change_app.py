"""Mutation: confirmation persists a value one greater than proposed."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
propose_change = base_change.propose_change
cancel_change = base_change.cancel_change


def confirm_change(actor, proposal_id):
    result = base_change.confirm_change(actor, proposal_id)
    if result.get("ok") and not result.get("replayed"):
        base_change._record["amount"] += 1
    return result
