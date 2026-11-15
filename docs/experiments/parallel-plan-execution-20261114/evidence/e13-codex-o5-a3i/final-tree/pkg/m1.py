def rle(s):
    """Encode each maximal character run with its decimal length."""
    if not s:
        return ""
    parts = []
    char = s[0]
    count = 1
    for current in s[1:]:
        if current == char:
            count += 1
        else:
            parts.append(char + str(count))
            char = current
            count = 1
    parts.append(char + str(count))
    return "".join(parts)
