"""Reference ledger with per-instance ownership and validate-before-commit."""

from __future__ import annotations


class Ledger:
    def __init__(self) -> None:
        self._balances: dict[str, int] = {}

    def apply(self, account: str, delta: int) -> int:
        current = self._balances.get(account, 0)
        next_balance = current + delta
        if next_balance < 0:
            raise ValueError("insufficient balance")
        self._balances[account] = next_balance
        return next_balance

    def snapshot(self) -> dict[str, int]:
        return dict(self._balances)
