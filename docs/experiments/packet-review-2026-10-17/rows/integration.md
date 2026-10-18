# Integration of the packet-review units (2026-10-17, firm)

- Branch `feat/shiploop-eff-int-c5f79b`. Wave 1 (U1-U10, six workers from 03c5edbc) merged in ad785c2f (U9), 986f63aa (U5),
  U6, acee1c33 (U7), 0aefb458 (U1), 8b696a4f (U3); head tables re-measured in e6a86587.
- Quick tier once, `run-all.sh --group quick --changed-from 03c5edbc`: RUN-ALL-EXIT=1, ten failing suites, all unit
  interactions or pins of deliberately changed lines (b0bacf5f lists each); each rerun once after the fixes, all OK.
- Wave 2 (W2-C procedure walk 4cdf08ee; W2-A/B step Proof and one step block 672973ae, state version 7) merged; head tables
  re-measured in fe18d950. Quick tier once, `--changed-from b0bacf5f`: RUN-ALL-EXIT=0.
- Learning: per-unit suites all passed and still ten suites failed at the first integration run; the cost is in units
  meeting each other (a record type changed under a new caller, two units sharing a card's byte bound, pins of lines
  another unit moved). One quick tier at the integrator found them all in one run, as the test-economy policy intends.
- Next: the live verification is a Battleship game in the owner's Salesforce org (owner, 2026-10-17), case
  `battleship-salesforce`, prefix SLBattle, with its own permission set (the chess run's F9).
