# Price and format contract

`price_cents(quantity, unit_cents)` accepts non-negative `int` values (never
`bool`) and returns their product. `format_price(cents)` accepts a non-negative
`int` (never `bool`) and returns dollars with exactly two decimal digits. Bad
inputs raise `ValueError`. Both functions are stateless.
