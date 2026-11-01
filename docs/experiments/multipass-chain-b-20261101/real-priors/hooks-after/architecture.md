# Architecture

## Decisions

### AD-1: Compose existing local boundaries
The HTTP listing route reads the existing ordered store, applies case-insensitive literal filtering and validates pagination before using the existing helper. Correct the helper's partial-page calculation. No extra service, dependency, cache or mutable state is needed. Confirm with unit and loopback component tests.

## Real-boundary checks

Planned local loopback HTTP tests exercise GET /users from an independent client against the server process with static users, including response status and JSON fields; GET /users/:id remains covered by the existing suite. A unit test exercises helper boundaries. Both run in the worktree and later in a fresh copy of the returned source as appropriate. There is no remote service, deployment, authentication, event delivery, cache or UI boundary for this task. Test cases set up and close their server; the store is read-only.

## Structure

AD-1 applies within the existing CommonJS modules: src/server.js imports src/users.js and src/paginate.js; helper exports remain unchanged. Tests under test/ import those same modules. No new persisted schema, migration or namespace is required. Each request remains a synchronous HTTP response over process-owned read-only data.

## Conventions

Keep dependency-free CommonJS, node:http, node:test and strict assertions; use existing server lifecycle pattern. Validate untrusted query input at the listing boundary.

## Interfaces and boundaries

GET /users remains the only changed HTTP interface. GET /users/:id and the in-memory store remain unchanged. No new platform service, event channel or durable state is introduced.

## Stack

Node.js CommonJS with built-in node:http and node:test; no dependencies.

## Superseded

None.
