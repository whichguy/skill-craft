def balanced(s):
    """Return whether bracket characters are balanced and properly nested."""
    stack = []
    opening = set("([{")
    matching = {")": "(", "]": "[", "}": "{"}
    for char in s:
        if char in opening:
            stack.append(char)
        elif char in matching:
            if not stack or stack.pop() != matching[char]:
                return False
    return not stack
