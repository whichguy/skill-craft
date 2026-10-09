# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-4c7ae00f3e9f4e69bcdc2e0fd505f20c",
  "created_at": "2026-10-09T06:45:21Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node system/http-smoke.js",
      "counts": null,
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.208,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node system/ui-click.js",
      "counts": null,
      "exit": 0,
      "host_dependent": true,
      "ids_missing": [],
      "seconds": 0.786,
      "status": "passed",
      "suite": "check"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "system-test",
  "work_item": ""
}
```
