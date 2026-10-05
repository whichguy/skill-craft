---
bump: patch
---
The refusal for an Improve opening that is too large now says how its byte counts are made: the sizes it lists and the room it states are counted escaped like JSON, so a newline or a quote costs 2 bytes and a non-ASCII character 6, and a file's byte size undercounts them. The stated room itself was already right; this only says what it measures, so a model that shortens the opening can measure it the same way and not be refused a second time.
