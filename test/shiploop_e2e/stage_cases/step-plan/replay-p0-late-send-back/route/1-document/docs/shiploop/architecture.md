# Architecture

## Decisions

AD-1: Implement the requested functions as a local CommonJS module at src/records.js, using Node built-ins and the existing node:test suite; no storage or service boundary is involved.

## Structure

src/ contains independent CommonJS helpers; test/ contains node:test cases.

## Real-boundary checks

Retain the local Node unit boundary: parsing is a pure in-process operation with no external service or storage boundary. The tests import the public CommonJS module directly; no separate remote check applies.
