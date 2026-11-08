"""Mutation: successful admin setup appears accepted but never persists."""
import base_setup

fixture_seed = base_setup.fixture_seed
read_config = base_setup.read_config


def save_setup(actor, values):
    result = base_setup.save_setup(actor, values)
    if result["ok"]:
        base_setup.fixture_seed({"display_name": "Demo", "mode": "safe"})
    return result
