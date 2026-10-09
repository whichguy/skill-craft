# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-0618dbff6b4244a1a5ca25e7beded1c8",
  "created_at": "2026-10-07T15:43:59Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": {
        "failed": 0,
        "ran": 14,
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
      "seconds": 0.534,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": {
        "failed": 0,
        "ran": 15,
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
      "seconds": 1.158,
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
      "seconds": 0.027,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 29,
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
      "seconds": 1.213,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
