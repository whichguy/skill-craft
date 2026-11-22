# Fix pass

Before the fix, `node --test` passed 5 of 5 tests. After it, `node --test` passes 8 of 8. Each new
test fails on the original `server.js` and passes with the fix.

## Shortfalls

- Fractional amounts enter the ledger as whole cents: fixed. Request bodies are parsed with the
  number literal's source text, and a literal that is not exactly whole as written fails the
  whole-cents checks. Test: `TC-6 rejects fractional amount literals that a double would round to whole cents`.
- A second process can erase an acknowledged expense: not changed. The request describes one
  service keeping its data in the file; two processes on one file are outside it. Refusing a second
  writer needs a cross-process lock that also handles a lock left behind by a crash (TC-4 restarts
  after SIGKILL), which is new hardening rather than a small fix. Reproduced as described. The
  README tells operators to run one process per `DATA_FILE` and describes the loss.
- An unrelated JSON file is silently overwritten: fixed. At startup, a file whose JSON has no
  `groups` list stops the process before it listens and is left unchanged. Test:
  `TC-7 refuses to start on an existing JSON file that is not a ledger and leaves it intact`.
- Some created groups cannot be used through ordinary URLs: not changed. The request gives member
  rules as the only 400 reasons for creation and sets no rule on the id's form. Rejecting `.`,
  `..`, unpaired surrogates or long ids would add validation rules the request does not ask for.
  Reproduced as described. The README lists which ids cannot be reached and why.
- Saving through a symlink leaves the ledger target stale: fixed. `DATA_FILE` is resolved to the
  file it points to at startup, so saves replace the target and keep the link. Test:
  `TC-8 saves through a symlinked DATA_FILE to the linked ledger`.

## Choices documented in README.md

Each one was checked against the running product before it was written.

- Ids and names need a non-whitespace character. They are compared exactly as sent, including case
  and surrounding spaces.
- A repeated member name counts once, at its first position, which decides leftover cents and ties.
- A duplicate id answers 409 even when the members are invalid.
- Creation answers `{"id": ...}`. Errors answer `{"error": "<message>"}`.
- The query string is ignored. The id segment is percent-decoded once (`room%2F1`).
- Other methods, extra segments and a trailing slash answer 404.
- Bodies are JSON whatever the Content-Type. Unknown properties are ignored. An equal split ignores
  `shares`.
- Request amounts go up to 9,007,199,254,740,991 cents. Literals such as `2.0` and `2e0` are
  accepted because they are exactly whole. `-0` is rejected as cents and counts as 0 as a share.
- Balance and settlement totals above the safe-integer range are exact JSON integers and need a
  precision-preserving parser.
- Balance and settlement answers use `JSON.rawJSON`. Tested on Node v26.12.1.
- A missing file is created on the first write. With a missing directory the server still starts
  and the first write answers 500. A file that is invalid JSON or not a ledger stops startup and is
  left unchanged.
- A failed save answers 500, changes nothing and can be retried.
- Saves leave the ledger with mode 0600 (a 0640 file became 0600).
- The server listens on all interfaces and has no authentication.
- `PORT=0` lets the OS pick the port, which is printed on standard output.
- Not changed: run one process per `DATA_FILE`, because with two processes the last save wins.
- Not changed: ids `.`, `..`, ids with unpaired surrogates and very long ids (431 past Node's
  16 KB header limit) are accepted but cannot be reached from ordinary clients.
- A symlinked `DATA_FILE` is saved through to its target. A symlink whose target does not exist yet
  is replaced by a regular file on the first save.
