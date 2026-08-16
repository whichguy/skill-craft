# DevLoop — loop detail

## Charter shape

```json
{
  "goal": "one sentence",
  "criteria": [
    {
      "id": "C1",
      "role": "change",
      "outcome": "observable behavior",
      "verifier": {
        "argv": ["python3", "-c", "import sys; sys.exit(1)"],
        "cwd": ".",
        "expected_exit": 0,
        "timeout_seconds": 60,
        "guard_paths": ["tests/test_example.py"]
      }
    }
  ]
}
```

- `role: change` — must be observed **failing** at PROVE before BUILD claims red→green.
- `role: regression` — may stay green throughout; still re-run at STOP.
- `argv` — no shell `-c` / `-lc` (including `/bin/bash -c`). Put pipelines in a repo script and list it in `guard_paths`.
- `guard_paths` — files whose content is frozen; mutating them after freeze → `guard_drift`.

## Freeze / prove / stop

1. `freeze` validates, checks argv[0] on PATH, hashes guards, writes `charter.json` + `charter.sha256` under run dir.
2. `prove` re-checks digests, runs every argv, writes `prove.json` including `change_observed_red`.
   Red is **sticky**: a later all-green re-prove (after BUILD) keeps prior red bits for the same charter hash so STOP does not false-block with `never_red`.
3. `stop` refuses if any `change` criterion was never red; re-checks digests; re-runs all; writes `receipt.json` with `mode: native`.

## Worked example

Goal: create `result.txt` containing exactly `devloop-ok`.

1. DEFINE criterion with `argv: ["python3","-c","import pathlib; assert pathlib.Path('result.txt').read_text()=='devloop-ok\\n'"]` and `guard_paths: []` (or a committed assert script).
2. PROVE fails (file missing) → red recorded.
3. BUILD writes `result.txt`.
4. STOP passes → receipt PASS.

## Redefine

If acceptance must change, end the run (`REDEFINE_REQUIRED`) and start a new freeze. Do not mutate the active charter.
