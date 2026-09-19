"""Mutant: a class-level mapping leaks balances between Ledger instances."""

from __future__ import annotations


class Ledger:
    _balances: dict[str, int] = {}

    def apply(self, account: str, delta: int) -> int:
        current = self._balances.get(account, 0)
        next_balance = current + delta
        if next_balance < 0:
            raise ValueError("insufficient balance")
        self._balances[account] = next_balance
        return next_balance

    def snapshot(self) -> dict[str, int]:
        return dict(self._balances)
