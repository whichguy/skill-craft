"""Mutation: confirmation replay performs a second persisted write."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
propose_change = base_change.propose_change
cancel_change = base_change.cancel_change


def confirm_change(actor, proposal_id):
    result = base_change.confirm_change(actor, proposal_id)
    if result.get("ok") and result.get("replayed"):
        base_change._record["version"] += 1
    return result
