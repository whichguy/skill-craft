# Specification

## R-1
Export 100+ user records including UTF-8 characters, commas, and multiline notes as valid JSON Lines using the existing repository CLI tools (`tools/export-v1.js` / `tools/export-v2-stream.js`).

## R-2
Preserve existing `/users` HTTP API endpoints and keep `node --test` passing with zero external npm dependencies.
