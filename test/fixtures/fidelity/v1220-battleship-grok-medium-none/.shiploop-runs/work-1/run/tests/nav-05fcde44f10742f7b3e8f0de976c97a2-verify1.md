# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-05fcde44f10742f7b3e8f0de976c97a2",
  "created_at": "2026-10-07T00:07:48Z",
  "disposition": "passed",
  "expect": "a test ran",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": null,
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5"
      ],
      "exit": 1,
      "ids": [
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-10",
        "TC-11"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.112,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-author",
  "work_item": "W1"
}
```
