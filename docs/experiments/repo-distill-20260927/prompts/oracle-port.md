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

The oracle reaches the program only through its public interfaces, given in
environment variables (both are set; use the ones this program has):

- `APP_CMD`: the shell command that runs the program's command line (for
  this original: `{APP_CMD_ORIGINAL}`). The oracle appends arguments and may
  write standard input; it checks standard output, standard error, exit
  status and files. For a server, each test starts it on a free port, waits
  until it answers (fail after 10 seconds), and stops it afterwards; never
  assume a fixed port or leave a process running.
- `APP_MODULE`: the absolute path of the file a consumer gets when importing
  the package (for this original: `{APP_MODULE_ORIGINAL}`). For a library,
  the oracle loads it with `await import(pathToFileURL(process.env.APP_MODULE))`
  and uses only its public exports, as a consumer would.

Each test creates its own temporary files and cleans up after itself.

## Rules

- Test observable behaviour through the command line, HTTP, files and output:
  the same behaviours the original tests check, reached from outside. A unit
  test of an internal function becomes a check of the user-visible behaviour
  that function produces, when there is one.
- Do not assert on branding (product name, logos, banner text, or any value
  that embeds the product's name, such as a default path) or on exact log
  wording; the rebuild uses another name. Assert the value's presence and
  shape instead. Do assert on everything the
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

Run `APP_CMD='{APP_CMD_ORIGINAL}' APP_MODULE='{APP_MODULE_ORIGINAL}' node --test {ORACLE_DIR}` and fix the
oracle until every test passes against the original. Check that `MAPPING.md`
lists every original test. End with one line:
`ORACLE WRITTEN: <oracle test count> tests, <mapped> mapped, <not observable> not observable, <excluded> excluded`.
