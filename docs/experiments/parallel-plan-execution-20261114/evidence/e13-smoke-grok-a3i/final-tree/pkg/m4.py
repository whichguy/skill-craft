"""Bracket-balance checks for mixed (), [], {} sequences."""


def balanced(s):
    """Return True iff ()[]{} in s are balanced and properly nested.

    Non-bracket characters are ignored. An empty string is balanced.
    """
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return not stack
