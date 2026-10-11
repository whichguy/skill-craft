# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-f32de8596be240ccb1f7ea20fd6a5224",
  "created_at": "2026-10-09T00:51:08Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 23,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2"
      ],
      "exit": 0,
      "ids": [
        "TC-new",
        "TC-miss",
        "TC-hit",
        "TC-sunk",
        "TC-repeat",
        "TC-win",
        "TC-after",
        "TC-args"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.115,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 23,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2"
      ],
      "exit": 0,
      "ids": [
        "TC-new",
        "TC-miss",
        "TC-hit",
        "TC-sunk",
        "TC-repeat",
        "TC-win",
        "TC-after",
        "TC-args"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.119,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "static-checks",
  "work_item": "W1"
}
```
