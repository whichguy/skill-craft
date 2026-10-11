# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-7b8eb31d74154aca8daff3ec1b4ede18",
  "created_at": "2026-10-08T18:17:33Z",
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
      "seconds": 0.115,
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
      "seconds": 0.139,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "grep -q 'node server.js' README.md",
      "counts": null,
      "criteria": [
        "C6"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.006,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "grep -q 'Contract:' rules.js && grep -q 'Contract:' server.js",
      "counts": null,
      "criteria": [
        "C7"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.008,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test --test-reporter spec",
      "counts": {
        "failed": 0,
        "ran": 15,
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
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12",
        "TC-13",
        "TC-14",
        "TC-15"
      ],
      "ids_missing": [],
      "min_tests": 15,
      "seconds": 0.151,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
