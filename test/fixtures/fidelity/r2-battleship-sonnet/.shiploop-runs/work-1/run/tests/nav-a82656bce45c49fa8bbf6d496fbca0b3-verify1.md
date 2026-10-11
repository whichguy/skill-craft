# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-a82656bce45c49fa8bbf6d496fbca0b3",
  "created_at": "2026-10-09T00:29:38Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": {
        "failed": 0,
        "ran": 4,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4"
      ],
      "ids_missing": [],
      "min_tests": 4,
      "seconds": 0.116,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 5,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3",
        "C4"
      ],
      "exit": 0,
      "ids": [
        "TC-5",
        "TC-6",
        "TC-7",
        "TC-8"
      ],
      "ids_missing": [],
      "min_tests": 4,
      "seconds": 0.237,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node -e \"const p=require('./package.json');process.exit(p.dependencies&&Object.keys(p.dependencies).length?1:0)\"",
      "counts": null,
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.046,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 9,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.244,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "verify",
  "work_item": "W1"
}
```
