def balanced(s):
    """Return whether the brackets in s are balanced and properly nested."""
    stack = []
    closing = {')': '(', ']': '[', '}': '{'}
    for char in s:
        if char in '([{':
            stack.append(char)
        elif char in closing:
            if not stack or stack.pop() != closing[char]:
                return False
    return not stack
