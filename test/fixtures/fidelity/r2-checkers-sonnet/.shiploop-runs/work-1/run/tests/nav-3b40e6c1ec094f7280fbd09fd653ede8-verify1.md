# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-3b40e6c1ec094f7280fbd09fd653ede8",
  "created_at": "2026-10-09T00:38:40Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/system.test.js",
      "counts": {
        "failed": 0,
        "ran": 3,
        "runners": [
          "node"
        ]
      },
      "exit": 0,
      "ids": [
        "ST-1",
        "ST-2",
        "ST-3"
      ],
      "ids_missing": [],
      "min_tests": 3,
      "seconds": 0.481,
      "status": "passed",
      "suite": "focused"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "system-test",
  "work_item": ""
}
```
