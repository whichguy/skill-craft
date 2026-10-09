# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-d81035ee3cb642dfbbeebaae4580ed58",
  "created_at": "2026-10-07T16:03:26Z",
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
      "seconds": 0.128,
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
      "seconds": 0.132,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
