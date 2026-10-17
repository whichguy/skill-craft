---
bump: minor
---
The ShipLoop skill card opens with a recovery block and is split into purpose files, so a model that lost its context
reads about 30 KB instead of 83 KB before it acts.
- Directly after the title, the card says what to do after a reset, summary or compaction: run
  `python3 <this skill>/scripts/shiploop next --run-dir <the run directory named in your summary or handoff>`, follow the
  packet it prints, and if no run directory is known, list `<repo-parent>/.shiploop-runs/*/run/state.md`, use the only
  active run for this repository, and record an open item instead of guessing when there are several. It asks the model
  to keep that command in any summary it writes.
- The card (83,199 bytes before, 29,771 now) keeps binding, starting and recovering a run, ownership, the durable
  handoff, following the current packet and the authority limits. Every other section moved, text unchanged, into ten
  files of at most 8 KB under `references/`, each opened behind a one-line trigger in the card's new "Read when" list:
  `run-start.md`, `run-options.md`, `backchain-route.md`, `guide-map.md`, `improve-stages.md`, `improve-child.md`,
  `inner-loop.md`, `test-loop.md`, `chain-route.md` and `chain-navigation.md`. Links from the other references and the
  README now point to the section's new file.
