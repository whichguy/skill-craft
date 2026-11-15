"""Bracket balancing."""

_PAIRS = {")": "(", "]": "[", "}": "{"}
_OPEN = set(_PAIRS.values())


def balanced(s):
    """Return True if the brackets ()[]{} in s are balanced and properly nested."""
    stack = []
    for ch in s:
        if ch in _OPEN:
            stack.append(ch)
        elif ch in _PAIRS:
            if not stack or stack.pop() != _PAIRS[ch]:
                return False
    return not stack
