# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-d21ec7c728c24bc69be98f4a3a3d854c",
  "created_at": "2026-10-05T14:06:34Z",
  "disposition": "passed",
  "expect": "red",
  "passed": true,
  "runs": [
    {
      "command": "node --test --test-reporter=spec --test-name-pattern='TC-01|TC-03|TC-04|TC-05|TC-06' test/game.test.js",
      "counts": null,
      "criteria": [
        "C2",
        "C3",
        "C4",
        "C5",
        "C6"
      ],
      "exit": 1,
      "ids": [
        "TC-01",
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.104,
      "status": "red",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "test-red",
  "work_item": "W1"
}
```
