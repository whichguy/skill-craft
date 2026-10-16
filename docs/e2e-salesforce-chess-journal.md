# Salesforce chess E2E: journal

Owner request (2026-10-10, recorded; 2026-10-16, go): have ShipLoop build one of the example apps in the owner's Salesforce
Developer Edition org and test it there. This file is the living record of the case, its safety design, each run and what each
run showed. Judge a run by ShipLoop's SDLC fidelity, not by the chess app (see the example-apps rule).

## Decisions (owner, 2026-10-16)

| Question | Answer |
|---|---|
| Deploy to the org? | Yes: alias `de`, prefix `SLChess`, remove everything afterwards |
| Host | Grok 4.7, medium effort |
| Scope | Chess rules engine in Apex, Apex tests, a simple Lightning web component board |

## Facts measured before building (read-only, 2026-10-16)

- `sf` 2.150.6; org `de` (Developer Edition) is connected and the default; its API version is 68.0.
- Baseline: 4 ApexClass, 13 LightningComponentBundle, nothing named `SLChess*` / `slChess*`.
- `sf org display --json` returns the org's `accessToken`. The harness therefore never calls it; connectedStatus comes from
  `sf org list --json`, and every stored output is scrubbed.
- Grok and Codex run in a throwaway HOME, so they cannot see the owner's `sf` login. The case carries `home_links`
  (`.sfdx`, `.sf`), symlinked into that HOME only for this case, like the existing Grok `auth.json` link. Nothing is typed,
  copied or stored. A model with a shell can read the linked login: the owner chose Grok knowing the link is required.

## Design

- **Independent oracle (S-9).** The harness runs its own anonymous Apex against the interface in the prompt and compares with the
  published perft counts of six standard positions (start 20/400, Kiwipete 48, position 3 14/191, position 4 6/264, position 5
  44/1486, a castling position 26), plus fool's mate, scholar's mate, a stalemate, an illegal move and the en-passant field.
  The model's own tests count too (`tests`: at least 8, all passing in the org), but they are not the oracle.
- **Cleanup is part of the case.** `snapshot` records the whole org's ApexClass and LightningComponentBundle names; `cleanup` removes
  only names with the exact case-sensitive prefix that are absent from the snapshot, by a destructive deploy listing named members
  (never a wildcard), and verifies the org equals the snapshot. It runs in a `finally` after grading. Preflight refuses an org that
  already holds prefixed items.
- **Rehearsal before the model run.** `chess_salesforce.py selftest` deploys a one-class probe (and a one-component probe), runs its
  test, and cleans up, to prove every real-CLI step on the real org before the model gets near it.

## Status

| Date | Event | Result |
|---|---|---|
| 2026-10-16 | Case, checks, fake `sf` and hermetic tests built (worker A); platform hooks in `run.py` (worker B) | see the commit |
| | Rehearsal (`selftest`) on the real org | not yet run |
| | Live run, Grok 4.7 medium | not yet run |

## Unproven (update when a run shows it)

- The destructive deploy of Apex classes and an LWC bundle on a Developer Edition org (the rehearsal tests exactly this).
- Whether `sf apex run test --class-names X --synchronous` and `sf apex run --file` return the JSON shapes the checks parse
  (shapes were written from the CLI's documented output, not captured, because capturing them needs a deploy).
- Whether Grok's isolated HOME with the two linked directories can use the `sf` login (the macOS keychain may need the real HOME).
- Whether 90 minutes is enough for this build.
