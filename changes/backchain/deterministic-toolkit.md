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
  route; `record` saves each review cycle and writes its report (a cycle whose plan changed is never trivial, and
  an assessment names the candidate it reviewed and what it checked); `verify` is the contract's evidence check and
  refuses any change to the frozen inputs, contract or resolved resources; `finish` accepts only the run's own
  terminal Until Loop packet and writes `{plan, convergence}`, or `{plan, review}` for a caller packet with
  `--review FILE`.
- Inherited steps keep their IDs and input edges, checked mechanically, and a caller's `edit_bounds` are enforced
  (edge keys `consumer<-supplier`, `null` for an `initial_state` input); an edge or step the run itself generated
  may be removed by a later review.
