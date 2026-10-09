# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-70f6c0cd83154115a326b7addc4ada43",
  "created_at": "2026-10-08T17:43:52Z",
  "disposition": "passed",
  "expect": "red",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": {
        "failed": 17,
        "ran": 18,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 1,
      "ids": [
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.124,
      "status": "red",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 20,
        "ran": 23,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3"
      ],
      "exit": 1,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4",
        "TC-5",
        "TC-9",
        "TC-10",
        "TC-13"
      ],
      "ids_missing": [],
      "min_tests": 10,
      "seconds": 5.318,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-red",
  "work_item": "W1"
}
```
