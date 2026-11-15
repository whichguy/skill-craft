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
    """Convert a standard subtractive Roman numeral (1..3999) to an integer."""
    total = 0
    n = len(s)
    for i, ch in enumerate(s):
        value = _VALUES[ch]
        if i + 1 < n and value < _VALUES[s[i + 1]]:
            total -= value
        else:
            total += value
    return total
