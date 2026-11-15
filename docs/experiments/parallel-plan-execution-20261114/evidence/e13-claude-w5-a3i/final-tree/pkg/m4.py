PAIRS = {")": "(", "]": "[", "}": "{"}
OPENERS = set(PAIRS.values())


def balanced(s):
    stack = []
    for ch in s:
        if ch in OPENERS:
            stack.append(ch)
        elif ch in PAIRS:
            if not stack or stack.pop() != PAIRS[ch]:
                return False
    return not stack
