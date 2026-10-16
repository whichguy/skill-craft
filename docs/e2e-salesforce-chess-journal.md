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
- Grok and Codex run in a throwaway HOME, so they cannot see the owner's `sf` login. The case first carried `home_links`
  (`.sfdx`, `.sf`), symlinked into that HOME only for this case, like the existing Grok `auth.json` link. Nothing is typed,
  copied or stored. A model with a shell can read the linked login: the owner chose Grok knowing the link is required.
  **Superseded 2026-10-16 (see Findings): the links do not work for `sf`; the case uses a guarded wrapper (`model_bin`).**

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
| 2026-10-16 | Rehearsal (`chess_salesforce.py selftest`) on the real org, real HOME | passed: probe class and test deployed, tested and removed; the org was identical to its 4 ApexClass / 13 LightningComponentBundle baseline afterwards |
| 2026-10-16 | Under Grok's throwaway HOME with `~/.sfdx` and `~/.sf` linked, `sf org list --json` | hung (measured by the main session); real HOME works. `home_links` dropped from the case |
| 2026-10-16 | Guarded `sf` wrapper (`platform.model_bin`, `checks/sf_guard.py`) built; hermetic suites `shiploop-e2e-sf-guard` (29) and `shiploop-e2e-platform` (40) pass | hermetic only; not yet run with the real `sf` or a model |
| | Preflight through the wrapper on the real org (`--preflight-only --case chess-salesforce`) | not yet run |
| | Live run, Grok 4.7 medium | not yet run |

## Unproven (update when a run shows it)

- The destructive deploy of Apex classes and an LWC bundle on a Developer Edition org (the rehearsal tests exactly this).
- Whether `sf apex run test --class-names X --synchronous` and `sf apex run --file` return the JSON shapes the checks parse
  (shapes were written from the CLI's documented output, not captured, because capturing them needs a deploy).
- ~~Whether Grok's isolated HOME with the two linked directories can use the `sf` login~~ Answered 2026-10-16: it cannot (Findings).
- That the real `sf` accepts every command the guard allows with the spellings Grok uses (the guard is tested against the fake only).
- Whether Grok, blocked on a command, goes around the wrapper (an absolute path to `sf`, or its own PATH): the isolated HOME is
  hygiene and the policy lives in the wrapper only for commands that go through it. `sf-calls.jsonl` shows the calls that did.
- Whether 90 minutes is enough for this build.

## Findings

### F1. `home_links` cannot give an isolated-HOME model the `sf` login (firm, measured 2026-10-16)

Under the throwaway HOME that Grok and Codex use, `sf org list --json` hangs even with `~/.sfdx` and `~/.sf` symlinked into it. The CLI
keeps its decryption key in the macOS keychain (an item named `sfdx` exists), and a different HOME hides it (measured: the hang; the keychain cause is the
main session's reading, not separately proven). The same command works with the real HOME. Evidence: the main session's run of the command under the isolated HOME and under
the real one, and the passing `selftest` rehearsal below (real HOME).

### F2. The rehearsal passed on the real org (firm, 2026-10-16)

`chess_salesforce.py selftest --org de --prefix SLChess` deployed a trivial `SLChessProbe` and `SLChessProbeTest`, ran the test,
and removed them by a named-member destructive deploy; the ApexClass and LightningComponentBundle name sets afterwards equalled the
4 / 13 baseline. That proves the real-CLI steps of snapshot, deploy, query, test and cleanup (the earlier "Unproven" items for the
destructive deploy).

### F3. Decision: a guarded wrapper instead of `home_links` (decided 2026-10-16)

The isolated HOME is environment hygiene, not a security boundary (the same OS user can read any absolute path), so a model that needs
the login should get a command that runs the real `sf` with the real HOME and enforces policy. The harness gained a generic
`platform.model_bin` (`{name: shell command}`): it writes `<output>/platform/bin/<name>` (`exec env HOME=<real> <command> "$@"`, the
`E2E_*` variables baked in) and puts the folder first on the host's PATH and on the preflight's PATH. The Salesforce policy is
`checks/sf_guard.py`: default deny; denies credential and configuration commands (`org display|open|login|logout|create|delete`,
`auth`, `config`, `alias`, `plugins`, `update`), data writes, `project delete`, destructive or wildcard deploys, auth URLs and a bare
`--`; pins every org-talking command to `--target-org de`; passes `--version`, `help`, `project generate`, `lightning generate` and
`org list`; scrubs the real `sf`'s output; logs one scrubbed line per call to `<output>/platform/sf-calls.jsonl`. A second wrapper,
`sfdx`, denies everything (the Salesforce CLI package ships it, and it would otherwise bypass the policy). `home_links` stays in
`run.py` as a generic feature with its tests; the case no longer lists it. Evidence: `test/shiploop-e2e-sf-guard.test.py`,
`test/shiploop-e2e-platform.test.py` (class `ModelBinTest`).

Limits (stated, not hidden): the wrapper governs what goes through it. A model that runs the real `sf` by absolute path, or edits its
own PATH, goes around it; the cleanup and the "org equals its baseline" verification are the backstop, and `sf-calls.jsonl` is the
record of what did go through. Anonymous Apex (`apex run`) and the model's own Apex tests run arbitrary code in the org by design.
