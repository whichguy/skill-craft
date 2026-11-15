"""Roman numeral conversion."""

_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def roman_to_int(s: str) -> int:
    """Convert a standard subtractive Roman numeral in 1..3999 to an int."""
    total = 0
    prev = 0
    for ch in reversed(s):
        value = _VALUES[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total
