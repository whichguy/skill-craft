"""Mutant: writes an invalid balance before validating the transition."""

from __future__ import annotations


class Ledger:
    def __init__(self) -> None:
        self._balances: dict[str, int] = {}

    def apply(self, account: str, delta: int) -> int:
        next_balance = self._balances.get(account, 0) + delta
        self._balances[account] = next_balance
        if next_balance < 0:
            raise ValueError("insufficient balance")
        return next_balance

    def snapshot(self) -> dict[str, int]:
        return dict(self._balances)
