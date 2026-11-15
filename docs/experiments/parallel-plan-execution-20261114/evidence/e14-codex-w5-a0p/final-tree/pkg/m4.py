def balanced(s):
    """Check bracket nesting, ignoring characters other than brackets."""
    stack = []
    matching = {")": "(", "]": "[", "}": "{"}
    for char in s:
        if char in "([{":
            stack.append(char)
        elif char in matching:
            if not stack or stack.pop() != matching[char]:
                return False
    return not stack
