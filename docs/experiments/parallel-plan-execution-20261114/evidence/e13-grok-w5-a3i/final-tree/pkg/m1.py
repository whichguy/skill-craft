def rle(s):
    if not s:
        return ""
    out = []
    prev = s[0]
    n = 1
    for ch in s[1:]:
        if ch == prev:
            n += 1
        else:
            out.append(prev)
            out.append(str(n))
            prev = ch
            n = 1
    out.append(prev)
    out.append(str(n))
    return "".join(out)
