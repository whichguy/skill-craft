# Fix pass

`node --test` before any change: 6 tests, 6 pass. After: 10 tests, 10 pass. Each shortfall in look.md was reproduced with its own steps before deciding. Each new test failed on the unchanged server.

## Shortfalls

- Fractional cents are silently recorded as whole cents: fixed. Request bodies are parsed with each number checked against its JSON text, so a non-whole value gets 400 even when a parser would round it to a whole one. Test: `TC-7 rejects amounts and shares whose JSON text is not a whole number`.
- Two instances can lose an acknowledged expense: not changed. The request describes one process with one PORT and one DATA_FILE, and within that process concurrent requests do not lose expenses (TC-5). Detecting or refusing a second process on the same file would be a new capability, a cross-process lock with stale-lock handling, not a correction. README.md states the limit and says to stop the old process before starting its replacement.
- A write through a symlink splits the ledger: fixed. DATA_FILE is resolved through symbolic links at startup, including a link whose target does not exist yet, so writes replace the target and keep the link. Test: `TC-8 writes through a symlinked DATA_FILE to its target and keeps the link`.
- Some successfully created groups are unusable through normal URLs: fixed. Creating a group with ID `.`, `..` or an ID holding a lone surrogate now gets 400 `Invalid group ID`, since no URL path segment can address one. Test: `TC-9 refuses group IDs that no URL path segment can address`.
- Startup fails on a newly allocated empty file: fixed. An empty or whitespace-only DATA_FILE starts with no groups. Other content that is not JSON still stops startup. Test: `TC-10 starts with no groups from an empty DATA_FILE`.

## Choices documented

README.md (new) describes how to run the service and every endpoint. Its section "Behaviour you should know about" states what the running service does for each of these:

- Duplicate members collapse to one member at the first position.
- IDs and names need some non-whitespace text and are matched exactly, with case and surrounding spaces kept.
- The URL format: one percent-decoded path segment, 400 for a malformed escape, query strings ignored.
- Unlisted methods and paths, including a trailing slash, return 404. No route lists, changes or deletes data.
- The group creation reply holds the ID and stored members. Checks run in this order: ID (400), then existing ID (409), then members.
- Request JSON: no Content-Type needed, unused properties ignored, and the last value wins for a repeated property.
- Error replies are `{"error": ...}`. A write failure gets 500, is logged to stderr, keeps nothing and uses up no expense number.
- The largest single amount is 9,007,199,254,740,991 cents.
- Large totals are exact JSON integers. Clients need a lossless parser for them.
- Defaults: PORT 3000, and DATA_FILE `expenses.json` in the working directory.
- Storage: the file is created on the first successful change, each write replaces it with a new 0600 file, and a symlink is kept with its target replaced.
- One process per data file, from the shortfall not changed. The file is read only at startup, outside edits are overwritten, and a second process on the same file is not detected and can lose expenses.
