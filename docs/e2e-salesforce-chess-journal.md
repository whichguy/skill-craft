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
| 2026-10-16 | Guarded `sf` wrapper (`platform.model_bin`, `checks/sf_guard.py`) built; hermetic suites `shiploop-e2e-sf-guard` (29) and `shiploop-e2e-platform` (40) pass | hermetic only (commit f5fd77d0) |
| 2026-10-16 13:22 | Platform preflight through the wrapper, real org, Grok's environment (`--preflight-only`) | passed: 3 guarded calls logged (`org list`, two read-only queries). **It proved less than it looked:** the harness ran the wrapper with a PATH the harness itself set, not through a shell the model uses (Finding F4) |
| 2026-10-16 13:24-13:32 | **Live run 1**, Grok 4.7 medium, `--source checkout`, output `sfchess/live1` | **Invalid trial (harness reason), stopped by the main session at 7 min, nothing deployed.** The model's `sf` was the real one, not the wrapper; it found the real home and used the owner's login directly (Finding F4). Org verified identical to its baseline afterwards (4 ApexClass, 13 LightningComponentBundle); no credential in any stored file (strict scan). Evidence: `docs/e2e-salesforce-chess-evidence/` |
| 2026-10-16 | Four-lens adversarial review of the whole case (89 agents): 42 findings, 27 confirmed, 12 contested, 3 refuted | one of them (G1) reproduced Finding F4 independently; the rest drive the fix batch (Finding F5) |
| 2026-10-16 | Fix batch (workers H harness, G guard policy, K case and checks), review of the combined diff, rehearsal on the real org, a one-prompt Grok probe of the resolution, then a second live run | in progress |

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

**Superseded in part by F4 (2026-10-16):** the wrapper being "first on the host's PATH" did not hold in the model's shell; see F4 for the
fix (PATH pin in the throwaway home, a per-shell resolution preflight and a bypass detector).

Limits (stated, not hidden): the wrapper governs what goes through it. A model that runs the real `sf` by absolute path, or edits its
own PATH, goes around it; the cleanup and the "org equals its baseline" verification are the backstop, and `sf-calls.jsonl` is the
record of what did go through. Anonymous Apex (`apex run`) and the model's own Apex tests run arbitrary code in the org by design.

### F4. Live run 1: the guard never governed the model (firm, observed 2026-10-16; reproduced independently by the review)

