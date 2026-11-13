# records

Small text-record helpers. Run the tests with `npm test` (node:test).

## Parsing records

`parseRecords(text)` is exported from `src/records.js` as a CommonJS function:

```js
const { parseRecords } = require('./src/records');
console.log(parseRecords('name=ada;team=x\n\nname=bob;team=y'));
// [{ name: 'ada', team: 'x' }, { name: 'bob', team: 'y' }]
```

Each non-blank line becomes an object. Fields are separated by `;`; each key must
start with a lowercase letter and contain only lowercase letters, digits, or
underscores. Keys are validated as written, while values are trimmed. The first
`=` separates the key from the value, so later `=` characters are part of the
value; an empty value is allowed. Blank lines are ignored, including in otherwise
empty input.

A non-string input throws `TypeError`. A missing `=`, invalid or empty key, or
duplicate key on a line throws `SyntaxError` with the 1-based source line number;
blank lines count toward that number. Errors do not include the input text. There
is no diagnostics setting or external service: the function runs locally and has
no side effects. See the [parser tests](test/records.test.js) for examples and the
[living specification](docs/shiploop/spec.md) for the accepted requirements.
