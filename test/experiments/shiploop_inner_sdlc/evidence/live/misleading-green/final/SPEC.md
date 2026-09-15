# Immutable allocation contract

`allocate_cents(total_cents, weights)` returns a new list of integer-cent
shares. `total_cents` is a non-negative `int` (never `bool`); `weights` is a
nonempty list of positive `int` values (never `bool`). Invalid input raises
`ValueError`, and `weights` must remain unchanged. Compute proportional floor
shares, then distribute leftover cents in input order, one per weight. Output
must sum exactly to `total_cents`. Keep this standard-library fixture small.
