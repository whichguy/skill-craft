# ShipLoop test-loop verification

```shiploop-state
{
  "action": "nav-bf528ec1eb86448a90e34c70f4add75e",
  "created_at": "2026-10-07T00:15:33Z",
  "disposition": "passed",
  "passed": true,
  "runs": [
    {
      "command": "node --test test/game.test.js",
      "counts": null,
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5"
      ],
      "exit": 0,
      "ids": [
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-10",
        "TC-11"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.119,
      "status": "passed",
      "suite": "focused"
    },
    {
      "command": "python3 -c 'import pathlib,re,sys; s=pathlib.Path(\"lib/game.js\").read_text(); pat=lambda n: re.search(r\"/\\*\\*[\\s\\S]{10,}?\\*/\\s*(?:export\\s+)?function \"+n, s); sys.exit(0 if pat(\"newGame\") and pat(\"fire\") else 1)'",
      "counts": null,
      "criteria": [
        "C6"
      ],
      "exit": 0,
      "ids_missing": [],
      "seconds": 0.054,
      "status": "passed",
      "suite": "check"
    },
    {
      "command": "node --test",
      "counts": null,
      "criteria": [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5"
      ],
      "exit": 0,
      "ids": [
        "TC-6",
        "TC-7",
        "TC-8",
        "TC-10",
        "TC-11"
      ],
      "ids_missing": [],
      "min_tests": 5,
      "seconds": 0.126,
      "status": "passed",
      "suite": "regression"
    }
  ],
  "schema": "shiploop-test-loop/v1",
  "stage": "regression",
  "work_item": "W1"
}
```
