from __future__ import annotations

def suite(*names):
    """Mark a unittest method or class for focused and/or smoke selection."""
    def apply(target):
        target.__shiploop_suites__ = frozenset(names)
        return target
    return apply
