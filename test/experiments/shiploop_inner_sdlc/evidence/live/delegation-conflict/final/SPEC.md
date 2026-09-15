# Immutable delivery quote contract

`quote.quote_cents(distance_km)` accepts a non-negative whole-number `int`
kilometre distance (never `bool`). The public kilometre value must be converted
to metres before the pricing component's metre interface is called. A quote is
200 cents plus 75 cents per complete kilometre. Invalid public inputs raise
`ValueError`. This is an isolated synthetic assembly, not real contributor work.
