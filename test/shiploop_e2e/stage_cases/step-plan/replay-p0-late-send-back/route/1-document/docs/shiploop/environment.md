# Environment

Seeded by the E2E harness from the case's own checks; discovery did not run.

## Commands

```sh
node --test
node --test --test-reporter=spec --test-name-pattern='TC-1|TC-2|TC-3|TC-4' test/records.test.js
npm test
node -e "const {parseRecords,select}=require('./src/records');const a=require('assert');a.deepStrictEqual(parseRecords('name=ada;team=x\n\nname=bob;team=y'),[{name:'ada',team:'x'},{name:'bob',team:'y'}]);a.deepStrictEqual(select(parseRecords('a=1\na=2'),'a','2'),[{a:'2'}]);a.throws(()=>parseRecords('a=1\nbad'),e=>e instanceof SyntaxError&&/line 2/.test(e.message));a.throws(()=>parseRecords(1),TypeError)"
```

The final seeded command also checks `select`; it cannot pass until S2 implements
that export. At S1 it reaches `TypeError: select is not a function`.

## Harnesses and suites

Retain the built-in node:test harness: test/records.test.js imports the CommonJS module and uses strict assertions; no fixtures or mocks are needed. The focused command selects the current TC-1 and TC-2 cases, while npm test includes them in the regression suite. The test stage owns the suite; revalidate both commands after changes to the module, suite, or Node environment. TC-3 and TC-4 belong to the later selection step.
