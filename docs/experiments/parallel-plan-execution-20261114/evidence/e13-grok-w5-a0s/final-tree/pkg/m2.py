"""Convert standard subtractive Roman numerals to integers."""

_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s: str) -> int:
    total = 0
    prev = 0
    for ch in reversed(s):
        val = _VALUES[ch]
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total
