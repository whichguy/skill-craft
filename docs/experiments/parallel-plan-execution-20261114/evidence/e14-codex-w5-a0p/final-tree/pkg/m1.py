def rle(s):
    """Encode each maximal character run with its decimal length."""
    parts = []
    start = 0
    while start < len(s):
        end = start + 1
        while end < len(s) and s[end] == s[start]:
            end += 1
        parts.append(s[start] + str(end - start))
        start = end
    return "".join(parts)
