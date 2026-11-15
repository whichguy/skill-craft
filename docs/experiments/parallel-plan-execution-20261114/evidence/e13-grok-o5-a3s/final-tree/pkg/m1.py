def rle(s):
    """Run-length encode s: each maximal run of equal chars becomes char + decimal length."""
    if not s:
        return ""
    parts = []
    prev = s[0]
    count = 1
    for ch in s[1:]:
        if ch == prev:
            count += 1
        else:
            parts.append(prev + str(count))
            prev = ch
            count = 1
    parts.append(prev + str(count))
    return "".join(parts)
