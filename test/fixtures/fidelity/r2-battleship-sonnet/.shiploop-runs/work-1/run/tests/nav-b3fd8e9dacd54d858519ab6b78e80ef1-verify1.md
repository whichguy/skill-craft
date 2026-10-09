# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-b3fd8e9dacd54d858519ab6b78e80ef1",
  "created_at": "2026-10-09T00:26:43Z",
  "disposition": "passed",
  "expect": "red",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": {
        "failed": 4,
        "ran": 4,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 1,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4"
      ],
      "ids_missing": [],
      "min_tests": 4,
      "seconds": 0.113,
      "status": "red",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 4,
        "ran": 4,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3",
        "C4"
      ],
      "exit": 1,
      "ids": [
        "TC-5",
        "TC-6",
        "TC-7",
        "TC-8"
      ],
      "ids_missing": [],
      "min_tests": 4,
      "seconds": 0.116,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-red",
  "work_item": "W1"
}
```
