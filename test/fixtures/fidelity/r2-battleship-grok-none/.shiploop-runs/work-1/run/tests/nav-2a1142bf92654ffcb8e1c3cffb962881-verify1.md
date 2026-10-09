# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-2a1142bf92654ffcb8e1c3cffb962881",
  "created_at": "2026-10-09T01:20:45Z",
  "disposition": "passed",
  "observed": {
    "kind": "fast-forward-merge",
    "where": "returned-result"
  },
  "passed": true,
  "runs": [
    {
      "command": "node --test",
      "counts": {
        "failed": 0,
        "ran": 35,
        "runners": [
          "node"
        ]
      },
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.554,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "PORT=38211 node server.js & p=$!; sleep 1; ok=0; curl -sf http://127.0.0.1:38211/ | grep -q '<title>Battleship</title>' || ok=1; g=$(curl -sf http://127.0.0.1:38211/api/new | sed -n 's/.*\"game\":\"\\([^\"]*\\)\".*/\\1/p'); [ -n \"$g\" ] || ok=1; curl -sf -X POST http://127.0.0.1:38211/api/fire -d \"{\\\"game\\\":\\\"$g\\\",\\\"row\\\":0,\\\"col\\\":0}\" | grep -q '\"result\"' || ok=1; kill $p; exit $ok",
      "counts": null,
      "exit": 0,
      "ids_missing": [],
      "seconds": 1.054,
      "status": "passed",
      "suite": "check"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "release-verify",
  "work_item": ""
}
```
