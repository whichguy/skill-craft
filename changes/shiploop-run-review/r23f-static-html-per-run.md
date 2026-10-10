---
bump: patch
---
Every Run Review export now also writes `run-review.html`: one self-contained, read-only file with that run's documents (the
run, its packets and Backchain loops, the starting expectations and settings) embedded in the page and a small stand-in for the
database, so the review of one run opens from disk with no network and can be kept as a reference. It says it is a static copy of
one run, not the shared record, and writes nothing. `export.py RUN_DIR --no-html` skips it.
