# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-73c032cd61af49dab762c3e3493adce4",
  "created_at": "2026-10-07T15:46:11Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": {
        "failed": 0,
        "ran": 16,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C1"
      ],
      "exit": 0,
      "ids": [
        "R-4",
        "R-5",
        "R-6",
        "R-8"
      ],
      "ids_missing": [],
      "min_tests": 6,
      "seconds": 0.136,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 17,
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
        "R-1",
        "R-2",
        "R-3",
        "R-5",
        "R-7",
        "R-10"
      ],
      "ids_missing": [],
      "min_tests": 8,
      "seconds": 0.322,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "! grep -rE \"require\\('[^.n][^']*'\\)\" game.js server.js test && ! grep -qs '\"dependencies\"' package.json",
      "counts": null,
      "criteria": [
        "C5"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.008,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 33,
        "runners": [
          "node"
        ]
      },
      "criteria": [
        "C4"
      ],
      "exit": 0,
      "ids_missing": [],
      "min_tests": 20,
      "seconds": 0.323,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "verify",
  "work_item": "W1"
}
```
