# SQLite catalog contract

`Catalog.open(path)` creates a SQLite catalog seeded with `bookmark` (125) and
`notebook` (450), after an intentionally simulated 0.15 second startup cost.
`list_items()` returns name/cents pairs sorted by name. `add(name, cents)` takes
a nonblank string and positive `int` (never `bool`), rejects duplicates without
changing their existing value, and raises `ValueError` for bad input. `close()`
is safe to call more than once. `fail_after_open=True` simulates failure after
resource acquisition and must close the acquired connection.
