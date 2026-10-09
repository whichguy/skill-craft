# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-b87d0a0a650d4a469d2d4dd731b70b0d",
  "created_at": "2026-10-09T00:32:47Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/rules.test.js",
      "counts": {
        "failed": 0,
        "ran": 27,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 0,
      "ids": [
        "TC-4",
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11"
      ],
      "ids_missing": [],
      "min_tests": 12,
      "seconds": 0.114,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 16,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C2",
        "C3"
      ],
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-5",
        "TC-13",
        "TC-14"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.356,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "! grep -E \"require\\(.(node:)?(http|fs|net)\" rules.js && grep -q PORT README.md && grep -q 'node --test' README.md && ! grep -q '\"dependencies\"' package.json",
      "counts": null,
      "criteria": [
        "C4"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.012,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 43,
        "runners": [
          "node"
        ]
      },
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.365,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
