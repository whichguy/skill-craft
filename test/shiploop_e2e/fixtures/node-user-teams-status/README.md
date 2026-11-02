# User service

An in-memory Node.js service with no npm dependencies. `npm start` runs `src/server.js` on `PORT`, and `npm test` runs the existing `node:test` files under `test/`.

## Project documents

The living documents are under `docs/shiploop/`: `spec.md` holds requirements and dated history, `architecture.md` records decisions, and `environment.md` records how to work with the project. The `## Requirements` section in `spec.md` is the authoritative set of active requirements; entries under `## Retired` or `## History` are records rather than active requirements. History may use R- or AD-numbered headings to identify earlier states.

Each requirement has a `Requirement:` field that states its intent and a `Status:` field for its disposition (`accepted` or `deferred`). `Current implementation:` and `Current verification:` describe the current state. For an implemented requirement, the implementation value starts with `implemented` or `complete` and includes a repo-relative JavaScript source file path. The verification value starts with `passed` and includes a repo-relative test file path under `test/`. For deferred work, the current values remain `not started` and `not run`. These fields record status and evidence; the project test suite and independent behavior checks establish whether the claims hold.

Field labels may be plain or bold, may have ordinary surrounding whitespace or a Markdown list marker, and may be reordered or placed beneath a short subheading within the requirement. A value may continue on the next nonempty line. Keep one copy of each field in its requirement. Headings inside fenced code examples are examples, not document sections. The `## History` section records earlier as-of states; keep those dated observations intact when updating current fields.
