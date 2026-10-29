---
bump: minor
---
`shiploop check` asks whether ShipLoop would accept the current result now, and `complete` takes its yes.
- The check and `complete` run one evaluator, so they give the same answer on the same inputs. Before, a dry run held
  the test stage's candidate to no floor and `complete` then refused it below the base run's count; and a dry run
  skipped the inner stage's allowed outcomes, so `complete` refused an outcome the dry run had passed.
- The check records one answer in `RUN/checks/<action>.md`, yes or no with the reason, tied to the state revision,
  the package version, the loop contract, the result draft, the working tree, the item's base, the counted runs the
  floors read and the lint option. `complete` takes a yes whose key still matches: it runs no gate again, and writes
  the check's base, candidate, mutation and Proof records as its counted ones, each naming the check record. Any
  change since the check makes `complete` run every gate again.
- The test stage's check now makes the real base run (`RUN/tests/<action>-base-check.md`, never counted), and holds
  its candidate run to the floor that run sets.
- Why: the phases B and C plan (docs/shiploop-check-phases-bc-plan-2026-10-28.md, findings F15 and P9).
