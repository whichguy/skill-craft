# Architecture

## Decisions

AD-1: Implement the requested functions as a local CommonJS module at src/records.js, using Node built-ins and the existing node:test suite; no storage or service boundary is involved.

## Structure

src/ contains independent CommonJS helpers; test/ contains node:test cases.
