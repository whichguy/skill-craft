"""Mutation: a denied actor can still overwrite setup configuration."""
import base_setup

fixture_seed = base_setup.fixture_seed
read_config = base_setup.read_config


def save_setup(actor, values):
    if actor != "admin" and isinstance(values, dict):
        base_setup.fixture_seed(values)
        return {"ok": False, "error": "PermissionError: actor is not authorized"}
    return base_setup.save_setup(actor, values)
