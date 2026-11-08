# Product specification

## Requirements

R-1: Add offline substring search to this Python catalog using the application's src/database.py connection. Search must be accent insensitive and Unicode casefold insensitive, without changing displayed titles: cafe finds Café Racer, STRASSE finds Die Straße, and interior query afe finds Café Racer. Query xyz finds no records. An empty query returns no matches. Search order is stable by ID and duplicate titles preserve distinct IDs. The fixed initial catalog fits in memory (at most 5000 titles), search needs no external service, no fuzzy ranking and no new dependency. A previous design note suggests SQLite FTS5 trigram or LIKE if they meet these semantics on this binding; that is a proposal, not an accepted requirement. Verify the chosen mechanism at its real boundary when needed, and retain implementation and consumer checks as future work. Temporary local experiments on disposable data are authorized. Existing tests must remain passing.

## Non-functional requirements

R-2: Keep data loss and false success visible; preserve the existing baseline and require repeatable behavioral tests for the new command. Use only the stated local standard-library runtime.

## Retired

None.
