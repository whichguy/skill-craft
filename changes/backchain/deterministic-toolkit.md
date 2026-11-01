---
bump: minor
---
Backchain ships its own command line, `scripts/backchain.py` (standard library, Python 3.9+): `check` gives the
structural verdict (the seven invariants) and completion of a plan, `package` writes it with recomputed
`parallel_groups`, and `export` writes the Plan Dispatcher execution graph of a complete plan. Native plans no
longer need the Backchain development checkout to be validated, packaged or handed to Plan Dispatcher.
