"""Mutation: cancelling a pending proposal writes its proposed amount."""
import base_change

fixture_seed = base_change.fixture_seed
read_record = base_change.read_record
propose_change = base_change.propose_change
confirm_change = base_change.confirm_change


def cancel_change(actor, proposal_id):
    result = base_change.cancel_change(actor, proposal_id)
    if result.get("ok") and not result.get("replayed"):
        base_change._record["amount"] = base_change._proposals[proposal_id]["amount"]
    return result
