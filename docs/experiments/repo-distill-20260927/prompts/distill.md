# Distill a specification from this repository

**Intent.** Someone who has never seen this repository must be able to
understand what it does, and to build a program that behaves the same way to
every user and client, from your specification alone. They will never see the
source code, the tests, the README or the repository's name.

**Your input.** The repository in the current directory. Read the source,
tests, documentation, configuration and examples. You may run it and its tests
to confirm a behaviour. Do not use the web.

**Your output.** Write exactly one file: `{SPEC_PATH}`. Change nothing else.

## What the specification must contain

1. **Purpose**: what the program is for, in a few sentences.
2. **Runtime and launch contract**: the platform and minimum version, how the
   program is installed and started (command, arguments, environment
   variables), and what it prints when it starts, fails or stops. The product
   is called **{PRODUCT_NAME}**; use that name everywhere and never the
   original name, owner or URL.
3. **Public interface (pinned)**: everything a user or client can observe and
   rely on: every command-line option, every HTTP method and route, request and
   response shapes, status codes, headers, query parameters and their
   combinations, file formats read and written, pages and what they show,
   error behaviour. Be exact: names, defaults, types, ordering, edge cases.
4. **Behaviour claims**: numbered `D-1`, `D-2`, ... Each claim is one
   testable statement of observable behaviour, followed by its evidence:
   `Evidence: path:line[-line]` (and/or `test: <test name>`). A claim with no
   evidence is not a claim; put it under Unknowns.
5. **Relationships**: what it depends on (runtime, notable libraries by role,
   not by requirement), what it reads or writes outside itself, and how other
   systems integrate with it.
6. **Unknowns**: anything you could not determine, and the reading you would
   take by default.
7. **Left free**: internal design choices a rebuild may make differently
   (module layout, libraries, algorithms) because no user can observe them.

## Rules

- Describe behaviour, not implementation. Never paste source or test code.
  Short literal examples of input and output are fine and encouraged.
- Pin what is observable, leave free what is not. When a behaviour is only
  reachable through internals (a function no user can call), say how a user
  reaches it, or put it under Left free.
- The program's observed behaviour is the truth. When a test, comment or
  document disagrees with what the program does (or a test cannot run),
  specify what the program does and record the disagreement under Unknowns.
- Prefer many small precise claims to few broad ones. Edge cases that the
  tests check are exactly the claims a rebuild is most likely to get wrong.

## Before you finish: grade your own result

Check each item and fix the specification until all hold:

- every behaviour a test in this repository checks through a user-reachable
  path is covered by at least one claim;
- every claim cites evidence that exists at that path and line;
- the original name, owner and URL appear nowhere;
- a reader with only this file could launch the program and exercise every
  route and option without guessing.

End with one line: `SPEC WRITTEN: <claim count> claims, <unknown count> unknowns`.
