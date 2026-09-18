from access import ASSIGNMENTS
from board import cards_for


def metadata_reader():
    return next(
        principal
        for principal, permissions in ASSIGNMENTS.items()
        if {"board:read", "board:metadata:read"}.issubset(permissions)
    )


def verify():
    card = cards_for(metadata_reader())[0]
    assert card["account_tier"] == "standard"
    assert card["renewal_window"] == "Q4"


if __name__ == "__main__":
    verify()
    print("board verifier passed")
