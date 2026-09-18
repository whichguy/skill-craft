# Activity labels

This is a local, standard-library Python utility. `minute_tally.py` owns the
literal activity list for the current process. Each invocation starts with that
source list; the repository has no file store, database, network client,
background worker, or deployment target.

Run the existing command with:

```sh
python3 minute_tally.py
```

Run the tests with:

```sh
python3 -m unittest test_minute_tally.py
```

