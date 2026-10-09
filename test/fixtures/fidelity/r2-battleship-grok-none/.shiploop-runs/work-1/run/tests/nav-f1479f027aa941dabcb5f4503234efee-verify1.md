# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-f1479f027aa941dabcb5f4503234efee",
  "created_at": "2026-10-09T00:38:19Z",
  "disposition": "passed",
  "expect": "a test ran",
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
      "seconds": 0.164,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-author",
  "work_item": "W1"
}
```
