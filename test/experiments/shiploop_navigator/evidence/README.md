# Recorded experiment evidence

These are archived observations from the September 14, 2026 pilots, not live
state or executable callbacks. `<SOURCE_CHECKOUT>` and `<INITIAL_TRIAL>` path
placeholders preserve relationships without binding the archive to a temp path.
The explicit repeat uses `<EXPLICIT_TRIAL>`.

- `summary.json`: inspected candidate commits, fixed-oracle totals, specification
  preservation, and accepted action/next-state observations for all four trials.
- `initial-*.md`, `explicit-*.md`: final source, tests, plan, commit message and
  worker records. Worker confidence is preserved as historical evidence, including
  the initial claim of specification compliance later found ambiguous.
- `packet-*.md`: the six primary inputs exported through public CLI `next`.
- `cold-a.json`, `cold-b.json`: raw primary interpretation responses with paths
  normalized. Each panel handled three cases in one fresh context.
- `cold-assessment.json`: parent semantic grading against preregistered criteria;
  identity and two proposed transitions were checked by code on pure state copies.
- `mechanical.json`: final compact-run generated-walk and subprocess-race evidence.
- `mechanical-integration.json`: compact rerun on the newer discovery-policy
  integration revision, without repeating the live-agent comparison.
- `calibration.md`: reference used to check that the prewritten oracle can pass.
- `supplemental.json`: six post-review tuple/float/boolean checks on each unchanged
  candidate, kept separate from the original 210-case comparison.

Initial exploratory readers received internal API-rendered packets with a relative
executable locator; those trials are excluded from primary cold results. Their
responses were not retained here. The defect was corrected in the packet exporter
and fresh readers repeated the primary cases. This is a disclosed preparation
amendment, not a production navigator defect.

The full 210-row oracle outputs remain ignored local run artifacts. The fixed
seed, oracle source and four candidate snapshots allow regenerating those checks.
No candidate snapshot is installed as a production skill or imported by CI.
