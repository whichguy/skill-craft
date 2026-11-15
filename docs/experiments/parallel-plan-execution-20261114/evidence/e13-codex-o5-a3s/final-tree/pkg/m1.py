def rle(s):
    """Encode each maximal character run with its decimal length."""
    if not s:
        return ""
    result = []
    previous = s[0]
    count = 1
    for character in s[1:]:
        if character == previous:
            count += 1
        else:
            result.append(previous + str(count))
            previous = character
            count = 1
    result.append(previous + str(count))
    return "".join(result)
