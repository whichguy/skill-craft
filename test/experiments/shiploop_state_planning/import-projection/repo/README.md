# Synthetic import projection

This is a local, standard-library model of a file-import state machine and a
database projection. It has no database connection, worker, credentials, or
release system. The source code models records in memory so a planner can trace
the existing contract; it does not authorize a real migration or rollout.

Run the current focused tests with:

```sh
python3 -m unittest test_imports.py
```

Read `docs/` before proposing a change: the state contract, reader compatibility
window, rollout sequence, and accepted workload criteria are separate inputs.
