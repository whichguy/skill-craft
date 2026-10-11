# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-98510acacea747c59f004a57d79cd0f7",
  "created_at": "2026-10-07T16:42:24Z",
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
      "seconds": 0.605,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "grep -q 'node server.js' README.md && grep -q PORT README.md",
      "counts": null,
      "criteria": [
        "C8"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.009,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "test -f browser.mjs && test ! -e test/browser.mjs",
      "counts": null,
      "criteria": [
        "C9"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.004,
      "status": "passed",
      "suite": "check"
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
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "C7"
      ],
      "exit": 0,
      "ids": [
        "TC-PLACE",
        "TC-MISS",
        "TC-HIT",
        "TC-SUNK",
        "TC-WIN",
        "TC-REPEAT",
        "TC-BOUNDS",
        "TC-OVER",
        "TC-HIDE",
        "TC-MEMORY",
        "TC-MODULE",
        "TC-NO-NPM",
        "TC-PORT",
        "TC-NEW",
        "TC-FIRE-HTTP",
        "TC-UNKNOWN",
        "TC-HTML"
      ],
      "ids_missing": [],
      "min_tests": 19,
      "seconds": 0.608,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W2"
}
```
