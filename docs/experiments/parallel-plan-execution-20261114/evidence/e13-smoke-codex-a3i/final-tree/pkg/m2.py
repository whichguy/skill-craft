def roman_to_int(s):
    """Convert a valid standard Roman numeral to an integer."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for symbol in reversed(s):
        value = values[symbol]
        total += -value if value < previous else value
        previous = value
    return total
