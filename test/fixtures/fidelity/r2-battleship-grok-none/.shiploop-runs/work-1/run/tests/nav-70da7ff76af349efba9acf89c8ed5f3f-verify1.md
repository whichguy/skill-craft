# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-70da7ff76af349efba9acf89c8ed5f3f",
  "created_at": "2026-10-09T00:42:49Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 19,
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
        "ran": 19,
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
      "seconds": 0.117,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-refine",
  "work_item": "W1"
}
```
