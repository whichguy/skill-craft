# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-ee3eccf7caf14a93aa143c45d210a47b",
  "created_at": "2026-10-09T06:27:37Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "accepted_ran": 5,
      "command": "node --test --test-reporter=spec test/game.test.js",
      "counts": {
        "failed": 0,
        "ran": 5,
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
        "TC-4",
        "TC-5"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.113,
      "status": "passed",
      "suite": "focused"
    },
    {
      "accepted_ran": 8,
      "command": "node --test --test-reporter=spec test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 8,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3",
        "C4",
        "C5"
      ],
      "exit": 0,
      "ids": [
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12",
        "TC-13"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.309,
      "status": "passed",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-green",
  "work_item": "W1"
}
```
