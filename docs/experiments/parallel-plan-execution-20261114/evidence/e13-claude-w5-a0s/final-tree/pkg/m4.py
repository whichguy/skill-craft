_PAIRS = {")": "(", "]": "[", "}": "{"}
_OPENERS = set(_PAIRS.values())


def balanced(s):
    """True when ()[]{} in s are balanced and properly nested; other chars ignored."""
    stack = []
    for ch in s:
        if ch in _OPENERS:
            stack.append(ch)
        elif ch in _PAIRS:
            if not stack or stack.pop() != _PAIRS[ch]:
                return False
    return not stack
