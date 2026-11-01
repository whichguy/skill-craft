---
bump: minor
---
Backchain ships its own command line, `scripts/backchain.py` (standard library, Python 3.9+), so a planning run no
longer writes its own bookkeeping code:

- `check` gives the structural verdict (the seven invariants) and completion of a plan, `package` writes it with
  recomputed `parallel_groups`, and `export` writes the Plan Dispatcher execution graph of a complete plan. Native
  plans no longer need the Backchain development checkout to be validated, packaged or handed to Plan Dispatcher.
- `prepare`, `freeze`, `record`, `verify` and `finish` keep a planning run's records: `freeze` writes the whole
  Until Loop contract (gate, every bound resource, frozen exit checks) for Until Loop's parent-written-contract
  route, `record` saves each review cycle and writes its report (a cycle whose plan changed is never trivial),
  `verify` is the contract's evidence check, and `finish` writes `{plan, convergence}`.
- Inherited steps keep their IDs and input edges, checked mechanically; an edge or step the run itself generated
  may be removed by a later review.
