# Environment

This fixture uses Python's standard library only. `readiness_cli.py` is a local synthetic interface; it has no network or account integration. The harness sets `NATIVE_SETUP_TARGET` to an external per-slice state directory. CLI setup, journey, and audit writes are limited to that directory.

## Documented commands

```sh
python3 readiness_cli.py probe service
python3 readiness_cli.py probe sandbox
python3 readiness_cli.py probe grant
python3 readiness_cli.py setup sandbox
python3 readiness_cli.py journey service
python3 readiness_cli.py journey sandbox
python3 readiness_cli.py journey grant
```

The seed records discovery without executing these commands. Probe signals are `ready`, `missing`, and `unavailable`; a prepared sandbox must also report `receipt_valid: true`. Journey signals are `completed` or `blocked`. These are distinct observations.

The requested regression harness is Python `unittest`; tests are to be authored for this task and are not claimed as existing or passing. The formatter contract is in README.md.
