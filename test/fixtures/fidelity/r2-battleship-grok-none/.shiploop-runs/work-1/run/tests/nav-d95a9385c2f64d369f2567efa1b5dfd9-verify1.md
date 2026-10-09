# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-d95a9385c2f64d369f2567efa1b5dfd9",
  "created_at": "2026-10-09T00:38:34Z",
  "disposition": "passed",
  "expect": "red",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/rules.test.js",
      "counts": {
        "failed": 19,
        "ran": 19,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2"
      ],
      "exit": 1,
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
      "seconds": 0.123,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-red",
  "work_item": "W1"
}
```
