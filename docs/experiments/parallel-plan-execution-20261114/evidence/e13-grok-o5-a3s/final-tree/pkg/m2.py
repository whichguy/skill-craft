"""Roman numeral conversion."""


def roman_to_int(s: str) -> int:
    """Convert a valid standard-subtractive Roman numeral (1..3999) to int."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    n = len(s)
    for i, ch in enumerate(s):
        val = values[ch]
        if i + 1 < n and val < values[s[i + 1]]:
            total -= val
        else:
            total += val
    return total
