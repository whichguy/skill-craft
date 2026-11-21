## Failing now
none. All 26 entries (U-1..U-5, C-1..C-21) in `ratchet/acceptance.json` pass on the product as it stands. Each runs
`node --test --test-name-pattern='^<id> ' acceptance/assign.test.js` (C-21 runs `npm test`, about 15 s).

## Discoveries
- `npm test` (`node --test`) also collects `acceptance/*.test.js`, so the acceptance tests run inside it; C-21 skips itself when `ACC_INNER` is set, to avoid recursion | Observable: `npm test` output lists the `U-n`/`C-n` tests | Why: Node's default test glob matches any `*.test.js` outside node_modules.
- C-3 Open points (trim, whitespace-only, control characters) are untested; only `""` and the 64/65 boundary are asserted | Observable: none | Why: left to the requester.
- C-5 repeated value on a resolved/closed ticket (409 vs 200) is untested; only a change of assignee is asserted | Observable: none | Why: Open point.
- The spec says nothing on `PUT` with a wrong-typed JSON body (array, non-JSON); C-4 treats them as 400 `invalid` | Observable: `PUT` body `[1]` or `not json` answers 400 | Why: docs/api.md says a body that is not a JSON object is `invalid`.
