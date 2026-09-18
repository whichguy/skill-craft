from copy import deepcopy


TRANSITIONS = {
    "received": {"validating"},
    "validating": {"accepted", "rejected"},
    "accepted": {"projecting"},
    "projecting": {"projected", "failed"},
    "failed": {"projecting"},
    "rejected": set(),
    "projected": set(),
}

EDITABLE_STATES = {"accepted", "projecting"}


class ConflictError(ValueError):
    pass


def transition(record, next_state):
    if next_state not in TRANSITIONS[record["state"]]:
        raise ValueError(f"invalid transition: {record['state']} -> {next_state}")
    updated = deepcopy(record)
    updated["state"] = next_state
    return updated


def append_summary_edit(record, expected_revision, text):
    if record["state"] not in EDITABLE_STATES:
        raise ValueError("summary edits require an accepted or projecting import")
    if expected_revision != record["revision"]:
        raise ConflictError("stale import revision")
    updated = deepcopy(record)
    updated["summary"] = [*record["summary"], text]
    updated["revision"] += 1
    return updated

