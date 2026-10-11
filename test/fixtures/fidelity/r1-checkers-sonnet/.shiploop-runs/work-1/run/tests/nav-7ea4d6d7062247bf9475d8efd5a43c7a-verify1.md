# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-7ea4d6d7062247bf9475d8efd5a43c7a",
  "created_at": "2026-10-08T17:50:43Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test --test-reporter=spec test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 9,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4",
        "TC-5",
        "TC-6",
        "TC-7",
        "TC-8"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.123,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test --test-reporter=spec test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 5,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C5",
        "C6"
      ],
      "exit": 0,
      "ids": [
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12",
        "TC-13"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.21,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "grep -q \"require(.\\./rules\" server.js",
      "counts": null,
      "criteria": [
        "C7"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.005,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test --test-reporter=spec",
      "counts": {
        "failed": 0,
        "ran": 14,
        "runners": [
          "node"
        ]
      },
      "exit": 0,
      "ids_missing": [],
      "min_tests": 13,
      "seconds": 0.223,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
