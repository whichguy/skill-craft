# Environment

Seeded by the E2E harness from the case's own checks; discovery did not run.

## Commands

```sh
node --test
node -e "const {parseRecords,select}=require('./src/records');const a=require('assert');a.deepStrictEqual(parseRecords('name=ada;team=x\n\nname=bob;team=y'),[{name:'ada',team:'x'},{name:'bob',team:'y'}]);a.deepStrictEqual(select(parseRecords('a=1\na=2'),'a','2'),[{a:'2'}]);a.throws(()=>parseRecords('a=1\nbad'),e=>e instanceof SyntaxError&&/line 2/.test(e.message));a.throws(()=>parseRecords(1),TypeError)"
```
