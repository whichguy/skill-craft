_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    """Convert a Roman numeral (1..3999, standard subtractive form) to int."""
    total = 0
    n = len(s)
    for i, ch in enumerate(s):
        v = _VALUES[ch]
        if i + 1 < n and v < _VALUES[s[i + 1]]:
            total -= v
        else:
            total += v
    return total
