# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-09ad5b7b122047a1bbb600fffafc53b6",
  "created_at": "2026-10-07T16:38:50Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 7,
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
        "TC-PORT",
        "TC-NEW",
        "TC-FIRE-HTTP",
        "TC-UNKNOWN",
        "TC-HTML",
        "TC-MODULE",
        "TC-NO-NPM"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.596,
      "status": "passed",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-green",
  "work_item": "W2"
}
```