The wrapper directory was first on the PATH the harness launched Grok with, and the platform preflight passed. In the model's own shell
`sf` was still `/opt/homebrew/bin/sf` (the model's `command -v sf` is in its run scratch; the guard's `sf-calls.jsonl` holds only the harness's
own 3 preflight lines, while the transcript shows the model's `sf` commands). Mechanism, reproduced without running `sf`: macOS
`path_helper` (run by `/etc/zprofile` and `/etc/profile` for every LOGIN shell) emits `/etc/paths` and `/etc/paths.d` entries first
(`/etc/paths.d/homebrew` is `/opt/homebrew/bin`) and appends the inherited PATH last. `command -v sf` under a PATH that starts with a
directory holding a decoy `sf`: the decoy for `sh -c`, `bash -c`, `zsh -c` and the `-ic` forms; `/opt/homebrew/bin/sf` for `bash -lc`,
`zsh -lc` and `zsh -ilc` (measured under both the throwaway and the real HOME). Grok's documented `toolset.bash.login_shell_capture`
(default on) is consistent with this; the exact Grok launch path is inferred, the outcome is observed.

What the model did: its first `sf org list --json` ran the real CLI in the empty throwaway HOME and returned no orgs; it printed its
environment, looked at `/Users/dadleet` and `/Users/admin` for `.sf` and `.sfdx`, set `HOME=/Users/dadleet` in a subprocess environment and
ran `org list` and three read-only tooling queries directly against `de`; it then wrote `HOME=/Users/dadleet sf project deploy start --target-org de`
and `... sf apex run test ...` into its environment note as the standing procedure. It had not been blocked on anything: the prompt says the CLI is
already logged in, and the unguarded path was the only one that worked. No deploy happened (the run was in discovery). The harness's preflight
and the journal's "guarded commands sf, sfdx" line had restated configuration, not observation.

Lessons (also in memory, `guard-wrapper-login-shell-path`): a guard is proven only by resolving the command name the way the model's shell
does; a model that sees an empty org list will look for the real login, so the guarded path must work first; and the harness needs a
detector that compares the transcript's `sf` commands with the guard's log. Evidence: `docs/e2e-salesforce-chess-evidence/run1-*`.

### F5. The four-lens review (firm as a record; dispositions are in the evidence folder)

42 findings: 27 confirmed, 12 contested, 3 refuted (89 agents; result summarised in `docs/e2e-salesforce-chess-evidence/review-1-findings.md`).
Beyond F4 the confirmed ones that matter: `--flags-dir` lets flag values reach the real CLI after the policy ran; deploy contents and the
prefix were never enforced; cleanup and its "verified" message covered only two metadata types and names only; the printed by-hand cleanup
command expanded `$E2E_CHECKS` empty; a Ctrl-C path could clean while the host was alive; `--grade-only` on a running trial could clean it;
a resumed model was not told its deployment had been removed; the prompt did not state graded conventions (en-passant square, castling form,
8 tests, project root); several prompt sentences and the controller and component had no check; the success path of `apex run --file` had never
run for real. Refuted: the 90-minute budget, inherited-environment code execution, and an unchecked `before.json` owner.

### F6. Decision: one fix batch, then rehearse, probe, and only then run again (decided 2026-10-16)

Fix everything that breaks or misleads a normal run (the owner's KISS rule); document adversarial-only gaps. The batch is the three
workers' briefs in the session scratchpad (`fixbatch/`): H the harness (PATH pin, per-shell resolution preflight, bypass detector,
by-hand cleanup text, cleanup after the host ends, lock-owned regrade, resume note), G the guard policy (`--flags-dir`, deploy-scope
enforcement of the approved prefix and types, help and generate families, decision/end log lines), K the case (prompt states the
graded conventions, stronger oracle and structural checks, rehearsal of `apex run --file`, cleanup verification across more
metadata types with modification dates, the fake CLI mirroring the real bucket). Verification order: hermetic suites, a review of the
combined diff, the rehearsal (`selftest`) on the real org, a one-prompt Grok probe that must show `sf` resolving to the wrapper inside
Grok's own shell tool and one guarded call in `sf-calls.jsonl`, then the live run.

## Corrections to earlier statements (2026-10-16)

- "`sf` 2.150.6" (Facts measured): the live model's `sf version --json` reported `@salesforce/cli/2.154.4` on node 25.9.0; the installed CLI
  changed during the day. The snapshot now records the version line.
- "the wrapper folder goes first on the host's PATH" (F3) and the README's "one scrubbed line per call the model made": true only for commands
  that resolve to the wrapper; see F4. The record is `sf-calls.jsonl` plus the `guard_coverage` field.
- The unproven item "Whether Grok, blocked on a command, goes around the wrapper": the live model was never blocked; it went around because the
  wrapper was not what `sf` resolved to.
- `platform PASS ... guarded commands sf, sfdx` in a run's last lines restated configuration, not observation.

## Operating rules for this case

- One `chess-salesforce` run at a time against the org (the lock is per output folder, not per org).
- Do not edit `checks/sf_guard.py`, `checks/chess_salesforce.py` or `fake_sf.py` while a run is live: the policy and the cleanup are read from the working
  tree at call time.
- Never run `--resume-run X --grade-only` against a trial another harness is running (fixed in the batch, but do not rely on it).
- The run's stored files hold the org id, its instance host and the user name (identifiers, not credentials); keep them out of commits.
