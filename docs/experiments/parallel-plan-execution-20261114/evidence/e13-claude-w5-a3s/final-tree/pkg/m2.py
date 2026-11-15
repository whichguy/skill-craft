_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    """Convert a Roman numeral (1..3999, standard subtractive form) to an int."""
    total = 0
    prev = 0
    for ch in reversed(s):
        v = _VALUES[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total
