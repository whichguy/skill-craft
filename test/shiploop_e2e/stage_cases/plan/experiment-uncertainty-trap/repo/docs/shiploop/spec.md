# Specification

## R-1
Export users as valid NDJSON via `tools/export-engine.js`, preserving multiline notes (each output line parses as valid JSON) and supporting arbitrarily large user lists (> 25 users).

## R-2
Preserve existing `/users` HTTP API endpoints and keep `node --test` passing with zero external npm dependencies.
