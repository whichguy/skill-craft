def price_cents(quantity, unit_cents):
    if type(quantity) is not int or quantity < 0:
        raise ValueError("quantity")
    if type(unit_cents) is not int or unit_cents < 0:
        raise ValueError("unit_cents")
    return quantity * unit_cents

def format_price(cents):
    if type(cents) is not int or cents < 0:
        raise ValueError("cents")
    return f"${cents // 100}.{cents % 100:02d}"
