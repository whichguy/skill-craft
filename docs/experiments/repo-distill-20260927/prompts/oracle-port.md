# Port this repository's tests into a black-box oracle

**Intent.** We will rebuild this program from a written specification, with a
completely different internal design, and need an independent check of
whether the rebuild behaves like the original. Your oracle is that check. It
must test only what a user or client can observe, so any correct rebuild
passes it and an incorrect one fails.

**Your input.** The repository in the current directory, including its tests.
Do not use the web.

**Your output.** Create the directory `{ORACLE_DIR}` containing:

- one or more `*.test.mjs` files for Node's built-in test runner
  (`node --test {ORACLE_DIR}`), using only Node built-ins (`node:test`,
  `node:assert`, `node:child_process`, `fetch`, `node:fs`, `node:os`, ...).
  No npm packages, no imports from this repository;
- `MAPPING.md`: a table with one row per original test (file and test name):
  the oracle test(s) that cover it, `not observable`, or `excluded`, each
  with the reason.

Change nothing outside `{ORACLE_DIR}`.

## How the oracle reaches the program

The program under test is started only through its command line. The
environment variable `APP_CMD` holds the shell command that starts it (for
this original: `{APP_CMD_ORIGINAL}`); the oracle appends the arguments it
needs (data files, port, options). Each test that needs a running program
creates its own temporary files, starts the program on a free port, waits
until it answers (fail after 10 seconds), and stops it afterwards. Never assume
a fixed port or leave a process running.

## Rules

- Test observable behaviour through the command line, HTTP, files and output:
  the same behaviours the original tests check, reached from outside. A unit
  test of an internal function becomes a check of the user-visible behaviour
  that function produces, when there is one.
- Do not assert on branding (product name, logos, banner text) or on exact
  log wording; the rebuild uses another name. Do assert on everything the
  interface promises: status codes, bodies, headers, ordering, persistence.
- Keep one oracle test per original behaviour where you can, named so a
  failure says which behaviour broke.
- The original's observed behaviour is the truth, not its tests or docs. An
  original test that is broken or fails against the original is not ported;
  list it in `MAPPING.md` as `excluded` with the reason.
- Every check must prove the behaviour happened, not only that something is
  absent: a program that answers 404 to everything must fail nearly every
  check. Pair a negative check (unknown id → 404) with the positive one it
  guards.

## Before you finish: grade your own result

Run `APP_CMD='{APP_CMD_ORIGINAL}' node --test {ORACLE_DIR}` and fix the
oracle until every test passes against the original. Check that `MAPPING.md`
lists every original test. End with one line:
`ORACLE WRITTEN: <oracle test count> tests, <mapped> mapped, <not observable> not observable, <excluded> excluded`.
