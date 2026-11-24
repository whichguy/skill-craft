# Specification

## R-1
Provide a file-backed JSON note store, `POST /notes` and `GET /notes` HTTP API endpoints, and a `bin/notes.js` CLI that creates and lists notes against the running HTTP server.

## R-2
Support search query, tag filtering, and pagination parameters on `GET /notes` and corresponding CLI flags.

## R-3
Support CSV and NDJSON export plus summary statistics (note count per tag and latest timestamp) across both HTTP API and CLI.

## R-4
Preserve existing `/users` HTTP API endpoints and keep `node --test` passing with zero external npm dependencies.
