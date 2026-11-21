# Test-writing sessions: how much they ran the built product

Source: `events.jsonl` of the five test-writing sessions under `/Users/dadleet/e2e-runs/ratchet-reworded-20261121-08805f`. Seconds from `run.json`. Events carry no timestamps, so "when" is the command's position among all shell commands (position / total, as a percent).

| Session | Seconds | Shell cmds | Cmds that ran tests or product (share) | (a) acceptance runs | (b) product's own tests | (c) other product probes | (a) exit nonzero / zero | (a) with a failing test shown in output | First (a): position (%) | First (c): position (%) | Distinct src/bin/scripts files read | Distinct docs/README files read | spec.md read cmds | plan.md read cmds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p3R-ticket-due-times-a | 1004.4 | 36 | 16 (44%) | 12 | 3 | 1 | 6 / 6 | 7 | 18 of 36 (50%) | 23 of 36 (64%) | 2 | 5 | 1 | 3 |
| p3R-ticket-due-times-b | 807.0 | 25 | 7 (28%) | 5 | 1 | 1 | 0 / 5 | 1 | 13 of 25 (52%) | 21 of 25 (84%) | 12 | 4 | 3 | 2 |
| p1R-ticket-due-times | 889.1 | 29 | 9 (31%) | 8 | 1 | 0 | 4 / 4 | 7 | 18 of 29 (62%) | none | 12 | 6 | 3 | 3 |
| p1R-ticket-assignment | 941.7 | 31 | 8 (26%) | 6 | 1 | 1 | 2 / 4 | 4 | 19 of 31 (61%) | 14 of 31 (45%) | 5 | 9 | 2 | 2 |
| p1R-stand-in-rules | 746.7 | 29 | 14 (48%) | 9 | 4 | 1 | 4 / 5 | 6 | 14 of 29 (48%) | 11 of 29 (38%) | 0 | 1 | 2 | 2 |
| Total | 4388.9 | 150 | 54 (36%) | 40 | 10 | 4 | 16 / 24 | 25 | | | | | 11 | 12 |

Position of the first command of any of the three kinds ((a), (b) or (c)): p3R-a 11 of 36 (31%), p3R-b 13 of 25 (52%), p1R-due-times 13 of 29 (45%), p1R-assignment 14 of 31 (45%), p1R-stand-in-rules 11 of 29 (38%).

## What the numbers show

- In every session the first acceptance-test run came after 48% to 62% of the shell commands (command 13 to 19, of 25 to 36). Before it, the sessions had run: one run of the product's own tests (p3R-a, p1R-due-times), nothing (p3R-b), or one other product probe (p1R-assignment, p1R-stand-in-rules); the rest of the earlier commands were reading, listing and writing files.
- Across the five sessions, 54 of 150 shell commands (26% to 48% per session) ran tests or the product; 40 of those were runs of the acceptance tests being written, 10 were the product's own tests, 4 were other product probes (one session had none).
- Of the 40 acceptance runs, 16 ended with a nonzero exit code and 24 with zero. In 25 of the 40 the output shows at least one failing test, because the runner scripts (a loop over the manifest in `ratchet/acceptance.json`) can exit 0 even when an item failed. Per session, nonzero exits were 6 of 12, 0 of 5, 4 of 8, 2 of 6 and 4 of 9.
- Product source reading varied widely: 12 distinct files under src/, bin/ or scripts/ in two sessions, 5 in one, 2 in one, 0 in one (p1R-stand-in-rules read only README.md). Reads of docs/ and README.md were 1 to 9 files. Reads of `ratchet/spec.md` were 1 to 3 commands and of `ratchet/plan.md` 2 to 3 commands per session.
- Other product probes (kind c) were 1 command in four sessions and none in p1R-ticket-due-times; the first one came at 38% to 84% of the commands. Two of them (p1R-assignment cmd 14, p1R-stand-in-rules cmd 11) came before the first acceptance run.

