# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-85d41f394def4ce9b86cf3c6968bc85c",
  "created_at": "2026-10-07T01:15:13Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "PORT=9876 node server.js >/tmp/battleship-release.out 2>/tmp/battleship-release.err & echo $! >/tmp/battleship-release.pid; sleep 0.5; curl -fsS http://127.0.0.1:9876/ | grep -q '<title>Battleship</title>'; code=$?; kill $(cat /tmp/battleship-release.pid); exit $code",
      "counts": null,
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.538,
      "status": "passed",
      "suite": "check"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "release-verify",
  "work_item": ""
}
```
