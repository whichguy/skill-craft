# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-4964e120cef043bda1bce0dcb834ddc4",
  "created_at": "2026-10-06T15:15:31Z",
  "disposition": "failed",
  "passed": false,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": null,
      "criteria": [
        "C1"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4",
        "TC-5",
        "TC-6",
        "TC-7"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.129,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": null,
      "criteria": [
        "C2",
        "C3",
        "C4"
      ],
      "exit": 0,
      "ids": [
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.284,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node -e \"const p=require('./package.json');if(Object.keys(p.dependencies||{}).length||Object.keys(p.devDependencies||{}).length)process.exit(1)\"",
      "counts": null,
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.045,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": null,
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "min_tests": 12,
      "seconds": 0.288,
      "status": "uncounted",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-refine",
  "work_item": "W1"
}
```
