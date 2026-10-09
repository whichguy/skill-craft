# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-13dfa8dd0e494322abb4c501b4bd207e",
  "created_at": "2026-10-09T06:39:41Z",
  "disposition": "passed",
  "expect": "a test ran",
  "passed": true,
  "runs": [
    {
      "command": "node --test --test-reporter=spec test/rules.test.js",
      "counts": {
        "failed": 19,
        "ran": 19,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 1,
      "ids": [
        "TC-4",
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12"
      ],
      "ids_missing": [],
      "min_tests": 14,
      "seconds": 0.115,
      "status": "red",
      "suite": "focused"
    },
    {
      "command": "node --test --test-reporter=spec test/server.test.js",
      "counts": {
        "failed": 11,
        "ran": 11,
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
        "TC-5",
        "TC-15"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 5.328,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-author",
  "work_item": "W1"
}
```
