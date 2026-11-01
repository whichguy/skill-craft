# Release smoke check of skill-craft 2.30.0 and 2.31.0 (2026-11-01)

**Question.** After the E2E harness made Claude on Anthropic the Claude host's default backend
(`2e1f89a8fbb671d150a85ab0ebb9f13bf0f0f02b`), do the documented post-release checks ("Smoke checks after a release" in
`docs/distribution.md`) work on the current release, and does a live ShipLoop session pass on the new default? Consumer: Round 8
of `docs/shiploop-portability-audit-journal.md`, and the owner's decision on what stays open.

**Under test.** Rows 1 to 4: skill-craft 2.30.0 / ShipLoop 1.29.0, release commit `41ee3d89d580fb715fc90994b2361348550698c7`,
the published release until about 10:38 PT. Rows 5 and 6: skill-craft 2.31.0 / ShipLoop 1.30.0, release commit
`5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a`, released by another session at about 10:38 PT while row 3 was running.

## What was run

| # | Check | How | Model |
|---|-------|-----|-------|
| 1 | Native install into a disposable Claude config, then probes on the installed tree (2.30.0) | `probes.sh` of `clean-install-20261101` (`v2.30.0-probes.out`) | none |
| 2 | The documented step 2 as written, gate only (2.30.0) | `run.py --case hello --host claude --source marketplace --preflight-only` (`v2.30.0-gate-refused.txt`) | none |
| 3 | One live `hello` session on the Claude host with no `--backend` and no `--model` | `run.py --case hello --host claude --plugin-dir <export of origin/main plugins/skill-craft> --max-budget-usd 25` (`v2.30.0-claude-default-hello-*.json`) | `claude-sonnet-5-5`, the default |
| 4 | One model call on the owner's real profile, which holds the native install (2.30.0) | `claude -p "... skills that begin with skill-craft:shiploop ..." --max-turns 1` (`v2.30.0-native-skill-list.json`) | `claude-sonnet-5-5` |
| 5 | Row 1 again on 2.31.0 | `probes.sh` (`v2.31.0-probes.out`) | none |
| 6 | Row 2 again on 2.31.0 | same command (`v2.31.0-gate-ok.txt`) | none |

## Results

1. **Passed.** The disposable config installs `skill-craft@whichguy` 2.30.0. The installed tree has no difference from
   `git archive origin/main plugins/skill-craft`, all eight entry scripts are mode 755, `FLOOR = (3, 9)` and the card's
   requirement line are present. On stock Python 3.9.6 in a clean environment `shiploop --help` exits 0 and `workspace start`
   exits 0 with a 13,758-byte packet. With `python3` absent all five hook entries exit 0 with no output. In the Python 3.7.3
   container the hooks are silent and `shiploop --help` exits 2 with the one-line requirement.
2. **Refused, as designed.** The gate stopped the documented command before anything started: `origin/main` carried one
   unreleased change note, `changes/shiploop/init-refuses-an-empty-non-git-folder.md`, from another session. The harness refuses
   because what it would test is then not what the marketplace serves. The served payload was still byte-identical to the 2.30.0
   release commit (`git diff --stat 41ee3d89 origin/main -- plugins/skill-craft .claude-plugin catalog/skill-craft-plugin.json`
   printed nothing), so row 3 ran that export through `--plugin-dir` and says so here.
3. **Passed, every verdict.** `result.json` records `backend: anthropic` and `model: claude-sonnet-5-5` with neither flag on the
   command line. Verdicts: invoked `/skill-craft:shiploop`, plugin (tree digest `3efc9db89059`, skill-craft 2.30.0 / ShipLoop
   1.29.0), process (rc 0, 1239.8 s, 280 turns, $5.6854), shiploop `done` (23 of 23 stages accepted), committed (HEAD `4896f37f`
   with 6 files, 15 commits, 0 uncommitted), and both request checks (`hello.py` prints `Hello, world!`;
   `python3 -m unittest -q`). Four ShipLoop commands exited 2 and were designed gates, not faults: three `--check-only` checks
   (a step path with no expectation, an open plan assumption due at the item, a criterion without its own focused test ID) and
   one `improve-pass` on an already-imported stage; the run went on to `done` after each. Asked a person 0, model glue 0.
   Cell context: the `hello` rows of the `claude` / `claude-sonnet-5-5` cell (21 with this one) range from 188 to 364 turns and
   from $3.88 to $7.65 over the last six; this run's 280 turns and $5.69 are inside that range, and the 2.27.3 run of the same
   morning (969.2 s, 188 turns, $4.13) is at its low end. One run each, so no change in cost is claimed.
4. **Passed.** The model listed `skill-craft:shiploop`, `skill-craft:shiploop-e2e-audit` and `skill-craft:shiploop-run-review`
   (1 turn, $0.1302): a model session on a native Claude install sees the ShipLoop skills.
5. **Passed.** The same probes on 2.31.0: tree identical to the published tree, eight modes 755, stock 3.9.6 clean-environment
   `--help` exit 0 and `workspace start` exit 0 (13,826 bytes), five hooks silent without `python3`, the 3.7.3 container as in row 1.
6. **Passed.** After the other session released 2.31.0, the documented command passed its gate: `origin/main 4a6c06c4 publishes
   skill-craft 2.31.0 / ShipLoop 1.30.0; ... unreleased notes: 0; main CI: success; OK`.

## Evidence boundary

- Row 3 is the only live ShipLoop session, and it ran 2.30.0, not 2.31.0. It loaded an export through `--plugin-dir` (the route
  `--source marketplace` also uses on the Claude host, minus its gate), so it is not a native Claude install. No live session
  has run 2.31.0 from this check; rows 5 and 6 cover its install and its gate only.
- Row 3 is one run on a machine at load average 106 / 121 / 98 on 18 CPUs when it started, so 1239.8 s is not a speed figure.
- Row 4 used the owner's own profile, with its other plugins and hooks, and started no run. It shows discoverability of a native
  install; it is not a clean-consumer check.
- Total model spend: $5.6854 (row 3) + $0.1302 (row 4) = $5.8156.
- `py39-apparatus-probe.txt` is a side check, not a release check: the 47 E2E-apparatus suites under macOS Python 3.9.6. It
  explains the "write to closed file" failures of Round 2 of the journal as a knock-on of `os.waitid`, which macOS Python
  lacks (journal Round 8, F23). The apparatus is declared 3.10+ and stays out of the 3.9 CI job.
- Not covered: Windows (declared unsupported in `docs/distribution.md`: the scripts use `fcntl`), WSL (Linux, untested),
  Python 3.8, a Mac without the Command Line Tools, a native Claude install with its own login, and Cursor, which holds only a
  local copy of skill-craft 1.21.0 (dated 2026-10-05) and an old `claude-craft` marketplace entry.
