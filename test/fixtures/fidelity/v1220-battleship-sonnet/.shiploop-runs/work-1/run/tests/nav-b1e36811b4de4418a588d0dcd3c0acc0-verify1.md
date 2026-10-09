# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-b1e36811b4de4418a588d0dcd3c0acc0",
  "created_at": "2026-10-06T15:13:37Z",
  "disposition": "passed",
  "expect": "red",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": null,
      "criteria": [
        "C1"
      ],
      "exit": 1,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-4",
        "TC-5",
        "TC-6",
        "TC-7"
      ],
      "ids_missing": [],
      "min_tests": 7,
      "seconds": 0.121,
      "status": "red",
      "suite": "focused"
    },
    {
      "command": "node --test test/server.test.js",
      "counts": null,
      "criteria": [
        "C2",
        "C3",
        "C4"
      ],
      "exit": 1,
      "ids": [
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.124,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-red",
  "work_item": "W1"
}
```
