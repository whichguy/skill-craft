def roman_to_int(s):
    """Convert a valid standard Roman numeral to an integer."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50,
              "C": 100, "D": 500, "M": 1000}
    total = 0
    for index, char in enumerate(s):
        value = values[char]
        if index + 1 < len(s) and value < values[s[index + 1]]:
            total -= value
        else:
            total += value
    return total
