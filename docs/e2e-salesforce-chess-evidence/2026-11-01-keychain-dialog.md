# 2026-11-01: the "Keychain Not Found" dialog is the Salesforce CLI in a throwaway HOME

The owner's screenshot (`2026-11-01-keychain-not-found-dialog.png`): a macOS dialog "Keychain Not Found. A keychain cannot be
found to store "local"." with the generic `exec` icon and the buttons Cancel and Reset To Defaults, seen repeatedly while E2E
runs were going.

## What names "local"

- The login keychain's only item named `local` anywhere (generic or internet password, as account, service or label):
  `security find-generic-password -a local` gives `"svce"="sfdx"`, `"acct"="local"`, label `sfdx`. Read as metadata only (no `-w`/`-g`).
- `@salesforce/core` 9.4.1 inside `/opt/homebrew/lib/node_modules/@salesforce/cli`: `lib/crypto/crypto.js` has `const ACCOUNT = 'local'`;
  `lib/crypto/keyChain.js` `retrieveKeychain` returns the Darwin native keychain on macOS unless `SF_USE_GENERIC_UNIX_KEYCHAIN` is
  true ("OSX can use the generic keychain. This is useful when running under an automation user."), and the generic store is
  `key.json` in `Global.DIR` (`~/.sfdx`). The native store calls `/usr/bin/security`, a bare executable, which explains the `exec` icon.
- Chromium is not the source: the Playwright that `checks/battleship_ui_browser.cjs` falls back to
  (`~/.cache/codex-runtimes/codex-primary-runtime/.../playwright-core` 1.62.1) launches Chromium with `--password-store=basic` and
  `--use-mock-keychain`, and Chromium's item would be named "Chromium Safe Storage" anyway.

## Where the real CLI ran in a throwaway HOME (read-only look at another session's runs)

The start-route probe (`~/e2e-runs-startroute/*/trials/*`, session of `test/shiploop_e2e/start_route.py`) launches Codex through
`run.py` (`host.env(out / "home")`) with the `sf-ui` prompt but no `platform.model_bin`, so the model's `sf` is the real
`/opt/homebrew/bin/sf` with HOME = `<trial>/home`. Commands that ran the CLI (not `command -v sf`, not the prompt text), counted
per trial across all start-route folders on 2026-11-01: `sf --version` 17 trials (no key needed), `sf data` 7, `sf org` 5,
`sf apex` 3, `sf alias` 1.

- `20261101/017-T1-sf-ui-03-a2`: two `sf data query --target-org de ...` processes still in state `S` at 00:54 and 00:45 in the
  model's own `ps`, then the command ended with exit 130 (interrupted).
- `20261101/005-C-sf-ui-38-a2`: the same `sf data query` ended with exit 130.
- `20261101/055-T1-sf-ui-18-a1`: `sf org list metadata ... --target-org de --json` printed the CLI's first-run notice (a new HOME)
  and failed; a sibling ended with exit 130.

The regular Salesforce cases route the model's `sf` through the guard wrapper (real HOME); the three UI/SF runs of 2026-10-31
(`~/e2e-runs-hostonly/20261031/ui-live-2`, `ui-live-3`, `sf-live-2`) record `guard_coverage.direct_sf_commands: 0`.

## After the change (hosts.THROWAWAY_HOME_ENV)

- Real CLI, fresh throwaway HOME with its XDG folders, `SF_USE_GENERIC_UNIX_KEYCHAIN=true` (telemetry off):
  `sf data query --target-org de --query 'SELECT Id FROM Organization LIMIT 1' --json` -> exit 2 after 2 s,
  `NamedOrgNotFoundError` "No authorization information found for de."; `<home>/.sfdx/key.json` (mode 600) was created. No dialog.
- The wrapper's path: the variable set, then `env -u SF_USE_GENERIC_UNIX_KEYCHAIN HOME=$HOME sf org list --json` -> status 0
  after 3 s, 2 orgs, alias `de`, `Connected`; `~/.sfdx/key.json` still does not exist (the real CLI read the real keychain).
- `test/shiploop-e2e-platform.test.py`: 169 tests OK (305 s), including the new assertions that the model's launch carries the
  variable and the wrapper's command does not.

Not measured: what "Reset To Defaults" does when the asking process has a throwaway HOME (Cancel is the safe answer; the CLI then
fails at once).

## The check, run live (2026-11-01, after the change)

`keychain-dialog-check/check_dialog.py <checkout> <scratch dir holding windows_of.js>` builds the throwaway-HOME environment with
the harness's own code and looks for a dialog with no permission (a SecurityAgent process, a waiting `security
*-generic-password`, the windows SecurityAgent owns). Its output on 2026-11-01 is `keychain-dialog-check/output-2026-11-01.txt`:
the control (old behaviour) raised the dialog in 2.2 s with its window on screen (425x172, layer 1000) and killing the command's
process group dismissed it 11.1 s later; with the change none of the five commands the trials ran raised one; the guarded
wrapper listed 2 orgs with no dialog; the installed Google Chrome launched through Playwright (the UI check's route) raised none
in the real HOME or in a throwaway HOME. Rerun it against any harness checkout before trusting that a run will not raise the dialog.
