# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-cddfca7e839440bf847003dd465dfd36",
  "created_at": "2026-10-07T01:03:09Z",
  "disposition": "failed",
  "passed": false,
  "runs": [
    {
      "command": "node --test --test-concurrency=1 --test-force-exit scripts/system-browser.test.js",
      "counts": null,
      "exit": 0,
      "ids": [
        "TC-4",
        "TC-15"
      ],
      "ids_missing": [
        "TC-15"
      ],
      "min_tests": 2,
      "seconds": 11.347,
      "status": "ids-missing",
      "suite": "focused"
    },
    {
      "command": "node --test",
      "counts": null,
      "exit": 0,
      "ids": [
        "TC-1",
        "TC-2",
        "TC-3",
        "TC-5",
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-9",
        "TC-10",
        "TC-11",
        "TC-12",
        "TC-13",
        "TC-14"
      ],
      "ids_missing": [],
      "min_tests": 14,
      "seconds": 8.907,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "system-test",
  "work_item": ""
}
```
