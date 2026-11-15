def rle(s):
    if not s:
        return ""
    parts = []
    current = s[0]
    count = 1
    for char in s[1:]:
        if char == current:
            count += 1
        else:
            parts.append(current + str(count))
            current, count = char, 1
    parts.append(current + str(count))
    return "".join(parts)
