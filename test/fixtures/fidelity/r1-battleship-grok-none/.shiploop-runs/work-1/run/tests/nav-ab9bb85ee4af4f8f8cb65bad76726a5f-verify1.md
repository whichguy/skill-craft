# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-ab9bb85ee4af4f8f8cb65bad76726a5f",
  "created_at": "2026-10-08T18:15:35Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test --test-reporter spec test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 8,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C7"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4",
        "TC-5",
        "TC-6",
        "TC-7",
        "TC-8"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.114,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test --test-reporter spec test/http.test.js",
      "counts": {
        "failed": 0,
        "ran": 7,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C4",
        "C5",
        "C7"
      ],
      "exit": 0,
      "ids": [
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12",
        "TC-13",
        "TC-14",
        "TC-15"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.145,
      "status": "passed",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-green",
  "work_item": "W1"
}
```
