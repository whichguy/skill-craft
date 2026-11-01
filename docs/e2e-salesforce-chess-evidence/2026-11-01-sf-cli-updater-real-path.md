# 2026-11-01: the Salesforce CLI updater, proved on its real path

The owner asked that the Salesforce CLI be kept current ("we just want to make sure we update it all the time"). The CLI is an npm
global under Homebrew's node (`/opt/homebrew/lib/node_modules/@salesforce/cli`), so `brew upgrade` never touches it. The job is
`~/.claude/tools/sf-cli-update-cron.sh` (cron, daily 09:20 local; regression suite `sf-cli-update-cron-tests.sh` beside it, which
runs against fake `npm`, `sf` and `pgrep`). It installs npm's `latest` tag when it differs from the installed version, waits while
any `sf` command runs, then runs `sf plugins update`; it notifies only on failure. Those two files live outside this repository.

On 2026-11-01 the installed CLI (2.156.8) already was `latest`, so the job had never installed anything for real. This is the real
run: real npm 12.2.1, real `sf`, real registry, against a temporary npm prefix holding a week-old CLI (2.156.5), so the owner's
install was not touched. `NPM_CONFIG_PREFIX` pointed at the prefix through a symlink without a UUID in its path, because `npm root -g`
prints UUID-shaped path segments as `***` (a first attempt under a UUID-named scratch folder failed for that reason: a test artifact).

## Run 1, before the fix: the install worked and the script called it a failure

```
2026-11-01 12:53:06: installing @salesforce/cli@2.156.8 (installed 2.156.5)
2026-11-01 12:53:14: ERROR — sf --version failed after the install: @salesforce/cli/2.156.8 darwin-arm64 node-v26.12.1
updater exit=4 (8 s)
version there now: 2.156.8
again (a no-op):  current: @salesforce/cli 2.156.8 is npm's latest      exit=0
the updated CLI, read-only against the real login: sf org list --json -> status 0, 2 orgs, alias de: True
your real install: 2.156.8, package.json mtime unchanged: yes
files against the owner's real 2.156.8 install: 21 files differ (6 only in his, 15 only in the upgraded one), all inside third-party nested dependencies
```

Cause: `version_line="$("$SF" --version 2>&1 | head -n 1)"` under `set -o pipefail`. The real CLI prints more than one line, `head`
exits after the first, `sf` dies of SIGPIPE (141), and the pipeline reads as a failure. In production every good update would have
been reported as an error and `sf plugins update` skipped. The fakes printed one line, so the 10 tests passed.

## The regression test, fail-first

The fake `sf --version` now prints its version line, pauses 0.3 s and prints two more lines. Against the unfixed script:

```
not ok 2 - newer and idle: installs latest, then updates plugins
not ok 8 - plugin update fails: exit 4 after the CLI moved
8 of 10 passed
```

The fix reads all the output and keeps its first line:

```
-version_line="$("$SF" --version 2>&1 | head -n 1)" || fail 4 "sf --version failed after the install: $version_line"
-log "updated: $installed -> $latest ($version_line)"
+version_out="$("$SF" --version 2>&1)" || fail 4 "sf --version failed after the install: ${version_out%%$'\n'*}"
+log "updated: $installed -> $latest (${version_out%%$'\n'*})"
```

After it: `10 of 10 passed`. No other `head` pipeline is left in the script.

## Run 2, after the fix

```
== back to a week-old CLI in the temporary prefix
now: 2.156.5
== the real updater, real npm and sf
2026-11-01 12:55:25: installing @salesforce/cli@2.156.8 (installed 2.156.5)
2026-11-01 12:55:32: updated: 2.156.5 -> 2.156.8 (@salesforce/cli/2.156.8 darwin-arm64 node-v26.12.1)
2026-11-01 12:55:33: plugins: @salesforce/cli: Updating plugins... done
updater exit=0 (9 s)
version there now: 2.156.8
== again: must be a no-op
2026-11-01 12:55:33: current: @salesforce/cli 2.156.8 is npm's latest
updater exit=0
== the updated CLI, read-only against the real login
  0 2 orgs, alias de: True
== your real install: 2.156.8, untouched: yes
```

## Other facts established on the way

- npm 12.2.1 skips install scripts for global installs (`npm warn install-scripts ... --allow-scripts=@salesforce/cli,yarn,protobufjs`),
  and `npm config get allow-scripts` is unset. The scripts that would have run: the CLI's `preinstall` (`scripts/preinstall.js`) only
  refuses to install over the legacy `sfdx-cli` 7.x; yarn's `preinstall` runs its own script with the output discarded and errors ignored; protobufjs's `postinstall` warns about a
  version scheme. None creates a file, so skipping them changes nothing, and the updater passes no flag for them.
- An in-place upgrade (2.156.5 to 2.156.8) differs from the owner's fresh 2.156.8 install by 21 files (6 only in his, 15 only in the
  upgraded one; the diff output has 25 lines with its hunk headers), all in third-party nested dependencies (`ink`'s nested `cli-truncate`, `es-toolkit` compat files, `@inquirer/core`'s `__probe` files); the CLI works.
- npm's dist-tags on 2026-11-01: `latest` 2.156.8, `latest-rc` 2.157.7, `nightly` 2.158.3 (the version list ends at 2.158.3). The job
  follows `latest`, the stable channel, so its first real update comes when `latest` moves.
- The existing scheduled task `nightly-cli-update` (02:06 daily) covers claude, grok, codex, cursor and antigravity, not this CLI.
- The success notification (a macOS banner) was removed from the job: it notifies only on failure, because a banner is a popup and
  the owner's complaint was popups.
