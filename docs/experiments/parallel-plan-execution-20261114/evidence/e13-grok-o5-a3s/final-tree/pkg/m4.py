"""Bracket-balance check that ignores non-bracket characters."""

_PAIRS = {")": "(", "]": "[", "}": "{"}
_OPEN = set(_PAIRS.values())


def balanced(s):
    """Return True iff ()[]{} in s are balanced and properly nested."""
    stack = []
    for ch in s:
        if ch in _OPEN:
            stack.append(ch)
        elif ch in _PAIRS:
            if not stack or stack[-1] != _PAIRS[ch]:
                return False
            stack.pop()
    return not stack
