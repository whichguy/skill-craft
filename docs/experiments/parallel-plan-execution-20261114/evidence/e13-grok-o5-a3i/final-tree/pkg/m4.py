"""Bracket-balance checks that ignore non-bracket characters."""

_PAIRS = {")": "(", "]": "[", "}": "{"}
_OPEN = set(_PAIRS.values())


def balanced(s):
    """Return True if ()[]{} in s are balanced and nested; ignore other chars."""
    stack = []
    for ch in s:
        if ch in _OPEN:
            stack.append(ch)
        elif ch in _PAIRS:
            if not stack or stack[-1] != _PAIRS[ch]:
                return False
            stack.pop()
    return not stack
