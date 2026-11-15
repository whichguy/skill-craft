def rle(s):
    """Run-length encode a string: each maximal run becomes char + decimal length."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        j = i
        while j < n and s[j] == s[i]:
            j += 1
        out.append(s[i] + str(j - i))
        i = j
    return "".join(out)
