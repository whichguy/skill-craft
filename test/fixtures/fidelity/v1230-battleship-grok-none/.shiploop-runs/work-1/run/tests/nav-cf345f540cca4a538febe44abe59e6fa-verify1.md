# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-cf345f540cca4a538febe44abe59e6fa",
  "created_at": "2026-10-07T16:02:30Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 12,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7"
      ],
      "exit": 0,
      "ids": [
        "TC-PLACE",
        "TC-MISS",
        "TC-HIT",
        "TC-SUNK",
        "TC-WIN",
        "TC-REPEAT",
        "TC-BOUNDS",
        "TC-OVER",
        "TC-HIDE",
        "TC-MEMORY",
        "TC-MODULE",
        "TC-NO-NPM"
      ],
      "ids_missing": [],
      "min_tests": 12,
      "seconds": 0.129,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 12,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7"
      ],
      "exit": 0,
      "ids": [
        "TC-PLACE",
        "TC-MISS",
        "TC-HIT",
        "TC-SUNK",
        "TC-WIN",
        "TC-REPEAT",
        "TC-BOUNDS",
        "TC-OVER",
        "TC-HIDE",
        "TC-MEMORY",
        "TC-MODULE",
        "TC-NO-NPM"
      ],
      "ids_missing": [],
      "min_tests": 12,
      "seconds": 0.13,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-refine",
  "work_item": "W1"
}
```
