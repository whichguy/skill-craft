# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-5fee0f99e2a84e9ead9e867d954270ec",
  "created_at": "2026-10-09T06:42:03Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "accepted_ran": 21,
      "command": "node --test --test-reporter=spec test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 21,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 0,
      "ids": [
        "TC-4",
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12"
      ],
      "ids_missing": [],
      "min_tests": 14,
      "seconds": 0.112,
      "status": "passed",
      "suite": "focused"
    },
    {
      "accepted_ran": 11,
      "command": "node --test --test-reporter=spec test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 11,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-5",
        "TC-15"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.27,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "grep -q \"require('./rules')\" server.js && ! grep -q \"require('node:http')\\|require('http')\" rules.js",
      "counts": null,
      "criteria": [
        "C4"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.009,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "grep -q 'node server.js' README.md && grep -q 'node --test' README.md",
      "counts": null,
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.007,
      "status": "passed",
      "suite": "check"
    },
    {
      "accepted_ran": 32,
      "command": "node --test --test-reporter=spec",
      "counts": {
        "failed": 0,
        "ran": 32,
        "runners": [
          "node"
        ]
      },
      "exit": 0,
      "ids_missing": [],
      "min_tests": 22,
      "seconds": 0.279,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
