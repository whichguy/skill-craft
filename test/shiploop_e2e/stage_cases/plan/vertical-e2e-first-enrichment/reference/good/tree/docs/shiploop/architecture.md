# Architecture

## Stack
- Node.js CommonJS, zero npm dependencies.

## Decisions

### AD-1
Keep zero external npm dependencies and preserve CommonJS module layout (`src/`, `bin/`, `test/`).

### AD-2
Use a vertical end-to-end-first slice structure (`W1` spine with atomic JSON file store + `/notes` HTTP routes + `bin/notes.js` CLI + executable E2E smoke test, followed by `W2` filtering/pagination and `W3` export/stats enrichments).