## How this was counted

Fields used from `events.jsonl` (all in `$RUNS/<run>/sessions/<session>/events.jsonl`):

- A shell command is an event with `type == "tool_call"` and `toolName == "run_terminal_command"`; its text is `rawInput.command`. File-edit events (`toolName == "search_replace"`) are not counted as commands. The count in the table is the number of such events (the `/bin/zsh -lc` wrapper is stripped before matching).
- The result is the later `type == "tool_call_update"` event with the same `toolCallId`; exit code is `rawOutput.exit_code` (recorded for every command) and the printed output is `rawOutput.output_for_prompt`. (`status` is "failed" for nonzero exit codes, matching `exit_code`.)
- Seconds: `run.json` `sessions[]` entry whose `label` equals the session folder's name after the first dash (`tests-1-1`).
- Events have no timestamps. Position is the 1-based index of the command in the stream.

Classification (I labelled each command by hand after a first automatic pass, because many runs are hidden in `python3 - <<PY` or `node <<NODE` scripts):

- Commands that only write a file (`cat > acceptance/x <<EOF`) were matched on the command head only, so test text inside the written file did not count as a run.
- (a) = ran something in `acceptance/` (`node --test ... acceptance/x.cjs`), including runner scripts that execute every command of `ratchet/acceptance.json` and patch-then-run commands. (b) = `npm test` or `node --test` of the product's own `test/` without an `acceptance/` test file. (c) = other product use: starting the old or new server (`src/server.js`), a `node` script calling `src/` or `bin/tickets.js` through the session's own harness, or an inspector probe loading `src/orders.js`. A command was counted once, in the first matching kind; a command that did both (a) and (b) is in (a).
- Exit code of a command is that of the whole shell line (for `a; b; c`, the last one; for runner scripts, the script's exit, which is 0 even if an item failed). The column "a with a failing test shown in output" instead looks for `not ok`, `✖`, `# fail [1-9]`, `FAIL`, `exit=[1-9]`, `Failing items`, or a per-item nonzero exit in the printed output.
- Distinct files read: paths under `src/`, `bin/`, `scripts/` (code columns) or `docs/`, `README.md` named in a non-write command that also uses `cat`, `sed`, `rg`, `grep`, `nl`, `head`, `tail` or `git show` (so `git show ada051d:src/format.js` counts; `git ls-tree` and `git diff --stat` listings do not). Files in `test/` are not counted here. `rg` was counted as a read when it named a path.
- spec/plan reads: number of commands that name `ratchet/spec.md` or `ratchet/plan.md` with a reading word (a `cat` of both counts in both columns; a `for f in ... ratchet/spec.md` loop and a `cat ratchet/spec.md ratchet/plan.md ratchet/build-*.md` count). Scripts that read the spec programmatically (`readFileSync`) are not counted (2 to 4 per p3R/p1R session).

Ambiguities:

- Runs of the product's tests with the session's own reporter or temp file name (`npm test` with `NODE_OPTIONS=--test-reporter=acceptance/npm-reporter.cjs`, or output redirected to an `acceptance-npm-test.txt` file; p3R-a cmds 19 and 36) were counted as (b), not (a). Counted as (a) instead, p3R-a would have 14 (a) and 1 (b).
- Three p1R-stand-in-rules commands (cmds 23, 25, 28) run the session's own helper `acceptance/project-tests.cjs` against temporary copies of the product with variations of its scripts; counted as (a).
- p1R-ticket-assignment cmd 19 also runs the product's `npm test`; counted once, in (a).
- The numbers of commands in the "tests or product" column exclude `node --check`, `git status`, `ps`, and pure reading or file-writing commands.
- Position as a share of commands is not time: commands vary a lot in length (some runs take up to a minute).
- Helper script: `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/50835528-f438-4c91-9001-f1d0ee5b8f4d/scratchpad/parallel/act2.py` (with the per-command labels hard-coded).
