def rle(s):
    """Encode each maximal character run with its decimal length."""
    if not s:
        return ""
    parts = []
    previous = s[0]
    count = 1
    for char in s[1:]:
        if char == previous:
            count += 1
        else:
            parts.append(previous + str(count))
            previous = char
            count = 1
    parts.append(previous + str(count))
    return "".join(parts)
