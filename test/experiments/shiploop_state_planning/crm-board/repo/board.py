from access import has_access


CARD = {
    "account": "sample-account-01",
    "account_tier": "standard",
    "renewal_window": "Q4",
}


def cards_for(principal):
    if not has_access(principal, "board:read"):
        raise PermissionError("board access is required")

    card = {"account": CARD["account"]}
    if has_access(principal, "board:metadata:read"):
        card.update(
            account_tier=CARD["account_tier"],
            renewal_window=CARD["renewal_window"],
        )
    return [card]

